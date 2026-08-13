from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer import SCENE_SCHEMA_VERSION
from cws_viewer.api import ViewerContractError, ViewerEditRequest, ViewerErrorCode
from cws_viewer.contracts import (
    BoundingBox,
    GeometryResource,
    ProjectScene,
    SceneModel,
    SceneNode,
    StyleDefinition,
)


def translated(x: float, y: float, z: float):
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


class ViewerContractTests(unittest.TestCase):
    payload = b"CWS synthetic display geometry v1"
    payload_hash = hashlib.sha256(payload).hexdigest()

    def _geometry(self, geometry_id: str = "geometry-part-1") -> GeometryResource:
        return GeometryResource(
            geometry_id=geometry_id,
            representation="mesh_lod",
            content_hash=self.payload_hash,
            units="mm",
            payload_ref=f"sha256/{self.payload_hash}.mesh",
        )

    def _model(self) -> SceneModel:
        return SceneModel(
            model_id="model-1",
            name="Synthetic project",
            source_file_id="source-1",
            transform=translated(1000.0, 2000.0, 0.0),
        )

    def _root(self, parent_node_id: str | None = None) -> SceneNode:
        return SceneNode(
            node_id="node-assembly-1",
            entity_id="assembly-1",
            model_id="model-1",
            kind="assembly",
            name="M1",
            parent_node_id=parent_node_id,
            local_bounds=BoundingBox((0.0, 0.0, 0.0), (200.0, 100.0, 10.0)),
            selectable=True,
        )

    def _part(self, *, parent_node_id: str = "node-assembly-1", geometry_id: str = "geometry-part-1") -> SceneNode:
        return SceneNode(
            node_id="node-part-1",
            entity_id="part-1",
            model_id="model-1",
            source_entity_id="#42",
            parent_node_id=parent_node_id,
            kind="part",
            name="P1",
            transform=translated(10.0, 20.0, 0.0),
            local_bounds=BoundingBox((0.0, 0.0, 0.0), (200.0, 100.0, 10.0)),
            geometry_id=geometry_id,
            geometry_hash=self.payload_hash,
            manufacturing_hash="1" * 64,
            tags=("plate", "S235JR"),
            properties_ref="properties/part-1.json",
        )

    def _scene(self, *, nodes=None, geometry=None) -> ProjectScene:
        return ProjectScene(
            schema_version=SCENE_SCHEMA_VERSION,
            project_id="project-1",
            revision_id="revision-7",
            models=(self._model(),),
            nodes=tuple(nodes if nodes is not None else (self._part(), self._root())),
            geometry=tuple(geometry if geometry is not None else (self._geometry(),)),
            styles=(StyleDefinition("default-steel", (0.45, 0.55, 0.65, 1.0)),),
        )

    def test_scene_roundtrip_is_deterministic_and_sorted(self) -> None:
        scene = self._scene()
        restored = ProjectScene.from_json_bytes(scene.to_json_bytes())
        self.assertEqual(restored, scene)
        self.assertEqual(restored.scene_hash, scene.scene_hash)
        self.assertEqual([node.node_id for node in restored.nodes], ["node-assembly-1", "node-part-1"])
        self.assertEqual(restored.to_json_bytes(), scene.to_json_bytes())

        reordered = self._scene(nodes=(self._root(), self._part()))
        self.assertEqual(reordered.scene_hash, scene.scene_hash)
        self.assertEqual(reordered.to_json_bytes(), scene.to_json_bytes())

    def test_future_or_malformed_schema_is_rejected(self) -> None:
        payload = self._scene().to_dict()
        for version in ("2.0", "1.1", "future"):
            with self.subTest(version=version):
                payload["schema_version"] = version
                payload["scene_hash"] = ""
                with self.assertRaises(ViewerContractError) as raised:
                    ProjectScene.from_dict(payload)
                self.assertEqual(raised.exception.code, ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED)

    def test_contracts_are_immutable_including_command_parameters(self) -> None:
        scene = self._scene()
        with self.assertRaises(FrozenInstanceError):
            scene.project_id = "changed"  # type: ignore[misc]

        request = ViewerEditRequest(
            request_id="request-1",
            project_id="project-1",
            part_id="part-1",
            operation="set_reference_face",
            parameters={"face_id": "face-7", "coordinates": [1.0, 2.0, 3.0]},
            expected_part_revision=4,
        )
        with self.assertRaises(TypeError):
            request.parameters["face_id"] = "face-8"  # type: ignore[index]
        self.assertEqual(request.parameters["coordinates"], (1.0, 2.0, 3.0))
        self.assertEqual(request.to_dict()["parameters"]["coordinates"], [1.0, 2.0, 3.0])

    def test_duplicate_stable_ids_are_rejected(self) -> None:
        duplicate_node_id = SceneNode(
            node_id="node-part-1",
            entity_id="part-2",
            model_id="model-1",
            kind="part",
            name="P2",
            local_bounds=BoundingBox((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        )
        duplicate_entity_id = SceneNode(
            node_id="node-part-2",
            entity_id="part-1",
            model_id="model-1",
            kind="part",
            name="P2",
            local_bounds=BoundingBox((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        )
        for extra in (duplicate_node_id, duplicate_entity_id):
            with self.subTest(extra=extra.node_id):
                with self.assertRaises(ViewerContractError):
                    self._scene(nodes=(self._root(), self._part(), extra))

    def test_missing_model_parent_and_geometry_references_are_rejected(self) -> None:
        missing_model = SceneNode(
            node_id="orphan-model",
            entity_id="orphan-model-entity",
            model_id="missing-model",
            kind="part",
            name="orphan",
            local_bounds=BoundingBox((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)),
        )
        cases = (
            (missing_model,),
            (self._root(), self._part(parent_node_id="missing-parent")),
            (self._root(), self._part(geometry_id="missing-geometry")),
        )
        for nodes in cases:
            with self.subTest(nodes=[item.node_id for item in nodes]):
                with self.assertRaises(ViewerContractError):
                    self._scene(nodes=nodes)

    def test_parent_cycles_are_rejected(self) -> None:
        with self.assertRaises(ViewerContractError):
            self._scene(nodes=(self._root(parent_node_id="node-part-1"), self._part()))

    def test_transform_must_be_finite_affine_and_right_handed(self) -> None:
        invalid_transforms = (
            (
                (-1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            (
                (1.0, 0.0, 0.0, float("nan")),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, 1.0, 0.0),
                (0.0, 0.0, 1.0, 1.0),
            ),
        )
        for transform in invalid_transforms:
            with self.subTest(transform=transform):
                with self.assertRaises(ViewerContractError):
                    SceneModel("model", "Invalid", transform=transform)

    def test_geometry_and_scene_hashes_are_checked(self) -> None:
        geometry = self._geometry()
        geometry.verify_payload(self.payload)
        with self.assertRaises(ViewerContractError) as raised:
            geometry.verify_payload(b"tampered")
        self.assertEqual(raised.exception.code, ViewerErrorCode.GEOMETRY_HASH_MISMATCH)

        payload = json.loads(self._scene().to_json_bytes())
        payload["nodes"][1]["name"] = "tampered"
        with self.assertRaises(ViewerContractError) as raised:
            ProjectScene.from_dict(payload)
        self.assertEqual(raised.exception.code, ViewerErrorCode.GEOMETRY_HASH_MISMATCH)

    def test_contract_import_does_not_load_cad_or_ui_dependencies(self) -> None:
        code = (
            "import json,sys,cws_viewer; "
            "blocked=('cadquery','OCP','casadi','tkinter','matplotlib','PySide6','vtk'); "
            "print(json.dumps([name for name in blocked if name in sys.modules]))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(completed.stdout), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
