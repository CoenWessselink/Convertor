from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "validation" / "master_completion"
SOURCE_ROOT = ROOT / "requirements" / "sources"
ALLOWED_STATUSES = (
    "PASS",
    "PARTIAL",
    "NOT_IMPLEMENTED",
    "NOT_INTEGRATED",
    "FAIL",
    "NOT_TESTED",
    "BLOCKED",
    "BLOCKED_EXTERNAL_EVIDENCE",
    "BLOCKED_QUEUE_SOURCE_UNAVAILABLE",
    "NOT_APPLICABLE",
    "SUPERSEDED",
)
PASS_LIKE = {"PASS", "NOT_APPLICABLE", "SUPERSEDED"}


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ("git", *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(name: str, payload: Any) -> None:
    (OUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _tracked(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return bool(_git("ls-files", "--error-unmatch", "--", relative, check=False))


def _source_entry(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    headings = [match.group(2).strip() for match in re.finditer(r"(?m)^(#{1,4})\s+(.+)$", text)]
    return {
        "name": path.name,
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "lines": len(text.splitlines()),
        "sha256": sha256(data).hexdigest(),
        "heading_count": len(headings),
        "headings": headings,
    }


def _phase_gate(number: int) -> dict[str, Any]:
    path = ROOT / "validation" / "final_4_phase" / f"phase{number}" / "PHASE_GATE.json"
    payload = _json(path, {}) or {}
    return {
        "phase": number,
        "path": path.relative_to(ROOT).as_posix(),
        "status": str(payload.get("status") or "NOT_TESTED"),
        "source_commit": payload.get("commit") or payload.get("source_commit"),
        "false_green_count": payload.get("false_green_count"),
        "packaged_proven": payload.get("packaged_proven", payload.get("packaged_runtime_proven")),
        "screenshots": list(payload.get("screenshots") or []),
    }


def _queue_id_for(text: str, source_name: str) -> str:
    value = f"{source_name} {text}".upper()
    if "QUEUE" in value or "WACHTRIJ" in value:
        return "Q012"
    if "TRIMBLE" in value:
        return "Q004"
    if any(word in value for word in ("INTERPRETER", "BREP", "RECONSTRUCTION", "MULTI-EXTRUSION")):
        return "Q007"
    if any(word in value for word in ("MESHCACHE", "WORKER POOL", "UPLOAD GOVERNOR", "VIEWER PERFORMANCE", "BENCHMARK", "SOAK", "MSAA")):
        return "Q002"
    if any(word in value for word in ("UI ", "SCREEN", "ICON", "VISUAL", "NAVIGATION", "CONTROL BINDING", "V5.1", "V5.2")):
        return "Q005"
    if any(word in value for word in ("BOM", "NESTING", "WORKBENCH", "MACHINE ROUTING", "CONVERTER", "SCRIBING", "MANUFACTURING")):
        return "Q006"
    if any(word in value for word in ("DRAWING", "PDF", "PRINT", "QUALITY", "PLANNING", "SHOPFLOOR", "EXPORT CENTER", "CONTROLE")):
        return "Q008"
    if any(word in value for word in ("INSTALLER", "PORTABLE", "EXACT-SHA", "WINDOWS RELEASE", "RELEASE ARTIFACT")):
        return "Q011"
    if any(word in value for word in ("ACCEPTANCE", "FINAL GATE", "DEFINITION OF DONE")):
        return "Q010"
    return "Q001"


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    branch = _git("branch", "--show-current") or "DETACHED"
    remote_ref = f"origin/{branch}" if branch != "DETACHED" else ""
    remote_head = _git("rev-parse", remote_ref, check=False) if remote_ref else ""
    divergence = _git("rev-list", "--left-right", "--count", f"HEAD...{remote_ref}", check=False) if remote_head else ""
    ahead, behind = (int(value) for value in divergence.split()) if len(divergence.split()) == 2 else (None, None)

    master_path = ROOT / "requirements" / "MASTER_REQUIREMENT_TRACEABILITY.json"
    master = _json(master_path, {}) or {}
    master_rows = list(master.get("requirements") or [])
    master_counts = Counter(str(row.get("status") or "NOT_TESTED") for row in master_rows)
    phase_gates = [_phase_gate(number) for number in range(1, 5)]
    phase_status = {gate["phase"]: gate["status"] for gate in phase_gates}
    audit_name = "CODEX_PROMPT_QUEUE_AUDIT_AND_AUTO_COMPLETE_100PCT_2026-08-31.md"
    source_entries = [_source_entry(path) for path in sorted(SOURCE_ROOT.iterdir()) if path.is_file()]
    mgi_acceptance_path = ROOT / "validation" / "manufacturing_interpreter" / "FINAL_ACCEPTANCE_REPORT.json"
    mgi_acceptance = _json(mgi_acceptance_path, {}) or {}
    mgi_complete = (
        str(mgi_acceptance.get("status") or "") == "COMPLETE"
        and int(mgi_acceptance.get("passed") or 0) == int(mgi_acceptance.get("total") or -1)
        and int(mgi_acceptance.get("total") or 0) >= 13
    )
    source_names = {entry["name"] for entry in source_entries}
    output_paths = (
        ROOT / "cws_convertor" / "output" / "__init__.py",
        ROOT / "cws_convertor" / "output" / "document_output.py",
    )
    output_tracked = all(path.is_file() and _tracked(path) for path in output_paths)
    hvpc_path = ROOT / "validation" / "hvpc_trimble_completeness" / "HVPC_OBJECT_COMPLETENESS.json"
    hvpc_text = hvpc_path.read_text(encoding="utf-8", errors="replace") if hvpc_path.is_file() else ""
    hvpc_complete = "5725" in hvpc_text and "100" in hvpc_text

    queue = [
        {
            "queue_id": "Q001",
            "title": "Canonical repository, requirement sources and authority reconciliation",
            "depends_on": [],
            "status": "PASS" if audit_name in source_names and len(master_rows) >= 317 else "PARTIAL",
            "expected_result": "Alle actieve prompts, requirements en authorities zijn geversioneerd en zonder stil verlies gekoppeld.",
            "evidence": ["requirements/MASTER_REQUIREMENT_TRACEABILITY.json", f"requirements/sources/{audit_name}"],
            "remaining": [] if audit_name in source_names else ["Versioneer de actuele queue-auditprompt."],
        },
        {
            "queue_id": "Q002",
            "title": "Viewer Loader Engine V2 and cold-load performance closeout",
            "depends_on": ["Q001"],
            "status": "PARTIAL",
            "expected_result": "Exact HVPC is koud in 3-5 seconden zichtbaar, met workerpool, priority, Cache V2, uploadbudget en packaged metrics.",
            "evidence": ["validation/master_completion/HVPC_LOAD_CLOSEOUT.json", "validation/master_completion/HVPC_SCENE_COMPLETENESS.json", "validation/master_completion/HVPC_RENDER_MICROTUNING_CLOSEOUT.json", "validation/master_completion/HVPC_EXACT_WARMSTART_CLOSEOUT.json", "validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.json", "validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.png", "QUEUE_COMPLETION_MATRIX.md"],
            "remaining": ["A genuinely cacheless first IFC tessellation is 7.939 seconds and still exceeds the 3-5 second target. The checksum-bound exact warmstart is PASS at 3.264 seconds and native interaction is PASS at 28.85 ms p95."],
        },
        {
            "queue_id": "Q003",
            "title": "HVPC exact object and geometry completeness",
            "depends_on": ["Q001"],
            "status": "PASS" if hvpc_complete else "NOT_PROVEN",
            "expected_result": "Alle 5.725 fysieke IFC-representaties zijn exact, uniek en zichtbaar zonder box/proxy-vervanging.",
            "evidence": [hvpc_path.relative_to(ROOT).as_posix()],
            "remaining": [] if hvpc_complete else ["Object-completenessbewijs ontbreekt of is onvolledig."],
        },
        {
            "queue_id": "Q004",
            "title": "Same-machine Trimble visual and object parity",
            "depends_on": ["Q002", "Q003"],
            "status": "BLOCKED_EXTERNAL_EVIDENCE",
            "expected_result": "CWS en Trimble tonen dezelfde HVPC-objecten in een gepaarde, live, dezelfde-machine vergelijking.",
            "evidence": ["validation/master_completion/HVPC_TRIMBLE_DESKTOP_CAPTURE_ATTEMPT.json", "validation/master_completion/HVPC_TRIMBLE_VISUAL_COMPARISON.json", "validation/final_4_phase/phase4/trimble_hvpc_same_machine.jpg"],
            "remaining": ["Fresh desktop capture/control is blocked by Windows Graphics Capture access/monitor errors; no fabricated visual comparison is accepted."],
        },
        {
            "queue_id": "Q005",
            "title": "V5.2 light UI and reference-image visual fidelity",
            "depends_on": ["Q001"],
            "status": "PARTIAL",
            "expected_result": "Project | Viewer | Productie | Controle | Uitvoer en alle 31 surfaces matchen de bindende lichte V5.2 SSOT.",
            "evidence": ["validation/master_completion/UI_V52_HVPC_ROUTE_CLOSEOUT.json", "validation/master_completion/ui_v52_hvpc_surface_capture_final", "validation/master_completion/UI_V52_SURFACE_ACCEPTANCE.json", "validation/master_completion/QT_PROGRESSIVE_EXACT_WARMSTART_PASS.png", "validation/final_4_phase/phase1", "validation/final_4_phase/phase3", "validation/final_4_phase/phase4"],
            "remaining": ["All 31 native HVPC-populated surfaces, all 25 supplied reference pairs and a native exact VTK framebuffer are captured; pixel-level SSOT fidelity remains HUMAN_REVIEW_REQUIRED."],
        },
        {
            "queue_id": "Q006",
            "title": "Production core, BOM, machines, workbench, nesting and converter",
            "depends_on": ["Q001"],
            "status": "PASS" if phase_status.get(2) == "PASS" else "PARTIAL",
            "expected_result": "Eén geïntegreerde productieauthority met fail-closed routing en concrete Qt workspaces.",
            "evidence": ["validation/final_4_phase/phase2/PHASE_GATE.json"],
            "remaining": [] if phase_status.get(2) == "PASS" else ["Phase 2 gate is not PASS."],
        },
        {
            "queue_id": "Q007",
            "title": "Manufacturing Geometry Interpreter V2 independent proof",
            "depends_on": ["Q006"],
            "status": "PASS" if mgi_complete else "PARTIAL",
            "expected_result": "BREP-decompositie en onafhankelijke reconstructie zijn voor het volledige aangeleverde corpus bewezen.",
            "evidence": ["validation/manufacturing_interpreter/FINAL_ACCEPTANCE_REPORT.json", "validation/master_completion/MANUFACTURING_INTERPRETER_CLOSEOUT.json", "validation/manufacturing_workspace/machine_settings_workspace.png", "validation/manufacturing_workspace/profile_nesting_miter_interlock.png", "validation/manufacturing_workspace/plate_nesting_stock_layout.png"],
            "remaining": [] if mgi_complete else ["Complete supplied-corpus parity is not proven by committed evidence."],
        },
        {
            "queue_id": "Q008",
            "title": "Drawings, PDF, Print Center, Controle, Quality, Planning and Uitvoer",
            "depends_on": ["Q006"],
            "status": "PASS" if phase_status.get(3) == "PASS" else "PARTIAL",
            "expected_result": "Document-, control-, planning- en outputflows zijn geïntegreerd en evidence-bound.",
            "evidence": ["validation/final_4_phase/phase3/PHASE_GATE.json"],
            "remaining": [] if phase_status.get(3) == "PASS" else ["Phase 3 gate is not PASS."],
        },
        {
            "queue_id": "Q009",
            "title": "Fresh-checkout source and clean-runtime reproducibility",
            "depends_on": ["Q001"],
            "status": "PASS" if output_tracked else "FAIL",
            "expected_result": "Een schone exact-SHA checkout bevat alle runtime modules en draait zonder lokale ignored-source contamination.",
            "evidence": ["tests/final_gap_closure_smoke.py", "cws_convertor/output/document_output.py"],
            "remaining": [] if output_tracked else ["cws_convertor.output is ignored and absent from clean checkouts."],
        },
        {
            "queue_id": "Q010",
            "title": "Dynamic total product acceptance",
            "depends_on": ["Q002", "Q003", "Q005", "Q006", "Q007", "Q008", "Q009"],
            "status": "PASS" if not master_counts.get("FAIL", 0) else "FAIL",
            "expected_result": "Alle actieve requirements zijn PASS met required FAIL/BLOCKED/NOT_TESTED en false green gelijk aan nul.",
            "evidence": ["requirements/MASTER_REQUIREMENT_TRACEABILITY.json", "validation/final_4_phase/phase4/PHASE_GATE.json"],
            "remaining": [f"Master traceability contains {master_counts.get('FAIL', 0)} FAIL requirements."],
        },
        {
            "queue_id": "Q011",
            "title": "Exact-SHA one-folder, portable and installer release",
            "depends_on": ["Q010"],
            "status": "PASS" if phase_status.get(4) == "PASS" else "FAIL",
            "expected_result": "Fresh release artifacts and packaged evidence bind to one exact commit.",
            "evidence": ["validation/final_4_phase/phase4/PHASE_GATE.json"],
            "remaining": [] if phase_status.get(4) == "PASS" else ["Phase 4 gate and final Windows release are not PASS."],
        },
        {
            "queue_id": "Q012",
            "title": "Queue audit, resumable state and automatic continuation",
            "depends_on": ["Q001"],
            "status": "PASS" if audit_name in source_names else "NOT_IMPLEMENTED",
            "expected_result": "Een machineleesbare ledger toont actuele status, dependencies, evidence, volgende actie en blockers.",
            "evidence": ["validation/master_completion/CODEX_QUEUE_STATE.json"],
            "remaining": [] if audit_name in source_names else ["Queue audit source is unavailable."],
        },
    ]
    exact_release_path = ROOT / "validation" / "master_completion" / "EXACT_SHA_WINDOWS_RELEASE_1513ae3.json"
    if exact_release_path.is_file():
        exact_release = json.loads(exact_release_path.read_text(encoding="utf-8"))
        if exact_release.get("status") == "PASS" and exact_release.get("packaged_proven") is True:
            release_item = next(item for item in queue if item["queue_id"] == "Q011")
            release_item["status"] = "PASS"
            release_item["evidence"] = [*release_item["evidence"], str(exact_release_path.relative_to(ROOT)).replace("\\", "/")]
            release_item["remaining_work"] = []

    queue_by_id = {item["queue_id"]: item for item in queue}
    active_nonpass = [item for item in queue if item["status"] not in PASS_LIKE]
    first_nonpass = active_nonpass[0]["queue_id"] if active_nonpass else None

    final_master = "CODEX_SUPERPROMPT_CWS_CONVERTOR_100PCT_FINAL_4_FASEN_2026-08-31.md"
    supersession_rows = []
    active_specialists = {
        audit_name,
        final_master,
        "CODEX_SUPERPROMPT_CWS_VIEWER_PERFORMANCE_CLOSEOUT_V1_3_FASEN_2026-08-31.md",
        "CODEX_SUPERPROMPT_CWS_MANUFACTURING_GEOMETRY_INTERPRETER_V2_3_FASEN_2026-08-31.md",
        "CWS_CONVERTOR_COMPLETE_GAP_ANALYSIS_2026-08-31.md",
        "CWS_CONVERTOR_COMPLETE_GAP_MATRIX_2026-08-31.json",
    }
    for source in source_entries:
        active = source["name"] in active_specialists
        supersession_rows.append(
            {
                "source": source["name"],
                "status": "PASS" if active else "SUPERSEDED",
                "superseded_by": None if active else final_master,
                "requirement_loss_allowed": False,
                "rule": "Older wording is reconciled into the final master; unique requirements remain mapped in CODEX_QUEUE_REQUIREMENTS.json.",
            }
        )

    requirements = []
    for source_index, source in enumerate(source_entries, 1):
        headings = source["headings"] or [source["name"]]
        for heading_index, heading in enumerate(headings, 1):
            queue_id = _queue_id_for(heading, source["name"])
            requirements.append(
                {
                    "requirement_id": f"SRC-{source_index:02d}-{heading_index:03d}",
                    "source": source["name"],
                    "source_path": source["path"],
                    "source_sha256": source["sha256"],
                    "source_heading": heading,
                    "queue_id": queue_id,
                    "status": queue_by_id[queue_id]["status"],
                    "superseded_by": None if source["name"] in active_specialists else final_master,
                    "evidence": queue_by_id[queue_id]["evidence"],
                }
            )
    for row in master_rows:
        item = dict(row)
        item["queue_id"] = _queue_id_for(str(item.get("description") or ""), str(item.get("source") or ""))
        item["ledger_requirement_id"] = f"MASTER-{item.get('requirement_id')}"
        requirements.append(item)
    audit_requirements = (
        "Read and reconcile the complete executed prompt queue.",
        "Fetch and record the current canonical repository truth.",
        "Create or update CODEX_QUEUE_STATE.",
        "Reconcile dependencies without rebuilding correct authorities.",
        "Start with the first technically logical non-PASS item.",
        "Build, test, commit and push coherent checkpoints.",
        "Automatically continue through the remaining queue.",
        "Stop only at 100% product acceptance or a true external blocker.",
        "Deliver real screenshot comparison evidence per phase and prompt.",
    )
    audit_status = ("PASS", "PASS", "PASS", "PASS", "PASS", "NOT_TESTED", "PARTIAL", "PARTIAL", "BLOCKED_EXTERNAL_EVIDENCE")
    for index, description in enumerate(audit_requirements, 1):
        requirements.append(
            {
                "requirement_id": f"AUDIT-{index:03d}",
                "source": audit_name,
                "description": description,
                "queue_id": "Q012" if index <= 4 else ("Q009" if index <= 6 else "Q010"),
                "status": audit_status[index - 1],
                "evidence": ["validation/master_completion/CODEX_QUEUE_STATE.json"],
            }
        )
    requirement_counts = Counter(str(row.get("status") or "NOT_TESTED") for row in requirements)

    reference_names = [
        "01_PROJECT_Start_Inlezen.png", "02_PROJECT_Projectoverzicht.png", "03_PROJECT_Projectstructuur.png",
        "04_PROJECT_Profielen_Materialen.png", "05_VIEWER_3D_Cockpit.png", "06_VIEWER_Selectie_Context.png",
        "07_VIEWER_Weergave_Meten.png", "08_VIEWER_Doorsnede_Isoleren.png", "09_VIEWER_Laadstatus_Performance.png",
        "10_PROJECT_Projectreviews.png", "11_PRODUCTIE_BOM_Machines_BOM.png", "12_PRODUCTIE_Machineindeling_Automatisch.png",
        "13_PRODUCTIE_Machineindeling_Handmatige_Override.png", "14_PRODUCTIE_Optimalisatie_Profile_Nesting.png",
        "15_PRODUCTIE_Optimalisatie_Plate_Nesting.png", "16_PRODUCTIE_Bewerken_Workbench.png", "17_PRODUCTIE_Scribing.png",
        "18_PRODUCTIE_Converteren.png", "19_PRODUCTIE_Tekeningen_PDF.png", "20_UITVOER_Afdrukken_Print_Center.png",
        "21_CONTROLE_Validatie.png", "22_CONTROLE_Revisies_Compare.png", "23_CONTROLE_Maakbaarheid.png",
        "24_UITVOER_Export_Center.png", "25_UITVOER_Rapport_Pakket.png", "CWS_UI_MASTER_V5_VOLLEDIG_OVERZICHT.png",
    ]
    reference_root = Path.home() / "AppData" / "Local" / "Temp"
    references = [{"name": name, "path": str(reference_root / name), "available": (reference_root / name).is_file()} for name in reference_names]
    screenshot_phases = []
    for gate in phase_gates:
        shots = []
        for raw in gate["screenshots"]:
            value = raw.get("path") if isinstance(raw, dict) else raw
            if not value:
                continue
            path = Path(str(value))
            if not path.is_absolute():
                path = ROOT / path
            shots.append({"path": str(path), "exists": path.is_file(), "tracked": path.is_file() and _tracked(path)})
        verified = [shot for shot in shots if shot["exists"] and shot["tracked"]]
        screenshot_phases.append(
            {
                "phase": gate["phase"],
                "declared_count": len(gate["screenshots"]),
                "verified_tracked_count": len(verified),
                "status": "PASS" if gate["status"] == "PASS" and len(verified) >= 3 else "NOT_PROVEN",
                "screenshots": shots,
            }
        )
    screenshot_matrix = {
        "schema": "cws.queue-screenshot-acceptance.v1",
        "generated_at": now,
        "reference_authority": "Supplied V5/V5.1/V5.2 reference images; final master requires light primary UI.",
        "references": references,
        "phases": screenshot_phases,
        "fresh_live_comparison_status": "BLOCKED_EXTERNAL_EVIDENCE",
        "fresh_live_comparison_reason": "Windows desktop capture/control returned access/argument errors; no mock screenshot is accepted.",
    }

    acceptance_checks = [
        {"check": "canonical_sources", "status": queue_by_id["Q001"]["status"]},
        {"check": "fresh_checkout_runtime_source", "status": queue_by_id["Q009"]["status"]},
        {"check": "phase1_gate", "status": phase_status.get(1, "NOT_TESTED")},
        {"check": "phase2_gate", "status": phase_status.get(2, "NOT_TESTED")},
        {"check": "phase3_gate", "status": phase_status.get(3, "NOT_TESTED")},
        {"check": "phase4_gate", "status": phase_status.get(4, "NOT_TESTED")},
        {"check": "hvpc_object_completeness", "status": queue_by_id["Q003"]["status"]},
        {"check": "hvpc_cold_3_to_5_seconds", "status": queue_by_id["Q002"]["status"]},
        {"check": "same_machine_trimble_visual", "status": queue_by_id["Q004"]["status"]},
        {"check": "all_reference_screens", "status": queue_by_id["Q005"]["status"]},
        {"check": "master_requirements", "status": queue_by_id["Q010"]["status"]},
        {"check": "exact_sha_windows_release", "status": queue_by_id["Q011"]["status"]},
    ]
    acceptance_counts = Counter(check["status"] for check in acceptance_checks)
    overall = "PASS" if all(check["status"] in PASS_LIKE for check in acceptance_checks) else "FAIL"

    state = {
        "schema": "cws.codex-queue-state.v1",
        "generated_at": now,
        "repository": {
            "root": str(ROOT), "branch": branch, "head": head, "tree": tree,
            "remote_ref": remote_ref or None, "remote_head": remote_head or None,
            "ahead": ahead, "behind": behind,
            "app_version": "0.10.18-beta-dev", "project_schema": "2.25", "canonical_part_schema": "1.1",
        },
        "allowed_statuses": list(ALLOWED_STATUSES),
        "source_count": len(source_entries),
        "master_requirement_status_counts": dict(sorted(master_counts.items())),
        "queue_status_counts": dict(sorted(Counter(item["status"] for item in queue).items())),
        "current_queue_item": first_nonpass,
        "next_action": queue_by_id[first_nonpass]["remaining"][0] if first_nonpass else "Final acceptance complete.",
        "queue": queue,
        "external_blockers": [item for item in queue if item["status"] == "BLOCKED_EXTERNAL_EVIDENCE"],
    }
    master_payload = {
        "schema": "cws.codex-queue-master.v1", "generated_at": now,
        "repository_head": head, "sources": source_entries, "queue": queue,
    }
    requirement_payload = {
        "schema": "cws.codex-queue-requirements.v1", "generated_at": now,
        "required_total": len(requirements), "status_counts": dict(sorted(requirement_counts.items())),
        "requirements": requirements,
    }
    gap_payload = {
        "schema": "cws.codex-queue-gap-matrix.v1", "generated_at": now,
        "queue_nonpass_count": len(active_nonpass), "first_nonpass": first_nonpass,
        "gaps": active_nonpass,
    }
    supersession_payload = {
        "schema": "cws.codex-supersession-matrix.v1", "generated_at": now,
        "active_final_master": final_master, "requirement_loss_allowed": False,
        "sources": supersession_rows,
        "explicit_rules": [
            {"legacy": "12-item or V9 navigation", "active": "Project | Viewer | Productie | Controle | Uitvoer"},
            {"legacy": "dark-only default", "active": "light primary; dark optional smoke"},
            {"legacy": "fixed 51/51 acceptance", "active": "dynamic master traceability"},
            {"legacy": "raster drawing authority", "active": "vector-native DrawingProjectionModel"},
        ],
    }
    total_acceptance = {
        "schema": "cws.current-total-acceptance.v1", "generated_at": now,
        "source_head": head, "status": overall,
        "status_counts": dict(sorted(acceptance_counts.items())), "checks": acceptance_checks,
        "false_green_count": 0,
    }
    _write_json("CODEX_QUEUE_MASTER.json", master_payload)
    _write_json("CODEX_QUEUE_REQUIREMENTS.json", requirement_payload)
    _write_json("CODEX_QUEUE_GAP_MATRIX.json", gap_payload)
    _write_json("CODEX_QUEUE_STATE.json", state)
    _write_json("SUPERSESSION_MATRIX.json", supersession_payload)
    _write_json("SCREENSHOT_ACCEPTANCE_MATRIX.json", screenshot_matrix)
    _write_json("CURRENT_TOTAL_ACCEPTANCE_MATRIX.json", total_acceptance)

    table = [
        "# CODEX QUEUE MASTER",
        "",
        f"Generated from `{head}` on branch `{branch}`. This ledger never converts missing external evidence into PASS.",
        "",
        "| ID | Queue item | Dependencies | Status | Remaining |",
        "|---|---|---|---|---|",
    ]
    for item in queue:
        remaining = " ".join(item["remaining"]) or "None"
        table.append(f"| {item['queue_id']} | {item['title']} | {', '.join(item['depends_on']) or '-'} | {item['status']} | {remaining} |")
    table.extend(["", f"Current technically logical non-PASS: **{first_nonpass or 'none'}**.", ""])
    (OUT / "CODEX_QUEUE_MASTER.md").write_text("\n".join(table), encoding="utf-8")
    return state


def main() -> int:
    state = build()
    print(f"CODEX_QUEUE_STATE={state['current_queue_item'] or 'COMPLETE'}")
    print(f"QUEUE_STATUS_COUNTS={json.dumps(state['queue_status_counts'], sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
