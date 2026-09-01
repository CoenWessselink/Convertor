from __future__ import annotations

import tempfile
import time
import json
from pathlib import Path
from types import SimpleNamespace

import cadquery as cq
from PySide6.QtWidgets import QApplication

from cws_convertor.manufacturing_interpreter import ManufacturingGeometryInterpreter, ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.report_store import ReportInvalidatedError, load_report_envelope, save_report
from cws_convertor.ui_qt.manufacturing_geometry_workspace import ManufacturingGeometryWorkspace
from cws_convertor.project.jobs import JobManager
from cws_convertor.manufacturing_interpreter.batch_cli import main as batch_cli_main


def _inspection(shape: object, name: str, exact: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        part_id=name,
        source_file_id=f"{name}.step",
        source_sha256=f"sha-{name}",
        source_geometry_hash=f"geometry-{name}",
        status="exact" if exact else "approximate",
        scope="single_part",
        geometry_kind="native_brep" if exact else "mesh",
        selection_verified=exact,
        production_geometry_exact=exact,
        native_shape=shape if exact else None,
    )


class ViewerProbe:
    def __init__(self) -> None:
        self.payload = None
        self.visible = False

    def set_manufacturing_overlay(self, payload) -> None:
        self.payload = payload

    def set_overlay_visible(self, visible: bool) -> None:
        self.visible = visible


def test_phase3_ui_viewerhost_and_report_persistence() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-phase3-") as root:
        shape = cq.Workplane("XY").box(180.0, 90.0, 16.0).faces(">Z").workplane().hole(24.0).val()
        interpreter = ManufacturingGeometryInterpreter(cache_root=Path(root) / "cache")
        source = Path(root) / "ui-part.step"
        cq.exporters.export(shape, str(source))
        viewer = ViewerProbe()
        workspace = ManufacturingGeometryWorkspace(viewer)
        workspace.interpreter = interpreter
        workspace.source_edit.setText(str(source))
        workspace.analyze_current_source()
        deadline = time.monotonic() + 20.0
        while workspace.current_report is None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.02)
        report = workspace.current_report
        assert report is not None
        assert workspace.current_report is report
        assert viewer.payload and viewer.visible
        assert workspace.tabs.count() == 5
        target = save_report(report, Path(root) / "report.json")
        loaded = load_report_envelope(
            target,
            source_sha256=report.source_sha256,
            source_geometry_hash=report.source_geometry_hash,
            tolerance_policy_hash=report.tolerance_policy_hash,
            profile_database_hash=report.profile_database_hash,
        )
        assert loaded["semantic_sha256"] == report.semantic_sha256
        try:
            load_report_envelope(
                target,
                source_sha256="changed",
                source_geometry_hash=report.source_geometry_hash,
                tolerance_policy_hash=report.tolerance_policy_hash,
                profile_database_hash=report.profile_database_hash,
            )
        except ReportInvalidatedError:
            pass
        else:
            raise AssertionError("Changed source hash must invalidate persisted report")
        workspace.close()


def test_phase3_jobmanager_cancel_retry_and_stale_generation() -> None:
    manager = JobManager(max_workers=2)

    def cancellable(context):
        for _ in range(200):
            context.check_cancelled()
            time.sleep(0.005)
        return "unexpected"

    cancelled_id = manager.submit("mgi-cancel", cancellable, max_retries=1)
    time.sleep(0.03)
    assert manager.cancel(cancelled_id)
    try:
        manager.wait(cancelled_id, 5.0)
    except Exception:
        pass
    assert manager.get(cancelled_id).status == "cancelled"

    attempts = {"count": 0}

    def retryable(context):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("synthetic native worker failure")
        return "recovered"

    failed_id = manager.submit("mgi-retry", retryable, max_retries=1)
    try:
        manager.wait(failed_id, 5.0)
    except RuntimeError:
        pass
    retried_id = manager.retry(failed_id)
    assert manager.wait(retried_id, 5.0) == "recovered"

    old_id = manager.submit("mgi-generation", lambda context: "old", generation=1)
    new_id = manager.submit("mgi-generation", lambda context: "new", generation=2)
    manager.wait(old_id, 5.0)
    manager.wait(new_id, 5.0)
    assert not manager.is_current_generation(old_id)
    assert manager.is_current_generation(new_id)
    manager.shutdown(wait=True, cancel_pending=True)


def test_phase3_cli_project_batch_and_benchmark() -> None:
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-batch-") as root:
        root_path = Path(root)
        sources = []
        for index in range(2):
            source = root_path / f"part-{index}.step"
            cq.exporters.export(cq.Workplane("XY").box(100 + index * 10, 50, 10).val(), str(source))
            sources.append(source)
        project = root_path / "batch.cwscproj"
        project.write_text(
            json.dumps({"parts": [{"part_id": f"P{index}", "source_path": source.name} for index, source in enumerate(sources)]}),
            encoding="utf-8",
        )
        aggregate = root_path / "batch-report.json"
        exit_code = batch_cli_main(
            [
                "--project", str(project),
                "--all",
                "--output", str(root_path / "out"),
                "--json-report", str(aggregate),
                "--benchmark",
            ]
        )
        assert exit_code == 0
        payload = json.loads(aggregate.read_text(encoding="utf-8"))
        assert payload["schema"] == "cws-manufacturing-interpreter-cli-v3"
        assert payload["summary"] == {"inputs": 2, "failures": 0}
        assert aggregate.with_suffix(".benchmark.json").is_file()


if __name__ == "__main__":
    test_phase3_ui_viewerhost_and_report_persistence()
    test_phase3_jobmanager_cancel_retry_and_stale_generation()
    test_phase3_cli_project_batch_and_benchmark()
    print("PASS: MGI V3 phase 3 UI, ViewerHost and persistence")
