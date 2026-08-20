"""Atomic profile-stock reservation transactions on ProjectModel state."""
from __future__ import annotations

from dataclasses import asdict
import threading
from typing import Iterable
from uuid import uuid4

from cws_convertor.project.model import ProjectModel, stable_sha256
from .models import ReservationRecord, ReservationRequest

_LOCK = threading.RLock()

class ReservationConflict(RuntimeError):
    code = "CWS-NEST-025"


def reserve_physical_stock(project: ProjectModel, requests: Iterable[ReservationRequest], *, run_id: str = "", user: str = "system", reservation_id: str | None = None) -> ReservationRecord:
    reqs = list(requests)
    if not reqs:
        raise ValueError("Minimaal één reserveringsrequest is vereist")
    rid = reservation_id or str(uuid4())
    with _LOCK:
        if rid in project.profile_nesting_reservations:
            raise ReservationConflict(f"Reservering {rid} bestaat al")
        # Preflight everything before mutating anything.
        staged: list[tuple[str, object, int]] = []
        seen: set[tuple[str, str]] = set()
        for req in reqs:
            key = (req.source_type, req.source_id)
            if key in seen: raise ReservationConflict(f"Dubbele reserveringsrequest voor {key}")
            seen.add(key)
            if req.quantity < 1: raise ValueError("Reserveringsquantity moet positief zijn")
            if req.source_type == "full_stock":
                entity = project.stock_items.get(req.source_id)
                if entity is None: raise ReservationConflict(f"Voorraaditem {req.source_id} bestaat niet")
                if req.expected_reservation_revision is not None and entity.reservation_revision != req.expected_reservation_revision:
                    raise ReservationConflict(f"Voorraaditem {req.source_id} is intussen gewijzigd")
                free = int(round(float(entity.available_quantity) - float(entity.reserved_quantity)))
                if entity.status not in {"available", "reserved"} or free < req.quantity:
                    raise ReservationConflict(f"Voorraaditem {req.source_id} is niet voldoende beschikbaar")
                staged.append((req.source_type, entity, req.quantity))
            elif req.source_type == "remnant":
                entity = project.remnants.get(req.source_id)
                if entity is None: raise ReservationConflict(f"Reststuk {req.source_id} bestaat niet")
                if req.quantity != 1: raise ReservationConflict("Een fysiek reststuk kan maar één keer worden gereserveerd")
                if req.expected_reservation_revision is not None and entity.reservation_revision != req.expected_reservation_revision:
                    raise ReservationConflict(f"Reststuk {req.source_id} is intussen gewijzigd")
                if entity.status != "available" or entity.reservation_ids:
                    raise ReservationConflict(f"Reststuk {req.source_id} is niet beschikbaar")
                staged.append((req.source_type, entity, 1))
            else:
                raise ValueError("Alleen fysieke full_stock/remnant bronnen worden gereserveerd")
        before = stable_sha256({"stock": project.stock_items, "remnants": project.remnants, "ledger": project.profile_nesting_reservations})
        project.profile_nesting_reservation_revision += 1
        for source_type, entity, quantity in staged:
            if source_type == "full_stock":
                entity.reserved_quantity += quantity
                entity.reservation_ids.append(rid)
                entity.reservation_revision += 1
                entity.status = "reserved" if entity.reserved_quantity >= entity.available_quantity else "available"
            else:
                entity.reservation_ids.append(rid)
                entity.reservation_revision += 1
                entity.status = "reserved"
        record = ReservationRecord(reservation_id=rid, run_id=run_id, project_id=project.project_id,
                                   requests=[asdict(r) for r in reqs], created_by=user,
                                   project_reservation_revision=project.profile_nesting_reservation_revision)
        record.refresh_hash(); project.profile_nesting_reservations[rid] = asdict(record)
        after = stable_sha256({"stock": project.stock_items, "remnants": project.remnants, "ledger": project.profile_nesting_reservations})
        project.audit("profile_nesting.stock_reserved", user=user, entity_id=rid, before_hash=before, after_hash=after,
                      details={"run_id": run_id, "request_count": len(reqs)})
        return record


def release_reservation(project: ProjectModel, reservation_id: str, *, user: str = "system") -> None:
    with _LOCK:
        raw = project.profile_nesting_reservations.get(reservation_id)
        if not raw: raise ReservationConflict(f"Onbekende reservering {reservation_id}")
        if raw.get("status") != "reserved": raise ReservationConflict("Reservering is niet actief")
        for req in raw.get("requests", []):
            source_type, source_id, quantity = req["source_type"], req["source_id"], int(req.get("quantity", 1))
            if source_type == "full_stock":
                entity = project.stock_items[source_id]
                entity.reserved_quantity = max(0.0, entity.reserved_quantity - quantity)
                entity.reservation_ids = [x for x in entity.reservation_ids if x != reservation_id]
                entity.reservation_revision += 1
                entity.status = "available"
            elif source_type == "remnant":
                entity = project.remnants[source_id]
                entity.reservation_ids = [x for x in entity.reservation_ids if x != reservation_id]
                entity.reservation_revision += 1
                entity.status = "available"
        project.profile_nesting_reservation_revision += 1
        raw["status"] = "released"; raw["released_by"] = user
        raw["project_reservation_revision"] = project.profile_nesting_reservation_revision
        copy = dict(raw); copy.pop("record_hash", None); raw["record_hash"] = stable_sha256(copy)
        project.audit("profile_nesting.stock_reservation_released", user=user, entity_id=reservation_id)
