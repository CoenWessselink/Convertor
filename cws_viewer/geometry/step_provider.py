"""STEP BREP display-mesh provider backed by CadQuery/OpenCascade."""
from __future__ import annotations
import threading
from pathlib import Path
import cadquery as cq
import numpy as np
from cws_viewer.contracts.geometry import CancelCheck, GeometryRequest, MeshData, TessellationSettings

PROVIDER_VERSION='cws-step-display-v1'
class UnsupportedStepGeometry(RuntimeError):pass

class StepMeshProvider:
    def __init__(self)->None:self._cache={};self._lock=threading.RLock()
    @property
    def provider_version(self):return PROVIDER_VERSION
    def supports(self,request):return request.source_format.upper() in {'STEP','STP'}
    def _solids(self,request):
        key=request.source_sha256
        with self._lock:
            if key not in self._cache:
                imported=cq.importers.importStep(str(Path(request.source_path)))
                vals=list(imported.vals())
                solids=[]
                for value in vals:
                    if isinstance(value,cq.Shape):
                        ss=value.Solids()
                        solids.extend(ss or [value])
                if not solids:
                    value=imported.val()
                    if value is not None:solids=list(value.Solids()) or [value]
                if not solids:raise UnsupportedStepGeometry('STEP bevat geen leesbare BREP-solid')
                self._cache[key]=tuple(solids)
            return self._cache[key]
    def load(self,request,settings,*,cancel_check:CancelCheck|None=None):
        if not self.supports(request):raise UnsupportedStepGeometry('StepMeshProvider ondersteunt alleen STEP')
        if cancel_check:cancel_check()
        solids=self._solids(request);idx=request.solid_index
        if idx>=len(solids):
            if len(solids)==1:idx=0
            else:raise UnsupportedStepGeometry(f'STEP solid-index {idx} buiten bereik ({len(solids)})')
        shape=solids[idx];verts,tris=shape.tessellate(settings.linear_deflection_mm,settings.angular_deflection_rad)
        if cancel_check:cancel_check()
        if not verts or not tris:raise UnsupportedStepGeometry('STEP-tessellatie leverde geen driehoeken')
        vertices=np.asarray([(float(v.x),float(v.y),float(v.z)) for v in verts],dtype=np.float64);triangles=np.asarray(tris,dtype=np.int32)
        return MeshData(vertices,triangles,request.source_geometry_hash,f'StepMeshProvider/{PROVIDER_VERSION}','source_tessellation',(),
                        {"source_format":"STEP","source_file_id":request.source_file_id,"source_entity_id":request.source_entity_id,"solid_index":idx,"solid_count":len(solids)})

__all__=['StepMeshProvider','UnsupportedStepGeometry','PROVIDER_VERSION']
