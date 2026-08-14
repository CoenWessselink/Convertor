"""Renderer-independent virtual project grid model."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any,Iterable

@dataclass(frozen=True,slots=True)
class GridColumn:
    key:str;label:str;width:int=120;visible:bool=True;order:int=0
@dataclass(frozen=True,slots=True)
class GridRow:
    entity_id:str;values:tuple[tuple[str,Any],...]
    def get(self,key,default=None):return dict(self.values).get(key,default)

_DEFAULT=(('status','Status'),('assembly_mark','Merk'),('part_position','Positie'),('name','Naam'),('category','Categorie'),('profile','Profiel'),('material','Materiaal'),('length_mm','Lengte'),('quantity_total','Aantal'),('mass_each_kg','Massa/stuk'),('classification_status','Classificatie'),('export_status','Export'),('warnings','Waarschuwingen'))
class ProjectGridModel:
    def __init__(self,project:Any)->None:
        self.project=project;self.columns=tuple(GridColumn(k,l,130,True,i) for i,(k,l) in enumerate(_DEFAULT));self._rows=self._build_rows()
    def _build_rows(self):
        rows=[]
        for e in (getattr(self.project,'parts',{}) or {}).values():
            a=','.join(sorted(getattr(e,'assembly_ids',()) or ()));issues='; '.join(str(getattr(i,'message',i)) for i in (getattr(e,'validation_issues',()) or ()))
            vals=(("status",str(getattr(e,'status',''))),("assembly_mark",str(getattr(getattr(e,'source_identity',None),'assembly_mark','') or a)),("part_position",str(getattr(e,'part_position',''))),("name",str(getattr(e,'name',''))),("category",str(getattr(e,'category',''))),("profile",str(getattr(e,'profile',''))),("material",str(getattr(e,'material',''))),("length_mm",float(getattr(e,'length_mm',0) or 0)),("quantity_total",int(getattr(e,'quantity_total',1) or 1)),("mass_each_kg",float(getattr(e,'mass_each_kg',0) or 0)),("classification_status",str(getattr(e,'classification_status',''))),("export_status",str(getattr(e,'export_status',''))),("warnings",issues))
            rows.append(GridRow(str(e.internal_id),vals))
        return tuple(rows)
    @property
    def rows(self):return self._rows
    def query(self,text:str='',*,filters:dict[str,Any]|None=None,sort_by:str='part_position',descending:bool=False):
        tokens=[t.casefold() for t in text.split() if t];filters=filters or {};rows=[]
        for r in self._rows:
            values=dict(r.values);hay=' '.join(str(v) for v in values.values()).casefold()
            if any(t not in hay for t in tokens):continue
            if any(str(values.get(k,''))!=str(v) for k,v in filters.items()):continue
            rows.append(r)
        def key(r):
            v=r.get(sort_by,'');return (isinstance(v,str),str(v).casefold() if isinstance(v,str) else v,r.entity_id)
        return tuple(sorted(rows,key=key,reverse=descending))
    def groups(self,key:str,rows:Iterable[GridRow]|None=None):
        out={}
        for r in rows or self._rows:out.setdefault(str(r.get(key,'')),[]).append(r)
        return {k:tuple(v) for k,v in sorted(out.items())}
    def save_layout(self,path:str|Path)->Path:
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps([asdict(c) for c in self.columns],indent=2,ensure_ascii=False),encoding='utf-8');return p
    def load_layout(self,path:str|Path)->tuple[GridColumn,...]:
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        known={c.key:c for c in self.columns}; loaded=[]; seen=set()
        for item in data:
            key=str(item.get('key',''))
            if key not in known or key in seen:continue
            base=known[key];loaded.append(GridColumn(key,str(item.get('label',base.label)),max(40,int(item.get('width',base.width))),bool(item.get('visible',base.visible)),int(item.get('order',len(loaded)))));seen.add(key)
        for base in self.columns:
            if base.key not in seen:loaded.append(GridColumn(base.key,base.label,base.width,base.visible,len(loaded)))
        self.columns=tuple(sorted(loaded,key=lambda c:(c.order,c.key)));return self.columns
    def set_columns(self,columns:Iterable[GridColumn])->tuple[GridColumn,...]:
        values=tuple(columns);keys=[c.key for c in values]
        if len(keys)!=len(set(keys)):raise ValueError('Dubbele gridkolom')
        self.columns=tuple(sorted(values,key=lambda c:(c.order,c.key)));return self.columns

__all__=['GridColumn','GridRow','ProjectGridModel']
