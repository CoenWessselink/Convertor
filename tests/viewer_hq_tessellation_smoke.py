from __future__ import annotations

import cadquery as cq

from cws_viewer.contracts.geometry import GeometryRequest, TessellationSettings


def _triangle_count(shape_factory, settings: TessellationSettings) -> int:
    shape = shape_factory()
    _vertices, triangles = shape.tessellate(
        settings.linear_deflection_mm,
        settings.angular_deflection_rad,
    )
    return len(triangles)


def test_hq_balanced_profile_is_default_and_versioned() -> None:
    settings = TessellationSettings()
    assert settings.linear_deflection_mm == 0.35
    assert settings.angular_deflection_rad == 0.18
    assert settings.circle_segments == 48
    assert settings.version == "cws-tessellation-v3-hq-balanced"


def test_hq_curves_gain_detail_without_planar_triangle_bloat() -> None:
    old = TessellationSettings(
        linear_deflection_mm=1.0,
        angular_deflection_rad=0.35,
        circle_segments=24,
        version="cws-tessellation-v2",
    )
    hq = TessellationSettings()

    old_curve = _triangle_count(
        lambda: cq.Workplane("XY").circle(50.0).extrude(100.0).val(), old
    )
    hq_curve = _triangle_count(
        lambda: cq.Workplane("XY").circle(50.0).extrude(100.0).val(), hq
    )
    old_box = _triangle_count(
        lambda: cq.Workplane("XY").box(100.0, 100.0, 100.0).val(), old
    )
    hq_box = _triangle_count(
        lambda: cq.Workplane("XY").box(100.0, 100.0, 100.0).val(), hq
    )

    assert hq_curve >= int(old_curve * 1.75)
    assert hq_box == old_box


def test_quality_profile_changes_cache_key_without_changing_geometry_identity() -> None:
    source_hash = "1" * 64
    request = GeometryRequest(
        geometry_id=f"geometry:{source_hash}",
        source_geometry_hash=source_hash,
        source_format="STEP",
        source_file_id="source:step",
        source_path="unused.step",
        source_sha256="2" * 64,
        source_entity_id="1",
        source_path_verified=True,
    )
    old = TessellationSettings(
        linear_deflection_mm=1.0,
        angular_deflection_rad=0.35,
        circle_segments=24,
        version="cws-tessellation-v2",
    )
    hq = TessellationSettings()

    assert request.geometry_id == f"geometry:{source_hash}"
    assert request.source_geometry_hash == source_hash
    assert request.cache_key(old, "provider-v1") != request.cache_key(hq, "provider-v1")
    assert request.cache_key(hq, "provider-v1") == request.cache_key(hq, "provider-v1")
