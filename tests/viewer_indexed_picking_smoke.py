from types import SimpleNamespace

from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend, _PickLocatorEntry
from cws_viewer.math3d import Vector3


class _Ids:
    def __init__(self):
        self.values = []

    def InsertNextId(self, value):
        self.values.append(int(value))

    def GetNumberOfIds(self):
        return len(self.values)

    def GetId(self, index):
        return self.values[index]


class _Vtk:
    vtkIdList = _Ids


class _Locator:
    def __init__(self, radius_values=(), closest_values=()):
        self.radius_values = tuple(radius_values)
        self.closest_values = tuple(closest_values)
        self.radius_calls = 0
        self.closest_calls = 0

    def FindPointsWithinRadius(self, radius, point, target):
        self.radius_calls += 1
        for value in self.radius_values:
            target.InsertNextId(value)

    def FindClosestNPoints(self, count, point, target):
        self.closest_calls += 1
        for value in self.closest_values[:count]:
            target.InsertNextId(value)


def _backend():
    backend = object.__new__(VtkProjectMeshAdaptiveBackend)
    backend._vtk = _Vtk()
    backend._state = None
    return backend


def test_radius_candidates_avoid_full_or_nearest_scan():
    backend = _backend()
    locator = _Locator(radius_values=(4, 7), closest_values=(0, 1, 2))
    entry = _PickLocatorEntry(locator, None, tuple(f"n{i}" for i in range(1000)), 125.0)
    result = backend._candidate_instance_indexes(entry, Vector3(1, 2, 3))
    assert result == (4, 7)
    assert locator.radius_calls == 1
    assert locator.closest_calls == 0


def test_empty_radius_falls_back_to_bounded_nearest_candidates():
    backend = _backend()
    locator = _Locator(radius_values=(), closest_values=tuple(range(100)))
    entry = _PickLocatorEntry(locator, None, tuple(f"n{i}" for i in range(1000)), 125.0)
    result = backend._candidate_instance_indexes(entry, Vector3.zero())
    assert result == tuple(range(backend.MAX_PICK_CANDIDATES))
    assert locator.radius_calls == 1
    assert locator.closest_calls == 1


def test_surface_pick_evaluates_only_spatial_candidates(monkeypatch):
    backend = _backend()
    entry = _PickLocatorEntry(_Locator(), None, tuple(f"n{i}" for i in range(5000)), 125.0)
    monkeypatch.setattr(backend, "_pick_locator", lambda group, index: entry)
    monkeypatch.setattr(backend, "_candidate_instance_indexes", lambda entry, point: (120, 3500))
    seen = []
    def surface(node_id, point, index):
        seen.append(node_id)
        return {"n120": 5.0, "n3500": 1.0}[node_id]
    monkeypatch.setattr(backend, "_surface_distance", surface)
    bounds = SimpleNamespace(minimum=Vector3(-1, -1, -1), maximum=Vector3(1, 1, 1))
    index = SimpleNamespace(world_bounds_by_node={"n120": bounds, "n3500": bounds})
    assert backend._node_nearest_surface_pick(object(), Vector3.zero(), index) == "n3500"
    assert seen == ["n120", "n3500"]
