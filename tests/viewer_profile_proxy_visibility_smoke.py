from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.adapters.source_geometry import ProjectGeometryCatalog


class ProfileAwareProxyBoundsTests(unittest.TestCase):
    @staticmethod
    def _entity(profile: str, length: float, bbox: tuple[float, float, float]):
        return SimpleNamespace(
            profile=profile,
            normalized_profile=profile,
            length_mm=length,
            size_mm=0.0,
            diameter_mm=0.0,
            geometry_descriptor={"cad_metrics": {"bbox_mm": list(bbox)}},
        )

    def test_strip_profile_expands_line_proxy_cross_section(self) -> None:
        entity = self._entity("STRIP10*70", 180.0, (180.0, 1.0, 1.0))
        size = ProjectGeometryCatalog._fallback_bounds(entity).size
        self.assertEqual((180.0, 10.0, 70.0), size.to_tuple())

    def test_catalogue_profile_expands_line_proxy_cross_section(self) -> None:
        entity = self._entity("HEA400", 6000.0, (6000.0, 1.0, 1.0))
        size = ProjectGeometryCatalog._fallback_bounds(entity).size
        self.assertEqual(6000.0, size.x)
        self.assertGreater(size.y, 1.0)
        self.assertGreater(size.z, 1.0)

    def test_unknown_profile_preserves_existing_fallback(self) -> None:
        entity = self._entity("UNKNOWN", 180.0, (180.0, 1.0, 1.0))
        size = ProjectGeometryCatalog._fallback_bounds(entity).size
        self.assertEqual((180.0, 1.0, 1.0), size.to_tuple())


if __name__ == "__main__":
    unittest.main()
