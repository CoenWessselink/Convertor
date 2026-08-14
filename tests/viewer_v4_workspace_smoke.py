from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.backends.memory import MemoryRenderBackend
from cws_viewer.contracts.enums import BackgroundTheme, ColorScheme, ProjectionType, RenderMode
from cws_viewer.contracts.state import ColorAssignment, ScenePatch
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.errors import ViewerError
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Rgba


class ViewerV4WorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = MemoryRenderBackend()
        self.controller = ViewerCoreController(self.backend, width=900, height=600)
        self.scene = build_synthetic_product_scene(250, parts_per_assembly=100)
        self.controller.load_scene(self.scene)

    def tearDown(self) -> None:
        self.controller.shutdown()

    def _prepare_state(self) -> None:
        self.controller.set_selection(("node:item:000010", "node:item:000249"))
        self.controller.hide(("node:item:000011",))
        self.controller.isolate(("node:assembly:0001",), ghost_context=True)
        self.controller.set_transparency(("node:item:000010",), 0.45)
        self.controller.colorize(
            (
                ColorAssignment(
                    node_id="node:item:000010",
                    color=Rgba(0.15, 0.82, 0.52, 1.0),
                ),
            )
        )
        self.controller.set_render_mode(RenderMode.WIREFRAME)
        self.controller.set_color_scheme(ColorScheme.STATUS)
        self.controller.set_background_theme(BackgroundTheme.SLATE)
        self.controller.set_projection(ProjectionType.ORTHOGRAPHIC)
        self.controller.set_accuracy_mode(True)
        self.controller.save_viewpoint("Controle LO4")
        self.controller.save_visibility_set("Lascontext")

    def test_exact_roundtrip_preserves_every_display_state(self) -> None:
        self._prepare_state()
        before = self.controller.export_workspace_state()
        with tempfile.TemporaryDirectory(prefix="cws-v4-workspace-") as temp:
            path = Path(temp) / "project.cwsview.json"
            self.controller.save_workspace(path)
            self.assertTrue(path.is_file())
            self.assertTrue(path.with_suffix(path.suffix + ".sha256").is_file())

            self.controller.show_all()
            self.controller.set_selection(())
            self.controller.reset_styles()
            self.controller.set_render_mode(RenderMode.SHADED)
            self.controller.set_background_theme(BackgroundTheme.LIGHT)
            report = self.controller.load_workspace(path)
            after = self.controller.export_workspace_state()

        self.assertTrue(report.exact_scene_match)
        self.assertFalse(report.dropped_node_ids)
        self.assertEqual(before.camera, after.camera)
        self.assertEqual(before.selected_node_ids, after.selected_node_ids)
        self.assertEqual(before.hidden_node_ids, after.hidden_node_ids)
        self.assertEqual(before.isolation_node_ids, after.isolation_node_ids)
        self.assertEqual(before.ghost_context, after.ghost_context)
        self.assertEqual(before.transparency_by_node, after.transparency_by_node)
        self.assertEqual(before.color_by_node, after.color_by_node)
        self.assertEqual(before.display_preferences, after.display_preferences)
        self.assertEqual(before.accuracy_mode, after.accuracy_mode)
        self.assertEqual(
            [item.name for item in before.viewpoints],
            [item.name for item in after.viewpoints],
        )
        self.assertEqual(
            [item.name for item in before.visibility_sets],
            [item.name for item in after.visibility_sets],
        )

    def test_revision_restore_uses_stable_ids_and_reports_missing(self) -> None:
        self._prepare_state()
        state = self.controller.export_workspace_state()
        replacement = build_synthetic_product_scene(
            200, parts_per_assembly=100, revision_id="V4-B"
        )
        self.controller.update_scene(
            ScenePatch(
                expected_scene_hash=self.scene.scene_hash,
                replacement_scene=replacement,
                reason="V4 stable-ID restore",
            )
        )
        report = self.controller.restore_workspace_state(
            state, allow_scene_mismatch=True
        )
        self.assertFalse(report.exact_scene_match)
        self.assertTrue(report.project_match)
        self.assertIn("node:item:000249", report.dropped_node_ids)
        self.assertEqual(("node:item:000010",), self.controller.get_selection())
        self.assertEqual(("node:assembly:0001",), self.controller.session.isolation)

    def test_changed_workspace_bytes_and_internal_hash_are_rejected(self) -> None:
        self._prepare_state()
        with tempfile.TemporaryDirectory(prefix="cws-v4-corrupt-") as temp:
            path = Path(temp) / "project.cwsview.json"
            self.controller.save_workspace(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["selected_node_ids"] = ["node:item:000099"]
            raw = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
            path.write_bytes(raw)
            with self.assertRaises(ViewerError):
                self.controller.load_workspace(path)

            # Make the file sidecar match; the embedded state_hash must still fail.
            sidecar = path.with_suffix(path.suffix + ".sha256")
            sidecar.write_text(hashlib.sha256(raw).hexdigest() + "\n", encoding="ascii")
            with self.assertRaises(ViewerError):
                self.controller.load_workspace(path)

    def test_true_hidden_line_is_rejected_until_removal_is_implemented(self) -> None:
        with self.assertRaises(ViewerError) as raised:
            self.controller.set_render_mode(RenderMode.HIDDEN_LINE)
        self.assertEqual(
            "CWS-VIEWER-RENDERER-CAPABILITY-MISSING",
            raised.exception.code.value,
        )
        self.assertEqual(
            RenderMode.HIDDEN_LINE.value,
            raised.exception.context["requested_render_mode"],
        )

    def test_color_scheme_switch_does_not_remove_transparency(self) -> None:
        self.controller.set_transparency(("node:item:000010",), 0.4)
        self.controller.colorize(
            (ColorAssignment("node:item:000010", Rgba(0.2, 0.4, 0.9, 1.0)),)
        )
        self.controller.clear_colors()
        self.controller.set_color_scheme(ColorScheme.MATERIAL)
        self.assertIn("node:item:000010", self.controller.session.transparency)
        self.assertFalse(self.controller.session.colors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
