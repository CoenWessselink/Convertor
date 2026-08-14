from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataclasses import replace
import tempfile
import unittest

from cws_viewer.properties import (
    GridLayout,
    GridLayoutIdentity,
    GridLayoutStore,
    GridScope,
    GridSort,
    ProjectGridModel,
)
from types import SimpleNamespace


class ViewerV8LayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        project = SimpleNamespace(parts={}, assemblies={}, purchased_items={}, fasteners={}, welds={}, project_phase="")
        self.model = ProjectGridModel(project)
        self.store = GridLayoutStore(Path(self.temp.name))
        self.identity = GridLayoutIdentity("CWS", "tester", "project-1", "Productie")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_atomic_tenant_layout_roundtrip(self) -> None:
        columns = tuple(
            replace(column, visible=(column.key in {"status", "part_position", "material", "total_mass_kg"}), order=index)
            for index, column in enumerate(reversed(self.model.columns))
        )
        layout = GridLayout(
            name="Productie",
            columns=columns,
            sorts=(GridSort("material"), GridSort("part_position", True)),
            scope=GridScope.BLOCKED,
            row_height=28,
        )
        stored = self.store.save(self.identity, layout)
        self.assertTrue(stored.path.is_file())
        self.assertTrue(stored.path.with_suffix(stored.path.suffix + ".sha256").is_file())
        loaded = self.store.load(self.identity)
        self.assertEqual(layout.to_dict(), loaded.layout.to_dict())
        self.assertEqual((self.identity,), self.store.list_layouts(company_id="CWS", user_id="tester", project_id="project-1"))

    def test_tamper_is_rejected(self) -> None:
        stored = self.store.save(self.identity, self.model.layout("Productie"))
        text = stored.path.read_text(encoding="utf-8")
        stored.path.write_text(text.replace("Productie", "Gemuteerd", 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.store.load(self.identity)

    def test_path_components_are_sanitized(self) -> None:
        identity = GridLayoutIdentity("../company", "user/../../", "project", "AUX")
        stored = self.store.save(identity, self.model.layout("AUX"))
        self.assertTrue(str(stored.path).startswith(str(Path(self.temp.name).resolve())))
        self.assertEqual("_AUX.cwsgrid.json", stored.path.name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
