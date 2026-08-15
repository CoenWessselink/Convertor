"""Broad-phase Model Control engine with explicit evidence levels."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Callable, Iterable, Protocol, Any

from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import BoundingBox
from cws_convertor.project.model import ProjectModel
from .model import (
    ClashCategory, ClashRecord, GeometryConfidence, ModelControlSettings,
    Severity, stable_fingerprint, make_clash_id,
)


class ExactPairEvaluator(Protocol):
    def __call__(self, entity_a: str, entity_b: str, required_clearance_mm: float) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class ScanStats:
    object_count: int
    theoretical_pairs: int
    broad_phase_candidates: int
    filtered_pairs: int
    evaluated_pairs: int
    results: int


@dataclass(frozen=True, slots=True)
class ScanResult:
    records: tuple[ClashRecord, ...]
    stats: ScanStats


def _overlap_axis(a0: float, a1: float, b0: float, b1: float) -> float:
    return min(a1, b1) - max(a0, b0)


def _bbox_intersection(a: BoundingBox, b: BoundingBox) -> tuple[tuple[float, float, float, float, float, float] | None, float]:
    ox = _overlap_axis(a.minimum.x, a.maximum.x, b.minimum.x, b.maximum.x)
    oy = _overlap_axis(a.minimum.y, a.maximum.y, b.minimum.y, b.maximum.y)
    oz = _overlap_axis(a.minimum.z, a.maximum.z, b.minimum.z, b.maximum.z)
    if ox <= 0 or oy <= 0 or oz <= 0:
        return None, 0.0
    minimum = (
        max(a.minimum.x, b.minimum.x), max(a.minimum.y, b.minimum.y), max(a.minimum.z, b.minimum.z)
    )
    maximum = (
        min(a.maximum.x, b.maximum.x), min(a.maximum.y, b.maximum.y), min(a.maximum.z, b.maximum.z)
    )
    return (*minimum, *maximum), float(ox * oy * oz)


def _axis_gap(a0: float, a1: float, b0: float, b1: float) -> float:
    if a1 < b0:
        return b0 - a1
    if b1 < a0:
        return a0 - b1
    return 0.0


def _bbox_distance(a: BoundingBox, b: BoundingBox) -> float:
    dx = _axis_gap(a.minimum.x, a.maximum.x, b.minimum.x, b.maximum.x)
    dy = _axis_gap(a.minimum.y, a.maximum.y, b.minimum.y, b.maximum.y)
    dz = _axis_gap(a.minimum.z, a.maximum.z, b.minimum.z, b.maximum.z)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _bbox_region_center(region: tuple[float, float, float, float, float, float]) -> tuple[float, float, float]:
    return (
        (region[0] + region[3]) * 0.5,
        (region[1] + region[4]) * 0.5,
        (region[2] + region[5]) * 0.5,
    )


def _intended_pairs(project: ProjectModel) -> set[frozenset[str]]:
    pairs: set[frozenset[str]] = set()
    for weld in project.welds.values():
        ids = [str(v) for v in weld.connected_part_ids if v]
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pairs.add(frozenset((a, b)))
    for fastener in project.fasteners.values():
        ids = [str(v) for v in fastener.connected_part_ids if v]
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pairs.add(frozenset((a, b)))
    return pairs


class ModelControlEngine:
    def __init__(self, settings: ModelControlSettings | None = None) -> None:
        self.settings = settings or ModelControlSettings()

    def scan(
        self,
        index: SceneIndex,
        project: ProjectModel,
        *,
        entity_ids: Iterable[str] | None = None,
        exact_pair_evaluator: ExactPairEvaluator | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> ScanResult:
        allowed = None if entity_ids is None else {str(v) for v in entity_ids}
        revision_id = str(getattr(project, "revision_content_sha256", lambda: "")() or "")
        scan_payload = {
            "project_id": str(project.project_id),
            "revision_id": revision_id,
            "scope": None if allowed is None else sorted(allowed),
            "settings": {
                "geometry_tolerance_mm": self.settings.geometry_tolerance_mm,
                "hard_clash_min_penetration_mm": self.settings.hard_clash_min_penetration_mm,
                "contact_tolerance_mm": self.settings.contact_tolerance_mm,
                "default_clearance_mm": self.settings.default_clearance_mm,
            },
        }
        scan_id = "SCAN-" + sha256(json.dumps(scan_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:12].upper()
        nodes = [
            node for node in index.scene.nodes
            if node.geometry_id is not None and node.selectable
            and (allowed is None or node.entity_id in allowed)
            and node.entity_id in project.parts
        ]
        entries = sorted(
            ((index.world_bounds_by_node[n.node_id], n.entity_id, n.node_id) for n in nodes),
            key=lambda item: item[0].minimum.x,
        )
        intended = _intended_pairs(project)
        active: list[tuple[BoundingBox, str, str]] = []
        candidates: list[tuple[BoundingBox, str, str, BoundingBox, str, str]] = []
        clearance = max(0.0, self.settings.default_clearance_mm)
        for current in entries:
            if cancel_check and cancel_check():
                break
            box, entity_id, node_id = current
            active = [item for item in active if item[0].maximum.x + clearance >= box.minimum.x]
            for other in active:
                obox, oentity, onode = other
                if _axis_gap(obox.minimum.y, obox.maximum.y, box.minimum.y, box.maximum.y) > clearance:
                    continue
                if _axis_gap(obox.minimum.z, obox.maximum.z, box.minimum.z, box.maximum.z) > clearance:
                    continue
                candidates.append((obox, oentity, onode, box, entity_id, node_id))
                if len(candidates) >= self.settings.max_candidates:
                    break
            active.append(current)
            if len(candidates) >= self.settings.max_candidates:
                break

        records: list[ClashRecord] = []
        filtered = 0
        evaluated = 0
        for a_box, a_id, _a_node, b_box, b_id, _b_node in candidates:
            if cancel_check and cancel_check():
                break
            if a_id == b_id:
                filtered += 1
                continue
            pair_key = frozenset((a_id, b_id))
            relation_contact = pair_key in intended
            bbox_region, bbox_volume = _bbox_intersection(a_box, b_box)
            bbox_distance = _bbox_distance(a_box, b_box)
            exact = exact_pair_evaluator(a_id, b_id, clearance) if exact_pair_evaluator else None
            evaluated += 1

            if exact:
                intersection_volume = exact.get("intersection_volume_mm3")
                distance = exact.get("minimum_distance_mm")
                exact_region = exact.get("intersection_bbox_mm")
                closest_a = exact.get("closest_point_a_mm")
                closest_b = exact.get("closest_point_b_mm")
                confidence = str(exact.get("geometry_confidence") or GeometryConfidence.VERIFIED.value)
                source = str(exact.get("geometry_source") or "exact_brep")
                if intersection_volume is not None and float(intersection_volume) > 0:
                    category = ClashCategory.CONTACT if relation_contact else ClashCategory.HARD
                    severity = Severity.INFO if relation_contact else Severity.CRITICAL
                    region = tuple(exact_region) if exact_region else bbox_region
                    reason = "Intended relation bevestigd met exacte overlap" if relation_contact else "Exacte BREP-intersectie boven tolerantie"
                    metric_distance = 0.0
                elif distance is not None and float(distance) < clearance:
                    category = ClashCategory.CONTACT if relation_contact else ClashCategory.CLEARANCE
                    severity = Severity.INFO if relation_contact else Severity.WARNING
                    region = bbox_region
                    reason = "Intended relation binnen contacttolerantie" if relation_contact else "Exacte minimumafstand onder clearance-regel"
                    metric_distance = float(distance)
                    intersection_volume = None
                else:
                    continue
            else:
                confidence = GeometryConfidence.APPROXIMATE.value
                source = "project_aabb"
                closest_a = closest_b = None
                intersection_volume = None
                metric_distance = bbox_distance
                region = bbox_region
                if relation_contact and (bbox_region is not None or bbox_distance <= self.settings.contact_tolerance_mm):
                    category = ClashCategory.CONTACT
                    severity = Severity.INFO
                    reason = "Bekende weld/fastener-relatie; AABB-evidence is alleen reviewbewijs"
                elif bbox_region is not None and bbox_volume > 0:
                    category = ClashCategory.MODEL_QUALITY
                    severity = Severity.WARNING
                    reason = "AABB-overlap kandidaat; exacte narrow-phase ontbreekt, dus geen hard-clashclaim"
                elif bbox_distance < clearance:
                    category = ClashCategory.CLEARANCE
                    severity = Severity.WARNING
                    reason = "AABB-afstand onder clearance-regel; exacte narrow-phase vereist voor vrijgave"
                else:
                    continue

            fingerprint = stable_fingerprint(a_id, b_id, category.value, "CWS-MC-V1", region)
            location = _bbox_region_center(region) if region is not None else (
                (a_box.center.x + b_box.center.x) * 0.5,
                (a_box.center.y + b_box.center.y) * 0.5,
                (a_box.center.z + b_box.center.z) * 0.5,
            )
            records.append(
                ClashRecord(
                    clash_id=make_clash_id(fingerprint),
                    clash_fingerprint=fingerprint,
                    part_a_id=a_id,
                    part_b_id=b_id,
                    category=category.value,
                    severity=severity.value,
                    project_id=str(project.project_id),
                    model_id=str(getattr(project.parts[a_id].source_identity, "source_file_id", "") or ""),
                    scan_id=scan_id,
                    revision_id=revision_id,
                    assembly_a_id=str((project.parts[a_id].assembly_ids or [""])[0]),
                    assembly_b_id=str((project.parts[b_id].assembly_ids or [""])[0]),
                    geometry_confidence=confidence,
                    geometry_source=source,
                    title=f"{category.value.title()}: {project.parts[a_id].part_position or project.parts[a_id].name} ↔ {project.parts[b_id].part_position or project.parts[b_id].name}",
                    classification_reason=reason,
                    evidence=f"{source}; confidence={confidence}",
                    rule_id="CWS-MC-V1",
                    rule_name="General model control",
                    world_location_mm=location,
                    intersection_bbox_mm=region,
                    intersection_volume_mm3=None if intersection_volume is None else float(intersection_volume),
                    minimum_distance_mm=metric_distance,
                    actual_clearance_mm=metric_distance if category == ClashCategory.CLEARANCE else None,
                    required_clearance_mm=clearance if category == ClashCategory.CLEARANCE else None,
                    clearance_delta_mm=(clearance - metric_distance) if category == ClashCategory.CLEARANCE else None,
                    closest_point_a_mm=None if closest_a is None else tuple(float(v) for v in closest_a),
                    closest_point_b_mm=None if closest_b is None else tuple(float(v) for v in closest_b),
                )
            )

        records.sort(key=lambda r: ({Severity.CRITICAL.value: 0, Severity.WARNING.value: 1, Severity.INFO.value: 2}.get(r.severity, 9), r.clash_id))
        count = len(nodes)
        return ScanResult(
            records=tuple(records),
            stats=ScanStats(
                object_count=count,
                theoretical_pairs=count * (count - 1) // 2,
                broad_phase_candidates=len(candidates),
                filtered_pairs=filtered,
                evaluated_pairs=evaluated,
                results=len(records),
            ),
        )


__all__ = ["ExactPairEvaluator", "ScanStats", "ScanResult", "ModelControlEngine"]
