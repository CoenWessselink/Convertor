"""Independent reconstruction validator for phase-4 angle-aware nesting plans."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .angle_geometry import (
    AngleGeometryError,
    build_orientation_variants,
    canonical_plane,
)
from .models import CutRequirement
from .results import PlanValidationReport
from .units import LengthKernel
from cws_convertor.project.model import stable_sha256


def _issue(code: str, message: str, *, object_ids=None, details=None) -> dict[str, Any]:
    return {
        "code": code, "severity": "error", "message": message, "blocking": True,
        "object_ids": list(object_ids or []), "technical_details": dict(details or {}),
    }


def _kernel(snapshot) -> LengthKernel:
    units = dict(getattr(snapshot, "units", {}) or {})
    return LengthKernel(units_per_mm=int(units.get("units_per_mm") or 1000))


def _interval_conflicts(zones: list[tuple[int, int]], start: int, end: int) -> bool:
    a,b=min(start,end),max(start,end)
    for z0,z1 in zones:
        if a == b:
            if z0 <= a < z1: return True
        elif max(a,z0) < min(b,z1): return True
    return False


def _machine_angle_valid(orientation, machine: dict[str, Any]) -> bool:
    lo=float(machine.get("min_saw_angle_deg",-90.0)); hi=float(machine.get("max_saw_angle_deg",90.0)); tol=float(machine.get("angle_tolerance_deg",0.01) or 0.01)
    for cut in (orientation.variant.start_cut, orientation.variant.end_cut):
        if float(cut.primary_angle_deg) < lo-tol or float(cut.primary_angle_deg) > hi+tol: return False
        if abs(float(cut.secondary_angle_deg)) > tol and str(machine.get("compound_cut_policy") or "blocked") != "supported": return False
    return True


def _vfloat(value: Any, label: str) -> float:
    import math
    try: result=float(value)
    except (TypeError,ValueError) as exc: raise AngleGeometryError(f"Ongeldige {label}") from exc
    if not math.isfinite(result): raise AngleGeometryError(f"{label} is niet eindig")
    return result


def _vdim(dims: dict[str,Any], *names: str) -> float | None:
    lowered={str(k).lower():v for k,v in dims.items()}
    for name in names:
        if name.lower() in lowered:
            try: value=float(lowered[name.lower()])
            except (TypeError,ValueError): continue
            if value>0: return value
    return None


def _validator_profile_vertices(ptype: str, dims: dict[str,Any]) -> list[tuple[float,float]] | None:
    width=_vdim(dims,"width","width_mm","b"); height=_vdim(dims,"height","height_mm","h")
    tw=_vdim(dims,"web_thickness","web_thickness_mm","tw","t_w"); tf=_vdim(dims,"flange_thickness","flange_thickness_mm","tf","t_f"); t=_vdim(dims,"thickness","thickness_mm","t")
    if not width or not height:return None
    b2=width/2;h2=height/2
    if ptype in {"i","i_profile","hea","heb","hem","ipe"} and tw and tf and tw<=width and 2*tf<=height:
        w2=tw/2;return [(-b2,-h2),(b2,-h2),(b2,-h2+tf),(w2,-h2+tf),(w2,h2-tf),(b2,h2-tf),(b2,h2),(-b2,h2),(-b2,h2-tf),(-w2,h2-tf),(-w2,-h2+tf),(-b2,-h2+tf)]
    if ptype in {"u","u_profile","upn","unp","c","c_profile"} and tw and tf and tw<=width and 2*tf<=height:
        left=-b2;wr=left+tw;return [(left,-h2),(b2,-h2),(b2,-h2+tf),(wr,-h2+tf),(wr,h2-tf),(b2,h2-tf),(b2,h2),(left,h2)]
    if ptype in {"l","l_profile","angle"} and t and t<=min(width,height):
        left=-b2;bottom=-h2;return [(left,bottom),(b2,bottom),(b2,bottom+t),(left+t,bottom+t),(left+t,h2),(left,h2)]
    if ptype in {"t","t_profile"} and tw and tf and tw<=width and tf<=height:
        w2=tw/2;return [(-b2,h2-tf),(b2,h2-tf),(b2,h2),(-b2,h2),(-b2,h2-tf),(-w2,h2-tf),(-w2,-h2),(w2,-h2),(w2,h2-tf)]
    return None


def _validator_section(line: dict[str,Any]) -> tuple[str,Any]:
    explicit=dict(line.get("section_geometry") or {})
    if explicit:
        kind=str(explicit.get("kind") or explicit.get("type") or "").lower()
        if kind in {"polygon","wire"}:
            pts=[]
            for raw in list(explicit.get("vertices_yz") or explicit.get("vertices") or []):
                if isinstance(raw,dict):y,z=raw.get("y"),raw.get("z")
                else:y,z=raw[0],raw[1]
                pts.append((_vfloat(y,"section y"),_vfloat(z,"section z")))
            if len(pts)<3:raise AngleGeometryError("Validator: exact polygon mist vertices")
            return "points",pts
        if kind in {"rectangle","box"}:
            w=_vfloat(explicit.get("width_mm"),"breedte");h=_vfloat(explicit.get("height_mm"),"hoogte");cy,cz=(explicit.get("center_yz") or [0,0])
            cy=_vfloat(cy,"center y");cz=_vfloat(cz,"center z");return "points",[(cy-w/2,cz-h/2),(cy-w/2,cz+h/2),(cy+w/2,cz-h/2),(cy+w/2,cz+h/2)]
        if kind in {"circle","round"}:
            r=explicit.get("radius_mm")
            if r is None and explicit.get("diameter_mm") is not None:r=float(explicit["diameter_mm"])/2
            cy,cz=(explicit.get("center_yz") or [0,0]);return "circle",(_vfloat(r,"radius"),_vfloat(cy,"center y"),_vfloat(cz,"center z"))
        raise AngleGeometryError("Validator: niet-ondersteunde exact section geometry")
    dims=dict(line.get("profile_dimensions_mm") or {});ptype=str(line.get("profile_type") or "").lower()
    if ptype in {"round","round_bar","chs","tube","pipe"}:
        d=_vdim(dims,"diameter","diameter_mm","outside_diameter","outer_diameter","d")
        if d:return "circle",(d/2,0.0,0.0)
    width=_vdim(dims,"width","width_mm","b");height=_vdim(dims,"height","height_mm","h")
    if ptype in {"flat","strip"}:
        height=height or _vdim(dims,"thickness","thickness_mm","t")
        if width and height:return "points",[(-width/2,-height/2),(-width/2,height/2),(width/2,-height/2),(width/2,height/2)]
    if ptype in {"rhs","shs","box"} and width and height:return "points",[(-width/2,-height/2),(-width/2,height/2),(width/2,-height/2),(width/2,height/2)]
    pts=_validator_profile_vertices(ptype,dims)
    if pts:return "points",pts
    raise AngleGeometryError("Validator: geen onafhankelijke exacte section representation")


def _independent_support_max(line: dict[str,Any], a: float,b: float,c: float) -> float:
    import math
    kind,data=_validator_section(line)
    if kind=="points":return max(a*y+b*z+c for y,z in data)
    r,cy,cz=data;return a*cy+b*cz+c+r*math.sqrt(a*a+b*b)


def _cut_x_function(cut: CutRequirement) -> tuple[float,float,float,float]:
    plane=canonical_plane(cut)
    a,b,c=plane.x_function();return a,b,c,abs(plane.nx)


def _cut_is_miter(cut: CutRequirement, angle_tol: float) -> bool:
    return abs(float(cut.primary_angle_deg))>angle_tol or abs(float(cut.secondary_angle_deg))>angle_tol


def _independent_cut_consumption(cut: CutRequirement,machine: dict[str,Any],kernel: LengthKernel) -> tuple[int,int]:
    _a,_b,_c,nx=_cut_x_function(cut); blade=_vfloat(machine.get("kerf_mm",0) or 0,"kerf");finish=_vfloat(cut.finish_allowance_mm or 0,"finish")
    if blade<0 or finish<0:raise AngleGeometryError("Negatieve kerf/finish")
    angle_tol=float(machine.get("angle_tolerance_deg",0.01) or 0.01)
    machine_extra=float(machine.get("extra_miter_loss_mm",0) or 0) if _cut_is_miter(cut,angle_tol) else 0.0
    return kernel.mm_to_units(blade/nx),kernel.mm_to_units(machine_extra)+kernel.mm_to_units(finish/nx)


def _independent_common(left_line,right_line,left,right,machine: dict[str,Any]) -> tuple[bool,list[str]]:
    reasons=[];angle_tol=max(float(machine.get("angle_tolerance_deg",0.01) or 0.01),1e-9);linear_tol=max(float(machine.get("machine_tolerance_mm",0.1) or 0.1),float(left.variant.end_cut.tolerance_mm or 0),float(right.variant.start_cut.tolerance_mm or 0))
    if str(machine.get("common_cut_policy") or "blocked")!="supported":reasons.append("machine_common_cut_not_supported")
    if not left.variant.end_cut.common_cut_allowed or not right.variant.start_cut.common_cut_allowed:reasons.append("part_common_cut_not_explicitly_allowed")
    if left.variant.production_equivalence!="exact" or right.variant.production_equivalence!="exact":reasons.append("orientation_not_exact")
    if str(left.variant.end_cut.reference or "")!="end" or str(right.variant.start_cut.reference or "")!="start":reasons.append("cut_surface_semantics_not_opposed")
    if abs(float(left.variant.end_cut.primary_angle_deg)-float(right.variant.start_cut.primary_angle_deg))>angle_tol or abs(float(left.variant.end_cut.secondary_angle_deg)-float(right.variant.start_cut.secondary_angle_deg))>angle_tol:reasons.append("cut_planes_not_parallel")
    if abs(float(left.variant.end_cut.finish_allowance_mm)-float(right.variant.start_cut.finish_allowance_mm))>linear_tol:reasons.append("finish_allowance_mismatch")
    if str(left_line.get("section_hash") or "")!=str(right_line.get("section_hash") or ""):reasons.append("section_hash_mismatch")
    if any(bool((f or {}).get("blocks_common_cut")) for f in list(left_line.get("relevant_features") or [])+list(right_line.get("relevant_features") or [])):reasons.append("feature_blocks_common_cut")
    return not reasons,reasons


def _independent_transition(prev_line,line,prev_p,prev_orientation,p,orientation,machine: dict[str,Any],kernel: LengthKernel, *, requested_common: bool | None = None) -> dict[str,Any]:
    la,lb,lc,_=_cut_x_function(prev_orientation.variant.end_cut);ra,rb,rc,_=_cut_x_function(orientation.variant.start_cut)
    geom_mm=_independent_support_max(prev_line,la-ra,lb-rb,lc-rc);geom_u=kernel.signed_mm_to_units(geom_mm)
    left_kerf,left_extra=_independent_cut_consumption(prev_orientation.variant.end_cut,machine,kernel);right_kerf,right_extra=_independent_cut_consumption(orientation.variant.start_cut,machine,kernel)
    common_possible,reasons=_independent_common(prev_line,line,prev_orientation,orientation,machine)
    # A proven common cut may always be executed as two separate cuts when the user
    # explicitly disables sharing.  The inverse is never allowed: requesting a
    # common cut without geometric/machine proof remains invalid.
    common = common_possible if requested_common is None else bool(requested_common and common_possible)
    requested_common_invalid = bool(requested_common is True and not common_possible)
    if common:
        # Equal cut plane/allowance is required by the conservative common-cut proof.
        kerf=max(left_kerf,right_kerf)
        # Each cut-consumption extra contains finish + possible machine miter loss.
        # For a shared cut the machine miter loss occurs once; finish allowances remain per side.
        _a,_b,_c,lnx=_cut_x_function(prev_orientation.variant.end_cut);_a,_b,_c,rnx=_cut_x_function(orientation.variant.start_cut)
        lf=kernel.mm_to_units(float(prev_orientation.variant.end_cut.finish_allowance_mm or 0)/lnx);rf=kernel.mm_to_units(float(orientation.variant.start_cut.finish_allowance_mm or 0)/rnx)
        angle_tol=float(machine.get("angle_tolerance_deg",0.01) or 0.01);miter= _cut_is_miter(prev_orientation.variant.end_cut,angle_tol) or _cut_is_miter(orientation.variant.start_cut,angle_tol)
        machine_extra=kernel.mm_to_units(machine.get("extra_miter_loss_mm",0) or 0) if miter else 0
        extra=lf+rf+machine_extra;cuts=1
    else:
        kerf=left_kerf+right_kerf;extra=left_extra+right_extra;cuts=2
    gap=geom_u+kerf+extra
    transition_id=stable_sha256({"left":prev_p.instance_id,"right":p.instance_id,"lv":prev_orientation.variant.variant_hash,"rv":orientation.variant.variant_hash,"machine":machine.get("configuration_hash") or machine.get("machine_id"),"common":common})[:32]
    return {"transition_id":transition_id,"geometry_delta_units":geom_u,"kerf_projection_units":kerf,"extra_loss_units":extra,"required_reference_gap_units":gap,"physical_spacing_units":gap,"cut_count":cuts,"common_cut":common,"common_cut_possible":common_possible,"requested_common_invalid":requested_common_invalid,"reasons":reasons}


def _independent_cut_interval(reference:int,envelope,kerf:int,extra:int=0)->tuple[int,int]:
    a=reference+int(envelope.min_offset_units);b=reference+int(envelope.max_offset_units)+max(0,int(kerf))+max(0,int(extra));return min(a,b),max(a,b)


def validate_angle_plan(snapshot, plan) -> PlanValidationReport:
    kernel=_kernel(snapshot); messages=[]
    if str(plan.input_snapshot_hash) != str(snapshot.snapshot_hash):
        messages.append(_issue("CWS-NEST-022","Plan is niet aan de actuele inputsnapshot gebonden."))
    lines={str(x.get("demand_line_id") or ""):dict(x) for x in list(snapshot.demand_lines or [])}
    instances={str(x.get("instance_id") or ""):dict(x) for x in list(snapshot.piece_instances or [])}
    required_ids=set(instances)
    stock={str(x.get("candidate_id") or ""):dict(x) for x in list(dict(snapshot.stock_snapshot or {}).get("candidates") or [])}
    machines={str(x.get("profile_id") or ""):dict(x) for x in list(dict(snapshot.machine_snapshot or {}).get("profiles") or [])}
    seen={}; usage={}
    gross=net=kerf_total=head_total=tail_total=remnant_total=waste_total=transition_total=0
    total_cost=0; purchase_count=physical_count=full_stock_count=remnant_source_count=0

    for bar in plan.bars:
        candidate=stock.get(bar.candidate_id); machine=machines.get(bar.machine_profile_id)
        if candidate is None:
            messages.append(_issue("CWS-NEST-011","Plan verwijst naar onbekende stockcandidate.",object_ids=[bar.bar_id,bar.candidate_id])); continue
        if machine is None or str(machine.get("machine_id") or "") != bar.machine_id:
            messages.append(_issue("CWS-NEST-008","Plan verwijst naar onbekend/verkeerd machineprofiel.",object_ids=[bar.bar_id,bar.machine_profile_id])); continue
        if str(machine.get("validation_status") or "") not in {"validated","released"}:
            messages.append(_issue("CWS-NEST-008","Machineprofiel is niet gevalideerd.",object_ids=[bar.machine_profile_id]))
        tolerance=kernel.mm_to_units(machine.get("machine_tolerance_mm",0) or 0)
        expected_head=kernel.mm_to_units(machine.get("head_trim_mm",0) or 0); expected_tail=kernel.mm_to_units(machine.get("tail_trim_mm",0) or 0); safety=kernel.mm_to_units(machine.get("safety_length_mm",0) or 0)
        minimum_remnant=max(kernel.mm_to_units(candidate.get("minimum_reusable_mm",0) or 0),kernel.mm_to_units(machine.get("minimum_end_remnant_mm",0) or 0))
        if int(bar.stock_length_units)!=int(candidate.get("length_units") or 0) or int(bar.head_trim_units)!=expected_head or int(bar.tail_trim_units)!=expected_tail:
            messages.append(_issue("CWS-NEST-023","Bar stock-/trimgegevens wijken af van snapshot.",object_ids=[bar.bar_id]))
        if str(bar.source_type)!=str(candidate.get("source_type") or "") or str(bar.source_id)!=str(candidate.get("source_id") or ""):
            messages.append(_issue("CWS-NEST-024","Bar stockbron wijkt af van snapshot.",object_ids=[bar.bar_id,bar.candidate_id]))
        if int(bar.kerf_units)!=kernel.mm_to_units(machine.get("kerf_mm",0) or 0):
            messages.append(_issue("CWS-NEST-023","Bar basis-kerf wijkt af van machineprofiel.",object_ids=[bar.bar_id]))
        if int(bar.safety_length_units)!=safety or int(bar.minimum_reusable_units)!=minimum_remnant:
            messages.append(_issue("CWS-NEST-023","Bar safety/remnantregels wijken af van snapshot.",object_ids=[bar.bar_id]))
        usage[bar.candidate_id]=usage.get(bar.candidate_id,0)+1
        available=candidate.get("available_quantity")
        if available is not None and usage[bar.candidate_id]>int(available):
            messages.append(_issue("CWS-NEST-012","Stock quantity wordt overschreden.",object_ids=[bar.candidate_id]))
        zones=[]
        for z in list(machine.get("forbidden_clamp_zones") or []):
            try:a=kernel.mm_to_units((z or {}).get("start_mm",0));b=kernel.mm_to_units((z or {}).get("end_mm",0))
            except Exception:continue
            if b>a:zones.append((a,b))
        placements=sorted(list(bar.placements),key=lambda p:int(p.sequence_index))
        stored_transitions={t.transition_id:t for t in list(bar.transitions)}
        expected_transition_ids=set(); prev=None; reconstructed_kerf=0; reconstructed_extra=0
        for seq,p in enumerate(placements,start=1):
            if int(p.sequence_index)!=seq:
                messages.append(_issue("CWS-NEST-014","Sequence index is niet aaneengesloten.",object_ids=[bar.bar_id,p.instance_id]))
            instance=instances.get(p.instance_id)
            if instance is None:
                messages.append(_issue("CWS-NEST-019","Onbekende piece instance.",object_ids=[p.instance_id,bar.bar_id])); continue
            if p.instance_id in seen:
                messages.append(_issue("CWS-NEST-019","Piece instance is dubbel toegewezen.",object_ids=[p.instance_id,seen[p.instance_id],bar.bar_id]))
            else:seen[p.instance_id]=bar.bar_id
            line_id=str(instance.get("demand_line_id") or ""); line=lines.get(line_id)
            if line is None:
                messages.append(_issue("CWS-NEST-019","Piece instance mist demand line.",object_ids=[p.instance_id])); continue
            if p.demand_line_id!=line_id or p.part_id!=str(instance.get("part_id") or line.get("part_id") or ""):
                messages.append(_issue("CWS-NEST-019","Placementidentiteit wijkt af van snapshot.",object_ids=[p.instance_id]))
            if p.manufacturing_hash!=str(instance.get("manufacturing_hash") or line.get("manufacturing_hash") or ""):
                messages.append(_issue("CWS-NEST-004","Manufacturing hash mismatch.",object_ids=[p.instance_id]))
            if str(candidate.get("section_hash") or "") and str(candidate.get("section_hash") or "")!=str(line.get("section_hash") or ""):
                messages.append(_issue("CWS-NEST-013","Section mismatch tussen stock en part.",object_ids=[p.instance_id,bar.candidate_id]))
            if str(candidate.get("material") or "")!=str(line.get("material") or "") or str(candidate.get("material_grade") or "")!=str(line.get("material_grade") or ""):
                messages.append(_issue("CWS-NEST-013","Materiaal/kwaliteit mismatch.",object_ids=[p.instance_id,bar.candidate_id]))
            try:variants=build_orientation_variants(line,machine,kernel=kernel,require_exact=True)
            except AngleGeometryError as exc:
                messages.append(_issue("CWS-NEST-026",f"Exacte oriëntatiegeometrie kan niet worden gereconstrueerd: {exc}",object_ids=[p.instance_id])); continue
            orientation=next((v for v in variants if v.variant.variant_id==p.orientation_id),None)
            if orientation is None or orientation.variant.production_equivalence!="exact" or not _machine_angle_valid(orientation,machine):
                messages.append(_issue("CWS-NEST-026","Opgeslagen oriëntatie is niet exact/machinegeldig.",object_ids=[p.instance_id,p.orientation_id])); continue
            if p.orientation_hash!=orientation.variant.variant_hash:
                messages.append(_issue("CWS-NEST-023","Orientation hash wijkt af.",object_ids=[p.instance_id]))
            expected_length=int(line.get("nominal_length_units") or 0)
            if int(p.length_units)!=expected_length:
                messages.append(_issue("CWS-NEST-001","Placementlengte wijkt af van demand line.",object_ids=[p.instance_id]))
            if prev is None:
                start_kerf,start_extra=_independent_cut_consumption(orientation.variant.start_cut,machine,kernel)
                ref_start=expected_head+start_kerf+start_extra-orientation.start_envelope.min_offset_units
                reconstructed_kerf += start_kerf; reconstructed_extra += start_extra
                if _interval_conflicts(zones,ref_start+orientation.start_envelope.min_offset_units-start_kerf-start_extra,ref_start+orientation.start_envelope.max_offset_units):
                    messages.append(_issue("CWS-NEST-016","Startzaagsnede kruist verboden klemzone.",object_ids=[p.instance_id,bar.bar_id]))
                expected_before=""
            else:
                prev_p,prev_line,prev_orientation=prev
                stored_id=str(p.transition_before_id or "")
                stored=stored_transitions.get(stored_id)
                if stored is None:
                    messages.append(_issue("CWS-NEST-017","Placement verwijst niet naar een bestaande transition.",object_ids=[prev_p.instance_id,p.instance_id,stored_id])); continue
                try:expected_t=_independent_transition(prev_line,line,prev_p,prev_orientation,p,orientation,machine,kernel,requested_common=bool(stored.common_cut))
                except AngleGeometryError as exc:
                    messages.append(_issue("CWS-NEST-017",f"Transition kan niet onafhankelijk exact worden bewezen: {exc}",object_ids=[prev_p.instance_id,p.instance_id])); continue
                expected_transition_ids.add(stored_id)
                if expected_t.get("requested_common_invalid"):
                    messages.append(_issue("CWS-NEST-017","Opgeslagen common cut kan niet onafhankelijk worden bewezen.",object_ids=[stored_id],details={"reasons":list(expected_t.get("reasons") or [])}))
                if stored_id != expected_t["transition_id"]:
                    messages.append(_issue("CWS-NEST-017","Transition-ID is niet consistent met de onafhankelijk gereconstrueerde uitvoeringskeuze.",object_ids=[stored_id,expected_t["transition_id"]]))
                mismatch=[]
                for key in ("geometry_delta_units","kerf_projection_units","extra_loss_units","required_reference_gap_units","physical_spacing_units","cut_count","common_cut"):
                    if getattr(stored,key)!=expected_t[key]:mismatch.append(key)
                if mismatch:
                    code="CWS-NEST-017" if "common_cut" in mismatch or "cut_count" in mismatch else "CWS-NEST-021"
                    messages.append(_issue(code,"Opgeslagen transition wijkt af van onafhankelijke geometrische reconstructie.",object_ids=[stored_id],details={"fields":mismatch}))
                ref_start=int(prev_p.reference_end_units)+int(expected_t["required_reference_gap_units"])
                if _interval_conflicts(zones,int(prev_p.reference_end_units)+prev_orientation.end_envelope.min_offset_units,ref_start+orientation.start_envelope.max_offset_units):
                    messages.append(_issue("CWS-NEST-016","Transitionzaagsnede kruist verboden klemzone.",object_ids=[stored_id,bar.bar_id]))
                reconstructed_kerf += int(expected_t["kerf_projection_units"]); reconstructed_extra += int(expected_t["extra_loss_units"]); expected_before=stored_id
                if p.transition_before_id!=expected_before or prev_p.transition_after_id!=expected_before:
                    messages.append(_issue("CWS-NEST-017","Placement-transitionlink is inconsistent.",object_ids=[p.instance_id,prev_p.instance_id]))
            ref_end=ref_start+expected_length; phys_min=ref_start+orientation.start_envelope.min_offset_units; phys_max=ref_end+orientation.end_envelope.max_offset_units
            expected_fields={
                "reference_start_units":ref_start,"reference_end_units":ref_end,"start_units":ref_start,"end_units":ref_end,"cut_position_units":ref_end,
                "physical_min_units":phys_min,"physical_max_units":phys_max,
                "start_envelope_min_units":orientation.start_envelope.min_offset_units,"start_envelope_max_units":orientation.start_envelope.max_offset_units,
                "end_envelope_min_units":orientation.end_envelope.min_offset_units,"end_envelope_max_units":orientation.end_envelope.max_offset_units,
            }
            for key,value in expected_fields.items():
                if int(getattr(p,key))!=int(value):messages.append(_issue("CWS-NEST-014",f"Placementveld {key} wijkt af van reconstructie.",object_ids=[p.instance_id]))
            if p.start_cut_hash!=orientation.variant.start_cut.requirement_hash or p.end_cut_hash!=orientation.variant.end_cut.requirement_hash:
                messages.append(_issue("CWS-NEST-023","Cut hash wijkt af van inputsnapshot/orientation.",object_ids=[p.instance_id]))
            if p.transition_after_id:
                after_t=stored_transitions.get(p.transition_after_id)
                if after_t is not None and int(p.kerf_units)!=int(after_t.kerf_projection_units):
                    messages.append(_issue("CWS-NEST-021","Placement kerf wijkt af van transition.",object_ids=[p.instance_id]))
            prev=(p,line,orientation)
        extra_ids=set(stored_transitions).difference(expected_transition_ids)
        if extra_ids:messages.append(_issue("CWS-NEST-017","Plan bevat onverwachte transitionrecords.",object_ids=sorted(extra_ids)))
        if not placements or prev is None:
            messages.append(_issue("CWS-NEST-019","Bar bevat geen valide placements.",object_ids=[bar.bar_id])); continue
        last_p,last_line,last_orientation=prev
        final_kerf,final_extra=_independent_cut_consumption(last_orientation.variant.end_cut,machine,kernel); reconstructed_kerf+=final_kerf; reconstructed_extra+=final_extra
        final_interval=_independent_cut_interval(int(last_p.reference_end_units),last_orientation.end_envelope,final_kerf,final_extra)
        if _interval_conflicts(zones,*final_interval):messages.append(_issue("CWS-NEST-016","Finale zaagsnede kruist verboden klemzone.",object_ids=[last_p.instance_id,bar.bar_id]))
        if int(last_p.final_cut_kerf_units)!=final_kerf:messages.append(_issue("CWS-NEST-021","Final cut kerf wijkt af.",object_ids=[last_p.instance_id]))
        for p in placements[:-1]:
            if int(p.final_cut_kerf_units)!=0:messages.append(_issue("CWS-NEST-021","Niet-laatste placement bevat final-cut kerf.",object_ids=[p.instance_id]))
        consumed_end=int(last_p.reference_end_units)+last_orientation.end_envelope.max_offset_units+final_kerf+final_extra
        if consumed_end>int(bar.stock_length_units)-expected_tail-safety+tolerance:messages.append(_issue("CWS-NEST-015","Bar overschrijdt stock-/safetygrens.",object_ids=[bar.bar_id]))
        residual=max(0,int(bar.stock_length_units)-expected_tail-consumed_end); reusable=residual if residual>0 and residual>=minimum_remnant else 0; waste=residual if residual>0 and reusable==0 else 0
        nominal=sum(int(p.length_units) for p in placements); transition_effect=consumed_end-expected_head-nominal-reconstructed_kerf
        expected_bar={"occupied_span_units":consumed_end-expected_head,"nominal_sum_units":nominal,"transition_effect_units":transition_effect,"projected_kerf_units":reconstructed_kerf,"raw_residual_units":residual,"reusable_remnant_units":reusable,"waste_units":waste,"common_cut_count":sum(1 for t in stored_transitions.values() if t.common_cut),"cut_count":2+sum(int(t.cut_count) for t in stored_transitions.values())}
        for key,value in expected_bar.items():
            if int(getattr(bar,key))!=int(value):messages.append(_issue("CWS-NEST-018" if key in {"transition_effect_units","projected_kerf_units","raw_residual_units","reusable_remnant_units","waste_units"} else "CWS-NEST-021",f"Barveld {key} wijkt af van reconstructie.",object_ids=[bar.bar_id]))
        gross+=int(bar.stock_length_units);net+=nominal;kerf_total+=reconstructed_kerf;head_total+=expected_head;tail_total+=expected_tail;remnant_total+=reusable;waste_total+=waste;transition_total+=transition_effect;total_cost+=int(bar.total_cost_micros)
        if bar.source_type=="purchase_option":purchase_count+=1
        else:physical_count+=1
        if bar.source_type=="full_stock":full_stock_count+=1
        if bar.source_type=="remnant":remnant_source_count+=1

    missing=sorted(required_ids.difference(seen));extra=sorted(set(seen).difference(required_ids))
    if missing:messages.append(_issue("CWS-NEST-019","Niet alle verplichte piece instances zijn toegewezen.",object_ids=missing[:20],details={"missing_count":len(missing)}))
    if extra:messages.append(_issue("CWS-NEST-019","Plan bevat niet-verplichte piece instances.",object_ids=extra[:20]))
    if plan.unassigned_instance_ids:messages.append(_issue("CWS-NEST-019","Plan bevat expliciet unassigned instances.",object_ids=list(plan.unassigned_instance_ids)[:20]))
    delta=gross-(net+kerf_total+head_total+tail_total+remnant_total+waste_total+transition_total)
    balance={"gross_stock_units":gross,"net_part_units":net,"kerf_units":kerf_total,"head_trim_units":head_total,"tail_trim_units":tail_total,"reusable_remnant_units":remnant_total,"waste_units":waste_total,"transition_effect_units":transition_total,"balance_delta_units":delta,"material_loss_units":kerf_total+head_total+tail_total+waste_total+transition_total}
    stored=asdict(plan.material_balance)
    for key in ("gross_stock_units","net_part_units","kerf_units","head_trim_units","tail_trim_units","reusable_remnant_units","waste_units","transition_effect_units","balance_delta_units"):
        if int(stored.get(key,0))!=int(balance[key]):messages.append(_issue("CWS-NEST-018",f"Materiaalbalansveld {key} wijkt af."))
    if delta!=0:messages.append(_issue("CWS-NEST-018","Materiaalbalans sluit niet exact.",details={"delta_units":delta}))
    if plan.objective is not None:
        metrics={"material_loss_units":balance["material_loss_units"],"waste_units":waste_total,"reusable_remnant_units":remnant_total,"gross_stock_units":gross,"net_part_units":net,"bar_count":len(plan.bars),"purchase_bar_count":purchase_count,"physical_bar_count":physical_count,"full_stock_bar_count":full_stock_count,"remnant_bar_count":remnant_source_count,"setup_count":len(plan.bars),"cost_micros":total_cost}
        for key,value in metrics.items():
            if int(plan.objective.raw_metrics.get(key,0))!=int(value):messages.append(_issue("CWS-NEST-021",f"Objective metric {key} wijkt af."))
    valid=not messages
    if not valid and not any(m["code"]=="CWS-NEST-021" for m in messages):messages.append(_issue("CWS-NEST-021","Angle-aware solverresultaat faalt onafhankelijke planvalidatie."))
    report=PlanValidationReport(input_snapshot_hash=str(snapshot.snapshot_hash),plan_hash=plan.plan_hash,valid=valid,status="passed" if valid else "blocked",messages=messages,material_balance=balance,assigned_instance_count=len(seen),required_instance_count=len(required_ids),checked_bar_count=len(plan.bars));report.refresh_hash();return report


__all__=["validate_angle_plan"]
