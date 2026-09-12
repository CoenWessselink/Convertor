from types import SimpleNamespace
from unittest.mock import patch

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend
from cws_viewer.contracts.enums import RenderMode
from cws_viewer.math3d import Matrix4, Rgba, Vector3


class _Mapper:
    def SetResolveCoincidentTopologyToPolygonOffset(self): pass
    def SetRelativeCoincidentTopologyPolygonOffsetParameters(self, *args): pass


class _Prop:
    def SetRepresentationToSurface(self): pass
    def EdgeVisibilityOff(self): pass
    def SetColor(self, *args): pass
    def SetOpacity(self, value): pass
    def LightingOff(self): pass


class _Actor:
    def __init__(self):
        self.mapper = _Mapper()
        self.prop = _Prop()
        self.pickable_off = 0
    def GetMapper(self): return self.mapper
    def GetProperty(self): return self.prop
    def PickableOff(self): self.pickable_off += 1


class _Index:
    def __init__(self, count=100):
        self.nodes_by_id = {}
        self.world_transform_by_node = {}
        for i in range(count):
            node_id = f"n{i}"
            self.nodes_by_id[node_id] = SimpleNamespace(geometry_id="shared-geometry")
            self.world_transform_by_node[node_id] = Matrix4.identity()
    def descendants(self, selected, **kwargs): return tuple(selected)
    def node(self, node_id): return self.nodes_by_id[node_id]


def _state(count=100):
    selected = tuple(f"n{i}" for i in range(count))
    return SimpleNamespace(
        selected_node_ids=selected,
        visible_set=set(selected),
        explode_offsets={},
        display_preferences=SimpleNamespace(selection_color=Rgba(1, .82, 0, 1), render_mode=RenderMode.SHADED),
    )


def test_selection_fill_batches_shared_geometry_into_one_overlay_actor():
    backend = object.__new__(VtkProjectMeshFeelV2Backend)
    backend._selection_fill_groups = []
    backend._node_instance = {}
    base_group = SimpleNamespace(mode=RenderMode.SHADED)
    for i in range(100): backend._node_instance[f"n{i}"] = (base_group, i)
    index = _Index(100)
    state = _state(100)
    calls = []
    def build(self, geometry_id, mode, instances, selection=False):
        calls.append((geometry_id, mode, tuple(instances), selection))
        return SimpleNamespace(actor=_Actor())
    with patch.object(VtkProjectMeshBackend, "_build_mesh_group", new=build):
        backend._rebuild_selection_fill(state, index)
    assert len(calls) == 1
    assert calls[0][0] == "shared-geometry"
    assert calls[0][3] is True
    assert len(calls[0][2]) == 100
    assert len(backend._selection_fill_groups) == 1
    assert backend._selection_fill_groups[0].actor.pickable_off == 1
