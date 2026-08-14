from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.core.diagnostics import collect_runtime_report, scan_for_forbidden_trimble_references
from cws_viewer.selftest import run_self_test


class ViewerRuntimeTests(unittest.TestCase):
    def test_contract_selftest_passes(self) -> None:
        report = run_self_test(deep_native=False, scan_root=ROOT / "cws_viewer")
        self.assertTrue(report.passed, report.to_json())

    def test_capability_report_is_machine_readable(self) -> None:
        report = collect_runtime_report(deep=False)
        payload = report.to_dict()
        self.assertEqual("CWS Viewer Core", payload["product"])
        self.assertTrue(payload["report_hash"])
        self.assertIn("vtk", {probe["module"] for probe in payload["probes"]})

    def test_cws_source_tree_contains_no_trimble_binaries(self) -> None:
        findings = scan_for_forbidden_trimble_references(ROOT)
        self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main(verbosity=2)
