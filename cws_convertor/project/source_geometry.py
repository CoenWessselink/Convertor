"""Verified, lazy source-geometry isolation for semantic project parts.

The resolver never selects a STEP solid by list position or filename. IFC
products are isolated by their persistent entity identity and are explicitly
reported as triangulated evidence, not as exact production BREP geometry.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Callable, Iterable, Mapping

from cws_convertor.errors import CWSError, ErrorCode
from .baseline import sha256_file
from .model import Part, SourceFileRecord


SOURCE_LOCATOR_SCHEMA_VERSION = 1
SOURCE_INSPECTION_SCHEMA_VERSION = 1
CancelCheck = Callable[[], None]


class SourceGeometryError(CWSError):
    """A source selector or source shape could not be verified safely."""


@dataclass
class SourceGeometryInspection:
    part_id: str
    source_file_id: str
    source_sha256: str
    source_geometry_hash: str
    status: str
    scope: str
    geometry_kind: str
    selection_verified: bool
    production_geometry_exact: bool
    metrics: dict[str, Any] = field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    native_shape: Any = field(default=None, repr=False, compare=False)
    mesh_vertices_mm: tuple[tuple[float, float, float], ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    mesh_triangles: tuple[tuple[int, int, int], ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SOURCE_INSPECTION_SCHEMA_VERSION,
            "part_id": self.part_id,
            "source_file_id": self.source_file_id,
            "source_sha256": self.source_sha256,
            "source_geometry_hash": self.source_geometry_hash,
            "status": self.status,
            "scope": self.scope,
            "geometry_kind": self.geometry_kind,
            "selection_verified": self.selection_verified,
            "production_geometry_exact": self.production_geometry_exact,
            "metrics": dict(self.metrics),
            "topology": dict(self.topology),
            "evidence": dict(self.evidence),
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
        }


def _source_entity_id(value: str | int) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.startswith("#") else f"#{text}"


def build_step_source_locator(
    source: SourceFileRecord,
    *,
    source_entity_id: str,
    solid_root_entity_ids: Iterable[int | str],
    source_geometry_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_LOCATOR_SCHEMA_VERSION,
        "source_format": "STEP",
        "source_file_id": source.source_id,
        "source_sha256": source.sha256,
        "source_entity_id": _source_entity_id(source_entity_id),
        "source_geometry_hash": str(source_geometry_hash or ""),
        "selector": {
            "kind": "step_brep_roots",
            "entity_ids": [
                _source_entity_id(item) for item in solid_root_entity_ids
            ],
        },
    }


def build_ifc_source_locator(
    source: SourceFileRecord,
    *,
    source_entity_id: str,
    global_id: str,
    representation_id: str,
    source_geometry_hash: str,
) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_LOCATOR_SCHEMA_VERSION,
        "source_format": "IFC",
        "source_file_id": source.source_id,
        "source_sha256": source.sha256,
        "source_entity_id": _source_entity_id(source_entity_id),
        "source_geometry_hash": str(source_geometry_hash or ""),
        "selector": {
            "kind": "ifc_product_entity",
            "entity_id": _source_entity_id(source_entity_id),
            "global_id": str(global_id or ""),
            "representation_id": _source_entity_id(representation_id),
        },
    }


def _fallback_locator(part: Part) -> dict[str, Any]:
    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    source_format = part.source_identity.source_format.upper()
    if source_format in {"STEP", "STP"}:
        return {
            "schema_version": SOURCE_LOCATOR_SCHEMA_VERSION,
            "source_format": "STEP",
            "source_file_id": part.source_identity.source_file_id,
            "source_sha256": part.source_identity.source_sha256,
            "source_entity_id": _source_entity_id(part.source_identity.source_entity_id),
            "source_geometry_hash": str(descriptor.get("source_geometry_hash") or ""),
            "selector": {
                "kind": "step_brep_roots",
                "entity_ids": [
                    _source_entity_id(item)
                    for item in list(descriptor.get("solid_root_entity_ids") or [])
                ],
            },
        }
    if source_format == "IFC":
        return {
            "schema_version": SOURCE_LOCATOR_SCHEMA_VERSION,
            "source_format": "IFC",
            "source_file_id": part.source_identity.source_file_id,
            "source_sha256": part.source_identity.source_sha256,
            "source_entity_id": _source_entity_id(part.source_identity.source_entity_id),
            "source_geometry_hash": str(descriptor.get("source_geometry_hash") or ""),
            "selector": {
                "kind": "ifc_product_entity",
                "entity_id": _source_entity_id(part.source_identity.source_entity_id),
                "global_id": part.source_identity.global_id,
                "representation_id": _source_entity_id(
                    str(descriptor.get("source_representation_id") or "")
                ),
            },
        }
    return {}


def source_locator_for_part(part: Part) -> dict[str, Any]:
    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    locator = descriptor.get("source_locator")
    return dict(locator) if isinstance(locator, Mapping) else _fallback_locator(part)


def _require_sha256(value: Any, label: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise SourceGeometryError(
            f"{label} is geen geldige SHA-256",
            code=ErrorCode.PROJECT_INVALID,
        )
    return text


def validate_source_locator(part: Part, locator: Mapping[str, Any] | None = None) -> None:
    value = dict(locator or source_locator_for_part(part))
    if not value:
        return
    if int(value.get("schema_version", 0) or 0) != SOURCE_LOCATOR_SCHEMA_VERSION:
        raise SourceGeometryError(
            f"Onderdeel {part.internal_id} heeft een niet-ondersteunde bronselector",
            code=ErrorCode.PROJECT_INVALID,
        )
    source_format = str(value.get("source_format") or "").upper()
    expected_format = part.source_identity.source_format.upper().replace("STP", "STEP")
    if source_format.replace("STP", "STEP") != expected_format:
        raise SourceGeometryError(
            f"Bronselectorformaat van onderdeel {part.internal_id} wijkt af",
            code=ErrorCode.PROJECT_INVALID,
        )
    if str(value.get("source_file_id") or "") != part.source_identity.source_file_id:
        raise SourceGeometryError(
            f"Bronselector van onderdeel {part.internal_id} verwijst naar een andere bron",
            code=ErrorCode.PROJECT_INVALID,
        )
    locator_sha = _require_sha256(value.get("source_sha256"), "Bronselectorhash")
    identity_sha = _require_sha256(
        part.source_identity.source_sha256,
        "Onderdeelbronhash",
    )
    if locator_sha != identity_sha:
        raise SourceGeometryError(
            f"Bronselectorhash van onderdeel {part.internal_id} wijkt af",
            code=ErrorCode.PROJECT_INVALID,
        )
    descriptor_hash = str(part.geometry_descriptor.get("source_geometry_hash") or "")
    locator_geometry_hash = str(value.get("source_geometry_hash") or "")
    if descriptor_hash and locator_geometry_hash != descriptor_hash:
        raise SourceGeometryError(
            f"Brongeometriehash van onderdeel {part.internal_id} wijkt af van de selector",
            code=ErrorCode.PROJECT_INVALID,
        )
    selector = value.get("selector")
    if not isinstance(selector, Mapping):
        raise SourceGeometryError(
            f"Onderdeel {part.internal_id} mist een bronselector",
            code=ErrorCode.PROJECT_INVALID,
        )
    if source_format == "STEP":
        if selector.get("kind") != "step_brep_roots":
            raise SourceGeometryError(
                f"Onderdeel {part.internal_id} heeft een ongeldige STEP-selector",
                code=ErrorCode.PROJECT_INVALID,
            )
        entity_ids = list(selector.get("entity_ids") or [])
        if any(not _source_entity_id(item) for item in entity_ids):
            raise SourceGeometryError(
                f"Onderdeel {part.internal_id} heeft een lege STEP-root",
                code=ErrorCode.PROJECT_INVALID,
            )
    elif source_format == "IFC":
        if selector.get("kind") != "ifc_product_entity" or not _source_entity_id(
            selector.get("entity_id", "")
        ):
            raise SourceGeometryError(
                f"Onderdeel {part.internal_id} heeft een ongeldige IFC-selector",
                code=ErrorCode.PROJECT_INVALID,
            )


def _inspection(
    part: Part,
    *,
    status: str,
    scope: str,
    geometry_kind: str,
    selection_verified: bool,
    production_geometry_exact: bool,
    metrics: Mapping[str, Any] | None = None,
    topology: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
    warnings: Iterable[str] = (),
    blocking_reasons: Iterable[str] = (),
    native_shape: Any = None,
    mesh_vertices_mm: Iterable[tuple[float, float, float]] = (),
    mesh_triangles: Iterable[tuple[int, int, int]] = (),
) -> SourceGeometryInspection:
    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, Mapping) else {}
    return SourceGeometryInspection(
        part_id=part.internal_id,
        source_file_id=part.source_identity.source_file_id,
        source_sha256=part.source_identity.source_sha256.lower(),
        source_geometry_hash=str(descriptor.get("source_geometry_hash") or ""),
        status=status,
        scope=scope,
        geometry_kind=geometry_kind,
        selection_verified=selection_verified,
        production_geometry_exact=production_geometry_exact,
        metrics=dict(metrics or {}),
        topology=dict(topology or {}),
        evidence=dict(evidence or {}),
        warnings=list(warnings),
        blocking_reasons=list(blocking_reasons),
        native_shape=native_shape,
        mesh_vertices_mm=tuple(mesh_vertices_mm),
        mesh_triangles=tuple(mesh_triangles),
    )


def _inspect_step(
    part: Part,
    source: SourceFileRecord,
    path: Path,
    locator: Mapping[str, Any],
    cancel_check: CancelCheck | None,
) -> SourceGeometryInspection:
    selector = dict(locator.get("selector") or {})
    root_ids = [_source_entity_id(item) for item in list(selector.get("entity_ids") or [])]
    if cancel_check is not None:
        cancel_check()
    try:
        import cadquery as cq

        imported = cq.importers.importStep(str(path))
        source_shape = imported.val()
        solids = list(source_shape.Solids())
    except Exception as exc:
        return _inspection(
            part,
            status="unavailable",
            scope="unknown",
            geometry_kind="semantic_reference",
            selection_verified=False,
            production_geometry_exact=False,
            blocking_reasons=[f"STEP-bronshape kon niet worden geladen: {exc}"],
        )
    if cancel_check is not None:
        cancel_check()

    evidence = {
        "selector_kind": "step_brep_roots",
        "selector_entity_ids": root_ids,
        "native_source_solid_count": len(solids),
        "selection_rule": "one semantic BREP root and one native source solid",
    }
    if len(root_ids) != 1 or len(solids) != 1:
        return _inspection(
            part,
            status="manual_validation_required",
            scope="unknown",
            geometry_kind="semantic_reference",
            selection_verified=False,
            production_geometry_exact=False,
            evidence=evidence,
            blocking_reasons=[
                "STEP-solid kan niet bewijsbaar aan dit onderdeel worden gekoppeld zonder selectie op volgorde."
            ],
        )

    shape = solids[0]
    box = shape.BoundingBox()
    topology = {
        "solid_count": len(shape.Solids()),
        "shell_count": len(shape.Shells()),
        "face_count": len(shape.Faces()),
        "edge_count": len(shape.Edges()),
        "vertex_count": len(shape.Vertices()),
    }
    metrics = {
        "scope": "exact_part",
        "fidelity": "native_brep",
        "measurement_method": "cadquery_native_brep",
        "solid_count": topology["solid_count"],
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
        "valid": bool(shape.isValid()),
    }
    return _inspection(
        part,
        status="resolved_exact",
        scope="part",
        geometry_kind="native_brep",
        selection_verified=True,
        production_geometry_exact=True,
        metrics=metrics,
        topology=topology,
        evidence=evidence,
        native_shape=shape,
    )


def _mesh_topology(
    vertices: tuple[tuple[float, float, float], ...],
    triangles: tuple[tuple[int, int, int], ...],
) -> dict[str, Any]:
    parents = list(range(len(vertices)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    edges: Counter[tuple[int, int]] = Counter()
    used: set[int] = set()
    for first, second, third in triangles:
        used.update((first, second, third))
        union(first, second)
        union(second, third)
        union(third, first)
        edges[tuple(sorted((first, second)))] += 1
        edges[tuple(sorted((second, third)))] += 1
        edges[tuple(sorted((third, first)))] += 1
    component_count = len({find(index) for index in used}) if used else 0
    closed = bool(edges) and all(count == 2 for count in edges.values())
    return {
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
        "mesh_edge_count": len(edges),
        "mesh_component_count": component_count,
        "closed_mesh": closed,
        "boundary_or_nonmanifold_edge_count": sum(count != 2 for count in edges.values()),
    }


def _mesh_metrics(
    vertices: tuple[tuple[float, float, float], ...],
    triangles: tuple[tuple[int, int, int], ...],
    topology: Mapping[str, Any],
) -> dict[str, Any]:
    if not vertices or not triangles:
        return {
            "scope": "entity",
            "fidelity": "triangulated_mesh",
            "measurement_method": "ifcopenshell_triangulation",
            "valid": False,
        }
    area = 0.0
    signed_volume = 0.0
    for first, second, third in triangles:
        a = vertices[first]
        b = vertices[second]
        c = vertices[third]
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        area += 0.5 * math.sqrt(sum(value * value for value in cross))
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    axes = list(zip(*vertices))
    bbox = [max(axis) - min(axis) for axis in axes]
    closed = bool(topology.get("closed_mesh"))
    components = int(topology.get("mesh_component_count", 0) or 0)
    return {
        "scope": "entity",
        "fidelity": "triangulated_mesh",
        "measurement_method": "ifcopenshell_triangulation",
        "solid_count": components if closed else None,
        "volume_mm3": abs(signed_volume) if closed else None,
        "area_mm2": area,
        "bbox_mm": bbox,
        "valid": bool(closed and all(math.isfinite(value) for value in (*bbox, area, signed_volume))),
    }


def _mesh_sha256(
    vertices: tuple[tuple[float, float, float], ...],
    triangles: tuple[tuple[int, int, int], ...],
) -> str:
    payload = {
        "vertices_mm": [[round(value, 9) for value in vertex] for vertex in vertices],
        "triangles": [list(triangle) for triangle in triangles],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def _write_worker_json(path: str, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(dict(payload), sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(target)


def _ifc_worker_payload(
    source_path: str,
    entity_id: int,
    expected_global_id: str,
    expected_representation: str,
) -> dict[str, Any]:
    import ifcopenshell
    import ifcopenshell.geom

    model = ifcopenshell.open(source_path)
    entity = model.by_id(entity_id)
    if entity is None or not entity.is_a("IfcProduct"):
        raise SourceGeometryError(
            f"IFC-selector #{entity_id} is geen IfcProduct",
            code=ErrorCode.IMPORT_AMBIGUOUS,
        )
    actual_global_id = str(getattr(entity, "GlobalId", "") or "")
    if expected_global_id and actual_global_id != expected_global_id:
        raise SourceGeometryError(
            f"IFC GlobalId van selector #{entity_id} wijkt af",
            code=ErrorCode.IMPORT_AMBIGUOUS,
            details={"expected": expected_global_id, "actual": actual_global_id},
        )
    representation = getattr(entity, "Representation", None)
    actual_representation = _source_entity_id(representation.id() if representation else "")
    if expected_representation and actual_representation != expected_representation:
        raise SourceGeometryError(
            f"IFC-representatie van selector #{entity_id} wijkt af",
            code=ErrorCode.IMPORT_AMBIGUOUS,
            details={"expected": expected_representation, "actual": actual_representation},
        )
    evidence = {
        "selector_kind": "ifc_product_entity",
        "ifc_entity_id": f"#{entity_id}",
        "global_id": actual_global_id,
        "representation_id": actual_representation,
        "coordinate_space": "product_local",
        "ifcopenshell_output_units": "SI converted to mm",
        "worker_process_isolated": True,
    }
    if representation is None:
        return {
            "status": "manual_validation_required",
            "scope": "entity",
            "geometry_kind": "semantic_reference",
            "selection_verified": True,
            "production_geometry_exact": False,
            "metrics": {},
            "topology": {},
            "evidence": evidence,
            "warnings": [],
            "blocking_reasons": [
                "De geselecteerde IFC-entiteit heeft geen geometrische representatie."
            ],
            "vertices_mm": [],
            "triangles": [],
        }
    settings = ifcopenshell.geom.settings()
    shape = ifcopenshell.geom.create_shape(settings, entity)
    flat_vertices = tuple(float(value) * 1000.0 for value in shape.geometry.verts)
    flat_faces = tuple(int(value) for value in shape.geometry.faces)
    vertices = tuple(
        (flat_vertices[index], flat_vertices[index + 1], flat_vertices[index + 2])
        for index in range(0, len(flat_vertices), 3)
    )
    triangles = tuple(
        (flat_faces[index], flat_faces[index + 1], flat_faces[index + 2])
        for index in range(0, len(flat_faces), 3)
    )
    topology = _mesh_topology(vertices, triangles)
    metrics = _mesh_metrics(vertices, triangles, topology)
    evidence["mesh_sha256"] = _mesh_sha256(vertices, triangles)
    return {
        "status": "resolved_mesh",
        "scope": "part",
        "geometry_kind": "triangulated_mesh",
        "selection_verified": True,
        "production_geometry_exact": False,
        "metrics": metrics,
        "topology": topology,
        "evidence": evidence,
        "warnings": [
            "IFC-brongeometrie is per entiteit geisoleerd als tessellatie; dit is geen exact production BREP."
        ],
        "blocking_reasons": [
            "Exacte IFC-BREP-vergelijking en productiefeaturevalidatie zijn nog vereist."
        ],
        "vertices_mm": vertices,
        "triangles": triangles,
    }


def _ifc_worker_entry(
    source_path: str,
    entity_id: int,
    expected_global_id: str,
    expected_representation: str,
    output_path: str,
) -> None:
    try:
        payload = _ifc_worker_payload(
            source_path,
            entity_id,
            expected_global_id,
            expected_representation,
        )
        result = {"ok": True, "result": payload}
    except SourceGeometryError as exc:
        result = {
            "ok": False,
            "error": {
                "message": exc.message,
                "code": exc.code.value,
                "details": dict(exc.details or {}),
            },
        }
    except Exception as exc:
        result = {
            "ok": False,
            "error": {
                "message": f"IFC-entiteitsgeometrie kon niet worden getesselleerd: {exc}",
                "code": ErrorCode.INTERNAL_ERROR.value,
                "details": {"type": type(exc).__name__},
            },
        }
    _write_worker_json(output_path, result)


def _run_ifc_worker(
    path: Path,
    entity_id: int,
    expected_global_id: str,
    expected_representation: str,
    cancel_check: CancelCheck | None,
) -> dict[str, Any]:
    import multiprocessing

    with tempfile.TemporaryDirectory(prefix="cws_ifc_shape_") as folder_name:
        output = Path(folder_name) / "result.json"
        context = multiprocessing.get_context("spawn")
        process = context.Process(
            target=_ifc_worker_entry,
            args=(
                str(path),
                entity_id,
                expected_global_id,
                expected_representation,
                str(output),
            ),
            name=f"cws-ifc-shape-{entity_id}",
        )
        process.start()
        try:
            while process.is_alive():
                process.join(timeout=0.1)
                if cancel_check is not None:
                    cancel_check()
        except BaseException:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5.0)
            raise
        process.join()
        if not output.is_file():
            return {
                "ok": False,
                "error": {
                    "message": (
                        "IFC-geometrieworker eindigde zonder resultaat "
                        f"(exitcode {process.exitcode})"
                    ),
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "details": {"exit_code": process.exitcode},
                },
            }
        return json.loads(output.read_text(encoding="utf-8"))


def _inspect_ifc(
    part: Part,
    source: SourceFileRecord,
    path: Path,
    locator: Mapping[str, Any],
    cancel_check: CancelCheck | None,
) -> SourceGeometryInspection:
    selector = dict(locator.get("selector") or {})
    raw_entity_id = _source_entity_id(selector.get("entity_id", ""))
    try:
        entity_id = int(raw_entity_id.removeprefix("#"))
    except ValueError as exc:
        raise SourceGeometryError(
            f"IFC-selector van onderdeel {part.internal_id} heeft geen numeriek entity-ID",
            code=ErrorCode.PROJECT_INVALID,
        ) from exc
    if cancel_check is not None:
        cancel_check()
    expected_global_id = str(selector.get("global_id") or "")
    expected_representation = _source_entity_id(selector.get("representation_id", ""))
    worker = _run_ifc_worker(
        path,
        entity_id,
        expected_global_id,
        expected_representation,
        cancel_check,
    )
    if not worker.get("ok"):
        error = dict(worker.get("error") or {})
        error_code = ErrorCode(str(error.get("code") or ErrorCode.INTERNAL_ERROR.value))
        if error_code in {ErrorCode.IMPORT_AMBIGUOUS, ErrorCode.PROJECT_INVALID}:
            raise SourceGeometryError(
                str(error.get("message") or "IFC-geometrieworker faalde"),
                code=error_code,
                details=dict(error.get("details") or {}),
            )
        return _inspection(
            part,
            status="unavailable",
            scope="unknown",
            geometry_kind="semantic_reference",
            selection_verified=False,
            production_geometry_exact=False,
            blocking_reasons=[str(error.get("message") or "IFC-geometrieworker faalde")],
        )
    payload = dict(worker.get("result") or {})
    vertices = tuple(tuple(float(value) for value in item) for item in payload.pop("vertices_mm", []))
    triangles = tuple(tuple(int(value) for value in item) for item in payload.pop("triangles", []))
    return _inspection(
        part,
        status=str(payload.get("status") or "unavailable"),
        scope=str(payload.get("scope") or "unknown"),
        geometry_kind=str(payload.get("geometry_kind") or "semantic_reference"),
        selection_verified=bool(payload.get("selection_verified", False)),
        production_geometry_exact=bool(payload.get("production_geometry_exact", False)),
        metrics=dict(payload.get("metrics") or {}),
        topology=dict(payload.get("topology") or {}),
        evidence=dict(payload.get("evidence") or {}),
        warnings=list(payload.get("warnings") or []),
        blocking_reasons=list(payload.get("blocking_reasons") or []),
        mesh_vertices_mm=vertices,
        mesh_triangles=triangles,
    )


def inspect_part_source_geometry(
    part: Part,
    source: SourceFileRecord,
    source_path: str | Path,
    *,
    cancel_check: CancelCheck | None = None,
) -> SourceGeometryInspection:
    path = Path(source_path).expanduser().resolve()
    if not path.is_file():
        raise SourceGeometryError(
            f"Bronbestand ontbreekt: {path.name}",
            code=ErrorCode.INVALID_INPUT,
        )
    if part.source_identity.source_file_id != source.source_id:
        raise SourceGeometryError(
            f"Onderdeel {part.internal_id} hoort niet bij bron {source.source_id}",
            code=ErrorCode.PROJECT_INVALID,
        )
    if cancel_check is not None:
        cancel_check()
    actual_sha = sha256_file(path)
    if actual_sha != source.sha256 or actual_sha != part.source_identity.source_sha256:
        raise SourceGeometryError(
            f"Bronbytes voor onderdeel {part.internal_id} zijn gewijzigd",
            code=ErrorCode.PROJECT_INVALID,
            details={"expected": source.sha256, "actual": actual_sha},
        )
    locator = source_locator_for_part(part)
    validate_source_locator(part, locator)
    source_format = str(locator.get("source_format") or "").upper()
    if source_format in {"STEP", "STP"}:
        return _inspect_step(part, source, path, locator, cancel_check)
    if source_format == "IFC":
        return _inspect_ifc(part, source, path, locator, cancel_check)
    raise SourceGeometryError(
        f"Brongeometrie-isolatie ondersteunt geen {source_format or source.source_format}",
        code=ErrorCode.UNSUPPORTED_FORMAT,
    )


def persist_source_geometry_inspection(
    part: Part,
    inspection: SourceGeometryInspection,
) -> dict[str, Any]:
    if inspection.part_id != part.internal_id:
        raise SourceGeometryError(
            "Brongeometrie-inspectie hoort bij een ander onderdeel",
            code=ErrorCode.PROJECT_INVALID,
        )
    descriptor = dict(part.geometry_descriptor or {})
    descriptor["source_locator"] = source_locator_for_part(part)
    descriptor["source_inspection"] = inspection.to_dict()
    if inspection.geometry_kind == "native_brep" and inspection.selection_verified:
        descriptor["cad_metrics"] = dict(inspection.metrics)
    elif inspection.geometry_kind == "triangulated_mesh" and inspection.selection_verified:
        descriptor["source_mesh_metrics"] = dict(inspection.metrics)
    part.geometry_descriptor = descriptor
    part.recompute_hashes()
    part.validate_hashes()
    return dict(descriptor["source_inspection"])


__all__ = [
    "SOURCE_LOCATOR_SCHEMA_VERSION",
    "SOURCE_INSPECTION_SCHEMA_VERSION",
    "SourceGeometryError",
    "SourceGeometryInspection",
    "build_ifc_source_locator",
    "build_step_source_locator",
    "inspect_part_source_geometry",
    "persist_source_geometry_inspection",
    "source_locator_for_part",
    "validate_source_locator",
]
