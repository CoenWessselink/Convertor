from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Part, ProjectSession, SourceFileRecord, SourceIdentity
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.viewer_boundary import build_viewer_host_snapshot
from cws_convertor.viewer.mesh_resources import ViewerMeshResource
from cws_convertor.viewer.vtk_backend import VtkOffscreenRenderer
from cws_convertor.viewer.workspace import ViewerWorkspaceState


class ViewerV6MainAppControlTests(unittest.TestCase):
    def _scene(self) -> tuple[ProjectSession, ViewerWorkspaceState, str]:
        session = ProjectSession.new("Integrated controls", created_by="test")
        session.project.sources["source-controls"] = SourceFileRecord(
            source_id="source-controls",
            file_name="controls.step",
            source_format="STEP",
            sha256="a" * 64,
            size_bytes=1,
        )
        part = Part(
            internal_id="controls-part",
            name="Control plate",
            part_position="P1",
            source_identity=SourceIdentity(
                source_format="STEP",
                source_file_id="source-controls",
                source_sha256="a" * 64,
                source_entity_id="#1",
            ),
            profile="PL10",
            material="S355JR",
            geometry_descriptor={"source_geometry_hash": "b" * 64, "bbox_mm": [100.0, 50.0, 10.0]},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="test")
        steel_model = build_steel_model_snapshot(session.project)
        state = ViewerWorkspaceState(steel_model, build_viewer_host_snapshot(steel_model))
        entity = state.entity(part.internal_id)
        binding = state.binding(part.internal_id)
        assert entity is not None and binding is not None
        resource = ViewerMeshResource(
            project_id=steel_model.project_id,
            steel_model_id=part.internal_id,
            viewer_geometry_id=binding.viewer_geometry_id,
            source_file_id=entity.source.source_file_id,
            source_sha256=entity.source.source_sha256,
            source_entity_id=entity.source.source_entity_id,
            source_geometry_hash=entity.geometry_hash,
            geometry_basis="source_native_brep",
            accuracy_status=entity.accuracy_status.value,
            vertices_mm=((0.0, 0.0, 0.0), (100.0, 0.0, 0.0), (0.0, 50.0, 0.0)),
            triangles=((0, 1, 2),),
            tessellation={"linear_deflection_mm": 0.2},
        )
        state.attach_mesh_resource(resource)
        return session, state, binding.viewer_node_id

    @unittest.skipIf(
        os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
        "GitHub Windows has no stable OpenGL context; packaged GUI gate covers the main app",
    )
    def test_project_controls_and_workspace_11_remain_display_only(self) -> None:
        session, state, node_id = self._scene()
        renderer = VtkOffscreenRenderer(width=320, height=220)
        try:
            renderer.command("scene.load", state.scene_payload())
            renderer.command("selection.set", {"viewer_node_ids": [node_id]})
            renderer.command("display.projection", {"projection": "orthographic"})
            renderer.command("display.render_mode", {"mode": "wireframe"})
            renderer.command("display.color_scheme", {"scheme": "material"})
            renderer.command("visibility.ghost", {"viewer_node_ids": [node_id]})
            renderer.command("section.set", {"plane_id": "z-1", "normal": [0, 0, 1], "origin": [0, 0, 0]})
            renderer.command("clipping_box.toggle")
            renderer.command("display.explode", {"factor": 0.4})
            workspace = renderer.command("workspace.export")["workspace"]

            schema = json.loads(
                (ROOT / "cws_viewer" / "schemas" / "viewer-workspace-1.1.schema.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(set(schema["required"]) <= set(workspace))

            self.assertEqual("1.1", workspace["schema_version"])
            self.assertEqual(state.steel_model.project_id, workspace["project_id"])
            self.assertEqual("orthographic", workspace["camera"]["projection"])
            self.assertEqual("wireframe", workspace["display_preferences"]["render_mode"])
            self.assertEqual("material", workspace["display_preferences"]["color_scheme"])
            self.assertEqual([node_id], workspace["selected_node_ids"])
            self.assertEqual(1, len(workspace["section_planes"]))
            self.assertIsNotNone(workspace["clipping_box"])
            self.assertEqual(64, len(workspace["state_hash"]))
            self.assertNotIn("manufacturing_hash", str(workspace))
            self.assertNotIn("production_release", str(workspace))

            renderer.command("visibility.hide", {"viewer_node_ids": [node_id]})
            renderer.command("display.render_mode", {"mode": "shaded"})
            renderer.command("workspace.load", {"workspace": workspace})
            telemetry = renderer.telemetry()
            self.assertEqual("wireframe", telemetry["render_mode"])
            self.assertEqual(0, telemetry["hidden_count"])
            self.assertEqual(1, telemetry["section_count"])

            tampered = copy.deepcopy(workspace)
            tampered["display_preferences"]["render_mode"] = "shaded"
            with self.assertRaisesRegex(ValueError, "checksum"):
                renderer.command("workspace.load", {"workspace": tampered})
        finally:
            renderer.close()
            session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
