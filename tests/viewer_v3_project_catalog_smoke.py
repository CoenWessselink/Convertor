from __future__ import annotations

from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.storage import ProjectStore
from cws_viewer.adapters.source_geometry import ProjectGeometryCatalog, ProjectSourceResolver

DEFAULT_PROJECT = Path(
    "/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL/"
    "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
)
PROJECT_PATH = Path(os.environ.get("CWS_V3_REFERENCE_PROJECT", DEFAULT_PROJECT))


@unittest.skipUnless(PROJECT_PATH.is_file(), f"V3 referentieproject ontbreekt: {PROJECT_PATH}")
class ViewerV3ProjectCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project_path = PROJECT_PATH
        cls.project = ProjectStore().open(cls.project_path, read_only=True).project
        cls.resolver = ProjectSourceResolver(
            cls.project,
            project_package_path=cls.project_path,
            search_roots=(Path("/mnt/data"),),
        )
        cls.catalog = ProjectGeometryCatalog().build(cls.project, cls.resolver)

    def test_reference_counts_and_sources(self) -> None:
        report = self.catalog.report
        self.assertIsNotNone(report)
        self.assertEqual(5809, report.entity_count)
        self.assertEqual(673, report.unique_geometry_count)
        self.assertEqual(5806, report.ifc_entity_count)
        self.assertEqual(3, report.step_entity_count)
        self.assertEqual(4, report.source_count)
        self.assertEqual(0, report.missing_identity_count)
        self.assertEqual(0, report.proxy_geometry_count)
        self.assertEqual(4, len(self.resolver.resolve_all()))

    def test_mlo4_lo4_share_one_verified_geometry(self) -> None:
        assemblies = [a for a in self.project.assemblies.values() if a.assembly_mark == "MLO4"]
        parts = [p for p in self.project.parts.values() if p.part_position == "LO4"]
        self.assertEqual(4, len(assemblies))
        self.assertEqual(4, len(parts))
        records = [self.catalog.records_by_entity[p.internal_id] for p in parts]
        self.assertEqual(1, len({record.geometry_id for record in records}))
        self.assertEqual({"154", "199", "29941", "29952"}, {item for r in records for item in r.source_item_ids})
        for part in parts:
            self.assertEqual("STRIP5*120", part.profile)
            self.assertEqual("S235JR", part.material)
            self.assertAlmostEqual(160.0, part.length_mm, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
