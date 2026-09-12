"""Execute explicit BOM intents through the existing canonical workspaces.

An export form is PREPARED, not a successful export. Read-only machine review
never grants an assignment or manufacturing/transport authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable

from cws_convertor.project.model import stable_sha256


@dataclass(frozen=True)
class _Outcome:
    status: str
    message: str
    outputs: tuple[str, ...] = ()
    start: Callable[[], Any] | None = None
    page: Any = None


def _open(window: Any, route: str) -> None:
    if not window.workspace_router.open_workspace(route):
        raise ValueError(f"Werkruimte {route!r} is niet aangesloten; actie niet uitgevoerd")


def _parts(project: Any, ids: tuple[str, ...]) -> tuple[str, ...]:
    if not ids or any(key not in project.parts for key in ids):
        raise ValueError("Selecteer bestaande canonieke onderdelen; geen lege of verbrede scope")
    return ids


def _resolve_part_ids(project: Any, ids: tuple[str, ...]) -> tuple[str, ...]:
    """Resolve parts and assemblies without widening outside the requested hierarchy."""
    resolved: list[str] = []
    visiting: set[str] = set()

    def add(value: str) -> None:
        if value not in resolved:
            resolved.append(value)

    def visit_assembly(assembly_id: str) -> None:
        if assembly_id in visiting:
            raise ValueError(f"Cyclische assemblystructuur bij {assembly_id}")
        assembly = project.assemblies.get(assembly_id)
        if assembly is None:
            raise ValueError(f"Onbekende assembly {assembly_id}")
        visiting.add(assembly_id)
        for part_id in tuple(getattr(assembly, "part_ids", ()) or ()):
            if part_id not in project.parts:
                raise ValueError(f"Assembly {assembly_id} verwijst naar onbekend onderdeel {part_id}")
            add(str(part_id))
        for child_id in tuple(getattr(assembly, "child_assembly_ids", ()) or ()):
            visit_assembly(str(child_id))
        visiting.remove(assembly_id)

    for key in ids:
        if key in project.parts:
            add(key)
        elif key in project.assemblies:
            visit_assembly(key)
        else:
            raise ValueError(f"Productiescope bevat onbekend object {key}")
    if not resolved:
        raise ValueError("Productiescope bevat geen maakdelen")
    return tuple(resolved)


def _machine_review(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    from cws_convertor.machine_routing import MachineRoutingService
    project, workspace = panel._workspace.project, panel._workspace
    _parts(project, ids)
    service = MachineRoutingService()
    reports = service.project_capabilities(project, ids)
    assignments = service.assignments(project)
    rows, lines = [], []
    for key in ids:
        part = project.parts[key]
        readiness = workspace.readiness_for_part(key, formats=("nc1", "step", "ifc", "dxf", "production_pdf"))
        candidates = []
        for machine_id, report in sorted(reports.get(key, {}).items()):
            decision = service.route(key, {machine_id: report})
            report_hash = service._value(report, "manufacturing_hash", "")
            binding = ("current" if report_hash and report_hash == part.manufacturing_hash
                       else "stale" if report_hash else "unproven")
            candidates.append({
                "machine_id": machine_id, "reported_eligible": decision.eligible,
                "binding": binding, "blocking_codes": list(decision.blocking_codes),
                "reason": decision.reason,
            })
        eligible = {row["machine_id"]: reports[key][row["machine_id"]]
                    for row in candidates if row["reported_eligible"] and row["binding"] == "current"}
        preferred = assignments.get(key)
        decision = service.route(key, eligible, preferred_machine=(preferred.assigned_machine_id if preferred else ""))
        codes = tuple(readiness.get("blocking_codes", ()))
        item = {
            "part_id": key, "manufacturing_hash": part.manufacturing_hash,
            "recommended_candidate": decision.machine_id, "candidates": candidates,
            "canonical_readiness": readiness, "machine_transfer_allowed": False,
            "production_authorized_by_review": False,
        }
        rows.append(item)
        lines.append(f"{part.part_position or key} · kandidaat: {decision.machine_id or 'geen actueel bewezen kandidaat'}")
        lines.append("Actuele onderdeelcontrole: " + (", ".join(codes) or "geen onderdeelblockers gerapporteerd"))
        if action in {"machine.alternatives", "machine.explain", "machine.validate"}:
            for row in candidates:
                lines.append(f"  {row['machine_id']} · bronbinding {row['binding']} · "
                             + (", ".join(row['blocking_codes']) or row['reason']))
        if not candidates:
            lines.append("  Geen capabilityrapporten beschikbaar; geen machine verzonnen.")
    record = {"schema": "cws-bom-machine-review-1", "action_id": action,
              "project_id": project.project_id, "entity_ids": list(ids), "rows": rows,
              "machine_transfer_allowed": False, "production_release_allowed": False}
    record["capabilities_sha256"] = stable_sha256({key: reports.get(key, {}) for key in ids})
    record["display_text"] = "\n".join(lines) + "\nAlleen controle/advies; geen toewijzing of machinevrijgave."
    record["sha256"] = stable_sha256(record)
    panel._hub_state.data.setdefault("machine_reviews", {})[action] = record
    panel._hub_state.data["last_machine_review_action"] = action
    panel._last_machine_review = record
    panel.detail_tabs.setCurrentIndex(2)
    panel.detail_labels["machine"].setText(record["display_text"])
    return _Outcome("passed", f"{len(rows)} onderdelen opnieuw beoordeeld; advies vastgelegd, geen machinevrijgave")


def _machine_review_text(panel: Any, ids: tuple[str, ...]) -> str:
    from cws_convertor.machine_routing import MachineRoutingService
    if panel._workspace is None or panel._hub_state is None:
        return ""
    state = panel._hub_state.data
    record = state.get("machine_reviews", {}).get(state.get("last_machine_review_action", ""), {})
    if not record or set(record.get("entity_ids", ())) != set(ids):
        return ""
    valid_hash = record.get("sha256") == stable_sha256({key: value for key, value in record.items() if key != "sha256"})
    project = panel._workspace.project
    valid_parts = all(row["part_id"] in project.parts and row["manufacturing_hash"] == project.parts[row["part_id"]].manufacturing_hash
                      for row in record.get("rows", ()))
    reports = MachineRoutingService.project_capabilities(project, ids)
    valid_reports = record.get("capabilities_sha256") == stable_sha256({key: reports.get(key, {}) for key in ids})
    if not (valid_hash and valid_parts and valid_reports):
        return "Machineadvies is verouderd of beschadigd. Voer Geschiktheid opnieuw controleren uit; geen nieuwe vrijgave."
    return str(record.get("display_text", ""))


def _values(value: Any) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, (tuple, list, set)):
        return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return (str(value).strip(),) if str(value).strip() else ()


def _alternatives_review(panel: Any, ids: tuple[str, ...]) -> _Outcome:
    project = panel._workspace.project
    _parts(project, ids)
    row_by_entity = {
        entity_id: row
        for row in panel._selected_rows()
        for entity_id in tuple(getattr(row, "entity_ids", ()) or ())
        if entity_id in ids
    }
    rows = []
    candidate_count = 0
    for key in ids:
        part = project.parts[key]
        properties = getattr(part, "properties", {}) or {}
        profile_values = []
        material_values = []
        for name in ("alternative_profile", "alternative_profiles", "substitute_profile", "substitute_profiles"):
            profile_values.extend(_values(properties.get(name)))
        for name in ("alternative_material", "alternative_materials", "substitute_material", "substitute_materials"):
            material_values.extend(_values(properties.get(name)))
        row = row_by_entity.get(key)
        if row is not None:
            material_values.extend(_values(getattr(row, "alternative_material", "")))
        profile_values = list(dict.fromkeys(profile_values))
        material_values = list(dict.fromkeys(material_values))
        candidate_count += len(profile_values) + len(material_values)
        rows.append({
            "part_id": key,
            "manufacturing_hash": getattr(part, "manufacturing_hash", ""),
            "current_profile": getattr(part, "normalized_profile", "") or getattr(part, "profile", ""),
            "current_material": getattr(part, "normalized_material", "") or getattr(part, "material", ""),
            "declared_profile_alternatives": profile_values,
            "declared_material_alternatives": material_values,
        })
    record = {
        "schema": "cws-bom-alternative-review-1",
        "action_id": "optimize.alternatives",
        "project_id": project.project_id,
        "entity_ids": list(ids),
        "rows": rows,
        "candidate_count": candidate_count,
        "substitution_applied": False,
        "production_release_allowed": False,
    }
    record["sha256"] = stable_sha256(record)
    panel._hub_state.data.setdefault("optimization_reviews", {})["alternatives"] = record
    message = (f"{candidate_count} expliciet vastgelegde profiel/materiaalalternatieven beoordeeld; niets automatisch vervangen"
               if candidate_count else
               "Alternatieven beoordeeld: geen expliciet vastgelegde profiel/materiaalalternatieven; niets verzonnen of vervangen")
    return _Outcome("passed", message)


def _compare_plate_runs(panel: Any, ids: tuple[str, ...]) -> _Outcome:
    from cws_convertor.optimization.plate_nesting.project_service import _record_digest
    project = panel._workspace.project
    runs = project.settings.get("plate_nesting_runs", {}) if isinstance(project.settings, dict) else {}
    matching = []
    for record in runs.values() if isinstance(runs, dict) else ():
        if not isinstance(record, dict) or record.get("schema") != "cws-project-plate-run-2":
            continue
        if record.get("record_sha256") != _record_digest(record):
            continue
        scope = tuple(str(value) for value in record.get("inputs", {}).get("entity_ids", ()))
        if set(scope) != set(ids):
            continue
        plan = record.get("plan", {})
        if isinstance(plan, dict) and plan.get("plan_sha256"):
            matching.append(record)
    if len(matching) < 2:
        return _Outcome("blocked", "Geen twee integere plaatoptimalisaties voor exact deze selectie; niets fictief vergeleken")
    previous, current = matching[-2], matching[-1]
    old, new = previous["plan"], current["plan"]
    metric_names = ("utilization", "scrap_area_mm2", "cut_length_mm", "pierce_count")
    metrics = {
        name: {
            "previous": float(old.get(name, 0.0)),
            "current": float(new.get(name, 0.0)),
            "delta": float(new.get(name, 0.0)) - float(old.get(name, 0.0)),
        }
        for name in metric_names
    }
    comparison = {
        "schema": "cws-bom-plate-comparison-1",
        "action_id": "optimize.compare",
        "project_id": project.project_id,
        "entity_ids": list(ids),
        "previous_run_id": old.get("run_id", ""),
        "current_run_id": new.get("run_id", ""),
        "previous_plan_sha256": old.get("plan_sha256", ""),
        "current_plan_sha256": new.get("plan_sha256", ""),
        "metrics": metrics,
        "selection_widened": False,
        "production_release_allowed": False,
    }
    comparison["sha256"] = stable_sha256(comparison)
    panel._hub_state.data.setdefault("optimization_reviews", {})["plate_compare"] = comparison
    return _Outcome(
        "passed",
        "Plaatoptimalisaties vergeleken voor exact dezelfde selectie · "
        f"benutting Δ {metrics['utilization']['delta']:+.4f} · "
        f"restoppervlak Δ {metrics['scrap_area_mm2']['delta']:+.1f} mm² · "
        f"snijlengte Δ {metrics['cut_length_mm']['delta']:+.1f} mm · "
        f"pierces Δ {metrics['pierce_count']['delta']:+.0f}",
    )


def _production_review(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    from cws_convertor.integration.production_workflow import build_production_workflow_snapshot
    project, workspace = panel._workspace.project, panel._workspace
    part_ids = _resolve_part_ids(project, ids)
    if action == "production.route":
        snapshot = build_production_workflow_snapshot(workspace, part_ids).to_dict()
        record = {
            "schema": "cws-bom-production-route-review-1",
            "action_id": action,
            "project_id": project.project_id,
            "source_entity_ids": list(ids),
            "resolved_part_ids": list(part_ids),
            "workflow": snapshot,
            "selection_widened": False,
            "production_release_allowed": False,
        }
        record["sha256"] = stable_sha256(record)
        panel._hub_state.data.setdefault("production_reviews", {})["route"] = record
        panel.action_requested.emit("production_workflow")
        return _Outcome(
            "passed",
            f"Productieroute beoordeeld voor {len(part_ids)} maakdelen · klaar {snapshot['ready_part_count']} · geblokkeerd {snapshot['blocked_part_count']} · volgende stap {snapshot['next_action']}",
        )
    if action == "production.operations":
        rows = []
        operation_count = 0
        for key in part_ids:
            part = project.parts[key]
            features = [dict(value) for value in tuple(getattr(part, "production_features", ()) or ()) if isinstance(value, dict)]
            operation_count += len(features)
            rows.append({
                "part_id": key,
                "manufacturing_hash": getattr(part, "manufacturing_hash", ""),
                "operations": features,
                "operation_count": len(features),
            })
        record = {
            "schema": "cws-bom-production-operations-review-1",
            "action_id": action,
            "project_id": project.project_id,
            "source_entity_ids": list(ids),
            "resolved_part_ids": list(part_ids),
            "rows": rows,
            "operation_count": operation_count,
            "selection_widened": False,
            "production_release_allowed": False,
        }
        record["sha256"] = stable_sha256(record)
        panel._hub_state.data.setdefault("production_reviews", {})["operations"] = record
        panel.action_requested.emit("production_workflow")
        return _Outcome("passed", f"{operation_count} canonieke productiebewerkingen beoordeeld voor {len(part_ids)} maakdelen; niets gewijzigd")
    raise ValueError(f"Productieactie {action} is niet aangesloten")


def _nesting(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    from cws_convertor.optimization.plate_nesting.project_service import is_plate
    window, workspace = panel.window, panel._workspace
    _parts(workspace.project, ids)
    if action == "optimize.alternatives":
        return _alternatives_review(panel, ids)
    types = {is_plate(workspace.project.parts[key]) for key in ids}
    requested = True if action == "optimize.plate" else False if action in {"optimize.profile", "optimize.trade_length"} else None
    if len(types) != 1 or (requested is not None and types != {requested}):
        raise ValueError("BOM-nestingscope bevat verkeerde of gemengde plaat/profielfamilies; selecteer één passende familie")
    plate = next(iter(types))
    route = "plate_nesting" if plate else "profile_nesting"
    page = window.plate_nesting_page if plate else window.profiles_page
    if getattr(page, "_job_id", None):
        raise ValueError("Er loopt al een nestingberekening; annuleer of voltooi die eerst")
    _open(window, route)
    page.set_context(workspace, window.application_context.selection)
    page.scope_combo.setCurrentIndex(page.scope_combo.findData("selection"))
    if not plate:
        page._analyse()
    if action in {"optimize.remnants_include", "optimize.remnants_exclude", "optimize.stock"}:
        include = action == "optimize.remnants_include"
        if plate:
            page.include_remnants.setChecked(include)
            page._refresh_input()
        else:
            old = str(page.stock_policy_combo.currentData())
            if action == "optimize.stock":
                policy = "stock_only"
            elif include:
                policy = "stock_and_remnants" if old in {"stock_only", "stock_and_remnants"} else "stock_remnants_purchase"
            else:
                policy = "stock_only" if old in {"stock_only", "stock_and_remnants", "remnants_only"} else "stock_purchase"
            page.stock_policy_combo.setCurrentIndex(page.stock_policy_combo.findData(policy))
        if action != "optimize.stock":
            return _Outcome("prepared", f"{route}: scope {len(ids)} onderdeel-IDs; reststuk/voorraadkeuze ingesteld. Nog niet berekend")
    if action == "optimize.trade_length":
        page.stock_policy_combo.setCurrentIndex(page.stock_policy_combo.findData("new_only"))
    if action == "optimize.kerf":
        if plate:
            page.kerf.setFocus(); page.kerf.selectAll()
        else:
            page.phase3_nesting_tabs.setCurrentWidget(page.machine_settings)
            page.machine_settings.tabs.setCurrentIndex(0)
            page.machine_settings.kerf_value.setFocus()
            return _Outcome("prepared", "Wijzig de kerf van het gekozen machineprofiel en sla op; daarna is opnieuw machinevalidatie nodig", page=page.machine_settings)
        return _Outcome("prepared", "Zaag/snede-instellingen geopend; geen fictieve toeslag toegepast en nog geen berekening")
    if action == "optimize.compare":
        if plate:
            return _compare_plate_runs(panel, ids)
        page._phase3_action("compare")
        return _Outcome("prepared", "Bestaande scenariocompare geopend; zie de runvalidatie voor het resultaat")
    if action not in {"optimize.plate", "optimize.profile", "optimize.trade_length", "optimize.stock", "optimize"}:
        raise ValueError(f"Geen nestinguitvoerder voor {action}")
    return _Outcome("prepared", f"{route}: berekening voorbereid voor uitsluitend {len(ids)} geselecteerde onderdeel-IDs",
                    start=(page.solve if plate else page._start_solve), page=page)


def _export(panel: Any, action: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScopeKind
    window, page = panel.window, panel.window.export_page
    page._bom_export_binding = None
    formats = {"export.nc1": ("DSTV",), "production.nc_preview": ("DSTV",),
               "export.step": ("STEP",), "export.ifc": ("IFC",),
               "export.dxf": ("DXF",), "export.pdf": ("PDF",),
               "export.production": ("DSTV", "STEP", "IFC", "DXF", "PDF"),
               "production_export": ("DSTV", "STEP", "IFC", "DXF", "PDF"),
               "export.package": ("DSTV", "STEP", "IFC", "DXF", "PDF")}
    grouping = {"export.grouping": "choose_explicit_grouping", "export.per_part": "per_part", "export.per_mark": "part_mark",
                "export.per_assembly": "assembly", "export.per_machine": "machine",
                "export.per_phase": "phase"}.get(action)
    if action not in formats and grouping is None:
        raise ValueError(f"Exportactie {action} is nog niet afzonderlijk aangesloten; geen bredere export uitgevoerd (W18)")
    if getattr(panel, "_preflight_partition_mode", "eligible") == "machine":
        grouping = "machine"
    _open(window, "export")
    page.set_context(panel._workspace, window.application_context.selection)
    parts = []
    for key in ids:
        if key in panel._workspace.project.parts:
            parts.append(key)
        elif key in panel._workspace.project.assemblies:
            parts.extend(page.service._assembly_part_ids(key, True))
        else:
            raise ValueError("Deze uitvoerscope bevat geen ondersteund onderdeel/assembly: " + key)
    if not parts:
        raise ValueError("Exportscope bevat geen maakdelen")
    page.scope.setCurrentIndex(page.scope.findData(ExportScopeKind.SELECTED_PARTS))
    page.scope_values.setText(",".join(dict.fromkeys(parts)))
    for name, check in page._format_checks.items():
        if action in formats:
            check.setChecked(name in formats[action])
    page._bom_unsupported_grouping = ""
    page.generate_button.setEnabled(True)
    if grouping == "choose_explicit_grouping":
        page._bom_export_binding = {"panel": panel, "workspace": panel._workspace, "preflight": preflight,
                                    "ids": tuple(sorted(set(parts))), "grouping": grouping,
                                    "formats": tuple(page._formats()), "action": action}
        page.grouping.setFocus()
        return _Outcome("prepared", "Kies en controleer de groepering en uitvoermap; nog geen bestanden gemaakt")
    if grouping == "part_mark" and all(key in panel._workspace.project.assemblies for key in ids):
        grouping = "assembly_mark"
    chosen = ExportGrouping(grouping or "combined")
    page.grouping.setCurrentIndex(page.grouping.findData(chosen))
    page._bom_export_binding = {"panel": panel, "workspace": panel._workspace, "preflight": preflight,
                                "ids": tuple(sorted(set(parts))), "grouping": chosen.value,
                                "formats": tuple(page._formats()), "action": action}
    prepared = page._preflight()
    window.application_context.update_export_context(active_export_scope=tuple(parts), grouping=chosen.value,
                                                      formats=tuple(page._formats()), preflight_hash=preflight.preflight_sha256)
    if prepared is None or prepared.blocking_codes or any(item.blocking_codes for item in prepared.items):
        return _Outcome("blocked", "Exacte exportselectie/format ingesteld maar preflight blokkeert; geen bestanden gemaakt")
    if action == "production.nc_preview":
        return _Outcome("prepared", f"DSTV/NC1-preview voorbereid voor exact {len(tuple(dict.fromkeys(parts)))} maakdelen; preflight akkoord, geen bestand of vrijgave gemaakt")
    return _Outcome("prepared", "Exacte exportselectie en formats ingesteld: " + ", ".join(page._formats())
                    + ". Kies/controleer de uitvoermap en bevestig Generate; nog geen bestanden gemaakt")


def _drawing(panel: Any, action: str, ids: tuple[str, ...], preflight: Any = None) -> _Outcome:
    if action == "drawing.batch_pdf":
        if preflight is None:
            raise ValueError("Batchtekening vereist een actuele BOM-preflight")
        from .bom_drawing_batch import prepare_batch_action
        return prepare_batch_action(panel, ids, preflight)
    window = panel.window
    if len(ids) != 1:
        raise ValueError("Deze tekenactie vereist één onderdeel of één assembly; batchtekeningen zijn nog apart af te nemen (W18)")
    allowed = {"drawing.open_part", "drawing.open_assembly", "drawing.generate", "drawing.regenerate",
               "drawing.preview", "drawing.approve", "drawing.revision", "drawing.dimension_check",
               "drawing.setup", "drawing.format", "drawing.scale", "drawing.views"}
    if action not in allowed:
        raise ValueError(f"Tekenactie {action} is nog niet afzonderlijk aangesloten; geen andere actie uitgevoerd (W18)")
    page = window.pdf_page
    key = ids[0]
    project = panel._workspace.project
    if action == "drawing.open_part" and key not in project.parts:
        raise ValueError("Onderdeeltekening vereist één onderdeel")
    if action == "drawing.open_assembly" and key not in project.assemblies:
        raise ValueError("Assemblytekening vereist één assembly")
    _open(window, "pdf_review")
    page.set_context(panel._workspace, window.application_context.selection)
    if page._entity_id != key:
        raise ValueError("Tekeningselectie komt niet overeen met de gevraagde canonieke ID")
    if action == "drawing.approve":
        page._release_dimension_revision()
        ok = page._dimension_document is not None and page._dimension_document.status == "released"
        return _Outcome("passed" if ok else "blocked", page.status.text())
    if action == "drawing.revision":
        before = getattr(page._dimension_document, "drawing_revision", None)
        page._begin_dimension_revision()
        after = getattr(page._dimension_document, "drawing_revision", None)
        return _Outcome("passed" if after != before else "cancelled", page.status.text())
    if action in {"drawing.setup", "drawing.format", "drawing.scale", "drawing.views"}:
        if action == "drawing.views":
            buttons = getattr(page, "view_buttons", {})
            focus = next(iter(buttons.values()), None)
            if focus is None:
                raise ValueError("Aanzichtkeuze is niet aangesloten; geen andere bladinstelling geopend")
        else:
            focus = page.scale if action == "drawing.scale" else page.format
        focus.setFocus()
        return _Outcome("prepared", f"{action}: bladinstellingen geopend voor {key}; nog geen uitvoer")
    result = page._generate(make_png=True, make_pdf=action in {"drawing.generate", "drawing.regenerate"})
    if result is None:
        return _Outcome("blocked", page.status.text())
    paths = tuple(str(value) for value in (result.pdf_path, result.png_path) if value)
    if not paths or any(not Path(value).is_file() for value in paths):
        raise ValueError("De tekenuitvoerder heeft geen bestaande uitvoerbestanden teruggegeven")
    if action == "drawing.dimension_check":
        from cws_convertor.drawings import DrawingLinter
        lint = DrawingLinter.lint(result.document).to_dict()
        blocked = any(item.get("blocking", True) for item in lint["issues"])
        return _Outcome("blocked" if blocked else "passed", json.dumps(lint, ensure_ascii=False), paths)
    return _Outcome("passed", page.status.text(), paths)


def _dispatch(panel: Any, action: str, route: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    workspace = panel._workspace
    if workspace is None or not ids:
        raise ValueError("Geen actieve BOM-selectie; de actie is niet uitgevoerd")
    context = panel.window.application_context
    if getattr(context, "workspace", workspace) is not workspace:
        raise ValueError("Project gewijzigd sinds BOM-preflight")
    if workspace.bom_snapshot.snapshot_sha256 != preflight.snapshot_sha256:
        raise ValueError("BOM gewijzigd sinds preflight")
    if any(workspace.project.get_entity(key) is None for key in ids):
        raise ValueError("De selectie bevat verwijderde of onbekende canonieke objecten")
    if action in {"production_export", "export.production", "export.nc1", "export.package"}:
        validation = workspace.bom_snapshot.validation
        if validation is None or not validation.production_ready:
            raise ValueError("De volledige BOM is niet productiegereed; productie-export blijft geblokkeerd")
    if action in {"machine.recommend", "machine.validate", "machine.alternatives", "machine.explain"}:
        return _machine_review(panel, action, ids)
    if action in {"production.route", "production.operations"}:
        return _production_review(panel, action, ids)
    if action == "production.nc_preview":
        return _export(panel, action, ids, preflight)
    if (action.startswith("optimize.") or action.startswith("drawing.")) and getattr(panel, "_preflight_partition_mode", "eligible") == "machine":
        raise ValueError("Uitvoeren per machine is voor deze batchactie nog niet aangesloten; geen gecombineerde vervangende actie uitgevoerd")
    if action.startswith("optimize.") or action == "optimize":
        return _nesting(panel, action, ids)
    if action.startswith("export.") or action == "production_export":
        return _export(panel, action, ids, preflight)
    if action.startswith("drawing."):
        return _drawing(panel, action, ids, preflight)
    # Only the explicit legacy toolbar navigation commands may open a workspace
    # without an executor. A canonical or misspelled action must never lose its
    # intent by quietly becoming navigation to its route.
    navigation = {"edit": "edit", "inspect": "inspect", "viewer": "viewer"}
    if action in navigation and route == navigation[action]:
        panel.action_requested.emit(route)
        return _Outcome("prepared", f"{action}: werkruimte geopend voor de selectie; nog niets uitgevoerd")
    raise ValueError(f"Geen afzonderlijke BOM-uitvoerder voor {action}; route {route!r} niet uitgevoerd")
