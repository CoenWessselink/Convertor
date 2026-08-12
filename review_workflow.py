"""Pure helpers for the interactive technical-PDF review workflow.

The GUI deliberately stores only explicit human actions:

* corrections use the strict allow-list already enforced by ``pdf_support``;
* confirmations may only reference evidence that actually exists;
* answers may only target open questions emitted by deterministic/AI analysis.

No geometry is inferred in this module.  It prepares a review payload that is
subsequently applied and validated by :func:`pdf_support.apply_review`.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from typing import Any, Iterable, Mapping

from canonical_model import CanonicalPart


_ALIAS_TO_CANONICAL = {
    "position": "header.position_number",
    "profile": "header.profile",
    "material": "header.material",
    "length": "header.length",
    "quantity": "header.quantity",
    "mark": "product.mark",
    "subject": "product.name",
    "scale": "drawing.scale",
    "sheet_format": "drawing.sheet_format",
    "orientation": "drawing.orientation",
    "reference_side": "properties.reference_side",
}

_LABELS = {
    "header.position_number": "Positie / onderdeelnummer",
    "header.part_number": "Onderdeelnummer",
    "header.drawing_number": "Tekeningnummer",
    "header.order_number": "Ordernummer",
    "header.profile": "Profiel",
    "header.profile_type": "DSTV-profieltype",
    "header.material": "Materiaal",
    "header.quantity": "Aantal",
    "header.length": "Lengte (mm)",
    "header.saw_length": "Zaaglengte (mm)",
    "header.dim1": "Hoofdmaat 1 / breedte (mm)",
    "header.dim2": "Hoofdmaat 2 / dikte (mm)",
    "header.dim3": "Hoofdmaat 3 (mm)",
    "header.dim4": "Hoofdmaat 4 (mm)",
    "header.radius": "Profielradius (mm)",
    "product.name": "Onderwerp / onderdeelnaam",
    "product.mark": "Merk",
    "product.project_number": "Projectnummer",
    "product.project_name": "Project",
    "product.client": "Opdrachtgever",
    "product.assembly_id": "Samenstelling",
    "product.coating": "Coating",
    "drawing.scale": "Schaal",
    "drawing.sheet_format": "Bladformaat",
    "drawing.orientation": "Oriëntatie",
    "drawing.projection_method": "Projectiemethode",
    "properties.reference_side": "DSTV-referentiezijde en oorsprong",
    "total_quantity": "Totaalaantal",
}


@dataclass(frozen=True)
class ReviewField:
    """One row in the interactive review table."""

    path: str
    label: str
    category: str
    current_value: Any
    evidence_path: str = ""
    confidence: float | None = None
    method: str = ""
    status: str = ""
    page: int | None = None
    editable: bool = False
    confirmable: bool = False
    question_ids: tuple[str, ...] = ()

    @property
    def display_value(self) -> str:
        return value_to_text(self.current_value)


_HEADER_EDITABLE = {
    "order_number",
    "drawing_number",
    "part_number",
    "position_number",
    "material",
    "quantity",
    "profile",
    "profile_type",
    "length",
    "saw_length",
    "dim1",
    "dim2",
    "dim3",
    "dim4",
    "radius",
}
_DRAWING_EDITABLE = {
    "scale",
    "sheet_format",
    "orientation",
    "projection_method",
    "drawing_status",
    "template_id",
    "company_style_id",
}
_PRODUCT_EDITABLE = {
    "name",
    "mark",
    "project_number",
    "project_name",
    "client",
    "assembly_id",
    "material_code",
    "material_grade",
    "density_kg_m3",
    "coating",
    "surface_treatment",
    "profile_category",
    "profile_series",
    "profile_designation",
    "profile_standard",
    "length_mm",
    "plate_thickness_mm",
    "main_dimensions_mm",
    "mass_each_kg",
    "mass_total_kg",
    "area_each_m2",
    "area_total_m2",
}


def canonical_path(field_path: str) -> str:
    """Map a detector/question alias to the strict canonical review path."""

    return _ALIAS_TO_CANONICAL.get(str(field_path), str(field_path))


def _is_editable(path: str) -> bool:
    if path.startswith("header."):
        return path.split(".", 1)[1] in _HEADER_EDITABLE
    if path.startswith("product."):
        return path.split(".", 1)[1] in _PRODUCT_EDITABLE
    if path.startswith("drawing."):
        return path.split(".", 1)[1] in _DRAWING_EDITABLE
    if path == "properties.reference_side":
        return True
    if re.fullmatch(r"holes\[(\d+)]\.(face|x|q|diameter|datum|operation|depth)", path):
        return True
    if re.fullmatch(r"contours\[(\d+)]\.points\[(\d+)]\.(x|q|radius|datum|notch)", path):
        return True
    return False


def _get_value(part: CanonicalPart, path: str, fallback: Any = None) -> Any:
    if path.startswith("header."):
        return getattr(part.header, path.split(".", 1)[1], fallback)
    if path.startswith("product."):
        return getattr(part.product, path.split(".", 1)[1], fallback)
    if path.startswith("drawing."):
        return getattr(part.drawing, path.split(".", 1)[1], fallback)
    if path == "properties.reference_side":
        return part.properties.get("reference_side", fallback)
    hole = re.fullmatch(r"holes\[(\d+)](?:\.(face|x|q|diameter|datum|operation|depth))?", path)
    if hole:
        index = int(hole.group(1))
        if not 0 <= index < len(part.holes):
            return fallback
        item = part.holes[index]
        name = hole.group(2)
        if name:
            return getattr(item, name, fallback)
        return {
            "face": item.face,
            "x": item.x,
            "q": item.q,
            "diameter": item.diameter,
            "datum": item.datum,
            "operation": item.operation,
            "depth": item.depth,
        }
    contour = re.fullmatch(r"contours\[(\d+)]", path)
    if contour:
        index = int(contour.group(1))
        if not 0 <= index < len(part.contours):
            return fallback
        item = part.contours[index]
        return {
            "kind": item.kind,
            "face": item.face,
            "points": len(item.points),
            "radii": [point.radius for point in item.points if point.radius > 0],
        }
    point = re.fullmatch(
        r"contours\[(\d+)]\.points\[(\d+)]\.(x|q|radius|datum|notch)", path
    )
    if point:
        contour_index, point_index, name = int(point.group(1)), int(point.group(2)), point.group(3)
        if not 0 <= contour_index < len(part.contours):
            return fallback
        points = part.contours[contour_index].points
        if not 0 <= point_index < len(points):
            return fallback
        return getattr(points[point_index], name, fallback)
    return fallback


def _label(path: str) -> str:
    if path in _LABELS:
        return _LABELS[path]
    hole = re.fullmatch(r"holes\[(\d+)](?:\.(.+))?", path)
    if hole:
        number = int(hole.group(1)) + 1
        names = {
            None: f"Gat {number} - volledig kenmerk",
            "face": f"Gat {number} - zijde",
            "x": f"Gat {number} - X (mm)",
            "q": f"Gat {number} - Y/Q (mm)",
            "diameter": f"Gat {number} - diameter (mm)",
            "depth": f"Gat {number} - diepte (mm)",
            "datum": f"Gat {number} - maatvoering",
            "operation": f"Gat {number} - bewerking",
        }
        return names.get(hole.group(2), path)
    contour = re.fullmatch(r"contours\[(\d+)]", path)
    if contour:
        return f"Contour {int(contour.group(1)) + 1} - volledig"
    point = re.fullmatch(r"contours\[(\d+)]\.points\[(\d+)]\.(.+)", path)
    if point:
        c, p, name = int(point.group(1)) + 1, int(point.group(2)) + 1, point.group(3)
        names = {"x": "X", "q": "Y/Q", "radius": "radius", "datum": "maatvoering", "notch": "inkeping"}
        unit = " (mm)" if name in {"x", "q", "radius"} else ""
        return f"Contour {c}, punt {p} - {names.get(name, name)}{unit}"
    return path


def _category(path: str) -> str:
    if path.startswith("header."):
        return "Productgegevens"
    if path.startswith("product."):
        return "Project en metadata"
    if path.startswith("drawing.") or path == "total_quantity":
        return "Tekening"
    if path.startswith("holes["):
        return "Gaten"
    if path.startswith("contours["):
        return "Contouren"
    if path.startswith("properties."):
        return "Productiereferentie"
    if path.startswith("ai."):
        return "AI-voorstel"
    return "Overig"


def _question_ids(part: CanonicalPart, *paths: str) -> tuple[str, ...]:
    candidates = {value for value in paths if value}
    result = [
        question.question_id
        for question in part.validation.unresolved_questions
        if question.field_path in candidates
    ]
    return tuple(result)


def collect_review_fields(part: CanonicalPart) -> list[ReviewField]:
    """Build deterministic review rows from evidence and exact model features."""

    rows: dict[str, ReviewField] = {}

    def add(
        path: str,
        *,
        current: Any = None,
        evidence_path: str = "",
        confidence: float | None = None,
        method: str = "",
        status: str = "",
        page: int | None = None,
        confirmable: bool = False,
        question_paths: Iterable[str] = (),
    ) -> None:
        canonical = canonical_path(path)
        row_key = canonical if _is_editable(canonical) else path
        if current is None:
            current = _get_value(part, canonical, None)
        question_ids = _question_ids(part, path, canonical, evidence_path, *question_paths)
        existing = rows.get(row_key)
        proposed = ReviewField(
            path=canonical if _is_editable(canonical) else path,
            label=_label(canonical if _is_editable(canonical) else path),
            category=_category(canonical if _is_editable(canonical) else path),
            current_value=current,
            evidence_path=evidence_path,
            confidence=confidence,
            method=method,
            status=status,
            page=page,
            editable=_is_editable(canonical),
            confirmable=bool(confirmable and evidence_path),
            question_ids=question_ids,
        )
        # Evidence-backed rows are more informative than generated exact rows.
        if existing is None or (evidence_path and not existing.evidence_path):
            rows[row_key] = proposed

    for evidence_path, evidence in part.field_evidence.items():
        mapped = canonical_path(evidence_path)
        current = _get_value(part, mapped, evidence.value)
        add(
            evidence_path,
            current=current,
            evidence_path=evidence_path,
            confidence=float(evidence.confidence),
            method=evidence.method,
            status=evidence.status,
            page=evidence.page,
            confirmable=True,
        )

    essentials = [
        "header.position_number",
        "header.part_number",
        "header.drawing_number",
        "header.order_number",
        "header.profile",
        "header.profile_type",
        "header.material",
        "header.quantity",
        "header.length",
        "header.saw_length",
        "header.dim1",
        "header.dim2",
        "header.dim3",
        "header.dim4",
        "header.radius",
        "product.name",
        "product.mark",
        "product.project_number",
        "product.project_name",
        "product.client",
        "product.assembly_id",
        "product.coating",
        "drawing.scale",
        "drawing.sheet_format",
        "drawing.orientation",
        "drawing.projection_method",
        "properties.reference_side",
    ]
    for path in essentials:
        value = _get_value(part, path, "")
        relevant = value not in {"", None, 0, 0.0} or any(
            canonical_path(question.field_path) == path
            for question in part.validation.unresolved_questions
        )
        if relevant:
            add(path, current=value, question_paths=(path,))

    for index, contour in enumerate(part.contours):
        parent = f"contours[{index}]"
        evidence = part.field_evidence.get(parent)
        add(
            parent,
            current=_get_value(part, parent),
            evidence_path=parent if evidence else "",
            confidence=float(evidence.confidence) if evidence else None,
            method=evidence.method if evidence else "exact_canonical_geometry",
            status=evidence.status if evidence else "exact",
            page=evidence.page if evidence else None,
            confirmable=evidence is not None,
        )
        for point_index, point in enumerate(contour.points):
            for name in ("x", "q", "radius"):
                path = f"{parent}.points[{point_index}].{name}"
                # Radius 0 remains useful for a geometry correction, but reduce
                # clutter by showing it only when another radius exists or the
                # point itself is the target of a question.
                if name == "radius" and point.radius <= 0 and not any(
                    question.field_path in {"radii", path}
                    for question in part.validation.unresolved_questions
                ):
                    continue
                add(path, current=getattr(point, name), method="exact_canonical_geometry", status="exact")

    for index, hole in enumerate(part.holes):
        parent = f"holes[{index}]"
        evidence = part.field_evidence.get(parent)
        add(
            parent,
            current=_get_value(part, parent),
            evidence_path=parent if evidence else "",
            confidence=float(evidence.confidence) if evidence else None,
            method=evidence.method if evidence else "exact_canonical_geometry",
            status=evidence.status if evidence else "exact",
            page=evidence.page if evidence else None,
            confirmable=evidence is not None,
        )
        for name in ("face", "x", "q", "diameter", "depth"):
            path = f"{parent}.{name}"
            nested = part.field_evidence.get(path)
            add(
                path,
                current=getattr(hole, name),
                evidence_path=path if nested else "",
                confidence=float(nested.confidence) if nested else None,
                method=nested.method if nested else "exact_canonical_geometry",
                status=nested.status if nested else "exact",
                page=nested.page if nested else None,
                confirmable=nested is not None,
            )

    # Ensure every question with a directly editable field has a row, even if
    # the detector emitted no evidence for it.
    for question in part.validation.unresolved_questions:
        mapped = canonical_path(question.field_path)
        if _is_editable(mapped):
            add(mapped, current=_get_value(part, mapped, ""), question_paths=(question.field_path,))

    category_order = {
        "Productgegevens": 0,
        "Project en metadata": 1,
        "Tekening": 2,
        "Productiereferentie": 3,
        "Contouren": 4,
        "Gaten": 5,
        "AI-voorstel": 6,
        "Overig": 7,
    }
    return sorted(
        rows.values(),
        key=lambda item: (category_order.get(item.category, 99), item.label.lower(), item.path),
    )


def value_to_text(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return f"{value:.6f}".rstrip("0").rstrip(".")
    if value is None:
        return ""
    return str(value)


def coerce_review_value(text: str, current_value: Any) -> Any:
    """Parse one human-entered value without eval or implicit geometry logic."""

    raw = str(text).strip()
    if isinstance(current_value, bool):
        normalized = raw.lower()
        if normalized in {"1", "true", "ja", "yes", "aan"}:
            return True
        if normalized in {"0", "false", "nee", "no", "uit"}:
            return False
        raise ValueError("Gebruik ja/nee of true/false")
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        number = float(raw.replace(",", "."))
        if not number.is_integer():
            raise ValueError("Dit veld vereist een geheel getal")
        return int(number)
    if isinstance(current_value, float):
        value = float(raw.replace(" ", "").replace(",", "."))
        if not math.isfinite(value):
            raise ValueError("Numerieke waarde moet eindig zijn")
        return value
    if isinstance(current_value, (list, dict, tuple)):
        value = json.loads(raw)
        if isinstance(current_value, list) and not isinstance(value, list):
            raise ValueError("Dit veld vereist een JSON-lijst")
        if isinstance(current_value, dict) and not isinstance(value, dict):
            raise ValueError("Dit veld vereist een JSON-object")
        return value
    return raw


def build_review_payload(
    part: CanonicalPart,
    *,
    reviewed_by: str,
    values: Mapping[str, Any] | None = None,
    confirm: Iterable[str] = (),
    answers: Mapping[str, Any] | None = None,
    comment: str = "",
) -> dict[str, Any]:
    """Create a strict review JSON document from explicit UI actions."""

    reviewer = str(reviewed_by).strip()
    if not reviewer:
        raise ValueError("Vul de naam van de beoordelaar in")

    fields = collect_review_fields(part)
    editable = {item.path: item for item in fields if item.editable}
    normalized_values: dict[str, Any] = {}
    for raw_path, raw_value in dict(values or {}).items():
        path = canonical_path(str(raw_path))
        field = editable.get(path)
        if field is None:
            raise ValueError(f"Veld {raw_path!r} is niet interactief wijzigbaar")
        normalized_values[path] = (
            coerce_review_value(raw_value, field.current_value)
            if isinstance(raw_value, str)
            else raw_value
        )

    existing_evidence = set(part.field_evidence)
    confirmations = {str(item) for item in confirm if str(item)}
    unknown_confirmations = confirmations - existing_evidence
    if unknown_confirmations:
        raise ValueError(
            "Bevestiging verwijst niet naar bestaand bronbewijs: "
            + ", ".join(sorted(unknown_confirmations))
        )

    question_ids = {item.question_id for item in part.validation.unresolved_questions}
    normalized_answers = {str(key): value for key, value in dict(answers or {}).items()}
    unknown_answers = set(normalized_answers) - question_ids
    if unknown_answers:
        raise ValueError(
            "Antwoord verwijst niet naar een bestaande controlevraag: "
            + ", ".join(sorted(unknown_answers))
        )

    return {
        "reviewed_by": reviewer,
        "values": normalized_values,
        "confirm": sorted(confirmations),
        "answers": normalized_answers,
        "comment": str(comment),
    }
