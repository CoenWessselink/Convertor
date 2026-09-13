"""Synthetic profile expectations constructed without the production builder."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import cadquery as cq

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from profile_database import ProfileDefinition
from cws_convertor.manufacturing_interpreter.contracts import ManufacturingInterpretationRequest
from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter


def independent_i(length=300., flange=5., web=4.):
    # Independent 100 x 60 polygon, dimensions intentionally not a stock designation.
    h,b=100.,60.
    points=[(-b/2,-h/2),(b/2,-h/2),(b/2,-h/2+flange),(web/2,-h/2+flange),
            (web/2,h/2-flange),(b/2,h/2-flange),(b/2,h/2),(-b/2,h/2),
            (-b/2,h/2-flange),(-web/2,h/2-flange),(-web/2,-h/2+flange),(-b/2,-h/2+flange)]
    return cq.Workplane('YZ').polyline(points).close().extrude(length).val()


def definition(name='SYNTHETIC-I'):
    return ProfileDefinition(name,'I','I',100,60,5,4,source='synthetic-independent-test')


def inspection(shape, name='opaque_body_348'):
    return SimpleNamespace(part_id=name,source_file_id='synthetic-source',source_sha256='fixture-'+name,
        source_geometry_hash='fixture-geometry-'+name,production_geometry_exact=True,
        selection_verified=True,native_shape=shape,geometry_kind='native_brep',evidence={})


class ProfileIntelligenceTests(unittest.TestCase):
    def analyze(self, shape, definitions=None, preferred=''):
        with tempfile.TemporaryDirectory() as directory:
            service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=definitions or [definition()]),cache_root=directory)
            return service.analyze(ManufacturingInterpretationRequest(inspection=inspection(shape),preferred_profile=preferred))

    def test_positive_i_polygon_matches_without_using_name(self):
        result=self.analyze(independent_i())
        self.assertEqual(result.profile.status.value,'PROVEN_WITHIN_POLICY')
        self.assertEqual(result.profile.designation,'SYNTHETIC-I')
        self.assertIn('MATERIAL_EVIDENCE_UNRESOLVED', result.blockers)

    def test_equal_area_wrong_web_and_flange_never_auto_match(self):
        # 2*60*6 + (100-12)*(240/88) = 960 = the reference area.
        result=self.analyze(independent_i(flange=6.,web=240./88.))
        self.assertNotEqual(result.profile.status.value,'PROVEN_WITHIN_POLICY')
        self.assertNotEqual(result.profile.designation,'SYNTHETIC-I')

    def test_short_i_uses_cross_section_not_longest_bbox_axis(self):
        result=self.analyze(independent_i(length=20.))
        self.assertEqual(result.profile.designation,'SYNTHETIC-I')
        chosen=next(a for a in result.axis_candidates if a.axis_id==result.selected_axis_id)
        self.assertAlmostEqual(chosen.length_mm,20.,places=5)

    def test_preferred_name_cannot_remove_geometric_ambiguity(self):
        result=self.analyze(independent_i(), [definition('A'),definition('B')], preferred='A')
        self.assertEqual(result.profile.status.value,'AMBIGUOUS')
        self.assertEqual(set(result.profile.candidates),{'A','B'})

    def test_rotated_profile_still_matches(self):
        result=self.analyze(independent_i().rotate((0,0,0),(1,2,3),37).translate((1234,-553,883)))
        self.assertEqual(result.profile.designation,'SYNTHETIC-I')

    def test_in_memory_catalogue_change_invalidates_cache(self):
        row=definition()
        with tempfile.TemporaryDirectory() as directory:
            service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[row]),cache_root=directory)
            request=ManufacturingInterpretationRequest(inspection=inspection(independent_i()))
            first=service.analyze(request)
            # Same object, same number of entries, unchanged path/size.
            row.dim3=6.;row.dim4=240./88.
            second=service.analyze(request)
            self.assertNotEqual(first.profile_database_hash,second.profile_database_hash)
            self.assertNotEqual(second.profile.status.value,'PROVEN_WITHIN_POLICY')

class SourceRevisionTests(unittest.TestCase):
    def test_source_changed_during_native_read_is_not_verified(self):
        from unittest.mock import patch
        from cws_convertor.manufacturing_interpreter.cli import _step_inspection
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'source.step'
            cq.exporters.export(independent_i(),str(path))
            original=cq.importers.importStep
            def changed_during_read(*args,**kwargs):
                result=original(*args,**kwargs)
                path.write_bytes(path.read_bytes()+b'\n')
                return result
            with patch.object(cq.importers,'importStep',side_effect=changed_during_read):
                with self.assertRaisesRegex(ValueError,'gewijzigd'):
                    _step_inspection(path)

    def test_same_geometry_retains_separate_occurrence_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            service=ManufacturingGeometryInterpreter(profile_database=SimpleNamespace(profiles=[definition()]),cache_root=directory)
            shape=independent_i()
            first=inspection(shape,'occurrence-A');second=inspection(shape,'occurrence-B')
            first.source_geometry_hash=second.source_geometry_hash='shared-native-resource'
            first.source_sha256=second.source_sha256='same-source-file'
            reports=[service.analyze(ManufacturingInterpretationRequest(inspection=i)) for i in (first,second)]
            self.assertEqual(['occurrence-A','occurrence-B'],[v.part_id for v in reports])
            self.assertNotEqual(reports[0].interpretation_id,reports[1].interpretation_id)
            self.assertTrue(all('MATERIAL_EVIDENCE_UNRESOLVED' in v.blockers for v in reports))

if __name__=='__main__': unittest.main(verbosity=2)
