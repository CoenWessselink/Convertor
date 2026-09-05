from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.vtk_project import VtkProjectBackend
from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend


class _Plane:
    def __init__(self, origin=(0.0, 0.0, 0.0), normal=(1.0, 0.0, 0.0)) -> None:
        self.origin = tuple(origin)
        self.normal = tuple(normal)

    def GetOrigin(self):
        return self.origin

    def GetNormal(self):
        return self.normal

    def SetOrigin(self, *value) -> None:
        self.origin = tuple(value)

    def SetNormal(self, *value) -> None:
        self.normal = tuple(value)


class _PlaneCollection:
    def __init__(self, values: list[_Plane]) -> None:
        self.values = values

    def GetNumberOfItems(self) -> int:
        return len(self.values)

    def GetItemAsObject(self, index: int) -> _Plane:
        return self.values[index]


class _Mapper:
    def __init__(self) -> None:
        self.planes: list[_Plane] = []
        self.modified = 0
        self.removed = 0

    def GetClippingPlanes(self):
        return _PlaneCollection(self.planes) if self.planes else None

    def AddClippingPlane(self, plane: _Plane) -> None:
        self.planes.append(plane)

    def RemoveAllClippingPlanes(self) -> None:
        self.removed += 1
        self.planes.clear()

    def Modified(self) -> None:
        self.modified += 1


class PersistentRenderResourceTests(unittest.TestCase):
    def test_mesh_backend_reuses_and_disables_clipping_plane(self) -> None:
        backend = object.__new__(VtkProjectMeshBackend)
        mapper = _Mapper()
        groups = (SimpleNamespace(mapper=mapper),)

        backend._apply_planes_to_groups(groups, (_Plane((5.0, 0.0, 0.0)),))
        self.assertEqual(1, mapper.modified)
        self.assertEqual(0, mapper.removed)
        self.assertEqual(1, len(mapper.planes))

        backend._apply_planes_to_groups(groups, ())
        self.assertEqual(1, mapper.modified)
        self.assertEqual(0, mapper.removed)
        self.assertEqual((-1.0e20, 0.0, 0.0), mapper.planes[0].origin)

        backend._apply_planes_to_groups(groups, (_Plane((9.0, 8.0, 7.0)),))
        self.assertEqual(1, mapper.modified)
        self.assertEqual((9.0, 8.0, 7.0), mapper.planes[0].origin)

    def test_classic_backend_keeps_rebuild_semantics(self) -> None:
        backend = object.__new__(VtkProjectBackend)
        mapper = _Mapper()
        mapper.planes.append(_Plane())

        backend._apply_planes_to_groups(
            (SimpleNamespace(mapper=mapper),), (_Plane((2.0, 0.0, 0.0)),)
        )

        self.assertEqual(1, mapper.removed)
        self.assertEqual(1, mapper.modified)
        self.assertEqual((2.0, 0.0, 0.0), mapper.planes[0].origin)


if __name__ == "__main__":
    unittest.main(verbosity=2)
