"""Immutable stock/purchase/remnant snapshots and compatibility prechecks."""
from __future__ import annotations

from dataclasses import asdict
import math
from typing import Iterable

from cws_convertor.project.model import ProjectModel, StockItem, Remnant, stable_sha256
from .models import NestingDemandLine, NestingMessage, PurchaseOption, StockCandidate, StockSnapshot
from .units import LengthKernel

ALLOWED_POLICIES = {
    "new_only", "stock_only", "remnants_only", "stock_and_remnants",
    "stock_remnants_purchase", "stock_first", "remnants_first", "cost",
    "waste", "lead_time",
}


def _candidate_from_stock(item: StockItem, kernel: LengthKernel) -> StockCandidate:
    free = max(0, int(round(float(item.available_quantity) - float(item.reserved_quantity))))
    c = StockCandidate(
        candidate_id=f"stock:{item.internal_id}", source_type="full_stock", source_id=item.internal_id,
        physical=True, profile_id=item.profile, section_hash=item.section_hash or str(item.properties.get("section_hash") or ""),
        material=item.material, material_grade=item.grade, length_mm=float(item.stock_length_mm),
        length_units=kernel.mm_to_units(item.stock_length_mm), available_quantity=free,
        heat=item.heat_number, batch=item.batch, certificate=item.certificate,
        supplier=item.supplier, location=item.location, unit_price=float(item.unit_price),
        minimum_reusable_mm=float(item.minimum_reusable_mm), reservation_status=item.status,
        reservation_revision=int(item.reservation_revision), measurement_reliability=item.measurement_reliability,
        provenance={"project_entity": item.internal_id},
    ); c.refresh_hash(); return c


def _candidate_from_remnant(item: Remnant, kernel: LengthKernel) -> StockCandidate:
    reserved = bool(item.reservation_ids) or item.status == "reserved"
    c = StockCandidate(
        candidate_id=f"remnant:{item.internal_id}", source_type="remnant", source_id=item.internal_id,
        physical=True, profile_id=item.profile, section_hash=item.section_hash or str(item.properties.get("section_hash") or ""),
        material=item.material, material_grade=item.grade, length_mm=float(item.remaining_length_mm),
        length_units=kernel.mm_to_units(item.remaining_length_mm), available_quantity=0 if reserved else 1,
        heat=item.heat_number, batch=item.batch, certificate=item.certificate,
        supplier=item.supplier, location=item.location, unit_price=float(item.cost_book_value),
        minimum_reusable_mm=float(item.minimum_reusable_mm), reservation_status=item.status,
        reservation_revision=int(item.reservation_revision), measurement_reliability=item.measurement_reliability,
        provenance={"project_entity": item.internal_id, "parent_stock_item_id": item.stock_item_id},
    ); c.refresh_hash(); return c


def _candidate_from_purchase(item: PurchaseOption, kernel: LengthKernel) -> StockCandidate:
    item.refresh_hash()
    c = StockCandidate(
        candidate_id=f"purchase:{item.purchase_option_id}", source_type="purchase_option", source_id=item.purchase_option_id,
        physical=False, profile_id=item.profile_id, section_hash=item.section_hash, material=item.material,
        material_grade=item.material_grade, length_mm=float(item.length_mm), length_units=kernel.mm_to_units(item.length_mm),
        available_quantity=item.available_quantity, supplier=item.supplier, lead_time_days=int(item.lead_time_days),
        unit_price=float(item.unit_price), extra_cost=float(item.transport_cost + item.cutting_cost),
        minimum_reusable_mm=float(item.minimum_reusable_mm), reservation_status="not_physical",
        measurement_reliability="supplier_catalog", provenance={"purchase_option_hash": item.snapshot_hash},
    ); c.refresh_hash(); return c


def build_stock_snapshot(
    project: ProjectModel,
    *,
    purchase_options: Iterable[PurchaseOption] = (),
    policy: str = "stock_remnants_purchase",
    kernel: LengthKernel | None = None,
) -> StockSnapshot:
    if policy not in ALLOWED_POLICIES:
        raise ValueError(f"Onbekend stockbeleid {policy!r}")
    kernel = kernel or LengthKernel()
    candidates: list[StockCandidate] = []
    include_stock = policy not in {"new_only", "remnants_only"}
    include_rem = policy in {"remnants_only", "stock_and_remnants", "stock_remnants_purchase", "stock_first", "remnants_first", "cost", "waste", "lead_time"}
    include_purchase = policy in {"new_only", "stock_remnants_purchase", "stock_first", "remnants_first", "cost", "waste", "lead_time"}
    if include_stock:
        for item in sorted(project.stock_items.values(), key=lambda x: x.internal_id):
            if item.status in {"available", "reserved"} and item.stock_length_mm > 0:
                candidates.append(_candidate_from_stock(item, kernel))
    if include_rem:
        for item in sorted(project.remnants.values(), key=lambda x: x.internal_id):
            if item.status in {"available", "reserved"} and item.remaining_length_mm > 0:
                candidates.append(_candidate_from_remnant(item, kernel))
    if include_purchase:
        candidates.extend(_candidate_from_purchase(p, kernel) for p in sorted(purchase_options, key=lambda x: x.purchase_option_id))
    snap = StockSnapshot(project_id=project.project_id, policy=policy,
                         reservation_revision=int(project.profile_nesting_reservation_revision), candidates=candidates)
    snap.refresh_hash(); return snap


def evaluate_stock_compatibility(
    demand: NestingDemandLine,
    candidate: StockCandidate,
    *, head_trim_mm: float = 0.0, tail_trim_mm: float = 0.0, kerf_mm: float = 0.0,
) -> list[NestingMessage]:
    issues: list[NestingMessage] = []
    def add(code: str, text: str):
        issues.append(NestingMessage(code=code, severity="error", message=text, blocking=True,
                                     object_ids=[demand.part_id, candidate.source_id]))
    if candidate.available_quantity is not None and candidate.available_quantity <= 0:
        add("CWS-NEST-012", "Stockcandidate heeft geen vrije hoeveelheid.")
    if candidate.section_hash and demand.section_hash and candidate.section_hash != demand.section_hash:
        add("CWS-NEST-011", "Section identity van stock en onderdeel verschilt.")
    elif candidate.profile_id and demand.profile_id and candidate.profile_id != demand.profile_id:
        add("CWS-NEST-011", "Profiel van stock en onderdeel verschilt.")
    if candidate.material != demand.material or candidate.material_grade != demand.material_grade:
        add("CWS-NEST-013", "Materiaal/kwaliteit van stock en onderdeel verschilt.")
    if demand.heat_requirement and candidate.heat != demand.heat_requirement:
        add("CWS-NEST-013", "Vereiste heat komt niet overeen met stock.")
    if demand.certificate_requirement and candidate.certificate != demand.certificate_requirement:
        add("CWS-NEST-013", "Vereist certificaat komt niet overeen met stock.")
    required = float(demand.nominal_length_mm) + float(head_trim_mm) + float(tail_trim_mm) + max(0.0, float(kerf_mm))
    if not math.isfinite(required) or candidate.length_mm + 1e-9 < required:
        add("CWS-NEST-011", "Onderdeel past individueel niet in deze stocklengte inclusief rechte-cut toeslagen.")
    return issues


def stock_snapshot_to_dict(snapshot: StockSnapshot) -> dict:
    payload = asdict(snapshot)
    payload["snapshot_hash"] = snapshot.snapshot_hash
    return payload
