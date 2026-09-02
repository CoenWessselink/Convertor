from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validation.run_phase1_large_ifc_performance import source_geometry_checks


@dataclass
class Inspection:
    status: str
    scope: str = "part"
    selection_verified: bool = True
    geometry_kind: str = "mesh"
    production_geometry_exact: bool = False


class Phase1LargeIfcEvidenceContractTests(unittest.TestCase):
    def test_review_mesh_is_selected_without_an_exact_claim(self) -> None:
        self.assertEqual(
            source_geometry_checks(Inspection(status="resolved_mesh")),
            {
                "part_geometry_selected": True,
                "ifc_mesh_not_claimed_as_exact_brep": True,
            },
        )

    def test_native_brep_is_a_stronger_valid_evidence_outcome(self) -> None:
        self.assertEqual(
            source_geometry_checks(
                Inspection(
                    status="resolved_exact",
                    geometry_kind="native_brep",
                    production_geometry_exact=True,
                )
            ),
            {
                "part_geometry_selected": True,
                "ifc_mesh_not_claimed_as_exact_brep": True,
            },
        )

    def test_mesh_claimed_as_exact_fails_closed(self) -> None:
        checks = source_geometry_checks(
            Inspection(status="resolved_exact", production_geometry_exact=True)
        )
        self.assertFalse(checks["ifc_mesh_not_claimed_as_exact_brep"])

    def test_unverified_selection_fails_closed(self) -> None:
        checks = source_geometry_checks(
            Inspection(status="resolved_exact", selection_verified=False)
        )
        self.assertFalse(checks["part_geometry_selected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
