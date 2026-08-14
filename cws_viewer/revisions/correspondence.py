"""Deterministic V7 correspondence for exact subshapes and features.

The matcher first uses identity evidence and only then placement-independent
geometric descriptors.  Ties are surfaced as ambiguous instead of being guessed.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Callable, Iterable, Sequence, TypeVar

from cws_viewer.exact.model import ExactPartSnapshot, FeatureDescriptor, SubshapeDescriptor
from cws_viewer.math3d import Vector3

from .model import (
    CompareRelation,
    CorrespondenceMethod,
    CorrespondenceReport,
    CorrespondenceStatus,
    SubshapeCorrespondence,
)

T = TypeVar("T")


def _hungarian_minimize(costs: Sequence[Sequence[float]]) -> tuple[tuple[int, int], ...]:
    """Deterministic rectangular Hungarian assignment without SciPy.

    The result contains at most ``min(rows, columns)`` pairs.  Callers still
    enforce their acceptance threshold and ambiguity policy; the solver merely
    prevents a locally greedy match from stealing a target needed by a better
    global correspondence.
    """

    if not costs or not costs[0]:
        return ()
    rows, cols = len(costs), len(costs[0])
    transposed = rows > cols
    matrix = [list(row) for row in costs]
    if transposed:
        matrix = [[matrix[row][column] for row in range(rows)] for column in range(cols)]
        rows, cols = cols, rows
    inf = 1.0e12
    u = [0.0] * (rows + 1)
    v = [0.0] * (cols + 1)
    p = [0] * (cols + 1)
    way = [0] * (cols + 1)
    for i in range(1, rows + 1):
        p[0] = i
        j0 = 0
        minv = [inf] * (cols + 1)
        used = [False] * (cols + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = inf
            j1 = 0
            for j in range(1, cols + 1):
                if used[j]:
                    continue
                current = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                if current < minv[j] - 1e-15:
                    minv[j] = current
                    way[j] = j0
                if minv[j] < delta - 1e-15 or (abs(minv[j] - delta) <= 1e-15 and (j1 == 0 or j < j1)):
                    delta = minv[j]
                    j1 = j
            if delta >= inf:
                break
            for j in range(cols + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    pairs: list[tuple[int, int]] = []
    for column in range(1, cols + 1):
        if not p[column]:
            continue
        row_index, column_index = p[column] - 1, column - 1
        if transposed:
            row_index, column_index = column_index, row_index
        pairs.append((row_index, column_index))
    return tuple(sorted(pairs))


def _ratio_score(a: float | None, b: float | None, *, floor: float = 1e-9) -> float:
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    denominator = max(abs(float(a)), abs(float(b)), floor)
    return max(0.0, 1.0 - abs(float(a) - float(b)) / denominator)


def _distance_score(a: Vector3, b: Vector3, scale: float) -> float:
    return max(0.0, 1.0 - (a - b).length() / max(scale, 1e-9))


def _direction_score(a: Vector3 | None, b: Vector3 | None, *, unoriented: bool = True) -> float:
    if a is None and b is None:
        return 1.0
    if a is None or b is None:
        return 0.0
    try:
        dot = a.normalized().dot(b.normalized())
    except ValueError:
        return 0.0
    if unoriented:
        dot = abs(dot)
    return max(0.0, min(1.0, (dot + (0.0 if unoriented else 1.0)) / (1.0 if unoriented else 2.0)))


def _relative_center(item_center: Vector3, snapshot: ExactPartSnapshot) -> Vector3:
    center = snapshot.properties.bounds.center
    size = snapshot.properties.bounds.size
    scale = max(size.x, size.y, size.z, 1.0)
    return (item_center - center) / scale


def _subshape_score(
    source: SubshapeDescriptor,
    target: SubshapeDescriptor,
    source_snapshot: ExactPartSnapshot,
    target_snapshot: ExactPartSnapshot,
) -> tuple[float, tuple[str, ...]]:
    if source.kind != target.kind or source.geometry_type != target.geometry_type:
        return 0.0, ("kind_or_geometry_type_differs",)
    reasons: list[str] = ["kind_and_geometry_type_match"]
    measure = _ratio_score(source.measure, target.measure)
    radius = _ratio_score(source.radius, target.radius)
    center = _distance_score(
        _relative_center(source.center, source_snapshot),
        _relative_center(target.center, target_snapshot),
        0.08,
    )
    direction = _direction_score(source.direction or source.axis_direction, target.direction or target.axis_direction)
    normal = _direction_score(source.normal, target.normal)
    parent_overlap = 1.0 if set(source.parent_ids) == set(target.parent_ids) else 0.5 if source.parent_ids and target.parent_ids else 0.8
    score = 0.34 * measure + 0.18 * radius + 0.24 * center + 0.10 * direction + 0.08 * normal + 0.06 * parent_overlap
    if measure > 0.999999:
        reasons.append("measure_equal")
    if radius > 0.999999:
        reasons.append("radius_equal")
    if center > 0.98:
        reasons.append("relative_center_equal")
    return max(0.0, min(1.0, score)), tuple(reasons)


def _feature_score(
    source: FeatureDescriptor,
    target: FeatureDescriptor,
    source_snapshot: ExactPartSnapshot,
    target_snapshot: ExactPartSnapshot,
) -> tuple[float, tuple[str, ...]]:
    if source.feature_type != target.feature_type:
        return 0.0, ("feature_type_differs",)
    reasons = ["feature_type_match"]
    center = _distance_score(
        _relative_center(source.center, source_snapshot),
        _relative_center(target.center, target_snapshot),
        0.08,
    )
    radius = _ratio_score(source.radius, target.radius)
    diameter = _ratio_score(source.diameter, target.diameter)
    depth = _ratio_score(source.depth, target.depth)
    axis = _direction_score(source.axis, target.axis)
    side = 1.0 if source.side == target.side else 0.6 if not source.side or not target.side else 0.0
    score = 0.30 * center + 0.18 * radius + 0.18 * diameter + 0.12 * depth + 0.12 * axis + 0.10 * side
    if center > 0.98:
        reasons.append("relative_center_equal")
    if max(radius, diameter) > 0.999999:
        reasons.append("size_equal")
    return max(0.0, min(1.0, score)), tuple(reasons)


def _match_records(
    source_items: Sequence[T],
    target_items: Sequence[T],
    *,
    source_id: Callable[[T], str],
    target_id: Callable[[T], str],
    kind: Callable[[T], str],
    signature: Callable[[T], str],
    scorer: Callable[[T, T], tuple[float, tuple[str, ...]]],
    threshold: float,
    ambiguity_margin: float,
) -> tuple[SubshapeCorrespondence, ...]:
    remaining_source = {source_id(item): item for item in source_items}
    remaining_target = {target_id(item): item for item in target_items}
    result: list[SubshapeCorrespondence] = []

    # 1. Stable IDs are strongest when both sides retained the same topology.
    for item_id in sorted(set(remaining_source) & set(remaining_target)):
        source = remaining_source.pop(item_id)
        target = remaining_target.pop(item_id)
        result.append(SubshapeCorrespondence(
            source_id=item_id,
            target_id=item_id,
            kind=kind(source),
            status=CorrespondenceStatus.MATCHED,
            method=CorrespondenceMethod.STABLE_ID,
            confidence=1.0,
            score=1.0,
            reasons=("stable_id_equal",),
        ))

    # 2. Unique signature matches survive harmless ordering changes.
    source_signatures: dict[str, list[T]] = defaultdict(list)
    target_signatures: dict[str, list[T]] = defaultdict(list)
    for item in remaining_source.values():
        source_signatures[signature(item)].append(item)
    for item in remaining_target.values():
        target_signatures[signature(item)].append(item)
    for sig in sorted(set(source_signatures) & set(target_signatures)):
        sources = source_signatures[sig]
        targets = target_signatures[sig]
        if len(sources) != 1 or len(targets) != 1:
            continue
        source, target = sources[0], targets[0]
        source_key, target_key = source_id(source), target_id(target)
        remaining_source.pop(source_key, None)
        remaining_target.pop(target_key, None)
        result.append(SubshapeCorrespondence(
            source_id=source_key,
            target_id=target_key,
            kind=kind(source),
            status=CorrespondenceStatus.MATCHED,
            method=CorrespondenceMethod.SIGNATURE,
            confidence=0.995,
            score=1.0,
            reasons=("unique_signature_equal",),
        ))

    # 3. Deterministic global geometric assignment.  A Hungarian assignment
    # avoids greedy target stealing.  Local or target-side ties remain blocked
    # instead of being guessed.
    source_keys = tuple(sorted(remaining_source))
    target_keys = tuple(sorted(remaining_target))
    scores: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {}
    for source_key in source_keys:
        for target_key in target_keys:
            scores[(source_key, target_key)] = scorer(remaining_source[source_key], remaining_target[target_key])

    costs = [
        [1.0 - scores[(source_key, target_key)][0] for target_key in target_keys]
        for source_key in source_keys
    ]
    assigned = _hungarian_minimize(costs) if source_keys and target_keys else ()
    assigned_by_source = {source_keys[row]: target_keys[column] for row, column in assigned}
    used_targets: set[str] = set()
    handled_sources: set[str] = set()

    target_rankings: dict[str, list[tuple[float, str]]] = {target: [] for target in target_keys}
    for source_key in source_keys:
        for target_key in target_keys:
            target_rankings[target_key].append((scores[(source_key, target_key)][0], source_key))
    for values in target_rankings.values():
        values.sort(key=lambda item: (-item[0], item[1]))

    for source_key in source_keys:
        target_key = assigned_by_source.get(source_key)
        if target_key is None:
            continue
        score, reasons = scores[(source_key, target_key)]
        if score < threshold:
            continue
        source_values = sorted(
            ((scores[(source_key, candidate)][0], candidate) for candidate in target_keys),
            key=lambda item: (-item[0], item[1]),
        )
        target_values = target_rankings[target_key]
        source_tie = len(source_values) > 1 and source_values[1][0] >= threshold and abs(source_values[0][0] - source_values[1][0]) <= ambiguity_margin
        target_tie = len(target_values) > 1 and target_values[1][0] >= threshold and abs(target_values[0][0] - target_values[1][0]) <= ambiguity_margin
        ambiguous = source_tie or target_tie
        source = remaining_source[source_key]
        result.append(SubshapeCorrespondence(
            source_id=source_key,
            target_id=target_key,
            kind=kind(source),
            status=CorrespondenceStatus.AMBIGUOUS if ambiguous else CorrespondenceStatus.MATCHED,
            method=CorrespondenceMethod.AMBIGUOUS if ambiguous else CorrespondenceMethod.GEOMETRIC,
            confidence=score,
            score=score,
            reasons=(*reasons, *(('multiple_equivalent_candidates',) if ambiguous else ('global_minimum_cost_assignment',))),
        ))
        handled_sources.add(source_key)
        used_targets.add(target_key)

    for source_key in source_keys:
        if source_key in handled_sources:
            continue
        source = remaining_source[source_key]
        result.append(SubshapeCorrespondence(
            source_id=source_key,
            target_id=None,
            kind=kind(source),
            status=CorrespondenceStatus.UNMATCHED,
            method=CorrespondenceMethod.UNMATCHED,
            confidence=0.0,
            score=0.0,
            reasons=("no_globally_assigned_candidate_above_threshold",),
        ))
    for target_key in target_keys:
        if target_key in used_targets:
            continue
        target = remaining_target[target_key]
        result.append(SubshapeCorrespondence(
            source_id=None,
            target_id=target_key,
            kind=kind(target),
            status=CorrespondenceStatus.UNMATCHED,
            method=CorrespondenceMethod.UNMATCHED,
            confidence=0.0,
            score=0.0,
            reasons=("target_has_no_source_match",),
        ))
    return tuple(sorted(result, key=lambda item: (item.kind, item.source_id or "~", item.target_id or "~")))


def build_correspondence(
    source: ExactPartSnapshot,
    target: ExactPartSnapshot,
    *,
    relation: CompareRelation = CompareRelation.REVISION,
    threshold: float = 0.82,
    ambiguity_margin: float = 0.015,
) -> CorrespondenceReport:
    if not 0.0 < threshold <= 1.0:
        raise ValueError("Correspondence threshold moet 0..1 zijn")
    if ambiguity_margin < 0:
        raise ValueError("ambiguity_margin mag niet negatief zijn")

    subshapes = _match_records(
        source.subshapes,
        target.subshapes,
        source_id=lambda item: item.stable_id,
        target_id=lambda item: item.stable_id,
        kind=lambda item: item.kind.value,
        signature=lambda item: item.signature_hash,
        scorer=lambda a, b: _subshape_score(a, b, source, target),
        threshold=threshold,
        ambiguity_margin=ambiguity_margin,
    )
    features = _match_records(
        source.features,
        target.features,
        source_id=lambda item: item.feature_id,
        target_id=lambda item: item.feature_id,
        kind=lambda item: item.feature_type,
        signature=lambda item: "|".join([
            item.feature_type,
            str(round(item.center.x, 6)),
            str(round(item.center.y, 6)),
            str(round(item.center.z, 6)),
            str(None if item.radius is None else round(item.radius, 6)),
            str(None if item.diameter is None else round(item.diameter, 6)),
            str(None if item.depth is None else round(item.depth, 6)),
        ]),
        scorer=lambda a, b: _feature_score(a, b, source, target),
        threshold=max(0.74, threshold - 0.06),
        ambiguity_margin=ambiguity_margin,
    )
    blocking: list[str] = []
    if any(item.status == CorrespondenceStatus.AMBIGUOUS for item in (*subshapes, *features)):
        blocking.append("CWS-V7-CORRESPONDENCE-AMBIGUOUS")
    if any(item.status == CorrespondenceStatus.UNMATCHED for item in features):
        blocking.append("CWS-V7-FEATURE-CORRESPONDENCE-INCOMPLETE")
    return CorrespondenceReport(
        relation=relation,
        source_geometry_hash=source.exact_geometry_hash,
        target_geometry_hash=target.exact_geometry_hash,
        subshapes=subshapes,
        features=features,
        blocking_codes=tuple(blocking),
    )


__all__ = ["build_correspondence"]
