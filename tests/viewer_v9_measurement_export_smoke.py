from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.math3d import Vector3
from cws_viewer.measurements import (
    ExactMeasurementAnchor,
    MeasurementProof,
    SnapType,
    distance,
)
from cws_viewer.measurements.export import export_csv, export_json, export_pdf


class ViewerV9MeasurementExportTests(unittest.TestCase):
    @staticmethod
    def _record():
        first = ExactMeasurementAnchor(
            node_id="node:a",
            entity_id="part-a",
            world_point=Vector3(0, 0, 0),
            geometry_hash="a" * 64,
            snap_type=SnapType.CENTER,
            proof=MeasurementProof.VERIFIED_MESH,
        )
        second = ExactMeasurementAnchor(
            node_id="node:b",
            entity_id="part-b",
            world_point=Vector3(30, 40, 0),
            geometry_hash="b" * 64,
            snap_type=SnapType.CENTER,
            proof=MeasurementProof.DISPLAY_PROXY,
        )
        return distance(first, second)

    def _verify_sidecar(self, path: Path) -> None:
        sidecar = path.with_suffix(path.suffix + ".sha256")
        self.assertTrue(sidecar.is_file())
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            sidecar.read_text(encoding="ascii").strip(),
        )

    def test_json_csv_pdf_are_atomic_checksumed_review_artifacts(self) -> None:
        record = self._record()
        self.assertFalse(record.production_eligible)
        with tempfile.TemporaryDirectory(prefix="cws-v9-measure-export-") as temp:
            root = Path(temp)
            json_path = export_json((record,), root / "measurements.json")
            csv_path = export_csv((record,), root / "measurements.csv")
            pdf_path = export_pdf(
                (record,), root / "measurements.pdf", project_name="V9 integration"
            )
            for path in (json_path, csv_path, pdf_path):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 50)
                self._verify_sidecar(path)
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual("cws-viewer-measurements-1.1", payload["schema"])
            self.assertFalse(payload["production_release_allowed"])
            self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))
            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF"))
            try:
                import fitz
                with fitz.open(pdf_path) as document:
                    text = "\n".join(page.get_text() for page in document)
                self.assertIn("meetrapport", text.lower())
                self.assertIn("productievrijgave", text.lower())
            except ImportError:
                pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
