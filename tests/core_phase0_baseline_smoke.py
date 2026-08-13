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

from validation.run_core_phase0_baseline import (
    REPORT_SCHEMA,
    collect_product_identity,
    collect_reference_inventory,
    collect_tracked_input_hashes,
    compare_master_prompts,
    verify_handover_zip,
)


class CorePhase0BaselineTests(unittest.TestCase):
    def test_product_and_pinned_input_contract(self) -> None:
        product = collect_product_identity()
        self.assertEqual(product["name"], "CWS Convertor")
        self.assertEqual(product["version"], "0.8.3-beta-dev")
        self.assertEqual(product["project_schema"], "2.5")
        self.assertEqual(REPORT_SCHEMA, "cws-core-phase0-baseline-v1")

        tracked = collect_tracked_input_hashes()
        self.assertTrue(all(item["present"] for item in tracked.values()))
        self.assertTrue(all(len(item["sha256"]) == 64 for item in tracked.values()))

    def test_prompt_comparison_is_text_aware(self) -> None:
        repository_prompt = ROOT / "docs" / "CODEX_MASTER_PROMPT_COMPLETE.md"
        comparison = compare_master_prompts(repository_prompt, repository_prompt)
        self.assertTrue(comparison["byte_identical"])
        self.assertTrue(comparison["text_identical"])
        self.assertEqual(comparison["differing_lines"], 0)

    def test_reference_inventory_keeps_manual_results_separate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_phase0_refs_") as folder:
            base = Path(folder)
            model_root = base / "models"
            result_root = base / "results"
            model_root.mkdir()
            result_root.mkdir()
            (model_root / "fixture.step").write_bytes(b"STEP fixture")
            (result_root / "fixture.expected.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "model": {
                            "id": "fixture",
                            "path": "fixture.step",
                            "format": "STEP",
                            "confidential": True,
                        },
                        "validation": {"status": "manual_validation_required"},
                        "comparison": {},
                    }
                ),
                encoding="utf-8",
            )
            inventory = collect_reference_inventory(
                model_roots=[(model_root, True, "local")],
                result_roots=[(result_root, True, "local")],
                supporting_roots=[],
            )
        self.assertEqual(inventory["model_count"], 1)
        self.assertEqual(inventory["models_by_format"], {"STEP": 1})
        self.assertEqual(
            inventory["expected_results_by_status"],
            {"manual_validation_required": 1},
        )
        self.assertEqual(inventory["models_by_confidentiality"], {"confidential": 1})

    def test_handover_manifest_verification_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_phase0_zip_") as folder:
            archive_path = Path(folder) / "handover.zip"
            payload = b"verified payload"
            checksum = hashlib.sha256(payload).hexdigest()
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("handover/payload.txt", payload)
                archive.writestr(
                    "handover/SHA256SUMS.txt",
                    f"{checksum}  payload.txt\n",
                )
            verified = verify_handover_zip(archive_path)
            self.assertEqual(verified["status"], "passed")
            self.assertEqual(verified["verified_entries"], 1)

            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("handover/payload.txt", b"changed")
                archive.writestr(
                    "handover/SHA256SUMS.txt",
                    f"{checksum}  payload.txt\n",
                )
            rejected = verify_handover_zip(archive_path)
            self.assertEqual(rejected["status"], "failed")
            self.assertEqual(rejected["verified_entries"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
