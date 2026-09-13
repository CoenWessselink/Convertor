"""Independent semantic inventory and atomic intake regressions (synthetic P21).

These tests assert source identities and publication behaviour, not fabricated
native geometry or physical manufacture counts for a multi-body product.
"""
from __future__ import annotations
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from cws_convertor.project import ProjectSession
from cws_convertor.project.model import ProjectModel
from cws_convertor.project.storage import ProjectPackageError

spec = importlib.util.spec_from_file_location('identity_fixture', ROOT / 'tests' / 'step_semantic_import_smoke.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def repeated_leaf_source():
    # Two paths through the same subassembly definition, one leaf occurrence
    # label reused in each path: these are two physical source occurrences.
    return fixture.ASSEMBLY_STEP.replace(
        "#30=NEXT_ASSEMBLY_USAGE_OCCURRENCE('OCC-1','Plate occurrence','',#12,#22,'P1');",
        """#40=PRODUCT('SUB','Subassembly','',(#2));
#41=PRODUCT_DEFINITION_FORMATION('','',#40);
#42=PRODUCT_DEFINITION('','',#41,$);
#50=NEXT_ASSEMBLY_USAGE_OCCURRENCE('SUB-A','','',#12,#42,'');
#51=NEXT_ASSEMBLY_USAGE_OCCURRENCE('SUB-B','','',#12,#42,'');
#30=NEXT_ASSEMBLY_USAGE_OCCURRENCE('LEAF','Plate occurrence','',#42,#22,'P1');""")


class IntakeIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'source.step'
        self.path.write_text(repeated_leaf_source(), encoding='utf-8')
        self.session = ProjectSession.new('Independent inventory')
        self.addCleanup(self.session.close)
        self.source_id = self.session.register_sources([self.path], include_step_geometry=False)[0].source.source_id

    def test_reused_source_entity_maps_every_occurrence_without_silent_overwrite(self):
        self.session.semantic_import_source(self.source_id)
        parts = list(self.session.project.parts.values())
        self.assertEqual(2, len(parts))
        occurrences = self.session.project.settings['source_entity_occurrences'][self.source_id]['#30']
        self.assertEqual(sorted(p.internal_id for p in parts), occurrences)
        self.assertNotIn('#30', self.session.project.settings['source_entity_maps'][self.source_id])

    def test_accounting_is_saved_reopened_and_reimported_without_duplicate_nodes(self):
        self.session.semantic_import_source(self.source_id)
        expected = self.session.project.settings['source_entity_occurrences'][self.source_id]
        self.session.semantic_import_source(self.source_id)
        self.assertEqual(expected, self.session.project.settings['source_entity_occurrences'][self.source_id])
        saved = self.session.save(Path(self.temp.name) / 'project.cwscproj')
        with ProjectSession.open(saved) as reopened:
            self.assertEqual(expected, reopened.project.settings['source_entity_occurrences'][self.source_id])
            self.assertEqual(2, len(reopened.project.parts))

    def test_changed_source_bytes_cannot_publish_a_mixed_revision(self):
        before = self.session.project.to_dict()
        changed = False
        def progress(current, total, text):
            nonlocal changed
            if 'geïmporteerd:' in text.lower() and not changed:
                self.path.write_bytes(self.path.read_bytes() + b'\n')
                changed = True
        with self.assertRaises(ProjectPackageError):
            self.session.semantic_import_sources([self.source_id], progress_callback=progress)
        self.assertTrue(changed)
        self.assertEqual(before, self.session.project.to_dict())

    def test_concurrent_user_edit_is_kept_instead_of_overwritten(self):
        original = self.session.project
        def progress(current, total, text):
            if 'geïmporteerd:' in text.lower():
                original.settings['user_edit_during_import'] = {'chosen': 'keep me'}
                self.session.dirty = True
        with self.assertRaises(ProjectPackageError):
            self.session.semantic_import_sources([self.source_id], progress_callback=progress)
        self.assertIs(original, self.session.project)
        self.assertEqual({'chosen': 'keep me'}, self.session.project.settings['user_edit_during_import'])
        self.assertFalse(self.session.project.parts)
        self.assertTrue(self.session.dirty)

    def test_concurrent_project_switch_is_never_rolled_back(self):
        other = ProjectModel.new('Other active project')
        def progress(current, total, text):
            if 'geïmporteerd:' in text.lower():
                self.session.project = other
                self.session.dirty = True
        with self.assertRaises(ProjectPackageError):
            self.session.semantic_import_sources([self.source_id], progress_callback=progress)
        self.assertIs(other, self.session.project)
        self.assertTrue(self.session.dirty)

    def test_cancel_after_classification_cannot_publish(self):
        import cws_convertor.project.service as service
        before = self.session.project.to_dict()
        finished = False
        original = service.classify_project_model
        def classify(*args, **kwargs):
            nonlocal finished
            result = original(*args, **kwargs)
            finished = True
            return result
        def cancel():
            if finished:
                raise RuntimeError('Cancelled before publish')
        with patch.object(service, 'classify_project_model', side_effect=classify):
            with self.assertRaisesRegex(RuntimeError, 'Cancelled'):
                self.session.semantic_import_sources([self.source_id], cancel_check=cancel)
        self.assertEqual(before, self.session.project.to_dict())

if __name__ == '__main__': unittest.main(verbosity=2)
