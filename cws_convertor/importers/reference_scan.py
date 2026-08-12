"""Safe text-level intake scanner for IFC/STEP regression fixtures.

This module does **not** claim to be the semantic importer from phase 2. It fixes
source facts before that importer is built: schemas, entity counts, product
records, solid counts and selected search anchors. The scanner never invents an
assembly tree and never splits a one-product/one-solid STEP file based on its
file name.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any


ENTITY_RE = re.compile(r"^\s*#\d+\s*=\s*([A-Z0-9_]+)\s*\(", re.IGNORECASE)
STEP_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)", re.IGNORECASE | re.DOTALL)
STEP_PRODUCT_RE = re.compile(
    r"#\d+\s*=\s*PRODUCT\s*\(\s*'((?:''|[^'])*)'\s*,\s*'((?:''|[^'])*)'",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class IFCReferenceScan:
    path: str
    file_name: str
    sha256: str
    size_bytes: int
    schema: str
    entity_count: int
    entity_type_count: int
    entity_counts: dict[str, int]
    token_hits: dict[str, int]
    elapsed_seconds: float
    import_strategy: str = "semantic_structure"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class STEPReferenceScan:
    path: str
    file_name: str
    sha256: str
    size_bytes: int
    schema: str
    entity_count: int
    entity_type_count: int
    entity_counts: dict[str, int]
    product_names: list[str]
    product_count: int
    product_definition_count: int
    assembly_relationship_count: int
    solid_count: int
    advanced_brep_representation_count: int
    elapsed_seconds: float
    import_strategy: str
    auto_split_allowed: bool
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceValidationResult:
    passed: bool
    checks: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="latin-1", errors="replace")


def _entity_counts(text: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in text.splitlines():
        match = ENTITY_RE.match(line)
        if match:
            counts[match.group(1).upper()] += 1
    return counts


def _extract_schema(text: str) -> str:
    match = STEP_SCHEMA_RE.search(text)
    if not match:
        return ""
    values = re.findall(r"'((?:''|[^'])*)'", match.group(1))
    return " | ".join(value.replace("''", "'") for value in values)


def scan_ifc(path: str | Path, *, tokens: list[str] | None = None) -> IFCReferenceScan:
    source = Path(path)
    started = time.perf_counter()
    text = _read_text(source)
    counts = _entity_counts(text)
    upper = text.upper()
    requested = tokens or ["MLO4", "LO4", "STRIP5*120", "S235JR"]
    schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'", text, re.IGNORECASE)
    return IFCReferenceScan(
        path=str(source),
        file_name=source.name,
        sha256=_sha256(source),
        size_bytes=source.stat().st_size,
        schema=schema_match.group(1) if schema_match else "",
        entity_count=sum(counts.values()),
        entity_type_count=len(counts),
        entity_counts=dict(sorted(counts.items())),
        token_hits={token: upper.count(token.upper()) for token in requested},
        elapsed_seconds=time.perf_counter() - started,
    )


def scan_step(path: str | Path) -> STEPReferenceScan:
    source = Path(path)
    started = time.perf_counter()
    text = _read_text(source)
    counts = _entity_counts(text)
    product_names = [
        match.group(1).replace("''", "'")
        for match in STEP_PRODUCT_RE.finditer(text)
    ]
    solid_count = (
        counts.get("MANIFOLD_SOLID_BREP", 0)
        + counts.get("BREP_WITH_VOIDS", 0)
        + counts.get("FACETED_BREP", 0)
    )
    assembly_relationship_count = (
        counts.get("NEXT_ASSEMBLY_USAGE_OCCURRENCE", 0)
        + counts.get("ASSEMBLY_COMPONENT_USAGE", 0)
        + counts.get("PRODUCT_DEFINITION_RELATIONSHIP", 0)
    )
    if assembly_relationship_count > 0:
        strategy = "semantic_structure"
        auto_split = True
        notes = ["Bron bevat assembly-/occurrencerelaties; behoud de semantische boom."]
    elif solid_count > 1:
        strategy = "loose_solids"
        auto_split = True
        notes = ["Geen assemblyboom; afzonderlijke topologische solids mogen als voorstellen worden geïmporteerd."]
    elif solid_count == 1:
        strategy = "single_product"
        auto_split = False
        notes = [
            "Eén product en één solid: niet automatisch splitsen op bestandsnaam of vermoed aantal."
        ]
    else:
        strategy = "ambiguous_geometry"
        auto_split = False
        notes = ["Geen betrouwbare solid-/assemblybasis; handmatige review vereist."]
    return STEPReferenceScan(
        path=str(source),
        file_name=source.name,
        sha256=_sha256(source),
        size_bytes=source.stat().st_size,
        schema=_extract_schema(text),
        entity_count=sum(counts.values()),
        entity_type_count=len(counts),
        entity_counts=dict(sorted(counts.items())),
        product_names=product_names,
        product_count=counts.get("PRODUCT", 0),
        product_definition_count=counts.get("PRODUCT_DEFINITION", 0),
        assembly_relationship_count=assembly_relationship_count,
        solid_count=solid_count,
        advanced_brep_representation_count=counts.get(
            "ADVANCED_BREP_SHAPE_REPRESENTATION", 0
        ),
        elapsed_seconds=time.perf_counter() - started,
        import_strategy=strategy,
        auto_split_allowed=auto_split,
        notes=notes,
    )


def validate_ifc_reference(scan: IFCReferenceScan) -> ReferenceValidationResult:
    expected = {
        "IFCELEMENTASSEMBLY": 353,
        "IFCPLATE": 1293,
        "IFCBEAM": 707,
        "IFCCOLUMN": 369,
        "IFCMECHANICALFASTENER": 723,
        "IFCFASTENER": 2654,
        "IFCFOOTING": 38,
        "IFCBUILDINGELEMENTPROXY": 19,
        "IFCSLAB": 3,
    }
    checks: list[dict[str, Any]] = []
    for key, value in expected.items():
        actual = int(scan.entity_counts.get(key, 0))
        checks.append(
            {
                "check": f"entity_count:{key}",
                "expected": value,
                "actual": actual,
                "passed": actual == value,
            }
        )
    for token in ("MLO4", "LO4", "STRIP5*120", "S235JR"):
        actual = int(scan.token_hits.get(token, 0))
        checks.append(
            {
                "check": f"search_anchor:{token}",
                "expected": ">0",
                "actual": actual,
                "passed": actual > 0,
            }
        )
    schema_ok = scan.schema.upper().startswith("IFC2X3") or scan.schema.upper().startswith("IFC4")
    checks.append(
        {
            "check": "ifc_schema",
            "expected": "IFC2X3 or IFC4",
            "actual": scan.schema,
            "passed": schema_ok,
        }
    )
    return ReferenceValidationResult(
        passed=all(item["passed"] for item in checks),
        checks=checks,
    )


def validate_step_reference(scan: STEPReferenceScan) -> ReferenceValidationResult:
    checks = [
        {
            "check": "schema_ap242",
            "expected": "contains AP242",
            "actual": scan.schema,
            "passed": "AP242" in scan.schema.upper(),
        },
        {
            "check": "product_count",
            "expected": 1,
            "actual": scan.product_count,
            "passed": scan.product_count == 1,
        },
        {
            "check": "product_definition_count",
            "expected": 1,
            "actual": scan.product_definition_count,
            "passed": scan.product_definition_count == 1,
        },
        {
            "check": "solid_count",
            "expected": 1,
            "actual": scan.solid_count,
            "passed": scan.solid_count == 1,
        },
        {
            "check": "no_fictitious_assembly",
            "expected": 0,
            "actual": scan.assembly_relationship_count,
            "passed": scan.assembly_relationship_count == 0,
        },
        {
            "check": "automatic_split_blocked",
            "expected": False,
            "actual": scan.auto_split_allowed,
            "passed": scan.auto_split_allowed is False,
        },
    ]
    return ReferenceValidationResult(
        passed=all(item["passed"] for item in checks),
        checks=checks,
        warnings=[] if scan.import_strategy == "single_product" else list(scan.notes),
    )


def write_scan_report(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = payload.to_dict() if hasattr(payload, "to_dict") else payload
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target


__all__ = [
    "IFCReferenceScan",
    "STEPReferenceScan",
    "ReferenceValidationResult",
    "scan_ifc",
    "scan_step",
    "validate_ifc_reference",
    "validate_step_reference",
    "write_scan_report",
]
