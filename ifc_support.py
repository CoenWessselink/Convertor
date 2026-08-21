"""IFC-ondersteuning met lossless converterpayload en veilige geometriefallback.

Converter-eigen IFC-bestanden worden altijd als een normale IFC4-tessellatie
weggeschreven, maar dragen daarnaast een versieerbaar, gehashte canonieke
productierepresentatie. Daardoor hoeven cirkels, gaten, bogen en profieltypes
bij een volgende converterstap niet opnieuw uit driehoeken te worden geraden.

IfcOpenShell blijft de voorkeurslezer voor willekeurige externe IFC-modellen.
Voor converter-eigen en eenvoudige externe ``IfcTriangulatedFaceSet``-bestanden
is een ingebouwde lezer beschikbaar, zodat de kernroutes niet stilvallen als de
optionele dependency in een broncode-omgeving ontbreekt. De Windows-release
behoort IfcOpenShell wel mee te leveren voor brede externe IFC-dekking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable

from cws_convertor.product import APP_VERSION

import cadquery as cq
import numpy as np

from analytic_fitting import recognize_analytic_shape
from canonical_model import (
    CanonicalHeader,
    CanonicalPart,
    CanonicalPayloadError,
    embed_part_in_step,
    extract_part_from_ifc,
    extract_part_from_nc1,
    extract_part_from_step,
    sha256_bytes,
)
from ifc_native import NativeIFCParseError, parse_native_ifc_meshes, write_native_ifc


class IFCDependencyError(RuntimeError):
    """IfcOpenShell is nodig voor deze specifieke externe IFC-representatie."""


def require_ifcopenshell():
    try:
        import ifcopenshell  # type: ignore
        import ifcopenshell.api  # type: ignore
        import ifcopenshell.geom  # type: ignore
        import ifcopenshell.util.element  # type: ignore
        import ifcopenshell.util.unit  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency is optional in source environment
        raise IFCDependencyError(
            "Dit externe IFC-bestand vereist IfcOpenShell. De uiteindelijke Windows-release "
            "levert die dependency mee; installeer voor broncodegebruik de vastgelegde "
            "requirements of gebruik een converter-eigen IFC met ingebouwde payload."
        ) from exc
    return ifcopenshell


def ifcopenshell_available() -> bool:
    try:
        require_ifcopenshell()
        return True
    except IFCDependencyError:
        return False


def ifc_available() -> bool:
    """De IFC-kern is beschikbaar; brede externe dekking vraagt IfcOpenShell."""

    return True


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
        return tuple(sorted((float(value) for value in lengths), reverse=True))


@dataclass
class IFCModelData:
    source: Path
    schema: str
    project_name: str
    items: list[IFCGeometryItem]
    warnings: list[str] = field(default_factory=list)
    reader: str = ""


@dataclass
class IFCConversionResult:
    source: Path
    outputs: list[Path]
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def primary_output(self) -> Path | None:
        return self.outputs[0] if self.outputs else None


def mesh_area(vertices: np.ndarray, triangles: np.ndarray) -> float:
    if len(vertices) == 0 or len(triangles) == 0:
        return 0.0
    polygons = vertices[triangles]
    cross = np.cross(polygons[:, 1] - polygons[:, 0], polygons[:, 2] - polygons[:, 0])
    return float(np.linalg.norm(cross, axis=1).sum() * 0.5)


def mesh_volume(vertices: np.ndarray, triangles: np.ndarray) -> float:
    if len(vertices) == 0 or len(triangles) == 0:
        return 0.0
    polygons = vertices[triangles]
    signed = np.einsum(
        "ij,ij->i",
        polygons[:, 0],
        np.cross(polygons[:, 1], polygons[:, 2]),
    ).sum() / 6.0
    return abs(float(signed))


def _percent_delta(reference: float, candidate: float) -> float:
    return (candidate - reference) / reference * 100.0 if abs(reference) > 1e-12 else 0.0


def _flatten_properties(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _flatten_properties(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_flatten_properties(item) for item in value]
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
        material = util_element.get_material(
            element,
            should_skip_usage=True,
            should_inherit=True,
        )
        return str(getattr(material, "Name", "") or "")
    except Exception:
        return ""


def _load_native_geometry(source: Path) -> IFCModelData:
    meshes = parse_native_ifc_meshes(source)
    payload = extract_part_from_ifc(source, strict=False)
    properties: dict[str, Any] = {}
    if payload is not None:
        properties["Pset_NC1StepConverter"] = {
            "SchemaVersion": payload.schema_version,
            "ConverterVersion": payload.converter_version,
            "SourceFormat": payload.source_format,
            "SourceFile": payload.source_file,
            "SourceSHA256": payload.source_sha256,
            "PartId": payload.part_id,
            "ProfileDesignation": payload.profile_designation,
            "ProfileType": payload.profile_type,
            "MaterialGrade": payload.material,
            "Quantity": payload.quantity,
            "PayloadValidated": True,
        }
    items = [
        IFCGeometryItem(
            guid=mesh.guid,
            name=mesh.name,
            ifc_class=mesh.ifc_class,
            tag=mesh.name,
            material_name=mesh.material or (payload.material if payload else ""),
            vertices_mm=mesh.vertices_mm,
            triangles=mesh.triangles,
            properties=dict(properties),
            quantities={},
        )
        for mesh in meshes
    ]
    warnings = [
        "IFC gelezen met ingebouwde IfcTriangulatedFaceSet-lezer; "
        "converterpayload is leidend voor productieconversies."
    ]
    return IFCModelData(source, "IFC4", source.stem, items, warnings, reader="native")


def _load_ifcopenshell_geometry(source: Path) -> IFCModelData:
    ifcopenshell = require_ifcopenshell()
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
    project_name = (
        str(getattr(projects[0], "Name", "") or source.stem)
        if projects
        else source.stem
    )
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
            vertices = np.asarray(geometry.verts, dtype=float).reshape((-1, 3)) * 1000.0
            faces = np.asarray(geometry.faces, dtype=int).reshape((-1, 3))
            if len(vertices) < 3 or len(faces) < 1:
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
            properties = {
                key: value
                for key, value in psets.items()
                if key not in quantities
            }
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
                    vertices_mm=vertices,
                    triangles=faces,
                    properties=_flatten_properties(properties),
                    quantities=_flatten_properties(quantities),
                )
            )
        except Exception as exc:
            warnings.append(
                f"{getattr(element, 'GlobalId', index)} ({element.is_a()}): "
                f"geometrie niet gelezen: {exc}"
            )
    if not items:
        detail = f" Waarschuwingen: {'; '.join(warnings[:3])}" if warnings else ""
        raise ValueError(
            f"Geen renderbare IfcElement-geometrie gevonden in {source.name}.{detail}"
        )
    return IFCModelData(
        source,
        str(getattr(model, "schema", "IFC")),
        project_name,
        items,
        warnings,
        reader="ifcopenshell",
    )


def _load_internal_occt_geometry(source: Path) -> IFCModelData:
    """Read common swept/BREP IFC geometry with the bundled Viewer V15 core."""

    import hashlib

    from cws_convertor.importers.ifc_project import IfcPlacementResolver
    from cws_convertor.importers.p21 import P21Document
    from cws_viewer.geometry.ifc_provider import (
        GeometryRequest,
        IfcMeshProvider,
        TessellationSettings,
        _detect_units,
    )

    document = P21Document.load(source)
    units = _detect_units(document)
    placements = IfcPlacementResolver(document, units)
    provider = IfcMeshProvider()
    settings = TessellationSettings(linear_deflection_mm=1.5, angular_deflection_rad=0.35)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    denied_tokens = (
        "REPRESENTATION", "REL", "PROPERTY", "QUANTITY", "STYLE",
        "MATERIAL", "PLACEMENT", "OWNERHISTORY", "CONTEXT", "PROFILE",
    )
    denied_types = {
        "IFCPROJECT", "IFCSITE", "IFCBUILDING", "IFCBUILDINGSTOREY",
        "IFCOPENINGELEMENT", "IFCSPACE", "IFCANNOTATION", "IFCGRID",
    }
    candidates = [
        (entity_id, entity)
        for entity_id, entity in document.entities.items()
        if entity.type_name.startswith("IFC")
        and entity.type_name not in denied_types
        and not any(token in entity.type_name for token in denied_tokens)
        and entity.ref(6) is not None
    ]
    items: list[IFCGeometryItem] = []
    warnings: list[str] = []
    for entity_id, entity in candidates:
        request = GeometryRequest(
            geometry_id=f"ifc:{source_hash}:{entity_id}",
            source_geometry_hash=source_hash,
            source_format="IFC",
            source_file_id=source.name,
            source_path=str(source),
            source_sha256=source_hash,
            source_entity_id=f"#{entity_id}",
        )
        try:
            mesh = provider.load(request, settings)
            if mesh is None or len(mesh.vertices) < 3 or len(mesh.triangles) < 1:
                continue
            vertices = np.asarray(mesh.vertices, dtype=float)
            placement_id = entity.ref(5)
            if placement_id is not None:
                _local, global_placement = placements.local_placement(placement_id)
                matrix = np.asarray(global_placement.matrix, dtype=float)
                homogeneous = np.column_stack((vertices, np.ones(len(vertices), dtype=float)))
                vertices = (homogeneous @ matrix.T)[:, :3]
            items.append(
                IFCGeometryItem(
                    guid=entity.string(0, "") or f"ifc-{entity_id}",
                    name=entity.string(2, "") or f"{entity.type_name} #{entity_id}",
                    ifc_class=entity.type_name,
                    tag=entity.string(7, ""),
                    material_name="",
                    vertices_mm=vertices,
                    triangles=np.asarray(mesh.triangles, dtype=int),
                    properties={
                        "reader": "viewer-v15-internal-occt",
                        "source_entity_id": f"#{entity_id}",
                        "material_recognition": "manual_required",
                    },
                    quantities={},
                    warnings=list(mesh.warnings),
                )
            )
        except Exception as exc:
            if len(warnings) < 40:
                warnings.append(f"#{entity_id} ({entity.type_name}): {exc}")
    if not items:
        detail = f" Waarschuwingen: {'; '.join(warnings[:3])}" if warnings else ""
        raise ValueError(f"Viewer V15 kon geen ondersteunde IFC-productgeometrie opbouwen.{detail}")
    warnings.insert(
        0,
        "IFC gelezen met de interne Viewer V15/OCCT-fallback; materiaalgrade blijft handmatig tot bronbewijs beschikbaar is.",
    )
    return IFCModelData(
        source,
        document.schema or "IFC",
        source.stem,
        items,
        warnings,
        reader="viewer-v15-internal-occt",
    )


def load_ifc_geometry(path: str | Path) -> IFCModelData:
    """Lees IFC-geometrie via IfcOpenShell of de ingebouwde tessellatielezer."""

    source = Path(path)
    errors: list[str] = []
    if ifcopenshell_available():
        try:
            return _load_ifcopenshell_geometry(source)
        except Exception as exc:
            errors.append(f"IfcOpenShell: {exc}")
    try:
        model = _load_native_geometry(source)
        if errors:
            model.warnings.insert(0, "Fallback na " + "; ".join(errors))
        return model
    except Exception as native_exc:
        errors.append(f"ingebouwde IFC-lezer: {native_exc}")
    try:
        model = _load_internal_occt_geometry(source)
        if errors:
            model.warnings.insert(0, "Fallback na " + "; ".join(errors))
        return model
    except Exception as internal_exc:
        errors.append(f"Viewer V15/OCCT: {internal_exc}")
    raise IFCDependencyError(
        f"IFC-geometrie van {source.name} kon niet worden gelezen. " + "; ".join(errors)
    )


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
    bbox = tuple(sorted((float(value) for value in np.ptp(points, axis=0)), reverse=True))
    metrics = {
        "volume": sum(item.volume_mm3 for item in model.items),
        "area": sum(item.area_mm2 for item in model.items),
        "bbox": bbox,
        "solids": len(model.items),
        "items": len(model.items),
        "warnings": model.warnings,
        "reader": model.reader,
    }
    return points, faces, metrics


def mesh_to_cq_shape(
    vertices_mm: np.ndarray,
    triangles: np.ndarray,
    *,
    make_solid: bool = True,
) -> cq.Shape:
    """Maak een (bij voorkeur gesloten) Open CASCADE-vorm uit een mesh."""

    faces: list[cq.Face] = []
    for triangle in np.asarray(triangles, dtype=int):
        points = [cq.Vector(*map(float, vertices_mm[int(index)])) for index in triangle]
        if (points[1] - points[0]).cross(points[2] - points[0]).Length <= 1e-10:
            continue
        try:
            wire = cq.Wire.makePolygon(points, close=True)
            faces.append(cq.Face.makeFromWires(wire))
        except Exception:
            continue
    if not faces:
        raise ValueError("IFC-mesh bevat geen geldige driehoeksvlakken")

    try:
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing

        sewer = BRepBuilderAPI_Sewing(1e-5, True, True, True, False)
        for face in faces:
            sewer.Add(face.wrapped)
        sewer.Perform()
        sewn = cq.Shape.cast(sewer.SewedShape())
        if make_solid:
            solids: list[cq.Solid] = []
            for shell in sewn.Shells():
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


def _shape_metrics(shape: cq.Shape) -> dict[str, Any]:
    box = shape.BoundingBox()
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": [float(box.xlen), float(box.ylen), float(box.zlen)],
        "solids": len(shape.Solids()),
    }


def _minimal_step_canonical(
    source: Path,
    shape: cq.Shape,
    material: str,
    warning: str,
) -> CanonicalPart:
    metrics = _shape_metrics(shape)
    canonical = CanonicalPart(
        converter_version=APP_VERSION,
        source_format="STEP",
        source_file=source.name,
        source_sha256=sha256_bytes(source.read_bytes()),
        part_id=source.stem,
        header=CanonicalHeader(
            part_number=source.stem,
            position_number=source.stem,
            material=material,
            quantity=1,
        ),
        warnings=[warning],
        geometry=metrics,
        recognition={
            "method": "unclassified analytic STEP",
            "confidence": 0.0,
            "production_nc1_allowed": False,
        },
    )
    canonical.add_attachment("step", source.name, "model/step", source.read_bytes())
    return canonical


def _canonical_for_step(
    source: Path,
    shape: cq.Shape,
    *,
    material: str,
) -> tuple[CanonicalPart, list[str]]:
    """Maak/haal een canoniek object; probeer veilige NC1-herkenning voor extern STEP."""

    existing = extract_part_from_step(source, strict=False)
    if existing is not None:
        warnings = ["Bestaande geverifieerde STEP-payload overgenomen."]
        if existing.attachment("step") is None:
            existing = existing.clone()
            existing.add_attachment("step", source.name, "model/step", source.read_bytes())
        return existing, warnings

    warnings: list[str] = []
    try:
        from conversion import step_to_nc1
        from profile_database import ProfileDatabase

        with tempfile.TemporaryDirectory(prefix="step_ifc_canonical_") as folder:
            nc1_path = Path(folder) / f"{source.stem}.nc1"
            result = step_to_nc1(
                source,
                nc1_path,
                material=material,
                order_number="STEP",
                profile_database=ProfileDatabase(),
                strict_validation=True,
                embed_converter_payload=True,
            )
            canonical = extract_part_from_nc1(nc1_path, strict=True)
            if canonical is None:
                raise CanonicalPayloadError("STEP→NC1 leverde geen canonieke payload")
            canonical = canonical.clone()
            canonical.recognition.update(
                {
                    "method": result.matched_by,
                    "confidence": float(result.confidence),
                    "profile": result.profile_designation,
                    "volume_delta_percent": float(result.volume_delta_percent),
                    "production_nc1_allowed": True,
                }
            )
            canonical.warnings.extend(result.warnings)
            warnings.append(
                "Extern STEP veilig geclassificeerd en als canonieke productiedata in IFC opgenomen."
            )
            return canonical, warnings
    except Exception as exc:
        warning = (
            "STEP kon niet veilig als DSTV-plaat/profiel worden geclassificeerd; "
            f"IFC bevat wel de exacte STEP-bijlage, maar automatische IFC→NC1 blijft geblokkeerd: {exc}"
        )
        warnings.append(warning)
        return _minimal_step_canonical(source, shape, material, warning), warnings


def _validate_ifc_preview_against_shape(
    source: Path,
    shape: cq.Shape,
    *,
    failure_limit_percent: float = 1.0,
) -> tuple[float | None, list[str]]:
    warnings: list[str] = []
    try:
        model = load_ifc_geometry(source)
        mesh_total = sum(item.volume_mm3 for item in model.items)
        shape_volume = float(shape.Volume())
        delta = _percent_delta(shape_volume, mesh_total)
        if abs(delta) > failure_limit_percent:
            raise ValueError(
                f"IFC-preview wijkt {delta:+.6f}% in volume af van de geverifieerde analytische vorm "
                f"(grens {failure_limit_percent:.3f}%)."
            )
        if abs(delta) > 0.05:
            warnings.append(
                f"IFC-preview is getesselleerd: volumeverschil t.o.v. analytische vorm {delta:+.6f}%."
            )
        return delta, warnings
    except IFCDependencyError as exc:
        warnings.append(f"Previewvolume niet gecontroleerd: {exc}")
        return None, warnings


def _load_external_exact_ifc_shapes(
    source: Path,
) -> tuple[list[cq.Shape], list[str], list[str], dict[str, Any]]:
    """Build source-parametric IFC BReps without a triangle-by-triangle STEP path."""

    from cws_convertor.importers.ifc_project import IfcPlacementResolver, _detect_units
    from cws_convertor.importers.p21 import P21Document
    from cws_viewer.contracts.geometry import TessellationSettings
    from cws_viewer.exact.ifc_profiles import ExactIfcShapeBuilder
    from cws_viewer.geometry.ifc_provider import IfcMeshProvider

    document = P21Document.load(source)
    units = _detect_units(document)
    placements = IfcPlacementResolver(document, units)
    builder = ExactIfcShapeBuilder(document, TessellationSettings())
    scale = float(units.length_to_mm)
    shapes: list[cq.Shape] = []
    failures: list[str] = []
    products = 0
    body_items = 0
    for entity in document.entities.values():
        if not entity.type_name.startswith("IFC"):
            continue
        items = IfcMeshProvider._product_items(document, f"#{entity.entity_id}")
        if not items:
            continue
        products += 1
        body_items += len(items)
        try:
            _relative, global_placement = placements.local_placement(entity.ref(5))
            combined_matrix = [list(row) for row in global_placement.matrix]
            for row in range(3):
                for column in range(3):
                    combined_matrix[row][column] *= scale
            placement_matrix = cq.Matrix(combined_matrix)
        except Exception as exc:
            failures.append(
                f"#{entity.entity_id} {entity.type_name}: plaatsing niet opgebouwd ({exc})"
            )
            continue
        for item_id in items:
            try:
                shape = builder.build(item_id)
                shapes.append(shape.transformGeometry(placement_matrix))
            except Exception as exc:
                failures.append(
                    f"#{entity.entity_id}/#{item_id} {entity.type_name}: {exc}"
                )

    warnings = list(dict.fromkeys(str(value) for value in builder.warnings if str(value)))
    details = {
        "route": "external-source-parametric-brep",
        "products": products,
        "body_items": body_items,
        "shape_count": len(shapes),
        "units_to_mm": scale,
    }
    return shapes, warnings, failures, details


def ifc_to_step(input_path: str | Path, output_path: str | Path) -> IFCConversionResult:
    source, target = Path(input_path), Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []

    payload = extract_part_from_ifc(source, strict=False)
    if payload is not None:
        step_bytes = payload.attachment_bytes("step")
        if step_bytes is not None:
            target.write_bytes(step_bytes)
            embed_part_in_step(target, payload)
            restored_shape = cq.importers.importStep(str(target)).val()
            preview_delta, preview_warnings = _validate_ifc_preview_against_shape(
                source,
                restored_shape,
                failure_limit_percent=1.0,
            )
            warnings.extend(preview_warnings)
            warnings.insert(
                0,
                "Analytische STEP lossless hersteld uit geverifieerde IFC-converterpayload; "
                "de IFC-tessellatie is niet gebruikt voor featureherkenning.",
            )
            return IFCConversionResult(
                source,
                [target],
                warnings,
                details={
                    "route": "payload-step",
                    "payload_schema": payload.schema_version,
                    "source_sha256": payload.source_sha256,
                    "preview_volume_delta_percent": preview_delta,
                },
            )
        nc1_bytes = payload.attachment_bytes("nc1")
        if nc1_bytes is not None:
            from conversion import convert_nc1_to_step

            with tempfile.TemporaryDirectory(prefix="ifc_step_payload_") as folder:
                nc1_path = Path(folder) / (payload.source_file or f"{payload.part_id}.nc1")
                if nc1_path.suffix.lower() not in {".nc", ".nc1"}:
                    nc1_path = nc1_path.with_suffix(".nc1")
                nc1_path.write_bytes(nc1_bytes)
                convert_nc1_to_step(nc1_path, target)
            warnings.append(
                "STEP analytisch herbouwd uit de geverifieerde NC1-bijlage van de IFC-payload."
            )
            return IFCConversionResult(
                source,
                [target],
                warnings,
                details={"route": "payload-nc1", "payload_schema": payload.schema_version},
            )

    # Voor externe IFC heeft IfcConvert voorrang omdat die meer analytische IFC-
    # representaties kan behouden dan een driehoeksfallback.
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
                details={"route": "IfcConvert"},
            )
        warnings.append(
            "IfcConvert viel terug op faceted export: "
            + (process.stderr.strip() or process.stdout.strip())
        )

    exact_route_warnings: list[str] = []
    try:
        exact_shapes, exact_warnings, exact_failures, exact_details = (
            _load_external_exact_ifc_shapes(source)
        )
        if exact_shapes and not exact_failures:
            _export_shapes_step(exact_shapes, target)
            return IFCConversionResult(
                source=source,
                outputs=[target],
                warnings=exact_warnings,
                failures=[],
                details=exact_details,
            )
        if exact_failures:
            exact_route_warnings.append(
                "Exacte IFC-BRep-route niet volledig; facettenfallback gebruikt. "
                f"{len(exact_failures)} Body-item(s) konden niet exact worden opgebouwd."
            )
            exact_route_warnings.extend(exact_failures[:20])
    except Exception as exc:
        exact_route_warnings.append(
            f"Exacte IFC-BRep-route niet beschikbaar; facettenfallback gebruikt: {exc}"
        )

    model = load_ifc_geometry(source)
    model.warnings[:0] = exact_route_warnings
    shapes: list[cq.Shape] = []
    analytic_items: list[dict[str, Any]] = []
    for item in model.items:
        recognition = recognize_analytic_shape(
            item.vertices_mm,
            item.triangles,
            minimum_confidence=0.92,
            radial_tolerance_mm=0.35,
        )
        analytic_items.append(
            {
                "guid": item.guid,
                "kind": recognition.kind,
                "confidence": float(recognition.confidence),
                "diagnostics": recognition.diagnostics,
                "accepted": recognition.shape is not None,
            }
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
        "overige geometrie blijft faceted en productieconversie blijft onder de strenge "
        "veiligheidscontrole en confidence-vrijgave."
    )
    return IFCConversionResult(
        source,
        [target],
        warnings,
        details={
            "route": "external-analytic-or-mesh",
            "reader": model.reader,
            "analytic_items": analytic_items,
        },
    )


def step_to_ifc(
    input_path: str | Path,
    output_path: str | Path,
    *,
    material: str = "S355JR",
) -> IFCConversionResult:
    """Schrijf IFC4-previewgeometrie plus exact canoniek productieobject."""

    source, target = Path(input_path), Path(output_path)
    shape = cq.importers.importStep(str(source)).val()
    if not shape.Solids() or shape.Volume() <= 1e-6:
        raise ValueError("STEP-bestand bevat geen exporteerbare gesloten geometrie")
    canonical, warnings = _canonical_for_step(source, shape, material=material)
    write_native_ifc(
        shape,
        target,
        name=canonical.part_id or source.stem,
        material=canonical.material or material,
        canonical=canonical,
        tolerance_mm=0.20,
    )
    preview_delta, preview_warnings = _validate_ifc_preview_against_shape(
        target,
        shape,
        failure_limit_percent=1.0,
    )
    warnings.extend(preview_warnings)
    warnings.append(
        "IFC bevat zichtbare tessellatie én Pset_NC1StepConverter met gehashte canonieke payload."
    )
    return IFCConversionResult(
        source,
        [target],
        warnings,
        details={
            "route": "native-ifc4-with-payload",
            "payload_schema": canonical.schema_version,
            "payload_source_format": canonical.source_format,
            "payload_source_sha256": canonical.source_sha256,
            "recognition_confidence": canonical.recognition.get("confidence"),
            "preview_volume_delta_percent": preview_delta,
        },
    )


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
        result = step_to_ifc(
            step_path,
            target,
            material=material or part.header.material or "S355JR",
        )
        result.source = source
        result.warnings = list(part.warnings) + result.warnings
        result.details["route"] = "nc1->analytic-step->ifc-payload"
        return result


def _payload_nc1_target(payload: CanonicalPart, output: Path, source: Path) -> Path:
    candidate = payload.part_id or Path(payload.source_file).stem or source.stem
    return output / f"{_safe_name(candidate, source.stem)}.nc1"


def _validate_payload_nc1(
    payload: CanonicalPart,
    nc1_path: Path,
    *,
    strict_validation: bool,
) -> tuple[dict[str, Any], list[str]]:
    from conversion import build_shape
    import converter as core

    part = core.parse_nc1(nc1_path)
    shape = build_shape(part).val()
    metrics = _shape_metrics(shape)
    warnings = list(part.warnings)
    expected_volume = float(payload.geometry.get("volume_mm3") or 0.0)
    delta = None
    if expected_volume > 0:
        delta = _percent_delta(expected_volume, float(metrics["volume_mm3"]))
        if abs(delta) > 0.001:
            warnings.append(
                f"Canonieke volumecontrole: {delta:+.9f}% verschil tussen payload en NC1-reconstructie."
            )
        if strict_validation and abs(delta) > 0.05:
            raise ValueError(
                f"Veiligheidscontrole payload afgekeurd: volumeverschil {delta:+.6f}% "
                "is groter dan 0,05%."
            )
    return {
        "profile": part.header.profile,
        "profile_type": part.header.profile_type,
        "part_number": part.header.part_number,
        "material": part.header.material,
        "quantity": part.header.quantity,
        "holes": len(part.holes),
        "contours": len(part.contours),
        "volume_mm3": metrics["volume_mm3"],
        "area_mm2": metrics["area_mm2"],
        "bbox_mm": metrics["bbox_mm"],
        "payload_volume_delta_percent": delta,
    }, warnings


def _write_manifest(
    path: Path,
    *,
    source: Path,
    outputs: list[Path],
    failures: list[str],
    items: list[dict[str, Any]],
    route: str,
) -> Path:
    path.write_text(
        json.dumps(
            {
                "source": source.name,
                "source_sha256": sha256_bytes(source.read_bytes()),
                "route": route,
                "converted": len([output for output in outputs if output.suffix.lower() in {".nc", ".nc1"}]),
                "failed": len(failures),
                "items": items,
                "production_note": (
                    "Automatische uitvoer is door de volumebeveiliging gegaan. "
                    "Controle in de gebruikte DSTV-viewer/machinepostprocessor blijft verplicht."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


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
    from conversion import step_to_nc1
    from profile_database import ProfileDatabase

    source, output = Path(input_path), Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    database = profile_database or ProfileDatabase()
    outputs: list[Path] = []
    failures: list[str] = []
    warnings: list[str] = []
    manifest_items: list[dict[str, Any]] = []

    payload = extract_part_from_ifc(source, strict=False)
    if payload is not None:
        target = _payload_nc1_target(payload, output, source)
        try:
            nc1_bytes = payload.attachment_bytes("nc1")
            if nc1_bytes is not None:
                target.write_bytes(nc1_bytes)
                metrics, item_warnings = _validate_payload_nc1(
                    payload,
                    target,
                    strict_validation=strict_validation,
                )
                outputs.append(target)
                warnings.extend(item_warnings)
                warnings.insert(
                    0,
                    "NC1 lossless hersteld uit geverifieerde IFC-converterpayload; "
                    "de getesselleerde IFC-preview is niet gebruikt voor featureherkenning.",
                )
                manifest_items.append(
                    {
                        "status": "converted",
                        "route": "payload-nc1",
                        "output": target.name,
                        "payload_schema": payload.schema_version,
                        "payload_source_format": payload.source_format,
                        "payload_source_sha256": payload.source_sha256,
                        "recognition": payload.recognition,
                        **metrics,
                    }
                )
            else:
                step_bytes = payload.attachment_bytes("step")
                if step_bytes is None:
                    raise ValueError(
                        "Geldige IFC-payload bevat geen NC1- of STEP-bijlage voor productieherstel."
                    )
                if payload.recognition.get("production_nc1_allowed") is False:
                    raise ValueError(
                        "IFC-payload markeert dit onderdeel als niet veilig automatisch naar NC1 te converteren."
                    )
                with tempfile.TemporaryDirectory(prefix="ifc_dstv_payload_") as folder:
                    step_path = Path(folder) / f"{source.stem}.step"
                    step_path.write_bytes(step_bytes)
                    result = step_to_nc1(
                        step_path,
                        target,
                        material=payload.material or material,
                        order_number=order_number,
                        profile_database=database,
                        preferred_profile=preferred_profile,
                        tolerance_mm=tolerance_mm,
                        strict_validation=strict_validation,
                    )
                metrics, item_warnings = _validate_payload_nc1(
                    payload,
                    target,
                    strict_validation=strict_validation,
                )
                outputs.append(target)
                warnings.extend(result.warnings)
                warnings.extend(item_warnings)
                manifest_items.append(
                    {
                        "status": "converted",
                        "route": "payload-step-to-nc1",
                        "output": target.name,
                        "profile": result.profile_designation,
                        "confidence": result.confidence,
                        "recognition": payload.recognition,
                        **metrics,
                    }
                )
        except Exception as exc:
            target.unlink(missing_ok=True)
            failures.append(f"{payload.part_id or source.stem}: {exc}")
            manifest_items.append(
                {
                    "status": "not-convertible",
                    "route": "payload",
                    "part_id": payload.part_id,
                    "error": str(exc),
                }
            )
        manifest = _write_manifest(
            output / f"{source.stem}_DSTV_manifest.json",
            source=source,
            outputs=outputs,
            failures=failures,
            items=manifest_items,
            route="converter-payload",
        )
        return IFCConversionResult(
            source,
            outputs + [manifest],
            warnings,
            failures,
            details={
                "route": "converter-payload",
                "payload_schema": payload.schema_version,
                "payload_source_format": payload.source_format,
            },
        )

    # Externe IFC zonder payload: geometrie per element converteren. Dit pad
    # blijft strikt en mag onzekere featureherkenning niet stilzwijgend vrijgeven.
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
                    raise ValueError(
                        "IFC-driehoeksgeometrie kon niet als gesloten solid worden opgebouwd"
                    )
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
                        "analytic_confidence": float(recognition.confidence),
                        "analytic_diagnostics": recognition.diagnostics,
                        "status": (
                            "converted-by-analytic-fallback"
                            if recognition.shape is not None
                            else "converted-by-geometric-fallback"
                        ),
                        "route": "external-analytic-or-geometry-fallback",
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
                        "route": "external-analytic-or-geometry-fallback",
                        "error": str(exc),
                    }
                )
    manifest = _write_manifest(
        output / f"{source.stem}_DSTV_manifest.json",
        source=source,
        outputs=outputs,
        failures=failures,
        items=manifest_items,
        route="external-analytic-or-geometry-fallback",
    )
    return IFCConversionResult(
        source,
        outputs + [manifest],
        warnings,
        failures,
        details={"route": "external-analytic-or-geometry-fallback", "reader": model.reader},
    )
