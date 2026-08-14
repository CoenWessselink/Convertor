"""Deterministic professional color schemes for project viewing."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Iterable

from cws_viewer.contracts.enums import ColorScheme, NodeKind
from cws_viewer.contracts.state import ColorAssignment
from cws_viewer.core.scene_index import SceneIndex
from cws_viewer.math3d import Rgba


_CATEGORY_COLORS: dict[NodeKind, Rgba] = {
    NodeKind.PART: Rgba(0.31, 0.62, 0.87, 1.0),
    NodeKind.PURCHASED_ITEM: Rgba(0.47, 0.73, 0.46, 1.0),
    NodeKind.FASTENER: Rgba(0.95, 0.70, 0.22, 1.0),
    NodeKind.WELD: Rgba(0.91, 0.35, 0.43, 1.0),
    NodeKind.REFERENCE: Rgba(0.53, 0.58, 0.64, 0.72),
    NodeKind.ASSEMBLY: Rgba(0.28, 0.51, 0.84, 1.0),
    NodeKind.FEATURE: Rgba(0.25, 0.82, 0.65, 1.0),
}

_PALETTE = (
    Rgba(0.20, 0.56, 0.83), Rgba(0.31, 0.72, 0.49), Rgba(0.94, 0.61, 0.20),
    Rgba(0.83, 0.35, 0.47), Rgba(0.53, 0.43, 0.82), Rgba(0.17, 0.70, 0.73),
    Rgba(0.78, 0.55, 0.26), Rgba(0.41, 0.66, 0.25), Rgba(0.85, 0.42, 0.24),
    Rgba(0.40, 0.48, 0.82), Rgba(0.72, 0.31, 0.69), Rgba(0.20, 0.69, 0.58),
    Rgba(0.64, 0.50, 0.34), Rgba(0.55, 0.66, 0.80), Rgba(0.78, 0.40, 0.57),
    Rgba(0.47, 0.75, 0.78), Rgba(0.62, 0.72, 0.35), Rgba(0.88, 0.52, 0.37),
)

_STATUS_COLORS = {
    "ready": Rgba(0.20, 0.72, 0.45),
    "validated": Rgba(0.20, 0.72, 0.45),
    "approved": Rgba(0.20, 0.72, 0.45),
    "pass": Rgba(0.20, 0.72, 0.45),
    "review": Rgba(0.95, 0.63, 0.18),
    "warning": Rgba(0.95, 0.63, 0.18),
    "partial": Rgba(0.95, 0.63, 0.18),
    "blocked": Rgba(0.90, 0.28, 0.31),
    "failed": Rgba(0.90, 0.28, 0.31),
    "error": Rgba(0.90, 0.28, 0.31),
    "unknown": Rgba(0.54, 0.59, 0.65),
}


def _stable_color(value: str) -> Rgba:
    digest = hashlib.sha256(value.casefold().encode("utf-8", "surrogatepass")).digest()
    return _PALETTE[int.from_bytes(digest[:4], "big") % len(_PALETTE)]


def _entity(project: Any, entity_id: str) -> Any | None:
    if hasattr(project, "get_entity"):
        value = project.get_entity(entity_id)
        if value is not None:
            return value
    for collection in ("assemblies", "parts", "purchased_items", "fasteners", "welds"):
        value = (getattr(project, collection, {}) or {}).get(entity_id)
        if value is not None:
            return value
    return None


def _source_model(entity: Any) -> str:
    identity = getattr(entity, "source_identity", None)
    return str(getattr(identity, "source_file_id", "") or "unknown-source")


def _assembly_key(entity: Any, index: SceneIndex, node_id: str) -> str:
    direct = str(getattr(entity, "assembly_mark", "") or "").strip()
    identity = getattr(entity, "source_identity", None)
    direct = direct or str(getattr(identity, "assembly_mark", "") or "").strip()
    if direct:
        return direct
    for ancestor in index.ancestors(node_id):
        node = index.node(ancestor)
        if node.kind == NodeKind.ASSEMBLY:
            return node.name or node.entity_id
    ids = tuple(getattr(entity, "assembly_ids", ()) or ())
    return ids[0] if ids else "unassigned"


def _status_key(entity: Any) -> str:
    candidates = (
        getattr(entity, "export_status", ""),
        getattr(entity, "classification_status", ""),
        getattr(entity, "status", ""),
    )
    text = " ".join(str(item or "").casefold() for item in candidates)
    for key in _STATUS_COLORS:
        if key in text:
            return key
    issues = tuple(getattr(entity, "validation_issues", ()) or ())
    if issues:
        if any("error" in str(getattr(item, "severity", item)).casefold() for item in issues):
            return "failed"
        return "warning"
    return "unknown"


@dataclass(frozen=True, slots=True)
class ColorLegendItem:
    key: str
    label: str
    color: Rgba
    count: int


class ProjectColorizer:
    """Create deterministic node color assignments without mutating project data."""

    def __init__(self, project: Any, index: SceneIndex) -> None:
        self.project = project
        self.index = index

    def assignments(self, scheme: ColorScheme) -> tuple[ColorAssignment, ...]:
        requested = ColorScheme(scheme)
        if requested == ColorScheme.ORIGINAL:
            return ()
        result: list[ColorAssignment] = []
        for node_id in self.index.renderable_node_ids:
            node = self.index.node(node_id)
            entity = _entity(self.project, node.entity_id)
            color: Rgba
            if requested == ColorScheme.MONOCHROME:
                color = Rgba(0.62, 0.68, 0.74, 1.0)
            elif requested == ColorScheme.CATEGORY:
                color = _CATEGORY_COLORS.get(node.kind, Rgba(0.55, 0.61, 0.67, 1.0))
            elif entity is None:
                color = Rgba(0.55, 0.61, 0.67, 1.0)
            elif requested == ColorScheme.MATERIAL:
                key = str(
                    getattr(entity, "normalized_material", "")
                    or getattr(entity, "material", "")
                    or "unknown-material"
                )
                color = _stable_color(key)
            elif requested == ColorScheme.PROFILE:
                key = str(
                    getattr(entity, "normalized_profile", "")
                    or getattr(entity, "profile", "")
                    or "unknown-profile"
                )
                color = _stable_color(key)
            elif requested == ColorScheme.STATUS:
                color = _STATUS_COLORS[_status_key(entity)]
            elif requested == ColorScheme.PHASE:
                properties = getattr(entity, "properties", {}) or {}
                key = str(
                    properties.get("Phase")
                    or properties.get("phase")
                    or getattr(entity, "phase", "")
                    or "unknown-phase"
                )
                color = _stable_color(key)
            elif requested == ColorScheme.SOURCE_MODEL:
                color = _stable_color(_source_model(entity))
            elif requested == ColorScheme.ASSEMBLY:
                color = _stable_color(_assembly_key(entity, self.index, node_id))
            else:
                color = Rgba(0.55, 0.61, 0.67, 1.0)
            result.append(ColorAssignment(node_id=node_id, color=color))
        return tuple(result)

    def legend(self, scheme: ColorScheme, *, limit: int = 30) -> tuple[ColorLegendItem, ...]:
        requested = ColorScheme(scheme)
        if requested == ColorScheme.ORIGINAL:
            return ()
        groups: dict[tuple[str, Rgba], int] = {}
        for assignment in self.assignments(requested):
            node = self.index.node(assignment.node_id)
            entity = _entity(self.project, node.entity_id)
            if requested == ColorScheme.CATEGORY:
                key = label = node.kind.value
            elif requested == ColorScheme.MONOCHROME:
                key = label = "Alle objecten"
            elif entity is None:
                key = label = "Onbekend"
            elif requested == ColorScheme.MATERIAL:
                key = label = str(getattr(entity, "normalized_material", "") or getattr(entity, "material", "") or "Onbekend")
            elif requested == ColorScheme.PROFILE:
                key = label = str(getattr(entity, "normalized_profile", "") or getattr(entity, "profile", "") or "Onbekend")
            elif requested == ColorScheme.STATUS:
                key = label = _status_key(entity)
            elif requested == ColorScheme.PHASE:
                props = getattr(entity, "properties", {}) or {}
                key = label = str(props.get("Phase") or props.get("phase") or getattr(entity, "phase", "") or "Onbekend")
            elif requested == ColorScheme.SOURCE_MODEL:
                key = label = _source_model(entity)
            else:
                key = label = _assembly_key(entity, self.index, assignment.node_id)
            groups[(key, assignment.color)] = groups.get((key, assignment.color), 0) + 1
        values = [ColorLegendItem(key, key, color, count) for (key, color), count in groups.items()]
        return tuple(sorted(values, key=lambda item: (-item.count, item.label.casefold()))[: max(1, int(limit))])


__all__ = ["ProjectColorizer", "ColorLegendItem"]
