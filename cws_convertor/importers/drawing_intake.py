"""Source-bound drawing tables and planar plate intake, without grade defaults.

Supported deterministic route: a single-position Tekla plate drawing, with
Model Part/Bolt geometry and a labelled paper-space bill of materials. Other
layouts remain documents with explicit review reasons, never empty success.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import math
import re
from typing import Any

from cws_convertor.project.model import Part, Assembly, SourceIdentity, FieldProvenance, stable_sha256


def _expanded(entities, ancestry=(), depth=0, annotations=False):
    if depth > 32:
        raise ValueError("DXF-blokhiërarchie te diep")
    for entity in entities:
        if entity.dxftype() == 'INSERT':
            name = entity.dxf.name
            if name in ancestry:
                raise ValueError("Cyclische DXF-blokverwijzing")
            if int(entity.dxf.get('row_count', 1)) != 1 or int(entity.dxf.get('column_count', 1)) != 1:
                raise ValueError("DXF-array vereist expliciete exemplaarselectie")
            skipped=[]
            children = list(entity.virtual_entities(skipped_entity_callback=lambda e,r:skipped.append(str(r)) if not (annotations and e.dxftype() in {'OLE2FRAME','VIEWPORT','IMAGE'}) else None))
            if skipped:
                raise ValueError("DXF-transformatie niet exact ondersteund: " + '; '.join(skipped))
            yield from _expanded(children, (*ancestry,name), depth+1, annotations)
            yield from entity.attribs
        else:
            yield entity


def _texts(entities):
    result=[]
    for e in _expanded(entities, annotations=True):
        if e.dxftype() not in {'TEXT','MTEXT','ATTRIB'}:
            continue
        text=e.plain_text() if e.dxftype()=='MTEXT' else str(e.dxf.text)
        text=re.sub(r'\s+',' ',text).strip()
        if text:
            result.append({'text':text, 'x':float(e.dxf.insert.x), 'y':float(e.dxf.insert.y)})
    return result


def _number(text):
    value=float(str(text).strip().replace(',','.'))
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Ongeldige positieve bronmaat/aantal")
    return value


def analyze_dxf_plate(path: str | Path) -> dict[str, Any]:
    import ezdxf
    from shapely.geometry import LineString, Point
    from shapely.ops import polygonize
    from material_database import MaterialDatabase
    doc=ezdxf.readfile(path)
    # Paper-space values are declared millimetres in this format. Unknown units
    # cannot be inferred from apparent size or from a default project material.
    if doc.units != 4:
        raise ValueError("Deze DXF-plaatroute vereist expliciete millimetereenheden")
    rows=[];totals=[];layout_names=[]
    headers=['Pos','Profiel','Materiaal','Lengte','Aantal','Merk']
    for layout in doc.layouts:
        if layout.name == 'Model':continue
        texts=_texts(layout)
        candidates=[t for t in texts if t['text'].casefold()=='pos']
        for anchor in candidates:
            band=[t for t in texts if abs(t['y']-anchor['y'])<0.15]
            found={h:next((t for t in band if t['text'].casefold()==h.casefold()),None) for h in headers}
            if not all(found.values()):continue
            xs=[found[h]['x'] for h in headers]
            if xs != sorted(xs) or len(set(xs))!=6:
                raise ValueError("Onduidelijke DXF-stuklijstkolommen")
            bounds=[(xs[i]+xs[i+1])/2 for i in range(5)]
            total_labels=[t for t in texts if t['y']<anchor['y'] and t['text'].casefold().startswith('totaal aantal')]
            if not total_labels:raise ValueError("Stuklijst mist expliciet totaalaantal")
            total_label=max(total_labels,key=lambda t:t['y'])
            total_numbers=[t for t in texts if abs(t['y']-total_label['y'])<0.15 and t['x']>total_label['x'] and re.fullmatch(r'\d+',t['text'])]
            if len(total_numbers)!=1:raise ValueError("Onduidelijk totaalaantal in stuklijst")
            totals.append(int(total_numbers[0]['text']));layout_names.append(layout.name)
            marks=[t for t in texts if total_label['y']<t['y']<anchor['y'] and abs(t['x']-xs[0])<1.5]
            for mark in sorted(marks,key=lambda t:-t['y']):
                cells=[[] for _ in headers]
                for t in texts:
                    if abs(t['y']-mark['y'])<0.15 and xs[0]-1.5<=t['x']<=xs[-1]+12:
                        column=sum(t['x']>edge for edge in bounds)
                        cells[column].append(t['text'])
                if any(len(cell)!=1 for cell in cells):raise ValueError("Onvolledige of dubbele DXF-stuklijstregel")
                values=[c[0] for c in cells];quantity=_number(values[4])
                if int(quantity)!=quantity:raise ValueError("Geen geheel productieaantal")
                rows.append(dict(position=values[0],profile=values[1],material=values[2],
                                 length_mm=_number(values[3]),quantity=int(quantity),assembly_mark=values[5],
                                 layout=layout.name,source_row_y=mark['y']))
    if not rows or len(totals)!=1:
        raise ValueError("Geen unieke gelabelde plaatstuklijst; documentbeoordeling vereist")
    identities={(r['position'],r['profile'],r['material'],r['length_mm']) for r in rows}
    if len(identities)!=1:raise ValueError("Meerdere/tegenstrijdige plaatposities vereisen afzonderlijke geometriekoppeling")
    position,profile,grade,length=next(iter(identities))
    match=re.fullmatch(r'(?:STRIP|PL|PLAAT)\s*(\d+(?:[.,]\d+)?)\s*[Xx*×]\s*(\d+(?:[.,]\d+)?)',profile)
    if not match:raise ValueError("Plaatdikte/breedte niet expliciet herkenbaar")
    thickness,width=map(_number,match.groups())
    resolution=MaterialDatabase().resolve(grade)
    if not resolution.resolved:raise ValueError("Expliciete materiaalgrade niet eenduidig herkend")
    if sum(r['quantity'] for r in rows)!=totals[0]:raise ValueError("Rijaantallen en afgedrukt totaal verschillen")
    part_entities=[];hole_entities=[];model_marks=[]
    for e in doc.modelspace():
        if e.dxftype()!='INSERT':continue
        kind=e.dxf.name.split('-',1)[0].casefold()
        if kind=='part':part_entities.extend(_expanded([e]))
        elif kind=='bolt':hole_entities.extend(_expanded([e]))
        elif kind=='mark':model_marks.extend(_texts([e]))
    if not any(t['text']==position for t in model_marks):
        raise ValueError("Model-posmerk en stuklijst zijn niet gekoppeld")
    lines=[]
    for e in part_entities:
        if e.dxftype()=='LINE':
            if abs(e.dxf.start.z)>1e-6 or abs(e.dxf.end.z)>1e-6:raise ValueError("Niet-vlakke plaatcontour")
            lines.append(LineString([(round(e.dxf.start.x,6),round(e.dxf.start.y,6)),
                                     (round(e.dxf.end.x,6),round(e.dxf.end.y,6))]))
        elif e.dxftype()=='LWPOLYLINE' and e.closed and not e.has_arc:
            points=[(round(x,6),round(y,6)) for x,y,*_ in e.get_points()];lines.append(LineString(points+[points[0]]))
        else:
            raise ValueError("Contour bevat niet exact ondersteunde curves; geen benaderde CNC-geometrie")
    polygons=list(polygonize(lines))
    if len(polygons)!=1 or not polygons[0].is_valid or polygons[0].interiors:
        raise ValueError("Geen unieke geldige gesloten plaatomtrek")
    poly=polygons[0];x0,y0,x1,y1=poly.bounds;dx,dy=x1-x0,y1-y0
    swap=False
    if abs(dx-length)<1e-4 and abs(dy-width)<1e-4:pass
    elif abs(dy-length)<1e-4 and abs(dx-width)<1e-4:swap=True
    else:raise ValueError("Modelmaten en stuklijstmaten verschillen; geen bladschaal op Model toepassen")
    holes=[]
    for e in hole_entities:
        if e.dxftype()=='LINE':continue  # graphical centre crosses, not cuts
        if e.dxftype()!='CIRCLE':raise ValueError("Onzekere bewerkingsgeometrie in Bolt-blok")
        c=e.dxf.center;r=float(e.dxf.radius)
        if r<=0 or abs(c.z)>1e-6 or not poly.contains(Point(c.x,c.y)) or Point(c.x,c.y).distance(poly.boundary)<r-1e-5:
            raise ValueError("Boring ligt niet volledig binnen de contour")
        holes.append({'x_mm':c.x-x0,'y_mm':c.y-y0,'diameter_mm':2*r})
    for i,a in enumerate(holes):
        for b in holes[:i]:
            if math.hypot(a['x_mm']-b['x_mm'],a['y_mm']-b['y_mm']) < (a['diameter_mm']+b['diameter_mm'])/2-1e-6:
                raise ValueError("Dubbele of overlappende boringen")
    outer=[(x-x0,y-y0) for x,y in poly.exterior.coords[:-1]]
    def transform(x,y):return (y,x) if swap else (x,y)
    local_holes=[{'x':transform(h['x_mm'],h['y_mm'])[0],'q':transform(h['x_mm'],h['y_mm'])[1],
                  'diameter':h['diameter_mm'],'depth':thickness,'face':'v','kind':'hole','operation':'drill'} for h in holes]
    result={'schema':'cws-dxf-plate-source-1','position':position,'profile':profile,'material':resolution.definition.code,
            'length_mm':length,'width_mm':width,'thickness_mm':thickness,'quantity':totals[0],
            'rows':rows,'source_model_dimensions_mm':[dx,dy],'source_holes':holes,
            'outer_contour':[transform(x,y) for x,y in outer],'holes':local_holes,
            'source_origin_mm':[x0,y0],'local_axis_swap':swap,'layout_names':layout_names,
            'scope':'exact planar source geometry and explicit table; production release remains separate'}
    result['geometry_sha256']=stable_sha256({k:result[k] for k in ('outer_contour','holes','thickness_mm')})
    return result


def materialize_dxf_plate(project, source, report, *, user='drawing-import'):
    position=report['position']
    identity=SourceIdentity(source_format='DXF',source_file_id=source.source_id,source_sha256=source.sha256,
                            source_entity_id='plate:'+position,part_position=position)
    identifier=project.stable_entity_id('part',identity)
    old=project.parts.get(identifier)
    if old is not None:
        if old.properties.get('dxf_source_report') != report:
            raise ValueError("Bestaande plaat is gewijzigd; revisiepad vereist")
        return old
    length,width,thickness=(report[k] for k in ('length_mm','width_mm','thickness_mm'))
    part=Part(internal_id=identifier,name=position,category='make_part',source_identity=identity,
              part_position=position,part_type='plate',profile=report['profile'],profile_type='B',
              material=report['material'],material_grade=report['material'],normalized_material=report['material'],
              material_confidence=1.0,quantity_total=report['quantity'],length_mm=length,
              geometry_descriptor={'source_format':'DXF','source_geometry_hash':report['geometry_sha256'],
                  'plate_geometry':{'outer_contour':report['outer_contour'],'inner_contours':[],
                     'thickness_mm':thickness,'width_mm':width,'bbox_mm':[length,width,thickness]},
                  'analytic_holes':report['holes'], 'geometry_role':'document_bound_planar_solid'},
              production_features=[{'kind':'contour','face':'AK:v','points':[{'x':x,'q':y,'radius':0.0} for x,y in report['outer_contour']]}]+report['holes'],
              properties={'dxf_source_report':report,'source_quantity_locations':report['rows'],
                          'material_recognition_status':'source_confirmed','manufacturing_release_required':True},
              nc1_eligible=False,export_status='blocked_pending_drawing_review',status='review_required')
    from canonical_model import (CanonicalPart, CanonicalHeader, CanonicalProductData,
                                 CanonicalHole, CanonicalContour, CanonicalContourPoint, CanonicalQuestion)
    canonical = CanonicalPart(source_format='DXF',source_file=source.file_name,source_sha256=source.sha256,
        import_method='dxf_planar_table_verified',part_id=position,
        header=CanonicalHeader(position_number=position,part_number=position,material=report['material'],
            quantity=report['quantity'],profile=report['profile'],profile_type='B',length=length,saw_length=length,
            dim1=width,dim2=thickness),
        product=CanonicalProductData(name=position,material_grade=report['material'],length_mm=length,
            profile_designation=report['profile'],plate_thickness_mm=thickness),
        contours=[CanonicalContour(kind='AK',face='v',points=[CanonicalContourPoint(x=x,q=y) for x,y in report['outer_contour']])],
        holes=[CanonicalHole(face=h['face'],x=h['x'],q=h['q'],diameter=h['diameter'],depth=h['depth'],operation=h['operation']) for h in report['holes']])
    canonical.validation.unresolved_questions.append(CanonicalQuestion('drawing-release','validation',
        'Beoordeel de gekoppelde DXF-bron en productievrijgave.'))
    part.set_canonical(canonical)
    part.geometry_descriptor['source_locator']={
        'schema_version':1,'source_format':'DXF','source_file_id':source.source_id,
        'source_sha256':source.sha256,'source_entity_id':identity.source_entity_id,
        'source_geometry_hash':report['geometry_sha256'],
        'selector':{'kind':'dxf_plate_position','position':position}}
    # One aggregate plate has a quantity distribution across assembly marks;
    # do not multiply the same aggregate by an assembly occurrence a second time.
    amounts=defaultdict(int)
    for row in report['rows']:amounts[row['assembly_mark']]+=row['quantity']
    for mark,count in sorted(amounts.items()):
        candidates=[a for a in project.assemblies.values() if a.assembly_mark==mark]
        if len(candidates)>1:raise ValueError("Samenstellingsmerk niet uniek in project: "+mark)
        if candidates:assembly=candidates[0]
        else:
            ai=SourceIdentity(source_format='DXF',source_file_id=source.source_id,source_sha256=source.sha256,
                              source_entity_id='bom-assembly:'+mark,assembly_mark=mark)
            assembly=Assembly(internal_id=project.stable_entity_id('assembly',ai),name=mark,assembly_mark=mark,
                              source_identity=ai,properties={'source':'drawing_quantity_allocation','geometry_placement_unknown':True})
            project.assemblies[assembly.internal_id]=assembly
        part.assembly_ids.append(assembly.internal_id);part.quantity_per_assembly[assembly.internal_id]=count
        if part.internal_id not in assembly.part_ids:assembly.part_ids.append(part.internal_id)
    for field in ('part_position','profile','material','material_grade','quantity_total','length_mm','geometry_descriptor','production_features'):
        part.field_provenance[field]=FieldProvenance(source_file_id=source.source_id,source_entity_id=identity.source_entity_id,
                source_path='DXF Model Part/Bolt + labelled paper-space table',method='dxf_planar_table_verified',confidence=1.0,status='source_confirmed')
    part.recompute_hashes();project.add_entity(part,user=user)
    return part


def analyze_assembly_pdf(path: str | Path) -> dict[str, Any] | None:
    """Read bounded PART NUMBER/QTY tables by word coordinates, not title text."""
    import fitz
    rows=[];drawing='';source_pages=[]
    with fitz.open(path) as doc:
        for page_index,page in enumerate(doc,1):
            words=page.get_text('words')
            headers=[w for w in words if w[4].upper() in {'QTY','QTY.','AANTAL'}]
            for h in headers:
                band=[w for w in words if abs((w[1]+w[3]-h[1]-h[3])/2)<3]
                bytext={w[4].upper():w for w in band}
                if not {'PART','NUMBER'}<=bytext.keys():continue
                # The left column is an item number; require its explicit header.
                item=next((w for w in band if w[4].upper() in {'ITEM','ITEM.','POS','POS.'}),None)
                if item is None:continue
                centers={'item':(item[0]+bytext.get('NO.',item)[2])/2,'quantity':(h[0]+h[2])/2,
                         'part_number':(bytext['PART'][0]+bytext['NUMBER'][2])/2}
                aliases={'length_mm':{'LENGTH','LENGTE'},'angle_1':{'ANGLE1','ANGLE_1'},'angle_2':{'ANGLE2','ANGLE_2'}}
                # Use remaining header word blocks (ANGLE plus 1/2) as separate columns.
                for w in band:
                    text=w[4].upper()
                    if text in {'LENGTH','LENGTE'}:centers['length_mm']=(w[0]+w[2])/2
                    if text in {'DESCRIPTION','OMSCHRIJVING'}:centers['description']=(w[0]+w[2])/2
                    if text in {'REV.','REV'}:centers['revision']=(w[0]+w[2])/2
                    if text in {'ANGLE1','ANGLE2'}:centers['angle_'+text[-1]]=(w[0]+w[2])/2
                angles=sorted((w for w in band if w[4].upper()=='ANGLE'),key=lambda w:w[0])
                for i,w in enumerate(angles[:2],1):centers[f'angle_{i}']=(w[0]+w[2])/2
                columns=sorted(centers,key=centers.get);xs=[centers[k] for k in columns]
                grid=[]
                header_y=(h[1]+h[3])/2
                for drawing_path in page.get_drawings():
                    for segment in drawing_path['items']:
                        if segment[0]!='l':continue
                        a,b=segment[1:3]
                        if abs(a.x-b.x)<0.1 and min(a.y,b.y)<=header_y<=max(a.y,b.y):
                            if not any(abs(a.x-x)<0.1 for x in grid):grid.append(a.x)
                grid.sort()
                cell_bounds=[]
                for x in xs:
                    cell=next(((a,b) for a,b in zip(grid,grid[1:]) if a<x<b),None)
                    if cell is None:break
                    cell_bounds.append(cell)
                if len(cell_bounds)!=len(columns) or len(set(cell_bounds))!=len(columns):
                    continue  # no proven column geometry; do not guess table cells
                edges=[bounds[1] for bounds in cell_bounds[:-1]]
                table_left,table_right=cell_bounds[0][0],cell_bounds[-1][1]
                # Item column anchors keep dimensions elsewhere on the page out.
                anchors=sorted((w for w in words if w[1]>h[3] and re.fullmatch(r'\d+',w[4]) and cell_bounds[columns.index('item')][0]<=w[0]<cell_bounds[columns.index('item')][1]),key=lambda w:w[1])
                local=[]
                for anchor in anchors:
                    number=int(anchor[4])
                    if number!=len(local)+1:break
                    cy=(anchor[1]+anchor[3])/2
                    line=[w for w in words if abs((w[1]+w[3])/2-cy)<2 and table_left<=w[0]<table_right-0.1]
                    cells={k:[] for k in columns}
                    for w in sorted(line,key=lambda w:w[0]):
                        # assign by centre; long part names are handled using next
                        # column's first observed numeric field below.
                        index=sum(w[0]+0.1>e for e in edges)
                        cells[columns[index]].append(w[4])
                    quantity=' '.join(cells.get('quantity',[]))
                    if not quantity.isdigit():raise ValueError('Onvolledige PDF-stuklijstregel: aantal')
                    part_number=' '.join(cells.get('part_number',[])).strip()
                    description=' '.join(cells.get('description',[])).strip()
                    if not part_number and not description:raise ValueError('Onvolledige PDF-stuklijstregel: identiteit')
                    row={'item':number,'quantity':int(quantity),'part_number':part_number,'description':description,'revision':' '.join(cells.get('revision',[])),'page':page_index,
                         'bbox':[item[0],anchor[1],page.rect.width,anchor[3]]}
                    for key in ('length_mm','angle_1','angle_2'):
                        text=' '.join(cells.get(key,[]));row[key]=text
                    local.append(row)
                if len(local)>=2:
                    rows.extend(local);source_pages.append(page_index)
            # Source drawing number must be printed, not guessed from the filename.
            labels=[w for w in words if w[4].casefold().rstrip(':') in {'tekeningnummer','drawingnumber','drawingno.'}]
            for label in labels:
                nearby=[w for w in words if label[1]<=w[1]<=label[3]+35 and
                        label[0]-5<=w[0]<=label[0]+160 and re.fullmatch(r'\d{2}-\d{3}-\d{3}',w[4])]
                if len(nearby)==1:drawing=nearby[0][4]
    if not rows:return None
    return {'schema':'cws-pdf-assembly-table-1','drawing_number':drawing,'rows':rows,
            'total_quantity':sum(r['quantity'] for r in rows),'row_count':len(rows),
            'pages':source_pages,'scope':'document BOM evidence; geometry and revision review required'}


def import_drawing_source(session, path: str | Path, *, user='drawing-import') -> dict:
    """Atomic drawing intake through the existing project/session storage."""
    from cws_convertor.project.model import ProjectModel
    from cws_convertor.project.classification import classify_project
    from cws_convertor.project.baseline import sha256_file
    path=Path(path).resolve();session._ensure_writable()
    report=analyze_dxf_plate(path) if path.suffix.lower()=='.dxf' else analyze_assembly_pdf(path)
    if report is None:return {'status':'document_only','reason':'No labelled assembly table'}
    previous=session.project;old_paths=dict(session.source_paths);old_dirty=session.dirty
    session.project=ProjectModel.from_dict(previous.to_dict())
    try:
        source=session.project.add_source_path(path,user=user)
        if sha256_file(path)!=source.sha256:raise ValueError("Tekening gewijzigd tijdens import")
        session.source_paths[source.source_id]=path
        if path.suffix.lower()=='.dxf':
            part=materialize_dxf_plate(session.project,source,report,user=user)
            classify_project(session.project,user=user,source_ids=[source.source_id])
            result={'status':'imported','part_ids':[part.internal_id],'quantity':part.quantity_total,'rows':len(report['rows'])}
        else:
            # Link exact declared part numbers only. No fuzzy filename match,
            # quantity overwrite, material propagation or revision approval.
            links=[]
            for row in report['rows']:
                matches=[p for p in session.project.parts.values() if row['part_number'] and row['part_number'] in
                         {p.part_position,p.name,p.properties.get('step_product_name','')}]
                links.append({'item':row['item'],'part_ids':[p.internal_id for p in matches],
                              'source_quantity':row['quantity'],'model_quantity':sum(p.quantity_total for p in matches),
                              'status':'quantity_match' if matches and sum(p.quantity_total for p in matches)==row['quantity'] else 'review_required'})
            report['model_links']=links
            result={'status':'bom_document','rows':report['row_count'],'quantity':report['total_quantity']}
        source.analysis['drawing_intake']=report;source.analysis_status='imported'
        source.semantic_import_complete=True;source.production_export_allowed=False
        session.project.settings.setdefault('drawing_source_evidence',{})[source.source_id]=report
        session.project.audit('project.drawing_source_imported',user=user,details={'source_id':source.source_id,**result})
        session.project.validate();session.dirty=True
        return result
    except Exception:
        session.project=previous;session.source_paths=old_paths;session.dirty=old_dirty
        raise
