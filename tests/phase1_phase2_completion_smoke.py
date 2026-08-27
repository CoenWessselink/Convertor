from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.bom import build_bom_snapshot, export_bom_package
from cws_convertor.conversion_capabilities import DEFAULT_CAPABILITY_REGISTRY
from cws_convertor.integration.ui_context import (
    U3_CONTEXT_SCHEMA,
    UnifiedApplicationContext,
    migrate_context_payload,
)
from cws_convertor.project import Part, ProjectSession, SourceIdentity, Transform3D
from cws_convertor.project.canonical_rebuild import rebuild_and_compare
from cws_convertor.project.jobs import JobManager
from cws_viewer.core.performance_evidence import METRIC_FIELDS, ViewerPerformanceEvidence


def _line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


class Phase1Phase2CompletionTests(unittest.TestCase):
    def test_full_context_serializes_and_migrates_without_project_mutation(self) -> None:
        context = UnifiedApplicationContext(active_surface="viewer")
        try:
            context.update_viewer_context(
                camera_state={"position": [1.0, 2.0, 3.0]},
                camera_target=(4.0, 5.0, 6.0),
                camera_projection="orthographic",
                camera_history=({"position": [0.0, 0.0, 1.0]},),
                visibility_state={"part-1": "ghosted"},
                hidden_entities=("part-2",),
                ghosted_entities=("part-1",),
                isolated_scope=("assembly-1",),
                section_planes=({"id": "section-1", "offset": 12.5},),
                clipping_state={"enabled": True},
            )
            context.update_workspace_context(
                search_state={"query": "LO4"},
                active_filters=("plate", "blocked"),
                active_workspace="workbench",
                workspace_history=("viewer", "workbench"),
            )
            context.update_review_context(
                measurement_state={"m-1": {"entity_id": "part-1"}},
                markup_state={"issue-1": {"status": "open"}},
                saved_view_state={"view-1": {"camera": "iso"}},
                active_bom_row="part-1",
                active_scribing_mark="mark-1",
            )
            context.update_manufacturing_context(
                active_edit_transaction="tx-1", active_nesting_run="nest-1"
            )
            context.update_export_context(active_export_scope=("part-1", "assembly-1"))
            payload = context.serialize_state()
            restored = UnifiedApplicationContext()
            try:
                snapshot = restored.restore_state(json.loads(json.dumps(payload)))
                self.assertEqual(U3_CONTEXT_SCHEMA, payload["schema"])
                self.assertEqual((4.0, 5.0, 6.0), snapshot.viewer_context.camera_target)
                self.assertEqual("workbench", snapshot.workspace_context.active_workspace)
                self.assertEqual("tx-1", snapshot.manufacturing_context.active_edit_transaction)
                self.assertEqual(("part-1", "assembly-1"), snapshot.export_context.active_export_scope)
            finally:
                restored.close()
            migrated = migrate_context_payload(
                {"schema": "cws-unified-ui-context-1.0", "project_id": "p", "active_surface": "viewer"}
            )
            self.assertEqual(U3_CONTEXT_SCHEMA, migrated["schema"])
        finally:
            context.close()

    def test_job_generation_cancel_progress_error_namespace_and_retry(self) -> None:
        manager = JobManager(max_workers=2)
        release = threading.Event()

        def delayed(context):
            context.stage("geometry", 0.25, "LOD0")
            release.wait(2.0)
            return "old"

        def current(context):
            context.stage("geometry", 1.0, "Exact")
            return "new"

        try:
            old = manager.submit("geometry", delayed, project_id="p", generation=1)
            new = manager.submit("geometry", current, project_id="p", generation=2)
            self.assertEqual("new", manager.wait(new, 3.0))
            release.set()
            manager.wait(old, 3.0)
            self.assertEqual("stale_discarded", manager.get(old).status)
            self.assertIsNone(manager.get(old).result)

            def cancellable(context):
                while True:
                    context.check_cancelled()
                    time.sleep(0.005)

            cancelled = manager.submit("drawing", cancellable, project_id="p")
            time.sleep(0.02)
            self.assertTrue(manager.cancel(cancelled))
            manager.wait(cancelled, 3.0)
            self.assertEqual("CWS.JOB.CANCELLED", manager.get(cancelled).error_namespace)

            attempts = []

            def flaky(_context):
                attempts.append(1)
                if len(attempts) == 1:
                    raise RuntimeError("temporary")
                return "recovered"

            failed = manager.submit("reporting", flaky, max_retries=1)
            with self.assertRaises(RuntimeError):
                manager.wait(failed, 3.0)
            self.assertEqual("CWS.JOB.REPORTING.RUNTIMEERROR", manager.get(failed).error_namespace)
            retried = manager.retry(failed)
            self.assertEqual("recovered", manager.wait(retried, 3.0))
        finally:
            manager.shutdown(cancel_pending=True)

    def test_workbench_rebuild_supports_countersink_and_pocket_but_registry_blocks_unproved_roundtrip(self) -> None:
        session = ProjectSession.new("Phase 2 exact", created_by="test")
        part = Part(
            internal_id="part-1",
            name="Plaat",
            part_position="P1",
            source_identity=SourceIdentity(
                source_format="STEP", source_sha256="a" * 64, source_entity_id="#1", part_position="P1"
            ),
            profile="PL10",
            profile_confidence=1.0,
            confidence=1.0,
            geometry_descriptor={"kind": "plate", "bbox_mm": [300.0, 180.0, 10.0]},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="test")
        session.start_part_workbench("part-1", user="test")
        state = session.update_part_workbench(
            "part-1",
            {
                "part_form": "plate",
                "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 300.0, "thickness_mm": 10.0},
                "production_frame": Transform3D.identity().matrix,
                "reference_sides": [{"side_id": "top", "label": "Top", "face_ref": "face:top", "confirmed": True}],
                "contours": [{
                    "contour_id": "outer", "role": "outer", "closed": True,
                    "segments": [
                        _line((0, 0), (300, 0)), _line((300, 0), (300, 180)),
                        _line((300, 180), (0, 180)), _line((0, 180), (0, 0)),
                    ],
                }],
                "features": [
                    {"feature_id": "cs-1", "kind": "countersunk_hole", "reference_side": "top", "parameters": {"x_mm": 50, "y_mm": 50, "diameter_mm": 12, "countersink_diameter_mm": 22, "countersink_angle_deg": 90, "through": True}},
                    {"feature_id": "pocket-1", "kind": "pocket", "reference_side": "top", "parameters": {"x_mm": 120, "y_mm": 60, "width_mm": 70, "height_mm": 45, "depth_mm": 4}},
                ],
            },
            user="test",
            reason="Exact countersink en pocket",
        )
        self.assertEqual([], state["current_revision"]["validation_issues"])
        rebuilt = rebuild_and_compare(part)
        self.assertIsNotNone(rebuilt.shape, rebuilt.report)
        self.assertEqual("built", rebuilt.report["build_status"])
        self.assertNotEqual("blocked", rebuilt.report["status"])
        evaluated = DEFAULT_CAPABILITY_REGISTRY.evaluate(
            source_format="STEP", part_form="plate", features=("countersunk_hole", "pocket"), exact_source=True
        )
        self.assertTrue(evaluated)
        self.assertTrue(all(blockers for _capability, blockers in evaluated))
        self.assertIn("unsupported_feature:countersunk_hole", {item for _cap, blockers in evaluated for item in blockers})
        session.close()

    def test_bom_has_json_csv_xlsx_pdf_and_viewer_metrics_have_fixed_schema(self) -> None:
        session = ProjectSession.new("BOM", created_by="test")
        part = Part(internal_id="p", name="P", part_position="P1", profile="PL10", material="S355", length_mm=100)
        part.recompute_hashes()
        session.project.add_entity(part)
        snapshot = build_bom_snapshot(session.project, user="test")
        with tempfile.TemporaryDirectory(prefix="cws-phase12-") as folder:
            outputs = export_bom_package(snapshot, folder, package_name="Phase12")
            suffixes = {path.suffix.lower() for path in outputs.values()}
            self.assertTrue({".json", ".csv", ".xlsx", ".pdf", ".zip"}.issubset(suffixes))
        evidence = ViewerPerformanceEvidence()
        evidence.mark("shell_visible_ms")
        evidence.observe("frame", 16.0)
        evidence.observe("frame", 18.0)
        payload = evidence.to_dict()
        self.assertEqual(set(METRIC_FIELDS), set(payload["metrics"]))
        self.assertEqual("cws-viewer-performance-evidence-1.0", payload["schema"])
        session.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
