from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import build_phase2_windows_release as phase2
import build_phase3_windows_release as phase3
import finalize_commit_bound_release as finalizer


class ReleaseTrackedSourceIntegritySmokeTests(unittest.TestCase):
    def _repository(self, root: Path) -> str:
        (root / "cws_convertor").mkdir()
        (root / "tests").mkdir()
        (root / "validation").mkdir()
        (root / "cws_convertor" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "tests" / "contract_smoke.py").write_text("PASS = True\n", encoding="utf-8")
        (root / "validation" / "contract.json").write_text("{}\n", encoding="utf-8")
        (root / "README.md").write_text("# fixture\n", encoding="utf-8")
        (root / "asset.bin").write_bytes(b"tracked but not source-packaged")
        subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "CWS CI"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "ci@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True)
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

    def test_phase2_allows_generated_untracked_evidence_but_rejects_tracked_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            revision = self._repository(root)
            (root / "validation" / "generated-evidence.json").write_text("{}\n", encoding="utf-8")
            with patch.object(phase2, "ROOT", root), patch.dict(os.environ, {"GITHUB_SHA": revision}):
                self.assertEqual(revision, phase2._clean_revision())
                (root / "cws_convertor" / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "cws_convertor/module.py"):
                    phase2._clean_revision()

    def test_final_binding_cleanliness_is_about_the_tracked_source_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._repository(root)
            (root / "generated-release.zip").write_bytes(b"artifact")
            with patch.object(finalizer, "ROOT", root):
                self.assertTrue(finalizer.clean_tree())
                (root / "README.md").write_text("changed\n", encoding="utf-8")
                self.assertFalse(finalizer.clean_tree())

    def test_phase3_source_package_enumerates_only_tracked_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._repository(root)
            (root / "cws_convertor" / "generated.py").write_text("UNTRACKED = True\n", encoding="utf-8")
            (root / "validation" / "generated.json").write_text("{}\n", encoding="utf-8")
            with patch.object(phase3, "ROOT", root):
                names = {path.relative_to(root).as_posix() for path in phase3.source_files()}
            self.assertEqual(
                {
                    "README.md",
                    "cws_convertor/module.py",
                    "tests/contract_smoke.py",
                    "validation/contract.json",
                },
                names,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
