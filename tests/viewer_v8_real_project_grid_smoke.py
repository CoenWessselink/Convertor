from __future__ import annotations

from pathlib import Path
import json
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.storage import ProjectStore
from cws_viewer.properties import (
    GridFilter,
    GridGroupSpec,
    GridQuery,
    GridScope,
    GridSort,
    FilterOperator,
    ProjectGridModel,
    export_grid_csv,
)

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)
DEFAULT_COMPARE = ROOT / "validation" / "viewer_v7" / "REAL_PROJECT_COMPARE_MANIFEST.json"


class ViewerV8RealProjectGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project_path = Path(os.environ.get("CWS_V8_REFERENCE_PROJECT", DEFAULT_PROJECT))
        if not project_path.is_file():
            raise unittest.SkipTest(f"V8 referentieproject ontbreekt: {project_path}")
        cls.project = ProjectStore().open(project_path, read_only=True).project
        compare = json.loads(DEFAULT_COMPARE.read_text(encoding="utf-8"))["report"] if DEFAULT_COMPARE.is_file() else None
        cls.model = ProjectGridModel(cls.project, revision_report=compare)

    def test_complete_entity_grid_and_lo4(self) -> None:
        counts = {}
        for row in self.model.rows:
            counts[row.entity_type] = counts.get(row.entity_type, 0) + 1
        self.assertEqual(353, counts.get("assembly"))
        self.assertEqual(2432, counts.get("part"))
        self.assertEqual(723, counts.get("fastener"))
        self.assertEqual(2654, counts.get("weld"))
        lo4 = self.model.execute(
            GridQuery(
                filters=(GridFilter("part_position", FilterOperator.EQ, "LO4"),),
                sorts=(GridSort("entity_id"),),
            )
        )
        self.assertEqual(4, lo4.row_count)
        self.assertTrue(all(row.get("profile") == "STRIP5*120" for row in lo4.iter_rows()))
        self.assertTrue(all(row.get("material") == "S235JR" for row in lo4.iter_rows()))

    def test_revision_scope_and_multilevel_grouping(self) -> None:
        changed = self.model.execute(
            GridQuery(
                scope=GridScope.CHANGED,
                groups=(GridGroupSpec("revision_status"), GridGroupSpec("revision_impacts")),
                sorts=(GridSort("revision_status"), GridSort("part_position")),
            )
        )
        self.assertGreaterEqual(changed.row_count, 5)
        statuses = {str(row.get("revision_status")) for row in changed.iter_rows()}
        self.assertTrue({"moved", "changed", "removed"} <= statuses)
        self.assertTrue(changed.groups)

    def test_selected_scope_export_contains_only_scope(self) -> None:
        lo4_ids = [row.entity_id for row in self.model.rows if row.get("part_position") == "LO4"]
        self.model.set_scope_state(selected_entity_ids=lo4_ids)
        selected = self.model.execute(GridQuery(scope=GridScope.SELECTED))
        self.assertEqual(4, selected.row_count)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lo4.csv"
            evidence = export_grid_csv(selected, path)
            self.assertEqual(4, evidence["rows"])
            text = path.read_text(encoding="utf-8-sig")
            self.assertEqual(4, sum(1 for line in text.splitlines()[1:] if line.strip()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
