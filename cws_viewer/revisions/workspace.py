"""Revision-safe reconciliation of viewer workspaces, measurements and reviews."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import Viewpoint
from cws_viewer.contracts.workspace import ViewerWorkspaceState
from cws_viewer.core.serialization import stable_sha256
from cws_viewer.measurements.model import (
    ExactMeasurementAnchor,
    MeasurementCollection,
    MeasurementRecord,
    MeasurementStatus,
)

from .model import ChangeKind, ProjectRevisionCompareReport, RevisionStateReconciliation


def _node_maps(
    old_scene: ProjectScene,
    new_scene: ProjectScene,
    report: ProjectRevisionCompareReport,
) -> tuple[dict[str, str], set[str], set[str]]:
    old_by_entity = {node.entity_id: node for node in old_scene.nodes}
    new_by_entity = {node.entity_id: node for node in new_scene.nodes}
    mapping: dict[str, str] = {}
    changed_entities: set[str] = set()
    removed_entities: set[str] = set()

    for node_id in set(node.node_id for node in old_scene.nodes) & set(node.node_id for node in new_scene.nodes):
        mapping[node_id] = node_id
    for change in report.changes:
        if change.old_entity_id and change.new_entity_id:
            old_node = old_by_entity.get(change.old_entity_id)
            new_node = new_by_entity.get(change.new_entity_id)
            if old_node and new_node:
                mapping[old_node.node_id] = new_node.node_id
        if change.manufacturing_changed or change.kind in {ChangeKind.ADDED, ChangeKind.REMOVED, ChangeKind.AMBIGUOUS}:
            if change.old_entity_id:
                changed_entities.add(change.old_entity_id)
            if change.new_entity_id:
                changed_entities.add(change.new_entity_id)
        if change.kind == ChangeKind.REMOVED and change.old_entity_id:
            removed_entities.add(change.old_entity_id)
    return mapping, changed_entities, removed_entities


def _map_ids(values: tuple[str, ...], mapping: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(mapping[item] for item in values if item in mapping))


def _map_pairs(values: tuple[tuple[str, Any], ...], mapping: Mapping[str, str]) -> tuple[tuple[str, Any], ...]:
    return tuple((mapping[node_id], value) for node_id, value in values if node_id in mapping)


def _map_viewpoint(
    viewpoint: Viewpoint,
    mapping: Mapping[str, str],
    new_scene_hash: str,
) -> Viewpoint:
    return replace(
        viewpoint,
        visible_node_ids=_map_ids(viewpoint.visible_node_ids, mapping),
        hidden_node_ids=_map_ids(viewpoint.hidden_node_ids, mapping),
        selected_node_ids=_map_ids(viewpoint.selected_node_ids, mapping),
        isolation_node_ids=_map_ids(viewpoint.isolation_node_ids, mapping),
        transparency_by_node=_map_pairs(viewpoint.transparency_by_node, mapping),
        color_by_node=_map_pairs(viewpoint.color_by_node, mapping),
        scene_hash=new_scene_hash,
    )


def _measurement_validity(record: MeasurementRecord) -> str:
    return stable_sha256({
        "kind": record.kind,
        "value": record.value,
        "unit": record.unit,
        "anchors": [anchor.to_dict() for anchor in record.anchors],
        "proof": record.proof.value,
    })


def _reconcile_measurements(
    measurements: MeasurementCollection,
    old_scene: ProjectScene,
    new_scene: ProjectScene,
    mapping: Mapping[str, str],
    changed_entities: set[str],
) -> tuple[MeasurementCollection, tuple[str, ...], tuple[str, ...]]:
    old_nodes = {node.node_id: node for node in old_scene.nodes}
    new_nodes = {node.node_id: node for node in new_scene.nodes}
    result = MeasurementCollection()
    invalidated: list[str] = []
    preserved: list[str] = []

    for record in measurements.values():
        reasons: list[str] = []
        anchors: list[ExactMeasurementAnchor] = []
        for anchor in record.anchors:
            new_node_id = mapping.get(anchor.node_id)
            if not new_node_id or new_node_id not in new_nodes:
                reasons.append(f"object {anchor.node_id} ontbreekt in nieuwe revisie")
                anchors.append(anchor)
                continue
            old_node = old_nodes.get(anchor.node_id)
            new_node = new_nodes[new_node_id]
            if new_node.entity_id in changed_entities or (old_node and old_node.entity_id in changed_entities):
                reasons.append(f"manufacturing geometry gewijzigd voor {new_node.entity_id}")
            expected_hash = anchor.geometry_hash or (old_node.geometry_hash if old_node else None)
            if expected_hash and new_node.geometry_hash and expected_hash != new_node.geometry_hash:
                reasons.append(f"geometry hash gewijzigd voor {new_node.entity_id}")
            world_point = anchor.world_point
            if old_node is not None and old_node.transform != new_node.transform:
                if anchor.local_point is None:
                    reasons.append(f"lokaal meetanker ontbreekt voor verplaatst object {new_node.entity_id}")
                else:
                    world_point = new_node.transform.transform_point(anchor.local_point)
            anchors.append(replace(
                anchor,
                node_id=new_node_id,
                entity_id=new_node.entity_id,
                source_entity_id=new_node.source_entity_id or anchor.source_entity_id,
                world_point=world_point,
                geometry_hash=new_node.geometry_hash or anchor.geometry_hash,
            ))
        updated = replace(record, anchors=tuple(anchors))
        if reasons:
            updated = replace(
                updated,
                status=MeasurementStatus.INVALIDATED,
                invalid_reason="; ".join(dict.fromkeys(reasons)),
                validity_hash=_measurement_validity(updated),
            )
            invalidated.append(record.measurement_id)
        else:
            updated = replace(
                updated,
                status=MeasurementStatus.VALID,
                invalid_reason="",
                validity_hash=_measurement_validity(updated),
            )
            preserved.append(record.measurement_id)
        result.add(updated)
    return result, tuple(invalidated), tuple(preserved)


def reconcile_revision_state(
    old_scene: ProjectScene,
    new_scene: ProjectScene,
    workspace: ViewerWorkspaceState,
    report: ProjectRevisionCompareReport,
    *,
    measurements: MeasurementCollection | None = None,
    review_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> tuple[ViewerWorkspaceState, MeasurementCollection, RevisionStateReconciliation]:
    if old_scene.project_id != new_scene.project_id or workspace.project_id != old_scene.project_id:
        raise ValueError("Workspace revision reconciliation vereist hetzelfde project")
    mapping, changed_entities, removed_entities = _node_maps(old_scene, new_scene, report)
    old_node_by_id = {node.node_id: node for node in old_scene.nodes}
    review_viewpoints: list[str] = []
    mapped_viewpoints: list[Viewpoint] = []
    for viewpoint in workspace.viewpoints:
        referenced_entities = {
            old_node_by_id[node_id].entity_id
            for node_id in (*viewpoint.visible_node_ids, *viewpoint.hidden_node_ids, *viewpoint.selected_node_ids, *viewpoint.isolation_node_ids)
            if node_id in old_node_by_id
        }
        if referenced_entities & changed_entities:
            review_viewpoints.append(viewpoint.viewpoint_id)
        mapped_viewpoints.append(_map_viewpoint(viewpoint, mapping, new_scene.scene_hash))

    mapped_state = ViewerWorkspaceState.create(
        project_id=workspace.project_id,
        scene_hash=new_scene.scene_hash,
        camera=workspace.camera,
        selection_level=workspace.selection_level,
        selected_node_ids=_map_ids(workspace.selected_node_ids, mapping),
        hidden_node_ids=_map_ids(workspace.hidden_node_ids, mapping),
        isolation_node_ids=_map_ids(workspace.isolation_node_ids, mapping),
        ghost_context=workspace.ghost_context,
        transparency_by_node=_map_pairs(workspace.transparency_by_node, mapping),
        color_by_node=_map_pairs(workspace.color_by_node, mapping),
        display_preferences=workspace.display_preferences,
        section_planes=workspace.section_planes,
        clipping_box=workspace.clipping_box,
        viewpoints=tuple(mapped_viewpoints),
        visibility_sets=workspace.visibility_sets,
        accuracy_mode=workspace.accuracy_mode,
        active_viewpoint_id=workspace.active_viewpoint_id if any(item.viewpoint_id == workspace.active_viewpoint_id for item in mapped_viewpoints) else None,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )

    updated_measurements, invalidated_measurements, preserved_measurements = _reconcile_measurements(
        measurements or MeasurementCollection(),
        old_scene,
        new_scene,
        mapping,
        changed_entities,
    )
    invalidated_reviews: list[str] = []
    for review_id, binding in (review_bindings or {}).items():
        entity_id = str(binding.get("entity_id") or "")
        if entity_id in changed_entities or entity_id in removed_entities:
            invalidated_reviews.append(str(review_id))
            continue
        geometry_hash = str(binding.get("geometry_hash") or "")
        current_node = next((node for node in new_scene.nodes if node.entity_id == entity_id), None)
        if geometry_hash and (current_node is None or current_node.geometry_hash != geometry_hash):
            invalidated_reviews.append(str(review_id))

    blocking: list[str] = []
    if invalidated_measurements:
        blocking.append("CWS-V7-MEASUREMENTS-INVALIDATED")
    if invalidated_reviews:
        blocking.append("CWS-V7-REVIEWS-INVALIDATED")
    reconciliation = RevisionStateReconciliation(
        old_revision_id=old_scene.revision_id or report.old_revision_id,
        new_revision_id=new_scene.revision_id or report.new_revision_id,
        preserved_viewpoint_ids=tuple(item.viewpoint_id for item in mapped_viewpoints),
        review_viewpoint_ids=tuple(sorted(review_viewpoints)),
        invalidated_measurement_ids=invalidated_measurements,
        preserved_measurement_ids=preserved_measurements,
        invalidated_review_ids=tuple(sorted(invalidated_reviews)),
        blocking_codes=tuple(blocking),
    )
    return mapped_state, updated_measurements, reconciliation


__all__ = ["reconcile_revision_state"]
