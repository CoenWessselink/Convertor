#!/usr/bin/env python3
"""Read IFC source evidence without inferring production profile/material/geometry.

This is an offline source probe. It never writes IFC or Tekla, and its optional
mesh bounds are approximate display metrics, never native equivalence evidence.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import pathlib
import sys

import ifcopenshell
import ifcopenshell.geom as ifcgeom
import ifcopenshell.util.element
import ifcopenshell.util.unit

TARGET_TYPES = ("IfcBeam", "IfcColumn", "IfcMember", "IfcPlate")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def material_evidence(product) -> list[dict]:
    evidence = []
    subjects = [("OCCURRENCE", product)]
    type_entity = ifcopenshell.util.element.get_type(product)
    if type_entity is not None:
        subjects.append(("TYPE", type_entity))
    for origin, subject in subjects:
        for relation in getattr(subject, "HasAssociations", ()) or ():
            if not relation.is_a("IfcRelAssociatesMaterial"):
                continue
            material = relation.RelatingMaterial
            for item in product.file.traverse(material):
                if item.is_a("IfcMaterial") and getattr(item, "Name", None):
                    evidence.append({"Origin": origin, "SourceEntityId": item.id(), "Path": "IfcRelAssociatesMaterial/IfcMaterial.Name", "Category": "MATERIAL_LABEL", "RawValue": item.Name})
    # Include direct and inherited properties independently, preserving provenance.
    for origin, subject in subjects:
        psets = ifcopenshell.util.element.get_psets(subject, should_inherit=False)
        for pset, properties in psets.items():
            for name, value in properties.items():
                if name == "id" or not isinstance(value, str) or not value.strip():
                    continue
                lower = name.casefold()
                if any(fragment in lower for fragment in ("material", "materiaal", "sterkte", "strength", "grade", "kwaliteit")):
                    category = "STRENGTH_GRADE" if any(f in lower for f in ("sterkte", "strength", "grade", "kwaliteit")) else "MATERIAL_LABEL"
                    evidence.append({"Origin": origin, "SourceEntityId": subject.id(), "Path": pset + "/" + name, "Category": category, "RawValue": value})
    return evidence


def profile_geometry_evidence(model, product) -> tuple[list[dict], list[dict], list[dict]]:
    representations, profiles, metadata = [], [], []
    seen = set()
    representation = getattr(product, "Representation", None)
    for rep in getattr(representation, "Representations", ()) or ():
        representations.append({"SourceEntityId": rep.id(), "Identifier": rep.RepresentationIdentifier, "RepresentationType": rep.RepresentationType, "ItemTypes": sorted({item.is_a() for item in rep.Items})})
        for entity in model.traverse(rep):
            if entity.id() in seen or not entity.is_a("IfcProfileDef"):
                continue
            seen.add(entity.id())
            scalar_attributes = {name: value for name, value in entity.get_info().items() if name not in ("id", "type") and isinstance(value, (str, int, float, bool))}
            profiles.append({"SourceEntityId": entity.id(), "IfcType": entity.is_a(), "ProfileNameRaw": entity.ProfileName, "ScalarAttributesRaw": scalar_attributes, "StepRecordSha256": hashlib.sha256(entity.to_string().encode("utf-8")).hexdigest()})
    subjects = [("OCCURRENCE", product)]
    type_entity = ifcopenshell.util.element.get_type(product)
    if type_entity is not None:
        subjects.append(("TYPE", type_entity))
    for origin, subject in subjects:
        for pset, properties in ifcopenshell.util.element.get_psets(subject, should_inherit=False).items():
            for name, value in properties.items():
                if isinstance(value, str) and value.strip() and ("profile" in name.casefold() or name in ("Type", "Type Name", "Reference", "Family and Type")):
                    metadata.append({"Origin": origin, "SourceEntityId": subject.id(), "Path": pset + "/" + name, "RawValue": value})
    return representations, profiles, metadata


def mesh_summary(product, settings) -> dict:
    try:
        bodies = [rep for rep in getattr(getattr(product, "Representation", None), "Representations", ()) or () if rep.RepresentationIdentifier == "Body"]
        if len(bodies) != 1:
            raise ValueError("Exactly one explicit Body representation is required for mesh metrics")
        shape = ifcgeom.create_shape(settings, product, repr=bodies[0])
        verts, faces = list(shape.geometry.verts), list(shape.geometry.faces)
        if len(verts) % 3 or len(faces) % 3 or not verts or not all(math.isfinite(x) for x in verts):
            raise ValueError("Empty or invalid tessellation")
        return {"Status": "APPROXIMATE_MESH_READ", "Units": "metre", "WorldCoordinates": True,
                "VertexCount": len(verts) // 3, "TriangleCount": len(faces) // 3,
                "BoundingBoxApproximate": {"Min": [min(verts[i::3]) for i in range(3)], "Max": [max(verts[i::3]) for i in range(3)]},
                "ExactEquivalence": "NOT_PROVEN", "GeometrySynthesis": "NONE"}
    except Exception as error:
        return {"Status": "MESH_READING_FAILED", "ErrorType": type(error).__name__, "Error": str(error)[:300], "ExactEquivalence": "NOT_PROVEN"}


def probe(source: pathlib.Path, mesh: bool = False) -> dict:
    before_sha = sha256_file(source)
    model = ifcopenshell.open(str(source))
    counts = {kind: len(model.by_type(kind)) for kind in TARGET_TYPES}
    products = sorted((p for kind in TARGET_TYPES for p in model.by_type(kind)), key=lambda p: (p.GlobalId or "", p.id()))
    roots = model.by_type("IfcRoot")
    guid_counts = collections.Counter(p.GlobalId for p in roots if p.GlobalId)
    duplicate_guids = {guid: count for guid, count in sorted(guid_counts.items()) if count > 1}
    settings = None
    if mesh:
        settings = ifcgeom.settings()
        settings.set(settings.USE_WORLD_COORDS, True)
    rows = []
    for product in products:
        materials = material_evidence(product)
        representations, profiles, metadata = profile_geometry_evidence(model, product)
        grades = sorted({e["RawValue"] for e in materials if e["Category"] == "STRENGTH_GRADE"})
        labels = sorted({e["RawValue"] for e in materials if e["Category"] == "MATERIAL_LABEL"})
        profile_names = sorted({e["ProfileNameRaw"] for e in profiles if e["ProfileNameRaw"]})
        reasons = ["PROFILE_GEOMETRY_EQUIVALENCE_NOT_PROVEN", "NATIVE_TEKLA_READBACK_NOT_RUN"]
        if not grades:
            reasons.append("NO_EXPLICIT_STRENGTH_GRADE")
        elif len(grades) > 1:
            reasons.append("CONFLICTING_EXPLICIT_STRENGTH_GRADES")
        elif grades[0] not in ("S235JR", "S355JR"):
            reasons.append("RAW_GRADE_NOT_APPROVED_TASCHE_GRADE_NO_SUFFIX_INFERRED")
        if len(labels) > 1:
            reasons.append("MULTIPLE_MATERIAL_LABELS_OR_COMPOSITE_SOURCE_REVIEW")
        if len(profile_names) > 1:
            reasons.append("MULTIPLE_EXPLICIT_PROFILE_NAMES")
        if not representations:
            reasons.append("SOURCE_REPRESENTATION_MISSING")
        if not product.GlobalId or guid_counts.get(product.GlobalId, 0) != 1:
            reasons.append("SOURCE_GLOBAL_ID_INVALID_OR_DUPLICATE")
        row = {"SourceEntityId": product.id(), "IfcType": product.is_a(), "GlobalId": product.GlobalId, "NameRaw": product.Name,
               "ObjectTypeRaw": product.ObjectType, "TagRaw": product.Tag, "MaterialEvidence": materials,
               "ExplicitStrengthGradesRaw": grades, "ExplicitMaterialLabelsRaw": labels, "MaterialNormalized": None, "MaterialProductionAuthority": "NOT_APPROVED",
               "ProfileDefinitions": profiles, "ProfileMetadataEvidence": metadata, "ProfileNormalized": None,
               "Representations": representations, "ReviewReasons": reasons, "Status": "REVIEW_REQUIRED", "NativeWrite": False}
        if mesh:
            row["MeshSummaryApproximate"] = mesh_summary(product, settings)
        rows.append(row)
    after_sha = sha256_file(source)
    if before_sha != after_sha:
        raise RuntimeError("Source changed while probing; freeze is invalid")
    grade_counts = collections.Counter(g for row in rows for g in row["ExplicitStrengthGradesRaw"])
    label_counts = collections.Counter(label for row in rows for label in {e["RawValue"] for e in row["MaterialEvidence"] if e["Category"] == "MATERIAL_LABEL"})
    profile_types = collections.Counter(profile["IfcType"] for row in rows for profile in row["ProfileDefinitions"])
    representation_types = collections.Counter(rep["RepresentationType"] or "UNNAMED" for row in rows for rep in row["Representations"])
    return {"SchemaVersion": "1.0", "RecordedAtUtc": dt.datetime.now(dt.timezone.utc).isoformat(), "ProbeScriptSha256": sha256_file(pathlib.Path(__file__)), "Status": "PASSED_READING_SOURCE",
            "Source": {"FileName": source.name, "ByteCount": source.stat().st_size, "Sha256": before_sha, "HashAfterRead": after_sha, "IfcSchema": model.schema, "IfcOpenShellVersion": ifcopenshell.version, "LengthUnitScaleToMetre": ifcopenshell.util.unit.calculate_unit_scale(model) if model.by_type("IfcUnitAssignment") else None},
            "Scope": {"IfcTypes": list(TARGET_TYPES), "Classification": "SOURCE_ENTITY_CLASSES_ONLY_NO_INFERRED_STEEL_FILTER"},
            "Summary": {"SourceOccurrenceCount": len(rows), "CountsByIfcType": counts, "IfcRootCount": len(roots), "DuplicateGlobalIdsAllIfcRoots": duplicate_guids,
                        "MissingGlobalIdsInTargetScope": sum(not row["GlobalId"] for row in rows), "ExplicitStrengthGradeCountsRaw": dict(sorted(grade_counts.items())),
                        "ExplicitMaterialLabelCountsRaw": dict(sorted(label_counts.items())),
                        "ConflictingStrengthGradeOccurrenceCount": sum(len(row["ExplicitStrengthGradesRaw"]) > 1 for row in rows),
                        "MultipleMaterialLabelOccurrenceCount": sum(len(row["ExplicitMaterialLabelsRaw"]) > 1 for row in rows),
                        "WithoutExplicitStrengthGradeOccurrenceCount": sum(not row["ExplicitStrengthGradesRaw"] for row in rows),
                        "ProfileDefinitionTypeCounts": dict(sorted(profile_types.items())), "RepresentationTypeCounts": dict(sorted(representation_types.items())),
                        "MeshReadCountApproximate": sum(row.get("MeshSummaryApproximate", {}).get("Status") == "APPROXIMATE_MESH_READ" for row in rows),
                        "MeshFailedCount": sum(row.get("MeshSummaryApproximate", {}).get("Status") == "MESH_READING_FAILED" for row in rows),
                        "ReviewRequiredCount": len(rows), "NormalizedProductionMaterials": 0, "NormalizedProductionProfiles": 0},
            "Gates": {"ActualSourceReading": "PASS", "SourceHashUnchanged": "PASS", "ExactGeometryEquivalence": "NOT_PROVEN", "WindowsRuntime": "NOT_RUN", "ActiveTeklaConnection": "NOT_RUN", "TeklaCreateSaveReopenReadback": "NOT_RUN", "Phase4Release": "NOT_RELEASED"},
            "Assertions": {"NoMaterialDefaults": True, "NoProfileDefaults": True, "NoBoundingBoxBeamSynthesis": True, "NoModelMutation": True, "ApproximateMeshIsNotEquivalenceProof": True},
            "Parts": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--mesh-summary", action="store_true")
    args = parser.parse_args()
    report = probe(args.source, args.mesh_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"Status": report["Status"], "Sha256": report["Source"]["Sha256"], "Summary": report["Summary"], "Gates": report["Gates"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
