"""Explicit, visibly marked fallback display proxies."""
from __future__ import annotations
import json, math
import numpy as np
from cws_viewer.contracts.geometry import CancelCheck, GeometryRequest, MeshData, TessellationSettings

PROVIDER_VERSION='cws-explicit-display-proxy-v2'

def _box(x,y,z,origin=(0.,0.,0.)):
    x=max(float(x),1.0);y=max(float(y),1.0);z=max(float(z),1.0)
    ox,oy,oz=(float(value) for value in origin)
    v=np.asarray([[ox,oy,oz],[ox+x,oy,oz],[ox+x,oy+y,oz],[ox,oy+y,oz],[ox,oy,oz+z],[ox+x,oy,oz+z],[ox+x,oy+y,oz+z],[ox,oy+y,oz+z]],dtype=np.float64)
    t=np.asarray([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]],dtype=np.int32)
    return v,t

def _cylinder(radius,length,sides):
    r=max(float(radius),.5);l=max(float(length),1.);n=max(int(sides),8);verts=[]
    for z in (0.,l):verts.extend((r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for i in range(n))
    verts.extend([(0,0,0),(0,0,l)]);b=2*n;top=b+1;tris=[]
    for i in range(n):
        j=(i+1)%n;tris.extend([(i,j,n+j),(i,n+j,n+i),(b,j,i),(top,n+i,n+j)])
    return np.asarray(verts,np.float64),np.asarray(tris,np.int32)

class ProxyMeshProvider:
    @property
    def provider_version(self):return PROVIDER_VERSION
    def supports(self,request):return True
    def load(self,request,settings,*,cancel_check:CancelCheck|None=None):
        if cancel_check:cancel_check()
        m=request.metadata_dict;diam=float(m.get('diameter_mm') or 0);length=float(m.get('length_mm') or 0);bounds=None
        try:bounds=json.loads(m.get('fallback_bounds_json',''))
        except Exception:bounds=None
        if diam>0:
            v,t=_cylinder(diam/2,max(length,diam),settings.circle_segments)
        else:
            size=[0.,0.,0.];origin=[0.,0.,0.]
            if isinstance(bounds,dict):
                lo=bounds.get('minimum',[0,0,0]);hi=bounds.get('maximum',[0,0,0]);origin=[float(lo[i]) for i in range(3)];size=[max(0,float(hi[i])-origin[i]) for i in range(3)]
            if max(size)<=0:
                s=max(float(m.get('size_mm') or 0),10.);size=[max(length,s),s,s];origin=[0.,0.,0.]
            v,t=_box(*size,origin=origin)
        return MeshData(v,t,request.source_geometry_hash,f'ProxyMeshProvider/{PROVIDER_VERSION}','display_proxy',
                        ('Brongeometrie niet ondersteund; zichtbaar begrensde displayproxy gebruikt',),{"source_format":request.source_format,"explicit_proxy":True})

__all__=['ProxyMeshProvider','PROVIDER_VERSION']
