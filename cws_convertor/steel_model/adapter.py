"""Compatibility adapter from persisted Project Model 2.5 to SteelModel 1.0."""
from __future__ import annotations

from typing import Any, Iterable

from cws_convertor.product import APP_NAME, LEGACY_APP_NAME
from cws_convertor.project.model import (
    Assembly,
    Fastener,
    MachineJob,
    Part,
    ProductionOperation,
    ProjectEntity,
    ProjectModel,
    PurchasedItem,
    Remnant,
    Weld,
)
from .contracts import (
    AccuracyStatus,
    SteelEntityRecord,
    SteelModelSnapshot,
    SteelRelationRecord,
    SteelSourceRecord,
    SteelSourceTrace,
    SteelValidationRecord,
)
from .tolerances import DEFAULT_TOLERANCE_POLICY, TolerancePolicy


def _part_accuracy(part: Part) -> tuple[AccuracyStatus, str]:
    descriptor = dict(part.geometry_descriptor or {})
    inspection = descriptor.get("source_inspection")
    if isinstance(inspection, dict):
        kind = str(inspection.get("geometry_kind") or "unknown")
        if bool(inspection.get("selection_verified")) and bool(
            inspection.get("production_geometry_exact")
        ):
            return AccuracyStatus.EXACT, kind
        if bool(inspection.get("selection_verified")):
            return AccuracyStatus.APPROXIMATE, kind
        return AccuracyStatus.MANUAL_VALIDATION_REQUIRED, kind
    if part.canonical_part and part.geometry_hash:
        return AccuracyStatus.TOLERANCE_VERIFIED, "canonical_part"
    kind = str(descriptor.get("kind") or descriptor.get("geometry_kind") or "unknown")
    return AccuracyStatus.MANUAL_VALIDATION_REQUIRED, kind


def _display_properties(entity: ProjectEntity) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": entity.name,
        "entity_type": entity.entity_type,
        "category": entity.category,
        "status": entity.status,
        "revision": entity.revision,
        "confidence": entity.confidence,
    }
    result.update(dict(entity.properties or {}))
    if isinstance(entity, Assembly):
        result.update(
            assembly_mark=entity.assembly_mark,
            quantity=entity.quantity,
            total_weight_kg=entity.total_weight_kg,
            surface_area_m2=entity.surface_area_m2,
            production_status=entity.production_status,
            drawing_status=entity.drawing_status,
        )
    elif isinstance(entity, Part):
        result.update(
            part_position=entity.part_position,
            quantity_total=entity.quantity_total,
            part_type=entity.part_type,
            profile=entity.profile,
            profile_type=entity.profile_type,
            material=entity.material,
            material_grade=entity.material_grade,
            length_mm=entity.length_mm,
            mass_each_kg=entity.mass_each_kg,
            surface_area_each_m2=entity.surface_area_each_m2,
            mirrored=entity.mirrored,
            export_status=entity.export_status,
            nc1_eligible=entity.nc1_eligible,
        )
    elif isinstance(entity, PurchasedItem):
        result.update(
            article_number=entity.article_number,
            supplier=entity.supplier,
            material=entity.material,
            grade=entity.grade,
            quantity=entity.quantity,
            unit=entity.unit,
            purchase_status=entity.purchase_status,
        )
    elif isinstance(entity, Fastener):
        result.update(
            fastener_type=entity.fastener_type,
            diameter_mm=entity.diameter_mm,
            length_mm=entity.length_mm,
            grade=entity.grade,
            quantity=entity.quantity,
        )
    elif isinstance(entity, Weld):
        result.update(
            weld_type=entity.weld_type,
            size_mm=entity.size_mm,
            length_mm=entity.length_mm,
            process=entity.process,
            location=entity.location,
        )
    return result


def _source_trace(project: ProjectModel, entity: ProjectEntity) -> SteelSourceTrace:
    identity = entity.source_identity
    source = project.sources.get(identity.source_file_id) if identity.source_file_id else None
    return SteelSourceTrace(
        source_file_id=identity.source_file_id,
        source_format=identity.source_format or (source.source_format if source else ""),
        source_sha256=identity.source_sha256 or (source.sha256 if source else ""),
        source_entity_id=identity.source_entity_id,
        global_id=identity.global_id,
        product_id=identity.product_id,
        occurrence_id=identity.occurrence_id,
    )


def _entity_record(project: ProjectModel, entity: ProjectEntity) -> SteelEntityRecord:
    accuracy = AccuracyStatus.NOT_APPLICABLE
    geometry_kind = "none"
    geometry_hash = ""
    manufacturing_hash = ""
    if isinstance(entity, Part):
        accuracy, geometry_kind = _part_accuracy(entity)
        geometry_hash = entity.geometry_hash
        manufacturing_hash = entity.manufacturing_hash
    return SteelEntityRecord(
        steel_model_id=entity.internal_id,
        entity_type=entity.entity_type,
        name=entity.name,
        category=entity.category,
        status=entity.status,
        source=_source_trace(project, entity),
        local_transform=tuple(entity.local_placement.flat()),
        global_transform=tuple(entity.global_placement.flat()),
        accuracy_status=accuracy,
        geometry_kind=geometry_kind,
        geometry_hash=geometry_hash,
        manufacturing_hash=manufacturing_hash,
        validation_issue_codes=tuple(
            issue.code for issue in entity.validation_issues if not issue.resolved
        ),
        display_properties=_display_properties(entity),
    )


def _relation_values(project: ProjectModel) -> Iterable[SteelRelationRecord]:
    for assembly in project.assemblies.values():
        for target in assembly.child_assembly_ids:
            yield SteelRelationRecord("assembly.child", assembly.internal_id, target)
        for target in assembly.part_ids:
            yield SteelRelationRecord("assembly.part", assembly.internal_id, target)
        for target in assembly.purchased_item_ids:
            yield SteelRelationRecord("assembly.purchased_item", assembly.internal_id, target)
        for target in assembly.fastener_ids:
            yield SteelRelationRecord("assembly.fastener", assembly.internal_id, target)
        for target in assembly.weld_ids:
            yield SteelRelationRecord("assembly.weld", assembly.internal_id, target)
    for fastener in project.fasteners.values():
        for target in fastener.connected_part_ids:
            yield SteelRelationRecord("fastener.connected_part", fastener.internal_id, target)
    for weld in project.welds.values():
        for target in weld.connected_part_ids:
            yield SteelRelationRecord("weld.connected_part", weld.internal_id, target)
    for remnant in project.remnants.values():
        if remnant.stock_item_id:
            yield SteelRelationRecord("remnant.stock_item", remnant.internal_id, remnant.stock_item_id)
    for operation in project.production_operations.values():
        for target in operation.part_ids:
            yield SteelRelationRecord("production_operation.part", operation.internal_id, target)
    for job in project.machine_jobs.values():
        for target in job.part_ids:
            yield SteelRelationRecord("machine_job.part", job.internal_id, target)
        for target in job.operation_ids:
            yield SteelRelationRecord("machine_job.operation", job.internal_id, target)


def _validation_records(project: ProjectModel) -> tuple[SteelValidationRecord, ...]:
    values: list[SteelValidationRecord] = []
    for issue in project.validation_issues:
        values.append(
            SteelValidationRecord(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
                blocking=issue.blocking,
                steel_model_id=issue.entity_id,
                field_path=issue.field_path,
                resolved=issue.resolved,
            )
        )
    for entity in project.iter_entities():
        for issue in entity.validation_issues:
            values.append(
                SteelValidationRecord(
                    code=issue.code,
                    message=issue.message,
                    severity=issue.severity,
                    blocking=issue.blocking,
                    steel_model_id=entity.internal_id,
                    field_path=issue.field_path,
                    resolved=issue.resolved,
                )
            )
    return tuple(values)


def build_steel_model_snapshot(
    project: ProjectModel,
    *,
    tolerance_policy: TolerancePolicy = DEFAULT_TOLERANCE_POLICY,
) -> SteelModelSnapshot:
    """Build a deterministic read model without mutating the project."""

    project.validate()
    semantic_hash = project.semantic_sha256()
    sources = tuple(
        SteelSourceRecord(
            source_id=source.source_id,
            source_format=source.source_format,
            source_sha256=source.sha256,
            file_name=source.file_name,
            import_strategy=source.import_strategy,
            analysis_status=source.analysis_status,
            semantic_import_complete=source.semantic_import_complete,
            production_export_allowed=source.production_export_allowed,
            schema=source.schema,
            application=source.application,
        )
        for source in project.sources.values()
    )
    snapshot = SteelModelSnapshot(
        project_id=project.project_id,
        project_name=project.project_name,
        project_model_schema=project.schema_version,
        project_semantic_sha256=semantic_hash,
        product_name=APP_NAME,
        compatibility_product_name=LEGACY_APP_NAME,
        units=project.units,
        coordinate_system=project.coordinate_system,
        project_status=project.status,
        sources=sources,
        entities=tuple(_entity_record(project, entity) for entity in project.iter_entities()),
        relations=tuple(_relation_values(project)),
        validation=_validation_records(project),
        tolerance_policy=tolerance_policy,
    )
    if project.semantic_sha256() != semantic_hash:
        raise RuntimeError("SteelModel adapter mutated the Project Model")
    return snapshot


__all__ = ["build_steel_model_snapshot"]
