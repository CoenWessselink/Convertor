from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession


STEP_WITHOUT_MATERIAL = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('unknown-material.step','2026-09-07T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P-001','Unknown material extrusion','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class AutomaticClassificationTests(unittest.TestCase):
    def test_semantic_import_never_leaves_new_parts_unclassified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_auto_classification_") as folder:
            source = Path(folder) / "unknown-material.step"
            source.write_text(STEP_WITHOUT_MATERIAL, encoding="utf-8")
            session = ProjectSession.new("Automatic classification")
            registration = session.register_sources([source], include_step_geometry=False)[0]

            result = session.semantic_import_source(registration.source.source_id)
            part = next(iter(session.project.parts.values()))

            self.assertEqual(part.classification_status, "review_required")
            self.assertNotEqual(part.classification_status, "unclassified")
            self.assertTrue(part.blocking_issues())
            summary = result.evidence["automatic_classification"]
            self.assertEqual(summary["classified_part_count"], 1)
            self.assertEqual(summary["review_required_count"], 1)
            self.assertIn(
                "automatic_classification",
                session.project.sources[registration.source.source_id].metadata,
            )
            self.assertEqual(
                session.project.sources[registration.source.source_id].analysis["semantic_import"]["evidence"]["automatic_classification"],
                summary,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
