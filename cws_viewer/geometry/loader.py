"""Cancelable, cached geometry loading coordinator."""
from __future__ import annotations
from dataclasses import dataclass
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import threading,time
from typing import Iterable,Sequence
from cws_viewer.cache.mesh_cache import MeshCache
from cws_viewer.contracts.geometry import GeometryLoadResult,GeometryLoadStatus,GeometryProvider,GeometryRequest,MeshData,ProgressCallback,TessellationSettings
from cws_viewer.performance import GeometryPriorityScheduler,LoadProfileSession

class GeometryLoadCancelled(RuntimeError):pass
class CancellationToken:
    def __init__(self)->None:self._event=threading.Event()
    def cancel(self)->None:self._event.set()
    @property
    def cancelled(self)->bool:return self._event.is_set()
    def check(self)->None:
        if self.cancelled:raise GeometryLoadCancelled('Geometrieladen geannuleerd')

class MeshRepository:
    def __init__(self)->None:self._meshes={};self._lock=threading.RLock()
    def put(self,geometry_id:str,mesh:MeshData)->None:
        with self._lock:self._meshes[str(geometry_id)]=mesh
    def get(self,geometry_id:str)->MeshData|None:
        with self._lock:return self._meshes.get(str(geometry_id))
    def require(self,geometry_id:str)->MeshData:
        mesh=self.get(geometry_id)
        if mesh is None:raise KeyError(geometry_id)
        return mesh
    def __contains__(self,geometry_id:str)->bool:return self.get(geometry_id) is not None
    def __len__(self)->int:
        with self._lock:return len(self._meshes)
    def ids(self):
        with self._lock:return tuple(sorted(self._meshes))
    @property
    def total_bytes(self)->int:
        with self._lock:return sum(m.byte_length for m in self._meshes.values())

@dataclass(frozen=True,slots=True)
class BatchLoadReport:
    requested_count:int;ready_count:int;partial_count:int;failed_count:int;cancelled_count:int;cache_hit_count:int;proxy_count:int;elapsed_seconds:float;results:tuple[GeometryLoadResult,...]
    def to_dict(self):return {"requested_count":self.requested_count,"ready_count":self.ready_count,"partial_count":self.partial_count,"failed_count":self.failed_count,"cancelled_count":self.cancelled_count,"cache_hit_count":self.cache_hit_count,"proxy_count":self.proxy_count,"elapsed_seconds":self.elapsed_seconds,"results":[r.to_dict() for r in self.results]}

class GeometryLoadCoordinator:
    def __init__(self,providers:Sequence[GeometryProvider],*,proxy_provider:GeometryProvider|None=None,cache:MeshCache|None=None,repository:MeshRepository|None=None,settings:TessellationSettings|None=None,max_workers:int=1,scheduler:GeometryPriorityScheduler|None=None,profiler:LoadProfileSession|None=None)->None:
        self.providers=tuple(providers);self.proxy_provider=proxy_provider;self.cache=cache;self.repository=repository if repository is not None else MeshRepository();self.settings=settings or TessellationSettings();self.max_workers=max(1,int(max_workers));self.scheduler=scheduler or GeometryPriorityScheduler();self.profiler=profiler;self.failed_requests={}
    def _provider(self,request):
        for p in self.providers:
            if p.supports(request):return p
        return None
    def load_one(self,request:GeometryRequest,*,token:CancellationToken|None=None,allow_proxy:bool=True)->GeometryLoadResult:
        start=time.perf_counter();check=token.check if token else None;provider=None;key=None
        try:
            if check:check()
            provider=self._provider(request)
            if provider is None:raise RuntimeError(f'Geen provider voor {request.source_format}')
            key=request.cache_key(self.settings,provider.provider_version);mesh=self.cache.get(key) if self.cache else None;hit=mesh is not None
            if mesh is None:
                mesh=provider.load(request,self.settings,cancel_check=check)
                if self.cache:self.cache.put(key,mesh,provider_version=provider.provider_version,settings=self.settings)
            self.repository.put(request.geometry_id,mesh);status=GeometryLoadStatus.PARTIAL if mesh.exactness!='source_tessellation' else GeometryLoadStatus.READY
            self.failed_requests.pop(request.geometry_id,None)
            return GeometryLoadResult(request,status,mesh,time.perf_counter()-start,hit,mesh.warnings,'')
        except GeometryLoadCancelled as exc:return GeometryLoadResult(request,GeometryLoadStatus.CANCELLED,None,time.perf_counter()-start,False,(),str(exc))
        except Exception as exc:
            self.failed_requests[request.geometry_id]=request
            if allow_proxy and self.proxy_provider is not None:
                try:
                    mesh=self.proxy_provider.load(request,self.settings,cancel_check=check);self.repository.put(request.geometry_id,mesh)
                    # Never store a fallback proxy under the primary provider key.
                    # Doing so makes a transient worker/startup failure permanently
                    # shadow valid IFC/STEP source geometry on every later run.
                    return GeometryLoadResult(request,GeometryLoadStatus.PARTIAL,mesh,time.perf_counter()-start,False,mesh.warnings,str(exc))
                except Exception as proxy_exc:exc=RuntimeError(f'{exc}; proxy faalde: {proxy_exc}')
            return GeometryLoadResult(request,GeometryLoadStatus.FAILED,None,time.perf_counter()-start,False,(),str(exc))
    def load_many(self,requests:Iterable[GeometryRequest],*,token:CancellationToken|None=None,progress:ProgressCallback|None=None,allow_proxy:bool=True)->BatchLoadReport:
        values=tuple(requests);start=time.perf_counter();results=[]
        if self.max_workers==1:
            for i,r in enumerate(self.scheduler.order(values)):
                result=self.load_one(r,token=token,allow_proxy=allow_proxy);results.append(result)
                if progress:progress((i+1)/max(len(values),1),f'{i+1}/{len(values)} {r.geometry_id}')
                if result.status==GeometryLoadStatus.CANCELLED:break
        else:
            # CadQuery/OCP providers can serialize internally; threads primarily keep source/cache IO responsive.
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                pending=list(values);active={};completed_count=0
                while pending or active:
                    while pending and len(active)<self.max_workers:
                        r=min(pending,key=self.scheduler.key);pending.remove(r)
                        active[pool.submit(self.load_one,r,token=token,allow_proxy=allow_proxy)]=r
                    completed,_=wait(tuple(active),return_when=FIRST_COMPLETED)
                    for future in completed:
                        active.pop(future,None);results.append(future.result());completed_count+=1
                        if progress:progress(completed_count/max(len(values),1),f'{completed_count}/{len(values)} geometry resources')
        results=tuple(sorted(results,key=lambda x:x.request.geometry_id));status=[r.status for r in results]
        if self.profiler is not None:
            for index,result in enumerate(results,1):
                mesh=result.mesh
                self.profiler.record_resource(geometry_id=result.request.geometry_id,source_entity=result.request.source_entity_id,cache_hit=bool(result.cache_hit),provider='' if mesh is None else mesh.provider,duration_seconds=float(result.elapsed_seconds),triangle_count=0 if mesh is None else mesh.triangle_count,vertex_count=0 if mesh is None else mesh.vertex_count,mesh_bytes=0 if mesh is None else mesh.byte_length,result=result.status.value,exactness='' if mesh is None else mesh.exactness,error=result.error)
                ratio=index/max(len(results),1)
                if index==1 and mesh is not None:self.profiler.mark('first_geometry')
                for threshold,label in ((0.25,'geometry_25'),(0.50,'geometry_50'),(0.75,'geometry_75'),(1.0,'geometry_100')):
                    if ratio>=threshold:self.profiler.mark(label)
        return BatchLoadReport(len(values),status.count(GeometryLoadStatus.READY),status.count(GeometryLoadStatus.PARTIAL),status.count(GeometryLoadStatus.FAILED),status.count(GeometryLoadStatus.CANCELLED),sum(r.cache_hit for r in results),sum(bool(r.mesh and r.mesh.exactness=='display_proxy') for r in results),time.perf_counter()-start,results)
    def retry_failed(self,*,token=None,progress=None,allow_proxy=True):
        requests=tuple(self.failed_requests.values())
        if self.cache is not None:
            for request in requests:
                provider=self._provider(request)
                if provider is not None:self.cache.invalidate(request.cache_key(self.settings,provider.provider_version))
        return self.load_many(requests,token=token,progress=progress,allow_proxy=allow_proxy)
    def close(self)->None:
        for provider in (*self.providers,self.proxy_provider):
            if bool(getattr(provider,'persistent_session_provider',False)):
                continue
            close=getattr(provider,'close',None) if provider is not None else None
            if callable(close):
                try:close()
                except Exception:pass
    def __enter__(self):return self
    def __exit__(self,*_):self.close()

__all__=['CancellationToken','GeometryLoadCancelled','MeshRepository','BatchLoadReport','GeometryLoadCoordinator']
