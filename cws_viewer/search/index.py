"""Fast, deterministic text/tag index over a ProjectScene and project properties.

Exact field matches deliberately outrank substring matches.  This prevents a
query such as ``LO4`` from returning assembly mark ``MLO4`` before the actual
part position ``LO4`` while retaining broad free-text search.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from cws_viewer.contracts.scene import ProjectScene

_TOKEN_RE = re.compile(r"[\w./*+-]+", re.UNICODE)


def _normalise(value: object) -> str:
    return str(value or "").strip().casefold()


def _tokens(value: object) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(_normalise(value)))


@dataclass(frozen=True, slots=True)
class SearchHit:
    node_id: str
    entity_id: str
    name: str
    score: int
    matched_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _SearchEntry:
    node: Any
    text: str
    fields: tuple[str, ...]
    field_tokens: frozenset[str]


class ViewerSearchIndex:
    """Search index with stable and explainable result ranking."""

    _ENTITY_FIELDS = (
        "part_position",
        "assembly_mark",
        "name",
        "profile",
        "normalized_profile",
        "material",
        "normalized_material",
        "classification_status",
        "export_status",
        "phase",
        "source_entity_id",
        "global_id",
        "tag",
    )

    def __init__(self, scene: ProjectScene, project: Any | None = None) -> None:
        self.scene = scene
        self._entries: list[_SearchEntry] = []
        entity_map: dict[str, Any] = {}
        if project is not None:
            for collection_name in (
                "assemblies",
                "parts",
                "purchased_items",
                "fasteners",
                "welds",
            ):
                entity_map.update(getattr(project, collection_name, {}) or {})

        for node in scene.nodes:
            entity = entity_map.get(node.entity_id)
            raw_fields: list[object] = [
                node.name,
                node.entity_id,
                node.source_entity_id or "",
                node.kind.value,
                *node.tags,
            ]
            if entity is not None:
                raw_fields.extend(
                    getattr(entity, key, "") for key in self._ENTITY_FIELDS
                )
            fields = tuple(value for value in map(_normalise, raw_fields) if value)
            text = " ".join(fields)
            field_tokens = frozenset(
                token for field in fields for token in _tokens(field)
            )
            self._entries.append(
                _SearchEntry(
                    node=node,
                    text=text,
                    fields=fields,
                    field_tokens=field_tokens,
                )
            )

    @staticmethod
    def _token_score(entry: _SearchEntry, token: str) -> int:
        """Return a deterministic relevance score for one query token."""
        if token in entry.fields:
            return 120
        if token in entry.field_tokens:
            return 90
        if any(field.startswith(token) for field in entry.fields):
            return 55
        if any(part.startswith(token) for part in entry.field_tokens):
            return 35
        if token in entry.text:
            return 12
        return 0

    def search(self, query: str, *, limit: int = 200) -> tuple[SearchHit, ...]:
        query_tokens = tuple(dict.fromkeys(_tokens(query)))
        if not query_tokens:
            return ()

        hits: list[SearchHit] = []
        for entry in self._entries:
            scores = tuple(self._token_score(entry, token) for token in query_tokens)
            if any(score <= 0 for score in scores):
                continue
            node = entry.node
            score = sum(scores)
            if node.selectable:
                score += 2
            if node.geometry_id:
                score += 3
            # Exact part/assembly identity fields should be preferred over generic
            # names/tags when all other relevance is equal.
            if node.kind.value in {"part", "purchased_item"}:
                score += 1
            hits.append(
                SearchHit(
                    node_id=node.node_id,
                    entity_id=node.entity_id,
                    name=node.name,
                    score=score,
                    matched_tokens=query_tokens,
                )
            )

        return tuple(
            sorted(
                hits,
                key=lambda hit: (
                    -hit.score,
                    hit.name.casefold(),
                    hit.node_id,
                ),
            )[: max(0, int(limit))]
        )


__all__ = ["SearchHit", "ViewerSearchIndex"]
