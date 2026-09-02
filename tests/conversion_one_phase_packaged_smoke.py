from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


SAMPLE_NC1 = """ST
** MATRIX_PLATE.nc1
  MATRIX
  MATRIX_PLATE
  1
  MATRIX_PLATE
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

FORMATS = ("NC1", "STEP", "IFC", "PDF")
EXTENSIONS = {"NC1": ".nc1", "STEP": ".step", "IFC": ".ifc", "PDF": ".pdf"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_archived_evidence(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    claimed = str(payload.pop("manifest_sha256", ""))
    actual = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    assert claimed == actual, {"manifest": str(path), "claimed": claimed, "actual": actual}
    for artifact in payload["artifacts"]:
        candidate = path.parent / artifact["relative_path"]
        assert candidate.is_file(), candidate
        assert _sha256(candidate) == artifact["sha256"], artifact


def _clean_environment() -> dict[str, str]:
    environment = os.environ.copy()
    system_root = Path(environment.get("SystemRoot", r"C:\Windows"))
    environment["PATH"] = os.pathsep.join(
        str(path)
        for path in (system_root / "System32", system_root, system_root / "System32" / "Wbem")
    )
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    if shutil.which("python", path=environment["PATH"]) or shutil.which("pip", path=environment["PATH"]):
        raise AssertionError("Packaged matrix child unexpectedly sees Python or pip")
    return environment


def _convert(
    executable: Path,
    source: Path,
    source_format: str,
    target_format: str,
    root: Path,
    environment: dict[str, str],
) -> tuple[Path, dict[str, Any]]:
    direction = f"{source_format.lower()}-{target_format.lower()}"
    route_root = root / direction
    output = route_root / "output"
    output.mkdir(parents=True, exist_ok=True)
    job = route_root / "job.json"
    result_path = route_root / "result.json"
    progress_path = route_root / "progress.json"
    job.write_text(
        json.dumps(
            {
                "sources": [str(source)],
                "output": str(output),
                "direction": direction,
                "material": "S235JR",
                "progress_path": str(progress_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(executable), "--conversion-worker", str(job), "--conversion-result", str(result_path)],
        cwd=route_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=420,
        check=False,
    )
    if completed.returncode != 0 or not result_path.is_file():
        raise AssertionError(
            f"{direction} worker failed ({completed.returncode})\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    envelope = json.loads(result_path.read_text(encoding="utf-8"))
    assert envelope["status"] == "passed", envelope
    batch = envelope["result"]
    assert batch["status"] == "passed", batch
    assert batch["preflight_complete_before_execution"] is True, batch
    assert batch["item_failure_isolation"] is True, batch
    assert len(batch["results"]) == 1, batch
    item = batch["results"][0]
    assert item["status"] == "passed", item
    assert item["plan"]["status"] in {"SUPPORTED", "SUPPORTED_WITH_LIMITS"}, item["plan"]
    assert item["plan"]["route"]["direction"] == direction, item["plan"]
    assert all(proof.get("status") == "PASS" for proof in item["proofs"].values()), item["proofs"]
    evidence = Path(item["evidence_path"])
    assert evidence.is_file() and evidence.stat().st_size > 0, evidence
    candidates = [
        Path(value)
        for value in item["outputs"]
        if Path(value).suffix.lower() == EXTENSIONS[target_format]
    ]
    assert candidates, item["outputs"]
    artifact = candidates[0]
    assert artifact.is_file() and artifact.stat().st_size > 0, artifact
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    assert progress["percent"] == 100, progress
    return artifact, {
        "direction": direction,
        "status": "PASS",
        "planner_status": item["plan"]["status"],
        "artifact": str(artifact),
        "artifact_sha256": _sha256(artifact),
        "evidence": str(evidence),
        "evidence_sha256": _sha256(evidence),
        "proofs": {name: proof["status"] for name, proof in item["proofs"].items()},
    }


def _expect_refusal(
    executable: Path,
    source: Path,
    direction: str,
    expected_plan_status: str,
    root: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    route_root = root / f"negative-{direction}-{source.stem}"
    route_root.mkdir(parents=True, exist_ok=True)
    output = route_root / "output"
    job = route_root / "job.json"
    result_path = route_root / "result.json"
    job.write_text(
        json.dumps(
            {
                "sources": [str(source)],
                "output": str(output),
                "direction": direction,
                "material": "S235JR",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(executable), "--conversion-worker", str(job), "--conversion-result", str(result_path)],
        cwd=route_root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0 and result_path.is_file(), completed
    envelope = json.loads(result_path.read_text(encoding="utf-8"))
    assert envelope["status"] == "passed", envelope
    batch = envelope["result"]
    assert batch["status"] == "completed_with_failures", batch
    item = batch["results"][0]
    assert item["plan"]["status"] == expected_plan_status, item
    assert item["status"] in {"blocked", "review_required"}, item
    assert item["failures"] and not item["outputs"], item
    return {
        "direction": direction,
        "status": "PASS",
        "planner_status": expected_plan_status,
        "execution_status": item["status"],
        "reasons": item["failures"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact-SHA packaged 12-route conversion matrix")
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    arguments = parser.parse_args()
    runtime = arguments.runtime_dir.resolve()
    executable = runtime / "CWS_Convertor.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    checkout_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
    ).strip()
    if checkout_sha != arguments.expected_sha:
        raise AssertionError(f"Exact-SHA mismatch: {checkout_sha} != {arguments.expected_sha}")

    report_path = arguments.output.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    environment = _clean_environment()
    with tempfile.TemporaryDirectory(prefix="cws-packaged-conversion-matrix-") as folder:
        root = Path(folder)
        nc1 = root / "MATRIX_PLATE.nc1"
        nc1.write_text(SAMPLE_NC1, encoding="ascii", newline="\r\n")
        sources: dict[str, Path] = {"NC1": nc1}
        rows: list[dict[str, Any]] = []

        for target in ("STEP", "IFC", "PDF"):
            artifact, row = _convert(
                executable, sources["NC1"], "NC1", target, root, environment
            )
            sources[target] = artifact
            rows.append(row)

        for source_format in ("STEP", "IFC", "PDF"):
            for target_format in FORMATS:
                if target_format == source_format:
                    continue
                _artifact, row = _convert(
                    executable,
                    sources[source_format],
                    source_format,
                    target_format,
                    root,
                    environment,
                )
                rows.append(row)

        from pypdf import PdfReader, PdfWriter

        external_pdf = root / "EXTERNAL_DRAWING.pdf"
        reader = PdfReader(str(sources["PDF"]))
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with external_pdf.open("wb") as stream:
            writer.write(stream)
        external_review = _expect_refusal(
            executable,
            external_pdf,
            "pdf-step",
            "REVIEW",
            root,
            environment,
        )

        unsafe_nc1 = root / "UNSUPPORTED_SC.nc1"
        unsafe_nc1.write_text(
            SAMPLE_NC1.replace("EN\n", "SC\n  unsupported machining instruction\nEN\n"),
            encoding="ascii",
            newline="\r\n",
        )
        unsupported_block = _expect_refusal(
            executable,
            unsafe_nc1,
            "nc1-step",
            "BLOCKED",
            root,
            environment,
        )

        expected = {
            f"{source.lower()}-{target.lower()}"
            for source in FORMATS
            for target in FORMATS
            if source != target
        }
        found = {row["direction"] for row in rows}
        assert len(rows) == 12 and found == expected, {"expected": sorted(expected), "found": sorted(found)}
        archive = report_path.parent / "conversion_packaged_matrix_evidence"
        if archive.exists():
            shutil.rmtree(archive)
        shutil.copytree(root, archive)
        for row in rows:
            artifact_relative = Path(str(row["artifact"])).relative_to(root)
            evidence_relative = Path(str(row["evidence"])).relative_to(root)
            row["artifact"] = str((archive / artifact_relative).resolve())
            row["artifact_relative_path"] = artifact_relative.as_posix()
            row["evidence"] = str((archive / evidence_relative).resolve())
            row["evidence_relative_path"] = evidence_relative.as_posix()
            _verify_archived_evidence(Path(row["evidence"]))
            row["archived_evidence_reopen"] = "PASS"
        report = {
            "schema": "cws.conversion.packaged-matrix.v1",
            "status": "PASS",
            "checkout_sha": checkout_sha,
            "executable": str(executable),
            "executable_sha256": _sha256(executable),
            "python_on_child_path": False,
            "route_count": len(rows),
            "evidence_archive": str(archive.resolve()),
            "routes": rows,
            "negative_gates": {
                "external_pdf_requires_review": external_review,
                "unsupported_nc1_feature_is_blocked": unsupported_block,
            },
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"status": "PASS", "report": str(report_path), "routes": 12}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
