"""Stale derived scenes must fall back to verified sources, never weaken identity.

Uses an actual STEP solid and project ZIP. Mutations affect only disposable cache
objects, not the canonical source. No rendering or material truth is mocked.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cws_convertor.project.service import ProjectSession
from cws_convertor.project.storage import ProjectPackageError
from cws_convertor.errors import ErrorCode
from cws_convertor.integration import IntegratedProjectWorkspace
from cws_viewer.geometry.loader import MeshRepository


class WarmstartRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cadquery as cq
        cls.directory=tempfile.TemporaryDirectory(prefix='cws-warmstart-recovery-')
        cls.folder=Path(cls.directory.name)
        step=cls.folder/'verified-source.step'
        cq.exporters.export(cq.Solid.makeBox(120,60,10),str(step))
        cls.path=cls.folder/'verified.cwscproj'
        with ProjectSession.new('Verified cache recovery',created_by='test') as session:
            registered=session.register_sources([step],include_step_geometry=True)[0]
            session.semantic_import_source(registered.source.source_id)
            session.save(cls.path,embed_sources=True,user='test')
        with IntegratedProjectWorkspace.open(cls.path,read_only=True,load_all_geometry=True,allow_proxy=False) as cold:
            cls.scene=cold.load_result.scene
            cls.repository=cold.load_result.repository
            cls.geometry_ids={item.geometry_id for item in cls.scene.geometry}
            if not cls.geometry_ids or cold.load_result.geometry_report.proxy_count:
                raise AssertionError('The fixture must contain native exact STEP geometry')

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def cache(self,scene=None,repository=None):
        return SimpleNamespace(scene=scene if scene is not None else self.scene,
                               repository=repository if repository is not None else self.repository,
                               elapsed_seconds=0.001,load_profile={'test':'explicit cache fixture'})

    def assert_recovered(self,cache):
        previews=[]
        with IntegratedProjectWorkspace.open(self.path,read_only=True,load_all_geometry=True,
                allow_proxy=False,preloaded_exact_scene=cache,preview_callback=previews.append) as actual:
            state=actual.load_result.load_profile['warmstart']
            self.assertEqual(state['status'],'rejected_canonical_mismatch')
            self.assertTrue(state['source_reloaded'])
            self.assertFalse(state['cached_scene_used'])
            self.assertIs(actual.load_result.project,actual.session.project)
            self.assertIsNot(actual.load_result.scene,cache.scene)
            self.assertIsNot(actual.load_result.repository,cache.repository)
            self.assertTrue(actual.identity_audit.passed)
            report=actual.load_result.geometry_report
            self.assertEqual(report.proxy_count,0)
            self.assertEqual(report.failed_count,0)
            self.assertEqual(report.ready_count,len(self.geometry_ids))
            self.assertEqual({r.geometry_id for r in actual.load_result.scene.geometry},self.geometry_ids)
            self.assertEqual(len(previews),1)
            for part in actual.project.parts.values():
                self.assertFalse(actual.readiness_for_part(part.internal_id)['allowed']['nc1'])

    def test_matching_exact_cache_is_reused(self):
        cached=self.cache()
        with IntegratedProjectWorkspace.open(self.path,read_only=True,load_all_geometry=True,
                allow_proxy=False,preloaded_exact_scene=cached) as actual:
            self.assertIs(actual.load_result.repository,cached.repository)
            self.assertEqual(actual.load_result.geometry_report.cache_hit_count,len(self.geometry_ids))
            self.assertTrue(actual.identity_audit.passed)

    def test_wrong_project_cache_is_rejected_and_source_reloaded(self):
        self.assert_recovered(self.cache(scene=replace(self.scene,project_id='wrong-project')))

    def test_changed_canonical_revision_is_recovered(self):
        model=replace(self.scene.models[0],revision_id='f'*64)
        self.assert_recovered(self.cache(scene=replace(self.scene,models=(model,))))

    def test_changed_node_identity_is_not_accepted(self):
        node=replace(self.scene.nodes[0],node_id='wrong-node')
        self.assert_recovered(self.cache(scene=replace(self.scene,nodes=(node,*self.scene.nodes[1:]))))

    def test_changed_geometry_hash_is_not_accepted(self):
        resource=replace(self.scene.geometry[0],content_hash='e'*64)
        self.assert_recovered(self.cache(scene=replace(self.scene,geometry=(resource,*self.scene.geometry[1:]))))

    def test_missing_cached_mesh_is_recovered_from_verified_step(self):
        self.assert_recovered(self.cache(repository=MeshRepository()))

    def test_damaged_source_package_is_still_blocked(self):
        damaged=self.folder/'damaged.cwscproj'
        with ZipFile(self.path) as original,ZipFile(damaged,'w',ZIP_DEFLATED) as target:
            for info in original.infolist():
                content=original.read(info.filename)
                if info.filename.startswith('sources/'):
                    content += b'\nUNVERIFIED SOURCE CHANGE\n'
                target.writestr(info.filename,content)
        with self.assertRaises(ProjectPackageError) as raised:
            IntegratedProjectWorkspace.open(damaged,read_only=True,load_all_geometry=True,
                allow_proxy=False,preloaded_exact_scene=self.cache())
        self.assertEqual(raised.exception.code,ErrorCode.PROJECT_CORRUPT)
        self.assertIn('Checksum',str(raised.exception))


if __name__=='__main__':unittest.main(verbosity=2)
