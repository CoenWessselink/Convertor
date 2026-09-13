from __future__ import annotations
import numpy as np
import pytest
from cws_viewer.contracts.geometry import MeshData, TessellationSettings
from cws_viewer.contracts.state import CameraState
from cws_viewer.contracts.enums import ProjectionType
from cws_viewer.geometry.silhouette_quality import inspect_silhouette_quality
from cws_viewer.math3d import BoundingBox, Vector3
from cws_viewer.performance.adaptive_detail import projected_extent_pixels

cq = pytest.importorskip("cadquery")

def _mesh(factory, settings: TessellationSettings) -> MeshData:
    shape=factory()
    vertices,triangles=shape.tessellate(settings.linear_deflection_mm,settings.angular_deflection_rad)
    return MeshData(
        np.asarray([[p.x,p.y,p.z] for p in vertices],dtype=np.float64),
        np.asarray(triangles,dtype=np.int32),
        "0"*64,"adaptive-test","source_tessellation",
    )

def test_closeup_profile_is_strict_and_cache_distinct():
    base=TessellationSettings(); close=TessellationSettings.close_up()
    assert close.linear_deflection_mm < base.linear_deflection_mm
    assert close.angular_deflection_rad < base.angular_deflection_rad
    assert close.circle_segments >= 128
    assert close.version == "cws-tessellation-v5-adaptive-closeup"
    assert close.fingerprint != base.fingerprint

def test_polygonal_curve_refines_while_planar_box_does_not():
    base=TessellationSettings(); close=TessellationSettings.close_up()
    coarse=_mesh(lambda:cq.Solid.makeCylinder(50,100),base)
    refined=_mesh(lambda:cq.Solid.makeCylinder(50,100),close)
    planar=_mesh(lambda:cq.Solid.makeBox(100,80,60),base)
    coarse_quality=inspect_silhouette_quality(coarse)
    refined_quality=inspect_silhouette_quality(refined)
    planar_quality=inspect_silhouette_quality(planar)
    assert coarse_quality.needs_refinement
    assert refined.triangle_count >= coarse.triangle_count*2
    assert not refined_quality.needs_refinement
    assert not planar_quality.needs_refinement
    assert planar.triangle_count == 12

def test_closeup_is_screen_space_bounded():
    bounds=BoundingBox(Vector3(-50,-50,-50),Vector3(50,50,50))
    near=CameraState(position=Vector3(0,-250,0),target=Vector3.zero(),up=Vector3(0,0,1))
    far=CameraState(position=Vector3(0,-5000,0),target=Vector3.zero(),up=Vector3(0,0,1))
    assert projected_extent_pixels(bounds,near,1000) > 90
    assert projected_extent_pixels(bounds,far,1000) < 90
    ortho=CameraState(position=Vector3(0,-1000,0),target=Vector3.zero(),up=Vector3(0,0,1),projection=ProjectionType.ORTHOGRAPHIC,ortho_scale=500)
    assert projected_extent_pixels(bounds,ortho,1000) == pytest.approx(200.0)
