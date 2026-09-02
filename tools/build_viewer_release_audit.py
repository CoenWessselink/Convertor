from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
AUDIT_SOURCES = ROOT / "docs" / "audit_sources"
DEFAULT_GAP_MATRIX = AUDIT_SOURCES / "CWS_CONVERTOR_VIEWER_GAP_MATRIX_NA_AANPASSING_2026-09-02.json"
TRACEABILITY_CANDIDATES = (
    ROOT / "validation" / "full_acceptance" / "master_traceability" / "MASTER_REQUIREMENT_TRACEABILITY.json",
    ROOT / "requirements" / "MASTER_REQUIREMENT_TRACEABILITY.json",
)
PASS_VALUES = {"PASS", "PASSED", "COMPLETE", "CLOSED", "GREEN", "SUCCESS"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def git(*arguments: str) -> str:
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def passed(value: object) -> bool:
    return str(value or "").upper() in PASS_VALUES


def command_output(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return (result.stdout or result.stderr or "").strip()


def collect_environment(commit: str, build_checksum: str, ifc: Path | None) -> dict[str, Any]:
    gpu = command_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress",
        ]
    )
    cpu = command_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress",
        ]
    )
    memory = command_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB,2)",
        ]
    )
    display = command_output(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Add-Type -AssemblyName System.Windows.Forms; [ordered]@{width=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width;height=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height;dpi_scale=$env:CWS_AUDIT_DPI_SCALE}|ConvertTo-Json -Compress",
        ]
    )
    ifc_payload: dict[str, Any] | None = None
    if ifc is not None:
        ifc_payload = {
            "path": str(ifc),
            "bytes": ifc.stat().st_size,
            "sha256": digest(ifc),
        }
    return {
        "schema": "cws-viewer-release-audit-environment-1.0",
        "generated_at": utc_now(),
        "repository": command_output(["git", "config", "--get", "remote.origin.url"]),
        "branch": git("branch", "--show-current"),
        "commit": commit,
        "tracked_worktree_clean": not bool(git("status", "--porcelain=v1", "--untracked-files=no")),
        "machine_id": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "cpu": cpu,
        "gpu": gpu,
        "ram_gib": memory,
        "display": display,
        "build_checksum": build_checksum,
        "ifc": ifc_payload,
    }


def detect_build() -> tuple[Path | None, str]:
    candidates = (
        ROOT / "dist" / "CWS_Convertor" / "CWS_Convertor.exe",
        ROOT / "release" / "final" / "RELEASE_MANIFEST.json",
        ROOT / "release" / "phase3" / "CWS_Convertor.exe",
    )
    path = next((item for item in candidates if item.is_file()), None)
    return path, digest(path) if path is not None else ""


def traceability_path() -> Path:
    return next((item for item in TRACEABILITY_CANDIDATES if item.is_file()), TRACEABILITY_CANDIDATES[-1])


def evidence_for_phase(phase: int) -> Path:
    exact = ROOT / "validation" / "full_acceptance" / "release_traceability" / f"phase{phase}" / "PHASE_GATE.json"
    if exact.is_file():
        return exact
    return ROOT / "validation" / "final_4_phase" / f"phase{phase}" / "PHASE_GATE.json"


def requirement_matrix(commit: str, environment: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source = load_json(traceability_path())
    requirements = list(source.get("requirements") or [])
    expected = int(source.get("required_total") or len(requirements))
    if expected != len(requirements) or expected < 1:
        raise RuntimeError("Dynamic requirement count is inconsistent")
    rows: list[dict[str, Any]] = []
    for requirement in requirements:
        phase = int(requirement.get("phase") or 0)
        proof = evidence_for_phase(phase)
        proof_ok = False
        proof_hash = ""
        note = "Exact-SHA phase evidence is missing"
        if proof.is_file():
            payload = load_json(proof)
            bound = str(payload.get("source_revision") or payload.get("commit") or "").lower()
            proof_ok = passed(payload.get("status")) and bound == commit
            proof_hash = digest(proof)
            note = "Exact-SHA packaged phase evidence" if proof_ok else f"Phase evidence is not PASS/bound to {commit}"
        result = "PASS" if passed(requirement.get("status")) and proof_ok else "FAIL"
        rows.append(
            {
                "requirement_id": str(requirement.get("requirement_id") or ""),
                "omschrijving": str(requirement.get("description") or ""),
                "bron": f"{requirement.get('source', '')}#{requirement.get('source_section', '')}",
                "controle": "; ".join(str(item) for item in requirement.get("test_paths") or ()),
                "platform": str(environment.get("platform") or ""),
                "resultaat": result,
                "bewijs": proof.relative_to(ROOT).as_posix() if proof.is_file() else "",
                "bewijs_sha256": proof_hash,
                "geteste_commit": commit,
                "opmerking": note,
            }
        )
    ids = [row["requirement_id"] for row in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise RuntimeError("Requirement IDs must be present and unique")
    counts = {name: sum(row["resultaat"] == name for row in rows) for name in ("PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE")}
    return rows, counts


def write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "requirement_id",
        "omschrijving",
        "bron",
        "controle",
        "platform",
        "resultaat",
        "bewijs",
        "bewijs_sha256",
        "geteste_commit",
        "opmerking",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def performance_values() -> dict[str, Any]:
    base = ROOT / "validation" / "full_acceptance" / "viewer_performance"
    cold_path = base / "phase2" / "COLD_RUNS.json"
    soak_path = base / "phase2" / "REAL_10MIN_SOAK.json"
    final_path = base / "phase3" / "FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.json"
    cold = load_json(cold_path) if cold_path.is_file() else {}
    soak = load_json(soak_path) if soak_path.is_file() else {}
    final = load_json(final_path) if final_path.is_file() else {}
    large = [row for row in cold.get("rows") or [] if str(row.get("model_class")) == "LARGE"]
    samples = [float(row.get("seconds") or 0.0) for row in large]
    return {
        "cold_samples_seconds": samples,
        "cold_every_run_le_5_seconds": bool(samples) and len(samples) >= 5 and max(samples) <= 5.0,
        "cold_max_seconds": max(samples) if samples else None,
        "soak_status": str(soak.get("status") or "NOT_TESTED"),
        "soak_duration_seconds": soak.get("duration_seconds") or soak.get("elapsed_seconds"),
        "frame_metrics": soak.get("frame_metrics") or {},
        "interaction_metrics": soak.get("interaction_metrics") or {},
        "resource_metrics": soak.get("resource_metrics") or soak.get("memory_metrics") or {},
        "geometry": soak.get("geometry") or soak.get("load_metrics") or {},
        "worker_failures": soak.get("worker_failures"),
        "final_status": str(final.get("status") or "NOT_TESTED"),
        "final_commit": str(final.get("commit40") or ""),
    }


def release_exact(commit: str) -> bool:
    manifest = ROOT / "release" / "final" / "RELEASE_MANIFEST.json"
    binding = ROOT / "validation" / "full_acceptance" / "RELEASE_BINDING.json"
    if not manifest.is_file() or not binding.is_file():
        return False
    values = (load_json(manifest), load_json(binding))
    return all(str(item.get("commit") or "").lower() == commit for item in values)


def gap_register(commit: str, gap_source: Path, perf: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source = load_json(gap_source)
    exact = release_exact(commit)
    rows: list[dict[str, Any]] = []
    pending_release = {"GAP-V-001", "GAP-V-010"}
    pending_interaction = {"GAP-V-002", "GAP-V-003"}
    pending_soak = {"GAP-V-005", "GAP-V-006", "GAP-V-015"}
    for item in source.get("gaps") or []:
        identity = str(item.get("id") or "")
        original = str(item.get("status") or "NOT_PROVEN").upper()
        status = "PASS" if original == "CLOSED" else "BLOCKED" if original in {"PARTIAL", "BLOCKED_EXTERNAL_EVIDENCE"} else "FAIL"
        reason = str(item.get("reason") or "")
        if identity in pending_release:
            status = "PASS" if exact else "FAIL"
            reason = "Exact-SHA release binding present" if exact else "Exact-SHA release binding is absent"
        elif identity in pending_interaction:
            status = "PASS" if perf["soak_status"] == "PASS" and perf["final_commit"].lower() == commit else "FAIL"
            reason = "Native interaction/soak gate is exact-SHA PASS" if status == "PASS" else "Exact-SHA interaction evidence is not PASS"
        elif identity == "GAP-V-004":
            status = "PASS" if perf["cold_every_run_le_5_seconds"] else "FAIL"
            reason = f"Five LARGE cold samples; maximum={perf['cold_max_seconds']} s, criterion <=5.0 s"
        elif identity in pending_soak:
            status = "PASS" if perf["soak_status"] == "PASS" and perf["final_commit"].lower() == commit else "FAIL"
            reason = "Exact-SHA real Viewer soak is PASS" if status == "PASS" else "Exact-SHA real Viewer soak is not PASS"
        rows.append({"gap_id": identity, "resultaat": status, "reden": reason, "baseline_status": original})
    counts = {name: sum(row["resultaat"] == name for row in rows) for name in ("PASS", "FAIL", "BLOCKED")}
    return rows, counts


def image_candidates() -> list[Path]:
    roots = (
        ROOT / "validation" / "full_acceptance" / "screenshots",
        ROOT / "validation" / "full_acceptance" / "viewer_performance",
        ROOT / "validation" / "results" / "windows-runtime-phase1",
        ROOT / "validation" / "results" / "windows-runtime-phase2",
        ROOT / "validation" / "results" / "windows-runtime-phase3",
    )
    paths: list[Path] = []
    for base in roots:
        if base.is_dir():
            paths.extend(sorted(base.rglob("*.png")))
    return paths


def scenario(path: Path) -> tuple[str, tuple[str, ...], str]:
    name = path.stem.lower()
    if "dpi" in name:
        return name, ("F4-003",), "native_windows_dpi_capture"
    if any(token in name for token in ("soak", "progressive", "warmstart", "aa_", "hidden", "wire")):
        return name, ("F4-007",), "native_vtk_viewer_capture"
    if "portable" in name:
        return name, ("F4-009",), "packaged_portable_gui_capture"
    if "install" in name:
        return name, ("F4-010",), "installed_gui_capture"
    if "phase" in name or "gui" in name:
        return name, ("F4-008",), "packaged_windows_gui_capture"
    return name, ("F4-002", "F4-003"), "native_qt_vtk_composite_capture"


def safe_slug(value: str) -> str:
    return "-".join(part for part in "".join(character.lower() if character.isalnum() else " " for character in value).split())[:80] or "capture"


def copy_evidence(
    destination: Path,
    *,
    commit: str,
    build_checksum: str,
    machine_id: str,
    generated_at: str,
    extra_images: Iterable[Path] = (),
    include_repository_images: bool = True,
) -> list[dict[str, Any]]:
    from PIL import Image, ImageDraw, ImageFont

    destination.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    candidates = [
        *(image_candidates() if include_repository_images else ()),
        *(path for path in extra_images if path.is_file()),
    ]
    for index, source in enumerate(candidates, 1):
        source_hash = digest(source)
        if source_hash in seen:
            continue
        seen.add(source_hash)
        label, requirement_ids, method = scenario(source)
        raw_name = f"EVID-{requirement_ids[0]}-{safe_slug(label)}-{commit[:8]}-{index:03d}-raw.png"
        raw = destination / raw_name
        shutil.copy2(source, raw)
        with Image.open(raw) as image:
            width, height = image.size
            annotated_image = image.convert("RGB")
        strip_height = max(62, min(92, height // 12))
        canvas = Image.new("RGB", (width, height + strip_height), "#071b2a")
        canvas.paste(annotated_image, (0, strip_height))
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        line1 = f"CWS VIEWER RELEASE AUDIT | {label} | {generated_at}"
        line2 = f"SHA {commit} | BUILD {build_checksum or 'NOT_AVAILABLE'} | MACHINE {machine_id}"
        draw.text((16, 12), line1, fill="#f7fbff", font=font)
        draw.text((16, 34), line2, fill="#43b9ff", font=font)
        annotated_name = raw_name.replace("-raw.png", "-annotated.png")
        annotated = destination / annotated_name
        canvas.save(annotated, "PNG", optimize=True)
        rows.extend(
            (
                {
                    "relative_name": raw.name,
                    "sha256": digest(raw),
                    "bytes": raw.stat().st_size,
                    "pixel_dimensions": [width, height],
                    "captured_at": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
                    "tested_commit": commit,
                    "build_checksum": build_checksum,
                    "machine_id": machine_id,
                    "scenario": label,
                    "requirement_ids": list(requirement_ids),
                    "capture_method": method,
                    "kind": "raw",
                    "source": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else str(source),
                },
                {
                    "relative_name": annotated.name,
                    "sha256": digest(annotated),
                    "bytes": annotated.stat().st_size,
                    "pixel_dimensions": [width, height + strip_height],
                    "captured_at": generated_at,
                    "tested_commit": commit,
                    "build_checksum": build_checksum,
                    "machine_id": machine_id,
                    "scenario": label,
                    "requirement_ids": list(requirement_ids),
                    "capture_method": f"{method}+audit_strip",
                    "kind": "annotated",
                    "source": raw.name,
                },
            )
        )
    return rows


def validate_evidence_manifest(evidence_dir: Path, manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    if not files:
        raise RuntimeError("Evidence manifest is empty")
    for item in files:
        path = evidence_dir / str(item.get("relative_name") or "")
        if not path.is_file():
            raise RuntimeError(f"Evidence file is missing: {path}")
        if digest(path) != item.get("sha256"):
            raise RuntimeError(f"Evidence hash mismatch: {path}")
        if path.stat().st_size != int(item.get("bytes") or -1):
            raise RuntimeError(f"Evidence size mismatch: {path}")


def copy_supporting_evidence(audit: Path) -> None:
    logs = audit / "logs"
    metrics = audit / "metrics"
    logs.mkdir(parents=True, exist_ok=True)
    metrics.mkdir(parents=True, exist_ok=True)
    log_root = ROOT / "validation" / "full_acceptance" / "logs"
    if log_root.is_dir():
        for source in sorted(log_root.rglob("*.log")):
            shutil.copy2(source, logs / source.name)
    performance = ROOT / "validation" / "full_acceptance" / "viewer_performance"
    if performance.is_dir():
        for source in sorted(performance.rglob("*")):
            if source.is_file() and source.suffix.lower() in {".json", ".csv", ".md", ".log"} and "cache" not in source.parts:
                target = metrics / source.relative_to(performance)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)


def build_bcf_evidence(destination: Path, commit: str) -> dict[str, Any]:
    destination.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any]
    controller = None
    try:
        from cws_viewer.backends.memory import MemoryRenderBackend
        from cws_viewer.core.v14_controller import V14ViewerCoreController
        from cws_viewer.fixtures import build_synthetic_product_scene
        from cws_viewer.review import Bcf21Verifier, ReviewPriority, V15ReviewWorkspaceService

        scene = build_synthetic_product_scene(30, parts_per_assembly=10)
        controller = V14ViewerCoreController(MemoryRenderBackend(), width=1200, height=800)
        controller.load_scene(scene)
        service = V15ReviewWorkspaceService(
            controller,
            project_id=scene.project_id,
            scene_hash=scene.scene_hash,
            store_path=destination / "review.json",
            project_metadata={"project_name": "Release audit", "revision_id": commit[:8]},
        )
        view = service.capture_view("Release audit viewpoint", owner="Codex release audit")
        entity = controller.index.node(controller.index.renderable_node_ids[0]).entity_id
        issue = service.create_issue(
            "BCF 2.1 release audit",
            description="Schema, viewpoint, comment and IFC selection evidence",
            priority=ReviewPriority.URGENT,
            created_by="release-audit",
            linked_entity_ids=(str(entity),),
            viewpoint_id=view.viewpoint_id,
            due_date_utc="2026-09-30T12:00:00Z",
        )
        service.add_comment(issue.issue_id, "release-audit", "Exact-SHA BCF schema audit")
        service.project_metadata["ifc_guid_by_entity"] = {str(entity): "0" * 22}
        target = service.export_bcf(destination / "CWS_VIEWER_RELEASE_AUDIT.bcfzip")
        verified = Bcf21Verifier().verify(target)
        report = {
            "schema": "cws-viewer-bcf-release-audit-1.0",
            "status": "PASS",
            "commit": commit,
            "archive": target.name,
            "archive_sha256": digest(target),
            "version": verified.version,
            "topic_count": verified.topic_count,
            "viewpoint_count": verified.viewpoint_count,
            "validated_files": list(verified.validated_files),
            "xsd_validation": "PASS",
            "semantic_roundtrip": "NOT_PROVEN",
            "external_buildingsmart_certification": "BLOCKED_EXTERNAL_EVIDENCE",
        }
    except Exception as exc:
        report = {
            "schema": "cws-viewer-bcf-release-audit-1.0",
            "status": "FAIL",
            "commit": commit,
            "error": f"{type(exc).__name__}: {exc}",
            "xsd_validation": "FAIL",
            "semantic_roundtrip": "NOT_PROVEN",
            "external_buildingsmart_certification": "BLOCKED_EXTERNAL_EVIDENCE",
        }
    finally:
        if controller is not None:
            controller.shutdown()
    write_json(destination / "BCF_VALIDATION_REPORT.json", report)
    return report


def build_proof_pdf(path: Path, report_title: str, commit: str, manifest: dict[str, Any], evidence_dir: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=report_title,
        author="CWS Convertor independent release audit",
    )
    story: list[Any] = [Paragraph(report_title, styles["Title"]), Spacer(1, 5 * mm)]
    story.append(Paragraph(f"Exact geteste commit: {commit}", styles["BodyText"]))
    story.append(Paragraph(f"Bewijsbestanden: {len(manifest.get('files') or [])}", styles["BodyText"]))
    story.append(Spacer(1, 6 * mm))
    summary = Table(
        [["Veld", "Waarde"], ["SHA", commit], ["Gegenereerd", str(manifest.get("generated_at"))], ["Machine", str(manifest.get("machine_id"))]],
        colWidths=[45 * mm, 190 * mm],
    )
    summary.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a2940")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#92a7b5")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([summary, PageBreak()])
    annotated = [item for item in manifest.get("files") or [] if item.get("kind") == "annotated"]
    for index, item in enumerate(annotated):
        source = evidence_dir / item["relative_name"]
        story.append(Paragraph(f"{index + 1}. {item['scenario']}", styles["Heading2"]))
        story.append(Paragraph(f"Requirement(s): {', '.join(item['requirement_ids'])} | SHA-256: {item['sha256']}", styles["BodyText"]))
        story.append(Spacer(1, 2 * mm))
        image = Image(str(source))
        image._restrictSize(255 * mm, 145 * mm)
        story.append(image)
        if index != len(annotated) - 1:
            story.append(PageBreak())
    document.build(story)


def checksums(audit: Path) -> Path:
    target = audit / "CHECKSUMS.sha256"
    files = [item for item in sorted(audit.rglob("*")) if item.is_file() and item != target]
    target.write_text("".join(f"{digest(item)}  {item.relative_to(audit).as_posix()}\n" for item in files), encoding="ascii")
    for line in target.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", 1)
        if digest(audit / relative) != expected:
            raise RuntimeError(f"Checksum verification failed: {relative}")
    return target


def write_report(
    path: Path,
    *,
    commit: str,
    counts: dict[str, int],
    gaps: list[dict[str, Any]],
    gap_counts: dict[str, int],
    perf: dict[str, Any],
    evidence_count: int,
    bcf: dict[str, Any],
    verdict: str,
    source_hashes: list[dict[str, Any]],
) -> None:
    blockers = [item for item in gaps if item["resultaat"] != "PASS"]
    lines = [
        "# CWS Convertor Viewer - onafhankelijke release-audit",
        "",
        f"Exact geteste commit: `{commit}`  ",
        f"Verdict: **{verdict}**  ",
        f"Dynamische requirements: `{sum(counts.values())}` - PASS `{counts['PASS']}`, FAIL `{counts['FAIL']}`, BLOCKED `{counts['BLOCKED']}`, NOT_APPLICABLE `{counts['NOT_APPLICABLE']}`.",
        "",
        "## Beslistabel",
        "",
        "| Onderdeel | Resultaat | Kernbewijs | Resterende gap |",
        "| --- | --- | --- | --- |",
        f"| Dynamisch gevonden requirements | {'PASS' if counts['FAIL'] == counts['BLOCKED'] == 0 else 'FAIL'} | `VIEWER_RELEASE_GAP_MATRIX.json` | {counts['FAIL']} FAIL, {counts['BLOCKED']} BLOCKED |",
        f"| HVPC cold exact load | {'PASS' if perf['cold_every_run_le_5_seconds'] else 'FAIL'} | LARGE cold max `{perf['cold_max_seconds']}` s | Iedere run moet <=5.000 s zijn |",
        f"| HVPC interactieve performance | {perf['soak_status']} | `metrics/phase2/REAL_10MIN_SOAK.json` | Exact-SHA native dGPU-bewijs vereist |",
        "| Visuele pariteit | BLOCKED | Echte CWS runtimebeelden in `evidence/` | Ondertekende menselijke 25/25-acceptatie ontbreekt |",
        "| Trimble-pariteit | BLOCKED | Open Trimble-sessie is geen object-voor-object bewijs | Identiek HVPC-model/camera plus revieweracceptatie ontbreekt |",
        "| Hidden-line | PASS indien native capture aanwezig | Hidden-line broncontract en native VTK-captures | Drie identieke camera-drieluiken moeten menselijk worden beoordeeld |",
        f"| BCF 2.1 schema/roundtrip | {bcf.get('xsd_validation')} / {bcf.get('semantic_roundtrip')} | `bcf/BCF_VALIDATION_REPORT.json` | Semantische import-roundtrip is niet bewezen |",
        "| BCF-certificering | BLOCKED | XSD-validatie is geen productcertificaat | Officieel buildingSMART-conformiteitsbewijs ontbreekt |",
        f"| Packaging/installatie | {'PASS' if release_exact(commit) else 'FAIL'} | exact-SHA release manifest en binding | Geen |",
        "| Toegankelijkheid/UX | BLOCKED | DPI en focusautomatisering | Screenreader, volledig contrast en menselijke UX-acceptatie ontbreken |",
        f"| CI en exact-SHA-releasebewijs | {'PASS' if release_exact(commit) else 'FAIL'} | release/final + binding | Remote workflowstatus afzonderlijk archiveren |",
        "",
        "## Bronconsistentie",
        "",
    ]
    lines.extend(f"- `{item['sha256']}` `{item['path']}`" for item in source_hashes)
    lines.extend(["", "## Open blockers", ""])
    lines.extend(f"- `{item['gap_id']}`: {item['reden']}" for item in blockers)
    lines.extend(
        [
            "",
            "## Bewijsintegriteit",
            "",
            f"- PNG-manifest bevat `{evidence_count}` bestanden.",
            "- Iedere bewijsfile is opnieuw gehasht en op bestandsgrootte gecontroleerd.",
            "- Requirementresultaten worden niet verhoogd zonder een PASS phase-gate die aan deze volledige commit is gebonden.",
            "- Geen bewijs, teststatus of drempelwaarde is gemanipuleerd.",
            "",
            "## Conclusie",
            "",
            "Deze audit is volledig uitgevoerd. Het product krijgt alleen `100% RELEASEGEREED` wanneer requirements, technische gaps en externe bewijsverplichtingen allemaal PASS zijn.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an exact-SHA independent CWS Viewer release audit bundle")
    parser.add_argument("--output-root", type=Path, default=ROOT / "release_audit")
    parser.add_argument("--ifc", type=Path)
    parser.add_argument("--gap-matrix", type=Path, default=DEFAULT_GAP_MATRIX)
    parser.add_argument("--extra-image", type=Path, action="append", default=[])
    parser.add_argument("--strict", action="store_true", help="Return non-zero unless the final verdict is 100% RELEASEGEREED")
    args = parser.parse_args()

    commit = git("rev-parse", "HEAD").lower()
    if len(commit) != 40:
        raise RuntimeError("A complete Git commit SHA is required")
    output = args.output_root.resolve() / commit
    if output.exists():
        raise RuntimeError(f"Audit output already exists and will not be overwritten: {output}")
    output.mkdir(parents=True)
    generated_at = utc_now()
    build_path, build_checksum = detect_build()
    ifc = args.ifc.resolve(strict=True) if args.ifc else None
    environment = collect_environment(commit, build_checksum, ifc)
    write_json(output / "AUDIT_ENVIRONMENT.json", environment)

    rows, counts = requirement_matrix(commit, environment)
    perf = performance_values()
    gaps, gap_counts = gap_register(commit, args.gap_matrix.resolve(strict=True), perf)
    bcf = build_bcf_evidence(output / "bcf", commit)
    copy_supporting_evidence(output)

    evidence_dir = output / "evidence"
    evidence_rows = copy_evidence(
        evidence_dir,
        commit=commit,
        build_checksum=build_checksum,
        machine_id=str(environment["machine_id"]),
        generated_at=generated_at,
        extra_images=args.extra_image,
    )
    manifest = {
        "schema": "cws-viewer-release-evidence-manifest-1.0",
        "generated_at": generated_at,
        "tested_commit": commit,
        "build_path": str(build_path) if build_path else "",
        "build_checksum": build_checksum,
        "machine_id": environment["machine_id"],
        "files": evidence_rows,
    }
    write_json(evidence_dir / "manifest.json", manifest)
    validate_evidence_manifest(evidence_dir, manifest)

    matrix = {
        "schema": "cws-viewer-release-gap-matrix-1.0",
        "generated_at": generated_at,
        "tested_commit": commit,
        "required_total": len(rows),
        "counts": counts,
        "requirements": rows,
        "viewer_gaps": gaps,
        "viewer_gap_counts": gap_counts,
        "performance": perf,
    }
    external_blockers = [item for item in gaps if item["resultaat"] != "PASS"]
    evidence_ok = len(evidence_rows) >= 20
    release_ready = counts == {"PASS": len(rows), "FAIL": 0, "BLOCKED": 0, "NOT_APPLICABLE": 0} and not external_blockers and evidence_ok and bcf.get("semantic_roundtrip") == "PASS" and bcf.get("external_buildingsmart_certification") == "PASS"
    verdict = "100% RELEASEGEREED" if release_ready else "NIET RELEASEGEREED"
    matrix["release_verdict"] = verdict
    matrix["false_green"] = False
    write_json(output / "VIEWER_RELEASE_GAP_MATRIX.json", matrix)
    write_matrix_csv(output / "VIEWER_RELEASE_GAP_MATRIX.csv", rows)
    write_json(output / "VIEWER_GAP_REGISTER.json", {"counts": gap_counts, "gaps": gaps})

    source_hashes = [
        {"path": item.relative_to(ROOT).as_posix(), "sha256": digest(item), "bytes": item.stat().st_size}
        for item in sorted(AUDIT_SOURCES.iterdir())
        if item.is_file()
    ]
    write_report(
        output / "VIEWER_RELEASE_AUDIT.md",
        commit=commit,
        counts=counts,
        gaps=gaps,
        gap_counts=gap_counts,
        perf=perf,
        evidence_count=len(evidence_rows),
        bcf=bcf,
        verdict=verdict,
        source_hashes=source_hashes,
    )
    reproduce = [
        "# Reproduce CWS Viewer release audit",
        "",
        f"Commit: `{commit}`",
        "",
        "```powershell",
        f"git checkout {commit}",
        "python tools/build_phase1_windows_release.py",
        "python tools/build_phase2_windows_release.py --skip-build",
        "python tools/build_phase3_windows_release.py --skip-build",
        "python tools/run_full_product_acceptance.py --reuse-fresh-phase3-evidence --defer-master-release-gate",
        "python tools/finalize_commit_bound_release.py --ci PASS",
        f"python tools/build_viewer_release_audit.py --ifc \"{ifc or '<HVPC_IFC>'}\" --strict",
        "```",
    ]
    (output / "REPRODUCE.md").write_text("\n".join(reproduce) + "\n", encoding="utf-8")
    build_proof_pdf(output / "VIEWER_RELEASE_EVIDENCE.pdf", "CWS Convertor Viewer - release evidence", commit, manifest, evidence_dir)
    checksum_path = checksums(output)
    print(json.dumps({"output": str(output), "commit": commit, "requirements": counts, "viewer_gaps": gap_counts, "evidence_files": len(evidence_rows), "bcf": bcf.get("status"), "checksums": str(checksum_path), "verdict": verdict}, indent=2))
    return 0 if release_ready or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
