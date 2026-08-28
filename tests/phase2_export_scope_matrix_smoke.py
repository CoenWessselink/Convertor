from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.export_scope_matrix import EXPORT_SCOPE_MATRIX, validate_export_scope_matrix
from cws_convertor.project.manufacturing_contracts import ExportScopeKind


class Phase2ExportScopeMatrixTests(unittest.TestCase):
    def test_all_twelve_canonical_scopes_are_explicit_and_fail_closed(self) -> None:
        self.assertEqual(12, len(tuple(ExportScopeKind)))
        self.assertEqual(set(ExportScopeKind), set(EXPORT_SCOPE_MATRIX))
        self.assertEqual((), validate_export_scope_matrix())
        self.assertTrue(all(policy.fail_closed for policy in EXPORT_SCOPE_MATRIX.values()))

    def test_selection_never_falls_back_and_full_project_is_explicit(self) -> None:
        self.assertEqual("current_selection", EXPORT_SCOPE_MATRIX[ExportScopeKind.SELECTION].backend_kind)
        self.assertFalse(EXPORT_SCOPE_MATRIX[ExportScopeKind.SELECTION].requires_values)
        self.assertTrue(EXPORT_SCOPE_MATRIX[ExportScopeKind.FULL_PROJECT].requires_explicit_full_project)
        self.assertTrue(EXPORT_SCOPE_MATRIX[ExportScopeKind.SELECTED_PARTS].requires_values)


if __name__ == "__main__":
    unittest.main(verbosity=2)
