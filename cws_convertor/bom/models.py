"""Versioned bill-of-materials snapshot models."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
from cws_convertor.project.model import stable_sha256, utc_now_iso

BOM_SCHEMA_VERSION = "1.2"

class DictMixin:
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class PartBOMRow(DictMixin):
    group_id: str
    status: str
    category: str
    part_position: str
    name: str
    profile: str
    material: str
    length_mm: float
    quantity: int
    mass_each_kg: float
    total_mass_kg: float
    surface_area_each_m2: float
    total_surface_area_m2: float
    assembly_marks: list[str]
    mirrored: bool
    nc1_eligible: bool
    classification_confidence: float
    profile_confidence: float
    material_confidence: float
    blocked: bool
    blocking_reasons: list[str]
    warnings: list[str]
    geometry_hash: str
    manufacturing_hash: str
    production_identity_hash: str
    source_entity_ids: list[str]
    part_ids: list[str]

@dataclass
class AssemblyBOMRow(DictMixin):
    group_id: str
    assembly_mark: str
    name: str
    quantity: int
    part_occurrences: int
    unique_part_groups: int
    purchased_occurrences: int
    fastener_count: int
    weld_count: int
    weight_each_kg: float
    total_weight_kg: float
    surface_area_each_m2: float
    total_surface_area_m2: float
    blocked: bool
    blocking_reasons: list[str]
    composition_hashes: list[str]
    assembly_ids: list[str]
    part_ids: list[str] = field(default_factory=list)
    purchased_item_ids: list[str] = field(default_factory=list)
    fastener_ids: list[str] = field(default_factory=list)
    weld_ids: list[str] = field(default_factory=list)
    child_assembly_ids: list[str] = field(default_factory=list)

@dataclass
class PurchaseBOMRow(DictMixin):
    group_id: str
    article_number: str
    description: str
    profile_or_size: str
    material_or_grade: str
    length_mm: float
    quantity: float
    unit: str
    supplier: str
    manufacturer: str
    standard: str
    unit_price: float
    total_price: float
    lead_time_days: int
    assembly_marks: list[str]
    blocked: bool
    blocking_reasons: list[str]
    warnings: list[str]
    source_entity_ids: list[str]
    part_ids: list[str]
    purchased_item_ids: list[str] = field(default_factory=list)

@dataclass
class FastenerBOMRow(DictMixin):
    group_id: str
    fastener_type: str
    diameter_mm: float
    grade: str
    length_mm: float
    standard: str
    hole_diameter_mm: float
    quantity: int
    assembly_marks: list[str]
    blocked: bool
    blocking_reasons: list[str]
    source_entity_ids: list[str]
    fastener_ids: list[str]

@dataclass
class WeldBOMRow(DictMixin):
    group_id: str
    weld_type: str
    size_mm: float
    length_mm: float
    process: str
    side: str
    location: str
    quantity: int
    total_length_mm: float
    total_time_minutes: float
    total_cost: float
    assembly_marks: list[str]
    blocked: bool
    blocking_reasons: list[str]
    source_entity_ids: list[str]
    weld_ids: list[str]

@dataclass
class MaterialBOMRow(DictMixin):
    group_id: str
    category: str
    material: str
    profile: str
    quantity: int
    net_length_mm: float
    total_mass_kg: float
    total_surface_area_m2: float
    part_group_count: int
    blocked: bool
    blocking_reasons: list[str]

@dataclass
class BOMConflict(DictMixin):
    conflict_id: str
    conflict_type: str
    severity: str
    blocking: bool
    key: str
    message: str
    entity_ids: list[str] = field(default_factory=list)
    group_ids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

@dataclass
class BOMValidation(DictMixin):
    passed: bool
    production_ready: bool
    checks: dict[str, bool]
    blocking_conflict_count: int
    warning_conflict_count: int
    traceability_coverage: float
    messages: list[str] = field(default_factory=list)

@dataclass
class BOMSnapshot:
    project_id: str
    project_name: str
    generated_at: str = field(default_factory=utc_now_iso)
    schema_version: str = BOM_SCHEMA_VERSION
    classification_report_sha256: str = ""
    part_bom: list[PartBOMRow] = field(default_factory=list)
    assembly_bom: list[AssemblyBOMRow] = field(default_factory=list)
    purchase_bom: list[PurchaseBOMRow] = field(default_factory=list)
    fastener_bom: list[FastenerBOMRow] = field(default_factory=list)
    weld_bom: list[WeldBOMRow] = field(default_factory=list)
    material_bom: list[MaterialBOMRow] = field(default_factory=list)
    conflicts: list[BOMConflict] = field(default_factory=list)
    traceability: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    validation: BOMValidation | None = None
    snapshot_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "generated_at": self.generated_at,
            "schema_version": self.schema_version,
            "classification_report_sha256": self.classification_report_sha256,
            "part_bom": [row.to_dict() for row in self.part_bom],
            "assembly_bom": [row.to_dict() for row in self.assembly_bom],
            "purchase_bom": [row.to_dict() for row in self.purchase_bom],
            "fastener_bom": [row.to_dict() for row in self.fastener_bom],
            "weld_bom": [row.to_dict() for row in self.weld_bom],
            "material_bom": [row.to_dict() for row in self.material_bom],
            "conflicts": [row.to_dict() for row in self.conflicts],
            "traceability": list(self.traceability),
            "summary": dict(self.summary),
            "validation": self.validation.to_dict() if self.validation else None,
            "snapshot_sha256": self.snapshot_sha256,
        }

    def refresh_hash(self) -> str:
        data = self.to_dict()
        data.pop("generated_at", None)
        data["snapshot_sha256"] = ""
        summary = dict(data.get("summary") or {})
        summary.pop("generated_at", None)
        data["summary"] = summary
        self.snapshot_sha256 = stable_sha256(data)
        return self.snapshot_sha256
