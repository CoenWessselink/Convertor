"""Deterministic synthetic benchmark/fuzz fixtures for Profile Nesting phase 8.

Synthetic fixtures prove software behaviour and performance only. They are not
owner-validated engineering truth and never unlock the production release gate.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import random
import tempfile
import time
import tracemalloc
from typing import Any

from cws_convertor.project.model import Part, ProjectModel, ReviewStatus
from cws_convertor.project.storage import ProjectStore
from .machine import MachineOptimizationProfile
from .stock import PurchaseOption
from .configuration import set_machine_profile, set_purchase_option
from .phase4 import solve_and_register_phase4
from .angle_validator import validate_angle_plan
from .serialization import input_snapshot_from_dict, plan_from_dict

BENCHMARK_FIXTURE_VERSION = "1.0"


def _cut(angle: float = 0.0, *, common: bool = False) -> dict[str, Any]:
    return {"status": "exact", "primary_angle_deg": float(angle), "secondary_angle_deg": 0.0, "common_cut_allowed": bool(common), "tolerance_mm": 0.1}


def build_synthetic_benchmark_project(
    piece_count: int,
    *,
    angle: bool = False,
    project_name: str = "Profile Nesting benchmark",
    stock_length_mm: float = 12000.0,
    released_parts: bool = True,
) -> ProjectModel:
    if piece_count < 1:
        raise ValueError("piece_count moet positief zijn")
    project = ProjectModel.new(project_name)
    rng = random.Random(20260814 + int(piece_count) + (100000 if angle else 0))
    # Keep the number of demand lines bounded while scaling instance count.
    distinct = min(32, max(1, piece_count))
    remaining = piece_count
    for index in range(distinct):
        slots_left = distinct - index
        quantity = remaining // slots_left
        remaining -= quantity
        length = 650.0 + ((index * 613) % 4300) + rng.randint(0, 120) / 10.0
        if angle:
            angle_values = [0.0, 15.0, 30.0, 45.0, -15.0, -30.0]
            start = _cut(angle_values[index % len(angle_values)], common=False)
            end = _cut(angle_values[(index * 3 + 1) % len(angle_values)], common=False)
        else:
            start = _cut(0.0)
            end = _cut(0.0)
        part = Part(
            internal_id=f"bench-part-{index:03d}", name=f"BENCH-{index:03d}", part_position=f"B{index:03d}",
            profile="RHS100x50", normalized_profile="RHS100x50", profile_type="rhs",
            material="S235JR", normalized_material="S235JR", material_grade="S235JR",
            length_mm=length, quantity_total=quantity, reference_sides=["front"],
            status=ReviewStatus.RELEASED.value if released_parts else ReviewStatus.VALIDATED.value,
            geometry_descriptor={"section_hash": "sec-rhs100x50"}, production_features=[],
            properties={
                "profile_nesting_cuts": {"start": start, "end": end},
                "profile_section_geometry": {"kind": "rectangle", "width_mm": 100.0, "height_mm": 50.0},
                "profile_dimensions_mm": {"width": 100.0, "height": 50.0},
                "allowed_orientations": ["as_modeled"],
                "orientation_equivalence_evidence": {},
            },
        )
        part.recompute_hashes()
        project.parts[part.internal_id] = part
    set_machine_profile(project, MachineOptimizationProfile(
        profile_id="bench-saw-v1", machine_id="BENCH-SAW", machine_group="Synthetic benchmark saw",
        validation_status="validated", supported_profile_types=["box"], supported_materials=["S235JR"],
        supported_operations=["saw"], supported_sides=["front", "back", "top", "bottom"],
        allowed_rotations_deg=[0.0, 180.0], max_part_length_mm=20000.0, max_stock_length_mm=24000.0,
        kerf_mm=2.7, head_trim_mm=30.0, tail_trim_mm=20.0, safety_length_mm=0.0,
        min_saw_angle_deg=-60.0, max_saw_angle_deg=60.0, angle_tolerance_deg=0.01,
        machine_tolerance_mm=0.1, position_tolerance_mm=0.1, common_cut_policy="supported",
        compound_cut_policy="supported",
    ))
    # Effectively unlimited synthetic purchase option for stress runs.
    set_purchase_option(project, PurchaseOption(
        purchase_option_id="bench-stock", supplier_article="SYNTH-BENCH", profile_id="RHS100x50",
        section_hash="sec-rhs100x50", material="S235JR", material_grade="S235JR",
        length_mm=stock_length_mm, available_quantity=max(piece_count, 8), unit_price=100.0,
    ))
    return project


def run_synthetic_case(case_id: str, piece_count: int, *, angle: bool, backend: str = "greedy", exact_max: int = 7) -> dict[str, Any]:
    project = build_synthetic_benchmark_project(piece_count, angle=angle, project_name=case_id)
    tracemalloc.start()
    started = time.perf_counter()
    run, snapshot, _demand, _context, plan, evidence, validation, _reservation = solve_and_register_phase4(
        project,
        backend=backend,
        scenario_id=case_id,
        scenario_family="waste",
        solver_configuration={"angle_exact_max_pieces": exact_max, "node_limit": 500000, "transition_matrix_max_unique_lines": 50},
    )
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    valid = bool(plan is not None and validation is not None and validation.valid)
    return {
        "case_id": case_id,
        "status": "passed" if valid else "failed",
        "piece_count": piece_count,
        "angle": angle,
        "backend_requested": backend,
        "backend_used": evidence.backend,
        "solver_status": evidence.status,
        "runtime_seconds": elapsed,
        "solver_runtime_seconds": evidence.runtime_seconds,
        "peak_tracemalloc_bytes": int(peak),
        "bar_count": len(plan.bars) if plan else 0,
        "plan_hash": plan.plan_hash if plan else "",
        "validation_hash": validation.report_hash if validation else "",
        "balance_delta_units": int(plan.material_balance.balance_delta_units) if plan else None,
        "nodes_explored": int(evidence.nodes_explored),
    }


def run_save_reopen_case(piece_count: int = 750) -> dict[str, Any]:
    project = build_synthetic_benchmark_project(piece_count, angle=False, project_name="save_reopen_large")
    run, _snapshot, _demand, _context, plan, _evidence, validation, _reservation = solve_and_register_phase4(
        project, backend="greedy", scenario_id="save-reopen-large", solver_configuration={"transition_matrix_max_unique_lines": 40}
    )
    started = time.perf_counter()
    tracemalloc.start()
    with tempfile.TemporaryDirectory(prefix="cws_nest_bench_") as td:
        path = Path(td) / "benchmark.cwscproj"
        ProjectStore().save(project, path, embed_sources=False)
        restored = ProjectStore().open(path, read_only=True).project
        restored.validate()
        restored_record = restored.profile_nesting_runs[run.run_id]
        restored_plan = plan_from_dict(dict(restored_record["plan"]))
        restored_snapshot = input_snapshot_from_dict(dict(restored_record["input_snapshot"]))
        report = validate_angle_plan(restored_snapshot, restored_plan)
        package_bytes = path.stat().st_size
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    valid = bool(plan is not None and validation and validation.valid and report.valid)
    return {
        "case_id": "save_reopen_large", "status": "passed" if valid else "failed", "piece_count": piece_count,
        "runtime_seconds": elapsed, "peak_tracemalloc_bytes": int(peak), "cwscproj_bytes": int(package_bytes),
        "plan_hash": plan.plan_hash if plan else "", "reopened_plan_hash": restored_plan.plan_hash if valid else "",
        "validation_hash": report.report_hash if valid else "",
    }


__all__ = ["BENCHMARK_FIXTURE_VERSION", "build_synthetic_benchmark_project", "run_synthetic_case", "run_save_reopen_case"]
