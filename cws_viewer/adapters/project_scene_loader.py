"""End-to-end real CWS project → display scene loading service."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Callable, Iterable, Sequence

from cws_convertor.project.storage import ProjectStore
from cws_viewer.adapters.project_model import CwsProjectSceneAdapter,SceneBuildOptions,SceneBuildReport
from cws_viewer.adapters.source_geometry import ProjectSourceResolver,ProjectGeometryCatalog,GeometryCatalogReport
from cws_viewer.cache import MeshCache
from cws_viewer.contracts.geometry import GeometryProvider,GeometryRequest,ProgressCallback,TessellationSettings
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.geometry import CancellationToken,GeometryLoadCoordinator,MeshRepository,IsolatedIfcMeshProvider,StepMeshProvider,ProxyMeshProvider,BatchLoadReport

@dataclass(frozen=True,slots=True)
class ProjectSceneLoadResult:
    project_path:Path
    project:object
    scene:ProjectScene
    repository:MeshRepository
    catalog:ProjectGeometryCatalog
    catalog_report:GeometryCatalogReport
    geometry_report:BatchLoadReport
    scene_report:SceneBuildReport
    elapsed_seconds:float
    timings:tuple[tuple[str,float],...]
    def to_dict(self):
        return {"project_path":str(self.project_path),"scene_hash":self.scene.scene_hash,"elapsed_seconds":self.elapsed_seconds,
                "timings":dict(self.timings),"catalog":self.catalog_report.to_dict(),"geometry":self.geometry_report.to_dict(),"scene":self.scene_report.to_dict(),
                "repository":{"mesh_count":len(self.repository),"bytes":self.repository.total_bytes}}

class ProjectSceneLoader:
    def __init__(self,*,cache_root:str|Path|None=None,source_search_roots:Iterable[str|Path]=(),settings:TessellationSettings|None=None,
                 provider_factory:Callable[[],Sequence[GeometryProvider]]|None=None)->None:
        self.cache_root=Path(cache_root or Path.home()/'.cws_convertor'/'viewer_mesh_cache').expanduser().resolve()
        self.source_search_roots=tuple(source_search_roots);self.settings=settings or TessellationSettings();self.provider_factory=provider_factory
    def load(self,project_path:str|Path,*,geometry_ids:Iterable[str]|None=None,load_all:bool=True,allow_proxy:bool=True,
             token:CancellationToken|None=None,progress:ProgressCallback|None=None)->ProjectSceneLoadResult:
        start=time.perf_counter();timings=[];path=Path(project_path).expanduser().resolve()
        t=time.perf_counter();package=ProjectStore().open(path,read_only=True);project=package.project;timings.append(('open_project',time.perf_counter()-t))
        if token:token.check()
        t=time.perf_counter();resolver=ProjectSourceResolver(project,project_package_path=path,search_roots=self.source_search_roots);catalog=ProjectGeometryCatalog().build(project,resolver);timings.append(('build_catalog',time.perf_counter()-t))
        assert catalog.report is not None
        requests=catalog.unique_requests(resolver)
        if geometry_ids is not None:
            allowed=set(str(x) for x in geometry_ids);requests=tuple(r for r in requests if r.geometry_id in allowed)
        elif not load_all:requests=()
        cache=MeshCache(self.cache_root);repository=MeshRepository();providers=tuple(self.provider_factory()) if self.provider_factory is not None else (IsolatedIfcMeshProvider(),StepMeshProvider());coordinator=GeometryLoadCoordinator(providers,proxy_provider=ProxyMeshProvider(),cache=cache,repository=repository,settings=self.settings,max_workers=1)
        t=time.perf_counter()
        try:geometry_report=coordinator.load_many(requests,token=token,progress=progress,allow_proxy=allow_proxy)
        finally:coordinator.close()
        timings.append(('load_geometry',time.perf_counter()-t))
        if token:token.check()
        t=time.perf_counter();adapter=CwsProjectSceneAdapter();scene=adapter.build_scene(project,SceneBuildOptions(),geometry_catalog=catalog,mesh_repository=repository);timings.append(('build_scene',time.perf_counter()-t))
        assert adapter.last_report is not None
        return ProjectSceneLoadResult(path,project,scene,repository,catalog,catalog.report,geometry_report,adapter.last_report,time.perf_counter()-start,tuple(timings))

__all__=['ProjectSceneLoadResult','ProjectSceneLoader']
