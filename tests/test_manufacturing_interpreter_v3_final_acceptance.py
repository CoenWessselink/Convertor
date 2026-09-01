from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import cadquery as cq
from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from cws_convertor.manufacturing_interpreter import ManufacturingGeometryInterpreter, ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.cli import _step_inspection
from cws_convertor.manufacturing_interpreter.contracts import InterpretationConfirmation
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator
from cws_convertor.manufacturing_interpreter.recognition_cache import RecognitionCacheV3, stable_sha256
from cws_convertor.ui_qt.u4_shell import CWSMainWindow


EXPECTED_CONTROL_IDS = {
    "mgi.source.open",
    "mgi.analyze",
    "mgi.cancel",
    "mgi.retry",
    "mgi.evidence.save",
    "mgi.features.table",
    "mgi.promote",
}


def _report(root: Path):
    source = root / "flat.step"
    cq.exporters.export(cq.Workplane("XY").box(400, 120, 12, centered=(False, True, True)).val(), str(source))
    interpreter = ManufacturingGeometryInterpreter(cache_root=root / "cache")
    request = ManufacturingInterpretationRequest(inspection=_step_inspection(source), requested_outputs=("STEP",))
    report = interpreter.analyze(request)
    return interpreter, request, report


def test_final_cache_reuses_complete_immutable_report() -> None:
    with tempfile.TemporaryDirectory() as folder:
        interpreter, request, first = _report(Path(folder))
        second = interpreter.analyze(request)
        assert first is second
        assert interpreter.final_cache_hits == 1
        assert interpreter.final_cache_misses == 1


def test_cache_key_invalidates_every_bound_authority() -> None:
    base = dict(
        source_sha256="source-a",
        source_geometry_hash="geometry-a",
        engine_version="engine-a",
        algorithm_versions=(("proof", "a"),),
        tolerance_policy_hash="tolerance-a",
        profile_database_hash="profiles-a",
        preferred_profile="",
        requested_outputs=("STEP",),
    )
    baseline = RecognitionCacheV3.key(**base)
    for field, value in {
        "source_sha256": "source-b",
        "source_geometry_hash": "geometry-b",
        "engine_version": "engine-b",
        "algorithm_versions": (("proof", "b"),),
        "tolerance_policy_hash": "tolerance-b",
        "profile_database_hash": "profiles-b",
        "preferred_profile": "IPE200",
        "requested_outputs": ("IFC",),
    }.items():
        changed = dict(base)
        changed[field] = value
        assert RecognitionCacheV3.key(**changed) != baseline, field


def test_full_profile_candidates_are_stable_and_ranked() -> None:
    with tempfile.TemporaryDirectory() as folder:
        interpreter, request, first = _report(Path(folder))
        second = interpreter.analyze(request)
        assert first.profile_candidates
        assert first.profile_candidates == second.profile_candidates
        scores = [candidate.score for candidate in first.profile_candidates]
        assert scores == sorted(scores, reverse=True)


def test_stale_promotion_is_blocked_before_canonical_mutation() -> None:
    with tempfile.TemporaryDirectory() as folder:
        _, _, report = _report(Path(folder))
        hypothesis_id = report.hypotheses[0].hypothesis_id if report.hypotheses else "base"
        confirmation = InterpretationConfirmation(
            confirmation_id="confirm-stale",
            report_hash=stable_sha256(report),
            hypothesis_id=hypothesis_id,
            user="acceptance",
        )
        with patch("cws_convertor.project.workbench.update_part_workbench") as update:
            result = WorkbenchPromotionCoordinator().promote(
                report=report,
                confirmation=confirmation,
                project=object(),
                user="acceptance",
                current_source_geometry_hash="changed-source",
                current_tolerance_policy_hash=report.tolerance_policy_hash,
                current_profile_database_hash=report.profile_database_hash,
            )
        assert result.status == "BLOCKED"
        assert "STALE_REPORT:SOURCE_GEOMETRY_HASH_CHANGED" in result.blockers
        update.assert_not_called()


def test_failed_promotion_rolls_back_transaction() -> None:
    with tempfile.TemporaryDirectory() as folder:
        _, _, report = _report(Path(folder))
        if report.readiness.value != "READY":
            return
        hypothesis_id = report.hypotheses[0].hypothesis_id if report.hypotheses else "base"
        confirmation = InterpretationConfirmation(
            confirmation_id="confirm-rollback",
            report_hash=stable_sha256(report),
            hypothesis_id=hypothesis_id,
            user="acceptance",
        )
        with patch("cws_convertor.project.workbench.update_part_workbench", side_effect=RuntimeError("forced failure")), patch(
            "cws_convertor.project.workbench.undo_part_workbench", return_value={"revision_hash": "rollback"}
        ) as undo:
            result = WorkbenchPromotionCoordinator().promote(
                report=report,
                confirmation=confirmation,
                project=object(),
                user="acceptance",
                current_source_geometry_hash=report.source_geometry_hash,
                current_tolerance_policy_hash=report.tolerance_policy_hash,
                current_profile_database_hash=report.profile_database_hash,
            )
        assert result.status == "BLOCKED"
        assert "WORKBENCH_REJECTED:RuntimeError" in result.blockers
        assert result.rolled_back
        undo.assert_called_once()


def test_runtime_owned_control_contract() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    window = CWSMainWindow()
    try:
        found = [str(obj.property("ui_test_id")) for obj in window.findChildren(QObject) if obj.property("ui_test_id")]
        mgi = [value for value in found if value.startswith("mgi.")]
        assert set(mgi) == EXPECTED_CONTROL_IDS
        assert len(mgi) == len(set(mgi))
    finally:
        window.close()
        app.processEvents()


def test_45_category_acceptance_artifact_has_no_false_green() -> None:
    path = Path("validation/manufacturing_interpreter_v3/final_acceptance/corpus/CORPUS_MANIFEST.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["category_count"] == 45
    assert payload["summary"]["false_ready"] == 0
    assert payload["summary"]["false_green"] == 0
    assert payload["summary"]["errors"] == []


if __name__ == "__main__":
    test_final_cache_reuses_complete_immutable_report()
    test_cache_key_invalidates_every_bound_authority()
    test_full_profile_candidates_are_stable_and_ranked()
    test_stale_promotion_is_blocked_before_canonical_mutation()
    test_failed_promotion_rolls_back_transaction()
    test_runtime_owned_control_contract()
    test_45_category_acceptance_artifact_has_no_false_green()
    print("manufacturing interpreter V3 final acceptance tests: PASS")
