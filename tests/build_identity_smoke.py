"""Negative and positive checks for commit-bound frozen executable identity."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor import build_identity as identity
sys.path.insert(0, str(ROOT / 'tools'))
import build_phase3_windows_release as builder

class BuildIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'app.py').write_text('VALUE = 1\n', encoding='utf-8')
        for args in [['init'], ['config','user.name','test'], ['config','user.email','test@example.invalid'], ['add','.'], ['commit','-m','fixture']]:
            subprocess.run(['git',*args],cwd=self.root,check=True,capture_output=True)
        self.commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.root,text=True).strip()

    def test_clean_exact_identity(self):
        result = json.loads(identity.write_build_identity(self.root).read_text())
        self.assertEqual(self.commit,result['source_commit'])
        self.assertFalse(result['tracked_dirty'])
        self.assertEqual(40,len(result['source_tree']))

    def test_dirty_refused(self):
        (self.root/'app.py').write_text('VALUE = 2\n')
        with self.assertRaisesRegex(RuntimeError,'lokale wijzigingen'):
            identity.write_build_identity(self.root)

    def test_untracked_runtime_refused(self):
        (self.root/'extra.py').write_text('VALUE = 2\n')
        with self.assertRaisesRegex(RuntimeError,'niet-vastgelegde'):
            identity.write_build_identity(self.root)

    def test_frozen_identity_is_read_from_bundle(self):
        source=identity.write_build_identity(self.root)
        with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS',str(source.parent),create=True):
            result=identity.read_build_identity()
        self.assertTrue(result['frozen'])
        self.assertEqual(self.commit,result['source_commit'])

    def test_missing_or_corrupt_frozen_identity_refused(self):
        with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS',str(self.root),create=True):
            with self.assertRaises(FileNotFoundError): identity.read_build_identity()
            (self.root/identity.FILENAME).write_text('{}')
            with self.assertRaises(RuntimeError): identity.read_build_identity()

    def test_trigger_sha_never_overrides_checked_out_source(self):
        with patch.object(builder,'ROOT',self.root), patch.dict(os.environ,{'GITHUB_SHA':'f'*40,'CWS_BUILD_EXPECTED_SHA':''}):
            self.assertEqual(self.commit,builder.source_revision())

    def test_expected_sha_mismatch_refused(self):
        with patch.object(builder,'ROOT',self.root), patch.dict(os.environ,{'CWS_BUILD_EXPECTED_SHA':'f'*40}):
            with self.assertRaisesRegex(RuntimeError,'differs from expected'): builder.source_revision()

if __name__=='__main__': unittest.main(verbosity=2)
