"""Phase-7 acceptance, stock reservation and release workflow."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from cws_convertor.project.model import ProjectModel, ReviewStatus, stable_sha256, utc_now_iso

from .angle_validator import validate_angle_plan
from .manual_planning import check_manual_freshness
from .configuration import load_formulas, load_machine_profiles, load_tools
from .eligibility import evaluate_part
from .machine import build_machine_snapshot
from .models import NestingRunStatus, ReservationRequest
from .reservation import ReservationConflict, release_reservation, reserve_physical_stock
from .serialization import input_snapshot_from_dict, plan_from_dict
from .phase7_reporting import create_release_package, verify_release_package

PHASE7_ACCEPTANCE_SCHEMA_VERSION="1.0"
PHASE7_RELEASE_SCHEMA_VERSION="1.0"
_ALLOWED_RESULTS={"optimal","feasible","timeout_feasible","manual_feasible"}


class ProfileNestingReleaseError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None=None):
        super().__init__(message); self.code=code; self.details=dict(details or {})


@dataclass
class NestingAcceptanceRecord:
    acceptance_id: str
    run_id: str
    project_id: str
    plan_hash: str
    input_snapshot_hash: str
    validation_report_hash: str
    accepted_at: str
    accepted_by: str
    reservation_ids: list[str]=field(default_factory=list)
    physical_requests: list[dict[str, Any]]=field(default_factory=list)
    status: str="accepted"
    record_hash: str=""
    schema_version: str=PHASE7_ACCEPTANCE_SCHEMA_VERSION
    def refresh_hash(self):
        payload=asdict(self); payload.pop("record_hash",None); self.record_hash=stable_sha256(payload); return self.record_hash


@dataclass
class NestingReleaseRecord:
    release_id: str
    run_id: str
    project_id: str
    acceptance_id: str
    plan_hash: str
    input_snapshot_hash: str
    validation_report_hash: str
    released_at: str
    released_by: str
    package_path: str
    package_zip_path: str
    package_manifest_hash: str
    package_zip_sha256: str
    neutral_job_manifest_hash: str
    machine_transfer_allowed: bool=False
    record_hash: str=""
    schema_version: str=PHASE7_RELEASE_SCHEMA_VERSION
    def refresh_hash(self):
        payload=asdict(self); payload.pop("record_hash",None); self.record_hash=stable_sha256(payload); return self.record_hash


def _record(project: ProjectModel, run_id: str) -> dict[str, Any]:
    rec=project.profile_nesting_runs.get(run_id)
    if not isinstance(rec,dict): raise ProfileNestingReleaseError("CWS-NEST-028",f"Onbekende profielnestingrun {run_id}")
    return rec


def _static_candidate_fingerprint(raw: dict[str, Any]) -> str:
    c=dict(raw)
    for key in ("available_quantity","reservation_status","reservation_revision","snapshot_hash"):
        c.pop(key,None)
    return stable_sha256(c)


def _snapshot_candidates(record: dict[str, Any]) -> dict[str,dict[str,Any]]:
    stock=dict(dict(record.get("input_snapshot") or {}).get("stock_snapshot") or {})
    return {str(x.get("candidate_id") or ""):dict(x) for x in list(stock.get("candidates") or [])}


def _reservation_requests_from_plan(project: ProjectModel, record: dict[str, Any]) -> list[ReservationRequest]:
    counts: dict[tuple[str,str],int]={}
    candidates=_snapshot_candidates(record)
    for raw in list(dict(record.get("plan") or {}).get("bars") or []):
        bar=dict(raw); source_type=str(bar.get("source_type") or ""); source_id=str(bar.get("source_id") or "")
        if source_type not in {"full_stock","remnant"}: continue
        counts[(source_type,source_id)]=counts.get((source_type,source_id),0)+1
    reqs=[]
    for (source_type,source_id),qty in sorted(counts.items()):
        cid=("stock:" if source_type=="full_stock" else "remnant:")+source_id; snap=candidates.get(cid,{})
        if source_type=="remnant" and qty!=1: raise ProfileNestingReleaseError("CWS-NEST-025",f"Reststuk {source_id} wordt meer dan eenmaal gebruikt")
        entity=project.stock_items.get(source_id) if source_type=="full_stock" else project.remnants.get(source_id)
        if entity is None: raise ProfileNestingReleaseError("CWS-NEST-025",f"Fysieke stockbron {source_id} bestaat niet meer")
        # Compare static identity before acquiring the optimistic reservation revision.
        current={
            "candidate_id":cid,"source_type":source_type,"source_id":source_id,"physical":True,
            "profile_id":getattr(entity,"profile",""),"section_hash":getattr(entity,"section_hash","") or str(getattr(entity,"properties",{}).get("section_hash") or ""),
            "material":getattr(entity,"material",""),"material_grade":getattr(entity,"grade",""),
            "length_mm":float(getattr(entity,"stock_length_mm",0.0) if source_type=="full_stock" else getattr(entity,"remaining_length_mm",0.0)),
            "length_units":int(snap.get("length_units") or 0),"heat":getattr(entity,"heat_number",""),"batch":getattr(entity,"batch",""),"certificate":getattr(entity,"certificate",""),
            "supplier":getattr(entity,"supplier",""),"location":getattr(entity,"location",""),"lead_time_days":int(snap.get("lead_time_days") or 0),
            "unit_price":float(getattr(entity,"unit_price",0.0) if source_type=="full_stock" else getattr(entity,"cost_book_value",0.0)),"extra_cost":float(snap.get("extra_cost") or 0.0),
            "minimum_reusable_mm":float(getattr(entity,"minimum_reusable_mm",0.0)),"measurement_reliability":getattr(entity,"measurement_reliability",""),"provenance":dict(snap.get("provenance") or {}),
        }
        if snap and _static_candidate_fingerprint(current)!=_static_candidate_fingerprint(snap):
            raise ProfileNestingReleaseError("CWS-NEST-024",f"Fysieke stockbron {source_id} wijkt af van de geoptimaliseerde snapshot")
        reqs.append(ReservationRequest(source_type=source_type,source_id=source_id,quantity=qty,expected_reservation_revision=int(getattr(entity,"reservation_revision",0))))
    return reqs


def _preflight(project: ProjectModel, run_id: str) -> tuple[dict[str,Any],dict[str,Any]]:
    record=_record(project,run_id); run=dict(record.get("run") or {}); plan_raw=record.get("plan"); snapshot_raw=record.get("input_snapshot"); validation_raw=dict(record.get("validation_report") or {})
    if not isinstance(plan_raw,dict) or not isinstance(snapshot_raw,dict): raise ProfileNestingReleaseError("CWS-NEST-021","Run mist plan of immutable inputsnapshot")
    if str(run.get("result_status") or "") not in _ALLOWED_RESULTS: raise ProfileNestingReleaseError("CWS-NEST-021",f"Solverstatus {run.get('result_status')!r} is niet vrijgeefbaar")
    if list(plan_raw.get("unassigned_instance_ids") or []): raise ProfileNestingReleaseError("CWS-NEST-021","Plan bevat niet-toegewezen stukinstanties")
    snapshot=input_snapshot_from_dict(snapshot_raw); plan=plan_from_dict(plan_raw); report=validate_angle_plan(snapshot,plan)
    if not report.valid: raise ProfileNestingReleaseError("CWS-NEST-021","Plan faalt onafhankelijke her-validatie",details=report.to_dict())
    if str(validation_raw.get("report_hash") or "")!=report.report_hash: raise ProfileNestingReleaseError("CWS-NEST-021","Opgeslagen validatierapport wijkt af van actuele onafhankelijke validatie")
    freshness=check_manual_freshness(project,run_id)
    if not freshness["fresh"]: raise ProfileNestingReleaseError("CWS-NEST-022","Plan is stale en kan niet worden geaccepteerd",details=freshness)
    blocked=[x for x in list(snapshot_raw.get("demand_lines") or []) if str(x.get("eligibility_status") or "")!="eligible"]
    if blocked: raise ProfileNestingReleaseError("CWS-NEST-021","Niet alle demandregels zijn volledig production-eligible",details={"demand_line_ids":[x.get("demand_line_id") for x in blocked]})
    return record,{"report":report.to_dict(),"freshness":freshness}


def accept_nesting_run(project: ProjectModel, run_id: str, *, user: str="system", reserve_stock: bool=True) -> NestingAcceptanceRecord:
    record=_record(project,run_id); run=dict(record.get("run") or {}); existing=record.get("acceptance")
    if str(run.get("status") or "")==NestingRunStatus.RELEASED.value: raise ProfileNestingReleaseError("CWS-NEST-021","Vrijgegeven run kan niet opnieuw worden geaccepteerd")
    if isinstance(existing,dict) and str(existing.get("status") or "")=="accepted":
        # Idempotent accept is evaluated before stock freshness because this
        # run's own reservation intentionally changes the current stock snapshot.
        if str(existing.get("plan_hash") or "")==str(dict(record.get("plan") or {}).get("plan_hash") or ""):
            return NestingAcceptanceRecord(**{k:v for k,v in existing.items() if k in NestingAcceptanceRecord.__dataclass_fields__})
        raise ProfileNestingReleaseError("CWS-NEST-021","Een andere planhash is al geaccepteerd")
    record,proof=_preflight(project,run_id); run=dict(record.get("run") or {})
    requests=_reservation_requests_from_plan(project,record) if reserve_stock else []
    reservation=None
    try:
        if requests:
            reservation=reserve_physical_stock(project,requests,run_id=run_id,user=user)
        accepted_at=utc_now_iso(); acceptance=NestingAcceptanceRecord(
            acceptance_id=str(uuid4()),run_id=run_id,project_id=project.project_id,plan_hash=str(dict(record.get("plan") or {}).get("plan_hash") or ""),input_snapshot_hash=str(dict(record.get("input_snapshot") or {}).get("snapshot_hash") or ""),validation_report_hash=str(dict(record.get("validation_report") or {}).get("report_hash") or ""),accepted_at=accepted_at,accepted_by=user,reservation_ids=[reservation.reservation_id] if reservation else [],physical_requests=[asdict(x) for x in requests],
        ); acceptance.refresh_hash()
        before=stable_sha256(record); record["acceptance"]=asdict(acceptance); run=dict(record.get("run") or {}); run["status"]=NestingRunStatus.ACCEPTED.value; run["accepted_at"]=accepted_at; run["modified_at"]=accepted_at; run["stock_reservations"]=[asdict(reservation)] if reservation else []; run.setdefault("audit",[]).append({"event":"accepted","at":accepted_at,"user":user,"acceptance_hash":acceptance.record_hash,"validation_hash":proof["report"]["report_hash"]}); record["run"]=run
        project.audit("profile_nesting.accepted",user=user,entity_id=run_id,before_hash=before,after_hash=stable_sha256(record),details={"acceptance_id":acceptance.acceptance_id,"reservation_ids":acceptance.reservation_ids})
        return acceptance
    except Exception:
        if reservation is not None:
            try: release_reservation(project,reservation.reservation_id,user=f"{user}:rollback")
            except Exception: pass
        raise


def _accepted_freshness(project: ProjectModel, run_id: str) -> dict[str,Any]:
    record=_record(project,run_id); acceptance=dict(record.get("acceptance") or {}); reasons=[]
    if not acceptance or acceptance.get("status")!="accepted": reasons.append({"kind":"acceptance","message":"Run is niet geaccepteerd"})
    snapshot=dict(record.get("input_snapshot") or {})

    # Demand freshness is checked without the stock-availability gate.  An
    # accepted run intentionally makes its selected physical stock unavailable
    # to other runs; that must not make its own demand appear stale.
    snapshot_lines={str(x.get("part_id") or ""):dict(x) for x in list(snapshot.get("demand_lines") or [])}
    for part_id,line in snapshot_lines.items():
        part=project.parts.get(part_id)
        if part is None:
            reasons.append({"kind":"demand","message":f"Onderdeel {part_id} ontbreekt"}); continue
        if str(part.manufacturing_hash or "")!=str(line.get("manufacturing_hash") or ""):
            reasons.append({"kind":"demand","message":f"Manufacturing identity van {part_id} is gewijzigd"}); continue
        if int(part.quantity_total or 0)!=int(line.get("quantity") or 0):
            reasons.append({"kind":"demand","message":f"Aantal van {part_id} is gewijzigd"}); continue
        try:
            current=evaluate_part(project,part,mode="production",candidate_machine_ids=list(line.get("candidate_machine_ids") or []))
            if current.snapshot_hash()!=stable_sha256(line):
                reasons.append({"kind":"demand","message":f"Productievraag van {part_id} wijkt af van de geaccepteerde snapshot"})
        except Exception as exc:
            reasons.append({"kind":"demand","message":f"Productievraag van {part_id} kan niet opnieuw worden bewezen: {exc}"})

    profiles,tools,formulas=load_machine_profiles(project),load_tools(project),load_formulas(project)
    current_machine=build_machine_snapshot(profiles,tools,formulas)
    if str(current_machine.get("snapshot_hash") or "")!=str(snapshot.get("machine_snapshot_hash") or ""):
        reasons.append({"kind":"machine","message":"Machine-/formuleconfiguratie is gewijzigd"})
    tool_payload={"schema_version":"1.0","tools":[asdict(t) for t in sorted(tools,key=lambda x:x.tool_id)]}; tool_payload["snapshot_hash"]=stable_sha256(tool_payload)
    if str(tool_payload.get("snapshot_hash") or "")!=str(snapshot.get("tool_snapshot_hash") or ""):
        reasons.append({"kind":"tool","message":"Gereedschapsbibliotheek is gewijzigd"})

    reservation_ids=[str(x) for x in list(acceptance.get("reservation_ids") or [])]
    for rid in reservation_ids:
        ledger=project.profile_nesting_reservations.get(rid)
        if not isinstance(ledger,dict) or ledger.get("status")!="reserved" or str(ledger.get("run_id") or "")!=run_id:
            reasons.append({"kind":"reservation","message":f"Reservering {rid} is niet actief voor deze run"})
    try:
        physical_requests=_reservation_requests_from_plan(project,record)
    except Exception as exc:
        physical_requests=[]; reasons.append({"kind":"stock","message":str(exc)})
    if physical_requests and not reservation_ids:
        reasons.append({"kind":"reservation","message":"Fysieke stock is geselecteerd maar niet transactioneel voor deze geaccepteerde run gereserveerd"})
    if physical_requests and reservation_ids:
        expected=sorted((x.source_type,x.source_id,int(x.quantity)) for x in physical_requests)
        actual=[]
        for rid in reservation_ids:
            ledger=project.profile_nesting_reservations.get(rid) or {}
            actual.extend((str(x.get("source_type") or ""),str(x.get("source_id") or ""),int(x.get("quantity") or 0)) for x in list(ledger.get("requests") or []))
        if sorted(actual)!=expected:
            reasons.append({"kind":"reservation","message":"Actieve reserveringsledger komt niet exact overeen met de fysieke bronnen van het geaccepteerde plan"})
    # Exact selected source identity must remain unchanged.
    candidates=_snapshot_candidates(record)
    checked_physical=False
    for raw_bar in list(dict(record.get("plan") or {}).get("bars") or []):
        bar=dict(raw_bar); st=str(bar.get("source_type") or ""); sid=str(bar.get("source_id") or "")
        if st=="purchase_option":
            cid=f"purchase:{sid}"; snap=candidates.get(cid,{}); current=project.profile_nesting_purchase_options.get(sid)
            expected_hash=str(dict(snap.get("provenance") or {}).get("purchase_option_hash") or "")
            if not isinstance(current,dict) or (expected_hash and str(current.get("snapshot_hash") or "")!=expected_hash):
                reasons.append({"kind":"stock","message":f"Purchase option {sid} is gewijzigd of ontbreekt"})
        elif st in {"full_stock","remnant"} and not checked_physical:
            checked_physical=True
            try: _reservation_requests_from_plan(project,record)
            except Exception as exc: reasons.append({"kind":"stock","message":str(exc)})
    return {"fresh":not reasons,"reasons":reasons,"freshness_hash":stable_sha256(reasons)}

def cancel_acceptance(project: ProjectModel, run_id: str, *, user: str="system") -> None:
    record=_record(project,run_id); run=dict(record.get("run") or {}); acceptance=dict(record.get("acceptance") or {})
    if str(run.get("status") or "")==NestingRunStatus.RELEASED.value: raise ProfileNestingReleaseError("CWS-NEST-021","Vrijgegeven run kan niet via acceptatie-annulering worden teruggedraaid")
    if not acceptance or acceptance.get("status")!="accepted": raise ProfileNestingReleaseError("CWS-NEST-021","Er is geen actieve acceptatie")
    for rid in list(acceptance.get("reservation_ids") or []): release_reservation(project,rid,user=user)
    acceptance["status"]="cancelled"; acceptance["cancelled_at"]=utc_now_iso(); acceptance["cancelled_by"]=user; tmp=dict(acceptance); tmp.pop("record_hash",None); acceptance["record_hash"]=stable_sha256(tmp); record["acceptance"]=acceptance
    run["status"]=NestingRunStatus.FEASIBLE.value; run["accepted_at"]=""; run["stock_reservations"]=[]; run["modified_at"]=utc_now_iso(); record["run"]=run; project.audit("profile_nesting.acceptance_cancelled",user=user,entity_id=run_id)


def release_nesting_run(project: ProjectModel, run_id: str, output_dir: str|Path, *, user: str="system", package_name: str|None=None, copy_part_artifacts: bool=True) -> tuple[NestingReleaseRecord,Any]:
    record=_record(project,run_id); run=dict(record.get("run") or {}); acceptance=dict(record.get("acceptance") or {})
    if str(run.get("status") or "")==NestingRunStatus.RELEASED.value and isinstance(record.get("release"),dict):
        raw=dict(record["release"]); return NestingReleaseRecord(**{k:v for k,v in raw.items() if k in NestingReleaseRecord.__dataclass_fields__}),None
    if str(run.get("status") or "")!=NestingRunStatus.ACCEPTED.value or acceptance.get("status")!="accepted": raise ProfileNestingReleaseError("CWS-NEST-021","Run moet eerst geaccepteerd zijn")
    fresh=_accepted_freshness(project,run_id)
    if not fresh["fresh"]: raise ProfileNestingReleaseError("CWS-NEST-022","Geaccepteerd plan is niet meer release-fresh",details=fresh)
    # For production release, linked parts must themselves be released when a
    # Part Workbench exists.  Synthetic/headless canonical parts without a
    # Workbench may use explicit released Part.status.
    snapshot=dict(record.get("input_snapshot") or {})
    bad=[]
    for line in list(snapshot.get("demand_lines") or []):
        part=project.parts.get(str(line.get("part_id") or ""));
        if part is None: bad.append(str(line.get("part_id") or "")); continue
        wb_status=str(dict(part.workbench or {}).get("current_revision",{}).get("review_status") or part.status)
        if wb_status!=ReviewStatus.RELEASED.value: bad.append(part.internal_id)
    if bad: raise ProfileNestingReleaseError("CWS-NEST-021","Release vereist vrijgegeven brononderdelen",details={"part_ids":bad})
    release_id=str(uuid4()); released_at=utc_now_iso()
    try:
        package=create_release_package(project,record,output_dir,release_id=release_id,released_at=released_at,released_by=user,package_name=package_name,copy_part_artifacts=copy_part_artifacts)
        verify=verify_release_package(package.root)
        if not verify.get("valid"): raise ProfileNestingReleaseError("CWS-NEST-029","Releasepakket faalt checksumverificatie",details=verify)
        release=NestingReleaseRecord(release_id=release_id,run_id=run_id,project_id=project.project_id,acceptance_id=str(acceptance.get("acceptance_id") or ""),plan_hash=str(dict(record.get("plan") or {}).get("plan_hash") or ""),input_snapshot_hash=str(snapshot.get("snapshot_hash") or ""),validation_report_hash=str(dict(record.get("validation_report") or {}).get("report_hash") or ""),released_at=released_at,released_by=user,package_path=str(package.root),package_zip_path=str(package.zip_path),package_manifest_hash=str(package.manifest.get("manifest_hash") or ""),package_zip_sha256=__import__("hashlib").sha256(package.zip_path.read_bytes()).hexdigest(),neutral_job_manifest_hash=str(package.manifest.get("neutral_job_manifest_hash") or ""),machine_transfer_allowed=False); release.refresh_hash()
        before=stable_sha256(record); record["release"]=asdict(release); run=dict(record.get("run") or {}); run["status"]=NestingRunStatus.RELEASED.value; run["released_at"]=released_at; run["modified_at"]=released_at; run["output_artifacts"]=[asdict(x) for x in package.artifacts]; run.setdefault("audit",[]).append({"event":"released","at":released_at,"user":user,"release_hash":release.record_hash,"package_manifest_hash":release.package_manifest_hash}); record["run"]=run; project.audit("profile_nesting.released",user=user,entity_id=run_id,before_hash=before,after_hash=stable_sha256(record),details={"release_id":release_id,"package_manifest_hash":release.package_manifest_hash,"machine_transfer_allowed":False})
        return release,package
    except Exception:
        # Accepted state and reservation remain intact so a write failure can be
        # retried safely; no release status is committed on output failure.
        raise


def release_summary(project: ProjectModel, run_id: str) -> dict[str,Any]:
    rec=_record(project,run_id); return {"run":deepcopy(rec.get("run") or {}),"acceptance":deepcopy(rec.get("acceptance") or {}),"release":deepcopy(rec.get("release") or {}),"freshness":_accepted_freshness(project,run_id) if rec.get("acceptance") else {"fresh":False,"reasons":[{"kind":"acceptance","message":"not accepted"}]}}


__all__=["PHASE7_ACCEPTANCE_SCHEMA_VERSION","PHASE7_RELEASE_SCHEMA_VERSION","ProfileNestingReleaseError","NestingAcceptanceRecord","NestingReleaseRecord","accept_nesting_run","cancel_acceptance","release_nesting_run","release_summary"]
