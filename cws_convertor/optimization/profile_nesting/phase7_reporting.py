"""Traceable phase-7 reports and neutral job packages for profile nesting.

All artefacts are review/production-planning artefacts.  This module never
creates proprietary controller code and never transmits a job to a machine.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import shutil
import stat
import tempfile
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import xlsxwriter
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from cws_convertor.product import APP_NAME, APP_VERSION
from .bar_visualization import build_bar_scene, piece_display_color, scene_to_svg
from cws_convertor.project.model import ProjectModel, stable_sha256, utc_now_iso
from cws_convertor.production_export.utils import (
    atomic_directory,
    atomic_write,
    canonical_json_bytes,
    safe_filename,
    sha256_file,
)

PACKAGE_FORMAT = "CWS_PROFILE_NESTING_PACKAGE_V1"
NEUTRAL_JOB_FORMAT = "CWS_NEUTRAL_PROFILE_CUT_JOB_V1"
REPORT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ReleasePackageLimits:
    """Resource limits for release package verification/extraction.

    Defaults are intentionally far above normal Profile Nesting packages but
    prevent ZIP bombs, pathological file counts and unexpectedly large payloads.
    """
    max_entries: int = 4096
    max_total_uncompressed_bytes: int = 2 * 1024 * 1024 * 1024
    max_single_file_bytes: int = 512 * 1024 * 1024
    max_compression_ratio: float = 500.0
    max_path_length: int = 1024
    max_manifest_artifacts: int = 4096


DEFAULT_RELEASE_PACKAGE_LIMITS = ReleasePackageLimits()


@dataclass
class NestingOutputArtifact:
    artifact_id: str
    format: str
    relative_path: str
    sha256: str
    size_bytes: int
    media_type: str
    run_id: str
    plan_hash: str
    input_snapshot_hash: str
    released: bool = False
    traceability: dict[str, Any] = field(default_factory=dict)
    artifact_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("artifact_hash", None)
        self.artifact_hash = stable_sha256(payload)
        return self.artifact_hash


@dataclass
class NestingPackageResult:
    root: Path
    zip_path: Path
    manifest: dict[str, Any]
    artifacts: list[NestingOutputArtifact]


def _units_to_mm(value: Any, snapshot: dict[str, Any]) -> float:
    units = dict(snapshot.get("units") or {})
    factor = int(units.get("units_per_mm") or 1000)
    return float(value or 0) / max(1, factor)


def _demand_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(x.get("demand_line_id") or ""): dict(x) for x in list(snapshot.get("demand_lines") or [])}


def _piece_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(x.get("instance_id") or ""): dict(x) for x in list(snapshot.get("piece_instances") or [])}


def _bar_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    plan = dict(record.get("plan") or {})
    snapshot = dict(record.get("input_snapshot") or {})
    stock_candidates = {
        str(x.get("candidate_id") or ""): dict(x)
        for x in list(dict(snapshot.get("stock_snapshot") or {}).get("candidates") or [])
    }
    result: list[dict[str, Any]] = []
    for raw in list(plan.get("bars") or []):
        bar = dict(raw)
        candidate = stock_candidates.get(str(bar.get("candidate_id") or ""), {})
        result.append({
            "bar_id": bar.get("bar_id", ""),
            "source_type": bar.get("source_type", ""),
            "source_id": bar.get("source_id", ""),
            "candidate_id": bar.get("candidate_id", ""),
            "stock_length_mm": _units_to_mm(bar.get("stock_length_units"), snapshot),
            "profile_id": candidate.get("profile_id", ""),
            "material": candidate.get("material", ""),
            "grade": candidate.get("material_grade", ""),
            "heat": candidate.get("heat", ""),
            "batch": candidate.get("batch", ""),
            "certificate": candidate.get("certificate", ""),
            "supplier": candidate.get("supplier", ""),
            "location": candidate.get("location", ""),
            "machine_id": bar.get("machine_id", ""),
            "machine_profile_id": bar.get("machine_profile_id", ""),
            "piece_count": len(list(bar.get("placements") or [])),
            "cut_count": int(bar.get("cut_count") or 0),
            "common_cut_count": int(bar.get("common_cut_count") or 0),
            "nominal_sum_mm": _units_to_mm(bar.get("nominal_sum_units"), snapshot),
            "occupied_span_mm": _units_to_mm(bar.get("occupied_span_units"), snapshot),
            "projected_kerf_mm": _units_to_mm(bar.get("projected_kerf_units"), snapshot),
            "head_trim_mm": _units_to_mm(bar.get("head_trim_units"), snapshot),
            "tail_trim_mm": _units_to_mm(bar.get("tail_trim_units"), snapshot),
            "reusable_remnant_mm": _units_to_mm(bar.get("reusable_remnant_units"), snapshot),
            "waste_mm": _units_to_mm(bar.get("waste_units"), snapshot),
            "transition_effect_mm": _units_to_mm(bar.get("transition_effect_units"), snapshot),
            "unit_price": float(candidate.get("unit_price") or 0.0),
            "total_cost": float(bar.get("total_cost_micros") or 0) / 1_000_000.0,
            "bar_hash": bar.get("bar_hash", ""),
        })
    return result


def _cut_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    plan = dict(record.get("plan") or {})
    snapshot = dict(record.get("input_snapshot") or {})
    demand = _demand_map(snapshot)
    pieces = _piece_map(snapshot)
    result: list[dict[str, Any]] = []
    for raw_bar in list(plan.get("bars") or []):
        bar = dict(raw_bar)
        transitions = {str(x.get("transition_id") or ""): dict(x) for x in list(bar.get("transitions") or [])}
        for raw in sorted(list(bar.get("placements") or []), key=lambda x: int(dict(x).get("sequence_index") or 0)):
            p = dict(raw)
            inst = pieces.get(str(p.get("instance_id") or ""), {})
            line = demand.get(str(p.get("demand_line_id") or ""), {})
            trans = transitions.get(str(p.get("transition_before_id") or ""), {})
            result.append({
                "bar_id": bar.get("bar_id", ""),
                "sequence": int(p.get("sequence_index") or 0) + 1,
                "instance_id": p.get("instance_id", ""),
                "part_id": p.get("part_id", ""),
                "part_position": p.get("part_position", "") or inst.get("part_position", ""),
                "assembly_marks": ",".join(line.get("assembly_marks") or inst.get("assembly_context") or []),
                "profile": line.get("profile_name", ""),
                "material": line.get("material", ""),
                "grade": line.get("material_grade", ""),
                "production_batch": line.get("production_batch", "") or inst.get("production_batch", ""),
                "heat_requirement": line.get("heat_requirement", ""),
                "certificate_requirement": line.get("certificate_requirement", ""),
                "quantity_ordinal": int(inst.get("quantity_ordinal") or 0),
                "nominal_length_mm": _units_to_mm(p.get("length_units"), snapshot),
                "reference_start_mm": _units_to_mm(p.get("reference_start_units"), snapshot),
                "reference_end_mm": _units_to_mm(p.get("reference_end_units"), snapshot),
                "cut_position_mm": _units_to_mm(p.get("cut_position_units"), snapshot),
                "orientation_id": p.get("orientation_id", ""),
                "machine_id": p.get("machine_id", ""),
                "common_cut_before": bool(trans.get("common_cut")) if trans else False,
                "start_angle_deg": float(dict(line.get("start_cut") or {}).get("primary_angle_deg") or 0.0),
                "start_secondary_angle_deg": float(dict(line.get("start_cut") or {}).get("secondary_angle_deg") or 0.0),
                "end_angle_deg": float(dict(line.get("end_cut") or {}).get("primary_angle_deg") or 0.0),
                "end_secondary_angle_deg": float(dict(line.get("end_cut") or {}).get("secondary_angle_deg") or 0.0),
                "transition_id": trans.get("transition_id", ""),
                "transition_kerf_mm": _units_to_mm(trans.get("kerf_projection_units"), snapshot) if trans else 0.0,
                "transition_gap_mm": _units_to_mm(trans.get("required_reference_gap_units"), snapshot) if trans else 0.0,
                "start_cut_hash": p.get("start_cut_hash", ""),
                "end_cut_hash": p.get("end_cut_hash", ""),
                "manufacturing_hash": p.get("manufacturing_hash", ""),
            })
    return result


def build_release_report(project: ProjectModel, record: dict[str, Any], *, release_id: str, released_at: str, released_by: str) -> dict[str, Any]:
    run=dict(record.get("run") or {}); snapshot=dict(record.get("input_snapshot") or {}); plan=dict(record.get("plan") or {}); evidence=dict(record.get("solver_evidence") or {}); validation=dict(record.get("validation_report") or {})
    balance=dict(plan.get("material_balance") or {}); objective=dict(plan.get("objective") or {}); bars=_bar_rows(record)
    # Aggregate equal profile/material demand groups rather than reporting only
    # the first line of a group.  This keeps the release report quantity totals
    # equal to the immutable demand snapshot when a project contains multiple
    # production lines for the same section/material identity.
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for line in list(snapshot.get("demand_lines") or []):
        item={"profile":line.get("profile_name",""),"profile_id":line.get("profile_id",""),"section_hash":line.get("section_hash",""),"material":line.get("material",""),"grade":line.get("material_grade",""),"quantity":int(line.get("quantity") or 0)}
        key=(str(item["profile_id"]),str(item["section_hash"]),str(item["material"]),str(item["grade"]))
        if key not in grouped:
            grouped[key]=item
        else:
            grouped[key]["quantity"]=int(grouped[key].get("quantity") or 0)+int(item["quantity"] or 0)
    profile_material=[grouped[key] for key in sorted(grouped)]
    used_stock=[{"bar_id":b["bar_id"],"source_type":b["source_type"],"source_id":b["source_id"],"candidate_id":b["candidate_id"],"stock_length_mm":b["stock_length_mm"],"machine_id":b["machine_id"],"machine_profile_id":b["machine_profile_id"]} for b in bars]
    payload={
        "schema_version":REPORT_SCHEMA_VERSION,"product":APP_NAME,"product_version":APP_VERSION,"project_id":project.project_id,"project_name":project.project_name,"run_id":run.get("run_id"),"release_id":release_id,"release_status":"released","released_at":released_at,"released_by":released_by,
        "scenario":{"id":run.get("scenario_id"),"family":run.get("scenario_family"),"mode":run.get("mode"),"stock_policy":run.get("stock_policy")},
        "traceability":{"input_snapshot_hash":snapshot.get("snapshot_hash"),"plan_hash":plan.get("plan_hash"),"validation_report_hash":validation.get("report_hash"),"machine_snapshot_hash":snapshot.get("machine_snapshot_hash"),"tool_snapshot_hash":snapshot.get("tool_snapshot_hash"),"stock_snapshot_hash":snapshot.get("stock_snapshot_hash"),"reservation_ids":[str(x.get("reservation_id") or "") for x in list(run.get("stock_reservations") or [])]},
        "profile_material_groups":profile_material,"stock_used":used_stock,
        "solver":{"status":run.get("result_status"),"backend":evidence.get("backend"),"backend_version":evidence.get("backend_version"),"exact_scope":evidence.get("exact_scope"),"exact_scope_reason":evidence.get("exact_scope_reason"),"lower_bound":evidence.get("lower_bound"),"upper_bound":evidence.get("upper_bound"),"absolute_gap":evidence.get("absolute_gap"),"relative_gap":evidence.get("relative_gap"),"gap_metric":evidence.get("gap_metric"),"runtime_seconds":evidence.get("runtime_seconds"),"nodes_explored":evidence.get("nodes_explored"),"states_pruned":evidence.get("states_pruned"),"simplifications":list(evidence.get("simplifications") or [])},
        "objective":objective,
        "material_balance":{"gross_stock_mm":_units_to_mm(balance.get("gross_stock_units"),snapshot),"net_part_mm":_units_to_mm(balance.get("net_part_units"),snapshot),"projected_kerf_mm":_units_to_mm(balance.get("kerf_units"),snapshot),"head_trim_mm":_units_to_mm(balance.get("head_trim_units"),snapshot),"tail_trim_mm":_units_to_mm(balance.get("tail_trim_units"),snapshot),"reusable_remnant_mm":_units_to_mm(balance.get("reusable_remnant_units"),snapshot),"scrap_mm":_units_to_mm(balance.get("waste_units"),snapshot),"transition_effect_mm":_units_to_mm(balance.get("transition_effect_units"),snapshot),"balance_delta_mm":_units_to_mm(balance.get("balance_delta_units"),snapshot)},
        "totals":{"bar_count":len(bars),"cut_count":sum(int(b.get("cut_count") or 0) for b in bars),"common_cut_count":sum(int(b.get("common_cut_count") or 0) for b in bars),"total_cost":sum(float(b.get("total_cost") or 0.0) for b in bars)},
        "validation":{"valid":bool(validation.get("valid")),"errors":list(validation.get("errors") or []),"warnings":list(validation.get("warnings") or []),"report_hash":validation.get("report_hash")},
        "output_contract":{"formats":["PDF","XLSX","CSV","JSON","labels PDF","neutral manufacturing JSON"],"machine_transfer_allowed":False,"controller_code_included":False},
    }
    payload["report_hash"]=stable_sha256({k:v for k,v in payload.items() if k!="report_hash"}); return payload


def _part_artifact_links(project: ProjectModel, record: dict[str, Any], root: Path, *, copy_files: bool) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for line in list(snapshot.get("demand_lines") or []):
        part_id = str(line.get("part_id") or "")
        part = project.parts.get(part_id)
        if part is None:
            continue
        expected_hash = str(line.get("manufacturing_hash") or "")
        artifacts = dict(dict(part.workbench or {}).get("artifacts") or {})
        for artifact_id, raw in sorted(artifacts.items()):
            a = dict(raw)
            if str(a.get("manufacturing_hash") or "") != expected_hash:
                continue
            if str(a.get("status") or "") != "current":
                continue
            key = (part_id, str(artifact_id))
            if key in seen:
                continue
            seen.add(key)
            source_path = Path(str(a.get("path") or "")) if a.get("path") else None
            source_exists = bool(source_path and source_path.is_file())
            sha = str(a.get("sha256") or "")
            verified = bool(source_exists and sha and sha256_file(source_path) == sha)
            copied_path = ""
            if copy_files and verified and source_path is not None:
                target = root / "part_artifacts" / safe_filename(part.part_position or part_id) / safe_filename(source_path.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target)
                if sha256_file(target) != sha:
                    raise IOError(f"Checksum van gekopieerd partartefact {artifact_id} wijkt af")
                copied_path = target.relative_to(root).as_posix()
            links.append({
                "part_id": part_id,
                "part_position": part.part_position,
                "manufacturing_hash": expected_hash,
                "artifact_id": artifact_id,
                "format": a.get("format", ""),
                "sha256": sha,
                "source_path": str(source_path) if source_path else "",
                "source_exists": source_exists,
                "source_checksum_verified": verified,
                "package_path": copied_path,
            })
    return links


def build_neutral_job_manifest(project: ProjectModel, record: dict[str, Any], *, release_id: str, released_at: str, released_by: str) -> dict[str, Any]:
    run = dict(record.get("run") or {})
    snapshot = dict(record.get("input_snapshot") or {})
    plan = dict(record.get("plan") or {})
    jobs = []
    for bar in _bar_rows(record):
        pieces = [x for x in _cut_rows(record) if x["bar_id"] == bar["bar_id"]]
        jobs.append({
            "bar_id": bar["bar_id"],
            "source": {"type": bar["source_type"], "source_id": bar["source_id"], "candidate_id": bar["candidate_id"]},
            "machine": {"machine_id": bar["machine_id"], "machine_profile_id": bar["machine_profile_id"]},
            "stock_length_mm": bar["stock_length_mm"],
            "cuts": pieces,
            "bar_hash": bar["bar_hash"],
        })
    payload = {
        "format": NEUTRAL_JOB_FORMAT,
        "schema_version": "1.0",
        "product": APP_NAME,
        "product_version": APP_VERSION,
        "project_id": project.project_id,
        "project_name": project.project_name,
        "run_id": run.get("run_id"),
        "release_id": release_id,
        "released_at": released_at,
        "released_by": released_by,
        "input_snapshot_hash": snapshot.get("snapshot_hash"),
        "plan_hash": plan.get("plan_hash"),
        "validation_report_hash": dict(record.get("validation_report") or {}).get("report_hash"),
        "machine_snapshot_hash": snapshot.get("machine_snapshot_hash"),
        "tool_snapshot_hash": snapshot.get("tool_snapshot_hash"),
        "stock_snapshot_hash": snapshot.get("stock_snapshot_hash"),
        "reservation_ids": [str(x.get("reservation_id") or "") for x in list(run.get("stock_reservations") or [])],
        "jobs": jobs,
        "machine_transfer": {"allowed": False, "reason": "Neutral manufacturing job only; no proprietary controller/postprocessor validation."},
    }
    payload["manifest_hash"] = stable_sha256({k: v for k, v in payload.items() if k != "manifest_hash"})
    return payload


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        atomic_write(path, b"\xef\xbb\xbf")
        return
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    atomic_write(path, output.getvalue().encode("utf-8-sig"))


def _json_cell(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return value


def _input_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    rows: list[dict[str, Any]] = []
    for line in list(snapshot.get("demand_lines") or []):
        line = dict(line)
        rows.append({
            "demand_line_id": line.get("demand_line_id", ""),
            "part_id": line.get("part_id", ""),
            "part_position": line.get("part_position", ""),
            "assembly_marks": ",".join(line.get("assembly_marks") or []),
            "profile": line.get("profile_name", ""),
            "profile_id": line.get("profile_id", ""),
            "section_hash": line.get("section_hash", ""),
            "material": line.get("material", ""),
            "grade": line.get("material_grade", ""),
            "length_mm": float(line.get("nominal_length_mm") or 0.0),
            "quantity": int(line.get("quantity") or 0),
            "start_angle_deg": float(dict(line.get("start_cut") or {}).get("primary_angle_deg") or 0.0),
            "start_secondary_deg": float(dict(line.get("start_cut") or {}).get("secondary_angle_deg") or 0.0),
            "end_angle_deg": float(dict(line.get("end_cut") or {}).get("primary_angle_deg") or 0.0),
            "end_secondary_deg": float(dict(line.get("end_cut") or {}).get("secondary_angle_deg") or 0.0),
            "allowed_orientations": ",".join(line.get("allowed_orientations") or []),
            "candidate_machines": ",".join(line.get("candidate_machine_ids") or []),
            "batch": line.get("production_batch", ""),
            "heat_requirement": line.get("heat_requirement", ""),
            "certificate_requirement": line.get("certificate_requirement", ""),
            "manufacturing_hash": line.get("manufacturing_hash", ""),
        })
    return rows


def _eligibility_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for line in list(dict(record.get("input_snapshot") or {}).get("demand_lines") or []):
        line = dict(line)
        reasons = list(line.get("eligibility_reasons") or [])
        rows.append({
            "demand_line_id": line.get("demand_line_id", ""),
            "part_position": line.get("part_position", ""),
            "profile": line.get("profile_name", ""),
            "material": line.get("material", ""),
            "status": line.get("eligibility_status", ""),
            "reason_count": len(reasons),
            "blocking_reasons": " | ".join(str(x) for x in reasons),
            "candidate_machines": ",".join(line.get("candidate_machine_ids") or []),
        })
    return rows


def _transition_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    rows: list[dict[str, Any]] = []
    for raw_bar in list(dict(record.get("plan") or {}).get("bars") or []):
        bar = dict(raw_bar)
        for raw in list(bar.get("transitions") or []):
            tr = dict(raw)
            rows.append({
                "bar_id": bar.get("bar_id", ""),
                "transition_id": tr.get("transition_id", ""),
                "left_instance_id": tr.get("left_instance_id", ""),
                "right_instance_id": tr.get("right_instance_id", ""),
                "common_cut": bool(tr.get("common_cut", False)),
                "cut_count": int(tr.get("cut_count") or 0),
                "kerf_projection_mm": _units_to_mm(tr.get("kerf_projection_units"), snapshot),
                "reference_gap_mm": _units_to_mm(tr.get("required_reference_gap_units"), snapshot),
                "transition_effect_mm": _units_to_mm(tr.get("transition_effect_units"), snapshot),
                "geometry_delta_mm": _units_to_mm(tr.get("geometry_delta_units"), snapshot),
                "proof_hash": tr.get("proof_hash", "") or tr.get("transition_hash", ""),
            })
    return rows


def _stock_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    rows: list[dict[str, Any]] = []
    for raw in list(dict(snapshot.get("stock_snapshot") or {}).get("candidates") or []):
        item = dict(raw)
        rows.append({
            "candidate_id": item.get("candidate_id", ""),
            "source_type": item.get("source_type", ""),
            "source_id": item.get("source_id", ""),
            "profile_id": item.get("profile_id", ""),
            "section_hash": item.get("section_hash", ""),
            "material": item.get("material", ""),
            "grade": item.get("material_grade", ""),
            "length_mm": float(item.get("length_mm") or 0.0),
            "available_quantity": int(item.get("available_quantity") or 0),
            "physical": bool(item.get("physical", False)),
            "reservation_status": item.get("reservation_status", ""),
            "reservation_revision": int(item.get("reservation_revision") or 0),
            "minimum_reusable_mm": float(item.get("minimum_reusable_mm") or 0.0),
            "heat": item.get("heat", ""),
            "batch": item.get("batch", ""),
            "certificate": item.get("certificate", ""),
            "location": item.get("location", ""),
            "supplier": item.get("supplier", ""),
            "unit_price": float(item.get("unit_price") or 0.0),
            "lead_time_days": int(item.get("lead_time_days") or 0),
            "snapshot_hash": item.get("snapshot_hash", ""),
        })
    return rows


def _purchase_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    bars = _bar_rows(record)
    grouped: dict[str, dict[str, Any]] = {}
    for bar in bars:
        if bar.get("source_type") != "purchase_option":
            continue
        key = str(bar.get("candidate_id") or bar.get("source_id") or "purchase")
        row = grouped.setdefault(key, {
            "candidate_id": key,
            "source_id": bar.get("source_id", ""),
            "profile_id": bar.get("profile_id", ""),
            "material": bar.get("material", ""),
            "grade": bar.get("grade", ""),
            "stock_length_mm": bar.get("stock_length_mm", 0.0),
            "bars_required": 0,
            "supplier": bar.get("supplier", ""),
            "unit_price": bar.get("unit_price", 0.0),
            "total_cost": 0.0,
        })
        row["bars_required"] += 1
        row["total_cost"] += float(bar.get("total_cost") or bar.get("unit_price") or 0.0)
    return [grouped[k] for k in sorted(grouped)]


def _balance_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    snapshot = dict(record.get("input_snapshot") or {})
    balance = dict(dict(record.get("plan") or {}).get("material_balance") or {})
    order = [
        ("gross_stock", "gross_stock_units"), ("net_parts", "net_part_units"),
        ("projected_kerf", "kerf_units"), ("head_trim", "head_trim_units"),
        ("tail_trim", "tail_trim_units"), ("transition_effect", "transition_effect_units"),
        ("reusable_remnant", "reusable_remnant_units"), ("scrap", "waste_units"),
        ("balance_delta", "balance_delta_units"), ("material_loss", "material_loss_units"),
    ]
    return [{"component": label, "value_mm": _units_to_mm(balance.get(key), snapshot), "raw_units": int(balance.get(key) or 0)} for label, key in order]


def _cost_time_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = dict(record.get("solver_evidence") or {})
    rows = []
    for bar in _bar_rows(record):
        rows.append({
            "bar_id": bar.get("bar_id", ""), "machine_id": bar.get("machine_id", ""),
            "piece_count": bar.get("piece_count", 0), "cut_count": bar.get("cut_count", 0),
            "common_cut_count": bar.get("common_cut_count", 0), "material_cost": bar.get("total_cost", 0.0),
            "solver_runtime_s": float(evidence.get("runtime_seconds") or 0.0),
            "calculated_cycle_time_s": "", "setup_time_s": "", "handling_time_s": "",
            "note": "Tijdvelden blijven leeg tenzij gevalideerde machineformules in de snapshot beschikbaar zijn.",
        })
    return rows


def _error_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    validation = dict(record.get("validation_report") or {})
    for msg in list(validation.get("messages") or []):
        item = dict(msg) if isinstance(msg, dict) else {"message": str(msg)}
        rows.append({"source": "validation", "severity": item.get("severity", item.get("level", "error")), "code": item.get("code", ""), "entity": item.get("entity_id", ""), "message": item.get("message", str(msg))})
    for row in _eligibility_rows(record):
        if row.get("status") not in {"eligible", "passed", "validated"} or row.get("blocking_reasons"):
            rows.append({"source": "eligibility", "severity": "block" if row.get("blocking_reasons") else "review", "code": "", "entity": row.get("part_position", ""), "message": row.get("blocking_reasons", "") or str(row.get("status", ""))})
    if not rows:
        rows.append({"source": "validation", "severity": "info", "code": "", "entity": "", "message": "Geen fouten of blokkades in het vrijgegeven plan."})
    return rows


def _audit_rows(project: ProjectModel, record: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in list(project.audit_log or []):
        data = asdict(event) if hasattr(event, "__dataclass_fields__") else dict(event)
        rows.append({
            "scope": "project", "timestamp": data.get("timestamp", ""), "user": data.get("user", ""),
            "action": data.get("action", ""), "entity_id": data.get("entity_id", ""),
            "before_hash": data.get("before_hash", ""), "after_hash": data.get("after_hash", ""),
            "details": _json_cell(data.get("details", {})),
        })
    for event in list(dict(record.get("run") or {}).get("audit") or []):
        event = dict(event)
        rows.append({
            "scope": "nesting_run", "timestamp": event.get("at", ""), "user": event.get("user", ""),
            "action": event.get("event", ""), "entity_id": dict(record.get("run") or {}).get("run_id", ""),
            "before_hash": "", "after_hash": event.get("release_hash", event.get("acceptance_hash", "")),
            "details": _json_cell(event),
        })
    return rows


def _scenario_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    run = dict(record.get("run") or {}); plan = dict(record.get("plan") or {}); objective = dict(plan.get("objective") or {})
    rows = [{
        "scenario_id": run.get("scenario_id", ""), "family": run.get("scenario_family", ""), "status": run.get("result_status", ""),
        "backend": dict(record.get("solver_evidence") or {}).get("backend", ""), "bar_count": len(list(plan.get("bars") or [])),
        "material_loss_mm": next((x["value_mm"] for x in _balance_rows(record) if x["component"] == "material_loss"), 0.0),
        "cost": sum(float(x.get("total_cost") or 0.0) for x in _bar_rows(record)), "objective": _json_cell(objective),
        "plan_hash": plan.get("plan_hash", ""), "selected": True,
    }]
    manual = dict(record.get("manual_planning") or {})
    baseline = dict(manual.get("solver_baseline") or {})
    if baseline:
        rows.append({
            "scenario_id": f"{run.get('scenario_id','')}:solver_baseline", "family": run.get("scenario_family", ""), "status": baseline.get("status", "baseline"),
            "backend": baseline.get("backend", ""), "bar_count": baseline.get("bar_count", ""), "material_loss_mm": baseline.get("material_loss_mm", ""),
            "cost": baseline.get("cost", ""), "objective": _json_cell(baseline.get("objective", {})), "plan_hash": baseline.get("plan_hash", ""), "selected": False,
        })
    return rows


def _write_xlsx(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str, released_at: str, released_by: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp.xlsx", dir=path.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        workbook = xlsxwriter.Workbook(temp)
        try:
            fixed_dt = datetime.fromisoformat(str(released_at).replace("Z", "+00:00"))
            if fixed_dt.tzinfo is not None:
                fixed_dt = fixed_dt.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            fixed_dt = datetime(1980, 1, 1)
        workbook.set_properties({"title": "CWS Profile Nesting release", "author": APP_NAME, "created": fixed_dt, "comments": f"Release {release_id}"})
        title = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#FFFFFF", "bg_color": "#16324F"})
        header = workbook.add_format({"bold": True, "font_color": "#FFFFFF", "bg_color": "#1F5C8A", "border": 1, "text_wrap": True, "valign": "vcenter"})
        cell = workbook.add_format({"border": 1, "valign": "top"})
        text = workbook.add_format({"border": 1, "valign": "top", "text_wrap": True})
        num = workbook.add_format({"border": 1, "num_format": "0.000"})
        money = workbook.add_format({"border": 1, "num_format": "€ #,##0.00"})
        blocked = workbook.add_format({"border": 1, "bg_color": "#FECACA"})
        ok = workbook.add_format({"border": 1, "bg_color": "#DCFCE7"})
        run = dict(record.get("run") or {}); plan = dict(record.get("plan") or {}); evidence=dict(record.get("solver_evidence") or {}); balance=dict(plan.get("material_balance") or {}); snapshot=dict(record.get("input_snapshot") or {}); validation=dict(record.get("validation_report") or {})

        ws = workbook.add_worksheet("Samenvatting")
        ws.merge_range("A1:F1", "CWS Profielnesting - vrijgave", title)
        summary = [
            ("Project", project.project_name), ("Project-ID", project.project_id), ("Run-ID", run.get("run_id", "")),
            ("Release-ID", release_id), ("Vrijgavestatus", "released"), ("Vrijgegeven op", released_at), ("Vrijgegeven door", released_by),
            ("Scenario", run.get("scenario_id", "")), ("Scenariofamilie", run.get("scenario_family", "")), ("Solverstatus", run.get("result_status", "")),
            ("Plan hash", plan.get("plan_hash", "")), ("Input snapshot", snapshot.get("snapshot_hash", "")), ("Validation hash", validation.get("report_hash", "")),
            ("Validatie", "GELDIG" if validation.get("valid") else "ONGELDIG"), ("Staven", len(list(plan.get("bars") or []))),
            ("Solver backend", evidence.get("backend", "")), ("Exact scope", evidence.get("exact_scope", False)), ("Lower bound", evidence.get("lower_bound", "")),
            ("Upper bound", evidence.get("upper_bound", "")), ("Relatieve gap", evidence.get("relative_gap", "")), ("Runtime s", evidence.get("runtime_seconds", 0.0)),
            ("Netto mm", _units_to_mm(balance.get("net_part_units"),snapshot)), ("Kerf mm", _units_to_mm(balance.get("kerf_units"),snapshot)),
            ("Trims mm", _units_to_mm(balance.get("head_trim_units"),snapshot)+_units_to_mm(balance.get("tail_trim_units"),snapshot)),
            ("Rest mm", _units_to_mm(balance.get("reusable_remnant_units"),snapshot)), ("Scrap mm", _units_to_mm(balance.get("waste_units"),snapshot)),
            ("Machine transfer", "GEBLOKKEERD - neutral job only"),
        ]
        for r, (k, v) in enumerate(summary, start=3):
            ws.write(r-1, 0, k, header); ws.write(r-1, 1, v, ok if k == "Validatie" and v == "GELDIG" else blocked if k == "Validatie" else cell)
        ws.set_column("A:A", 24); ws.set_column("B:B", 78)

        sheet_payloads = [
            ("Invoer", _input_rows(record)),
            ("Eligibility", _eligibility_rows(record)),
            ("Scenariovergelijking", _scenario_rows(record)),
            ("Geoptimaliseerde staven", _bar_rows(record)),
            ("Zaagposities", _cut_rows(record)),
            ("Cuts en kerfs", _transition_rows(record)),
            ("Voorraad en rest", _stock_rows(record)),
            ("Inkoopbehoefte", _purchase_rows(record)),
            ("Materiaalbalans", _balance_rows(record)),
            ("Kosten en tijden", _cost_time_rows(record)),
            ("Solver evidence", [{"veld": k, "waarde": _json_cell(v)} for k, v in sorted(evidence.items())]),
            ("Foutenlijst", _error_rows(record)),
            ("Audit", _audit_rows(project, record)),
        ]
        for name, rows in sheet_payloads:
            sh = workbook.add_worksheet(name)
            if not rows:
                sh.write(0, 0, "Geen gegevens", header)
                continue
            keys = list(rows[0])
            for c, key in enumerate(keys): sh.write(0, c, key, header)
            for r, row in enumerate(rows, start=1):
                for c, key in enumerate(keys):
                    value = _json_cell(row.get(key))
                    fmt = num if isinstance(value, float) else cell
                    if key in {"total_cost", "material_cost", "unit_price", "cost"} and isinstance(value, (int, float)):
                        fmt = money
                    elif isinstance(value, str) and (len(value) > 45 or key in {"details", "blocking_reasons", "message", "objective", "waarde", "note"}):
                        fmt = text
                    sh.write(r, c, value, fmt)
            sh.autofilter(0, 0, len(rows), len(keys)-1); sh.freeze_panes(1, 0)
            for c, key in enumerate(keys):
                width = min(42, max(11, len(str(key))+2, min(36, max((len(str(_json_cell(row.get(key, "")))) for row in rows[:100]), default=0)+2)))
                sh.set_column(c, c, width)
            if name == "Eligibility" and "status" in keys:
                col = keys.index("status")
                sh.conditional_format(1, col, len(rows), col, {"type": "text", "criteria": "containing", "value": "eligible", "format": ok})
            if name == "Foutenlijst" and "severity" in keys:
                col = keys.index("severity")
                sh.conditional_format(1, col, len(rows), col, {"type": "text", "criteria": "containing", "value": "block", "format": blocked})
        workbook.close()
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def _draw_bar_plan_pdf(pdf: canvas.Canvas, record: dict[str, Any], bar: dict[str, Any], *, x: float, y: float, width: float, height: float) -> None:
    scene = build_bar_scene(record, str(bar.get("bar_id") or ""))
    length = max(scene.stock_length_mm, 1e-9)
    def sx(mm_value: float) -> float:
        return x + width * max(0.0, min(length, mm_value)) / length
    y0 = y + height * 0.18
    bar_h = height * 0.55
    role_fill = {
        "stock": colors.HexColor("#DCFCE7"), "piece": colors.HexColor("#F6D365"),
        "trim": colors.HexColor("#94A3B8"), "kerf": colors.HexColor("#111827"),
        "forbidden": colors.HexColor("#FECACA"), "remnant": colors.HexColor("#86EFAC"),
        "scrap": colors.HexColor("#FCA5A5"),
    }
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(x, y + height - 8, f"{scene.bar_id} - {scene.stock_length_mm:.1f} mm - {bar.get('profile_id','')} {bar.get('material','')} {bar.get('grade','')}")
    trace = " / ".join(v for v in [str(bar.get("heat") or ""), str(bar.get("batch") or ""), str(bar.get("certificate") or "")] if v)
    if trace:
        pdf.setFont("Helvetica", 6.2); pdf.drawRightString(x + width, y + height - 8, f"Heat/batch/cert: {trace[:70]}")
    for prim in scene.primitives:
        if prim.kind == "rect":
            xx1, xx2 = sx(prim.x1_mm), sx(prim.x2_mm)
            low, high = min(xx1, xx2), max(xx1, xx2)
            yy = y0 + bar_h * prim.y1
            hh = max(1.0, bar_h * (prim.y2 - prim.y1))
            fill = role_fill.get(prim.role, colors.HexColor("#CBD5E1"))
            if prim.role == "piece":
                try:
                    fill = colors.HexColor(piece_display_color(prim, "part"))
                except Exception:
                    pass
            pdf.setFillColor(fill); pdf.setStrokeColor(colors.HexColor("#334155")); pdf.setLineWidth(0.45)
            pdf.rect(low, yy, max(0.8, high-low), hh, fill=1, stroke=1)
            if prim.label and prim.role in {"piece", "remnant", "scrap"} and high-low > 28:
                pdf.setFillColor(colors.black); pdf.setFont("Helvetica", 5.4)
                pdf.drawCentredString((low+high)/2, yy + hh/2 - 2, prim.label[:45])
        elif prim.kind == "cut":
            xx = sx(prim.x1_mm)
            angle = float(prim.metadata.get("angle_deg") or 0.0)
            secondary = float(prim.metadata.get("secondary_angle_deg") or 0.0)
            visual = max(-10.0, min(10.0, math.tan(math.radians(angle)) * bar_h * 0.33))
            pdf.setStrokeColor(colors.HexColor("#0F172A")); pdf.setLineWidth(0.9)
            pdf.line(xx-visual, y0 + bar_h*0.12, xx+visual, y0 + bar_h*0.88)
            if abs(angle) > 0.01 or abs(secondary) > 0.01:
                pdf.setFont("Helvetica", 5.2); pdf.setFillColor(colors.HexColor("#0F172A"))
                label = f"{angle:+.1f}°" + (f"/{secondary:+.1f}°" if abs(secondary) > 0.01 else "")
                pdf.drawString(xx+2, y0 + bar_h*0.93, label)
        elif prim.kind == "marker":
            xx = sx(prim.x1_mm)
            pdf.setStrokeColor(colors.HexColor("#16A34A") if prim.role == "common" else colors.HexColor("#7C3AED"))
            pdf.setLineWidth(1.6); pdf.line(xx, y0, xx, y0 + bar_h)
            if prim.label:
                pdf.setFont("Helvetica-Bold", 5.3); pdf.setFillColor(colors.HexColor("#166534") if prim.role == "common" else colors.HexColor("#6D28D9"))
                pdf.drawString(xx+1.5, y0 + bar_h + 1, prim.label[:18])
        elif prim.kind == "line" and prim.role == "centerline":
            pdf.setStrokeColor(colors.HexColor("#64748B")); pdf.setLineWidth(0.35); pdf.setDash(3, 2)
            pdf.line(sx(prim.x1_mm), y0 + bar_h*0.5, sx(prim.x2_mm), y0 + bar_h*0.5); pdf.setDash()
    pdf.setFillColor(colors.black); pdf.setFont("Helvetica", 5.5)
    pdf.drawString(x, y+2, "0")
    pdf.drawRightString(x+width, y+2, f"{length:.1f} mm")


def _write_pdf(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str, released_at: str, released_by: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run = dict(record.get("run") or {}); plan = dict(record.get("plan") or {}); validation = dict(record.get("validation_report") or {}); evidence=dict(record.get("solver_evidence") or {}); balance=dict(plan.get("material_balance") or {}); snapshot=dict(record.get("input_snapshot") or {})
    bars = _bar_rows(record); cuts = _cut_rows(record); errors = _error_rows(record)
    pdf = canvas.Canvas(str(path), pagesize=landscape(A4), pageCompression=1, invariant=1)
    W, H = landscape(A4)
    def header(title: str, *, watermark: str = "VRIJGEGEVEN"):
        pdf.setFillColor(colors.HexColor("#16324F")); pdf.rect(0, H-18*mm, W, 18*mm, fill=1, stroke=0)
        pdf.setFillColor(colors.white); pdf.setFont("Helvetica-Bold", 15); pdf.drawString(12*mm, H-11.5*mm, title)
        pdf.setFont("Helvetica", 7); pdf.drawRightString(W-10*mm, H-11*mm, f"{APP_NAME} {APP_VERSION}")
        pdf.saveState(); pdf.setFillColor(colors.Color(0.3,0.3,0.3,alpha=0.08)); pdf.setFont("Helvetica-Bold", 46); pdf.translate(W/2,H/2); pdf.rotate(27); pdf.drawCentredString(0,0,watermark); pdf.restoreState()
        pdf.setFillColor(colors.black)
    header("Profielnesting - vrijgave- en zaagrapport")
    pdf.setFont("Helvetica", 8)
    summary = [
        f"Project: {project.project_name}", f"Project-ID: {project.project_id}", f"Run-ID: {run.get('run_id','')}",
        f"Release-ID: {release_id}", f"Vrijgegeven: {released_at} door {released_by}", f"Scenario: {run.get('scenario_id','')} / {run.get('scenario_family','')}",
        f"Solverstatus: {run.get('result_status','')}", f"Plan hash: {plan.get('plan_hash','')}",
        f"Input snapshot: {snapshot.get('snapshot_hash','')}",
        f"Validation: {'GELDIG' if validation.get('valid') else 'ONGELDIG'} - {validation.get('report_hash','')}",
        f"Solver: {evidence.get('backend','')} · exact={evidence.get('exact_scope',False)} · lower={evidence.get('lower_bound')} · upper={evidence.get('upper_bound')} · gap={evidence.get('relative_gap')} · {float(evidence.get('runtime_seconds') or 0):.3f}s",
        f"Balans mm: netto {_units_to_mm(balance.get('net_part_units'),snapshot):.3f} + kerf {_units_to_mm(balance.get('kerf_units'),snapshot):.3f} + trims {(_units_to_mm(balance.get('head_trim_units'),snapshot)+_units_to_mm(balance.get('tail_trim_units'),snapshot)):.3f} + transition {_units_to_mm(balance.get('transition_effect_units'),snapshot):.3f} + rest {_units_to_mm(balance.get('reusable_remnant_units'),snapshot):.3f} + scrap {_units_to_mm(balance.get('waste_units'),snapshot):.3f}",
        "Machine-uitvoer: NIET INBEGREPEN - neutral jobmanifest; directe machineoverdracht is geblokkeerd.",
    ]
    y = H-27*mm
    for line in summary: pdf.drawString(12*mm, y, str(line)[:180]); y -= 4.7*mm
    y -= 1*mm
    pdf.setFont("Helvetica-Bold", 8); cols=[("Bar",24),("Bron",30),("Stock",18),("Profiel",25),("Materiaal",22),("Machine",23),("Stuks",12),("Kerf",15),("Rest",16)]
    x=10*mm
    for label,width in cols: pdf.drawString(x,y,label); x+=width*mm
    y-=4.2*mm; pdf.setFont("Helvetica",6.7)
    for bar in bars:
        if y < 14*mm: pdf.showPage(); header("Profielnesting - staven vervolg"); y=H-27*mm
        values=[bar['bar_id'],f"{bar['source_type']}:{bar['source_id']}",f"{bar['stock_length_mm']:.1f}",bar.get('profile_id',''),f"{bar.get('material','')} {bar.get('grade','')}",bar['machine_id'],bar['piece_count'],f"{bar['projected_kerf_mm']:.2f}",f"{bar['reusable_remnant_mm']:.1f}"]
        x=10*mm
        for value,(_,width) in zip(values,cols): pdf.drawString(x,y,str(value)[:20]); x+=width*mm
        y-=4.0*mm

    # One graphical, scale-correct bar plan per bar.  This page is deliberately
    # derived from the same persisted vector scene as the desktop visualizer.
    for index, bar in enumerate(bars, start=1):
        pdf.showPage(); header(f"Grafisch zaagplan {index}/{len(bars)} - {bar['bar_id']}")
        _draw_bar_plan_pdf(pdf, record, bar, x=12*mm, y=62*mm, width=W-24*mm, height=95*mm)
        pdf.setFont("Helvetica", 7)
        trace = [
            f"Bron: {bar['source_type']} / {bar['source_id']} / {bar['candidate_id']}",
            f"Profiel: {bar.get('profile_id','')} - materiaal: {bar.get('material','')} {bar.get('grade','')}",
            f"Heat: {bar.get('heat','') or '-'}  Batch: {bar.get('batch','') or '-'}  Certificaat: {bar.get('certificate','') or '-'}",
            f"Machine: {bar['machine_id']} / {bar['machine_profile_id']}",
            f"Kerf: {bar['projected_kerf_mm']:.3f} mm  Head trim: {bar['head_trim_mm']:.3f} mm  Tail trim: {bar['tail_trim_mm']:.3f} mm",
            f"Rest: {bar['reusable_remnant_mm']:.3f} mm  Scrap: {bar['waste_mm']:.3f} mm  Common cuts: {bar['common_cut_count']}",
            f"Bar hash: {bar['bar_hash']}",
        ]
        yy=51*mm
        for line in trace: pdf.drawString(12*mm, yy, line[:180]); yy-=4.2*mm

    pdf.showPage(); header("Profielnesting - zaagvolgorde")
    y=H-27*mm; pdf.setFont("Helvetica-Bold",6.7)
    cols2=[("Bar",19),("Seq",8),("Pos",19),("Profiel",24),("Lengte",18),("Start",18),("Eind",18),("Start°",13),("Eind°",13),("Common",13),("Machine",20)]
    x=8*mm
    for label,width in cols2: pdf.drawString(x,y,label); x+=width*mm
    y-=4.3*mm; pdf.setFont("Helvetica",6.1)
    for row in cuts:
        if y<14*mm: pdf.showPage(); header("Profielnesting - zaagvolgorde vervolg"); y=H-27*mm
        vals=[row['bar_id'],row['sequence'],row['part_position'],row['profile'],f"{row['nominal_length_mm']:.2f}",f"{row['reference_start_mm']:.2f}",f"{row['reference_end_mm']:.2f}",f"{row['start_angle_deg']:+.1f}",f"{row['end_angle_deg']:+.1f}","JA" if row['common_cut_before'] else "NEE",row['machine_id']]
        x=8*mm
        for value,(_,width) in zip(vals,cols2): pdf.drawString(x,y,str(value)[:18]); x+=width*mm
        y-=3.8*mm

    pdf.showPage(); header("Validatie, waarschuwingen en traceability")
    pdf.setFont("Helvetica-Bold",8); pdf.drawString(12*mm,H-28*mm,"Validatie/foutenlijst")
    yy=H-34*mm; pdf.setFont("Helvetica",7)
    for row in errors[:35]:
        pdf.drawString(12*mm,yy,f"[{row.get('severity','')}] {row.get('code','')} {row.get('entity','')}: {row.get('message','')}"[:185]); yy-=4.2*mm
    if yy<45*mm: yy=45*mm
    pdf.setFont("Helvetica-Bold",8); pdf.drawString(12*mm,yy-4*mm,"Traceability")
    yy-=10*mm; pdf.setFont("Helvetica",6.5)
    for label,value in [
        ("Plan hash",plan.get("plan_hash","")),("Input snapshot hash",snapshot.get("snapshot_hash","")),
        ("Validation report hash",validation.get("report_hash","")),("Machine snapshot hash",snapshot.get("machine_snapshot_hash","")),
        ("Tool snapshot hash",snapshot.get("tool_snapshot_hash","")),("Stock snapshot hash",snapshot.get("stock_snapshot_hash","")),
    ]:
        pdf.drawString(12*mm,yy,f"{label}: {value}"[:190]); yy-=4.2*mm
    pdf.save()

def _draw_qr(pdf: canvas.Canvas, uri: str, x: float, y: float, size: float = 27*mm) -> None:
    qr=QrCodeWidget(uri); bounds=qr.getBounds()
    drawing=Drawing(size,size,transform=[size/(bounds[2]-bounds[0]),0,0,size/(bounds[3]-bounds[1]),0,0]); drawing.add(qr); renderPDF.draw(drawing,pdf,x,y)


def _label_header(pdf: canvas.Canvas, title: str) -> None:
    pdf.setFillColor(colors.HexColor("#16324F")); pdf.rect(0,40*mm,100*mm,10*mm,fill=1,stroke=0)
    pdf.setFillColor(colors.white); pdf.setFont("Helvetica-Bold",9.5); pdf.drawString(5*mm,44*mm,f"{APP_NAME} - {title}")
    pdf.setFillColor(colors.black)


def _write_bar_labels_pdf(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_id=str(dict(record.get("run") or {}).get("run_id") or "")
    pdf = canvas.Canvas(str(path), pagesize=(100*mm, 50*mm), pageCompression=1, invariant=1)
    for bar in _bar_rows(record):
        _label_header(pdf,"VOORRAADSTAAF")
        pdf.setFont("Helvetica-Bold",14); pdf.drawString(5*mm,33*mm,str(bar['bar_id'])[:28]); pdf.setFont("Helvetica",7.2)
        lines=[f"Project: {project.project_name}",f"Profiel: {bar.get('profile_id','')} - {bar.get('material','')} {bar.get('grade','')}",f"Bron: {bar['source_type']} / {bar['source_id']}",f"Stock: {bar['stock_length_mm']:.1f} mm - Machine: {bar['machine_id']}",f"Heat/batch: {bar.get('heat','') or '-'} / {bar.get('batch','') or '-'}",f"Release: {release_id[:18]}"]
        for i,line in enumerate(lines): pdf.drawString(5*mm,(27-i*3.7)*mm,line[:62])
        _draw_qr(pdf,f"cws://project/{project.project_id}/profile-nesting/{run_id}/bar/{bar['bar_id']}?release={release_id}",70*mm,7*mm)
        pdf.showPage()
    pdf.save()


def _write_piece_labels_pdf(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_id=str(dict(record.get("run") or {}).get("run_id") or "")
    pdf = canvas.Canvas(str(path), pagesize=(100*mm, 50*mm), pageCompression=1, invariant=1)
    for row in _cut_rows(record):
        _label_header(pdf,"GEZAAGD STUK")
        title=str(row.get("part_position") or row.get("instance_id") or "stuk")
        pdf.setFont("Helvetica-Bold",14); pdf.drawString(5*mm,33*mm,title[:28]); pdf.setFont("Helvetica",7.1)
        lines=[
            f"Project: {project.project_name}",f"Profiel: {row.get('profile','')} - {row.get('material','')} {row.get('grade','')}",
            f"Lengte: {row.get('nominal_length_mm',0):.2f} mm - Qty instance: {row.get('quantity_ordinal',0)}",
            f"Staaf/seq: {row.get('bar_id','')} / {row.get('sequence','')} - Machine: {row.get('machine_id','')}",
            f"Batch/heat: {row.get('production_batch','') or '-'} / {row.get('heat_requirement','') or '-'}",
            f"Release: {release_id[:18]}",
        ]
        for i,line in enumerate(lines): pdf.drawString(5*mm,(27-i*3.7)*mm,line[:62])
        _draw_qr(pdf,f"cws://project/{project.project_id}/profile-nesting/{run_id}/piece/{row.get('instance_id','')}?release={release_id}",70*mm,7*mm)
        pdf.showPage()
    pdf.save()


def _write_remnant_labels_pdf(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    run_id=str(dict(record.get("run") or {}).get("run_id") or "")
    pdf = canvas.Canvas(str(path), pagesize=(100*mm, 50*mm), pageCompression=1, invariant=1)
    any_page=False
    for index, bar in enumerate(_bar_rows(record), start=1):
        if float(bar.get("reusable_remnant_mm") or 0.0) <= 0:
            continue
        any_page=True; remnant_id=f"REM-{run_id[:8]}-{index:03d}"
        _label_header(pdf,"VOORSPELD RESTSTUK")
        pdf.setFont("Helvetica-Bold",13); pdf.drawString(5*mm,33*mm,remnant_id); pdf.setFont("Helvetica",7.1)
        lines=[f"Project: {project.project_name}",f"Profiel: {bar.get('profile_id','')} - {bar.get('material','')} {bar.get('grade','')}",f"Restlengte: {bar.get('reusable_remnant_mm',0):.2f} mm",f"Afkomstig van: {bar.get('bar_id','')} / {bar.get('source_id','')}",f"Heat/batch/cert: {bar.get('heat','') or '-'} / {bar.get('batch','') or '-'} / {bar.get('certificate','') or '-'}",f"Release: {release_id[:18]}"]
        for i,line in enumerate(lines): pdf.drawString(5*mm,(27-i*3.7)*mm,line[:62])
        _draw_qr(pdf,f"cws://project/{project.project_id}/profile-nesting/{run_id}/remnant/{remnant_id}?release={release_id}",70*mm,7*mm)
        pdf.showPage()
    if not any_page:
        _label_header(pdf,"VOORSPELD RESTSTUK"); pdf.setFont("Helvetica",8); pdf.drawString(5*mm,28*mm,"Geen herbruikbare reststukken in dit plan."); pdf.showPage()
    pdf.save()


def _write_labels_pdf(path: Path, project: ProjectModel, record: dict[str, Any], *, release_id: str) -> None:
    """Backward-compatible voorraadstaaflabel entry point."""
    _write_bar_labels_pdf(path, project, record, release_id=release_id)

def _collect_artifacts(root: Path, run_id: str, plan_hash: str, snapshot_hash: str) -> list[NestingOutputArtifact]:
    mapping={".pdf":"application/pdf",".xlsx":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",".csv":"text/csv",".json":"application/json",".svg":"image/svg+xml"}
    result=[]
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in {"manifest.json"}):
        rel=path.relative_to(root).as_posix(); ext=path.suffix.lower();
        art=NestingOutputArtifact(artifact_id=f"nest:{run_id}:{stable_sha256(rel)[:16]}",format=ext.lstrip("."),relative_path=rel,sha256=sha256_file(path),size_bytes=path.stat().st_size,media_type=mapping.get(ext,"application/octet-stream"),run_id=run_id,plan_hash=plan_hash,input_snapshot_hash=snapshot_hash,released=True)
        art.refresh_hash(); result.append(art)
    return result


def create_release_package(project: ProjectModel, record: dict[str, Any], output_dir: str | Path, *, release_id: str, released_at: str, released_by: str, package_name: str | None = None, copy_part_artifacts: bool = True) -> NestingPackageResult:
    run=dict(record.get("run") or {}); plan=dict(record.get("plan") or {}); snapshot=dict(record.get("input_snapshot") or {})
    run_id=str(run.get("run_id") or ""); plan_hash=str(plan.get("plan_hash") or ""); snapshot_hash=str(snapshot.get("snapshot_hash") or "")
    base=safe_filename(package_name or f"{project.project_name}_{run.get('scenario_id','nesting')}_{run_id[:8]}_NESTING_RELEASE")
    final_root=Path(output_dir)/base
    with atomic_directory(final_root) as root:
        atomic_write(root/"data"/"run.json",canonical_json_bytes(run))
        atomic_write(root/"data"/"input_snapshot.json",canonical_json_bytes(snapshot))
        atomic_write(root/"data"/"plan.json",canonical_json_bytes(plan))
        atomic_write(root/"data"/"solver_evidence.json",canonical_json_bytes(record.get("solver_evidence") or {}))
        atomic_write(root/"data"/"validation_report.json",canonical_json_bytes(record.get("validation_report") or {}))
        release_report=build_release_report(project,record,release_id=release_id,released_at=released_at,released_by=released_by)
        atomic_write(root/"reports"/"profile_nesting_report.json",canonical_json_bytes(release_report))
        _write_csv(root/"reports"/"bars.csv",_bar_rows(record)); _write_csv(root/"reports"/"cuts.csv",_cut_rows(record))
        _write_xlsx(root/"reports"/"profile_nesting.xlsx",project,record,release_id=release_id,released_at=released_at,released_by=released_by)
        _write_pdf(root/"reports"/"profile_nesting.pdf",project,record,release_id=release_id,released_at=released_at,released_by=released_by)
        _write_bar_labels_pdf(root/"labels"/"bar_labels.pdf",project,record,release_id=release_id)
        _write_piece_labels_pdf(root/"labels"/"piece_labels.pdf",project,record,release_id=release_id)
        _write_remnant_labels_pdf(root/"labels"/"remnant_labels.pdf",project,record,release_id=release_id)
        for bar in _bar_rows(record):
            scene_to_svg(build_bar_scene(record,str(bar.get("bar_id") or "")), root/"reports"/"bar_plans"/f"{safe_filename(str(bar.get('bar_id') or 'bar'))}.svg")
        neutral=build_neutral_job_manifest(project,record,release_id=release_id,released_at=released_at,released_by=released_by)
        atomic_write(root/"neutral_job"/"neutral_profile_cut_job.json",canonical_json_bytes(neutral))
        links=_part_artifact_links(project,record,root,copy_files=copy_part_artifacts)
        atomic_write(root/"part_artifacts"/"artifact_links.json",canonical_json_bytes({"links":links}))
        artifacts=_collect_artifacts(root,run_id,plan_hash,snapshot_hash)
        manifest={
            "format":PACKAGE_FORMAT,"schema_version":REPORT_SCHEMA_VERSION,"product":APP_NAME,"product_version":APP_VERSION,
            "created_at":released_at,"project_id":project.project_id,"project_name":project.project_name,"run_id":run_id,
            "release_id":release_id,"released_at":released_at,"released_by":released_by,"input_snapshot_hash":snapshot_hash,"plan_hash":plan_hash,
            "validation_report_hash":dict(record.get("validation_report") or {}).get("report_hash",""),"reservation_ids":[str(x.get("reservation_id") or "") for x in list(run.get("stock_reservations") or [])],
            "neutral_job_manifest_hash":neutral["manifest_hash"],"part_artifact_links":links,"machine_transfer_allowed":False,
            "artifacts":[asdict(x) for x in artifacts],
        }
        manifest["manifest_hash"]=stable_sha256({k:v for k,v in manifest.items() if k!="manifest_hash"})
        atomic_write(root/"manifest.json",canonical_json_bytes(manifest))
    # tempfile/mkstemp defaults can leave the published package owner-only on
    # POSIX.  Normalize read permissions after atomic publication so operators
    # and verification tooling in the same environment can inspect the release.
    try:
        final_root.chmod(0o755)
        for published in final_root.rglob("*"):
            published.chmod(0o755 if published.is_dir() else 0o644)
    except OSError:
        # Windows chmod semantics are intentionally limited; content integrity
        # is enforced by the manifest hashes rather than POSIX mode bits.
        pass
    # deterministic zip published only after the directory itself is complete
    zip_path=final_root.with_suffix(".zip")
    fd,temp_name=tempfile.mkstemp(prefix=f".{zip_path.name}.",suffix=".tmp",dir=zip_path.parent); os.close(fd); temp=Path(temp_name)
    try:
        with zipfile.ZipFile(temp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
            for path in sorted(p for p in final_root.rglob("*") if p.is_file()):
                info=zipfile.ZipInfo(path.relative_to(final_root).as_posix(),date_time=(1980,1,1,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
                zf.writestr(info,path.read_bytes())
        os.replace(temp,zip_path)
    finally:
        temp.unlink(missing_ok=True)
    return NestingPackageResult(root=final_root,zip_path=zip_path,manifest=manifest,artifacts=artifacts)


def _safe_extract_release_zip(zip_path: Path, destination: Path, limits: ReleasePackageLimits = DEFAULT_RELEASE_PACKAGE_LIMITS) -> list[str]:
    """Extract a release ZIP without traversal, links, duplicates or ZIP bombs."""
    errors: list[str] = []
    seen: set[str] = set()
    total_uncompressed = 0
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > int(limits.max_entries):
            errors.append(f"zip bevat te veel entries: {len(infos)} > {limits.max_entries}")
            return errors
        for info in infos:
            raw_name = str(info.filename or "").replace("\\", "/")
            pure = PurePosixPath(raw_name)
            if not raw_name or len(raw_name) > int(limits.max_path_length) or pure.is_absolute() or ".." in pure.parts:
                errors.append(f"onveilige zip-entry: {raw_name!r}")
                continue
            normalized = pure.as_posix().rstrip("/")
            if not normalized:
                continue
            if normalized in seen:
                errors.append(f"dubbele zip-entry: {normalized}")
                continue
            seen.add(normalized)
            mode = (int(info.external_attr) >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                errors.append(f"symbolische link niet toegestaan in zip: {normalized}")
                continue
            if int(info.flag_bits) & 0x1:
                errors.append(f"versleutelde zip-entry niet toegestaan: {normalized}")
                continue
            size = int(info.file_size or 0)
            compressed = int(info.compress_size or 0)
            if size > int(limits.max_single_file_bytes):
                errors.append(f"zip-entry te groot: {normalized} ({size} bytes)")
                continue
            total_uncompressed += size
            if total_uncompressed > int(limits.max_total_uncompressed_bytes):
                errors.append("zip overschrijdt maximale totale ongecomprimeerde grootte")
                continue
            if size > 0:
                ratio = float(size) / float(max(1, compressed))
                if ratio > float(limits.max_compression_ratio):
                    errors.append(f"verdachte compressieverhouding: {normalized} ({ratio:.1f}:1)")
                    continue
            target = destination.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                # Bounded by the metadata/resource checks above.  ZipFile also
                # verifies CRC while reading the member.
                data = zf.read(info)
                if len(data) != size:
                    errors.append(f"zip-entry grootte wijkt af tijdens extractie: {normalized}")
                    continue
                target.write_bytes(data)
    return errors


def verify_release_package(path: str | Path, limits: ReleasePackageLimits = DEFAULT_RELEASE_PACKAGE_LIMITS) -> dict[str, Any]:
    root=Path(path)
    if root.is_file() and root.suffix.lower()==".zip":
        with tempfile.TemporaryDirectory(prefix="cws_nest_verify_") as td:
            extract_errors=_safe_extract_release_zip(root,Path(td),limits)
            if extract_errors:
                return {"valid":False,"errors":extract_errors,"zip_sha256":sha256_file(root),"limits":asdict(limits)}
            result=verify_release_package(td,limits); result["zip_sha256"]=sha256_file(root); return result
    manifest_path=root/"manifest.json"
    if not manifest_path.is_file(): return {"valid":False,"errors":["manifest.json ontbreekt"],"limits":asdict(limits)}
    try:
        if manifest_path.stat().st_size > int(limits.max_single_file_bytes):
            return {"valid":False,"errors":["manifest.json overschrijdt bestandsgroottelimiet"],"limits":asdict(limits)}
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"valid":False,"errors":[f"manifest.json is ongeldig: {exc}"],"limits":asdict(limits)}
    errors=[]
    if str(manifest.get("format") or "")!=PACKAGE_FORMAT:
        errors.append("onbekend release package format")
    if bool(manifest.get("machine_transfer_allowed")):
        errors.append("release manifest staat ten onrechte machineoverdracht toe")
    stored=str(manifest.get("manifest_hash") or ""); expected=stable_sha256({k:v for k,v in manifest.items() if k!="manifest_hash"})
    if stored!=expected: errors.append("manifest_hash mismatch")

    raw_artifacts=list(manifest.get("artifacts") or [])
    if len(raw_artifacts)>int(limits.max_manifest_artifacts):
        errors.append(f"manifest bevat te veel artefacten: {len(raw_artifacts)} > {limits.max_manifest_artifacts}")
    expected_files={"manifest.json"}
    seen_paths=set()
    expected_total=manifest_path.stat().st_size
    for raw in raw_artifacts[: int(limits.max_manifest_artifacts)+1]:
        rel=str(raw.get("relative_path") or "").replace("\\","/")
        pure=PurePosixPath(rel)
        if not rel or len(rel)>int(limits.max_path_length) or pure.is_absolute() or ".." in pure.parts:
            errors.append(f"onveilig artefactpad in manifest: {rel!r}")
            continue
        rel=pure.as_posix()
        if rel in seen_paths:
            errors.append(f"dubbel artefactpad in manifest: {rel}")
            continue
        seen_paths.add(rel); expected_files.add(rel)
        stored_artifact_hash=str(raw.get("artifact_hash") or "")
        artifact_payload=dict(raw); artifact_payload.pop("artifact_hash",None)
        if not stored_artifact_hash or stable_sha256(artifact_payload)!=stored_artifact_hash:
            errors.append(f"artifact_hash mismatch: {rel}")
        target=root.joinpath(*pure.parts)
        if target.is_symlink():
            errors.append(f"symbolische link niet toegestaan: {rel}")
        elif not target.is_file():
            errors.append(f"artefact ontbreekt: {rel}")
        else:
            size=target.stat().st_size; expected_total+=size
            if size>int(limits.max_single_file_bytes): errors.append(f"artefact te groot: {rel}")
            if sha256_file(target)!=str(raw.get("sha256") or ""):
                errors.append(f"checksum mismatch: {rel}")
            if int(raw.get("size_bytes") or -1)!=size:
                errors.append(f"bestandsgrootte mismatch: {rel}")
    if expected_total>int(limits.max_total_uncompressed_bytes):
        errors.append("package overschrijdt maximale totale grootte")

    actual_files=set(); actual_total=0
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_symlink():
                errors.append(f"symbolische link niet toegestaan in package: {p.relative_to(root).as_posix()}")
                continue
            if p.is_file():
                rel=p.relative_to(root).as_posix(); actual_files.add(rel); actual_total += p.stat().st_size
                if len(actual_files)>int(limits.max_entries):
                    errors.append(f"package bevat te veel bestanden: > {limits.max_entries}"); break
    if actual_total>int(limits.max_total_uncompressed_bytes):
        errors.append("package overschrijdt maximale totale bestandsgrootte")
    for rel in sorted(actual_files-expected_files):
        errors.append(f"onvermeld artefact in package: {rel}")
    for rel in sorted(expected_files-actual_files):
        errors.append(f"verwacht packagebestand ontbreekt: {rel}")

    neutral=root/"neutral_job"/"neutral_profile_cut_job.json"
    if neutral.is_file():
        try:
            payload=json.loads(neutral.read_text(encoding="utf-8"))
            mh=str(payload.get("manifest_hash") or ""); calc=stable_sha256({k:v for k,v in payload.items() if k!="manifest_hash"})
            if mh!=calc: errors.append("neutral job manifest hash mismatch")
            if str(manifest.get("neutral_job_manifest_hash") or "")!=mh: errors.append("neutral job hash wijkt af van release manifest")
            if bool(dict(payload.get("machine_transfer") or {}).get("allowed")): errors.append("neutral job staat ten onrechte machineoverdracht toe")
        except Exception as exc:
            errors.append(f"neutral jobmanifest is ongeldig: {exc}")
    else: errors.append("neutral jobmanifest ontbreekt")
    return {"valid":not errors,"errors":errors,"manifest_hash":stored,"artifact_count":len(raw_artifacts),"limits":asdict(limits),"total_bytes":actual_total}


__all__=["ReleasePackageLimits","DEFAULT_RELEASE_PACKAGE_LIMITS","PACKAGE_FORMAT","NEUTRAL_JOB_FORMAT","REPORT_SCHEMA_VERSION","NestingOutputArtifact","NestingPackageResult","build_release_report","build_neutral_job_manifest","create_release_package","verify_release_package"]
