"""BCF interoperability extension contract.

CWS deliberately does not emit a file labelled BCF until a concrete BCF
version has been validated against the official buildingSMART schema.  This
module keeps CWS review data logically mappable without producing a false or
non-compliant BCF archive.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
from uuid import UUID, uuid5

_NAMESPACE = UUID("3987e7cd-54e0-4be8-a55b-8c03953342d2")


@dataclass(frozen=True, slots=True)
class BcfTopicMapping:
    guid: str
    title: str
    description: str
    status: str
    priority: str
    author: str
    assigned_to: str
    related_entity_ids: tuple[str, ...]
    related_ifc_guids: tuple[str, ...] = ()
    comment_count: int = 0
    viewpoint_count: int = 0
    snapshot_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_review_topic(value: Any, *, project_id: str, ifc_guid_by_entity: dict[str, str] | None = None) -> BcfTopicMapping:
    """Map a CWS clash/review issue to BCF-style topic semantics."""
    if hasattr(value, "part_a_id"):
        entities = tuple(v for v in (str(getattr(value,"part_a_id","")),str(getattr(value,"part_b_id",""))) if v)
        stable = str(getattr(value,"clash_fingerprint","") or getattr(value,"clash_id","") or repr(value))
        title = str(getattr(value,"title","") or getattr(value,"clash_id","Clash"))
        description = str(getattr(value,"description","") or getattr(value,"classification_reason",""))
        author = ""
        comments = list(getattr(value,"comments",[]) or [])
        viewpoints = list(getattr(value,"viewpoints",[]) or [])
        screenshots = list(getattr(value,"screenshots",[]) or [])
    else:
        entities = tuple(str(v) for v in getattr(value,"linked_entity_ids",()) or ())
        stable = str(getattr(value,"issue_id","") or repr(value))
        title = str(getattr(value,"title","") or "Review issue")
        description = str(getattr(value,"description","") or "")
        author = str(getattr(value,"created_by","") or "")
        comments = list(getattr(value,"comments",[]) or [])
        viewpoints = [getattr(value,"viewpoint_id",None)] if getattr(value,"viewpoint_id",None) else []
        screenshots = list(getattr(value,"screenshots",[]) or [])
    mapping = ifc_guid_by_entity or {}
    ifc_guids = tuple(mapping[e] for e in entities if e in mapping and mapping[e])
    guid = str(uuid5(_NAMESPACE, f"{project_id}|{stable}"))
    return BcfTopicMapping(
        guid=guid,
        title=title,
        description=description,
        status=str(getattr(value,"status","open")),
        priority=str(getattr(value,"priority","normal")),
        author=author,
        assigned_to=str(getattr(value,"assigned_to",getattr(value,"assignee","")) or ""),
        related_entity_ids=entities,
        related_ifc_guids=ifc_guids,
        comment_count=len(comments),
        viewpoint_count=len(viewpoints),
        snapshot_count=len(screenshots),
    )


class BcfExportNotCertified(RuntimeError):
    code = "CWS-BCF-EXPORT-NOT-CERTIFIED"


class BcfExporterExtension:
    """Explicit extension point for a future schema-certified exporter."""
    certified_version: str | None = None

    def export(self, *_: Any, **__: Any) -> None:
        raise BcfExportNotCertified(
            "BCF-export is nog niet schema-gecertificeerd; gebruik het portable .cwsreview-pakket."
        )


__all__=["BcfTopicMapping","map_review_topic","BcfExportNotCertified","BcfExporterExtension"]
