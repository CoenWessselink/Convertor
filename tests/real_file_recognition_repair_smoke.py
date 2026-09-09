"""Generalised regressions for private-file findings; no private CAD is stored."""
from __future__ import annotations
from pathlib import Path
import copy
import dataclasses
import json
import re
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from cws_convertor.project import ProjectSession
from cws_convertor.importers.p21 import P21Document,P21ParseError
from cws_convertor.importers.step_project import StepIndex
from cws_convertor.importers.drawing_intake import analyze_dxf_plate,analyze_assembly_pdf
from cws_convertor.project.source_geometry import inspect_part_source_geometry
from cws_convertor.manufacturing_interpreter.reconstruction import prove_equivalence
from cws_convertor.manufacturing_interpreter.contracts import GeometryProofStatus
from cws_convertor.steel_model.tolerances import DEFAULT_TOLERANCE_POLICY


def hierarchy_text(cycle=False):
    lines=[]
    for i,name in [(1,'ROOT'),(2,'REUSED'),(3,'LEAF'),(4,'LOOSE'),(5,'SURFACE')]:
        j=i*10
        lines.extend([f"#{j}=PRODUCT('{name}','{name}','',());",
                      f"#{j+1}=PRODUCT_DEFINITION_FORMATION('','',#{j});",
                      f"#{j+2}=PRODUCT_DEFINITION('','',#{j+1},$);"])
    for n,p,c in [(101,12,22),(102,12,22),(103,22,32),(104,22,32)]:
        lines.append(f"#{n}=NEXT_ASSEMBLY_USAGE_OCCURRENCE('{n}','  ','',#{p},#{c},'');")
    if cycle:lines.append("#105=NEXT_ASSEMBLY_USAGE_OCCURRENCE('105','','',#32,#12,'');")
    for n,definition,kind in [(201,32,'MANIFOLD_SOLID_BREP'),(211,42,'MANIFOLD_SOLID_BREP'),(221,52,'SHELL_BASED_SURFACE_MODEL')]:
        lines.extend([f"#{n}=PRODUCT_DEFINITION_SHAPE('','',#{definition});",
                      f"#{n+1}=SHAPE_DEFINITION_REPRESENTATION(#{n},#{n+2});",
                      f"#{n+2}=SHAPE_REPRESENTATION('',(#{n+3}),$);",
                      f"#{n+3}={kind}('',());"])
    return "ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\n"+'\n'.join(lines)+"\nENDSEC;\nEND-ISO-10303-21;"


def dxf_fixture(path, *, quantity=5,total=5,grade='S235JR',units=4,duplicate_hole=False):
    import ezdxf
    d=ezdxf.new('R2010');d.units=units
    b=d.blocks.new('Part-TEST');b.add_lwpolyline([(0,0),(100,0),(100,40),(0,40)],close=True)
    d.modelspace().add_blockref('Part-TEST',(20,30))
    b=d.blocks.new('Bolt-TEST');b.add_circle((0,0),4)
    d.modelspace().add_blockref('Bolt-TEST',(80,50))
    if duplicate_hole:d.modelspace().add_blockref('Bolt-TEST',(80,50))
    b=d.blocks.new('Mark-TEST');b.add_text('T1',dxfattribs={'height':2.5});d.modelspace().add_blockref('Mark-TEST',(150,30))
    l=d.layouts.get('Layout1');xs=[0,20,55,80,100,120]
    for x,text in zip(xs,['Pos','Profiel','Materiaal','Lengte','Aantal','Merk']):l.add_text(text,dxfattribs={'insert':(x,20),'height':2.5})
    for x,text in zip(xs,['T1','STRIP5*40',grade,'100',str(quantity),'ASM']):l.add_text(text,dxfattribs={'insert':(x,15),'height':2.5})
    l.add_text('Totaal aantal:',dxfattribs={'insert':(80,10),'height':2.5});l.add_text(str(total),dxfattribs={'insert':(105,10),'height':2.5})
    d.saveas(path)


class SourceIntakeRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def session(self,path):
        session=ProjectSession.new('test');self.addCleanup(session.close)
        source=session.register_sources([path],include_step_geometry=False)[0].source
        result=session.semantic_import_source(source.source_id)
        return session,source,result
    def test_reused_assemblies_expand_all_paths_and_loose_roots(self):
        p=self.root/'tree.stp';p.write_text(hierarchy_text());s,_,r=self.session(p)
        self.assertEqual(6,len(s.project.parts));self.assertEqual(3,len(s.project.assemblies))
        leaves=[v for v in s.project.parts.values() if v.properties['step_product_name']=='LEAF']
        self.assertEqual(4,len(leaves));self.assertEqual(4,len({v.source_identity.occurrence_id for v in leaves}))
        self.assertTrue(all(v.name.strip()=='LEAF' for v in leaves))
        self.assertEqual(1,sum(v.category=='reference' for v in s.project.parts.values()))
        self.assertTrue(r.evidence['all_current_products_preserved'])
    def test_occurrence_identity_repeat_is_stable(self):
        p=self.root/'tree.stp';p.write_text(hierarchy_text());s,source,_=self.session(p);a=set(s.project.parts)
        s.semantic_import_source(source.source_id);self.assertEqual(a,set(s.project.parts))
    def test_cycles_cannot_hide_behind_independent_root(self):
        p=self.root/'cycle.stp';p.write_text(hierarchy_text(True))
        with self.assertRaises(Exception):self.session(p)
    def test_complex_records_keep_references_and_strings(self):
        p=self.root/'complex.stp';p.write_text("ISO-10303-21;DATA;#71=(REPRESENTATION_RELATIONSHIP('a (x)','can''t',#3,#4) REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION(#5) SHAPE_REPRESENTATION_RELATIONSHIP());#90=(LENGTH_UNIT() NAMED_UNIT(*) SI_UNIT(.MILLI.,.METRE.));ENDSEC;END-ISO-10303-21;")
        d=P21Document.load(p);e=d.get(71)
        self.assertEqual('REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION',e.type_name)
        self.assertEqual((3,4,5),e.references);self.assertEqual("can't",e.string(1));self.assertIn(90,d.entities)
    def test_dxf_model_and_table_intake_preserves_quantity_holes_and_locations(self):
        path=self.root/'plate.dxf';dxf_fixture(path);report=analyze_dxf_plate(path)
        self.assertEqual(5,report['quantity']);self.assertEqual(1,len(report['holes']))
        self.assertEqual((60,20),(report['holes'][0]['x'],report['holes'][0]['q']))
        s=ProjectSession.new('plate');self.addCleanup(s.close);result=s.import_drawing_source(path)
        p=next(iter(s.project.parts.values()));self.assertEqual(5,p.quantity_total);self.assertEqual(1,len(p.canonical_part['holes']))
        self.assertEqual(5,sum(p.quantity_per_assembly.values()));self.assertFalse(p.nc1_eligible)
        self.assertEqual(1,len(s.project.parts));self.assertEqual('imported',result['status'])
        s.import_drawing_source(path);self.assertEqual(1,len(s.project.parts))
        file=s.save(self.root/'project.cwscproj')
        with ProjectSession.open(file) as reopened:
            q=next(iter(reopened.project.parts.values()));self.assertEqual(5,q.quantity_total)
            src=reopened.project.sources[q.source_identity.source_file_id]
            ins=inspect_part_source_geometry(q,src,reopened.source_paths[src.source_id])
            self.assertTrue(ins.selection_verified);self.assertTrue(ins.production_geometry_exact)
            self.assertAlmostEqual(100*40*5-3.141592653589793*16*5,ins.metrics['volume_mm3'],places=5)
    def test_dxf_nonclosing_quantity_fails_without_mutating_project(self):
        p=self.root/'bad.dxf';dxf_fixture(p,total=6);s=ProjectSession.new('x');self.addCleanup(s.close)
        before=s.project.to_dict()
        with self.assertRaises(ValueError):s.import_drawing_source(p)
        self.assertEqual(before,s.project.to_dict())
    def test_dxf_grade_cannot_be_guessed(self):
        p=self.root/'bad.dxf';dxf_fixture(p,grade='UNKNOWN')
        with self.assertRaises(ValueError):analyze_dxf_plate(p)
    def test_dxf_units_cannot_be_guessed(self):
        p=self.root/'bad.dxf';dxf_fixture(p,units=0)
        with self.assertRaises(ValueError):analyze_dxf_plate(p)
    def test_dxf_duplicate_bore_fails(self):
        p=self.root/'bad.dxf';dxf_fixture(p,duplicate_hole=True)
        with self.assertRaises(ValueError):analyze_dxf_plate(p)
    def test_native_selector_uses_nonsequential_labels(self):
        import cadquery as cq
        from cws_convertor.project.step_native import resolve_step_roots
        import hashlib
        p=self.root/'native.step'
        cq.exporters.export(cq.Compound.makeCompound([cq.Solid.makeBox(10,20,30),cq.Solid.makeBox(4,5,6,cq.Vector(100,0,0))]),str(p))
        text=p.read_text();ids=sorted(set(int(v) for v in re.findall(r'#(\d+)\s*=',text)))
        mapping={v:90000+(len(ids)-i)*13 for i,v in enumerate(ids)}
        text=re.sub(r'#(\d+)',lambda m:'#'+str(mapping[int(m[1])]),text);p.write_text(text)
        idx=StepIndex.build(P21Document.load(p));sha=hashlib.sha256(p.read_bytes()).hexdigest()
        volumes=[]
        for entity in idx.solid_roots:
            shape,proof=resolve_step_roots(p,sha,(entity,));volumes.append(round(shape.Volume(),6))
            self.assertEqual([f'#{entity}'],proof['selector_entity_ids'])
        self.assertEqual([120.0,6000.0],sorted(volumes))
        with self.assertRaises(ValueError):resolve_step_roots(p,sha,(1,))
        p.write_text(text+'\n')
        with self.assertRaises(ValueError):resolve_step_roots(p,sha,tuple(idx.solid_roots))
    def test_omitted_local_hole_does_not_pass_large_global_volume_tolerance(self):
        import cadquery as cq
        base=cq.Solid.makeBox(2000,300,50)
        source=base.cut(cq.Solid.makeCylinder(7,5,cq.Vector(1000,150,45)))
        proof=prove_equivalence(source,base,DEFAULT_TOLERANCE_POLICY)
        self.assertEqual(GeometryProofStatus.FAILED,proof.status)
        exact=prove_equivalence(source,source.copy(),DEFAULT_TOLERANCE_POLICY)
        self.assertEqual(GeometryProofStatus.PROVEN_BREP_EQUIVALENT,exact.status)
    def test_ifc_explicit_mark_and_context_are_not_technical_id_or_steel(self):
        from tests.ifc_material_recognition_smoke import _import_fixture
        session=_import_fixture("IFC4", """
#10=IFCBEAM('PART-A',$,'Beam',$,$,$,$,'ID-TECHNICAL',.BEAM.);
#11=IFCBEAM('PART-B',$,'Wall',$,$,$,$,'ID-WALL',.BEAM.);
#20=IFCPROPERTYSINGLEVALUE('Part mark',$,IFCLABEL('P-A'),$);
#21=IFCPROPERTYSINGLEVALUE('Grade',$,IFCLABEL('S235JR'),$);
#22=IFCPROPERTYSET('PA',$,'Tekla Common',$,(#20,#21));
#23=IFCRELDEFINESBYPROPERTIES('RA',$,$,$,(#10),#22);
#24=IFCPROPERTYSINGLEVALUE('Part mark',$,IFCLABEL('W-A'),$);
#25=IFCPROPERTYSINGLEVALUE('Grade',$,IFCLABEL('METSELWERK'),$);
#26=IFCPROPERTYSET('PB',$,'Tekla Common',$,(#24,#25));
#27=IFCRELDEFINESBYPROPERTIES('RB',$,$,$,(#11),#26);
#30=IFCMATERIAL('CONCRETE/METSELWERK',$,$);
#31=IFCRELASSOCIATESMATERIAL('MAT',$,$,$,(#11),#30);
""")
        self.addCleanup(session.close)
        parts={part.part_position:part for part in session.project.parts.values()}
        self.assertEqual({'P-A','W-A'},set(parts));self.assertEqual('METSELWERK',parts['W-A'].material)
        self.assertEqual('non_steel',parts['W-A'].category);self.assertFalse(parts['W-A'].nc1_eligible)
        self.assertEqual('S235JR',parts['P-A'].material)

    def test_native_component_selector_cannot_switch_roots_or_forge_hash(self):
        import cadquery as cq
        p=self.root/'two.step'
        cq.exporters.export(cq.Compound.makeCompound([cq.Solid.makeBox(10,20,30),cq.Solid.makeBox(4,5,6,cq.Vector(100,0,0))]),str(p))
        s,source,_=self.session(p);parts=list(s.project.parts.values());self.assertEqual(2,len(parts))
        a,b=parts;first=copy.deepcopy(a.geometry_descriptor)
        a.geometry_descriptor['source_locator']['selector']['entity_ids']=b.geometry_descriptor['source_locator']['selector']['entity_ids']
        with self.assertRaises(Exception):inspect_part_source_geometry(a,source,p)
        a.geometry_descriptor=first
        a.geometry_descriptor['source_geometry_hash']='a'*64
        a.geometry_descriptor['source_locator']['source_geometry_hash']='a'*64
        result=inspect_part_source_geometry(a,source,p)
        self.assertFalse(result.production_geometry_exact)

    def test_native_nested_assembly_placements_match_all_root_geometry(self):
        import cadquery as cq
        from OCP.gp import gp_Trsf
        from collections import Counter
        component=cq.Solid.makeBox(7,11,19)
        sub=cq.Assembly(name='sub').add(component,name='one',loc=cq.Location((4,6,8)))
        sub.add(component,name='two',loc=cq.Location((40,50,60),(0,0,1),35))
        assembly=cq.Assembly(name='root').add(sub,name='s1',loc=cq.Location((100,200,300)))
        assembly.add(sub,name='s2',loc=cq.Location((-120,80,40),(0,1,0),30))
        path=self.root/'assembly.step';assembly.save(str(path))
        session,source,_=self.session(path)
        self.assertEqual(4,len(session.project.parts))
        observed=[]
        for part in session.project.parts.values():
            inspection=inspect_part_source_geometry(part,source,path);self.assertTrue(inspection.production_geometry_exact)
            transform=gp_Trsf();transform.SetValues(*[v for row in part.global_placement.matrix[:3] for v in row])
            native=inspection.native_shape.moved(cq.Location(transform))
            observed.append(tuple(round(v,5) for v in native.Center().toTuple()))
        expected=[tuple(round(v,5) for v in solid.Center().toTuple()) for shape in cq.importers.importStep(str(path)).vals() for solid in shape.Solids()]
        self.assertEqual(Counter(expected),Counter(observed))

    def test_source_hole_completeness_matches_position_side_and_diameter(self):
        from types import SimpleNamespace
        from cws_convertor.manufacturing_interpreter.source_operations import compare_source_holes
        def feature(identity,x,z=0,diameter=8):
            return SimpleNamespace(feature_id=identity,semantic_type=SimpleNamespace(value='HOLE'),parameters=tuple(dict(
                origin_x=x,origin_y=20,origin_z=z,axis_x=0,axis_y=0,axis_z=1,diameter_mm=diameter,depth_mm=5).items()))
        evidence={'header':{'profile_type':'B','dim1':40,'dim2':5,'dim3':0,'dim4':0},'holes':[
            {'face':'v','x':30,'q':20,'diameter':8,'depth':0,'operation':''},
            {'face':'v','x':60,'q':20,'diameter':8,'depth':0,'operation':''}]}
        good=SimpleNamespace(features=(feature('a',30),feature('b',60)))
        self.assertEqual('PASS',compare_source_holes(evidence['header'],evidence['holes'],good.features)['status'])
        for bad in ((feature('a',30),),(feature('a',30),feature('b',61)),
                    (feature('a',30),feature('b',60,diameter=9)),(feature('a',30),feature('b',60,z=5)),
                    (feature('a',30),feature('a',60))):
            self.assertEqual('FAIL',compare_source_holes(evidence['header'],evidence['holes'],bad)['status'])

    def test_original_operation_withdrawal_changes_recognition_cache(self):
        from types import SimpleNamespace
        from cws_convertor.manufacturing_interpreter.recognition_geometry import source_authority_state
        inspection=SimpleNamespace(evidence={'original_nc1_operations':{'status':'PROVEN','source_nc1_sha256':'a'*64}})
        before=source_authority_state(inspection)
        inspection.evidence['original_nc1_operations']['status']='CONFLICT'
        self.assertNotEqual(before,source_authority_state(inspection))

    def test_closed_native_ifc_faces_preserved_but_open_shell_rejected(self):
        import cadquery as cq
        from cws_convertor.project.native_topology import closed_faces_to_solid
        original=cq.Solid.makeBox(9,17,27)
        recovered, evidence=closed_faces_to_solid(cq.Compound.makeCompound(original.Faces()))
        self.assertAlmostEqual(original.Volume(),recovered.Volume(),places=6)
        self.assertEqual(6,evidence['result_face_count']);self.assertFalse(evidence['geometry_added'])
        with self.assertRaises(ValueError):
            closed_faces_to_solid(cq.Compound.makeCompound(original.Faces()[:-1]))

    def test_custom_section_is_named_without_fabricating_catalog_approval(self):
        from cws_convertor.manufacturing_interpreter.contracts import InterpretationReadiness, ProfileRecognition
        # A real native analysis supplies the full dataclass section; this test
        # checks the name/status contract independently of a particular catalogue.
        import cadquery as cq
        from tests.manufacturing_interpreter_phase1_smoke import inspection
        from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter
        from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest
        shape=cq.Solid.makeBox(123.456,23.456,4.123)
        native=ManufacturingGeometryInterpreter(cache_root=self.root/'cache').analyze(ManufacturingInterpretationRequest(inspection=inspection(shape,'custom')))
        self.assertTrue(native.profile.designation.startswith('CUSTOM-'))
        self.assertNotEqual(GeometryProofStatus.PROVEN_WITHIN_POLICY,native.profile.status)
        self.assertNotEqual(InterpretationReadiness.READY,native.readiness)

    def test_pdf_assembly_table_not_tolerance_profile(self):
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Table,TableStyle
        from pdf_support import analyze_pdf
        p=self.root/'drawing.pdf';c=canvas.Canvas(str(p),pagesize=(800,600))
        rows=[['ITEM NO.','QTY.','PART NUMBER','REV.','DESCRIPTION','LENGTH','ANGLE1','ANGLE2'],
              ['1','4','P-A','','Plate','100','0','0'],['2','7','P-B','','Angle','200','0','0']]
        t=Table(rows,colWidths=[60,40,110,35,120,65,65,65],rowHeights=20)
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,(0,0,0)),('FONTSIZE',(0,0),(-1,-1),8)]))
        t.wrapOn(c,780,500);t.drawOn(c,30,300)
        c.drawString(30,100,'DIN ISO 2768');c.drawString(550,100,'Tekeningnummer:');c.drawString(550,84,'21-010-001');c.save()
        report=analyze_assembly_pdf(p);self.assertEqual(11,report['total_quantity']);self.assertEqual(2,report['row_count'])
        candidate=analyze_pdf(p);self.assertEqual('external_assembly_bom',candidate.mode);self.assertFalse(candidate.part.header.profile)
        self.assertFalse(candidate.part.validation.production_export_allowed)

if __name__=='__main__':unittest.main(verbosity=2)
