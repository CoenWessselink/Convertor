"""Deterministic CWS Model Control records.

The viewer may present model-control evidence but never upgrades approximate
AABB evidence to exact manufacturing truth. Exact metrics must be supplied by
an exact narrow-phase provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any


class ClashCategory(StrEnum):
    HARD = "hard"
    CLEARANCE = "clearance"
    CONTACT = "contact"
    PRODUCTION = "production"
    ASSEMBLY = "assembly"
    MODEL_QUALITY = "model_quality"


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class IssueStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ACTION_REQUIRED = "action_required"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    IGNORED = "ignored"
    REOPENED = "reopened"


class GeometryConfidence(StrEnum):
    VERIFIED = "verified"
    APPROXIMATE = "approximate"
    PROXY = "proxy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ModelControlSettings:
    geometry_tolerance_mm: float = 0.5
    hard_clash_min_penetration_mm: float = 0.5
    contact_tolerance_mm: float = 1.0
    default_clearance_mm: float = 10.0
    max_candidates: int = 250_000


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ClashRecord:
    clash_id: str
    clash_fingerprint: str
    part_a_id: str
    part_b_id: str
    category: str
    severity: str
    status: str = IssueStatus.OPEN.value
    priority: str = "normal"
    project_id: str = ""
    model_id: str = ""
    scan_id: str = ""
    revision_id: str = ""
    revision_status: str = "new"
    assembly_a_id: str = ""
    assembly_b_id: str = ""
    geometry_confidence: str = GeometryConfidence.UNKNOWN.value
    geometry_source: str = ""
    title: str = ""
    description: str = ""
    classification_reason: str = ""
    evidence: str = ""
    rule_id: str = ""
    rule_name: str = ""
    world_location_mm: tuple[float, float, float] | None = None
    intersection_bbox_mm: tuple[float, float, float, float, float, float] | None = None
    intersection_volume_mm3: float | None = None
    minimum_distance_mm: float | None = None
    actual_clearance_mm: float | None = None
    required_clearance_mm: float | None = None
    clearance_delta_mm: float | None = None
    closest_point_a_mm: tuple[float, float, float] | None = None
    closest_point_b_mm: tuple[float, float, float] | None = None
    assigned_to: str = ""
    assigned_role: str = ""
    due_date: str = ""
    resolution_note: str = ""
    accepted_reason: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    comments: list[dict[str, Any]] = field(default_factory=list)
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    viewpoints: list[dict[str, Any]] = field(default_factory=list)
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_comment(self, *, author: str, text: str, attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if not str(author).strip() or not str(text).strip():
            raise ValueError("Clashopmerking vereist auteur en tekst")
        now = utc_now_iso()
        comment = {
            "comment_id": "COM-" + sha256(f"{self.clash_id}|{author}|{now}|{text}".encode("utf-8")).hexdigest()[:12].upper(),
            "author": str(author).strip(),
            "created_at": now,
            "updated_at": now,
            "text": str(text).strip(),
            "edited": False,
            "attachments": list(attachments or []),
        }
        self.comments.append(comment)
        self.updated_at = now
        self.audit_events.append({"event": "comment", "author": comment["author"], "created_at": now, "comment_id": comment["comment_id"]})
        return comment

    def set_status(self, status: IssueStatus | str, *, actor: str, reason: str = "") -> None:
        new_status = IssueStatus(status).value
        if new_status in {IssueStatus.ACCEPTED.value, IssueStatus.IGNORED.value} and not str(reason).strip():
            raise ValueError("Accept/Ignore vereist een reden")
        previous = self.status
        self.status = new_status
        self.touch()
        if new_status == IssueStatus.ACCEPTED.value:
            self.accepted_reason = str(reason).strip()
        if new_status == IssueStatus.RESOLVED.value:
            self.resolution_note = str(reason).strip()
        self.audit_events.append({"event": "status", "actor": str(actor), "from": previous, "to": new_status, "reason": str(reason), "created_at": self.updated_at})

    def assign(self, *, actor: str, user: str = "", role: str = "", due_date: str = "") -> None:
        self.assigned_to = str(user).strip()
        self.assigned_role = str(role).strip()
        self.due_date = str(due_date).strip()
        self.touch()
        self.audit_events.append({"event": "assignment", "actor": str(actor), "assigned_to": self.assigned_to, "assigned_role": self.assigned_role, "due_date": self.due_date, "created_at": self.updated_at})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_fingerprint(part_a_id: str, part_b_id: str, category: str, rule_id: str, region: tuple[float, ...] | None) -> str:
    pair = sorted((str(part_a_id), str(part_b_id)))
    payload = {
        "pair": pair,
        "category": str(category),
        "rule_id": str(rule_id),
        "region": None if region is None else [round(float(v), 1) for v in region],
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def make_clash_id(fingerprint: str) -> str:
    return "CL-" + fingerprint[:10].upper()


__all__ = [
    "ClashCategory", "Severity", "IssueStatus", "GeometryConfidence",
    "ModelControlSettings", "ClashRecord", "stable_fingerprint", "make_clash_id",
]
