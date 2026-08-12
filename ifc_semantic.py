"""Semantic IFC4 writer for validated canonical plate parts.

The converter-native IFC writer remains available as a universal tessellation
fallback.  This module adds a production-oriented representation for plates:

* ``IfcPlate`` product semantics;
* ``IfcExtrudedAreaSolid`` with an exact 2D outer profile;
* analytical ``IfcCircle`` inner curves for through-holes;
* ``IfcIndexedPolyCurve`` arc segments for rounded contour vertices;
* an additional tessellated fallback representation for dependency-light
  preview and volume checks;
* the complete, hashed canonical payload in ``Pset_NC1StepConverter``.

All dimensions are supplied by the validated canonical model; this writer does
not infer or alter production geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime as _dt
import math
import uuid
from typing import Iterable

import cadquery as cq
import numpy as np

from canonical_model import (
    PAYLOAD_CODEC,
    CanonicalContour,
    CanonicalPart,
    embed_part_in_ifc_text,
    encode_part,
    sha256_bytes,
)

_IFC_GUID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"


class SemanticIFCError(ValueError):
    """Canonical data cannot safely be represented by this semantic writer."""


@dataclass(frozen=True)
class _RoundedVertex:
    tangent_in: np.ndarray
    tangent_out: np.ndarray
    center: np.ndarray
    start_angle_rad: float
    extent_rad: float


def _guid22(seed: str) -> str:
    number = int.from_bytes(uuid.uuid5(uuid.NAMESPACE_URL, seed).bytes, "big")
    chars = ["0"] * 22
    for index in range(21, -1, -1):
        chars[index] = _IFC_GUID_ALPHABET[number & 0x3F]
        number >>= 6
    return "".join(chars)


def _escape(value: object) -> str:
    return str(value).replace("'", "''")


def _real(value: float) -> str:
    if not math.isfinite(float(value)):
        raise SemanticIFCError("IFC-getal is niet eindig")
    text = f"{float(value):.12g}"
    if "e" not in text.lower() and "." not in text:
        text += "."
    return text


def _chunk(text: str, size: int = 1800) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def _rounded_vertex(
    previous: np.ndarray,
    current: np.ndarray,
    following: np.ndarray,
    radius: float,
) -> _RoundedVertex | None:
    incoming = previous - current
    outgoing = following - current
    lin = float(np.linalg.norm(incoming))
    lout = float(np.linalg.norm(outgoing))
    if radius <= 0 or lin <= 1e-9 or lout <= 1e-9:
        return None
    incoming /= lin
    outgoing /= lout
    cosine = float(np.clip(np.dot(incoming, outgoing), -1.0, 1.0))
    angle = math.acos(cosine)
    if angle <= 1e-6 or abs(math.pi - angle) <= 1e-6:
        return None
    tangent_distance = radius / math.tan(angle / 2.0)
    if tangent_distance > lin * 0.499 or tangent_distance > lout * 0.499:
        raise SemanticIFCError(
            f"Contourradius {radius:g} mm past niet tussen aangrenzende contoursegmenten"
        )
    actual_radius = tangent_distance * math.tan(angle / 2.0)
    tangent_in = current + incoming * tangent_distance
    tangent_out = current + outgoing * tangent_distance
    bisector = incoming + outgoing
    bnorm = float(np.linalg.norm(bisector))
    if bnorm <= 1e-9:
        return None
    bisector /= bnorm
    center = current + bisector * (actual_radius / math.sin(angle / 2.0))
    start = math.atan2(tangent_in[1] - center[1], tangent_in[0] - center[0])
    end = math.atan2(tangent_out[1] - center[1], tangent_out[0] - center[0])
    cross = float(np.cross(np.append(tangent_in - center, 0.0), np.append(tangent_out - center, 0.0))[2])
    if cross >= 0:
        extent = (end - start) % (2.0 * math.pi)
    else:
        extent = -((start - end) % (2.0 * math.pi))
    if abs(extent) > math.pi:
        extent = extent - 2.0 * math.pi if extent > 0 else extent + 2.0 * math.pi
    return _RoundedVertex(tangent_in, tangent_out, center, start, extent)


def _contour_points(part: CanonicalPart) -> tuple[list[np.ndarray], list[float]]:
    contour: CanonicalContour | None = next(
        (item for item in part.contours if item.kind.upper() not in {"IK", "INNER"}),
        part.contours[0] if part.contours else None,
    )
    if contour is None or len(contour.points) < 3:
        length = float(part.header.length)
        width = float(part.header.dim1)
        if length <= 0 or width <= 0:
            raise SemanticIFCError("Semantische plaat-IFC vereist een gesloten buitencontour")
        return (
            [
                np.asarray((0.0, 0.0)),
                np.asarray((length, 0.0)),
                np.asarray((length, width)),
                np.asarray((0.0, width)),
            ],
            [0.0, 0.0, 0.0, 0.0],
        )
    points = [np.asarray((float(item.x), float(item.q)), dtype=float) for item in contour.points]
    radii = [max(0.0, float(item.radius)) for item in contour.points]
    if len(points) > 3 and float(np.linalg.norm(points[0] - points[-1])) <= 1e-7:
        points.pop()
        radii.pop()
    if len(points) < 3:
        raise SemanticIFCError("Buitencontour bevat minder dan drie unieke punten")
    return points, radii


def _indexed_curve_data(part: CanonicalPart) -> tuple[list[np.ndarray], list[tuple[str, tuple[int, ...]]]]:
    vertices, radii = _contour_points(part)
    rounded: list[_RoundedVertex | None] = []
    for index, current in enumerate(vertices):
        rounded.append(
            _rounded_vertex(
                vertices[index - 1],
                current,
                vertices[(index + 1) % len(vertices)],
                radii[index],
            )
        )

    start = rounded[0].tangent_out if rounded[0] is not None else vertices[0]
    points: list[np.ndarray] = [np.asarray(start, dtype=float)]
    segments: list[tuple[str, tuple[int, ...]]] = []
    current_index = 1
    for next_index in range(1, len(vertices) + 1):
        vertex_index = next_index % len(vertices)
        rounded_vertex = rounded[vertex_index]
        tangent_in = rounded_vertex.tangent_in if rounded_vertex is not None else vertices[vertex_index]
        if float(np.linalg.norm(points[current_index - 1] - tangent_in)) > 1e-9:
            points.append(np.asarray(tangent_in, dtype=float))
            new_index = len(points)
            segments.append(("line", (current_index, new_index)))
            current_index = new_index
        if rounded_vertex is not None:
            middle_angle = rounded_vertex.start_angle_rad + rounded_vertex.extent_rad / 2.0
            radius = float(np.linalg.norm(rounded_vertex.tangent_in - rounded_vertex.center))
            middle = rounded_vertex.center + np.asarray(
                (math.cos(middle_angle) * radius, math.sin(middle_angle) * radius)
            )
            points.append(middle)
            middle_index = len(points)
            points.append(np.asarray(rounded_vertex.tangent_out, dtype=float))
            out_index = len(points)
            segments.append(("arc", (current_index, middle_index, out_index)))
            current_index = out_index
    if float(np.linalg.norm(points[-1] - points[0])) > 1e-7:
        points.append(points[0].copy())
        segments.append(("line", (current_index, len(points))))
    return points, segments


def _mesh(shape: cq.Shape, tolerance_mm: float = 0.20) -> tuple[np.ndarray, np.ndarray]:
    entities: Iterable[cq.Shape] = list(shape.Solids()) or [shape]
    all_points: list[np.ndarray] = []
    all_triangles: list[np.ndarray] = []
    offset = 0
    for entity in entities:
        vertices, triangles = entity.tessellate(float(tolerance_mm), 0.15)
        points = np.asarray([vertex.toTuple() for vertex in vertices], dtype=float)
        faces = np.asarray(triangles, dtype=int)
        if len(points) < 3 or len(faces) < 1:
            continue
        all_points.append(points)
        all_triangles.append(faces + offset)
        offset += len(points)
    if not all_points:
        raise SemanticIFCError("Plaat-solid kon niet worden getesselleerd voor IFC-preview")
    return np.vstack(all_points), np.vstack(all_triangles)


def write_semantic_plate_ifc(
    part: CanonicalPart,
    shape: cq.Shape,
    output_path: str | Path,
    *,
    tolerance_mm: float = 0.20,
) -> Path:
    """Write a validated plate as semantic swept IFC plus preview tessellation."""

    if part.header.profile_type != "B":
        raise SemanticIFCError("Deze writer ondersteunt uitsluitend plaat-/stripprofieltype B")
    thickness_mm = float(part.header.dim2 or part.product.plate_thickness_mm)
    if thickness_mm <= 0:
        raise SemanticIFCError("Plaatdikte ontbreekt")
    if shape.Volume() <= 1e-6 or not shape.Solids():
        raise SemanticIFCError("Canonieke plaat heeft geen geldige gesloten solid")
    for hole in part.holes:
        if hole.face not in {"", "v"} or hole.operation or hole.depth > 0:
            raise SemanticIFCError("Alleen eenvoudige doorgaande plaatgaten zijn semantisch ondersteund")
        if hole.diameter <= 0:
            raise SemanticIFCError("Ongeldige gatdiameter")

    profile_points, profile_segments = _indexed_curve_data(part)
    mesh_points, mesh_triangles = _mesh(shape, tolerance_mm=tolerance_mm)
    name = part.part_id or part.header.position_number or part.header.part_number or "PART"
    material = part.material or part.product.material_grade or "S235JR"
    timestamp = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    owner_epoch = int(_dt.datetime.now(_dt.timezone.utc).timestamp())

    lines: list[str] = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ViewDefinition [ReferenceView_V1.2]'),'2;1');",
        f"FILE_NAME('{_escape(Path(output_path).name)}','{timestamp}',('CWS Convertor'),('CWS Convertor'),'CWS Convertor v{_escape(part.converter_version)}','CWS Convertor v{_escape(part.converter_version)}','');",
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
        "#1=IFCPERSON($,$,'Converter',$,$,$,$,$);",
        "#2=IFCORGANIZATION($,'CWS Convertor',$,$,$);",
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
        f"#4=IFCAPPLICATION(#2,'{_escape(part.converter_version)}','CWS Convertor','CWSCONVERTOR');",
        f"#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,{owner_epoch});",
        "#6=IFCCARTESIANPOINT((0.,0.,0.));",
        "#7=IFCDIRECTION((0.,0.,1.));",
        "#8=IFCDIRECTION((1.,0.,0.));",
        "#9=IFCAXIS2PLACEMENT3D(#6,#7,#8);",
        "#10=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,$);",
        "#11=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);",
        "#12=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);",
        "#13=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);",
        "#14=IFCUNITASSIGNMENT((#11,#12,#13));",
        f"#15=IFCPROJECT('{_guid22(name + ':project')}',#5,'{_escape(name)}',$,$,$,$,(#10),#14);",
        f"#16=IFCMATERIAL('{_escape(material)}',$,'Steel');",
        f"#17=IFCSITE('{_guid22(name + ':site')}',#5,'Default Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$);",
        f"#18=IFCBUILDING('{_guid22(name + ':building')}',#5,'Default Building',$,$,$,$,$,.ELEMENT.,$,$,$);",
        f"#19=IFCBUILDINGSTOREY('{_guid22(name + ':storey')}',#5,'Default Storey',$,$,$,$,$,.ELEMENT.,0.);",
        f"#20=IFCRELAGGREGATES('{_guid22(name + ':rel-site')}',#5,$,$,#15,(#17));",
        f"#21=IFCRELAGGREGATES('{_guid22(name + ':rel-building')}',#5,$,$,#17,(#18));",
        f"#22=IFCRELAGGREGATES('{_guid22(name + ':rel-storey')}',#5,$,$,#18,(#19));",
        "#23=IFCLOCALPLACEMENT($,#9);",
    ]

    next_id = 30
    point_list_id = next_id
    next_id += 1
    point_rows = ",".join(
        f"({_real(point[0] / 1000.0)},{_real(point[1] / 1000.0)})" for point in profile_points
    )
    lines.append(f"#{point_list_id}=IFCCARTESIANPOINTLIST2D(({point_rows}));")
    segment_rows = []
    for kind, indices in profile_segments:
        values = ",".join(str(index) for index in indices)
        segment_rows.append(
            f"IFCARCINDEX(({values}))" if kind == "arc" else f"IFCLINEINDEX(({values}))"
        )
    curve_id = next_id
    next_id += 1
    lines.append(
        f"#{curve_id}=IFCINDEXEDPOLYCURVE(#{point_list_id},({','.join(segment_rows)}),.F.);"
    )

    inner_curve_ids: list[int] = []
    for index, hole in enumerate(part.holes, start=1):
        point_id, direction_id, placement_id, circle_id = next_id, next_id + 1, next_id + 2, next_id + 3
        next_id += 4
        lines.extend(
            [
                f"#{point_id}=IFCCARTESIANPOINT(({_real(hole.x / 1000.0)},{_real(hole.q / 1000.0)}));",
                f"#{direction_id}=IFCDIRECTION((1.,0.));",
                f"#{placement_id}=IFCAXIS2PLACEMENT2D(#{point_id},#{direction_id});",
                f"#{circle_id}=IFCCIRCLE(#{placement_id},{_real(hole.diameter / 2000.0)});",
            ]
        )
        inner_curve_ids.append(circle_id)

    profile_id = next_id
    next_id += 1
    if inner_curve_ids:
        lines.append(
            f"#{profile_id}=IFCARBITRARYPROFILEDEFWITHVOIDS(.AREA.,'{_escape(name)} profile',#{curve_id},({','.join('#' + str(item) for item in inner_curve_ids)}));"
        )
    else:
        lines.append(
            f"#{profile_id}=IFCARBITRARYCLOSEDPROFILEDEF(.AREA.,'{_escape(name)} profile',#{curve_id});"
        )
    solid_origin_id, solid_axis_id, extrude_dir_id, solid_id = next_id, next_id + 1, next_id + 2, next_id + 3
    next_id += 4
    lines.extend(
        [
            f"#{solid_origin_id}=IFCCARTESIANPOINT((0.,0.,0.));",
            f"#{solid_axis_id}=IFCAXIS2PLACEMENT3D(#{solid_origin_id},#7,#8);",
            f"#{extrude_dir_id}=IFCDIRECTION((0.,0.,1.));",
            f"#{solid_id}=IFCEXTRUDEDAREASOLID(#{profile_id},#{solid_axis_id},#{extrude_dir_id},{_real(thickness_mm / 1000.0)});",
        ]
    )
    swept_rep_id = next_id
    next_id += 1
    lines.append(f"#{swept_rep_id}=IFCSHAPEREPRESENTATION(#10,'Body','SweptSolid',(#{solid_id}));")

    mesh_points_id, mesh_set_id, mesh_rep_id = next_id, next_id + 1, next_id + 2
    next_id += 3
    mesh_point_rows = ",".join(
        f"({_real(point[0] / 1000.0)},{_real(point[1] / 1000.0)},{_real(point[2] / 1000.0)})"
        for point in mesh_points
    )
    triangle_rows = ",".join(
        f"({int(face[0]) + 1},{int(face[1]) + 1},{int(face[2]) + 1})" for face in mesh_triangles
    )
    lines.extend(
        [
            f"#{mesh_points_id}=IFCCARTESIANPOINTLIST3D(({mesh_point_rows}));",
            f"#{mesh_set_id}=IFCTRIANGULATEDFACESET(#{mesh_points_id},$,.T.,({triangle_rows}),$);",
            f"#{mesh_rep_id}=IFCSHAPEREPRESENTATION(#10,'Body-Fallback','Tessellation',(#{mesh_set_id}));",
        ]
    )
    product_shape_id, plate_id = next_id, next_id + 1
    next_id += 2
    lines.extend(
        [
            f"#{product_shape_id}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{swept_rep_id},#{mesh_rep_id}));",
            f"#{plate_id}=IFCPLATE('{_guid22(name + ':plate')}',#5,'{_escape(name)}',$,'{_escape(part.product.name or 'Plate')}',#23,#{product_shape_id},'{_escape(part.product.mark or name)}',.SHEET.);",
        ]
    )
    lines.extend(
        [
            f"#{next_id}=IFCRELCONTAINEDINSPATIALSTRUCTURE('{_guid22(name + ':containment')}',#5,$,$,(#{plate_id}),#19);",
            f"#{next_id + 1}=IFCRELASSOCIATESMATERIAL('{_guid22(name + ':material')}',#5,$,$,(#{plate_id}),#16);",
        ]
    )
    next_id += 2

    quantity_ids = [next_id, next_id + 1, next_id + 2]
    quantity_set_id, quantity_rel_id = next_id + 3, next_id + 4
    next_id += 5
    volume_m3 = float(shape.Volume()) / 1_000_000_000.0
    area_m2 = float(shape.Area()) / 1_000_000.0
    lines.extend(
        [
            f"#{quantity_ids[0]}=IFCQUANTITYLENGTH('Length',$,$,{_real(part.header.length / 1000.0)},$);",
            f"#{quantity_ids[1]}=IFCQUANTITYAREA('SurfaceArea',$,$,{_real(area_m2)},$);",
            f"#{quantity_ids[2]}=IFCQUANTITYVOLUME('NetVolume',$,$,{_real(volume_m3)},$);",
            f"#{quantity_set_id}=IFCELEMENTQUANTITY('{_guid22(name + ':qto')}',#5,'Qto_PlateBaseQuantities',$,$,({','.join('#' + str(item) for item in quantity_ids)}));",
            f"#{quantity_rel_id}=IFCRELDEFINESBYPROPERTIES('{_guid22(name + ':qto-rel')}',#5,$,$,(#{plate_id}),#{quantity_set_id});",
        ]
    )

    encoded = encode_part(part)
    payload_chunks = _chunk(encoded)
    payload_properties: list[int] = []
    payload_values: list[tuple[str, str, str]] = [
        ("SchemaVersion", "IFCTEXT", part.schema_version),
        ("ConverterVersion", "IFCTEXT", part.converter_version),
        ("PartId", "IFCTEXT", name),
        ("SourceSHA256", "IFCTEXT", part.source_sha256),
        ("PayloadCodec", "IFCTEXT", PAYLOAD_CODEC),
        ("PayloadSHA256", "IFCTEXT", sha256_bytes(encoded.encode("ascii"))),
        ("PayloadChunkCount", "IFCINTEGER", str(len(payload_chunks))),
    ]
    payload_values.extend(
        (f"PayloadChunk_{index:04d}", "IFCTEXT", chunk)
        for index, chunk in enumerate(payload_chunks, start=1)
    )
    for prop_name, value_type, value in payload_values:
        prop_id = next_id
        next_id += 1
        payload_properties.append(prop_id)
        if value_type == "IFCINTEGER":
            rendered = f"IFCINTEGER({int(value)})"
        else:
            rendered = f"{value_type}('{_escape(value)}')"
        lines.append(
            f"#{prop_id}=IFCPROPERTYSINGLEVALUE('{_escape(prop_name)}',$,{rendered},$);"
        )
    pset_id, pset_rel_id = next_id, next_id + 1
    lines.extend(
        [
            f"#{pset_id}=IFCPROPERTYSET('{_guid22(name + ':converter-pset')}',#5,'Pset_NC1StepConverter',$,({','.join('#' + str(item) for item in payload_properties)}));",
            f"#{pset_rel_id}=IFCRELDEFINESBYPROPERTIES('{_guid22(name + ':converter-pset-rel')}',#5,$,$,(#{plate_id}),#{pset_id});",
        ]
    )

    lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
    text = embed_part_in_ifc_text("\n".join(lines) + "\n", part)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    return output
