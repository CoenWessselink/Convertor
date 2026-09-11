"""Qt orchestration for the existing BOM Batch-PDF action and central JobManager."""
from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from cws_convertor.drawings.batch import (
    prepare_drawing_batch, publish_drawing_batch, stage_drawing_batch, _revision,
)


def prepare_batch_action(panel: Any, ids: tuple[str, ...], preflight: Any):
    from PySide6 import QtWidgets
    from .bom_action_dispatch import _Outcome

    if getattr(panel, "_drawing_batch_job", ""):
        raise ValueError("Er loopt al een tekenbatch; voltooi of annuleer die eerst")
    if not ids or any(key not in panel._workspace.project.parts and key not in panel._workspace.project.assemblies for key in ids):
        raise ValueError("Selecteer bestaande onderdelen of assemblies voor de tekenbatch")
    if getattr(panel.window, "job_manager", None) is None:
        raise ValueError("De centrale JobManager ontbreekt; tekenbatch niet gestart")
    workspace = panel._workspace
    source_revision = _revision(workspace.project)
    configured = str(workspace.project.settings.get("drawing_output_directory") or "")
    folder = QtWidgets.QFileDialog.getExistingDirectory(panel, "Uitvoermap voor geselecteerde tekenbatch", configured)
    if not folder:
        return _Outcome("cancelled", "Tekenbatch geannuleerd; geen bestanden gemaakt")
    if panel._workspace is not workspace or panel.window.application_context.workspace is not workspace:
        raise ValueError("Project gewijzigd tijdens mapkeuze; tekenbatch niet gestart")
    if _revision(workspace.project) != source_revision:
        raise ValueError("Project of maatvoering gewijzigd tijdens mapkeuze; bevestig de batch opnieuw")
    defaults = dict(getattr(panel.window.pdf_page, "_default_sheet_settings", {}))
    return _Outcome(
        "prepared", f"Reviewbatch voorbereid voor {len(ids)} objecten; nog geen bestanden of nieuwe vrijgave",
        start=lambda: _start_batch(panel, ids, preflight, Path(folder), defaults, workspace, source_revision),
    )


def _start_batch(panel: Any, ids: tuple[str, ...], preflight: Any, folder: Path, defaults: dict,
                 expected_workspace: Any, expected_revision: str) -> None:
    from PySide6 import QtCore, QtWidgets
    from cws_convertor.output import DocumentOutputService

    workspace, state = panel._workspace, panel._hub_state
    manager = panel.window.job_manager
    if workspace is not expected_workspace or panel.window.application_context.workspace is not workspace:
        raise ValueError("Project gewijzigd vóór batchstart; geen publicatie")
    if _revision(workspace.project) != expected_revision:
        raise ValueError("Project of maatvoering gewijzigd vóór batchstart")
    if workspace.bom_snapshot.snapshot_sha256 != preflight.snapshot_sha256:
        raise ValueError("BOM gewijzigd sinds de controle; tekenbatch opnieuw voorbereiden")
    if getattr(panel, "_drawing_batch_job", ""):
        raise ValueError("Er loopt al een tekenbatch")
    if state is None:
        raise ValueError("BOM-resultaatregistratie ontbreekt")
    holder: dict[str, Any] = {}
    dialog = QtWidgets.QProgressDialog("Tekenbatch voorbereiden", "Annuleren", 0, 100, panel)
    dialog.setWindowTitle("CWS geselecteerde tekenbatch")
    dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
    dialog.setMinimumDuration(0)
    dialog.setAutoClose(False)
    dialog.setAutoReset(False)
    panel._drawing_batch_job = "preparing"
    panel._drawing_batch_dialog = dialog

    def finish_result(status: str, message: str, payload: dict | None = None) -> None:
        outputs = tuple(str(payload[key]) for key in ("pdf", "manifest")) if payload else ()
        state.record_result("drawing.batch_pdf", preflight, status=status, messages=(message,), outputs=outputs)
        workspace.session.dirty = True
        if panel._workspace is workspace:
            panel._last_drawing_batch = {"status": status, "message": message, **(payload or {})}
            panel.status.setText(message)

    try:
        snapshot = prepare_drawing_batch(workspace, ids, defaults)
        def work(context):
            result = stage_drawing_batch(context, snapshot, folder)
            holder["staged"] = result
            return {"staging": str(result.staging)}
        job_id = manager.submit(
            "bom-drawing-batch", work, project_id=workspace.project.project_id,
            scope={"entity_ids": list(ids), "source_revision": snapshot.project_revision},
            description="Geselecteerde objecttekeningen via bestaande tekenengine",
            timeout=180, resource_budget={"workers": 1, "max_entities": 250},
        )
        panel._drawing_batch_job = job_id
        panel._last_drawing_batch = {"status": "running", "entity_ids": list(ids)}
        dialog.canceled.connect(lambda: manager.cancel(job_id))
        timer = QtCore.QTimer(panel)
        timer.setInterval(100)

        def poll():
            record = manager.get(job_id)
            current = panel._workspace is workspace and getattr(panel.window.application_context, "workspace", None) is workspace
            if not current or dialog.wasCanceled():
                manager.cancel(job_id)
            if record.status in {"queued", "running"}:
                dialog.setLabelText(record.message)
                dialog.setValue(min(99, int(record.progress * 100)))
                return
            timer.stop()
            try:
                result = holder.get("staged")
                if record.status != "completed" or not current or dialog.wasCanceled() or not manager.is_current_generation(job_id):
                    raise ValueError(record.error or "Tekenbatch geannuleerd/verouderd; geen publicatie")
                if result is None:
                    raise ValueError("Tekenbatch heeft geen compleet resultaat")
                payload = publish_drawing_batch(result, snapshot, workspace)
                panel._drawing_batch_job = ""
                finish_result("passed", f"Reviewbatch gemaakt: {len(ids)} objecten, {payload['page_count']} bladen; geen nieuwe vrijgave", payload)
                # Register only paths that survived verification and publication,
                # never private worker paths or another project's results.
                try:
                    DocumentOutputService.shared().register(
                        payload["pdf"], kind="drawing_review_batch", producer="EngineeringDrawingGenerator",
                        entity_ids=ids,
                    )
                except Exception as registration_error:
                    # Publication has completed atomically. A recent-output UI
                    # failure cannot retroactively turn real files into "blocked".
                    panel.status.setText(
                        f"Reviewbatch gemaakt; opnemen in uitvoerhistorie mislukt: {registration_error}"
                    )
            except Exception as exc:
                result = holder.get("staged")
                if result is not None:
                    shutil.rmtree(result.staging, ignore_errors=True)
                finish_result("blocked", str(exc))
            finally:
                panel._drawing_batch_job = ""
                dialog.close()
                dialog.deleteLater()
                timer.deleteLater()
        timer.timeout.connect(poll)
        timer.start()
    except Exception as exc:
        panel._drawing_batch_job = ""
        dialog.close()
        dialog.deleteLater()
        finish_result("blocked", str(exc))
        raise
