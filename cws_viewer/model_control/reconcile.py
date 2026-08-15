"""Revision-safe reconciliation of Model Control scan results."""
from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from .model import ClashRecord, IssueStatus, utc_now_iso


def _pair_key(record: ClashRecord) -> tuple[tuple[str, str], str, str]:
    return (tuple(sorted((record.part_a_id, record.part_b_id))), record.category, record.rule_id)


def _carry_review_state(source: ClashRecord, target: ClashRecord) -> None:
    target.status = source.status
    target.priority = source.priority
    target.assigned_to = source.assigned_to
    target.assigned_role = source.assigned_role
    target.due_date = source.due_date
    target.resolution_note = source.resolution_note
    target.accepted_reason = source.accepted_reason
    target.created_at = source.created_at
    target.comments = deepcopy(source.comments)
    target.screenshots = deepcopy(source.screenshots)
    target.attachments = deepcopy(source.attachments)
    target.viewpoints = deepcopy(source.viewpoints)
    target.audit_events = deepcopy(source.audit_events)


def reconcile_scan(previous: Iterable[ClashRecord], current: Iterable[ClashRecord]) -> tuple[ClashRecord, ...]:
    """Preserve review history and classify NEW/UNCHANGED/CHANGED/RESOLVED.

    A fingerprint match is strongest.  If the spatial fingerprint changed but
    there is exactly one prior record for the same part-pair/category/rule, the
    issue is treated as CHANGED and review history is retained.  Ambiguous
    matches are never guessed.
    """
    old = tuple(previous); fresh = [deepcopy(item) for item in current]
    by_fingerprint = {item.clash_fingerprint: item for item in old}
    by_pair: dict[tuple[tuple[str, str], str, str], list[ClashRecord]] = {}
    for item in old:
        by_pair.setdefault(_pair_key(item), []).append(item)
    matched_old: set[str] = set()
    now = utc_now_iso()
    for item in fresh:
        prior = by_fingerprint.get(item.clash_fingerprint)
        if prior is not None:
            matched_old.add(prior.clash_id)
            _carry_review_state(prior, item)
            item.revision_status = "unchanged"
            item.updated_at = now
            continue
        candidates = [candidate for candidate in by_pair.get(_pair_key(item), ()) if candidate.clash_id not in matched_old]
        if len(candidates) == 1:
            prior = candidates[0]
            matched_old.add(prior.clash_id)
            _carry_review_state(prior, item)
            item.revision_status = "changed"
            item.updated_at = now
            item.audit_events.append({"event": "clash_changed", "previous_clash_id": prior.clash_id, "created_at": now})
        else:
            item.revision_status = "new"
    resolved: list[ClashRecord] = []
    for prior in old:
        if prior.clash_id in matched_old:
            continue
        item = deepcopy(prior)
        item.revision_status = "resolved"
        item.status = IssueStatus.RESOLVED.value
        item.resolution_note = item.resolution_note or "Niet meer aangetroffen in nieuwe modelcontrole"
        item.updated_at = now
        item.audit_events.append({"event": "auto_resolved_on_rescan", "created_at": now})
        resolved.append(item)
    combined = fresh + resolved
    combined.sort(key=lambda r: (r.revision_status == "resolved", r.severity, r.clash_id))
    return tuple(combined)


__all__ = ["reconcile_scan"]
