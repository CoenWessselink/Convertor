from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load_manifest_module():
    path = ROOT / "tools" / "build_codex_release_manifest.py"
    spec = importlib.util.spec_from_file_location("build_codex_release_manifest", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodexReleasePipelineContractTests(unittest.TestCase):
    def test_both_release_entrypoints_use_strict_manifest_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-windows-exe.yml").read_text(
            encoding="utf-8"
        )
        batch = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")
        command = "tools\\build_codex_release_manifest.py"
        self.assertIn(command, batch)
        self.assertIn(command.replace("\\", "/"), workflow)
        self.assertIn("--runtime-results", batch)
        self.assertIn("--runtime-results", workflow)

    def test_workflow_routes_the_bom_release_branch_and_uploads_release(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "build-windows-exe.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("agent/cws-bom-production-hub-v1", workflow)
        self.assertIn("tools/capture_bom_production_hub.py", workflow)
        self.assertIn("tools/run_phase3_gates.py --reuse-fresh-evidence", workflow)
        self.assertIn("path: release/*", workflow)

    def test_manifest_gate_only_tolerates_generated_evidence_changes(self) -> None:
        module = _load_manifest_module()
        self.assertTrue(module.allowed_generated_change("validation/phases/result.json"))
        self.assertTrue(
            module.allowed_generated_change(
                "requirements/MASTER_REQUIREMENT_TRACEABILITY.json"
            )
        )
        self.assertFalse(module.allowed_generated_change("cws_convertor/product.py"))
        self.assertFalse(module.allowed_generated_change("installer/CWS_Convertor.iss"))

    def test_manifest_gate_accepts_only_explicit_success_states(self) -> None:
        module = _load_manifest_module()
        for status in ("pass", "passed", "green", "complete", "success"):
            self.assertTrue(module.passed({"status": status}))
        for status in ("", "red", "failed", "blocked", "skipped"):
            self.assertFalse(module.passed({"status": status}))


if __name__ == "__main__":
    unittest.main()
