"""Demand extraction, eligibility and grouping for profile nesting.

This module only consumes current ProjectModel state. It does not import CAD
files and does not infer missing production geometry.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Iterable
from uuid import UUID, uuid5

from cws_convertor.project.model import Part, ProjectModel, ReviewStatus, stable_sha256, utc_now_iso
from .models import (
    CutRequirement,
    CutStatus,
    EligibilityStatus,
    NestingDemandLine,
    NestingEligibilityReport,
    NestingMessage,
    PieceInstance,
)
from .units import LengthKernel, LengthKernelError
from .angle_geometry import AngleGeometryError, canonicalize_cut_requirement

_SUPPORTED_PROFILE_TYPES = {
    "i", "i_profile", "hea", "heb", "hem", "ipe", "u", "u_profile", "upn", "unp",
    "l", "angle", "t", "t_profile", "rhs", "shs", "chs", "tube", "pipe", "round",
    "round_bar", "flat", "strip", "bar", "profile", "c_profile", "c",
}
_INSTANCE_NAMESPACE = UUID("4e205d4a-b665-4f04-881f-18cb66a53535")


def _message(code: str, text: str, part: Part, *, blocking: bool = True, severity: str = "error") -> NestingMessage:
    return NestingMessage(
        code=code,
        severity=severity,
        message=text,
        blocking=blocking,
        object_ids=[part.internal_id],
    )


def _section_hash(part: Part) -> str:
    descriptor = dict(part.geometry_descriptor or {})
    explicit = str(
        descriptor.get("section_hash")
        or descriptor.get("profile_section_hash")
        or part.properties.get("section_hash", "")
    ).strip()
    if explicit:
        return explicit
    # Geometry hash is conservative: it prevents accidental grouping when an
    # exact section identity is not separately available.  It may create more
    # groups, never unsafe coalescing.
    return part.geometry_hash


def _confirmed_reference_frame(part: Part) -> bool:
    state = dict(part.workbench or {})
    if not state:
        return bool(part.reference_sides)
    revision = dict(state.get("current_revision") or {})
    sides = list(revision.get("reference_sides") or [])
    confirmed = [item for item in sides if isinstance(item, dict) and bool(item.get("confirmed"))]
    return bool(confirmed or part.reference_sides)


def _cuts(part: Part) -> tuple[CutRequirement, CutRequirement, list[NestingMessage]]:
    raw = dict(part.properties.get("profile_nesting_cuts") or {})
    issues: list[NestingMessage] = []
    if raw:
        start = CutRequirement(**{k: v for k, v in dict(raw.get("start") or {}).items() if k in CutRequirement.__dataclass_fields__})
        end = CutRequirement(**{k: v for k, v in dict(raw.get("end") or {}).items() if k in CutRequirement.__dataclass_fields__})
        try:
            canonicalize_cut_requirement(start, reference="start")
            canonicalize_cut_requirement(end, reference="end")
        except AngleGeometryError as exc:
            start.status = CutStatus.UNSUPPORTED.value if start.status == CutStatus.EXACT.value else start.status
            end.status = CutStatus.UNSUPPORTED.value if end.status == CutStatus.EXACT.value else end.status
            start.refresh_hash(); end.refresh_hash()
            issues.append(_message("CWS-NEST-006", f"Zaagvlak kan niet exact worden genormaliseerd: {exc}", part))
        if start.status == CutStatus.UNSUPPORTED.value or end.status == CutStatus.UNSUPPORTED.value:
            issues.append(_message("CWS-NEST-006", "Start- of eindzaagvoorwaarde is niet ondersteund.", part))
        return start, end, issues
    # A plain square cut is exact only when explicitly marked, or for a clean
    # reviewed constant-section part with no end-operation ambiguity.
    square_explicit = bool(part.properties.get("square_end_cuts_confirmed", False))
    status = CutStatus.EXACT.value if square_explicit else CutStatus.REVIEW.value
    common_allowed = bool(part.properties.get("common_cut_allowed", False))
    start = CutRequirement(status=status, reference="start", common_cut_allowed=common_allowed)
    end = CutRequirement(status=status, reference="end", common_cut_allowed=common_allowed)
    if status == CutStatus.EXACT.value:
        canonicalize_cut_requirement(start, reference="start")
        canonicalize_cut_requirement(end, reference="end")
    else:
        start.refresh_hash(); end.refresh_hash()
    if not square_explicit:
        issues.append(_message(
            "CWS-NEST-006",
            "Start- en eindzaagconditie zijn nog niet expliciet bevestigd.",
            part,
            blocking=False,
            severity="warning",
        ))
    return start, end, issues


def _assembly_marks(project: ProjectModel, part: Part) -> list[str]:
    values: list[str] = []
    for assembly_id in sorted(part.assembly_ids):
        assembly = project.assemblies.get(assembly_id)
        if assembly and assembly.assembly_mark:
            values.append(assembly.assembly_mark)
    return sorted(set(values))


def _group_key(part: Part, *, section_hash: str, machine_class: str = "unassigned") -> str:
    payload = {
        "section_hash": section_hash,
        "profile": part.normalized_profile or part.profile,
        "material": part.normalized_material or part.material,
        "grade": part.material_grade,
        "heat_policy": str(part.properties.get("heat_policy") or "default"),
        "certificate_policy": str(part.properties.get("certificate_policy") or "default"),
        "machine_class": machine_class,
        "coating_constraint": str(part.properties.get("nesting_coating_constraint") or ""),
        "production_batch": str(part.properties.get("production_batch") or ""),
        "orientation_policy": str(part.properties.get("orientation_policy") or "as_modeled"),
        "units": "mm",
        "tolerance_set": part.tolerances,
    }
    return stable_sha256(payload)


def evaluate_part(
    project: ProjectModel,
    part: Part,
    *,
    mode: str = "production",
    kernel: LengthKernel | None = None,
    candidate_machine_ids: list[str] | None = None,
    defer_machine_compatibility: bool = False,
) -> NestingDemandLine:
    if mode not in {"concept", "production"}:
        raise ValueError("mode moet 'concept' of 'production' zijn")
    kernel = kernel or LengthKernel()
    reasons: list[NestingMessage] = []

    if not part.manufacturing_hash:
        reasons.append(_message("CWS-NEST-004", "Actuele manufacturing hash ontbreekt.", part))
    else:
        try:
            part.validate_hashes()
        except Exception as exc:
            reasons.append(_message("CWS-NEST-004", f"Manufacturing hash is stale of ongeldig: {exc}", part))

    profile_name = (part.normalized_profile or part.profile).strip()
    section_hash = _section_hash(part)
    if not profile_name or not section_hash:
        reasons.append(_message("CWS-NEST-002", "Profiel/section identity ontbreekt.", part))

    profile_type = (part.profile_type or "").strip().lower()
    if profile_type and profile_type not in _SUPPORTED_PROFILE_TYPES:
        reasons.append(_message("CWS-NEST-005", f"Profieltype {part.profile_type!r} valt niet in de huidige 1D-scope.", part))

    material = (part.normalized_material or part.material).strip()
    grade = part.material_grade.strip()
    if not material or not grade:
        reasons.append(_message("CWS-NEST-003", "Materiaal en/of kwaliteit ontbreekt.", part))

    try:
        quantized = kernel.quantize_mm(part.length_mm)
        if quantized.units <= 0:
            raise LengthKernelError("Lengte moet groter zijn dan nul")
    except LengthKernelError as exc:
        quantized = kernel.quantize_mm(0)
        reasons.append(_message("CWS-NEST-001", str(exc), part))

    if not _confirmed_reference_frame(part):
        reasons.append(_message("CWS-NEST-007", "Productieframe/referentiezijde is niet bevestigd.", part))

    start_cut, end_cut, cut_issues = _cuts(part)
    general_finish = float(part.properties.get("finish_allowance_mm", 0.0) or 0.0)
    if general_finish < 0:
        reasons.append(_message("CWS-NEST-006", "Finish-/slijptoegift mag niet negatief zijn.", part))
    elif general_finish > 0:
        if float(start_cut.finish_allowance_mm or 0.0) == 0.0: start_cut.finish_allowance_mm = general_finish
        if float(end_cut.finish_allowance_mm or 0.0) == 0.0: end_cut.finish_allowance_mm = general_finish
        if start_cut.status == CutStatus.EXACT.value: canonicalize_cut_requirement(start_cut, reference="start")
        if end_cut.status == CutStatus.EXACT.value: canonicalize_cut_requirement(end_cut, reference="end")
    reasons.extend(cut_issues)

    if part.blocking_issues():
        reasons.append(_message("CWS-NEST-004", "Onderdeel heeft nog blokkerende productieissues.", part))

    if mode == "production":
        workbench_status = str(dict(part.workbench or {}).get("current_revision", {}).get("review_status") or part.status)
        if workbench_status not in {ReviewStatus.VALIDATED.value, ReviewStatus.RELEASED.value}:
            reasons.append(_message("CWS-NEST-004", "Productiemodus vereist een gevalideerd of vrijgegeven onderdeel.", part))

    if candidate_machine_ids is None:
        candidate_machine_ids = sorted(
            str(item) for item in list(part.properties.get("nesting_candidate_machine_ids") or []) if str(item)
        )
    else:
        candidate_machine_ids = sorted(str(item) for item in candidate_machine_ids if str(item))
    if not candidate_machine_ids and not defer_machine_compatibility:
        reasons.append(_message(
            "CWS-NEST-008",
            "Geen geschikte profielnestingmachine bewezen.",
            part,
            blocking=(mode == "production"),
            severity="error" if mode == "production" else "warning",
        ))

    blocking = any(item.blocking for item in reasons)
    review = any(not item.blocking for item in reasons)
    status = EligibilityStatus.BLOCKED.value if blocking else (EligibilityStatus.REVIEW.value if review else EligibilityStatus.ELIGIBLE.value)
    group_key = _group_key(part, section_hash=section_hash)
    line_id = stable_sha256({
        "project_id": project.project_id,
        "part_id": part.internal_id,
        "manufacturing_hash": part.manufacturing_hash,
        "group_key": group_key,
    })
    return NestingDemandLine(
        demand_line_id=line_id,
        group_key=group_key,
        part_id=part.internal_id,
        part_position=part.part_position,
        manufacturing_hash=part.manufacturing_hash,
        assembly_marks=_assembly_marks(project, part),
        profile_id=profile_name,
        profile_name=profile_name,
        section_hash=section_hash,
        profile_type=part.profile_type,
        profile_dimensions_mm={str(k): float(v) for k, v in dict(part.properties.get("profile_dimensions_mm") or part.geometry_descriptor.get("section_dimensions_mm") or {}).items()},
        section_geometry=dict(part.properties.get("profile_section_geometry") or part.geometry_descriptor.get("section_geometry") or {}),
        material=material,
        material_grade=grade,
        heat_requirement=str(part.properties.get("heat_requirement") or ""),
        certificate_requirement=str(part.properties.get("certificate_requirement") or ""),
        nominal_length_mm=part.length_mm,
        nominal_length_units=quantized.units,
        quantity=max(0, int(part.quantity_total)),
        start_cut=start_cut,
        end_cut=end_cut,
        production_tolerance_mm=float(part.tolerances.get("length_mm", 0.0) or 0.0),
        finish_allowance_mm=float(part.properties.get("finish_allowance_mm", 0.0) or 0.0),
        relevant_features=list(part.production_features),
        allowed_orientations=list(part.properties.get("allowed_orientations") or ["as_modeled"]),
        orientation_equivalence_evidence=dict(part.properties.get("orientation_equivalence_evidence") or {}),
        candidate_machine_ids=candidate_machine_ids,
        production_batch=str(part.properties.get("production_batch") or ""),
        priority=int(part.properties.get("production_priority") or 0),
        due_date=str(part.properties.get("due_date") or ""),
        eligibility_status=status,
        eligibility_reasons=reasons,
    )


def extract_demand(
    project: ProjectModel,
    *,
    mode: str = "production",
    kernel: LengthKernel | None = None,
    candidate_machine_ids_by_part: dict[str, list[str]] | None = None,
    defer_machine_compatibility: bool = False,
) -> NestingEligibilityReport:
    kernel = kernel or LengthKernel()
    project_revision_hash = project.revision_content_sha256()
    lines: list[NestingDemandLine] = []
    instances: list[PieceInstance] = []
    report_messages: list[NestingMessage] = []

    for part_id in sorted(project.parts):
        part = project.parts[part_id]
        if part.category != "make_part":
            continue
        line = evaluate_part(
            project, part, mode=mode, kernel=kernel,
            candidate_machine_ids=(candidate_machine_ids_by_part or {}).get(part.internal_id) if candidate_machine_ids_by_part is not None else None,
            defer_machine_compatibility=defer_machine_compatibility,
        )
        lines.append(line)
        for ordinal in range(1, max(0, line.quantity) + 1):
            instance_id = str(uuid5(
                _INSTANCE_NAMESPACE,
                f"{project.project_id}|{line.demand_line_id}|{ordinal}",
            ))
            instances.append(PieceInstance(
                instance_id=instance_id,
                demand_line_id=line.demand_line_id,
                part_id=line.part_id,
                manufacturing_hash=line.manufacturing_hash,
                quantity_ordinal=ordinal,
                part_position=line.part_position,
                assembly_context=list(line.assembly_marks),
                project_phase=project.project_phase,
                production_batch=line.production_batch,
                priority=line.priority,
                due_date=line.due_date,
            ))
        report_messages.extend(line.eligibility_reasons)

    report = NestingEligibilityReport(
        mode=mode,
        generated_at=utc_now_iso(),
        project_id=project.project_id,
        project_revision_hash=project_revision_hash,
        demand_lines=lines,
        piece_instances=instances,
        messages=report_messages,
    )
    report.refresh_hash()
    return report
