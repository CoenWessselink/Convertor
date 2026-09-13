"""Geometry-only quality heuristics for adaptive close-up refinement.

The detector intentionally ignores hard structural corners. It looks for
adjacent triangle pairs whose dihedral angle is small enough to represent a
smooth curve, but still large enough to be visible as a polygonal silhouette.
This makes CHS/tubes, holes, bolts and rolled profile radii refine while planar
plates and 90-degree structural edges remain untouched.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
from cws_viewer.contracts.geometry import MeshData

@dataclass(frozen=True, slots=True)
class SilhouetteQualityReport:
    needs_refinement: bool
    max_smooth_dihedral_deg: float
    smooth_edge_count: int
    triangle_count: int
    reason: str


def inspect_silhouette_quality(
    mesh: MeshData,
    *,
    hard_edge_deg: float = 32.0,
    target_smooth_step_deg: float = 3.0,
    max_triangles_to_scan: int = 250_000,
) -> SilhouetteQualityReport:
    triangles=np.asarray(mesh.triangles,dtype=np.int64)
    vertices=np.asarray(mesh.vertices,dtype=np.float64)
    if len(triangles)==0 or len(vertices)==0:
        return SilhouetteQualityReport(False,0.0,0,0,"empty")
    if len(triangles)>max_triangles_to_scan:
        stride=max(1,len(triangles)//max_triangles_to_scan)
        triangles=triangles[::stride]
    a=vertices[triangles[:,0]]; b=vertices[triangles[:,1]]; c=vertices[triangles[:,2]]
    normals=np.cross(b-a,c-a)
    lengths=np.linalg.norm(normals,axis=1)
    valid=lengths>1e-12
    normals[valid]/=lengths[valid,None]
    edges={}
    for face_index,tri in enumerate(triangles):
        if not valid[face_index]:
            continue
        for u,v in ((int(tri[0]),int(tri[1])),(int(tri[1]),int(tri[2])),(int(tri[2]),int(tri[0]))):
            key=(u,v) if u<v else (v,u)
            previous=edges.get(key)
            if previous is None:
                edges[key]=face_index
                continue
            if not isinstance(previous, int):
                continue
            dot=float(np.clip(np.dot(normals[previous],normals[face_index]),-1.0,1.0))
            angle=math.degrees(math.acos(dot))
            edges[key]=(previous,face_index,angle)
    smooth=[]
    for value in edges.values():
        if isinstance(value,tuple) and len(value)==3:
            angle=float(value[2])
            if 1e-4<angle<float(hard_edge_deg):
                smooth.append(angle)
    maximum=max(smooth,default=0.0)
    needs=bool(smooth and maximum>float(target_smooth_step_deg))
    reason=(
        f"smooth-facet-step {maximum:.2f}° > {target_smooth_step_deg:.2f}°"
        if needs else "within-closeup-silhouette-target"
    )
    return SilhouetteQualityReport(needs,maximum,len(smooth),int(len(mesh.triangles)),reason)

__all__=["SilhouetteQualityReport","inspect_silhouette_quality"]
