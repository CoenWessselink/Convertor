from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.build_viewer_release_audit import copy_evidence, digest, validate_evidence_manifest


class ViewerReleaseAuditSmoke(unittest.TestCase):
    def test_raw_and_annotated_evidence_are_hash_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "workspace-viewer.png"
            Image.new("RGB", (640, 360), "#dfeaf2").save(source)
            destination = root / "evidence"
            rows = copy_evidence(
                destination,
                commit="a" * 40,
                build_checksum="b" * 64,
                machine_id="TEST-MACHINE",
                generated_at="2026-09-02T00:00:00Z",
                extra_images=(source,),
                include_repository_images=False,
            )
            manifest = {"files": rows}
            validate_evidence_manifest(destination, manifest)
            self.assertEqual(2, len(rows))
            self.assertEqual({"raw", "annotated"}, {row["kind"] for row in rows})
            target = destination / rows[0]["relative_name"]
            self.assertEqual(rows[0]["sha256"], digest(target))

    def test_manifest_validation_fails_closed_after_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "phase3-gui.png"
            Image.new("RGB", (320, 200), "white").save(source)
            destination = root / "evidence"
            rows = copy_evidence(
                destination,
                commit="c" * 40,
                build_checksum="d" * 64,
                machine_id="TEST-MACHINE",
                generated_at="2026-09-02T00:00:00Z",
                extra_images=(source,),
                include_repository_images=False,
            )
            tampered = destination / rows[0]["relative_name"]
            tampered.write_bytes(tampered.read_bytes() + b"tampered")
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                validate_evidence_manifest(destination, {"files": rows})


if __name__ == "__main__":
    unittest.main(verbosity=2)
