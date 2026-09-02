"""Versioned, renderer-neutral production drawing document.

Every preview, PDF and print route consumes this exact model.  Coordinates are
millimetres from the top-left of the sheet; renderers only translate the
coordinate system and never reconstruct drawing semantics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from typing import Any, Mapping, Sequence


DRAWING_DOCUMENT_SCHEMA = "cws.production-drawing-document.v1"
DRAWING_ENGINE_VERSION = "cws-production-drawing-engine-v1"


def _stable_hash(value: Mapping[str, Any]) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(slots=True)
class DrawingPrimitive:
    """One vector primitive on a named production-drawing layer."""

    kind: str
    layer: str
    points: list[list[float]] = field(default_factory=list)
    text: str = ""
    center: list[float] = field(default_factory=list)
    radius: float = 0.0
    width: float = 0.25
    color: str = "#173b5d"
    fill: str = ""
    dash: list[float] = field(default_factory=list)
    font_size: float = 3.0
    bold: bool = False
    rotation: float = 0.0
    refs: list[str] = field(default_factory=list)
    semantic_id: str = ""

    def bounds(self) -> tuple[float, float, float, float] | None:
        if self.kind == "circle" and len(self.center) == 2:
            x, y = (float(value) for value in self.center)
            radius = max(0.0, float(self.radius))
            return x - radius, y - radius, x + radius, y + radius
        if self.kind == "text" and len(self.points) == 1:
            x, y = (float(value) for value in self.points[0])
            width = max(0.8, len(self.text) * self.font_size * 0.52)
            height = max(0.8, self.font_size * 1.18)
            return x, y - height, x + width, y
        if not self.points:
            return None
        xs = [float(point[0]) for point in self.points]
        ys = [float(point[1]) for point in self.points]
        return min(xs), min(ys), max(xs), max(ys)

    def validate(self) -> None:
        if self.kind not in {"line", "polyline", "polygon", "rect", "circle", "text"}:
            raise ValueError(f"Onbekend tekenprimitief {self.kind!r}")
        numbers = [value for point in self.points for value in point]
        numbers.extend(self.center)
        numbers.extend((self.radius, self.width, self.font_size, self.rotation))
        if any(not math.isfinite(float(value)) for value in numbers):
            raise ValueError("Tekenprimitief bevat een niet-eindige waarde")


@dataclass(slots=True)
class DrawingPage:
    number: int
    title: str
    width_mm: float
    height_mm: float
    primitives: list[DrawingPrimitive] = field(default_factory=list)
    view_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.number < 1 or self.width_mm <= 0.0 or self.height_mm <= 0.0:
            raise ValueError("Ongeldige tekenbladconfiguratie")
        for primitive in self.primitives:
            primitive.validate()


@dataclass(slots=True)
class DrawingDocument:
    entity_id: str
    document_type: str
    sheet_format: str
    orientation: str
    unit: str
    scale_denominator: int
    geometry_basis: str
    geometry_sha256: str
    manufacturing_sha256: str
    source_revision: str
    pages: list[DrawingPage]
    title_block: dict[str, Any] = field(default_factory=dict)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    bom: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dimensions: list[dict[str, Any]] = field(default_factory=list)
    dimension_chains: list[dict[str, Any]] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)
    manual_dimensions: list[dict[str, Any]] = field(default_factory=list)
    expected_manufacturing_sha256: str = ""
    hlr_method: str = "mesh_fallback"
    sections_requested: bool = False
    section_method: str = "not_requested"
    canonical_rebuild_current: bool = False
    canonical_payload_current: bool = False
    roundtrip_current: bool = False
    dimension_mode: str = "Hoofdmaten"
    dimensions_enabled: bool = True
    title_block_enabled: bool = True
    lint: dict[str, Any] = field(default_factory=dict)
    visible_content_sha256: str = ""
    schema_version: str = DRAWING_DOCUMENT_SCHEMA
    engine_version: str = DRAWING_ENGINE_VERSION
    document_sha256: str = ""

    def _hash_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload["document_sha256"] = ""
        payload["visible_content_sha256"] = ""
        return payload

    def seal(self) -> str:
        self.document_sha256 = _stable_hash(self._hash_payload())
        return self.document_sha256

    def validate(self) -> None:
        if self.schema_version != DRAWING_DOCUMENT_SCHEMA:
            raise ValueError(f"Niet-ondersteund DrawingDocument-schema {self.schema_version!r}")
        if self.orientation not in {"portrait", "landscape"}:
            raise ValueError("Oriëntatie moet portrait of landscape zijn")
        if self.unit not in {"mm", "cm"}:
            raise ValueError("Eenheid moet mm of cm zijn")
        if self.scale_denominator < 1:
            raise ValueError("Tekenschaal moet positief zijn")
        if not self.pages:
            raise ValueError("DrawingDocument bevat geen bladen")
        expected_numbers = list(range(1, len(self.pages) + 1))
        if [page.number for page in self.pages] != expected_numbers:
            raise ValueError("Bladnummering is niet aaneengesloten")
        for page in self.pages:
            page.validate()
        supplied = self.document_sha256
        if supplied and supplied != _stable_hash(self._hash_payload()):
            raise ValueError("DrawingDocument-hash is ongeldig")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DrawingDocument":
        data = dict(raw)
        data["pages"] = [
            DrawingPage(
                **{
                    **dict(page),
                    "primitives": [DrawingPrimitive(**dict(item)) for item in page.get("primitives", ())],
                }
            )
            for page in data.get("pages", ())
        ]
        document = cls(**data)
        document.validate()
        return document

    def canonical_json(self) -> bytes:
        self.validate()
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")


def page_size_mm(sheet_format: str, orientation: str) -> tuple[float, float]:
    portrait = {
        "A4": (210.0, 297.0),
        "A3": (297.0, 420.0),
        "A2": (420.0, 594.0),
        "A1": (594.0, 841.0),
        "A0": (841.0, 1189.0),
    }
    width, height = portrait.get(str(sheet_format).upper(), portrait["A3"])
    if str(orientation).lower() == "landscape":
        width, height = height, width
    return width, height


__all__ = [
    "DRAWING_DOCUMENT_SCHEMA",
    "DRAWING_ENGINE_VERSION",
    "DrawingDocument",
    "DrawingPage",
    "DrawingPrimitive",
    "page_size_mm",
]
