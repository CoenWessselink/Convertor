"""Veilige AI-laag voor technische PDF-interpretatie.

Ontwerpregels:
- AI interpreteert uitsluitend semantiek, documentstructuur en layoutvoorstellen.
- Exacte contouren, gatposities, maatwaarden, NC1/DSTV, STEP en IFC worden
  uitsluitend door de deterministische geometriekern gemaakt en gevalideerd.
- Cloud-AI staat standaard uit en vereist per aanroep expliciete toestemming.
- De lokale provider werkt volledig offline en is altijd de eerste analyselaag.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
import uuid
from typing import Any, Callable, Iterable, Protocol


OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.6"


class AIConfigurationError(RuntimeError):
    """De gekozen AI-provider is niet geïnstalleerd of niet geconfigureerd."""


class CloudAIConsentError(PermissionError):
    """Cloudverwerking werd gevraagd zonder expliciete toestemming."""


class AIResponseError(ValueError):
    """Een AI-response voldoet niet aan het begrensde adviescontract."""

# AI mag deze semantische velden voorstellen. Exacte featurecoordinaten vallen
# bewust buiten de lijst.
ALLOWED_FIELD_NAMES = {
    "project",
    "project_number",
    "order_number",
    "drawing_number",
    "position",
    "part_number",
    "mark",
    "assembly_id",
    "subject",
    "client",
    "work",
    "material",
    "material_grade",
    "profile",
    "profile_category",
    "length_text",
    "length_mm",
    "quantity",
    "total_quantity",
    "scale",
    "sheet_format",
    "drawing_status",
    "revision",
    "drawn_by",
    "checked_by",
    "date",
    "units",
    "hole_callouts",
    "radius_callouts",
    "radius_callouts_mm",
    "general_notes",
    "weld_notes",
    "coating",
}

# Geen enkele cloudresponse mag productiegeometrie of seriële machinecode
# bevatten. De controle loopt recursief over alle JSON-sleutels.
FORBIDDEN_KEY_FRAGMENTS = {
    "nc1",
    "dstv",
    "step",
    "ifc",
    "vertex",
    "vertices",
    "coordinate",
    "contour",
    "solid",
    "brep",
    "mesh",
    "toolpath",
    "machine_code",
    "gcode",
    "geometry",
    "hole_position",
    "feature_position",
}

SYSTEM_INSTRUCTIONS = """Je bent een semantische assistent voor technische staaltekeningen.
Je mag alleen tekstvelden, documentclassificatie, aanzichtnamen, conflicten,
controlevragen en layoutvoorstellen teruggeven. Genereer nooit NC1/DSTV-regels,
STEP/IFC-data, contourcoordinaten, gatposities, 3D-geometrie of productie-
vrijgave. Neem onzekere gegevens niet als feit aan. Gebruik de meegeleverde
JSON-schema-uitvoer exact. Geschreven maatwaarden mogen als tekstvoorstel worden
herkend, maar exacte geometrie wordt later deterministisch gekoppeld en berekend.
"""

# Structured Outputs gebruikt een beperkte JSON-Schema-subset. Nullable velden
# worden daarom met anyOf beschreven en niet met een type-array.
AI_RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_type": {"type": "string"},
        "language": {"type": "string"},
        "fields": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "value": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "integer"},
                            {"type": "boolean"},
                            {"type": "null"},
                        ]
                    },
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "page": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
                    "evidence": {"type": "string"},
                },
                "required": ["name", "value", "confidence", "page", "evidence"],
            },
        },
        "views": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "page": {"type": "integer"},
                    "view_type": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "evidence": {"type": "string"},
                },
                "required": ["page", "view_type", "confidence", "evidence"],
            },
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string"},
                    "message": {"type": "string"},
                    "alternatives": {"type": "array", "items": {"type": "string"}},
                    "blocking": {"type": "boolean"},
                },
                "required": ["field", "message", "alternatives", "blocking"],
            },
        },
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string"},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "blocking": {"type": "boolean"},
                },
                "required": ["field", "question", "options", "blocking"],
            },
        },
        "layout_suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "document_type",
        "language",
        "fields",
        "views",
        "conflicts",
        "questions",
        "layout_suggestions",
    ],
}


@dataclass
class DocumentEvidence:
    source_name: str
    page_count: int
    text: str = ""
    page_texts: list[str] = field(default_factory=list)
    classification: str = "unknown"
    page_summaries: list[dict[str, Any]] = field(default_factory=list)
    vector_summary: dict[str, Any] = field(default_factory=dict)
    detected_fields: dict[str, Any] = field(default_factory=dict)
    deterministic_conflicts: list[dict[str, Any]] = field(default_factory=list)
    missing_critical_fields: list[str] = field(default_factory=list)

    def to_context(self) -> dict[str, Any]:
        # Geen binaire broninhoud; alleen reeds lokaal geëxtraheerde context.
        return {
            "source_name": self.source_name,
            "page_count": int(self.page_count),
            "classification": self.classification,
            "page_summaries": self.page_summaries,
            "vector_summary": self.vector_summary,
            "detected_fields": self.detected_fields,
            "deterministic_conflicts": self.deterministic_conflicts,
            "missing_critical_fields": self.missing_critical_fields,
            "native_text": self.text[:120_000],
        }


@dataclass
class AIFieldProposal:
    name: str
    value: Any
    confidence: float
    page: int | None = None
    evidence: str = ""
    method: str = "ai_semantic"


@dataclass
class AIViewProposal:
    page: int
    view_type: str
    confidence: float
    evidence: str = ""


@dataclass
class AIConflict:
    field: str
    message: str
    alternatives: list[str] = field(default_factory=list)
    blocking: bool = True


@dataclass
class AIQuestion:
    field: str
    question: str
    options: list[str] = field(default_factory=list)
    blocking: bool = True


@dataclass
class AILayoutProposal:
    sheet_format: str = "A4"
    orientation: str = "landscape"
    views: list[str] = field(default_factory=list)
    detail_views: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class AIAnalysisResult:
    provider: str
    model: str = ""
    document_type: str = "technical_drawing"
    language: str = "unknown"
    fields: list[AIFieldProposal] = field(default_factory=list)
    views: list[AIViewProposal] = field(default_factory=list)
    conflicts: list[AIConflict] = field(default_factory=list)
    questions: list[AIQuestion] = field(default_factory=list)
    layout_suggestions: list[str] = field(default_factory=list)
    layout: AILayoutProposal | None = None
    audit: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Backwards-compatible naam voor de cloudprovider-interface.
AIInterpretation = AIAnalysisResult
AISemanticField = AIFieldProposal


class AIProvider(Protocol):
    name: str

    def interpret(
        self,
        document_context: dict[str, Any],
        page_images: Iterable[bytes] = (),
        *,
        cloud_consent: bool = False,
    ) -> AIAnalysisResult:
        ...


def _number(value: str) -> float:
    return float(value.replace(" ", "").replace(",", "."))


def _clean_profile(value: str) -> str:
    return re.sub(r"\s+", "", value.upper()).replace("X", "*")


def _evidence(text: str, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


class LocalDrawingAI:
    """Local-first semantische interpretatie en reproduceerbaar layoutadvies.

    Dit is bewust geen geometrieherkenner. De provider leest alleen native/OCR-
    tekst en produceert voorstellen met provenance en confidence.
    """

    name = "local-semantic-rules-v1"

    _profile = (
        r"(?:STRIP|PL)\s*\d+(?:[.,]\d+)?\s*[xX*]\s*\d+(?:[.,]\d+)?"
        r"|(?:HEA|HEB|HEM|IPE|IPN|UPN|UPE|UNP|RHS|SHS|CHS|L|T)\s*[-/]?\s*\d+(?:[./-]\d+)*"
        r"|D\s*\d+(?:[.,]\d+)?"
    )

    def _add(
        self,
        fields: dict[str, AIFieldProposal],
        name: str,
        value: Any,
        confidence: float,
        evidence: str,
        *,
        page: int | None = 1,
    ) -> None:
        candidate = AIFieldProposal(
            name=name,
            value=value,
            confidence=max(0.0, min(1.0, float(confidence))),
            page=page,
            evidence=_evidence(evidence),
            method=self.name,
        )
        current = fields.get(name)
        if current is None or candidate.confidence > current.confidence:
            fields[name] = candidate

    def analyse(self, evidence: DocumentEvidence) -> AIAnalysisResult:
        text = evidence.text or "\n".join(evidence.page_texts)
        flat = re.sub(r"\s+", " ", text.replace("×", "*")).strip()
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        fields: dict[str, AIFieldProposal] = {}
        conflicts: list[AIConflict] = []
        questions: list[AIQuestion] = []

        # Stukregel: Pos Profiel Materiaal Lengte Aantal Merk.
        bom_pattern = re.compile(
            rf"(?P<position>[A-Z][A-Z0-9_.-]{{1,30}})\s+"
            rf"(?P<profile>{self._profile})\s+"
            r"(?P<material>S\d{3}(?:[A-Z0-9+.-]*))\s+"
            r"(?P<length>\d+(?:[.,]\d+)?)\s+"
            r"(?P<quantity>\d+)\s+"
            r"(?P<mark>[A-Z][A-Z0-9_.-]{1,30})",
            re.IGNORECASE,
        )
        bom = bom_pattern.search(flat)
        if bom:
            row = bom.group(0)
            self._add(fields, "position", bom.group("position").upper(), 0.995, row)
            self._add(fields, "part_number", bom.group("position").upper(), 0.99, row)
            self._add(fields, "profile", _clean_profile(bom.group("profile")), 0.995, row)
            self._add(fields, "material", bom.group("material").upper(), 0.995, row)
            self._add(fields, "material_grade", bom.group("material").upper(), 0.99, row)
            self._add(fields, "length_mm", _number(bom.group("length")), 0.995, row)
            self._add(fields, "quantity", int(bom.group("quantity")), 0.995, row)
            self._add(fields, "mark", bom.group("mark").upper(), 0.995, row)

        # Individuele fallbackvelden wanneer geen complete stukregel aanwezig is.
        profile_matches = list(re.finditer(self._profile, flat, re.IGNORECASE))
        if profile_matches:
            profiles = [_clean_profile(item.group(0)) for item in profile_matches]
            unique_profiles = list(dict.fromkeys(profiles))
            self._add(fields, "profile", unique_profiles[0], 0.92 if len(unique_profiles) == 1 else 0.72, profile_matches[0].group(0))
            if len(unique_profiles) > 1:
                conflicts.append(
                    AIConflict(
                        field="profile",
                        message="Meerdere verschillende profielbenamingen gevonden.",
                        alternatives=unique_profiles[:8],
                        blocking=True,
                    )
                )

        materials = list(dict.fromkeys(match.group(0).upper() for match in re.finditer(r"\bS\d{3}(?:[A-Z0-9+.-]*)\b", flat)))
        if materials:
            self._add(fields, "material", materials[0], 0.91 if len(materials) == 1 else 0.70, materials[0])
            if len(materials) > 1:
                conflicts.append(
                    AIConflict(
                        field="material",
                        message="Meerdere materiaalkwaliteiten gevonden; controleer welke voor het onderdeel geldt.",
                        alternatives=materials[:8],
                        blocking=True,
                    )
                )

        total_match = re.search(r"Totaal\s+aantal(?:\s+keer\s+uit\s+te\s+voeren)?\s*[:=]?\s*(\d+)", flat, re.IGNORECASE)
        if total_match:
            self._add(fields, "total_quantity", int(total_match.group(1)), 0.99, total_match.group(0))

        scale_match = re.search(r"(?:Schaal\s*[:=]?\s*)?(1\s*:\s*\d+(?:[.,]\d+)?)", flat, re.IGNORECASE)
        if scale_match:
            self._add(fields, "scale", re.sub(r"\s+", "", scale_match.group(1)), 0.97, scale_match.group(0))

        sheet_match = re.search(r"\bA[1-4]\b", flat, re.IGNORECASE)
        if sheet_match:
            self._add(fields, "sheet_format", sheet_match.group(0).upper(), 0.96, sheet_match.group(0))

        hole_callouts: list[dict[str, Any]] = []
        for match in re.finditer(
            r"(?P<count>\d+)\s*[*xX]\s*(?:Ø|DIA\.?|DIAM\.?|O/)\s*(?P<diameter>\d+(?:[.,]\d+)?)",
            text.replace("×", "*"),
            re.IGNORECASE,
        ):
            hole_callouts.append(
                {
                    "count": int(match.group("count")),
                    "diameter_mm": _number(match.group("diameter")),
                    "text": _evidence(match.group(0), 80),
                }
            )
        if hole_callouts:
            self._add(fields, "hole_callouts", hole_callouts, 0.97, "; ".join(item["text"] for item in hole_callouts))

        radii = [_number(match.group(1)) for match in re.finditer(r"\bR\s*([0-9]+(?:[.,][0-9]+)?)", text, re.IGNORECASE)]
        if radii:
            self._add(fields, "radius_callouts_mm", radii, 0.94, ", ".join(f"R {value:g}" for value in radii))

        # Labelgebaseerde tekstvelden.
        label_patterns = {
            "drawing_number": r"(?:Tekening(?:nummer)?|Drawing\s*no\.?)[\s:=-]*([A-Z0-9_.-]+)",
            "project_number": r"(?:Project(?:nummer)?)[\s:=-]*([A-Z0-9_.-]+)",
            "drawn_by": r"(?:Getekend|Drawn\s*by)[\s:=-]*([^|;]{2,40})",
            "revision": r"(?:Revisie|Revision|Rev\.?)[\s:=-]*([A-Z0-9_.-]+)",
            "drawing_status": r"(?:Status)[\s:=-]*([A-Z][A-Z ]{2,30})",
        }
        for name, pattern in label_patterns.items():
            match = re.search(pattern, flat, re.IGNORECASE)
            if match:
                self._add(fields, name, match.group(1).strip(), 0.82, match.group(0))

        # Onderwerp: geef inhoudelijke hoofdletters-regel voorrang.
        subject_candidates = []
        table_header_tokens = {"POS", "PROFIEL", "MATERIAAL", "LENGTE", "AANTAL", "MERK"}
        for line in lines:
            upper = line.upper()
            words = set(re.findall(r"[A-ZÀ-ÖØ-Ý0-9]+", upper))
            # Een stuklijstkop zoals "Pos Profiel Materiaal Lengte Aantal Merk"
            # is geen onderwerp, ook al bevat die het woord PROFIEL.
            if len(words & table_header_tokens) >= 3:
                continue
            if any(token in upper for token in ("LOSSE PLAAT", "LIGGER", "KOLOM", "ONDERDEELTEKENING", "PROFIEL")):
                if len(line) <= 80 and not re.search(r"STRIP|HEA|HEB|IPE|UPN|S\d{3}", upper):
                    subject_candidates.append(line)
        if subject_candidates:
            self._add(fields, "subject", subject_candidates[0], 0.90, subject_candidates[0])

        # Eenheden zijn bij de ondersteunde DSTV/staaltekeningen standaard alleen
        # een voorstel; de geometrische laag moet dit nog consistent bevestigen.
        if re.search(r"\bmm\b|millimeter", flat, re.IGNORECASE):
            self._add(fields, "units", "mm", 0.98, "mm")
        elif fields.get("profile") or fields.get("length_mm"):
            self._add(fields, "units", "mm", 0.80, "impliciet uit profiel-/maataanduiding")

        # Reeds deterministisch gedetecteerde velden mogen als extra evidence
        # worden toegevoegd, maar niet met een hogere confidence dan de bron opgeeft.
        for name, item in evidence.detected_fields.items():
            if name not in ALLOWED_FIELD_NAMES:
                continue
            if isinstance(item, dict):
                self._add(
                    fields,
                    name,
                    item.get("value"),
                    float(item.get("confidence", 0.0)),
                    str(item.get("evidence", "deterministische detectie")),
                    page=item.get("page"),
                )
            else:
                self._add(fields, name, item, 0.50, "deterministische detectie")

        critical = ("position", "profile", "material", "length_mm", "quantity")
        for name in critical:
            if name not in fields or fields[name].value in (None, "", 0):
                questions.append(
                    AIQuestion(
                        field=name,
                        question=f"Vul het ontbrekende kritische veld {name} in.",
                        blocking=True,
                    )
                )
        for conflict in evidence.deterministic_conflicts:
            conflicts.append(
                AIConflict(
                    field=str(conflict.get("field", "unknown")),
                    message=str(conflict.get("message", "Tegenstrijdige gegevens gevonden.")),
                    alternatives=[str(value) for value in conflict.get("alternatives") or []],
                    blocking=bool(conflict.get("blocking", True)),
                )
            )

        language = "nl" if re.search(r"\b(tekening|materiaal|aantal|schaal|getekend)\b", flat, re.IGNORECASE) else "unknown"
        document_type = "part_drawing" if fields.get("position") or fields.get("profile") else "technical_drawing"
        return AIAnalysisResult(
            provider=self.name,
            document_type=document_type,
            language=language,
            fields=list(fields.values()),
            conflicts=conflicts,
            questions=questions,
            audit={
                "local_only": True,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "source_text_sha256": hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest(),
            },
        )

    # Alias voor de protocolnaam.
    def interpret(
        self,
        document_context: dict[str, Any],
        page_images: Iterable[bytes] = (),
        *,
        cloud_consent: bool = False,
    ) -> AIAnalysisResult:
        del page_images, cloud_consent
        evidence = DocumentEvidence(
            source_name=str(document_context.get("source_name", "document.pdf")),
            page_count=int(document_context.get("page_count", 1)),
            text=str(document_context.get("native_text") or document_context.get("extracted_text") or ""),
            classification=str(document_context.get("classification", "unknown")),
            page_summaries=list(document_context.get("page_summaries") or []),
            vector_summary=dict(document_context.get("vector_summary") or {}),
            detected_fields=dict(document_context.get("detected_fields") or {}),
            deterministic_conflicts=list(document_context.get("deterministic_conflicts") or []),
            missing_critical_fields=list(document_context.get("missing_critical_fields") or []),
        )
        return self.analyse(evidence)

    def suggest_layout(self, part: Any) -> AILayoutProposal:
        profile_type = str(getattr(part, "profile_type", "") or "").upper()
        holes = list(getattr(part, "holes", []) or [])
        if profile_type == "B":
            views = ["front", "edge"]
            rationale = ["Plaatvlak is het primaire productieaanzicht.", "Dikte wordt in een randaanzicht getoond."]
            if holes or getattr(getattr(part, "header", None), "radius", 0.0):
                rationale.append("Gaten/contourkenmerken worden in het primaire plaatvlak gemaatvoerd.")
            return AILayoutProposal(
                sheet_format="A4",
                orientation="landscape",
                views=views + ["isometric"],
                rationale=rationale,
                confidence=0.94,
            )
        return AILayoutProposal(
            sheet_format="A4",
            orientation="landscape",
            views=["front", "top", "end", "isometric"],
            rationale=["Profielen vereisen lengteaanzicht en doorsnede/eindaanzicht."],
            confidence=0.90,
        )


class LocalSemanticProvider(LocalDrawingAI):
    """Compatibele naam voor oudere aanroepen."""


Transport = Callable[[urllib.request.Request, float], tuple[int, bytes, dict[str, str]]]


def _default_transport(request: urllib.request.Request, timeout: float) -> tuple[int, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured HTTPS endpoint
            return int(response.status), response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(), dict(exc.headers.items()) if exc.headers else {}


def _extract_output_text(response: dict[str, Any]) -> str:
    direct = response.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    for item in response.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
            if isinstance(content, dict) and content.get("type") == "refusal":
                raise RuntimeError("Cloud-AI weigerde de interpretatie: " + str(content.get("refusal", "")))
    status = str(response.get("status", ""))
    incomplete = response.get("incomplete_details") or {}
    if status == "incomplete":
        raise RuntimeError("Cloud-AI-response is onvolledig: " + str(incomplete.get("reason", "unknown")))
    raise ValueError("AI-response bevat geen output_text")


def _scan_forbidden_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"AI-response bevat verboden productiesleutel {path}.{key}")
            _scan_forbidden_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, f"{path}[{index}]")
    elif isinstance(value, str):
        suspicious = (
            r"ISO-10303-21",
            r"\bIFC[A-Z0-9_]+\s*\(",
            r"(?:^|\n)\s*(?:ST|AK|IK|BO|EN)\s*(?:\n|$)",
            r"\b(?:NC1|DSTV|GCODE|TOOLPATH)\b",
        )
        import re

        for pattern in suspicious:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"AI-response bevat verboden productie-inhoud in {path}")


def validate_ai_payload(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("AI-uitvoer is geen JSON-object")
    allowed_top = set(AI_RESULT_SCHEMA["properties"])
    extra = set(data) - allowed_top
    if extra:
        raise ValueError("AI-uitvoer bevat niet-toegestane velden: " + ", ".join(sorted(extra)))
    required = set(AI_RESULT_SCHEMA["required"])
    missing = required - set(data)
    if missing:
        raise ValueError("AI-uitvoer mist verplichte velden: " + ", ".join(sorted(missing)))
    _scan_forbidden_keys(data)
    for field_item in data.get("fields") or []:
        name = str(field_item.get("name", ""))
        if name not in ALLOWED_FIELD_NAMES:
            raise ValueError(f"AI probeerde niet-toegestaan semantisch veld {name!r} te leveren")
        confidence = float(field_item.get("confidence", -1.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"AI-confidence voor {name!r} ligt buiten 0..1")
    return data


class OpenAIResponsesProvider:
    """Optionele cloudprovider via de OpenAI Responses API.

    Alleen gerenderde pagina-afbeeldingen en lokaal geëxtraheerde semantische
    context worden verzonden. Elke aanroep vereist ``cloud_consent=True``.
    De request gebruikt ``store=False`` en Structured Outputs.
    """

    name = "openai-responses"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        endpoint: str = OPENAI_RESPONSES_ENDPOINT,
        timeout_seconds: float = 90.0,
        transport: Transport | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("Voor cloud-AI moet een expliciet OpenAI-model worden ingesteld")
        self.model = model.strip()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.endpoint = endpoint or OPENAI_RESPONSES_ENDPOINT
        if not self.endpoint.lower().startswith("https://"):
            raise ValueError("Cloud-AI-endpoint moet HTTPS gebruiken")
        self.timeout_seconds = float(timeout_seconds)
        self.transport = transport or _default_transport

    def interpret(
        self,
        document_context: dict[str, Any],
        page_images: Iterable[bytes] = (),
        *,
        cloud_consent: bool = False,
    ) -> AIAnalysisResult:
        if not cloud_consent:
            raise PermissionError("Cloud-AI is geblokkeerd: expliciete toestemming ontbreekt")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY ontbreekt")

        images = list(page_images)
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": (
                    "Interpreteer uitsluitend semantische tekeninggegevens. "
                    "De lokale analysecontext volgt als JSON:\n"
                    + json.dumps(document_context, ensure_ascii=False, sort_keys=True)
                ),
            }
        ]
        image_hashes: list[str] = []
        for image in images:
            image_hashes.append(hashlib.sha256(image).hexdigest())
            data_url = "data:image/png;base64," + base64.b64encode(image).decode("ascii")
            content.append({"type": "input_image", "image_url": data_url, "detail": "high"})

        request_payload = {
            "model": self.model,
            "store": False,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": [{"role": "user", "content": content}],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "technical_drawing_semantics",
                    "strict": True,
                    "schema": AI_RESULT_SCHEMA,
                }
            },
        }
        body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
        client_request_id = str(uuid.uuid4())
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "NC1-STEP-IFC-Converter/0.5",
                "X-Client-Request-Id": client_request_id,
            },
        )
        status, response_body, headers = self.transport(request, self.timeout_seconds)
        if status < 200 or status >= 300:
            safe_message = response_body.decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"Cloud-AI gaf HTTP {status}: {safe_message}")
        response = json.loads(response_body.decode("utf-8"))
        parsed = validate_ai_payload(json.loads(_extract_output_text(response)))

        return AIAnalysisResult(
            provider=self.name,
            model=self.model,
            document_type=str(parsed.get("document_type", "technical_drawing")),
            language=str(parsed.get("language", "unknown")),
            fields=[AIFieldProposal(method=self.name, **item) for item in parsed.get("fields") or []],
            views=[AIViewProposal(**item) for item in parsed.get("views") or []],
            conflicts=[AIConflict(**item) for item in parsed.get("conflicts") or []],
            questions=[AIQuestion(**item) for item in parsed.get("questions") or []],
            layout_suggestions=[str(item) for item in parsed.get("layout_suggestions") or []],
            audit={
                "provider": self.name,
                "model": self.model,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "cloud_consent": True,
                "store": False,
                "image_sha256": image_hashes,
                "request_id": response.get("id", ""),
                "client_request_id": client_request_id,
                "response_headers": {
                    key: value
                    for key, value in headers.items()
                    if key.lower() in {"x-request-id", "openai-processing-ms"}
                },
            },
        )


def _normalise_cloud_semantics(result: AIAnalysisResult) -> AIAnalysisResult:
    """Normaliseer calloutteksten zonder geometrie te construeren."""

    for item in result.fields:
        if item.name == "length_text" and isinstance(item.value, str):
            match = re.search(r"\d+(?:[.,]\d+)?", item.value)
            if match:
                item.name = "length_mm"
                item.value = _number(match.group(0))
        elif item.name == "hole_callouts" and isinstance(item.value, str):
            match = re.search(r"(\d+)\s*[*xX×]\s*(?:Ø|DIA\.?|O/)\s*(\d+(?:[.,]\d+)?)", item.value, re.IGNORECASE)
            if match:
                item.value = [{"count": int(match.group(1)), "diameter_mm": _number(match.group(2)), "text": item.value}]
        elif item.name in {"radius_callouts", "radius_callouts_mm"} and isinstance(item.value, str):
            values = [_number(match.group(1)) for match in re.finditer(r"R\s*(\d+(?:[.,]\d+)?)", item.value, re.IGNORECASE)]
            item.name = "radius_callouts_mm"
            item.value = values
    return result


def _merge_results(local: AIAnalysisResult, cloud: AIAnalysisResult) -> AIAnalysisResult:
    field_map = {item.name: item for item in local.fields}
    for item in cloud.fields:
        current = field_map.get(item.name)
        if current is None or item.confidence > current.confidence:
            field_map[item.name] = item
    view_map: dict[tuple[int, str], AIViewProposal] = {
        (item.page, item.view_type.lower()): item for item in local.views
    }
    for item in cloud.views:
        key = (item.page, item.view_type.lower())
        current = view_map.get(key)
        if current is None or item.confidence > current.confidence:
            view_map[key] = item
    return AIAnalysisResult(
        provider=f"{local.provider}+{cloud.provider}",
        model=cloud.model,
        document_type=cloud.document_type or local.document_type,
        language=cloud.language if cloud.language != "unknown" else local.language,
        fields=list(field_map.values()),
        views=list(view_map.values()),
        conflicts=local.conflicts + cloud.conflicts,
        questions=local.questions + cloud.questions,
        layout_suggestions=local.layout_suggestions + cloud.layout_suggestions,
        audit={"local": local.audit, "cloud": cloud.audit},
    )


def analyse_with_ai(
    evidence: DocumentEvidence,
    *,
    mode: str = "local",
    cloud_endpoint: str = "",
    cloud_api_key: str = "",
    cloud_model: str = "",
    allow_cloud: bool = False,
    page_images: Iterable[bytes] = (),
) -> AIAnalysisResult:
    selected = (mode or "local").strip().lower()
    if selected in {"off", "none", "disabled"}:
        return AIAnalysisResult(
            provider="disabled",
            questions=[
                AIQuestion(field=name, question=f"Vul het ontbrekende kritische veld {name} in.", blocking=True)
                for name in ("position", "profile", "material", "length_mm", "quantity")
            ],
            audit={"local_only": True, "disabled": True, "processed_at": datetime.now(timezone.utc).isoformat()},
        )

    local = LocalDrawingAI().analyse(evidence)
    if selected in {"local", "offline", "rules"}:
        return local
    if selected not in {"cloud", "openai", "hybrid"}:
        raise ValueError(f"Onbekende AI-modus {mode!r}; kies off, local of cloud")
    if not allow_cloud:
        raise PermissionError("Cloud-AI is geblokkeerd: expliciete toestemming ontbreekt")

    context = evidence.to_context()
    context["detected_fields"] = {
        item.name: {
            "value": item.value,
            "confidence": item.confidence,
            "page": item.page,
            "evidence": item.evidence,
        }
        for item in local.fields
    }
    provider = OpenAIResponsesProvider(
        model=cloud_model or os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        api_key=cloud_api_key or None,
        endpoint=cloud_endpoint or OPENAI_RESPONSES_ENDPOINT,
    )
    cloud = _normalise_cloud_semantics(
        provider.interpret(context, page_images, cloud_consent=True)
    )
    return _merge_results(local, cloud)


def _question_id(prefix: str, field_name: str, message: str) -> str:
    digest = hashlib.sha256(f"{field_name}|{message}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def apply_ai_analysis(part: Any, result: AIAnalysisResult) -> Any:
    """Voeg uitsluitend semantiek/provenance toe aan een CanonicalPart.

    De functie importeert canonical_model lazy om circulaire imports te vermijden.
    Productiegeometrie, contouren en gaten worden nooit aangepast.
    """

    from canonical_model import CanonicalFieldValue, CanonicalQuestion

    updated = part.clone()
    for proposal in result.fields:
        if proposal.name not in ALLOWED_FIELD_NAMES:
            continue
        name = proposal.name
        # Gestandaardiseerde aliases voor de deterministische PDF-laag.
        if name == "length_text" and isinstance(proposal.value, str):
            match = re.search(r"\d+(?:[.,]\d+)?", proposal.value)
            if match:
                name = "length_mm"
                proposal = AIFieldProposal(
                    name=name,
                    value=_number(match.group(0)),
                    confidence=proposal.confidence,
                    page=proposal.page,
                    evidence=proposal.evidence,
                    method=proposal.method,
                )
        if name == "radius_callouts":
            name = "radius_callouts_mm"
        current = updated.field_values.get(name)
        if current is None or float(proposal.confidence) >= float(current.confidence):
            updated.field_values[name] = CanonicalFieldValue(
                value=proposal.value,
                source_page=proposal.page,
                method=proposal.method or result.provider,
                confidence=max(0.0, min(1.0, float(proposal.confidence))),
                status="automatic",
                evidence=proposal.evidence,
            )

    existing_ids = {item.question_id for item in updated.validation.unresolved_questions}
    for question in result.questions:
        qid = _question_id("ai-question", question.field, question.question)
        if qid not in existing_ids:
            updated.validation.unresolved_questions.append(
                CanonicalQuestion(
                    question_id=qid,
                    field_name=question.field,
                    message=question.question,
                    options=[str(value) for value in question.options],
                    blocking=bool(question.blocking),
                )
            )
            existing_ids.add(qid)
    for conflict in result.conflicts:
        qid = _question_id("ai-conflict", conflict.field, conflict.message)
        if qid not in existing_ids:
            updated.validation.unresolved_questions.append(
                CanonicalQuestion(
                    question_id=qid,
                    field_name=conflict.field,
                    message=conflict.message,
                    options=[str(value) for value in conflict.alternatives],
                    blocking=bool(conflict.blocking),
                )
            )
            existing_ids.add(qid)

    for view in result.views:
        updated.drawing.views.append(
            {
                "page": int(view.page),
                "view_type": view.view_type,
                "confidence": float(view.confidence),
                "source": result.provider,
                "evidence": view.evidence,
                "confirmed": False,
            }
        )
    if result.layout_suggestions:
        updated.properties["ai_layout_suggestions"] = list(result.layout_suggestions)

    blocking_open = any(
        question.blocking and question.status.lower() not in {"answered", "resolved", "dismissed"}
        for question in updated.validation.unresolved_questions
    )
    if blocking_open:
        updated.validation.production_export_allowed = False
        updated.validation.export_status = "review_required"
    updated.properties["ai_provider"] = result.provider
    updated.properties["ai_model"] = result.model
    updated.properties["ai_document_type"] = result.document_type
    updated.properties["ai_language"] = result.language
    updated.audit_log.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "ai_semantic_interpretation",
            "provider": result.provider,
            "model": result.model,
            "field_count": len(result.fields),
            "question_count": len(result.questions),
            "conflict_count": len(result.conflicts),
            "audit": result.audit,
        }
    )
    updated.validate()
    return updated


def page_images_from_paths(paths: Iterable[str | Path]) -> list[bytes]:
    return [Path(path).read_bytes() for path in paths]

# ---------------------------------------------------------------------------
# Canonical drawing-review API used by the integrated v0.5 PDF module.
# ---------------------------------------------------------------------------

@dataclass
class AISettings:
    """Runtime settings for the advisory drawing interpreter.

    Cloud processing is disabled by default. ``transport`` exists only for
    deterministic tests and enterprise gateways; normal users leave it unset.
    """

    provider: str = "none"  # none, local-rules, openai
    model: str = DEFAULT_OPENAI_MODEL
    allow_cloud: bool = False
    api_key: str = ""
    endpoint: str = OPENAI_RESPONSES_ENDPOINT
    max_pages: int = 3
    render_dpi: int = 144
    audit_log: str = ""
    timeout: float = 90.0
    transport: Callable[[urllib.request.Request, float], tuple[int, bytes, dict[str, str]]] | None = None


@dataclass
class AIFieldSuggestion:
    field_path: str
    value: Any
    confidence: float
    page: int = 1
    source_text: str = ""
    reason: str = ""

    def validate(self) -> None:
        if not self.field_path.strip():
            raise ValueError("AI-veldsuggestie mist field_path")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("AI-confidence moet tussen 0 en 1 liggen")
        if int(self.page) < 1:
            raise ValueError("AI-paginanummer moet 1 of hoger zijn")


@dataclass
class AIQuestionSuggestion:
    field_path: str
    question: str
    severity: str = "blocking"
    alternatives: list[str] = field(default_factory=list)
    page: int = 1
    reason: str = ""


@dataclass
class AIInterpretation:
    provider: str
    model: str
    fields: list[AIFieldSuggestion] = field(default_factory=list)
    questions: list[AIQuestionSuggestion] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    request_id: str = ""
    response_sha256: str = ""
    audit: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for item in self.fields:
            item.validate()
        for item in self.questions:
            if not item.field_path.strip() or not item.question.strip():
                raise ValueError("AI-vraag mist field_path of vraagtekst")
            if item.severity not in {"blocking", "warning", "information"}:
                raise ValueError(f"Ongeldige AI-vraagernst: {item.severity!r}")
            if int(item.page) < 1:
                raise ValueError("AI-vraag heeft een ongeldig paginanummer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _local_review_interpretation(context: dict[str, Any]) -> AIInterpretation:
    labels = {
        "position": "onderdeelpositie",
        "profile": "profiel",
        "material": "materiaal",
        "length": "lengte",
        "plate_thickness": "plaatdikte",
        "outer_contour": "gesloten buitencontour",
        "hole_positions": "gatposities",
        "reference_side": "referentiezijde",
    }
    questions: list[AIQuestionSuggestion] = []
    for field_path in [str(item) for item in context.get("missing_critical", [])]:
        label = labels.get(field_path, field_path.replace("_", " "))
        questions.append(
            AIQuestionSuggestion(
                field_path=field_path,
                question=f"Welke waarde of geometrische referentie geldt voor {label}?",
                severity="blocking",
                reason="Kritisch productiegegeven ontbreekt in de deterministische PDF-analyse.",
            )
        )
    for field_path in [str(item) for item in context.get("conflicts", [])]:
        label = labels.get(field_path, field_path.replace("_", " "))
        questions.append(
            AIQuestionSuggestion(
                field_path=field_path,
                question=f"Welke van de conflicterende interpretaties voor {label} is correct?",
                severity="blocking",
                reason="De deterministische analyse vond tegenstrijdige brongegevens.",
            )
        )
    return AIInterpretation(
        provider="local-rules",
        model="deterministic-question-engine-v1",
        questions=questions,
        audit={"local_only": True, "store": False},
    )


def _render_pdf_page_images(
    pdf_path: str | Path,
    *,
    max_pages: int,
    render_dpi: int,
) -> list[bytes]:
    try:
        import pymupdf
    except Exception as exc:
        raise RuntimeError("PyMuPDF ontbreekt; PDF-pagina's kunnen niet worden gerenderd") from exc
    source = Path(pdf_path)
    document = pymupdf.open(source)
    try:
        count = min(len(document), max(1, int(max_pages)))
        zoom = max(72, int(render_dpi)) / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        return [
            document[index].get_pixmap(matrix=matrix, alpha=False).tobytes("png")
            for index in range(count)
        ]
    finally:
        document.close()


def _write_drawing_ai_audit(
    pdf_path: str | Path,
    settings: AISettings,
    result: AIInterpretation,
    *,
    page_count: int,
) -> None:
    if not settings.audit_log:
        return
    target = Path(settings.audit_log).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest(),
        "provider": result.provider,
        "model": result.model,
        "page_count": int(page_count),
        "request_id": result.request_id,
        "response_sha256": result.response_sha256,
        "field_count": len(result.fields),
        "question_count": len(result.questions),
        "store": False,
    }
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def interpret_drawing(
    pdf_path: str | Path,
    *,
    deterministic_context: dict[str, Any],
    settings: AISettings | None = None,
) -> AIInterpretation:
    """Interpret a drawing without ever producing production geometry.

    The local provider only formulates review questions. The optional OpenAI
    provider uses the Responses API request contract already guarded above:
    explicit consent, ``store=false``, strict Structured Outputs and recursive
    rejection of geometry/machine-code fields.
    """

    active = settings or AISettings()
    provider_name = active.provider.strip().lower()
    if provider_name in {"", "none", "off"}:
        return AIInterpretation(provider="none", model="none", audit={"store": False})
    if provider_name in {"local", "local-rules", "rules"}:
        result = _local_review_interpretation(deterministic_context)
        result.validate()
        return result
    if provider_name not in {"openai", "cloud", "hybrid"}:
        raise ValueError(f"Onbekende AI-provider: {active.provider!r}")
    if not active.allow_cloud:
        raise CloudAIConsentError(
            "Cloud-AI is uitgeschakeld. Geef per bewerking expliciet toestemming voordat een tekening wordt verzonden."
        )

    images = _render_pdf_page_images(
        pdf_path,
        max_pages=active.max_pages,
        render_dpi=active.render_dpi,
    )
    safe_context = {
        key: deterministic_context[key]
        for key in (
            "page_count",
            "page_classification",
            "sheet_format",
            "orientation",
            "detected_fields",
            "missing_critical",
            "conflicts",
            "vector_path_count",
            "image_count",
        )
        if key in deterministic_context
    }
    provider = OpenAIResponsesProvider(
        model=active.model or DEFAULT_OPENAI_MODEL,
        api_key=active.api_key or None,
        endpoint=active.endpoint or OPENAI_RESPONSES_ENDPOINT,
        timeout=float(active.timeout),
        transport=active.transport,
    )
    cloud = provider.interpret(safe_context, images, cloud_consent=True)
    fields = [
        AIFieldSuggestion(
            field_path=item.name,
            value=item.value,
            confidence=float(item.confidence),
            page=int(item.page or 1),
            source_text=item.evidence,
            reason="Semantische cloud-AI-suggestie; deterministische geometriekoppeling vereist.",
        )
        for item in cloud.fields
    ]
    questions = [
        AIQuestionSuggestion(
            field_path=item.field,
            question=item.question,
            severity="blocking" if item.blocking else "warning",
            alternatives=[str(value) for value in item.options],
            page=1,
            reason="Door AI geformuleerde controlevraag; geen productiegeometrie.",
        )
        for item in cloud.questions
    ]
    questions.extend(
        AIQuestionSuggestion(
            field_path=item.field,
            question=item.message,
            severity="blocking" if item.blocking else "warning",
            alternatives=[str(value) for value in item.alternatives],
            page=1,
            reason="AI detecteerde een mogelijk semantisch conflict.",
        )
        for item in cloud.conflicts
    )
    response_material = json.dumps(cloud.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    result = AIInterpretation(
        provider=cloud.provider,
        model=cloud.model,
        fields=fields,
        questions=questions,
        warnings=[],
        request_id=str(cloud.audit.get("request_id", "")),
        response_sha256=hashlib.sha256(response_material).hexdigest(),
        audit=dict(cloud.audit),
    )
    result.validate()
    _write_drawing_ai_audit(pdf_path, active, result, page_count=len(images))
    return result
