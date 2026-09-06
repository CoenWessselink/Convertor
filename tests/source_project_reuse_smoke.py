from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.ui_qt.project_intake import find_reusable_project


class SourceProjectReuseTests(unittest.TestCase):
    def test_unchanged_embedded_source_reuses_newest_project(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "model.ifc"
            source.write_bytes(b"ISO-10303-21;\nEND-ISO-10303-21;\n")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            project = root / "model.cwscproj"
            manifest = {
                "embedded_sources": [
                    {"path": "sources/model.ifc", "sha256": digest, "size": source.stat().st_size}
                ]
            }
            with zipfile.ZipFile(project, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))

            self.assertEqual(find_reusable_project((source,), root), project.resolve())
            source.write_bytes(source.read_bytes() + b"changed")
            self.assertIsNone(find_reusable_project((source,), root))

    def test_nc_source_never_matches_step_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "part.nc1"
            source.write_text("ST\nEN", encoding="ascii")
            self.assertIsNone(find_reusable_project((source,), root))

    def test_exact_preview_and_converter_selection_are_wired_into_the_main_flow(self) -> None:
        main_source = (ROOT / "cws_convertor" / "ui_qt" / "main_window.py").read_text(
            encoding="utf-8"
        )
        workspace_source = (
            ROOT / "cws_convertor" / "ui_qt" / "project_workspace.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def open_source_preview", workspace_source)
        self.assertIn("self.project_page.open_source_preview(first)", main_source)
        self.assertIn("self.converter_page.set_project_selection(workspace, selection)", main_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
