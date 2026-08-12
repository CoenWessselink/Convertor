"""Canoniek productieonderdeel en lossless payloadtransport.

De converter gebruikt dit model als stabiele semantische laag tussen NC1/DSTV,
STEP en IFC. Converter-eigen bestanden kunnen een gecomprimeerde, gehashte
payload dragen. De zichtbare geometrie blijft een normaal STEP/IFC-model; de
payload voorkomt dat productiefeatures opnieuw uit een tessellatie moeten
worden geraden.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
import base64
import copy
import hashlib
import json
import re
import zlib
from typing import Any, Iterable

SCHEMA_VERSION = "1.1"
PAYLOAD_CODEC = "zlib+base64+json"
STEP_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
NC1_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
IFC_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
MAX_ATTACHMENT_BYTES = 32 * 1024 * 1024
MAX_RAW_PAYLOAD_BYTES = 96 * 1024 * 1024
MAX_ENCODED_PAYLOAD_CHARS = 160 * 1024 * 1024


class CanonicalPayloadError(ValueError):
    """Payload is aanwezig maar ongeldig, beschadigd of niet ondersteund."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


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
    mark: str = ""
    project_number: str = ""
    assembly_id: str = ""
    part_name: str = ""
    coating: str = ""
    material_grade: str = ""
    density_kg_m3: float = 7850.0
    profile_category: str = ""
    profile_series: str = ""
    profile_standard: str = ""
    thickness: float = 0.0
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
class CanonicalFieldValue:
    """Waarde met herkomst, confidence en menselijke reviewstatus."""

    value: Any = None
    source_page: int | None = None
    source_bbox: list[float] = field(default_factory=list)
    method: str = ""
    confidence: float = 0.0
    status: str = "automatic"
    confirmed_by: str = ""
    evidence: str = ""


@dataclass
class CanonicalQuestion:
    question_id: str
    field_name: str
    message: str
    options: list[str] = field(default_factory=list)
    blocking: bool = True
    status: str = "open"
    answer: str = ""


@dataclass
class CanonicalDrawing:
    sheet_format: str = "A4"
    orientation: str = "landscape"
    scale: str = "auto"
    status: str = "draft"
    template_id: str = "default"
    title_block: dict[str, Any] = field(default_factory=dict)
    views: list[dict[str, Any]] = field(default_factory=list)
    dimensions: list[dict[str, Any]] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)
    visible_drawing_sha256: str = ""


@dataclass
class CanonicalValidation:
    errors: list[str] = field(default_factory=list)
    unresolved_questions: list[CanonicalQuestion] = field(default_factory=list)
    geometric_comparison: dict[str, Any] = field(default_factory=dict)
    feature_comparison: dict[str, Any] = field(default_factory=dict)
    export_status: str = "draft"
    production_export_allowed: bool = True
    released_by: str = ""
    released_at: str = ""


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
    converter_version: str = "0.5.0"
    source_format: str = ""
    source_file: str = ""
    source_sha256: str = ""
    part_id: str = ""
    imported_at: str = ""
    import_method: str = ""
    header: CanonicalHeader = field(default_factory=CanonicalHeader)
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
    field_values: dict[str, CanonicalFieldValue] = field(default_factory=dict)
    drawing: CanonicalDrawing = field(default_factory=CanonicalDrawing)
    validation: CanonicalValidation = field(default_factory=CanonicalValidation)
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalPart":
        if not isinstance(data, dict):
            raise CanonicalPayloadError("Canoniek model is geen JSON-object")
        version = str(data.get("schema_version", ""))
        if version.split(".", 1)[0] != SCHEMA_VERSION.split(".", 1)[0]:
            raise CanonicalPayloadError(
                f"Niet-ondersteunde canonieke schema-versie {version!r}; verwacht {SCHEMA_VERSION}"
            )

        def filtered(dataclass_type: type, values: dict[str, Any]) -> dict[str, Any]:
            allowed = {item.name for item in fields(dataclass_type)}
            return {key: value for key, value in values.items() if key in allowed}

        header = CanonicalHeader(**filtered(CanonicalHeader, dict(data.get("header") or {})))
        contours: list[CanonicalContour] = []
        for contour_data in data.get("contours") or []:
            points = []
            for point_data in contour_data.get("points") or []:
                item = dict(point_data)
                weld = item.get("weld", (0.0, 0.0, 0.0, 0.0))
                item["weld"] = tuple(float(v) for v in weld)
                points.append(CanonicalContourPoint(**item))
            contours.append(
                CanonicalContour(
                    kind=str(contour_data.get("kind", "")),
                    face=str(contour_data.get("face", "")),
                    points=points,
                )
            )
        holes = [CanonicalHole(**filtered(CanonicalHole, dict(item))) for item in data.get("holes") or []]
        field_values = {
            str(key): CanonicalFieldValue(**filtered(CanonicalFieldValue, dict(value)))
            for key, value in (data.get("field_values") or {}).items()
        }
        drawing = CanonicalDrawing(**filtered(CanonicalDrawing, dict(data.get("drawing") or {})))
        validation_data = dict(data.get("validation") or {})
        questions = [
            CanonicalQuestion(**filtered(CanonicalQuestion, dict(item)))
            for item in validation_data.pop("unresolved_questions", []) or []
        ]
        validation = CanonicalValidation(
            unresolved_questions=questions,
            **filtered(CanonicalValidation, validation_data),
        )
        attachments = {
            str(key): CanonicalAttachment(**dict(value))
            for key, value in (data.get("attachments") or {}).items()
        }
        part = cls(
            schema_version=version,
            converter_version=str(data.get("converter_version", "")),
            source_format=str(data.get("source_format", "")),
            source_file=str(data.get("source_file", "")),
            source_sha256=str(data.get("source_sha256", "")),
            part_id=str(data.get("part_id", "")),
            imported_at=str(data.get("imported_at", "")),
            import_method=str(data.get("import_method", "")),
            header=header,
            contours=contours,
            holes=holes,
            unsupported_blocks=[str(v) for v in data.get("unsupported_blocks") or []],
            warnings=[str(v) for v in data.get("warnings") or []],
            coordinate_frame=dict(data.get("coordinate_frame") or {}),
            geometry=dict(data.get("geometry") or {}),
            recognition=dict(data.get("recognition") or {}),
            properties=dict(data.get("properties") or {}),
            field_values=field_values,
            drawing=drawing,
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
        for name, field_value in self.field_values.items():
            if not 0.0 <= float(field_value.confidence) <= 1.0:
                raise CanonicalPayloadError(f"Confidence van veld {name!r} ligt buiten 0..1")
        blocking_open = [
            question.question_id
            for question in self.validation.unresolved_questions
            if question.blocking and question.status.lower() not in {"answered", "resolved", "dismissed"}
        ]
        if self.validation.production_export_allowed and (self.validation.errors or blocking_open):
            raise CanonicalPayloadError(
                "Productie-export staat aan terwijl blokkerende fouten of vragen openstaan"
            )
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


def canonical_json_bytes(part: CanonicalPart) -> bytes:
    """Deterministische JSON-representatie, inclusief gecontroleerde bijlagen."""

    part.validate()
    return json.dumps(
        part.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_sha256(part: CanonicalPart) -> str:
    return sha256_bytes(canonical_json_bytes(part))


def geometry_sha256(part: CanonicalPart) -> str:
    """Hash alleen productiebepalende geometrie en lokale assen."""

    payload = {
        "profile": part.header.profile,
        "profile_type": part.header.profile_type,
        "length": part.header.length,
        "dimensions": [
            part.header.dim1, part.header.dim2, part.header.dim3, part.header.dim4,
            part.header.radius, part.header.thickness,
        ],
        "coordinate_frame": part.coordinate_frame,
        "contours": [asdict(item) for item in part.contours],
        "holes": [asdict(item) for item in part.holes],
        "geometry": part.geometry,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(raw)


def production_export_allowed(part: CanonicalPart) -> tuple[bool, list[str]]:
    reasons = list(part.validation.errors)
    reasons.extend(
        question.message
        for question in part.validation.unresolved_questions
        if question.blocking and question.status.lower() not in {"answered", "resolved", "dismissed"}
    )
    if not part.validation.production_export_allowed:
        reasons.append("Canoniek model is nog niet vrijgegeven voor productie-export")
    return (not reasons), reasons


def encode_part(part: CanonicalPart) -> str:
    raw = canonical_json_bytes(part)
    compressed = zlib.compress(raw, level=9)
    envelope = PayloadEnvelope(
        schema_version=SCHEMA_VERSION,
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
    """Verwijder alleen convertercommentregels; overige STEP-bytes blijven gelijk."""

    return _strip_step_payload(data.decode("latin-1")).encode("latin-1")


def embed_part_in_step(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    original = target.read_bytes()
    text = _strip_step_payload(original.decode("latin-1"))
    newline = "\r\n" if "\r\n" in text else "\n"
    chunks = _chunk(encode_part(part))
    comments = newline.join(
        f"/* {STEP_MARKER} {index}/{len(chunks)} {chunk} */"
        for index, chunk in enumerate(chunks, start=1)
    )
    marker = "END-ISO-10303-21;"
    position = text.upper().rfind(marker)
    if position >= 0:
        prefix = text[:position]
        suffix = text[position:]
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
        line
        for line in text.splitlines(keepends=True)
        if not line.lstrip().startswith(f"** {NC1_MARKER} ")
    ]
    return "".join(kept).encode("ascii", errors="replace")


def embed_part_in_nc1(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    original = target.read_bytes()
    text = original.decode("ascii", errors="replace")
    newline = "\r\n" if "\r\n" in text else "\n"
    raw_lines = text.splitlines(keepends=True)
    lines = [
        line
        for line in raw_lines
        if not line.lstrip().startswith(f"** {NC1_MARKER} ")
    ]
    chunks = _chunk(encode_part(part), size=72)
    payload_lines = [
        f"** {NC1_MARKER} {index}/{len(chunks)} {chunk}{newline}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    insert_at = None
    for index, line in enumerate(lines):
        if line.strip() == "ST":
            insert_at = index + 1
            break
    if insert_at is None:
        raise ValueError(f"Geen ST-blok gevonden in {target.name}")
    # Zorg dat de ST-regel een regeleinde heeft voordat payloadregels volgen.
    if lines[insert_at - 1] and not lines[insert_at - 1].endswith(("\n", "\r")):
        lines[insert_at - 1] += newline
    lines[insert_at:insert_at] = payload_lines
    target.write_bytes("".join(lines).encode("ascii", errors="replace"))


def extract_part_from_nc1(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    lines = Path(path).read_text(encoding="ascii", errors="replace").splitlines()
    matches = []
    pattern = re.compile(
        rf"^\s*\*\*\s+{re.escape(NC1_MARKER)}\s+(\d+)/(\d+)\s+([A-Za-z0-9+/=]+)\s*$",
        re.IGNORECASE,
    )
    for line in lines:
        match = pattern.match(line)
        if match:
            matches.append(match.groups())
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
    """Lees de lossless payload uit echte IfcPropertySingleValue-records.

    De commentkopie is alleen redundantie voor dependency-arme herstelacties. De
    propertyset is de primaire, interoperabele opslaglaag en blijft bruikbaar
    wanneer comments door een IFC-tool worden verwijderd.
    """

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
    chunks: list[tuple[str, str, str]] = []
    try:
        total = int(values.get("PayloadChunkCount", "0"))
    except ValueError as exc:
        raise CanonicalPayloadError("IFC PayloadChunkCount is ongeldig") from exc
    if total <= 0:
        return None
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
    converter_version: str = "0.5.0",
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
        part_id=part.header.part_number or source.stem,
        import_method="exact",
        header=header,
        contours=contours,
        holes=holes,
        unsupported_blocks=list(part.unsupported_blocks),
        warnings=list(part.warnings),
        geometry=dict(geometry or {}),
        recognition=dict(recognition or {"method": "native NC1 parser", "confidence": 1.0}),
        field_values={
            "position": CanonicalFieldValue(
                value=header.position_number, method="native NC1 parser", confidence=1.0
            ),
            "profile": CanonicalFieldValue(
                value=header.profile, method="native NC1 parser", confidence=1.0
            ),
            "material": CanonicalFieldValue(
                value=header.material, method="native NC1 parser", confidence=1.0
            ),
            "quantity": CanonicalFieldValue(
                value=header.quantity, method="native NC1 parser", confidence=1.0
            ),
        },
        validation=CanonicalValidation(export_status="validated", production_export_allowed=True),
    )
    canonical.add_attachment("nc1", source.name, "application/x-dstv", data)
    return canonical


def write_attachment(part: CanonicalPart, key: str, target: str | Path) -> Path:
    data = part.attachment_bytes(key)
    if data is None:
        raise KeyError(f"Canonieke payload bevat geen bijlage {key!r}")
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return output
