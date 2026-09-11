"""Exact review formats/scopes and publication failures; no production approval."""
from __future__ import annotations
from copy import deepcopy
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cws_convertor.bom import build_bom_snapshot
from cws_convertor.bom.review_export import export_bom_review
from cws_convertor.bom.workspace import BOMScope, scoped_bom_snapshot
from cws_convertor.project.model import Assembly, Part, ProjectModel


def _project():
    project = ProjectModel.new('Synthetic review fixture')
    for key, quantity in (('P1', 2), ('P2', 3)):
        part = Part(internal_id=key, name='B1', part_position='B1',
            profile='HEA200', normalized_profile='HEA200', material='S355J2',
            normalized_material='S355J2', material_grade='S355J2', length_mm=2500,
            quantity_total=quantity, mass_each_kg=105, surface_area_each_m2=3.2,
            classification_status='confirmed', classification_confidence=1,
            profile_confidence=1, material_confidence=1,
            geometry_descriptor={'bbox': [2500,200,190]})
        part.recompute_hashes(); project.add_entity(part)
    project.add_entity(Assembly(internal_id='A1', assembly_mark='A1', name='A1', part_ids=['P1','P2']))
    for part in project.parts.values(): part.assembly_ids.append('A1')
    project.validate()
    return project


class ReviewExports(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.project = _project()
        self.source = build_bom_snapshot(self.project, classify_if_needed=False)
        self.scope = BOMScope.create(family='parts', entity_ids=('P1',), group_ids=(self.source.part_bom[0].group_id,))
        self.snapshot = scoped_bom_snapshot(self.source, scope=self.scope, project=self.project, strict_entities=True)

    def write(self, action):
        return export_bom_review(self.snapshot, self.out, action_id=action,
                                 source_snapshot_sha256=self.source.snapshot_sha256)

    def verify(self, outputs, action):
        manifest = json.loads(outputs['REVIEW_EXPORT.json'].read_text())
        self.assertEqual(action, manifest['action_id'])
        self.assertEqual(self.snapshot.snapshot_sha256, manifest['snapshot_sha256'])
        self.assertTrue(manifest['review_only']); self.assertFalse(manifest['production_release_allowed'])
        self.assertFalse(manifest['machine_transfer_allowed'])
        for name, item in manifest['files'].items():
            p = outputs[name]
            self.assertTrue(p.is_absolute()); self.assertTrue(p.is_file())
            self.assertEqual(item['sha256'], hashlib.sha256(p.read_bytes()).hexdigest())
        return manifest

    def test_strict_selection_does_not_expand_to_shared_mark_or_parent_siblings(self):
        self.assertEqual(['P1'], self.snapshot.part_bom[0].part_ids)
        self.assertEqual(2, self.snapshot.part_bom[0].quantity)
        self.assertEqual([], self.snapshot.assembly_bom)
        self.assertEqual({'P1'}, {r['internal_id'] for r in self.snapshot.traceability})
        self.assertEqual(5000, self.snapshot.summary['total_part_length_mm'])
        self.assertEqual(210, self.snapshot.summary['total_part_mass_kg'])
        self.assertEqual(2, self.snapshot.material_bom[0].quantity)
        self.assertEqual(5000, self.snapshot.material_bom[0].net_length_mm)

    def test_zero_quantity_is_not_invented_as_one(self):
        self.project.parts['P1'].quantity_total = 0
        scoped = scoped_bom_snapshot(self.source, scope=self.scope, project=self.project, strict_entities=True)
        self.assertEqual(0, scoped.part_bom[0].quantity)
        self.assertEqual(0, scoped.part_bom[0].total_mass_kg)

    def test_invalid_quantity_is_rejected_not_truncated(self):
        self.project.parts['P1'].quantity_total = 1.5
        with self.assertRaisesRegex(ValueError, 'Reviewaantal'):
            scoped_bom_snapshot(self.source, scope=self.scope, project=self.project, strict_entities=True)

    def test_unknown_group_does_not_silently_export_empty_scope(self):
        with self.assertRaisesRegex(ValueError, 'BOM-groepen'):
            scoped_bom_snapshot(self.source, scope=BOMScope.create(family='parts', group_ids=('unknown',)), project=self.project, strict_entities=True)

    def test_group_only_scope_requires_explicit_entities(self):
        with self.assertRaisesRegex(ValueError, "object-IDs"):
            scoped_bom_snapshot(self.source, scope=BOMScope.create(family="parts", group_ids=(self.source.part_bom[0].group_id,)), project=self.project, strict_entities=True)

    def test_nested_shared_assembly_group_is_rejected(self):
        child = Assembly(internal_id="CH1", assembly_mark="CH", name="CH", part_ids=["P1"])
        other = Assembly(internal_id="CH2", assembly_mark="CH", name="CH", part_ids=["P2"])
        self.project.add_entity(child); self.project.add_entity(other)
        self.project.assemblies["A1"].child_assembly_ids = ["CH1"]
        self.project.assemblies["A1"].part_ids = []
        self.project.parts["P1"].assembly_ids = ["CH1"]
        self.project.parts["P2"].assembly_ids = ["CH2"]
        source = build_bom_snapshot(self.project, classify_if_needed=False)
        child_row = next(r for r in source.assembly_bom if "CH1" in r.assembly_ids)
        self.assertIn("CH2", child_row.assembly_ids)
        with self.assertRaisesRegex(ValueError, "niet-geselecteerde occurrences"):
            scoped_bom_snapshot(source, scope=BOMScope.create(family="assemblies", entity_ids=("A1",)), project=self.project, strict_entities=True)

    def test_selected_part_keeps_assembly_mark_as_context_not_sibling_rows(self):
        self.assertEqual(['A1'], self.snapshot.part_bom[0].assembly_marks)
        self.assertEqual([], self.snapshot.assembly_bom)

    def test_two_selected_parts_preserve_full_actual_quantity(self):
        scoped = scoped_bom_snapshot(self.source, scope=BOMScope.create(family='parts', entity_ids=('P1','P2')), project=self.project, strict_entities=True)
        self.assertEqual(5, scoped.part_bom[0].quantity)
        self.assertEqual({'P1','P2'}, set(scoped.part_bom[0].part_ids))

    def test_legacy_scope_behavior_is_not_silently_changed(self):
        legacy = scoped_bom_snapshot(self.source, scope=self.scope, project=self.project)
        self.assertEqual(5, legacy.part_bom[0].quantity)
        self.assertEqual({'P1','P2'}, set(legacy.part_bom[0].part_ids))

    def test_explicit_assembly_keeps_its_children(self):
        scoped = scoped_bom_snapshot(self.source, scope=BOMScope.create(family='assemblies', entity_ids=('A1',)),
                                    project=self.project, strict_entities=True)
        self.assertEqual(5, scoped.part_bom[0].quantity)
        self.assertEqual({'P1','P2'}, set(scoped.part_bom[0].part_ids))

    def test_empty_strict_scope_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Lege'):
            scoped_bom_snapshot(self.source, scope=BOMScope.create(family='parts'), project=self.project, strict_entities=True)

    def test_unknown_strict_entity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'onbekende'):
            scoped_bom_snapshot(self.source, scope=BOMScope.create(family='parts', entity_ids=('missing',)), project=self.project, strict_entities=True)

    def test_strict_scope_requires_project(self):
        with self.assertRaises(ValueError):
            scoped_bom_snapshot(self.source, scope=self.scope, strict_entities=True)

    def test_json_is_only_json_and_preserves_raw_data(self):
        self.snapshot.project_name = '=Synthetic fixture'
        self.snapshot.refresh_hash()
        outputs = self.write('export.json'); manifest = self.verify(outputs, 'export.json')
        self.assertEqual({'.json'}, {Path(n).suffix for n in manifest['files'] if n not in {'manifest.json', 'validation.json', 'SHA256SUMS.txt'}})
        data = json.loads(outputs[next(n for n in manifest['files'] if n not in {"manifest.json", "validation.json", "SHA256SUMS.txt"})].read_text())
        self.assertEqual('=Synthetic fixture', data['project_name'])
        self.assertEqual(['P1'], data['part_bom'][0]['part_ids'])

    def test_csv_has_eight_datasets_no_unrequested_pdf_or_xlsx(self):
        outputs = self.write('export.csv'); manifest = self.verify(outputs, 'export.csv')
        self.assertEqual(8, len(set(manifest['files']) - {"manifest.json", "validation.json", "SHA256SUMS.txt"}))
        self.assertEqual({'.csv'}, {Path(n).suffix for n in manifest['files'] if n not in {'manifest.json', 'validation.json', 'SHA256SUMS.txt'}})
        with outputs['part_bom.csv'].open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual('2', rows[0]['quantity']); self.assertEqual('P1', rows[0]['part_ids'])

    def test_xlsx_has_only_workbook_and_no_formula_or_external_link_injection(self):
        self.snapshot.part_bom[0].part_position = '=HYPERLINK("https://invalid.example","X")'
        self.snapshot.refresh_hash()
        outputs = self.write('export.xlsx'); manifest = self.verify(outputs, 'export.xlsx')
        self.assertEqual({'.xlsx'}, {Path(n).suffix for n in manifest['files'] if n not in {'manifest.json', 'validation.json', 'SHA256SUMS.txt'}})
        path = outputs[next(n for n in manifest['files'] if n not in {"manifest.json", "validation.json", "SHA256SUMS.txt"})]
        with zipfile.ZipFile(path) as z:
            self.assertFalse(any(n.startswith('xl/externalLinks/') for n in z.namelist()))
            for n in z.namelist():
                if n.startswith('xl/worksheets/') and n.endswith('.xml'):
                    self.assertEqual([], ET.fromstring(z.read(n)).findall('.//{*}f'))
            self.assertIn(b"'=HYPERLINK", z.read('xl/sharedStrings.xml'))

    def test_complete_review_kit_still_contains_original_formats(self):
        outputs = self.write('export.review'); manifest = self.verify(outputs, 'export.review')
        self.assertTrue({'.xlsx','.csv','.json','.pdf','.zip'} <= {Path(n).suffix for n in manifest['files'] if n not in {'manifest.json', 'validation.json', 'SHA256SUMS.txt'}})

    def test_unknown_action_writes_nothing(self):
        with self.assertRaises(ValueError): self.write('export.step')
        self.assertEqual([], list(self.out.iterdir()))

    def test_changed_snapshot_is_rejected(self):
        self.snapshot.part_bom[0].quantity = 999
        with self.assertRaisesRegex(ValueError,'hash'): self.write('export.json')
        self.assertEqual([], list(self.out.iterdir()))

    def test_stale_before_start_writes_nothing(self):
        with self.assertRaisesRegex(ValueError,'verouderde'):
            export_bom_review(self.snapshot,self.out,action_id='export.json',validate_before_publish=lambda:False)
        self.assertEqual([], list(self.out.iterdir()))

    def test_changed_source_during_write_cleans_staging_and_does_not_publish(self):
        with self.assertRaisesRegex(ValueError,'niet gepubliceerd'):
            with patch('cws_convertor.bom.review_export._digest', wraps=__import__('cws_convertor.bom.review_export',fromlist=['_digest'])._digest):
                replies = iter((True,False))
                export_bom_review(self.snapshot,self.out,action_id='export.json',validate_before_publish=lambda:next(replies))
        self.assertEqual([], list(self.out.iterdir()))

    def test_writer_failure_cleans_partial_files(self):
        def fail(path, snapshot):
            path.write_bytes(b'partial'); raise OSError('simulated disk failure')
        with patch('cws_convertor.bom.export._write_xlsx', side_effect=fail):
            with self.assertRaises(OSError): self.write('export.xlsx')
        self.assertEqual([], list(self.out.iterdir()))

    def test_collision_does_not_overwrite_existing_review(self):
        with patch('cws_convertor.bom.review_export.uuid4',return_value=SimpleNamespace(hex='a'*32)):
            first=self.write('export.json'); before={p: p.read_bytes() for p in first.values()}
            with self.assertRaises(FileExistsError): self.write('export.json')
        self.assertEqual(1,len(list(self.out.iterdir())))
        for path,data in before.items():self.assertEqual(data,path.read_bytes())

    def test_repeated_export_does_not_mix_formats_or_modify_project(self):
        before=deepcopy(self.project.to_dict())
        first=self.write('export.csv'); second=self.write('export.xlsx')
        self.assertNotEqual(next(iter(first.values())).parent,next(iter(second.values())).parent)
        self.assertEqual(before,self.project.to_dict())

    def test_missing_output_directory_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            export_bom_review(self.snapshot,self.out/'missing',action_id='export.json')
        self.assertEqual([],list(self.out.iterdir()))


if __name__ == '__main__': unittest.main(verbosity=2)
