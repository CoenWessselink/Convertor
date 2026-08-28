from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hashes(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _hashes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _hashes(item)
    elif isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in value):
        yield value.lower()


class Phase2M18PackagedGateTests(unittest.TestCase):
    def test_authority_runtime_hash_and_zip_are_valid_in_source_and_package(self) -> None:
        roots = [ROOT / "cws_convertor" / "manufacturing"]
        packaged = os.environ.get("CWS_PHASE2_RUNTIME_DIR", "").strip()
        if packaged:
            roots.append(Path(packaged).resolve())
        for root in roots:
            archives = list(root.rglob("m18_authority_runtime.zip"))
            manifests = list(root.rglob("m18_authority_runtime.manifest.json"))
            self.assertEqual(1, len(archives), root)
            self.assertEqual(1, len(manifests), root)
            actual = _sha(archives[0])
            manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertIn(actual, set(_hashes(manifest)))
            with zipfile.ZipFile(archives[0], "r") as bundle:
                self.assertIsNone(bundle.testzip())
                self.assertGreater(len(bundle.namelist()), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
