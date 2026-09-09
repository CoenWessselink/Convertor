"""Semantic IFC project importer for CWS Convertor.

The importer preserves IFC identity, hierarchy, properties, materials,
placements and source geometry semantics.  It deliberately does not infer NC1
features from faceted/CSG geometry.  Every imported make-part therefore remains
production-blocked until the later feature-recognition and roundtrip gate has
succeeded.

IfcOpenShell can be added as an optional broad-geometry backend in a later
release.  The implementation below is dependency-light and is validated on the
large Tekla IFC2X3 reference model supplied with the project.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Mapping

from cws_convertor.project.model import (
    Assembly,
    EntityCategory,
    Fastener,
    FieldProvenance,
    Part,
    ProjectModel,
    ReviewStatus,
    SourceFileRecord,
    SourceIdentity,
    Transform3D,
    ValidationIssue,
    Weld,
    utc_now_iso,
)
from cws_convertor.project.source_geometry import build_ifc_source_locator

from .p21 import P21Document, P21Entity, scalar_value
from .semantic import (
    SEMANTIC_IMPORT_VERSION,
    SemanticCancelCheck,
    SemanticImportError,
    SemanticImportResult,
)

ProgressCallback = Callable[[float, str], None]
IFC_IMPORTER_VERSION = SEMANTIC_IMPORT_VERSION

IFC_PRODUCT_TYPES = {
    "IFCELEMENTASSEMBLY",
    "IFCPLATE",
    "IFCBEAM",
    "IFCCOLUMN",
    "IFCMEMBER",
    "IFCFOOTING",
    "IFCSLAB",
    "IFCBUILDINGELEMENTPROXY",
    "IFCMECHANICALFASTENER",
    "IFCFASTENER",
}
IFC_PART_TYPES = {
    "IFCPLATE",
    "IFCBEAM",
    "IFCCOLUMN",
    "IFCMEMBER",
    "IFCFOOTING",
    "IFCSLAB",
    "IFCBUILDINGELEMENTPROXY",
}
IFC_SPATIAL_TYPES = {
    "IFCPROJECT",
    "IFCSITE",
    "IFCBUILDING",
    "IFCBUILDINGSTOREY",
    "IFCSPACE",
}
_GEOMETRY_STOP_TYPES = {
    "IFCGEOMETRICREPRESENTATIONCONTEXT",
    "IFCGEOMETRICREPRESENTATIONSUBCONTEXT",
    "IFCOWNERHISTORY",
    "IFCPRESENTATIONSTYLEASSIGNMENT",
    "IFCSURFACESTYLE",
    "IFCSURFACESTYLERENDERING",
    "IFCCOLOURRGB",
    "IFCSTYLEDITEM",
}
_GEOMETRY_RELEVANT_TYPES = {
    "IFCEXTRUDEDAREASOLID",
    "IFCFACETEDBREP",
    "IFCMANIFOLDSOLIDBREP",
    "IFCBOOLEANRESULT",
    "IFCBOOLEANCLIPPINGRESULT",
    "IFCMAPPEDITEM",
    "IFCREPRESENTATIONMAP",
    "IFCSWEPTDISKSOLID",
    "IFCPOLYGONALFACESET",
    "IFCTRIANGULATEDFACESET",
    "IFCHALFSPACESOLID",
    "IFCSECTIONEDSOLIDHORIZONTAL",
}


@dataclass(frozen=True)
class IfcUnits:
    length_to_mm: float = 1.0
    area_to_m2: float = 1.0
    volume_to_m3: float = 1.0
    mass_to_kg: float = 1.0
    length_name: str = "millimetre"


@dataclass
class IfcIndexes:
    property_values: dict[int, tuple[str, Any, str]]
    property_sets: dict[int, tuple[str, dict[str, Any], dict[str, int]]]
    object_property_sets: dict[int, list[int]]
    object_materials: dict[int, list[str]]
    object_material_semantics: dict[int, list[dict[str, Any]]]
    object_type_names: dict[int, str]
    object_type_ids: dict[int, int]
    aggregate_children: dict[int, list[int]]
    aggregate_parents: dict[int, list[int]]
    spatial_containment: dict[int, list[int]]
    element_spatial_parent: dict[int, int]
    connections: list[tuple[int, int, list[int]]]


def _progress(callback: ProgressCallback | None, value: float, message: str) -> None:
    if callback is not None:
        callback(max(0.0, min(1.0, float(value))), message)


def _check_cancelled(callback: SemanticCancelCheck | None) -> None:
    if callback is not None:
        callback()


def _as_ref(value: Any) -> int | None:
    if isinstance(value, Mapping) and set(value) == {"ref"}:
        try:
            return int(value["ref"])
        except (TypeError, ValueError):
            return None
    return None


def _as_refs(value: Any) -> list[int]:
    result: list[int] = []
    if isinstance(value, Mapping):
        ref = _as_ref(value)
        if ref is not None:
            return [ref]
        for item in value.values():
            result.extend(_as_refs(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            result.extend(_as_refs(item))
    return result


def _typed_measure(value: Any) -> tuple[str, Any]:
    current = value
    measure_type = ""
    while isinstance(current, Mapping) and "type" in current and "value" in current:
        if not measure_type:
            measure_type = str(current.get("type") or "").upper()
        current = current.get("value")
    return measure_type, scalar_value(current)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        result = int(float(value))
    except (TypeError, ValueError):
        return default
    return result


def _normalise_name(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text not in {"$", "*"}:
            return text
    return ""


def _prefix_factor(prefix: str) -> float:
    return {
        "EXA": 1e18,
        "PETA": 1e15,
        "TERA": 1e12,
        "GIGA": 1e9,
        "MEGA": 1e6,
        "KILO": 1e3,
        "HECTO": 1e2,
        "DECA": 1e1,
        "DECI": 1e-1,
        "CENTI": 1e-2,
        "MILLI": 1e-3,
        "MICRO": 1e-6,
        "NANO": 1e-9,
        "PICO": 1e-12,
        "FEMTO": 1e-15,
        "ATTO": 1e-18,
        "": 1.0,
        "NONE": 1.0,
    }.get(str(prefix or "").upper(), 1.0)


def _detect_units(document: P21Document) -> IfcUnits:
    length_to_mm = 1.0
    area_to_m2 = 1.0
    volume_to_m3 = 1.0
    mass_to_kg = 1.0
    length_name = "millimetre"
    for entity in document.iter_type("IFCSIUNIT"):
        unit_type = entity.string(1).upper()
        prefix = entity.string(2).upper()
        name = entity.string(3).upper()
        factor = _prefix_factor(prefix)
        if unit_type == "LENGTHUNIT" and name == "METRE":
            length_to_mm = factor * 1000.0
            length_name = f"{prefix.lower() + ' ' if prefix else ''}metre".strip()
        elif unit_type == "AREAUNIT" and name == "SQUARE_METRE":
            area_to_m2 = factor * factor
        elif unit_type == "VOLUMEUNIT" and name == "CUBIC_METRE":
            volume_to_m3 = factor * factor * factor
        elif unit_type == "MASSUNIT" and name == "GRAM":
            mass_to_kg = factor / 1000.0
    return IfcUnits(
        length_to_mm=length_to_mm,
        area_to_m2=area_to_m2,
        volume_to_m3=volume_to_m3,
        mass_to_kg=mass_to_kg,
        length_name=length_name,
    )


def _convert_property_value(measure_type: str, value: Any, units: IfcUnits) -> Any:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return value
    kind = measure_type.upper()
    number = float(value)
    if "LENGTH" in kind:
        return number * units.length_to_mm
    if "AREA" in kind:
        return number * units.area_to_m2
    if "VOLUME" in kind:
        return number * units.volume_to_m3
    if "MASS" in kind:
        return number * units.mass_to_kg
    return value


def _build_property_indexes(document: P21Document, units: IfcUnits) -> tuple[
    dict[int, tuple[str, Any, str]],
    dict[int, tuple[str, dict[str, Any], dict[str, int]]],
    dict[int, list[int]],
]:
    values: dict[int, tuple[str, Any, str]] = {}
    for entity in document.iter_type("IFCPROPERTYSINGLEVALUE"):
        name = entity.string(0)
        measure_type, raw_value = _typed_measure(entity.value(2))
        values[entity.entity_id] = (
            name,
            _convert_property_value(measure_type, raw_value, units),
            measure_type,
        )

    # Basic IFC quantity support is included even though the Tekla reference
    # primarily emits quantity-like values in property sets.
    quantity_types = {
        "IFCQUANTITYLENGTH": (3, "IFCLENGTHMEASURE"),
        "IFCQUANTITYAREA": (3, "IFCAREAMEASURE"),
        "IFCQUANTITYVOLUME": (3, "IFCVOLUMEMEASURE"),
        "IFCQUANTITYWEIGHT": (3, "IFCMASSMEASURE"),
        "IFCQUANTITYCOUNT": (3, "IFCCOUNTMEASURE"),
        "IFCQUANTITYTIME": (3, "IFCTIMEMEASURE"),
    }
    for type_name, (index, measure_type) in quantity_types.items():
        for entity in document.iter_type(type_name):
            name = entity.string(0)
            raw_value = entity.number(index)
            values[entity.entity_id] = (
                name,
                _convert_property_value(measure_type, raw_value, units),
                measure_type,
            )

    psets: dict[int, tuple[str, dict[str, Any], dict[str, int]]] = {}
    for entity in document.iter_type("IFCPROPERTYSET"):
        name = entity.string(2) or f"PropertySet #{entity.entity_id}"
        props: dict[str, Any] = {}
        sources: dict[str, int] = {}
        for property_id in entity.refs(4):
            item = values.get(property_id)
            if item is None:
                continue
            prop_name, prop_value, _measure_type = item
            if not prop_name:
                continue
            # Preserve duplicate keys deterministically rather than silently
            # discarding a later conflicting source value.
            key = prop_name
            suffix = 2
            while key in props and props[key] != prop_value:
                key = f"{prop_name} ({suffix})"
                suffix += 1
            props[key] = prop_value
            sources[key] = property_id
        psets[entity.entity_id] = (name, props, sources)

    for entity in document.iter_type("IFCELEMENTQUANTITY"):
        name = entity.string(2) or f"ElementQuantity #{entity.entity_id}"
        props: dict[str, Any] = {}
        sources: dict[str, int] = {}
        for quantity_id in entity.refs(5):
            item = values.get(quantity_id)
            if item is None:
                continue
            prop_name, prop_value, _measure_type = item
            if prop_name:
                props[prop_name] = prop_value
                sources[prop_name] = quantity_id
        psets[entity.entity_id] = (name, props, sources)

    object_psets: dict[int, list[int]] = defaultdict(list)
    for relation in document.iter_type("IFCRELDEFINESBYPROPERTIES"):
        property_set_id = relation.ref(5)
        if property_set_id is None or property_set_id not in psets:
            continue
        for object_id in relation.refs(4):
            object_psets[object_id].append(property_set_id)
    return values, psets, dict(object_psets)


def _resolve_material_names(
    document: P21Document,
    entity_id: int | None,
    *,
    active: set[int] | None = None,
) -> list[str]:
    semantics = _resolve_material_semantics(document, entity_id, active=active)
    result: list[str] = []
    seen: set[str] = set()
    for item in semantics:
        name = item.get("material_name", "")
        clean = str(name or "").strip()
        if clean and clean.casefold() not in seen:
            seen.add(clean.casefold())
            result.append(clean)
    return result


def _resolve_material_semantics(
    document: P21Document,
    entity_id: int | None,
    *,
    units: IfcUnits | None = None,
    active: set[int] | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Expand IFC material selects without losing layer/profile roles.

    IFC2X3 material lists/layers and IFC4 profile/constituent sets use
    different argument positions.  Keeping this traversal explicit prevents
    a profile name or set name from being mistaken for a steel grade.
    """

    if entity_id is None:
        return []
    active = active or set()
    if entity_id in active:
        return []
    entity = document.get(entity_id)
    if entity is None:
        return []
    active.add(entity_id)
    base = dict(context or {})
    path = list(base.get("material_path_entity_ids") or [])
    path.append(str(entity_id))
    base["material_path_entity_ids"] = path
    records: list[dict[str, Any]] = []

    def descend(ref: int | None, **extra: Any) -> None:
        child_context = dict(base)
        child_context.update(extra)
        records.extend(
            _resolve_material_semantics(
                document,
                ref,
                units=units,
                active=active,
                context=child_context,
            )
        )

    if entity.type_name == "IFCMATERIAL":
        record = dict(base)
        record.update(
            {
                "semantic_kind": record.get("semantic_kind", "material"),
                "material_entity_id": str(entity_id),
                "material_name": entity.string(0).strip(),
                "material_description": entity.string(1).strip(),
                "material_category": entity.string(2).strip(),
            }
        )
        records.append(record)
    elif entity.type_name == "IFCMATERIALLIST":
        for ref in entity.refs(0):
            descend(ref, semantic_kind="material_list", material_list_entity_id=str(entity_id))
    elif entity.type_name in {"IFCMATERIALLAYER", "IFCMATERIALLAYERWITHOFFSETS"}:
        thickness = entity.number(1)
        descend(
            entity.ref(0),
            semantic_kind="material_layer",
            material_layer_entity_id=str(entity_id),
            layer_name=entity.string(3).strip(),
            layer_description=entity.string(4).strip(),
            layer_category=entity.string(5).strip(),
            layer_priority=entity.number(6),
            layer_offset_direction=entity.string(7).strip() if entity.type_name == "IFCMATERIALLAYERWITHOFFSETS" else "",
            layer_offset_values_mm=[
                _float(scalar_value(value)) * (units.length_to_mm if units else 1.0)
                for value in (entity.value(8) or ())
            ] if entity.type_name == "IFCMATERIALLAYERWITHOFFSETS" else [],
            layer_thickness_mm=(
                float(thickness) * (units.length_to_mm if units else 1.0)
                if thickness is not None
                else None
            ),
        )
    elif entity.type_name == "IFCMATERIALLAYERSETUSAGE":
        offset = entity.number(3)
        descend(
            entity.ref(0),
            material_layer_set_usage_entity_id=str(entity_id),
            layer_set_direction=entity.string(1).strip(),
            direction_sense=entity.string(2).strip(),
            offset_from_reference_line_mm=(
                float(offset) * (units.length_to_mm if units else 1.0)
                if offset is not None
                else None
            ),
        )
    elif entity.type_name == "IFCMATERIALLAYERSET":
        for ref in entity.refs(0):
            descend(
                ref,
                material_set_entity_id=str(entity_id),
                material_set_name=entity.string(1).strip(),
                material_set_description=entity.string(2).strip(),
            )
    elif entity.type_name == "IFCMATERIALPROFILE":
        # IFC4: Name, Description, Material, Profile, Priority, Category.
        profile_id = entity.ref(3)
        profile = document.get(profile_id)
        profile_descriptor = (
            _profile_definition_descriptor(profile, units or IfcUnits())
            if profile is not None
            else {}
        )
        descend(
            entity.ref(2),
            semantic_kind="material_profile",
            material_profile_entity_id=str(entity_id),
            material_profile_name=entity.string(0).strip(),
            material_profile_description=entity.string(1).strip(),
            material_profile_category=entity.string(5).strip(),
            material_profile_priority=entity.number(4),
            profile_definition_entity_id=str(profile_id or ""),
            profile_definition_type=profile.type_name if profile else "",
            profile_definition_name=profile.string(1).strip() if profile else "",
            profile_definition=profile_descriptor,
        )
    elif entity.type_name == "IFCMATERIALPROFILESETUSAGE":
        extent = entity.number(2)
        descend(
            entity.ref(0),
            material_profile_set_usage_entity_id=str(entity_id),
            cardinal_point=entity.number(1),
            reference_extent_mm=(
                float(extent) * (units.length_to_mm if units else 1.0)
                if extent is not None
                else None
            ),
        )
    elif entity.type_name == "IFCMATERIALPROFILESETUSAGETAPERING":
        # IFC4 subtype inherits ForProfileSet, CardinalPoint, ReferenceExtent;
        # ForProfileEndSet and CardinalEndPoint follow at indices 3 and 4.
        extent = entity.number(2)
        for end, ref, cardinal in (
            ("start", entity.ref(0), entity.number(1)),
            ("end", entity.ref(3), entity.number(4)),
        ):
            descend(
                ref,
                material_profile_set_usage_entity_id=str(entity_id),
                tapering_end=end,
                cardinal_point=cardinal,
                reference_extent_mm=(float(extent) * (units.length_to_mm if units else 1.0)) if extent is not None else None,
            )
    elif entity.type_name == "IFCMATERIALPROFILESET":
        for ref in entity.refs(2):
            descend(
                ref,
                material_set_entity_id=str(entity_id),
                material_set_name=entity.string(0).strip(),
                material_set_description=entity.string(1).strip(),
            )
    elif entity.type_name == "IFCMATERIALCONSTITUENT":
        # IFC4: Name, Description, Material, Fraction, Category.
        descend(
            entity.ref(2),
            semantic_kind="material_constituent",
            material_constituent_entity_id=str(entity_id),
            constituent_name=entity.string(0).strip(),
            constituent_description=entity.string(1).strip(),
            constituent_fraction=entity.number(3),
            constituent_category=entity.string(4).strip(),
        )
    elif entity.type_name == "IFCMATERIALCONSTITUENTSET":
        for ref in entity.refs(2):
            descend(
                ref,
                material_set_entity_id=str(entity_id),
                material_set_name=entity.string(0).strip(),
                material_set_description=entity.string(1).strip(),
            )
    else:
        # Forward-compatible, material-only traversal.  Never walk arbitrary
        # product references because that could attach unrelated materials.
        for ref in entity.references:
            target = document.get(ref)
            if target and target.type_name.startswith("IFCMATERIAL"):
                descend(ref)
    active.remove(entity_id)
    return records


def _build_material_indexes(
    document: P21Document,
    units: IfcUnits,
    object_type_ids: Mapping[int, int],
) -> tuple[dict[int, list[str]], dict[int, list[dict[str, Any]]]]:
    direct: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for relation in document.iter_type("IFCRELASSOCIATESMATERIAL"):
        material_id = relation.ref(5)
        semantics = _resolve_material_semantics(document, material_id, units=units)
        if not semantics:
            continue
        for object_id in relation.refs(4):
            for semantic in semantics:
                record = dict(semantic)
                record.update(
                    {
                        "association_entity_id": str(relation.entity_id),
                        "material_root_entity_id": str(material_id or ""),
                        "inherited_from_type": False,
                        "inherited_from_type_entity_id": "",
                        "effective": True,
                    }
                )
                direct[object_id].append(record)

    expanded: dict[int, list[dict[str, Any]]] = {
        object_id: list(records) for object_id, records in direct.items()
    }
    for object_id, type_id in object_type_ids.items():
        if type_id not in direct:
            continue
        inherited: list[dict[str, Any]] = []
        for semantic in direct[type_id]:
            record = dict(semantic)
            record["inherited_from_type"] = True
            record["inherited_from_type_entity_id"] = str(type_id)
            # Preserve overridden type evidence for audit, but never feed it
            # into canonical resolution when the occurrence declares its own.
            record["effective"] = object_id not in direct
            inherited.append(record)
        expanded[object_id] = list(expanded.get(object_id, [])) + inherited

    names: dict[int, list[str]] = {}
    for object_id, records in expanded.items():
        seen: set[str] = set()
        object_names: list[str] = []
        for record in records:
            if not bool(record.get("effective", True)):
                continue
            name = str(record.get("material_name") or "").strip()
            key = name.casefold()
            if name and key not in seen:
                seen.add(key)
                object_names.append(name)
        names[object_id] = object_names
    return names, expanded


def _build_material_index(document: P21Document) -> dict[int, list[str]]:
    """Compatibility wrapper for callers that only need direct names."""

    names, _semantics = _build_material_indexes(document, IfcUnits(), {})
    return names


def _build_type_indexes(document: P21Document) -> tuple[dict[int, str], dict[int, int]]:
    names: dict[int, str] = {}
    ids: dict[int, int] = {}
    for relation in document.iter_type("IFCRELDEFINESBYTYPE"):
        type_id = relation.ref(5)
        type_entity = document.get(type_id)
        if type_entity is None:
            continue
        type_name = _first_nonempty(type_entity.string(2), type_entity.string(0))
        for object_id in relation.refs(4):
            ids[object_id] = type_id
            if type_name:
                names[object_id] = type_name
    return names, ids


def _build_type_index(document: P21Document) -> dict[int, str]:
    names, _ids = _build_type_indexes(document)
    return names


def _build_relation_indexes(document: P21Document) -> tuple[
    dict[int, list[int]],
    dict[int, list[int]],
    dict[int, list[int]],
    dict[int, int],
    list[tuple[int, int, list[int]]],
]:
    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, list[int]] = defaultdict(list)
    for relation in document.iter_type("IFCRELAGGREGATES", "IFCRELNESTS"):
        parent_id = relation.ref(4)
        if parent_id is None:
            continue
        for child_id in relation.refs(5):
            if child_id not in children[parent_id]:
                children[parent_id].append(child_id)
            if parent_id not in parents[child_id]:
                parents[child_id].append(parent_id)

    spatial: dict[int, list[int]] = defaultdict(list)
    element_parent: dict[int, int] = {}
    for relation in document.iter_type("IFCRELCONTAINEDINSPATIALSTRUCTURE"):
        container_id = relation.ref(5)
        if container_id is None:
            continue
        for element_id in relation.refs(4):
            spatial[container_id].append(element_id)
            element_parent[element_id] = container_id

    connections: list[tuple[int, int, list[int]]] = []
    for relation in document.iter_type("IFCRELCONNECTSWITHREALIZINGELEMENTS"):
        relating = relation.ref(5)
        related = relation.ref(6)
        if relating is None or related is None:
            continue
        connections.append((relating, related, relation.refs(7)))
    return dict(children), dict(parents), dict(spatial), element_parent, connections


def _build_indexes(document: P21Document, units: IfcUnits) -> IfcIndexes:
    property_values, property_sets, object_property_sets = _build_property_indexes(
        document, units
    )
    type_names, type_ids = _build_type_indexes(document)
    # IFC4 types may own property sets through HasPropertySets while IFC2X3
    # exporters often attach them through IfcRelDefinesByProperties.  Merge
    # both forms after direct occurrence sets so occurrence values win.
    for type_id in set(type_ids.values()):
        type_entity = document.get(type_id)
        if type_entity is None:
            continue
        target = object_property_sets.setdefault(type_id, [])
        for property_set_id in type_entity.refs(5):
            if property_set_id in property_sets and property_set_id not in target:
                target.append(property_set_id)
    for object_id, type_id in type_ids.items():
        target = object_property_sets.setdefault(object_id, [])
        for property_set_id in object_property_sets.get(type_id, []):
            if property_set_id not in target:
                target.append(property_set_id)
    material_names, material_semantics = _build_material_indexes(
        document, units, type_ids
    )
    children, parents, spatial, element_parent, connections = _build_relation_indexes(
        document
    )
    return IfcIndexes(
        property_values=property_values,
        property_sets=property_sets,
        object_property_sets=object_property_sets,
        object_materials=material_names,
        object_material_semantics=material_semantics,
        object_type_names=type_names,
        object_type_ids=type_ids,
        aggregate_children=children,
        aggregate_parents=parents,
        spatial_containment=spatial,
        element_spatial_parent=element_parent,
        connections=connections,
    )


def _product_property_sets(
    entity_id: int,
    indexes: IfcIndexes,
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[Any, str, int]]]:
    nested: dict[str, dict[str, Any]] = {}
    flattened: dict[str, tuple[Any, str, int]] = {}
    for property_set_id in indexes.object_property_sets.get(entity_id, []):
        item = indexes.property_sets.get(property_set_id)
        if item is None:
            continue
        name, properties, sources = item
        target = nested.setdefault(name, {})
        for property_name, value in properties.items():
            # The occurrence's sets are ordered before inherited type sets.
            # Do not let the latter overwrite an explicit occurrence value.
            target.setdefault(property_name, value)
            normalized = _normalise_name(property_name)
            existing = flattened.get(normalized)
            if existing is None or ((existing[0] is None or existing[0] == "") and (value is not None and value != "")):
                flattened[normalized] = (
                    value,
                    f"{name}.{property_name}",
                    int(sources.get(property_name, property_set_id)),
                )
    return nested, flattened


def _property(
    flattened: Mapping[str, tuple[Any, str, int]],
    *names: str,
    default: Any = None,
) -> tuple[Any, str, int]:
    for name in names:
        item = flattened.get(_normalise_name(name))
        if item is not None and (item[0] is not None and item[0] != ""):
            return item
    return default, "", 0


def _vec(value: Any, dimension: int = 3) -> list[float]:
    scalar = scalar_value(value)
    if not isinstance(scalar, list):
        return [0.0] * dimension
    result = [_float(item) for item in scalar[:dimension]]
    result.extend([0.0] * (dimension - len(result)))
    return result


def _normalise(vector: Iterable[float], fallback: Iterable[float]) -> list[float]:
    values = [float(item) for item in vector]
    length = math.sqrt(sum(item * item for item in values))
    if length <= 1e-12:
        values = [float(item) for item in fallback]
        length = math.sqrt(sum(item * item for item in values))
    return [item / length for item in values]


def _cross(left: Iterable[float], right: Iterable[float]) -> list[float]:
    a = list(left)
    b = list(right)
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _dot(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _matrix_multiply(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [
            sum(left[row][index] * right[index][column] for index in range(4))
            for column in range(4)
        ]
        for row in range(4)
    ]


class IfcPlacementResolver:
    def __init__(self, document: P21Document, units: IfcUnits) -> None:
        self.document = document
        self.units = units
        self._axis_cache: dict[int, Transform3D] = {}
        self._local_cache: dict[int, tuple[Transform3D, Transform3D]] = {}
        self._active: set[int] = set()

    def _point(self, entity_id: int | None, dimension: int = 3) -> list[float]:
        entity = self.document.get(entity_id)
        if entity is None or entity.type_name != "IFCCARTESIANPOINT":
            return [0.0] * dimension
        values = _vec(entity.value(0), dimension)
        return [item * self.units.length_to_mm for item in values]

    def _direction(self, entity_id: int | None, fallback: list[float]) -> list[float]:
        entity = self.document.get(entity_id)
        if entity is None or entity.type_name != "IFCDIRECTION":
            return list(fallback)
        return _normalise(_vec(entity.value(0), len(fallback)), fallback)

    def axis_transform(self, entity_id: int | None) -> Transform3D:
        if entity_id is None:
            return Transform3D.identity()
        cached = self._axis_cache.get(entity_id)
        if cached is not None:
            return cached
        entity = self.document.get(entity_id)
        if entity is None:
            return Transform3D.identity()
        if entity.type_name == "IFCAXIS2PLACEMENT2D":
            origin2 = self._point(entity.ref(0), 2)
            x2 = self._direction(entity.ref(1), [1.0, 0.0])
            x_axis = _normalise([x2[0], x2[1], 0.0], [1.0, 0.0, 0.0])
            z_axis = [0.0, 0.0, 1.0]
            y_axis = _normalise(_cross(z_axis, x_axis), [0.0, 1.0, 0.0])
            origin = [origin2[0], origin2[1], 0.0]
        elif entity.type_name == "IFCAXIS2PLACEMENT3D":
            origin = self._point(entity.ref(0), 3)
            z_axis = self._direction(entity.ref(1), [0.0, 0.0, 1.0])
            raw_x = self._direction(entity.ref(2), [1.0, 0.0, 0.0])
            # Orthogonalise the IFC RefDirection against Axis to absorb harmless
            # floating point noise while rejecting no semantic information.
            raw_x = [raw_x[i] - _dot(raw_x, z_axis) * z_axis[i] for i in range(3)]
            x_axis = _normalise(raw_x, [1.0, 0.0, 0.0])
            y_axis = _normalise(_cross(z_axis, x_axis), [0.0, 1.0, 0.0])
            x_axis = _normalise(_cross(y_axis, z_axis), x_axis)
        else:
            return Transform3D.identity()
        transform = Transform3D(
            [
                [x_axis[0], y_axis[0], z_axis[0], origin[0]],
                [x_axis[1], y_axis[1], z_axis[1], origin[1]],
                [x_axis[2], y_axis[2], z_axis[2], origin[2]],
                [0.0, 0.0, 0.0, 1.0],
            ]
        )
        transform.validate()
        self._axis_cache[entity_id] = transform
        return transform

    def local_placement(self, entity_id: int | None) -> tuple[Transform3D, Transform3D]:
        if entity_id is None:
            identity = Transform3D.identity()
            return identity, identity
        cached = self._local_cache.get(entity_id)
        if cached is not None:
            return cached
        if entity_id in self._active:
            raise SemanticImportError(f"Cyclische IFC-placement bij #{entity_id}")
        entity = self.document.get(entity_id)
        if entity is None or entity.type_name != "IFCLOCALPLACEMENT":
            identity = Transform3D.identity()
            return identity, identity
        self._active.add(entity_id)
        relative = self.axis_transform(entity.ref(1))
        parent_id = entity.ref(0)
        if parent_id is None:
            global_transform = relative
        else:
            _parent_local, parent_global = self.local_placement(parent_id)
            global_transform = Transform3D(
                _matrix_multiply(parent_global.matrix, relative.matrix)
            )
            global_transform.validate()
        self._active.remove(entity_id)
        result = (relative, global_transform)
        self._local_cache[entity_id] = result
        return result


def _display_representation_ids(
    document: P21Document,
    definition: Any,
) -> tuple[int, ...]:
    """Return one coherent, renderable representation set for an IFC product.

    IFC products may expose Body, Axis, FootPrint and other parallel
    representations. Combining those sets produces duplicate or non-solid
    display geometry and lets a single unsupported helper representation force
    an otherwise valid product onto the proxy path. Prefer the authoritative
    Body representation and only use a non-auxiliary fallback when Body is not
    present.
    """
    if definition is None:
        return ()
    if definition.type_name == "IFCPRODUCTDEFINITIONSHAPE":
        candidate_ids = definition.refs(2)
    elif definition.type_name in {"IFCSHAPEREPRESENTATION", "IFCREPRESENTATION"}:
        candidate_ids = [definition.entity_id]
    else:
        return ()

    candidates: list[tuple[int, str]] = []
    for shape_id in candidate_ids:
        shape = document.get(shape_id)
        if shape is None:
            continue
        candidates.append((shape_id, shape.string(1).strip().upper()))

    for preferred in ("BODY", "FACETATION", "REFERENCE", "BOX"):
        selected = tuple(shape_id for shape_id, identifier in candidates if identifier == preferred)
        if selected:
            return selected

    auxiliary = {"AXIS", "FOOTPRINT", "CLEARANCE"}
    return tuple(shape_id for shape_id, identifier in candidates if identifier not in auxiliary)


def _dimension_text(value: float) -> str:
    return f"{float(value):.12g}"


@lru_cache(maxsize=1)
def _profile_dimension_catalog() -> tuple[Any, ...]:
    try:
        from profile_database import ProfileDatabase

        return tuple(ProfileDatabase(writable_copy=False).profiles)
    except Exception:
        return ()


def _unique_profile_by_dimensions(
    profile_types: set[str],
    expected: Mapping[str, float],
) -> tuple[str, list[str]]:
    """Match only explicitly supplied dimensions with machine precision."""

    matches: list[str] = []
    for profile in _profile_dimension_catalog():
        if str(profile.profile_type).upper() not in profile_types:
            continue
        matches_expected = True
        for field_name, value in expected.items():
            actual = float(getattr(profile, field_name, 0.0) or 0.0)
            if abs(actual - float(value)) > 1e-6:
                matches_expected = False
                break
        if matches_expected and profile.designation not in matches:
            matches.append(profile.designation)
    matches.sort()
    return (matches[0] if len(matches) == 1 else ""), matches


def _profile_definition_descriptor(
    profile: P21Entity,
    units: IfcUnits,
) -> dict[str, Any]:
    factor = units.length_to_mm
    kind = profile.type_name
    dimensions: dict[str, float] = {}
    catalogue_types: set[str] = set()
    catalogue_expected: dict[str, float] = {}

    def dim(index: int) -> float | None:
        value = profile.number(index)
        return None if value is None else float(value) * factor

    if kind == "IFCRECTANGLEPROFILEDEF":
        width, depth = dim(3), dim(4)
        if width is not None and depth is not None:
            dimensions = {"width": width, "depth": depth}
            catalogue_types = {"B"}
            catalogue_expected = {"dim1": max(width, depth), "dim2": min(width, depth)}
    elif kind == "IFCRECTANGLEHOLLOWPROFILEDEF":
        width, depth, wall = dim(3), dim(4), dim(5)
        if width is not None and depth is not None and wall is not None:
            dimensions = {"width": width, "depth": depth, "wall_thickness": wall}
            inner_radius, outer_radius = dim(6), dim(7)
            if inner_radius is not None:
                dimensions["inner_fillet_radius"] = inner_radius
            if outer_radius is not None:
                dimensions["outer_fillet_radius"] = outer_radius
            catalogue_types = {"M"}
            catalogue_expected = {
                "dim1": max(width, depth),
                "dim2": min(width, depth),
                "dim3": wall,
                "dim4": wall,
            }
    elif kind == "IFCCIRCLEPROFILEDEF":
        radius = dim(3)
        if radius is not None:
            dimensions = {"radius": radius, "diameter": 2.0 * radius}
            catalogue_types = {"RU"}
            catalogue_expected = {"dim1": 2.0 * radius}
    elif kind == "IFCCIRCLEHOLLOWPROFILEDEF":
        radius, wall = dim(3), dim(4)
        if radius is not None and wall is not None:
            dimensions = {
                "radius": radius,
                "diameter": 2.0 * radius,
                "wall_thickness": wall,
            }
            catalogue_types = {"RO"}
            catalogue_expected = {"dim1": 2.0 * radius, "dim3": wall}
    elif kind == "IFCISHAPEPROFILEDEF":
        width, depth, web, flange = dim(3), dim(4), dim(5), dim(6)
        if None not in (width, depth, web, flange):
            dimensions = {
                "overall_width": width,
                "overall_depth": depth,
                "web_thickness": web,
                "flange_thickness": flange,
            }
            fillet = dim(7)
            if fillet is not None:
                dimensions["fillet_radius"] = fillet
            catalogue_types = {"I"}
            catalogue_expected = {
                "dim1": depth,
                "dim2": width,
                "dim3": flange,
                "dim4": web,
            }
    elif kind == "IFCLSHAPEPROFILEDEF":
        depth, width, thickness = dim(3), dim(4), dim(5)
        width = depth if width is None else width
        if None not in (depth, width, thickness):
            dimensions = {"depth": depth, "width": width, "thickness": thickness}
            fillet, edge = dim(6), dim(7)
            if fillet is not None:
                dimensions["fillet_radius"] = fillet
            if edge is not None:
                dimensions["edge_radius"] = edge
            catalogue_types = {"L"}
            catalogue_expected = {
                "dim1": max(depth, width),
                "dim2": min(depth, width),
                "dim3": thickness,
                "dim4": thickness,
            }
    elif kind == "IFCUSHAPEPROFILEDEF":
        depth, width, web, flange = dim(3), dim(4), dim(5), dim(6)
        if None not in (depth, width, web, flange):
            dimensions = {
                "depth": depth,
                "flange_width": width,
                "web_thickness": web,
                "flange_thickness": flange,
            }
            fillet, edge = dim(7), dim(8)
            if fillet is not None:
                dimensions["fillet_radius"] = fillet
            if edge is not None:
                dimensions["edge_radius"] = edge
            catalogue_types = {"U", "C"}
            catalogue_expected = {
                "dim1": depth,
                "dim2": width,
                "dim3": flange,
                "dim4": web,
            }

    designation, candidates = _unique_profile_by_dimensions(
        catalogue_types, catalogue_expected
    ) if catalogue_types and catalogue_expected else ("", [])
    custom_parts = [f"CUSTOM:{kind}"]
    custom_parts.extend(
        f"{key.upper()}={_dimension_text(value)}"
        for key, value in sorted(dimensions.items())
    )
    return {
        "source_entity_id": str(profile.entity_id),
        "entity_type": kind,
        "ifc_type": kind,
        "profile_type": profile.string(0).strip(),
        "profile_name": profile.string(1).strip(),
        "dimensions_mm": dimensions,
        "parameters_mm": dimensions,
        "catalog_designation": designation,
        "catalog_candidates": candidates,
        "custom_designation": ":".join(custom_parts),
        "resolution_status": (
            "catalog_exact" if designation else "custom_deterministic"
            if dimensions else "unsupported"
        ),
    }


def _profile_family_from_definitions(
    definitions: Iterable[Mapping[str, Any]],
) -> str:
    families = {
        "IFCRECTANGLEPROFILEDEF": "flat",
        "IFCRECTANGLEHOLLOWPROFILEDEF": "rhs",
        "IFCCIRCLEPROFILEDEF": "round_bar",
        "IFCCIRCLEHOLLOWPROFILEDEF": "chs",
        "IFCISHAPEPROFILEDEF": "i",
        "IFCLSHAPEPROFILEDEF": "angle",
        "IFCUSHAPEPROFILEDEF": "u",
    }
    resolved = {
        families[str(item.get("entity_type") or "").upper()]
        for item in definitions
        if str(item.get("entity_type") or "").upper() in families
    }
    return next(iter(resolved)) if len(resolved) == 1 else ""


def _representation_summary(
    document: P21Document,
    representation_id: int | None,
    *,
    units: IfcUnits | None = None,
) -> dict[str, Any]:
    if representation_id is None:
        return {
            "source_representation_id": "",
            "representation_count": 0,
            "item_count": 0,
            "source_geometry_hash": "",
            "status": "missing",
        }
    definition = document.get(representation_id)
    if definition is None:
        return {
            "source_representation_id": str(representation_id),
            "representation_count": 0,
            "item_count": 0,
            "source_geometry_hash": "",
            "status": "missing_reference",
        }
    representation_ids = list(_display_representation_ids(document, definition))
    item_ids: list[int] = []
    representation_records: list[dict[str, Any]] = []
    primitive_counts: Counter[str] = Counter()
    profile_names: list[str] = []
    profile_definitions: list[dict[str, Any]] = []
    extrusion_depths: list[float] = []
    for shape_id in representation_ids:
        shape = document.get(shape_id)
        if shape is None:
            continue
        items = shape.refs(3)
        item_ids.extend(items)
        representation_records.append(
            {
                "source_entity_id": str(shape_id),
                "identifier": shape.string(1),
                "representation_type": shape.string(2),
                "item_source_ids": [str(item) for item in items],
                "item_types": [
                    document.get(item).type_name if document.get(item) else "MISSING"
                    for item in items
                ],
            }
        )
        reachable = document.reachable_ids(items, stop_types=_GEOMETRY_STOP_TYPES)
        for reachable_id in reachable:
            entity = document.get(reachable_id)
            if entity is None:
                continue
            if entity.type_name in _GEOMETRY_RELEVANT_TYPES:
                primitive_counts[entity.type_name] += 1
            if entity.type_name == "IFCEXTRUDEDAREASOLID":
                depth = entity.number(3)
                if depth is not None:
                    extrusion_depths.append(float(depth))
                profile = document.get(entity.ref(0))
                if profile is not None:
                    profile_name = profile.string(1)
                    if profile_name and profile_name not in profile_names:
                        profile_names.append(profile_name)
                    descriptor = _profile_definition_descriptor(
                        profile, units or IfcUnits()
                    )
                    if descriptor not in profile_definitions:
                        profile_definitions.append(descriptor)
    geometry_hash = (
        document.combined_semantic_hash(
            item_ids,
            ignore_types=_GEOMETRY_STOP_TYPES,
            order_independent=True,
        )
        if item_ids
        else ""
    )
    return {
        "source_representation_id": str(representation_id),
        "representation_count": len(representation_records),
        "item_count": len(item_ids),
        "representations": representation_records,
        "primitive_counts": dict(sorted(primitive_counts.items())),
        "profile_names": profile_names,
        "profile_definitions": profile_definitions,
        "extrusion_depths_source_units": extrusion_depths,
        "extrusion_depths_mm": [
            value * (units.length_to_mm if units else 1.0)
            for value in extrusion_depths
        ],
        "source_geometry_hash": geometry_hash,
        "source_semantics_preserved": True,
        "production_features_resolved": False,
        "status": "semantic_source_geometry",
    }


def _spatial_node(document: P21Document, entity_id: int) -> dict[str, Any]:
    entity = document.require(entity_id)
    return {
        "source_entity_id": str(entity_id),
        "entity_type": entity.type_name,
        "global_id": entity.string(0),
        "name": entity.string(2),
        "description": entity.string(3),
        "child_source_ids": [],
        "contained_entity_source_ids": [],
        "contained_internal_ids": [],
    }


def _build_spatial_tree(
    document: P21Document,
    indexes: IfcIndexes,
    source_to_internal: Mapping[int, str],
) -> dict[str, Any]:
    nodes = {
        entity.entity_id: _spatial_node(document, entity.entity_id)
        for entity in document.iter_type(*sorted(IFC_SPATIAL_TYPES))
    }
    parent_ids: set[int] = set()
    child_ids: set[int] = set()
    for parent_id, children in indexes.aggregate_children.items():
        if parent_id not in nodes:
            continue
        for child_id in children:
            if child_id in nodes:
                nodes[parent_id]["child_source_ids"].append(str(child_id))
                parent_ids.add(parent_id)
                child_ids.add(child_id)
    for container_id, elements in indexes.spatial_containment.items():
        node = nodes.get(container_id)
        if node is None:
            continue
        node["contained_entity_source_ids"] = [str(item) for item in elements]
        node["contained_internal_ids"] = [
            source_to_internal[item] for item in elements if item in source_to_internal
        ]
    roots = [str(item) for item in nodes if item not in child_ids]
    return {
        "schema": document.schema,
        "roots": roots,
        "nodes": {str(key): value for key, value in sorted(nodes.items())},
    }


def _source_identity(
    source: SourceFileRecord,
    entity: P21Entity,
    *,
    part_position: str = "",
    assembly_mark: str = "",
) -> SourceIdentity:
    return SourceIdentity(
        source_format="IFC",
        source_file_id=source.source_id,
        source_sha256=source.sha256,
        source_entity_id=str(entity.entity_id),
        global_id=entity.string(0),
        part_position=part_position,
        assembly_mark=assembly_mark,
    )


def _provenance(
    source: SourceFileRecord,
    entity_id: int,
    source_path: str,
    *,
    method: str = "ifc_semantic_exact",
    confidence: float = 1.0,
    status: str = "automatic",
) -> FieldProvenance:
    return FieldProvenance(
        source_file_id=source.source_id,
        source_entity_id=str(entity_id),
        source_path=source_path,
        method=method,
        confidence=confidence,
        status=status,
    )


def _flattened_value(
    flattened: Mapping[str, tuple[Any, str, int]],
    names: Iterable[str],
) -> tuple[Any, str, int]:
    return _property(flattened, *list(names))


def _clean_material(value: str) -> str:
    text = str(value or "").strip()
    upper = text.upper()
    if upper.startswith("STEEL/"):
        return text.split("/", 1)[1]
    return text


_MATERIAL_PLACEHOLDERS = {
    "", "$", "*", "-", "N/A", "NA", "NONE", "NULL", "UNDEFINED",
    "NOTDEFINED", "NOT DEFINED", "UNKNOWN", "ONBEKEND",
}


def _material_key(value: Any) -> str:
    clean = _clean_material(str(value or "").strip())
    if clean.upper() in _MATERIAL_PLACEHOLDERS:
        return ""
    resolved = _material_alias_catalog().resolve(clean)
    return str(resolved.material_code or clean).upper()


@lru_cache(maxsize=1)
def _material_alias_catalog():
    from material_database import MaterialDatabase
    return MaterialDatabase()


def _material_property_evidence(entity_id: int, indexes: IfcIndexes) -> list[dict[str, Any]]:
    """Preserve conflicting synonyms/duplicates while respecting type override."""
    inherited_sets = set(indexes.object_property_sets.get(indexes.object_type_ids.get(entity_id), []))
    candidates: list[dict[str, Any]] = []
    for pset_id in indexes.object_property_sets.get(entity_id, []):
        pset = indexes.property_sets.get(pset_id)
        if not pset:
            continue
        name, properties, sources = pset
        for field_name, value in properties.items():
            key = _normalise_name(field_name).split(" (")[0]
            if key not in {"material", "material grade", "grade"} or not _material_key(value):
                continue
            candidates.append({
                "value": value,
                "source_path": f"{name}.{field_name}",
                "source_entity_id": int(sources.get(field_name, pset_id)),
                "inherited": pset_id in inherited_sets,
            })
    has_occurrence = any(not item["inherited"] for item in candidates)
    for item in candidates:
        item["effective"] = not has_occurrence or not item["inherited"]
    return candidates


def _resolve_part_material(
    explicit_value: Any,
    explicit_path: str,
    explicit_source: int,
    semantics: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Resolve one production material from explicit IFC evidence.

    All leaf semantics remain available in the returned evidence.  A composite
    or conflicting association never becomes a made-up single grade.
    """

    explicit = _clean_material(str(explicit_value or "").strip())
    explicit_key = _material_key(explicit)
    association_values: dict[str, str] = {}
    association_records: list[Mapping[str, Any]] = []
    records_by_key: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in semantics:
        if not bool(record.get("effective", True)):
            continue
        name = _clean_material(str(record.get("material_name") or "").strip())
        key = _material_key(name)
        if not key:
            continue
        association_values.setdefault(key, name)
        association_records.append(record)
        records_by_key[key].append(record)

    candidate_values = list(association_values.values())
    resolution = {
        "value": "",
        "status": "missing",
        "confidence": 0.0,
        "method": "ifc_material_unresolved",
        "source_entity_id": int(explicit_source or 0),
        "source_path": explicit_path,
        "explicit_value": explicit if explicit_key else "",
        "associated_candidates": candidate_values,
    }
    if len(association_values) > 1:
        if explicit_key and explicit_key not in association_values:
            resolution["status"] = "conflicting_evidence"
            return resolution
        if explicit_key:
            resolution.update(
                {
                    "value": explicit,
                    "status": "resolved_composite_primary",
                    "confidence": 1.0,
                    "method": "ifc_property_declared_primary",
                }
            )
            return resolution
        loadbearing_keys = {
            key
            for key, records in records_by_key.items()
            if any(
                str(
                    record.get("layer_category")
                    or record.get("material_profile_category")
                    or record.get("constituent_category")
                    or ""
                ).strip().upper().replace("_", "") == "LOADBEARING"
                for record in records
            )
        }
        if len(loadbearing_keys) == 1:
            selected_key = next(iter(loadbearing_keys))
            selected_record = records_by_key[selected_key][0]
            inherited = bool(selected_record.get("inherited_from_type"))
            resolution.update(
                {
                    "value": association_values[selected_key],
                    "status": "resolved_composite_primary",
                    "confidence": 0.95 if inherited else 1.0,
                    "method": "ifc_material_loadbearing_role",
                    "source_entity_id": _int(
                        selected_record.get("inherited_from_type_entity_id")
                        or selected_record.get("material_entity_id")
                    ),
                    "source_path": (
                        "IfcRelDefinesByType/IfcMaterialRole[LoadBearing]"
                        if inherited else "IfcMaterialRole[LoadBearing]"
                    ),
                }
            )
            return resolution
        resolution["status"] = "ambiguous_association"
        return resolution
    if explicit_key and association_values and explicit_key not in association_values:
        resolution["status"] = "conflicting_evidence"
        return resolution
    if explicit_key:
        resolution.update(
            {
                "value": explicit,
                "status": "resolved",
                "confidence": 1.0,
                "method": "ifc_property_exact",
            }
        )
        return resolution
    if len(association_values) == 1:
        record = association_records[0]
        inherited = bool(record.get("inherited_from_type"))
        resolution.update(
            {
                "value": candidate_values[0],
                "status": "resolved_inherited" if inherited else "resolved",
                "confidence": 0.95 if inherited else 1.0,
                "method": (
                    "ifc_type_material_inheritance"
                    if inherited
                    else "ifc_material_association_exact"
                ),
                "source_entity_id": _int(
                    record.get("inherited_from_type_entity_id")
                    or record.get("material_entity_id")
                ),
                "source_path": (
                    "IfcRelDefinesByType/IfcRelAssociatesMaterial"
                    if inherited
                    else "IfcRelAssociatesMaterial"
                ),
            }
        )
    return resolution


def _resolve_fastener_grade(
    explicit_value: Any,
    explicit_path: str,
    explicit_source: int,
    standard_value: Any,
    standard_path: str,
    standard_source: int,
    semantics: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    from cws_convertor.project.classification import fastener_grade_candidates

    material_records = [
        record for record in semantics if bool(record.get("effective", True))
    ]
    material_values = [record.get("material_name", "") for record in material_records]
    explicit_candidates = fastener_grade_candidates(explicit_value)
    standard_candidates = fastener_grade_candidates(standard_value)
    material_candidates = fastener_grade_candidates(*material_values)
    candidates = tuple(
        sorted(set(explicit_candidates + standard_candidates + material_candidates))
    )
    result: dict[str, Any] = {
        "value": candidates[0] if len(candidates) == 1 else "",
        "candidates": list(candidates),
        "status": "resolved" if len(candidates) == 1 else
        "conflicting_evidence" if len(candidates) > 1 else "missing",
        "method": "ifc_fastener_grade_unresolved",
        "confidence": 0.0,
        "source_entity_id": 0,
        "source_path": "",
    }
    if len(candidates) != 1:
        return result
    grade = candidates[0]
    if grade in explicit_candidates:
        result.update(
            method="ifc_fastener_grade_property_exact",
            confidence=1.0,
            source_entity_id=int(explicit_source or 0),
            source_path=explicit_path,
        )
    elif grade in standard_candidates:
        result.update(
            method="ifc_fastener_standard_grade_exact",
            confidence=1.0,
            source_entity_id=int(standard_source or 0),
            source_path=standard_path,
        )
    else:
        source_record = next(
            (
                record for record in material_records
                if grade in fastener_grade_candidates(record.get("material_name", ""))
            ),
            {},
        )
        inherited = bool(source_record.get("inherited_from_type"))
        result.update(
            method=(
                "ifc_type_fastener_material_grade"
                if inherited else "ifc_fastener_material_grade_exact"
            ),
            confidence=0.95 if inherited else 1.0,
            source_entity_id=_int(
                source_record.get("inherited_from_type_entity_id")
                or source_record.get("material_entity_id")
            ),
            source_path=(
                "IfcRelDefinesByType/IfcRelAssociatesMaterial.RelatingMaterial.Name"
                if inherited
                else "IfcRelAssociatesMaterial.RelatingMaterial.Name"
            ),
        )
    return result


def _classification_for_part(entity_type: str, material: str) -> str:
    if entity_type in {"IFCFOOTING", "IFCSLAB"}:
        return EntityCategory.NON_STEEL.value
    if entity_type == "IFCBUILDINGELEMENTPROXY":
        return EntityCategory.UNKNOWN.value
    if material and any(token in material.upper() for token in ("CONCRETE", "BETON", "TIMBER", "WOOD", "HOUT", "METSELWERK", "MASONRY")):
        return EntityCategory.NON_STEEL.value
    return EntityCategory.MAKE_PART.value


def _group_material_associations(
    entity: P21Entity,
    semantics: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in semantics:
        grouped[str(item.get("association_entity_id") or "")].append(item)
    associations: list[dict[str, Any]] = []
    for association_id, records in grouped.items():
        first = records[0]
        if first.get("material_profile_set_usage_entity_id"):
            kind = "profile_set_usage"
        elif first.get("material_layer_set_usage_entity_id"):
            kind = "layer_set_usage"
        elif first.get("material_constituent_entity_id"):
            kind = "constituent_set"
        elif first.get("material_profile_entity_id"):
            kind = "profile_set"
        elif first.get("material_layer_entity_id"):
            kind = "layer_set"
        elif first.get("material_list_entity_id"):
            kind = "material_list"
        else:
            kind = "material"
        components: list[dict[str, Any]] = []
        for record in records:
            component: dict[str, Any] = {
                "material": {
                    "source_entity_id": str(record.get("material_entity_id") or ""),
                    "name": str(record.get("material_name") or ""),
                    "description": str(record.get("material_description") or ""),
                    "category": str(record.get("material_category") or ""),
                },
                "source_path_entity_ids": list(
                    record.get("material_path_entity_ids") or []
                ),
                "tapering_end": str(record.get("tapering_end") or ""),
            }
            if record.get("material_layer_entity_id"):
                component.update(
                    {
                        "source_entity_id": str(record.get("material_layer_entity_id")),
                        "name": str(record.get("layer_name") or ""),
                        "description": str(record.get("layer_description") or ""),
                        "category": str(record.get("layer_category") or ""),
                        "priority": record.get("layer_priority"),
                        "thickness_mm": record.get("layer_thickness_mm"),
                        "offset_direction": record.get("layer_offset_direction", ""),
                        "offset_values_mm": list(record.get("layer_offset_values_mm") or []),
                    }
                )
            elif record.get("material_profile_entity_id"):
                component.update(
                    {
                        "source_entity_id": str(record.get("material_profile_entity_id")),
                        "name": str(record.get("material_profile_name") or ""),
                        "description": str(record.get("material_profile_description") or ""),
                        "category": str(record.get("material_profile_category") or ""),
                        "priority": record.get("material_profile_priority"),
                        "profile": {
                            "source_entity_id": str(
                                record.get("profile_definition_entity_id") or ""
                            ),
                            "ifc_type": str(record.get("profile_definition_type") or ""),
                            "name": str(record.get("profile_definition_name") or ""),
                            "descriptor": dict(
                                record.get("profile_definition") or {}
                            ),
                        },
                    }
                )
            elif record.get("material_constituent_entity_id"):
                component.update(
                    {
                        "source_entity_id": str(
                            record.get("material_constituent_entity_id")
                        ),
                        "name": str(record.get("constituent_name") or ""),
                        "description": str(
                            record.get("constituent_description") or ""
                        ),
                        "category": str(record.get("constituent_category") or ""),
                        "fraction": record.get("constituent_fraction"),
                    }
                )
            components.append(component)
        inherited = bool(first.get("inherited_from_type"))
        associations.append(
            {
                "source_entity_id": association_id,
                "material_root_entity_id": str(
                    first.get("material_root_entity_id") or ""
                ),
                "kind": kind,
                "scope": "type" if inherited else "occurrence",
                "effective": bool(first.get("effective", True)),
                "declared_on_entity_id": str(
                    first.get("inherited_from_type_entity_id") or entity.entity_id
                ),
                "set_name": str(first.get("material_set_name") or ""),
                "set_description": str(first.get("material_set_description") or ""),
                "usage": {
                    "direction": str(first.get("layer_set_direction") or ""),
                    "sense": str(first.get("direction_sense") or ""),
                    "offset_mm": first.get("offset_from_reference_line_mm"),
                    "cardinal_point": first.get("cardinal_point"),
                    "reference_extent_mm": first.get("reference_extent_mm"),
                },
                "components": components,
            }
        )
    return associations


def _entity_property_payload(
    entity: P21Entity,
    nested_properties: dict[str, dict[str, Any]],
    material_names: list[str],
    type_name: str,
    material_semantics: Iterable[Mapping[str, Any]] | None = None,
    type_entity_id: int | None = None,
) -> dict[str, Any]:
    payload = {
        "ifc_entity_type": entity.type_name,
        "ifc_global_id": entity.string(0),
        "ifc_name": entity.string(2),
        "ifc_description": entity.string(3),
        "ifc_object_type": entity.string(4),
        "ifc_tag": entity.string(7),
        "ifc_type_name": type_name,
        "ifc_type_entity_id": str(type_entity_id or ""),
        "ifc_materials": material_names,
        "ifc_property_sets": nested_properties,
    }
    if material_semantics is not None:
        semantic_records = [dict(item) for item in material_semantics]
        payload["ifc_material_semantics"] = semantic_records
        payload["ifc_material_associations"] = _group_material_associations(
            entity, semantic_records
        )
    return payload


def import_ifc_project(
    project: ProjectModel,
    source: SourceFileRecord,
    path: str | Path,
    *,
    user: str = "system",
    progress: ProgressCallback | None = None,
    cancel_check: SemanticCancelCheck | None = None,
) -> SemanticImportResult:
    started = time.perf_counter()
    result = SemanticImportResult(
        source_id=source.source_id,
        file_name=source.file_name,
        source_format="IFC",
        strategy=source.import_strategy,
    )
    _check_cancelled(cancel_check)
    _progress(progress, 0.01, "IFC Part 21-grafiek lezen")
    document = P21Document.load(path, cancel_check=cancel_check)
    _check_cancelled(cancel_check)
    if "IFC" not in document.schema.upper():
        raise SemanticImportError(
            f"Bestand {source.file_name} declareert geen IFC-schema",
            {"schema": document.schema},
        )
    result.source_entity_counts = document.counts()
    result.schema = document.schema
    units = _detect_units(document)
    _progress(progress, 0.08, "IFC properties, materialen en relaties indexeren")
    indexes = _build_indexes(document, units)
    _check_cancelled(cancel_check)
    placement_resolver = IfcPlacementResolver(document, units)

    source_to_internal: dict[int, str] = {}
    assembly_by_source: dict[int, Assembly] = {}
    part_by_source: dict[int, Part] = {}
    fastener_by_source: dict[int, Fastener] = {}
    weld_by_source: dict[int, Weld] = {}
    mark_counts: Counter[str] = Counter()
    part_position_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    missing_representation = 0
    placement_failures: list[str] = []

    assembly_entities = list(document.iter_type("IFCELEMENTASSEMBLY"))
    for index, entity in enumerate(assembly_entities):
        if index % 25 == 0:
            _check_cancelled(cancel_check)
        nested, flattened = _product_property_sets(entity.entity_id, indexes)
        mark_value, mark_path, mark_source = _flattened_value(
            flattened,
            (
                "Assembly/Cast unit Mark",
                "Assembly/Cast unit position number",
                "Assembly Mark",
            ),
        )
        assembly_mark = _first_nonempty(mark_value, entity.string(7))
        identity = _source_identity(source, entity, assembly_mark=assembly_mark)
        internal_id = project.stable_entity_id("assembly", identity)
        try:
            local, global_transform = placement_resolver.local_placement(entity.ref(5))
        except Exception as exc:
            local = Transform3D.identity()
            global_transform = Transform3D.identity()
            placement_failures.append(f"#{entity.entity_id}: {exc}")
        weight, weight_path, weight_source = _flattened_value(
            flattened,
            ("Assembly/Cast unit weight", "Weight", "GrossWeight", "NetWeight"),
        )
        area, _area_path, _area_source = _flattened_value(
            flattened,
            ("Net surface area", "NetArea", "GrossArea", "SurfaceArea"),
        )
        assembly = Assembly(
            internal_id=internal_id,
            name=_first_nonempty(entity.string(2), assembly_mark, f"Assembly #{entity.entity_id}"),
            source_identity=identity,
            local_placement=local,
            global_placement=global_transform,
            properties=_entity_property_payload(
                entity,
                nested,
                indexes.object_materials.get(entity.entity_id, []),
                indexes.object_type_names.get(entity.entity_id, ""),
                indexes.object_material_semantics.get(entity.entity_id, []),
                indexes.object_type_ids.get(entity.entity_id),
            ),
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            assembly_mark=assembly_mark,
            quantity=1,
            total_weight_kg=_float(weight),
            surface_area_m2=_float(area),
            production_status=ReviewStatus.REVIEW_REQUIRED.value,
        )
        if assembly_mark:
            assembly.field_provenance["assembly_mark"] = _provenance(
                source,
                mark_source or entity.entity_id,
                mark_path or "IfcElement.Tag",
            )
            mark_counts[assembly_mark] += 1
        if weight_path:
            assembly.field_provenance["total_weight_kg"] = _provenance(
                source, weight_source, weight_path
            )
        assembly_by_source[entity.entity_id] = assembly
        source_to_internal[entity.entity_id] = internal_id
        project.assemblies[internal_id] = assembly
        if index % 50 == 0:
            _progress(
                progress,
                0.10 + 0.08 * (index / max(1, len(assembly_entities))),
                f"Assemblies materialiseren ({index}/{len(assembly_entities)})",
            )

    part_entities: list[P21Entity] = []
    for type_name in sorted(IFC_PART_TYPES):
        part_entities.extend(document.iter_type(type_name))
    part_entities.sort(key=lambda item: item.entity_id)
    for index, entity in enumerate(part_entities):
        if index % 25 == 0:
            _check_cancelled(cancel_check)
        nested, flattened = _product_property_sets(entity.entity_id, indexes)
        position_value, position_path, position_source = _flattened_value(
            flattened,
            ("Tekla Common.Part mark", "Part mark", "Part position number", "Part Position", "Position", "Mark"),
        )
        assembly_value, _assembly_path, _assembly_source = _flattened_value(
            flattened,
            ("Assembly/Cast unit position number", "Assembly/Cast unit Mark", "Assembly mark", "Assembly Mark"),
        )
        part_position = _first_nonempty(position_value, entity.string(7))
        assembly_mark = _first_nonempty(assembly_value)
        identity = _source_identity(
            source,
            entity,
            part_position=part_position,
            assembly_mark=assembly_mark,
        )
        internal_id = project.stable_entity_id("part", identity)
        try:
            local, global_transform = placement_resolver.local_placement(entity.ref(5))
        except Exception as exc:
            local = Transform3D.identity()
            global_transform = Transform3D.identity()
            placement_failures.append(f"#{entity.entity_id}: {exc}")
        material_names = indexes.object_materials.get(entity.entity_id, [])
        material_semantics = indexes.object_material_semantics.get(entity.entity_id, [])
        material_property, material_path, material_source = _flattened_value(
            flattened,
            ("MATERIAL", "Material", "Material grade", "Grade"),
        )
        property_evidence = _material_property_evidence(entity.entity_id, indexes)
        effective_properties = [item for item in property_evidence if item["effective"]]
        if effective_properties:
            primary = effective_properties[0]
            material_property, material_path, material_source = primary["value"], primary["source_path"], primary["source_entity_id"]
        material_resolution = _resolve_part_material(
            material_property,
            material_path,
            material_source,
            material_semantics,
        )
        material_resolution["property_evidence"] = property_evidence
        if len({_material_key(item["value"]) for item in effective_properties}) > 1:
            material_resolution.update(value="", status="conflicting_evidence", confidence=0.0, method="ifc_property_conflict")
        material = str(material_resolution["value"] or "")
        raw_context = str(material_property or "").strip()
        context_tokens = {"METSELWERK", "MASONRY", "BRICK", "BRICKWORK"}
        associated_context = [str(v).strip().upper().removeprefix("CONCRETE/")
                              for v in material_resolution.get("associated_candidates", ())]
        property_context = [str(v["value"]).strip().upper() for v in effective_properties]
        if (not material and raw_context.upper() in context_tokens
                and all(v == raw_context.upper() for v in associated_context + property_context)):
            material_resolution["original_resolution_status"] = material_resolution["status"]
            material = raw_context
            material_resolution.update(value=material, status="resolved_non_steel_context", confidence=1.0,
                                       method="explicit_non_steel_property", source_path=material_path,
                                       source_entity_id=material_source)
        profile_property, profile_path, profile_source = _flattened_value(
            flattened,
            ("PROFILE", "Profile", "Profile name", "Section", "Cross section"),
        )
        type_name = indexes.object_type_names.get(entity.entity_id, "")
        representation = _representation_summary(document, entity.ref(6), units=units)
        representation["source_locator"] = build_ifc_source_locator(
            source,
            source_entity_id=identity.source_entity_id,
            global_id=identity.global_id,
            representation_id=str(representation.get("source_representation_id") or ""),
            source_geometry_hash=str(representation.get("source_geometry_hash") or ""),
        )
        named_profile = _first_nonempty(
            profile_property,
            entity.string(3),
            type_name,
            *(representation.get("profile_names") or []),
        )
        profile_definitions = list(representation.get("profile_definitions") or [])
        geometry_catalogs = list(
            dict.fromkeys(
                str(item.get("catalog_designation") or "")
                for item in profile_definitions
                if item.get("catalog_designation")
            )
        )
        geometry_customs = list(
            dict.fromkeys(
                str(item.get("custom_designation") or "")
                for item in profile_definitions
                if item.get("custom_designation")
            )
        )
        profile = _first_nonempty(
            named_profile,
            geometry_catalogs[0] if len(geometry_catalogs) == 1 else "",
            geometry_customs[0] if len(geometry_customs) == 1 else "",
        )
        length, length_path, length_source = _flattened_value(
            flattened,
            ("Length", "CutLength", "Cut length", "OverallLength"),
        )
        weight, weight_path, weight_source = _flattened_value(
            flattened,
            ("Weight", "NetWeight", "GrossWeight", "Mass"),
        )
        area, area_path, area_source = _flattened_value(
            flattened,
            ("Net surface area", "NetArea", "GrossArea", "SurfaceArea"),
        )
        coating, coating_path, coating_source = _flattened_value(
            flattened,
            ("Finish", "Coating", "Surface treatment"),
        )
        category = _classification_for_part(entity.type_name, material)
        from cws_convertor.project.production_normalization import (
            infer_profile_type,
            prepare_exact_imported_part,
        )
        from cws_convertor.project.classification import (
            _catalog_material,
            _catalog_profile,
        )

        exact_profile = _catalog_profile(profile)
        exact_material = _catalog_material(material)
        named_profile_catalog = _catalog_profile(named_profile)
        profile_conflict = bool(
            named_profile_catalog
            and geometry_catalogs
            and any(item != named_profile_catalog for item in geometry_catalogs)
        )
        if profile_conflict:
            profile = ""
            exact_profile = ""

        part = Part(
            internal_id=internal_id,
            name=_first_nonempty(
                entity.string(2), part_position, profile, f"{entity.type_name} #{entity.entity_id}"
            ),
            category=category,
            source_identity=identity,
            local_placement=local,
            global_placement=global_transform,
            properties=_entity_property_payload(
                entity,
                nested,
                material_names,
                type_name,
                material_semantics,
                indexes.object_type_ids.get(entity.entity_id),
            ),
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            part_position=part_position,
            quantity_total=1,
            part_type=entity.type_name.removeprefix("IFC").lower(),
            profile=profile,
            profile_type=(
                _profile_family_from_definitions(profile_definitions)
                or infer_profile_type(profile, entity.type_name)
            ),
            material=material,
            material_grade=material,
            profile_confidence=1.0 if exact_profile else (0.65 if profile else 0.0),
            material_confidence=(
                1.0 if exact_material else
                0.65 if material_resolution["status"].startswith("resolved") else 0.0
            ),
            length_mm=_float(length),
            mass_each_kg=_float(weight),
            surface_area_each_m2=_float(area),
            geometry_descriptor=representation,
            coating=str(coating or ""),
            nc1_eligible=False,
            export_status="review_required",
        )
        part.properties["ifc_material_resolution"] = dict(material_resolution)
        if material_resolution["status"] == "ambiguous_association":
            part.validation_issues.append(
                ValidationIssue(
                    code="CWS-IFC-MATERIAL-PRIMARY-AMBIGUOUS",
                    message=(
                        "Meerdere IFC-materialen zijn behouden; er is geen "
                        "eenduidig primair productiemateriaal gedeclareerd."
                    ),
                    severity="error",
                    blocking=True,
                    entity_id=internal_id,
                    field_path="material",
                    source="ifc_semantic_import",
                )
            )
        elif material_resolution["status"] == "conflicting_evidence":
            part.validation_issues.append(
                ValidationIssue(
                    code="CWS-IFC-MATERIAL-CONFLICT",
                    message=(
                        "IFC-property en materiaalassociatie spreken elkaar tegen; "
                        "materiaal is niet automatisch gekozen."
                    ),
                    severity="error",
                    blocking=True,
                    entity_id=internal_id,
                    field_path="material",
                    source="ifc_semantic_import",
                )
            )
        if profile_conflict:
            part.validation_issues.append(
                ValidationIssue(
                    code="CWS-IFC-PROFILE-CONFLICT",
                    message=(
                        "Genoemd IFC-profiel en parametrische profieldefinitie "
                        "verwijzen naar verschillende catalogusprofielen."
                    ),
                    severity="error",
                    blocking=True,
                    entity_id=internal_id,
                    field_path="profile",
                    source="ifc_semantic_import",
                )
            )
        part.properties["ifc_spatial_container_source_id"] = str(
            indexes.element_spatial_parent.get(entity.entity_id, "")
        )
        part.properties["semantic_import"] = {
            "identity_exact": True,
            "placement_exact": entity.ref(5) is not None,
            "property_mapping_exact": True,
            "source_geometry_semantics_preserved": bool(
                representation.get("source_semantics_preserved")
            ),
            "production_features_resolved": False,
        }
        if part_position:
            part.field_provenance["part_position"] = _provenance(
                source,
                position_source or entity.entity_id,
                position_path or "IfcElement.Tag",
            )
            part_position_counts[part_position] += 1
        if profile:
            if profile_property:
                resolved_profile_source = profile_source or entity.entity_id
                resolved_profile_path = profile_path
                resolved_profile_method = "ifc_semantic_exact"
                resolved_profile_confidence = 1.0
            elif entity.string(3):
                resolved_profile_source = entity.entity_id
                resolved_profile_path = "IfcProduct.Description"
                resolved_profile_method = "ifc_semantic_exact"
                resolved_profile_confidence = 1.0
            elif type_name:
                resolved_profile_source = indexes.object_type_ids.get(
                    entity.entity_id, entity.entity_id
                )
                resolved_profile_path = "IfcRelDefinesByType/IfcTypeObject.Name"
                resolved_profile_method = "ifc_type_inheritance"
                resolved_profile_confidence = 0.95
            else:
                descriptor = profile_definitions[0] if profile_definitions else {}
                resolved_profile_source = _int(
                    descriptor.get("source_entity_id"), entity.entity_id
                )
                resolved_profile_path = "IfcExtrudedAreaSolid.SweptArea"
                resolved_profile_method = "ifc_parametric_profile_definition"
                resolved_profile_confidence = 1.0 if exact_profile else 0.8
            part.field_provenance["profile"] = _provenance(
                source,
                resolved_profile_source,
                resolved_profile_path,
                method=resolved_profile_method,
                confidence=resolved_profile_confidence,
                status="automatic" if exact_profile else "derived",
            )
        if material:
            part.field_provenance["material"] = _provenance(
                source,
                _int(material_resolution["source_entity_id"], entity.entity_id),
                str(material_resolution["source_path"] or "IfcRelAssociatesMaterial"),
                method=str(material_resolution["method"]),
                confidence=float(material_resolution["confidence"]),
                status=(
                    "derived"
                    if material_resolution["status"] == "resolved_inherited"
                    else "automatic"
                ),
            )
        if length_path:
            part.field_provenance["length_mm"] = _provenance(
                source, length_source, length_path
            )
        if weight_path:
            part.field_provenance["mass_each_kg"] = _provenance(
                source, weight_source, weight_path
            )
        if area_path:
            part.field_provenance["surface_area_each_m2"] = _provenance(
                source, area_source, area_path
            )
        if coating_path:
            part.field_provenance["coating"] = _provenance(
                source, coating_source, coating_path
            )
        # Exact-source preparation must inspect the populated evidence flags
        # and field provenance; it may not promote an incomplete import row.
        prepare_exact_imported_part(part)
        if representation.get("status") != "semantic_source_geometry":
            missing_representation += 1
        part.recompute_hashes()
        part.validate_base()
        part_by_source[entity.entity_id] = part
        source_to_internal[entity.entity_id] = internal_id
        project.parts[internal_id] = part
        classification_counts[category] += 1
        if index % 100 == 0:
            _progress(
                progress,
                0.19 + 0.34 * (index / max(1, len(part_entities))),
                f"Onderdelen materialiseren ({index}/{len(part_entities)})",
            )

    mechanical_entities = list(document.iter_type("IFCMECHANICALFASTENER"))
    for index, entity in enumerate(mechanical_entities):
        if index % 25 == 0:
            _check_cancelled(cancel_check)
        nested, flattened = _product_property_sets(entity.entity_id, indexes)
        diameter, diameter_path, diameter_source = _flattened_value(
            flattened,
            ("Bolt size", "Nominal diameter", "Diameter"),
        )
        if diameter is None or diameter == "":
            direct = entity.number(8)
            diameter = direct * units.length_to_mm if direct is not None else 0.0
            diameter_path = "IfcMechanicalFastener.NominalDiameter"
            diameter_source = entity.entity_id
        length, length_path, length_source = _flattened_value(
            flattened,
            ("Bolt length", "Length", "Nominal length"),
        )
        if length is None or length == "":
            direct = entity.number(9)
            length = direct * units.length_to_mm if direct is not None else 0.0
            length_path = "IfcMechanicalFastener.NominalLength"
            length_source = entity.entity_id
        quantity, _quantity_path, _quantity_source = _flattened_value(
            flattened,
            ("Bolt count", "Count", "Quantity"),
        )
        standard, standard_path, standard_source = _flattened_value(
            flattened,
            ("Bolt standard", "Standard"),
        )
        grade, grade_path, grade_source = _flattened_value(
            flattened,
            ("Bolt grade", "Grade", "Quality"),
        )
        hole_diameter, _hole_path, _hole_source = _flattened_value(
            flattened,
            ("Bolt hole diameter", "Hole diameter"),
        )
        slot_x, _sx_path, _sx_source = _flattened_value(
            flattened, ("Slotted hole x", "Slot x")
        )
        slot_y, _sy_path, _sy_source = _flattened_value(
            flattened, ("Slotted hole y", "Slot y")
        )
        fastener_material_semantics = indexes.object_material_semantics.get(
            entity.entity_id, []
        )
        grade_resolution = _resolve_fastener_grade(
            grade,
            grade_path,
            grade_source,
            standard,
            standard_path,
            standard_source,
            fastener_material_semantics,
        )
        identity = _source_identity(source, entity)
        internal_id = project.stable_entity_id("fastener", identity)
        representation = _representation_summary(document, entity.ref(6), units=units)
        representation["source_locator"] = build_ifc_source_locator(
            source,
            source_entity_id=identity.source_entity_id,
            global_id=identity.global_id,
            representation_id=str(representation.get("source_representation_id") or ""),
            source_geometry_hash=str(representation.get("source_geometry_hash") or ""),
        )
        try:
            local, global_transform = placement_resolver.local_placement(entity.ref(5))
        except Exception as exc:
            local = Transform3D.identity()
            global_transform = Transform3D.identity()
            placement_failures.append(f"#{entity.entity_id}: {exc}")
        fastener = Fastener(
            internal_id=internal_id,
            name=_first_nonempty(entity.string(2), "Fastener"),
            source_identity=identity,
            local_placement=local,
            global_placement=global_transform,
            properties=_entity_property_payload(
                entity,
                nested,
                indexes.object_materials.get(entity.entity_id, []),
                indexes.object_type_names.get(entity.entity_id, ""),
                fastener_material_semantics,
                indexes.object_type_ids.get(entity.entity_id),
            ),
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            fastener_type=_first_nonempty(entity.string(2), "mechanical_fastener"),
            diameter_mm=_float(diameter),
            grade=str(grade_resolution["value"] or ""),
            length_mm=_float(length),
            standard=str(standard or ""),
            quantity=max(1, _int(quantity, 1)),
            hole_diameter_mm=_float(hole_diameter),
            slot={"x_mm": _float(slot_x), "y_mm": _float(slot_y)},
            geometry_descriptor=representation,
        )
        fastener.properties["ifc_fastener_grade_resolution"] = dict(grade_resolution)
        if grade_resolution["status"] == "conflicting_evidence":
            fastener.validation_issues.append(
                ValidationIssue(
                    code="CWS-IFC-FASTENER-GRADE-CONFLICT",
                    message=(
                        "Tegenstrijdige bevestigingskwaliteiten in IFC-property, "
                        "norm of materiaalassociatie; kwaliteit is niet gekozen."
                    ),
                    severity="error",
                    blocking=True,
                    entity_id=internal_id,
                    field_path="grade",
                    source="ifc_semantic_import",
                )
            )
        fastener.field_provenance["diameter_mm"] = _provenance(
            source, diameter_source, diameter_path
        )
        fastener.field_provenance["length_mm"] = _provenance(
            source, length_source, length_path
        )
        if fastener.grade:
            fastener.field_provenance["grade"] = _provenance(
                source,
                _int(grade_resolution["source_entity_id"], entity.entity_id),
                str(grade_resolution["source_path"]),
                method=str(grade_resolution["method"]),
                confidence=float(grade_resolution["confidence"]),
                status=(
                    "derived"
                    if str(grade_resolution["method"]).startswith("ifc_type_")
                    else "automatic"
                ),
            )
        fastener_by_source[entity.entity_id] = fastener
        source_to_internal[entity.entity_id] = internal_id
        project.fasteners[internal_id] = fastener
        classification_counts[EntityCategory.FASTENER.value] += 1
        if index % 150 == 0:
            _progress(
                progress,
                0.54 + 0.08 * (index / max(1, len(mechanical_entities))),
                f"Bevestigingsmiddelen materialiseren ({index}/{len(mechanical_entities)})",
            )

    generic_fastener_entities = list(document.iter_type("IFCFASTENER"))
    non_weld_fasteners = 0
    for index, entity in enumerate(generic_fastener_entities):
        if index % 25 == 0:
            _check_cancelled(cancel_check)
        nested, flattened = _product_property_sets(entity.entity_id, indexes)
        generic_standard, generic_standard_path, generic_standard_source = _flattened_value(
            flattened, ("Bolt standard", "Standard")
        )
        generic_grade, generic_grade_path, generic_grade_source = _flattened_value(
            flattened, ("Bolt grade", "Grade", "Quality")
        )
        generic_material_semantics = indexes.object_material_semantics.get(
            entity.entity_id, []
        )
        generic_grade_resolution = _resolve_fastener_grade(
            generic_grade,
            generic_grade_path,
            generic_grade_source,
            generic_standard,
            generic_standard_path,
            generic_standard_source,
            generic_material_semantics,
        )
        combined_text = " ".join(
            [
                entity.string(2),
                entity.string(3),
                entity.string(4),
                entity.string(7),
                " ".join(nested),
            ]
        ).casefold()
        is_weld = any(token in combined_text for token in ("weld", "las", "lassen"))
        identity = _source_identity(source, entity)
        representation = _representation_summary(document, entity.ref(6), units=units)
        representation["source_locator"] = build_ifc_source_locator(
            source,
            source_entity_id=identity.source_entity_id,
            global_id=identity.global_id,
            representation_id=str(representation.get("source_representation_id") or ""),
            source_geometry_hash=str(representation.get("source_geometry_hash") or ""),
        )
        try:
            local, global_transform = placement_resolver.local_placement(entity.ref(5))
        except Exception as exc:
            local = Transform3D.identity()
            global_transform = Transform3D.identity()
            placement_failures.append(f"#{entity.entity_id}: {exc}")
        if is_weld:
            weld_type, _weld_type_path, _weld_type_source = _flattened_value(
                flattened, ("Weld type", "Type")
            )
            weld_size, _weld_size_path, _weld_size_source = _flattened_value(
                flattened, ("Weld size", "Size", "Throat thickness")
            )
            weld_length, _weld_length_path, _weld_length_source = _flattened_value(
                flattened, ("Weld length", "Length")
            )
            process, _process_path, _process_source = _flattened_value(
                flattened, ("Weld process", "Process")
            )
            location, _location_path, _location_source = _flattened_value(
                flattened, ("Location", "Weld location")
            )
            internal_id = project.stable_entity_id("weld", identity)
            weld = Weld(
                internal_id=internal_id,
                name=_first_nonempty(entity.string(2), "Weld"),
                source_identity=identity,
                local_placement=local,
                global_placement=global_transform,
                properties=_entity_property_payload(
                    entity,
                    nested,
                    indexes.object_materials.get(entity.entity_id, []),
                    indexes.object_type_names.get(entity.entity_id, ""),
                    generic_material_semantics,
                    indexes.object_type_ids.get(entity.entity_id),
                ),
                confidence=1.0,
                status=ReviewStatus.REVIEW_REQUIRED.value,
                weld_type=str(weld_type or ""),
                size_mm=_float(weld_size),
                length_mm=_float(weld_length),
                process=str(process or ""),
                location=str(location or "workshop"),
                geometry_descriptor=representation,
            )
            weld_by_source[entity.entity_id] = weld
            source_to_internal[entity.entity_id] = internal_id
            project.welds[internal_id] = weld
            classification_counts[EntityCategory.WELD.value] += 1
        else:
            # IFCFASTENER is not automatically called a weld.  Non-weld cases
            # remain visible as ordinary fasteners and are flagged for review.
            internal_id = project.stable_entity_id("fastener", identity)
            fastener = Fastener(
                internal_id=internal_id,
                name=_first_nonempty(entity.string(2), "Fastener"),
                source_identity=identity,
                local_placement=local,
                global_placement=global_transform,
                properties=_entity_property_payload(
                    entity,
                    nested,
                    indexes.object_materials.get(entity.entity_id, []),
                    indexes.object_type_names.get(entity.entity_id, ""),
                    generic_material_semantics,
                    indexes.object_type_ids.get(entity.entity_id),
                ),
                confidence=0.8,
                status=ReviewStatus.REVIEW_REQUIRED.value,
                fastener_type="ifc_fastener_unclassified",
                grade=str(generic_grade_resolution["value"] or ""),
                standard=str(generic_standard or ""),
                geometry_descriptor=representation,
            )
            fastener.properties["ifc_fastener_grade_resolution"] = dict(
                generic_grade_resolution
            )
            if generic_grade_resolution["status"] == "conflicting_evidence":
                fastener.validation_issues.append(
                    ValidationIssue(
                        code="CWS-IFC-FASTENER-GRADE-CONFLICT",
                        message=(
                            "Tegenstrijdige bevestigingskwaliteiten; kwaliteit "
                            "is niet automatisch gekozen."
                        ),
                        severity="error",
                        blocking=True,
                        entity_id=internal_id,
                        field_path="grade",
                        source="ifc_semantic_import",
                    )
                )
            if fastener.grade:
                fastener.field_provenance["grade"] = _provenance(
                    source,
                    _int(
                        generic_grade_resolution["source_entity_id"],
                        entity.entity_id,
                    ),
                    str(generic_grade_resolution["source_path"]),
                    method=str(generic_grade_resolution["method"]),
                    confidence=float(generic_grade_resolution["confidence"]),
                    status=(
                        "derived"
                        if str(generic_grade_resolution["method"]).startswith(
                            "ifc_type_"
                        )
                        else "automatic"
                    ),
                )
            fastener.validation_issues.append(
                ValidationIssue(
                    code="CWS-IFC-FASTENER-REVIEW",
                    message="IfcFastener kon niet deterministisch als lasobject worden bevestigd.",
                    severity="warning",
                    blocking=False,
                    entity_id=internal_id,
                    source=source.file_name,
                )
            )
            fastener_by_source[entity.entity_id] = fastener
            source_to_internal[entity.entity_id] = internal_id
            project.fasteners[internal_id] = fastener
            classification_counts[EntityCategory.FASTENER.value] += 1
            non_weld_fasteners += 1
        if index % 250 == 0:
            _progress(
                progress,
                0.63 + 0.09 * (index / max(1, len(generic_fastener_entities))),
                f"Las-/fastenerobjecten materialiseren ({index}/{len(generic_fastener_entities)})",
            )

    _progress(progress, 0.73, "Assembly-, spatial- en verbindingrelaties koppelen")
    assembly_relations = 0
    attached_parts = 0
    attached_fasteners = 0
    attached_welds = 0
    child_assemblies = 0
    for relation_index, (parent_source_id, children) in enumerate(
        indexes.aggregate_children.items()
    ):
        if relation_index % 100 == 0:
            _check_cancelled(cancel_check)
        assembly = assembly_by_source.get(parent_source_id)
        if assembly is None:
            continue
        assembly_relations += 1
        for child_source_id in children:
            child_assembly = assembly_by_source.get(child_source_id)
            if child_assembly is not None:
                if child_assembly.internal_id not in assembly.child_assembly_ids:
                    assembly.child_assembly_ids.append(child_assembly.internal_id)
                    child_assemblies += 1
                continue
            part = part_by_source.get(child_source_id)
            if part is not None:
                if part.internal_id not in assembly.part_ids:
                    assembly.part_ids.append(part.internal_id)
                    attached_parts += 1
                if assembly.internal_id not in part.assembly_ids:
                    part.assembly_ids.append(assembly.internal_id)
                    part.quantity_per_assembly[assembly.internal_id] = 1
                continue
            fastener = fastener_by_source.get(child_source_id)
            if fastener is not None:
                if fastener.internal_id not in assembly.fastener_ids:
                    assembly.fastener_ids.append(fastener.internal_id)
                    attached_fasteners += 1
                continue
            weld = weld_by_source.get(child_source_id)
            if weld is not None:
                if weld.internal_id not in assembly.weld_ids:
                    assembly.weld_ids.append(weld.internal_id)
                    attached_welds += 1
        if len(assembly.part_ids) == 1:
            # Only one structural child makes the main-part choice unambiguous.
            assembly.main_part_id = assembly.part_ids[0]
            assembly.properties["main_part_method"] = "single_structural_child_exact"
        elif assembly.part_ids:
            assembly.properties["main_part_method"] = "unresolved_multiple_structural_children"

    connected_relation_count = 0
    connected_realizing_count = 0
    for relation_index, (relating_source, related_source, realizing_sources) in enumerate(
        indexes.connections
    ):
        if relation_index % 100 == 0:
            _check_cancelled(cancel_check)
        connected_parts = [
            part_by_source[item].internal_id
            for item in (relating_source, related_source)
            if item in part_by_source
        ]
        if not connected_parts:
            continue
        connected_relation_count += 1
        for realizing_source in realizing_sources:
            fastener = fastener_by_source.get(realizing_source)
            if fastener is not None:
                for part_id in connected_parts:
                    if part_id not in fastener.connected_part_ids:
                        fastener.connected_part_ids.append(part_id)
                connected_realizing_count += 1
            weld = weld_by_source.get(realizing_source)
            if weld is not None:
                for part_id in connected_parts:
                    if part_id not in weld.connected_part_ids:
                        weld.connected_part_ids.append(part_id)
                connected_realizing_count += 1

    # Instance grouping is explicit metadata; individual occurrences retain
    # their own GlobalId and placement.
    for assembly in assembly_by_source.values():
        if assembly.assembly_mark:
            assembly.properties["assembly_mark_instance_count"] = mark_counts[
                assembly.assembly_mark
            ]
    for part in part_by_source.values():
        if part.part_position:
            part.properties["part_position_instance_count"] = part_position_counts[
                part.part_position
            ]

    spatial_tree = _build_spatial_tree(document, indexes, source_to_internal)
    project.settings.setdefault("spatial_trees", {})[source.source_id] = spatial_tree

    if placement_failures:
        result.warnings.append(
            f"{len(placement_failures)} IFC-placement(s) konden niet veilig worden opgebouwd; identiteit bleef behouden."
        )
        result.evidence["placement_failure_samples"] = placement_failures[:20]
    if missing_representation:
        result.warnings.append(
            f"{missing_representation} onderdeelobject(en) hebben geen bruikbare IfcProductDefinitionShape."
        )
    if non_weld_fasteners:
        result.warnings.append(
            f"{non_weld_fasteners} IfcFastener-object(en) zijn niet als las herkend en blijven ter controle als fastener staan."
        )

    # This phase proves semantic materialisation, not NC1 feature safety.
    blocking_reason = (
        "Externe IFC-geometrie en properties zijn semantisch behouden, maar "
        "productiefeatures/NC1-zijden zijn nog niet voor ieder onderdeel "
        "deterministisch gereconstrueerd en geroundtript."
    )
    result.blocking_reasons.append(blocking_reason)
    result.semantic_import_complete = True
    result.production_export_allowed = False
    result.imported_counts = {
        "assembly": len(assembly_by_source),
        "part": len(part_by_source),
        "fastener": len(fastener_by_source),
        "weld": len(weld_by_source),
        "total": (
            len(assembly_by_source)
            + len(part_by_source)
            + len(fastener_by_source)
            + len(weld_by_source)
        ),
    }
    result.classified_counts = dict(sorted(classification_counts.items()))
    result.relation_counts = {
        **{
            key: value
            for key, value in document.counts().items()
            if key.startswith("IFCREL")
        },
        "aggregate_relations_to_assemblies": assembly_relations,
        "child_assemblies": child_assemblies,
        "attached_parts": attached_parts,
        "attached_fasteners": attached_fasteners,
        "attached_welds": attached_welds,
        "connection_relations_with_parts": connected_relation_count,
        "connected_realizing_elements": connected_realizing_count,
        "spatial_containment_relations": len(indexes.spatial_containment),
    }
    result.mark_groups = {
        "assembly_marks": dict(mark_counts.most_common()),
        "part_positions": dict(part_position_counts.most_common()),
    }
    result.spatial_tree = spatial_tree
    result.geometry_summary = {
        "part_representations": len(part_by_source) - missing_representation,
        "parts_without_representation": missing_representation,
        "source_faceted_breps": len(document.ids_of_type("IFCFACETEDBREP")),
        "source_extruded_area_solids": len(document.ids_of_type("IFCEXTRUDEDAREASOLID")),
        "geometry_fingerprint_method": "ID-independent Part 21 representation-item Merkle hash",
        "production_features_resolved": False,
    }

    # Concrete evidence used by the supplied Tekla acceptance model.  This is
    # derived from the materialised graph, not by searching raw text.
    mlo4_assemblies = [
        item for item in assembly_by_source.values() if item.assembly_mark == "MLO4"
    ]
    lo4_parts = [item for item in part_by_source.values() if item.part_position == "LO4"]
    lo4_links = [
        {
            "assembly_internal_id": assembly.internal_id,
            "assembly_global_id": assembly.source_identity.global_id,
            "part_internal_ids": [
                part_id
                for part_id in assembly.part_ids
                if project.parts.get(part_id)
                and project.parts[part_id].part_position == "LO4"
            ],
        }
        for assembly in mlo4_assemblies
    ]
    bolt14 = [
        item
        for item in fastener_by_source.values()
        if abs(item.diameter_mm - 14.0) <= 1e-9
        or abs(item.hole_diameter_mm - 14.0) <= 1e-9
    ]
    result.evidence.update(
        {
            "schema": document.schema,
            "units": {
                "length_to_mm": units.length_to_mm,
                "area_to_m2": units.area_to_m2,
                "volume_to_m3": units.volume_to_m3,
                "mass_to_kg": units.mass_to_kg,
            },
            "MLO4_assembly_instances": len(mlo4_assemblies),
            "LO4_part_instances": len(lo4_parts),
            "MLO4_LO4_links": lo4_links,
            "LO4_profiles": sorted({item.profile for item in lo4_parts if item.profile}),
            "LO4_materials": sorted({item.material for item in lo4_parts if item.material}),
            "LO4_lengths_mm": sorted({round(item.length_mm, 9) for item in lo4_parts}),
            "MLO4_weights_kg": sorted(
                {round(item.total_weight_kg, 9) for item in mlo4_assemblies}
            ),
            "diameter_14_fastener_count": len(bolt14),
            "repeated_assembly_marks": {
                key: value
                for key, value in mark_counts.items()
                if value > 1
            },
        }
    )

    source.metadata["semantic_import"] = result.to_dict()
    source.metadata["semantic_import_version"] = result.importer_version
    source.metadata["semantic_imported_at"] = utc_now_iso()
    source.metadata["materialised_entity_count"] = result.entity_counts["total_materialised"]
    source.metadata["production_block_reason"] = blocking_reason
    source.warnings = list(dict.fromkeys([*source.warnings, *result.warnings]))

    _check_cancelled(cancel_check)
    result.completed_at = utc_now_iso()
    result.elapsed_seconds = round(time.perf_counter() - started, 6)
    source.metadata["semantic_import"] = result.to_dict()
    project.audit(
        "source.ifc_semantic_imported",
        user=user,
        entity_id=source.source_id,
        after_hash=source.sha256,
        details={
            "imported_counts": result.imported_counts,
            "relation_counts": result.relation_counts,
            "elapsed_seconds": result.elapsed_seconds,
            "production_export_allowed": False,
        },
    )
    _progress(progress, 1.0, "IFC semantische import gereed")
    document.release_caches()
    return result.normalise()


class IFCSemanticProjectImporter:
    """Protocol adapter used by the shared transactional project service."""

    importer_version = IFC_IMPORTER_VERSION

    def import_source(
        self,
        project: ProjectModel,
        source: SourceFileRecord,
        source_path: Path,
        *,
        user: str,
        progress: ProgressCallback | None = None,
        cancel_check: SemanticCancelCheck | None = None,
    ) -> SemanticImportResult:
        result = import_ifc_project(
            project,
            source,
            source_path,
            user=user,
            progress=progress,
            cancel_check=cancel_check,
        )
        result.normalise()
        # Preserve raw IFC relationship entity counts alongside the derived
        # relationship summaries.  The acceptance baseline intentionally
        # checks both: raw source semantics and materialised relationships.
        for type_name, count in result.source_class_counts.items():
            if type_name.startswith("IFCREL"):
                result.relationship_counts.setdefault(type_name, int(count))
        result.relation_counts = dict(result.relationship_counts)

        # Canonical evidence names used by the acceptance tests and reports.
        evidence = result.evidence
        evidence.setdefault(
            "MLO4_assembly_count",
            int(evidence.get("MLO4_assembly_instances", 0) or 0),
        )
        evidence.setdefault(
            "bolt_or_hole_diameter_14_count",
            int(evidence.get("diameter_14_fastener_count", 0) or 0),
        )
        lo4_parts = [
            {
                "internal_id": part.internal_id,
                "source_entity_id": part.source_identity.source_entity_id,
                "profile": part.profile,
                "material": part.material,
                "length_mm": part.length_mm,
                "mass_each_kg": part.mass_each_kg,
                "assembly_ids": list(part.assembly_ids),
                "geometry_hash": part.geometry_hash,
                "manufacturing_hash": part.manufacturing_hash,
            }
            for part in project.parts.values()
            if part.source_identity.source_file_id == source.source_id
            and part.part_position == "LO4"
        ]
        evidence.setdefault("LO4_parts", lo4_parts)
        evidence.setdefault(
            "connected_weld_count",
            sum(
                bool(weld.connected_part_ids)
                for weld in project.welds.values()
                if weld.source_identity.source_file_id == source.source_id
            ),
        )
        repeated = dict(evidence.get("repeated_assembly_marks") or {})
        evidence.setdefault(
            "repeated_marks",
            {key: int(repeated.get(key, 0) or 0) for key in ("LA1", "A1", "MP1", "MP2")},
        )
        return result.normalise()


__all__ = [
    "IFC_PART_TYPES",
    "IFC_PRODUCT_TYPES",
    "IFC_SPATIAL_TYPES",
    "IfcPlacementResolver",
    "IfcUnits",
    "IFCSemanticProjectImporter",
    "import_ifc_project",
]
