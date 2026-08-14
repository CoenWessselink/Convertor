"""Revision-aware revalidation of exact scribing proposals."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Mapping

from cws_viewer.exact.model import ExactPartRuntime
from cws_viewer.exact.scribing import (
    ScribeProposal,
    ScribeProposalRuntime,
    ScribeStatus,
    ScribingReviewService,
    propose_contact_lines,
)
from cws_viewer.math3d import Vector3


class ScribeRevalidationStatus(StrEnum):
    PRESERVED = "preserved"
    INVALIDATED = "invalidated"
    ADDED = "added"


@dataclass(frozen=True, slots=True)
class ScribeRevalidationItem:
    old_proposal_id: str | None
    new_proposal_id: str | None
    status: ScribeRevalidationStatus
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", ScribeRevalidationStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_proposal_id": self.old_proposal_id,
            "new_proposal_id": self.new_proposal_id,
            "status": self.status.value,
            "reason": self.reason,
        }


@dataclass(slots=True)
class ScribeRevalidationResult:
    service: ScribingReviewService
    items: tuple[ScribeRevalidationItem, ...]
    blocking_codes: tuple[str, ...]

    @property
    def preserved_count(self) -> int:
        return sum(item.status == ScribeRevalidationStatus.PRESERVED for item in self.items)

    @property
    def invalidated_count(self) -> int:
        return sum(item.status == ScribeRevalidationStatus.INVALIDATED for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-scribe-revalidation-1.0",
            "items": [item.to_dict() for item in self.items],
            "blocking_codes": list(self.blocking_codes),
            "preserved_count": self.preserved_count,
            "invalidated_count": self.invalidated_count,
            "new_review": self.service.payload(),
        }


def _vec(value: Any) -> Vector3:
    if isinstance(value, Vector3):
        return value
    return Vector3.from_iterable(value)


def _curve_distance(old: Mapping[str, Any], new: ScribeProposal) -> float:
    old_start, old_end = _vec(old["start"]), _vec(old["end"])
    direct = (old_start - new.start).length() + (old_end - new.end).length()
    reverse = (old_start - new.end).length() + (old_end - new.start).length()
    length_delta = abs(float(old.get("length_mm", 0.0)) - new.length_mm)
    type_penalty = 1e6 if str(old.get("geometry_type", "")).upper() != new.geometry_type.upper() else 0.0
    return min(direct, reverse) + length_delta + type_penalty


def revalidate_scribing_review(
    old_payload: Mapping[str, Any],
    new_target: ExactPartRuntime,
    new_partner: ExactPartRuntime,
    *,
    tolerance_mm: float = 0.02,
) -> ScribeRevalidationResult:
    if tolerance_mm <= 0:
        raise ValueError("Scribe revalidation tolerance moet positief zijn")
    new_runtime = list(propose_contact_lines(new_target, new_partner))
    old_proposals = list(old_payload.get("proposals") or [])
    used_new: set[int] = set()
    result_runtime: list[ScribeProposalRuntime] = []
    items: list[ScribeRevalidationItem] = []
    blocking: list[str] = []

    for old in old_proposals:
        candidates = sorted(
            ((_curve_distance(old, runtime.proposal), index, runtime) for index, runtime in enumerate(new_runtime) if index not in used_new),
            key=lambda item: (item[0], item[1]),
        )
        old_id = str(old.get("proposal_id") or "")
        old_status = ScribeStatus(str(old.get("status", ScribeStatus.PROPOSED.value)))
        if not candidates or candidates[0][0] > tolerance_mm * 4.0:
            items.append(ScribeRevalidationItem(old_id, None, ScribeRevalidationStatus.INVALIDATED, "contact_curve_changed_or_removed"))
            if old_status == ScribeStatus.CONFIRMED:
                blocking.append("CWS-V7-CONFIRMED-SCRIBE-INVALIDATED")
            continue
        if len(candidates) > 1 and abs(candidates[0][0] - candidates[1][0]) <= tolerance_mm * 0.1:
            items.append(ScribeRevalidationItem(old_id, None, ScribeRevalidationStatus.INVALIDATED, "ambiguous_contact_curve_correspondence"))
            blocking.append("CWS-V7-SCRIBE-CORRESPONDENCE-AMBIGUOUS")
            continue
        _distance, index, runtime = candidates[0]
        used_new.add(index)
        proposal = runtime.proposal
        if old_status in {ScribeStatus.CONFIRMED, ScribeStatus.REJECTED}:
            proposal = replace(
                proposal,
                status=old_status,
                reviewer=str(old.get("reviewer") or ""),
                review_reason=str(old.get("review_reason") or ""),
                reviewed_at=str(old.get("reviewed_at") or ""),
            )
        result_runtime.append(ScribeProposalRuntime(proposal, runtime.edge_shape))
        items.append(ScribeRevalidationItem(old_id, proposal.proposal_id, ScribeRevalidationStatus.PRESERVED, "exact_contact_curve_preserved"))

    for index, runtime in enumerate(new_runtime):
        if index in used_new:
            continue
        result_runtime.append(runtime)
        items.append(ScribeRevalidationItem(None, runtime.proposal.proposal_id, ScribeRevalidationStatus.ADDED, "new_contact_curve"))

    service = ScribingReviewService(new_target, new_partner, tuple(result_runtime))
    return ScribeRevalidationResult(service=service, items=tuple(items), blocking_codes=tuple(dict.fromkeys(blocking)))


__all__ = [
    "ScribeRevalidationStatus",
    "ScribeRevalidationItem",
    "ScribeRevalidationResult",
    "revalidate_scribing_review",
]
