"""Create reproducible, machine-readable evidence for core phase 0.

The report deliberately stores only aggregate information for local reference
registries. Confidential model paths and filenames never leave the workstation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib import metadata
from itertools import zip_longest
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from typing import Iterable
import zipfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_SCHEMA = "cws-core-phase0-baseline-v1"

MODEL_FORMATS = {
    ".step": "STEP",
    ".stp": "STEP",
    ".ifc": "IFC",
    ".nc": "DSTV",
    ".nc1": "DSTV",
}

DEPENDENCIES = (
    "cadquery",
    "cadquery-ocp",
    "casadi",
    "ifcopenshell",
    "matplotlib",
    "numpy",
    "Pillow",
    "PyMuPDF",
    "pypdf",
    "reportlab",
    "scipy",
    "XlsxWriter",
    "pyinstaller",
)

TRACKED_INPUTS = (
    "requirements.txt",
    "requirements-runtime.lock.txt",
    "requirements-build.txt",
    "requirements-build.lock.txt",
    "SBOM.spdx.json",
)

REQUIRED_FIXTURES = (
    {
        "id": "tekla_ifc",
        "filename": "TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc",
        "purpose": "required semantic IFC regression",
    },
    {
        "id": "step_11864",
        "filename": "Samenstel nieuw - 11864_Predeterminado (1).step",
        "purpose": "required STEP regression",
    },
    {
        "id": "step_11881",
        "filename": "Samenstel nieuw - 11881_Predeterminado (1).step",
        "purpose": "required STEP regression",
    },
    {
        "id": "step_footplate_high",
        "filename": "Samenstel nieuw - 2x voetplaat hoog.step",
        "purpose": "required STEP regression",
    },
    {
        "id": "lo4_pdf",
        "filename": "Pos LO4 - LOSSE PLAAT.pdf",
        "purpose": "required real binary PDF regression",
    },
    {
        "id": "step_d1500",
        "filename": "Samenstel nieuw - D1500-0190_Predeterminado (1).step",
        "purpose": "older required STEP regression",
    },
    {
        "id": "step_part18",
        "filename": "Staalconstructie bordes c04 - Part 18.step",
        "purpose": "older required STEP regression",
    },
    {
        "id": "pdf_review_p1811",
        "filename": "P1811.nc1",
        "purpose": "real PDF review fixture expected by the legacy smoke test",
    },
)

KNOWN_NON_SUBSTITUTES = (
    {
        "for": "lo4_pdf",
        "filename": "14542_01.pdf",
        "reason": "supporting document; not the named LO4 binary",
    },
    {
        "for": "step_part18",
        "filename": "Samenstel nieuw - Part 18.step",
        "reason": "different source name; cannot be substituted silently",
    },
    {
        "for": "pdf_review_p1811",
        "filename": "P1811_3_PLAAT_PL10_130.nc1",
        "reason": "generated regression output; not the original named fixture",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _command_output(arguments: list[str]) -> str:
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        return ""
    return completed.stdout.strip()


def collect_git_state() -> dict:
    status = _command_output(["git", "status", "--porcelain"])
    return {
        "branch": _command_output(["git", "branch", "--show-current"]),
        "head": _command_output(["git", "rev-parse", "HEAD"]),
        "baseline_source": _command_output(
            ["git", "rev-parse", "v0.8-codex-handover"]
        ),
        "clean_at_start": not bool(status),
        "status_entries": len(status.splitlines()) if status else 0,
        "tags": _command_output(["git", "tag", "--list"]).splitlines(),
    }


def collect_product_identity() -> dict:
    from cws_convertor.product import (
        APP_NAME,
        APP_VERSION,
        LEGACY_APP_NAME,
        PROJECT_SCHEMA_VERSION,
    )

    return {
        "name": APP_NAME,
        "compatibility_name": LEGACY_APP_NAME,
        "version": APP_VERSION,
        "project_schema": PROJECT_SCHEMA_VERSION,
    }


def collect_environment() -> dict:
    packages: dict[str, str] = {}
    for package in DEPENDENCIES:
        try:
            packages[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            packages[package] = "not-installed"
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "interpreter": _display_path(Path(sys.executable)),
        "packages": packages,
    }


def collect_tracked_input_hashes() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for relative in TRACKED_INPUTS:
        path = ROOT / relative
        result[relative] = {
            "present": path.is_file(),
            "bytes": path.stat().st_size if path.is_file() else None,
            "sha256": sha256_file(path) if path.is_file() else None,
        }
    return result


def compare_master_prompts(provided: Path, repository: Path) -> dict:
    provided_bytes = provided.read_bytes()
    repository_bytes = repository.read_bytes()
    provided_lines = provided_bytes.decode("utf-8-sig").splitlines()
    repository_lines = repository_bytes.decode("utf-8-sig").splitlines()
    differences = []
    for line_number, (left, right) in enumerate(
        zip_longest(provided_lines, repository_lines, fillvalue=""),
        start=1,
    ):
        if left != right:
            differences.append(
                {
                    "line": line_number,
                    "provided": left,
                    "repository": right,
                }
            )
    return {
        "provided": {
            "name": provided.name,
            "bytes": len(provided_bytes),
            "sha256": hashlib.sha256(provided_bytes).hexdigest(),
        },
        "repository": {
            "path": repository.relative_to(ROOT).as_posix(),
            "bytes": len(repository_bytes),
            "sha256": hashlib.sha256(repository_bytes).hexdigest(),
        },
        "byte_identical": provided_bytes == repository_bytes,
        "text_identical": provided_lines == repository_lines,
        "differing_lines": len(differences),
        "differences": differences[:20],
    }


def verify_handover_zip(path: Path | None) -> dict:
    if path is None:
        return {"status": "not_supplied"}
    if not path.is_file():
        return {"status": "missing", "name": path.name}

    errors: list[str] = []
    verified = 0
    expected = 0
    with zipfile.ZipFile(path) as archive:
        checksum_members = [
            name
            for name in archive.namelist()
            if name.endswith("/SHA256SUMS.txt")
            and name.count("/") == 1
        ]
        if len(checksum_members) != 1:
            errors.append(
                f"Expected one root SHA256SUMS.txt, found {len(checksum_members)}"
            )
        else:
            checksum_member = checksum_members[0]
            prefix = checksum_member[: -len("SHA256SUMS.txt")]
            checksum_text = archive.read(checksum_member).decode("utf-8-sig")
            for line in checksum_text.splitlines():
                if not line.strip():
                    continue
                match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
                if not match:
                    errors.append(f"Invalid checksum line: {line[:120]}")
                    continue
                expected += 1
                expected_hash, relative = match.groups()
                member = prefix + relative.replace("\\", "/")
                try:
                    with archive.open(member) as stream:
                        digest = hashlib.sha256()
                        while chunk := stream.read(1024 * 1024):
                            digest.update(chunk)
                except KeyError:
                    errors.append(f"Missing archive member: {relative}")
                    continue
                if digest.hexdigest().lower() != expected_hash.lower():
                    errors.append(f"Checksum mismatch: {relative}")
                    continue
                verified += 1

    return {
        "status": "passed" if not errors and verified == expected else "failed",
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "manifest_entries": expected,
        "verified_entries": verified,
        "errors": errors[:20],
    }


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _existing_roots(items: Iterable[tuple[Path, bool, str]]) -> list[tuple[Path, bool, str]]:
    return [(path, confidential, label) for path, confidential, label in items if path.is_dir()]


def default_model_roots() -> list[tuple[Path, bool, str]]:
    roots = [
        (ROOT / "reference-models", False, "repository"),
        (ROOT / "reference-models-local", True, "local"),
    ]
    roots.extend(
        (Path(item), True, "external")
        for item in os.environ.get("CWS_REFERENCE_MODEL_ROOTS", "").split(os.pathsep)
        if item
    )
    return _existing_roots(roots)


def default_result_roots() -> list[tuple[Path, bool, str]]:
    roots = [
        (ROOT / "reference-results", False, "repository"),
        (ROOT / "reference-results-local", True, "local"),
    ]
    roots.extend(
        (Path(item), True, "external")
        for item in os.environ.get("CWS_REFERENCE_RESULT_ROOTS", "").split(os.pathsep)
        if item
    )
    return _existing_roots(roots)


def _find_named_file(search_roots: Iterable[Path], filename: str) -> list[Path]:
    expected = filename.casefold()
    matches: list[Path] = []
    seen_roots: set[Path] = set()
    for root in search_roots:
        if not root.is_dir():
            continue
        resolved = root.resolve()
        if resolved in seen_roots:
            continue
        seen_roots.add(resolved)
        matches.extend(
            path for path in root.rglob("*") if path.is_file() and path.name.casefold() == expected
        )
    return matches


def collect_reference_inventory(
    model_roots: list[tuple[Path, bool, str]] | None = None,
    result_roots: list[tuple[Path, bool, str]] | None = None,
    supporting_roots: list[Path] | None = None,
) -> dict:
    model_roots = default_model_roots() if model_roots is None else model_roots
    result_roots = default_result_roots() if result_roots is None else result_roots
    supporting_roots = supporting_roots or [ROOT / "validation", ROOT / "reference-results-local"]

    model_counts: Counter[str] = Counter()
    model_bytes: Counter[str] = Counter()
    confidentiality: Counter[str] = Counter()
    all_model_search_roots: list[Path] = []
    for root, confidential, label in model_roots:
        all_model_search_roots.append(root)
        for path in root.rglob("*"):
            model_format = MODEL_FORMATS.get(path.suffix.lower()) if path.is_file() else None
            if not model_format:
                continue
            model_counts[model_format] += 1
            model_bytes[model_format] += path.stat().st_size
            confidentiality["confidential" if confidential else "repository"] += 1

    result_statuses: Counter[str] = Counter()
    result_locations: Counter[str] = Counter()
    result_errors = 0
    for root, _confidential, label in result_roots:
        for path in root.rglob("*.expected.json"):
            result_locations[label] += 1
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                status = str((value.get("validation") or {}).get("status") or "missing")
                result_statuses[status] += 1
            except (OSError, UnicodeError, json.JSONDecodeError):
                result_errors += 1

    search_roots = all_model_search_roots + [root for root, _, _ in result_roots] + supporting_roots
    fixtures = []
    for fixture in REQUIRED_FIXTURES:
        matches = _find_named_file(search_roots, fixture["filename"])
        fixtures.append(
            {
                **fixture,
                "present": bool(matches),
                "match_count": len(matches),
                "matches": [_display_path(path) for path in matches],
            }
        )

    alternatives = []
    for fixture in KNOWN_NON_SUBSTITUTES:
        matches = _find_named_file(search_roots, fixture["filename"])
        alternatives.append(
            {
                **fixture,
                "present": bool(matches),
                "match_count": len(matches),
                "matches": [_display_path(path) for path in matches],
            }
        )

    cwsc_projects = []
    for root in search_roots:
        if root.is_dir():
            cwsc_projects.extend(path for path in root.rglob("*.cwscproj") if path.is_file())

    return {
        "model_count": sum(model_counts.values()),
        "model_bytes": sum(model_bytes.values()),
        "models_by_format": dict(sorted(model_counts.items())),
        "bytes_by_format": dict(sorted(model_bytes.items())),
        "models_by_confidentiality": dict(sorted(confidentiality.items())),
        "expected_result_count": sum(result_statuses.values()) + result_errors,
        "expected_results_by_status": dict(sorted(result_statuses.items())),
        "expected_results_by_location": dict(sorted(result_locations.items())),
        "invalid_expected_results": result_errors,
        "required_fixtures": fixtures,
        "known_non_substitutes": alternatives,
        "reference_project_count": len(cwsc_projects),
        "legacy_flat_reference_root_set": bool(os.environ.get("CWS_REFERENCE_ROOT")),
    }


def run_process(arguments: list[str], *, label: str) -> dict:
    started = time.perf_counter()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT)
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration = time.perf_counter() - started
    output = "\n".join(
        item.strip() for item in (completed.stdout, completed.stderr) if item.strip()
    )
    test_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
    skipped_match = re.search(r"skipped=(\d+)", output)
    return {
        "label": label,
        "command": [_display_path(Path(arguments[0])), *arguments[1:]],
        "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "duration_seconds": round(duration, 3),
        "unittest_count": int(test_match.group(1)) if test_match else None,
        "skipped": int(skipped_match.group(1)) if skipped_match else 0,
        "output": output,
    }


def run_quality_gates(run_tests: bool = True) -> dict:
    python = sys.executable
    compile_result = run_process(
        [python, "-m", "compileall", "-q", "-x", r"[\\/]\.venv[\\/]", "."],
        label="compileall",
    )
    pip_result = run_process([python, "-m", "pip", "check"], label="pip-check")
    smoke_results = []
    if run_tests:
        for path in sorted((ROOT / "tests").glob("*_smoke.py")):
            smoke_results.append(run_process([python, str(path)], label=path.name))

    failed = sum(
        result["status"] == "failed"
        for result in [compile_result, pip_result, *smoke_results]
    )
    skipped = sum(result["skipped"] for result in smoke_results)
    if failed:
        overall = "failed"
    elif skipped:
        overall = "passed_with_declared_gaps"
    elif not run_tests:
        overall = "checks_only"
    else:
        overall = "passed"
    return {
        "overall": overall,
        "compileall": compile_result,
        "pip_check": pip_result,
        "smoke_scripts_run": len(smoke_results),
        "smoke_scripts_passed": sum(
            result["status"] == "passed" for result in smoke_results
        ),
        "smoke_scripts_failed": sum(
            result["status"] == "failed" for result in smoke_results
        ),
        "known_unittest_count": sum(
            result["unittest_count"] or 0 for result in smoke_results
        ),
        "skipped_tests": skipped,
        "smoke_results": smoke_results,
    }


def build_report(
    *,
    master_prompt: Path,
    handover_zip: Path | None,
    run_tests: bool,
) -> dict:
    repository_prompt = ROOT / "docs" / "CODEX_MASTER_PROMPT_COMPLETE.md"
    report = {
        "schema": REPORT_SCHEMA,
        "phase": 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "core application baseline; viewer implementation excluded",
        "git": collect_git_state(),
        "product": collect_product_identity(),
        "environment": collect_environment(),
        "tracked_inputs": collect_tracked_input_hashes(),
        "master_prompt": compare_master_prompts(master_prompt, repository_prompt),
        "handover": verify_handover_zip(handover_zip),
        "references": collect_reference_inventory(),
    }
    report["quality_gates"] = run_quality_gates(run_tests=run_tests)
    report["baseline_status"] = report["quality_gates"]["overall"]
    return report


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--master-prompt",
        type=Path,
        default=Path(
            os.environ.get(
                "CWS_MASTER_PROMPT",
                ROOT / "docs" / "CODEX_MASTER_PROMPT_COMPLETE.md",
            )
        ),
    )
    parser.add_argument(
        "--handover-zip",
        type=Path,
        default=Path(os.environ["CWS_HANDOVER_ZIP"])
        if os.environ.get("CWS_HANDOVER_ZIP")
        else None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "results" / "core-phase0-baseline-windows.json",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Collect inventory and static checks without running smoke scripts.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        master_prompt=args.master_prompt,
        handover_zip=args.handover_zip,
        run_tests=not args.skip_tests,
    )
    write_json_atomic(args.output, report)
    summary = {
        "status": report["baseline_status"],
        "output": _display_path(args.output),
        "smoke_scripts": report["quality_gates"]["smoke_scripts_run"],
        "skipped_tests": report["quality_gates"]["skipped_tests"],
        "reference_models": report["references"]["model_count"],
        "validated_reference_results": report["references"][
            "expected_results_by_status"
        ].get("validated", 0),
    }
    print(json.dumps(summary, sort_keys=True))
    return 1 if report["baseline_status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
