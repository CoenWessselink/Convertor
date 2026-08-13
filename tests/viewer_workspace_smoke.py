from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import (
    Assembly,
    Part,
    ProjectSession,
    SourceIdentity,
    ValidationIssue,
)
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.contracts import AccuracyStatus
from cws_convertor.steel_model.viewer_boundary import (
    REQUIRED_VIEWER_CAPABILITIES,
    STEEL_MODEL_SCHEMA_VERSION,
    VIEWER_HOST_CONTRACT_VERSION,
    ViewerHandshake,
    ViewerHostSnapshot,
    build_viewer_host_snapshot,
)
from cws_convertor.ui.project_viewer import ProjectViewerPanel
from cws_convertor.viewer.workspace import ViewerWorkspaceState
from project_tab import CWSProjectTab


class ViewerWorkspaceTests(unittest.TestCase):
    def _session(self, folder: Path) -> ProjectSession:
        source_path = folder / "viewer.ifc"
        source_path.write_text("IFC viewer fixture", encoding="ascii")
        session = ProjectSession.new("Viewer accuracy", created_by="tester")
        source = session.project.add_source_path(source_path, user="tester")
        source.analysis_status = "imported"
        source.semantic_import_complete = True
        source.import_strategy = "B_separate_solids"
        identity = SourceIdentity(
            source_file_id=source.source_id,
            source_format="IFC",
            source_sha256=source.sha256,
            source_entity_id="#42",
            global_id="viewer-guid",
            part_position="K14",
            assembly_mark="A1",
        )
        part = Part(
            internal_id="part-k14",
            name="Randligger",
            source_identity=identity,
            part_position="K14",
            assembly_ids=["assembly-a1"],
            profile="IPE300",
            material="S355J2",
            length_mm=6200.0,
            geometry_descriptor={
                "source_geometry_hash": "b" * 64,
                "source_inspection": {
                    "selection_verified": True,
                    "production_geometry_exact": False,
                    "geometry_kind": "triangulated_mesh",
                },
            },
        )
        part.recompute_hashes()
        part.validation_issues.append(
            ValidationIssue(
                code="CWS-VIEW-001",
                message="Meshcontrole binnen tolerantie bevestigen",
                severity="warning",
                blocking=False,
                entity_id=part.internal_id,
            )
        )
        assembly = Assembly(
            internal_id="assembly-a1",
            name="Spant A",
            source_identity=identity,
            assembly_mark="A1",
            part_ids=[part.internal_id],
        )
        session.project.add_entity(part, user="tester")
        session.project.add_entity(assembly, user="tester")
        return session

    def _state(self, session: ProjectSession) -> ViewerWorkspaceState:
        steel_model = build_steel_model_snapshot(session.project)
        return ViewerWorkspaceState(steel_model, build_viewer_host_snapshot(steel_model))

    def test_verified_workspace_selects_bidirectionally_and_exposes_trace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_state_") as folder_name:
            session = self._session(Path(folder_name))
            try:
                state = self._state(session)
                payload = state.select("part-k14")
                self.assertEqual(payload["source_entity_id"], "#42")
                self.assertEqual(payload["steel_model_id"], "part-k14")
                self.assertTrue(payload["viewer_node_id"])
                self.assertEqual(payload["accuracy_status"], AccuracyStatus.APPROXIMATE.value)
                self.assertEqual(
                    state.select_viewer_node(payload["viewer_node_id"])["steel_model_id"],
                    "part-k14",
                )
                self.assertEqual(state.issues()[0].code, "CWS-VIEW-001")
                manifest = state.visual_manifest()
                self.assertEqual(manifest["entity_count"], 2)
                self.assertEqual(manifest["binding_count"], 2)
                self.assertEqual(manifest["accuracy"]["approximate"], 1)
            finally:
                session.close()

    def test_tree_search_keeps_source_assembly_and_part_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_tree_") as folder_name:
            session = self._session(Path(folder_name))
            try:
                state = self._state(session)
                tree = state.tree("K14")
                self.assertEqual(len(tree), 1)
                all_nodes = []

                def collect(nodes) -> None:
                    for node in nodes:
                        all_nodes.append(node)
                        collect(node.children)

                collect(tree)
                part_node = next(item for item in all_nodes if item.steel_model_id == "part-k14")
                assembly_node = next(
                    item for item in all_nodes if item.steel_model_id == "assembly-a1"
                )
                self.assertIn("K14", part_node.label)
                self.assertIn(part_node, assembly_node.children)
                self.assertEqual(part_node.accuracy_status, "approximate")
                self.assertEqual(state.search("IPE300")[0].steel_model_id, "part-k14")
            finally:
                session.close()

    def test_tampered_or_incomplete_host_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_guard_") as folder_name:
            session = self._session(Path(folder_name))
            try:
                steel_model = build_steel_model_snapshot(session.project)
                host = build_viewer_host_snapshot(steel_model)
                raw = host.to_dict()
                raw["bindings"] = raw["bindings"][:-1]
                raw.pop("snapshot_sha256")
                incomplete = ViewerHostSnapshot.from_dict(raw)
                with self.assertRaisesRegex(ValueError, "do not cover"):
                    ViewerWorkspaceState(steel_model, incomplete)

                raw = copy.deepcopy(host.to_dict())
                raw["bindings"][0]["accuracy_status"] = "exact"
                raw.pop("snapshot_sha256")
                changed = ViewerHostSnapshot.from_dict(raw)
                with self.assertRaisesRegex(ValueError, "accuracy status mismatch"):
                    ViewerWorkspaceState(steel_model, changed)
            finally:
                session.close()

    def test_renderer_tools_require_complete_handshake(self) -> None:
        with tempfile.TemporaryDirectory(prefix="viewer_handshake_") as folder_name:
            session = self._session(Path(folder_name))
            try:
                state = self._state(session)
                incomplete = ViewerHandshake(
                    component_name="Parallel Viewer",
                    component_version="0.1",
                    contract_version=VIEWER_HOST_CONTRACT_VERSION,
                    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
                    capabilities=("scene.load", "selection.sync"),
                )
                self.assertFalse(state.register_handshake(incomplete)["compatible"])
                self.assertFalse(state.capability_available("measurement.state"))
                complete = ViewerHandshake(
                    component_name="Parallel Viewer",
                    component_version="1.0",
                    contract_version=VIEWER_HOST_CONTRACT_VERSION,
                    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
                    capabilities=REQUIRED_VIEWER_CAPABILITIES,
                )
                self.assertTrue(state.register_handshake(complete)["compatible"])
                self.assertTrue(state.capability_available("measurement.state"))
            finally:
                session.close()

    def test_tk_panel_loads_real_state_and_synchronizes_selection(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.withdraw()
        with tempfile.TemporaryDirectory(prefix="viewer_ui_") as folder_name:
            session = self._session(Path(folder_name))
            selected: list[str] = []
            panel = ProjectViewerPanel(root, selection_callback=selected.append)
            panel.pack(fill="both", expand=True)
            try:
                panel.load_project(session.project)
                root.update_idletasks()
                self.assertEqual(len(panel.state.steel_model.entities), 2)
                self.assertEqual(str(panel.select_button["state"]), "disabled")
                self.assertEqual(str(panel.measure_button["state"]), "disabled")
                self.assertTrue(panel.select_entity("part-k14", notify=True))
                self.assertEqual(selected[-1], "part-k14")
                self.assertEqual(panel.state.selected_id, "part-k14")
                self.assertIn("part-k14", panel.export_visual_manifest())
                incomplete_handshake = ViewerHandshake(
                    component_name="Incomplete Viewer",
                    component_version="0.1",
                    contract_version=VIEWER_HOST_CONTRACT_VERSION,
                    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
                    capabilities=("scene.load", "selection.sync"),
                )
                rejected_commands: list[tuple[str, dict]] = []
                report = panel.attach_renderer(
                    incomplete_handshake,
                    lambda command, payload: rejected_commands.append((command, payload)),
                )
                self.assertFalse(report["compatible"])
                panel.select_entity("part-k14")
                panel._run_renderer_command("camera.fit_all", require_attached=False)
                self.assertEqual(rejected_commands, [])
                self.assertEqual(str(panel.measure_button["state"]), "disabled")
                complete_handshake = ViewerHandshake(
                    component_name="Parallel Viewer",
                    component_version="1.0",
                    contract_version=VIEWER_HOST_CONTRACT_VERSION,
                    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
                    capabilities=REQUIRED_VIEWER_CAPABILITIES,
                )
                panel.register_renderer_handshake(complete_handshake)
                self.assertEqual(str(panel.measure_button["state"]), "disabled")
                commands: list[tuple[str, dict]] = []
                panel.attach_renderer(
                    complete_handshake,
                    lambda command, payload: commands.append((command, payload)),
                )
                self.assertEqual(commands[0][0], "scene.load")
                scene_payload = commands[0][1]
                self.assertEqual(
                    scene_payload["steel_model_snapshot_sha256"],
                    panel.state.steel_model.snapshot_sha256,
                )
                self.assertEqual(
                    scene_payload["viewer_host_snapshot_sha256"],
                    panel.state.viewer_host.snapshot_sha256,
                )
                self.assertEqual(
                    scene_payload["steel_model"]["project_id"],
                    scene_payload["viewer_host"]["project_id"],
                )
                self.assertEqual(str(panel.measure_button["state"]), "normal")
                self.assertEqual(str(panel.select_button["state"]), "normal")
                panel.select_button.invoke()
                self.assertEqual(commands[-1][0], "selection.begin")
                panel.measure_button.invoke()
                self.assertEqual(commands[-1][0], "measurement.begin")
                commands.clear()
                viewer_node_id = panel.state.binding("part-k14").viewer_node_id
                panel.select_viewer_node(viewer_node_id)
                root.update()
                self.assertEqual(commands, [])
                panel.load_project(session.project)
                self.assertEqual(commands[-1][0], "scene.load")
            finally:
                panel.destroy()
                session.close()
                root.destroy()

    def test_main_app_does_not_echo_incoming_renderer_selection(self) -> None:
        class PartGridStub:
            def exists(self, part_id: str) -> bool:
                return part_id == "part-k14"

            def selection_set(self, _part_id: str) -> None:
                pass

            def focus(self, _part_id: str) -> None:
                pass

            def see(self, _part_id: str) -> None:
                pass

        tab = object.__new__(CWSProjectTab)
        tab.part_grid = PartGridStub()
        tab._part_selected = Mock()
        CWSProjectTab._select_part_everywhere(tab, "part-k14", source="viewer")
        tab._part_selected.assert_called_once_with(sync_renderer=False)

    def test_real_project_tab_does_not_echo_delayed_tk_selection_event(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.withdraw()
        with tempfile.TemporaryDirectory(prefix="viewer_project_tab_") as folder_name:
            session = self._session(Path(folder_name))
            tab = CWSProjectTab(root)
            tab.pack(fill="both", expand=True)
            tab.session = session
            try:
                tab.refresh()
                root.update()
                handshake = ViewerHandshake(
                    component_name="Parallel Viewer",
                    component_version="1.0",
                    contract_version=VIEWER_HOST_CONTRACT_VERSION,
                    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
                    capabilities=REQUIRED_VIEWER_CAPABILITIES,
                )
                commands: list[tuple[str, dict]] = []
                tab.project_viewer.attach_renderer(
                    handshake,
                    lambda command, payload: commands.append((command, payload)),
                )
                commands.clear()
                binding = tab.project_viewer.state.binding("part-k14")
                tab.project_viewer.select_viewer_node(binding.viewer_node_id)
                root.update()
                self.assertEqual(commands, [])
                self.assertEqual(tab.project_viewer.state.selected_id, "part-k14")
                self.assertEqual(tab.part_grid.selection(), ("part-k14",))
            finally:
                tab.session = None
                tab.destroy()
                session.close()
                root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
