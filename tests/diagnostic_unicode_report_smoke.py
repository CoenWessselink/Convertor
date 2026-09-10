"""Real redirected-stream regression for the frozen Windows diagnostic failure."""
from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from CWS_Convertor_App import _write_report


class DiagnosticUnicodeReportTests(unittest.TestCase):
    def payload(self):
        return {"status": "PASS", "visible_text": "● Voorbeeld Ø18 ±0,5 – café 📐", "count": 48}

    def capture(self, encoding, path=None):
        output = io.BytesIO()
        stream = io.TextIOWrapper(output, encoding=encoding, errors="strict", newline="\n")
        with contextlib.redirect_stdout(stream):
            _write_report(path, self.payload())
        stream.flush()
        text = output.getvalue().decode(encoding)
        self.assertEqual(json.loads(text), self.payload())
        self.assertTrue(text.isascii())
        return text

    def test_windows_cp1252_preserves_every_code_point(self):
        self.capture("cp1252")

    def test_ascii_stream_preserves_non_bmp_characters(self):
        text = self.capture("ascii")
        self.assertIn(r"\ud83d\udcd0", text)

    def test_utf8_stream_uses_same_lossless_json(self):
        self.capture("utf-8")

    def test_report_file_remains_human_readable_utf8(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subdir" / "evidence.json"
            console = self.capture("cp1252", path)
            text = path.read_bytes().decode("utf-8")
            self.assertIn("● Voorbeeld Ø18", text)
            self.assertEqual(json.loads(text), json.loads(console))
            self.assertTrue(text.endswith("\n"))

    def test_real_file_write_errors_are_not_hidden(self):
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                _write_report(Path(tempfile.gettempdir()) / "report.json", self.payload())


if __name__ == "__main__":
    unittest.main(verbosity=2)
