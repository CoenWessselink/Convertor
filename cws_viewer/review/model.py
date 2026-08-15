"""Non-destructive viewer review/markup contracts.

These records are deliberately separate from Canonical Project Model geometry.
They may reference canonical entity IDs and exact/viewer evidence, but they can
never change manufacturing geometry or release production output.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256
import json
from typing import Any, Iterable


class MarkupKind(StrEnum):
    TEXT = "text"
    ARROW = "arrow"
    CLOUD = "cloud"
    FREEHAND = "freehand"


class ReviewStatus(StrEnum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    ACTION_REQUIRED = "action_required"
    ACCEPTED = "accepted"
    RESOLVED = "resolved"
    REOPENED = "reopened"


class ReviewSeverity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:12].upper()}"


@dataclass(frozen=True, slots=True)
class MarkupAnchor:
    entity_id: str | None = None
    node_id: str | None = None
    feature_id: str | None = None
    world_point_mm: tuple[float, float, float] | None = None
    geometry_hash: str | None = None
    evidence: str = "viewer"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MarkupRecord:
    markup_id: str
    kind: str
    text: str = ""
    anchors: tuple[MarkupAnchor, ...] = ()
    world_points_mm: tuple[tuple[float, float, float], ...] = ()
    color: str = "#0b5bd3"
    line_width: float = 2.0
    created_by: str = ""
    created_utc: str = field(default_factory=_now)
    visible: bool = True
    status: str = "active"
    provenance: str = "manual_review"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["anchors"] = [a.to_dict() for a in self.anchors]
        data["world_points_mm"] = [list(p) for p in self.world_points_mm]
        return data

    @classmethod
    def create(
        cls,
        kind: MarkupKind | str,
        *,
        text: str = "",
        anchors: Iterable[MarkupAnchor] = (),
        world_points_mm: Iterable[tuple[float, float, float]] = (),
        created_by: str = "",
        color: str = "#0b5bd3",
    ) -> "MarkupRecord":
        kind_value = MarkupKind(kind).value
        anchors_tuple = tuple(anchors)
        points_tuple = tuple(tuple(float(v) for v in p) for p in world_points_mm)
        payload = {
            "kind": kind_value,
            "text": text,
            "anchors": [a.to_dict() for a in anchors_tuple],
            "points": points_tuple,
            "created_by": created_by,
        }
        return cls(
            markup_id=_stable_id("MK", payload),
            kind=kind_value,
            text=text,
            anchors=anchors_tuple,
            world_points_mm=points_tuple,
            created_by=created_by,
            color=color,
        )


@dataclass(frozen=True, slots=True)
class ReviewComment:
    author: str
    text: str
    created_utc: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(slots=True)
class ReviewIssue:
    issue_id: str
    title: str
    description: str = ""
    severity: str = ReviewSeverity.INFO.value
    status: str = ReviewStatus.OPEN.value
    assignee: str = ""
    linked_entity_ids: tuple[str, ...] = ()
    linked_clash_ids: tuple[str, ...] = ()
    markup_ids: tuple[str, ...] = ()
    viewpoint_id: str | None = None
    comments: list[ReviewComment] = field(default_factory=list)
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    created_by: str = ""
    created_utc: str = field(default_factory=_now)
    updated_utc: str = field(default_factory=_now)
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        title: str,
        *,
        description: str = "",
        severity: ReviewSeverity | str = ReviewSeverity.INFO,
        created_by: str = "",
        linked_entity_ids: Iterable[str] = (),
        linked_clash_ids: Iterable[str] = (),
        markup_ids: Iterable[str] = (),
    ) -> "ReviewIssue":
        payload = {
            "title": title,
            "description": description,
            "entities": sorted(str(v) for v in linked_entity_ids),
            "clashes": sorted(str(v) for v in linked_clash_ids),
            "markups": sorted(str(v) for v in markup_ids),
            "created_by": created_by,
        }
        return cls(
            issue_id=_stable_id("ISS", payload),
            title=title,
            description=description,
            severity=ReviewSeverity(severity).value,
            created_by=created_by,
            linked_entity_ids=tuple(str(v) for v in linked_entity_ids),
            linked_clash_ids=tuple(str(v) for v in linked_clash_ids),
            markup_ids=tuple(str(v) for v in markup_ids),
        )

    def add_comment(self, author: str, text: str) -> ReviewComment:
        if not str(author).strip() or not str(text).strip():
            raise ValueError("Opmerking vereist auteur en tekst")
        comment = ReviewComment(str(author).strip(), str(text).strip())
        self.comments.append(comment)
        self.updated_utc = _now()
        self.audit_events.append({"event": "comment_added", "author": comment.author, "utc": comment.created_utc})
        return comment

    def assign(self, user: str, *, actor: str) -> None:
        self.assignee = str(user).strip()
        self.updated_utc = _now()
        self.audit_events.append({"event": "assigned", "actor": str(actor), "assignee": self.assignee, "utc": self.updated_utc})

    def set_status(self, status: ReviewStatus | str, *, actor: str) -> None:
        self.status = ReviewStatus(status).value
        self.updated_utc = _now()
        self.audit_events.append({"event": "status_changed", "actor": str(actor), "status": self.status, "utc": self.updated_utc})

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["comments"] = [c.to_dict() for c in self.comments]
        return data


__all__ = [
    "MarkupKind", "MarkupAnchor", "MarkupRecord",
    "ReviewStatus", "ReviewSeverity", "ReviewComment", "ReviewIssue",
]
