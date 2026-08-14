"""Content-addressed, checksum-verified display mesh cache."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
import hashlib, json, os, tempfile, threading
from pathlib import Path
import numpy as np
from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings

_CACHE_FORMAT = "cws-viewer-mesh-cache-v1"

@dataclass(slots=True)
class MeshCacheStats:
    memory_hits: int = 0
    disk_hits: int = 0
    misses: int = 0
    writes: int = 0
    corrupt_entries: int = 0
    evictions: int = 0
    def to_dict(self) -> dict[str,int]: return {k:int(getattr(self,k)) for k in self.__dataclass_fields__}

class MeshCache:
    def __init__(self, root: str|Path, *, max_memory_items: int=128) -> None:
        self.root=Path(root).expanduser().resolve(); self.root.mkdir(parents=True,exist_ok=True)
        self.max_memory_items=max(0,int(max_memory_items)); self._memory: OrderedDict[str,MeshData]=OrderedDict()
        self._lock=threading.RLock(); self.stats=MeshCacheStats()
    @staticmethod
    def key_for(request: GeometryRequest, settings: TessellationSettings, provider_version: str)->str:
        return request.cache_key(settings,provider_version)
    def _path_for(self,key:str)->Path:
        if len(key)!=64 or any(c not in '0123456789abcdef' for c in key.lower()): raise ValueError('Meshcache-key is geen SHA-256')
        return self.root/key[:2]/f'{key.lower()}.npz'
    @staticmethod
    def _sha(path:Path)->str:
        d=hashlib.sha256()
        with path.open('rb') as h:
            for block in iter(lambda:h.read(1024*1024),b''): d.update(block)
        return d.hexdigest()
    def _remember(self,key:str,mesh:MeshData)->None:
        if self.max_memory_items<=0:return
        self._memory[key]=mesh; self._memory.move_to_end(key)
        while len(self._memory)>self.max_memory_items:
            self._memory.popitem(last=False); self.stats.evictions+=1
    def get(self,key:str)->MeshData|None:
        with self._lock:
            mesh=self._memory.get(key)
            if mesh is not None:
                self._memory.move_to_end(key); self.stats.memory_hits+=1; return mesh
            path=self._path_for(key); checksum=path.with_suffix('.sha256')
            if not path.is_file() or not checksum.is_file(): self.stats.misses+=1; return None
            try:
                if checksum.read_text(encoding='ascii').strip().lower()!=self._sha(path): raise ValueError('cache checksum')
                with np.load(path,allow_pickle=False) as ar:
                    vertices=np.array(ar['vertices'],dtype=np.float64,copy=True); triangles=np.array(ar['triangles'],dtype=np.int32,copy=True)
                    meta=json.loads(bytes(np.asarray(ar['metadata_json'],dtype=np.uint8)).decode('utf-8'))
                if meta.get('format')!=_CACHE_FORMAT or meta.get('cache_key')!=key: raise ValueError('cache metadata')
                mesh=MeshData(vertices,triangles,str(meta['source_geometry_hash']),str(meta.get('provider','cache')),
                              str(meta.get('exactness','source_tessellation')),tuple(meta.get('warnings',())),
                              dict(meta.get('mesh_metadata',{})),str(meta['mesh_hash']))
                self._remember(key,mesh); self.stats.disk_hits+=1; return mesh
            except Exception:
                self.stats.corrupt_entries+=1; path.unlink(missing_ok=True); checksum.unlink(missing_ok=True); self.stats.misses+=1; return None
    def put(self,key:str,mesh:MeshData,*,provider_version:str,settings:TessellationSettings)->Path:
        with self._lock:
            path=self._path_for(key); path.parent.mkdir(parents=True,exist_ok=True)
            meta={"format":_CACHE_FORMAT,"cache_key":key,"provider":mesh.provider,"provider_version":provider_version,
                  "settings":settings.to_dict(),"source_geometry_hash":mesh.source_geometry_hash,"mesh_hash":mesh.mesh_hash,
                  "exactness":mesh.exactness,"warnings":list(mesh.warnings),"mesh_metadata":dict(mesh.metadata),
                  "vertex_count":mesh.vertex_count,"triangle_count":mesh.triangle_count}
            raw=json.dumps(meta,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
            fd,name=tempfile.mkstemp(prefix=f'.{key}.',suffix='.tmp',dir=path.parent); os.close(fd); tmp=Path(name)
            try:
                with tmp.open('wb') as h:
                    np.savez_compressed(h,vertices=mesh.vertices,triangles=mesh.triangles,metadata_json=np.frombuffer(raw,dtype=np.uint8)); h.flush(); os.fsync(h.fileno())
                digest=self._sha(tmp); os.replace(tmp,path)
                ctmp=path.with_suffix('.sha256.tmp'); ctmp.write_text(digest+'\n',encoding='ascii'); os.replace(ctmp,path.with_suffix('.sha256'))
                self._remember(key,mesh); self.stats.writes+=1; return path
            finally: tmp.unlink(missing_ok=True)
    def invalidate(self,key:str)->None:
        with self._lock:
            self._memory.pop(key,None); p=self._path_for(key); p.unlink(missing_ok=True); p.with_suffix('.sha256').unlink(missing_ok=True)
    def clear_memory(self)->None:
        with self._lock:self._memory.clear()

__all__=['MeshCache','MeshCacheStats']
