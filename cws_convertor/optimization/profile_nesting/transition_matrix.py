"""Deterministic, geometry-backed transition matrix materialisation for phase 4.

The angle solver can evaluate transitions lazily while searching.  This module
materialises the same *allowed transition space* per demand-line/orientation
pair for diagnostics, UI evidence and focused regression tests.  It operates on
unique demand lines, never on every quantity instance, so repeated parts do not
cause a quadratic piece-instance explosion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from cws_convertor.project.model import stable_sha256
from .angle_geometry import AngleGeometryError, build_orientation_variants, build_transition
from .units import LengthKernel

TRANSITION_MATRIX_SCHEMA_VERSION = "1.0"


@dataclass
class TransitionMatrixEntry:
    left_demand_line_id: str
    right_demand_line_id: str
    left_variant_id: str
    right_variant_id: str
    machine_profile_id: str
    machine_id: str
    status: str
    common_cut: bool = False
    geometry_delta_units: int = 0
    kerf_projection_units: int = 0
    extra_loss_units: int = 0
    required_reference_gap_units: int = 0
    cut_count: int = 0
    transition_hash: str = ""
    proof: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    entry_hash: str = ""

    def refresh_hash(self) -> str:
        payload=asdict(self);payload.pop("entry_hash",None)
        self.entry_hash=stable_sha256(payload);return self.entry_hash


@dataclass
class TransitionMatrix:
    input_snapshot_hash: str
    entries: list[TransitionMatrixEntry]
    schema_version: str = TRANSITION_MATRIX_SCHEMA_VERSION
    status: str = "complete"
    unique_line_count: int = 0
    machine_profile_count: int = 0
    exact_entry_count: int = 0
    unsupported_entry_count: int = 0
    matrix_hash: str = ""

    def refresh_hash(self) -> str:
        for entry in self.entries:entry.refresh_hash()
        payload=asdict(self);payload.pop("matrix_hash",None)
        self.matrix_hash=stable_sha256(payload);return self.matrix_hash

    def to_dict(self)->dict[str,Any]:return asdict(self)


def _kernel(snapshot) -> LengthKernel:
    units=dict(getattr(snapshot,"units",{}) or {})
    return LengthKernel(units_per_mm=int(units.get("units_per_mm") or 1000))


def _machine_valid(orientation,machine:dict[str,Any])->bool:
    lo=float(machine.get("min_saw_angle_deg",-90));hi=float(machine.get("max_saw_angle_deg",90));tol=float(machine.get("angle_tolerance_deg",0.01) or 0.01)
    for cut in (orientation.variant.start_cut,orientation.variant.end_cut):
        p=float(cut.primary_angle_deg);s=float(cut.secondary_angle_deg)
        if p<lo-tol or p>hi+tol:return False
        if abs(s)>tol and str(machine.get("compound_cut_policy") or "blocked")!="supported":return False
    return True


def _base_pair_compatible(left:dict[str,Any],right:dict[str,Any])->bool:
    return (
        str(left.get("section_hash") or "")==str(right.get("section_hash") or "")
        and str(left.get("material") or "")==str(right.get("material") or "")
        and str(left.get("material_grade") or "")==str(right.get("material_grade") or "")
        and str(left.get("heat_requirement") or "")==str(right.get("heat_requirement") or "")
        and str(left.get("certificate_requirement") or "")==str(right.get("certificate_requirement") or "")
    )


def build_transition_matrix(snapshot, *, max_unique_lines: int = 50) -> TransitionMatrix:
    lines=[dict(x) for x in list(getattr(snapshot,"demand_lines",[]) or []) if str((x or {}).get("eligibility_status") or "")=="eligible"]
    lines=sorted(lines,key=lambda x:str(x.get("demand_line_id") or ""))
    machines=[dict(x) for x in list(dict(getattr(snapshot,"machine_snapshot",{}) or {}).get("profiles") or []) if str((x or {}).get("validation_status") or "") in {"validated","released"}]
    machines=sorted(machines,key=lambda x:(str(x.get("profile_id") or ""),str(x.get("machine_id") or "")))
    if len(lines)>int(max_unique_lines):
        matrix=TransitionMatrix(input_snapshot_hash=str(snapshot.snapshot_hash),entries=[],status="lazy_not_materialized",unique_line_count=len(lines),machine_profile_count=len(machines))
        matrix.refresh_hash();return matrix
    kernel=_kernel(snapshot);entries=[]
    for machine in machines:
        variant_cache={}
        for line in lines:
            line_id = str(line.get("demand_line_id") or "")
            candidate_machine_ids = {str(v) for v in list(line.get("candidate_machine_ids") or []) if str(v)}
            if candidate_machine_ids and str(machine.get("machine_id") or "") not in candidate_machine_ids:
                variant_cache[line_id] = []
                continue
            try:
                variant_cache[line_id]=[v for v in build_orientation_variants(line,machine,kernel=kernel,require_exact=True) if _machine_valid(v,machine)]
            except AngleGeometryError:
                variant_cache[line_id]=[]
        for left in lines:
            left_id=str(left.get("demand_line_id") or "")
            for right in lines:
                right_id=str(right.get("demand_line_id") or "")
                machine_id = str(machine.get("machine_id") or "")
                left_machine_ids = {str(v) for v in list(left.get("candidate_machine_ids") or []) if str(v)}
                right_machine_ids = {str(v) for v in list(right.get("candidate_machine_ids") or []) if str(v)}
                if (left_machine_ids and machine_id not in left_machine_ids) or (right_machine_ids and machine_id not in right_machine_ids):
                    continue
                if not _base_pair_compatible(left,right):continue
                lv=variant_cache.get(left_id,[]);rv=variant_cache.get(right_id,[])
                if not lv or not rv:
                    entry=TransitionMatrixEntry(left_id,right_id,"","",str(machine.get("profile_id") or ""),str(machine.get("machine_id") or ""),"unsupported",reason="no_exact_machine_valid_orientation")
                    entry.refresh_hash();entries.append(entry);continue
                for left_orientation in lv:
                    for right_orientation in rv:
                        try:
                            tg=build_transition(left,right,f"line:{left_id}",left_orientation,f"line:{right_id}",right_orientation,machine,kernel=kernel,allow_common_cut=True,require_exact=True)
                            t=tg.transition
                            entry=TransitionMatrixEntry(
                                left_id,right_id,left_orientation.variant.variant_id,right_orientation.variant.variant_id,
                                str(machine.get("profile_id") or ""),str(machine.get("machine_id") or ""),"exact",
                                common_cut=bool(t.common_cut),geometry_delta_units=int(t.geometry_delta_units),kerf_projection_units=int(t.kerf_projection_units),
                                extra_loss_units=int(t.extra_loss_units),required_reference_gap_units=int(t.required_reference_gap_units),cut_count=int(t.cut_count),
                                transition_hash=t.transition_hash,proof=dict(t.proof),
                            )
                        except AngleGeometryError as exc:
                            entry=TransitionMatrixEntry(left_id,right_id,left_orientation.variant.variant_id,right_orientation.variant.variant_id,str(machine.get("profile_id") or ""),str(machine.get("machine_id") or ""),"unsupported",reason=str(exc))
                        entry.refresh_hash();entries.append(entry)
    entries.sort(key=lambda e:(e.machine_profile_id,e.left_demand_line_id,e.left_variant_id,e.right_demand_line_id,e.right_variant_id,e.status))
    matrix=TransitionMatrix(
        input_snapshot_hash=str(snapshot.snapshot_hash),entries=entries,unique_line_count=len(lines),machine_profile_count=len(machines),
        exact_entry_count=sum(e.status=="exact" for e in entries),unsupported_entry_count=sum(e.status!="exact" for e in entries),
    )
    matrix.refresh_hash();return matrix


__all__=["TRANSITION_MATRIX_SCHEMA_VERSION","TransitionMatrixEntry","TransitionMatrix","build_transition_matrix"]
