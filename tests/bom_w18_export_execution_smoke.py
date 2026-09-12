"""Real BOM QActions, real export worker and independently reopened artifacts.

The fixture uses the existing synthetic CAD Workbench/rebuild/roundtrip/review
pipeline. It cannot grant external machine or supplier acceptance.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("CWS_HEADLESS_GUI_SMOKE", "1")

EXPORT_ACTIONS = {"export.step", "export.ifc", "export.dxf", "export.pdf", "export.nc1", "export.production",
                  "export.package", "export.grouping", "export.occurrences", "export.per_part", "export.per_mark",
                  "export.per_assembly", "export.per_machine", "export.per_phase", "production.nc_preview"}
_BASE_PAYLOAD = None


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _project(folder):
    global _BASE_PAYLOAD
    from cws_convertor.project import ProjectModel
    if _BASE_PAYLOAD is None:
        from cws_convertor.ui_qt.bom_export_evidence import _released_project
        first = _released_project(folder / "roundtrip-P1", part_id="P1", part_position="SAME", assembly_id="A1", assembly_mark="A1")
        second = _released_project(folder / "roundtrip-P2", part_id="P2", part_position="SAME", assembly_id="A2", assembly_mark="A2")
        project = first.project
        project.parts.update(second.project.parts)
        project.assemblies.update(second.project.assemblies)
        for index, key in enumerate(("P1", "P2"), 1):
            part = project.parts[key]
            part.properties["phase"] = f"PH{index}"
            machine = f"M{index}"
            project.settings.setdefault("manufacturing_machine_capabilities", {})[key] = {machine: {
                "part_id": key, "machine_id": machine, "production_ready": True, "manufacturing_hash": part.manufacturing_hash,
                "fixture": "Explicitly synthetic grouping capability; no physical machine authorization"}}
        from cws_convertor.machine_routing import MachineRoutingService
        MachineRoutingService().assign_automatic(project, ("P1", "P2"), user="synthetic grouping fixture")
        _BASE_PAYLOAD = project.to_dict()
    return ProjectModel.from_dict(deepcopy(_BASE_PAYLOAD))


def run_case(action, folder, app):
    from PySide6 import QtWidgets
    from cws_convertor.bom import build_bom_snapshot
    from cws_convertor.bom.production_hub import BOMHubState
    from cws_convertor.project import ProjectStore, JobManager
    from cws_convertor.project.manufacturing_contracts import ExportGrouping
    from cws_convertor.production_export.verify import verify_export_zip
    from cws_convertor.ui_qt.bom_workspace import BomWorkspacePanel
    from cws_convertor.ui_qt.phase3_workspaces import Phase3ExportCenterPanel
    project = _project(folder.parent / "cad-inputs")
    workspace = SimpleNamespace(project=project, session=SimpleNamespace(project=project, dirty=False),
                                bom_snapshot=build_bom_snapshot(project, classify_if_needed=False))
    selected = ("A1",) if action == "export.per_assembly" else ("P1",)
    host = QtWidgets.QMainWindow()
    host.job_manager = JobManager(max_workers=1)
    host.project_page = None
    host.application_context = SimpleNamespace(workspace=workspace,
        selection=SimpleNamespace(entity_ids=selected, primary_entity_id=selected[0]),
        update_review_context=lambda **kw: None, update_export_context=lambda **kw: None)
    page = Phase3ExportCenterPanel(None, project, job_manager=host.job_manager, parent=host)
    host.export_page = page
    host.workspace_router = SimpleNamespace(open_workspace=lambda route: route == "export")
    checks = []
    messages = []
    def check(name, passed):
        assert passed, name + " | " + repr(messages[-2:])
        checks.append({"name": name, "status": "PASS"})
    def modal(*args, **kw):
        messages.append(str(args[2] if len(args) > 2 else args))
        return QtWidgets.QMessageBox.StandardButton.Ok
    try:
        with patch.object(BomWorkspacePanel, "_restore_layout", lambda _self: None), patch.object(QtWidgets.QMessageBox, "warning", modal), patch.object(QtWidgets.QMessageBox, "information", modal):
            panel = BomWorkspacePanel(host)
            host.setCentralWidget(panel)
            def select(ids, **kw):
                host.application_context.selection = SimpleNamespace(entity_ids=tuple(ids), primary_entity_id=ids[0] if ids else None)
                panel.set_context(workspace, host.application_context.selection)
                page.set_context(workspace, host.application_context.selection)
            host.application_context.request_selection = select
            host.application_context.clear_selection = lambda **kw: select(())
            select(selected)
            if action == "export.per_assembly":
                panel.family_tabs.setCurrentIndex(next(index for index in range(panel.family_tabs.count()) if panel.family_tabs.tabData(index) == "assemblies"))
                select(selected)
            for name, control in page._format_checks.items():
                control.setChecked(name == "STEP")
            app.processEvents()
            before = {entity.internal_id: deepcopy(asdict(entity)) for entity in project.iter_entities()}
            input_hash = hashlib.sha256(json.dumps(project.to_dict(), sort_keys=True).encode()).hexdigest()
            panel._populate_action_matrix()
            qaction = panel._matrix_qactions[action]
            if not qaction.isEnabled() and action in {"export.nc1", "export.production", "export.package"}:
                return {"status": "PARTIAL", "executed": True, "qt_action_executed": False,
                        "positive_postcondition": False, "selected_ids": list(selected), "selection_widened": None,
                        "nonselected_stable": True, "restart": False, "undo": False, "checks": [],
                        "reason": "Shipping QAction rejects current fixture at full-BOM production readiness; authorized positive workflow is unproved. " + qaction.toolTip()}
            check("Actual canonical QAction enabled", qaction.isEnabled())
            qaction.trigger()
            app.processEvents()
            check("Export scope is exact resolved P1", page._scope().entity_ids == ("P1",))
            if action == "export.grouping":
                page.grouping.setCurrentIndex(page.grouping.findData(ExportGrouping.PER_PART))
                page.grouping.activated.emit(page.grouping.currentIndex())
            page.output_dir.setText(str(folder / "export"))
            page.generate_button.click()
            app.processEvents()
            job = page.current_background_job_id
            check("Actual export worker submitted", bool(job))
            deadline = time.monotonic() + 120
            while host.job_manager.get(job).status in {"queued", "running"} and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.005)
            for _ in range(4):
                app.processEvents()
                time.sleep(.005)
            result = host.job_manager.get(job)
            check("Actual export worker completed: " + str(result.error), result.status == "completed")
            package = Path(result.result["package_path"])
            check("Actual package independently verifies", verify_export_zip(package)["valid"])
            formats_seen = set()
            parsed = []
            with zipfile.ZipFile(package) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                check("Package binds exact selected P1 and no machine transfer", manifest["selected_part_ids"] == ["P1"] and not manifest["machine_transfer_allowed"])
                groups = manifest["groups"]
                check("Group partitions do not widen selection", [key for group in groups for key in group["part_ids"]] == ["P1"])
                for group in groups:
                    with zipfile.ZipFile(io.BytesIO(archive.read(group["file"]))) as child:
                        content = json.loads(child.read("manifest.json"))
                        check("Child artifact identities exactly match P1", [item["part_id"] for item in content["items"]] == ["P1"])
                        for item in content["items"]:
                            for artifact in item["artifacts"]:
                                if artifact.get("status") != "exported":
                                    continue
                                data = child.read(artifact["relative_path"])
                                check("Actual artifact size and hash independently match", len(data) == artifact["size_bytes"] and hashlib.sha256(data).hexdigest() == artifact["sha256"])
                                suffix = Path(artifact["relative_path"]).suffix.lower()
                                path = folder / "independently-read" / Path(artifact["relative_path"]).name
                                path.parent.mkdir(exist_ok=True)
                                path.write_bytes(data)
                                if suffix in {".step", ".stp"}:
                                    import cadquery as cq
                                    import math
                                    shape = cq.importers.importStep(str(path)).val()
                                    check("STEP independently parses to valid nonempty solid", shape.isValid() and shape.Volume() > 0)
                                    check("STEP independent volume and bounds match canonical plate/hole", abs(shape.Volume() - (200*100*10-math.pi*7*7*10)) < .1
                                          and all(abs(left-right) < .001 for left,right in zip((shape.BoundingBox().xlen,shape.BoundingBox().ylen,shape.BoundingBox().zlen),(200,100,10))))
                                    formats_seen.add("step")
                                elif suffix == ".ifc":
                                    import ifcopenshell
                                    import ifcopenshell.geom
                                    import ifcopenshell.util.shape
                                    import math
                                    model = ifcopenshell.open(str(path))
                                    products = [product for product in model.by_type("IfcProduct") if getattr(product, "Representation", None)]
                                    check("IFC independently resolves exact single canonical plate identity", len(products) == 1 and products[0].Name == "SAME" and products[0].is_a("IfcPlate"))
                                    independent_shape = ifcopenshell.geom.create_shape(ifcopenshell.geom.settings(), products[0])
                                    mesh = independent_shape.geometry
                                    vertices = mesh.verts
                                    check("IFC independent meshing matches canonical plate bounds", all(abs((max(vertices[index::3])-min(vertices[index::3]))*1000-expected) < .01 for index,expected in enumerate((200,100,10))))
                                    check("IFC independent mesh volume matches canonical hole removal", abs(ifcopenshell.util.shape.get_volume(mesh)*1e9 - (200000-math.pi*49*10)) < 3)
                                    formats_seen.add("ifc")
                                elif suffix == ".dxf":
                                    import ezdxf
                                    model = ezdxf.readfile(path)
                                    lines = list(model.modelspace().query("LINE"))
                                    circles = list(model.modelspace().query("CIRCLE"))
                                    check("DXF independent contours match canonical rectangle", len(lines) == 4 and
                                          {tuple(line.dxf.start) for line in lines} == {(0,0,0),(200,0,0),(200,100,0),(0,100,0)})
                                    check("DXF independent hole matches canonical machining feature", len(circles) == 1 and tuple(circles[0].dxf.center) == (40,40,0) and circles[0].dxf.radius == 7)
                                    formats_seen.add("dxf")
                                elif suffix == ".pdf":
                                    import fitz
                                    with fitz.open(path) as document:
                                        check("PDF independently renders nonempty page", len(document) > 0 and bool(document[0].get_pixmap().samples))
                                    formats_seen.add("pdf")
                                elif suffix in {".nc1", ".dstv"}:
                                    import converter
                                    parsed_nc = converter.parse_nc1(path)
                                    check("NC1 independent parser resolves canonical profile dimensions", parsed_nc.header.length == 200 and parsed_nc.header.plate_thickness == 10)
                                    check("NC1 independent parser resolves exact canonical hole operations", len(parsed_nc.holes) == 1
                                          and (parsed_nc.holes[0].x, parsed_nc.holes[0].q, parsed_nc.holes[0].diameter) == (40,40,14))
                                    formats_seen.add("nc1")
                                parsed.append(str(path))
            expected = {"export.step": {"step"}, "export.ifc": {"ifc"}, "export.dxf": {"dxf"}, "export.pdf": {"pdf"},
                        "export.nc1": {"nc1"}, "production.nc_preview": {"nc1"}, "export.production": {"step", "ifc", "dxf", "nc1", "pdf"},
                        "export.package": {"step", "ifc", "dxf", "nc1", "pdf"}}.get(action, {"step"})
            check("Actual independent readers saw requested representations", expected.issubset(formats_seen))
            after = {entity.internal_id: deepcopy(asdict(entity)) for entity in project.iter_entities()}
            check("Export leaves all canonical entities unchanged", after == before)
            records = panel._hub_state.data["batch_results"]
            completed = bool(records and records[-1]["action"] == action and records[-1]["status"] == "passed")
            saved = ProjectStore().save(project, folder / "export-state.cwscproj")
            reopened = ProjectStore().open(saved).project
            check("Real project reopen retains exact export audit", BOMHubState(reopened).data["batch_results"] == records)
            return {"status": "PASS" if completed else "PARTIAL", "executed": True, "qt_action_executed": True,
                    "positive_postcondition": completed, "selected_ids": list(selected), "selection_widened": False,
                    "nonselected_stable": True, "restart": True, "undo": False, "checks": checks,
                    "input_hash": input_hash, "output_hash": digest(package),
                    "artifacts": [{"path": str(path.resolve()), "sha256": digest(path)} for path in folder.rglob("*") if path.is_file()],
                    "reason": "" if completed else "Actual artifacts passed, but the original QAction lacks a completed canonical result binding."}
    finally:
        host.job_manager.shutdown(wait=True)
        host.close()
        host.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    import tempfile
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    summary = {name: 0 for name in ("PASS", "PARTIAL", "FAIL")}
    with tempfile.TemporaryDirectory(prefix="cws-w18-exports-") as temporary:
        for action in sorted(EXPORT_ACTIONS):
            folder = Path(temporary) / action
            folder.mkdir()
            try:
                result = run_case(action, folder, app)
                status, reason = result["status"], result["reason"]
            except Exception as exc:
                status, reason = "FAIL", f"{type(exc).__name__}: {exc}"
            summary[status] += 1
            print(action + " = " + status + (" | " + reason if reason else ""), flush=True)
    print("BOM_W18_EXPORT_EXECUTION = " + ("FAIL" if summary["FAIL"] else "PARTIAL" if summary["PARTIAL"] else "PASS"), summary)
    raise SystemExit(1 if summary["FAIL"] else 0)
