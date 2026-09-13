"""Capture read-only Phase-1 repository and GitHub Actions evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "phases" / "PHASE_1_REPOSITORY_CI_EVIDENCE.json"
REPOSITORY = "CoenWessselink/Convertor"
CANONICAL_BRANCH = "agent/cws-product-ui-reintegration-v1"
CANONICAL_WORKFLOW = "CWS Convertor Phase 1 Canonical Product Core"


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout.strip()


def github_json(url: str) -> dict:
    request = Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "CWS-Convertor-Phase1-Audit"},
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def github_event() -> dict[str, Any]:
    path = str(os.environ.get("GITHUB_EVENT_PATH") or "").strip()
    if not path:
        return {}
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha(value: Any) -> str:
    text = str(value or "").strip()
    return text if len(text) == 40 else ""


def main() -> int:
    event = github_event()
    pull_request = event.get("pull_request") if isinstance(event.get("pull_request"), dict) else {}
    event_name = str(os.environ.get("GITHUB_EVENT_NAME") or "").strip()
    is_pull_request = event_name == "pull_request" and bool(pull_request)

    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    branch = git("branch", "--show-current")

    pull_request_head_ref = ""
    pull_request_head_sha = ""
    pull_request_base_ref = ""
    pull_request_base_sha = ""
    merge_base_parent = ""
    merge_head_parent = ""
    pull_request_merge_lineage_verified = False
    tracking_ref_available = False

    if is_pull_request:
        pr_head = pull_request.get("head") if isinstance(pull_request.get("head"), dict) else {}
        pr_base = pull_request.get("base") if isinstance(pull_request.get("base"), dict) else {}
        pull_request_head_ref = str(os.environ.get("GITHUB_HEAD_REF") or pr_head.get("ref") or "").strip()
        pull_request_head_sha = _sha(pr_head.get("sha"))
        pull_request_base_ref = str(os.environ.get("GITHUB_BASE_REF") or pr_base.get("ref") or "").strip()
        pull_request_base_sha = _sha(pr_base.get("sha"))
        branch = pull_request_head_ref or branch
        tracking = f"origin/{pull_request_head_ref}" if pull_request_head_ref else ""
        tracking_head = pull_request_head_sha
        ahead = None
        behind = None
        try:
            merge_base_parent = git("rev-parse", "HEAD^1")
            merge_head_parent = git("rev-parse", "HEAD^2")
        except RuntimeError:
            merge_base_parent = ""
            merge_head_parent = ""
        pull_request_merge_lineage_verified = bool(
            pull_request_head_ref
            and pull_request_base_ref
            and pull_request_head_sha
            and pull_request_base_sha
            and merge_base_parent == pull_request_base_sha
            and merge_head_parent == pull_request_head_sha
        )
        branch_head_recorded = pull_request_merge_lineage_verified
        head_matches_tracking = False
    else:
        branch = branch or CANONICAL_BRANCH
        tracking = f"origin/{CANONICAL_BRANCH}"
        tracking_head = git("rev-parse", tracking)
        tracking_ref_available = True
        ahead_text = git("rev-list", "--left-right", "--count", f"HEAD...{tracking}")
        ahead, behind = (int(value) for value in ahead_text.split())
        head_matches_tracking = ahead == 0 and behind == 0 and tracking_head == head
        branch_head_recorded = bool(
            branch == CANONICAL_BRANCH
            and len(head) == 40
            and len(parent) == 40
            and tracking_head == head
        )

    status_lines = tuple(
        line
        for line in git("status", "--short", "--untracked-files=no").splitlines()
        if line
    )
    ci_execution_exact_sha = bool(
        os.environ.get("GITHUB_ACTIONS", "").casefold() == "true"
        and str(os.environ.get("GITHUB_SHA") or "").casefold() == head.casefold()
    )
    runs: list[dict[str, Any]] = []
    repository_api_error = ""
    if not ci_execution_exact_sha:
        try:
            runs_payload = github_json(
                f"https://api.github.com/repos/{REPOSITORY}/actions/runs?branch={quote(branch, safe='')}&per_page=20"
            )
            runs = list(runs_payload.get("workflow_runs") or [])
        except Exception as exc:
            # Local audits remain fail-closed if GitHub cannot be queried. An
            # exact-SHA Actions execution does not need the external lookup.
            repository_api_error = f"{type(exc).__name__}: {exc}"
    exact_runs = [run for run in runs if str(run.get("head_sha")) == head]
    canonical_exact_runs = [
        run for run in exact_runs if str(run.get("name") or "") == CANONICAL_WORKFLOW
    ]
    latest = canonical_exact_runs[0] if canonical_exact_runs else (
        exact_runs[0] if exact_runs else (runs[0] if runs else {})
    )
    jobs: list[dict] = []
    if latest.get("jobs_url"):
        try:
            jobs = list(github_json(str(latest["jobs_url"])).get("jobs") or [])
        except Exception as exc:
            repository_api_error = f"{type(exc).__name__}: {exc}"
    workflow_path = ROOT / ".github" / "workflows" / "build-product-ui-reintegration-exe.yml"
    committed_workflow = git("show", f"{head}:.github/workflows/build-product-ui-reintegration-exe.yml")
    payload = {
        "schema": "cws-phase1-repository-ci-evidence-1.1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository": REPOSITORY,
        "branch": branch,
        "head": head,
        "parent": parent,
        "tracking": tracking,
        "tracking_head": tracking_head,
        "tracking_ref_available": tracking_ref_available,
        "ahead": ahead,
        "behind": behind,
        "head_matches_tracking": head_matches_tracking,
        "checkout_mode": "pull_request_merge" if is_pull_request else "branch_tracking",
        "pull_request": {
            "head_ref": pull_request_head_ref,
            "head_sha": pull_request_head_sha,
            "base_ref": pull_request_base_ref,
            "base_sha": pull_request_base_sha,
            "merge_base_parent": merge_base_parent,
            "merge_head_parent": merge_head_parent,
            "merge_lineage_verified": pull_request_merge_lineage_verified,
        },
        "working_tree_clean": not status_lines,
        "working_tree_change_count": len(status_lines),
        "working_tree_status": list(status_lines),
        "repository_api_error": repository_api_error,
        "workflow": {
            "path": str(workflow_path.relative_to(ROOT)),
            "committed_non_whitespace_bytes": len(committed_workflow.strip().encode("utf-8")),
            "local_non_whitespace_bytes": len(workflow_path.read_text(encoding="utf-8").strip().encode("utf-8")),
            "local_differs_from_head": workflow_path.read_text(encoding="utf-8") != committed_workflow,
        },
        "latest_exact_head_run": {
            "id": latest.get("id"),
            "name": latest.get("name"),
            "head_sha": latest.get("head_sha"),
            "status": latest.get("status"),
            "conclusion": latest.get("conclusion"),
            "created_at": latest.get("created_at"),
            "updated_at": latest.get("updated_at"),
            "html_url": latest.get("html_url"),
            "job_count": len(jobs),
        },
        "branch_head_recorded": branch_head_recorded,
        "required_ci_green": bool(
            latest.get("head_sha") == head
            and latest.get("status") == "completed"
            and latest.get("conclusion") == "success"
            and jobs
        ),
    }
    payload["ci_execution_exact_sha"] = ci_execution_exact_sha
    payload["required_ci_green"] = bool(payload["required_ci_green"] or payload["ci_execution_exact_sha"])
    payload["status"] = (
        "PASS"
        if payload["branch_head_recorded"] and payload["working_tree_clean"] and payload["required_ci_green"]
        else "FAIL"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "branch_head_recorded": payload["branch_head_recorded"],
                "checkout_mode": payload["checkout_mode"],
                "working_tree_clean": payload["working_tree_clean"],
                "required_ci_green": payload["required_ci_green"],
                "status": payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
