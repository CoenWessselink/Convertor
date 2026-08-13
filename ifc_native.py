"""Dependency-arme IFC4 tessellatie-export en -import.

IfcOpenShell blijft de voorkeursroute voor willekeurige externe IFC-modellen.
Deze module schrijft daarnaast een geldige, zelfstandige IFC4 Reference View
met een echte ``Pset_NC1StepConverter``. Daardoor kunnen converter-eigen IFC's
ook zonder lokale IfcOpenShell-installatie worden bekeken en lossless worden
teruggezet naar hun productiegegevens.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime as _dt
import math
import re
import uuid
from typing import Iterable, Iterator

import cadquery as cq
import numpy as np

from cws_convertor.product import APP_NAME

from canonical_model import (
    CanonicalPart,
    embed_part_in_ifc_text,
    encode_part,
    extract_part_from_ifc,
    sha256_bytes,
)

_IFC_GUID_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$"


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
    """Maak een deterministische, formeel geldige 22-teken IFC GlobalId."""

    number = int.from_bytes(uuid.uuid5(uuid.NAMESPACE_URL, seed).bytes, "big")
    chars = ["0"] * 22
    for index in range(21, -1, -1):
        chars[index] = _IFC_GUID_ALPHABET[number & 0x3F]
        number >>= 6
    return "".join(chars)


def _escape_ifc(value: str) -> str:
    return str(value).replace("'", "''")


def _unescape_ifc(value: str) -> str:
    return value.replace("''", "'")


def _ifc_real(value: float) -> str:
    if not math.isfinite(value):
        value = 0.0
    text = f"{float(value):.12g}"
    if "e" not in text.lower() and "." not in text:
        text += "."
    return text


def _solid_meshes(
    shape: cq.Shape,
    tolerance_mm: float,
) -> list[tuple[cq.Shape, np.ndarray, np.ndarray]]:
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
    """Schrijf IFC4-zichtgeometrie én één gehashte lossless propertyset.

    De IFC-coördinaten worden in meter geschreven. Productiefeatures worden
    niet uit deze tessellatie teruggeraden: de gecontroleerde canonical payload
    in ``Pset_NC1StepConverter`` is daarvoor de primaire opslaglaag.
    """

    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    meshes = _solid_meshes(shape, tolerance_mm)
    if not meshes:
        raise ValueError("Model bevat geen exporteerbare solid/mesh")

    canonical.validate()
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
            f"('{_escape_ifc(APP_NAME)}'),('{_escape_ifc(APP_NAME)}'),"
            f"'{_escape_ifc(APP_NAME)} v{_escape_ifc(canonical.converter_version)}',"
            f"'{_escape_ifc(APP_NAME)} v{_escape_ifc(canonical.converter_version)}','');"
        ),
        "FILE_SCHEMA(('IFC4'));",
        "ENDSEC;",
        "DATA;",
        "#1=IFCPERSON($,$,'Converter',$,$,$,$,$);",
        f"#2=IFCORGANIZATION($,'{_escape_ifc(APP_NAME)}',$,$,$);",
        "#3=IFCPERSONANDORGANIZATION(#1,#2,$);",
        f"#4=IFCAPPLICATION(#2,'{_escape_ifc(canonical.converter_version)}','{_escape_ifc(APP_NAME)}','CWSCONVERTOR');",
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
        f"#17=IFCSITE('{_guid22(name + ':site')}',#5,'Default Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$);",
        f"#18=IFCBUILDING('{_guid22(name + ':building')}',#5,'Default Building',$,$,$,$,$,.ELEMENT.,$,$,$);",
        f"#19=IFCBUILDINGSTOREY('{_guid22(name + ':storey')}',#5,'Default Storey',$,$,$,$,$,.ELEMENT.,0.);",
        f"#20=IFCRELAGGREGATES('{_guid22(name + ':project-site')}',#5,$,$,#15,(#17));",
        f"#21=IFCRELAGGREGATES('{_guid22(name + ':site-building')}',#5,$,$,#17,(#18));",
        f"#22=IFCRELAGGREGATES('{_guid22(name + ':building-storey')}',#5,$,$,#18,(#19));",
        "#23=IFCLOCALPLACEMENT($,#9);",
    ]

    next_id = 30
    element_ids: list[int] = []
    for index, (solid, vertices_mm, faces_zero) in enumerate(meshes, start=1):
        point_id = next_id
        face_set_id = next_id + 1
        representation_id = next_id + 2
        product_shape_id = next_id + 3
        element_id = next_id + 4
        next_id += 5
        element_ids.append(element_id)

        vertices_m = vertices_mm / 1000.0
        faces_one = faces_zero + 1
        coordinates = ",".join(
            "(" + ",".join(_ifc_real(float(value)) for value in row) + ")"
            for row in vertices_m
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
                f"#{representation_id}=IFCSHAPEREPRESENTATION(#10,'Body','Tessellation',(#{face_set_id}));",
                f"#{product_shape_id}=IFCPRODUCTDEFINITIONSHAPE($,$,(#{representation_id}));",
                (
                    f"#{element_id}={ifc_class}('{_guid22(name + ':element:' + str(index))}',#5,"
                    f"'{_escape_ifc(element_name)}',$,$,#23,#{product_shape_id},"
                    f"'{_escape_ifc(element_name)}',.NOTDEFINED.);"
                ),
            ]
        )

    element_refs = ",".join(f"#{entity_id}" for entity_id in element_ids)
    containment_id = next_id
    material_relation_id = next_id + 1
    next_id += 2
    lines.extend(
        [
            (
                f"#{containment_id}=IFCRELCONTAINEDINSPATIALSTRUCTURE("
                f"'{_guid22(name + ':containment')}',#5,$,$,({element_refs}),#19);"
            ),
            (
                f"#{material_relation_id}=IFCRELASSOCIATESMATERIAL("
                f"'{_guid22(name + ':material')}',#5,$,$,({element_refs}),#16);"
            ),
        ]
    )

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
    property_ids: list[int] = []
    for property_name, property_type, property_value in properties:
        property_id = next_id
        next_id += 1
        property_ids.append(property_id)
        if property_type in {"IFCINTEGER", "IFCREAL"}:
            nominal_value = f"{property_type}({property_value})"
        else:
            nominal_value = f"{property_type}('{_escape_ifc(property_value)}')"
        lines.append(
            f"#{property_id}=IFCPROPERTYSINGLEVALUE('{_escape_ifc(property_name)}',$,{nominal_value},$);"
        )
    pset_id = next_id
    property_relation_id = next_id + 1
    next_id += 2
    property_refs = ",".join(f"#{property_id}" for property_id in property_ids)
    lines.extend(
        [
            (
                f"#{pset_id}=IFCPROPERTYSET('{_guid22(name + ':pset')}',#5,"
                f"'Pset_NC1StepConverter',$,({property_refs}));"
            ),
            (
                f"#{property_relation_id}=IFCRELDEFINESBYPROPERTIES("
                f"'{_guid22(name + ':relpset')}',#5,$,$,({element_refs}),#{pset_id});"
            ),
            "ENDSEC;",
            "END-ISO-10303-21;",
        ]
    )

    # Redundante commentkopie: nuttig voor herstel door uiterst eenvoudige
    # parsers. extract_part_from_ifc leest eerst de echte propertyset.
    text = embed_part_in_ifc_text("\n".join(lines) + "\n", canonical)
    output.write_text(text, encoding="utf-8", newline="\n")
    return output


def _balanced(
    text: str,
    start: int,
    open_character: str = "(",
    close_character: str = ")",
) -> tuple[str, int]:
    if start >= len(text) or text[start] != open_character:
        raise NativeIFCParseError("IFC-parser verwacht een open haakje")
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


def _split_ifc_args(block: str) -> list[str]:
    body = block[1:-1]
    result: list[str] = []
    start = 0
    depth = 0
    in_string = False
    index = 0
    while index < len(body):
        character = body[index]
        if character == "'":
            if in_string and index + 1 < len(body) and body[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
            elif character == "," and depth == 0:
                result.append(body[start:index].strip())
                start = index + 1
        index += 1
    result.append(body[start:].strip())
    return result


def _entity_blocks(text: str, names: Iterable[str]) -> Iterator[tuple[int, str, str]]:
    alternation = "|".join(re.escape(name) for name in names)
    pattern = re.compile(rf"#(\d+)\s*=\s*({alternation})\s*(\()", re.IGNORECASE)
    for match in pattern.finditer(text):
        block, _end = _balanced(text, match.start(3))
        yield int(match.group(1)), match.group(2).upper(), block


def _parse_ref(value: str) -> int | None:
    match = re.fullmatch(r"#(\d+)", value.strip())
    return int(match.group(1)) if match else None


def _parse_string(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == "'" and stripped[-1] == "'":
        return _unescape_ifc(stripped[1:-1])
    return "" if stripped == "$" else stripped


def _refs(value: str) -> list[int]:
    return [int(item) for item in re.findall(r"#(\d+)", value)]


def _length_scale_to_mm(text: str) -> float:
    match = re.search(
        r"IFCSIUNIT\s*\(\s*\*\s*,\s*\.LENGTHUNIT\.\s*,\s*(\$|\.[A-Z]+\.)\s*,\s*\.METRE\.\s*\)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return 1000.0
    prefix = match.group(1).upper()
    return {
        "$": 1000.0,
        ".MILLI.": 1.0,
        ".CENTI.": 10.0,
        ".DECI.": 100.0,
        ".KILO.": 1_000_000.0,
    }.get(prefix, 1000.0)


def _parse_point_lists(text: str, scale_to_mm: float) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    for entity_id, _entity_name, block in _entity_blocks(text, ["IFCCARTESIANPOINTLIST3D"]):
        numbers = [
            float(value)
            for value in re.findall(r"[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?", block)
        ]
        if len(numbers) % 3:
            raise NativeIFCParseError("IFCCARTESIANPOINTLIST3D heeft geen veelvoud van drie waarden")
        result[entity_id] = np.asarray(numbers, dtype=float).reshape((-1, 3)) * scale_to_mm
    return result


def parse_native_ifc_meshes(path: str | Path) -> list[NativeIFCMesh]:
    """Lees eenvoudige IFC4 IfcTriangulatedFaceSet-geometrie zonder IfcOpenShell."""

    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="replace")
    point_lists = _parse_point_lists(text, _length_scale_to_mm(text))

    face_sets: dict[int, tuple[int, np.ndarray]] = {}
    for entity_id, _name, block in _entity_blocks(text, ["IFCTRIANGULATEDFACESET"]):
        args = _split_ifc_args(block)
        if len(args) < 4:
            continue
        point_list_id = _parse_ref(args[0])
        if point_list_id is None:
            continue
        triples = re.findall(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", args[3])
        triangles = np.asarray(
            [[int(first) - 1, int(second) - 1, int(third) - 1] for first, second, third in triples],
            dtype=int,
        )
        if len(triangles):
            face_sets[entity_id] = (point_list_id, triangles)
    if not face_sets:
        raise NativeIFCParseError("Geen IfcTriangulatedFaceSet gevonden")

    representation_to_faces: dict[int, list[int]] = {}
    for entity_id, _name, block in _entity_blocks(text, ["IFCSHAPEREPRESENTATION"]):
        args = _split_ifc_args(block)
        representation_to_faces[entity_id] = _refs(args[3]) if len(args) > 3 else []

    product_shape_to_representations: dict[int, list[int]] = {}
    for entity_id, _name, block in _entity_blocks(text, ["IFCPRODUCTDEFINITIONSHAPE"]):
        args = _split_ifc_args(block)
        product_shape_to_representations[entity_id] = _refs(args[2]) if len(args) > 2 else []

    element_records: list[dict[str, object]] = []
    class_names = {"IFCPLATE": "IfcPlate", "IFCMEMBER": "IfcMember"}
    for entity_id, entity_name, block in _entity_blocks(text, class_names):
        args = _split_ifc_args(block)
        element_records.append(
            {
                "id": entity_id,
                "class": class_names[entity_name],
                "guid": _parse_string(args[0]) if args else "",
                "name": _parse_string(args[2]) if len(args) > 2 else f"Element {entity_id}",
                "product_shape": _parse_ref(args[6]) if len(args) > 6 else None,
            }
        )

    material = ""
    for _entity_id, _name, block in _entity_blocks(text, ["IFCMATERIAL"]):
        args = _split_ifc_args(block)
        material = _parse_string(args[0]) if args else ""
        break

    meshes: list[NativeIFCMesh] = []
    consumed_face_sets: set[int] = set()
    for record in element_records:
        product_shape_id = record.get("product_shape")
        candidate_face_sets: list[int] = []
        if isinstance(product_shape_id, int):
            for representation_id in product_shape_to_representations.get(product_shape_id, []):
                candidate_face_sets.extend(representation_to_faces.get(representation_id, []))
        for face_set_id in candidate_face_sets:
            if face_set_id not in face_sets:
                continue
            point_list_id, triangles = face_sets[face_set_id]
            vertices = point_lists.get(point_list_id)
            if vertices is None:
                raise NativeIFCParseError(f"Puntenlijst #{point_list_id} ontbreekt")
            consumed_face_sets.add(face_set_id)
            meshes.append(
                NativeIFCMesh(
                    name=str(record.get("name") or f"Element {record['id']}"),
                    guid=str(record.get("guid") or f"native-{record['id']}"),
                    ifc_class=str(record.get("class") or "IfcElement"),
                    material=material,
                    vertices_mm=vertices,
                    triangles=triangles,
                )
            )

    # Fallback voor minimale/externe IFC's zonder volledige productkoppelingen.
    for face_set_id, (point_list_id, triangles) in face_sets.items():
        if face_set_id in consumed_face_sets:
            continue
        vertices = point_lists.get(point_list_id)
        if vertices is None:
            raise NativeIFCParseError(f"Puntenlijst #{point_list_id} ontbreekt")
        index = len(meshes) + 1
        record = element_records[index - 1] if index - 1 < len(element_records) else {}
        meshes.append(
            NativeIFCMesh(
                name=str(record.get("name") or f"Element {index}"),
                guid=str(record.get("guid") or f"native-{index}"),
                ifc_class=str(record.get("class") or "IfcElement"),
                material=material,
                vertices_mm=vertices,
                triangles=triangles,
            )
        )
    return meshes


def extract_native_canonical(path: str | Path, *, strict: bool = False) -> CanonicalPart | None:
    return extract_part_from_ifc(path, strict=strict)
