"""Small verified real-source fixture for packaged V3 viewer probes."""
from __future__ import annotations

import hashlib
import json
from importlib import resources

import numpy as np

from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind
from cws_viewer.contracts.geometry import MeshData
from cws_viewer.contracts.scene import GeometryResource, MeshLod, ProjectScene, SceneModel, SceneNode
from cws_viewer.geometry.loader import MeshRepository
from cws_viewer.math3d import Matrix4, Rgba, Vector3
from cws_viewer.contracts.scene import StyleDefinition


def load_lo4_reference_mesh() -> tuple[str, MeshData, dict]:
    root = resources.files("cws_viewer.fixtures") / "data"
    manifest = json.loads((root / "lo4_source_mesh_manifest.json").read_text(encoding="utf-8"))
    raw = (root / "lo4_source_mesh.npz").read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest["fixture_sha256"]:
        raise ValueError("LO4 displaymeshfixture checksum wijkt af")
    import io

    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:
        vertices = np.array(archive["vertices"], dtype=np.float64, copy=True)
        triangles = np.array(archive["triangles"], dtype=np.int32, copy=True)
    mesh = MeshData(
        vertices,
        triangles,
        manifest["source_geometry_hash"],
        "verified-v3-packaged-fixture",
        exactness=manifest["exactness"],
        metadata={
            "source_entity_id": manifest["source_entity_id"],
            "source_item_ids": manifest["source_item_ids"],
            "fixture": True,
        },
        mesh_hash=manifest["mesh_hash"],
    )
    return manifest["geometry_id"], mesh, manifest


def build_lo4_reference_scene() -> tuple[ProjectScene, MeshRepository]:
    geometry_id, mesh, manifest = load_lo4_reference_mesh()
    repository = MeshRepository()
    repository.put(geometry_id, mesh)
    resource = GeometryResource(
        geometry_id=geometry_id,
        representation=GeometryRepresentation.MESH_LOD,
        content_hash=manifest["source_geometry_hash"],
        units="mm",
        payload_ref=f"memory://mesh/{geometry_id}",
        lods=(
            MeshLod(
                level=0,
                content_hash=mesh.mesh_hash,
                payload_ref=f"memory://mesh/{geometry_id}",
                vertex_count=mesh.vertex_count,
                triangle_count=mesh.triangle_count,
                byte_length=mesh.byte_length,
            ),
        ),
        metadata=(("exactness", mesh.exactness), ("fixture", "LO4")),
    )
    nodes = []
    positions = ((0.0, 0.0, 0.0), (220.0, 0.0, 0.0), (0.0, 240.0, 0.0), (220.0, 240.0, 0.0))
    for index, (x, y, z) in enumerate(positions, start=1):
        nodes.append(
            SceneNode(
                node_id=f"entity:lo4-{index}",
                entity_id=f"lo4-{index}",
                source_entity_id=str(manifest["source_entity_id"]),
                parent_node_id=None,
                kind=NodeKind.PART,
                name=f"LO4 #{index}",
                transform=Matrix4.translation(Vector3(x, y, z)),
                local_bounds=mesh.bounds,
                geometry_id=geometry_id,
                selectable=True,
                tags=("LO4", "MLO4", "STRIP5*120", "S235JR"),
                geometry_hash=manifest["source_geometry_hash"],
                style_id="style-part",
            )
        )
    scene = ProjectScene.create(
        project_id="viewer-v3-lo4-fixture",
        revision_id="fixture-1",
        models=(
            SceneModel(
                model_id="model:lo4-fixture",
                name="LO4 real-source packaged fixture",
                source_file_id=None,
                root_node_ids=tuple(node.node_id for node in nodes),
            ),
        ),
        nodes=tuple(nodes),
        geometry=(resource,),
        styles=(StyleDefinition("style-part", Rgba(0.3, 0.62, 0.88, 1.0)),),
    )
    return scene, repository


__all__ = ["load_lo4_reference_mesh", "build_lo4_reference_scene"]
