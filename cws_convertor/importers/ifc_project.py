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
    object_type_names: dict[int, str]
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
    if entity_id is None:
        return []
    active = active or set()
    if entity_id in active:
        return []
    entity = document.get(entity_id)
    if entity is None:
        return []
    active.add(entity_id)
    names: list[str] = []
    if entity.type_name == "IFCMATERIAL":
        names.append(entity.string(0))
    elif entity.type_name == "IFCMATERIALLIST":
        for ref in entity.refs(0):
            names.extend(_resolve_material_names(document, ref, active=active))
    elif entity.type_name in {"IFCMATERIALLAYER", "IFCMATERIALPROFILE"}:
        names.extend(_resolve_material_names(document, entity.ref(0), active=active))
    elif entity.type_name in {"IFCMATERIALLAYERSETUSAGE", "IFCMATERIALPROFILESETUSAGE"}:
        names.extend(_resolve_material_names(document, entity.ref(0), active=active))
    elif entity.type_name in {"IFCMATERIALLAYERSET", "IFCMATERIALPROFILESET"}:
        for ref in entity.refs(0):
            names.extend(_resolve_material_names(document, ref, active=active))
        if entity.string(1):
            names.append(entity.string(1))
    else:
        for ref in entity.references:
            target = document.get(ref)
            if target and target.type_name.startswith("IFCMATERIAL"):
                names.extend(_resolve_material_names(document, ref, active=active))
    active.remove(entity_id)
    result: list[str] = []
    seen: set[str] = set()
    for name in names:
        clean = str(name or "").strip()
        if clean and clean.casefold() not in seen:
            seen.add(clean.casefold())
            result.append(clean)
    return result


def _build_material_index(document: P21Document) -> dict[int, list[str]]:
    result: dict[int, list[str]] = defaultdict(list)
    for relation in document.iter_type("IFCRELASSOCIATESMATERIAL"):
        material_id = relation.ref(5)
        names = _resolve_material_names(document, material_id)
        if not names:
            continue
        for object_id in relation.refs(4):
            for name in names:
                if name not in result[object_id]:
                    result[object_id].append(name)
    return dict(result)


def _build_type_index(document: P21Document) -> dict[int, str]:
    result: dict[int, str] = {}
    for relation in document.iter_type("IFCRELDEFINESBYTYPE"):
        type_id = relation.ref(5)
        type_entity = document.get(type_id)
        if type_entity is None:
            continue
        type_name = _first_nonempty(type_entity.string(2), type_entity.string(0))
        for object_id in relation.refs(4):
            if type_name:
                result[object_id] = type_name
    return result


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
    children, parents, spatial, element_parent, connections = _build_relation_indexes(
        document
    )
    return IfcIndexes(
        property_values=property_values,
        property_sets=property_sets,
        object_property_sets=object_property_sets,
        object_materials=_build_material_index(document),
        object_type_names=_build_type_index(document),
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
            target[property_name] = value
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


def _representation_summary(document: P21Document, representation_id: int | None) -> dict[str, Any]:
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
        "extrusion_depths_source_units": extrusion_depths,
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
) -> FieldProvenance:
    return FieldProvenance(
        source_file_id=source.source_id,
        source_entity_id=str(entity_id),
        source_path=source_path,
        method=method,
        confidence=confidence,
        status="automatic",
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


def _classification_for_part(entity_type: str, material: str) -> str:
    if entity_type in {"IFCFOOTING", "IFCSLAB"}:
        return EntityCategory.NON_STEEL.value
    if entity_type == "IFCBUILDINGELEMENTPROXY":
        return EntityCategory.UNKNOWN.value
    if material and any(token in material.upper() for token in ("CONCRETE", "BETON", "TIMBER", "WOOD", "HOUT")):
        return EntityCategory.NON_STEEL.value
    return EntityCategory.MAKE_PART.value


def _entity_property_payload(
    entity: P21Entity,
    nested_properties: dict[str, dict[str, Any]],
    material_names: list[str],
    type_name: str,
) -> dict[str, Any]:
    return {
        "ifc_entity_type": entity.type_name,
        "ifc_global_id": entity.string(0),
        "ifc_name": entity.string(2),
        "ifc_description": entity.string(3),
        "ifc_object_type": entity.string(4),
        "ifc_tag": entity.string(7),
        "ifc_type_name": type_name,
        "ifc_materials": material_names,
        "ifc_property_sets": nested_properties,
    }


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
            ("Part position number", "Part Position", "Position", "Mark"),
        )
        assembly_value, _assembly_path, _assembly_source = _flattened_value(
            flattened,
            ("Assembly/Cast unit position number", "Assembly/Cast unit Mark", "Assembly Mark"),
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
        material_property, material_path, material_source = _flattened_value(
            flattened,
            ("MATERIAL", "Material", "Material grade", "Grade"),
        )
        associated_material = next(
            (
                item
                for item in material_names
                if item and item.casefold() not in {"undefined", "notdefined"}
            ),
            "",
        )
        material = _clean_material(_first_nonempty(material_property, associated_material))
        profile_property, profile_path, profile_source = _flattened_value(
            flattened,
            ("PROFILE", "Profile", "Profile name", "Section", "Cross section"),
        )
        type_name = indexes.object_type_names.get(entity.entity_id, "")
        representation = _representation_summary(document, entity.ref(6))
        representation["source_locator"] = build_ifc_source_locator(
            source,
            source_entity_id=identity.source_entity_id,
            global_id=identity.global_id,
            representation_id=str(representation.get("source_representation_id") or ""),
            source_geometry_hash=str(representation.get("source_geometry_hash") or ""),
        )
        profile = _first_nonempty(
            profile_property,
            entity.string(3),
            type_name,
            *(representation.get("profile_names") or []),
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
                entity, nested, material_names, type_name
            ),
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            part_position=part_position,
            quantity_total=1,
            part_type=entity.type_name.removeprefix("IFC").lower(),
            profile=profile,
            profile_type=infer_profile_type(profile, entity.type_name),
            material=material,
            material_grade=material,
            length_mm=_float(length),
            mass_each_kg=_float(weight),
            surface_area_each_m2=_float(area),
            geometry_descriptor=representation,
            coating=str(coating or ""),
            nc1_eligible=False,
            export_status="review_required",
        )
        prepare_exact_imported_part(part)
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
            part.field_provenance["profile"] = _provenance(
                source,
                profile_source or entity.entity_id,
                profile_path or (
                    "IfcProduct.Description" if entity.string(3) else "IfcType.Name"
                ),
            )
        if material:
            part.field_provenance["material"] = _provenance(
                source,
                material_source or entity.entity_id,
                material_path or "IfcRelAssociatesMaterial",
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
        standard, _standard_path, _standard_source = _flattened_value(
            flattened,
            ("Bolt standard", "Standard"),
        )
        grade, _grade_path, _grade_source = _flattened_value(
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
        identity = _source_identity(source, entity)
        internal_id = project.stable_entity_id("fastener", identity)
        representation = _representation_summary(document, entity.ref(6))
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
            ),
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            fastener_type=_first_nonempty(entity.string(2), "mechanical_fastener"),
            diameter_mm=_float(diameter),
            grade=str(grade or ""),
            length_mm=_float(length),
            standard=str(standard or ""),
            quantity=max(1, _int(quantity, 1)),
            hole_diameter_mm=_float(hole_diameter),
            slot={"x_mm": _float(slot_x), "y_mm": _float(slot_y)},
            geometry_descriptor=representation,
        )
        fastener.field_provenance["diameter_mm"] = _provenance(
            source, diameter_source, diameter_path
        )
        fastener.field_provenance["length_mm"] = _provenance(
            source, length_source, length_path
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
        representation = _representation_summary(document, entity.ref(6))
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
                ),
                confidence=0.8,
                status=ReviewStatus.REVIEW_REQUIRED.value,
                fastener_type="ifc_fastener_unclassified",
                geometry_descriptor=representation,
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
