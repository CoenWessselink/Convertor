"""Actual DimensionGraph schema must bind to the existing DrawingLinter."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor.drawings.linter import _chain_conflict
from tests.interactive_dimension_editor_v2_smoke import _build


class ChainBindingTests(unittest.TestCase):
    def setUp(self):
        self.dimensions = {key: {'id': key, 'value_mm': value} for key, value in (
            ('total', 200), ('x1', 40), ('x2', 120), ('dx1', 40), ('dx2', 80))}
        self.ordinate = {'id': 'x', 'kind': 'ordinate_chain', 'axis': 'x',
                         'datum': {'type': 'datum'}, 'dimension_ids': ['x1', 'x2'],
                         'total_dimension_id': 'total'}
        self.combined = {**self.ordinate, 'kind': 'combined_incremental_absolute_chain',
                         'dimension_ids': ['dx1', 'dx2'], 'absolute_dimension_ids': ['x1', 'x2']}

    def test_actual_linter_accepts_canonical_ids_without_legacy_members(self):
        document = _build(dimensions=list(self.dimensions.values()), dimension_chains=[self.ordinate, self.combined])
        self.assertFalse(any(row['code'] == 'DRAWING_DIMENSION_CHAIN_CONFLICT' for row in document.lint['issues']))
        self.assertEqual(document.dimension_chains, [self.ordinate, self.combined])

    def test_single_station_has_explicit_datum_and_total(self):
        chain = {**self.ordinate, 'dimension_ids': ['x1']}
        self.assertFalse(_chain_conflict(chain, self.dimensions))
        for key in ('datum', 'total_dimension_id'):
            invalid = deepcopy(chain); invalid.pop(key)
            self.assertTrue(_chain_conflict(invalid, self.dimensions))

    def test_unknown_duplicate_missing_and_mixed_ids_remain_blocked(self):
        for ids in ([], ['unknown'], ['x1', 'x1'], 'x1'):
            self.assertTrue(_chain_conflict({**self.ordinate, 'dimension_ids': ids}, self.dimensions))
        self.assertTrue(_chain_conflict({**self.ordinate, 'members': ['x1', 'x2']}, self.dimensions))
        self.assertTrue(_chain_conflict({**self.ordinate, 'total_dimension_id': 'x1'}, self.dimensions))

    def test_out_of_order_and_out_of_range_remain_blocked(self):
        self.assertTrue(_chain_conflict({**self.ordinate, 'dimension_ids': ['x2', 'x1']}, self.dimensions))
        values = deepcopy(self.dimensions); values['total']['value_mm'] = 100
        self.assertTrue(_chain_conflict(self.ordinate, values))
        self.assertTrue(_chain_conflict(self.combined, values))

    def test_contradictory_incremental_absolute_chain_remains_blocked(self):
        values = deepcopy(self.dimensions); values['dx2']['value_mm'] = 70
        self.assertTrue(_chain_conflict(self.combined, values))
        for ids in (['x1'], ['x1', 'missing'], ['x1', 'x1'], ['x2', 'x1']):
            self.assertTrue(_chain_conflict({**self.combined, 'absolute_dimension_ids': ids}, self.dimensions))

    def test_nonfinite_and_negative_values_are_not_release_evidence(self):
        for value in (float('nan'), float('inf'), -1, 'bad'):
            values = deepcopy(self.dimensions); values['x1']['value_mm'] = value
            self.assertTrue(_chain_conflict(self.ordinate, values))

    def test_legacy_member_contract_is_not_relaxed(self):
        self.assertFalse(_chain_conflict({'id': 'legacy', 'members': ['x1', 'x2']}, self.dimensions))
        for values in ([], ['x1'], ['x1', 'x1'], ['x1', 'missing']):
            self.assertTrue(_chain_conflict({'id': 'legacy', 'members': values}, self.dimensions))


if __name__ == '__main__':
    unittest.main(verbosity=2)
