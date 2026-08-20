"""Phase-8 production-release gate and cryptographically bound evidence validation.

The gate is deliberately conservative: local tests or synthetic benchmarks can
prove software properties, but they cannot substitute owner-validated straight
and miter jobs or a clean Windows x64 packaged-runtime result.  External
evidence is accepted only when the referenced artefacts physically exist and
their SHA-256 values match the evidence record.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
import json
import re
from typing import Any

from cws_convertor.product import APP_VERSION
from cws_convertor.project.model import stable_sha256, utc_now_iso
from cws_convertor.production_export.utils import sha256_file
from .postprocessor import DEFAULT_POSTPROCESSOR_REGISTRY, PostprocessorRegistry

PHASE8_RELEASE_GATE_SCHEMA_VERSION = "1.1"
OWNER_VALIDATION_SCHEMA_VERSION = "1.1"
WINDOWS_EVIDENCE_SCHEMA_VERSION = "1.1"
BENCHMARK_EVIDENCE_SCHEMA_VERSION = "1.0"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class ReleaseGateCheck:
    check_id: str
    status: str  # passed | blocked | warning
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileNestingReleaseGate:
    product_version: str
    checks: list[ReleaseGateCheck]
    production_feature_released: bool
    machine_output_released: bool
    supported_postprocessors: list[dict[str, Any]]
    generated_at: str = field(default_factory=utc_now_iso)
    schema_version: str = PHASE8_RELEASE_GATE_SCHEMA_VERSION
    report_hash: str = ""

    def refresh_hash(self) -> str:
        payload = self.to_dict(include_hash=False)
        payload.pop("generated_at", None)
        self.report_hash = stable_sha256(payload)
        return self.report_hash

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        if not include_hash:
            payload.pop("report_hash", None)
        return payload


def _load_context(value: dict[str, Any] | str | Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    if value is None:
        return None, None
    if isinstance(value, dict):
        payload = dict(value)
        root = payload.pop("evidence_root", None)
        return payload, Path(root).resolve() if root else None
    path = Path(value).resolve()
    return json.loads(path.read_text(encoding="utf-8")), path.parent


def _load(value: dict[str, Any] | str | Path | None) -> dict[str, Any] | None:
    return _load_context(value)[0]


def _resolve_evidence_path(root: Path | None, relative_path: str) -> Path | None:
    if root is None or not relative_path:
        return None
    pure = PurePosixPath(str(relative_path).replace("\\", "/"))
    if pure.is_absolute() or ".." in pure.parts:
        return None
    candidate = root.joinpath(*pure.parts).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _verify_artifact(ref: Any, root: Path | None, label: str) -> tuple[bool, str, dict[str, Any]]:
    item = dict(ref or {}) if isinstance(ref, dict) else {}
    rel = str(item.get("path") or "")
    expected = str(item.get("sha256") or "").lower()
    if not rel:
        return False, f"{label}: artefactpad ontbreekt", {}
    if not _SHA256_RE.fullmatch(expected):
        return False, f"{label}: geldige SHA-256 ontbreekt", {"path": rel}
    path = _resolve_evidence_path(root, rel)
    if path is None:
        return False, f"{label}: bewijsroot/pad is ongeldig of ontbreekt", {"path": rel}
    if not path.is_file():
        return False, f"{label}: bewijsbestand bestaat niet: {rel}", {"path": rel}
    actual = sha256_file(path).lower()
    if actual != expected:
        return False, f"{label}: SHA-256 mismatch voor {rel}", {"path": rel, "expected": expected, "actual": actual}
    return True, "", {"path": rel, "sha256": actual, "size_bytes": path.stat().st_size}


def validate_benchmark_evidence(value: dict[str, Any] | str | Path | None) -> ReleaseGateCheck:
    payload = _load(value)
    if not payload:
        return ReleaseGateCheck("benchmark", "blocked", "Fase-8 benchmarkevidence ontbreekt")
    errors: list[str] = []
    if str(payload.get("schema_version") or "") != BENCHMARK_EVIDENCE_SCHEMA_VERSION:
        errors.append("onbekende benchmark schema-versie")
    if str(payload.get("product_version") or "") != APP_VERSION:
        errors.append("benchmark hoort niet bij de actuele applicatieversie")
    if str(payload.get("status") or "") != "passed":
        errors.append("benchmark suite is niet volledig geslaagd")
    cases = list(payload.get("cases") or [])
    required = {"straight_greedy_large", "angle_greedy_medium", "angle_exact_small", "save_reopen_large"}
    got = {str(c.get("case_id") or "") for c in cases if str(c.get("status") or "") == "passed"}
    missing = sorted(required - got)
    if missing:
        errors.append(f"verplichte benchmarkcases ontbreken: {', '.join(missing)}")
    return ReleaseGateCheck("benchmark", "passed" if not errors else "blocked", "Benchmarkpoort geslaagd" if not errors else "; ".join(errors), {"case_count": len(cases)})


def validate_windows_evidence(value: dict[str, Any] | str | Path | None) -> ReleaseGateCheck:
    payload, root = _load_context(value)
    if not payload:
        return ReleaseGateCheck("windows_x64", "blocked", "Clean-Windows-x64 packaged-runtime evidence ontbreekt")
    errors: list[str] = []
    verified: dict[str, Any] = {}
    if str(payload.get("schema_version") or "") != WINDOWS_EVIDENCE_SCHEMA_VERSION:
        errors.append("onbekende Windows-evidence schema-versie")
    if str(payload.get("product_version") or "") != APP_VERSION:
        errors.append("Windows-evidence hoort niet bij de actuele applicatieversie")
    commit = str(payload.get("source_commit") or payload.get("commit") or "")
    if len(commit) < 7 or commit.lower() in {"unknown", "none", "n/a"}:
        errors.append("Windows-evidence mist een concrete source_commit")
    for key in ("source", "dist", "portable", "installed", "installer", "uninstall"):
        if str(dict(payload.get("matrix") or {}).get(key) or "") != "passed":
            errors.append(f"Windows matrix {key} is niet passed")
    if payload.get("python_required") is not False:
        errors.append("geïnstalleerde/portable runtime is niet bewezen Python-onafhankelijk")
    if str(payload.get("profile_nesting_packaged_smoke") or "") != "passed":
        errors.append("packaged Profile Nesting solve/release smoke ontbreekt")
    required_artifacts = {"installer", "portable", "gui_exe", "cli_exe", "packaged_smoke_result", "uninstall_log"}
    artifacts = dict(payload.get("artifacts") or {})
    for key in sorted(required_artifacts):
        ok, message, details = _verify_artifact(artifacts.get(key), root, f"Windows {key}")
        if not ok:
            errors.append(message)
        else:
            verified[key] = details
    smoke_ref = artifacts.get("packaged_smoke_result")
    smoke_path = _resolve_evidence_path(root, str(dict(smoke_ref or {}).get("path") or "")) if isinstance(smoke_ref, dict) else None
    if smoke_path and smoke_path.is_file():
        try:
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
            if str(smoke.get("status") or "") != "passed" or str(smoke.get("product_version") or "") != APP_VERSION:
                errors.append("packaged smoke artefact is niet passed voor de actuele applicatieversie")
        except Exception:
            errors.append("packaged smoke artefact is geen geldig JSON-evidencebestand")
    return ReleaseGateCheck(
        "windows_x64", "passed" if not errors else "blocked",
        "Clean-Windows-x64 poort geslaagd" if not errors else "; ".join(errors),
        {"run_id": payload.get("run_id", ""), "source_commit": commit, "verified_artifacts": verified},
    )


def validate_owner_validation(value: dict[str, Any] | str | Path | None) -> ReleaseGateCheck:
    payload, root = _load_context(value)
    if not payload:
        return ReleaseGateCheck("owner_validation", "blocked", "Eigenaar-gevalideerde praktijkjobs ontbreken (minimaal één rechte en één verstekjob)")
    errors: list[str] = []
    verified_cases: list[dict[str, Any]] = []
    if str(payload.get("schema_version") or "") != OWNER_VALIDATION_SCHEMA_VERSION:
        errors.append("onbekende owner-validation schema-versie")
    if str(payload.get("product_version") or "") != APP_VERSION:
        errors.append("owner-validation hoort niet bij de actuele applicatieversie")
    commit = str(payload.get("source_commit") or "")
    if len(commit) < 7 or commit.lower() in {"unknown", "none", "n/a"}:
        errors.append("owner-validation mist een concrete source_commit")
    approval_ok, approval_message, approval_details = _verify_artifact(payload.get("approval_artifact"), root, "owner approval")
    if not approval_ok:
        errors.append(approval_message)
    cases = list(payload.get("cases") or [])
    approved = [c for c in cases if bool(c.get("owner_approved")) and str(c.get("status") or "") == "passed"]
    scopes = {str(c.get("scope") or "") for c in approved}
    if "straight" not in scopes:
        errors.append("geen eigenaar-gevalideerde rechte-cutjob")
    if "angle" not in scopes:
        errors.append("geen eigenaar-gevalideerde verstekjob")
    for case in approved:
        cid = str(case.get("case_id") or "")
        if not cid:
            errors.append("case_id ontbreekt bij eigenaar-gevalideerde case")
        if not str(case.get("owner") or "") or not str(case.get("approved_at") or ""):
            errors.append(f"owner/approved_at ontbreekt bij case {cid}")
        if not str(case.get("machine_id") or ""):
            errors.append(f"machine_id ontbreekt bij case {cid}")
        if str(case.get("product_version") or "") != APP_VERSION:
            errors.append(f"product_version mismatch bij case {cid}")
        if str(case.get("source_commit") or "") != commit:
            errors.append(f"source_commit mismatch bij case {cid}")
        input_ref = {"path": case.get("input_path", ""), "sha256": case.get("input_sha256", "")}
        result_ref = {"path": case.get("expected_result_path", ""), "sha256": case.get("expected_result_sha256", "")}
        i_ok, i_msg, i_details = _verify_artifact(input_ref, root, f"owner case {cid} input")
        r_ok, r_msg, r_details = _verify_artifact(result_ref, root, f"owner case {cid} resultaat")
        if not i_ok: errors.append(i_msg)
        if not r_ok: errors.append(r_msg)
        if i_ok and r_ok:
            verified_cases.append({"case_id": cid, "scope": case.get("scope"), "machine_id": case.get("machine_id"), "input": i_details, "result": r_details})
    return ReleaseGateCheck(
        "owner_validation", "passed" if not errors else "blocked",
        "Praktijkvalidatiepoort geslaagd" if not errors else "; ".join(errors),
        {"approved_cases": len(approved), "scopes": sorted(scopes), "source_commit": commit, "approval_artifact": approval_details if approval_ok else {}, "verified_cases": verified_cases},
    )


def evaluate_profile_nesting_release_gate(
    *,
    benchmark_evidence: dict[str, Any] | str | Path | None = None,
    windows_evidence: dict[str, Any] | str | Path | None = None,
    owner_validation: dict[str, Any] | str | Path | None = None,
    test_evidence: dict[str, Any] | str | Path | None = None,
    registry: PostprocessorRegistry = DEFAULT_POSTPROCESSOR_REGISTRY,
) -> ProfileNestingReleaseGate:
    checks = [validate_benchmark_evidence(benchmark_evidence), validate_windows_evidence(windows_evidence), validate_owner_validation(owner_validation)]
    tests = _load(test_evidence)
    if tests and str(tests.get("status") or "") == "passed" and str(tests.get("product_version") or "") == APP_VERSION:
        checks.insert(0, ReleaseGateCheck("regression", "passed", "Actuele profielnesting regressie-evidence geslaagd", {"tests": tests.get("summary", tests.get("counts", {}))}))
    else:
        checks.insert(0, ReleaseGateCheck("regression", "blocked", "Actuele profielnesting regressie-evidence ontbreekt of is niet passed"))
    descriptors = [d.to_dict() for d in registry.descriptors()]
    enabled = [d for d in descriptors if bool(d.get("production_enabled"))]
    checks.append(ReleaseGateCheck("postprocessors", "passed" if enabled else "warning", f"{len(enabled)} eigenaar-gevalideerde machinepostprocessor(s) actief" if enabled else "Geen proprietary machinepostprocessor als gevalideerd geregistreerd; neutral job blijft de enige standaarduitvoer", {"registered": len(descriptors), "production_enabled": len(enabled)}))
    production = all(c.status == "passed" for c in checks if c.check_id in {"regression", "benchmark", "windows_x64", "owner_validation"})
    gate = ProfileNestingReleaseGate(
        product_version=APP_VERSION,
        checks=checks,
        production_feature_released=production,
        machine_output_released=bool(production and enabled),
        supported_postprocessors=enabled,
    )
    gate.refresh_hash()
    return gate


__all__ = [
    "PHASE8_RELEASE_GATE_SCHEMA_VERSION", "OWNER_VALIDATION_SCHEMA_VERSION", "WINDOWS_EVIDENCE_SCHEMA_VERSION",
    "BENCHMARK_EVIDENCE_SCHEMA_VERSION", "ReleaseGateCheck", "ProfileNestingReleaseGate",
    "validate_benchmark_evidence", "validate_windows_evidence", "validate_owner_validation", "evaluate_profile_nesting_release_gate",
]
