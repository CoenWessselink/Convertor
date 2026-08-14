"""Read-only property/provenance provider for the Viewer and grid."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Iterable,Mapping

@dataclass(frozen=True,slots=True)
class PropertyRecord:
    key:str;label:str;value:Any;group:str='Algemeen';unit:str='';provenance:str='';confidence:float|None=None;status:str='source';editable:bool=False
    def to_dict(self):return {"key":self.key,"label":self.label,"value":self.value,"group":self.group,"unit":self.unit,"provenance":self.provenance,"confidence":self.confidence,"status":self.status,"editable":self.editable}

_LABELS={"internal_id":"Interne ID","name":"Naam","part_position":"Positie","assembly_mark":"Merk","profile":"Profiel","normalized_profile":"Genormaliseerd profiel","material":"Materiaal","normalized_material":"Genormaliseerd materiaal","length_mm":"Lengte","mass_each_kg":"Massa/stuk","surface_area_each_m2":"Oppervlak/stuk","quantity_total":"Aantal totaal","quantity":"Aantal","classification_status":"Classificatie","export_status":"Exportstatus","geometry_hash":"Geometry hash","manufacturing_hash":"Manufacturing hash"}
_UNITS={"length_mm":"mm","diameter_mm":"mm","hole_diameter_mm":"mm","size_mm":"mm","mass_each_kg":"kg","surface_area_each_m2":"m²"}

class ProjectPropertyProvider:
    def __init__(self,project:Any)->None:self.project=project
    def entity(self,entity_id:str)->Any:
        if hasattr(self.project,'get_entity'):
            hit=self.project.get_entity(entity_id)
            if hit is not None:return hit
        for name in ('assemblies','parts','purchased_items','fasteners','welds'):
            hit=(getattr(self.project,name,{}) or {}).get(entity_id)
            if hit is not None:return hit
        raise KeyError(entity_id)
    @staticmethod
    def _flat(value:Any,prefix:str='')->Iterable[tuple[str,Any]]:
        if isinstance(value,Mapping):
            for k,v in value.items():yield from ProjectPropertyProvider._flat(v,f'{prefix}.{k}' if prefix else str(k))
        elif isinstance(value,(list,tuple)):
            if all(not isinstance(v,(dict,list,tuple)) for v in value):yield prefix,', '.join(str(v) for v in value)
            else:
                for i,v in enumerate(value):yield from ProjectPropertyProvider._flat(v,f'{prefix}[{i}]')
        else:yield prefix,value
    def records(self,entity_id:str)->tuple[PropertyRecord,...]:
        e=self.entity(entity_id);data=e.to_dict() if hasattr(e,'to_dict') else dict(vars(e));prov_raw=getattr(e,'field_provenance',{}) or {};prov=dict(prov_raw) if isinstance(prov_raw,Mapping) else {};confidence_raw=getattr(e,'confidence',None);confidence=dict(confidence_raw) if isinstance(confidence_raw,Mapping) else {};overall_confidence=float(confidence_raw) if isinstance(confidence_raw,(int,float)) else None
        result=[]
        primary=('internal_id','name','part_position','assembly_mark','profile','normalized_profile','material','normalized_material','length_mm','diameter_mm','quantity_total','quantity','mass_each_kg','surface_area_each_m2','classification_status','export_status')
        for key in primary:
            if key not in data:continue
            p=prov.get(key);ptext=str(getattr(p,'method','') or getattr(p,'source','') or p or '')
            conf=confidence.get(key,overall_confidence);conf=float(conf) if isinstance(conf,(int,float)) else None
            result.append(PropertyRecord(key,_LABELS.get(key,key.replace('_',' ').title()),data[key],'Algemeen',_UNITS.get(key,''),ptext,conf,'source',False))
        source=data.get('source_identity') or {}
        for key,value in self._flat(source,'source_identity'):result.append(PropertyRecord(key,key.split('.')[-1].replace('_',' ').title(),value,'Herkomst'))
        for key in ('geometry_hash','manufacturing_hash','production_identity_hash'):
            if data.get(key):result.append(PropertyRecord(key,_LABELS.get(key,key.replace('_',' ').title()),data[key],'Validatie'))
        for key,value in sorted((data.get('properties') or {}).items()):result.append(PropertyRecord(f'properties.{key}',str(key),value,'Bronproperties'))
        return tuple(result)

__all__=['PropertyRecord','ProjectPropertyProvider']
