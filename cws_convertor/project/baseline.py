"""Dependency-light IFC/STEP baseline inspection for project imports.

This module is the deterministic intake pass that runs before the semantic
importer. It records schema, entity counts, product/assembly evidence, source
hashes and the safest import strategy. The result is persisted in the project
file, remains available as audit evidence and is re-verified before semantic
materialisation starts.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
import hashlib
import json
import math
import re
from typing import Any, Iterator

from cws_convertor.product import APP_NAME
from .model import ImportStrategy

ANALYSIS_VERSION = "1.0"
_ENTITY_RE = re.compile(r"^\s*#(\d+)\s*=\s*([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*$", re.I | re.S)
_STRING_RE = re.compile(r"'((?:''|[^'])*)'")
_TYPED_VALUE_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*\((.*)\)$", re.I | re.S)
_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$")


class BaselineInspectionError(ValueError):
    pass


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def iter_p21_statements(path: str | Path, chunk_size: int = 256 * 1024) -> Iterator[str]:
    """Yield ISO-10303-21 statements split on semicolons outside strings."""

    source = Path(path)
    buffer: list[str] = []
    in_string = False
    pending_quote = False
    with source.open("r", encoding="utf-8", errors="replace", newline="") as stream:
        while chunk := stream.read(chunk_size):
            index = 0
            while index < len(chunk):
                char = chunk[index]
                if pending_quote:
                    # A quote at the previous chunk boundary is doubled when
                    # the current first character is also a quote.
                    if char == "'":
                        buffer.append(char)
                        pending_quote = False
                        index += 1
                        continue
                    in_string = not in_string
                    pending_quote = False
                if char == "'":
                    buffer.append(char)
                    if index + 1 < len(chunk):
                        if chunk[index + 1] == "'":
                            buffer.append("'")
                            index += 2
                            continue
                        in_string = not in_string
                    else:
                        pending_quote = True
                    index += 1
                    continue
                if char == ";" and not in_string:
                    statement = "".join(buffer).strip()
                    buffer.clear()
                    if statement:
                        yield statement
                else:
                    buffer.append(char)
                index += 1
    if pending_quote:
        in_string = not in_string
    remainder = "".join(buffer).strip()
    if remainder:
        yield remainder


def split_p21_args(text: str) -> list[str]:
    args: list[str] = []
    buffer: list[str] = []
    depth = 0
    in_string = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "'":
            buffer.append(char)
            if in_string and index + 1 < len(text) and text[index + 1] == "'":
                buffer.append("'")
                index += 2
                continue
            in_string = not in_string
            index += 1
            continue
        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif char == "," and depth == 0:
                args.append("".join(buffer).strip())
                buffer.clear()
                index += 1
                continue
        buffer.append(char)
        index += 1
    args.append("".join(buffer).strip())
    return args


def _unescape_step_string(value: str) -> str:
    return value.replace("''", "'")


def parse_p21_value(text: str) -> Any:
    value = text.strip()
    if value in {"$", "*", ""}:
        return None
    if value.startswith("'") and value.endswith("'"):
        return _unescape_step_string(value[1:-1])
    if value.startswith("#") and value[1:].isdigit():
        return {"ref": int(value[1:])}
    if value.startswith(".") and value.endswith("."):
        return value.strip(".")
    if _NUMBER_RE.fullmatch(value):
        number = float(value)
        return int(number) if number.is_integer() and "." not in value and "E" not in value.upper() else number
    typed = _TYPED_VALUE_RE.match(value)
    if typed:
        name = typed.group(1).upper()
        inner = typed.group(2).strip()
        inner_args = split_p21_args(inner)
        parsed: Any
        if len(inner_args) == 1:
            parsed = parse_p21_value(inner_args[0])
        else:
            parsed = [parse_p21_value(item) for item in inner_args]
        return {"type": name, "value": parsed}
    if value.startswith("(") and value.endswith(")"):
        return [parse_p21_value(item) for item in split_p21_args(value[1:-1])]
    return value


def _typed_scalar(value: Any) -> Any:
    while isinstance(value, dict) and "type" in value and "value" in value:
        value = value["value"]
    return value


def _string_arg(args: list[str], index: int) -> str:
    if index >= len(args):
        return ""
    parsed = _typed_scalar(parse_p21_value(args[index]))
    return str(parsed) if parsed is not None else ""


def _number_arg(args: list[str], index: int) -> float | None:
    if index >= len(args):
        return None
    parsed = _typed_scalar(parse_p21_value(args[index]))
    if isinstance(parsed, (int, float)) and math.isfinite(float(parsed)):
        return float(parsed)
    return None


def _extract_schema(statement: str) -> str:
    match = re.search(r"FILE_SCHEMA\s*\(\s*\((.*)\)\s*\)", statement, re.I | re.S)
    if not match:
        return ""
    strings = [_unescape_step_string(item) for item in _STRING_RE.findall(match.group(1))]
    return ", ".join(strings)


def _extract_file_name(statement: str) -> dict[str, Any]:
    match = re.search(r"FILE_NAME\s*\((.*)\)", statement, re.I | re.S)
    if not match:
        return {}
    args = split_p21_args(match.group(1))
    return {
        "name": _string_arg(args, 0),
        "timestamp": _string_arg(args, 1),
        "preprocessor_version": _string_arg(args, 4),
        "originating_system": _string_arg(args, 5),
        "authorization": _string_arg(args, 6),
    }


@dataclass
class BaselineAnalysis:
    analysis_version: str = ANALYSIS_VERSION
    path: str = ""
    file_name: str = ""
    source_format: str = ""
    sha256: str = ""
    size_bytes: int = 0
    schema: str = ""
    header: dict[str, Any] = field(default_factory=dict)
    entity_counts: dict[str, int] = field(default_factory=dict)
    product_records: list[dict[str, Any]] = field(default_factory=list)
    product_count: int = 0
    solid_count: int = 0
    assembly_relation_count: int = 0
    import_strategy: ImportStrategy = ImportStrategy.NOT_ANALYSED
    strategy_reason: str = ""
    class_summary: dict[str, int] = field(default_factory=dict)
    mark_frequencies: dict[str, int] = field(default_factory=dict)
    property_samples: dict[str, list[Any]] = field(default_factory=dict)
    reference_checks: dict[str, Any] = field(default_factory=dict)
    geometry_metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["import_strategy"] = self.import_strategy.value
        return data

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BaselineAnalysis":
        raw = dict(value or {})
        raw["import_strategy"] = ImportStrategy(
            raw.get("import_strategy", ImportStrategy.NOT_ANALYSED.value)
        )
        return cls(**{key: raw[key] for key in cls.__dataclass_fields__ if key in raw})


def _inspect_ifc(path: Path) -> BaselineAnalysis:
    counts: Counter[str] = Counter()
    mark_frequencies: Counter[str] = Counter()
    property_values: dict[str, list[Any]] = defaultdict(list)
    product_records: list[dict[str, Any]] = []
    schema = ""
    header: dict[str, Any] = {}

    product_types = {
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
    tagged_types = product_types - {"IFCFASTENER"}

    for statement in iter_p21_statements(path):
        upper = statement.lstrip().upper()
        if upper.startswith("FILE_SCHEMA"):
            schema = _extract_schema(statement)
            continue
        if upper.startswith("FILE_NAME"):
            header.update(_extract_file_name(statement))
            continue
        match = _ENTITY_RE.match(statement)
        if not match:
            continue
        entity_id, entity_type, arg_text = int(match.group(1)), match.group(2).upper(), match.group(3)
        counts[entity_type] += 1
        args = split_p21_args(arg_text)

        if entity_type in product_types:
            record = {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "global_id": _string_arg(args, 0),
                "name": _string_arg(args, 2),
                "description": _string_arg(args, 3),
                "object_type": _string_arg(args, 4),
                "tag": _string_arg(args, 7),
            }
            if entity_type == "IFCMECHANICALFASTENER":
                record["nominal_diameter_mm"] = _number_arg(args, 8)
                record["nominal_length_mm"] = _number_arg(args, 9)
            if len(product_records) < 250:
                product_records.append(record)
            if entity_type in tagged_types and record["tag"]:
                mark_frequencies[record["tag"]] += 1

        if entity_type == "IFCPROPERTYSINGLEVALUE":
            name = _string_arg(args, 0)
            parsed = _typed_scalar(parse_p21_value(args[2])) if len(args) > 2 else None
            if name and parsed is not None and len(property_values[name]) < 50:
                property_values[name].append(parsed)

    class_summary = {
        "assemblies": counts["IFCELEMENTASSEMBLY"],
        "plates": counts["IFCPLATE"],
        "beams": counts["IFCBEAM"],
        "columns": counts["IFCCOLUMN"],
        "members": counts["IFCMEMBER"],
        "mechanical_fasteners": counts["IFCMECHANICALFASTENER"],
        "weld_fastener_objects": counts["IFCFASTENER"],
        "footings": counts["IFCFOOTING"],
        "building_element_proxies": counts["IFCBUILDINGELEMENTPROXY"],
        "slabs": counts["IFCSLAB"],
    }
    semantic_tree = counts["IFCELEMENTASSEMBLY"] > 0 and counts["IFCRELAGGREGATES"] > 0
    strategy = ImportStrategy.SEMANTIC_STRUCTURE if semantic_tree else ImportStrategy.SEPARATE_SOLIDS
    reason = (
        "IFC bevat IfcElementAssembly en IfcRelAggregates; semantische productstructuur heeft prioriteit."
        if semantic_tree
        else "IFC bevat geen aantoonbare assemblyboom; importeer producten afzonderlijk en laat relaties controleren."
    )

    def values(name: str) -> list[Any]:
        return list(property_values.get(name, []))

    all_text = json.dumps(
        {"marks": dict(mark_frequencies), "properties": property_values},
        ensure_ascii=False,
    ).upper()
    reference_checks = {
        "MLO4_found": "MLO4" in all_text,
        "LO4_found": "LO4" in all_text,
        "STRIP5*120_found": any(
            record.get("description") == "STRIP5*120" or record.get("tag") == "STRIP5*120"
            for record in product_records
        ) or "STRIP5*120" in all_text,
        "S235JR_found": "S235JR" in all_text,
        "length_160_mm_found": any(abs(float(item) - 160.0) <= 1e-9 for item in values("Length") if isinstance(item, (int, float))),
        "assembly_weight_0_6_kg_found": any(abs(float(item) - 0.6) <= 0.05 for item in values("Assembly/Cast unit weight") if isinstance(item, (int, float))),
        "bolt_or_hole_diameter_14_mm_found": any(
            abs(float(item) - 14.0) <= 1e-9
            for name in ("Bolt size", "Bolt hole diameter", "Washer diameter")
            for item in values(name)
            if isinstance(item, (int, float))
        ) or any(
            abs(float(record.get("nominal_diameter_mm") or -1.0) - 14.0) <= 1e-9
            for record in product_records
            if record.get("entity_type") == "IFCMECHANICALFASTENER"
        ),
        "repeated_mark_counts": {
            mark: int(mark_frequencies.get(mark, 0)) for mark in ("LA1", "A1", "MP1", "MP2")
        },
    }

    warnings: list[str] = []
    if not semantic_tree:
        warnings.append("Geen betrouwbare IFC-assemblyboom gevonden; projectimport vereist extra review.")
    if counts["IFCFACETEDBREP"]:
        warnings.append(
            f"IFC bevat {counts['IFCFACETEDBREP']} gefacetteerde BREP-objecten; productiefeatures mogen daaruit niet blind worden afgeleid."
        )

    return BaselineAnalysis(
        path=str(path),
        file_name=path.name,
        source_format="IFC",
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        schema=schema,
        header=header,
        entity_counts=dict(sorted(counts.items())),
        product_records=product_records,
        product_count=sum(counts[item] for item in product_types),
        solid_count=counts["IFCEXTRUDEDAREASOLID"] + counts["IFCFACETEDBREP"],
        assembly_relation_count=counts["IFCRELAGGREGATES"],
        import_strategy=strategy,
        strategy_reason=reason,
        class_summary=class_summary,
        mark_frequencies=dict(mark_frequencies.most_common()),
        property_samples={key: value for key, value in sorted(property_values.items())},
        reference_checks=reference_checks,
        warnings=warnings,
    )


def _step_geometry_metrics(path: Path) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    try:
        import cadquery as cq

        imported = cq.importers.importStep(str(path))
        shape = imported.val()
        solids = list(shape.Solids())
        box = shape.BoundingBox()
        metrics = {
            "cadquery_loaded": True,
            "solid_count": len(solids),
            "volume_mm3": float(shape.Volume()),
            "area_mm2": float(shape.Area()),
            "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
            "valid": bool(shape.isValid()),
        }
        return metrics, warnings
    except Exception as exc:
        warnings.append(f"CAD-geometrienulmeting niet uitgevoerd: {exc}")
        return {"cadquery_loaded": False}, warnings


def _inspect_step(path: Path, *, include_geometry: bool) -> BaselineAnalysis:
    counts: Counter[str] = Counter()
    products: list[dict[str, Any]] = []
    schema = ""
    header: dict[str, Any] = {}
    for statement in iter_p21_statements(path):
        upper = statement.lstrip().upper()
        if upper.startswith("FILE_SCHEMA"):
            schema = _extract_schema(statement)
            continue
        if upper.startswith("FILE_NAME"):
            header.update(_extract_file_name(statement))
            continue
        match = _ENTITY_RE.match(statement)
        if not match:
            continue
        entity_id, entity_type, arg_text = int(match.group(1)), match.group(2).upper(), match.group(3)
        counts[entity_type] += 1
        if entity_type == "PRODUCT":
            args = split_p21_args(arg_text)
            products.append(
                {
                    "entity_id": entity_id,
                    "product_id": _string_arg(args, 0),
                    "name": _string_arg(args, 1),
                    "description": _string_arg(args, 2),
                }
            )

    solid_count = (
        counts["MANIFOLD_SOLID_BREP"]
        + counts["BREP_WITH_VOIDS"]
        + counts["FACETED_BREP"]
        + counts["SHELL_BASED_SURFACE_MODEL"]
    )
    assembly_relations = (
        counts["NEXT_ASSEMBLY_USAGE_OCCURRENCE"]
        + counts["ASSEMBLY_COMPONENT_USAGE"]
        + counts["PRODUCT_DEFINITION_USAGE"]
    )
    product_count = counts["PRODUCT"]
    if assembly_relations > 0 and product_count > 1:
        strategy = ImportStrategy.SEMANTIC_STRUCTURE
        reason = "STEP bevat meerdere producten met assembly usage-relaties; behoud AP242-productstructuur."
    elif solid_count >= 1:
        strategy = ImportStrategy.SEPARATE_SOLIDS
        if product_count == 1 and solid_count == 1:
            reason = "STEP bevat één productrecord en één BREP-solid; importeer als één onderdeel en splits niet op bestandsnaam."
        else:
            reason = "STEP bevat losse solids zonder betrouwbare assemblyboom; groepeer placement-onafhankelijk na geometrische import."
    else:
        strategy = ImportStrategy.FUSED_REVIEW
        reason = "STEP bevat geen eenduidige product-/solidstructuur; veilige visuele review is verplicht."

    warnings: list[str] = []
    product_names = [str(item.get("name") or item.get("product_id") or "") for item in products]
    if product_count == 1 and solid_count == 1 and any(re.match(r"^\s*\d+\s*[xX]\b", name) for name in product_names):
        warnings.append(
            "De productnaam suggereert mogelijk meerdere stuks, maar de bron bevat één product en één solid; niet automatisch opsplitsen."
        )
    if assembly_relations == 0:
        warnings.append("Geen STEP-assembly usage-relaties gevonden.")

    geometry_metrics: dict[str, Any] = {}
    if include_geometry:
        geometry_metrics, geometry_warnings = _step_geometry_metrics(path)
        warnings.extend(geometry_warnings)
        if geometry_metrics.get("cadquery_loaded") and int(geometry_metrics.get("solid_count", 0)) != solid_count:
            warnings.append(
                "Topologische solidtelling uit CAD-import wijkt af van de P21-entiteitstelling; semantische importer moet dit verklaren."
            )

    return BaselineAnalysis(
        path=str(path),
        file_name=path.name,
        source_format="STEP",
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        schema=schema,
        header=header,
        entity_counts=dict(sorted(counts.items())),
        product_records=products,
        product_count=product_count,
        solid_count=solid_count,
        assembly_relation_count=assembly_relations,
        import_strategy=strategy,
        strategy_reason=reason,
        class_summary={
            "products": product_count,
            "product_definitions": counts["PRODUCT_DEFINITION"],
            "brep_solids": solid_count,
            "assembly_relations": assembly_relations,
            "advanced_faces": counts["ADVANCED_FACE"],
            "circles": counts["CIRCLE"],
            "cylindrical_surfaces": counts["CYLINDRICAL_SURFACE"],
        },
        reference_checks={
            "single_product_record": product_count == 1,
            "single_brep_solid": solid_count == 1,
            "no_assembly_relations": assembly_relations == 0,
            "product_names": product_names,
        },
        geometry_metrics=geometry_metrics,
        warnings=warnings,
    )


def inspect_model_file(path: str | Path, *, include_geometry: bool = False) -> BaselineAnalysis:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise BaselineInspectionError(f"Modelbestand bestaat niet: {source}")
    suffix = source.suffix.lower()
    if suffix == ".ifc":
        return _inspect_ifc(source)
    if suffix in {".step", ".stp"}:
        return _inspect_step(source, include_geometry=include_geometry)
    raise BaselineInspectionError(f"Niet-ondersteund projectbronformaat: {source.suffix}")


def write_baseline_report(
    analyses: list[BaselineAnalysis],
    output_path: str | Path,
    *,
    title: str = f"{APP_NAME} projectimport-nulmeting",
) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "title": title,
        "analysis_version": ANALYSIS_VERSION,
        "files": [item.to_dict() for item in analyses],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return target


__all__ = [
    "ANALYSIS_VERSION",
    "BaselineAnalysis",
    "BaselineInspectionError",
    "inspect_model_file",
    "iter_p21_statements",
    "parse_p21_value",
    "sha256_file",
    "split_p21_args",
    "write_baseline_report",
]
