from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION
from runtime_diagnostics import run_native_self_test


SAMPLE_NC1 = """ST
** SAMPLE_PLATE.nc1
  RUNTIME
  SAMPLE_PLATE
  1
  SAMPLE_PLATE
  S235JR
  1
  STRIP10*220
  B
     240.00,240.00
     220.00
      10.00
      10.00
      10.00
       0.00
     80.000
      2.174
      0.000
      0.000
      0.000
      0.000




AK
  v       0.00u      0.00       0.00       0.00       0.00       0.00       0.00
        240.00       0.00       0.00       0.00       0.00       0.00       0.00
        240.00     220.00       0.00       0.00       0.00       0.00       0.00
          0.00     220.00       0.00       0.00       0.00       0.00       0.00
          0.00       0.00       0.00       0.00       0.00       0.00       0.00
BO
  v     120.00s    110.00      22.00
EN
"""


def _clean_runtime_environment() -> dict[str, str]:
    environment = os.environ.copy()
    system_root = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(
        str(path)
        for path in (system_root / "System32", system_root, system_root / "System32" / "Wbem")
    )
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    if shutil.which("python", path=environment["PATH"]) or shutil.which("pip", path=environment["PATH"]):
        raise AssertionError("De opgeschoonde child-PATH bevat nog Python of pip")
    return environment


def _run(
    command: list[str],
    *,
    environment: dict[str, str],
    cwd: Path,
    timeout: int = 180,
    accepted_returncodes: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    accepted = accepted_returncodes or {0}
    if completed.returncode not in accepted:
        raise AssertionError(
            f"Opdracht faalde ({completed.returncode}): {command}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def _read_passed_result(path: Path, required_checks: set[str]) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"Diagnoserapport ontbreekt: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["status"] == "passed", result
    assert result["runtime"]["frozen"] is True, result["runtime"]
    assert result["runtime"]["external_python_on_path"] is None, result["runtime"]
    checks = {check["name"]: check for check in result["checks"]}
    assert required_checks <= checks.keys(), checks.keys()
    assert all(checks[name]["status"] == "passed" for name in required_checks), checks
    return result


def run_packaged_runtime(runtime_dir: Path, label: str, result_dir: Path) -> dict[str, Any]:
    runtime_dir = runtime_dir.resolve()
    result_dir = result_dir.resolve()
    result_dir.mkdir(parents=True, exist_ok=True)
    gui = runtime_dir / "CWS_Convertor.exe"
    cli = runtime_dir / "CWS_Convertor_CLI.exe"
    assert gui.is_file(), f"GUI EXE ontbreekt: {gui}"
    assert cli.is_file(), f"CLI EXE ontbreekt: {cli}"
    environment = _clean_runtime_environment()

    with tempfile.TemporaryDirectory(prefix=f"cws-{label}-") as temporary_name:
        work = Path(temporary_name)
        selftest_path = result_dir / f"{label}-native-selftest.json"
        gui_path = result_dir / f"{label}-gui-smoke.json"
        _run([str(gui), "--self-test", "--output", str(selftest_path)], environment=environment, cwd=work)
        native_result = _read_passed_result(
            selftest_path,
            {
                "casadi",
                "cadquery_ocp",
                "ifcopenshell",
                "pymupdf",
                "scientific_rendering",
                "project_roundtrips",
            },
        )
        _run([str(gui), "--gui-smoke", "--output", str(gui_path)], environment=environment, cwd=work)
        gui_result = _read_passed_result(gui_path, {"casadi", "cadquery_ocp", "gui"})

        version = _run([str(cli), "--version"], environment=environment, cwd=work)
        assert f"{APP_NAME} {APP_VERSION}" in version.stdout, version.stdout

        project = work / "runtime-smoke.cwscproj"
        _run([str(cli), "project-new", str(project), "--name", f"{label} runtime smoke"], environment=environment, cwd=work)
        assert project.is_file() and project.stat().st_size > 0
        _run([str(cli), "project-info", str(project)], environment=environment, cwd=work)

        nc1 = work / "SAMPLE_PLATE.nc1"
        nc1.write_text(SAMPLE_NC1, encoding="ascii", newline="\r\n")
        conversion_dir = work / "conversion"
        conversion_dir.mkdir()
        _run([str(cli), "nc1-to-step", str(nc1), "-o", str(conversion_dir)], environment=environment, cwd=work)
        step = conversion_dir / "SAMPLE_PLATE.step"
        assert step.is_file() and step.stat().st_size > 1_000, f"STEP-uitvoer ontbreekt of is leeg: {step}"

        _run([str(cli), "dstv-to-ifc", str(nc1), "-o", str(conversion_dir)], environment=environment, cwd=work)
        ifc_files = sorted(conversion_dir.glob("*.ifc"))
        assert len(ifc_files) == 1, f"Verwacht precies één IFC-uitvoer, gevonden: {ifc_files}"
        ifc = ifc_files[0]
        import_report = work / "semantic-import.json"
        _run(
            [
                str(cli),
                "project-import",
                str(project),
                str(ifc),
                "--json-report",
                str(import_report),
            ],
            environment=environment,
            cwd=work,
            accepted_returncodes={0, 3},
        )
        imported = json.loads(import_report.read_text(encoding="utf-8"))
        assert imported["status"] == "review_required", imported
        assert imported["project"]["entity_counts"]["part"] >= 1, imported["project"]

        parts_report = work / "parts.json"
        _run(
            [
                str(cli),
                "project-list-parts",
                str(project),
                "--limit",
                "1",
                "--json-report",
                str(parts_report),
            ],
            environment=environment,
            cwd=work,
        )
        parts = json.loads(parts_report.read_text(encoding="utf-8"))
        assert parts["returned"] == 1, parts
        part_id = parts["parts"][0]["part_id"]
        inspection_report = work / "source-geometry.json"
        _run(
            [
                str(cli),
                "project-inspect-source-geometry",
                str(project),
                part_id,
                "--json-report",
                str(inspection_report),
            ],
            environment=environment,
            cwd=work,
            timeout=240,
        )
        inspected = json.loads(inspection_report.read_text(encoding="utf-8"))
        inspection = inspected["inspection"]
        assert inspected["status"] == "passed", inspected
        assert inspection["status"] == "resolved_mesh", inspection
        assert inspection["scope"] == "part", inspection
        assert inspection["geometry_kind"] == "triangulated_mesh", inspection
        assert inspection["selection_verified"] is True, inspection
        assert inspection["production_geometry_exact"] is False, inspection
        assert inspection["metrics"]["volume_mm3"] > 0.0, inspection
        _run([str(cli), "project-verify", str(project)], environment=environment, cwd=work)

        summary = {
            "application_version": APP_VERSION,
            "label": label,
            "status": "passed",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_directory": str(runtime_dir),
            "python_on_child_path": False,
            "native_checks": {check["name"]: check["status"] for check in native_result["checks"]},
            "gui_checks": {check["name"]: check["status"] for check in gui_result["checks"]},
            "cli_version": version.stdout.strip(),
            "project_smoke": "passed",
            "nc1_to_step_smoke": {"status": "passed", "step_bytes": step.stat().st_size},
            "ifc_source_geometry_smoke": {
                "status": "passed",
                "geometry_kind": inspection["geometry_kind"],
                "selection_verified": inspection["selection_verified"],
                "production_geometry_exact": inspection["production_geometry_exact"],
            },
        }
    summary_path = result_dir / f"{label}-packaged-runtime.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CWS packaged Windows-runtime regression")
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--label", default="dist")
    parser.add_argument("--result-dir", type=Path, default=ROOT / "validation" / "results" / "windows-runtime")
    arguments = parser.parse_args(argv)
    if arguments.runtime_dir is None:
        result = run_native_self_test()
        assert result["status"] == "passed", result
        print("packaged_runtime_smoke: source fallback OK")
        return 0
    summary = run_packaged_runtime(arguments.runtime_dir, arguments.label, arguments.result_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
