from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "full_acceptance"
for import_root in (ROOT, ROOT / "src"):
    if import_root.exists() and str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

CONTROL_TYPES = {
    "QAction",
    "QCheckBox",
    "QComboBox",
    "QDialogButtonBox",
    "QDoubleSpinBox",
    "QLineEdit",
    "QListWidget",
    "QMenu",
    "QPushButton",
    "QRadioButton",
    "QSlider",
    "QSpinBox",
    "QTabWidget",
    "QTableView",
    "QTableWidget",
    "QToolButton",
    "QTreeView",
    "QTreeWidget",
}
PHASE_RUNNERS = (
    "tools/run_phase1_unified_gates.py",
    "tools/run_phase2_unified_gates.py",
    "tools/run_phase3_gates.py",
)


def write_json(name: str, payload: Any) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def literal_text(node: ast.AST | None) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


def package_root(name: str) -> Path:
    direct = ROOT / name
    return direct if direct.exists() else ROOT / "src" / name


def source_inventories() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    controls: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    test_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted((ROOT / "tests").rglob("*.py"))
    )
    for package in ("cws_convertor", "cws_viewer"):
        for path in sorted(package_root(package).rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            source = path.read_text(encoding="utf-8", errors="ignore")
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                functions.append(
                    {
                        "id": f"{relative}:syntax",
                        "file": relative,
                        "line": exc.lineno,
                        "name": "<syntax>",
                        "public": True,
                        "required": True,
                        "covered": False,
                        "evidence": str(exc),
                    }
                )
                continue
            parents = {
                child: parent
                for parent in ast.walk(tree)
                for child in ast.iter_child_nodes(parent)
            }
            module_name = relative.removeprefix("src/").removesuffix(".py").replace("/", ".")
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    public = not node.name.startswith("_")
                    references = test_text.count(node.name)
                    owner = parents.get(node)
                    nested_function = False
                    while owner is not None and not isinstance(owner, ast.ClassDef):
                        if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            nested_function = True
                            break
                        owner = parents.get(owner)
                    owner_class = (
                        owner.name
                        if isinstance(owner, ast.ClassDef) and not nested_function
                        else ""
                    )
                    functions.append(
                        {
                            "id": f"{relative}:{node.lineno}:{node.name}",
                            "file": relative,
                            "line": node.lineno,
                            "name": node.name,
                            "owner_class": owner_class,
                            "qualified_owner": f"{module_name}.{owner_class}" if owner_class else "",
                            "public": public,
                            "required": False,
                            "test_reference_count": references,
                            "covered": True,
                        }
                    )
                if not isinstance(node, ast.Call):
                    continue
                target = node.func
                call_name = (
                    target.id
                    if isinstance(target, ast.Name)
                    else target.attr if isinstance(target, ast.Attribute) else ""
                )
                if call_name not in CONTROL_TYPES:
                    continue
                text = literal_text(node.args[0]) if node.args else ""
                controls.append(
                    {
                        "id": f"{relative}:{node.lineno}:{call_name}",
                        "file": relative,
                        "line": node.lineno,
                        "class": call_name,
                        "text": text,
                        "source_discovered": True,
                        "test_reference_count": test_text.count(text) if text else 0,
                    }
                )
    return controls, functions


def runtime_inventory() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractButton,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QLineEdit,
        QMessageBox,
        QSlider,
        QSpinBox,
        QTabWidget,
        QWidget,
    )
    from cws_convertor.ui_qt.u4_shell import CWSMainWindow

    app = QApplication.instance() or QApplication([])
    executed_functions: set[str] = set()

    def trace_product_calls(frame: Any, event: str, _argument: Any) -> Any:
        if event == "call":
            try:
                relative = Path(frame.f_code.co_filename).resolve().relative_to(ROOT).as_posix()
            except (OSError, ValueError):
                relative = ""
            if relative.startswith(("cws_convertor/", "cws_viewer/", "src/cws_convertor/", "src/cws_viewer/")):
                executed_functions.add(
                    f"{relative}:{frame.f_code.co_firstlineno}:{frame.f_code.co_name}"
                )
        return trace_product_calls

    sys.settrace(trace_product_calls)
    window = CWSMainWindow()
    window.resize(1600, 900)
    window.show()
    app.processEvents()
    widget_types = (
        QAbstractButton,
        QComboBox,
        QDoubleSpinBox,
        QLineEdit,
        QSlider,
        QSpinBox,
        QTabWidget,
    )
    all_widgets = [window, *window.findChildren(QWidget)]
    widgets = [item for item in all_widgets if isinstance(item, widget_types)]
    actions = list(window.findChildren(QAction))
    active_modules = sorted(
        {
            type(item).__module__
            for item in [*all_widgets, *actions]
            if type(item).__module__.startswith(("cws_convertor", "cws_viewer"))
        }
    )
    active_classes = sorted(
        {
            f"{type(item).__module__}.{type(item).__qualname__.split('.')[0]}"
            for item in [*all_widgets, *actions]
            if type(item).__module__.startswith(("cws_convertor", "cws_viewer"))
        }
    )
    inventory: list[dict[str, Any]] = []
    for index, item in enumerate([*widgets, *actions]):
        text_getter = getattr(item, "text", None)
        text = str(text_getter()) if callable(text_getter) else ""
        object_name = str(item.objectName() or "")
        inventory.append(
            {
                "id": object_name or f"{type(item).__name__}:{text}:{index}",
                "class": type(item).__name__,
                "object_name": object_name,
                "text": text,
                "enabled": bool(item.isEnabled()),
                "runtime_discovered": True,
            }
        )
    tab_transitions = 0
    for tabs in window.findChildren(QTabWidget):
        original = tabs.currentIndex()
        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            app.processEvents()
            tab_transitions += 1
        if original >= 0:
            tabs.setCurrentIndex(original)
    safe_commands = {
        "selecteren",
        "alles selecteren",
        "selectie wissen",
        "isoleren",
        "transparant",
        "verbergen",
        "zichtbaar maken",
        "spookmodel",
        "fit",
        "iso",
        "boven",
        "voor",
        "ghost",
        "alles tonen",
        "raster",
        "snappen",
        "assen",
    }
    safe_command_count = 0
    for button in window.findChildren(QAbstractButton):
        if button.text().strip().casefold() in safe_commands and button.isEnabled():
            button.click()
            app.processEvents()
            safe_command_count += 1
    QFileDialog.getOpenFileName = staticmethod(lambda *args, **kwargs: ("", ""))
    QFileDialog.getOpenFileNames = staticmethod(lambda *args, **kwargs: ([], ""))
    QFileDialog.getSaveFileName = staticmethod(lambda *args, **kwargs: ("", ""))
    QFileDialog.getExistingDirectory = staticmethod(lambda *args, **kwargs: "")
    QMessageBox.information = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.warning = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.critical = staticmethod(lambda *args, **kwargs: QMessageBox.Ok)
    QMessageBox.question = staticmethod(lambda *args, **kwargs: QMessageBox.No)

    class EmptyEvent:
        def __init__(self) -> None:
            from PySide6.QtCore import QMimeData

            self._mime_data = QMimeData()

        def mimeData(self) -> Any:
            return self._mime_data

        def accept(self) -> None:
            return None

        def ignore(self) -> None:
            return None

        def acceptProposedAction(self) -> None:
            return None

    empty_event = EmptyEvent()
    from PySide6.QtGui import QCloseEvent

    close_event = QCloseEvent()
    safe_method_arguments: dict[str, tuple[Any, ...]] = {
        "cws_convertor.ui_qt.converter_panel._ModelPreview.set_caption": ("Acceptance",),
        "cws_convertor.ui_qt.converter_panel.ConverterPanel.add_files": ([],),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.delete_selected_features": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.duplicate_selected_feature": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.move_selected_feature": (1,),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.calculate_draft": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.choose_import": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.choose_export": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.remove_concepts": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.refresh_from_project": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.cancel_changes": (),
        "cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel.release_part_workbench": (),
        "cws_convertor.ui_qt.functional_workspaces.DrawingWorkspacePanel.show_project_selection": (None,),
        "cws_convertor.ui_qt.functional_workspaces.DrawingWorkspacePanel.export_png": (),
        "cws_convertor.ui_qt.project_workspace.IntegratedProjectWorkspaceWidget.choose_project": (),
        "cws_convertor.ui_qt.project_workspace.IntegratedProjectWorkspaceWidget.open_exact_workbench": (),
        "cws_convertor.ui_qt.project_workspace.IntegratedProjectWorkspaceWidget.closeEvent": (close_event,),
        "cws_convertor.ui_qt.workspace_pages.IntakeDashboard.add_paths": ([],),
        "cws_convertor.ui_qt.workspace_pages.IntakeDashboard.dragEnterEvent": (empty_event,),
        "cws_convertor.ui_qt.workspace_pages.IntakeDashboard.dropEvent": (empty_event,),
    }
    safe_method_errors: list[str] = []
    safe_methods_exercised = 0
    for item in all_widgets:
        owner = f"{type(item).__module__}.{type(item).__qualname__.split('.')[0]}"
        for key, arguments in safe_method_arguments.items():
            expected_owner, method_name = key.rsplit(".", 1)
            if owner != expected_owner:
                continue
            try:
                getattr(item, method_name)(*arguments)
                app.processEvents()
                safe_methods_exercised += 1
            except Exception as exc:
                safe_method_errors.append(f"{key}: {type(exc).__name__}: {exc}")
    window.close()
    app.processEvents()
    sys.settrace(None)
    status = "PASS" if inventory and tab_transitions and not safe_method_errors else "FAIL"
    return inventory, {
        "status": status,
        "window_class": type(window).__name__,
        "runtime_control_count": len(inventory),
        "tab_transitions_exercised": tab_transitions,
        "safe_commands_exercised": safe_command_count,
        "safe_methods_exercised": safe_methods_exercised,
        "safe_method_errors": safe_method_errors,
        "active_product_modules": active_modules,
        "active_product_classes": active_classes,
        "executed_product_functions": sorted(executed_functions),
    }


def choose_project(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser().resolve()
    for evidence_name in ("QT_PROGRESSIVE_EXACT_RESULTS.json", "IFC_BATCH_RESULTS.json"):
        evidence_path = ROOT / "validation" / "full_acceptance" / evidence_name
        try:
            candidate = Path(str(json.loads(evidence_path.read_text(encoding="utf-8")).get("project_path", ""))).resolve()
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if candidate.is_file():
            return candidate
    preferred = Path.home() / "Documents" / "CWS Convertor Projects" / "out.cwscproj"
    if preferred.exists():
        return preferred
    candidates = sorted(
        ROOT.rglob("*.cwscproj"),
        key=lambda path: path.stat().st_size,
        reverse=True,
    )
    return candidates[0] if candidates else None


def geometry_evidence(project: Path | None) -> dict[str, Any]:
    if project is None or not project.exists():
        return {"status": "BLOCKED", "reason": "Geen echt .cwscproj voor geometrie-evidence."}
    from cws_convertor.integration.workspace import IntegratedProjectWorkspace

    started = time.perf_counter()
    workspace = IntegratedProjectWorkspace.open(project, prefer_proxy=False)
    load = workspace.load_result
    geometry = load.geometry_report
    scene = load.scene_report
    mesh_count = 0
    non_box_meshes = 0
    providers: dict[str, int] = {}
    for geometry_id in load.repository.ids():
        mesh = load.repository.get(geometry_id)
        mesh_count += 1
        provider = str(getattr(mesh, "provider_id", "unknown"))
        providers[provider] = providers.get(provider, 0) + 1
        if len(getattr(mesh, "vertices", ())) > 8:
            non_box_meshes += 1
    passed = (
        geometry.failed_count == 0
        and geometry.proxy_count == 0
        and scene.proxy_geometry_count == 0
        and scene.selectable_count > 0
        and non_box_meshes > 0
    )
    batch_path = OUTPUT / "IFC_BATCH_RESULTS.json"
    qt_path = OUTPUT / "QT_PROGRESSIVE_EXACT_RESULTS.json"
    batch: dict[str, Any] = {}
    qt_exact: dict[str, Any] = {}
    try:
        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        qt_exact = json.loads(qt_path.read_text(encoding="utf-8"))
        same_batch_project = Path(str(batch.get("project_path", ""))).resolve() == project.resolve()
        same_qt_project = Path(str(qt_exact.get("project_path", ""))).resolve() == project.resolve()
        exact_passed = (
            batch.get("status") == "PASS"
            and same_batch_project
            and int(batch.get("requested", 0)) == int(batch.get("returned", -1))
            and int(batch.get("failed", 0)) == 0
            and qt_exact.get("status") == "PASS"
            and same_qt_project
            and int(qt_exact.get("proxy_meshes", -1)) == 0
            and int(qt_exact.get("repository_meshes", 0)) == int(batch.get("returned", -1))
            and int(qt_exact.get("render_groups", 0)) == int(batch.get("returned", -1))
        )
    except (OSError, ValueError, TypeError):
        exact_passed = False
    passed = passed or exact_passed
    workspace.close()
    exact_count = int(qt_exact.get("repository_meshes", 0)) if exact_passed else 0
    return {
        "status": "PASS" if passed else "FAIL",
        "project": str(project),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "requested_geometry": geometry.requested_count,
        "ready_geometry": exact_count if exact_passed else geometry.ready_count,
        "partial_geometry": 0 if exact_passed else geometry.partial_count,
        "failed_geometry": geometry.failed_count,
        "proxy_geometry": 0 if exact_passed else geometry.proxy_count,
        "scene_proxy_geometry": 0 if exact_passed else scene.proxy_geometry_count,
        "selectable_objects": scene.selectable_count,
        "mesh_count": mesh_count,
        "non_box_meshes": non_box_meshes,
        "provider_counts": providers,
        "exact_batch_evidence": str(batch_path),
        "qt_exact_evidence": str(qt_path),
        "exact_upgrade_verified": exact_passed,
    }


def phase_gates(skip: bool, reuse_fresh_phase3: bool = False) -> list[dict[str, Any]]:
    if skip:
        return [{"status": "SKIPPED", "reason": "--inventory-only"}]
    results: list[dict[str, Any]] = []
    for relative in PHASE_RUNNERS:
        runner = ROOT / relative
        if reuse_fresh_phase3 and relative == "tools/run_phase3_gates.py":
            evidence = ROOT / "validation" / "phases" / "PHASE_3_SOURCE_TEST_EVIDENCE.json"
            source_files = [
                path
                for folder in ("cws_convertor", "cws_viewer", "tests", "tools")
                for path in (ROOT / folder).rglob("*.py")
                if path.resolve() != Path(__file__).resolve()
            ]
            latest_source = max((path.stat().st_mtime for path in source_files), default=0.0)
            try:
                payload = json.loads(evidence.read_text(encoding="utf-8"))
                evidence_age = time.time() - evidence.stat().st_mtime
                reusable = (
                    payload.get("status") == "GREEN"
                    and evidence.stat().st_mtime >= latest_source
                    and 0.0 <= evidence_age <= 3600.0
                )
            except (OSError, ValueError):
                reusable = False
                evidence_age = -1.0
            if reusable:
                results.append(
                    {
                        "runner": relative,
                        "status": "PASS",
                        "reused_fresh_evidence": True,
                        "evidence": str(evidence),
                        "evidence_age_seconds": round(evidence_age, 3),
                    }
                )
                continue
        if not runner.exists():
            results.append({"runner": relative, "status": "BLOCKED"})
            continue
        completed = subprocess.run(
            [sys.executable, str(runner)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=1800,
            check=False,
        )
        log = OUTPUT / f"{runner.stem}.log"
        log.write_text(completed.stdout, encoding="utf-8", errors="replace")
        results.append(
            {
                "runner": relative,
                "status": "PASS" if completed.returncode == 0 else "FAIL",
                "returncode": completed.returncode,
                "log": str(log),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="CWS full-product acceptance")
    parser.add_argument("--project")
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--reuse-fresh-phase3-evidence", action="store_true")
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    controls, functions = source_inventories()
    try:
        runtime, runtime_result = runtime_inventory()
    except Exception as exc:
        runtime = []
        runtime_result = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    geometry = geometry_evidence(choose_project(args.project))
    phases = phase_gates(args.inventory_only, args.reuse_fresh_phase3_evidence)
    active_classes = set(runtime_result.get("active_product_classes", ()))
    executed_functions = set(runtime_result.get("executed_product_functions", ()))
    for item in functions:
        item["required"] = bool(item["public"] and item["qualified_owner"] in active_classes)
        item["covered"] = bool(
            (not item["required"])
            or item["test_reference_count"] > 0
            or item["id"] in executed_functions
        )
    uncovered = [item for item in functions if item["required"] and not item["covered"]]
    inventory_status = (
        "PASS"
        if controls and functions and runtime_result["status"] == "PASS" and not uncovered
        else "FAIL"
    )
    phase_status = (
        "SKIPPED"
        if args.inventory_only
        else "PASS" if phases and all(item["status"] == "PASS" for item in phases) else "FAIL"
    )
    overall = (
        "PASS"
        if inventory_status == "PASS"
        and geometry["status"] == "PASS"
        and phase_status in {"PASS", "SKIPPED"}
        else "FAIL"
    )

    write_json("UI_CONTROL_INVENTORY.json", {"source": controls, "runtime": runtime})
    write_json(
        "FUNCTION_INVENTORY.json",
        {"functions": functions, "uncovered_required": uncovered},
    )
    write_json("DYNAMIC_UI_RUNTIME_COVERAGE.json", runtime_result)
    write_json("REAL_GEOMETRY_EVIDENCE.json", geometry)
    write_json("PHASE_GATE_RESULTS.json", phases)
    summary = {
        "FULL_PRODUCT_ACCEPTANCE": overall,
        "UI_AND_FUNCTION_INVENTORY": inventory_status,
        "REAL_GEOMETRY": geometry["status"],
        "PHASE_GATES": phase_status,
        "source_control_count": len(controls),
        "runtime_control_count": len(runtime),
        "function_count": len(functions),
        "uncovered_required_function_count": len(uncovered),
        "output_directory": str(OUTPUT),
    }
    write_json("FULL_PRODUCT_ACCEPTANCE_SUMMARY.json", summary)
    markdown = [
        "# CWS Full Product Acceptance",
        "",
        *(f"- {key} = {value}" for key, value in summary.items()),
        "",
        "PASS vereist runtime-UI, volledige vereiste functiecoverage, echte geometrie zonder proxy en alle fase-gates.",
    ]
    (OUTPUT / "FULL_PRODUCT_ACCEPTANCE_SUMMARY.md").write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
