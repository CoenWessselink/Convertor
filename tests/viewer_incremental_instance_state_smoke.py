from types import SimpleNamespace
from unittest.mock import patch

from cws_viewer.backends.vtk_project_mesh import VtkProjectMeshBackend
from cws_viewer.contracts.enums import RenderMode
from cws_viewer.contracts.state import ViewerDisplayPreferences
from cws_viewer.math3d import Matrix4, Rgba, Vector3
from cws_viewer.rendering.contracts import RenderState


class _Points:
    def __init__(self, count):
        self.values = [(0.0, 0.0, 0.0) for _ in range(count)]
        self.get_calls = self.set_calls = self.modified_calls = 0
    def GetPoint(self, index):
        self.get_calls += 1
        return self.values[index]
    def SetPoint(self, index, *value):
        self.set_calls += 1
        self.values[index] = tuple(value)
    def Modified(self): self.modified_calls += 1


class _Array:
    def __init__(self, values):
        self.values = list(values)
        self.get_calls = self.set_calls = self.modified_calls = 0
    def GetValue(self, index):
        self.get_calls += 1
        return self.values[index]
    def SetValue(self, index, value):
        self.set_calls += 1
        self.values[index] = value
    def GetTuple(self, index):
        self.get_calls += 1
        return self.values[index]
    def SetTypedTuple(self, index, value):
        self.set_calls += 1
        self.values[index] = tuple(value)
    def Modified(self): self.modified_calls += 1


class _Index:
    def __init__(self, count):
        self.world_transform_by_node = {f"n{i}": Matrix4.translation(Vector3(float(i), 0.0, 0.0)) for i in range(count)}
        self.nodes_by_id = {f"n{i}": SimpleNamespace(entity_id=f"e{i}") for i in range(count)}
    def node(self, node_id): return self.nodes_by_id[node_id]


def _state(count, *, hidden=(), ghosted=(), explode=(), prefs=None):
    hidden = set(hidden)
    return RenderState(
        scene_hash="scene",
        visible_node_ids=tuple(f"n{i}" for i in range(count) if f"n{i}" not in hidden),
        ghosted_node_ids=tuple(ghosted),
        selected_node_ids=(),
        transparency_by_node=(),
        color_by_node=(),
        display_preferences=prefs or ViewerDisplayPreferences(render_mode=RenderMode.SHADED),
        explode_offsets_by_node=tuple(explode),
    )


def _backend(count=5725):
    backend = object.__new__(VtkProjectMeshBackend)
    points = _Points(count)
    mask = _Array([1] * count)
    colors = _Array([(128, 160, 200, 255)] * count)
    group = SimpleNamespace(mode=RenderMode.SHADED, points=points, mask=mask, colors=colors)
    backend._mesh_groups = [group]
    backend._node_instance = {f"n{i}": (group, i) for i in range(count)}
    backend._instance_visible_cache = frozenset(f"n{i}" for i in range(count))
    backend._instance_ghosted_cache = frozenset()
    backend._instance_colors_cache = {}
    backend._instance_transparency_cache = {}
    backend._instance_explode_cache = {}
    backend._instance_preferences_cache = ViewerDisplayPreferences(render_mode=RenderMode.SHADED)
    return backend, group


def test_single_visibility_delta_touches_one_of_5725_instances():
    count = 5725
    backend, group = _backend(count)
    index = _Index(count)
    with patch.object(VtkProjectMeshBackend, "_ensure_static_groups"), \
         patch.object(VtkProjectMeshBackend, "_style_for_node") as style, \
         patch.object(VtkProjectMeshBackend, "_configure_group_mode") as mode:
        backend._update_instance_state(_state(count, hidden=("n2711",)), index)
    assert group.mask.get_calls == 1
    assert group.mask.set_calls == 1
    assert group.mask.values[2711] == 0
    assert group.points.get_calls == 0
    assert group.colors.get_calls == 0
    style.assert_not_called()
    mode.assert_not_called()


def test_single_explode_delta_touches_one_instance_only():
    count = 5725
    backend, group = _backend(count)
    index = _Index(count)
    with patch.object(VtkProjectMeshBackend, "_ensure_static_groups"), \
         patch.object(VtkProjectMeshBackend, "_style_for_node") as style, \
         patch.object(VtkProjectMeshBackend, "_configure_group_mode"):
        backend._update_instance_state(
            _state(count, explode=(("n41", Vector3(0.0, 3.0, 0.0)),)), index
        )
    assert group.points.get_calls == 1
    assert group.points.set_calls == 1
    assert group.mask.get_calls == 0
    assert group.colors.get_calls == 0
    style.assert_not_called()


def test_single_ghost_delta_restyles_one_instance_only():
    count = 5725
    backend, group = _backend(count)
    index = _Index(count)
    with patch.object(VtkProjectMeshBackend, "_ensure_static_groups"), \
         patch.object(VtkProjectMeshBackend, "_configure_group_mode"), \
         patch.object(VtkProjectMeshBackend, "_style_for_node", return_value=(RenderMode.SHADED, Rgba(1, 0, 0, 1))) as style, \
         patch.object(VtkProjectMeshBackend, "_rgba_bytes", return_value=(255, 0, 0, 255)):
        backend._update_instance_state(_state(count, ghosted=("n99",)), index)
    assert style.call_count == 1
    assert group.colors.get_calls == 1
    assert group.colors.set_calls == 1
    assert group.mask.get_calls == 0
    assert group.points.get_calls == 0
