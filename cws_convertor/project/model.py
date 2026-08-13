"""Canonical Project Model 2.x for CWS Convertor.

The project model sits above the existing :class:`canonical_model.CanonicalPart`.
It adds stable project identity, assemblies, procurement, stock, production and
machine entities while preserving the proven deterministic part payload.

Geometry and manufacturing fingerprints deliberately exclude global placement.
Moving a part in a building therefore does not invalidate its NC1/PDF output,
while changing material or a production feature does.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, is_dataclass
import copy
import datetime as _dt
from enum import Enum
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, ClassVar, Iterable, Mapping, TypeVar
from uuid import UUID, uuid4, uuid5

from canonical_model import CanonicalPart, sha256_file
from cws_convertor.errors import CWSError, ErrorCode
from cws_convertor.product import APP_VERSION, PROJECT_SCHEMA_VERSION

PROJECT_ID_NAMESPACE = UUID("bbd71aef-84df-4e31-bd22-c2c1c8b91c69")
HASH_ALGORITHM_VERSION = "cws-geometry-v1"
MANUFACTURING_HASH_VERSION = "cws-manufacturing-v1"
ROTATION_TOLERANCE = 1e-6


class ProjectValidationError(CWSError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, ErrorCode.PROJECT_INVALID, details)


class EntityCategory(str, Enum):
    MAKE_PART = "make_part"
    PURCHASED_ITEM = "purchased_item"
    FASTENER = "fastener"
    WELD = "weld"
    ASSEMBLY = "assembly"
    NON_STEEL = "non_steel"
    REFERENCE = "reference"
    UNKNOWN = "unknown"


class ImportStrategy(str, Enum):
    """Safest available import route for a complete IFC/STEP source."""

    SEMANTIC_STRUCTURE = "A_semantic_structure"
    SEPARATE_SOLIDS = "B_separate_solids"
    FUSED_REVIEW = "C_fused_review"
    NOT_ANALYSED = "not_analysed"


class ReviewStatus(str, Enum):
    NEW = "new"
    REVIEW_REQUIRED = "review_required"
    VALIDATED = "validated"
    RELEASED = "released"
    BLOCKED = "blocked"
    OBSOLETE = "obsolete"


def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _normalise_for_hash(value: Any, *, precision: int = 9) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(key): _normalise_for_hash(item, precision=precision)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalise_for_hash(item, precision=precision) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectValidationError("Niet-eindige numerieke waarde in projectdata")
        rounded = round(value, precision)
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def stable_json_bytes(value: Any) -> bytes:
    stream = io.StringIO()
    _write_stable_json(value, stream.write)
    return stream.getvalue().encode("utf-8")


def stable_sha256(value: Any) -> str:
    digest = hashlib.sha256()
    fragments: list[str] = []
    fragment_size = 0

    def write(fragment: str) -> None:
        nonlocal fragment_size
        fragments.append(fragment)
        fragment_size += len(fragment)
        if fragment_size >= 128 * 1024:
            digest.update("".join(fragments).encode("utf-8"))
            fragments.clear()
            fragment_size = 0

    _write_stable_json(value, write)
    if fragments:
        digest.update("".join(fragments).encode("utf-8"))
    return digest.hexdigest()


def _write_stable_json(value: Any, write, *, precision: int = 9) -> None:
    """Stream the canonical JSON representation without a second full copy.

    The previous implementation first normalised an entire project graph and
    then asked :func:`json.dumps` to allocate another complete string.  On a
    multi-thousand-object IFC model, three consecutive hashes could retain
    enough allocator memory to stall the desktop process.  This writer keeps
    exactly the same canonical ordering and numeric rules while emitting
    fragments incrementally.
    """

    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, Path):
        value = str(value)
    if isinstance(value, Mapping):
        # Project snapshots overwhelmingly use string keys.  Avoid allocating a
        # duplicate key map for every nested object; only fall back to the
        # historical string-key conversion when a non-string key is present.
        if all(isinstance(key, str) for key in value):
            mapped = value
        else:
            mapped = {str(key): item for key, item in value.items()}
        write("{")
        first = True
        for key in sorted(mapped):
            if not first:
                write(",")
            first = False
            # ``encode_basestring`` is the same JSON string encoder used by
            # ``json.dumps`` but avoids constructing a new encoder for every
            # key.  A 6k-object IFC project contains hundreds of thousands of
            # keys, so this is a material save-time improvement.
            write(json.encoder.encode_basestring(key))
            write(":")
            _write_stable_json(mapped[key], write, precision=precision)
        write("}")
        return
    if isinstance(value, (list, tuple)):
        write("[")
        for index, item in enumerate(value):
            if index:
                write(",")
            _write_stable_json(item, write, precision=precision)
        write("]")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProjectValidationError("Niet-eindige numerieke waarde in projectdata")
        rounded = round(value, precision)
        value = 0.0 if rounded == 0.0 else rounded
        # CPython's JSON encoder serialises finite floats with ``repr``.
        # Reusing that representation avoids a full ``json.dumps`` call for
        # every coordinate while keeping the previous canonical bytes.
        write(repr(value))
        return
    if isinstance(value, bool):
        write("true" if value else "false")
        return
    if value is None:
        write("null")
        return
    if isinstance(value, int):
        write(str(value))
        return
    if isinstance(value, str):
        write(json.encoder.encode_basestring(value))
        return
    write(json.encoder.encode_basestring(str(value)))


def _major(version: str) -> str:
    return str(version).split(".", 1)[0]


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted numeric schema version without accepting loose text.

    Project packages are production evidence.  A future ``2.9`` schema must
    not be treated as compatible merely because it shares major version 2.
    """

    text = str(version or "").strip()
    if not text:
        return ()
    parts = text.split(".")
    if any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def project_hash_bundle_from_snapshot(snapshot: Mapping[str, Any]) -> dict[str, str]:
    """Calculate the three canonical project hashes from one detached snapshot.

    This helper is shared by :class:`ProjectModel` and the project package
    writer.  It preserves the exact v0.6 hash semantics while avoiding repeated
    recursive ``to_dict`` copies for large semantic IFC projects.
    """

    semantic_hash = stable_sha256(snapshot)
    content_payload = {
        key: value
        for key, value in snapshot.items()
        if key not in {"app_version", "modified_at", "audit_log", "revisions"}
    }
    content_hash = stable_sha256(content_payload)
    revision_payload = dict(content_payload)
    revision_payload["sources"] = {
        source_id: {
            key: value
            for key, value in dict(source).items()
            if key not in {"original_path", "embedded_path"}
        }
        for source_id, source in dict(content_payload.get("sources") or {}).items()
    }
    revision_hash = stable_sha256(revision_payload)
    return {
        "semantic_sha256": semantic_hash,
        "content_sha256": content_hash,
        "revision_content_sha256": revision_hash,
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _enum_value(value: Any) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def _require_finite_number(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    strictly_positive: bool = False,
) -> float:
    """Validate one numeric project value and return it as ``float``.

    Project data is persisted for later production phases.  NaN/Infinity and
    negative quantities must therefore be rejected at the model boundary,
    rather than leaking into BOM totals, optimisation or machine jobs.
    """

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ProjectValidationError(f"{label} is geen geldig getal") from exc
    if not math.isfinite(number):
        raise ProjectValidationError(f"{label} moet eindig zijn")
    if strictly_positive and number <= 0.0:
        raise ProjectValidationError(f"{label} moet groter dan nul zijn")
    if minimum is not None and number < minimum:
        raise ProjectValidationError(f"{label} mag niet kleiner zijn dan {minimum:g}")
    return number


def _require_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ProjectValidationError(f"{label} moet een positief geheel getal zijn")
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ProjectValidationError(f"{label} moet een positief geheel getal zijn") from exc
    try:
        original = float(value)
    except (TypeError, ValueError):
        original = float(number)
    if not math.isfinite(original) or abs(original - number) > 1e-9 or number < 1:
        raise ProjectValidationError(f"{label} moet een positief geheel getal zijn")
    return number


def _require_unique_ids(values: Iterable[str], label: str) -> list[str]:
    items = [str(value) for value in values]
    if any(not item for item in items):
        raise ProjectValidationError(f"{label} bevat een lege ID")
    if len(items) != len(set(items)):
        raise ProjectValidationError(f"{label} bevat dubbele IDs")
    return items


@dataclass
class Transform3D:
    """Right-handed homogeneous transform stored row-major as a 4x4 matrix."""

    matrix: list[list[float]] = field(
        default_factory=lambda: [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    @classmethod
    def identity(cls) -> "Transform3D":
        return cls()

    @classmethod
    def from_flat(cls, values: Iterable[float]) -> "Transform3D":
        items = [float(item) for item in values]
        if len(items) != 16:
            raise ProjectValidationError("Een placementmatrix moet 16 waarden bevatten")
        return cls([items[index : index + 4] for index in range(0, 16, 4)])

    def flat(self) -> list[float]:
        self.validate()
        return [float(item) for row in self.matrix for item in row]

    def translation_mm(self) -> tuple[float, float, float]:
        self.validate()
        return (
            float(self.matrix[0][3]),
            float(self.matrix[1][3]),
            float(self.matrix[2][3]),
        )

    def validate(self) -> None:
        if len(self.matrix) != 4 or any(len(row) != 4 for row in self.matrix):
            raise ProjectValidationError("Placementmatrix moet exact 4x4 zijn")
        for row in self.matrix:
            for item in row:
                if not math.isfinite(float(item)):
                    raise ProjectValidationError("Placementmatrix bevat een niet-eindige waarde")
        expected = [0.0, 0.0, 0.0, 1.0]
        if any(abs(float(a) - b) > 1e-9 for a, b in zip(self.matrix[3], expected)):
            raise ProjectValidationError("Laatste rij van placementmatrix moet [0,0,0,1] zijn")

        # Project placements are rigid, right-handed coordinate systems.  A
        # reflection would silently turn a normal part into its mirrored
        # production variant, so reject it at the model boundary rather than
        # leaving that ambiguity to an exporter.
        axes = [
            [float(self.matrix[row][column]) for row in range(3)]
            for column in range(3)
        ]
        lengths = [math.sqrt(sum(component * component for component in axis)) for axis in axes]
        if any(length <= 1e-12 for length in lengths):
            raise ProjectValidationError("Placementmatrix bevat een nul-as")
        normalised = [
            [component / length for component in axis]
            for axis, length in zip(axes, lengths)
        ]
        for left in range(3):
            for right in range(left + 1, 3):
                dot = sum(
                    normalised[left][index] * normalised[right][index]
                    for index in range(3)
                )
                if abs(dot) > 1e-6:
                    raise ProjectValidationError("Placementassen moeten onderling loodrecht zijn")
        x_axis, y_axis, z_axis = normalised
        cross_xy = [
            x_axis[1] * y_axis[2] - x_axis[2] * y_axis[1],
            x_axis[2] * y_axis[0] - x_axis[0] * y_axis[2],
            x_axis[0] * y_axis[1] - x_axis[1] * y_axis[0],
        ]
        handedness = sum(cross_xy[index] * z_axis[index] for index in range(3))
        if handedness <= 1e-6:
            raise ProjectValidationError("Placementmatrix moet een rechterhandig assenstelsel bevatten")

        # Project placements are rigid, right-handed transforms.  Accepting a
        # mirrored/scaled/sheared matrix here would make local geometry hashes
        # and manufacturing orientation ambiguous.  Validate the upper-left
        # 3x3 rotation explicitly instead of silently normalising it.
        rotation = [
            [float(self.matrix[row][column]) for column in range(3)]
            for row in range(3)
        ]
        for index, axis in enumerate(rotation):
            norm = math.sqrt(sum(component * component for component in axis))
            if abs(norm - 1.0) > ROTATION_TOLERANCE:
                raise ProjectValidationError(
                    f"Placementas {index + 1} is niet genormaliseerd (norm={norm:.9g})"
                )
        for left in range(3):
            for right in range(left + 1, 3):
                dot = sum(rotation[left][index] * rotation[right][index] for index in range(3))
                if abs(dot) > ROTATION_TOLERANCE:
                    raise ProjectValidationError(
                        "Placementmatrix bevat niet-orthogonale assen"
                    )
        determinant = (
            rotation[0][0]
            * (rotation[1][1] * rotation[2][2] - rotation[1][2] * rotation[2][1])
            - rotation[0][1]
            * (rotation[1][0] * rotation[2][2] - rotation[1][2] * rotation[2][0])
            + rotation[0][2]
            * (rotation[1][0] * rotation[2][1] - rotation[1][1] * rotation[2][0])
        )
        if abs(determinant - 1.0) > ROTATION_TOLERANCE:
            raise ProjectValidationError(
                "Placementmatrix moet rechtsdraaiend zijn en determinant +1 hebben "
                f"(gevonden {determinant:.9g})"
            )

    @classmethod
    def from_dict(cls, value: Any) -> "Transform3D":
        if isinstance(value, cls):
            value.validate()
            return value
        if isinstance(value, dict):
            if "matrix" in value:
                result = cls([[float(item) for item in row] for row in value["matrix"]])
            elif "flat" in value:
                result = cls.from_flat(value["flat"])
            else:
                result = cls.identity()
        elif isinstance(value, (list, tuple)):
            result = cls.from_flat(value)
        else:
            result = cls.identity()
        result.validate()
        return result


@dataclass
class SourceIdentity:
    source_format: str = ""
    source_file_id: str = ""
    source_sha256: str = ""
    source_entity_id: str = ""
    global_id: str = ""
    product_id: str = ""
    occurrence_id: str = ""
    part_position: str = ""
    assembly_mark: str = ""

    def stable_key(self) -> str:
        values = [
            self.source_format.upper(),
            self.source_sha256.lower(),
            self.source_entity_id,
            self.global_id,
            self.product_id,
            self.occurrence_id,
            self.part_position,
            self.assembly_mark,
        ]
        return "|".join(str(item).strip() for item in values)

    @classmethod
    def from_dict(cls, value: Any) -> "SourceIdentity":
        raw = dict(value or {}) if isinstance(value, dict) else {}
        allowed = {item.name for item in fields(cls)}
        return cls(**{key: raw[key] for key in allowed if key in raw})


@dataclass
class FieldProvenance:
    source_file_id: str = ""
    source_entity_id: str = ""
    source_path: str = ""
    method: str = "exact"
    confidence: float = 1.0
    status: str = "automatic"  # automatic, confirmed, corrected, derived
    confirmed_by: str = ""
    confirmed_at: str = ""
    notes: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ProjectValidationError("Provenance-confidence moet tussen 0 en 1 liggen")

    @classmethod
    def from_dict(cls, value: Any) -> "FieldProvenance":
        raw = dict(value or {}) if isinstance(value, dict) else {}
        allowed = {item.name for item in fields(cls)}
        result = cls(**{key: raw[key] for key in allowed if key in raw})
        result.validate()
        return result


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "warning"  # information, warning, error
    blocking: bool = False
    entity_id: str = ""
    field_path: str = ""
    source: str = ""
    resolved: bool = False
    resolution: str = ""
    resolved_by: str = ""
    resolved_at: str = ""

    @classmethod
    def from_dict(cls, value: Any) -> "ValidationIssue":
        raw = dict(value or {}) if isinstance(value, dict) else {}
        allowed = {item.name for item in fields(cls)}
        return cls(**{key: raw[key] for key in allowed if key in raw})


@dataclass
class AuditEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now_iso)
    user: str = "system"
    action: str = ""
    entity_id: str = ""
    before_hash: str = ""
    after_hash: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Any) -> "AuditEvent":
        raw = dict(value or {}) if isinstance(value, dict) else {}
        allowed = {item.name for item in fields(cls)}
        return cls(**{key: raw[key] for key in allowed if key in raw})


@dataclass
class SourceFileRecord:
    source_id: str
    file_name: str
    source_format: str
    sha256: str
    size_bytes: int
    original_path: str = ""
    imported_at: str = field(default_factory=utc_now_iso)
    embedded_path: str = ""
    schema: str = ""
    application: str = ""
    import_strategy: str = ImportStrategy.NOT_ANALYSED.value
    analysis_status: str = "registered"
    semantic_import_complete: bool = False
    production_export_allowed: bool = False
    analysis: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        project_id: str,
        path: str | Path,
        *,
        source_format: str | None = None,
    ) -> "SourceFileRecord":
        source = Path(path)
        digest = sha256_file(source)
        fmt = (source_format or source.suffix.lstrip(".") or "unknown").upper()
        source_id = str(uuid5(PROJECT_ID_NAMESPACE, f"{project_id}|source|{digest}|{source.name}"))
        return cls(
            source_id=source_id,
            file_name=source.name,
            source_format=fmt,
            sha256=digest,
            size_bytes=source.stat().st_size,
            original_path=str(source.resolve()),
        )

    @classmethod
    def from_dict(cls, value: Any) -> "SourceFileRecord":
        raw = dict(value or {}) if isinstance(value, dict) else {}
        allowed = {item.name for item in fields(cls)}
        result = cls(**{key: raw[key] for key in allowed if key in raw})
        try:
            ImportStrategy(result.import_strategy)
        except ValueError as exc:
            raise ProjectValidationError(
                f"Onbekende importstrategie {result.import_strategy!r}"
            ) from exc
        if result.analysis_status not in {
            "registered", "analyzing", "analyzed", "imported", "review_required", "failed"
        }:
            raise ProjectValidationError(
                f"Onbekende bronanalysestatus {result.analysis_status!r}"
            )
        return result


@dataclass
class ProjectEntity:
    internal_id: str
    name: str = ""
    category: str = EntityCategory.UNKNOWN.value
    source_identity: SourceIdentity = field(default_factory=SourceIdentity)
    local_placement: Transform3D = field(default_factory=Transform3D.identity)
    global_placement: Transform3D = field(default_factory=Transform3D.identity)
    properties: dict[str, Any] = field(default_factory=dict)
    field_provenance: dict[str, FieldProvenance] = field(default_factory=dict)
    confidence: float = 1.0
    status: str = ReviewStatus.NEW.value
    revision: str = ""
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    modified_at: str = field(default_factory=utc_now_iso)

    ENTITY_TYPE: ClassVar[str] = "entity"

    @property
    def entity_type(self) -> str:
        return self.ENTITY_TYPE

    def blocking_issues(self) -> list[ValidationIssue]:
        return [issue for issue in self.validation_issues if issue.blocking and not issue.resolved]

    def validate_base(self) -> None:
        if not self.internal_id:
            raise ProjectValidationError(f"{self.entity_type} mist internal_id")
        try:
            EntityCategory(self.category)
        except ValueError as exc:
            raise ProjectValidationError(
                f"{self.entity_type} {self.internal_id} heeft onbekende categorie {self.category!r}"
            ) from exc
        confidence = _require_finite_number(
            self.confidence,
            f"Confidence van {self.entity_type} {self.internal_id}",
        )
        if not 0.0 <= confidence <= 1.0:
            raise ProjectValidationError(
                f"{self.entity_type} {self.internal_id} heeft ongeldige confidence"
            )
        self.local_placement.validate()
        self.global_placement.validate()
        for field_path, provenance in self.field_provenance.items():
            if not str(field_path).strip():
                raise ProjectValidationError(
                    f"{self.entity_type} {self.internal_id} bevat provenance zonder veldpad"
                )
            provenance.validate()
        for issue in self.validation_issues:
            if not issue.code.strip() or not issue.message.strip():
                raise ProjectValidationError(
                    f"{self.entity_type} {self.internal_id} bevat een onvolledige validatiekwestie"
                )
            if issue.severity not in {"information", "warning", "error"}:
                raise ProjectValidationError(
                    f"Validatiekwestie {issue.code} heeft onbekende severity {issue.severity!r}"
                )
        source_sha = self.source_identity.source_sha256.strip()
        if source_sha and (
            len(source_sha) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in source_sha)
        ):
            raise ProjectValidationError(
                f"{self.entity_type} {self.internal_id} heeft een ongeldige bron-SHA-256"
            )

    def base_to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["entity_type"] = self.entity_type
        return data


@dataclass
class Assembly(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "assembly"
    category: str = EntityCategory.ASSEMBLY.value
    assembly_mark: str = ""
    quantity: int = 1
    child_assembly_ids: list[str] = field(default_factory=list)
    part_ids: list[str] = field(default_factory=list)
    main_part_id: str = ""
    purchased_item_ids: list[str] = field(default_factory=list)
    fastener_ids: list[str] = field(default_factory=list)
    weld_ids: list[str] = field(default_factory=list)
    total_weight_kg: float = 0.0
    surface_area_m2: float = 0.0
    production_status: str = ReviewStatus.NEW.value
    drawing_status: str = "not_created"
    artifact_ids: list[str] = field(default_factory=list)


@dataclass
class Part(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "part"
    category: str = EntityCategory.MAKE_PART.value
    part_position: str = ""
    assembly_ids: list[str] = field(default_factory=list)
    quantity_total: int = 1
    quantity_per_assembly: dict[str, int] = field(default_factory=dict)
    part_type: str = "unknown"
    profile: str = ""
    profile_type: str = ""
    material: str = ""
    material_grade: str = ""
    length_mm: float = 0.0
    mass_each_kg: float = 0.0
    surface_area_each_m2: float = 0.0
    canonical_part: dict[str, Any] | None = None
    geometry_descriptor: dict[str, Any] = field(default_factory=dict)
    production_features: list[dict[str, Any]] = field(default_factory=list)
    reference_sides: list[str] = field(default_factory=list)
    mirrored: bool = False
    tolerances: dict[str, Any] = field(default_factory=dict)
    coating: str = ""
    geometry_hash: str = ""
    manufacturing_hash: str = ""
    hash_algorithm_version: str = HASH_ALGORITHM_VERSION
    manufacturing_hash_version: str = MANUFACTURING_HASH_VERSION
    nc1_eligible: bool = False
    export_status: str = "blocked"
    workbench: dict[str, Any] = field(default_factory=dict)
    classification_status: str = "unclassified"
    classification_method: str = ""
    classification_rule_id: str = ""
    classification_reason: str = ""
    classification_confidence: float = 0.0
    normalized_profile: str = ""
    normalized_material: str = ""
    profile_confidence: float = 0.0
    material_confidence: float = 0.0
    production_identity_hash: str = ""
    production_identity_version: str = "cws-production-identity-v1"
    bom_group_key: str = ""

    def canonical(self) -> CanonicalPart | None:
        return CanonicalPart.from_dict(self.canonical_part) if self.canonical_part else None

    def set_canonical(self, canonical: CanonicalPart) -> None:
        self.canonical_part = canonical.to_dict()
        self.profile = canonical.header.profile
        self.profile_type = canonical.header.profile_type
        self.material = canonical.header.material
        self.material_grade = canonical.product.material_grade or canonical.header.material
        self.length_mm = canonical.product.length_mm or canonical.header.length
        self.mass_each_kg = canonical.product.mass_each_kg or canonical.header.weight
        self.surface_area_each_m2 = canonical.product.area_each_m2
        self.part_position = canonical.header.position_number or canonical.part_id
        self.name = canonical.product.name or self.part_position or self.name
        self.quantity_total = max(1, int(canonical.header.quantity or 1))
        self.coating = canonical.product.coating
        self.production_features = [
            {
                "kind": "contour",
                "face": item.kind + ":" + item.face,
                "points": [asdict(point) for point in item.points],
            }
            for item in canonical.contours
        ] + [
            {
                "kind": "hole",
                "face": hole.face,
                "x": hole.x,
                "q": hole.q,
                "diameter": hole.diameter,
                "depth": hole.depth,
                "operation": hole.operation,
            }
            for hole in canonical.holes
        ]
        self.nc1_eligible = bool(canonical.refresh_export_gate())
        self.recompute_hashes()

    def _geometry_fingerprint_payload(self) -> dict[str, Any]:
        workbench_payload: dict[str, Any] = {}
        if self.workbench:
            from .workbench import workbench_geometry_payload

            workbench_payload = workbench_geometry_payload(self.workbench)
        canonical = self.canonical()
        if canonical is not None:
            frame = dict(canonical.coordinate_frame or {})
            frame["origin_mm"] = [0.0, 0.0, 0.0]
            payload = {
                "version": self.hash_algorithm_version,
                "coordinate_axes": frame,
                "mirrored": self.mirrored,
                "header": {
                    "profile": canonical.header.profile,
                    "profile_type": canonical.header.profile_type,
                    "length": canonical.header.length,
                    "saw_length": canonical.header.saw_length,
                    "dim1": canonical.header.dim1,
                    "dim2": canonical.header.dim2,
                    "dim3": canonical.header.dim3,
                    "dim4": canonical.header.dim4,
                    "radius": canonical.header.radius,
                },
                "contours": [asdict(item) for item in canonical.contours],
                "holes": [asdict(item) for item in canonical.holes],
                "geometry": canonical.geometry,
            }
            if workbench_payload:
                payload["workbench"] = workbench_payload
            return payload
        descriptor = self.geometry_descriptor
        # Semantic IFC/STEP descriptors contain source entity IDs for audit and
        # viewer navigation.  Those occurrence IDs must never make otherwise
        # identical production geometry look different.  When an importer has
        # supplied an ID-independent source-geometry fingerprint, hash only the
        # geometry-relevant facts and keep the rich source descriptor outside
        # the manufacturing fingerprint.
        if isinstance(descriptor, Mapping) and descriptor.get("source_geometry_hash"):
            representation_types = sorted(
                {
                    str(item.get("representation_type") or "")
                    for item in list(descriptor.get("representations") or [])
                    if isinstance(item, Mapping)
                    and str(item.get("representation_type") or "")
                }
            )
            descriptor = {
                "source_geometry_hash": descriptor.get("source_geometry_hash"),
                "primitive_counts": descriptor.get("primitive_counts", {}),
                "profile_names": descriptor.get("profile_names", []),
                "extrusion_depths_source_units": descriptor.get(
                    "extrusion_depths_source_units", []
                ),
                "representation_types": representation_types,
                "solid_count": descriptor.get("solid_count"),
                "volume_mm3": descriptor.get("volume_mm3"),
                "area_mm2": descriptor.get("area_mm2"),
                "bbox_sorted_mm": descriptor.get("bbox_sorted_mm"),
                "topology": descriptor.get("topology", {}),
            }
        payload = {
            "version": self.hash_algorithm_version,
            "descriptor": descriptor,
            "features": self.production_features,
            "profile": self.profile,
            "profile_type": self.profile_type,
            "length_mm": self.length_mm,
            "mirrored": self.mirrored,
        }
        if workbench_payload:
            payload["workbench"] = workbench_payload
        return payload

    def _manufacturing_fingerprint_payload(self, geometry_hash: str) -> dict[str, Any]:
        return {
            "version": self.manufacturing_hash_version,
            "geometry_hash": geometry_hash,
            "material": self.material,
            "material_grade": self.material_grade,
            "profile": self.profile,
            "profile_type": self.profile_type,
            "length_mm": self.length_mm,
            "features": self.production_features,
            "reference_sides": self.reference_sides,
            "mirrored": self.mirrored,
            "tolerances": self.tolerances,
            "coating": self.coating,
        }

    def recompute_hashes(self) -> tuple[str, str]:
        self.geometry_hash = stable_sha256(self._geometry_fingerprint_payload())
        self.manufacturing_hash = stable_sha256(
            self._manufacturing_fingerprint_payload(self.geometry_hash)
        )
        return self.geometry_hash, self.manufacturing_hash

    def validate_hashes(self) -> None:
        if isinstance(self.geometry_descriptor, Mapping) and self.geometry_descriptor.get(
            "source_locator"
        ):
            from .source_geometry import SourceGeometryError, validate_source_locator

            try:
                validate_source_locator(self)
            except SourceGeometryError as exc:
                raise ProjectValidationError(exc.message, exc.details) from exc
        if self.workbench:
            from .workbench import validate_workbench_state

            validate_workbench_state(self, self.workbench)
        valid_statuses = {"unclassified", "automatic", "review_required", "confirmed", "blocked"}
        if self.classification_status not in valid_statuses:
            raise ProjectValidationError(
                f"Onderdeel {self.internal_id} heeft ongeldige classificatiestatus {self.classification_status!r}"
            )
        for label, value in (
            ("classification_confidence", self.classification_confidence),
            ("profile_confidence", self.profile_confidence),
            ("material_confidence", self.material_confidence),
        ):
            numeric = _require_finite_number(value, f"{label} van onderdeel {self.internal_id}")
            if not 0.0 <= numeric <= 1.0:
                raise ProjectValidationError(
                    f"Onderdeel {self.internal_id} heeft ongeldige {label}"
                )
        if self.production_identity_hash and (
            len(self.production_identity_hash) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in self.production_identity_hash)
        ):
            raise ProjectValidationError(
                f"Onderdeel {self.internal_id} heeft ongeldige production identity hash"
            )
        current_geometry = self.geometry_hash
        current_manufacturing = self.manufacturing_hash
        expected_geometry = stable_sha256(self._geometry_fingerprint_payload())
        expected_manufacturing = stable_sha256(
            self._manufacturing_fingerprint_payload(expected_geometry)
        )
        if current_geometry and current_geometry != expected_geometry:
            raise ProjectValidationError(
                f"Geometry hash van onderdeel {self.internal_id} klopt niet",
                {"stored": current_geometry, "expected": expected_geometry},
            )
        if current_manufacturing and current_manufacturing != expected_manufacturing:
            raise ProjectValidationError(
                f"Manufacturing hash van onderdeel {self.internal_id} klopt niet",
                {"stored": current_manufacturing, "expected": expected_manufacturing},
            )
        self.geometry_hash = expected_geometry
        self.manufacturing_hash = expected_manufacturing


@dataclass
class PurchasedItem(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "purchased_item"
    category: str = EntityCategory.PURCHASED_ITEM.value
    article_number: str = ""
    supplier: str = ""
    manufacturer: str = ""
    description: str = ""
    standard: str = ""
    material: str = ""
    grade: str = ""
    dimensions: dict[str, Any] = field(default_factory=dict)
    quantity: float = 1.0
    unit: str = "piece"
    unit_price: float = 0.0
    lead_time_days: int = 0
    alternatives: list[str] = field(default_factory=list)
    internal_processing_required: bool = False
    purchase_status: str = ReviewStatus.NEW.value
    assembly_ids: list[str] = field(default_factory=list)


@dataclass
class Fastener(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "fastener"
    category: str = EntityCategory.FASTENER.value
    fastener_type: str = ""
    diameter_mm: float = 0.0
    grade: str = ""
    length_mm: float = 0.0
    standard: str = ""
    quantity: int = 1
    connected_part_ids: list[str] = field(default_factory=list)
    hole_diameter_mm: float = 0.0
    slot: dict[str, Any] = field(default_factory=dict)


@dataclass
class Weld(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "weld"
    category: str = EntityCategory.WELD.value
    weld_type: str = ""
    size_mm: float = 0.0
    length_mm: float = 0.0
    process: str = ""
    side: str = ""
    location: str = "workshop"
    connected_part_ids: list[str] = field(default_factory=list)
    time_minutes: float = 0.0
    cost: float = 0.0


@dataclass
class StockItem(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "stock_item"
    material: str = ""
    profile: str = ""
    grade: str = ""
    stock_length_mm: float = 0.0
    plate_size_mm: list[float] = field(default_factory=list)
    heat_number: str = ""
    batch: str = ""
    certificate: str = ""
    supplier: str = ""
    location: str = ""
    available_quantity: float = 0.0
    reserved_quantity: float = 0.0
    unit_price: float = 0.0
    status: str = "available"


@dataclass
class Remnant(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "remnant"
    stock_item_id: str = ""
    material: str = ""
    profile: str = ""
    grade: str = ""
    remaining_length_mm: float = 0.0
    remaining_contour: dict[str, Any] = field(default_factory=dict)
    minimum_reusable_mm: float = 0.0
    location: str = ""
    measured_at: str = ""
    status: str = "available"


@dataclass
class ProductionOperation(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "production_operation"
    operation_type: str = ""
    part_ids: list[str] = field(default_factory=list)
    machine_class: str = ""
    machine_id: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    cycle_time_minutes: float = 0.0
    tool: str = ""
    quality_checks: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MachineProfile(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "machine_profile"
    machine_id: str = ""
    manufacturer: str = ""
    machine_type: str = ""
    controller: str = ""
    supported_formats: list[str] = field(default_factory=list)
    min_dimensions_mm: dict[str, float] = field(default_factory=dict)
    max_dimensions_mm: dict[str, float] = field(default_factory=dict)
    axes: list[str] = field(default_factory=list)
    supported_operations: list[str] = field(default_factory=list)
    tools: list[dict[str, Any]] = field(default_factory=list)
    kerf_mm: float = 0.0
    clamp_zones: list[dict[str, Any]] = field(default_factory=list)
    tolerance_mm: float = 0.0
    postprocessor_version: str = ""
    enabled: bool = False


@dataclass
class MachineJob(ProjectEntity):
    ENTITY_TYPE: ClassVar[str] = "machine_job"
    machine_id: str = ""
    part_ids: list[str] = field(default_factory=list)
    operation_ids: list[str] = field(default_factory=list)
    postprocessor_version: str = ""
    simulation_status: str = "not_run"
    release_status: str = "blocked"
    job_file: str = ""
    checksum: str = ""
    operator: str = ""
    output_log: list[str] = field(default_factory=list)


ENTITY_TYPES: dict[str, type[ProjectEntity]] = {
    cls.ENTITY_TYPE: cls
    for cls in (
        Assembly,
        Part,
        PurchasedItem,
        Fastener,
        Weld,
        StockItem,
        Remnant,
        ProductionOperation,
        MachineProfile,
        MachineJob,
    )
}

ENTITY_COLLECTIONS: dict[str, str] = {
    "assembly": "assemblies",
    "part": "parts",
    "purchased_item": "purchased_items",
    "fastener": "fasteners",
    "weld": "welds",
    "stock_item": "stock_items",
    "remnant": "remnants",
    "production_operation": "production_operations",
    "machine_profile": "machine_profiles",
    "machine_job": "machine_jobs",
}


TEntity = TypeVar("TEntity", bound=ProjectEntity)


def _entity_from_dict(entity_type: str, value: dict[str, Any]) -> ProjectEntity:
    cls = ENTITY_TYPES.get(entity_type)
    if cls is None:
        raise ProjectValidationError(f"Onbekend projectentitytype {entity_type!r}")
    raw = dict(value or {})
    raw.pop("entity_type", None)
    raw["source_identity"] = SourceIdentity.from_dict(raw.get("source_identity"))
    raw["local_placement"] = Transform3D.from_dict(raw.get("local_placement"))
    raw["global_placement"] = Transform3D.from_dict(raw.get("global_placement"))
    raw["field_provenance"] = {
        str(key): FieldProvenance.from_dict(item)
        for key, item in dict(raw.get("field_provenance") or {}).items()
    }
    raw["validation_issues"] = [
        ValidationIssue.from_dict(item) for item in list(raw.get("validation_issues") or [])
    ]
    allowed = {item.name for item in fields(cls)}
    entity = cls(**{key: raw[key] for key in allowed if key in raw})
    entity.validate_base()
    if isinstance(entity, Part):
        entity.validate_hashes()
    return entity


@dataclass
class ProjectModel:
    schema_version: str = PROJECT_SCHEMA_VERSION
    app_version: str = APP_VERSION
    project_id: str = field(default_factory=lambda: str(uuid4()))
    project_name: str = "Nieuw project"
    description: str = ""
    customer: str = ""
    order_number: str = ""
    project_phase: str = ""
    units: str = "mm"
    coordinate_system: dict[str, Any] = field(
        default_factory=lambda: {
            "name": "project",
            "origin_mm": [0.0, 0.0, 0.0],
            "x_axis": [1.0, 0.0, 0.0],
            "y_axis": [0.0, 1.0, 0.0],
            "z_axis": [0.0, 0.0, 1.0],
        }
    )
    created_at: str = field(default_factory=utc_now_iso)
    modified_at: str = field(default_factory=utc_now_iso)
    created_by: str = ""
    status: str = ReviewStatus.NEW.value
    sources: dict[str, SourceFileRecord] = field(default_factory=dict)
    assemblies: dict[str, Assembly] = field(default_factory=dict)
    parts: dict[str, Part] = field(default_factory=dict)
    purchased_items: dict[str, PurchasedItem] = field(default_factory=dict)
    fasteners: dict[str, Fastener] = field(default_factory=dict)
    welds: dict[str, Weld] = field(default_factory=dict)
    stock_items: dict[str, StockItem] = field(default_factory=dict)
    remnants: dict[str, Remnant] = field(default_factory=dict)
    production_operations: dict[str, ProductionOperation] = field(default_factory=dict)
    machine_profiles: dict[str, MachineProfile] = field(default_factory=dict)
    machine_jobs: dict[str, MachineJob] = field(default_factory=dict)
    materials: dict[str, dict[str, Any]] = field(default_factory=dict)
    production_orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    revisions: list[dict[str, Any]] = field(default_factory=list)
    validation_issues: list[ValidationIssue] = field(default_factory=list)
    audit_log: list[AuditEvent] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)
    migration_history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def new(
        cls,
        project_name: str,
        *,
        description: str = "",
        customer: str = "",
        order_number: str = "",
        project_phase: str = "",
        created_by: str = "",
    ) -> "ProjectModel":
        project = cls(
            project_name=project_name.strip() or "Nieuw project",
            description=description.strip(),
            customer=customer.strip(),
            order_number=order_number.strip(),
            project_phase=project_phase.strip(),
            created_by=created_by.strip(),
        )
        project.audit("project.created", user=created_by or "system")
        return project

    def audit(
        self,
        action: str,
        *,
        user: str = "system",
        entity_id: str = "",
        before_hash: str = "",
        after_hash: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            user=user or "system",
            action=action,
            entity_id=entity_id,
            before_hash=before_hash,
            after_hash=after_hash,
            details=dict(details or {}),
        )
        self.audit_log.append(event)
        self.modified_at = event.timestamp
        return event

    def stable_entity_id(self, entity_type: str, identity: SourceIdentity | str) -> str:
        key = identity.stable_key() if isinstance(identity, SourceIdentity) else str(identity)
        if not key.strip("|"):
            raise ProjectValidationError("Stabiele entity-ID vereist een bronidentiteit")
        return str(uuid5(PROJECT_ID_NAMESPACE, f"{self.project_id}|{entity_type}|{key}"))

    def upsert_validation_issue(
        self,
        issue: ValidationIssue,
        *,
        user: str = "system",
    ) -> ValidationIssue:
        """Create or update one stable validation issue without duplicates."""

        existing = next(
            (
                item
                for item in self.validation_issues
                if item.code == issue.code
                and item.entity_id == issue.entity_id
                and item.field_path == issue.field_path
            ),
            None,
        )
        if existing is None:
            self.validation_issues.append(issue)
            target = issue
            action = "validation_issue.added"
        else:
            before = stable_sha256(existing)
            for field_info in fields(ValidationIssue):
                setattr(existing, field_info.name, getattr(issue, field_info.name))
            target = existing
            action = "validation_issue.updated"
            self.audit(
                action,
                user=user,
                entity_id=target.entity_id,
                before_hash=before,
                after_hash=stable_sha256(target),
                details={"code": target.code},
            )
            return target
        self.audit(
            action,
            user=user,
            entity_id=target.entity_id,
            after_hash=stable_sha256(target),
            details={"code": target.code},
        )
        return target

    def mark_source_semantic_import_pending(
        self,
        source_id: str,
        *,
        user: str = "system",
    ) -> None:
        source = self.sources.get(source_id)
        if source is None:
            raise ProjectValidationError(f"Onbekende projectbron {source_id}")
        source.semantic_import_complete = False
        source.production_export_allowed = False
        source.metadata["semantic_import_pending"] = True
        source.metadata["production_export_allowed"] = False
        self.upsert_validation_issue(
            ValidationIssue(
                code="CWS-PROJECT-SOURCE-PENDING-SEMANTIC-IMPORT",
                message=(
                    f"Bron {source.file_name} is alleen geïnventariseerd; "
                    "semantische IFC/STEP-import en productievrijgave ontbreken nog."
                ),
                severity="warning",
                blocking=True,
                entity_id=source_id,
                field_path="sources.semantic_import",
                source=source.file_name,
            ),
            user=user,
        )
        self.status = ReviewStatus.REVIEW_REQUIRED.value

    def mark_source_semantic_import_complete(
        self,
        source_id: str,
        *,
        production_export_allowed: bool,
        user: str = "system",
    ) -> None:
        """Resolve the intake gate after a later semantic importer has run."""

        source = self.sources.get(source_id)
        if source is None:
            raise ProjectValidationError(f"Onbekende projectbron {source_id}")
        source.semantic_import_complete = True
        source.production_export_allowed = bool(production_export_allowed)
        source.analysis_status = (
            "imported" if production_export_allowed else "review_required"
        )
        source.metadata["semantic_import_pending"] = False
        source.metadata["production_export_allowed"] = bool(production_export_allowed)
        for issue in self.validation_issues:
            if (
                issue.code == "CWS-PROJECT-SOURCE-PENDING-SEMANTIC-IMPORT"
                and issue.entity_id == source_id
            ):
                issue.resolved = True
                issue.resolution = "Semantische import afgerond"
                issue.resolved_by = user or "system"
                issue.resolved_at = utc_now_iso()
        production_issue = ValidationIssue(
            code="CWS-PROJECT-SOURCE-PRODUCTION-BLOCKED",
            message=(
                f"Bron {source.file_name} is semantisch geïmporteerd, maar de "
                "productievalidatie is nog niet vrijgegeven."
            ),
            severity="error",
            blocking=not bool(production_export_allowed),
            entity_id=source_id,
            field_path="sources.production_export_allowed",
            source=source.file_name,
            resolved=bool(production_export_allowed),
            resolution=(
                "Productievalidatie geslaagd" if production_export_allowed else ""
            ),
            resolved_by=(user or "system") if production_export_allowed else "",
            resolved_at=utc_now_iso() if production_export_allowed else "",
        )
        self.upsert_validation_issue(production_issue, user=user)
        self.audit(
            "source.semantic_import_completed",
            user=user,
            entity_id=source_id,
            details={"production_export_allowed": bool(production_export_allowed)},
        )
        self.status = (
            ReviewStatus.VALIDATED.value
            if not self.blocking_issues()
            else ReviewStatus.REVIEW_REQUIRED.value
        )

    def add_source_path(
        self,
        path: str | Path,
        *,
        source_format: str | None = None,
        user: str = "system",
    ) -> SourceFileRecord:
        record = SourceFileRecord.from_path(
            self.project_id,
            path,
            source_format=source_format,
        )
        existing = next(
            (item for item in self.sources.values() if item.sha256 == record.sha256),
            None,
        )
        if existing is not None:
            return existing
        self.sources[record.source_id] = record
        self.audit(
            "source.added",
            user=user,
            entity_id=record.source_id,
            details={"file_name": record.file_name, "sha256": record.sha256},
        )
        return record

    def add_entity(self, entity: TEntity, *, user: str = "system") -> TEntity:
        collection_name = ENTITY_COLLECTIONS.get(entity.entity_type)
        if collection_name is None:
            raise ProjectValidationError(f"Niet-ondersteund entitytype {entity.entity_type}")
        collection: dict[str, TEntity] = getattr(self, collection_name)
        existing = self.get_entity(entity.internal_id)
        if existing is not None and existing.entity_type != entity.entity_type:
            raise ProjectValidationError(
                f"Entity-ID {entity.internal_id} is al in gebruik door {existing.entity_type}"
            )
        before_hash = stable_sha256(existing.base_to_dict()) if existing is not None else ""
        entity.validate_base()
        if isinstance(entity, Part):
            entity.validate_hashes()
        collection[entity.internal_id] = entity
        self.audit(
            "entity.updated" if existing is not None else "entity.added",
            user=user,
            entity_id=entity.internal_id,
            before_hash=before_hash,
            after_hash=stable_sha256(entity.base_to_dict()),
            details={"entity_type": entity.entity_type, "name": entity.name},
        )
        return entity

    def add_canonical_part(
        self,
        canonical: CanonicalPart,
        *,
        source_file_id: str = "",
        assembly_id: str = "",
        source_entity_id: str = "",
        user: str = "system",
    ) -> Part:
        source_sha = canonical.source_sha256
        if source_file_id and source_file_id in self.sources:
            source_sha = self.sources[source_file_id].sha256
        identity = SourceIdentity(
            source_format=canonical.source_format,
            source_file_id=source_file_id,
            source_sha256=source_sha,
            source_entity_id=source_entity_id or canonical.part_id,
            part_position=canonical.header.position_number or canonical.part_id,
            assembly_mark=canonical.product.mark or canonical.product.assembly_id,
        )
        internal_id = self.stable_entity_id("part", identity)
        part = self.parts.get(internal_id) or Part(
            internal_id=internal_id,
            source_identity=identity,
            name=canonical.product.name or canonical.part_id,
            status=(
                ReviewStatus.VALIDATED.value
                if canonical.validation.production_export_allowed
                else ReviewStatus.REVIEW_REQUIRED.value
            ),
        )
        part.source_identity = identity
        part.set_canonical(canonical)
        if assembly_id:
            if assembly_id not in part.assembly_ids:
                part.assembly_ids.append(assembly_id)
            part.quantity_per_assembly.setdefault(assembly_id, 1)
        self.add_entity(part, user=user)
        if assembly_id and assembly_id in self.assemblies:
            assembly = self.assemblies[assembly_id]
            if part.internal_id not in assembly.part_ids:
                assembly.part_ids.append(part.internal_id)
                self.add_entity(assembly, user=user)
        return part

    @classmethod
    def from_canonical_part(
        cls,
        canonical: CanonicalPart,
        *,
        project_name: str | None = None,
        user: str = "migration",
    ) -> "ProjectModel":
        name = project_name or canonical.product.project_name or canonical.header.order_number or canonical.part_id
        project = cls.new(
            name or "Geïmporteerd onderdeel",
            customer=canonical.product.client,
            order_number=canonical.header.order_number,
            created_by=user,
        )
        if canonical.source_file and canonical.source_sha256:
            source_id = str(
                uuid5(
                    PROJECT_ID_NAMESPACE,
                    f"{project.project_id}|source|{canonical.source_sha256}|{canonical.source_file}",
                )
            )
            project.sources[source_id] = SourceFileRecord(
                source_id=source_id,
                file_name=canonical.source_file,
                source_format=canonical.source_format,
                sha256=canonical.source_sha256,
                size_bytes=0,
            )
        else:
            source_id = ""
        project.add_canonical_part(canonical, source_file_id=source_id, user=user)
        project.migration_history.append(
            {
                "from": f"CanonicalPart/{canonical.schema_version}",
                "to": f"ProjectModel/{PROJECT_SCHEMA_VERSION}",
                "timestamp": utc_now_iso(),
            }
        )
        project.audit("project.migrated_from_canonical_part", user=user)
        return project

    def remove_entities_for_source(
        self,
        source_id: str,
        *,
        user: str = "system",
    ) -> dict[str, int]:
        """Remove all materialised entities originating from one source.

        Semantic re-import is transactional at the service layer.  This helper
        makes it idempotent by pruning both the entities and every reciprocal
        project relation before the new graph is inserted.  Entities from
        other sources are preserved.
        """

        if source_id not in self.sources:
            raise ProjectValidationError(f"Onbekende projectbron {source_id}")
        remove_ids = {
            entity.internal_id
            for entity in self.iter_entities()
            if entity.source_identity.source_file_id == source_id
        }
        counts: dict[str, int] = {}
        if not remove_ids:
            return {entity_type: 0 for entity_type in ENTITY_COLLECTIONS}

        for assembly in self.assemblies.values():
            if assembly.internal_id in remove_ids:
                continue
            assembly.child_assembly_ids = [
                item for item in assembly.child_assembly_ids if item not in remove_ids
            ]
            assembly.part_ids = [item for item in assembly.part_ids if item not in remove_ids]
            assembly.purchased_item_ids = [
                item for item in assembly.purchased_item_ids if item not in remove_ids
            ]
            assembly.fastener_ids = [
                item for item in assembly.fastener_ids if item not in remove_ids
            ]
            assembly.weld_ids = [item for item in assembly.weld_ids if item not in remove_ids]
            if assembly.main_part_id in remove_ids:
                assembly.main_part_id = ""

        for part in self.parts.values():
            if part.internal_id in remove_ids:
                continue
            part.assembly_ids = [item for item in part.assembly_ids if item not in remove_ids]
            part.quantity_per_assembly = {
                key: value
                for key, value in part.quantity_per_assembly.items()
                if key not in remove_ids
            }
        for purchased in self.purchased_items.values():
            if purchased.internal_id not in remove_ids:
                purchased.assembly_ids = [
                    item for item in purchased.assembly_ids if item not in remove_ids
                ]
        for fastener in self.fasteners.values():
            if fastener.internal_id not in remove_ids:
                fastener.connected_part_ids = [
                    item for item in fastener.connected_part_ids if item not in remove_ids
                ]
        for weld in self.welds.values():
            if weld.internal_id not in remove_ids:
                weld.connected_part_ids = [
                    item for item in weld.connected_part_ids if item not in remove_ids
                ]
        for operation in self.production_operations.values():
            if operation.internal_id not in remove_ids:
                operation.part_ids = [item for item in operation.part_ids if item not in remove_ids]
        for job in self.machine_jobs.values():
            if job.internal_id not in remove_ids:
                job.part_ids = [item for item in job.part_ids if item not in remove_ids]
                job.operation_ids = [
                    item for item in job.operation_ids if item not in remove_ids
                ]

        for entity_type, collection_name in ENTITY_COLLECTIONS.items():
            collection: dict[str, ProjectEntity] = getattr(self, collection_name)
            matching = [key for key in collection if key in remove_ids]
            for key in matching:
                collection.pop(key, None)
            counts[entity_type] = len(matching)

        self.validation_issues = [
            issue for issue in self.validation_issues if issue.entity_id not in remove_ids
        ]
        spatial_trees = self.settings.get("spatial_trees")
        if isinstance(spatial_trees, dict):
            spatial_trees.pop(source_id, None)
        self.audit(
            "source.materialised_entities_removed",
            user=user,
            entity_id=source_id,
            details={"counts": counts},
        )
        return counts

    def get_entity(self, entity_id: str) -> ProjectEntity | None:
        for collection_name in ENTITY_COLLECTIONS.values():
            collection: dict[str, ProjectEntity] = getattr(self, collection_name)
            if entity_id in collection:
                return collection[entity_id]
        return None

    def iter_entities(self) -> Iterable[ProjectEntity]:
        for collection_name in ENTITY_COLLECTIONS.values():
            yield from getattr(self, collection_name).values()

    def entity_counts(self) -> dict[str, int]:
        return {
            entity_type: len(getattr(self, collection_name))
            for entity_type, collection_name in ENTITY_COLLECTIONS.items()
        }

    def blocking_issues(self) -> list[ValidationIssue]:
        result = [
            issue for issue in self.validation_issues if issue.blocking and not issue.resolved
        ]
        for entity in self.iter_entities():
            result.extend(entity.blocking_issues())
        return result

    def production_gate(self) -> dict[str, Any]:
        """Return the deterministic project-wide production release gate.

        A project with only an IFC/STEP baseline scan is intentionally never
        production-ready.  Every registered source must have completed the
        semantic importer and its own validation gate, and no unresolved
        blocking issue may remain anywhere in the project graph.
        """

        source_failures = [
            {
                "source_id": source.source_id,
                "file_name": source.file_name,
                "semantic_import_complete": source.semantic_import_complete,
                "production_export_allowed": source.production_export_allowed,
            }
            for source in self.sources.values()
            if not source.semantic_import_complete or not source.production_export_allowed
        ]
        issues = self.blocking_issues()
        allowed = bool(self.sources) and not source_failures and not issues
        return {
            "allowed": allowed,
            "source_count": len(self.sources),
            "source_failures": source_failures,
            "blocking_issues": [asdict(issue) for issue in issues],
            "reason": (
                "Productie-export vrijgegeven"
                if allowed
                else (
                    "Project bevat nog geen bronbestanden"
                    if not self.sources
                    else "Semantische import of productievalidatie is nog niet compleet"
                )
            ),
        }

    def validate(self, *, verify_hashes: bool = True) -> None:
        """Validate the complete project graph and all production identities.

        Project Model 2.1 is the persistence boundary for later BOM,
        optimisation and machine phases.  Validation is deliberately strict:
        dangling references, cyclic assemblies, non-rigid placements and
        impossible quantities are blocked before a package can be saved.
        """

        if _major(self.schema_version) != _major(PROJECT_SCHEMA_VERSION):
            raise ProjectValidationError(
                f"Niet-ondersteund Project Model-schema {self.schema_version!r}; "
                f"verwacht {PROJECT_SCHEMA_VERSION}"
            )
        if not self.project_id:
            raise ProjectValidationError("Project mist project_id")
        try:
            UUID(self.project_id)
        except ValueError as exc:
            raise ProjectValidationError("Project-ID is geen geldige UUID") from exc
        if not self.project_name.strip():
            raise ProjectValidationError("Projectnaam mag niet leeg zijn")
        if self.units not in {"mm", "inch"}:
            raise ProjectValidationError(f"Niet-ondersteunde projecteenheid {self.units!r}")
        try:
            ReviewStatus(self.status)
        except ValueError as exc:
            raise ProjectValidationError(f"Onbekende projectstatus {self.status!r}") from exc

        coordinate = dict(self.coordinate_system or {})
        try:
            origin = [float(value) for value in coordinate.get("origin_mm", [0.0, 0.0, 0.0])]
            x_axis = [float(value) for value in coordinate.get("x_axis", [1.0, 0.0, 0.0])]
            y_axis = [float(value) for value in coordinate.get("y_axis", [0.0, 1.0, 0.0])]
            z_axis = [float(value) for value in coordinate.get("z_axis", [0.0, 0.0, 1.0])]
        except (TypeError, ValueError) as exc:
            raise ProjectValidationError("Projectassen bevatten geen geldige getallen") from exc
        if any(len(values) != 3 for values in (origin, x_axis, y_axis, z_axis)):
            raise ProjectValidationError("Projectassen en oorsprong moeten drie waarden bevatten")
        Transform3D(
            [
                [x_axis[0], y_axis[0], z_axis[0], origin[0]],
                [x_axis[1], y_axis[1], z_axis[1], origin[1]],
                [x_axis[2], y_axis[2], z_axis[2], origin[2]],
                [0.0, 0.0, 0.0, 1.0],
            ]
        ).validate()

        seen_ids: dict[str, str] = {}
        for entity_type, collection_name in ENTITY_COLLECTIONS.items():
            collection: dict[str, ProjectEntity] = getattr(self, collection_name)
            for key, entity in collection.items():
                if key != entity.internal_id:
                    raise ProjectValidationError(
                        f"Key {key!r} in {collection_name} wijkt af van entity-ID "
                        f"{entity.internal_id!r}"
                    )
                if entity.entity_type != entity_type:
                    raise ProjectValidationError(
                        f"Entity {entity.internal_id} staat in {collection_name}, maar is "
                        f"van type {entity.entity_type}"
                    )
                entity.validate_base()
                previous = seen_ids.get(entity.internal_id)
                if previous is not None:
                    raise ProjectValidationError(
                        f"Dubbele entity-ID {entity.internal_id} in {previous} en "
                        f"{entity.entity_type}"
                    )
                seen_ids[entity.internal_id] = entity.entity_type
                if isinstance(entity, Part) and verify_hashes:
                    entity.validate_hashes()

                identity = entity.source_identity
                if identity.source_file_id:
                    source = self.sources.get(identity.source_file_id)
                    if source is None:
                        raise ProjectValidationError(
                            f"{entity.entity_type} {entity.internal_id} verwijst naar "
                            f"ontbrekende bron {identity.source_file_id}"
                        )
                    if identity.source_sha256 and identity.source_sha256.lower() != source.sha256.lower():
                        raise ProjectValidationError(
                            f"Bronhash van {entity.entity_type} {entity.internal_id} wijkt af "
                            f"van bronrecord {source.source_id}"
                        )

                if isinstance(entity, Assembly):
                    _require_positive_int(entity.quantity, f"Aantal van assembly {entity.internal_id}")
                    _require_finite_number(
                        entity.total_weight_kg,
                        f"Totaalgewicht van assembly {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_finite_number(
                        entity.surface_area_m2,
                        f"Oppervlak van assembly {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_unique_ids(entity.child_assembly_ids, f"Children van assembly {entity.internal_id}")
                    _require_unique_ids(entity.part_ids, f"Onderdelen van assembly {entity.internal_id}")
                    _require_unique_ids(
                        entity.purchased_item_ids,
                        f"Inkoopdelen van assembly {entity.internal_id}",
                    )
                    _require_unique_ids(entity.fastener_ids, f"Fasteners van assembly {entity.internal_id}")
                    _require_unique_ids(entity.weld_ids, f"Lassen van assembly {entity.internal_id}")
                elif isinstance(entity, Part):
                    _require_positive_int(entity.quantity_total, f"Aantal van onderdeel {entity.internal_id}")
                    for label, value in (
                        ("lengte", entity.length_mm),
                        ("massa", entity.mass_each_kg),
                        ("oppervlak", entity.surface_area_each_m2),
                    ):
                        _require_finite_number(
                            value,
                            f"{label.capitalize()} van onderdeel {entity.internal_id}",
                            minimum=0.0,
                        )
                    _require_unique_ids(entity.assembly_ids, f"Assemblies van onderdeel {entity.internal_id}")
                    for assembly_id, quantity in entity.quantity_per_assembly.items():
                        if assembly_id not in entity.assembly_ids:
                            raise ProjectValidationError(
                                f"Onderdeel {entity.internal_id} heeft een aantal voor assembly "
                                f"{assembly_id}, maar geen assemblyrelatie"
                            )
                        _require_positive_int(
                            quantity,
                            f"Aantal van onderdeel {entity.internal_id} in assembly {assembly_id}",
                        )
                elif isinstance(entity, PurchasedItem):
                    _require_finite_number(
                        entity.quantity,
                        f"Aantal van inkoopdeel {entity.internal_id}",
                        strictly_positive=True,
                    )
                    _require_finite_number(
                        entity.unit_price,
                        f"Stukprijs van inkoopdeel {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_finite_number(
                        entity.lead_time_days,
                        f"Levertijd van inkoopdeel {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_unique_ids(entity.assembly_ids, f"Assemblies van inkoopdeel {entity.internal_id}")
                elif isinstance(entity, Fastener):
                    _require_positive_int(entity.quantity, f"Aantal van fastener {entity.internal_id}")
                    for label, value in (
                        ("diameter", entity.diameter_mm),
                        ("lengte", entity.length_mm),
                        ("gatdiameter", entity.hole_diameter_mm),
                    ):
                        _require_finite_number(
                            value,
                            f"{label.capitalize()} van fastener {entity.internal_id}",
                            minimum=0.0,
                        )
                    _require_unique_ids(
                        entity.connected_part_ids,
                        f"Gekoppelde onderdelen van fastener {entity.internal_id}",
                    )
                elif isinstance(entity, Weld):
                    for label, value in (
                        ("lasgrootte", entity.size_mm),
                        ("laslengte", entity.length_mm),
                        ("bewerkingstijd", entity.time_minutes),
                        ("kosten", entity.cost),
                    ):
                        _require_finite_number(
                            value,
                            f"{label.capitalize()} van las {entity.internal_id}",
                            minimum=0.0,
                        )
                    _require_unique_ids(
                        entity.connected_part_ids,
                        f"Gekoppelde onderdelen van las {entity.internal_id}",
                    )
                elif isinstance(entity, StockItem):
                    for label, value in (
                        ("handelslengte", entity.stock_length_mm),
                        ("beschikbare hoeveelheid", entity.available_quantity),
                        ("gereserveerde hoeveelheid", entity.reserved_quantity),
                        ("stukprijs", entity.unit_price),
                    ):
                        _require_finite_number(
                            value,
                            f"{label.capitalize()} van voorraaditem {entity.internal_id}",
                            minimum=0.0,
                        )
                    if float(entity.reserved_quantity) > float(entity.available_quantity) + 1e-9:
                        raise ProjectValidationError(
                            f"Voorraaditem {entity.internal_id} reserveert meer dan beschikbaar is"
                        )
                    for index, value in enumerate(entity.plate_size_mm):
                        _require_finite_number(
                            value,
                            f"Plaatmaat {index + 1} van voorraaditem {entity.internal_id}",
                            strictly_positive=True,
                        )
                elif isinstance(entity, Remnant):
                    _require_finite_number(
                        entity.remaining_length_mm,
                        f"Restlengte van {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_finite_number(
                        entity.minimum_reusable_mm,
                        f"Minimum herbruikbare maat van {entity.internal_id}",
                        minimum=0.0,
                    )
                elif isinstance(entity, ProductionOperation):
                    _require_finite_number(
                        entity.cycle_time_minutes,
                        f"Cyclustijd van bewerking {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_unique_ids(entity.part_ids, f"Onderdelen van bewerking {entity.internal_id}")
                elif isinstance(entity, MachineProfile):
                    _require_finite_number(
                        entity.kerf_mm,
                        f"Kerf van machine {entity.internal_id}",
                        minimum=0.0,
                    )
                    _require_finite_number(
                        entity.tolerance_mm,
                        f"Tolerantie van machine {entity.internal_id}",
                        minimum=0.0,
                    )
                    for key, value in entity.min_dimensions_mm.items():
                        _require_finite_number(
                            value,
                            f"Minimum machineafmeting {key} van {entity.internal_id}",
                            minimum=0.0,
                        )
                    for key, value in entity.max_dimensions_mm.items():
                        maximum = _require_finite_number(
                            value,
                            f"Maximum machineafmeting {key} van {entity.internal_id}",
                            minimum=0.0,
                        )
                        if key in entity.min_dimensions_mm and maximum < float(entity.min_dimensions_mm[key]):
                            raise ProjectValidationError(
                                f"Maximum machineafmeting {key} is kleiner dan het minimum "
                                f"voor {entity.internal_id}"
                            )
                elif isinstance(entity, MachineJob):
                    _require_unique_ids(entity.part_ids, f"Onderdelen van machinejob {entity.internal_id}")
                    _require_unique_ids(
                        entity.operation_ids,
                        f"Bewerkingen van machinejob {entity.internal_id}",
                    )

        for assembly in self.assemblies.values():
            for child_id in assembly.child_assembly_ids:
                if child_id not in self.assemblies:
                    raise ProjectValidationError(
                        f"Assembly {assembly.internal_id} verwijst naar ontbrekende child "
                        f"assembly {child_id}"
                    )
                if child_id == assembly.internal_id:
                    raise ProjectValidationError("Assembly mag zichzelf niet als child bevatten")
            for part_id in assembly.part_ids:
                part = self.parts.get(part_id)
                if part is None:
                    raise ProjectValidationError(
                        f"Assembly {assembly.internal_id} verwijst naar ontbrekend onderdeel {part_id}"
                    )
                if assembly.internal_id not in part.assembly_ids:
                    raise ProjectValidationError(
                        f"Assemblyrelatie tussen {assembly.internal_id} en {part_id} is niet wederkerig"
                    )
            if assembly.main_part_id and assembly.main_part_id not in assembly.part_ids:
                raise ProjectValidationError(
                    f"Hoofdonderdeel {assembly.main_part_id} staat niet in assembly "
                    f"{assembly.internal_id}"
                )
            for purchased_id in assembly.purchased_item_ids:
                purchased = self.purchased_items.get(purchased_id)
                if purchased is None:
                    raise ProjectValidationError(
                        f"Assembly {assembly.internal_id} verwijst naar ontbrekend inkoopdeel "
                        f"{purchased_id}"
                    )
                if assembly.internal_id not in purchased.assembly_ids:
                    raise ProjectValidationError(
                        f"Inkooprelatie tussen {assembly.internal_id} en {purchased_id} is niet wederkerig"
                    )
            for fastener_id in assembly.fastener_ids:
                if fastener_id not in self.fasteners:
                    raise ProjectValidationError(
                        f"Assembly {assembly.internal_id} verwijst naar ontbrekende fastener "
                        f"{fastener_id}"
                    )
            for weld_id in assembly.weld_ids:
                if weld_id not in self.welds:
                    raise ProjectValidationError(
                        f"Assembly {assembly.internal_id} verwijst naar ontbrekende las {weld_id}"
                    )

        # Detect deep assembly cycles; checking only self-reference is not
        # enough for A -> B -> C -> A graphs.
        visit_state: dict[str, int] = {}
        visit_path: list[str] = []

        def visit_assembly(assembly_id: str) -> None:
            state = visit_state.get(assembly_id, 0)
            if state == 2:
                return
            if state == 1:
                try:
                    index = visit_path.index(assembly_id)
                    cycle = visit_path[index:] + [assembly_id]
                except ValueError:
                    cycle = visit_path + [assembly_id]
                raise ProjectValidationError(
                    "Cyclische assemblystructuur: " + " -> ".join(cycle)
                )
            visit_state[assembly_id] = 1
            visit_path.append(assembly_id)
            for child_id in self.assemblies[assembly_id].child_assembly_ids:
                visit_assembly(child_id)
            visit_path.pop()
            visit_state[assembly_id] = 2

        for assembly_id in self.assemblies:
            visit_assembly(assembly_id)

        for part in self.parts.values():
            for assembly_id in part.assembly_ids:
                assembly = self.assemblies.get(assembly_id)
                if assembly is None:
                    raise ProjectValidationError(
                        f"Onderdeel {part.internal_id} verwijst naar ontbrekende assembly "
                        f"{assembly_id}"
                    )
                if part.internal_id not in assembly.part_ids:
                    raise ProjectValidationError(
                        f"Assemblyrelatie tussen {part.internal_id} en {assembly_id} is niet wederkerig"
                    )

        for purchased in self.purchased_items.values():
            for assembly_id in purchased.assembly_ids:
                assembly = self.assemblies.get(assembly_id)
                if assembly is None:
                    raise ProjectValidationError(
                        f"Inkoopdeel {purchased.internal_id} verwijst naar ontbrekende assembly "
                        f"{assembly_id}"
                    )
                if purchased.internal_id not in assembly.purchased_item_ids:
                    raise ProjectValidationError(
                        f"Inkooprelatie tussen {purchased.internal_id} en {assembly_id} is niet wederkerig"
                    )

        for fastener in self.fasteners.values():
            for part_id in fastener.connected_part_ids:
                if part_id not in self.parts:
                    raise ProjectValidationError(
                        f"Fastener {fastener.internal_id} verwijst naar ontbrekend onderdeel {part_id}"
                    )
        for weld in self.welds.values():
            for part_id in weld.connected_part_ids:
                if part_id not in self.parts:
                    raise ProjectValidationError(
                        f"Las {weld.internal_id} verwijst naar ontbrekend onderdeel {part_id}"
                    )
        for operation in self.production_operations.values():
            for part_id in operation.part_ids:
                if part_id not in self.parts:
                    raise ProjectValidationError(
                        f"Bewerking {operation.internal_id} verwijst naar ontbrekend onderdeel {part_id}"
                    )
            if operation.machine_id and not any(
                profile.machine_id == operation.machine_id
                for profile in self.machine_profiles.values()
            ):
                raise ProjectValidationError(
                    f"Bewerking {operation.internal_id} verwijst naar onbekende machine "
                    f"{operation.machine_id}"
                )
        for remnant in self.remnants.values():
            if remnant.stock_item_id and remnant.stock_item_id not in self.stock_items:
                raise ProjectValidationError(
                    f"Reststuk {remnant.internal_id} verwijst naar ontbrekend voorraaditem "
                    f"{remnant.stock_item_id}"
                )

        machine_ids: dict[str, str] = {}
        for profile in self.machine_profiles.values():
            if not profile.machine_id:
                continue
            previous = machine_ids.get(profile.machine_id)
            if previous is not None:
                raise ProjectValidationError(
                    f"Machine-ID {profile.machine_id!r} is dubbel in {previous} en "
                    f"{profile.internal_id}"
                )
            machine_ids[profile.machine_id] = profile.internal_id
        for job in self.machine_jobs.values():
            if job.machine_id and job.machine_id not in machine_ids:
                raise ProjectValidationError(
                    f"Machinejob {job.internal_id} verwijst naar onbekende machine {job.machine_id}"
                )
            for part_id in job.part_ids:
                if part_id not in self.parts:
                    raise ProjectValidationError(
                        f"Machinejob {job.internal_id} verwijst naar ontbrekend onderdeel {part_id}"
                    )
            for operation_id in job.operation_ids:
                if operation_id not in self.production_operations:
                    raise ProjectValidationError(
                        f"Machinejob {job.internal_id} verwijst naar ontbrekende bewerking "
                        f"{operation_id}"
                    )

        for source_id, source in self.sources.items():
            if source_id != source.source_id:
                raise ProjectValidationError(
                    f"Source key {source_id} komt niet overeen met record-ID {source.source_id}"
                )
            if not source.file_name.strip() or not source.source_format.strip():
                raise ProjectValidationError(f"Bron {source_id} mist bestandsnaam of formaat")
            if len(source.sha256) != 64 or any(
                ch not in "0123456789abcdefABCDEF" for ch in source.sha256
            ):
                raise ProjectValidationError(f"Bron {source.file_name} heeft ongeldige SHA-256")
            if int(source.size_bytes) < 0:
                raise ProjectValidationError(
                    f"Bron {source.file_name} heeft negatieve bestandsgrootte"
                )
            try:
                ImportStrategy(source.import_strategy)
            except ValueError as exc:
                raise ProjectValidationError(
                    f"Bron {source.file_name} heeft onbekende importstrategie "
                    f"{source.import_strategy!r}"
                ) from exc
            if source.production_export_allowed and not source.semantic_import_complete:
                raise ProjectValidationError(
                    f"Bron {source.file_name} kan niet productievrij zijn zonder "
                    "afgeronde semantische import"
                )

        valid_reference_ids = set(seen_ids) | set(self.sources)
        for issue in self.validation_issues:
            if not issue.code.strip() or not issue.message.strip():
                raise ProjectValidationError("Project bevat een onvolledige validatiekwestie")
            if issue.severity not in {"information", "warning", "error"}:
                raise ProjectValidationError(
                    f"Validatiekwestie {issue.code} heeft onbekende severity {issue.severity!r}"
                )
            if issue.entity_id and issue.entity_id not in valid_reference_ids:
                raise ProjectValidationError(
                    f"Validatiekwestie {issue.code} verwijst naar onbekende entity "
                    f"{issue.entity_id}"
                )

        revision_ids: set[str] = set()
        revision_sequences: list[int] = []
        for revision in self.revisions:
            revision_id = str(revision.get("revision_id") or "")
            if not revision_id or revision_id in revision_ids:
                raise ProjectValidationError("Project bevat een lege of dubbele revision_id")
            revision_ids.add(revision_id)
            sequence = _require_positive_int(
                revision.get("sequence"),
                f"Volgnummer van revisie {revision_id}",
            )
            revision_sequences.append(sequence)
            for hash_key in (
                "before_content_sha256",
                "content_sha256",
                "manufacturing_state_sha256",
            ):
                digest = str(revision.get(hash_key) or "")
                if digest and (
                    len(digest) != 64
                    or any(ch not in "0123456789abcdefABCDEF" for ch in digest)
                ):
                    raise ProjectValidationError(
                        f"Revisie {revision_id} bevat ongeldige {hash_key}"
                    )
        if revision_sequences and revision_sequences != list(range(1, len(revision_sequences) + 1)):
            raise ProjectValidationError(
                "Revisievolgnummers moeten uniek, oplopend en zonder gaten zijn"
            )

        audit_ids: set[str] = set()
        for event in self.audit_log:
            if not event.event_id or event.event_id in audit_ids:
                raise ProjectValidationError("Auditlog bevat een lege of dubbele event-ID")
            audit_ids.add(event.event_id)
            if not event.action.strip():
                raise ProjectValidationError(
                    f"Auditevent {event.event_id} mist een actie"
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-ready project snapshot.

        ``dataclasses.asdict(self)`` recursively copied every entity collection
        and the former implementation then serialised those same collections a
        second time to add ``entity_type``.  Large IFC projects therefore paid
        the full cost twice and could show pathological memory/GC behaviour on
        reopening.  Serialising the known top-level fields explicitly is both
        deterministic and linear in the project size.
        """

        entity_collection_names = set(ENTITY_COLLECTIONS.values())
        data: dict[str, Any] = {}
        for field_info in fields(self):
            name = field_info.name
            if name in entity_collection_names:
                continue
            value = getattr(self, name)
            if name == "sources":
                data[name] = {
                    source_id: asdict(source)
                    for source_id, source in value.items()
                }
            elif name == "validation_issues":
                data[name] = [asdict(item) for item in value]
            elif name == "audit_log":
                data[name] = [asdict(item) for item in value]
            else:
                data[name] = copy.deepcopy(value)

        for _entity_type, collection_name in ENTITY_COLLECTIONS.items():
            data[collection_name] = {
                entity_id: entity.base_to_dict()
                for entity_id, entity in getattr(self, collection_name).items()
            }
        return data

    def to_json_bytes(self) -> bytes:
        return stable_json_bytes(self.to_dict())

    def semantic_sha256(self) -> str:
        return stable_sha256(self.to_dict())

    def content_sha256(self) -> str:
        """Stable hash of user/project content, excluding save bookkeeping.

        This fingerprint drives the revision list.  Audit rows, previous
        revision rows, the current application version and ``modified_at`` are
        excluded so that a no-op save does not create a new revision.
        """

        payload = self.to_dict()
        for key in ("app_version", "modified_at", "audit_log", "revisions"):
            payload.pop(key, None)
        return stable_sha256(payload)

    def revision_content_sha256(self) -> str:
        """Hash user/project content while excluding storage and audit noise.

        The full semantic hash deliberately changes when the audit log or save
        metadata changes.  Revision detection must not create a new revision
        merely because a package was moved, embedded sources were extracted or
        a save timestamp was written.  This fingerprint therefore excludes
        those volatile fields while retaining all production-relevant model
        data, validation state and source analysis results.
        """

        payload = self.to_dict()
        for key in ("app_version", "modified_at", "audit_log", "revisions"):
            payload.pop(key, None)
        for source in dict(payload.get("sources") or {}).values():
            if isinstance(source, dict):
                source.pop("original_path", None)
                source.pop("embedded_path", None)
        return stable_sha256(payload)

    def manufacturing_state_sha256(self) -> str:
        payload = {
            "project_id": self.project_id,
            "parts": {
                entity_id: {
                    "manufacturing_hash": part.manufacturing_hash,
                    "quantity_total": part.quantity_total,
                    "assembly_ids": sorted(part.assembly_ids),
                }
                for entity_id, part in sorted(self.parts.items())
            },
            "assemblies": {
                entity_id: {
                    "mark": assembly.assembly_mark,
                    "quantity": assembly.quantity,
                    "part_ids": sorted(assembly.part_ids),
                    "fastener_ids": sorted(assembly.fastener_ids),
                    "weld_ids": sorted(assembly.weld_ids),
                }
                for entity_id, assembly in sorted(self.assemblies.items())
            },
        }
        return stable_sha256(payload)

    def summary(self, *, include_expensive_hashes: bool = True) -> dict[str, Any]:
        """Return project KPIs and release-gate state.

        A verified package may contain thousands of entities.  GUI list refresh
        and ``project-info`` can reuse the immutable hashes that
        :class:`ProjectStore` verified while opening the package.  Callers that
        need a fresh audit fingerprint keep the default and recompute all three
        content hashes from one project snapshot.
        """

        if include_expensive_hashes:
            hashes = project_hash_bundle_from_snapshot(self.to_dict())
            semantic_hash = hashes["semantic_sha256"]
            content_hash = hashes["content_sha256"]
            revision_hash = hashes["revision_content_sha256"]
        else:
            semantic_hash = str(getattr(self, "_verified_semantic_sha256", ""))
            content_hash = str(getattr(self, "_verified_content_sha256", ""))
            revision_hash = str(getattr(self, "_verified_revision_content_sha256", ""))
        return {
            "schema_version": self.schema_version,
            "app_version": self.app_version,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "description": self.description,
            "customer": self.customer,
            "order_number": self.order_number,
            "project_phase": self.project_phase,
            "status": self.status,
            "source_count": len(self.sources),
            "entity_counts": self.entity_counts(),
            "blocking_issue_count": len(self.blocking_issues()),
            "content_sha256": content_hash,
            "semantic_sha256": semantic_hash,
            "revision_content_sha256": revision_hash,
            "manufacturing_state_sha256": (
                str(getattr(self, "_verified_manufacturing_state_sha256", ""))
                or self.manufacturing_state_sha256()
            ),
            "production_gate": self.production_gate(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectModel":
        if not isinstance(data, dict):
            raise ProjectValidationError("Project Model is geen JSON-object")
        migrated = migrate_project_dict(data)
        version = str(migrated.get("schema_version", ""))
        if version != PROJECT_SCHEMA_VERSION:
            raise ProjectValidationError(
                f"Niet-ondersteund Project Model-schema {version!r}; verwacht {PROJECT_SCHEMA_VERSION}"
            )
        raw = dict(migrated)
        raw["sources"] = {
            str(key): SourceFileRecord.from_dict(value)
            for key, value in dict(raw.get("sources") or {}).items()
        }
        raw["validation_issues"] = [
            ValidationIssue.from_dict(item) for item in list(raw.get("validation_issues") or [])
        ]
        raw["audit_log"] = [
            AuditEvent.from_dict(item) for item in list(raw.get("audit_log") or [])
        ]
        for entity_type, collection_name in ENTITY_COLLECTIONS.items():
            raw[collection_name] = {
                str(key): _entity_from_dict(
                    str(value.get("entity_type") or entity_type),
                    dict(value),
                )
                for key, value in dict(raw.get(collection_name) or {}).items()
            }
        allowed = {item.name for item in fields(cls)}
        project = cls(**{key: raw[key] for key in allowed if key in raw})
        project.validate()
        return project

    @classmethod
    def from_json_bytes(cls, data: bytes) -> "ProjectModel":
        try:
            raw = json.loads(data.decode("utf-8"))
        except Exception as exc:
            raise ProjectValidationError("Project JSON kan niet worden gelezen") from exc
        return cls.from_dict(raw)


def migrate_project_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate known historical project representations to the current schema.

    Version 1.0 was never released as a package, but early development fixtures
    used ``canonical_parts``. Supporting that shape makes the first public
    project schema safe for existing canonical payloads and future migration
    tests.
    """

    raw = json.loads(json.dumps(data))
    version = str(raw.get("schema_version", ""))
    if not version and "canonical_parts" in raw:
        version = "1.0"
        raw["schema_version"] = version
    current = _version_tuple(PROJECT_SCHEMA_VERSION)
    parsed = _version_tuple(version)
    if parsed and current and parsed > current:
        return raw
    if version == PROJECT_SCHEMA_VERSION:
        return raw
    if version in {"2.0", "2.1", "2.2", "2.3", "2.4"} and PROJECT_SCHEMA_VERSION == "2.5":
        raw["schema_version"] = PROJECT_SCHEMA_VERSION
        migration_timestamp = utc_now_iso()
        for part in dict(raw.get("parts") or {}).values():
            if isinstance(part, dict):
                part.setdefault("workbench", {})
                state = part.get("workbench")
                if isinstance(state, dict) and state:
                    state["schema_version"] = "1.1"

                    def invalidate_revision(revision: Any) -> None:
                        if not isinstance(revision, dict):
                            return
                        roundtrip = revision.get("roundtrip_validation")
                        if not isinstance(roundtrip, dict):
                            return
                        if roundtrip.get("status") in {None, "", "not_run", "invalidated"}:
                            return
                        roundtrip["status"] = "invalidated"
                        roundtrip["invalidated_at"] = migration_timestamp
                        roundtrip["invalidated_reason"] = "workbench_hash_contract_upgraded"
                        for result in dict(roundtrip.get("formats") or {}).values():
                            if isinstance(result, dict):
                                result["status"] = "invalidated"
                        roundtrip.pop("report_sha256", None)
                        roundtrip["report_sha256"] = stable_sha256(roundtrip)

                    invalidate_revision(state.get("current_revision"))
                    for command in list(state.get("commands") or []):
                        if not isinstance(command, dict):
                            continue
                        invalidate_revision(command.get("before_revision"))
                        invalidate_revision(command.get("after_revision"))
                        command["before_sha256"] = stable_sha256(
                            dict(command.get("before_revision") or {})
                        )
                        command["after_sha256"] = stable_sha256(
                            dict(command.get("after_revision") or {})
                        )
                    for record in list(state.get("revision_history") or []):
                        if not isinstance(record, dict):
                            continue
                        invalidate_revision(record.get("snapshot"))
                        record["snapshot_sha256"] = stable_sha256(
                            dict(record.get("snapshot") or {})
                        )
                    for artifact in dict(state.get("artifacts") or {}).values():
                        if isinstance(artifact, dict):
                            artifact["status"] = "invalidated"
                            artifact["invalidated_at"] = migration_timestamp
                            artifact["invalidated_reason"] = "workbench_hash_contract_upgraded"
                    rebuild = state.get("canonical_rebuild")
                    if isinstance(rebuild, dict) and rebuild:
                        rebuild["status"] = "invalidated"
                        rebuild["invalidated_at"] = migration_timestamp
                        rebuild["invalidated_reason"] = "workbench_hash_contract_upgraded"
                    part["geometry_hash"] = ""
                    part["manufacturing_hash"] = ""
                    part["production_identity_hash"] = ""
                    part["bom_group_key"] = ""
                    part["nc1_eligible"] = False
                    part["export_status"] = "blocked_pending_roundtrip_validation"
        history = list(raw.get("migration_history") or [])
        history.append(
            {
                "from": version,
                "to": PROJECT_SCHEMA_VERSION,
                "timestamp": migration_timestamp,
                "reason": (
                    "Part Workbench 1.1 met herkenningshash en gebonden roundtripvalidatie toegevoegd."
                ),
            }
        )
        raw["migration_history"] = history
        return raw
    if _major(version) != "1":
        return raw

    canonical_parts = list(raw.get("canonical_parts") or [])
    project = ProjectModel.new(
        str(raw.get("project_name") or "Gemigreerd project"),
        customer=str(raw.get("customer") or ""),
        order_number=str(raw.get("order_number") or ""),
        created_by="migration",
    )
    legacy_project_id = str(raw.get("project_id") or "")
    try:
        UUID(legacy_project_id)
        project.project_id = legacy_project_id
    except ValueError:
        pass
    for part_data in canonical_parts:
        project.add_canonical_part(CanonicalPart.from_dict(dict(part_data)), user="migration")
    project.migration_history.append(
        {
            "from": version,
            "to": PROJECT_SCHEMA_VERSION,
            "timestamp": utc_now_iso(),
            "legacy_part_count": len(canonical_parts),
        }
    )
    project.audit("project.schema_migrated", user="migration", details={"from": version})
    return project.to_dict()


__all__ = [
    "PROJECT_SCHEMA_VERSION",
    "HASH_ALGORITHM_VERSION",
    "MANUFACTURING_HASH_VERSION",
    "ProjectValidationError",
    "ImportStrategy",
    "EntityCategory",
    "ReviewStatus",
    "Transform3D",
    "SourceIdentity",
    "FieldProvenance",
    "ValidationIssue",
    "AuditEvent",
    "SourceFileRecord",
    "ProjectEntity",
    "Assembly",
    "Part",
    "PurchasedItem",
    "Fastener",
    "Weld",
    "StockItem",
    "Remnant",
    "ProductionOperation",
    "MachineProfile",
    "MachineJob",
    "ProjectModel",
    "stable_sha256",
    "stable_json_bytes",
    "migrate_project_dict",
]
