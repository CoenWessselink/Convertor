"""Deterministic source/packaged self-tests for CWS Viewer V0."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from cws_viewer.adapters import CwsProjectSceneAdapter
from cws_viewer.backends import HeadlessViewerController
from cws_viewer.contracts.enums import GeometryRepresentation, NodeKind, StandardView
from cws_viewer.contracts.scene import GeometryResource, ProjectScene, SceneModel, SceneNode
from cws_viewer.core.diagnostics import collect_runtime_report
from cws_viewer.math3d import BoundingBox, Matrix4, Vector3


@dataclass(frozen=True, slots=True)
class SelfTestCheck:
    name: str
    status: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "details": self.details}


@dataclass(frozen=True, slots=True)
class SelfTestReport:
    checks: tuple[SelfTestCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.status == "passed" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "passed" if self.passed else "failed",
            "check_count": len(self.checks),
            "checks": [check.to_dict() for check in self.checks],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent, sort_keys=True)


def synthetic_scene() -> ProjectScene:
    payload = b"cws-viewer-v0-synthetic-box"
    digest = hashlib.sha256(payload).hexdigest()
    geometry = GeometryResource(
        geometry_id="geometry:synthetic-box",
        representation=GeometryRepresentation.MESH_LOD,
        content_hash=digest,
        units="mm",
        payload_ref="memory://synthetic/box",
        byte_length=len(payload),
        metadata=(("fixture", "v0-contract"),),
    )
    root = SceneNode(
        node_id="node:root",
        entity_id="project:selftest",
        source_entity_id=None,
        parent_node_id=None,
        kind=NodeKind.PROJECT,
        name="Viewer self-test",
        transform=Matrix4.identity(),
        local_bounds=BoundingBox.from_dimensions(100.0, 50.0, 10.0),
        geometry_id=None,
        selectable=False,
        clippable=False,
    )
    part = SceneNode(
        node_id="node:part",
        entity_id="part:selftest",
        source_entity_id="#1",
        parent_node_id=root.node_id,
        kind=NodeKind.PART,
        name="Box 100×50×10",
        transform=Matrix4.identity(),
        local_bounds=BoundingBox.from_dimensions(100.0, 50.0, 10.0),
        geometry_id=geometry.geometry_id,
        geometry_hash=digest,
        selectable=True,
        clippable=True,
    )
    return ProjectScene.create(
        project_id="project:selftest",
        revision_id="revision:selftest",
        models=(
            SceneModel(
                model_id="model:selftest",
                name="Synthetic scene",
                source_file_id=None,
                root_node_ids=(root.node_id,),
            ),
        ),
        nodes=(root, part),
        geometry=(geometry,),
    )


def run_contract_self_test() -> tuple[SelfTestCheck, ...]:
    checks: list[SelfTestCheck] = []
    scene = synthetic_scene()
    checks.append(
        SelfTestCheck(
            "scene-create-validate",
            "passed",
            {"scene_hash": scene.scene_hash, "node_count": len(scene.nodes)},
        )
    )

    restored = ProjectScene.from_dict(json.loads(json.dumps(scene.to_dict())))
    if restored != scene or restored.scene_hash != scene.scene_hash:
        raise AssertionError("Scene JSON-roundtrip is niet deterministisch")
    checks.append(
        SelfTestCheck(
            "scene-json-roundtrip",
            "passed",
            {"scene_hash": restored.scene_hash},
        )
    )

    controller = HeadlessViewerController()
    controller.load_scene(scene)
    controller.set_selection(("node:part",))
    controller.isolate(("node:part",), ghost_context=True)
    controller.fit_selection()
    controller.set_standard_view(StandardView.ISOMETRIC)
    viewpoint = controller.save_viewpoint("Self-test")
    controller.show_all()
    controller.activate_viewpoint(viewpoint)
    if controller.get_selection() != ("node:part",):
        raise AssertionError("Selection/Viewpoint roundtrip faalde")
    checks.append(
        SelfTestCheck(
            "headless-controller-state",
            "passed",
            {
                "selection": list(controller.get_selection()),
                "hidden_count": len(controller.hidden_node_ids),
                "viewpoint_id": viewpoint.viewpoint_id,
            },
        )
    )
    controller.shutdown()
    return tuple(checks)


def run_self_test(
    *,
    deep_native: bool = False,
    scan_root: str | Path | None = None,
) -> SelfTestReport:
    checks = list(run_contract_self_test())
    runtime = collect_runtime_report(deep=deep_native, scan_root=scan_root)
    required_ok = runtime.all_required_ok if deep_native else True
    checks.append(
        SelfTestCheck(
            "runtime-diagnostics",
            "passed" if required_ok else "failed",
            runtime.to_dict(),
        )
    )
    if runtime.forbidden_reference_count:
        checks.append(
            SelfTestCheck(
                "forbidden-trimble-binaries",
                "failed",
                {"count": runtime.forbidden_reference_count},
            )
        )
    else:
        checks.append(
            SelfTestCheck("forbidden-trimble-binaries", "passed", {"count": 0})
        )
    return SelfTestReport(tuple(checks))


__all__ = [
    "SelfTestCheck",
    "SelfTestReport",
    "synthetic_scene",
    "run_contract_self_test",
    "run_self_test",
]
