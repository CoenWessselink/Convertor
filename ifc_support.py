"""Optionele IFC-ondersteuning via IfcOpenShell.

De module importeert IfcOpenShell pas op het moment dat een IFC-functie wordt
gebruikt. Daardoor blijven NC1/STEP en de viewer bruikbaar wanneer de optionele
IFC-dependency nog niet is geïnstalleerd.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import math
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable

import cadquery as cq
import numpy as np

from canonical_model import (
    CanonicalHeader,
    CanonicalPart,
    canonical_from_nc1_part,
    embed_part_in_nc1,
    embed_part_in_step,
    extract_part_from_ifc,
    extract_part_from_nc1,
    extract_part_from_step,
    sha256_bytes,
)
from ifc_native import parse_native_ifc_meshes, write_native_ifc
from analytic_fitting import recognize_analytic_shape


class IFCDependencyError(RuntimeError):
    pass


def require_ifcopenshell():
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.api  # type: ignore
        import ifcopenshell.geom  # type: ignore
        import ifcopenshell.util.element  # type: ignore
        import ifcopenshell.util.unit  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency is optional in source environment
        raise IFCDependencyError(
            "Voor algemene externe IFC-geometrie is IfcOpenShell nodig. De officiële "
            "Windows-installer bundelt deze dependency; converter-eigen IFC4-tessellaties "
            "blijven ook met de ingebouwde parser beschikbaar."
        ) from exc
    return ifcopenshell


def ifc_available() -> bool:
    try:
        require_ifcopenshell()
        return True
    except IFCDependencyError:
        return False


@dataclass
class IFCGeometryItem:
    guid: str
    name: str
    ifc_class: str
    tag: str
    material_name: str
    vertices_mm: np.ndarray
    triangles: np.ndarray
    properties: dict[str, Any] = field(default_factory=dict)
    quantities: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def area_mm2(self) -> float:
        return mesh_area(self.vertices_mm, self.triangles)

    @property
    def volume_mm3(self) -> float:
        return mesh_volume(self.vertices_mm, self.triangles)

    @property
    def bbox_mm(self) -> tuple[float, float, float]:
        if len(self.vertices_mm) == 0:
            return 0.0, 0.0, 0.0
        lengths = np.ptp(self.vertices_mm, axis=0)
        return tuple(sorted((float(v) for v in lengths), reverse=True))


@dataclass
class IFCModelData:
    source: Path
    schema: str
    project_name: str
    items: list[IFCGeometryItem]
    warnings: list[str] = field(default_factory=list)


@dataclass
class IFCConversionResult:
    source: Path
    outputs: list[Path]
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def primary_output(self) -> Path | None:
        return self.outputs[0] if self.outputs else None


def mesh_area(vertices: np.ndarray, triangles: np.ndarray) -> float:
    if len(vertices) == 0 or len(triangles) == 0:
        return 0.0
    polys = vertices[triangles]
    cross = np.cross(polys[:, 1] - polys[:, 0], polys[:, 2] - polys[:, 0])
    return float(np.linalg.norm(cross, axis=1).sum() * 0.5)


def mesh_volume(vertices: np.ndarray, triangles: np.ndarray) -> float:
    if len(vertices) == 0 or len(triangles) == 0:
        return 0.0
    polys = vertices[triangles]
    signed = np.einsum("ij,ij->i", polys[:, 0], np.cross(polys[:, 1], polys[:, 2])).sum() / 6.0
    return abs(float(signed))


def _flatten_properties(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _flatten_properties(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_flatten_properties(v) for v in value]
    return str(value)


def _material_name(element: Any, util_element: Any) -> str:
    try:
        materials = util_element.get_materials(element, should_inherit=True)
    except TypeError:
        materials = util_element.get_materials(element)
    except Exception:
        materials = []
    names = []
    for material in materials or []:
        name = getattr(material, "Name", None)
        if name:
            names.append(str(name))
    if names:
        return ", ".join(dict.fromkeys(names))
    try:
        material = util_element.get_material(element, should_skip_usage=True, should_inherit=True)
        return str(getattr(material, "Name", "") or "")
    except Exception:
        return ""


def load_ifc_geometry(path: str | Path) -> IFCModelData:
    """Lees IFC-geometrie in millimeters.

    Externe IFC-modellen gebruiken bij voorkeur IfcOpenShell. Converter-eigen
    IFC4-tessellaties hebben daarnaast een dependency-arme parser, zodat viewer,
    hoeveelheden en lossless roundtrip ook in de portable kern blijven werken.
    """

    source = Path(path)
    canonical = extract_part_from_ifc(source, strict=False)

    try:
        ifcopenshell = require_ifcopenshell()
    except IFCDependencyError as dependency_error:
        try:
            native_meshes = parse_native_ifc_meshes(source)
        except Exception as native_error:
            raise IFCDependencyError(
                f"{dependency_error} Native IFC-parser kon {source.name} ook niet lezen: {native_error}"
            ) from native_error
        properties: dict[str, Any] = {}
        if canonical is not None:
            properties["Pset_NC1StepConverter"] = {
                "SchemaVersion": canonical.schema_version,
                "ConverterVersion": canonical.converter_version,
                "SourceFormat": canonical.source_format,
                "SourceFile": canonical.source_file,
                "SourceSHA256": canonical.source_sha256,
                "PartId": canonical.part_id,
                "ProfileDesignation": canonical.profile_designation,
                "ProfileType": canonical.profile_type,
                "PayloadVerified": True,
            }
        items = [
            IFCGeometryItem(
                guid=mesh.guid,
                name=mesh.name,
                ifc_class=mesh.ifc_class,
                tag=canonical.part_id if canonical is not None else "",
                material_name=mesh.material or (canonical.material if canonical is not None else ""),
                vertices_mm=mesh.vertices_mm,
                triangles=mesh.triangles,
                properties=properties,
                warnings=["Geometrie gelezen met ingebouwde IFC4-tessellatieparser"],
            )
            for mesh in native_meshes
        ]
        return IFCModelData(
            source=source,
            schema="IFC4",
            project_name=(canonical.part_id if canonical is not None else source.stem),
            items=items,
            warnings=[
                "IfcOpenShell niet beschikbaar; converter/native IfcTriangulatedFaceSet-parser gebruikt."
            ],
        )

    import ifcopenshell.geom  # type: ignore
    import ifcopenshell.util.element  # type: ignore

    model = ifcopenshell.open(str(source))
    settings = ifcopenshell.geom.settings()
    try:
        settings.set(settings.USE_WORLD_COORDS, True)
    except Exception:
        pass
    try:
        settings.set(settings.WELD_VERTICES, True)
    except Exception:
        pass

    projects = model.by_type("IfcProject")
    project_name = str(getattr(projects[0], "Name", "") or source.stem) if projects else source.stem
    items: list[IFCGeometryItem] = []
    warnings: list[str] = []
    excluded = {"IfcOpeningElement", "IfcSpace", "IfcAnnotation", "IfcGrid"}
    elements = model.by_type("IfcElement")
    for index, element in enumerate(elements, start=1):
        if element.is_a() in excluded or not getattr(element, "Representation", None):
            continue
        try:
            shape = ifcopenshell.geom.create_shape(settings, element)
            geometry = shape.geometry
            verts = np.asarray(geometry.verts, dtype=float).reshape((-1, 3)) * 1000.0
            faces = np.asarray(geometry.faces, dtype=int).reshape((-1, 3))
            if len(verts) < 3 or len(faces) < 1:
                continue
            psets = ifcopenshell.util.element.get_psets(
                element,
                psets_only=False,
                qtos_only=False,
                should_inherit=True,
            )
            quantities = {
                key: value
                for key, value in psets.items()
                if str(key).lower().startswith(("qto_", "basequantities"))
            }
            properties = {key: value for key, value in psets.items() if key not in quantities}
            if canonical is not None:
                properties.setdefault(
                    "Pset_NC1StepConverter_Verification",
                    {
                        "PayloadVerified": True,
                        "SchemaVersion": canonical.schema_version,
                        "SourceSHA256": canonical.source_sha256,
                    },
                )
            items.append(
                IFCGeometryItem(
                    guid=str(getattr(element, "GlobalId", "") or f"element-{index}"),
                    name=str(
                        getattr(element, "Name", "")
                        or getattr(element, "ObjectType", "")
                        or f"Element {index}"
                    ),
                    ifc_class=str(element.is_a()),
                    tag=str(getattr(element, "Tag", "") or ""),
                    material_name=_material_name(element, ifcopenshell.util.element),
                    vertices_mm=verts,
                    triangles=faces,
                    properties=_flatten_properties(properties),
                    quantities=_flatten_properties(quantities),
                )
            )
        except Exception as exc:
            warnings.append(
                f"{getattr(element, 'GlobalId', index)} ({element.is_a()}): geometrie niet gelezen: {exc}"
            )
    if not items:
        detail = f" Waarschuwingen: {'; '.join(warnings[:3])}" if warnings else ""
        raise ValueError(f"Geen renderbare IfcElement-geometrie gevonden in {source.name}.{detail}")
    return IFCModelData(source, str(getattr(model, "schema", "IFC")), project_name, items, warnings)


def combined_mesh(path: str | Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    model = load_ifc_geometry(path)
    vertices: list[np.ndarray] = []
    triangles: list[np.ndarray] = []
    offset = 0
    for item in model.items:
        vertices.append(item.vertices_mm)
        triangles.append(item.triangles + offset)
        offset += len(item.vertices_mm)
    points = np.vstack(vertices)
    faces = np.vstack(triangles)
    bbox = tuple(sorted((float(v) for v in np.ptp(points, axis=0)), reverse=True))
    metrics = {
        "volume": sum(item.volume_mm3 for item in model.items),
        "area": sum(item.area_mm2 for item in model.items),
        "bbox": bbox,
        "solids": len(model.items),
        "items": len(model.items),
        "warnings": model.warnings,
    }
    return points, faces, metrics


def mesh_to_cq_shape(vertices_mm: np.ndarray, triangles: np.ndarray, *, make_solid: bool = True) -> cq.Shape:
    """Maak een (bij voorkeur gesloten) Open CASCADE-vorm uit een driehoeksmesh."""
    faces: list[cq.Face] = []
    for tri in np.asarray(triangles, dtype=int):
        points = [cq.Vector(*map(float, vertices_mm[int(i)])) for i in tri]
        if (points[1] - points[0]).cross(points[2] - points[0]).Length <= 1e-10:
            continue
        try:
            wire = cq.Wire.makePolygon(points, close=True)
            faces.append(cq.Face.makeFromWires(wire))
        except Exception:
            continue
    if not faces:
        raise ValueError("IFC-mesh bevat geen geldige driehoeksvlakken")

    # Sew triangle faces; a closed IFC triangulation can then become a solid.
    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
        sewer = BRepBuilderAPI_Sewing(1e-5, True, True, True, False)
        for face in faces:
            sewer.Add(face.wrapped)
        sewer.Perform()
        sewn = cq.Shape.cast(sewer.SewedShape())
        if make_solid:
            shells = sewn.Shells()
            solids: list[cq.Solid] = []
            for shell in shells:
                try:
                    solid = cq.Solid.makeSolid(shell).fix()
                    if solid.isValid() and solid.Volume() > 1e-6:
                        solids.append(solid)
                except Exception:
                    continue
            if len(solids) == 1:
                return solids[0]
            if solids:
                return cq.Compound.makeCompound(solids)
        return sewn.fix()
    except Exception:
        try:
            shell = cq.Shell.makeShell(faces)
            if make_solid:
                solid = cq.Solid.makeSolid(shell).fix()
                if solid.isValid() and solid.Volume() > 1e-6:
                    return solid
            return shell
        except Exception:
            return cq.Compound.makeCompound(faces)


def _safe_name(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", text or "").strip("_.")
    return cleaned[:120] or fallback


def _export_shapes_step(shapes: Iterable[cq.Shape], output_path: Path) -> None:
    values = list(shapes)
    if not values:
        raise ValueError("Geen geometrie om als STEP te exporteren")
    shape = values[0] if len(values) == 1 else cq.Compound.makeCompound(values)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(shape, str(output_path), exportType="STEP")


def ifc_to_step(input_path: str | Path, output_path: str | Path) -> IFCConversionResult:
    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    # Converter-eigen IFC: herstel eerst de gehashte analytische/productiedata.
    canonical = extract_part_from_ifc(source, strict=False)
    if canonical is not None:
        step_bytes = canonical.attachment_bytes("step")
        if step_bytes:
            target.write_bytes(step_bytes)
            embed_part_in_step(target, canonical)
            return IFCConversionResult(
                source,
                [target],
                ["STEP lossless hersteld uit geverifieerde Pset_NC1StepConverter-payload"],
            )
        nc1_bytes = canonical.attachment_bytes("nc1")
        if nc1_bytes:
            from conversion import convert_nc1_to_step

            with tempfile.TemporaryDirectory(prefix="ifc_payload_step_") as folder:
                nc1_path = Path(folder) / (canonical.attachment("nc1").name or f"{source.stem}.nc1")
                nc1_path.write_bytes(nc1_bytes)
                embed_part_in_nc1(nc1_path, canonical)
                convert_nc1_to_step(nc1_path, target)
            embed_part_in_step(target, canonical)
            return IFCConversionResult(
                source,
                [target],
                ["STEP analytisch opgebouwd uit geverifieerde canonieke NC1-payload"],
            )

    # Prefer the official IfcConvert CLI when available; it preserves more IFC geometry semantics.
    executable = shutil.which("IfcConvert") or shutil.which("IfcConvert.exe")
    if executable:
        process = subprocess.run(
            [executable, str(source), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if process.returncode == 0 and target.exists():
            return IFCConversionResult(
                source,
                [target],
                [line for line in process.stderr.splitlines() if line.strip()],
            )
        warnings.append(
            f"IfcConvert viel terug op faceted export: {process.stderr.strip() or process.stdout.strip()}"
        )

    model = load_ifc_geometry(source)
    shapes: list[cq.Shape] = []
    for item in model.items:
        recognition = recognize_analytic_shape(
            item.vertices_mm,
            item.triangles,
            minimum_confidence=0.92,
            radial_tolerance_mm=0.35,
        )
        if recognition.shape is not None:
            shapes.append(recognition.shape)
            if recognition.kind == "cylinder":
                warnings.append(
                    f"{item.guid}: analytische cilinder hersteld "
                    f"(Ø{float(recognition.diagnostics.get('diameter_mm', 0.0)):.3f} mm, "
                    f"confidence {recognition.confidence:.1%}, "
                    f"radiale RMS {float(recognition.diagnostics.get('rms_residual_mm', 0.0)):.4f} mm)."
                )
            continue
        try:
            shapes.append(mesh_to_cq_shape(item.vertices_mm, item.triangles, make_solid=True))
            if recognition.kind != "none":
                warnings.append(
                    f"{item.guid}: analytische kandidaat niet vrijgegeven "
                    f"(confidence {recognition.confidence:.1%}); faceted fallback gebruikt."
                )
        except Exception as exc:
            warnings.append(f"{item.guid}: niet naar STEP-oppervlak omgezet: {exc}")
    _export_shapes_step(shapes, target)
    warnings.extend(model.warnings)
    warnings.append(
        "Externe IFC zonder converterpayload: analytische fitting wordt eerst geprobeerd; "
        "overige geometrie blijft faceted en vereist herkenningscontrole/confidence."
    )
    return IFCConversionResult(source, [target], warnings)


def _api_run(ifcopenshell: Any, usecase: str, model: Any | None = None, **settings: Any) -> Any:
    if model is None:
        return ifcopenshell.api.run(usecase, **settings)
    return ifcopenshell.api.run(usecase, model, **settings)


def _create_ifc_project(name: str):
    ifcopenshell = require_ifcopenshell()
    model = _api_run(ifcopenshell, "project.create_file", version="IFC4")
    project = _api_run(ifcopenshell, "root.create_entity", model, ifc_class="IfcProject", name=name)
    # Explicit SI metre units keep vertices and quantities unambiguous.
    try:
        length = _api_run(ifcopenshell, "unit.add_si_unit", model, unit_type="LENGTHUNIT")
        area = _api_run(ifcopenshell, "unit.add_si_unit", model, unit_type="AREAUNIT")
        volume = _api_run(ifcopenshell, "unit.add_si_unit", model, unit_type="VOLUMEUNIT")
        _api_run(ifcopenshell, "unit.assign_unit", model, units=[length, area, volume])
    except Exception:
        _api_run(ifcopenshell, "unit.assign_unit", model)

    model_context = _api_run(ifcopenshell, "context.add_context", model, context_type="Model")
    body = _api_run(
        ifcopenshell,
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    site = _api_run(ifcopenshell, "root.create_entity", model, ifc_class="IfcSite", name="Default Site")
    building = _api_run(ifcopenshell, "root.create_entity", model, ifc_class="IfcBuilding", name="Default Building")
    storey = _api_run(ifcopenshell, "root.create_entity", model, ifc_class="IfcBuildingStorey", name="Default Storey")
    _api_run(ifcopenshell, "aggregate.assign_object", model, products=[site], relating_object=project)
    _api_run(ifcopenshell, "aggregate.assign_object", model, products=[building], relating_object=site)
    _api_run(ifcopenshell, "aggregate.assign_object", model, products=[storey], relating_object=building)
    return ifcopenshell, model, body, storey


def _solid_meshes(shape: cq.Shape, tolerance: float = 0.5) -> list[tuple[cq.Shape, np.ndarray, np.ndarray]]:
    solids = list(shape.Solids())
    entities: list[cq.Shape] = solids or [shape]
    result = []
    for entity in entities:
        vertices, triangles = entity.tessellate(tolerance, 0.25)
        points = np.asarray([v.toTuple() for v in vertices], dtype=float)
        faces = np.asarray(triangles, dtype=int)
        if len(points) and len(faces):
            result.append((entity, points, faces))
    return result


def _classify_ifc_entity(shape: cq.Shape) -> str:
    box = shape.BoundingBox()
    dims = sorted((float(box.xlen), float(box.ylen), float(box.zlen)))
    if dims[0] <= max(30.0, 0.08 * dims[-1]) and dims[1] > 2.5 * dims[0]:
        return "IfcPlate"
    return "IfcMember"


def step_to_ifc(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
) -> IFCConversionResult:
    """Exporteer STEP als zichtbare IFC4 plus gehashte canonieke productiedata."""

    from conversion import __version__ as converter_version, step_to_nc1

    source, target = Path(input_path), Path(output_path)
    shape = cq.importers.importStep(str(source)).val()
    if not shape.Solids() and shape.Volume() <= 1e-9:
        raise ValueError("STEP-bestand bevat geen exporteerbare geometrie")

    warnings: list[str] = []
    canonical = extract_part_from_step(source, strict=False)
    if canonical is None:
        # Laat dezelfde gevalideerde plaat-/profielherkenning een canoniek model
        # opleveren. Dit voorkomt dubbele, afwijkende herkenningslogica.
        with tempfile.TemporaryDirectory(prefix="step_canonical_") as folder:
            nc1_path = Path(folder) / f"{source.stem}.nc1"
            try:
                result = step_to_nc1(
                    source,
                    nc1_path,
                    material=material,
                    order_number="STEP",
                    strict_validation=True,
                )
                canonical = extract_part_from_nc1(nc1_path, strict=True)
                if canonical is None:
                    raise ValueError("STEP→NC1 leverde geen canonieke payload")
                warnings.extend(result.warnings)
            except Exception as exc:
                # Complexe STEP kan nog steeds naar IFC/viewer/Excel; alleen de
                # automatische productie-NC1-fallback krijgt dan geen 100% claim.
                box = shape.BoundingBox()
                canonical = CanonicalPart(
                    converter_version=converter_version,
                    source_format="STEP",
                    source_file=source.name,
                    source_sha256=sha256_bytes(source.read_bytes()),
                    part_id=source.stem,
                    header=CanonicalHeader(
                        part_number=source.stem,
                        position_number=source.stem,
                        material=material,
                        quantity=1,
                        profile="UNKNOWN",
                        profile_type="",
                        length=max(float(box.xlen), float(box.ylen), float(box.zlen)),
                    ),
                    geometry={
                        "volume_mm3": float(shape.Volume()),
                        "area_mm2": float(shape.Area()),
                        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
                        "solids": len(shape.Solids()),
                    },
                    recognition={
                        "method": "STEP geometry only",
                        "confidence": 0.0,
                        "error": str(exc),
                    },
                    warnings=[
                        "STEP kon niet veilig als productie-NC1 worden herkend; "
                        "exacte STEP-bron is wel lossless bewaard."
                    ],
                )
                canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
                warnings.append(f"Canonieke productieherkenning niet voltooid: {exc}")

    if canonical.attachment("step") is None:
        canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
    canonical.validate()
    effective_material = canonical.material or material or "S355JR"
    write_native_ifc(
        shape,
        target,
        name=canonical.part_id or source.stem,
        material=effective_material,
        canonical=canonical,
        tolerance_mm=0.20,
    )
    warnings.append(
        "IFC bevat zichtbare IFC4-tessellatie (0,20 mm) én geverifieerde lossless "
        "Pset_NC1StepConverter-productiedata; roundtrip gebruikt niet de mesh."
    )
    return IFCConversionResult(source, [target], warnings)


def dstv_to_ifc(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
) -> IFCConversionResult:
    from conversion import convert_nc1_to_step

    source, target = Path(input_path), Path(output_path)
    with tempfile.TemporaryDirectory(prefix="nc1_ifc_") as folder:
        step_path = Path(folder) / f"{source.stem}.step"
        part = convert_nc1_to_step(source, step_path)
        result = step_to_ifc(step_path, target, material=part.header.material or material or "S355JR")
        result.source = source
        result.warnings = list(part.warnings) + result.warnings
        return result


def ifc_to_dstv(
    input_path: str | Path,
    output_directory: str | Path,
    *,
    material: str = "S355JR",
    order_number: str = "IFC",
    profile_database: Any = None,
    preferred_profile: str = "",
    tolerance_mm: float = 1.0,
    strict_validation: bool = True,
) -> IFCConversionResult:
    from conversion import build_shape, step_to_nc1
    import converter as core
    from profile_database import ProfileDatabase

    source, output = Path(input_path), Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    database = profile_database or ProfileDatabase()
    outputs: list[Path] = []
    failures: list[str] = []
    warnings: list[str] = []
    manifest_items: list[dict[str, Any]] = []

    canonical = extract_part_from_ifc(source, strict=False)
    if canonical is not None:
        nc1_bytes = canonical.attachment_bytes("nc1")
        if nc1_bytes is None and canonical.attachment_bytes("step") is not None:
            with tempfile.TemporaryDirectory(prefix="ifc_payload_dstv_") as folder:
                step_path = Path(folder) / (canonical.attachment("step").name or f"{source.stem}.step")
                step_path.write_bytes(canonical.attachment_bytes("step") or b"")
                embed_part_in_step(step_path, canonical)
                target_name = _safe_name(
                    canonical.header.part_number or canonical.part_id or source.stem,
                    source.stem,
                )
                target = output / f"{target_name}.nc1"
                try:
                    result = step_to_nc1(
                        step_path,
                        target,
                        material=canonical.material or material,
                        order_number=canonical.header.order_number or order_number,
                        profile_database=database,
                        preferred_profile=preferred_profile,
                        tolerance_mm=tolerance_mm,
                        strict_validation=strict_validation,
                    )
                    outputs.append(target)
                    warnings.extend(result.warnings)
                    manifest_items.append(
                        {
                            "guid": "canonical-payload",
                            "name": canonical.part_id,
                            "ifc_class": "converter-payload",
                            "output": target.name,
                            "profile": result.profile_designation,
                            "confidence": result.confidence,
                            "volume_delta_percent": result.volume_delta_percent,
                            "status": "converted-from-lossless-step-payload",
                        }
                    )
                except Exception as exc:
                    failures.append(f"Canonieke STEP-payload kon niet veilig naar NC1: {exc}")
        elif nc1_bytes is not None:
            target_name = _safe_name(
                canonical.header.part_number or canonical.part_id or source.stem,
                source.stem,
            )
            target = output / f"{target_name}.nc1"
            target.write_bytes(nc1_bytes)
            embed_part_in_nc1(target, canonical)
            try:
                part = core.parse_nc1(target)
                shape = build_shape(part).val()
                reconstructed_volume = float(shape.Volume())
                expected_volume = float(canonical.geometry.get("volume_mm3") or 0.0)
                volume_delta = (
                    (reconstructed_volume - expected_volume) / expected_volume * 100.0
                    if expected_volume > 1e-9
                    else 0.0
                )
                profile_type = part.header.profile_type
                failure_limit = 0.75 if profile_type in {"B", "I", "U", "C", "RU", "RO"} else 2.00
                if strict_validation and abs(volume_delta) > failure_limit:
                    target.unlink(missing_ok=True)
                    raise ValueError(
                        f"Veiligheidscontrole payload afgekeurd: volumeverschil {volume_delta:+.4f}% "
                        f"is groter dan {failure_limit:.2f}%."
                    )
                outputs.append(target)
                warnings.append(
                    f"{target.name}: NC1 lossless hersteld uit geverifieerde canonieke IFC-payload"
                )
                manifest_items.append(
                    {
                        "guid": "canonical-payload",
                        "name": canonical.part_id,
                        "ifc_class": "converter-payload",
                        "output": target.name,
                        "profile": part.header.profile,
                        "profile_type": profile_type,
                        "confidence": 1.0,
                        "volume_delta_percent": volume_delta,
                        "source_sha256": canonical.source_sha256,
                        "schema_version": canonical.schema_version,
                        "status": "converted-from-lossless-nc1-payload",
                    }
                )
            except Exception as exc:
                target.unlink(missing_ok=True)
                failures.append(f"Canonieke NC1-payload afgewezen: {exc}")

        manifest = output / f"{source.stem}_DSTV_manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "source": source.name,
                    "payload_detected": True,
                    "payload_schema": canonical.schema_version,
                    "source_format": canonical.source_format,
                    "source_sha256": canonical.source_sha256,
                    "converted": len(outputs),
                    "failed": len(failures),
                    "items": manifest_items,
                    "production_note": (
                        "Payload en checksums zijn gevalideerd; geometrische veiligheidscontrole blijft actief."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return IFCConversionResult(source, outputs + [manifest], warnings, failures)

    # Externe IFC zonder convertermetadata: geometrische fallback met confidence.
    model = load_ifc_geometry(source)
    warnings.extend(model.warnings)
    with tempfile.TemporaryDirectory(prefix="ifc_dstv_") as folder:
        temp = Path(folder)
        for index, item in enumerate(model.items, start=1):
            stem = _safe_name(item.tag or item.name or item.guid, f"element_{index:03d}")
            try:
                recognition = recognize_analytic_shape(
                    item.vertices_mm,
                    item.triangles,
                    minimum_confidence=0.92,
                    radial_tolerance_mm=0.35,
                )
                shape = recognition.shape
                if shape is None:
                    shape = mesh_to_cq_shape(item.vertices_mm, item.triangles, make_solid=True)
                if not shape.Solids() or shape.Volume() <= 1e-6:
                    raise ValueError("IFC-driehoeksgeometrie kon niet als gesloten solid worden opgebouwd")
                step_path = temp / f"{stem}.step"
                cq.exporters.export(shape, str(step_path), exportType="STEP")
                target = output / f"{stem}.nc1"
                result = step_to_nc1(
                    step_path,
                    target,
                    material=item.material_name or material,
                    order_number=order_number,
                    profile_database=database,
                    preferred_profile=preferred_profile,
                    tolerance_mm=tolerance_mm,
                    strict_validation=strict_validation,
                )
                outputs.append(target)
                warnings.extend(f"{stem}: {warning}" for warning in result.warnings)
                manifest_items.append(
                    {
                        "guid": item.guid,
                        "name": item.name,
                        "ifc_class": item.ifc_class,
                        "output": target.name,
                        "profile": result.profile_designation,
                        "confidence": result.confidence,
                        "volume_delta_percent": result.volume_delta_percent,
                        "analytic_recognition": recognition.kind,
                        "analytic_confidence": recognition.confidence,
                        "analytic_diagnostics": recognition.diagnostics,
                        "status": (
                            "converted-by-analytic-fallback"
                            if recognition.shape is not None
                            else "converted-by-geometric-fallback"
                        ),
                    }
                )
            except Exception as exc:
                message = f"{item.guid} / {item.name}: {exc}"
                failures.append(message)
                manifest_items.append(
                    {
                        "guid": item.guid,
                        "name": item.name,
                        "ifc_class": item.ifc_class,
                        "status": "not-convertible",
                        "error": str(exc),
                    }
                )
    manifest = output / f"{source.stem}_DSTV_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "source": source.name,
                "payload_detected": False,
                "converted": len(outputs),
                "failed": len(failures),
                "items": manifest_items,
                "production_note": (
                    "Externe IFC zonder converterpayload: controle in een DSTV-viewer/machinepostprocessor "
                    "en handmatige vrijgave blijven verplicht."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return IFCConversionResult(source, outputs + [manifest], warnings, failures)

