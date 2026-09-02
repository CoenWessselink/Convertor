from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION, CANONICAL_PART_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION

OUTPUT = ROOT / "validation" / "full_acceptance"


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def classification(path: str) -> tuple[str, str, bool, bool, str]:
    normalized = path.replace("\\", "/")
    generated_roots = (
        "validation/results/phase3/",
        "validation/results/windows-runtime-phase2/",
        "validation/results/windows-runtime-phase3/",
        "validation/viewer_repair_diagnostic/",
    )
    acceptance_sources = {
        "validation/full_acceptance/PRE_RELEASE_WORKTREE_AUDIT.json",
        "validation/full_acceptance/PRE_RELEASE_WORKTREE_AUDIT.md",
        "validation/full_acceptance/UNCOMMITTED_ACCEPTANCE_ROOT_CAUSE.json",
        "validation/full_acceptance/UNCOMMITTED_ACCEPTANCE_ROOT_CAUSE.md",
    }
    if normalized in acceptance_sources:
        return "COMMIT_REQUIRED", "Release-audit is reproduceerbare bron-evidence", True, False, "docs"
    if normalized.startswith("validation/full_acceptance/") or normalized.startswith(generated_roots):
        kind = "screenshot" if normalized.lower().endswith((".png", ".jpg", ".jpeg")) else "artifact"
        return "GENERATED_ARTIFACT_DO_NOT_COMMIT", "Door acceptance-runner reproduceerbare evidence", False, True, kind
    if normalized in {"CWS_Convertor_Phase3.exe", "CWS_Convertor_Setup_0.10.18-beta-dev_x64.exe"}:
        return "GENERATED_ARTIFACT_DO_NOT_COMMIT", "Niet-commitgebonden lokaal buildproduct", False, True, "artifact"
    if normalized.endswith((".log", ".tmp")) or "__pycache__" in normalized:
        return "TEMPORARY_DELETE", "Tijdelijke runtime-output", False, True, "artifact"
    if normalized.startswith(("cws_convertor/", "cws_viewer/")):
        return "COMMIT_REQUIRED", "Productbron of gebundelde runtime-authority", True, False, "source"
    if normalized.startswith("tests/"):
        return "COMMIT_REQUIRED", "Regression- of acceptancetest", True, False, "test"
    if normalized.startswith(("tools/", "validation/")) and normalized.endswith(".py"):
        return "COMMIT_REQUIRED", "Reproduceerbare acceptance/buildworkflow", True, False, "workflow"
    if normalized.startswith(".github/"):
        return "COMMIT_REQUIRED", "Required CI op exacte release-SHA", True, False, "workflow"
    if normalized.startswith(("docs/", "installer/")):
        return "COMMIT_REQUIRED", "Release-, gebruikers- of packagingdocumentatie", True, False, "docs"
    if normalized in {".gitignore", "CWS_Convertor.spec", "build_windows_exe.bat", "converter.py", "runtime_diagnostics.py", "requirements-runtime.lock.txt"}:
        return "COMMIT_REQUIRED", "Reproduceerbare product/buildconfiguratie", True, False, "workflow"
    return "REVIEW_REQUIRED", "Niet automatisch geclassificeerd", False, False, "artifact"


def porcelain_records() -> list[dict[str, Any]]:
    output = git("status", "--porcelain=v1", "--untracked-files=all")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:].split(" -> ")[-1]
        category, reason, needed, generated, kind = classification(path)
        records.append({
            "path": path.replace("\\", "/"), "status": status,
            "classification": category, "reason": reason,
            "needed_for_reproducibility": needed, "generated": generated, "kind": kind,
        })
        seen.add(path.replace("\\", "/"))
    generated_candidates = [
        *(ROOT.glob("*.exe")),
        *(ROOT / "validation" / "full_acceptance").rglob("*"),
        *(ROOT / "validation" / "results" / "phase3").rglob("*"),
        *(ROOT / "validation" / "results" / "windows-runtime-phase2").rglob("*"),
        *(ROOT / "validation" / "results" / "windows-runtime-phase3").rglob("*"),
        *(ROOT / "validation" / "viewer_repair_diagnostic").rglob("*"),
    ]
    for candidate in generated_candidates:
        if not candidate.is_file():
            continue
        path = candidate.relative_to(ROOT).as_posix()
        if path in seen:
            continue
        category, reason, needed, generated, kind = classification(path)
        records.append({
            "path": path, "status": "!!", "classification": category, "reason": reason,
            "needed_for_reproducibility": needed, "generated": generated, "kind": kind,
        })
    return sorted(records, key=lambda item: item["path"])


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    branch = git("branch", "--show-current")
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    remote = git("rev-parse", "origin/agent/cws-product-ui-reintegration-v1")
    behind, ahead = (int(value) for value in git("rev-list", "--left-right", "--count", f"{remote}...{head}").split())
    records = porcelain_records()
    generated = [item["path"] for item in records if item["generated"]]
    required = [item["path"] for item in records if item["classification"] == "COMMIT_REQUIRED"]
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "schema": "cws-pre-release-worktree-audit-1.0", "generated_at": timestamp,
        "branch": branch, "head": head, "parent": parent, "remote_head": remote,
        "ahead": ahead, "behind": behind, "working_tree_clean": not bool(records),
        "version": APP_VERSION, "project_model": PROJECT_SCHEMA_VERSION,
        "canonical_part": CANONICAL_PART_SCHEMA_VERSION, "files": records,
    }
    (OUTPUT / "PRE_RELEASE_WORKTREE_AUDIT.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Pre-release worktree audit", "", f"Branch: `{branch}`", f"HEAD: `{head}`",
        f"Parent: `{parent}`", f"Ahead/behind: `{ahead}/{behind}`", "",
        "| Path | Status | Classificatie | Reden |", "| --- | --- | --- | --- |",
    ]
    lines.extend(f"| `{item['path']}` | `{item['status']}` | `{item['classification']}` | {item['reason']} |" for item in records)
    (OUTPUT / "PRE_RELEASE_WORKTREE_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    root_cause = {
        "schema": "cws-uncommitted-acceptance-root-cause-1.0", "generated_at": timestamp,
        "base_commit": head, "branch": branch, "dirty_files": [item["path"] for item in records if item["status"] != "!!"],
        "required_changes": required, "generated_files": generated,
        "artifact_naming_logic": {
            "phase3_previous": "tools/build_phase3_windows_release.py used REVISION_TAG='uncommitted'",
            "phase3_validation_previous": "tools/build_phase3_validation.py expected an _uncommitted source package",
            "phase1_previous": "tools/build_phase1_windows_release.py fell back to uncommitted without GITHUB_SHA",
            "installer_previous": "installer/CWS_Convertor.iss omitted commit7",
        },
        "root_cause": "Acceptance ran in a dirty development worktree while packaging had explicit uncommitted fallbacks and no clean-tree/exact-SHA release boundary.",
        "corrective_action": "Commit required source, fail closed on unknown SHA or dirty tree, rebuild from a fresh exact-SHA checkout, rerun every dynamic master requirement and bind every final artifact and checksum to commit7.",
    }
    (OUTPUT / "UNCOMMITTED_ACCEPTANCE_ROOT_CAUSE.json").write_text(json.dumps(root_cause, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT / "UNCOMMITTED_ACCEPTANCE_ROOT_CAUSE.md").write_text(
        "# Uncommitted acceptance root cause\n\n"
        f"Base commit: `{head}`\n\n"
        "De 51/51-run gebruikte noodzakelijke lokale bronwijzigingen, maar de packaginglaag bevatte expliciete "
        "`uncommitted`-fallbacks en geen harde clean-tree/exact-SHA grens. Daardoor was functionele acceptance groen, "
        "maar het artifact niet cryptografisch aan dezelfde gepushte broncommit gebonden.\n\n"
        "Correctie: commit en push uitsluitend reproduceerbare bron, bouw vanuit een fresh exact-SHA checkout, "
        "herhaal alle source/packaged/portable/installer-gates en genereer daarna commitgebonden hashes en manifests.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "files": len(records), "commit_required": len(required), "generated": len(generated)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
