from __future__ import annotations

import inspect
from pathlib import Path
import unittest

from cws_viewer.adapters.project_scene_loader import ProjectSceneLoader


class ProxySourceAppearanceRegressionTests(unittest.TestCase):
    def test_proxy_first_scene_keeps_ifc_source_appearance_enabled(self) -> None:
        source = inspect.getsource(ProjectSceneLoader.load_project)
        self.assertIn("enrich_source_appearance=True", source)
        self.assertNotIn("enrich_source_appearance=not fast_proxy_catalog", source)

    def test_exact_upgrade_republishes_source_appearance_scene(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "cws_convertor"
            / "ui_qt"
            / "project_workspace.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"source_appearance_scene": source_appearance_scene', source)
        self.assertIn("catalog._documents[source_file_id] = P21Document.load", source)
        self.assertIn("self.viewer.load_scene(source_scene)", source)

    def test_empty_proxy_item_ids_are_recovered_from_ifc_entity(self) -> None:
        source = inspect.getsource(
            __import__(
                "cws_viewer.adapters.source_style_scene",
                fromlist=["SourceAppearanceProjectSceneAdapter"],
            ).SourceAppearanceProjectSceneAdapter.build_scene
        )
        self.assertIn("if not source_item_ids", source)
        self.assertIn("ProjectGeometryCatalog._ifc_items", source)


if __name__ == "__main__":
    unittest.main()
