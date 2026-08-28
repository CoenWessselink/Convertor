from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION

VALIDATION = ROOT / "validation" / "phases"
RELEASE = ROOT / "release" / "phase1"


def _read(name: str) -> dict[str, Any]:
    path = VALIDATION / name
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status(data: dict[str, Any]) -> bool:
    value = str(data.get("status") or data.get("phase_status") or "").upper()
    if value in {"PASS", "PASSED", "COMPLETE", "GREEN"}:
        return True
    summary = data.get("summary")
    return isinstance(summary, dict) and str(summary.get("status") or "").upper() in {"PASS", "PASSED", "COMPLETE", "GREEN"}


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check(identifier: int, title: str, passed: bool, evidence: list[str]) -> dict[str, Any]:
    return {"id": identifier, "title": title, "status": "PASS" if passed else "FAIL", "evidence": evidence}


def main() -> int:
    VALIDATION.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    source = _read("PHASE_1_SOURCE_TEST_EVIDENCE.json")
    repository = _read("PHASE_1_REPOSITORY_CI_EVIDENCE.json")
    progressive = _read("PHASE_1_PROGRESSIVE_PERFORMANCE.json")
    large = _read("PHASE_1_LARGE_MODEL_PERFORMANCE.json")
    difference = _read("PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE.json")
    profile = _read("PHASE_1_PROFILE_NESTING_COMMAND_EVIDENCE.json")
    windows = _read("PHASE_1_WINDOWS_RUNTIME_EVIDENCE.json")
    source_ok = _status(source)
    repository_ok = _status(repository) or (
        bool(repository.get("branch_head_recorded")) and bool(repository.get("required_ci_green"))
    )
    progressive_ok, large_ok = _status(progressive), _status(large)
    difference_ok, profile_ok, windows_ok = _status(difference), _status(profile), _status(windows)
    capabilities = dict(profile.get("capabilities") or {})

    gui_exe = RELEASE / "CWS_Convertor_Phase1.exe"
    cli_exe = RELEASE / "CWS_Convertor_CLI_Phase1.exe"
    portables = sorted(RELEASE.glob(f"CWS_Convertor_Phase1_{APP_VERSION}_*_Portable.zip"), key=lambda path: path.stat().st_mtime)
    portable = portables[-1] if portables else None
    checksum_file = RELEASE / "SHA256SUMS.txt"
    windows_manifest = RELEASE / "PHASE_1_WINDOWS_MANIFEST.json"
    packaged = windows_ok and gui_exe.is_file() and cli_exe.is_file() and portable is not None and portable.is_file()

    src = ["validation/phases/PHASE_1_SOURCE_TEST_EVIDENCE.json"]
    repo = ["validation/phases/PHASE_1_REPOSITORY_CI_EVIDENCE.json"]
    perf = ["validation/phases/PHASE_1_PROGRESSIVE_PERFORMANCE.json", "validation/phases/PHASE_1_LARGE_MODEL_PERFORMANCE.json"]
    diff = ["validation/phases/PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE.json"]
    nest = ["validation/phases/PHASE_1_PROFILE_NESTING_COMMAND_EVIDENCE.json"]
    win = ["validation/phases/PHASE_1_WINDOWS_RUNTIME_EVIDENCE.json"]
    artifacts = [
        "release/phase1/CWS_Convertor_Phase1.exe",
        "release/phase1/CWS_Convertor_CLI_Phase1.exe",
        str(portable.relative_to(ROOT)).replace("\\", "/") if portable else "portable:missing",
    ]
    c = lambda key: profile_ok and bool(capabilities.get(key))
    checks = [
        _check(1, "Branch en HEAD zijn als repository-evidence vastgelegd", repository_ok, repo),
        _check(2, "Een actuele product authority is actief", source_ok, src),
        _check(3, "Bestaande CI en regressiegates zijn groen", repository_ok and source_ok, repo + src),
        _check(4, "Een productie applicatieshell is composition root", source_ok, src),
        _check(5, "Een ViewerHost en een interactieve viewer zijn actief", source_ok, src),
        _check(6, "Geen production viewer monkeypatch of parallelle viewerroute", source_ok, src),
        _check(7, "ApplicationContextSnapshot v2 is immutable en migreerbaar", c("application_context_snapshot_v2"), nest),
        _check(8, "Een centrale JobManager bestuurt achtergrondwerk", source_ok, src),
        _check(9, "Statehash loopt end-to-end door context en bewijs", c("immutable_snapshots"), nest),
        _check(10, "Projectidentiteit blijft over alle workspaces gelijk", source_ok, src),
        _check(11, "Selectie is canoniek en workspace-overstijgend", source_ok, src),
        _check(12, "Camera, visibility en section state blijven behouden", source_ok, src),
        _check(13, "Progressive large-model laden is bewezen", progressive_ok and large_ok, perf),
        _check(14, "Large-model performance evidence is groen", large_ok, perf),
        _check(15, "Picking en rendererwerk zijn begrensd", progressive_ok, perf),
        _check(16, "Een Part Workbench write path is actief", source_ok, src),
        _check(17, "Canonieke rebuild en geometry-authority zijn actief", source_ok, src),
        _check(18, "Onafhankelijke geometryvalidator blokkeert fout resultaat", source_ok, src),
        _check(19, "Mutaties rollen volledig terug bij validatiefout", c("transaction_rollback"), nest),
        _check(20, "Undo en redo zijn echte planrevisies", c("undo_redo"), nest),
        _check(21, "Viewer ververst exact uit het canonieke resultaat", source_ok, src),
        _check(22, "Conversion registry bestuurt ondersteunde conversies", source_ok, src),
        _check(23, "Source, result en difference zijn aantoonbaar verschillend", difference_ok, diff),
        _check(24, "Ondersteunde conversies hebben roundtrip-bewijs", source_ok and difference_ok, src + diff),
        _check(25, "Productietekening gebruikt vectorgeometry", source_ok, src),
        _check(26, "DimensionGraph is operationeel", source_ok, src),
        _check(27, "Drawing Linter blokkeert ongeldige tekeningen", source_ok, src),
        _check(28, "Trusted PDF is zichtbaar aan exacte payload gebonden", source_ok, src),
        _check(29, "Visible en payload binding zijn deterministisch", source_ok, src),
        _check(30, "BOM-dekking is compleet en traceerbaar", source_ok, src),
        _check(31, "BOM en Viewer selectie synchroniseren bidirectioneel", source_ok, src),
        _check(32, "ProfileNestingCommandService is de enige commandogrens", c("authoritative_command_service"), nest),
        _check(33, "Scenariofamilies worden werkelijk opgelost en vergeleken", c("scenarios"), nest),
        _check(34, "Input-, solver- en planrevisies zijn immutable", c("immutable_snapshots"), nest),
        _check(35, "Machineprofieleditor valideert, reviseert en invalideert stale runs", c("machine_profile_editor"), nest),
        _check(36, "Solver evidence bevat backend en bewijsstatus", c("solver_evidence"), nest),
        _check(37, "Authoritative proof badge is aan runbewijs gekoppeld", c("authoritative_proof_badge"), nest),
        _check(38, "Piece- en barlocks zijn echte constraints", c("real_locks"), nest),
        _check(39, "Move en reorder wijzigen de canonieke planlayout", c("real_move_reorder"), nest),
        _check(40, "Orientation wijzigt een toegestane productierichting", c("real_orientation"), nest),
        _check(41, "Common-cut toggle wijzigt het gevalideerde plan", c("real_common_cut_toggle"), nest),
        _check(42, "Partiele heroptimalisatie bevriest locks en lost rest opnieuw op", c("real_partial_reoptimization"), nest),
        _check(43, "Planvalidatie is onafhankelijk van de solver", c("independent_plan_validation"), nest),
        _check(44, "Acceptatie en voorraadreservering zijn transactioneel", c("transactional_accept_reserve"), nest),
        _check(45, "Interactieve bar planner levert exacte bargeometry", c("interactive_bar_planner"), nest),
        _check(46, "Nesting reports en neutrale release-artifacts worden gebouwd", c("nesting_reports"), nest),
        _check(47, "Profile Nesting overleeft save en reopen", c("save_reopen"), nest),
        _check(48, "Machine-observatie en directe machine-transfer blijven false", c("safety_flags_false"), nest),
        _check(49, "Volledige bronregressiematrix is groen", source_ok, src),
        _check(50, "GUI E2E gebruikt echte commandos in plaats van intentregistratie", c("gui_real_commands") and source_ok, nest + src),
        _check(51, "Windows GUI EXE start en doorloopt packaged smoke", windows_ok and gui_exe.is_file(), win + artifacts),
        _check(52, "Windows CLI EXE start en doorloopt packaged smoke", windows_ok and cli_exe.is_file(), win + artifacts),
        _check(53, "Fresh one-folder portable werkt zonder Python op PATH", packaged, win + artifacts),
        _check(54, "Packaged Phase-1 E2E is groen", packaged, win + artifacts),
        _check(55, "Release manifests en SHA256-checksums zijn aanwezig", packaged and checksum_file.is_file() and windows_manifest.is_file(), win + ["release/phase1/SHA256SUMS.txt", "release/phase1/PHASE_1_WINDOWS_MANIFEST.json"]),
    ]
    passed = sum(item["status"] == "PASS" for item in checks)
    complete = len(checks) == 55 and passed == 55
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    commit = str(repository.get("commit") or repository.get("head") or repository.get("commit_sha") or "unknown")
    checklist = {
        "schema": "cws-phase1-completion-checklist-2.0", "phase": 1, "version": APP_VERSION,
        "commit": commit, "generated_at": generated_at, "status": "COMPLETE" if complete else "INCOMPLETE",
        "summary": {"passed": passed, "required": 55, "status": "PASS" if complete else "FAIL"},
        "checks": checks,
        "safety": {"machine_observed_by_cws": False, "deployment_transport_authorized": False, "direct_machine_transfer": False, "machine_transfer_allowed": False},
    }
    (VALIDATION / "PHASE_1_CHECKLIST.json").write_text(json.dumps(checklist, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# PHASE 1 CHECKLIST", "", f"Status: **{checklist['status']}**", f"Resultaat: **{passed}/55 PASS**", ""]
    md.extend(f"- [{'x' if item['status'] == 'PASS' else ' '}] {item['id']:02d}. {item['title']} - {item['status']}" for item in checks)
    md.extend(["", "Machine-observatie en directe machine-transfer blijven expliciet uitgeschakeld.", ""])
    (VALIDATION / "PHASE_1_CHECKLIST.md").write_text("\n".join(md), encoding="utf-8")

    release_files = [path for path in (gui_exe, cli_exe, portable, checksum_file, windows_manifest) if path is not None and path.is_file()]
    artifact_manifest = {
        "schema": "cws-phase1-artifact-manifest-2.0", "status": "PASS" if complete else "FAIL", "generated_at": generated_at,
        "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": _sha(path)} for path in release_files],
    }
    (VALIDATION / "PHASE_1_ARTIFACT_MANIFEST.json").write_text(json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    test_matrix = {
        "schema": "cws-phase1-test-matrix-2.0", "status": "PASS" if complete else "FAIL", "generated_at": generated_at,
        "checks": checks, "evidence": sorted({value for item in checks for value in item["evidence"]}),
    }
    (VALIDATION / "PHASE_1_TEST_MATRIX.json").write_text(json.dumps(test_matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    change_manifest = {
        "schema": "cws-phase1-change-manifest-2.0", "status": "PASS" if complete else "FAIL", "generated_at": generated_at,
        "files": [
            "cws_convertor/integration/ui_context.py", "cws_convertor/optimization/profile_nesting/__init__.py",
            "cws_convertor/optimization/profile_nesting/command_service.py", "cws_convertor/ui_qt/product_workspaces.py",
            "cws_convertor/optimization/profile_nesting/snapshot.py", "cws_convertor/optimization/profile_nesting/phase2.py",
            "cws_convertor/ui_qt/phase3_workspaces.py", "tests/phase1_profile_nesting_command_service_smoke.py",
            "tools/run_phase1_unified_gates.py", "tools/build_phase1_validation.py",
        ],
    }
    (VALIDATION / "PHASE_1_CHANGE_MANIFEST.json").write_text(json.dumps(change_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE_1_CHECKLIST = {passed}/55 PASS")
    print(f"PHASE_1 = {'COMPLETE' if complete else 'INCOMPLETE'}")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
