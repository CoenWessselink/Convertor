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
from pathlib import Path
from typing import Any, Iterable, Mapping


class MarkupKind(StrEnum):
    TEXT = "text"
    LINE = "line"
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


class ReviewPriority(StrEnum):
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_id(prefix: str, payload: dict[str, Any]) -> str:
    digest = sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MarkupAnchor":
        point = value.get("world_point_mm")
        return cls(
            entity_id=(None if value.get("entity_id") in {None, ""} else str(value.get("entity_id"))),
            node_id=(None if value.get("node_id") in {None, ""} else str(value.get("node_id"))),
            feature_id=(None if value.get("feature_id") in {None, ""} else str(value.get("feature_id"))),
            world_point_mm=(None if point is None else tuple(float(v) for v in point)),
            geometry_hash=(None if value.get("geometry_hash") in {None, ""} else str(value.get("geometry_hash"))),
            evidence=str(value.get("evidence", "viewer")),
        )


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
    def from_dict(cls, value: Mapping[str, Any]) -> "MarkupRecord":
        return cls(
            markup_id=str(value["markup_id"]),
            kind=MarkupKind(str(value.get("kind", MarkupKind.TEXT.value))).value,
            text=str(value.get("text", "")),
            anchors=tuple(MarkupAnchor.from_dict(item) for item in value.get("anchors", ())),
            world_points_mm=tuple(tuple(float(v) for v in point) for point in value.get("world_points_mm", ())),
            color=str(value.get("color", "#0b5bd3")),
            line_width=float(value.get("line_width", 2.0)),
            created_by=str(value.get("created_by", "")),
            created_utc=str(value.get("created_utc", "") or _now()),
            visible=bool(value.get("visible", True)),
            status=str(value.get("status", "active")),
            provenance=str(value.get("provenance", "manual_review")),
        )

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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewComment":
        return cls(
            author=str(value.get("author", "")),
            text=str(value.get("text", "")),
            created_utc=str(value.get("created_utc", "") or _now()),
        )


@dataclass(frozen=True, slots=True)
class ReviewAttachment:
    attachment_id: str
    name: str
    path: str
    sha256: str
    media_type: str = "application/octet-stream"
    size_bytes: int = 0
    added_by: str = ""
    added_utc: str = field(default_factory=_now)

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        added_by: str = "",
        media_type: str = "application/octet-stream",
    ) -> "ReviewAttachment":
        source = Path(path).expanduser().resolve()
        payload = source.read_bytes()
        digest = sha256(payload).hexdigest()
        stable = _stable_id("ATT", {"name": source.name, "sha256": digest})
        return cls(
            attachment_id=stable,
            name=source.name,
            path=str(source),
            sha256=digest,
            media_type=str(media_type or "application/octet-stream"),
            size_bytes=len(payload),
            added_by=str(added_by),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewAttachment":
        return cls(
            attachment_id=str(value["attachment_id"]),
            name=str(value.get("name", "")),
            path=str(value.get("path", "")),
            sha256=str(value.get("sha256", "")),
            media_type=str(value.get("media_type", "application/octet-stream")),
            size_bytes=int(value.get("size_bytes", 0)),
            added_by=str(value.get("added_by", "")),
            added_utc=str(value.get("added_utc", "") or _now()),
        )


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
    priority: str = ReviewPriority.NORMAL.value
    due_date_utc: str | None = None
    tags: tuple[str, ...] = ()
    attachments: list[ReviewAttachment] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        title: str,
        *,
        description: str = "",
        severity: ReviewSeverity | str = ReviewSeverity.INFO,
        priority: ReviewPriority | str = ReviewPriority.NORMAL,
        created_by: str = "",
        linked_entity_ids: Iterable[str] = (),
        linked_clash_ids: Iterable[str] = (),
        markup_ids: Iterable[str] = (),
        viewpoint_id: str | None = None,
        due_date_utc: str | None = None,
        tags: Iterable[str] = (),
    ) -> "ReviewIssue":
        clean_title = str(title).strip()
        if not clean_title:
            raise ValueError("Issue vereist een titel")
        payload = {
            "title": clean_title,
            "description": description,
            "entities": sorted(str(v) for v in linked_entity_ids),
            "clashes": sorted(str(v) for v in linked_clash_ids),
            "markups": sorted(str(v) for v in markup_ids),
            "created_by": created_by,
        }
        return cls(
            issue_id=_stable_id("ISS", payload),
            title=clean_title,
            description=str(description),
            severity=ReviewSeverity(severity).value,
            priority=ReviewPriority(priority).value,
            created_by=str(created_by),
            linked_entity_ids=tuple(dict.fromkeys(str(v) for v in linked_entity_ids if str(v))),
            linked_clash_ids=tuple(dict.fromkeys(str(v) for v in linked_clash_ids if str(v))),
            markup_ids=tuple(dict.fromkeys(str(v) for v in markup_ids if str(v))),
            viewpoint_id=(None if viewpoint_id in {None, ""} else str(viewpoint_id)),
            due_date_utc=(None if due_date_utc in {None, ""} else str(due_date_utc)),
            tags=tuple(dict.fromkeys(str(v).strip() for v in tags if str(v).strip())),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewIssue":
        return cls(
            issue_id=str(value["issue_id"]),
            title=str(value.get("title", "")),
            description=str(value.get("description", "")),
            severity=ReviewSeverity(str(value.get("severity", ReviewSeverity.INFO.value))).value,
            status=ReviewStatus(str(value.get("status", ReviewStatus.OPEN.value))).value,
            assignee=str(value.get("assignee", "")),
            linked_entity_ids=tuple(str(v) for v in value.get("linked_entity_ids", ())),
            linked_clash_ids=tuple(str(v) for v in value.get("linked_clash_ids", ())),
            markup_ids=tuple(str(v) for v in value.get("markup_ids", ())),
            viewpoint_id=(None if value.get("viewpoint_id") in {None, ""} else str(value.get("viewpoint_id"))),
            comments=[ReviewComment.from_dict(item) for item in value.get("comments", ())],
            screenshots=[dict(item) for item in value.get("screenshots", ())],
            created_by=str(value.get("created_by", "")),
            created_utc=str(value.get("created_utc", "") or _now()),
            updated_utc=str(value.get("updated_utc", "") or _now()),
            audit_events=[dict(item) for item in value.get("audit_events", ())],
            priority=ReviewPriority(str(value.get("priority", ReviewPriority.NORMAL.value))).value,
            due_date_utc=(None if value.get("due_date_utc") in {None, ""} else str(value.get("due_date_utc"))),
            tags=tuple(str(v) for v in value.get("tags", ())),
            attachments=[ReviewAttachment.from_dict(item) for item in value.get("attachments", ())],
        )

    def add_comment(self, author: str, text: str) -> ReviewComment:
        if not str(author).strip() or not str(text).strip():
            raise ValueError("Opmerking vereist auteur en tekst")
        comment = ReviewComment(str(author).strip(), str(text).strip())
        self.comments.append(comment)
        self.updated_utc = _now()
        self.audit_events.append(
            {"event": "comment_added", "author": comment.author, "utc": comment.created_utc}
        )
        return comment

    def assign(self, user: str, *, actor: str) -> None:
        self.assignee = str(user).strip()
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "assigned",
                "actor": str(actor),
                "assignee": self.assignee,
                "utc": self.updated_utc,
            }
        )

    def set_status(self, status: ReviewStatus | str, *, actor: str) -> None:
        self.status = ReviewStatus(status).value
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "status_changed",
                "actor": str(actor),
                "status": self.status,
                "utc": self.updated_utc,
            }
        )

    def set_priority(self, priority: ReviewPriority | str, *, actor: str) -> None:
        self.priority = ReviewPriority(priority).value
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "priority_changed",
                "actor": str(actor),
                "priority": self.priority,
                "utc": self.updated_utc,
            }
        )

    def set_due_date(self, due_date_utc: str | None, *, actor: str) -> None:
        self.due_date_utc = None if due_date_utc in {None, ""} else str(due_date_utc)
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "due_date_changed",
                "actor": str(actor),
                "due_date_utc": self.due_date_utc,
                "utc": self.updated_utc,
            }
        )

    def link_viewpoint(self, viewpoint_id: str | None, *, actor: str) -> None:
        self.viewpoint_id = None if viewpoint_id in {None, ""} else str(viewpoint_id)
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "viewpoint_link_changed",
                "actor": str(actor),
                "viewpoint_id": self.viewpoint_id,
                "utc": self.updated_utc,
            }
        )

    def add_attachment(self, attachment: ReviewAttachment, *, actor: str = "") -> None:
        if attachment.attachment_id not in {item.attachment_id for item in self.attachments}:
            self.attachments.append(attachment)
        self.updated_utc = _now()
        self.audit_events.append(
            {
                "event": "attachment_added",
                "actor": str(actor or attachment.added_by),
                "attachment_id": attachment.attachment_id,
                "utc": self.updated_utc,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["comments"] = [c.to_dict() for c in self.comments]
        data["attachments"] = [a.to_dict() for a in self.attachments]
        data["linked_entity_ids"] = list(self.linked_entity_ids)
        data["linked_clash_ids"] = list(self.linked_clash_ids)
        data["markup_ids"] = list(self.markup_ids)
        data["tags"] = list(self.tags)
        return data


__all__ = [
    "MarkupKind",
    "MarkupAnchor",
    "MarkupRecord",
    "ReviewStatus",
    "ReviewSeverity",
    "ReviewPriority",
    "ReviewComment",
    "ReviewAttachment",
    "ReviewIssue",
]
