from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cws_convertor.manufacturing_interpreter.contracts import CrossSectionSignature
from cws_convertor.manufacturing_interpreter.profile_geometry import match_full_profile_geometry
from cws_convertor.steel_model.tolerances import DEFAULT_TOLERANCE_POLICY
from profile_database import ProfileDefinition
class CandidateMetricTests(unittest.TestCase):
 def test_unmeasured_moments_and_contours_are_not_zero_errors(self):
  section=CrossSectionSignature('s','f',3080,788,200,100,12,0,(('LINE',12),),'I')
  row=match_full_profile_geometry(section,SimpleNamespace(profiles=[ProfileDefinition('SYNTHETIC_I','I','I',200,100,10,6)]),DEFAULT_TOLERANCE_POLICY)[0]
  self.assertIsNone(row.contour_distance_mm)
  self.assertIsNone(row.moment_residual)
  self.assertIsNone(row.radius_residual_mm)
  self.assertEqual('COARSE_CANDIDATE_ONLY',row.evidence_status)
 def test_empty_catalogue_cannot_make_match(self):
  section=CrossSectionSignature('s','f',3080,788,200,100,12,0,(('LINE',12),),'I')
  self.assertFalse(match_full_profile_geometry(section,SimpleNamespace(profiles=[]),DEFAULT_TOLERANCE_POLICY))
if __name__=='__main__':unittest.main(verbosity=2)
