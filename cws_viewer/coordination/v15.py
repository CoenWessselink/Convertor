"""V15 T6 assembly, revision compare, clash/preflight and sequence contracts.

T6 coordinates existing proven CWS project/revision/model-control engines.  It
adds deterministic viewer state and evidence manifests without creating a second
manufacturing truth.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable

from cws_viewer.core.serialization import stable_sha256
from cws_viewer.model_control import ModelControlEngine, ModelControlSettings, ScanResult
from cws_viewer.revisions import ProjectRevisionCompareReport, compare_project_revisions
from cws_viewer.version import VIEWER_PREVIEW_VERSION

V15_T6_SCHEMA = "cws-viewer-coordination-15.5"
V15_T6_VERSION = VIEWER_PREVIEW_VERSION


class SequenceKind(StrEnum):
    CONSTRUCTION = "construction"
    ASSEMBLY = "assembly"
    PRODUCTION_REVIEW = "production_review"


@dataclass(frozen=True, slots=True)
class AssemblyContext:
    assembly_id: str
    assembly_mark: str
    name: str
    parent_assembly_id: str | None
    child_assembly_ids: tuple[str, ...]
    main_part_id: str | None
    secondary_part_ids: tuple[str, ...]
    purchased_item_ids: tuple[str, ...]
    fastener_ids: tuple[str, ...]
    weld_ids: tuple[str, ...]

    @property
    def direct_entity_ids(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                [
                    *(value for value in (self.main_part_id,) if value),
                    *self.secondary_part_ids,
                    *self.purchased_item_ids,
                    *self.fastener_ids,
                    *self.weld_ids,
                ]
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "assembly_id": self.assembly_id,
            "assembly_mark": self.assembly_mark,
            "name": self.name,
            "parent_assembly_id": self.parent_assembly_id,
            "child_assembly_ids": list(self.child_assembly_ids),
            "main_part_id": self.main_part_id,
            "secondary_part_ids": list(self.secondary_part_ids),
            "purchased_item_ids": list(self.purchased_item_ids),
            "fastener_ids": list(self.fastener_ids),
            "weld_ids": list(self.weld_ids),
        }


@dataclass(frozen=True, slots=True)
class SequenceStep:
    step_id: str
    index: int
    name: str
    kind: SequenceKind
    assembly_ids: tuple[str, ...]
    entity_ids: tuple[str, ...]
    cumulative_entity_ids: tuple[str, ...]
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "index": self.index,
            "name": self.name,
            "kind": self.kind.value,
            "assembly_ids": list(self.assembly_ids),
            "entity_ids": list(self.entity_ids),
            "cumulative_entity_ids": list(self.cumulative_entity_ids),
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class SequencePlan:
    plan_id: str
    project_id: str
    kind: SequenceKind
    steps: tuple[SequenceStep, ...]
    cumulative: bool
    manifest_sha256: str = ""
    viewer_only: bool = True

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        kind: SequenceKind,
        steps: Iterable[SequenceStep],
        cumulative: bool,
    ) -> "SequencePlan":
        values = tuple(steps)
        payload = {
            "project_id": str(project_id),
            "kind": SequenceKind(kind).value,
            "cumulative": bool(cumulative),
            "steps": [item.to_dict() for item in values],
            "viewer_only": True,
        }
        digest = stable_sha256(payload)
        return cls(
            plan_id=f"SEQ-{digest[:12].upper()}",
            project_id=str(project_id),
            kind=SequenceKind(kind),
            steps=values,
            cumulative=bool(cumulative),
            manifest_sha256=digest,
            viewer_only=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_id": self.project_id,
            "kind": self.kind.value,
            "cumulative": self.cumulative,
            "viewer_only": self.viewer_only,
            "steps": [item.to_dict() for item in self.steps],
            "manifest_sha256": self.manifest_sha256,
        }


@dataclass(frozen=True, slots=True)
class CompareEvidence:
    report: ProjectRevisionCompareReport
    manifest_sha256: str

    @classmethod
    def from_report(cls, report: ProjectRevisionCompareReport) -> "CompareEvidence":
        return cls(report=report, manifest_sha256=stable_sha256(report.to_dict()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "report": self.report.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ClashEvidence:
    scan: ScanResult
    manifest_sha256: str

    @classmethod
    def from_scan(cls, scan: ScanResult) -> "ClashEvidence":
        records = []
        for item in scan.records:
            raw = item.to_dict()
            # Workflow timestamps are audit metadata, not clash identity. Keep
            # deterministic evidence bound to pair/rule/geometry metrics only.
            for key in (
                "created_at",
                "updated_at",
                "comments",
                "screenshots",
                "attachments",
                "viewpoints",
                "audit_events",
            ):
                raw.pop(key, None)
            records.append(raw)
        payload = {
            "records": records,
            "stats": {
                "object_count": scan.stats.object_count,
                "theoretical_pairs": scan.stats.theoretical_pairs,
                "broad_phase_candidates": scan.stats.broad_phase_candidates,
                "filtered_pairs": scan.stats.filtered_pairs,
                "evaluated_pairs": scan.stats.evaluated_pairs,
                "results": scan.stats.results,
            },
        }
        return cls(scan=scan, manifest_sha256=stable_sha256(payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_sha256": self.manifest_sha256,
            "stats": {
                "object_count": self.scan.stats.object_count,
                "theoretical_pairs": self.scan.stats.theoretical_pairs,
                "broad_phase_candidates": self.scan.stats.broad_phase_candidates,
                "filtered_pairs": self.scan.stats.filtered_pairs,
                "evaluated_pairs": self.scan.stats.evaluated_pairs,
                "results": self.scan.stats.results,
            },
            "records": [item.to_dict() for item in self.scan.records],
        }


def coordination_contract() -> dict[str, Any]:
    return {
        "schema": V15_T6_SCHEMA,
        "version": V15_T6_VERSION,
        "capabilities": {
            "assembly_drilldown": True,
            "assembly_main_secondary_hierarchy": True,
            "assembly_parent_child_navigation": True,
            "canonical_revision_compare": True,
            "compare_added_removed_changed_moved": True,
            "compare_manifest_hash": True,
            "clash_spatial_broad_phase": True,
            "clash_no_global_n_squared_bruteforce": True,
            "clash_exact_narrow_phase_extension": True,
            "clash_approximate_evidence_not_hard_claim": True,
            "construction_sequence": True,
            "assembly_sequence": True,
            "production_review_sequence": True,
            "sequence_visibility_timeline": True,
            "coordination_audit_evidence": True,
        },
        "safety": {
            "sequence_is_machine_schedule": False,
            "approximate_aabb_is_exact_clash": False,
            "compare_rewrites_canonical_ids": False,
            "viewer_can_release_machine_output": False,
        },
    }


class V15CoordinationService:
    def __init__(
        self,
        controller: Any,
        project: Any,
        *,
        model_control_settings: ModelControlSettings | None = None,
    ) -> None:
        self.controller = controller
        self.project = project
        self.model_control = ModelControlEngine(model_control_settings)
        self._last_compare: CompareEvidence | None = None
        self._last_clash: ClashEvidence | None = None
        self._active_plan: SequencePlan | None = None
        self._active_step_index: int | None = None

    def assembly_contexts(self) -> tuple[AssemblyContext, ...]:
        assemblies = dict(getattr(self.project, "assemblies", {}) or {})
        parent_by_child: dict[str, str] = {}
        for assembly_id, assembly in assemblies.items():
            for child_id in getattr(assembly, "child_assembly_ids", ()) or ():
                parent_by_child.setdefault(str(child_id), str(assembly_id))
        contexts: list[AssemblyContext] = []
        for assembly_id, assembly in assemblies.items():
            part_ids = tuple(str(v) for v in getattr(assembly, "part_ids", ()) or ())
            main = str(getattr(assembly, "main_part_id", "") or "") or None
            secondary = tuple(part_id for part_id in part_ids if part_id != main)
            contexts.append(
                AssemblyContext(
                    assembly_id=str(assembly_id),
                    assembly_mark=str(getattr(assembly, "assembly_mark", "") or ""),
                    name=str(getattr(assembly, "name", "") or getattr(assembly, "assembly_mark", "") or assembly_id),
                    parent_assembly_id=parent_by_child.get(str(assembly_id)),
                    child_assembly_ids=tuple(str(v) for v in getattr(assembly, "child_assembly_ids", ()) or ()),
                    main_part_id=main,
                    secondary_part_ids=secondary,
                    purchased_item_ids=tuple(str(v) for v in getattr(assembly, "purchased_item_ids", ()) or ()),
                    fastener_ids=tuple(str(v) for v in getattr(assembly, "fastener_ids", ()) or ()),
                    weld_ids=tuple(str(v) for v in getattr(assembly, "weld_ids", ()) or ()),
                )
            )
        return tuple(sorted(contexts, key=lambda item: (item.assembly_mark.casefold(), item.name.casefold(), item.assembly_id)))

    def assembly_context(self, assembly_id: str) -> AssemblyContext:
        value = str(assembly_id)
        return next(item for item in self.assembly_contexts() if item.assembly_id == value)

    def root_assembly_ids(self) -> tuple[str, ...]:
        contexts = self.assembly_contexts()
        return tuple(item.assembly_id for item in contexts if item.parent_assembly_id is None)

    def assembly_descendants(self, assembly_id: str, *, include_self: bool = True) -> tuple[str, ...]:
        by_id = {item.assembly_id: item for item in self.assembly_contexts()}
        if str(assembly_id) not in by_id:
            raise KeyError(assembly_id)
        result: list[str] = []
        stack = [str(assembly_id)]
        while stack:
            current = stack.pop()
            if current in result:
                continue
            if include_self or current != str(assembly_id):
                result.append(current)
            children = sorted(
                by_id[current].child_assembly_ids,
                key=lambda child: (
                    by_id.get(child, AssemblyContext(child, "", child, None, (), None, (), (), (), ())).assembly_mark.casefold(),
                    child,
                ),
                reverse=True,
            )
            stack.extend(children)
        return tuple(result)

    def assembly_entity_ids(self, assembly_id: str, *, recursive: bool = True) -> tuple[str, ...]:
        contexts = {item.assembly_id: item for item in self.assembly_contexts()}
        assembly_ids = (
            self.assembly_descendants(assembly_id, include_self=True)
            if recursive
            else (str(assembly_id),)
        )
        values: list[str] = []
        for aid in assembly_ids:
            values.extend(contexts[aid].direct_entity_ids)
        return tuple(dict.fromkeys(values))

    def _node_ids_for_entities(self, entity_ids: Iterable[str]) -> tuple[str, ...]:
        wanted = {str(v) for v in entity_ids}
        return tuple(
            node.node_id
            for node in self.controller.index.scene.nodes
            if node.entity_id in wanted and node.geometry_id is not None
        )

    def select_assembly(self, assembly_id: str, *, recursive: bool = True) -> tuple[str, ...]:
        nodes = self._node_ids_for_entities(self.assembly_entity_ids(assembly_id, recursive=recursive))
        self.controller.set_selection(nodes, mode="replace")
        return nodes

    def isolate_assembly(self, assembly_id: str, *, recursive: bool = True) -> tuple[str, ...]:
        nodes = self._node_ids_for_entities(self.assembly_entity_ids(assembly_id, recursive=recursive))
        if nodes:
            self.controller.isolate(nodes, ghost_context=False)
            self.controller.fit_all()
        return nodes

    def select_main_part(self, assembly_id: str) -> tuple[str, ...]:
        context = self.assembly_context(assembly_id)
        nodes = () if not context.main_part_id else self._node_ids_for_entities((context.main_part_id,))
        self.controller.set_selection(nodes, mode="replace")
        if nodes:
            self.controller.fit_selection()
        return nodes

    def select_secondary_parts(self, assembly_id: str) -> tuple[str, ...]:
        context = self.assembly_context(assembly_id)
        nodes = self._node_ids_for_entities(context.secondary_part_ids)
        self.controller.set_selection(nodes, mode="replace")
        return nodes

    def compare_revisions(self, old_project: Any, new_project: Any | None = None) -> CompareEvidence:
        report = compare_project_revisions(old_project, self.project if new_project is None else new_project)
        self._last_compare = CompareEvidence.from_report(report)
        return self._last_compare

    @property
    def last_compare(self) -> CompareEvidence | None:
        return self._last_compare

    def select_change(self, change_id: str) -> tuple[str, ...]:
        if self._last_compare is None:
            return ()
        change = next(item for item in self._last_compare.report.changes if item.change_id == str(change_id))
        entity_id = change.new_entity_id or change.old_entity_id
        if not entity_id:
            return ()
        nodes = self._node_ids_for_entities((entity_id,))
        self.controller.set_selection(nodes, mode="replace")
        if nodes:
            self.controller.fit_selection()
        return nodes

    def scan_clashes(
        self,
        *,
        entity_ids: Iterable[str] | None = None,
        exact_pair_evaluator: Any | None = None,
        cancel_check: Any | None = None,
    ) -> ClashEvidence:
        scan = self.model_control.scan(
            self.controller.index,
            self.project,
            entity_ids=entity_ids,
            exact_pair_evaluator=exact_pair_evaluator,
            cancel_check=cancel_check,
        )
        self._last_clash = ClashEvidence.from_scan(scan)
        return self._last_clash

    @property
    def last_clash(self) -> ClashEvidence | None:
        return self._last_clash

    def select_clash(self, clash_id: str) -> tuple[str, ...]:
        if self._last_clash is None:
            return ()
        record = next(item for item in self._last_clash.scan.records if item.clash_id == str(clash_id))
        nodes = self._node_ids_for_entities((record.part_a_id, record.part_b_id))
        self.controller.set_selection(nodes, mode="replace")
        if nodes:
            self.controller.fit_selection()
        return nodes

    def _ordered_assemblies(self) -> tuple[AssemblyContext, ...]:
        contexts = {item.assembly_id: item for item in self.assembly_contexts()}
        ordered: list[AssemblyContext] = []
        seen: set[str] = set()

        def walk(assembly_id: str) -> None:
            if assembly_id in seen or assembly_id not in contexts:
                return
            seen.add(assembly_id)
            current = contexts[assembly_id]
            ordered.append(current)
            for child in sorted(
                current.child_assembly_ids,
                key=lambda value: (
                    contexts[value].assembly_mark.casefold() if value in contexts else "",
                    value,
                ),
            ):
                walk(child)

        for root in sorted(
            self.root_assembly_ids(),
            key=lambda value: (contexts[value].assembly_mark.casefold(), value),
        ):
            walk(root)
        for orphan in sorted(set(contexts) - seen):
            walk(orphan)
        return tuple(ordered)

    def build_sequence(self, kind: SequenceKind | str) -> SequencePlan:
        requested = SequenceKind(kind)
        contexts = self._ordered_assemblies()
        steps: list[SequenceStep] = []
        cumulative: list[str] = []

        if requested in {SequenceKind.CONSTRUCTION, SequenceKind.ASSEMBLY}:
            for index, context in enumerate(contexts):
                entities = context.direct_entity_ids
                cumulative.extend(value for value in entities if value not in cumulative)
                step_payload = {
                    "project_id": str(self.project.project_id),
                    "kind": requested.value,
                    "assembly": context.assembly_id,
                    "index": index,
                    "entities": entities,
                }
                digest = stable_sha256(step_payload)
                steps.append(
                    SequenceStep(
                        step_id=f"STEP-{digest[:10].upper()}",
                        index=index,
                        name=context.assembly_mark or context.name or context.assembly_id,
                        kind=requested,
                        assembly_ids=(context.assembly_id,),
                        entity_ids=entities,
                        cumulative_entity_ids=tuple(cumulative),
                        note=(
                            "Cumulatieve bouw-/montageweergave; geen planning- of machinevrijgave"
                        ),
                    )
                )
            cumulative_mode = True
        else:
            rows: list[tuple[str, int, str, str, str]] = []
            parts = dict(getattr(self.project, "parts", {}) or {})
            for context in contexts:
                part_ids = tuple(
                    value
                    for value in (
                        *((context.main_part_id,) if context.main_part_id else ()),
                        *context.secondary_part_ids,
                    )
                    if value in parts
                )
                for order, part_id in enumerate(part_ids):
                    part = parts[part_id]
                    rows.append(
                        (
                            context.assembly_mark.casefold(),
                            order,
                            str(getattr(part, "part_position", "") or part_id).casefold(),
                            context.assembly_id,
                            part_id,
                        )
                    )
            for index, (_mark, _order, _pos, assembly_id, part_id) in enumerate(sorted(rows)):
                part = dict(getattr(self.project, "parts", {}) or {})[part_id]
                digest = stable_sha256(
                    {
                        "project_id": str(self.project.project_id),
                        "kind": requested.value,
                        "assembly": assembly_id,
                        "part": part_id,
                        "index": index,
                    }
                )
                steps.append(
                    SequenceStep(
                        step_id=f"STEP-{digest[:10].upper()}",
                        index=index,
                        name=str(getattr(part, "part_position", "") or getattr(part, "name", "") or part_id),
                        kind=requested,
                        assembly_ids=(assembly_id,),
                        entity_ids=(part_id,),
                        cumulative_entity_ids=(part_id,),
                        note="Productie-reviewvolgorde voor viewer; geen machine-operation sequence",
                    )
                )
            cumulative_mode = False

        plan = SequencePlan.create(
            project_id=str(self.project.project_id),
            kind=requested,
            steps=steps,
            cumulative=cumulative_mode,
        )
        self._active_plan = plan
        self._active_step_index = None
        return plan

    def apply_sequence_step(self, plan: SequencePlan, index: int) -> SequenceStep:
        if not 0 <= int(index) < len(plan.steps):
            raise IndexError(index)
        step = plan.steps[int(index)]
        entities = step.cumulative_entity_ids if plan.cumulative else step.entity_ids
        nodes = self._node_ids_for_entities(entities)
        if nodes:
            self.controller.isolate(nodes, ghost_context=False)
            self.controller.fit_all()
        else:
            self.controller.show_all()
        self._active_plan = plan
        self._active_step_index = int(index)
        return step

    def reset_sequence(self) -> None:
        self.controller.show_all()
        self._active_step_index = None

    @property
    def active_sequence(self) -> tuple[SequencePlan | None, int | None]:
        return self._active_plan, self._active_step_index

    def evidence_manifest(self) -> dict[str, Any]:
        payload = {
            "schema": V15_T6_SCHEMA,
            "project_id": str(getattr(self.project, "project_id", "") or ""),
            "scene_hash": self.controller.index.scene.scene_hash,
            "assembly_contexts": [item.to_dict() for item in self.assembly_contexts()],
            "compare": None if self._last_compare is None else self._last_compare.to_dict(),
            "clash": None if self._last_clash is None else self._last_clash.to_dict(),
            "sequence": None if self._active_plan is None else self._active_plan.to_dict(),
            "production_machine_transfer_allowed": False,
        }
        payload["manifest_sha256"] = stable_sha256(payload)
        return payload


__all__ = [
    "AssemblyContext",
    "ClashEvidence",
    "CompareEvidence",
    "SequenceKind",
    "SequencePlan",
    "SequenceStep",
    "V15CoordinationService",
    "V15_T6_SCHEMA",
    "V15_T6_VERSION",
    "coordination_contract",
]
