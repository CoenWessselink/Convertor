"""Conservative material-candidate evidence shared by PDF and DXF intake.

Only explicit source text or metadata is considered. Geometry, colour and
rendering style are prohibited evidence sources and are ignored fail-closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
from pathlib import Path
import re
from typing import Any, Iterable


_MATERIAL_LABEL_RE = re.compile(
    r"\b(?:MATERIAL(?:\s+GRADE)?|MATERIAAL(?:KWALITEIT)?|"
    r"STAALKWALITEIT|STEEL\s+GRADE|ALLOY|QUALITY|GRADE)\s*[:=]\s*(?P<value>[^;|]{1,80})",
    re.IGNORECASE,
)
_CONTEXT_PREFIX_RE = re.compile(
    r"^(?:MAT(?:ERIAL)?|MATERIAAL|GRADE|QUALITY|ALLOY)[_ .:/-]+(?P<value>.+)$",
    re.IGNORECASE,
)
_KNOWN_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])(?:"
    r"S\d{3}[A-Z0-9+.-]*"
    r"|1\.\d{4}"
    r"|AISI\s*\d{3}[A-Z]*"
    r"|EN\s*AW[- ]?\d{4}[ -]?[A-Z]\d{1,3}"
    r"|\d{4}[- ](?:T\d{1,3}|H\d{1,3})"
    r"|A[24][ -](?:50|70|80)"
    r"|(?:4\.6|5\.6|5\.8|6\.8|8\.8|9\.8|10\.9|12\.9)"
    r"|C\d{2}/\d{2}"
    r"|(?:C18|C24|C30|GL24H|GL28C)"
    r"|(?:PA\s*6|POM[- ]?C|PE[- ]?HD|HDPE|PVC[- ]?U|PTFE|PET[- ]?P|PEEK)"
    r"|(?:ERTALON\s*6\s*PLA|ERTACETAL\s*C|ERTALYTE|VUREN|MULTIPLEX)"
    r")(?![A-Z0-9])",
    re.IGNORECASE,
)
_PROFILE_CONTEXT_RE = re.compile(
    r"\b(?:STRIP|PL|PLAAT|FLAT|HEA|HEB|HEM|IPE|IPN|UPN|UNP|UPE|RHS|SHS|CHS|KOKER|ROUND|L)\s*\d",
    re.IGNORECASE,
)
_FORBIDDEN_SOURCE_TOKENS = ("geometry", "geometr", "colour", "color", "rgb", "aci", "render")


def _key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _clean_candidate(value: Any) -> str:
    text = str(value or "").strip().strip("[](){}<>.,;:|")
    # Stop at common drawing-table separators and trailing field labels.
    text = re.split(r"\s{2,}|\t|\b(?:LENGTH|LENGTE|QTY|AANTAL|PROFILE|PROFIEL)\b", text, maxsplit=1, flags=re.IGNORECASE)[0]
    return text.strip().strip("[](){}<>.,;:|")[:80]


@dataclass(frozen=True)
class SourceTextEvidence:
    text: str
    source_format: str
    source_kind: str
    source_reference: str
    confidence: float
    page: int | None = None
    bbox: tuple[float, ...] = ()
    field_name: str = ""


@dataclass(frozen=True)
class MaterialCandidate:
    raw_value: str
    normalized_value: str
    canonical_code: str
    catalog_status: str
    confidence: float
    source_format: str
    source_kind: str
    source_reference: str
    source_text: str
    page: int | None = None
    bbox: tuple[float, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["bbox"] = list(self.bbox)
        return payload


@dataclass(frozen=True)
class MaterialCandidateEvidence:
    status: str
    selected_value: str = ""
    confidence: float = 0.0
    review_status: str = "review_required"
    material_grade_proven: bool = False
    reason: str = ""
    candidates: tuple[MaterialCandidate, ...] = ()
    ignored_sources: tuple[str, ...] = ()
    inference_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "text_or_metadata_candidates_only": True,
            "geometry_can_prove_material_grade": False,
            "colour_can_prove_material_grade": False,
            "default_material_allowed": False,
        }
    )

    @property
    def conflict(self) -> bool:
        return self.status == "conflict"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "selected_value": self.selected_value,
            "confidence": self.confidence,
            "review_status": self.review_status,
            "material_grade_proven": self.material_grade_proven,
            "reason": self.reason,
            "candidates": [item.to_dict() for item in self.candidates],
            "ignored_sources": list(self.ignored_sources),
            "inference_policy": dict(self.inference_policy),
        }


def _candidate_values(record: SourceTextEvidence, *, database: Any = None) -> list[str]:
    text = str(record.text or "").strip()
    if not text:
        return []
    label = str(record.field_name or "").upper()
    explicit_field = any(token in label for token in ("MATERIAL", "MATERIAAL", "GRADE", "QUALITY", "ALLOY"))
    if explicit_field:
        return [_clean_candidate(text)]

    values = [_clean_candidate(match.group("value")) for match in _MATERIAL_LABEL_RE.finditer(text)]
    if values:
        return [value for value in values if value]

    contextual = _CONTEXT_PREFIX_RE.match(text)
    if contextual:
        value = _clean_candidate(contextual.group("value"))
        return [value] if value else []

    stripped = text.strip("[](){}<>.,;:| ")
    if database is not None and database.resolve(stripped).resolved:
        return [stripped]
    full = _KNOWN_TOKEN_RE.fullmatch(stripped)
    if full:
        return [_clean_candidate(full.group(0))]

    # A recognized material token in a profile/BOM-like row is candidate
    # evidence. Bare numbers such as 8.8 are not scanned from arbitrary text.
    if _PROFILE_CONTEXT_RE.search(text):
        return [
            _clean_candidate(match.group(0)) for match in _KNOWN_TOKEN_RE.finditer(text)
            if not re.fullmatch(r"\d+\.\d+", match.group(0))
        ]
    return []


def collect_material_candidate_evidence(
    records: Iterable[SourceTextEvidence],
) -> MaterialCandidateEvidence:
    candidates: list[MaterialCandidate] = []
    ignored: list[str] = []
    try:
        from material_database import MaterialDatabase

        database = MaterialDatabase()
    except Exception:
        database = None

    seen: set[tuple[str, str, str, int | None]] = set()
    for record in records:
        kind_lower = f"{record.source_kind} {record.field_name}".lower()
        if any(token in kind_lower for token in _FORBIDDEN_SOURCE_TOKENS):
            ignored.append(f"{record.source_format}:{record.source_kind}:{record.source_reference}")
            continue
        for raw in _candidate_values(record, database=database):
            if not raw:
                continue
            resolution = database.resolve(
                raw,
                provenance={
                    "source_format": record.source_format,
                    "source_kind": record.source_kind,
                    "source_reference": record.source_reference,
                },
            ) if database is not None else None
            canonical = resolution.material_code if resolution is not None and resolution.resolved else ""
            catalog_status = resolution.status if resolution is not None else "unavailable"
            confidence = max(0.0, min(0.94, float(record.confidence)))
            if resolution is not None:
                confidence = min(confidence, float(resolution.confidence)) if resolution.resolved else 0.0
            identity = canonical or _key(raw)
            duplicate_key = (identity, record.source_kind, record.source_reference, record.page)
            if duplicate_key in seen:
                continue
            seen.add(duplicate_key)
            candidates.append(
                MaterialCandidate(
                    raw_value=raw,
                    normalized_value=_key(raw),
                    canonical_code=canonical,
                    catalog_status=catalog_status,
                    confidence=confidence,
                    source_format=record.source_format.upper(),
                    source_kind=record.source_kind,
                    source_reference=record.source_reference,
                    source_text=record.text,
                    page=record.page,
                    bbox=tuple(float(item) for item in record.bbox[:4]),
                )
            )

    candidates.sort(
        key=lambda item: (
            item.canonical_code or item.normalized_value,
            -item.confidence,
            item.source_kind,
            item.source_reference,
        )
    )
    identities = {item.canonical_code or item.normalized_value for item in candidates if item.normalized_value}
    if not candidates:
        return MaterialCandidateEvidence(
            status="unresolved",
            reason="Geen expliciete materiaaltekst of -metadata aangetroffen; er wordt geen default gebruikt.",
            ignored_sources=tuple(sorted(set(ignored))),
        )
    if len(identities) > 1:
        return MaterialCandidateEvidence(
            status="conflict",
            reason="Meerdere verschillende materiaalwaarden zijn aangetroffen; menselijke selectie is vereist.",
            candidates=tuple(candidates),
            ignored_sources=tuple(sorted(set(ignored))),
        )

    resolved = [item for item in candidates if item.canonical_code]
    if not resolved:
        return MaterialCandidateEvidence(
            status="unresolved",
            reason="Materiaaltekst is aanwezig maar niet exact of als expliciete catalogusalias opgelost.",
            candidates=tuple(candidates),
            ignored_sources=tuple(sorted(set(ignored))),
        )
    selected = max(resolved, key=lambda item: item.confidence)
    return MaterialCandidateEvidence(
        status="candidate",
        selected_value=selected.canonical_code,
        confidence=selected.confidence,
        reason="Eén catalogusidentiteit heeft expliciet bronbewijs; bevestiging blijft vereist.",
        candidates=tuple(candidates),
        ignored_sources=tuple(sorted(set(ignored))),
    )


def pdf_material_records(path: str | Path) -> list[SourceTextEvidence]:
    """Read real PDF text spans; no OCR/AI/visual material guessing occurs."""
    import pymupdf

    source = Path(path)
    records: list[SourceTextEvidence] = []
    with pymupdf.open(source) as document:
        for page_number, page in enumerate(document, 1):
            for block_index, block in enumerate(page.get_text("dict").get("blocks", [])):
                for line_index, line in enumerate(block.get("lines", [])):
                    text = " ".join(str(span.get("text", "")) for span in line.get("spans", []))
                    records.append(SourceTextEvidence(
                        text=text, source_format="PDF", source_kind="vector_text",
                        source_reference=f"{source.name}:page:{page_number}:block:{block_index}:line:{line_index}",
                        confidence=0.90, page=page_number,
                        bbox=tuple(line.get("bbox", ())),
                    ))
        for name, value in (document.metadata or {}).items():
            records.append(SourceTextEvidence(
                text=str(value or ""), source_format="PDF", source_kind="document_metadata",
                source_reference=f"{source.name}:metadata:{name}", confidence=0.80,
                field_name=str(name),
            ))
    return records


def _dxf_text(value: str) -> str:
    # Preserve unknown formatting as evidence instead of guessing through it.
    value = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda match: chr(int(match.group(1), 16)), value)
    value = value.replace(r"\P", "\n").replace(r"\~", " ")
    value = re.sub(r"\\[ACFHQTW][^;]*;", "", value, flags=re.IGNORECASE)
    return value.strip("{} ")


def dxf_material_records(path: str | Path) -> list[SourceTextEvidence]:
    """Read ASCII DXF TEXT/MTEXT/attributes/layer names without a CAD kernel.

    Entity handles and attribute tags are retained. Binary DXF is explicitly
    unsupported here; colours, dimensions, geometry and render materials are
    deliberately never interpreted as a manufacturing material grade.
    """
    source = Path(path)
    raw = source.read_bytes()
    if raw.startswith(b"AutoCAD Binary DXF") or b"\0" in raw[:256]:
        raise ValueError("Binaire DXF vereist expliciete conversie naar ASCII DXF voor materiaaltekstextractie.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        codepage = re.search(rb"\$DWGCODEPAGE\s*\r?\n\s*3\s*\r?\n\s*ANSI_(\d+)", raw)
        encoding = f"cp{codepage.group(1).decode('ascii')}" if codepage else "cp1252"
        text = raw.decode(encoding, errors="strict")
    lines = text.splitlines()
    if len(lines) % 2:
        raise ValueError("Ongeldige ASCII DXF: onvolledig groepcode/waarde-paar.")
    groups: list[tuple[str, list[tuple[int, str]]]] = []
    current: list[tuple[int, str]] = []
    kind = ""
    for index in range(0, len(lines), 2):
        try:
            code = int(lines[index].strip())
        except ValueError as exc:
            raise ValueError(f"Ongeldige DXF groepcode op regel {index + 1}.") from exc
        value = lines[index + 1].strip()
        if code == 0:
            if kind:
                groups.append((kind, current))
            kind, current = value.upper(), []
        else:
            current.append((code, value))
    if kind:
        groups.append((kind, current))
    if not any(kind == "EOF" for kind, _ in groups):
        raise ValueError("Ongeldige ASCII DXF: EOF-markering ontbreekt.")

    records: list[SourceTextEvidence] = []
    for index, (kind, fields) in enumerate(groups):
        handle = next((value for code, value in fields if code == 5), str(index))
        reference = f"{source.name}:{kind}:{handle}"
        if kind in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            text_codes = {1, 3} if kind == "MTEXT" else {1}
            text = _dxf_text("".join(value for code, value in fields if code in text_codes))
            tag = next((value for code, value in fields if code == 2), "") if kind in {"ATTRIB", "ATTDEF"} else ""
            for line_index, line in enumerate(text.splitlines()):
                records.append(SourceTextEvidence(
                    text=line, source_format="DXF", source_kind=f"{kind.lower()}_text",
                    source_reference=f"{reference}:line:{line_index}", confidence=0.90,
                    field_name=tag,
                ))
        if kind == "LAYER":
            for code, value in fields:
                if code == 2:
                    records.append(SourceTextEvidence(
                        text=value, source_format="DXF", source_kind="layer_name",
                        source_reference=reference, confidence=0.65,
                    ))
        # Entity layer assignments can carry explicit grade metadata even when
        # the table has been stripped; never read the entity's colour fields.
        for code, value in fields:
            if code == 8:
                records.append(SourceTextEvidence(
                    text=value, source_format="DXF", source_kind="entity_layer_name",
                    source_reference=reference, confidence=0.65,
                ))
    return records


def analyze_source_material_document(path: str | Path) -> dict[str, Any]:
    """Return portable candidate evidence for an auxiliary project document.

    These candidates are document-scoped, not assigned to every project part.
    Failures are visible in the manifest and always leave material unresolved.
    """
    source = Path(path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    records: list[SourceTextEvidence] = []
    extraction_status = "complete"
    error = ""
    try:
        if source.suffix.lower() == ".pdf":
            records = pdf_material_records(source)
        elif source.suffix.lower() == ".dxf":
            records = dxf_material_records(source)
        else:
            raise ValueError(f"Materiaalbewijs-extractie niet ondersteund voor {source.suffix}.")
    except ImportError as exc:
        extraction_status, error = "dependency_unavailable", str(exc)
    except Exception as exc:
        extraction_status, error = "failed", str(exc)
    evidence = collect_material_candidate_evidence(records).to_dict()
    return {
        **evidence,
        "source_sha256": digest,
        "source_file": source.name,
        "extraction_status": extraction_status,
        "extraction_error": error,
        "text_record_count": len(records),
        "scope": "document_unassigned",
        "part_assignment_required": True,
        "production_export_allowed": False,
    }


def confirm_material_candidate_evidence(
    evidence: dict[str, Any], value: str, *, reviewer: str, reviewed_at: str,
) -> dict[str, Any]:
    """Record explicit human selection without discarding original candidates."""
    from material_database import MaterialDatabase

    if not str(reviewer).strip():
        raise ValueError("Materiaalbevestiging vereist een reviewer.")
    resolution = MaterialDatabase().resolve(value)
    if not resolution.resolved:
        raise ValueError("Materiaal is niet bekend in de catalogus; voeg eerst een gecontroleerde materiaaldefinitie toe.")
    return {
        **evidence,
        "source_status": evidence.get("source_status", evidence.get("status", "unresolved")),
        "status": "human_confirmed",
        "selected_value": resolution.material_code,
        "confidence": 1.0,
        "review_status": "confirmed",
        "material_grade_proven": True,
        "human_confirmation": {
            "reviewer": str(reviewer).strip(), "reviewed_at": str(reviewed_at),
            "raw_value": str(value), "material_code": resolution.material_code,
            "method": "explicit_human_material_selection",
        },
    }


__all__ = [
    "MaterialCandidate",
    "MaterialCandidateEvidence",
    "SourceTextEvidence",
    "collect_material_candidate_evidence",
    "confirm_material_candidate_evidence",
    "analyze_source_material_document",
    "dxf_material_records",
    "pdf_material_records",
]
