from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from tools.build_trimble_parity_validation import BLOCKED_EXTERNAL_EVIDENCE, PASS, build_validation


class TrimbleParityEvidenceContractTests(unittest.TestCase):
    def _session(self, root: Path) -> Path:
        trimble_exe = root / "TrimbleConnect.exe"
        cws_exe = root / "CWS_Convertor.exe"
        model = root / "same.ifc"
        trimble_exe.write_bytes(b"trimble")
        cws_exe.write_bytes(b"cws")
        model.write_bytes(b"ISO-10303-21;")
        captures = root / "captures"
        captures.mkdir()
        (captures / "trimble_reference.jpg").write_bytes(b"trimble-capture")
        (captures / "cws_reference.jpg").write_bytes(b"cws-capture")
        session = {
            "trimble": {"executable": str(trimble_exe), "file_version": "test", "model_path": str(model)},
            "cws": {"executable": str(cws_exe), "source_file_id": "same-source"},
            "pairing": {"same_model_verified": True, "same_camera_verified": False},
            "host": {"os": "Windows", "gpus": ["test-gpu"]},
            "capture_directory": str(captures),
            "input": {"observations": {}},
            "performance": {"trimble_measured": False},
            "ui_audit": {"current_primary_workspaces": ["Viewer"]},
            "architecture_audit": {"context_action_service_found": False},
        }
        path = root / "REFERENCE_SESSION.json"
        path.write_text(json.dumps(session), encoding="utf-8")
        return path

    def test_internal_pass_cannot_promote_missing_external_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "validation"
            phases = root / "phases"
            checklist = build_validation({"status": PASS, "duration_seconds": 0.25}, output_dir=output, phase_output_dir=phases, session_path=self._session(root))
            self.assertEqual(42, checklist["case_total"])
            self.assertEqual(BLOCKED_EXTERNAL_EVIDENCE, checklist["status"])
            self.assertGreater(checklist["required_pass"], 0)
            self.assertGreater(checklist["required_blocked_external_evidence"], 0)
            self.assertNotEqual(PASS, json.loads((output / "TRIMBLE_PARITY_VISUAL_MATRIX.json").read_text())["status"])
            self.assertNotEqual(PASS, json.loads((output / "TRIMBLE_CWS_PERFORMANCE_COMPARISON.json").read_text())["status"])

    def test_reference_environment_can_pass_while_comparison_stays_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / "validation"
            phases = root / "phases"
            build_validation({"status": PASS, "duration_seconds": 0.1}, output_dir=output, phase_output_dir=phases, session_path=self._session(root))
            environment = json.loads((output / "TRIMBLE_REFERENCE_ENVIRONMENT.json").read_text())
            mapping = json.loads((output / "TRIMBLE_INPUT_MAPPING.json").read_text())
            matrix = json.loads((output / "TRIMBLE_PARITY_MATRIX.json").read_text())
            self.assertEqual(PASS, environment["status"])
            self.assertEqual(BLOCKED_EXTERNAL_EVIDENCE, mapping["status"])
            self.assertEqual(42, len(matrix["cases"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
