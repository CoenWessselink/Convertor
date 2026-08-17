"""End-to-end real CWS project → display scene loading service."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Callable, Iterable, Sequence

from cws_convertor.project.storage import ProjectStore
from cws_viewer.adapters.project_model import SceneBuildOptions,SceneBuildReport
from cws_viewer.adapters.source_style_scene import SourceAppearanceProjectSceneAdapter
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
        """Open a project package and construct its viewer scene.

        V9 also exposes :meth:`load_project`, which accepts the already-opened
        canonical project instance used by the host application.  Keeping this
        convenience method preserves the standalone viewer API while the main
        CWS Convertor integration can prove that tree, grid, BOM and renderer
        all reference one and the same in-memory project model.
        """
        start=time.perf_counter();path=Path(project_path).expanduser().resolve()
        t=time.perf_counter();package=ProjectStore().open(path,read_only=True);project=package.project
        open_elapsed=time.perf_counter()-t
        result=self.load_project(project,path,geometry_ids=geometry_ids,load_all=load_all,allow_proxy=allow_proxy,token=token,progress=progress)
        timings=(('open_project',open_elapsed),)+tuple(result.timings)
        return ProjectSceneLoadResult(path,result.project,result.scene,result.repository,result.catalog,result.catalog_report,result.geometry_report,result.scene_report,time.perf_counter()-start,timings)

    def load_project(self,project:object,project_path:str|Path,*,geometry_ids:Iterable[str]|None=None,load_all:bool=True,
                     allow_proxy:bool=True,token:CancellationToken|None=None,
                     progress:ProgressCallback|None=None)->ProjectSceneLoadResult:
        """Build a scene from an already-opened Canonical Project Model.

        The object is never cloned or re-opened.  This is the V9 integration
        boundary that prevents a second project truth from being introduced by
        the viewer.  Source files are still verified through the project package
        path and SHA-256 identities before geometry is accepted.
        """
        start=time.perf_counter();timings=[];path=Path(project_path).expanduser().resolve()
        if token:token.check()
        t=time.perf_counter();resolver=ProjectSourceResolver(project,project_package_path=path,search_roots=self.source_search_roots);catalog=ProjectGeometryCatalog().build(project,resolver);timings.append(('build_catalog',time.perf_counter()-t))
        assert catalog.report is not None
        requests=catalog.unique_requests(resolver)
        if geometry_ids is not None:
            allowed=set(str(x) for x in geometry_ids);requests=tuple(r for r in requests if r.geometry_id in allowed)
        elif not load_all:requests=()

        # Phase 1 warm-start optimisation.  Keep enough cache entries resident
        # for the current project and checksum-verify/decompress independent
        # entries in parallel.  Native IFC/STEP tessellation itself remains in
        # the proven serial crash-isolated path below.
        cache=MeshCache(self.cache_root,max_memory_items=max(128,min(len(requests),2048)))
        repository=MeshRepository()
        providers=tuple(self.provider_factory()) if self.provider_factory is not None else (IsolatedIfcMeshProvider(),StepMeshProvider())
        t=time.perf_counter();prefetch_keys=[]
        for request in requests:
            provider=next((candidate for candidate in providers if candidate.supports(request)),None)
            if provider is not None:
                prefetch_keys.append(request.cache_key(self.settings,provider.provider_version))
        prefetch_hits=cache.prefetch(
            prefetch_keys,
            max_workers=max(1,min(4,int(os.cpu_count() or 1))),
        ) if prefetch_keys else 0
        timings.append(('prefetch_geometry_cache',time.perf_counter()-t))
        if progress and requests:
            progress(0.0,f'Cache voorbereid · {prefetch_hits}/{len(requests)} geometrieën')

        coordinator=GeometryLoadCoordinator(providers,proxy_provider=ProxyMeshProvider(),cache=cache,repository=repository,settings=self.settings,max_workers=1)
        t=time.perf_counter()
        try:geometry_report=coordinator.load_many(requests,token=token,progress=progress,allow_proxy=allow_proxy)
        finally:coordinator.close()
        timings.append(('load_geometry',time.perf_counter()-t))
        if token:token.check()
        t=time.perf_counter();adapter=SourceAppearanceProjectSceneAdapter();scene=adapter.build_scene(project,SceneBuildOptions(),geometry_catalog=catalog,mesh_repository=repository);timings.append(('build_scene',time.perf_counter()-t))
        assert adapter.last_report is not None
        return ProjectSceneLoadResult(path,project,scene,repository,catalog,catalog.report,geometry_report,adapter.last_report,time.perf_counter()-start,tuple(timings))

__all__=['ProjectSceneLoadResult','ProjectSceneLoader']
