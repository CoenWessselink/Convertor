"""Revision difference isolation for project and exact-part viewers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import ColorAssignment
from cws_viewer.core.controller import ViewerCoreController
from cws_viewer.math3d import Rgba

from .model import ChangeKind, CorrespondenceStatus, ProjectRevisionCompareReport
from .exact_compare import ExactCompareBundle


_CHANGE_COLORS = {
    ChangeKind.UNCHANGED: Rgba(0.42, 0.48, 0.55, 1.0),
    ChangeKind.ADDED: Rgba(0.17, 0.82, 0.42, 1.0),
    ChangeKind.REMOVED: Rgba(0.92, 0.20, 0.22, 1.0),
    ChangeKind.MOVED: Rgba(0.20, 0.58, 0.96, 1.0),
    ChangeKind.CHANGED: Rgba(1.00, 0.56, 0.08, 1.0),
    ChangeKind.AMBIGUOUS: Rgba(0.82, 0.20, 0.86, 1.0),
}


@dataclass(frozen=True, slots=True)
class DifferenceIsolationSet:
    node_ids_by_kind: tuple[tuple[ChangeKind, tuple[str, ...]], ...]
    removed_old_node_ids: tuple[str, ...]
    missing_entity_ids: tuple[str, ...]

    def nodes(self, kinds: Iterable[ChangeKind] | None = None) -> tuple[str, ...]:
        selected = None if kinds is None else {ChangeKind(item) for item in kinds}
        return tuple(
            node_id
            for kind, node_ids in self.node_ids_by_kind
            if selected is None or kind in selected
            for node_id in node_ids
        )

    def to_dict(self) -> dict:
        return {
            "node_ids_by_kind": {kind.value: list(node_ids) for kind, node_ids in self.node_ids_by_kind},
            "removed_old_node_ids": list(self.removed_old_node_ids),
            "missing_entity_ids": list(self.missing_entity_ids),
        }


def build_difference_isolation(
    old_scene: ProjectScene,
    new_scene: ProjectScene,
    report: ProjectRevisionCompareReport,
) -> DifferenceIsolationSet:
    old_by_entity = {node.entity_id: node for node in old_scene.nodes}
    new_by_entity = {node.entity_id: node for node in new_scene.nodes}
    grouped: dict[ChangeKind, list[str]] = {kind: [] for kind in ChangeKind}
    removed: list[str] = []
    missing: list[str] = []
    for change in report.changes:
        if change.kind == ChangeKind.REMOVED:
            node = old_by_entity.get(change.old_entity_id or "")
            if node:
                removed.append(node.node_id)
            elif change.old_entity_id:
                missing.append(change.old_entity_id)
            continue
        node = new_by_entity.get(change.new_entity_id or "")
        if node:
            grouped[change.kind].append(node.node_id)
        elif change.new_entity_id:
            missing.append(change.new_entity_id)
    return DifferenceIsolationSet(
        node_ids_by_kind=tuple((kind, tuple(sorted(grouped[kind]))) for kind in ChangeKind),
        removed_old_node_ids=tuple(sorted(removed)),
        missing_entity_ids=tuple(sorted(set(missing))),
    )


def apply_difference_view(
    controller: ViewerCoreController,
    isolation: DifferenceIsolationSet,
    *,
    kinds: Iterable[ChangeKind] = (ChangeKind.ADDED, ChangeKind.MOVED, ChangeKind.CHANGED, ChangeKind.AMBIGUOUS),
    ghost_context: bool = True,
) -> tuple[str, ...]:
    selected = tuple(dict.fromkeys(isolation.nodes(kinds)))
    controller.reset_styles()
    assignments = []
    for kind, node_ids in isolation.node_ids_by_kind:
        assignments.extend(ColorAssignment(node_id=node_id, color=_CHANGE_COLORS[kind]) for node_id in node_ids)
    if assignments:
        controller.colorize(assignments)
    if selected:
        controller.isolate(selected, ghost_context=ghost_context)
        controller.set_selection(selected[:1])
    else:
        controller.show_all()
    return selected




@dataclass(frozen=True, slots=True)
class ExactDifferenceIsolation:
    source_subshape_ids: tuple[str, ...]
    target_subshape_ids: tuple[str, ...]
    removed_subshape_ids: tuple[str, ...]
    added_subshape_ids: tuple[str, ...]
    changed_subshape_pairs: tuple[tuple[str, str], ...]
    ambiguous_subshape_pairs: tuple[tuple[str | None, str | None], ...]
    changed_feature_pairs: tuple[tuple[str | None, str | None], ...]

    def to_dict(self) -> dict:
        return {
            "source_subshape_ids": list(self.source_subshape_ids),
            "target_subshape_ids": list(self.target_subshape_ids),
            "removed_subshape_ids": list(self.removed_subshape_ids),
            "added_subshape_ids": list(self.added_subshape_ids),
            "changed_subshape_pairs": [list(item) for item in self.changed_subshape_pairs],
            "ambiguous_subshape_pairs": [list(item) for item in self.ambiguous_subshape_pairs],
            "changed_feature_pairs": [list(item) for item in self.changed_feature_pairs],
        }


def build_exact_difference_isolation(bundle: ExactCompareBundle) -> ExactDifferenceIsolation:
    source_ids: list[str] = []
    target_ids: list[str] = []
    removed: list[str] = []
    added: list[str] = []
    changed: list[tuple[str, str]] = []
    ambiguous: list[tuple[str | None, str | None]] = []
    for item in bundle.correspondence.subshapes:
        if item.status == CorrespondenceStatus.UNMATCHED:
            if item.source_id:
                source_ids.append(item.source_id); removed.append(item.source_id)
            if item.target_id:
                target_ids.append(item.target_id); added.append(item.target_id)
            continue
        if item.status == CorrespondenceStatus.AMBIGUOUS:
            if item.source_id: source_ids.append(item.source_id)
            if item.target_id: target_ids.append(item.target_id)
            ambiguous.append((item.source_id, item.target_id))
            continue
        if item.source_id and item.target_id and (item.method.value == "geometric" or item.score < 0.999999):
            source_ids.append(item.source_id); target_ids.append(item.target_id)
            changed.append((item.source_id, item.target_id))
    changed_features = tuple(
        (item.source_id, item.target_id)
        for item in bundle.correspondence.features
        if item.status != CorrespondenceStatus.MATCHED or item.method.value == "geometric" or item.score < 0.999999
    )
    return ExactDifferenceIsolation(
        source_subshape_ids=tuple(dict.fromkeys(source_ids)),
        target_subshape_ids=tuple(dict.fromkeys(target_ids)),
        removed_subshape_ids=tuple(dict.fromkeys(removed)),
        added_subshape_ids=tuple(dict.fromkeys(added)),
        changed_subshape_pairs=tuple(changed),
        ambiguous_subshape_pairs=tuple(ambiguous),
        changed_feature_pairs=changed_features,
    )


__all__ = ["DifferenceIsolationSet", "ExactDifferenceIsolation", "build_difference_isolation", "apply_difference_view", "build_exact_difference_isolation"]
