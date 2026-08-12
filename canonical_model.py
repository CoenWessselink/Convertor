"""Canoniek productieonderdeel en lossless payloadtransport.

De converter gebruikt dit model als stabiele semantische laag tussen NC1/DSTV,
STEP en IFC. Converter-eigen bestanden kunnen een gecomprimeerde, gehashte
payload dragen. De zichtbare geometrie blijft een normaal STEP/IFC-model; de
payload voorkomt dat productiefeatures opnieuw uit een tessellatie moeten
worden geraden.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import base64
import copy
import hashlib
import json
import re
import zlib
from typing import Any, Iterable

SCHEMA_VERSION = "1.0"
PAYLOAD_CODEC = "zlib+base64+json"
STEP_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
NC1_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
IFC_MARKER = "NC1_STEP_CONVERTER_PAYLOAD_V1"
MAX_ATTACHMENT_BYTES = 32 * 1024 * 1024


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
    converter_version: str = "0.4.0"
    source_format: str = ""
    source_file: str = ""
    source_sha256: str = ""
    part_id: str = ""
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
        header = CanonicalHeader(**dict(data.get("header") or {}))
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
        holes = [CanonicalHole(**dict(item)) for item in data.get("holes") or []]
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
            header=header,
            contours=contours,
            holes=holes,
            unsupported_blocks=[str(v) for v in data.get("unsupported_blocks") or []],
            warnings=[str(v) for v in data.get("warnings") or []],
            coordinate_frame=dict(data.get("coordinate_frame") or {}),
            geometry=dict(data.get("geometry") or {}),
            recognition=dict(data.get("recognition") or {}),
            properties=dict(data.get("properties") or {}),
            attachments=attachments,
        )
        part.validate()
        return part

    def validate(self) -> None:
        if self.schema_version.split(".", 1)[0] != SCHEMA_VERSION.split(".", 1)[0]:
            raise CanonicalPayloadError(f"Niet-ondersteunde schema-versie {self.schema_version}")
        if self.source_sha256 and len(self.source_sha256) != 64:
            raise CanonicalPayloadError("source_sha256 heeft niet de verwachte lengte")
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


def encode_part(part: CanonicalPart) -> str:
    part.validate()
    raw = json.dumps(part.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    compressed = zlib.compress(raw, level=9)
    envelope = PayloadEnvelope(
        schema_version=SCHEMA_VERSION,
        codec=PAYLOAD_CODEC,
        payload_sha256=sha256_bytes(raw),
        payload_b64=base64.b64encode(compressed).decode("ascii"),
    )
    return base64.b64encode(envelope.to_json_bytes()).decode("ascii")


def decode_part(encoded: str) -> CanonicalPart:
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
        raw = zlib.decompress(compressed)
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


def _strip_step_payload(text: str) -> str:
    pattern = re.compile(
        rf"/\*\s*{re.escape(STEP_MARKER)}\s+\d+/\d+\s+[A-Za-z0-9+/=]+\s*\*/\s*",
        flags=re.IGNORECASE,
    )
    return pattern.sub("", text)


def embed_part_in_step(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    text = target.read_text(encoding="latin-1", errors="replace")
    text = _strip_step_payload(text).rstrip() + "\n"
    chunks = _chunk(encode_part(part))
    comments = "\n".join(
        f"/* {STEP_MARKER} {index}/{len(chunks)} {chunk} */"
        for index, chunk in enumerate(chunks, start=1)
    )
    marker = "END-ISO-10303-21;"
    pos = text.upper().rfind(marker)
    if pos >= 0:
        text = text[:pos].rstrip() + "\n" + comments + "\n" + text[pos:]
    else:
        text = text.rstrip() + "\n" + comments + "\n"
    target.write_text(text, encoding="latin-1", newline="\n")


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
        totals = {int(total) for _index, total, _chunk_text in matches}
        if len(totals) != 1:
            raise CanonicalPayloadError("STEP-payload bevat conflicterende aantallen")
        total = totals.pop()
        parts = {int(index): chunk_text for index, _total, chunk_text in matches}
        if sorted(parts) != list(range(1, total + 1)):
            raise CanonicalPayloadError("STEP-payload mist één of meer chunks")
        return decode_part("".join(parts[index] for index in range(1, total + 1)))
    except CanonicalPayloadError:
        if strict:
            raise
        return None


def _strip_nc1_payload(lines: Iterable[str]) -> list[str]:
    return [line for line in lines if not line.lstrip().startswith(f"** {NC1_MARKER} ")]


def embed_part_in_nc1(path: str | Path, part: CanonicalPart) -> None:
    target = Path(path)
    text = target.read_text(encoding="ascii", errors="replace")
    lines = _strip_nc1_payload(text.splitlines())
    chunks = _chunk(encode_part(part), size=72)
    payload_lines = [
        f"** {NC1_MARKER} {index}/{len(chunks)} {chunk}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    try:
        insert_at = next(index for index, line in enumerate(lines) if line.strip() == "ST") + 1
    except StopIteration as exc:
        raise ValueError(f"Geen ST-blok gevonden in {target.name}") from exc
    lines[insert_at:insert_at] = payload_lines
    target.write_text("\r\n".join(lines) + "\r\n", encoding="ascii", newline="")


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
        totals = {int(total) for _index, total, _chunk_text in matches}
        if len(totals) != 1:
            raise CanonicalPayloadError("NC1-payload bevat conflicterende aantallen")
        total = totals.pop()
        parts = {int(index): chunk_text for index, _total, chunk_text in matches}
        if sorted(parts) != list(range(1, total + 1)):
            raise CanonicalPayloadError("NC1-payload mist één of meer chunks")
        return decode_part("".join(parts[index] for index in range(1, total + 1)))
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


def extract_part_from_ifc(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        rf"/\*\s*{re.escape(IFC_MARKER)}\s+(\d+)/(\d+)\s+([A-Za-z0-9+/=]+)\s*\*/",
        text,
        flags=re.IGNORECASE,
    )
    if not matches:
        return None
    try:
        totals = {int(total) for _index, total, _chunk_text in matches}
        if len(totals) != 1:
            raise CanonicalPayloadError("IFC-payload bevat conflicterende aantallen")
        total = totals.pop()
        parts = {int(index): chunk_text for index, _total, chunk_text in matches}
        if sorted(parts) != list(range(1, total + 1)):
            raise CanonicalPayloadError("IFC-payload mist één of meer chunks")
        return decode_part("".join(parts[index] for index in range(1, total + 1)))
    except CanonicalPayloadError:
        if strict:
            raise
        return None


def canonical_from_nc1_part(
    part: Any,
    *,
    source_bytes: bytes | None = None,
    converter_version: str = "0.4.0",
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
        header=header,
        contours=contours,
        holes=holes,
        unsupported_blocks=list(part.unsupported_blocks),
        warnings=list(part.warnings),
        geometry=dict(geometry or {}),
        recognition=dict(recognition or {"method": "native NC1 parser", "confidence": 1.0}),
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
