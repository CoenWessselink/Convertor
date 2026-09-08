"""Reproducible material/model acceptance; a skipped test is never a pass.

Every suite runs in a separate Python process. The child reports actual unittest
outcomes, including plain test_* functions and legacy run/main entry points.
This is deliberately not a parser of a test script's optimistic stdout message.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import unittest
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "validation" / "material_model_recognition"
NATIVE_MODULES = ("cadquery", "OCP", "ifcopenshell", "PySide6.QtWidgets", "fitz", "ezdxf", "reportlab", "pypdf", "numpy")


@dataclass(frozen=True)
class SuiteSpec:
    path: str
    area: str
    dependencies: tuple[str, ...] = ()
    entrypoint: str = ""

    @property
    def name(self) -> str:
        return Path(self.path).stem


SUITES = (
    SuiteSpec("tests/material_resolution_smoke.py", "material_catalog"),
    SuiteSpec("tests/profile_catalog_lookup_smoke.py", "model_recognition"),
    SuiteSpec("tests/ifc_material_recognition_smoke.py", "ifc_semantics"),
    SuiteSpec("tests/ifc_semantic_import_smoke.py", "ifc_semantics"),
    SuiteSpec("tests/native_ifc_material_binding_smoke.py", "ifc_semantics", ("numpy",)),
    SuiteSpec("tests/step_semantic_import_smoke.py", "step_semantics"),
    SuiteSpec("tests/project_auto_classification_smoke.py", "classification"),
    SuiteSpec("tests/project_classification_smoke.py", "classification"),
    SuiteSpec("tests/material_classification_safety_smoke.py", "classification"),
    SuiteSpec("tests/project_semantic_service_smoke.py", "classification"),
    SuiteSpec("tests/project_deferred_recognition_smoke.py", "classification"),
    SuiteSpec("tests/project_model_smoke.py", "project_regression"),
    SuiteSpec("tests/project_storage_smoke.py", "project_regression"),
    SuiteSpec("tests/project_bom_smoke.py", "project_regression"),
    SuiteSpec("tests/project_service_smoke.py", "project_regression"),
    SuiteSpec("tests/unified_project_schema_u1_smoke.py", "project_regression"),
    SuiteSpec("tests/material_workbench_gate_smoke.py", "workbench_release"),
    SuiteSpec("tests/material_release_gate_smoke.py", "workbench_release"),
    SuiteSpec("tests/part_workbench_smoke.py", "workbench_release"),
    SuiteSpec("tests/production_export_negative_smoke.py", "workbench_release", ("reportlab",), "run"),
    SuiteSpec("tests/production_export_smoke.py", "workbench_release", ("reportlab",), "run"),
    SuiteSpec("tests/manufacturing_interpreter_material_promotion_step_smoke.py", "model_recognition"),
    SuiteSpec("tests/manufacturing_topology_safety_smoke.py", "model_recognition"),
    SuiteSpec("tests/manufacturing_material_evidence_safety_smoke.py", "model_recognition"),
    SuiteSpec("tests/conversion_material_defaults_smoke.py", "conversion_material_policy"),
    SuiteSpec("tests/ifc_conversion_material_policy_smoke.py", "conversion_material_policy"),
    SuiteSpec("tests/conversion_material_native_smoke.py", "conversion_material_policy", ("cadquery", "OCP")),
    SuiteSpec("tests/material_review_logic_smoke.py", "material_review"),
    SuiteSpec("tests/source_material_evidence_smoke.py", "pdf_dxf_evidence", ("fitz",)),
    SuiteSpec("tests/pdf_material_candidate_smoke.py", "pdf_dxf_evidence", ("fitz", "pypdf", "reportlab", "numpy")),
    SuiteSpec("tests/pdf_model_material_gate_native_smoke.py", "pdf_dxf_evidence", ("cadquery", "OCP", "fitz", "pypdf", "reportlab", "numpy")),
    SuiteSpec("tests/material_review_ui_smoke.py", "material_review", ("PySide6.QtWidgets",)),
    SuiteSpec("tests/viewer_v9_workbench_persistence_smoke.py", "material_review", ("cadquery", "OCP")),
    SuiteSpec("tests/manufacturing_interpreter_phase1_smoke.py", "model_recognition", ("cadquery", "OCP"), "main"),
    SuiteSpec("tests/part_workbench_roundtrip_smoke.py", "workbench_release", ("cadquery", "OCP", "ifcopenshell")),
    SuiteSpec("tests/production_editor_smoke.py", "workbench_release", ("cadquery", "OCP")),
    # Mixed suite: execute pure checks even without CAD. Its two native skips
    # deliberately make the suite INCOMPLETE, never PASS.
    SuiteSpec("tests/production_normalization_smoke.py", "workbench_release"),
    SuiteSpec("tests/production_normalization_safety_smoke.py", "workbench_release"),
    SuiteSpec("tests/bom_material_integration_smoke.py", "bom_material_safety"),
    SuiteSpec("tests/bom_production_hub_complete_smoke.py", "bom_production_hub"),
    SuiteSpec("tests/bom_production_hub_smoke.py", "bom_production_hub"),
    SuiteSpec("tests/viewer_shared_cache_lasso_smoke.py", "bom_viewer_integration", ("numpy",)),
    SuiteSpec("tests/material_model_acceptance_runner_smoke.py", "acceptance_integrity"),
)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def percent(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def git_output(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def source_fingerprint(root: Path = ROOT) -> dict[str, Any]:
    """Hash source files, including untracked edits; exclude generated evidence."""
    names = git_output(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split("\0")
    source_paths = []
    for name in sorted(set(names)):
        path = root / name
        if not name or not path.is_file() or path.is_symlink():
            continue
        if any(part in {"validation", "release", "dist", "build", ".git", "__pycache__"} for part in Path(name).parts):
            continue
        if path.suffix.lower() not in {".py", ".json", ".yml", ".yaml", ".txt", ".toml", ".ini", ".md"}:
            continue
        source_paths.append({"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    payload = json.dumps(source_paths, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {
        "git_sha": git_output(root, "rev-parse", "HEAD"),
        "git_branch": git_output(root, "branch", "--show-current"),
        "dirty": bool(git_output(root, "status", "--porcelain=v1")),
        "source_file_count": len(source_paths),
        "source_tree_sha256": hashlib.sha256(payload).hexdigest(),
        "files": source_paths,
    }


class EvidenceResult(unittest.TextTestResult):
    """Record logical test methods separately from subtest/fixture events."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.records: dict[str, dict[str, Any]] = {}

    def record(self, test: Any, status: str, detail: str = "", *, started: bool = False) -> None:
        item = self.records.setdefault(test.id(), {"test": test.id(), "status": status, "started": started, "details": []})
        priority = {"RUNNING": 0, "PASS": 1, "SKIPPED": 2, "EXPECTED_FAILURE": 3, "FAIL": 4, "ERROR": 5}
        if priority[status] >= priority[item["status"]]:
            item["status"] = status
        if started:
            item["started"] = True
        if detail:
            item["details"].append(detail)

    def startTest(self, test: Any) -> None:
        super().startTest(test)
        self.record(test, "RUNNING", started=True)

    def addSuccess(self, test: Any) -> None:
        super().addSuccess(test)
        self.record(test, "PASS")

    def addFailure(self, test: Any, err: Any) -> None:
        super().addFailure(test, err)
        self.record(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test: Any, err: Any) -> None:
        super().addError(test, err)
        self.record(test, "ERROR", self._exc_info_to_string(err, test))

    def addSkip(self, test: Any, reason: str) -> None:
        super().addSkip(test, reason)
        self.record(test, "SKIPPED", reason)

    def addExpectedFailure(self, test: Any, err: Any) -> None:
        super().addExpectedFailure(test, err)
        self.record(test, "EXPECTED_FAILURE", self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test: Any) -> None:
        super().addUnexpectedSuccess(test)
        self.record(test, "FAIL", "Unexpected success: expected-failure contract must be repaired.")

    def addSubTest(self, test: Any, subtest: Any, err: Any) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            status = "FAIL" if issubclass(err[0], test.failureException) else "ERROR"
            self.record(test, status, subtest.id() + "\n" + self._exc_info_to_string(err, test))


def collect_suite(module: Any, entrypoint: str = "") -> unittest.TestSuite:
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    for name in sorted(vars(module)):
        function = getattr(module, name)
        if name.startswith("test_") and callable(function) and getattr(function, "__module__", None) == module.__name__:
            suite.addTest(unittest.FunctionTestCase(function, description=f"{module.__name__}.{name}"))
    if suite.countTestCases() == 0 and entrypoint:
        def legacy_entrypoint() -> None:
            result = getattr(module, entrypoint)()
            if result not in (None, 0):
                raise AssertionError(f"Entry point returned {result!r}")
        suite.addTest(unittest.FunctionTestCase(legacy_entrypoint, description=f"{module.__name__}.{entrypoint}"))
    return suite


def run_child(path: Path, result_path: Path, entrypoint: str = "") -> int:
    for directory in (ROOT, ROOT / "src"):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    payload: dict[str, Any] = {"status": "ERROR", "tests_run": 0, "tests_passed": 0, "records": []}
    try:
        spec = importlib.util.spec_from_file_location("cws_acceptance_" + path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        suite = collect_suite(module, entrypoint)
        if not suite.countTestCases():
            raise RuntimeError("No test cases discovered; zero tests cannot pass acceptance.")
        result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
        records = list(result.records.values())
        has_incomplete = bool(result.skipped or result.expectedFailures)
        status = "FAIL" if not result.wasSuccessful() else "INCOMPLETE" if has_incomplete else "PASS"
        payload.update(
            status=status,
            tests_run=result.testsRun,
            tests_passed=sum(item["started"] and item["status"] == "PASS" for item in records),
            skipped_events=len(result.skipped),
            expected_failure_events=len(result.expectedFailures),
            failure_events=len(result.failures) + len(result.unexpectedSuccesses),
            error_events=len(result.errors),
            records=records,
        )
    except BaseException:
        # Includes SystemExit(0) during import: this is not proof of a test run.
        payload["error"] = traceback.format_exc()
        print(payload["error"], file=sys.stderr)
    write_json(result_path, payload)
    return 0 if payload["status"] == "PASS" and payload["tests_run"] > 0 else 1


def probe_dependencies(modules: tuple[str, ...] = NATIVE_MODULES) -> dict[str, dict[str, Any]]:
    findings = {}
    for name in modules:
        command = [sys.executable, "-c", "import importlib; importlib.import_module(" + repr(name) + "); print('IMPORT_OK')"]
        try:
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=90, check=False)
            findings[name] = {"available": result.returncode == 0, "returncode": result.returncode, "detail": (result.stderr or result.stdout)[-5000:]}
        except subprocess.TimeoutExpired:
            findings[name] = {"available": False, "detail": "Import probe timed out after 90 seconds."}
    return findings


def run_suite(spec: SuiteSpec, output: Path, dependencies: dict[str, dict[str, Any]], timeout: float) -> dict[str, Any]:
    record: dict[str, Any] = {"suite": spec.name, "path": spec.path, "area": spec.area, "status": "BLOCKED", "tests_run": 0, "tests_passed": 0}
    log_path = output / "logs" / f"{spec.name}.log"
    result_path = output / "suites" / f"{spec.name}.json"
    record["log"] = str(log_path.relative_to(output))
    record["result"] = str(result_path.relative_to(output))
    missing = [name for name in spec.dependencies if not dependencies.get(name, {}).get("available")]
    if not (ROOT / spec.path).is_file():
        record["reason"] = "Test suite file is missing."
    elif missing:
        record["reason"] = "Missing or broken required imports: " + ", ".join(missing)
    else:
        # Never accept evidence left behind by an older run of this suite.
        result_path.unlink(missing_ok=True)
        command = [sys.executable, str(Path(__file__).resolve()), "--child", str(ROOT / spec.path), "--child-result", str(result_path)]
        if spec.entrypoint:
            command += ["--entrypoint", spec.entrypoint]
        record["command"] = command
        environment = dict(os.environ, PYTHONUTF8="1", QT_QPA_PLATFORM="offscreen", CWS_HEADLESS_GUI_SMOKE="1", CWS_RECOGNITION_EVIDENCE_DIR=str(output))
        started = time.monotonic()
        try:
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment, timeout=timeout, check=False)
            record["returncode"] = process.returncode
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(process.stdout + "\n--- STDERR ---\n" + process.stderr, encoding="utf-8")
            if result_path.is_file():
                record.update(json.loads(result_path.read_text(encoding="utf-8")))
            else:
                record.update(status="ERROR", reason="Child exited without structured test evidence.")
            if process.returncode != 0 and record["status"] == "PASS":
                record.update(status="ERROR", reason="Child returned nonzero despite a PASS result.")
            if record["status"] == "PASS" and (record.get("tests_run", 0) == 0 or record.get("skipped_events", 0) or record.get("expected_failure_events", 0)):
                record.update(status="INCOMPLETE", reason="Zero tests, skips, or expected failures are not a pass.")
        except subprocess.TimeoutExpired as exc:
            record.update(status="TIMEOUT", reason=f"Suite exceeded {timeout} seconds.")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            def as_text(value: str | bytes | None) -> str:
                return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
            log_path.write_text(as_text(exc.stdout) + "\n" + as_text(exc.stderr), encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            record.update(status="ERROR", reason=f"Cannot execute suite or read its evidence: {exc}")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                log.write("\n" + traceback.format_exc())
        record["duration_seconds"] = round(time.monotonic() - started, 3)
        write_json(result_path, record)
        return record
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(record["reason"] + "\n", encoding="utf-8")
    write_json(result_path, record)
    return record


def summarize(records: list[dict[str, Any]], *, required_suites: int) -> dict[str, Any]:
    counts = Counter(item["status"] for item in records)
    test_count = sum(item.get("tests_run", 0) for item in records)
    test_passed = sum(item.get("tests_passed", 0) for item in records)
    areas = {}
    for area in sorted({spec.area for spec in SUITES} | {item["area"] for item in records}):
        selected = [item for item in records if item["area"] == area]
        required = sum(spec.area == area for spec in SUITES) or len(selected)
        passed = sum(item["status"] == "PASS" for item in selected)
        areas[area] = {"required_suites": required, "evaluated_suites": len(selected), "passed_suites": passed, "suite_pass_percentage": percent(passed, required)}
    return {
        "required_suites": required_suites,
        "evaluated_suites": len(records),
        "passed_suites": counts["PASS"],
        "suite_status_counts": dict(counts),
        "suite_pass_percentage": percent(counts["PASS"], required_suites),
        "tests_run": test_count,
        "tests_passed": test_passed,
        "executed_test_pass_percentage": percent(test_passed, test_count),
        "skipped_events": sum(item.get("skipped_events", 0) for item in records),
        "expected_failure_events": sum(item.get("expected_failure_events", 0) for item in records),
        "areas": areas,
        "percentage_scope": "Suite percentages measure this fixed acceptance manifest, not universal recognition accuracy. Tests not run have no fabricated test count.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-native", action="store_true", help="Require the full manifest and all real native imports; no subsets or skipped tests.")
    parser.add_argument("--suite", action="append", default=[], help="Development-only suite stem (repeatable); never gives full acceptance.")
    parser.add_argument("--timeout", type=float, default=900.0, help="Maximum seconds per suite.")
    parser.add_argument("--child", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--child-result", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--entrypoint", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.child:
        if not args.child_result:
            parser.error("--child-result is required with --child")
        return run_child(args.child, args.child_result, args.entrypoint)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.require_native and args.suite:
        parser.error("--require-native requires every suite; remove --suite")
    unknown = set(args.suite) - {suite.name for suite in SUITES}
    if unknown:
        parser.error("Unknown suites: " + ", ".join(sorted(unknown)))
    selected = tuple(suite for suite in SUITES if not args.suite or suite.name in args.suite)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    before = source_fingerprint()
    write_json(output / "SOURCE_FINGERPRINT.json", before)
    dependencies = probe_dependencies()
    write_json(output / "DEPENDENCIES.json", dependencies)
    records = []
    for spec in selected:
        print(f"RUN {spec.name}", flush=True)
        record = run_suite(spec, output, dependencies, args.timeout)
        records.append(record)
        print(f"{record['status']} {spec.name}: {record['tests_passed']}/{record['tests_run']} tests passed", flush=True)
    after = source_fingerprint()
    unchanged = bool(before["git_sha"] and before["source_file_count"]) and before["source_tree_sha256"] == after["source_tree_sha256"] and before["git_sha"] == after["git_sha"]
    summary = summarize(records, required_suites=len(SUITES))
    selected_passed = bool(records) and all(item["status"] == "PASS" for item in records)
    native_available = all(item["available"] for item in dependencies.values())
    full_acceptance = selected_passed and len(records) == len(SUITES) and unchanged and native_available
    status = "PASS" if full_acceptance else "SUBSET_PASS" if args.suite and selected_passed and unchanged else "INCOMPLETE"
    if not unchanged or any(item["status"] in {"FAIL", "ERROR", "TIMEOUT"} for item in records):
        status = "FAIL"
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "acceptance_passed": full_acceptance,
        "installer_release_approved": False,
        "installer_release_note": "This recognition gate does not prove packaged Windows EXE/installer, full-program regression, or field recognition accuracy.",
        "require_native": args.require_native,
        "native_available": native_available,
        "source_unchanged_during_run": unchanged,
        "source": {key: value for key, value in before.items() if key != "files"},
        "source_after": {key: value for key, value in after.items() if key != "files"},
        "runtime": {"python": sys.version, "executable": sys.executable, "platform": sys.platform},
        "summary": summary,
        "dependencies": dependencies,
        "suites": records,
    }
    write_json(output / "FINAL_ACCEPTANCE.json", payload)
    print(json.dumps({"status": status, **summary}, ensure_ascii=False, indent=2), flush=True)
    return 0 if full_acceptance or (status == "SUBSET_PASS" and not args.require_native) else 1


if __name__ == "__main__":
    raise SystemExit(main())
