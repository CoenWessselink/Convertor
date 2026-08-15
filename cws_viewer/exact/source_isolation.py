"""Exact per-part source BREP isolation for external IFC and STEP projects.

This module bridges semantic project identity to exact OCCT shapes without
creating a second project model. It consumes the source identifiers already
stored on :class:`cws_convertor.project.model.Part` and returns an
:class:`~cws_viewer.exact.model.ExactPartRuntime` plus auditable evidence.

The implementation is deliberately conservative:

* STEP shapes are transferred by their Part-21 BREP root entity IDs. A whole
  STEP file is never treated as one part when the semantic importer identified
  multiple products/solids.
* IFC shapes are reconstructed from the exact product representation items.
  Supported analytical/CSG entities remain OCCT BREP. Any declared
  approximation blocks production-grade exactness.
* World placement is evidence only. The isolated BREP remains in its source
  local coordinate system so placement changes cannot alter manufacturing
  identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.gp import gp_Pnt, gp_Trsf

from cws_convertor.importers.ifc_project import _detect_units
from cws_convertor.importers.p21 import P21Document
from cws_convertor.project.model import Part
from cws_viewer.contracts.geometry import TessellationSettings
from cws_viewer.exact.catalog import build_exact_runtime
from cws_viewer.exact.model import ExactPartRuntime
from cws_viewer.geometry.ifc_provider import UnsupportedIfcGeometry
from cws_viewer.exact.ifc_profiles import ExactIfcShapeBuilder

ISOLATION_SCHEMA = "cws-source-brep-isolation-1.0"
ISOLATOR_VERSION = "cws-source-brep-v10.3"
DEFAULT_MAX_CATALOG_SUBSHAPES = 10_000


class IsolationStatus(StrEnum):
    EXACT = "exact"
    EXACT_WITH_DECLARED_APPROXIMATIONS = "exact_with_declared_approximations"
    BLOCKED = "blocked"


class SourceBrepIsolationError(RuntimeError):
    def __init__(self, message: str, *, code: str = "CWS-V10-SOURCE-BREP-ISOLATION-FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SourceBrepEvidence:
    part_id: str
    source_format: str
    source_file_id: str
    source_entity_id: str
    source_sha256: str
    source_geometry_hash: str
    method: str
    item_entity_ids: tuple[str, ...]
    unit_scale_to_mm: float
    status: IsolationStatus
    warnings: tuple[str, ...] = ()
    blocking_codes: tuple[str, ...] = ()
    local_placement: tuple[tuple[float, ...], ...] = ()
    global_placement: tuple[tuple[float, ...], ...] = ()
    shape_geometry_hash: str = ""
    solid_count: int = 0
    face_count: int = 0
    edge_count: int = 0
    vertex_count: int = 0
    catalog_deferred: bool = False
    valid: bool = False
    provider_version: str = ISOLATOR_VERSION
    schema: str = ISOLATION_SCHEMA

    @property
    def production_exact(self) -> bool:
        return self.status == IsolationStatus.EXACT and self.valid and self.solid_count == 1 and not self.blocking_codes

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "provider_version": self.provider_version,
            "part_id": self.part_id,
            "source_format": self.source_format,
            "source_file_id": self.source_file_id,
            "source_entity_id": self.source_entity_id,
            "source_sha256": self.source_sha256,
            "source_geometry_hash": self.source_geometry_hash,
            "shape_geometry_hash": self.shape_geometry_hash,
            "method": self.method,
            "item_entity_ids": list(self.item_entity_ids),
            "unit_scale_to_mm": self.unit_scale_to_mm,
            "status": self.status.value,
            "production_exact": self.production_exact,
            "warnings": list(self.warnings),
            "blocking_codes": list(self.blocking_codes),
            "local_placement": [list(row) for row in self.local_placement],
            "global_placement": [list(row) for row in self.global_placement],
            "solid_count": self.solid_count,
            "face_count": self.face_count,
            "edge_count": self.edge_count,
            "vertex_count": self.vertex_count,
            "catalog_deferred": self.catalog_deferred,
            "valid": self.valid,
        }


@dataclass(slots=True)
class SourceBrepIsolationResult:
    runtime: ExactPartRuntime | None
    evidence: SourceBrepEvidence
    shape: cq.Shape | None = None

    @property
    def source_shape_available(self) -> bool:
        return self.shape is not None

    @property
    def available(self) -> bool:
        return self.runtime is not None and self.shape is not None

    @property
    def production_exact(self) -> bool:
        return self.available and self.evidence.production_exact


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _matrix(value: Any) -> tuple[tuple[float, ...], ...]:
    raw = getattr(value, "matrix", value)
    try:
        rows = tuple(tuple(float(item) for item in row) for row in raw)
    except Exception:
        return ()
    return rows if len(rows) == 4 and all(len(row) == 4 for row in rows) else ()


def _descriptor(part: Part) -> dict[str, Any]:
    return dict(part.geometry_descriptor or {}) if isinstance(part.geometry_descriptor, Mapping) else {}


def _normalised_entity_ids(values: Iterable[Any]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip().lstrip("#")
        if text and text.isdigit() and text not in result:
            result.append(text)
    return tuple(result)


def _scale_shape(shape: cq.Shape, scale: float) -> cq.Shape:
    scale = float(scale)
    if abs(scale - 1.0) <= 1e-12:
        return shape
    transform = gp_Trsf()
    transform.SetScale(gp_Pnt(0.0, 0.0, 0.0), scale)
    result = BRepBuilderAPI_Transform(shape.wrapped, transform, True).Shape()
    scaled = cq.Shape.cast(result)
    if scaled.isNull():
        raise SourceBrepIsolationError("IFC-eenhedentransformatie leverde een lege shape op", code="CWS-V10-IFC-UNIT-SCALE-FAILED")
    return scaled


def _compound(shapes: Iterable[cq.Shape]) -> cq.Shape:
    values = [shape for shape in shapes if shape is not None and not shape.isNull()]
    if not values:
        raise SourceBrepIsolationError("Bronrepresentatie leverde geen shape op", code="CWS-V10-SOURCE-BREP-EMPTY")
    if len(values) == 1:
        return values[0]
    return cq.Compound.makeCompound(values)


def _validate_shape(shape: cq.Shape, *, allow_compound: bool = False) -> tuple[int, bool, tuple[str, ...]]:
    if shape is None or shape.isNull():
        raise SourceBrepIsolationError("Geïsoleerde bronshape is leeg", code="CWS-V10-SOURCE-BREP-EMPTY")
    solids = list(shape.Solids())
    valid = bool(shape.isValid())
    blocking: list[str] = []
    if not valid:
        blocking.append("CWS-V10-SOURCE-BREP-INVALID")
    if len(solids) != 1 and not allow_compound:
        blocking.append("CWS-V10-SOURCE-BREP-MULTI-SOLID")
    return len(solids), valid, tuple(blocking)


def _topology_counts(shape: cq.Shape) -> tuple[int, int, int]:
    return len(shape.Faces()), len(shape.Edges()), len(shape.Vertices())


def _runtime_or_deferred(shape: cq.Shape, *, part_id: str, source_name: str, max_catalog_subshapes: int) -> tuple[ExactPartRuntime | None, tuple[int, int, int], bool]:
    counts = _topology_counts(shape)
    deferred = sum(counts) > int(max_catalog_subshapes)
    if deferred:
        return None, counts, True
    return build_exact_runtime(shape, part_id=part_id, source_name=source_name), counts, False


class StepSourceBrepIsolator:
    method = "occt_step_entity_transfer"

    def __init__(self, *, max_catalog_subshapes: int = DEFAULT_MAX_CATALOG_SUBSHAPES) -> None:
        self.max_catalog_subshapes = int(max_catalog_subshapes)

    @staticmethod
    def _solid_root_ids(part: Part) -> tuple[str, ...]:
        return _normalised_entity_ids(_descriptor(part).get("solid_root_entity_ids") or ())

    @staticmethod
    def _transfer(path: Path, entity_ids: tuple[str, ...]) -> cq.Shape:
        reader = STEPControl_Reader()
        status = reader.ReadFile(str(path))
        if status != IFSelect_RetDone:
            raise SourceBrepIsolationError(f"OCCT kon STEP-bron niet lezen: {status}", code="CWS-V10-STEP-READ-FAILED")
        transferred: list[cq.Shape] = []
        for entity_id in entity_ids:
            selection = reader.GiveList(f"#{entity_id}")
            if selection.Length() != 1:
                raise SourceBrepIsolationError(f"STEP-entity #{entity_id} is niet uniek selecteerbaar ({selection.Length()} matches)", code="CWS-V10-STEP-ENTITY-NOT-UNIQUE")
            reader.ClearShapes()
            if not reader.TransferList(selection) or reader.NbShapes() < 1:
                raise SourceBrepIsolationError(f"STEP-entity #{entity_id} kon niet naar BREP worden getransfereerd", code="CWS-V10-STEP-ENTITY-TRANSFER-FAILED")
            shapes = [cq.Shape.cast(reader.Shape(index)) for index in range(1, reader.NbShapes() + 1)]
            transferred.extend(shape for shape in shapes if not shape.isNull())
        return _compound(transferred)

    def isolate(self, part: Part, source_path: str | Path) -> SourceBrepIsolationResult:
        path = Path(source_path).expanduser().resolve()
        entity_ids = self._solid_root_ids(part)
        if not entity_ids:
            raise SourceBrepIsolationError("STEP-part mist aantoonbare solid-root entity IDs", code="CWS-V10-STEP-SOLID-ROOT-MISSING")
        source_sha = _sha256_file(path)
        expected_sha = str(part.source_identity.source_sha256 or "").lower()
        if expected_sha and source_sha != expected_sha:
            raise SourceBrepIsolationError("STEP-bronhash wijkt af van de projectbron", code="CWS-V10-SOURCE-SHA256-MISMATCH")
        shape = self._transfer(path, entity_ids)
        solid_count, valid, shape_blocking = _validate_shape(shape)
        runtime, topology, deferred = _runtime_or_deferred(shape, part_id=part.internal_id, source_name=f"{path.name}#{','.join(entity_ids)}", max_catalog_subshapes=self.max_catalog_subshapes)
        blocking = list(shape_blocking)
        if deferred:
            blocking.append("CWS-V10-EXACT-CATALOG-DEFERRED-LARGE-PART")
        evidence = SourceBrepEvidence(
            part_id=part.internal_id, source_format="STEP", source_file_id=part.source_identity.source_file_id,
            source_entity_id=part.source_identity.source_entity_id, source_sha256=source_sha,
            source_geometry_hash=str(_descriptor(part).get("source_geometry_hash") or part.geometry_hash),
            shape_geometry_hash=(runtime.snapshot.exact_geometry_hash if runtime else str(_descriptor(part).get("source_geometry_hash") or part.geometry_hash)),
            method=self.method, item_entity_ids=entity_ids, unit_scale_to_mm=1.0,
            status=IsolationStatus.EXACT if not shape_blocking else IsolationStatus.BLOCKED,
            blocking_codes=tuple(dict.fromkeys(blocking)), local_placement=_matrix(part.local_placement), global_placement=_matrix(part.global_placement),
            solid_count=solid_count, face_count=topology[0], edge_count=topology[1], vertex_count=topology[2], catalog_deferred=deferred, valid=valid,
        )
        return SourceBrepIsolationResult(runtime=runtime, evidence=evidence, shape=shape)


class IfcSourceBrepIsolator:
    method = "ifc_semantic_csg_occt"

    def __init__(self, *, max_catalog_subshapes: int = DEFAULT_MAX_CATALOG_SUBSHAPES) -> None:
        self.max_catalog_subshapes = int(max_catalog_subshapes)

    @staticmethod
    def _item_ids(part: Part) -> tuple[str, ...]:
        descriptor = _descriptor(part); values: list[Any] = []
        for representation in descriptor.get("representations") or ():
            if isinstance(representation, Mapping):
                values.extend(representation.get("item_source_ids") or ())
        if not values:
            values.extend(descriptor.get("source_item_ids") or ())
        return _normalised_entity_ids(values)

    def isolate(self, part: Part, source_path: str | Path) -> SourceBrepIsolationResult:
        path = Path(source_path).expanduser().resolve()
        item_ids = self._item_ids(part)
        if not item_ids:
            raise SourceBrepIsolationError("IFC-part mist representation-item IDs", code="CWS-V10-IFC-REPRESENTATION-ITEM-MISSING")
        source_sha = _sha256_file(path)
        expected_sha = str(part.source_identity.source_sha256 or "").lower()
        if expected_sha and source_sha != expected_sha:
            raise SourceBrepIsolationError("IFC-bronhash wijkt af van de projectbron", code="CWS-V10-SOURCE-SHA256-MISMATCH")
        document = P21Document.load(path)
        unit_scale = float(_detect_units(document).length_to_mm)
        builder = ExactIfcShapeBuilder(document, TessellationSettings())
        before = len(builder.warnings)
        try:
            shapes = [builder.build(int(entity_id)) for entity_id in item_ids]
        except UnsupportedIfcGeometry as exc:
            raise SourceBrepIsolationError(f"IFC-representation kan niet exact worden opgebouwd: {exc}", code="CWS-V10-IFC-GEOMETRY-UNSUPPORTED") from exc
        shape = _scale_shape(_compound(shapes), unit_scale)
        warnings = tuple(dict.fromkeys(builder.warnings[before:]))
        solid_count, valid, shape_blocking = _validate_shape(shape)
        blocking = list(shape_blocking); status = IsolationStatus.EXACT
        if warnings:
            status = IsolationStatus.EXACT_WITH_DECLARED_APPROXIMATIONS; blocking.append("CWS-V10-IFC-DECLARED-GEOMETRY-APPROXIMATION")
        if shape_blocking:
            status = IsolationStatus.BLOCKED
        runtime, topology, deferred = _runtime_or_deferred(shape, part_id=part.internal_id, source_name=f"{path.name}#{','.join(item_ids)}", max_catalog_subshapes=self.max_catalog_subshapes)
        if deferred:
            blocking.append("CWS-V10-EXACT-CATALOG-DEFERRED-LARGE-PART")
        evidence = SourceBrepEvidence(
            part_id=part.internal_id, source_format="IFC", source_file_id=part.source_identity.source_file_id,
            source_entity_id=part.source_identity.source_entity_id, source_sha256=source_sha,
            source_geometry_hash=str(_descriptor(part).get("source_geometry_hash") or part.geometry_hash),
            shape_geometry_hash=(runtime.snapshot.exact_geometry_hash if runtime else str(_descriptor(part).get("source_geometry_hash") or part.geometry_hash)),
            method=self.method, item_entity_ids=item_ids, unit_scale_to_mm=unit_scale, status=status, warnings=warnings,
            blocking_codes=tuple(dict.fromkeys(blocking)), local_placement=_matrix(part.local_placement), global_placement=_matrix(part.global_placement),
            solid_count=solid_count, face_count=topology[0], edge_count=topology[1], vertex_count=topology[2], catalog_deferred=deferred, valid=valid,
        )
        return SourceBrepIsolationResult(runtime=runtime, evidence=evidence, shape=shape)


class SourceBrepIsolator:
    def __init__(self, *, max_catalog_subshapes: int = DEFAULT_MAX_CATALOG_SUBSHAPES) -> None:
        self.step = StepSourceBrepIsolator(max_catalog_subshapes=max_catalog_subshapes)
        self.ifc = IfcSourceBrepIsolator(max_catalog_subshapes=max_catalog_subshapes)

    def isolate(self, part: Part, source_path: str | Path) -> SourceBrepIsolationResult:
        source_format = str(part.source_identity.source_format or "").upper()
        if source_format == "STEP":
            return self.step.isolate(part, source_path)
        if source_format == "IFC":
            return self.ifc.isolate(part, source_path)
        raise SourceBrepIsolationError(f"Bronformaat {source_format or '?'} ondersteunt geen exacte isolatie", code="CWS-V10-EXACT-SOURCE-FORMAT-UNSUPPORTED")


__all__ = [
    "ISOLATION_SCHEMA", "ISOLATOR_VERSION", "DEFAULT_MAX_CATALOG_SUBSHAPES", "IsolationStatus",
    "SourceBrepEvidence", "SourceBrepIsolationError", "SourceBrepIsolationResult",
    "StepSourceBrepIsolator", "IfcSourceBrepIsolator", "SourceBrepIsolator",
]
