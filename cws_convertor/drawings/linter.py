"""Fail-closed production drawing validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .document import DrawingDocument, DrawingPrimitive


@dataclass(frozen=True, slots=True)
class DrawingLintIssue:
    code: str
    message: str
    severity: str = "error"
    blocking: bool = True
    page: int | None = None
    semantic_id: str = ""


@dataclass(frozen=True, slots=True)
class DrawingLintResult:
    release_ready: bool
    issues: tuple[DrawingLintIssue, ...]
    checked_primitives: int
    checked_pages: int
    dimension_coverage_percent: float
    feature_coverage_percent: float

    def to_dict(self) -> dict:
        return asdict(self)


def _overlap(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return not (
        left[2] <= right[0]
        or right[2] <= left[0]
        or left[3] <= right[1]
        or right[3] <= left[1]
    )


def _ids(values: Iterable[dict], *names: str) -> set[str]:
    result: set[str] = set()
    for value in values:
        for name in names:
            item = str(value.get(name) or "").strip()
            if item:
                result.add(item)
                break
    return result


def _valid_sha256(value: str) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text)


class DrawingLinter:
    """Check freshness, coverage, clipping and annotation collisions."""

    REQUIRED_TITLE_FIELDS = (
        "project",
        "entity",
        "profile",
        "material",
        "revision",
        "status",
    )

    @classmethod
    def lint(cls, document: DrawingDocument) -> DrawingLintResult:
        document.validate()
        issues: list[DrawingLintIssue] = []
        if document.geometry_basis != "canonical_rebuild_brep":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_GEOMETRY_NOT_CANONICAL",
                    "Review gebruikt geen canonical rebuilt BREP; productie-vrijgave blijft geblokkeerd.",
                )
            )
        if document.hlr_method != "occt_hlr":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_EXACT_HLR_MISSING",
                    "Exacte OCCT hidden-line removal is voor deze geometrie niet bewezen.",
                )
            )
        if not _valid_sha256(document.geometry_sha256):
            issues.append(
                DrawingLintIssue(
                    "DRAWING_GEOMETRY_HASH_MISSING",
                    "De tekening mist een geldige 64-teken hash van de exacte geometrie.",
                )
            )
        if not _valid_sha256(document.manufacturing_sha256) or not _valid_sha256(document.expected_manufacturing_sha256):
            issues.append(
                DrawingLintIssue(
                    "DRAWING_MANUFACTURING_HASH_MISSING",
                    "De tekening mist een geldige binding met de actuele productierevisie.",
                )
            )
        if document.sections_requested and document.section_method != "occt_brep_section":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_EXACT_SECTION_MISSING",
                    "De gevraagde doorsnede is niet als exacte OCCT BREP-vlakdoorsnede bewezen.",
                )
            )
        if not document.canonical_rebuild_current:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_GEOMETRY_STALE",
                    "De tekening is niet aan een actuele, opgeslagen canonical rebuild gebonden.",
                )
            )
        if not document.canonical_payload_current:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_CANONICAL_PAYLOAD_MISSING",
                    "De zichtbare tekening mist een actuele canonical payload voor Trusted PDF.",
                )
            )
        if not document.roundtrip_current:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_ROUNDTRIP_NOT_CURRENT",
                    "NC1/STEP/IFC/PDF-roundtrip is niet actueel en groen.",
                )
            )
        if str(document.title_block.get("status") or "").strip().lower() != "released":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_SOURCE_NOT_RELEASED",
                    "De Workbench-revisie is nog niet vrijgegeven.",
                )
            )
        if not document.dimensions_enabled:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSIONS_DISABLED",
                    "Maatvoering is uitgeschakeld; productie-vrijgave is niet toegestaan.",
                )
            )
        if document.dimension_mode != "Productiematen":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSION_MODE_REVIEW_ONLY",
                    "Productie-vrijgave vereist de maatmodus Productiematen.",
                )
            )
        if not document.title_block_enabled:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_TITLE_BLOCK_DISABLED",
                    "Titelblok is uitgeschakeld; productie-vrijgave is niet toegestaan.",
                )
            )
        if (
            document.expected_manufacturing_sha256
            and document.manufacturing_sha256 != document.expected_manufacturing_sha256
        ):
            issues.append(
                DrawingLintIssue(
                    "DRAWING_MANUFACTURING_HASH_MISMATCH",
                    "De tekening verwijst naar een andere productierevisie.",
                )
            )
        for key in cls.REQUIRED_TITLE_FIELDS:
            if not str(document.title_block.get(key) or "").strip():
                issues.append(
                    DrawingLintIssue(
                        "DRAWING_TITLE_FIELD_MISSING",
                        f"Titelblokveld {key!r} ontbreekt.",
                        semantic_id=key,
                    )
                )

        expected_dimensions = {
            str(item.get("id") or "")
            for item in document.dimensions
            if bool(item.get("critical", True)) and item.get("id")
        }
        placed_dimensions = {
            primitive.semantic_id
            for page in document.pages
            for primitive in page.primitives
            if primitive.layer == "dimensions" and primitive.semantic_id
        }
        missing_dimensions = sorted(expected_dimensions - placed_dimensions)
        if missing_dimensions:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSIONS_MISSING",
                    "Kritische maten ontbreken: " + ", ".join(missing_dimensions),
                )
            )
        dimension_coverage = (
            100.0
            if not expected_dimensions
            else 100.0 * len(expected_dimensions & placed_dimensions) / len(expected_dimensions)
        )

        expected_features = _ids(document.features, "feature_id", "id")
        annotated_features = {
            reference
            for page in document.pages
            for primitive in page.primitives
            if primitive.layer in {"annotations", "centerlines", "hatch"}
            for reference in primitive.refs
        }
        missing_features = sorted(expected_features - annotated_features)
        if missing_features:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_FEATURES_UNANNOTATED",
                    "Productiefeatures missen een gekoppelde annotatie: " + ", ".join(missing_features),
                )
            )
        feature_coverage = (
            100.0
            if not expected_features
            else 100.0 * len(expected_features & annotated_features) / len(expected_features)
        )

        manual_ids = _ids(document.manual_dimensions, "id", "dimension_id")
        missing_manual = sorted(manual_ids - placed_dimensions)
        if missing_manual:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_MANUAL_DIMENSIONS_MISSING",
                    "Eigen maten ontbreken in het document: " + ", ".join(missing_manual),
                )
            )
        for item in document.manual_dimensions:
            dimension_id = str(item.get("id") or item.get("dimension_id") or "")
            feature_id = str(item.get("feature_id") or "")
            anchor_type = str(item.get("anchor_type") or "")
            if not feature_id or anchor_type not in {"datum_offset", "feature_center", "edge_projection"}:
                issues.append(
                    DrawingLintIssue(
                        "DRAWING_MANUAL_DIMENSION_UNANCHORED",
                        "Eigen maat mist een stabiel feature-/randanker.",
                        semantic_id=dimension_id,
                    )
                )

        checked = 0
        for page in document.pages:
            annotation_bounds: list[tuple[DrawingPrimitive, tuple[float, float, float, float]]] = []
            for primitive in page.primitives:
                checked += 1
                bounds = primitive.bounds()
                if bounds is None:
                    continue
                tolerance = 0.25
                if (
                    bounds[0] < -tolerance
                    or bounds[1] < -tolerance
                    or bounds[2] > page.width_mm + tolerance
                    or bounds[3] > page.height_mm + tolerance
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_CONTENT_CLIPPED",
                            f"Tekenobject {primitive.semantic_id or primitive.kind} valt buiten blad {page.number}.",
                            page=page.number,
                            semantic_id=primitive.semantic_id,
                        )
                    )
                if primitive.kind == "text" and primitive.layer in {
                    "sheet",
                    "views",
                    "annotations",
                    "dimensions",
                    "bom",
                    "notes",
                    "title",
                }:
                    for other, other_bounds in annotation_bounds:
                        if _overlap(bounds, other_bounds):
                            issues.append(
                                DrawingLintIssue(
                                    "DRAWING_ANNOTATION_COLLISION",
                                    "Maat- of annotatietekst overlapt een andere geplaatste tekst.",
                                    page=page.number,
                                    semantic_id=primitive.semantic_id or other.semantic_id,
                                )
                            )
                            break
                    annotation_bounds.append((primitive, bounds))

        unique: dict[tuple[str, int | None, str], DrawingLintIssue] = {}
        for issue in issues:
            unique.setdefault((issue.code, issue.page, issue.semantic_id), issue)
        values = tuple(unique.values())
        return DrawingLintResult(
            release_ready=not any(issue.blocking for issue in values),
            issues=values,
            checked_primitives=checked,
            checked_pages=len(document.pages),
            dimension_coverage_percent=round(dimension_coverage, 3),
            feature_coverage_percent=round(feature_coverage, 3),
        )


__all__ = ["DrawingLintIssue", "DrawingLintResult", "DrawingLinter"]
