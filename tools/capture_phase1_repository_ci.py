"""Capture read-only Phase-1 repository and GitHub Actions evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "phases" / "PHASE_1_REPOSITORY_CI_EVIDENCE.json"
REPOSITORY = "CoenWessselink/Convertor"
CANONICAL_BRANCH = "agent/cws-product-ui-reintegration-v1"


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


def main() -> int:
    branch = git("branch", "--show-current") or CANONICAL_BRANCH
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    tracking = f"origin/{CANONICAL_BRANCH}"
    tracking_head = git("rev-parse", tracking)
    ahead_text = git("rev-list", "--left-right", "--count", f"HEAD...{tracking}")
    ahead, behind = (int(value) for value in ahead_text.split())
    status_lines = tuple(line for line in git("status", "--short").splitlines() if line)
    runs_payload = github_json(
        f"https://api.github.com/repos/{REPOSITORY}/actions/runs?branch={quote(branch, safe='')}&per_page=20"
    )
    runs = list(runs_payload.get("workflow_runs") or [])
    exact_runs = [run for run in runs if str(run.get("head_sha")) == head]
    latest = exact_runs[0] if exact_runs else (runs[0] if runs else {})
    jobs: list[dict] = []
    if latest.get("jobs_url"):
        jobs = list(github_json(str(latest["jobs_url"])).get("jobs") or [])
    workflow_path = ROOT / ".github" / "workflows" / "build-product-ui-reintegration-exe.yml"
    committed_workflow = git("show", f"{head}:.github/workflows/build-product-ui-reintegration-exe.yml")
    payload = {
        "schema": "cws-phase1-repository-ci-evidence-1.0",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "repository": REPOSITORY,
        "branch": branch,
        "head": head,
        "parent": parent,
        "tracking": tracking,
        "ahead": ahead,
        "behind": behind,
        "head_matches_tracking": ahead == 0 and behind == 0 and tracking_head == head,
        "working_tree_clean": not status_lines,
        "working_tree_change_count": len(status_lines),
        "working_tree_status": list(status_lines),
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
        "branch_head_recorded": bool(branch == CANONICAL_BRANCH and len(head) == 40 and len(parent) == 40 and tracking_head == head),
        "required_ci_green": bool(
            latest.get("head_sha") == head
            and latest.get("status") == "completed"
            and latest.get("conclusion") == "success"
            and jobs
        ),
    }
    payload["ci_execution_exact_sha"] = bool(
        os.environ.get("GITHUB_ACTIONS", "").casefold() == "true"
        and str(os.environ.get("GITHUB_SHA") or "").casefold() == head.casefold()
    )
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
                "working_tree_clean": payload["working_tree_clean"],
                "required_ci_green": payload["required_ci_green"],
                "status": payload["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
