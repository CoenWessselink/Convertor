"""Opt in to audited W18 scenario evidence without promoting product acceptance.

The matrix may remain PARTIAL. A PASS in this binding report means that the
individual scenario references were verified, not that the product, action,
functional dimension, or installed build passed acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import master_requirements_v2 as master

SCHEMA = "cws-w18-requirements-binding-1.0"
AUDIT_SCHEMA = "cws-bom-w18-coverage-3.0"
ENVELOPE = ("commit", "app_version", "environment", "input_hash", "scenario", "result", "output_hash")
ACCEPTED = {"PASS", "NOT_APPLICABLE"}
SCENARIO_STATES = ACCEPTED | {"PARTIAL", "BLOCKED_EXTERNAL"}


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _content_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _inside(path: Path | str, root: Path) -> Path:
    path = Path(path)
    path = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Evidence and output paths must remain inside the workspace: " + str(path))
    return path


def _relative_source(relative: str, root: Path) -> Path:
    if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative
            or any(character in relative for character in ("\n", "\r", "\0"))
            or PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts
            or PurePosixPath(relative).as_posix() != relative):
        raise ValueError("Invalid relative source path: " + repr(relative))
    return _inside(relative, root)


def _reject_product_claims(report: dict[str, Any]) -> None:
    for key in ("installed_main_window", "installed_main_window_proven", "installed_tested",
                "real_world_tested", "release_ready", "external_acceptance_proven"):
        if report.get(key) not in (None, False, "UNVERIFIED", "PARTIAL", "BLOCKED_EXTERNAL"):
            raise ValueError("Source/component evidence cannot assert " + key)
    if report.get("installed_commit"):
        raise ValueError("Source/component evidence cannot assert an installed_commit")


def validate_source_commit(report: dict[str, Any], root: Path = ROOT) -> str:
    """Require current bytes and the reported Git tree to agree for every source.

    Compare raw blob bytes, not Git's clean/smudge-normalized worktree status.
    An unrelated documentation change is permitted; a dirty executable source,
    absent source blob, or invented/non-commit SHA is not.
    """
    root = Path(root).resolve()
    _reject_product_claims(report)
    commit = report.get("commit", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Evidence commit must be a complete Git SHA")
    verified = subprocess.run(["git", "rev-parse", "--verify", commit + "^{commit}"],
                              cwd=root, capture_output=True, text=True)
    if verified.returncode or verified.stdout.strip() != commit:
        raise ValueError("Evidence commit does not exist as the stated Git commit: " + commit)
    if report.get("source_unchanged_during_run") is not True:
        raise ValueError("Evidence sources were not stable during execution")
    sources = report.get("sources")
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Evidence source manifest is missing")
    for relative, expected in sources.items():
        path = _relative_source(relative, root)
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid source SHA256: " + relative)
        if not path.is_file() or master.sha256(path) != expected:
            raise ValueError("Missing or changed current source: " + relative)
    # One binary batch preserves exact blob bytes and avoids launching Git once
    # for each of the several hundred transitive runtime files in the manifest.
    names = sorted(sources)
    request = "".join(commit + ":" + name + "\n" for name in names).encode("utf-8")
    result = subprocess.run(["git", "cat-file", "--batch"], cwd=root, input=request, capture_output=True)
    if result.returncode:
        raise ValueError("Cannot read evidence commit source blobs")
    offset = 0
    for relative in names:
        end = result.stdout.find(b"\n", offset)
        header = result.stdout[offset:end].split() if end >= 0 else []
        if len(header) != 3 or header[1] != b"blob" or not header[2].isdigit():
            raise ValueError("Source is absent from the evidence commit: " + relative)
        size = int(header[2])
        start = end + 1
        blob = result.stdout[start:start + size]
        if len(blob) != size or result.stdout[start + size:start + size + 1] != b"\n":
            raise ValueError("Invalid Git source blob response: " + relative)
        if hashlib.sha256(blob).hexdigest() != sources[relative]:
            raise ValueError("Dirty or stale source differs from evidence commit: " + relative)
        offset = start + size + 1
    return commit


def _audit_catalog(path: Path) -> dict[str, Any]:
    from tools import audit_bom_w18_scenario_coverage as audit
    return audit.build_catalog(path)


def build_evidence(positive_results: Path | str, root: Path = ROOT) -> dict[str, Any]:
    """Read the strict audit; retain only its explicitly accepted scenarios."""
    root = Path(root).resolve()
    path = _inside(positive_results, root)
    raw = path.read_bytes()
    report = json.loads(raw)
    if any(key not in report or not report[key] for key in ENVELOPE):
        raise ValueError("Positive report lacks the seven required evidence fields")
    if report["result"] not in {"PASS", "PARTIAL"}:
        raise ValueError("Failed or unexecuted matrix cannot bind scenario evidence")
    if not isinstance(report["environment"], dict) or not isinstance(report["app_version"], str):
        raise ValueError("Evidence environment and app version must describe the source run")
    if any(not re.fullmatch(r"[0-9a-f]{64}", str(report[key])) for key in ("input_hash", "output_hash")):
        raise ValueError("Evidence input/output hashes must be exact SHA256")
    if report["input_hash"] != report.get("matrix_sha256"):
        raise ValueError("Evidence input hash differs from the canonical matrix input")
    actions = report.get("actions")
    if (not isinstance(actions, list)
            or report["output_hash"] != hashlib.sha256(json.dumps(actions, sort_keys=True).encode()).hexdigest()):
        raise ValueError("Evidence output hash does not match the complete observed action results")
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError("Invalid observed action record")
        if (action.get("installed_commit") or action.get("installed_tested") not in (None, False)
                or action.get("installed_main_window") not in (None, False)):
            raise ValueError("Source/component action cannot assert installed acceptance")
    commit = validate_source_commit(report, root)
    catalog = _audit_catalog(path)
    if catalog.get("schema") != AUDIT_SCHEMA:
        raise ValueError("W18 binding requires the complete 15-scenario audit 3.0 schema")
    _reject_product_claims(catalog)
    expected = {item["action_id"] for item in master.canonical_actions(root)}
    actions = catalog.get("actions", [])
    if len(actions) != 87 or {row.get("action_id") for row in actions} != expected:
        raise ValueError("Audited catalog must contain exactly the 87 canonical actions")
    requirements = {}
    counts: Counter[str] = Counter()
    for action in actions:
        scenarios = action.get("scenarios")
        if not isinstance(scenarios, dict) or set(scenarios) != set(master.SCENARIOS):
            raise ValueError("Incomplete 15-scenario audit: " + action["action_id"])
        accepted, details = {}, {}
        for name in master.SCENARIOS:
            entry = scenarios[name]
            if (not isinstance(entry, dict) or entry.get("status") not in SCENARIO_STATES
                    or type(entry.get("applicable")) is not bool
                    or not isinstance(entry.get("reason"), str) or not entry["reason"].strip()
                    or not isinstance(entry.get("evidence"), list)):
                raise ValueError("Invalid audited scenario: " + action["action_id"] + "/" + name)
            status = entry["status"]
            if (status == "NOT_APPLICABLE") != (entry["applicable"] is False):
                raise ValueError("Unreviewed scenario applicability: " + action["action_id"] + "/" + name)
            counts[status] += 1
            if status in ACCEPTED:
                if not entry["evidence"] or any(not isinstance(item, dict) or not item.get("kind")
                                                or not item.get("source") for item in entry["evidence"]):
                    raise ValueError("Accepted scenario lacks specific evidence: " + action["action_id"] + "/" + name)
                accepted[name] = status
                details[name] = deepcopy(entry)
        requirements["W18-" + action["action_id"]] = {
            "action_id": action["action_id"], "scenarios": accepted,
            "scenario_evidence": details, "dimensions": {},
        }
    if path.read_bytes() != raw:
        raise ValueError("Positive evidence changed during binding")
    validate_source_commit(report, root)
    return {
        "schema": SCHEMA, "commit": commit, "app_version": report["app_version"],
        "environment": deepcopy(report["environment"]), "input_hash": hashlib.sha256(raw).hexdigest(),
        "scenario": "Verified binding of audited W18 individual scenarios to Master Requirements V2",
        "result": "PASS", "output_hash": _content_hash(requirements),
        "claim": "PASS verifies this binding only. No complete action, acceptance dimension, installed build or release is promoted.",
        "source_report": {"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
                          "result": report["result"]},
        "sources": deepcopy(report["sources"]), "source_unchanged_during_run": True,
        "source_commit_verified": True, "audit_schema": catalog["schema"],
        "audit_catalog_sha256": _content_hash(catalog), "scenario_counts": dict(sorted(counts.items())),
        "installed_tested": False, "installed_commit": None, "real_world_tested": False,
        "release_ready": False, "requirements": requirements,
    }


def verify_evidence(path: Path | str, root: Path = ROOT) -> dict[str, Any]:
    """Reaudit retained input/artifacts and commit bytes; a hash alone is insufficient."""
    path = _inside(path, Path(root))
    evidence = master.read_json(path)
    if evidence.get("schema") != SCHEMA:
        raise ValueError("Unsupported W18 requirement binding schema")
    source = evidence.get("source_report", {})
    input_path = _inside(source.get("path", ""), Path(root))
    if not input_path.is_file() or master.sha256(input_path) != source.get("sha256"):
        raise ValueError("Bound positive input is missing or changed")
    if build_evidence(input_path, root) != evidence:
        raise ValueError("Binding content does not match freshly audited evidence")
    return evidence


def attach_evidence(register: dict[str, Any], evidence: dict[str, Any], path: Path | str,
                    root: Path = ROOT) -> dict[str, Any]:
    """Attach scenario references, keeping acceptance dimensions unchanged."""
    register = deepcopy(register)
    path = _inside(path, Path(root))
    if register["source_commit"] != evidence["commit"]:
        raise ValueError("Requirement baseline and scenario source commit differ")
    relative = path.relative_to(Path(root).resolve()).as_posix()
    envelope = {**{key: evidence[key] for key in ENVELOPE}, "path": relative, "sha256": master.sha256(path)}
    for row in register["requirements"]:
        bound = evidence["requirements"].get(row["requirement_id"])
        if not bound or not bound["scenarios"]:
            continue
        row["evidence"].append(deepcopy(envelope))
        row["test"]["state"] = "INDIVIDUAL_SCENARIOS_PROVEN_ACCEPTANCE_PARTIAL"
        for test in ("tests/bom_w18_positive_matrix_smoke.py", "tools/audit_bom_w18_scenario_coverage.py"):
            if test not in row["test"]["paths"]:
                row["test"]["paths"].append(test)
        for name, state in bound["scenarios"].items():
            detail = bound["scenario_evidence"][name]
            row["scenarios"][name] = {"required": detail["applicable"], "state": state,
                                      "reason": detail["reason"], "evidence": [relative]}
    register["w18_evidence_binding"] = {"path": relative, "sha256": master.sha256(path),
                                       "scenario_counts": evidence["scenario_counts"],
                                       "acceptance_dimensions_promoted": []}
    register["summary"] = master.summarize(register)
    return register


def write_binding(positive_results: Path | str, output: Path | str, *,
                  evidence_output: Path | str | None = None, markdown_output: Path | str | None = None,
                  root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    output = _inside(output, root)
    evidence_output = _inside(evidence_output or output.with_name(output.stem + ".w18-evidence.json"), root)
    paths = [_inside(positive_results, root), output, evidence_output]
    if markdown_output is not None:
        paths.append(_inside(markdown_output, root))
    if len(set(paths)) != len(paths):
        raise ValueError("Input, binding report, register and Markdown need distinct paths")
    evidence = build_evidence(positive_results, root)
    register = master.build_register(root, evidence["commit"])
    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    evidence_output.write_bytes(_json_bytes(evidence))
    verify_evidence(evidence_output, root)
    register = attach_evidence(register, evidence, evidence_output, root)
    errors = master.validate_register(register, root)
    if errors:
        raise ValueError("Bound register failed validation: " + "; ".join(errors[:8]))
    output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve the generator's field order, so binding a few scenario results
    # does not rewrite every requirement row in the review diff.
    output.write_bytes((json.dumps(register, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if markdown_output is not None:
        markdown_path = paths[-1]
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_bytes(master.markdown(register).encode("utf-8"))
    return register


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive-results", type=Path)
    parser.add_argument("--output", type=Path, help="Explicit opt-in destination for the bound V2 JSON")
    parser.add_argument("--evidence-output", type=Path)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--check-evidence", type=Path, help="Reaudit a previously written binding report")
    args = parser.parse_args()
    try:
        if args.check_evidence:
            evidence = verify_evidence(args.check_evidence)
            counts = evidence["scenario_counts"]
        else:
            if not args.positive_results or not args.output:
                parser.error("--positive-results and --output are required when binding evidence")
            register = write_binding(args.positive_results, args.output,
                                     evidence_output=args.evidence_output, markdown_output=args.markdown)
            counts = register["w18_evidence_binding"]["scenario_counts"]
        print(json.dumps({"status": "PASS", "claim": "scenario binding verified; product acceptance remains partial",
                          "scenarios": counts}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "FAIL", "error": str(error)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
