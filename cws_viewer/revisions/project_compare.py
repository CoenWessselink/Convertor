"""Deterministic project revision comparison for CWS Viewer V7."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from cws_convertor.project.model import Part, ProjectModel
from cws_viewer.math3d import Vector3

from .model import (
    ChangeKind,
    CompareRelation,
    CorrespondenceMethod,
    ImpactKind,
    PlacementDelta,
    ProjectRevisionCompareReport,
    RevisionObjectChange,
)


def _source_display_id(part: Part) -> str:
    identity = part.source_identity
    return (
        identity.global_id
        or identity.occurrence_id
        or identity.product_id
        or identity.source_entity_id
        or identity.part_position
        or part.internal_id
    )


def _identity_tokens(part: Part) -> tuple[tuple[str, str], ...]:
    identity = part.source_identity
    tokens: list[tuple[str, str]] = []
    for label, value in (
        ("global_id", identity.global_id),
        ("occurrence_id", identity.occurrence_id),
        ("product_id", identity.product_id),
        ("source_entity", f"{identity.source_format.upper()}:{identity.source_entity_id}" if identity.source_entity_id else ""),
        ("part_position", part.part_position or identity.part_position),
    ):
        text = str(value or "").strip()
        if text:
            tokens.append((label, text))
    return tuple(tokens)


def _translation(part: Part) -> Vector3:
    rows = part.global_placement.matrix
    return Vector3(float(rows[0][3]), float(rows[1][3]), float(rows[2][3]))


def _orthonormal_basis(rows) -> tuple[Vector3, Vector3, Vector3]:
    # IFC/STEP placements are expected to be rigid, but real exports can carry
    # tiny scale/shear drift.  Directly multiplying such matrices yields a
    # false rotation even when two matrices are byte-identical.  Gram-Schmidt
    # extracts the represented orientation without treating numerical drift as
    # a revision change.
    x = Vector3(float(rows[0][0]), float(rows[1][0]), float(rows[2][0])).normalized()
    y_raw = Vector3(float(rows[0][1]), float(rows[1][1]), float(rows[2][1]))
    y = (y_raw - x * x.dot(y_raw)).normalized()
    z = x.cross(y).normalized()
    z_source = Vector3(float(rows[0][2]), float(rows[1][2]), float(rows[2][2]))
    if z.dot(z_source) < 0.0:
        z = z * -1.0
        y = z.cross(x).normalized()
    return x, y, z


def _placement_delta(old: Part, new: Part) -> PlacementDelta:
    old_rows, new_rows = old.global_placement.matrix, new.global_placement.matrix
    translation = _translation(new) - _translation(old)
    max_delta = max(abs(float(old_rows[r][c]) - float(new_rows[r][c])) for r in range(4) for c in range(4))
    if max_delta <= 1e-12:
        rotation = 0.0
    else:
        try:
            old_basis = _orthonormal_basis(old_rows)
            new_basis = _orthonormal_basis(new_rows)
            relative = [[old_basis[i].dot(new_basis[j]) for j in range(3)] for i in range(3)]
            trace = relative[0][0] + relative[1][1] + relative[2][2]
            cosine = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
            rotation = math.degrees(math.acos(cosine))
        except ValueError:
            # An invalid/degenerate placement must remain visible as a large
            # change rather than being silently treated as equal.
            rotation = 180.0
    return PlacementDelta(
        translation_mm=translation,
        translation_distance_mm=translation.length(),
        rotation_delta_deg=rotation,
        matrix_max_delta=max_delta,
    )


def _placement_equal(delta: PlacementDelta, *, translation_tolerance_mm: float, rotation_tolerance_deg: float) -> bool:
    return delta.translation_distance_mm <= translation_tolerance_mm and delta.rotation_delta_deg <= rotation_tolerance_deg


def _impacts(old: Part, new: Part) -> tuple[ImpactKind, ...]:
    result: list[ImpactKind] = []
    if old.geometry_hash != new.geometry_hash:
        result.append(ImpactKind.GEOMETRY)
    if (old.material, old.material_grade, old.normalized_material) != (
        new.material,
        new.material_grade,
        new.normalized_material,
    ):
        result.append(ImpactKind.MATERIAL)
    if (old.profile, old.profile_type, old.normalized_profile, old.length_mm) != (
        new.profile,
        new.profile_type,
        new.normalized_profile,
        new.length_mm,
    ):
        result.append(ImpactKind.PROFILE)
    if old.production_features != new.production_features:
        result.append(ImpactKind.FEATURE)
    if bool(old.mirrored) != bool(new.mirrored):
        result.append(ImpactKind.MIRROR)
    if old.reference_sides != new.reference_sides:
        result.append(ImpactKind.REFERENCE)
    if old.tolerances != new.tolerances:
        result.append(ImpactKind.TOLERANCE)
    if old.coating != new.coating:
        result.append(ImpactKind.COATING)
    if (old.quantity_total, old.quantity_per_assembly) != (new.quantity_total, new.quantity_per_assembly):
        result.append(ImpactKind.QUANTITY)
    if set(old.assembly_ids) != set(new.assembly_ids):
        result.append(ImpactKind.ASSEMBLY_RELATION)
    if (
        old.classification_status,
        old.category,
        old.classification_rule_id,
    ) != (
        new.classification_status,
        new.category,
        new.classification_rule_id,
    ):
        result.append(ImpactKind.CLASSIFICATION)
    if old.manufacturing_hash != new.manufacturing_hash and not any(
        item in result
        for item in (
            ImpactKind.GEOMETRY,
            ImpactKind.MATERIAL,
            ImpactKind.PROFILE,
            ImpactKind.FEATURE,
            ImpactKind.MIRROR,
            ImpactKind.REFERENCE,
            ImpactKind.TOLERANCE,
            ImpactKind.COATING,
        )
    ):
        result.append(ImpactKind.OTHER_MANUFACTURING)
    return tuple(dict.fromkeys(result))


def _change_id(old: Part | None, new: Part | None) -> str:
    payload = {
        "old": None if old is None else old.internal_id,
        "new": None if new is None else new.internal_id,
        "old_geometry": "" if old is None else old.geometry_hash,
        "new_geometry": "" if new is None else new.geometry_hash,
        "old_manufacturing": "" if old is None else old.manufacturing_hash,
        "new_manufacturing": "" if new is None else new.manufacturing_hash,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:24]
    return f"change-{digest}"


def _record(
    old: Part | None,
    new: Part | None,
    *,
    kind: ChangeKind,
    method: CorrespondenceMethod,
    confidence: float,
    impacts: Iterable[ImpactKind] = (),
    placement_delta: PlacementDelta | None = None,
    reasons: Iterable[str] = (),
    blocking_codes: Iterable[str] = (),
) -> RevisionObjectChange:
    return RevisionObjectChange(
        change_id=_change_id(old, new),
        kind=kind,
        old_entity_id=None if old is None else old.internal_id,
        new_entity_id=None if new is None else new.internal_id,
        old_source_id=None if old is None else _source_display_id(old),
        new_source_id=None if new is None else _source_display_id(new),
        correspondence_method=method,
        confidence=confidence,
        impacts=tuple(impacts),
        old_geometry_hash="" if old is None else old.geometry_hash,
        new_geometry_hash="" if new is None else new.geometry_hash,
        old_manufacturing_hash="" if old is None else old.manufacturing_hash,
        new_manufacturing_hash="" if new is None else new.manufacturing_hash,
        placement_delta=placement_delta,
        reasons=tuple(reasons),
        blocking_codes=tuple(blocking_codes),
        old_part_position="" if old is None else old.part_position,
        new_part_position="" if new is None else new.part_position,
    )


def _unique_token_matches(old_parts: Mapping[str, Part], new_parts: Mapping[str, Part], used_old: set[str], used_new: set[str]):
    old_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    new_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    for part_id, part in old_parts.items():
        if part_id not in used_old:
            for token in _identity_tokens(part):
                old_map[token].append(part_id)
    for part_id, part in new_parts.items():
        if part_id not in used_new:
            for token in _identity_tokens(part):
                new_map[token].append(part_id)
    priority = {"global_id": 0, "occurrence_id": 1, "product_id": 2, "source_entity": 3, "part_position": 4}
    matches: list[tuple[str, str, str, float]] = []
    for token in sorted(set(old_map) & set(new_map), key=lambda item: (priority.get(item[0], 99), item[0], item[1])):
        old_ids, new_ids = old_map[token], new_map[token]
        if len(old_ids) == 1 and len(new_ids) == 1:
            old_id, new_id = old_ids[0], new_ids[0]
            if old_id in used_old or new_id in used_new:
                continue
            confidence = {"global_id": 1.0, "occurrence_id": 0.99, "product_id": 0.98, "source_entity": 0.93, "part_position": 0.88}.get(token[0], 0.85)
            matches.append((old_id, new_id, token[0], confidence))
            used_old.add(old_id)
            used_new.add(new_id)
    return matches


def _hash_matches(
    old_parts: Mapping[str, Part],
    new_parts: Mapping[str, Part],
    used_old: set[str],
    used_new: set[str],
    *,
    attr: str,
    method: CorrespondenceMethod,
):
    old_map: dict[str, list[str]] = defaultdict(list)
    new_map: dict[str, list[str]] = defaultdict(list)
    for part_id, part in old_parts.items():
        value = str(getattr(part, attr, "") or "")
        if part_id not in used_old and value:
            old_map[value].append(part_id)
    for part_id, part in new_parts.items():
        value = str(getattr(part, attr, "") or "")
        if part_id not in used_new and value:
            new_map[value].append(part_id)
    matches: list[tuple[str, str, CorrespondenceMethod, float]] = []
    ambiguous: list[tuple[list[str], list[str], str]] = []
    for digest in sorted(set(old_map) & set(new_map)):
        olds, news = old_map[digest], new_map[digest]
        if len(olds) == 1 and len(news) == 1:
            old_id, new_id = olds[0], news[0]
            used_old.add(old_id); used_new.add(new_id)
            matches.append((old_id, new_id, method, 0.96 if method == CorrespondenceMethod.MANUFACTURING_HASH else 0.92))
            continue
        # Multiple identical instances are matched by nearest placement only
        # when the assignment is unambiguous.
        remaining_news = set(news)
        proposed: list[tuple[float, str, str]] = []
        ambiguous_group = False
        for old_id in sorted(olds):
            distances = sorted(
                ((_translation(old_parts[old_id]) - _translation(new_parts[new_id])).length(), new_id)
                for new_id in remaining_news
            )
            if not distances:
                continue
            if len(distances) > 1 and abs(distances[0][0] - distances[1][0]) <= 1e-7:
                ambiguous_group = True
                break
            proposed.append((distances[0][0], old_id, distances[0][1]))
            remaining_news.remove(distances[0][1])
        if ambiguous_group or len(proposed) != min(len(olds), len(news)):
            ambiguous.append((list(olds), list(news), digest))
            continue
        for _distance, old_id, new_id in sorted(proposed):
            used_old.add(old_id); used_new.add(new_id)
            matches.append((old_id, new_id, method, 0.90 if method == CorrespondenceMethod.MANUFACTURING_HASH else 0.86))
    return matches, ambiguous


def compare_project_revisions(
    old_project: ProjectModel,
    new_project: ProjectModel,
    *,
    translation_tolerance_mm: float = 1e-6,
    rotation_tolerance_deg: float = 1e-6,
) -> ProjectRevisionCompareReport:
    if old_project.project_id != new_project.project_id:
        raise ValueError("Revision compare vereist hetzelfde project_id")
    old_project.validate(); new_project.validate()
    old_parts, new_parts = old_project.parts, new_project.parts
    used_old: set[str] = set()
    used_new: set[str] = set()
    matched: list[tuple[str, str, CorrespondenceMethod, float, tuple[str, ...]]] = []
    changes: list[RevisionObjectChange] = []
    blocking: list[str] = []

    # Stable internal IDs are deterministic across normal reimports.
    for part_id in sorted(set(old_parts) & set(new_parts)):
        used_old.add(part_id); used_new.add(part_id)
        matched.append((part_id, part_id, CorrespondenceMethod.STABLE_ID, 1.0, ("stable_internal_id",)))

    for old_id, new_id, token_kind, confidence in _unique_token_matches(old_parts, new_parts, used_old, used_new):
        matched.append((old_id, new_id, CorrespondenceMethod.SOURCE_IDENTITY, confidence, (f"unique_{token_kind}",)))

    for attr, method in (
        ("manufacturing_hash", CorrespondenceMethod.MANUFACTURING_HASH),
        ("geometry_hash", CorrespondenceMethod.GEOMETRY_HASH),
    ):
        hash_matches, ambiguous_groups = _hash_matches(old_parts, new_parts, used_old, used_new, attr=attr, method=method)
        for old_id, new_id, match_method, confidence in hash_matches:
            matched.append((old_id, new_id, match_method, confidence, (f"unique_or_nearest_{attr}",)))
        for old_ids, new_ids, digest in ambiguous_groups:
            blocking.append("CWS-V7-PART-CORRESPONDENCE-AMBIGUOUS")
            reasons = (
                f"ambiguous_{attr}:{digest[:12]}",
                f"old_candidates:{','.join(sorted(old_ids))}",
                f"new_candidates:{','.join(sorted(new_ids))}",
                "geen kandidaat is stilzwijgend gekoppeld",
            )
            # Emit every candidate explicitly.  This prevents an aggregate
            # first-item record from leaving sibling candidates reusable.
            for old_id in sorted(old_ids):
                changes.append(_record(
                    old_parts[old_id], None,
                    kind=ChangeKind.AMBIGUOUS,
                    method=CorrespondenceMethod.AMBIGUOUS,
                    confidence=0.0,
                    impacts=(ImpactKind.GEOMETRY,),
                    reasons=reasons,
                    blocking_codes=("CWS-V7-PART-CORRESPONDENCE-AMBIGUOUS",),
                ))
            for new_id in sorted(new_ids):
                changes.append(_record(
                    None, new_parts[new_id],
                    kind=ChangeKind.AMBIGUOUS,
                    method=CorrespondenceMethod.AMBIGUOUS,
                    confidence=0.0,
                    impacts=(ImpactKind.GEOMETRY,),
                    reasons=reasons,
                    blocking_codes=("CWS-V7-PART-CORRESPONDENCE-AMBIGUOUS",),
                ))
            used_old.update(old_ids); used_new.update(new_ids)

    for old_id, new_id, method, confidence, reasons in sorted(matched, key=lambda item: (item[0], item[1])):
        old, new = old_parts[old_id], new_parts[new_id]
        delta = _placement_delta(old, new)
        impacts = list(_impacts(old, new))
        placement_changed = not _placement_equal(delta, translation_tolerance_mm=translation_tolerance_mm, rotation_tolerance_deg=rotation_tolerance_deg)
        if placement_changed:
            impacts.insert(0, ImpactKind.PLACEMENT)
        manufacturing_same = old.manufacturing_hash == new.manufacturing_hash
        if manufacturing_same and not impacts:
            kind = ChangeKind.UNCHANGED
        elif manufacturing_same and set(impacts) <= {ImpactKind.PLACEMENT, ImpactKind.QUANTITY, ImpactKind.ASSEMBLY_RELATION}:
            kind = ChangeKind.MOVED if ImpactKind.PLACEMENT in impacts else ChangeKind.CHANGED
        else:
            kind = ChangeKind.CHANGED
        codes: list[str] = []
        if kind == ChangeKind.CHANGED and not manufacturing_same:
            codes.append("CWS-V7-MANUFACTURING-CHANGE")
        changes.append(_record(
            old,
            new,
            kind=kind,
            method=method,
            confidence=confidence,
            impacts=tuple(dict.fromkeys(impacts)),
            placement_delta=delta,
            reasons=reasons,
            blocking_codes=codes,
        ))

    for part_id in sorted(set(old_parts) - used_old):
        changes.append(_record(
            old_parts[part_id],
            None,
            kind=ChangeKind.REMOVED,
            method=CorrespondenceMethod.UNMATCHED,
            confidence=1.0,
            impacts=(ImpactKind.GEOMETRY,),
            reasons=("part_not_present_in_new_revision",),
            blocking_codes=("CWS-V7-PART-REMOVED",),
        ))
    for part_id in sorted(set(new_parts) - used_new):
        changes.append(_record(
            None,
            new_parts[part_id],
            kind=ChangeKind.ADDED,
            method=CorrespondenceMethod.UNMATCHED,
            confidence=1.0,
            impacts=(ImpactKind.GEOMETRY,),
            reasons=("part_not_present_in_old_revision",),
            blocking_codes=(),
        ))

    changes.sort(key=lambda item: (item.kind.value, item.old_entity_id or "~", item.new_entity_id or "~"))
    if any(item.kind == ChangeKind.AMBIGUOUS for item in changes):
        blocking.append("CWS-V7-PART-CORRESPONDENCE-AMBIGUOUS")
    return ProjectRevisionCompareReport.create(
        project_id=old_project.project_id,
        old_revision_id=old_project.revision_content_sha256(),
        new_revision_id=new_project.revision_content_sha256(),
        changes=tuple(changes),
        relation=CompareRelation.REVISION,
        blocking_codes=tuple(dict.fromkeys(blocking)),
    )


__all__ = ["compare_project_revisions"]
