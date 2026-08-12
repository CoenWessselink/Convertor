"""Dependency-light ISO-10303-21 entity graph utilities.

The complete-model importers need more than the v0.6 count-only scanner, but
CWS Convertor must also remain usable when optional vendor libraries such as
IfcOpenShell are unavailable.  This module loads a Part 21 file as a lazy
entity graph.  Arguments are parsed only when requested, so a large Tekla IFC
can be inspected without first materialising every nested value.

The graph is intentionally format-neutral and is used by both the IFC and STEP
semantic importers.  It never turns tessellated geometry into production
features; it only preserves source semantics, relations and deterministic
source-subgraph fingerprints.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from cws_convertor.project.baseline import (
    iter_p21_statements,
    parse_p21_value,
    split_p21_args,
)

_ENTITY_RE = re.compile(
    r"^\s*#(\d+)\s*=\s*([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*$",
    re.I | re.S,
)
_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\((.*)\)\s*\)", re.I | re.S)
_STRING_RE = re.compile(r"'((?:''|[^'])*)'")


class P21ParseError(ValueError):
    """Raised when a Part 21 source cannot be represented safely."""


# Backward-compatible name used by the early importer prototype.
P21Error = P21ParseError


def _unescape(value: str) -> str:
    return value.replace("''", "'")


def _normalise_scalar(value: Any) -> Any:
    if isinstance(value, float):
        # Stable textual representation without changing engineering values.
        rounded = round(value, 12)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, Mapping):
        if set(value) == {"ref"}:
            return {"ref": int(value["ref"])}
        return {
            str(key): _normalise_scalar(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalise_scalar(item) for item in value]
    return value


def iter_value_refs(value: Any) -> Iterator[int]:
    """Yield all entity references contained in a parsed Part 21 value."""

    if isinstance(value, Mapping):
        if set(value) == {"ref"}:
            try:
                yield int(value["ref"])
            except (TypeError, ValueError):
                return
            return
        for item in value.values():
            yield from iter_value_refs(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_value_refs(item)


def scalar_value(value: Any) -> Any:
    """Unwrap nested STEP/IFC typed values while preserving lists."""

    current = value
    while isinstance(current, Mapping) and "type" in current and "value" in current:
        current = current["value"]
    if isinstance(current, list):
        return [scalar_value(item) for item in current]
    return current


@dataclass(slots=True)
class P21Entity:
    entity_id: int
    type_name: str
    raw_args: str
    _tokens: tuple[str, ...] | None = None
    _values: tuple[Any, ...] | None = None
    _references: tuple[int, ...] | None = None

    @property
    def tokens(self) -> tuple[str, ...]:
        if self._tokens is None:
            self._tokens = tuple(split_p21_args(self.raw_args))
        return self._tokens

    @property
    def values(self) -> tuple[Any, ...]:
        if self._values is None:
            self._values = tuple(parse_p21_value(token) for token in self.tokens)
        return self._values

    @property
    def references(self) -> tuple[int, ...]:
        if self._references is None:
            refs: list[int] = []
            for value in self.values:
                refs.extend(iter_value_refs(value))
            self._references = tuple(refs)
        return self._references

    def value(self, index: int, default: Any = None) -> Any:
        try:
            return self.values[index]
        except IndexError:
            return default

    def scalar(self, index: int, default: Any = None) -> Any:
        value = self.value(index, default)
        if value is default:
            return default
        result = scalar_value(value)
        return default if result is None else result

    def string(self, index: int, default: str = "") -> str:
        value = self.scalar(index, None)
        return default if value is None else str(value)

    def number(self, index: int, default: float | None = None) -> float | None:
        value = self.scalar(index, None)
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def ref(self, index: int) -> int | None:
        value = self.value(index)
        if isinstance(value, Mapping) and set(value) == {"ref"}:
            try:
                return int(value["ref"])
            except (TypeError, ValueError):
                return None
        return None

    def refs(self, index: int) -> list[int]:
        value = self.value(index)
        return list(iter_value_refs(value))

    # Compatibility API shared by both semantic importers.
    @property
    def args(self) -> tuple[str, ...]:
        return self.tokens

    @property
    def parsed_args(self) -> tuple[Any, ...]:
        return self.values

    def arg(self, index: int, default: Any = None) -> Any:
        return self.value(index, default)

    def raw_arg(self, index: int, default: str = "") -> str:
        try:
            return self.tokens[index]
        except IndexError:
            return default

    def direct_refs(self) -> tuple[int, ...]:
        return self.references


class P21Document:
    """Lazy in-memory view of an ISO-10303-21 file."""

    def __init__(
        self,
        *,
        path: Path,
        entities: dict[int, P21Entity],
        by_type: dict[str, tuple[int, ...]],
        schema: str = "",
        header: dict[str, Any] | None = None,
    ) -> None:
        self.path = path
        self.entities = entities
        self.by_type = by_type
        self.schema = schema
        self.header = dict(header or {})
        self._semantic_hash_cache: dict[tuple[int, tuple[str, ...]], str] = {}

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        cancel_check: Callable[[], None] | None = None,
    ) -> "P21Document":
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise P21ParseError(f"Part 21-bestand bestaat niet: {source}")
        entities: dict[int, P21Entity] = {}
        type_ids: dict[str, list[int]] = defaultdict(list)
        schema = ""
        header: dict[str, Any] = {}
        for statement_number, statement in enumerate(iter_p21_statements(source), start=1):
            # Part 21 parsing is streaming, but a large IFC may still contain
            # tens of thousands of statements.  Give GUI/API jobs a bounded
            # cooperative cancellation point without changing parser output.
            if cancel_check is not None and statement_number % 500 == 0:
                cancel_check()
            upper = statement.lstrip().upper()
            if upper.startswith("FILE_SCHEMA"):
                match = _SCHEMA_RE.search(statement)
                if match:
                    schema = ", ".join(
                        _unescape(item) for item in _STRING_RE.findall(match.group(1))
                    )
                continue
            if upper.startswith("FILE_NAME"):
                # Keep the raw header statement for forensic output.  The
                # count-only baseline scanner already exposes parsed fields.
                header["file_name_statement"] = statement
                continue
            match = _ENTITY_RE.match(statement)
            if not match:
                continue
            entity_id = int(match.group(1))
            if entity_id in entities:
                raise P21ParseError(f"Dubbele Part 21 entity-ID #{entity_id}")
            type_name = match.group(2).upper()
            entity = P21Entity(entity_id, type_name, match.group(3))
            entities[entity_id] = entity
            type_ids[type_name].append(entity_id)
        if cancel_check is not None:
            cancel_check()
        if not entities:
            raise P21ParseError(f"Geen Part 21-entiteiten gevonden in {source.name}")
        return cls(
            path=source,
            entities=entities,
            by_type={key: tuple(values) for key, values in type_ids.items()},
            schema=schema,
            header=header,
        )

    def get(self, entity_id: int | None) -> P21Entity | None:
        if entity_id is None:
            return None
        return self.entities.get(int(entity_id))

    def require(self, entity_id: int) -> P21Entity:
        entity = self.get(entity_id)
        if entity is None:
            raise P21ParseError(f"Ontbrekende Part 21-referentie #{entity_id}")
        return entity

    def ids_of_type(self, *type_names: str) -> tuple[int, ...]:
        result: list[int] = []
        for type_name in type_names:
            result.extend(self.by_type.get(type_name.upper(), ()))
        return tuple(result)

    def iter_type(self, *type_names: str) -> Iterator[P21Entity]:
        for entity_id in self.ids_of_type(*type_names):
            yield self.entities[entity_id]

    @property
    def type_index(self) -> dict[str, tuple[int, ...]]:
        return self.by_type

    def ids(self, type_name: str) -> tuple[int, ...]:
        return self.ids_of_type(type_name)

    def arg_ref(self, entity: P21Entity | int, index: int) -> int | None:
        actual = self.require(entity) if isinstance(entity, int) else entity
        return actual.ref(index)

    def arg_refs(self, entity: P21Entity | int, index: int) -> list[int]:
        actual = self.require(entity) if isinstance(entity, int) else entity
        return actual.refs(index)

    def scalar(self, entity: P21Entity | int, index: int, default: Any = None) -> Any:
        actual = self.require(entity) if isinstance(entity, int) else entity
        return actual.scalar(index, default)

    def text(self, entity: P21Entity | int, index: int, default: str = "") -> str:
        actual = self.require(entity) if isinstance(entity, int) else entity
        return actual.string(index, default)

    def number(
        self,
        entity: P21Entity | int,
        index: int,
        default: float | None = None,
    ) -> float | None:
        actual = self.require(entity) if isinstance(entity, int) else entity
        return actual.number(index, default)

    def counts(self) -> dict[str, int]:
        return {key: len(value) for key, value in sorted(self.by_type.items())}

    def collect_graph(
        self,
        roots: Iterable[int],
        *,
        ignore_types: Iterable[str] = (),
        max_entities: int = 250_000,
    ) -> set[int]:
        return self.reachable_ids(
            roots,
            stop_types=ignore_types,
            max_nodes=max_entities,
        )

    def reachable_ids(
        self,
        roots: Iterable[int],
        *,
        stop_types: Iterable[str] = (),
        max_nodes: int = 250_000,
    ) -> set[int]:
        stops = {item.upper() for item in stop_types}
        todo = [int(item) for item in roots]
        visited: set[int] = set()
        while todo:
            entity_id = todo.pop()
            if entity_id in visited:
                continue
            entity = self.get(entity_id)
            if entity is None:
                continue
            visited.add(entity_id)
            if len(visited) > max_nodes:
                raise P21ParseError("Part 21-subgrafiek overschrijdt de veiligheidslimiet")
            if entity.type_name in stops:
                continue
            todo.extend(ref for ref in entity.references if ref not in visited)
        return visited

    def semantic_hash(
        self,
        entity_id: int,
        *,
        ignore_types: Iterable[str] = (),
        ignore_argument_indexes: Mapping[str, Sequence[int]] | None = None,
        precision: int = 9,
        _memo: dict[int, str] | None = None,
        _stack: set[int] | None = None,
    ) -> str:
        """Return an ID-independent Merkle hash of one referenced subgraph.

        Numeric entity IDs are replaced by the semantic hash of their target.
        Presentation-only entity classes and selected volatile arguments can be
        ignored.  Cycles are represented by entity type, never by source ID.
        """

        ignored = tuple(sorted({item.upper() for item in ignore_types}))
        ignored_indexes = {
            str(key).upper(): tuple(sorted(int(index) for index in values))
            for key, values in dict(ignore_argument_indexes or {}).items()
        }
        cache_signature = json.dumps(
            {"types": ignored, "indexes": ignored_indexes, "precision": int(precision)},
            sort_keys=True,
            separators=(",", ":"),
        )
        key = (int(entity_id), (cache_signature,))
        if _memo is None:
            cached = self._semantic_hash_cache.get(key)
            if cached:
                return cached
        ignore_set = set(ignored)
        memo = _memo if _memo is not None else {}
        active = _stack if _stack is not None else set()

        def normalise(value: Any) -> Any:
            if isinstance(value, Mapping):
                if set(value) == {"ref"}:
                    ref_id = int(value["ref"])
                    target = self.get(ref_id)
                    if target is None:
                        return {"missing_ref": True}
                    if target.type_name in ignore_set:
                        return {"ignored_type": target.type_name}
                    return {"ref_hash": visit(ref_id)}
                return {
                    str(name): normalise(item)
                    for name, item in sorted(value.items(), key=lambda pair: str(pair[0]))
                }
            if isinstance(value, (list, tuple)):
                return [normalise(item) for item in value]
            if isinstance(value, float):
                rounded = round(value, int(precision))
                return 0.0 if rounded == 0.0 else rounded
            return _normalise_scalar(value)

        def visit(current_id: int) -> str:
            if current_id in memo:
                return memo[current_id]
            entity = self.get(current_id)
            if entity is None:
                return hashlib.sha256(b"missing").hexdigest()
            if current_id in active:
                payload = {"cycle_type": entity.type_name}
                return hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
            active.add(current_id)
            skip = set(ignored_indexes.get(entity.type_name, ()))
            payload = {
                "type": entity.type_name,
                "args": [
                    normalise(value)
                    for index, value in enumerate(entity.values)
                    if index not in skip
                ],
            }
            digest = hashlib.sha256(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            active.remove(current_id)
            memo[current_id] = digest
            return digest

        digest = visit(int(entity_id))
        if _memo is None:
            self._semantic_hash_cache[key] = digest
        return digest

    def semantic_entity_hash(
        self,
        entity_id: int,
        **kwargs: Any,
    ) -> str:
        return self.semantic_hash(entity_id, **kwargs)

    def release_caches(self) -> None:
        """Drop parsed argument/hash caches after one import phase.

        Large Tekla IFC and AP242 files can contain more than one hundred
        thousand entities.  Parsed values are useful during import, but keeping
        them alive after the canonical project entities have been materialised
        would unnecessarily multiply memory use when the next source is read.
        """

        for entity in self.entities.values():
            entity._tokens = None
            entity._values = None
            entity._references = None
        self._semantic_hash_cache.clear()

    def combined_semantic_hash(
        self,
        entity_ids: Sequence[int],
        *,
        ignore_types: Iterable[str] = (),
        ignore_argument_indexes: Mapping[str, Sequence[int]] | None = None,
        precision: int = 9,
        order_independent: bool = False,
    ) -> str:
        memo: dict[int, str] = {}
        digests = [
            self.semantic_hash(
                entity_id,
                ignore_types=ignore_types,
                ignore_argument_indexes=ignore_argument_indexes,
                precision=precision,
                _memo=memo,
                _stack=set(),
            )
            for entity_id in entity_ids
        ]
        if order_independent:
            digests.sort()
        payload = json.dumps(digests, separators=(",", ":")).encode("ascii")
        return hashlib.sha256(payload).hexdigest()


__all__ = [
    "P21Document",
    "P21Entity",
    "P21Error",
    "P21ParseError",
    "iter_value_refs",
    "scalar_value",
]
