"""Build all Phase-1 runtime evidence in dependency order from a clean checkout."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PHASES = ROOT / "validation" / "phases"
RESULTS = ROOT / "validation" / "results"
EXACT_RESULT = RESULTS / "viewer-v6-real-11881-exact-source.json"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def run(command: list[str]) -> dict[str, object]:
    started = time.perf_counter()
    completed = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )
    result = {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    print(f"[{'PASS' if result['passed'] else 'FAIL'}] {' '.join(command[1:3])}")
    return result


def external_path(value: str | None, suffixes: set[str]) -> Path | None:
    if not value:
        return None
    candidate = Path(value).expanduser().resolve()
    return candidate if candidate.is_file() and candidate.suffix.lower() in suffixes else None


def find_owner_file(suffixes: set[str], *, name_contains: str = "") -> Path | None:
    root = ROOT / "reference-models-local"
    if not root.is_dir():
        return None
    candidates = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and (not name_contains or name_contains.lower() in path.name.lower())
    ]
    return (
        max(candidates, key=lambda path: (path.stat().st_size, str(path).lower()))
        if candidates
        else None
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--step-source", type=Path)
    parser.add_argument("--large-ifc", type=Path)
    parser.add_argument("--product-count", type=int, default=5000)
    args = parser.parse_args()
    PHASES.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    generated_fixture = PHASES / "fixtures" / "phase1-large-acceptance.ifc"
    step = (
        (args.step_source.expanduser().resolve() if args.step_source else None)
        or external_path(os.environ.get("CWS_PHASE1_STEP_SOURCE"), {".step", ".stp"})
        or find_owner_file({".step", ".stp"}, name_contains="11881")
        or (ROOT / "validation" / "v0.2_generated_step" / "Pr1301.step")
    )
    if not step.is_file():
        raise SystemExit(f"Exact STEP acceptance source ontbreekt: {step}")
    large_ifc = (
        (args.large_ifc.expanduser().resolve() if args.large_ifc else None)
        or external_path(os.environ.get("CWS_PHASE1_LARGE_IFC"), {".ifc"})
        or find_owner_file({".ifc"})
    )
    fixture_class = (
        "owner_real_large_ifc"
        if large_ifc is not None
        else "deterministic_redistributable_large_ifc"
    )
    steps: list[dict[str, object]] = []
    generated_count = 0
    if large_ifc is None:
        generated = run(
            [
                sys.executable,
                str(ROOT / "validation" / "generate_phase1_large_ifc_fixture.py"),
                "--output",
                str(generated_fixture),
                "--product-count",
                str(args.product_count),
            ]
        )
        steps.append({"name": "generate_large_ifc", **generated})
        generated_count = 1
        large_ifc = generated_fixture.resolve()
    commands = (
        (
            "progressive_loading",
            [
                sys.executable,
                str(ROOT / "validation" / "run_phase_b_progressive_loading.py"),
                "--output",
                str(PHASES / "PHASE_1_PROGRESSIVE_PERFORMANCE.json"),
                "--entity-count",
                "5000",
            ],
        ),
        (
            "large_model_performance",
            [
                sys.executable,
                str(ROOT / "validation" / "run_phase1_large_ifc_performance.py"),
                "--input",
                str(large_ifc),
                "--output",
                str(PHASES / "PHASE_1_LARGE_MODEL_PERFORMANCE.json"),
                "--label",
                fixture_class,
            ],
        ),
        (
            "exact_source_result",
            [
                sys.executable,
                str(ROOT / "validation" / "run_phase1_exact_source_result.py"),
                "--input",
                str(step),
                "--output",
                str(EXACT_RESULT),
            ],
        ),
        (
            "source_result_difference",
            [
                sys.executable,
                str(ROOT / "tools" / "build_phase1_real_evidence.py"),
                "--large",
                str(PHASES / "PHASE_1_LARGE_MODEL_PERFORMANCE.json"),
                "--result",
                str(EXACT_RESULT),
                "--source",
                str(step),
                "--output",
                str(PHASES / "PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE.json"),
            ],
        ),
    )
    for name, command in commands:
        outcome = run(command)
        steps.append({"name": name, **outcome})
        if not outcome["passed"]:
            break
    passed = (
        len(steps) == len(commands) + generated_count
        and all(bool(item["passed"]) for item in steps)
    )
    payload = {
        "schema": "cws-phase1-reproducible-evidence-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "fixture_class": fixture_class,
        "large_model": {
            "path": str(large_ifc),
            "bytes": large_ifc.stat().st_size if large_ifc.is_file() else 0,
        },
        "exact_source": {
            "path": str(step),
            "bytes": step.stat().st_size,
            "sha256": digest(step),
        },
        "steps": steps,
    }
    target = PHASES / "PHASE_1_REPRODUCIBLE_EVIDENCE.json"
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"PHASE_1_REPRODUCIBLE_EVIDENCE = {'PASS' if passed else 'FAIL'}")
    print(target)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
