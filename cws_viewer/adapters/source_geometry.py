"""Verified source resolution and geometry catalogues for CWS Viewer V3.

The catalogue preserves source identity.  It does not infer manufacturing
features and never mutates the Canonical Project Model.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, shutil, zipfile
from pathlib import Path
from typing import Any, Iterable, Mapping

from cws_convertor.importers.ifc_project import _GEOMETRY_STOP_TYPES
from cws_convertor.importers.p21 import P21Document
from cws_viewer.contracts.geometry import GeometryRequest
from cws_viewer.core.serialization import is_sha256, stable_sha256
from cws_viewer.math3d import BoundingBox, Vector3


def _sha256_file(path:Path)->str:
    d=hashlib.sha256()
    with path.open('rb') as h:
        for block in iter(lambda:h.read(1024*1024),b''): d.update(block)
    return d.hexdigest()

def _safe_archive_name(name:str)->bool:
    p=Path(name.replace('\\','/')); return bool(name) and not p.is_absolute() and '..' not in p.parts

def _source_dict(source:Any)->dict[str,Any]:
    return {k: (int(getattr(source,k,0) or 0) if k=='size_bytes' else str(getattr(source,k,'') or ''))
            for k in ('source_id','file_name','source_format','sha256','size_bytes','original_path','embedded_path')}

@dataclass(frozen=True,slots=True)
class ResolvedSource:
    source_id:str; path:Path; source_format:str; sha256:str; size_bytes:int; resolution_method:str

class ProjectSourceResolver:
    def __init__(self, project:Any, *, project_package_path:str|Path|None=None,
                 search_roots:Iterable[str|Path]=(), extraction_root:str|Path|None=None)->None:
        self.project=project
        self.project_package_path=None if project_package_path is None else Path(project_package_path).expanduser().resolve()
        self.search_roots=tuple(Path(p).expanduser().resolve() for p in search_roots)
        self.extraction_root=Path(extraction_root or Path.home()/'.cws_convertor'/'viewer_source_cache').expanduser().resolve()
        self.extraction_root.mkdir(parents=True,exist_ok=True); self._resolved:dict[str,ResolvedSource]={}
    def _verify(self,source:Mapping[str,Any],candidate:Path,method:str)->ResolvedSource|None:
        if not candidate.is_file():return None
        size=int(source.get('size_bytes') or 0)
        if size and candidate.stat().st_size!=size:return None
        actual=_sha256_file(candidate); expected=str(source.get('sha256') or '').lower()
        if expected and actual!=expected:return None
        return ResolvedSource(str(source['source_id']),candidate.resolve(),str(source.get('source_format') or '').upper(),actual,candidate.stat().st_size,method)
    def resolve(self,source_id:str)->ResolvedSource:
        source_id=str(source_id)
        if source_id in self._resolved:return self._resolved[source_id]
        obj=dict(getattr(self.project,'sources',{}) or {}).get(source_id)
        if obj is None:raise FileNotFoundError(f'Projectbron bestaat niet: {source_id}')
        source=_source_dict(obj); source['sha256']=str(source['sha256']).lower(); source['source_format']=str(source['source_format']).upper()
        if not source['source_id'] or not is_sha256(source['sha256']):raise ValueError(f'Projectbron {source_id} heeft ongeldige identiteit/hash')
        if source['original_path']:
            hit=self._verify(source,Path(source['original_path']).expanduser(),'verified_original_path')
            if hit:self._resolved[source_id]=hit;return hit
        for root in self.search_roots:
            hit=self._verify(source,root/source['file_name'],'verified_search_root')
            if hit:self._resolved[source_id]=hit;return hit
        package=self.project_package_path; embedded=str(source['embedded_path'])
        if package and package.is_file() and embedded:
            if not _safe_archive_name(embedded):raise ValueError(f'Onveilig embedded bronpad: {embedded}')
            target=self.extraction_root/source['sha256'][:2]/source['sha256']/source['file_name']; target.parent.mkdir(parents=True,exist_ok=True)
            hit=self._verify(source,target,'verified_extracted_cache')
            if hit:self._resolved[source_id]=hit;return hit
            temp=target.with_suffix(target.suffix+'.tmp');temp.unlink(missing_ok=True)
            with zipfile.ZipFile(package,'r') as ar:
                if embedded not in ar.namelist():raise FileNotFoundError(f'Embedded bron ontbreekt: {embedded}')
                info=ar.getinfo(embedded)
                if int(source['size_bytes'] or 0) and info.file_size!=int(source['size_bytes']):raise ValueError('Embedded brongrootte wijkt af')
                with ar.open(info) as src,temp.open('wb') as dst:shutil.copyfileobj(src,dst)
            hit=self._verify(source,temp,'verified_embedded_extract')
            if hit is None:temp.unlink(missing_ok=True);raise ValueError('Embedded bron faalde SHA-256-verificatie')
            temp.replace(target); hit=ResolvedSource(hit.source_id,target,hit.source_format,hit.sha256,hit.size_bytes,'verified_embedded_extract')
            self._resolved[source_id]=hit;return hit
        raise FileNotFoundError(f"Bronbestand {source['file_name']} ({source_id}) niet gevonden met geldige SHA-256")
    def resolve_all(self)->dict[str,ResolvedSource]:return {sid:self.resolve(sid) for sid in sorted(dict(self.project.sources))}

@dataclass(frozen=True,slots=True)
class EntityGeometryRecord:
    internal_id:str; source_file_id:str; source_entity_id:str; source_format:str; geometry_id:str; source_geometry_hash:str
    source_representation_id:str=''; source_item_ids:tuple[str,...]=(); solid_index:int=0
    fallback_bounds:BoundingBox=BoundingBox.zero(); warnings:tuple[str,...]=(); metadata:tuple[tuple[str,str],...]=()
    def request(self,source:ResolvedSource)->GeometryRequest:
        return GeometryRequest(self.geometry_id,self.source_geometry_hash,self.source_format,self.source_file_id,str(source.path),source.sha256,
                               self.source_entity_id,self.source_representation_id,self.source_item_ids,self.solid_index,'mm',self.metadata)

@dataclass(frozen=True,slots=True)
class GeometryCatalogReport:
    entity_count:int; unique_geometry_count:int; ifc_entity_count:int; step_entity_count:int; proxy_geometry_count:int; missing_identity_count:int; source_count:int; warnings:tuple[str,...]
    def to_dict(self)->dict[str,Any]:
        return {"entity_count":self.entity_count,"unique_geometry_count":self.unique_geometry_count,"ifc_entity_count":self.ifc_entity_count,
                "step_entity_count":self.step_entity_count,"proxy_geometry_count":self.proxy_geometry_count,"missing_identity_count":self.missing_identity_count,
                "source_count":self.source_count,"warnings":list(self.warnings)}

class ProjectGeometryCatalog:
    def __init__(self)->None:
        self.records_by_entity:dict[str,EntityGeometryRecord]={}; self.records_by_geometry:dict[str,EntityGeometryRecord]={}; self.report:GeometryCatalogReport|None=None
        self._documents:dict[str,P21Document]={}
    @staticmethod
    def _entity_source(entity:Any)->tuple[str,str,str]:
        i=getattr(entity,'source_identity',None)
        if i is None:return '','',''
        return str(getattr(i,'source_file_id','') or ''),str(getattr(i,'source_entity_id','') or '').lstrip('#'),str(getattr(i,'source_format','') or '').upper()
    @staticmethod
    def _fallback_bounds(entity:Any)->BoundingBox:
        d=dict(getattr(entity,'geometry_descriptor',{}) or {}); cad=dict(d.get('cad_metrics') or {})
        bbox=cad.get('bbox_mm') or d.get('bbox_sorted_mm') or d.get('dimensions_mm')
        if isinstance(bbox,(list,tuple)) and len(bbox)>=3:
            vals=[max(0.0,float(v or 0)) for v in bbox[:3]]; return BoundingBox.from_dimensions(*vals)
        diameter=max(0.0,float(getattr(entity,'diameter_mm',0) or 0)); length=max(0.0,float(getattr(entity,'length_mm',0) or 0)); size=max(0.0,float(getattr(entity,'size_mm',0) or 0))
        if diameter>0:return BoundingBox.from_dimensions(diameter,diameter,max(length,diameter))
        if length>0:return BoundingBox.from_dimensions(max(length,size,1),max(size,1),max(size,1))
        return BoundingBox.zero()
    @staticmethod
    def _ifc_items(doc:P21Document,source_entity_id:str)->tuple[str,tuple[str,...],str]:
        try:entity=doc.require(int(source_entity_id))
        except (ValueError,KeyError):return '',(),''
        rep_id=entity.ref(6); definition=doc.get(rep_id)
        if definition is None:return str(rep_id or ''),(),''
        shape_ids=definition.refs(2) if definition.type_name=='IFCPRODUCTDEFINITIONSHAPE' else [definition.entity_id]
        items=[]
        for sid in shape_ids:
            shape=doc.get(sid)
            if shape:items.extend(shape.refs(3))
        if not items:return str(rep_id or ''),(),''
        digest=doc.combined_semantic_hash(items,ignore_types=_GEOMETRY_STOP_TYPES,order_independent=True)
        return str(rep_id or ''),tuple(str(x) for x in items),digest
    def build(self,project:Any,resolver:ProjectSourceResolver)->'ProjectGeometryCatalog':
        records={}; unique={}; warnings=[]; missing=ifc_count=step_count=proxy_count=0; step_index:dict[str,int]={}
        cols=(dict(getattr(project,'parts',{}) or {}),dict(getattr(project,'purchased_items',{}) or {}),dict(getattr(project,'fasteners',{}) or {}),dict(getattr(project,'welds',{}) or {}))
        entities=[e for c in cols for e in c.values()]
        for entity in sorted(entities,key=lambda e:str(getattr(e,'internal_id',''))):
            iid=str(getattr(entity,'internal_id','') or ''); sfid,se_id,fmt=self._entity_source(entity)
            if not iid or not sfid or not se_id:missing+=1;continue
            source=resolver.resolve(sfid); descriptor=dict(getattr(entity,'geometry_descriptor',{}) or {}); recwarn=[]; rep='';items=();solid_index=0;source_hash=''
            if fmt=='IFC':
                doc=self._documents.get(sfid)
                if doc is None:doc=P21Document.load(source.path);self._documents[sfid]=doc
                rep,items,computed=self._ifc_items(doc,se_id); dh=str(descriptor.get('source_geometry_hash') or '').lower();source_hash=computed or dh
                if dh and computed and dh!=computed:recwarn.append('IFC descriptorhash wijkt af van bron-Merklehash; bronhash gebruikt')
                ifc_count+=1
            elif fmt=='STEP':
                source_hash=str(descriptor.get('source_geometry_hash') or '').lower();items=tuple(str(v) for v in descriptor.get('solid_root_entity_ids',()) or ())
                solid_index=step_index.get(sfid,0);step_index[sfid]=solid_index+1;step_count+=1
            else:recwarn.append(f'Niet-ondersteund bronformaat: {fmt}')
            proxy=False
            if not is_sha256(source_hash):
                source_hash=stable_sha256({"source_sha256":source.sha256,"source_entity_id":se_id,"kind":type(entity).__name__,
                                          "diameter_mm":getattr(entity,'diameter_mm',0),"length_mm":getattr(entity,'length_mm',0),"size_mm":getattr(entity,'size_mm',0)})
                recwarn.append('Geen bronrepresentatie; expliciete displayproxy vereist');proxy=True;proxy_count+=1
            geometry_id=f'geometry:{source_hash}'; bounds=self._fallback_bounds(entity)
            metadata=(('source_file_id',sfid),('source_format',fmt),('source_entity_id',se_id),('source_representation_id',rep),('source_item_ids',','.join(items)),
                      ('entity_type',type(entity).__name__),('profile',str(getattr(entity,'profile','') or '')),('material',str(getattr(entity,'material','') or '')),
                      ('part_position',str(getattr(entity,'part_position','') or '')),('assembly_mark',str(getattr(entity,'assembly_mark','') or '')),
                      ('diameter_mm',str(getattr(entity,'diameter_mm',0) or 0)),('length_mm',str(getattr(entity,'length_mm',0) or 0)),('size_mm',str(getattr(entity,'size_mm',0) or 0)),
                      ('fallback_bounds_json',json.dumps({"minimum":bounds.minimum.to_tuple(),"maximum":bounds.maximum.to_tuple()},separators=(',',':'))),
                      ('explicit_proxy','true' if proxy else 'false'))
            rec=EntityGeometryRecord(iid,sfid,se_id,fmt,geometry_id,source_hash,rep,items,solid_index,bounds,tuple(recwarn),metadata)
            records[iid]=rec;unique.setdefault(geometry_id,rec);warnings.extend(f'{iid}: {m}' for m in recwarn)
        self.records_by_entity=records;self.records_by_geometry=unique
        self.report=GeometryCatalogReport(len(records),len(unique),ifc_count,step_count,proxy_count,missing,len(dict(getattr(project,'sources',{}) or {})),tuple(warnings))
        return self
    def record_for_entity(self,internal_id:str)->EntityGeometryRecord|None:return self.records_by_entity.get(str(internal_id))
    def unique_requests(self,resolver:ProjectSourceResolver)->tuple[GeometryRequest,...]:
        return tuple(self.records_by_geometry[g].request(resolver.resolve(self.records_by_geometry[g].source_file_id)) for g in sorted(self.records_by_geometry))

__all__=['ResolvedSource','ProjectSourceResolver','EntityGeometryRecord','GeometryCatalogReport','ProjectGeometryCatalog']
