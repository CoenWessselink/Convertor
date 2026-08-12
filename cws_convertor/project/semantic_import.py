"""Transactional semantic IFC/STEP import boundary.

The baseline scanner records facts only. This module turns verified source
bytes into canonical project entities while preserving the production gate.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from cws_convertor.errors import ErrorCode
from cws_convertor.importers.semantic import (
    SemanticCancelCheck,
    SemanticImportResult,
)
from cws_convertor.project.baseline import sha256_file
from cws_convertor.project.model import (
    Part,
    ProjectModel,
    ProjectValidationError,
    utc_now_iso,
)
from cws_convertor.project.storage import ProjectPackageError


def source_entity_ids(project: ProjectModel, source_id: str) -> set[str]:
    return {
        entity.internal_id
        for entity in project.iter_entities()
        if entity.source_identity.source_file_id == source_id
    }


def purge_source_entities(
    project: ProjectModel,
    source_id: str,
    *,
    user: str = "system",
) -> int:
    """Remove a prior semantic snapshot and every derived source index."""

    removing = source_entity_ids(project, source_id)
    project.remove_entities_for_source(source_id, user=user)
    project.validation_issues = [
        issue
        for issue in project.validation_issues
        if not (
            issue.entity_id == source_id
            and issue.code.startswith(("CWS-SEMANTIC-", "CWS-PROJECT-SOURCE-"))
        )
    ]
    for section_name in (
        "semantic_imports",
        "spatial_trees",
        "product_trees",
        "source_entity_maps",
        "mark_groups",
        "geometry_groups",
        "manufacturing_groups",
    ):
        section = project.settings.get(section_name)
        if isinstance(section, dict):
            section.pop(source_id, None)

    source = project.sources.get(source_id)
    if source is not None:
        for key in (
            "semantic_import_version",
            "semantic_importer_version",
            "semantic_imported_at",
            "semantic_entity_counts",
            "semantic_source_class_counts",
            "semantic_relationship_counts",
            "semantic_import_strategy",
            "semantic_import_elapsed_seconds",
            "semantic_blocking_reasons",
        ):
            source.metadata.pop(key, None)
        source.analysis.pop("semantic_import", None)
        source.semantic_import_complete = False
        source.production_export_allowed = False

    return len(removing)


def _rebuild_semantic_indexes(project: ProjectModel, source_id: str) -> None:
    entities = [
        entity
        for entity in project.iter_entities()
        if entity.source_identity.source_file_id == source_id
    ]
    source_map: dict[str, str] = {}
    assembly_marks: dict[str, list[str]] = defaultdict(list)
    part_positions: dict[str, list[str]] = defaultdict(list)
    geometry_groups: dict[str, list[str]] = defaultdict(list)
    manufacturing_groups: dict[str, list[str]] = defaultdict(list)

    for entity in entities:
        source_entity_id = entity.source_identity.source_entity_id
        if source_entity_id:
            source_map[source_entity_id] = entity.internal_id
        if entity.entity_type == "assembly":
            mark = getattr(entity, "assembly_mark", "")
            if mark:
                assembly_marks[mark].append(entity.internal_id)
        if isinstance(entity, Part):
            if entity.part_position:
                part_positions[entity.part_position].append(entity.internal_id)
            if entity.geometry_hash:
                geometry_groups[entity.geometry_hash].append(entity.internal_id)
            if entity.manufacturing_hash:
                manufacturing_groups[entity.manufacturing_hash].append(entity.internal_id)

    project.settings.setdefault("source_entity_maps", {})[source_id] = dict(sorted(source_map.items()))
    project.settings.setdefault("mark_groups", {})[source_id] = {
        "assembly_marks": {key: sorted(value) for key, value in sorted(assembly_marks.items())},
        "part_positions": {key: sorted(value) for key, value in sorted(part_positions.items())},
    }
    project.settings.setdefault("geometry_groups", {})[source_id] = {
        key: sorted(value) for key, value in sorted(geometry_groups.items())
    }
    project.settings.setdefault("manufacturing_groups", {})[source_id] = {
        key: sorted(value) for key, value in sorted(manufacturing_groups.items())
    }

    semantic_materials: dict[str, dict] = {}
    for part in project.parts.values():
        material = (part.material or part.material_grade).strip()
        if not material:
            continue
        entry = semantic_materials.setdefault(
            material,
            {"part_count": 0, "source_ids": set(), "grades": set()},
        )
        entry["part_count"] += 1
        if part.source_identity.source_file_id:
            entry["source_ids"].add(part.source_identity.source_file_id)
        if part.material_grade:
            entry["grades"].add(part.material_grade)
    for material, facts in semantic_materials.items():
        existing = dict(project.materials.get(material) or {})
        existing.update(
            {
                "code": material,
                "semantic_part_count": facts["part_count"],
                "semantic_source_ids": sorted(facts["source_ids"]),
                "semantic_grades": sorted(facts["grades"]),
            }
        )
        project.materials[material] = existing
    active_materials = set(semantic_materials)
    for material, entry in list(project.materials.items()):
        if "semantic_part_count" in entry and material not in active_materials:
            entry["semantic_part_count"] = 0
            entry["semantic_source_ids"] = []
            entry["semantic_grades"] = []


def semantic_import_source(
    project: ProjectModel,
    source_id: str,
    source_path: str | Path,
    *,
    user: str = "system",
    progress_callback: Callable[[float, str], None] | None = None,
    cancel_check: SemanticCancelCheck | None = None,
) -> SemanticImportResult:
    if cancel_check is not None:
        cancel_check()
    source = project.sources.get(source_id)
    if source is None:
        raise ProjectValidationError(f"Onbekende projectbron {source_id}")
    path = Path(source_path).expanduser().resolve()
    if not path.is_file():
        raise ProjectPackageError(
            f"Bronbestand voor semantische import ontbreekt: {path}",
            code=ErrorCode.INVALID_INPUT,
        )
    actual_sha = sha256_file(path)
    if cancel_check is not None:
        cancel_check()
    if actual_sha != source.sha256:
        raise ProjectPackageError(
            f"Bronbytes van {source.file_name} zijn gewijzigd sinds registratie",
            code=ErrorCode.PROJECT_INVALID,
            details={"expected": source.sha256, "actual": actual_sha},
        )

    purge_source_entities(project, source_id, user=user)
    suffix = path.suffix.lower()
    if suffix == ".ifc" or source.source_format.upper() == "IFC":
        from cws_convertor.importers.ifc_project import IFCSemanticProjectImporter
        importer = IFCSemanticProjectImporter()
    elif suffix in {".step", ".stp"} or source.source_format.upper() in {"STEP", "STP"}:
        from cws_convertor.importers.step_project import STEPSemanticProjectImporter
        importer = STEPSemanticProjectImporter()
    else:
        raise ProjectPackageError(
            f"Semantische projectimport ondersteunt geen {path.suffix or source.source_format}",
            code=ErrorCode.UNSUPPORTED_FORMAT,
        )

    result = importer.import_source(
        project,
        source,
        path,
        user=user,
        progress=progress_callback,
        cancel_check=cancel_check,
    )
    result.normalise()
    source.schema = result.schema or source.schema
    source.import_strategy = result.strategy or source.import_strategy
    source.analysis_status = "imported" if result.production_export_allowed else "review_required"
    source.warnings = list(dict.fromkeys([*source.warnings, *result.warnings]))
    source.analysis["semantic_import"] = result.to_dict()
    source.metadata.update(
        {
            "semantic_import_version": result.importer_version,
            "semantic_importer_version": result.importer_version,
            "semantic_imported_at": utc_now_iso(),
            "semantic_entity_counts": dict(result.entity_counts),
            "semantic_source_class_counts": dict(result.source_class_counts),
            "semantic_relationship_counts": dict(result.relationship_counts),
            "semantic_import_strategy": result.strategy,
            "semantic_import_elapsed_seconds": result.elapsed_seconds,
            "semantic_blocking_reasons": list(result.blocking_reasons),
            "semantic_import_pending": False,
        }
    )
    project.settings.setdefault("semantic_imports", {})[source_id] = result.to_dict()
    _rebuild_semantic_indexes(project, source_id)
    project.mark_source_semantic_import_complete(
        source_id,
        production_export_allowed=result.production_export_allowed,
        user=user,
    )
    project.audit(
        "source.semantic_import",
        user=user,
        entity_id=source_id,
        details={
            "file_name": source.file_name,
            "format": source.source_format,
            "strategy": result.strategy,
            "importer_version": result.importer_version,
            "entity_counts": result.entity_counts,
            "production_export_allowed": result.production_export_allowed,
        },
    )
    project.validate()
    return result


__all__ = ["purge_source_entities", "semantic_import_source", "source_entity_ids"]
