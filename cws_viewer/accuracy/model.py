"""Accuracy/Debug Mode data for traceable source → scene → mesh inspection."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cws_viewer.core.scene_index import SceneIndex


class AccuracyStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True, slots=True)
class AccuracyIssue:
    code: str
    status: AccuracyStatus
    message: str


@dataclass(frozen=True, slots=True)
class AccuracyRecord:
    node_id: str
    entity_id: str
    source_entity_id: str
    geometry_id: str
    scene_units: str
    geometry_hash: str
    manufacturing_hash: str
    geometry_resource_hash: str
    mesh_hash: str
    source_geometry_hash: str
    mesh_provider: str
    mesh_exactness: str
    vertex_count: int
    triangle_count: int
    transform_determinant: float
    right_handed: bool
    world_bounds_min: tuple[float, float, float]
    world_bounds_max: tuple[float, float, float]
    world_bounds_size: tuple[float, float, float]
    profile: str
    material: str
    recognition_status: str
    status: AccuracyStatus
    issues: tuple[AccuracyIssue, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "entity_id": self.entity_id,
            "source_entity_id": self.source_entity_id,
            "geometry_id": self.geometry_id,
            "scene_units": self.scene_units,
            "geometry_hash": self.geometry_hash,
            "manufacturing_hash": self.manufacturing_hash,
            "geometry_resource_hash": self.geometry_resource_hash,
            "mesh_hash": self.mesh_hash,
            "source_geometry_hash": self.source_geometry_hash,
            "mesh_provider": self.mesh_provider,
            "mesh_exactness": self.mesh_exactness,
            "vertex_count": self.vertex_count,
            "triangle_count": self.triangle_count,
            "transform_determinant": self.transform_determinant,
            "right_handed": self.right_handed,
            "world_bounds_min": self.world_bounds_min,
            "world_bounds_max": self.world_bounds_max,
            "world_bounds_size": self.world_bounds_size,
            "profile": self.profile,
            "material": self.material,
            "recognition_status": self.recognition_status,
            "status": self.status.value,
            "issues": [
                {"code": item.code, "status": item.status.value, "message": item.message}
                for item in self.issues
            ],
        }


class ViewerAccuracyProvider:
    def __init__(self, index: SceneIndex, project: Any, mesh_repository: Any | None = None) -> None:
        self.index = index
        self.project = project
        self.mesh_repository = mesh_repository

    def _entity(self, entity_id: str) -> Any | None:
        if hasattr(self.project, "get_entity"):
            value = self.project.get_entity(entity_id)
            if value is not None:
                return value
        for name in ("assemblies", "parts", "purchased_items", "fasteners", "welds"):
            value = (getattr(self.project, name, {}) or {}).get(entity_id)
            if value is not None:
                return value
        return None

    def record(self, node_id: str) -> AccuracyRecord:
        node = self.index.node(node_id)
        entity = self._entity(node.entity_id)
        geometry = self.index.geometry_by_id.get(node.geometry_id or "")
        mesh = None
        if self.mesh_repository is not None and node.geometry_id:
            getter = getattr(self.mesh_repository, "get", None)
            if callable(getter):
                mesh = getter(node.geometry_id)
        issues: list[AccuracyIssue] = []
        determinant = self.index.world_transform_by_node[node_id].determinant3()
        right_handed = determinant > 0.0
        if not right_handed:
            issues.append(AccuracyIssue("CWS-ACCURACY-LEFT-HANDED", AccuracyStatus.FAIL, "Placement is niet rechtsgeldig"))
        if node.geometry_id is None:
            issues.append(AccuracyIssue("CWS-ACCURACY-NO-GEOMETRY", AccuracyStatus.WARNING, "Node heeft geen displaygeometrie"))
        exactness = str(getattr(mesh, "exactness", "") or "")
        if exactness == "display_proxy":
            issues.append(AccuracyIssue("CWS-ACCURACY-DISPLAY-PROXY", AccuracyStatus.WARNING, "Alleen expliciete displayproxy beschikbaar"))
        elif exactness == "display_approximation":
            issues.append(AccuracyIssue("CWS-ACCURACY-DISPLAY-APPROXIMATION", AccuracyStatus.WARNING, "Displaygeometrie bevat verklaarde benadering"))
        elif mesh is not None and exactness != "source_tessellation":
            issues.append(AccuracyIssue("CWS-ACCURACY-UNKNOWN-EXACTNESS", AccuracyStatus.WARNING, f"Onbekende display-exactness: {exactness or 'leeg'}"))
        geometry_resource_hash = str(getattr(geometry, "content_hash", "") or "")
        source_geometry_hash = str(getattr(mesh, "source_geometry_hash", "") or "")
        # ``node.geometry_hash`` is the canonical/project geometry identity, while
        # ``mesh.source_geometry_hash`` identifies the source representation used
        # for display tessellation.  They are intentionally separate namespaces.
        # Integrity must therefore be checked against GeometryResource.content_hash.
        if geometry_resource_hash and source_geometry_hash and geometry_resource_hash != source_geometry_hash:
            issues.append(
                AccuracyIssue(
                    "CWS-ACCURACY-SOURCE-GEOMETRY-HASH-MISMATCH",
                    AccuracyStatus.FAIL,
                    "GeometryResource content hash wijkt af van de mesh source hash",
                )
            )
        if node.geometry_id and mesh is None:
            issues.append(
                AccuracyIssue(
                    "CWS-ACCURACY-MESH-NOT-LOADED",
                    AccuracyStatus.WARNING,
                    "Displaymesh is niet geladen",
                )
            )
        mesh_warnings = tuple(str(item) for item in (getattr(mesh, "warnings", ()) or ()))
        issues.extend(
            AccuracyIssue("CWS-ACCURACY-MESH-WARNING", AccuracyStatus.WARNING, message)
            for message in mesh_warnings
        )
        profile = str(getattr(entity, "normalized_profile", "") or getattr(entity, "profile", "") or "")
        material = str(getattr(entity, "normalized_material", "") or getattr(entity, "material", "") or "")
        recognition = str(getattr(entity, "classification_status", "") or getattr(entity, "status", "") or "")
        if node.kind.value in {"part", "purchased_item"} and not profile:
            issues.append(AccuracyIssue("CWS-ACCURACY-PROFILE-UNKNOWN", AccuracyStatus.WARNING, "Profiel/doorsnede is niet herkend"))
        if recognition.strip().casefold() in {"", "unclassified", "unknown", "review_required", "blocked"}:
            issues.append(
                AccuracyIssue(
                    "CWS-ACCURACY-RECOGNITION-REVIEW",
                    AccuracyStatus.WARNING,
                    f"Productieclassificatie vereist controle: {recognition or 'onbekend'}",
                )
            )
        if any(item.status == AccuracyStatus.FAIL for item in issues):
            status = AccuracyStatus.FAIL
        elif issues:
            status = AccuracyStatus.WARNING
        else:
            status = AccuracyStatus.PASS
        bounds = self.index.world_bounds_by_node[node_id]
        return AccuracyRecord(
            node_id=node.node_id,
            entity_id=node.entity_id,
            source_entity_id=str(node.source_entity_id or ""),
            geometry_id=str(node.geometry_id or ""),
            scene_units=str(getattr(geometry, "units", "") or ""),
            geometry_hash=str(node.geometry_hash or ""),
            manufacturing_hash=str(node.manufacturing_hash or ""),
            geometry_resource_hash=geometry_resource_hash,
            mesh_hash=str(getattr(mesh, "mesh_hash", "") or ""),
            source_geometry_hash=source_geometry_hash,
            mesh_provider=str(getattr(mesh, "provider", "") or ""),
            mesh_exactness=exactness,
            vertex_count=int(getattr(mesh, "vertex_count", 0) or 0),
            triangle_count=int(getattr(mesh, "triangle_count", 0) or 0),
            transform_determinant=float(determinant),
            right_handed=right_handed,
            world_bounds_min=bounds.minimum.to_tuple(),
            world_bounds_max=bounds.maximum.to_tuple(),
            world_bounds_size=bounds.size.to_tuple(),
            profile=profile,
            material=material,
            recognition_status=recognition,
            status=status,
            issues=tuple(issues),
        )


__all__ = ["AccuracyStatus", "AccuracyIssue", "AccuracyRecord", "ViewerAccuracyProvider"]
