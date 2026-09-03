from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ViewerSourceMirrorSmoke(unittest.TestCase):
    def test_ifc_source_mirror_is_hash_bound_reused_and_self_healing(self) -> None:
        from cws_viewer.geometry.worker_pool import _stage_ifc_source

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "network-source.ifc"
            payload = b"ISO-10303-21;\nDATA;\n#1=IFCPROJECT('CWS');\nENDSEC;\nEND-ISO-10303-21;\n"
            source.write_bytes(payload)
            source_hash = hashlib.sha256(payload).hexdigest()
            mirror_root = root / "local-mirror"
            with patch.dict(os.environ, {"CWS_VIEWER_SOURCE_MIRROR_ROOT": str(mirror_root)}):
                first = _stage_ifc_source(str(source), source_hash)
                second = _stage_ifc_source(str(source), source_hash)
                self.assertEqual(first, second)
                self.assertEqual(first.name, f"{source_hash}.ifc")
                self.assertEqual(first.read_bytes(), payload)

                first.write_bytes(b"corrupt")
                repaired = _stage_ifc_source(str(source), source_hash)
                self.assertEqual(repaired, first)
                self.assertEqual(repaired.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
