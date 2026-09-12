from types import SimpleNamespace

import vtk

from cws_viewer.backends.vtk_project_mesh_v14 import VtkProjectMeshV14Backend
from cws_viewer.math3d import BoundingBox, Vector3


def _backend_and_index(count: int = 120):
    render_window = vtk.vtkRenderWindow()
    render_window.SetSize(1280, 720)
    renderer = vtk.vtkRenderer()
    renderer.SetViewport(0.05, 0.1, 0.95, 0.9)
    render_window.AddRenderer(renderer)
    camera = renderer.GetActiveCamera()
    camera.SetPosition(1200.0, -1800.0, 1400.0)
    camera.SetFocalPoint(0.0, 0.0, 0.0)
    camera.SetViewUp(0.0, 0.0, 1.0)
    camera.SetViewAngle(35.0)
    camera.SetClippingRange(1.0, 10000.0)

    ids = tuple(f"n{i}" for i in range(count))
    bounds = {}
    for i, node_id in enumerate(ids):
        x = float((i % 20) * 35 - 330)
        y = float((i // 20) * 45 - 120)
        z = float((i % 7) * 18 - 40)
        bounds[node_id] = BoundingBox(Vector3(x, y, z), Vector3(x + 22, y + 30, z + 16))
    index = SimpleNamespace(renderable_node_ids=ids, world_bounds_by_node=bounds)
    offsets = {ids[3]: Vector3(15.0, -9.0, 7.0), ids[87]: Vector3(-20.0, 3.0, 11.0)}
    state = SimpleNamespace(visible_set=frozenset(ids), explode_offsets=offsets)
    backend = object.__new__(VtkProjectMeshV14Backend)
    backend._renderer = renderer
    backend._render_window = render_window
    backend._state = state
    return backend, index


def _legacy_rect(backend, bounds, offset):
    values = []
    for corner in bounds.corners():
        p = corner + offset
        backend._renderer.SetWorldPoint(p.x, p.y, p.z, 1.0)
        backend._renderer.WorldToDisplay()
        x, y, _ = backend._renderer.GetDisplayPoint()
        values.append((int(round(x)), int(round(y))))
    return min(x for x, _ in values), min(y for _, y in values), max(x for x, _ in values), max(y for _, y in values)


def test_bulk_projection_matches_legacy_world_to_display_pixels():
    backend, index = _backend_and_index()
    projected = {node_id: (x0, y0, x1, y1) for node_id, x0, y0, x1, y1 in backend._visible_screen_bounds(index)}
    for node_id in index.renderable_node_ids:
        expected = _legacy_rect(backend, index.world_bounds_by_node[node_id], backend._state.explode_offsets.get(node_id, Vector3.zero()))
        assert projected[node_id] == expected


def test_lasso_broad_phase_preserves_exact_rect_intersection():
    polygon = ((100.0, 100.0), (500.0, 120.0), (480.0, 500.0), (120.0, 480.0))
    candidates = [
        (-50.0, -50.0, 50.0, 50.0),
        (150.0, 150.0, 160.0, 160.0),
        (490.0, 300.0, 510.0, 320.0),
        (600.0, 600.0, 700.0, 700.0),
    ]
    px0 = min(p[0] for p in polygon); py0 = min(p[1] for p in polygon)
    px1 = max(p[0] for p in polygon); py1 = max(p[1] for p in polygon)
    exact = [VtkProjectMeshV14Backend._polygon_intersects_rect(polygon, rect) for rect in candidates]
    accelerated = []
    for bx0, by0, bx1, by1 in candidates:
        if bx1 < px0 or bx0 > px1 or by1 < py0 or by0 > py1:
            accelerated.append(False)
        else:
            accelerated.append(VtkProjectMeshV14Backend._polygon_intersects_rect(polygon, (bx0, by0, bx1, by1)))
    assert accelerated == exact
