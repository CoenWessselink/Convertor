from __future__ import annotations

from pathlib import Path

PATH = Path("cws_convertor/ui_qt/bom_action_dispatch.py")
text = PATH.read_text(encoding="utf-8")

old_import = """def _export(panel: Any, action: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:\n    from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScopeKind\n    window, page = panel.window, panel.window.export_page\n"""
new_import = """def _export(panel: Any, action: str, ids: tuple[str, ...], preflight: Any) -> _Outcome:\n    from cws_convertor.project.manufacturing_contracts import ExportGrouping, ExportScopeKind\n    from cws_convertor.ui_qt.bom_export_completion import choose_and_start_bom_export\n    window, page = panel.window, panel.window.export_page\n"""
if old_import not in text:
    raise SystemExit("dispatcher import anchor not found")
text = text.replace(old_import, new_import, 1)

old_tail = """    if prepared is None or prepared.blocking_codes or any(item.blocking_codes for item in prepared.items):\n        return _Outcome(\"blocked\", \"Exacte exportselectie/format ingesteld maar preflight blokkeert; geen bestanden gemaakt\")\n    return _Outcome(\"prepared\", \"Exacte exportselectie en formats ingesteld: \" + \", \".join(page._formats())\n                    + \". Kies/controleer de uitvoermap en bevestig Generate; nog geen bestanden gemaakt\")\n"""
new_tail = """    if prepared is None or prepared.blocking_codes or any(item.blocking_codes for item in prepared.items):\n        return _Outcome(\"blocked\", \"Exacte exportselectie/format ingesteld maar preflight blokkeert; geen bestanden gemaakt\")\n    started, message = choose_and_start_bom_export(page)\n    if not started:\n        status = \"cancelled\" if \"geannuleerd\" in message.casefold() else \"blocked\"\n        return _Outcome(status, message)\n    return _Outcome(\n        \"prepared\",\n        message + \". Definitieve PASS/FAIL volgt uitsluitend via de bestaande Export Center-verificatie\",\n        page=page,\n    )\n"""
if old_tail not in text:
    raise SystemExit("dispatcher export tail anchor not found")
text = text.replace(old_tail, new_tail, 1)
PATH.write_text(text, encoding="utf-8")
print("PASS: dispatcher now starts canonical Export Center after exact BOM export preflight")
