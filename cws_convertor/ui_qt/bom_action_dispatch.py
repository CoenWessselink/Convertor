"""Execute explicit BOM intents through the existing canonical workspaces.

An export form is PREPARED, not a successful export. Read-only machine review
never grants an assignment or manufacturing/transport authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
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


def _nesting(panel: Any, action: str, ids: tuple[str, ...]) -> _Outcome:
    from cws_convertor.optimization.plate_nesting.project_service import is_plate
    window, workspace = panel.window, panel._workspace
    _parts(workspace.project, ids)
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
        return _Outcome("prepared", "Zaag/snede-instellingen geopend; geen fictieve toeslag toegepast en nog geen berekening")
    if action == "optimize.compare":
        if plate:
            compare = getattr(page, "_compare_plans", None) or getattr(page, "compare_plans", None)
            if compare is None:
                raise ValueError("Vergelijken van plaatplannen is nog niet aangesloten; er is geen vergelijking uitgevoerd")
            result = compare()
            return _Outcome("passed" if result is not False else "blocked", "Plaatplanvergelijking uitgevoerd in de canonieke plaatnestingwerkruimte")
        page._phase3_action("compare")
        status_widget = getattr(page, "phase3_nesting_status", None)
        message = status_widget.text() if status_widget is not None and hasattr(status_widget, "text") else "Profiel-scenariocompare uitgevoerd"
        blocked = str(message).strip().upper().startswith("BLOCKED") or str(message).strip().upper().startswith("ERROR")
        return _Outcome("blocked" if blocked else "passed", str(message))
    if action == "optimize.alternatives":
        raise ValueError("Alternatieve profielen/materialen hebben nog geen canonieke uitvoerder; geen alternatief verzonnen")
    if action not in {"optimize.plate", "optimize.profile", "optimize.trade_length", "optimize.stock", "optimize"}:
        raise ValueError(f"Geen nestinguitvoerder voor {action}")
    return _Outcome("prepared", f"{route}: berekening voorbereid voor uitsluitend {len(ids)} geselecteerde onderdeel-IDs",
                    start=(page.solve if plate else page._start_solve), page=page)


def _export(panel: Any, action: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:
    from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScopeKind
    from cws_convertor.ui_qt.bom_export_completion import choose_and_start_bom_export
    window, page = panel.window, panel.window.export_page
    page._bom_export_binding = None
    formats = {"export.nc1": ("DSTV",), "export.step": ("STEP",), "export.ifc": ("IFC",),
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
    started, message = choose_and_start_bom_export(page)
    if not started:
        status = "cancelled" if "geannuleerd" in message.casefold() else "blocked"
        return _Outcome(status, message)
    return _Outcome(
        "prepared",
        message + ". Definitieve PASS/FAIL volgt uitsluitend via de bestaande Export Center-verificatie",
        page=page,
    )


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
               "drawing.setup", "drawing.format", "drawing.scale", "drawing.views", "drawing.print"}
    if action not in allowed:
        raise ValueError(f"Tekenactie {action} is nog niet afzonderlijk aangesloten; geen andere actie uitgevoerd (W18)")
    page = window.pdf_page
    key = ids[0]
    project = panel._workspace.project
    if action == "drawing.open_part" and key not in project.parts:
        raise ValueError("Onderdeeltekening vereist één onderdeel")
    if action == "drawing.open_assembly" and key not in project.assemblies:
        raise ValueError("Assemblytekening vereist één assembly")
    _open(window, "pdf")
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
        focus = page.scale if action == "drawing.scale" else page.format
        focus.setFocus()
        return _Outcome("prepared", f"{action}: bladinstellingen geopend voor {key}; nog geen uitvoer")
    result = page._generate(make_png=True, make_pdf=action in {"drawing.generate", "drawing.regenerate", "drawing.print"})
    if result is None:
        return _Outcome("blocked", page.status.text())
    paths = tuple(str(value) for value in (result.pdf_path, result.png_path) if value)
    if not paths or any(not Path(value).is_file() for value in paths):
        raise ValueError("De tekenuitvoerder heeft geen bestaande uitvoerbestanden teruggegeven")
    if action == "drawing.print":
        pdfs = tuple(value for value in paths if value.lower().endswith(".pdf"))
        if not pdfs:
            raise ValueError("Printactie heeft geen canoniek PDF-bestand opgeleverd")
        if os.environ.get("CWS_HEADLESS_GUI_SMOKE") == "1" or os.environ.get("QT_QPA_PLATFORM", "").casefold() == "offscreen":
            return _Outcome("prepared", "Canonieke PDF gegenereerd; native printerdialoog vereist interactieve Windows-acceptatie", pdfs)
        from cws_convertor.ui_qt.production_printing import print_pdf_file
        printed = print_pdf_file(pdfs[0], parent=page)
        return _Outcome("passed" if printed else "cancelled", "PDF naar de native Qt-printerroute gestuurd" if printed else "Printdialoog geannuleerd", pdfs)
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
    if (action.startswith("optimize.") or action.startswith("drawing.")) and getattr(panel, "_preflight_partition_mode", "eligible") == "machine":
        raise ValueError("Uitvoeren per machine is voor deze batchactie nog niet aangesloten; geen gecombineerde vervangende actie uitgevoerd")
    if action.startswith("optimize.") or action == "optimize":
        return _nesting(panel, action, ids)
    if action.startswith("export.") or action == "production_export":
        return _export(panel, action, ids, preflight)
    if action.startswith("drawing."):
        return _drawing(panel, action, ids, preflight)
    panel.action_requested.emit(route)
    return _Outcome("prepared", f"{action}: scope doorgezet naar {route}; geen voltooide bewerking geclaimd")
