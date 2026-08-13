from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from cws_convertor.production_export import ExportRequest, ProductionExportEngine
from cws_convertor.production_export.project_loader import load_project_snapshot
from cws_convertor.production_export.verify import verify_export_directory, verify_export_zip


def _project(tmp: Path) -> tuple[dict, Path]:
    trusted_nc1 = b"ST\n** CWS TEST NC1\nEN\n"
    trusted_step = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('CWS TEST'),'2;1');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
    trusted_ifc = b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('ViewDefinition [ReferenceView_V1.2]'),'2;1');\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n"
    trusted_pdf = b"%PDF-1.4\n% CWS trusted test artifact\n%%EOF\n"
    part = {
        "id": "part-001",
        "part_position": "P001",
        "assembly_marks": ["M001"],
        "classification": "make_part",
        "classification_confidence": 1.0,
        "classification_confirmed": True,
        "normalized_profile": "STRIP10*100",
        "normalized_material": "S355JR",
        "length_mm": 500.0,
        "mass_kg": 3.925,
        "geometry_hash": "a" * 64,
        "manufacturing_hash": "b" * 64,
        "production_identity_hash": "c" * 64,
        "feature_validation_status": "validated",
        "local_axes": {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]},
        "trusted_artifacts": {
            "nc1": trusted_nc1,
            "step": trusted_step,
            "ifc": trusted_ifc,
            "production_pdf": trusted_pdf,
        },
    }
    blocked = {
        "id": "part-002",
        "part_position": "P002",
        "assembly_marks": ["M001"],
        "classification": "unknown",
        "geometry_hash": "d" * 64,
        "manufacturing_hash": "",
    }
    project = {
        "schema_version": "2.3",
        "project_id": "project-test",
        "project_name": "Export Veiligheidstest",
        "parts": [part, blocked],
        "assemblies": [{"id": "asm-1", "assembly_mark": "M001", "part_ids": ["part-001", "part-002"]}],
    }
    project_path = tmp / "test.cwscproj"
    with zipfile.ZipFile(project_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(project, ensure_ascii=False, default=lambda value: {"bytes_base64": __import__('base64').b64encode(value).decode('ascii')}))
    # Replace the bytes with base64 dictionaries for transport through JSON.
    raw = json.loads(zipfile.ZipFile(project_path).read("project.json"))
    for fmt, value in list(raw["parts"][0]["trusted_artifacts"].items()):
        if isinstance(value, dict) and "bytes_base64" in value:
            raw["parts"][0]["trusted_artifacts"][fmt] = value
    with zipfile.ZipFile(project_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps(raw, ensure_ascii=False))
    return project, project_path


def run() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        project, project_path = _project(tmp)
        loaded = load_project_snapshot(project_path)
        assert loaded.snapshot["project_id"] == "project-test"
        request = ExportRequest(output_dir=tmp / "out")
        manifest, root, zip_path = ProductionExportEngine().export_project(loaded.snapshot, request)
        assert len(manifest.items) == 2
        first = next(item for item in manifest.items if item.part_id == "part-001")
        second = next(item for item in manifest.items if item.part_id == "part-002")
        assert first.status.value == "exported", first.to_dict()
        assert second.status.value in {"partial", "blocked"}, second.to_dict()
        assert any(a.format == "nc1" and a.status.value == "exported" for a in first.artifacts)
        assert any(a.format == "nc1" and a.status.value == "blocked" for a in second.artifacts)
        assert any(a.format == "review_pdf" and a.status.value == "exported" for a in second.artifacts)
        assert (root / "manifest.json").is_file()
        assert (root / "SHA256SUMS.txt").is_file()
        assert (root / "assemblies" / "M001" / "stuklijst.csv").is_file()
        assert verify_export_directory(root)["valid"]
        assert zip_path is not None and verify_export_zip(zip_path)["valid"]

        # Path traversal and unknown format must be rejected.
        evil = dict(project)
        evil["parts"] = [dict(project["parts"][0], part_position="../../escape")]
        manifest2, root2, _ = ProductionExportEngine().export_project(
            evil, ExportRequest(output_dir=tmp / "out2", formats=["json"], create_zip=False)
        )
        assert root2.is_dir()
        assert not (tmp / "escape.json").exists()
        try:
            ProductionExportEngine().export_project(
                project, ExportRequest(output_dir=tmp / "bad", formats=["gcode"])
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Onbekend formaat is niet geweigerd")


if __name__ == "__main__":
    run()
    print("production_export_smoke: OK")
