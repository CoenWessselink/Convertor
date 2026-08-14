from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceIdentity
from cws_convertor.steel_model.viewer_boundary import (
    REQUIRED_VIEWER_CAPABILITIES,
    STEEL_MODEL_SCHEMA_VERSION,
    VIEWER_HOST_CONTRACT_VERSION,
    ViewerHandshake,
)
from cws_convertor.ui.project_viewer import ProjectViewerPanel
from cws_convertor.viewer.mesh_resources import ViewerMeshResource
from cws_convertor.viewer.progressive_loader import ProgressiveMeshLoadPlan


HANDSHAKE = ViewerHandshake(
    component_name="Progressive test renderer",
    component_version="1.0",
    contract_version=VIEWER_HOST_CONTRACT_VERSION,
    steel_model_schema_version=STEEL_MODEL_SCHEMA_VERSION,
    capabilities=REQUIRED_VIEWER_CAPABILITIES,
)


class ProgressiveMeshLoadPlanTests(unittest.TestCase):
    def test_claims_are_bounded_and_selection_moves_to_front(self) -> None:
        plan = ProgressiveMeshLoadPlan(
            ("part-1", "part-2", "part-3", "part-4"),
            max_in_flight=2,
        )
        self.assertTrue(plan.prioritize("part-4"))
        self.assertEqual(plan.claim(), ("part-4", "part-1"))
        self.assertEqual(plan.claim(), ())
        self.assertTrue(plan.mark_loaded("part-4"))
        self.assertEqual(plan.claim(), ("part-2",))
        self.assertEqual(plan.manifest()["pending"], 2)

    def test_failure_can_be_retried_without_changing_total(self) -> None:
        plan = ProgressiveMeshLoadPlan(("part-1",), max_in_flight=1)
        self.assertEqual(plan.claim(), ("part-1",))
        self.assertTrue(plan.mark_failed("part-1", "bronmesh ontbreekt"))
        self.assertEqual(plan.manifest()["status"], "completed_with_errors")
        self.assertTrue(plan.prioritize("part-1"))
        self.assertEqual(plan.claim(), ("part-1",))
        self.assertTrue(plan.mark_loaded("part-1"))
        manifest = plan.manifest()
        self.assertEqual(manifest["status"], "completed")
        self.assertEqual(manifest["loaded"], 1)
        self.assertEqual(manifest["failed"], 0)

    def test_cancel_marks_queued_and_pending_work_terminal(self) -> None:
        timestamps = iter((10.0, 10.25))
        plan = ProgressiveMeshLoadPlan(
            ("part-1", "part-2", "part-3"),
            max_in_flight=1,
            clock=lambda: next(timestamps),
        )
        self.assertEqual(plan.claim(), ("part-1",))
        plan.cancel()
        manifest = plan.manifest(include_runtime=True)
        self.assertEqual(manifest["status"], "cancelled")
        self.assertEqual(manifest["cancelled"], 3)
        self.assertEqual(manifest["elapsed_ms"], 250)
        self.assertFalse(plan.mark_loaded("part-1"))


class ProgressiveViewerPanelTests(unittest.TestCase):
    def _session(self, folder: Path, part_count: int) -> ProjectSession:
        source_path = folder / "progressive.ifc"
        source_path.write_text("generated progressive viewer fixture", encoding="ascii")
        session = ProjectSession.new("Progressive viewer")
        source = session.project.add_source_path(source_path)
        source.analysis_status = "imported"
        source.semantic_import_complete = True
        for index in range(part_count):
            identity = SourceIdentity(
                source_file_id=source.source_id,
                source_format="IFC",
                source_sha256=source.sha256,
                source_entity_id=f"#{index + 1}",
                part_position=f"P{index + 1}",
            )
            part = Part(
                internal_id=f"part-{index + 1}",
                name=f"Part {index + 1}",
                source_identity=identity,
                part_position=f"P{index + 1}",
                geometry_descriptor={
                    "source_geometry_hash": f"{index + 1:064x}",
                    "source_inspection": {
                        "selection_verified": True,
                        "production_geometry_exact": False,
                        "geometry_kind": "triangulated_mesh",
                    },
                },
            )
            part.recompute_hashes()
            session.project.add_entity(part)
        return session

    @staticmethod
    def _resource(panel: ProjectViewerPanel, part_id: str) -> ViewerMeshResource:
        entity = panel.state.entity(part_id)
        binding = panel.state.binding(part_id)
        return ViewerMeshResource(
            project_id=panel.state.steel_model.project_id,
            steel_model_id=part_id,
            viewer_geometry_id=binding.viewer_geometry_id,
            source_file_id=entity.source.source_file_id,
            source_sha256=entity.source.source_sha256,
            source_entity_id=entity.source.source_entity_id,
            source_geometry_hash=entity.geometry_hash,
            geometry_basis="source_ifc_triangulation",
            accuracy_status=entity.accuracy_status.value,
            vertices_mm=((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0)),
            triangles=((0, 1, 2),),
            tessellation={"method": "generated_progressive_fixture"},
        )

    def _panel(
        self,
        root: tk.Tk,
        session: ProjectSession,
    ) -> tuple[ProjectViewerPanel, list[tuple[str, dict]]]:
        commands: list[tuple[str, dict]] = []
        panel = ProjectViewerPanel(root)
        panel.pack(fill="both", expand=True)
        root.update()
        panel.load_project(session.project)
        panel.attach_renderer(
            HANDSHAKE,
            lambda command, payload: commands.append((command, payload)),
        )
        return panel, commands

    @staticmethod
    def _wait(root: tk.Tk, predicate, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            root.update()
            if predicate():
                return
            time.sleep(0.01)
        raise AssertionError("Timed out while waiting for progressive viewer loading")

    def test_project_load_is_bounded_prioritized_and_batched(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.geometry("760x560+10000+10000")
        with tempfile.TemporaryDirectory(prefix="progressive_viewer_") as folder_name:
            session = self._session(Path(folder_name), 12)
            panel = None
            try:
                panel, commands = self._panel(root, session)
                panel.select_entity("part-12")
                lock = threading.Lock()
                order: list[str] = []
                active = 0
                maximum_active = 0

                def provider(part_id: str, *, cancel_check) -> ViewerMeshResource:
                    nonlocal active, maximum_active
                    with lock:
                        order.append(part_id)
                        active += 1
                        maximum_active = max(maximum_active, active)
                    try:
                        time.sleep(0.035)
                        cancel_check()
                        return self._resource(panel, part_id)
                    finally:
                        with lock:
                            active -= 1

                setattr(provider, "viewer_max_concurrency", 2)
                setattr(provider, "viewer_accepts_cancel", True)
                commands.clear()
                panel.load_project(session.project, mesh_provider=provider)
                self._wait(
                    root,
                    lambda: panel._mesh_plan is not None and panel._mesh_plan.is_finished,
                )
                manifest = panel._mesh_plan.manifest()
                self.assertEqual(manifest["loaded"], 12)
                self.assertEqual(maximum_active, 2)
                self.assertIn("part-12", order[:2])
                patch_commands = [item for item in commands if item[0] == "scene.patch"]
                self.assertLess(len(patch_commands), 12)
                self.assertEqual(panel.state.visual_manifest()["mesh_resource_count"], 12)
                self.assertEqual(str(panel.mesh_cancel_button["state"]), "disabled")
            finally:
                if panel is not None:
                    panel.destroy()
                session.close()
                root.destroy()

    def test_cancel_discards_late_results_and_selection_can_restart(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.geometry("760x560+10000+10000")
        with tempfile.TemporaryDirectory(prefix="cancel_viewer_") as folder_name:
            session = self._session(Path(folder_name), 8)
            panel = None
            try:
                panel, _commands = self._panel(root, session)

                def provider(part_id: str, *, cancel_check) -> ViewerMeshResource:
                    for _index in range(30):
                        time.sleep(0.005)
                        cancel_check()
                    return self._resource(panel, part_id)

                setattr(provider, "viewer_max_concurrency", 2)
                setattr(provider, "viewer_accepts_cancel", True)
                panel.load_project(session.project, mesh_provider=provider)
                self._wait(root, lambda: panel._mesh_plan.manifest()["pending"] == 2)
                panel.cancel_mesh_requests(clear_plan=False)
                cancelled_generation = panel._mesh_generation
                self._wait(root, lambda: panel._mesh_events.empty())
                self.assertEqual(
                    panel.state.visual_manifest()["mesh_resource_count"],
                    0,
                )
                self.assertEqual(panel._mesh_plan.manifest()["status"], "cancelled")

                panel.select_entity("part-8")
                self.assertGreater(panel._mesh_generation, cancelled_generation)
                self._wait(
                    root,
                    lambda: panel.state.mesh_resource("part-8") is not None,
                    timeout=8.0,
                )
                self.assertEqual(panel._mesh_plan.manifest()["mode"], "selection_only")
                self.assertEqual(
                    panel.state.visual_manifest()["mesh_resource_count"],
                    1,
                )
            finally:
                if panel is not None:
                    panel.destroy()
                session.close()
                root.destroy()

    def test_invalid_resource_does_not_reject_valid_batch_neighbours(self) -> None:
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk-weergave niet beschikbaar: {exc}")
        root.geometry("760x560+10000+10000")
        with tempfile.TemporaryDirectory(prefix="failed_mesh_viewer_") as folder_name:
            session = self._session(Path(folder_name), 6)
            panel = None
            try:
                panel, _commands = self._panel(root, session)
                first_pair = threading.Barrier(2)

                def provider(part_id: str, *, cancel_check) -> ViewerMeshResource:
                    if part_id in {"part-1", "part-2"}:
                        first_pair.wait(timeout=2.0)
                    cancel_check()
                    resource = self._resource(panel, part_id)
                    return (
                        replace(resource, project_id="wrong-project")
                        if part_id == "part-2"
                        else resource
                    )

                setattr(provider, "viewer_max_concurrency", 2)
                setattr(provider, "viewer_accepts_cancel", True)
                panel.load_project(session.project, mesh_provider=provider)
                self._wait(root, lambda: panel._mesh_plan.is_finished)
                manifest = panel._mesh_plan.manifest()
                self.assertEqual(manifest["loaded"], 5)
                self.assertEqual(manifest["failed"], 1)
                self.assertIn("part-2", manifest["failures"])
                self.assertEqual(panel.state.visual_manifest()["mesh_resource_count"], 5)
                self.assertIsNotNone(panel.state.mesh_resource("part-1"))
                self.assertIsNone(panel.state.mesh_resource("part-2"))
            finally:
                if panel is not None:
                    panel.destroy()
                session.close()
                root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
