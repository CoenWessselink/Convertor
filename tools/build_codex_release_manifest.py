"""Validate and bind the complete Codex Windows release handover.

This command is intentionally the final step of both ``build_windows_exe.bat``
and the GitHub Windows workflow.  It does not build or repair missing evidence:
every required source, BOM, packaged, portable, installed and uninstall gate
must already have produced a durable PASS result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION
from tools.capture_bom_production_hub import BOM_CAPTURE_FILENAMES


PASS_VALUES = {"PASS", "PASSED", "GREEN", "COMPLETE", "SUCCESS"}


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=ROOT, text=True, encoding="utf-8"
    ).strip()


def tracked_change_paths() -> list[str]:
    """Return tracked porcelain paths without stripping the first status column."""

    porcelain = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )
    return [
        line[3:].split(" -> ")[-1]
        for line in porcelain.splitlines()
        if len(line) >= 4
    ]


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON object vereist: {path}")
    return payload


def passed(payload: dict[str, Any]) -> bool:
    return str(payload.get("status", "")).upper() in PASS_VALUES


def require_pass(path: Path, label: str) -> dict[str, Any]:
    payload = load(path)
    if not passed(payload):
        raise RuntimeError(f"{label} is niet PASS: {path}")
    return payload


def release_file(release: Path, predicate: Any, label: str) -> Path:
    matches = sorted(path for path in release.iterdir() if path.is_file() and predicate(path))
    if len(matches) != 1:
        raise RuntimeError(f"Exact één {label} vereist; gevonden: {[path.name for path in matches]}")
    return matches[0]


def allowed_generated_change(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith("validation/") or normalized in {
        "requirements/ACTIVE_REQUIREMENTS.json",
        "requirements/MASTER_REQUIREMENT_TRACEABILITY.json",
        "requirements/MASTER_REQUIREMENT_TRACEABILITY.md",
        "requirements/SUPERSEDED_REQUIREMENTS.json",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind complete Codex release evidence")
    parser.add_argument("--release-dir", type=Path, default=ROOT / "release")
    parser.add_argument(
        "--runtime-results",
        type=Path,
        default=ROOT / "validation" / "results" / "windows-runtime",
    )
    args = parser.parse_args()
    release = args.release_dir.expanduser().resolve()
    runtime_results = args.runtime_results.expanduser().resolve()
    release.mkdir(parents=True, exist_ok=True)

    commit = git("rev-parse", "HEAD").lower()
    tree = git("rev-parse", "HEAD^{tree}").lower()
    branch = git("branch", "--show-current") or str(
        __import__("os").environ.get("GITHUB_REF_NAME") or "DETACHED"
    )
    commit7 = commit[:7]
    if len(commit) != 40 or len(tree) != 40:
        raise RuntimeError("Exacte Git commit en tree zijn vereist")

    tracked_changes = tracked_change_paths()
    disallowed = [path for path in tracked_changes if not allowed_generated_change(path)]
    if disallowed:
        raise RuntimeError(f"Productbron wijzigde tijdens acceptance: {disallowed}")

    phases = ROOT / "validation" / "phases"
    phase1_repro = require_pass(
        phases / "PHASE_1_REPRODUCIBLE_EVIDENCE.json", "Phase 1 large-IFC"
    )
    phase1 = require_pass(phases / "PHASE_1_SOURCE_TEST_EVIDENCE.json", "Phase 1")
    phase2 = require_pass(phases / "PHASE_2_SOURCE_TEST_EVIDENCE.json", "Phase 2")
    phase3 = require_pass(phases / "PHASE_3_SOURCE_TEST_EVIDENCE.json", "Phase 3")
    soak = require_pass(phases / "PHASE_3_SOAK_EVIDENCE.json", "10-minutensoak")
    soak_seconds = float(soak.get("elapsed_seconds", 0.0))
    if soak_seconds < 600.0 or float(soak.get("requested_duration_seconds", 0.0)) < 600.0:
        raise RuntimeError(f"Soak is te kort: {soak_seconds} seconden")

    runtime_evidence: dict[str, dict[str, Any]] = {}
    for label in ("dist", "portable", "installed"):
        payload = require_pass(
            runtime_results / f"{label}-packaged-runtime.json",
            f"{label} packaged runtime",
        )
        if payload.get("python_on_child_path") is not False:
            raise RuntimeError(f"{label} runtime zag externe Python op child-PATH")
        if str(payload.get("application_version")) != APP_VERSION:
            raise RuntimeError(f"{label} runtimeversie wijkt af van {APP_VERSION}")
        runtime_evidence[label] = payload
    source_native = require_pass(
        runtime_results / "source-native-selftest.json", "source native selftest"
    )
    source_gui = require_pass(runtime_results / "source-gui-smoke.json", "source GUI-smoke")
    installed_associations = require_pass(
        runtime_results / "installed-associations.json", "geïnstalleerde associaties"
    )
    uninstall_associations = require_pass(
        runtime_results / "uninstall-associations.json", "uninstall-associaties"
    )

    bom_manifest_path = release / "BOM_EVIDENCE" / "BOM_RUNTIME_CAPTURE_MANIFEST.json"
    bom = load(bom_manifest_path)
    captured_files = tuple(str(item.get("file") or "") for item in bom.get("captures", ()))
    if bom.get("source_sha") != commit or captured_files != BOM_CAPTURE_FILENAMES:
        raise RuntimeError(
            "BOM runtimecapture is niet exact aan commit en de acht vereiste beelden gebonden"
        )
    if not bom.get("capture_font_glyphs_verified") or not bom.get("capture_font_family"):
        raise RuntimeError("BOM runtimecapture bevat geen bewezen leesbaar lettertype")
    for capture in bom["captures"]:
        image = bom_manifest_path.parent / str(capture["file"])
        if not image.is_file() or digest(image) != str(capture["sha256"]):
            raise RuntimeError(f"BOM capture ongeldig: {image}")

    installer = release_file(
        release,
        lambda path: path.name == f"CWS_Convertor_Setup_{APP_VERSION}_{commit7}_x64.exe",
        "exact-SHA installer",
    )
    portable = release_file(
        release,
        lambda path: path.suffix.casefold() == ".zip"
        and "portable" in path.name.casefold()
        and APP_VERSION in path.name
        and commit7 in path.name,
        "exact-SHA portable ZIP",
    )
    source_zip = release_file(
        release,
        lambda path: path.name == f"CWS_Convertor_Source_{APP_VERSION}_{commit7}.zip",
        "source ZIP",
    )
    bundle = release_file(
        release,
        lambda path: path.name == f"CWS_Convertor_{APP_VERSION}_{commit7}.bundle",
        "Git bundle",
    )
    sbom = release_file(
        release,
        lambda path: path.name == f"CWS_Convertor_SBOM_{APP_VERSION}_{commit7}.cdx.json",
        "SBOM",
    )
    sbom_payload = load(sbom)
    if sbom_payload.get("bomFormat") != "CycloneDX" or (
        sbom_payload.get("metadata", {}).get("component", {}).get("version") != APP_VERSION
    ):
        raise RuntimeError("SBOM is niet aan de actuele productversie gebonden")

    core_artifacts = [installer, portable, source_zip, bundle, sbom]
    artifact_records = [
        {
            "name": path.name,
            "relative_path": path.relative_to(release).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        }
        for path in core_artifacts
    ]
    manifest = {
        "schema": "cws-codex-complete-windows-release-1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "product": APP_NAME,
        "version": APP_VERSION,
        "branch": branch,
        "commit": commit,
        "tree": tree,
        "source_tree_unchanged": not disallowed,
        "generated_evidence_changes": tracked_changes,
        "source_gates": {
            "phase1_large_ifc": phase1_repro["status"],
            "phase1": phase1["status"],
            "phase2": phase2["status"],
            "phase3": phase3["status"],
            "soak_seconds": soak_seconds,
        },
        "runtime_matrix": {
            "source_native": source_native["status"],
            "source_gui": source_gui["status"],
            "one_folder": runtime_evidence["dist"]["status"],
            "fresh_portable": runtime_evidence["portable"]["status"],
            "installed_no_external_python": runtime_evidence["installed"]["status"],
            "installed_file_associations": installed_associations["status"],
            "uninstall_association_cleanup": uninstall_associations["status"],
        },
        "bom_evidence": {
            "manifest": bom_manifest_path.relative_to(release).as_posix(),
            "snapshot_sha256": bom.get("bom_snapshot_sha256"),
            "capture_count": len(bom["captures"]),
            "production_ready": bom.get("validation", {}).get("production_ready"),
        },
        "artifacts": artifact_records,
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer.allowed": False,
        },
    }
    manifest_path = release / "CODEX_RELEASE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    checksum_files = sorted(
        path
        for path in release.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    )
    checksum_path = release / "SHA256SUMS.txt"
    checksum_path.write_text(
        "".join(
            f"{digest(path)}  {path.relative_to(release).as_posix()}\n"
            for path in checksum_files
        ),
        encoding="ascii",
    )
    for line in checksum_path.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        if digest(release / relative) != expected:
            raise RuntimeError(f"Checksumverificatie faalde: {relative}")

    print(
        json.dumps(
            {
                "status": "PASS",
                "commit": commit,
                "version": APP_VERSION,
                "artifacts": len(artifact_records),
                "checksummed_files": len(checksum_files),
                "manifest": str(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
