"""Deterministic BOM, procurement and traceability aggregation."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from cws_convertor.project.classification import (
    ClassificationReport,
    classify_project,
)
from cws_convertor.project.model import (
    EntityCategory,
    ProjectModel,
    stable_sha256,
    utc_now_iso,
)
from .models import (
    AssemblyBOMRow,
    BOMConflict,
    BOMSnapshot,
    BOMValidation,
    FastenerBOMRow,
    MaterialBOMRow,
    PartBOMRow,
    PurchaseBOMRow,
    WeldBOMRow,
)


def _round(value: Any, digits: int = 6) -> float:
    try:
        return round(float(value or 0.0), digits)
    except (TypeError, ValueError):
        return 0.0


def _part_marks(project: ProjectModel, part) -> list[str]:
    marks = {
        project.assemblies[aid].assembly_mark
        for aid in part.assembly_ids
        if aid in project.assemblies and project.assemblies[aid].assembly_mark
    }
    if part.source_identity.assembly_mark:
        marks.add(part.source_identity.assembly_mark)
    return sorted(marks)


def _blocking_reasons(entity) -> list[str]:
    return sorted({issue.message for issue in entity.blocking_issues()})


def _source_entity_ids(entities: Iterable[Any]) -> list[str]:
    return sorted({
        item.source_identity.source_entity_id
        for item in entities
        if item.source_identity.source_entity_id
    })


def _group_parts(project: ProjectModel):
    groups: dict[str, list[Any]] = defaultdict(list)
    for part in project.parts.values():
        if part.category == EntityCategory.PURCHASED_ITEM.value:
            continue
        key = part.production_identity_hash or part.manufacturing_hash or part.internal_id
        groups[key].append(part)
    return groups


def _build_part_rows(project: ProjectModel):
    rows: list[PartBOMRow] = []
    part_to_group: dict[str, str] = {}
    mark_conflicts = {
        conflict.key
        for conflict in _classification_conflicts(project)
        if conflict.conflict_type == "same_mark_different_manufacturing"
    }
    for key, group in sorted(_group_parts(project).items()):
        exemplar = sorted(group, key=lambda p: p.internal_id)[0]
        quantity = sum(max(1, int(p.quantity_total or 1)) for p in group)
        masses = [float(p.mass_each_kg or 0.0) for p in group]
        surfaces = [float(p.surface_area_each_m2 or 0.0) for p in group]
        total_mass = sum(float(p.mass_each_kg or 0.0) * max(1, int(p.quantity_total or 1)) for p in group)
        total_surface = sum(float(p.surface_area_each_m2 or 0.0) * max(1, int(p.quantity_total or 1)) for p in group)
        marks = sorted({mark for p in group for mark in _part_marks(project, p)})
        positions = sorted({p.part_position for p in group if p.part_position})
        reasons = sorted({reason for p in group for reason in _blocking_reasons(p)})
        if any(position in mark_conflicts for position in positions):
            reasons.append("Dezelfde part position verwijst naar verschillende productie-identiteiten")
        warnings: list[str] = []
        if len(positions) > 1:
            warnings.append("Gelijke productie-identiteit komt onder meerdere part positions voor")
        if len({p.normalized_material for p in group}) > 1:
            reasons.append("Materiaalconflict binnen productie-identiteit")
        if len({(p.normalized_profile or p.profile).strip().upper() for p in group}) > 1:
            reasons.append("Profielconflict binnen productie-identiteit")
        if len({_round(p.length_mm) for p in group}) > 1:
            reasons.append("Lengteconflict binnen productie-identiteit")
        if len({_round(p.mass_each_kg) for p in group}) > 1:
            reasons.append("Massa per stuk verschilt binnen productie-identiteit")
        if len({_round(p.surface_area_each_m2, 9) for p in group}) > 1:
            reasons.append("Oppervlakte per stuk verschilt binnen productie-identiteit")
        group_id = f"PART-{key[:16]}"
        row = PartBOMRow(
            group_id=group_id,
            status="blocked" if reasons else "ready",
            category=exemplar.category,
            part_position=", ".join(positions),
            name=exemplar.name,
            profile=exemplar.normalized_profile or exemplar.profile,
            material=exemplar.normalized_material or exemplar.material_grade or exemplar.material,
            length_mm=_round(exemplar.length_mm),
            quantity=quantity,
            mass_each_kg=_round(sum(masses) / len(masses) if masses else 0.0),
            total_mass_kg=_round(total_mass),
            surface_area_each_m2=_round(sum(surfaces) / len(surfaces) if surfaces else 0.0, 9),
            total_surface_area_m2=_round(total_surface, 9),
            assembly_marks=marks,
            mirrored=bool(exemplar.mirrored),
            nc1_eligible=all(bool(p.nc1_eligible) for p in group),
            classification_confidence=min(float(p.classification_confidence) for p in group),
            profile_confidence=min(float(p.profile_confidence) for p in group),
            material_confidence=min(float(p.material_confidence) for p in group),
            blocked=bool(reasons),
            blocking_reasons=list(dict.fromkeys(reasons)),
            warnings=warnings,
            geometry_hash=exemplar.geometry_hash,
            manufacturing_hash=exemplar.manufacturing_hash,
            production_identity_hash=key,
            source_entity_ids=_source_entity_ids(group),
            part_ids=sorted(p.internal_id for p in group),
        )
        rows.append(row)
        for part in group:
            part_to_group[part.internal_id] = group_id
    return rows, part_to_group


def _classification_conflicts(project: ProjectModel):
    from cws_convertor.project.classification import detect_identity_conflicts
    return detect_identity_conflicts(project.parts.values())


def _build_purchase_rows(project: ProjectModel):
    groups: dict[tuple[Any, ...], list[tuple[str, Any]]] = defaultdict(list)
    for part in project.parts.values():
        if part.category != EntityCategory.PURCHASED_ITEM.value:
            continue
        key = (
            (part.part_position or part.source_identity.part_position).strip().upper(),
            part.name.strip().upper(),
            (part.normalized_profile or part.profile).strip().upper(),
            (part.normalized_material or part.material_grade or part.material).strip().upper(),
            _round(part.length_mm),
            "PIECE",
            "",
            "",
            "",
            0.0,
            0,
        )
        groups[key].append(("part", part))
    for item in project.purchased_items.values():
        dimensions = dict(item.dimensions or {})
        profile_or_size = str(
            dimensions.get("profile")
            or dimensions.get("size")
            or dimensions.get("description")
            or ""
        )
        length_mm = _round(dimensions.get("length_mm") or dimensions.get("length") or 0.0)
        material_or_grade = item.grade or item.material
        key = (
            item.article_number.strip().upper(),
            (item.description or item.name).strip().upper(),
            profile_or_size.strip().upper(),
            material_or_grade.strip().upper(),
            length_mm,
            (item.unit or "piece").strip().upper(),
            item.supplier.strip().upper(),
            item.manufacturer.strip().upper(),
            item.standard.strip().upper(),
            _round(item.unit_price, 2),
            int(item.lead_time_days or 0),
        )
        groups[key].append(("purchased_item", item))
    rows: list[PurchaseBOMRow] = []
    entity_to_group: dict[str, str] = {}
    for key, group in sorted(groups.items(), key=lambda item: str(item[0])):
        kind, exemplar = sorted(group, key=lambda pair: pair[1].internal_id)[0]
        quantity = sum(
            max(1, int(entity.quantity_total or 1))
            if entity_kind == "part"
            else max(0.0, float(entity.quantity or 0.0))
            for entity_kind, entity in group
        )
        group_hash = stable_sha256(["purchase", key])
        group_id = f"BUY-{group_hash[:16]}"
        reasons = sorted({
            reason
            for _entity_kind, entity in group
            for reason in _blocking_reasons(entity)
        })
        warnings: list[str] = []
        if kind == "part":
            article_number = exemplar.part_position or exemplar.source_identity.part_position
            description = exemplar.name or exemplar.profile
            profile_or_size = exemplar.normalized_profile or exemplar.profile
            material_or_grade = exemplar.normalized_material or exemplar.material_grade or exemplar.material
            length_mm = _round(exemplar.length_mm)
            unit = "piece"
            supplier = manufacturer = standard = ""
            unit_price = 0.0
            lead_time_days = 0
        else:
            dimensions = dict(exemplar.dimensions or {})
            article_number = exemplar.article_number
            description = exemplar.description or exemplar.name
            profile_or_size = str(
                dimensions.get("profile")
                or dimensions.get("size")
                or dimensions.get("description")
                or ""
            )
            material_or_grade = exemplar.grade or exemplar.material
            length_mm = _round(dimensions.get("length_mm") or dimensions.get("length") or 0.0)
            unit = exemplar.unit or "piece"
            supplier = exemplar.supplier
            manufacturer = exemplar.manufacturer
            standard = exemplar.standard
            unit_price = _round(exemplar.unit_price, 2)
            lead_time_days = int(exemplar.lead_time_days or 0)
        if not description and not profile_or_size:
            reasons.append("Artikelomschrijving ontbreekt")
        if not article_number:
            warnings.append("Bron-part-position ontbreekt; interne group-ID wordt gebruikt")
        assembly_marks: set[str] = set()
        for entity_kind, entity in group:
            if entity_kind == "part":
                assembly_marks.update(_part_marks(project, entity))
            else:
                assembly_marks.update(
                    project.assemblies[assembly_id].assembly_mark
                    for assembly_id in entity.assembly_ids
                    if assembly_id in project.assemblies
                    and project.assemblies[assembly_id].assembly_mark
                )
                if entity.source_identity.assembly_mark:
                    assembly_marks.add(entity.source_identity.assembly_mark)
        rows.append(PurchaseBOMRow(
            group_id=group_id,
            article_number=article_number,
            description=description,
            profile_or_size=profile_or_size,
            material_or_grade=material_or_grade,
            length_mm=length_mm,
            quantity=float(quantity),
            unit=unit,
            supplier=supplier,
            manufacturer=manufacturer,
            standard=standard,
            unit_price=unit_price,
            total_price=_round(unit_price * quantity, 2),
            lead_time_days=lead_time_days,
            assembly_marks=sorted(assembly_marks),
            blocked=bool(reasons),
            blocking_reasons=list(dict.fromkeys(reasons)),
            warnings=warnings,
            source_entity_ids=_source_entity_ids(entity for _kind, entity in group),
            part_ids=sorted(entity.internal_id for entity_kind, entity in group if entity_kind == "part"),
            purchased_item_ids=sorted(
                entity.internal_id for entity_kind, entity in group if entity_kind == "purchased_item"
            ),
        ))
        for _entity_kind, entity in group:
            entity_to_group[entity.internal_id] = group_id
    return rows, entity_to_group


def _build_fastener_rows(project: ProjectModel):
    groups: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    fastener_marks: dict[str, set[str]] = defaultdict(set)
    for assembly in project.assemblies.values():
        for entity_id in assembly.fastener_ids:
            if assembly.assembly_mark:
                fastener_marks[entity_id].add(assembly.assembly_mark)
    for item in project.fasteners.values():
        key = (
            item.fastener_type.strip().upper(), _round(item.diameter_mm), item.grade.strip().upper(),
            _round(item.length_mm), item.standard.strip().upper(), _round(item.hole_diameter_mm),
        )
        groups[key].append(item)
    rows: list[FastenerBOMRow] = []
    entity_to_group: dict[str, str] = {}
    for key, group in sorted(groups.items(), key=lambda item: str(item[0])):
        exemplar = sorted(group, key=lambda x: x.internal_id)[0]
        group_id = f"FAST-{stable_sha256(['fastener', key])[:16]}"
        reasons = []
        if not exemplar.fastener_type and not exemplar.diameter_mm:
            reasons.append("Bevestigertype en diameter ontbreken")
        rows.append(FastenerBOMRow(
            group_id=group_id,
            fastener_type=exemplar.fastener_type or exemplar.name,
            diameter_mm=_round(exemplar.diameter_mm),
            grade=exemplar.grade,
            length_mm=_round(exemplar.length_mm),
            standard=exemplar.standard,
            hole_diameter_mm=_round(exemplar.hole_diameter_mm),
            quantity=sum(max(1, int(item.quantity or 1)) for item in group),
            assembly_marks=sorted({mark for item in group for mark in fastener_marks[item.internal_id]}),
            blocked=bool(reasons),
            blocking_reasons=reasons,
            source_entity_ids=_source_entity_ids(group),
            fastener_ids=sorted(item.internal_id for item in group),
        ))
        for item in group:
            entity_to_group[item.internal_id] = group_id
    return rows, entity_to_group


def _weld_mark(project: ProjectModel, weld) -> str:
    marks: set[str] = set()
    for part_id in weld.connected_part_ids:
        part = project.parts.get(part_id)
        if part:
            marks.update(_part_marks(project, part))
    for assembly in project.assemblies.values():
        if weld.internal_id in assembly.weld_ids and assembly.assembly_mark:
            marks.add(assembly.assembly_mark)
    return ", ".join(sorted(marks)) or "ONGEKOPPELD"


def _build_weld_rows(project: ProjectModel):
    # Preserve the complete fabrication identity. Different weld types, sizes,
    # processes, sides or locations may never disappear into one assembly row.
    groups: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    for weld in project.welds.values():
        mark = _weld_mark(project, weld)
        key = (
            mark,
            (weld.weld_type or weld.name).strip().upper(),
            _round(weld.size_mm),
            weld.process.strip().upper(),
            weld.side.strip().upper(),
            weld.location.strip().upper(),
        )
        groups[key].append(weld)
    rows: list[WeldBOMRow] = []
    entity_to_group: dict[str, str] = {}
    for key, group in sorted(groups.items(), key=lambda item: str(item[0])):
        mark = str(key[0])
        exemplar = sorted(group, key=lambda x: x.internal_id)[0]
        group_id = f"WELD-{stable_sha256(['weld', key])[:16]}"
        reasons = [] if mark != "ONGEKOPPELD" else ["Las is niet aan een assembly gekoppeld"]
        rows.append(WeldBOMRow(
            group_id=group_id,
            weld_type=exemplar.weld_type or exemplar.name,
            size_mm=_round(exemplar.size_mm),
            length_mm=_round(exemplar.length_mm),
            process=exemplar.process,
            side=exemplar.side,
            location=exemplar.location,
            quantity=len(group),
            total_length_mm=_round(sum(float(item.length_mm or 0.0) for item in group)),
            total_time_minutes=_round(sum(float(item.time_minutes or 0.0) for item in group)),
            total_cost=_round(sum(float(item.cost or 0.0) for item in group), 2),
            assembly_marks=[] if mark == "ONGEKOPPELD" else [mark],
            blocked=bool(reasons),
            blocking_reasons=reasons,
            source_entity_ids=_source_entity_ids(group),
            weld_ids=sorted(item.internal_id for item in group),
        ))
        for item in group:
            entity_to_group[item.internal_id] = group_id
    return rows, entity_to_group


def _assembly_compositions(project: ProjectModel, part_to_group: dict[str, str]):
    by_mark: dict[str, list[Any]] = defaultdict(list)
    for assembly in project.assemblies.values():
        by_mark[assembly.assembly_mark or assembly.internal_id].append(assembly)
    result: dict[str, set[str]] = {}
    for mark, group in by_mark.items():
        hashes = set()
        for assembly in group:
            composition = sorted(
                part_to_group[part_id]
                for part_id in (*assembly.part_ids, *assembly.purchased_item_ids)
                if part_id in part_to_group
            )
            hashes.add(stable_sha256(composition))
        result[mark] = hashes
    return by_mark, result


def _build_assembly_rows(project: ProjectModel, part_to_group, purchase_to_group):
    all_part_group = dict(part_to_group)
    all_part_group.update(purchase_to_group)
    by_mark, compositions = _assembly_compositions(project, all_part_group)
    rows: list[AssemblyBOMRow] = []
    entity_to_group: dict[str, str] = {}
    for mark, group in sorted(by_mark.items()):
        exemplar = sorted(group, key=lambda x: x.internal_id)[0]
        group_id = f"ASM-{stable_sha256(['assembly', mark])[:16]}"
        comp_hashes = sorted(compositions[mark])
        reasons = []
        if len(comp_hashes) > 1:
            reasons.append("Hetzelfde assemblymerk heeft verschillende onderdeelcomposities")
        part_occurrences = sum(
            1 for a in group for pid in a.part_ids
            if pid in project.parts and project.parts[pid].category != EntityCategory.PURCHASED_ITEM.value
        )
        purchased_occurrences = sum(
            1 for a in group for pid in a.part_ids
            if pid in project.parts and project.parts[pid].category == EntityCategory.PURCHASED_ITEM.value
        ) + sum(
            1 for a in group for pid in a.purchased_item_ids
            if pid in project.purchased_items
        )
        rows.append(AssemblyBOMRow(
            group_id=group_id,
            assembly_mark=mark,
            name=exemplar.name,
            quantity=len(group),
            part_occurrences=part_occurrences,
            unique_part_groups=len({
                all_part_group[pid]
                for a in group
                for pid in (*a.part_ids, *a.purchased_item_ids)
                if pid in all_part_group
            }),
            purchased_occurrences=purchased_occurrences,
            fastener_count=sum(
                max(1, int(project.fasteners[fid].quantity or 1))
                for a in group for fid in a.fastener_ids if fid in project.fasteners
            ),
            weld_count=sum(1 for a in group for wid in a.weld_ids if wid in project.welds),
            weight_each_kg=_round(sum(float(a.total_weight_kg or 0.0) for a in group) / len(group)),
            total_weight_kg=_round(sum(float(a.total_weight_kg or 0.0) for a in group)),
            surface_area_each_m2=_round(sum(float(a.surface_area_m2 or 0.0) for a in group) / len(group), 9),
            total_surface_area_m2=_round(sum(float(a.surface_area_m2 or 0.0) for a in group), 9),
            blocked=bool(reasons),
            blocking_reasons=reasons,
            composition_hashes=comp_hashes,
            assembly_ids=sorted(a.internal_id for a in group),
            part_ids=sorted({pid for a in group for pid in a.part_ids if pid in project.parts}),
            purchased_item_ids=sorted({
                pid for a in group for pid in a.purchased_item_ids
                if pid in project.purchased_items
            }),
            fastener_ids=sorted({
                fid for a in group for fid in a.fastener_ids if fid in project.fasteners
            }),
            weld_ids=sorted({
                wid for a in group for wid in a.weld_ids if wid in project.welds
            }),
            child_assembly_ids=sorted({
                child for a in group for child in a.child_assembly_ids
                if child in project.assemblies
            }),
        ))
        for a in group:
            entity_to_group[a.internal_id] = group_id
    return rows, entity_to_group, compositions


def _build_material_rows(project: ProjectModel, part_rows: list[PartBOMRow]):
    groups: dict[tuple[str, str, str], list[PartBOMRow]] = defaultdict(list)
    for row in part_rows:
        groups[(row.category, row.material, row.profile)].append(row)
    rows: list[MaterialBOMRow] = []
    for key, group in sorted(groups.items()):
        category, material, profile = key
        reasons = sorted({reason for row in group for reason in row.blocking_reasons})
        rows.append(MaterialBOMRow(
            group_id=f"MAT-{stable_sha256(['material', key])[:16]}",
            category=category,
            material=material,
            profile=profile,
            quantity=sum(row.quantity for row in group),
            net_length_mm=_round(sum(row.length_mm * row.quantity for row in group)),
            total_mass_kg=_round(sum(row.total_mass_kg for row in group)),
            total_surface_area_m2=_round(sum(row.total_surface_area_m2 for row in group), 9),
            part_group_count=len(group),
            blocked=bool(reasons),
            blocking_reasons=reasons,
        ))
    return rows


def _build_conflicts(project: ProjectModel, compositions, part_to_group):
    conflicts: list[BOMConflict] = []
    identity = _classification_conflicts(project)
    for item in identity:
        if item.conflict_type in {"same_mark_different_manufacturing", "same_geometry_different_material"}:
            conflicts.append(BOMConflict(
                conflict_id=item.conflict_id,
                conflict_type=item.conflict_type,
                severity=item.severity,
                blocking=item.blocking,
                key=item.key,
                message=item.message,
                entity_ids=list(item.entity_ids),
                group_ids=sorted({part_to_group[x] for x in item.entity_ids if x in part_to_group}),
                evidence=dict(item.evidence),
            ))
    for mark, hashes in sorted(compositions.items()):
        if len(hashes) > 1:
            assemblies = [a.internal_id for a in project.assemblies.values() if (a.assembly_mark or a.internal_id) == mark]
            conflicts.append(BOMConflict(
                conflict_id=stable_sha256(["assembly_composition", mark, sorted(hashes)]),
                conflict_type="same_assembly_mark_different_composition",
                severity="error",
                blocking=True,
                key=mark,
                message=f"Assemblymerk {mark} bevat {len(hashes)} verschillende composities.",
                entity_ids=sorted(assemblies),
                evidence={"composition_hashes": sorted(hashes)},
            ))
    unresolved = [p.internal_id for p in project.parts.values() if p.category == EntityCategory.UNKNOWN.value]
    if unresolved:
        conflicts.append(BOMConflict(
            conflict_id=stable_sha256(["unresolved_classification", sorted(unresolved)]),
            conflict_type="unresolved_classification",
            severity="error",
            blocking=True,
            key="project",
            message=f"{len(unresolved)} onderdelen vereisen nog handmatige classificatie.",
            entity_ids=sorted(unresolved),
            group_ids=sorted({part_to_group[x] for x in unresolved if x in part_to_group}),
        ))
    multi_mark = [x for x in identity if x.conflict_type == "same_geometry_different_marks"]
    if multi_mark:
        conflicts.append(BOMConflict(
            conflict_id=stable_sha256(["same_geometry_different_marks", [x.conflict_id for x in multi_mark]]),
            conflict_type="same_geometry_different_marks",
            severity="warning",
            blocking=False,
            key="project",
            message=f"{len(multi_mark)} geometriegroepen komen onder meerdere part positions voor.",
            entity_ids=sorted({i for x in multi_mark for i in x.entity_ids}),
            evidence={"group_count": len(multi_mark)},
        ))
    return conflicts


def _traceability(project, maps):
    rows: list[dict[str, Any]] = []
    for entity_type, collection, mapping in (
        ("assembly", project.assemblies, maps["assembly"]),
        ("part", project.parts, {**maps["part"], **maps["purchase"]}),
        ("purchased_item", project.purchased_items, maps["purchase"]),
        ("fastener", project.fasteners, maps["fastener"]),
        ("weld", project.welds, maps["weld"]),
    ):
        for entity in collection.values():
            rows.append({
                "entity_type": entity_type,
                "internal_id": entity.internal_id,
                "group_id": mapping.get(entity.internal_id, ""),
                "name": entity.name,
                "category": entity.category,
                "source_file_id": entity.source_identity.source_file_id,
                "source_entity_id": entity.source_identity.source_entity_id,
                "global_id": entity.source_identity.global_id,
                "part_position": entity.source_identity.part_position or getattr(entity, "part_position", ""),
                "assembly_mark": entity.source_identity.assembly_mark or getattr(entity, "assembly_mark", ""),
                "geometry_hash": getattr(entity, "geometry_hash", ""),
                "manufacturing_hash": getattr(entity, "manufacturing_hash", ""),
                "production_identity_hash": getattr(entity, "production_identity_hash", ""),
            })
    return sorted(rows, key=lambda x: (x["entity_type"], x["internal_id"]))


def build_bom_snapshot(
    project: ProjectModel,
    *,
    user: str = "system",
    classify_if_needed: bool = True,
) -> BOMSnapshot:
    classification_data = project.settings.get("classification") or {}
    if classify_if_needed and (
        not classification_data
        or any(part.classification_status == "unclassified" for part in project.parts.values())
    ):
        report = classify_project(project, user=user)
        classification_hash = report.report_sha256
    else:
        classification_hash = str(classification_data.get("report_sha256") or "")

    part_rows, part_map = _build_part_rows(project)
    purchase_rows, purchase_map = _build_purchase_rows(project)
    fastener_rows, fastener_map = _build_fastener_rows(project)
    weld_rows, weld_map = _build_weld_rows(project)
    assembly_rows, assembly_map, compositions = _build_assembly_rows(project, part_map, purchase_map)
    material_rows = _build_material_rows(project, part_rows)
    conflicts = _build_conflicts(project, compositions, part_map)
    traceability = _traceability(project, {
        "part": part_map, "purchase": purchase_map, "fastener": fastener_map,
        "weld": weld_map, "assembly": assembly_map,
    })

    total_entities = (
        len(project.parts)
        + len(project.purchased_items)
        + len(project.assemblies)
        + len(project.fasteners)
        + len(project.welds)
    )
    coverage = len(traceability) / total_entities if total_entities else 1.0
    non_purchase_parts = [p for p in project.parts.values() if p.category != EntityCategory.PURCHASED_ITEM.value]
    expected_mass = sum(float(p.mass_each_kg or 0.0) * max(1, int(p.quantity_total or 1)) for p in non_purchase_parts)
    expected_area = sum(float(p.surface_area_each_m2 or 0.0) * max(1, int(p.quantity_total or 1)) for p in non_purchase_parts)
    expected_length = sum(float(p.length_mm or 0.0) * max(1, int(p.quantity_total or 1)) for p in non_purchase_parts)
    grouped_part_ids = [entity_id for row in part_rows for entity_id in row.part_ids]
    grouped_legacy_purchase_ids = [entity_id for row in purchase_rows for entity_id in row.part_ids]
    grouped_purchase_ids = [
        entity_id for row in purchase_rows for entity_id in row.purchased_item_ids
    ]
    grouped_assembly_ids = [entity_id for row in assembly_rows for entity_id in row.assembly_ids]
    grouped_fastener_ids = [entity_id for row in fastener_rows for entity_id in row.fastener_ids]
    grouped_weld_ids = [entity_id for row in weld_rows for entity_id in row.weld_ids]
    traceability_ids = [str(row.get("internal_id") or "") for row in traceability]
    checks = {
        "part_coverage": sorted(grouped_part_ids) == sorted(part.internal_id for part in non_purchase_parts),
        "part_unique_membership": len(grouped_part_ids) == len(set(grouped_part_ids)),
        "purchase_coverage": (
            sorted(grouped_legacy_purchase_ids)
            == sorted(
                part.internal_id
                for part in project.parts.values()
                if part.category == EntityCategory.PURCHASED_ITEM.value
            )
            and sorted(grouped_purchase_ids) == sorted(project.purchased_items)
        ),
        "purchase_unique_membership": (
            len(grouped_legacy_purchase_ids) == len(set(grouped_legacy_purchase_ids))
            and len(grouped_purchase_ids) == len(set(grouped_purchase_ids))
            and not set(grouped_legacy_purchase_ids).intersection(grouped_purchase_ids)
        ),
        "assembly_coverage": sorted(grouped_assembly_ids) == sorted(project.assemblies),
        "assembly_unique_membership": len(grouped_assembly_ids) == len(set(grouped_assembly_ids)),
        "fastener_coverage": sorted(grouped_fastener_ids) == sorted(project.fasteners),
        "fastener_unique_membership": len(grouped_fastener_ids) == len(set(grouped_fastener_ids)),
        "weld_coverage": sorted(grouped_weld_ids) == sorted(project.welds),
        "weld_unique_membership": len(grouped_weld_ids) == len(set(grouped_weld_ids)),
        "traceability_coverage": len(traceability_ids) == total_entities,
        "traceability_unique_membership": (
            len(traceability_ids) == len(set(traceability_ids))
            and all(str(row.get("group_id") or "") for row in traceability)
        ),
        "mass_balance": abs(sum(row.total_mass_kg for row in part_rows) - expected_mass) <= 0.01,
        "surface_balance": abs(sum(row.total_surface_area_m2 for row in part_rows) - expected_area) <= 1e-6,
        "length_balance": abs(sum(row.length_mm * row.quantity for row in part_rows) - expected_length) <= 1e-3,
    }
    blocking_count = sum(1 for item in conflicts if item.blocking)
    warning_count = sum(1 for item in conflicts if not item.blocking)
    source_gate_open = bool(project.sources) and all(
        source.production_export_allowed for source in project.sources.values()
    )
    production_ready = all(checks.values()) and blocking_count == 0 and source_gate_open
    validation = BOMValidation(
        passed=all(checks.values()),
        production_ready=production_ready,
        checks=checks,
        blocking_conflict_count=blocking_count,
        warning_conflict_count=warning_count,
        traceability_coverage=coverage,
        messages=([] if all(checks.values()) else ["Een of meer BOM-identiteits- of balanscontroles zijn mislukt"])
        + ([] if source_gate_open else ["Bronbewijs ontbreekt of externe IFC/STEP-bronnen zijn nog niet productie-vrijgegeven"]),
    )
    summary = {
        "part_group_count": len(part_rows),
        "assembly_group_count": len(assembly_rows),
        "purchase_group_count": len(purchase_rows),
        "fastener_group_count": len(fastener_rows),
        "weld_group_count": len(weld_rows),
        "material_group_count": len(material_rows),
        "traceability_record_count": len(traceability),
        "blocking_conflict_count": blocking_count,
        "warning_conflict_count": warning_count,
        "total_part_mass_kg": _round(sum(row.total_mass_kg for row in part_rows)),
        "total_part_surface_m2": _round(sum(row.total_surface_area_m2 for row in part_rows), 9),
        "total_part_length_mm": _round(sum(row.length_mm * row.quantity for row in part_rows)),
        "purchase_quantity": _round(sum(row.quantity for row in purchase_rows)),
        "fastener_quantity": sum(row.quantity for row in fastener_rows),
        "weld_object_count": sum(row.quantity for row in weld_rows),
        "generated_at": utc_now_iso(),
    }
    snapshot = BOMSnapshot(
        project_id=project.project_id,
        project_name=project.project_name,
        classification_report_sha256=classification_hash,
        part_bom=part_rows,
        assembly_bom=assembly_rows,
        purchase_bom=purchase_rows,
        fastener_bom=fastener_rows,
        weld_bom=weld_rows,
        material_bom=material_rows,
        conflicts=conflicts,
        traceability=traceability,
        summary=summary,
        validation=validation,
    )
    snapshot.refresh_hash()
    project.settings["bom"] = {
        "schema_version": snapshot.schema_version,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "generated_at": snapshot.generated_at,
        "summary": summary,
        "validation": validation.to_dict(),
    }
    project.audit(
        "project.bom_built",
        user=user,
        after_hash=snapshot.snapshot_sha256,
        details=summary,
    )
    project.validate()
    return snapshot


__all__ = ["build_bom_snapshot"]
