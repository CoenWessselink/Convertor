"""Deterministic project-part classification and production identity.

AI may suggest labels elsewhere, but this module only applies auditable rules,
normalises known material/profile spellings and keeps unresolved objects blocked.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import re
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .model import (
    EntityCategory,
    FieldProvenance,
    Part,
    ProjectModel,
    ProjectValidationError,
    ValidationIssue,
    stable_sha256,
    utc_now_iso,
)

CLASSIFICATION_VERSION = "cws-classification-v2"
PRODUCTION_IDENTITY_VERSION = "cws-production-identity-v1"
_VALID_CLASSIFICATIONS = {
    EntityCategory.MAKE_PART.value,
    EntityCategory.PURCHASED_ITEM.value,
    EntityCategory.NON_STEEL.value,
    EntityCategory.REFERENCE.value,
    EntityCategory.UNKNOWN.value,
}

_MATERIAL_ALIASES = {
    "S235 JR": "S235JR",
    "STEEL/S235JR": "S235JR",
    "S355 JR": "S355JR",
    "STEEL/S355JR": "S355JR",
    "CONCRETE/C20/25": "C20/25",
    "CONCRETE/C50/60": "C50/60",
}
_NON_STEEL_CATEGORIES = {
    "Hout", "Gelamineerd hout", "Houtplaat", "Beton", "Kunststof", "Technische kunststof",
}
_FASTENER_CATEGORIES = {"Bevestigingsstaal", "RVS bevestigingsmiddelen"}
_FASTENER_GRADES = {
    "4.6", "5.6", "5.8", "6.8", "8.8", "9.8", "10.9", "12.9",
    "A2", "A2-50", "A2-70", "A2-80",
    "A4", "A4-50", "A4-70", "A4-80",
}
_FASTENER_WORDS = {
    "BOUT", "BOLT", "MOER", "NUT", "RING", "WASHER", "ANKER",
    "DRAADEIND", "DRAADSTANG", "SCHROEF", "SCREW", "FASTENER",
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


@lru_cache(maxsize=1)
def _profile_catalog() -> Any:
    from profile_database import ProfileDatabase

    return ProfileDatabase(writable_copy=False)


@lru_cache(maxsize=1)
def _material_catalog() -> Any:
    from material_database import MaterialDatabase

    return MaterialDatabase()


def _profile_lookup_candidates(value: Any) -> tuple[str, ...]:
    raw = _text(value).upper().replace(",", ".").replace("×", "X")
    # Resolve only anchored workshop aliases. Every derived spelling still
    # has to match exactly one immutable catalogue row; substring/fuzzy
    # matching is deliberately not used here.
    candidates = [raw]
    rectangular = re.fullmatch(
        r"K(?:OKER)?\s*(\d+(?:\.\d+)?)\s*(?:[X*]|/)\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
        raw,
    )
    square = re.fullmatch(
        r"K(?:OKER)?\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
        raw,
    )
    if rectangular:
        height, width, wall = rectangular.groups()
        candidates.append(f"RHS{height}X{width}X{wall}")
    elif square:
        side, wall = square.groups()
        candidates.append(f"SHS{side}X{side}X{wall}")

    unp = re.fullmatch(r"UNP[- ]?(\d+(?:\.\d+)?)", raw)
    if unp:
        candidates.append(f"UPN{unp.group(1)}")

    flat = re.fullmatch(
        r"(?:STRIP|PL|PLAAT|FLAT)\s*(\d+(?:\.\d+)?)\s*[X*]\s*(\d+(?:\.\d+)?)",
        raw,
    )
    if flat:
        thickness, width = flat.groups()
        candidates.append(f"FLAT{width}X{thickness}")

    equal_angle = re.fullmatch(
        r"L\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
        raw,
    )
    if equal_angle:
        leg, thickness = equal_angle.groups()
        candidates.append(f"L{leg}X{leg}X{thickness}")

    round_bar = re.fullmatch(
        r"(?:ROND|ROUND|ROD|DIA|DIA\.|[Ø⌀])\s*[Ø⌀]?\s*(\d+(?:\.\d+)?)",
        raw,
    )
    if round_bar:
        candidates.append(f"ROUND{round_bar.group(1)}")

    return tuple(candidates)


def _profile_exact_key(value: str) -> str:
    """Normalize display spelling without merging different dimensions.

    Decimal points and slashes carry dimensions. Removing all punctuation
    previously let SHS20x20x15 resolve to SHS20x20x1.5, for example.
    Only explicit dimensional/display equivalents are interchangeable here.
    """
    key = re.sub(r"\s+", "", str(value or "").upper())
    key = key.replace(",", ".").replace("×", "X").replace("*", "X")
    return re.sub(r"^(HEA|HEB|HEM|IPE|IPN|UPN|UPE)-(?=\d)", r"\1", key)


@lru_cache(maxsize=2)
def _catalog_profile_index(
    snapshot: tuple[tuple[str, tuple[str, ...]], ...],
) -> Mapping[str, frozenset[str]]:
    """Immutable exact index, invalidated by row/alias content changes.

    A fresh cheap tuple snapshot at lookup time detects list replacement,
    appended rows and direct alias edits without a mutable stale index. Store
    every designation for a key: first-match selection would hide conflicts.
    """
    mutable: dict[str, set[str]] = {}
    for designation, aliases in snapshot:
        for value in (designation, *aliases):
            key = _profile_exact_key(value)
            if key:
                mutable.setdefault(key, set()).add(designation)
    return MappingProxyType({key: frozenset(values) for key, values in mutable.items()})


def _catalog_profile(value: Any) -> str:

    keys = {
        _profile_exact_key(candidate)
        for candidate in _profile_lookup_candidates(value)
        if candidate
    }
    if not keys:
        return ""
    try:
        snapshot = tuple(
            (profile.designation, tuple(profile.aliases))
            for profile in _profile_catalog().profiles
        )
        index = _catalog_profile_index(snapshot)
        matches = set().union(*(index.get(key, ()) for key in keys))
    except Exception:
        matches = set()
    return next(iter(matches)) if len(matches) == 1 else ""


def _catalog_material(value: Any) -> str:
    from material_database import normalise_material

    key = normalise_material(_MATERIAL_ALIASES.get(_text(value).upper(), _text(value)))
    if not key:
        return ""
    try:
        matches = [material.code for material in _material_catalog().materials if key in material.search_names]
    except Exception:
        matches = []
    return matches[0] if len(set(matches)) == 1 else ""


def normalize_material(value: Any) -> str:
    text = _text(value).upper().replace("–", "-")
    if text.startswith("STEEL/") and text not in _MATERIAL_ALIASES:
        text = text.split("/", 1)[1]
    text = _MATERIAL_ALIASES.get(text, text)
    return _catalog_material(text) or text


def normalize_profile(value: Any) -> str:
    text = _text(value).upper()
    text = text.replace("×", "*").replace(" X ", "*")
    text = re.sub(r"\s*\*\s*", "*", text)
    text = re.sub(r"\s+", "", text)
    # Preserve recognisable catalog spellings while removing harmless separators.
    text = text.replace("HEA-", "HEA").replace("HEB-", "HEB").replace("IPE-", "IPE")
    return _catalog_profile(text) or text


def fastener_grade_candidates(*values: Any) -> tuple[str, ...]:
    """Return exact, canonical grades carried by fastener-specific fields.

    Standards such as ``EN ISO 4014-8.8`` and material labels such as
    ``STEEL/8.8`` are supported, while partial numbers (``18.8``) and unknown
    grade-like text remain unresolved. Multiple different grades are kept so
    the importer can fail closed instead of choosing one silently.
    """

    found: set[str] = set()
    numeric = r"4\.6|5\.6|5\.8|6\.8|8\.8|9\.8|10\.9|12\.9"
    for value in values:
        text = _text(value).upper().replace("–", "-").replace("—", "-")
        if not text:
            continue
        for match in re.finditer(rf"(?<![0-9.])({numeric})(?![0-9.])", text):
            found.add(match.group(1))
        for match in re.finditer(
            r"(?<![A-Z0-9])(A[24])(?:\s*[-/]\s*(50|70|80))?(?![A-Z0-9])",
            text,
        ):
            family, strength = match.groups()
            found.add(f"{family}-{strength}" if strength else family)
    return tuple(sorted(found))


def normalize_fastener_grade(*values: Any) -> str:
    """Return a grade only when all supplied evidence is unambiguous."""

    candidates = fastener_grade_candidates(*values)
    return candidates[0] if len(candidates) == 1 else ""


@dataclass(frozen=True)
class ClassificationDecision:
    part_id: str
    category: str
    status: str
    method: str
    rule_id: str
    reason: str
    confidence: float
    normalized_profile: str
    normalized_material: str
    profile_confidence: float
    material_confidence: float
    blocking_reasons: tuple[str, ...] = ()
    source_entity_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["blocking_reasons"] = list(self.blocking_reasons)
        return data


@dataclass(frozen=True)
class IdentityConflict:
    conflict_id: str
    conflict_type: str
    key: str
    entity_ids: tuple[str, ...]
    hashes: tuple[str, ...]
    message: str
    severity: str = "warning"
    blocking: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entity_ids"] = list(self.entity_ids)
        data["hashes"] = list(self.hashes)
        return data


@dataclass
class ClassificationReport:
    project_id: str
    generated_at: str
    version: str
    category_counts: dict[str, int]
    classified_part_count: int
    unknown_part_count: int
    review_required_count: int
    blocking_part_count: int
    identity_conflict_count: int
    blocking_identity_conflict_count: int
    source_ids: list[str]
    conflicts: list[IdentityConflict] = field(default_factory=list)
    decisions: list[ClassificationDecision] = field(default_factory=list)
    report_sha256: str = ""

    def to_dict(self, *, include_decisions: bool = True) -> dict[str, Any]:
        data = {
            "project_id": self.project_id,
            "generated_at": self.generated_at,
            "version": self.version,
            "category_counts": dict(self.category_counts),
            "classified_part_count": self.classified_part_count,
            "unknown_part_count": self.unknown_part_count,
            "review_required_count": self.review_required_count,
            "blocking_part_count": self.blocking_part_count,
            "identity_conflict_count": self.identity_conflict_count,
            "blocking_identity_conflict_count": self.blocking_identity_conflict_count,
            "source_ids": list(self.source_ids),
            "conflicts": [item.to_dict() for item in self.conflicts],
            "report_sha256": self.report_sha256,
        }
        if include_decisions:
            data["decisions"] = [item.to_dict() for item in self.decisions]
        return data

    def refresh_hash(self) -> str:
        data = self.to_dict(include_decisions=True)
        data.pop("generated_at", None)
        data["report_sha256"] = ""
        self.report_sha256 = stable_sha256(data)
        return self.report_sha256


def _part_source_class(part: Part) -> str:
    return _text(part.properties.get("ifc_entity_type") or part.part_type).upper()


def _raw_material(part: Part) -> str:
    return _text(part.material_grade or part.material)


def decide_part_classification(part: Part) -> ClassificationDecision:
    raw_material = _raw_material(part)
    raw_profile = part.profile
    exact_material = _catalog_material(raw_material)
    material_definition = _material_catalog().find(exact_material) if exact_material else None
    material_category = material_definition.category if material_definition else ""
    exact_profile = _catalog_profile(raw_profile)
    material = exact_material or normalize_material(raw_material)
    profile = exact_profile or normalize_profile(raw_profile)
    source_format = _text(part.source_identity.source_format).upper()
    source_class = _part_source_class(part)
    combined = " ".join(
        [part.name, part.part_position, part.profile, source_class]
    ).upper()
    words = set(re.findall(r"[A-Z0-9.]+", combined))

    category = EntityCategory.UNKNOWN.value
    status = "review_required"
    rule_id = "CWS-CLASS-UNKNOWN"
    reason = "Onvoldoende betrouwbare productie- of inkoopkenmerken."
    confidence = 0.45
    blocking: list[str] = []

    if material_category in _FASTENER_CATEGORIES or material in _FASTENER_GRADES or words.intersection(_FASTENER_WORDS):
        category = EntityCategory.PURCHASED_ITEM.value
        status = "automatic"
        rule_id = "CWS-CLASS-PURCHASED-FASTENER-COMPONENT"
        reason = "Standaard bevestigingscomponent op basis van kwaliteit/naam."
        confidence = 0.99
    elif material_category in _NON_STEEL_CATEGORIES:
        category = EntityCategory.NON_STEEL.value
        status = "automatic"
        rule_id = "CWS-CLASS-NON-STEEL-MATERIAL"
        reason = "Expliciet niet-metallisch catalogusmateriaal."
        confidence = 0.99
    elif source_format == "STEP" and "VOETPLAAT" in combined and not exact_material:
        category = EntityCategory.MAKE_PART.value
        status = "review_required"
        rule_id = "CWS-CLASS-STEP-FOOTPLATE"
        reason = "Naam duidt op maakdeel, maar profiel/materiaal ontbreken in STEP."
        confidence = 0.82
        blocking.extend(["Materiaal ontbreekt", "Productieprofiel/-features nog niet bevestigd"])
    elif source_format == "STEP" and not material:
        category = EntityCategory.UNKNOWN.value
        status = "review_required"
        rule_id = "CWS-CLASS-STEP-AMBIGUOUS"
        reason = "STEP-solid zonder betrouwbare materiaal- of productclassificatie."
        confidence = 0.45
        blocking.append("Handmatige keuze maakdeel of inkoopdeel vereist")
    elif (material_definition is not None) or source_class in {
        "IFCPLATE", "IFCBEAM", "IFCCOLUMN", "IFCMEMBER"
    }:
        category = EntityCategory.MAKE_PART.value
        status = "automatic"
        rule_id = "CWS-CLASS-STEEL-MAKE-PART"
        reason = "Metallisch catalogusmateriaal of expliciete maakdeelklasse; productiegates blijven apart."
        confidence = 0.99
    else:
        blocking.append("Objectcategorie moet handmatig worden bevestigd")

    material_conflict = bool(
        part.material and part.material_grade
        and normalize_material(part.material) != normalize_material(part.material_grade)
    )
    if material_conflict:
        blocking.append("Bronmateriaal en materiaalkwaliteit conflicteren")
    if not exact_material:
        blocking.append("Materiaal ontbreekt of is niet exact als cataloguscode/alias herkend")
    if category == EntityCategory.MAKE_PART.value:
        if not profile:
            blocking.append("Productieprofiel ontbreekt; geometriehash is geen profielbewijs")
        elif profile and not exact_profile:
            blocking.append("Profiel niet exact in de vaste profielendatabase; handmatig bevestigen")
    if blocking:
        status = "review_required"
    if not part.part_position:
        blocking.append("Part position ontbreekt")
        if status == "automatic":
            status = "review_required"

    return ClassificationDecision(
        part_id=part.internal_id,
        category=category,
        status=status,
        method="deterministic_rules",
        rule_id=rule_id,
        reason=reason,
        confidence=confidence,
        normalized_profile=profile,
        normalized_material="" if material_conflict else exact_material,
        profile_confidence=1.0 if exact_profile else (0.65 if profile else 0.0),
        material_confidence=1.0 if exact_material and not material_conflict else 0.0,
        blocking_reasons=tuple(dict.fromkeys(blocking)),
        source_entity_id=part.source_identity.source_entity_id,
    )


def compute_production_identity(part: Part) -> str:
    """Placement-independent identity used by BOM and revision control."""
    payload = {
        "version": PRODUCTION_IDENTITY_VERSION,
        "category": part.category,
        "geometry_hash": part.geometry_hash,
        "manufacturing_hash": part.manufacturing_hash,
        "profile": part.normalized_profile or normalize_profile(part.profile),
        "material": part.normalized_material or normalize_material(_raw_material(part)),
        "length_mm": round(float(part.length_mm or 0.0), 6),
        "features": part.production_features,
        "reference_sides": part.reference_sides,
        "mirrored": bool(part.mirrored),
        "tolerances": part.tolerances,
        "coating": _text(part.coating).upper(),
    }
    return stable_sha256(payload)


def _remove_classification_issues(part: Part) -> None:
    part.validation_issues = [
        issue for issue in part.validation_issues
        if not issue.code.startswith("CWS-CLASSIFICATION-")
    ]


def _apply_decision(part: Part, decision: ClassificationDecision, *, user: str) -> None:
    _remove_classification_issues(part)
    part.category = decision.category
    part.classification_status = decision.status
    part.classification_method = decision.method
    part.classification_rule_id = decision.rule_id
    part.classification_reason = decision.reason
    part.classification_confidence = decision.confidence
    part.normalized_profile = decision.normalized_profile
    part.normalized_material = decision.normalized_material
    part.profile_confidence = decision.profile_confidence
    part.material_confidence = decision.material_confidence
    part.production_identity_version = PRODUCTION_IDENTITY_VERSION
    part.production_identity_hash = compute_production_identity(part)
    part.bom_group_key = part.production_identity_hash
    part.field_provenance["category"] = FieldProvenance(
        source_file_id=part.source_identity.source_file_id,
        source_entity_id=part.source_identity.source_entity_id,
        source_path="classification.category",
        method=decision.method,
        confidence=decision.confidence,
        status="automatic" if decision.status != "confirmed" else "confirmed",
        confirmed_by=user if decision.status == "confirmed" else "",
        confirmed_at=utc_now_iso() if decision.status == "confirmed" else "",
        notes=[decision.rule_id, decision.reason],
    )
    for index, reason in enumerate(decision.blocking_reasons, start=1):
        part.validation_issues.append(
            ValidationIssue(
                code=f"CWS-CLASSIFICATION-BLOCK-{index:02d}",
                message=reason,
                severity="error",
                blocking=True,
                entity_id=part.internal_id,
                field_path="classification",
                source=part.source_identity.source_entity_id,
            )
        )
    part.modified_at = utc_now_iso()


def detect_identity_conflicts(parts: Iterable[Part]) -> list[IdentityConflict]:
    material_parts = [p for p in parts if p.category != EntityCategory.PURCHASED_ITEM.value]
    conflicts: list[IdentityConflict] = []

    by_mark: dict[str, list[Part]] = defaultdict(list)
    for part in material_parts:
        if part.part_position:
            by_mark[part.part_position].append(part)
    for mark, group in sorted(by_mark.items()):
        hashes = sorted({p.production_identity_hash for p in group if p.production_identity_hash})
        if len(hashes) > 1:
            ids = tuple(sorted(p.internal_id for p in group))
            conflicts.append(IdentityConflict(
                conflict_id=stable_sha256(["same_mark_different_identity", mark, ids]),
                conflict_type="same_mark_different_manufacturing",
                key=mark,
                entity_ids=ids,
                hashes=tuple(hashes),
                message=f"Part position {mark} bevat {len(hashes)} verschillende productie-identiteiten.",
                severity="error",
                blocking=True,
                evidence={"part_position": mark, "occurrence_count": len(group)},
            ))

    by_geometry: dict[str, list[Part]] = defaultdict(list)
    for part in material_parts:
        if part.geometry_hash:
            by_geometry[part.geometry_hash].append(part)
    for geometry_hash, group in sorted(by_geometry.items()):
        marks = sorted({p.part_position for p in group if p.part_position})
        materials = sorted({p.normalized_material for p in group if p.normalized_material})
        ids = tuple(sorted(p.internal_id for p in group))
        if len(marks) > 1:
            conflicts.append(IdentityConflict(
                conflict_id=stable_sha256(["same_geometry_different_marks", geometry_hash, marks]),
                conflict_type="same_geometry_different_marks",
                key=geometry_hash,
                entity_ids=ids,
                hashes=(geometry_hash,),
                message=f"Dezelfde geometrie komt voor onder meerdere posities: {', '.join(marks[:8])}.",
                severity="warning",
                blocking=False,
                evidence={"part_positions": marks},
            ))
        if len(materials) > 1:
            conflicts.append(IdentityConflict(
                conflict_id=stable_sha256(["same_geometry_different_material", geometry_hash, materials]),
                conflict_type="same_geometry_different_material",
                key=geometry_hash,
                entity_ids=ids,
                hashes=(geometry_hash,),
                message=f"Dezelfde geometrie heeft verschillende materialen: {', '.join(materials)}.",
                severity="error",
                blocking=True,
                evidence={"materials": materials},
            ))

    for part in sorted(material_parts, key=lambda p: p.internal_id):
        if not part.part_position:
            conflicts.append(IdentityConflict(
                conflict_id=stable_sha256(["missing_part_position", part.internal_id]),
                conflict_type="missing_part_position",
                key=part.internal_id,
                entity_ids=(part.internal_id,),
                hashes=(part.production_identity_hash,),
                message=f"Onderdeel {part.name or part.internal_id} heeft geen part position.",
                severity="error",
                blocking=True,
            ))
        if part.category == EntityCategory.UNKNOWN.value:
            conflicts.append(IdentityConflict(
                conflict_id=stable_sha256(["unknown_classification", part.internal_id]),
                conflict_type="unknown_classification",
                key=part.internal_id,
                entity_ids=(part.internal_id,),
                hashes=(part.production_identity_hash,),
                message=f"Onderdeel {part.name or part.internal_id} is nog niet geclassificeerd.",
                severity="error",
                blocking=True,
            ))
    return conflicts


def classify_project(
    project: ProjectModel,
    *,
    user: str = "system",
    source_ids: Iterable[str] | None = None,
    force: bool = False,
    include_decisions: bool = False,
) -> ClassificationReport:
    selected = {str(item) for item in source_ids or []}
    decisions: list[ClassificationDecision] = []
    for part in project.parts.values():
        if selected and part.source_identity.source_file_id not in selected:
            continue
        if part.classification_status == "confirmed" and not force:
            continue
        decision = decide_part_classification(part)
        _apply_decision(part, decision, user=user)
        decisions.append(decision)

    conflicts = detect_identity_conflicts(project.parts.values())
    category_counts = Counter(part.category for part in project.parts.values())
    review_count = sum(
        1 for part in project.parts.values()
        if part.classification_status in {"review_required", "blocked"}
    )
    blocking_part_count = sum(1 for part in project.parts.values() if part.blocking_issues())
    report = ClassificationReport(
        project_id=project.project_id,
        generated_at=utc_now_iso(),
        version=CLASSIFICATION_VERSION,
        category_counts=dict(sorted(category_counts.items())),
        classified_part_count=len(project.parts),
        unknown_part_count=category_counts.get(EntityCategory.UNKNOWN.value, 0),
        review_required_count=review_count,
        blocking_part_count=blocking_part_count,
        identity_conflict_count=len(conflicts),
        blocking_identity_conflict_count=sum(1 for item in conflicts if item.blocking),
        source_ids=sorted(selected or project.sources.keys()),
        conflicts=conflicts,
        decisions=decisions if include_decisions else [],
    )
    report.refresh_hash()
    project.settings["classification"] = report.to_dict(include_decisions=False)
    project.audit(
        "project.classified",
        user=user,
        after_hash=report.report_sha256,
        details={
            "version": CLASSIFICATION_VERSION,
            "category_counts": report.category_counts,
            "conflicts": len(conflicts),
            "blocking_conflicts": report.blocking_identity_conflict_count,
        },
    )
    project.validate()
    return report


def set_manual_part_classification(
    project: ProjectModel,
    part_id: str,
    category: str,
    *,
    user: str,
    reason: str,
    normalized_profile: str | None = None,
    normalized_material: str | None = None,
) -> ClassificationReport:
    if category not in _VALID_CLASSIFICATIONS:
        raise ProjectValidationError(f"Ongeldige handmatige classificatie {category!r}")
    part = project.parts.get(part_id)
    if part is None:
        raise ProjectValidationError(f"Onbekend onderdeel {part_id}")
    if not _text(reason):
        raise ProjectValidationError("Handmatige classificatie vereist een reden")
    if not _text(user):
        raise ProjectValidationError("Handmatige classificatie vereist een reviewer")
    material = (
        _catalog_material(normalized_material)
        if normalized_material is not None
        else part.normalized_material or _catalog_material(_raw_material(part))
    )
    if normalized_material is not None and not material:
        raise ProjectValidationError("Materiaalbevestiging vereist een exacte cataloguscode of alias")
    if category == EntityCategory.MAKE_PART.value and normalized_material is None:
        if part.material and part.material_grade and normalize_material(part.material) != normalize_material(part.material_grade):
            raise ProjectValidationError("Conflicterend materiaal en kwaliteit moeten eerst worden opgelost")
    profile = normalize_profile(part.profile if normalized_profile is None else normalized_profile)
    decision = ClassificationDecision(
        part_id=part.internal_id,
        category=category,
        status="confirmed",
        method="manual_review",
        rule_id="CWS-CLASS-MANUAL-CONFIRMATION",
        reason=_text(reason),
        confidence=1.0,
        normalized_profile=profile,
        normalized_material=material,
        # Confirming a category does not silently confirm unrelated fields.
        profile_confidence=(1.0 if normalized_profile is not None else part.profile_confidence) if profile else 0.0,
        material_confidence=(1.0 if normalized_material is not None else part.material_confidence) if material else 0.0,
        blocking_reasons=(),
        source_entity_id=part.source_identity.source_entity_id,
    )
    before = stable_sha256(part.base_to_dict())
    _apply_decision(part, decision, user=user)
    for field_name, supplied, value in (
        ("normalized_profile", normalized_profile, profile),
        ("normalized_material", normalized_material, material),
    ):
        if supplied is not None and value:
            part.field_provenance[field_name] = FieldProvenance(
                source_file_id=part.source_identity.source_file_id,
                source_entity_id=part.source_identity.source_entity_id,
                source_path=f"classification.{field_name}",
                method="manual_review", confidence=1.0, status="confirmed",
                confirmed_by=user, confirmed_at=utc_now_iso(),
                notes=[reason, f"Bevestigd als {value}"],
            )
    project.audit(
        "part.classification_confirmed",
        user=user,
        entity_id=part_id,
        before_hash=before,
        after_hash=stable_sha256(part.base_to_dict()),
        details={"category": category, "reason": reason},
    )
    return classify_project(project, user=user, force=False)


__all__ = [
    "CLASSIFICATION_VERSION",
    "PRODUCTION_IDENTITY_VERSION",
    "ClassificationDecision",
    "IdentityConflict",
    "ClassificationReport",
    "normalize_material",
    "normalize_profile",
    "fastener_grade_candidates",
    "normalize_fastener_grade",
    "decide_part_classification",
    "compute_production_identity",
    "detect_identity_conflicts",
    "classify_project",
    "set_manual_part_classification",
]
