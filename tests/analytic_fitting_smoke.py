from __future__ import annotations

from pathlib import Path
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq
import numpy as np

from analytic_fitting import (
    fit_circle_2d,
    fit_cylinder_mesh,
    recognize_analytic_shape,
    simplify_collinear,
)


def _tessellate(shape: cq.Shape, tolerance: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    vertices, triangles = shape.tessellate(tolerance, 0.15)
    return (
        np.asarray([vertex.toTuple() for vertex in vertices], dtype=float),
        np.asarray(triangles, dtype=int),
    )


def main() -> int:
    # Cirkel uit gefacetteerde ring, inclusief kleine deterministische meetruis.
    angles = np.linspace(0.0, 2.0 * math.pi, 48, endpoint=False)
    noise = 0.01 * np.sin(angles * 7.0)
    radius = 18.0 + noise
    circle_points = np.column_stack((12.5 + radius * np.cos(angles), -3.0 + radius * np.sin(angles)))
    circle = fit_circle_2d(circle_points, tolerance_mm=0.10)
    assert abs(circle.center_xy[0] - 12.5) < 0.01
    assert abs(circle.center_xy[1] + 3.0) < 0.01
    assert abs(circle.radius_mm - 18.0) < 0.01
    assert circle.confidence > 0.95

    # Veel punten op rechte randen moeten compact naar vier hoekpunten.
    contour = [
        (0.0, 0.0),
        (25.0, 0.0),
        (50.0, 0.0),
        (100.0, 0.0),
        (100.0, 20.0),
        (100.0, 50.0),
        (70.0, 50.0),
        (0.0, 50.0),
        (0.0, 25.0),
        (0.0, 0.0),
    ]
    simplified = simplify_collinear(contour, tolerance_mm=0.001, closed=True)
    assert len(simplified) == 4

    # Ronde staaf onder willekeurige hoek moet als analytische cilinder terugkomen.
    direction = cq.Vector(0.2, 0.7, 0.68).normalized()
    cylinder_shape = cq.Solid.makeCylinder(10.0, 260.0, cq.Vector(15.0, -7.0, 22.0), direction)
    vertices, triangles = _tessellate(cylinder_shape)
    cylinder = fit_cylinder_mesh(vertices, triangles)
    assert abs(cylinder.diameter_mm - 20.0) < 0.01
    assert abs(cylinder.length_mm - 260.0) < 0.01
    assert cylinder.confidence > 0.95
    recognized = recognize_analytic_shape(vertices, triangles, minimum_confidence=0.92)
    assert recognized.kind == "cylinder" and recognized.shape is not None

    # Een blok mag niet als cilinder worden vrijgegeven.
    block = cq.Workplane("XY").box(100.0, 50.0, 10.0).val()
    block_vertices, block_triangles = _tessellate(block)
    rejected = recognize_analytic_shape(block_vertices, block_triangles, minimum_confidence=0.92)
    assert rejected.shape is None

    print(
        json.dumps(
            {
                "circle": {
                    "radius_mm": circle.radius_mm,
                    "rms_residual_mm": circle.rms_residual_mm,
                    "confidence": circle.confidence,
                },
                "collinear_points_before": len(contour) - 1,
                "collinear_points_after": len(simplified),
                "cylinder": {
                    "diameter_mm": cylinder.diameter_mm,
                    "length_mm": cylinder.length_mm,
                    "rms_residual_mm": cylinder.rms_residual_mm,
                    "volume_delta_percent": cylinder.volume_delta_percent,
                    "confidence": cylinder.confidence,
                },
                "box_recognition": rejected.kind,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
