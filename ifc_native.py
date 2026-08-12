"""Dependency-arme IFC4 tessellatie-export en -import voor converterbestanden.

IfcOpenShell blijft de voorkeursroute voor willekeurige externe IFC-modellen.
Deze module garandeert echter dat converter-eigen IFC-bestanden ook zonder een
lokale Python/IfcOpenShell-installatie kunnen worden geschreven en dat hun
lossless canonieke payload kan worden hersteld.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import datetime as _dt
import hashlib
import json
import math
import re
import uuid
from typing import Any, Iterable

import cadquery as cq
import numpy as np

from canonical_model import CanonicalPart, encode_part, embed_part_in_ifc_text, extract_part_from_ifc, sha256_bytes


@dataclass
class NativeIFCMesh:
    name: str
    guid: str
    ifc_class: str
    material: str
    vertices_mm: np.ndarray
    triangles: np.ndarray


class NativeIFCParseError(ValueError):
    pass


def _guid22(seed: str) -> str:
    # Deterministic 22-character IFC-compatible alphabet. It is not intended as
    # a cryptographic identifier; source hashes remain the integrity anchor.
    raw = uuid.uuid5(uuid.NAMESPACE_URL, seed).bytes
    text = base64.b64encode(raw).decode("ascii").rstrip("=").replace("+", "$").replace("/", "_")
    return text[:22]


def _escape_ifc(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "''")


def _ifc_real(value: float) -> str:
    if not math.isfinite(value):
        value = 0.0
    text = f"{float(value):.12g}"
    if "e" not in text.lower() and "." not in text:
        text += "."
    return text


def _solid_meshes(shape: cq.Shape, tolerance_mm: float) -> list[tuple[cq.Shape, np.ndarray, np.ndarray]]:
    entities: list[cq.Shape] = list(shape.Solids()) or [shape]
    result: list[tuple[cq.Shape, np.ndarray, np.ndarray]] = []
    for entity in entities:
        vertices, triangles = entity.tessellate(float(tolerance_mm), 0.15)
        points = np.asarray([vertex.toTuple() for vertex in vertices], dtype=float)
        faces = np.asarray(triangles, dtype=int)
        if len(points) >= 3 and len(faces) >= 1:
            result.append((entity, points, faces))
    return result


def _classify(shape: cq.Shape) -> str:
    box = shape.BoundingBox()
    dimensions = sorted((float(box.xlen), float(box.ylen), float(box.zlen)))
    if dimensions[0] <= max(30.0, 0.08 * dimensions[-1]) and dimensions[1] > 2.5 * dimensions[0]:
        return "IFCPLATE"
    return "IFCMEMBER"


def _chunk(text: str, size: int = 1800) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


def write_native_ifc(
    shape: cq.Shape,
    target: str | Path,
    *,
    name: str,
    material: str,
    canonical: CanonicalPart,
    tolerance_mm: float = 0.20,
) -> Path:
    """Schrijf een zelfstandige IFC4 met zichtbare tessellatie plus lossless Pset."""

    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    meshes = _solid_meshes(shape, tolerance_mm)
    if not meshes:
        raise ValueError("Model bevat geen exporteerbare solid/mesh")

    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    timestamp = now.isoformat()
    epoch = int(now.timestamp())
    encoded = encode_part(canonical)
    payload_chunks = _chunk(encoded)
    payload_sha = sha256_bytes(encoded.encode("ascii"))

    lines = [
        "ISO-10303-21;",
        "HEADER;",
        "FILE_DESCRIPTION(('ViewDefinition [ReferenceView_V1.2]'),'2;1');",
        (
            f"FILE_NAME('{_escape_ifc(output.name)}','{timestamp}',"
            "('NC1 STEP IFC Converter'),('NC1 STEP IFC Converter'),"
            f"'NC1 STEP IFC Converter v{_escape_ifc(canonical.converter_version)}',"
            f"'NC1 STEP IFC Converter v{_escape_ifc(canonical.converter_version)}','');"
        ),
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
        "#1=IFCPERSON($,$,'Converter',$,$,$,$,$);",
        "#2=IFCORGANIZATION($,'NC1 STEP IFC Converter',$,$,$);",
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
        f"#4=IFCAPPLICATION(#2,'{_escape_ifc(canonical.converter_version)}','NC1 STEP IFC Converter','NC1STEPIFC');",
        f"#5=IFCOWNERHISTORY(#3,#4,$,.ADDED.,$,$,$,{epoch});",
        "#6=IFCCARTESIANPOINT((0.,0.,0.));",
        "#7=IFCDIRECTION((0.,0.,1.));",
        "#8=IFCDIRECTION((1.,0.,0.));",
        "#9=IFCAXIS2PLACEMENT3D(#6,#7,#8);",
        "#10=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#9,$);",
        "#11=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);",
        "#12=IFCSIUNIT(*,.AREAUNIT.,$,.SQUARE_METRE.);",
        "#13=IFCSIUNIT(*,.VOLUMEUNIT.,$,.CUBIC_METRE.);",
        "#14=IFCUNITASSIGNMENT((#11,#12,#13));",
        f"#15=IFCPROJECT('{_guid22(name + ':project')}',#5,'{_escape_ifc(name)}',$,$,$,$,(#10),#14);",
        f"#16=IFCMATERIAL('{_escape_ifc(material)}',$,'Steel');",
    ]

    next_id = 20
    for index, (solid, vertices_mm, faces_zero) in enumerate(meshes, start=1):
        point_id = next_id
        face_set_id = next_id + 1
        rep_id = next_id + 2
        pds_id = next_id + 3
        element_id = next_id + 4
        rel_material_id = next_id + 5
        next_id += 6

        vertices_m = vertices_mm / 1000.0
        faces_one = faces_zero + 1
        coordinates = ",".join(
            "(" + ",".join(_ifc_real(float(value)) for value in row) + ")" for row in vertices_m
        )
        indexes = ",".join(
            "(" + ",".join(str(int(value)) for value in row) + ")" for row in faces_one
        )
        element_name = name if len(meshes) == 1 else f"{name}_{index:03d}"
        ifc_class = _classify(solid)
        lines.extend(
            [
                f"#{point_id}=IFCCARTESIANPOINTLIST3D(({coordinates}));",
                f"#{face_set_id}=IFCTRIANGULATEDFACESET(#{point_id},$,.T.,({indexes}),$);",
                f"#{rep_id}=IFCSHAPEREPRESENTATION(#10,'Body','Tessellation',(#{face_set_id}));",
                f"#{pds_id}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{rep_id}));",
                (
                    f"#{element_id}={ifc_class}('{_guid22(name + ':element:' + str(index))}',#5,"
                    f"'{_escape_ifc(element_name)}',$,$,$,#{pds_id},'{_escape_ifc(element_name)}',.NOTDEFINED.);"
                ),
                (
                    f"#{rel_material_id}=IFCRELASSOCIATESMATERIAL("
                    f"'{_guid22(name + ':material:' + str(index))}',#5,$,$,(#{element_id}),#16);"
                ),
            ]
        )

        property_ids: list[int] = []
        properties: list[tuple[str, str, str]] = [
            ("SchemaVersion", "IFCTEXT", canonical.schema_version),
            ("ConverterVersion", "IFCTEXT", canonical.converter_version),
            ("SourceFormat", "IFCTEXT", canonical.source_format),
            ("SourceFile", "IFCTEXT", canonical.source_file),
            ("SourceSHA256", "IFCTEXT", canonical.source_sha256),
            ("PartId", "IFCTEXT", canonical.part_id),
            ("ProfileDesignation", "IFCTEXT", canonical.profile_designation),
            ("ProfileType", "IFCTEXT", canonical.profile_type),
            ("MaterialGrade", "IFCTEXT", canonical.material or material),
            ("Quantity", "IFCINTEGER", str(int(canonical.quantity or 1))),
            ("PayloadCodec", "IFCTEXT", "zlib+base64+json"),
            ("PayloadSHA256", "IFCTEXT", payload_sha),
            ("PayloadChunkCount", "IFCINTEGER", str(len(payload_chunks))),
            ("MeshTolerance_mm", "IFCREAL", _ifc_real(tolerance_mm)),
        ]
        properties.extend(
            (f"PayloadChunk_{chunk_index:04d}", "IFCTEXT", chunk)
            for chunk_index, chunk in enumerate(payload_chunks, start=1)
        )
        for prop_name, prop_type, prop_value in properties:
            prop_id = next_id
            next_id += 1
            property_ids.append(prop_id)
            if prop_type in {"IFCINTEGER", "IFCREAL"}:
                nominal = f"{prop_type}({prop_value})"
            else:
                nominal = f"{prop_type}('{_escape_ifc(prop_value)}')"
            lines.append(
                f"#{prop_id}=IFCPROPERTYSINGLEVALUE('{_escape_ifc(prop_name)}',$,{nominal},$);"
            )
        pset_id = next_id
        rel_pset_id = next_id + 1
        next_id += 2
        prop_refs = ",".join(f"#{prop_id}" for prop_id in property_ids)
        lines.extend(
            [
                (
                    f"#{pset_id}=IFCPROPERTYSET('{_guid22(name + ':pset:' + str(index))}',#5,"
                    f"'Pset_NC1StepConverter',$,({prop_refs}));"
                ),
                (
                    f"#{rel_pset_id}=IFCRELDEFINESBYPROPERTIES("
                    f"'{_guid22(name + ':relpset:' + str(index))}',#5,$,$,(#{element_id}),#{pset_id});"
                ),
            ]
        )

    lines.extend(["ENDSEC;", "END-ISO-10303-21;"])
    text = "\n".join(lines) + "\n"
    text = embed_part_in_ifc_text(text, canonical)
    output.write_text(text, encoding="utf-8", newline="\n")
    return output


def _balanced(text: str, start: int, open_character: str = "(", close_character: str = ")") -> tuple[str, int]:
    depth = 0
    in_string = False
    index = start
    while index < len(text):
        character = text[index]
        if character == "'":
            if in_string and index + 1 < len(text) and text[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if character == open_character:
                depth += 1
            elif character == close_character:
                depth -= 1
                if depth == 0:
                    return text[start : index + 1], index + 1
        index += 1
    raise NativeIFCParseError("Ongebalanceerde IFC-haakjes")


def _parse_point_lists(text: str) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    for match in re.finditer(r"#(\d+)\s*=\s*IFCCARTESIANPOINTLIST3D\s*\(", text, re.IGNORECASE):
        block, _end = _balanced(text, match.end() - 1)
        numbers = [
            float(value)
            for value in re.findall(r"[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?", block)
        ]
        if len(numbers) % 3:
            raise NativeIFCParseError("IFCCARTESIANPOINTLIST3D heeft geen veelvoud van drie waarden")
        result[int(match.group(1))] = np.asarray(numbers, dtype=float).reshape((-1, 3)) * 1000.0
    return result


def parse_native_ifc_meshes(path: str | Path) -> list[NativeIFCMesh]:
    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="replace")
    point_lists = _parse_point_lists(text)
    face_sets: list[tuple[int, int, np.ndarray]] = []
    for match in re.finditer(
        r"#(\d+)\s*=\s*IFCTRIANGULATEDFACESET\s*\(\s*#(\d+)\s*,",
        text,
        re.IGNORECASE,
    ):
        block, _end = _balanced(text, match.end() - 1)
        flag_position = block.upper().find(".T.")
        sub = block[flag_position + 3 :] if flag_position >= 0 else block
        opening = sub.find("(")
        if opening < 0:
            continue
        coordinate_block, _end = _balanced(sub, opening)
        triples = re.findall(
            r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", coordinate_block
        )
        triangles = np.asarray(
            [[int(first) - 1, int(second) - 1, int(third) - 1] for first, second, third in triples],
            dtype=int,
        )
        face_sets.append((int(match.group(1)), int(match.group(2)), triangles))
    if not face_sets:
        raise NativeIFCParseError("Geen IfcTriangulatedFaceSet gevonden")

    element_records = []
    for match in re.finditer(
        r"#(\d+)\s*=\s*(IFCPLATE|IFCMEMBER)\s*\(\s*'([^']*)'\s*,[^;]*?'([^']*)'\s*,\.NOTDEFINED\.\s*\)\s*;",
        text,
        re.IGNORECASE,
    ):
        element_records.append(
            {
                "id": int(match.group(1)),
                "class": match.group(2).title().replace("Ifc", "Ifc"),
                "guid": match.group(3),
                "name": match.group(4),
            }
        )
    material_match = re.search(r"IFCMATERIAL\s*\(\s*'([^']*)'", text, re.IGNORECASE)
    material = material_match.group(1).replace("''", "'") if material_match else ""

    meshes: list[NativeIFCMesh] = []
    for index, (_face_set_id, point_list_id, triangles) in enumerate(face_sets):
        vertices = point_lists.get(point_list_id)
        if vertices is None:
            raise NativeIFCParseError(f"Puntenlijst #{point_list_id} ontbreekt")
        record = element_records[index] if index < len(element_records) else {}
        meshes.append(
            NativeIFCMesh(
                name=str(record.get("name") or f"Element {index + 1}"),
                guid=str(record.get("guid") or f"native-{index + 1}"),
                ifc_class=str(record.get("class") or "IfcElement"),
                material=material,
                vertices_mm=vertices,
                triangles=triangles,
            )
        )
    return meshes


def extract_native_canonical(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    return extract_part_from_ifc(path, strict=strict)
