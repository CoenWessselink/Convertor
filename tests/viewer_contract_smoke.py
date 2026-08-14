from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind
from cws_viewer.contracts.scene import GeometryResource, ProjectScene, SceneModel, SceneNode
from cws_viewer.core.validation import verify_geometry_payloads
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Matrix4
from cws_viewer.selftest import synthetic_scene


class ViewerContractTests(unittest.TestCase):
    def test_scene_roundtrip_and_hash_are_deterministic(self) -> None:
        scene = synthetic_scene()
        restored = ProjectScene.from_dict(json.loads(json.dumps(scene.to_dict())))
        self.assertEqual(scene, restored)
        self.assertEqual(scene.scene_hash, restored.calculate_hash())

    def test_scene_node_is_immutable(self) -> None:
        node = synthetic_scene().nodes[1]
        with self.assertRaises(FrozenInstanceError):
            node.name = "gewijzigd"  # type: ignore[misc]

    def test_unknown_future_major_schema_is_rejected(self) -> None:
        payload = synthetic_scene().to_dict()
        payload["schema_version"] = "9.0"
        with self.assertRaises(ViewerError) as raised:
            ProjectScene.from_dict(payload)
        self.assertEqual(ViewerErrorCode.SCENE_SCHEMA_UNSUPPORTED, raised.exception.code)

    def test_duplicate_stable_node_id_is_blocked(self) -> None:
        scene = synthetic_scene()
        duplicate = replace(scene.nodes[1], entity_id="part:duplicate")
        with self.assertRaises(ViewerError) as raised:
            ProjectScene.create(
                project_id=scene.project_id,
                revision_id=scene.revision_id,
                models=scene.models,
                nodes=(*scene.nodes, duplicate),
                geometry=scene.geometry,
            )
        self.assertEqual(ViewerErrorCode.SCENE_DUPLICATE_ID, raised.exception.code)

    def test_missing_parent_reference_is_blocked(self) -> None:
        scene = synthetic_scene()
        broken = replace(scene.nodes[1], parent_node_id="node:missing")
        with self.assertRaises(ViewerError) as raised:
            ProjectScene.create(
                project_id=scene.project_id,
                revision_id=scene.revision_id,
                models=scene.models,
                nodes=(scene.nodes[0], broken),
                geometry=scene.geometry,
            )
        self.assertEqual(ViewerErrorCode.SCENE_REFERENCE_MISSING, raised.exception.code)

    def test_left_handed_transform_is_rejected(self) -> None:
        with self.assertRaises(ViewerError) as raised:
            Matrix4.from_rows(
                [
                    [-1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1],
                ]
            )
        self.assertEqual(ViewerErrorCode.TRANSFORM_INVALID, raised.exception.code)

    def test_geometry_payload_hash_and_length_are_verified(self) -> None:
        payload = b"cws-viewer-v0-synthetic-box"
        scene = synthetic_scene()
        result = verify_geometry_payloads(scene, lambda _: payload)
        self.assertEqual(1, result["payload_count"])
        self.assertEqual(len(payload), result["total_bytes"])

        with self.assertRaises(ViewerError) as raised:
            verify_geometry_payloads(scene, lambda _: b"tampered")
        self.assertEqual(ViewerErrorCode.GEOMETRY_HASH_MISMATCH, raised.exception.code)

    def test_unsafe_payload_reference_is_blocked(self) -> None:
        payload = b"unsafe"
        digest = hashlib.sha256(payload).hexdigest()
        resource = GeometryResource(
            geometry_id="geometry:unsafe",
            representation=GeometryRepresentation.MESH_LOD,
            content_hash=digest,
            units="mm",
            payload_ref="file://../secret.bin",
        )
        node = SceneNode(
            node_id="node:root",
            entity_id="project:unsafe",
            source_entity_id=None,
            parent_node_id=None,
            kind=NodeKind.PROJECT,
            name="Unsafe",
            transform=Matrix4.identity(),
            local_bounds=BoundingBox.zero(),
            geometry_id=resource.geometry_id,
            selectable=False,
        )
        with self.assertRaises(ViewerError) as raised:
            ProjectScene.create(
                project_id="project:unsafe",
                revision_id=None,
                models=(SceneModel("model:unsafe", "Unsafe", None, (node.node_id,)),),
                nodes=(node,),
                geometry=(resource,),
            )
        self.assertEqual(ViewerErrorCode.GEOMETRY_PAYLOAD_UNSAFE, raised.exception.code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
