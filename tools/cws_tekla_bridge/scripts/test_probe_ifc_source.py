#!/usr/bin/env python3
"""Actual source regression: explicitly supply the private Het Koraal IFC file.

No model file is embedded in the repository. Missing/mismatched real input fails
this command; it is never skipped or counted as a Tekla runtime pass.
"""
import argparse
import json
import pathlib
import tempfile
import unittest.mock

import ifcopenshell
import probe_ifc_source as probe

REFERENCE_SHA256 = "38f708e817188cba112bdfdbe4f4a93518d2073510fa6cd8fc0f81fe6c5bbbe8"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    results = []

    def check(name, action):
        try:
            action()
            results.append({"Name": name, "Status": "PASS"})
        except Exception as error:
            results.append({"Name": name, "Status": "FAIL", "Error": type(error).__name__ + ": " + str(error)})

    def require(condition, message):
        if not condition:
            raise AssertionError(message)

    report = None

    def freeze():
        require(args.source.is_file(), "Private real IFC source must be supplied; this gate is not skippable")
        require(probe.sha256_file(args.source) == REFERENCE_SHA256, "Source does not match the frozen real reference")
    check("Actual IFC reference SHA-256 matches freeze", freeze)
    if results[-1]["Status"] == "PASS":
        report = probe.probe(args.source)
        check("Actual IFC raw occurrence counts and identity coverage", lambda: require(
            report["Summary"]["CountsByIfcType"] == {"IfcBeam": 214, "IfcColumn": 90, "IfcMember": 0, "IfcPlate": 0}
            and report["Summary"]["SourceOccurrenceCount"] == 304 and report["Summary"]["DuplicateGlobalIdsAllIfcRoots"] == {}
            and report["Summary"]["MissingGlobalIdsInTargetScope"] == 0,
            "Exact frozen source identities/class counts changed"))
        check("Actual IFC source grades remain literal and unresolved", lambda: require(
            report["Summary"]["ExplicitStrengthGradeCountsRaw"] == {"S235": 165, "S275": 32, "S355": 35}
            and report["Summary"]["WithoutExplicitStrengthGradeOccurrenceCount"] == 72
            and all(p["MaterialNormalized"] is None and p["ProfileNormalized"] is None and not p["NativeWrite"] for p in report["Parts"]),
            "No grade suffix/default, profile inference or native write is authorized"))
        check("Source-read success cannot become Windows/Tekla phase 4 release", lambda: require(
            report["Status"] == "PASSED_READING_SOURCE" and report["Gates"]["ExactGeometryEquivalence"] == "NOT_PROVEN"
            and report["Gates"]["ActiveTeklaConnection"] == "NOT_RUN" and report["Gates"]["Phase4Release"] == "NOT_RELEASED"
            and report["Summary"]["ReviewRequiredCount"] == 304, "Source proof falsely promoted into runtime proof"))

        def changed_source():
            with unittest.mock.patch.object(probe, "sha256_file", side_effect=[REFERENCE_SHA256, "changed-after-read"]):
                try:
                    probe.probe(args.source)
                except RuntimeError as error:
                    require("Source changed" in str(error), "Wrong failure cause")
                    return
            raise AssertionError("Source hash drift was accepted")
        check("Source mutation during inspection invalidates freeze", changed_source)

    def conflicting_source():
        model = ifcopenshell.file(schema="IFC4")
        beam = model.create_entity("IfcBeam", GlobalId=ifcopenshell.guid.new(), Name="No engineering defaults")
        for name, grade in (("GdV", "S275JR"), ("Independent detail", "S355JR")):
            prop = model.create_entity("IfcPropertySingleValue", Name="Sterkteklasse", NominalValue=model.create_entity("IfcLabel", grade))
            pset = model.create_entity("IfcPropertySet", GlobalId=ifcopenshell.guid.new(), Name=name, HasProperties=[prop])
            model.create_entity("IfcRelDefinesByProperties", GlobalId=ifcopenshell.guid.new(), RelatedObjects=[beam], RelatingPropertyDefinition=pset)
        with tempfile.TemporaryDirectory(prefix="cws-ifc-probe-") as temp:
            path = pathlib.Path(temp) / "conflict.ifc"
            model.write(str(path))
            row = probe.probe(path)["Parts"][0]
        require(row["ExplicitStrengthGradesRaw"] == ["S275JR", "S355JR"], "Evidence from one part was overwritten by another property")
        require("CONFLICTING_EXPLICIT_STRENGTH_GRADES" in row["ReviewReasons"] and row["MaterialNormalized"] is None
                and row["ProfileNormalized"] is None and not row["NativeWrite"], "Conflict was silently resolved")
    check("Contradictory explicit source properties remain REVIEW_REQUIRED", conflicting_source)
    payload = {"SchemaVersion": "1.0", "Environment": "OFFLINE_REAL_IFC_SOURCE_READING", "ReferenceSourceSha256": REFERENCE_SHA256,
               "TestCount": len(results), "Passed": sum(r["Status"] == "PASS" for r in results), "Failed": sum(r["Status"] != "PASS" for r in results),
               "WindowsRuntime": "NOT_RUN", "TeklaRuntime": "NOT_RUN", "Results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if payload["Failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
