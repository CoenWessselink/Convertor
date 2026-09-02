from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_full_product_acceptance import exact_upgrade_verified


class FullAcceptanceGeometryEvidenceTests(unittest.TestCase):
    def test_exact_meshes_may_share_a_render_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws-exact-evidence-") as directory:
            project = Path(directory) / "large.cwscproj"
            batch = {
                "status": "PASS",
                "project_path": str(project),
                "requested": 9,
                "returned": 9,
                "failed": 0,
            }
            qt_exact = {
                "status": "PASS",
                "project_path": str(project),
                "finished": True,
                "proxy_meshes": 0,
                "repository_meshes": 9,
                "exact_meshes": 9,
                "render_groups": 1,
            }

            self.assertTrue(exact_upgrade_verified(project, batch, qt_exact))

            for key, invalid in (
                ("proxy_meshes", 1),
                ("exact_meshes", 8),
                ("render_groups", 0),
                ("render_groups", 10),
            ):
                with self.subTest(key=key, invalid=invalid):
                    candidate = {**qt_exact, key: invalid}
                    self.assertFalse(exact_upgrade_verified(project, batch, candidate))


if __name__ == "__main__":
    unittest.main(verbosity=2)
