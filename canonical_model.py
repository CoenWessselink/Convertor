"""Canoniek productieonderdeel en lossless payloadtransport.

De converter gebruikt dit model als stabiele semantische laag tussen NC1/DSTV,
STEP en IFC. Converter-eigen bestanden kunnen een gecomprimeerde, gehashte
payload dragen. De zichtbare geometrie blijft een normaal STEP/IFC-model; de
payload voorkomt dat productiefeatures opnieuw uit een tessellatie moeten
worden geraden.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import datetime as _dt
from pathlib import Path
import base64
import copy
import hashlib
import json
import re
import zlib
from typing import Any, Iterable

from cws_convertor.product import APP_VERSION, LEGACY_PAYLOAD_MARKER

SCHEMA_VERSION = "1.1"
DEFAULT_CONVERTER_VERSION = APP_VERSION
PAYLOAD_CODEC = "zlib+base64+json"
STEP_MARKER = LEGACY_PAYLOAD_MARKER
NC1_MARKER = LEGACY_PAYLOAD_MARKER
IFC_MARKER = LEGACY_PAYLOAD_MARKER
MAX_ATTACHMENT_BYTES = 32 * 1024 * 1024
MAX_RAW_PAYLOAD_BYTES = 96 * 1024 * 1024
MAX_ENCODED_PAYLOAD_CHARS = 160 * 1024 * 1024


class CanonicalPayloadError(ValueError):
    """Payload is aanwezig maar ongeldig, beschadigd of niet ondersteund."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def utc_now_iso() -> str:
    """Return a compact, timezone-aware ISO timestamp.

    Timestamps are deliberately kept out of geometry fingerprints, but are
    useful for provenance and release/audit information in the canonical
    model.
    """

    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _dataclass_from_dict(cls, value: Any):
    """Build ``cls`` from a dictionary while ignoring future minor fields.

    Schema 1.x payloads are minor-version compatible. Filtering unknown keys
    prevents a newer producer from breaking an older 1.x reader solely because
    it added non-critical metadata.
    """

    raw = dict(value or {}) if isinstance(value, dict) else {}
    allowed = {item.name for item in fields(cls)}
    return cls(**{key: item for key, item in raw.items() if key in allowed})


@dataclass
class CanonicalHeader:
    order_number: str = ""
    drawing_number: str = ""
    part_number: str = ""
    position_number: str = ""
    material: str = ""
    quantity: int = 1
    profile: str = ""
    profile_type: str = ""
    length: float = 0.0
    saw_length: float = 0.0
    dim1: float = 0.0
    dim2: float = 0.0
    dim3: float = 0.0
    dim4: float = 0.0
    radius: float = 0.0
    weight: float = 0.0
    paint_area: float = 0.0
    web_miter_front: float = 0.0
    web_miter_rear: float = 0.0
    flange_miter_front: float = 0.0
    flange_miter_rear: float = 0.0
    info: list[str] = field(default_factory=list)


@dataclass
class CanonicalContourPoint:
    x: float
    q: float
    datum: str = ""
    notch: str = ""
    radius: float = 0.0
    weld: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class CanonicalContour:
    kind: str
    face: str
    points: list[CanonicalContourPoint] = field(default_factory=list)


@dataclass
class CanonicalHole:
    face: str
    x: float
    q: float
    diameter: float
    datum: str = ""
    operation: str = ""
    depth: float = 0.0


@dataclass
class CanonicalEvidence:
    """Traceable evidence for one interpreted field.

    ``field_evidence`` on :class:`CanonicalPart` uses dotted field paths as
    keys, for example ``"header.material"`` or ``"holes[0].diameter"``.
    Coordinates are PDF points in the source page coordinate system unless a
    method explicitly states otherwise.
    """

    value: Any = None
    page: int | None = None
    bbox: list[float] = field(default_factory=list)
    method: str = ""
    confidence: float = 0.0
    status: str = "automatic"  # automatic, confirmed, corrected, derived
    source_text: str = ""
    confirmed_by: str = ""
    confirmed_at: str = ""
    notes: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise CanonicalPayloadError("Evidence-confidence moet tussen 0 en 1 liggen")
        if self.page is not None and int(self.page) < 1:
            raise CanonicalPayloadError("Evidence-paginanummer moet 1 of hoger zijn")
        if self.bbox and len(self.bbox) != 4:
            raise CanonicalPayloadError("Evidence-bbox moet vier waarden bevatten")


@dataclass
class CanonicalQuestion:
    """One explicit ambiguity that must not be silently guessed."""

    question_id: str
    field_path: str
    prompt: str
    severity: str = "blocking"  # blocking, warning, information
    alternatives: list[Any] = field(default_factory=list)
    page: int | None = None
    bbox: list[float] = field(default_factory=list)
    reason: str = ""
    status: str = "open"  # open, answered, dismissed
    answer: Any = None
    answered_by: str = ""
    answered_at: str = ""

    def is_blocking(self) -> bool:
        return self.severity == "blocking" and self.status == "open"


@dataclass
class CanonicalProductData:
    """Product and commercial metadata not represented by legacy DSTV fields."""

    name: str = ""
    mark: str = ""
    project_number: str = ""
    project_name: str = ""
    client: str = ""
    assembly_id: str = ""
    material_code: str = ""
    material_grade: str = ""
    density_kg_m3: float = 0.0
    coating: str = ""
    surface_treatment: str = ""
    profile_category: str = ""
    profile_series: str = ""
    profile_designation: str = ""
    profile_standard: str = ""
    length_mm: float = 0.0
    plate_thickness_mm: float = 0.0
    main_dimensions_mm: list[float] = field(default_factory=list)
    mass_each_kg: float = 0.0
    mass_total_kg: float = 0.0
    area_each_m2: float = 0.0
    area_total_m2: float = 0.0


@dataclass
class CanonicalDrawingData:
    """Drawing semantics and deterministic layout settings."""

    views: list[dict[str, Any]] = field(default_factory=list)
    projection_method: str = "first_angle"
    scale: str = ""
    sheet_format: str = "A3"
    orientation: str = "landscape"
    sheet_number: int = 1
    sheet_count: int = 1
    dimensions: list[dict[str, Any]] = field(default_factory=list)
    dimension_chains: list[dict[str, Any]] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)
    symbols: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    title_block: dict[str, Any] = field(default_factory=dict)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    template_id: str = "default"
    company_style_id: str = "default"
    drawing_status: str = "concept"  # concept, review, released, obsolete
    visible_content_sha256: str = ""


@dataclass
class CanonicalValidationData:
    """Validation state and the production export gate."""

    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unresolved_questions: list[CanonicalQuestion] = field(default_factory=list)
    geometric_comparison: dict[str, Any] = field(default_factory=dict)
    feature_comparison: dict[str, Any] = field(default_factory=dict)
    export_status: str = "blocked"  # blocked, concept, validated, released
    production_export_allowed: bool = False
    released_by: str = ""
    released_at: str = ""

    def blocking_questions(self) -> list[CanonicalQuestion]:
        return [question for question in self.unresolved_questions if question.is_blocking()]

    def refresh_gate(self) -> bool:
        self.production_export_allowed = not self.errors and not self.blocking_questions()
        if self.production_export_allowed and self.export_status == "blocked":
            self.export_status = "validated"
        elif not self.production_export_allowed and self.export_status in {"validated", "released"}:
            self.export_status = "blocked"
        return self.production_export_allowed


@dataclass
class CanonicalAttachment:
    """Exact bron-/tussenbestand in de payload, inclusief eigen checksum."""

    name: str
    media_type: str
    data_b64: str
    sha256: str
    size: int

    @classmethod
    def from_bytes(cls, name: str, media_type: str, data: bytes) -> "CanonicalAttachment":
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"Bijlage {name!r} is groter dan {MAX_ATTACHMENT_BYTES} bytes")
        return cls(
            name=name,
            media_type=media_type,
            data_b64=base64.b64encode(data).decode("ascii"),
            sha256=sha256_bytes(data),
            size=len(data),
        )

    def bytes(self) -> bytes:
        if int(self.size) < 0 or int(self.size) > MAX_ATTACHMENT_BYTES:
            raise CanonicalPayloadError(
                f"Bijlage {self.name!r} overschrijdt de ingestelde veiligheidslimiet"
            )
        try:
            data = base64.b64decode(self.data_b64.encode("ascii"), validate=True)
        except Exception as exc:
            raise CanonicalPayloadError(f"Bijlage {self.name!r} bevat ongeldige base64") from exc
        if len(data) != int(self.size):
            raise CanonicalPayloadError(
                f"Bijlage {self.name!r} heeft grootte {len(data)}, verwacht {self.size}"
            )
        if sha256_bytes(data) != self.sha256:
            raise CanonicalPayloadError(f"Checksum van bijlage {self.name!r} klopt niet")
        return data


@dataclass
class CanonicalPart:
    schema_version: str = SCHEMA_VERSION
    converter_version: str = DEFAULT_CONVERTER_VERSION
    source_format: str = ""
    source_file: str = ""
    source_sha256: str = ""
    imported_at: str = ""
    import_method: str = ""
    part_id: str = ""
    header: CanonicalHeader = field(default_factory=CanonicalHeader)
    product: CanonicalProductData = field(default_factory=CanonicalProductData)
    contours: list[CanonicalContour] = field(default_factory=list)
    holes: list[CanonicalHole] = field(default_factory=list)
    unsupported_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    coordinate_frame: dict[str, Any] = field(
        default_factory=lambda: {
            "origin_mm": [0.0, 0.0, 0.0],
            "x_axis": [1.0, 0.0, 0.0],
            "y_axis": [0.0, 1.0, 0.0],
            "z_axis": [0.0, 0.0, 1.0],
        }
    )
    geometry: dict[str, Any] = field(default_factory=dict)
    recognition: dict[str, Any] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)
    drawing: CanonicalDrawingData = field(default_factory=CanonicalDrawingData)
    field_evidence: dict[str, CanonicalEvidence] = field(default_factory=dict)
    validation: CanonicalValidationData = field(default_factory=CanonicalValidationData)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    attachments: dict[str, CanonicalAttachment] = field(default_factory=dict)

    @property
    def material(self) -> str:
        return self.header.material

    @property
    def quantity(self) -> int:
        return self.header.quantity

    @property
    def profile_designation(self) -> str:
        return self.header.profile

    @property
    def profile_type(self) -> str:
        return self.header.profile_type

    def add_attachment(self, key: str, name: str, media_type: str, data: bytes) -> None:
        self.attachments[str(key)] = CanonicalAttachment.from_bytes(name, media_type, data)

    def attachment_bytes(self, key: str) -> bytes | None:
        attachment = self.attachments.get(key)
        return attachment.bytes() if attachment else None

    def attachment(self, key: str) -> CanonicalAttachment | None:
        return self.attachments.get(key)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json_bytes(self, *, include_attachments: bool = True) -> bytes:
        data = self.to_dict()
        if not include_attachments:
            data["attachments"] = {}
        return json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def semantic_sha256(self, *, include_attachments: bool = False) -> str:
        """Hash the complete semantic model in a deterministic representation."""

        return sha256_bytes(self.to_json_bytes(include_attachments=include_attachments))

    def geometry_sha256(self) -> str:
        """Hash only production geometry and identity-critical dimensions."""

        payload = {
            "coordinate_frame": self.coordinate_frame,
            "header": {
                "profile": self.header.profile,
                "profile_type": self.header.profile_type,
                "length": self.header.length,
                "saw_length": self.header.saw_length,
                "dim1": self.header.dim1,
                "dim2": self.header.dim2,
                "dim3": self.header.dim3,
                "dim4": self.header.dim4,
                "radius": self.header.radius,
            },
            "contours": [asdict(item) for item in self.contours],
            "holes": [asdict(item) for item in self.holes],
            "geometry": self.geometry,
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return sha256_bytes(raw)

    def set_evidence(self, field_path: str, evidence: CanonicalEvidence) -> None:
        evidence.validate()
        self.field_evidence[str(field_path)] = evidence

    def add_question(self, question: CanonicalQuestion) -> None:
        if not any(item.question_id == question.question_id for item in self.validation.unresolved_questions):
            self.validation.unresolved_questions.append(question)
        self.refresh_export_gate()

    def refresh_export_gate(self) -> bool:
        allowed = self.validation.refresh_gate()
        if self.recognition.get("production_export_allowed") is False:
            allowed = False
            self.validation.production_export_allowed = False
            if self.validation.export_status in {"validated", "released"}:
                self.validation.export_status = "blocked"
        return allowed

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalPart":
        if not isinstance(data, dict):
            raise CanonicalPayloadError("Canoniek model is geen JSON-object")
        version = str(data.get("schema_version", ""))
        if version.split(".", 1)[0] != SCHEMA_VERSION.split(".", 1)[0]:
            raise CanonicalPayloadError(
                f"Niet-ondersteunde canonieke schema-versie {version!r}; verwacht {SCHEMA_VERSION}"
            )
        raw_header = dict(data.get("header") or {})
        header = _dataclass_from_dict(CanonicalHeader, raw_header)
        product = _dataclass_from_dict(CanonicalProductData, data.get("product"))
        # Migrate the first in-project schema-1.1 representation in which
        # product metadata still lived directly on the legacy header.
        legacy_product_map = {
            "part_name": "name",
            "mark": "mark",
            "project_number": "project_number",
            "assembly_id": "assembly_id",
            "material": "material_code",
            "material_grade": "material_grade",
            "density_kg_m3": "density_kg_m3",
            "coating": "coating",
            "profile_category": "profile_category",
            "profile_series": "profile_series",
            "profile": "profile_designation",
            "profile_standard": "profile_standard",
            "length": "length_mm",
            "thickness": "plate_thickness_mm",
        }
        for legacy_name, product_name in legacy_product_map.items():
            current = getattr(product, product_name)
            legacy = raw_header.get(legacy_name)
            if current in {"", 0, 0.0, None} and legacy not in {"", 0, 0.0, None}:
                setattr(product, product_name, legacy)
        contours: list[CanonicalContour] = []
        for contour_data in data.get("contours") or []:
            points = []
            for point_data in contour_data.get("points") or []:
                item = dict(point_data)
                weld = item.get("weld", (0.0, 0.0, 0.0, 0.0))
                item["weld"] = tuple(float(v) for v in weld)
                points.append(_dataclass_from_dict(CanonicalContourPoint, item))
            contours.append(
                CanonicalContour(
                    kind=str(contour_data.get("kind", "")),
                    face=str(contour_data.get("face", "")),
                    points=points,
                )
            )
        holes = [_dataclass_from_dict(CanonicalHole, item) for item in data.get("holes") or []]
        attachments = {
            str(key): _dataclass_from_dict(CanonicalAttachment, value)
            for key, value in (data.get("attachments") or {}).items()
        }
        evidence = {
            str(key): _dataclass_from_dict(CanonicalEvidence, value)
            for key, value in (data.get("field_evidence") or {}).items()
        }
        if not evidence:
            for key, value in (data.get("field_values") or {}).items():
                raw = dict(value or {})
                evidence[str(key)] = CanonicalEvidence(
                    value=raw.get("value"),
                    page=raw.get("source_page"),
                    bbox=[float(item) for item in raw.get("source_bbox") or []],
                    method=str(raw.get("method", "")),
                    confidence=float(raw.get("confidence", 0.0) or 0.0),
                    status=str(raw.get("status", "automatic")),
                    source_text=str(raw.get("evidence", "")),
                    confirmed_by=str(raw.get("confirmed_by", "")),
                )
        validation_raw = dict(data.get("validation") or {})
        questions: list[CanonicalQuestion] = []
        for item in validation_raw.pop("unresolved_questions", []) or []:
            raw = dict(item or {})
            if "field_path" not in raw and "field_name" in raw:
                raw["field_path"] = raw.get("field_name", "")
            if "prompt" not in raw and "message" in raw:
                raw["prompt"] = raw.get("message", "")
            if "alternatives" not in raw and "options" in raw:
                raw["alternatives"] = raw.get("options") or []
            if "severity" not in raw and "blocking" in raw:
                raw["severity"] = "blocking" if raw.get("blocking") else "warning"
            questions.append(_dataclass_from_dict(CanonicalQuestion, raw))
        validation = _dataclass_from_dict(CanonicalValidationData, validation_raw)
        validation.unresolved_questions = questions
        drawing_raw = dict(data.get("drawing") or {})
        if "drawing_status" not in drawing_raw and "status" in drawing_raw:
            drawing_raw["drawing_status"] = drawing_raw.get("status")
        if "visible_content_sha256" not in drawing_raw and "visible_drawing_sha256" in drawing_raw:
            drawing_raw["visible_content_sha256"] = drawing_raw.get("visible_drawing_sha256")
        part = cls(
            schema_version=version,
            converter_version=str(data.get("converter_version", "")),
            source_format=str(data.get("source_format", "")),
            source_file=str(data.get("source_file", "")),
            source_sha256=str(data.get("source_sha256", "")),
            imported_at=str(data.get("imported_at", "")),
            import_method=str(data.get("import_method", "")),
            part_id=str(data.get("part_id", "")),
            header=header,
            product=product,
            contours=contours,
            holes=holes,
            unsupported_blocks=[str(v) for v in data.get("unsupported_blocks") or []],
            warnings=[str(v) for v in data.get("warnings") or []],
            coordinate_frame=dict(data.get("coordinate_frame") or {}),
            geometry=dict(data.get("geometry") or {}),
            recognition=dict(data.get("recognition") or {}),
            properties=dict(data.get("properties") or {}),
            drawing=_dataclass_from_dict(CanonicalDrawingData, drawing_raw),
            field_evidence=evidence,
            validation=validation,
            audit_log=[dict(item) for item in data.get("audit_log") or []],
            attachments=attachments,
        )
        part.validate()
        return part

    def validate(self) -> None:
        if self.schema_version.split(".", 1)[0] != SCHEMA_VERSION.split(".", 1)[0]:
            raise CanonicalPayloadError(f"Niet-ondersteunde schema-versie {self.schema_version}")
        if self.source_sha256 and len(self.source_sha256) != 64:
            raise CanonicalPayloadError("source_sha256 heeft niet de verwachte lengte")
        for evidence in self.field_evidence.values():
            evidence.validate()
        for question in self.validation.unresolved_questions:
            if question.page is not None and int(question.page) < 1:
                raise CanonicalPayloadError("Vraag-paginanummer moet 1 of hoger zijn")
            if question.bbox and len(question.bbox) != 4:
                raise CanonicalPayloadError("Vraag-bbox moet vier waarden bevatten")
        for attachment in self.attachments.values():
            attachment.bytes()
        if self.source_sha256:
            source_key = {"NC1": "nc1", "DSTV": "nc1", "STEP": "step", "STP": "step"}.get(
                self.source_format.upper()
            )
            if source_key and source_key in self.attachments:
                if self.attachments[source_key].sha256 != self.source_sha256:
                    raise CanonicalPayloadError(
                        f"Bronhash komt niet overeen met bijlage {source_key!r}"
                    )
        self.refresh_export_gate()

    def clone(self) -> "CanonicalPart":
        return copy.deepcopy(self)


@dataclass
class PayloadEnvelope:
    schema_version: str
    codec: str
    payload_sha256: str
    payload_b64: str

    def to_json_bytes(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )

    @classmethod
    def from_json_bytes(cls, data: bytes) -> "PayloadEnvelope":
        try:
            raw = json.loads(data.decode("utf-8"))
            return cls(**raw)
        except Exception as exc:
            raise CanonicalPayloadError("Payload-envelop is geen geldige JSON") from exc


def encode_part(part: CanonicalPart) -> str:
    part.validate()
    raw = part.to_json_bytes(include_attachments=True)
    compressed = zlib.compress(raw, level=9)
    envelope = PayloadEnvelope(
        schema_version=part.schema_version,
        codec=PAYLOAD_CODEC,
        payload_sha256=sha256_bytes(raw),
        payload_b64=base64.b64encode(compressed).decode("ascii"),
    )
    return base64.b64encode(envelope.to_json_bytes()).decode("ascii")


def decode_part(encoded: str) -> CanonicalPart:
    if len(encoded) > MAX_ENCODED_PAYLOAD_CHARS:
        raise CanonicalPayloadError("Canonieke payload is groter dan de ingestelde veiligheidslimiet")
    try:
        envelope_data = base64.b64decode(encoded.encode("ascii"), validate=True)
    except Exception as exc:
        raise CanonicalPayloadError("Payload-envelop bevat ongeldige base64") from exc
    envelope = PayloadEnvelope.from_json_bytes(envelope_data)
    if envelope.schema_version.split(".", 1)[0] != SCHEMA_VERSION.split(".", 1)[0]:
        raise CanonicalPayloadError(f"Niet-ondersteunde payloadschema-versie {envelope.schema_version}")
    if envelope.codec != PAYLOAD_CODEC:
        raise CanonicalPayloadError(f"Niet-ondersteunde payloadcodec {envelope.codec!r}")
    try:
        compressed = base64.b64decode(envelope.payload_b64.encode("ascii"), validate=True)
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, MAX_RAW_PAYLOAD_BYTES + 1)
        if len(raw) > MAX_RAW_PAYLOAD_BYTES or decompressor.unconsumed_tail:
            raise CanonicalPayloadError("Gedecomprimeerde payload overschrijdt de veiligheidslimiet")
        raw += decompressor.flush(MAX_RAW_PAYLOAD_BYTES + 1 - len(raw))
        if len(raw) > MAX_RAW_PAYLOAD_BYTES:
            raise CanonicalPayloadError("Gedecomprimeerde payload overschrijdt de veiligheidslimiet")
    except CanonicalPayloadError:
        raise
    except Exception as exc:
        raise CanonicalPayloadError("Payload kon niet worden gedecomprimeerd") from exc
    if sha256_bytes(raw) != envelope.payload_sha256:
        raise CanonicalPayloadError("Checksum van canonieke payload klopt niet")
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise CanonicalPayloadError("Canonieke payload bevat ongeldige JSON") from exc
    return CanonicalPart.from_dict(data)


def _chunk(text: str, size: int = 1800) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def _assemble_chunks(matches: Iterable[tuple[str, str, str]], label: str) -> str:
    rows = list(matches)
    if not rows:
        raise CanonicalPayloadError(f"{label}-payload bevat geen chunks")
    totals = {int(total) for _index, total, _chunk_text in rows}
    if len(totals) != 1:
        raise CanonicalPayloadError(f"{label}-payload bevat conflicterende aantallen")
    total = totals.pop()
    if total <= 0 or total > 1_000_000:
        raise CanonicalPayloadError(f"{label}-payload bevat een ongeldig chunk-aantal")
    parts: dict[int, str] = {}
    for index_text, _total, chunk_text in rows:
        index = int(index_text)
        if index < 1 or index > total:
            raise CanonicalPayloadError(f"{label}-payload bevat een ongeldige chunkindex {index}")
        if index in parts and parts[index] != chunk_text:
            raise CanonicalPayloadError(f"{label}-payload bevat conflicterende chunk {index}")
        parts[index] = chunk_text
    if sorted(parts) != list(range(1, total + 1)):
        raise CanonicalPayloadError(f"{label}-payload mist één of meer chunks")
    encoded = "".join(parts[index] for index in range(1, total + 1))
    if len(encoded) > MAX_ENCODED_PAYLOAD_CHARS:
        raise CanonicalPayloadError(f"{label}-payload overschrijdt de veiligheidslimiet")
    return encoded


def _strip_step_payload(text: str) -> str:
    pattern = re.compile(
        rf"(?mi)^[ \t]*/\*[ \t]*{re.escape(STEP_MARKER)}[ \t]+\d+/\d+[ \t]+[A-Za-z0-9+/=]+[ \t]*\*/[ \t]*(?:\r?\n)?"
    )
    return pattern.sub("", text)


def strip_step_payload_bytes(data: bytes) -> bytes:
    return _strip_step_payload(data.decode("latin-1")).encode("latin-1")


def embed_part_in_step(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    text = _strip_step_payload(target.read_bytes().decode("latin-1"))
    newline = "\r\n" if "\r\n" in text else "\n"
    chunks = _chunk(encode_part(part))
    comments = newline.join(
        f"/* {STEP_MARKER} {index}/{len(chunks)} {chunk} */"
        for index, chunk in enumerate(chunks, start=1)
    )
    marker = "END-ISO-10303-21;"
    position = text.upper().rfind(marker)
    if position >= 0:
        prefix, suffix = text[:position], text[position:]
        if prefix and not prefix.endswith(("\n", "\r")):
            prefix += newline
        text = prefix + comments + newline + suffix
    else:
        if text and not text.endswith(("\n", "\r")):
            text += newline
        text += comments + newline
    target.write_bytes(text.encode("latin-1"))


def extract_part_from_step(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    text = Path(path).read_text(encoding="latin-1", errors="replace")
    matches = re.findall(
        rf"/\*\s*{re.escape(STEP_MARKER)}\s+(\d+)/(\d+)\s+([A-Za-z0-9+/=]+)\s*\*/",
        text,
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    try:
        return decode_part(_assemble_chunks(matches, "STEP"))
    except CanonicalPayloadError:
        if strict:
            raise
        return None


def _strip_nc1_payload(lines: Iterable[str]) -> list[str]:
    return [line for line in lines if not line.lstrip().startswith(f"** {NC1_MARKER} ")]


def strip_nc1_payload_bytes(data: bytes) -> bytes:
    text = data.decode("ascii", errors="replace")
    kept = [
        line for line in text.splitlines(keepends=True)
        if not line.lstrip().startswith(f"** {NC1_MARKER} ")
    ]
    return "".join(kept).encode("ascii", errors="replace")


def embed_part_in_nc1(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    text = target.read_bytes().decode("ascii", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = [
        line for line in text.splitlines(keepends=True)
        if not line.lstrip().startswith(f"** {NC1_MARKER} ")
    ]
    chunks = _chunk(encode_part(part), size=72)
    payload_lines = [
        f"** {NC1_MARKER} {index}/{len(chunks)} {chunk}{newline}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    insert_at = next((index + 1 for index, line in enumerate(lines) if line.strip() == "ST"), None)
    if insert_at is None:
        raise ValueError(f"Geen ST-blok gevonden in {target.name}")
    if lines[insert_at - 1] and not lines[insert_at - 1].endswith(("\n", "\r")):
        lines[insert_at - 1] += newline
    lines[insert_at:insert_at] = payload_lines
    target.write_bytes("".join(lines).encode("ascii", errors="replace"))


def extract_part_from_nc1(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    lines = Path(path).read_text(encoding="ascii", errors="replace").splitlines()
    pattern = re.compile(
        rf"^\s*\*\*\s+{re.escape(NC1_MARKER)}\s+(\d+)/(\d+)\s+([A-Za-z0-9+/=]+)\s*$",
        re.IGNORECASE,
    )
    matches = [match.groups() for line in lines if (match := pattern.match(line))]
    if not matches:
        return None
    try:
        return decode_part(_assemble_chunks(matches, "NC1"))
    except CanonicalPayloadError:
        if strict:
            raise
        return None


def embed_part_in_ifc_text(text: str, part: CanonicalPart) -> str:
    pattern = re.compile(
        rf"/\*\s*{re.escape(IFC_MARKER)}\s+\d+/\d+\s+[A-Za-z0-9+/=]+\s*\*/\s*",
        re.IGNORECASE,
    )
    clean = pattern.sub("", text).rstrip() + "\n"
    chunks = _chunk(encode_part(part))
    comments = "\n".join(
        f"/* {IFC_MARKER} {index}/{len(chunks)} {chunk} */"
        for index, chunk in enumerate(chunks, start=1)
    )
    marker = "ENDSEC;"
    pos = clean.upper().rfind(marker)
    if pos >= 0:
        return clean[:pos].rstrip() + "\n" + comments + "\n" + clean[pos:]
    return clean + comments + "\n"


def _ifc_unescape(value: str) -> str:
    return value.replace("''", "'").replace("\\\\", "\\")


def _extract_part_from_ifc_pset(text: str) -> CanonicalPart | None:
    if "PSET_NC1STEPCONVERTER" not in text.upper():
        return None
    property_pattern = re.compile(
        r"#\d+\s*=\s*IFCPROPERTYSINGLEVALUE\s*\(\s*'([^']*(?:''[^']*)*)'\s*,\s*\$\s*,\s*"
        r"(IFCTEXT|IFCLABEL|IFCIDENTIFIER|IFCINTEGER|IFCREAL)\s*\(\s*(?:'((?:''|[^'])*)'|([^\)]*))\s*\)\s*,\s*\$\s*\)\s*;",
        re.IGNORECASE,
    )
    values: dict[str, str] = {}
    for match in property_pattern.finditer(text):
        name = _ifc_unescape(match.group(1))
        value = _ifc_unescape(match.group(3)) if match.group(3) is not None else match.group(4).strip()
        previous = values.get(name)
        if previous is not None and previous != value:
            raise CanonicalPayloadError(f"IFC-property {name!r} komt met conflicterende waarden voor")
        values[name] = value
    try:
        total = int(values.get("PayloadChunkCount", "0"))
    except ValueError as exc:
        raise CanonicalPayloadError("IFC PayloadChunkCount is ongeldig") from exc
    if total <= 0:
        return None
    chunks: list[tuple[str, str, str]] = []
    for index in range(1, total + 1):
        key = f"PayloadChunk_{index:04d}"
        if key not in values:
            raise CanonicalPayloadError(f"IFC-propertyset mist {key}")
        chunks.append((str(index), str(total), values[key]))
    encoded = _assemble_chunks(chunks, "IFC-Pset")
    expected_sha = values.get("PayloadSHA256", "")
    if expected_sha and sha256_bytes(encoded.encode("ascii")) != expected_sha:
        raise CanonicalPayloadError("Checksum van IFC-propertysetpayload klopt niet")
    codec = values.get("PayloadCodec", PAYLOAD_CODEC)
    if codec != PAYLOAD_CODEC:
        raise CanonicalPayloadError(f"Niet-ondersteunde IFC-payloadcodec {codec!r}")
    return decode_part(encoded)


def extract_part_from_ifc(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        pset_part = _extract_part_from_ifc_pset(text)
        if pset_part is not None:
            return pset_part
        matches = re.findall(
            rf"/\*\s*{re.escape(IFC_MARKER)}\s+(\d+)/(\d+)\s+([A-Za-z0-9+/=]+)\s*\*/",
            text,
            flags=re.IGNORECASE,
        )
        if not matches:
            return None
        return decode_part(_assemble_chunks(matches, "IFC-comment"))
    except CanonicalPayloadError:
        if strict:
            raise
        return None

def canonical_from_nc1_part(
    part: Any,
    *,
    source_bytes: bytes | None = None,
    converter_version: str = DEFAULT_CONVERTER_VERSION,
    geometry: dict[str, Any] | None = None,
    recognition: dict[str, Any] | None = None,
) -> CanonicalPart:
    """Maak een CanonicalPart uit het bestaande converter.NC1Part-object."""

    source = Path(part.source)
    data = source_bytes if source_bytes is not None else source.read_bytes()
    header = CanonicalHeader(**asdict(part.header))
    contours = [
        CanonicalContour(
            kind=contour.kind,
            face=contour.face,
            points=[
                CanonicalContourPoint(
                    x=float(point.x),
                    q=float(point.q),
                    datum=point.datum,
                    notch=point.notch,
                    radius=float(point.radius),
                    weld=tuple(float(value) for value in point.weld),
                )
                for point in contour.points
            ],
        )
        for contour in part.contours
    ]
    holes = [
        CanonicalHole(
            face=hole.face,
            x=float(hole.x),
            q=float(hole.q),
            diameter=float(hole.diameter),
            datum=hole.datum,
            operation=hole.operation,
            depth=float(hole.depth),
        )
        for hole in part.holes
    ]
    canonical = CanonicalPart(
        converter_version=converter_version,
        source_format="NC1",
        source_file=source.name,
        source_sha256=sha256_bytes(data),
        imported_at=utc_now_iso(),
        import_method="exact",
        part_id=part.header.position_number or part.header.drawing_number or source.stem,
        header=header,
        product=CanonicalProductData(
            name=part.header.position_number or part.header.drawing_number or source.stem,
            material_code=part.header.material,
            material_grade=part.header.material,
            profile_designation=part.header.profile,
            length_mm=float(part.header.length),
            plate_thickness_mm=(float(part.header.dim2) if part.header.profile_type == "B" else 0.0),
            main_dimensions_mm=[
                float(value)
                for value in (
                    part.header.length,
                    part.header.dim1,
                    part.header.dim2,
                    part.header.dim3,
                    part.header.dim4,
                )
                if float(value) > 0
            ],
        ),
        contours=contours,
        holes=holes,
        unsupported_blocks=list(part.unsupported_blocks),
        warnings=list(part.warnings),
        geometry=dict(geometry or {}),
        recognition=dict(
            recognition
            or {
                "method": "native NC1 parser",
                "confidence": 1.0,
                "production_export_allowed": True,
            }
        ),
        validation=CanonicalValidationData(
            warnings=list(part.warnings),
            export_status="validated",
            production_export_allowed=True,
        ),
    )
    for field_path, value in {
        "header.position_number": header.position_number,
        "header.part_number": header.part_number,
        "header.profile": header.profile,
        "header.material": header.material,
        "header.quantity": header.quantity,
        "header.length": header.length,
    }.items():
        canonical.set_evidence(
            field_path,
            CanonicalEvidence(
                value=value,
                method="native_nc1",
                confidence=1.0,
                status="confirmed",
                source_text=str(value),
            ),
        )
    canonical.add_attachment("nc1", source.name, "application/x-dstv", data)
    canonical.refresh_export_gate()
    return canonical


def write_attachment(part: CanonicalPart, key: str, target: str | Path) -> Path:
    data = part.attachment_bytes(key)
    if data is None:
        raise KeyError(f"Canonieke payload bevat geen bijlage {key!r}")
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return output


def geometry_sha256(part: CanonicalPart) -> str:
    return part.geometry_sha256()


def production_export_allowed(part: CanonicalPart) -> tuple[bool, list[str]]:
    reasons = list(part.validation.errors)
    reasons.extend(question.prompt for question in part.validation.blocking_questions())
    if not part.validation.production_export_allowed:
        reasons.append("Canoniek model is nog niet vrijgegeven voor productie-export")
    return (not reasons), reasons
