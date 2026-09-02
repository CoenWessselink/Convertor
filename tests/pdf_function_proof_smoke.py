from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_pdf_function_proof import REQUIREMENTS, validate_matrix


class PDFFunctionProofContractTests(unittest.TestCase):
    def test_matrix_requires_all_43_pass_items_with_hashed_visual_evidence(self) -> None:
        self.assertEqual([item[0] for item in REQUIREMENTS], [f"PDF-{index:02d}" for index in range(1, 44)])
        with tempfile.TemporaryDirectory(prefix="cws_pdf_proof_contract_") as folder_name:
            root = Path(folder_name)
            pdf = root / "actual.pdf"
            image = root / "actual.png"
            output = canvas.Canvas(str(pdf))
            output.drawString(72, 720, "CWS actual generated PDF proof")
            output.line(72, 700, 400, 700)
            output.save()
            Image.new("RGB", (800, 500), "white").save(image)
            pdf_hash = sha256(pdf.read_bytes()).hexdigest()
            image_hash = sha256(image.read_bytes()).hexdigest()
            items = [
                {
                    "requirement_id": requirement_id,
                    "status": "PASS",
                    "generated_pdf": pdf.name,
                    "rendered_image": image.name,
                    "ui_screenshot": image.name,
                    "output_sha256": pdf_hash,
                    "evidence_sha256": image_hash,
                }
                for requirement_id, _title, _category in REQUIREMENTS
            ]
            validate_matrix(items, root)
            items[-1]["requirement_id"] = "PDF-42"
            with self.assertRaises(RuntimeError):
                validate_matrix(items, root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
