from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_material_model_recognition_acceptance import (
    NATIVE_MODULES,
    SUITES,
    SuiteSpec,
    main,
    probe_dependencies,
    run_suite,
    source_fingerprint,
    summarize,
)


class MaterialModelAcceptanceRunnerTests(unittest.TestCase):
    def child(self, source: str, *, entrypoint: str = "") -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory(prefix="cws-recognition-acceptance-") as folder:
            root = Path(folder)
            suite = root / "fixture.py"
            result = root / "result.json"
            suite.write_text(source, encoding="utf-8")
            command = [sys.executable, str(ROOT / "tools/run_material_model_recognition_acceptance.py"), "--child", str(suite), "--child-result", str(result)]
            if entrypoint:
                command.extend(("--entrypoint", entrypoint))
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=30)
            self.assertTrue(result.is_file(), process.stderr)
            return process, json.loads(result.read_text(encoding="utf-8"))

    def test_unittest_and_plain_functions_have_exact_logical_counts(self) -> None:
        process, report = self.child("import unittest\nclass Checks(unittest.TestCase):\n def test_one(self):\n  self.assertTrue(True)\ndef test_two():\n assert 2 + 2 == 4\n")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["tests_run"], 2)
        self.assertEqual(report["tests_passed"], 2)

    def test_manifest_has_unique_suites_and_every_dependency_is_probed(self) -> None:
        self.assertEqual(len(SUITES), len({suite.name for suite in SUITES}))
        self.assertEqual(len(SUITES), len({suite.path for suite in SUITES}))
        self.assertTrue({name for suite in SUITES for name in suite.dependencies} <= set(NATIVE_MODULES))

    def test_exit_zero_with_skipped_test_is_never_pass(self) -> None:
        process, report = self.child("import unittest\nclass Checks(unittest.TestCase):\n @unittest.skip('native runtime unavailable')\n def test_native(self): pass\n def test_core(self): pass\n")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["tests_run"], 2)
        self.assertEqual(report["tests_passed"], 1)
        self.assertEqual(report["skipped_events"], 1)

    def test_expected_failure_is_not_acceptance(self) -> None:
        process, report = self.child("import unittest\nclass Checks(unittest.TestCase):\n @unittest.expectedFailure\n def test_pending(self): self.fail('not implemented')\n")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["tests_passed"], 0)
        self.assertEqual(report["expected_failure_events"], 1)

    def test_failed_subtests_do_not_inflate_logical_test_count(self) -> None:
        process, report = self.child("import unittest\nclass Checks(unittest.TestCase):\n def test_many(self):\n  for n in range(2):\n   with self.subTest(n=n): self.fail(str(n))\n")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["tests_run"], 1)
        self.assertEqual(report["tests_passed"], 0)
        self.assertEqual(report["failure_events"], 2)

    def test_zero_tests_and_system_exit_zero_during_import_are_errors(self) -> None:
        for source in ("answer = 42\n", "raise SystemExit(0)\n"):
            with self.subTest(source=source):
                process, report = self.child(source)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(report["status"], "ERROR")
                self.assertEqual(report["tests_run"], 0)

    def test_legacy_entrypoint_return_code_is_checked(self) -> None:
        process, report = self.child("def main(): return 3\n", entrypoint="main")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["tests_run"], 1)

    def test_missing_native_dependency_is_blocked_with_logs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-recognition-blocked-") as folder:
            output = Path(folder)
            spec = SuiteSpec("tests/material_resolution_smoke.py", "material_catalog", ("cadquery",))
            report = run_suite(spec, output, {"cadquery": {"available": False}}, timeout=10)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertEqual(report["tests_run"], 0)
            self.assertTrue((output / report["log"]).is_file())
            self.assertTrue((output / report["result"]).is_file())

    def test_stale_pass_file_is_not_reused_when_child_emits_no_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-recognition-stale-") as folder:
            output = Path(folder)
            spec = SuiteSpec("tests/material_resolution_smoke.py", "material_catalog")
            old = output / "suites" / f"{spec.name}.json"
            old.parent.mkdir(parents=True)
            old.write_text(json.dumps({"status": "PASS", "tests_run": 999, "tests_passed": 999}), encoding="utf-8")
            with patch("tools.run_material_model_recognition_acceptance.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
                report = run_suite(spec, output, {}, timeout=10)
            self.assertEqual(report["status"], "ERROR")
            self.assertEqual(report["tests_passed"], 0)

    def test_full_manifest_is_percentage_denominator_in_partial_run(self) -> None:
        result = summarize([
            {"suite": "one", "area": "fixture", "status": "PASS", "tests_run": 2, "tests_passed": 2},
            {"suite": "two", "area": "fixture", "status": "BLOCKED", "tests_run": 0, "tests_passed": 0},
        ], required_suites=4)
        self.assertEqual(result["suite_pass_percentage"], 25.0)
        self.assertEqual(result["executed_test_pass_percentage"], 100.0)
        self.assertEqual(result["required_suites"], 4)
        self.assertEqual(result["evaluated_suites"], 2)

    def test_strict_native_rejects_subset_without_starting_tests(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--require-native", "--suite", "material_resolution_smoke"])
        self.assertEqual(raised.exception.code, 2)

    def test_dependency_probe_imports_module_instead_of_only_finding_spec(self) -> None:
        result = probe_dependencies(("json", "cws_definitely_not_installed_module_389a6"))
        self.assertTrue(result["json"]["available"])
        self.assertFalse(result["cws_definitely_not_installed_module_389a6"]["available"])

    def test_source_fingerprint_includes_untracked_source_and_ignores_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-recognition-fingerprint-") as folder:
            root = Path(folder)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            source = root / "model.py"
            source.write_text("VERSION = 1\n", encoding="utf-8")
            first = source_fingerprint(root)
            self.assertEqual(first["source_file_count"], 1)
            (root / "validation").mkdir()
            (root / "validation/result.json").write_text("{}", encoding="utf-8")
            self.assertEqual(source_fingerprint(root)["source_tree_sha256"], first["source_tree_sha256"])
            source.write_text("VERSION = 2\n", encoding="utf-8")
            self.assertNotEqual(source_fingerprint(root)["source_tree_sha256"], first["source_tree_sha256"])


if __name__ == "__main__":
    unittest.main()
