"""Fail-closed production drawing validation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

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
        valid_view_ids = {
            str(item.get("view_id") or item.get("view") or "")
            for item in document.view_contexts
            if str(item.get("view_id") or item.get("view") or "")
        }
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

        manual_ids = _ids(
            (item for item in document.manual_dimensions if bool(item.get("visible", True))),
            "id",
            "dimension_id",
        )
        missing_manual = sorted(manual_ids - placed_dimensions)
        if missing_manual:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_MANUAL_DIMENSIONS_MISSING",
                    "Eigen maten ontbreken in het document: " + ", ".join(missing_manual),
                )
            )
        interactive_items = [item for item in document.manual_dimensions if item.get("anchors")]
        if interactive_items and document.dimension_editor_schema != "cws.drawing-dimension-editor.v2":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSION_EDITOR_SCHEMA_UNKNOWN",
                    "Interactieve maatvoering gebruikt niet het ondersteunde V2-schema.",
                )
            )
        if interactive_items and document.dimension_editor_status != "released":
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSION_EDITOR_NOT_RELEASED",
                    "Interactieve maatvoering staat nog in concept en is niet formeel vrijgegeven.",
                )
            )
        standard_style = (
            str(document.dimension_style.get("style_id") or "") == "cws-standard"
            and str(document.dimension_style.get("version") or "") == "2.0"
        )
        approved_custom_style = (
            str(document.dimension_style.get("profile_scope") or "") in {"company", "project", "object"}
            and str(document.dimension_style.get("base_style_id") or "") == "cws-standard"
            and bool(str(document.dimension_style.get("approved_by") or "").strip())
            and bool(str(document.dimension_style.get("style_id") or "").strip())
            and bool(str(document.dimension_style.get("version") or "").strip())
        )
        if interactive_items and not (standard_style or approved_custom_style):
            issues.append(
                DrawingLintIssue(
                    "DRAWING_DIMENSION_STYLE_UNKNOWN",
                    "Interactieve maatvoering mist een versiegebonden maatstijl.",
                )
            )
        if interactive_items and document.dimension_style and standard_style:
            expected_style = {
                "arrow_type": "closed_filled",
                "arrow_size_mm": 2.5,
                "font_family": "Segoe UI",
                "text_height_mm": 2.5,
                "line_width_mm": 0.2,
                "line_color": "#0066dc",
                "decimals": 1,
            }
            if any(document.dimension_style.get(key) != value for key, value in expected_style.items()):
                issues.append(
                    DrawingLintIssue(
                        "DRAWING_DIMENSION_STYLE_CHANGED",
                        "De inhoud van cws-standard 2.0 wijkt af van het vrijgegeven stijlprofiel.",
                    )
                )
        if interactive_items:
            try:
                if float(document.dimension_style.get("text_height_mm") or 0.0) < 2.0:
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_DIMENSION_TEXT_UNREADABLE",
                            "Maatteksthoogte is kleiner dan 2,0 mm op papier.",
                        )
                    )
            except (TypeError, ValueError):
                issues.append(
                    DrawingLintIssue(
                        "DRAWING_DIMENSION_TEXT_UNREADABLE",
                        "Maatteksthoogte is niet geldig.",
                    )
                )
        dimension_ids = [str(item.get("id") or item.get("dimension_id") or "") for item in document.manual_dimensions]
        duplicate_ids = sorted({item for item in dimension_ids if item and dimension_ids.count(item) > 1})
        if duplicate_ids:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_MANUAL_DIMENSION_DUPLICATE",
                    "Dubbele handmatige maat-ID's: " + ", ".join(duplicate_ids),
                )
            )
        for item in document.manual_dimensions:
            dimension_id = str(item.get("id") or item.get("dimension_id") or "")
            anchors = [dict(value) for value in item.get("anchors") or () if isinstance(value, Mapping)]
            if anchors:
                if (
                    str(item.get("style_id") or "") != str(document.dimension_style.get("style_id") or "")
                    or str(item.get("style_version") or "") != str(document.dimension_style.get("version") or "")
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_DIMENSION_STYLE_STALE",
                            "Maatobject gebruikt niet de actuele versie van de tekenstijl.",
                            semantic_id=dimension_id,
                        )
                    )
                state = str(item.get("state") or "RESOLVED")
                if state in {"ORPHANED", "ORPHANED_VIEW", "CONFLICT", "STALE"}:
                    issues.append(
                        DrawingLintIssue(
                            f"DRAWING_MANUAL_DIMENSION_{state}",
                            f"Interactieve maat heeft blokkerende resolutiestatus {state}.",
                            semantic_id=dimension_id,
                        )
                    )
                if state == "OVERRIDDEN" and not str(item.get("override_approved_by") or "").strip():
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_OVERRIDE_UNAPPROVED",
                            "Afwijkende zichtbare maattekst is niet formeel goedgekeurd.",
                            semantic_id=dimension_id,
                        )
                    )
                if (
                    str(item.get("kind") or "") not in {"leader", "text"}
                    and str(item.get("label") or "").strip()
                    and not str(item.get("override_reason") or "").strip()
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_OVERRIDE_REASON_MISSING",
                            "Afwijkende geometrische maattekst heeft geen wijzigingsreden.",
                            semantic_id=dimension_id,
                        )
                    )
                if not anchors or any(
                    not str(anchor.get("entity_id") or "").strip()
                    or not str(anchor.get("view_id") or "").strip()
                    or not str(anchor.get("sheet_id") or "").strip()
                    or len(list(anchor.get("projected_point") or ())) != 2
                    or not bool(anchor.get("resolved", True))
                    for anchor in anchors
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_UNANCHORED",
                            "Interactieve maat mist een stabiel geometrisch anker.",
                            semantic_id=dimension_id,
                        )
                    )
                if any(
                    int(anchor.get("page_number") or 0) != int(item.get("page_number") or 0)
                    or str(anchor.get("sheet_id") or "") != str(item.get("sheet_id") or "")
                    or str(anchor.get("view_id") or "") != str(item.get("view_id") or "")
                    or str(anchor.get("view_id") or "") not in valid_view_ids
                    for anchor in anchors
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_ANCHOR_CONTEXT_MISMATCH",
                            "Een maatanker hoort niet bij hetzelfde aanzicht, blad of maatobject.",
                            semantic_id=dimension_id,
                        )
                    )
                if any(str(anchor.get("geometry_sha256") or "") != document.geometry_sha256 for anchor in anchors):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_GEOMETRY_MISMATCH",
                            "Een interactief maatanker hoort bij een andere geometrieversie.",
                            semantic_id=dimension_id,
                        )
                    )
                if any(str(anchor.get("manufacturing_sha256") or "") != document.manufacturing_sha256 for anchor in anchors):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_MANUFACTURING_MISMATCH",
                            "Een interactief maatanker hoort bij een andere productierevisie.",
                            semantic_id=dimension_id,
                        )
                    )
                if document.document_type != "assembly" and any(
                    str(anchor.get("entity_id") or "") != document.entity_id for anchor in anchors
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_CROSS_ENTITY_LEAK",
                            "Een partmaat verwijst naar geometrie van een andere entity.",
                            semantic_id=dimension_id,
                        )
                    )
                non_geometric_note = str(item.get("kind") or "") == "text" and all(
                    str(anchor.get("proof") or "") == "non_geometric_annotation" for anchor in anchors
                )
                if document.geometry_basis == "canonical_rebuild_brep" and not non_geometric_note and any(
                    str(anchor.get("proof") or "") != "canonical_projection" for anchor in anchors
                ):
                    issues.append(
                        DrawingLintIssue(
                            "DRAWING_MANUAL_DIMENSION_PROOF_INSUFFICIENT",
                            "De productiemaat is niet uit een gevalideerde canonical projectie bewezen.",
                            semantic_id=dimension_id,
                        )
                    )
                continue
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

        semantic_ids = [str(item.get("id") or "") for item in document.dimensions if str(item.get("id") or "")]
        duplicate_critical = sorted({value for value in semantic_ids if semantic_ids.count(value) > 1})
        if duplicate_critical:
            issues.append(
                DrawingLintIssue(
                    "DRAWING_CRITICAL_DIMENSION_DUPLICATE",
                    "Kritische maatdefinities zijn dubbel aanwezig: " + ", ".join(duplicate_critical),
                )
            )
        for chain in document.dimension_chains:
            chain_id = str(chain.get("id") or "")
            members = [str(value) for value in chain.get("members") or () if str(value)]
            if not chain_id or len(members) < 2 or len(set(members)) != len(members) or any(value not in semantic_ids for value in members):
                issues.append(
                    DrawingLintIssue(
                        "DRAWING_DIMENSION_CHAIN_CONFLICT",
                        "Maatketen is onvolledig, dubbel of verwijst naar een ontbrekende maat.",
                        semantic_id=chain_id,
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
