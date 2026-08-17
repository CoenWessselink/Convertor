"""Source presentation appearance extraction for the CWS Viewer.

This module is deliberately display-only.  It reads presentation/style entities
from the verified source graph and never changes canonical or manufacturing
geometry.  IFC colours are therefore treated as the authoritative *viewer
appearance* when they are present in the source file; CWS category colours are
only a fallback for sources without presentation information.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Iterable

from cws_convertor.importers.p21 import P21Document, P21Entity
from cws_viewer.math3d import Rgba


@dataclass(frozen=True, slots=True)
class SourceAppearance:
    color: Rgba
    provenance: str
    source_style_id: str = ""


def _clamp01(value: float | None, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    return max(0.0, min(1.0, float(value)))


class IfcAppearanceResolver:
    """Resolve IFC2x3/IFC4 surface presentation colours by representation item.

    Tekla and other authoring tools commonly attach ``IfcStyledItem`` records to
    representation items (or a mapped child item).  Geometry hashing correctly
    excludes these style entities; this resolver walks the representation graph
    separately so appearance can be restored without contaminating geometry
    identity.
    """

    _SURFACE_TYPES = {
        "IFCSURFACESTYLERENDERING",
        "IFCSURFACESTYLESHADING",
    }

    def __init__(self, document: P21Document) -> None:
        self.document = document
        self._appearance_by_item: dict[int, tuple[SourceAppearance, ...]] = {}
        self._build_index()

    def _colour(self, entity_id: int | None) -> Rgba | None:
        entity = self.document.get(entity_id)
        if entity is None or entity.type_name != "IFCCOLOURRGB":
            return None
        return Rgba(
            _clamp01(entity.number(1), 0.5),
            _clamp01(entity.number(2), 0.5),
            _clamp01(entity.number(3), 0.5),
            1.0,
        )

    def _styles_from_entity(
        self,
        entity: P21Entity,
        *,
        active: set[int] | None = None,
    ) -> tuple[SourceAppearance, ...]:
        active = set() if active is None else active
        if entity.entity_id in active:
            return ()
        active.add(entity.entity_id)
        try:
            kind = entity.type_name
            if kind == "IFCPRESENTATIONSTYLEASSIGNMENT":
                refs = entity.refs(0)
                return self._styles_from_refs(refs, active=active)
            if kind == "IFCSURFACESTYLE":
                refs = entity.refs(2)
                return self._styles_from_refs(refs, active=active)
            if kind in self._SURFACE_TYPES:
                base = self._colour(entity.ref(0))
                if base is None:
                    return ()
                transparency = (
                    _clamp01(entity.number(1), 0.0)
                    if kind == "IFCSURFACESTYLERENDERING"
                    else 0.0
                )
                color = Rgba(base.red, base.green, base.blue, 1.0 - transparency)
                return (
                    SourceAppearance(
                        color=color,
                        provenance=f"ifc:{kind.casefold()}",
                        source_style_id=f"#{entity.entity_id}",
                    ),
                )
            # Some exports reference the RGB directly through a presentation
            # assignment.  Accept this harmless display form as well.
            if kind == "IFCCOLOURRGB":
                color = self._colour(entity.entity_id)
                if color is not None:
                    return (
                        SourceAppearance(
                            color=color,
                            provenance="ifc:colourrgb",
                            source_style_id=f"#{entity.entity_id}",
                        ),
                    )
            return ()
        finally:
            active.discard(entity.entity_id)

    def _styles_from_refs(
        self,
        refs: Iterable[int],
        *,
        active: set[int] | None = None,
    ) -> tuple[SourceAppearance, ...]:
        result: list[SourceAppearance] = []
        for ref in refs:
            entity = self.document.get(ref)
            if entity is not None:
                result.extend(self._styles_from_entity(entity, active=active))
        return tuple(result)

    def _build_index(self) -> None:
        mapping: dict[int, list[SourceAppearance]] = {}
        for styled in self.document.iter_type("IFCSTYLEDITEM"):
            target = styled.ref(0)
            if target is None:
                continue
            values = self._styles_from_refs(styled.refs(1))
            if values:
                mapping.setdefault(target, []).extend(values)
        self._appearance_by_item = {
            item_id: tuple(values) for item_id, values in mapping.items()
        }

    @staticmethod
    def _key(appearance: SourceAppearance) -> tuple[int, int, int, int]:
        color = appearance.color
        return tuple(
            int(round(max(0.0, min(1.0, value)) * 255.0))
            for value in (color.red, color.green, color.blue, color.alpha)
        )  # type: ignore[return-value]

    def color_for_items(
        self,
        source_item_ids: Iterable[str | int],
        *,
        max_graph_nodes: int = 2048,
    ) -> SourceAppearance | None:
        """Return the deterministic dominant appearance for representation items.

        Mapped IFC geometry can put ``IfcStyledItem`` one or more levels below
        the product's top representation item.  Breadth-first traversal keeps
        near/top-level style assignments preferred while still recovering the
        common mapped-item case.  If several items use the same colour, the
        dominant source colour wins deterministically.
        """
        queue: deque[tuple[int, int]] = deque()
        seen: set[int] = set()
        for raw in source_item_ids:
            try:
                value = int(str(raw).lstrip("#"))
            except (TypeError, ValueError):
                continue
            queue.append((value, 0))

        found: list[tuple[int, SourceAppearance]] = []
        visited = 0
        while queue and visited < max(1, int(max_graph_nodes)):
            entity_id, depth = queue.popleft()
            if entity_id in seen:
                continue
            seen.add(entity_id)
            visited += 1
            for appearance in self._appearance_by_item.get(entity_id, ()):
                found.append((depth, appearance))
            entity = self.document.get(entity_id)
            if entity is None:
                continue
            for ref in entity.references:
                target = self.document.get(ref)
                if target is None:
                    continue
                # Presentation relations themselves are not geometry children;
                # they are already handled through the reverse styled-item map.
                if target.type_name.startswith("IFCSTYLE") or target.type_name in {
                    "IFCCOLOURRGB",
                    "IFCPRESENTATIONSTYLEASSIGNMENT",
                    "IFCSURFACESTYLE",
                    "IFCSURFACESTYLERENDERING",
                    "IFCSURFACESTYLESHADING",
                }:
                    continue
                queue.append((ref, depth + 1))

        if not found:
            return None
        counts = Counter(self._key(item) for _depth, item in found)
        dominant_key, _count = min(
            counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )
        candidates = [
            (depth, item)
            for depth, item in found
            if self._key(item) == dominant_key
        ]
        _depth, chosen = min(
            candidates,
            key=lambda pair: (pair[0], pair[1].source_style_id, pair[1].provenance),
        )
        return chosen


__all__ = ["IfcAppearanceResolver", "SourceAppearance"]
