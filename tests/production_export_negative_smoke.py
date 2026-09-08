from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.production_export import ExportRequest, ProductionExportEngine
from cws_convertor.production_export.readiness import ReadinessGate
from cws_convertor.production_export.verify import ExportVerificationError, verify_export_directory


def run() -> None:
    gate = ReadinessGate(minimum_confidence=0.95)
    unsafe = {
        "id": "unsafe",
        "part_position": "X1",
        "classification": "make_part",
        "classification_confidence": 0.6,
        "normalized_profile": "HEA140",
        "normalized_material": "S355JR",
        "geometry_hash": "1" * 64,
        "manufacturing_hash": "2" * 64,
        "production_identity_hash": "3" * 64,
        "feature_validation_status": "estimated",
        "local_axes": None,
    }
    assessment = gate.assess(unsafe, ["nc1", "step", "ifc", "production_pdf"])
    assert not assessment.production_ready
    assert not assessment.allowed("nc1")
    codes = {m.code for m in assessment.messages_for("nc1")}
    assert "CWS-EXP-021" in codes
    assert "CWS-EXP-110" in codes
    assert "CWS-EXP-111" in codes
    assert "CWS-EXP-120" in codes

    # Canonical Project Model parts expose ``category`` rather than the older
    # generic ``classification`` key.  Review/material confidence must still
    # be enforced for this real application shape.
    project_part_shape = {
        "internal_id": "project-part",
        "category": "make_part",
        "classification_status": "review_required",
        "classification_confidence": 0.99,
        "normalized_profile": "HEA140",
        "normalized_material": "S355JR",
        "profile_confidence": 0.60,
        "material_confidence": 0.65,
        "geometry_hash": "4" * 64,
        "manufacturing_hash": "5" * 64,
        "production_identity_hash": "6" * 64,
        "feature_validation_status": "validated",
        "local_axes": {"x": [1, 0, 0]},
    }
    project_assessment = gate.assess(project_part_shape, ["nc1"])
    project_codes = {message.code for message in project_assessment.messages_for("nc1")}
    assert "CWS-EXP-022" in project_codes
    assert "CWS-EXP-105" in project_codes
    assert "CWS-EXP-106" in project_codes

    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        project = {"project_id": "negative", "project_name": "Negatief", "parts": [unsafe]}
        manifest, root, _ = ProductionExportEngine().export_project(
            project, ExportRequest(output_dir=tmp, create_zip=False)
        )
        assert manifest.summary["production_artifacts_exported"] == 0
        assert not manifest.summary["production_ready"]
        assert not list(root.rglob("*.nc1"))
        assert not list(root.rglob("*.step"))
        assert not list(root.rglob("*.ifc"))
        review_files = list(root.rglob("*REVIEW_NIET_VRIJGEGEVEN.pdf"))
        assert len(review_files) == 1
        verify_export_directory(root)

        # Tampering must be detected.
        manifest_file = root / "manifest.json"
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        data["project_name"] = "Gemanipuleerd"
        manifest_file.write_text(json.dumps(data), encoding="utf-8")
        try:
            verify_export_directory(root)
        except ExportVerificationError:
            pass
        else:
            raise AssertionError("Manipulatie van manifest is niet gedetecteerd")


if __name__ == "__main__":
    run()
    print("production_export_negative_smoke: OK")
