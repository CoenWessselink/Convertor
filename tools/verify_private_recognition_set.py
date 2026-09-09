"""Run a hash-bound private file acceptance set without publishing its contents.

Usage: python tools/verify_private_recognition_set.py --manifest /private/set.json
       --root /private/inputs --output /private/proof [--native-all]
Each manifest file has `file`, `sha256`, and a non-empty `expected` map of
observed fields. Fixture files/expectations stay outside the public repository.
This is source-runtime evidence; an installed EXE run remains a separate gate.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def observe(path: Path, output: Path, native_all: bool) -> dict:
    from cws_convertor.project import ProjectSession
    from cws_convertor.project.source_geometry import inspect_part_source_geometry
    from cws_convertor.manufacturing_interpreter.pipeline import ManufacturingGeometryInterpreter
    from cws_convertor.manufacturing_interpreter.project_link import build_project_part_request
    from cws_convertor.importers.drawing_intake import analyze_assembly_pdf, analyze_dxf_plate
    result: dict = {}
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        from pdf_support import analyze_pdf
        table = analyze_assembly_pdf(path)
        if table is None:
            raise ValueError('Geen aantoonbare assemblagestuklijst')
        candidate = analyze_pdf(path)
        result.update(rows=table['row_count'], quantity=table['total_quantity'], drawing_number=table['drawing_number'],
                      candidate_profile=candidate.part.header.profile, candidate_mode=candidate.mode)
        _json(output/'pdf-table.json', table)
        return result
    model_path = path
    if suffix in {'.nc', '.nc1'}:
        from conversion import convert_file
        files, warnings, failures = convert_file(path, output/'converted', 'nc1-step', strict_validation=True)
        if failures or len(files) != 1:
            raise ValueError(f'NC1-conversie onvolledig: {failures}')
        model_path = Path(files[0]); result['conversion_warnings'] = list(warnings)
    with ProjectSession.new('Private recognition acceptance') as session:
        if suffix == '.dxf':
            drawing = analyze_dxf_plate(path)
            intake = session.import_drawing_source(path)
            part = session.project.parts[intake['part_ids'][0]]
            source = session.project.sources[part.source_identity.source_file_id]
            result.update(rows=len(drawing['rows']), position=drawing['position'], material=drawing['material'],
                          dimensions_mm=[drawing['length_mm'], drawing['width_mm'], drawing['thickness_mm']],
                          source_holes=drawing['source_holes'])
            _json(output/'drawing.json', drawing)
        else:
            source = session.register_sources([model_path], include_step_geometry=False)[0].source
            session.semantic_import_source(source.source_id)
        project = session.project
        result.update(parts=len(project.parts), assemblies=len(project.assemblies), fasteners=len(project.fasteners),
                      quantity=sum(p.quantity_total for p in project.parts.values()),
                      empty_names=sum(not p.name.strip() for p in project.parts.values()),
                      categories=dict(Counter(p.category for p in project.parts.values())),
                      names=dict(Counter(p.properties.get('step_product_name') or p.name for p in project.parts.values())))
        if suffix == '.ifc':
            declared = [(p, properties.get('Part mark')) for p in project.parts.values()
                        for properties in p.properties.get('ifc_property_sets', {}).values() if properties.get('Part mark')]
            result['declared_part_marks'] = len(declared)
            result['correct_part_marks'] = sum(p.part_position == mark for p, mark in declared)
        inspections = []
        inspect_all = native_all or suffix in {'.dxf', '.nc', '.nc1'} or len(project.parts) == 1
        for part in project.parts.values() if inspect_all else ():
            inspection = inspect_part_source_geometry(part, source, model_path)
            inspections.append(inspection.to_dict())
            if len(project.parts) == 1 and inspection.production_geometry_exact:
                request = build_project_part_request(part, inspection)
                report = ManufacturingGeometryInterpreter(cache_root=output/'cache').analyze(request)
                holes = [f for f in report.features if f.semantic_type.value == 'HOLE']
                result.update(hole_count=len(holes), profile=part.profile, recognised_profile=report.profile.designation,
                              profile_status=report.profile.status.value, equivalence=report.equivalence.status.value,
                              material=part.material, readiness=report.readiness.value, blockers=list(report.blockers))
                result['hole_diameters_mm'] = sorted(round(dict(f.parameters).get('diameter_mm', 2*dict(f.parameters).get('radius_mm', 0)), 6) for f in holes)
                frame_match = dict(report.evidence).get('source_hole_frame_match')
                if frame_match:
                    result['source_hole_frame_match'] = json.loads(frame_match)['status']
                _json(output/'recognition.json', report.to_dict())
            if part.canonical_part:
                result['canonical_holes'] = len(part.get_canonical().holes)
        if inspections:
            result['geometry_statuses'] = dict(Counter(row['status'] for row in inspections))
            result['verified_source_selectors'] = sum(row['selection_verified'] for row in inspections)
            result['exact_brep_parts'] = sum(row['production_geometry_exact'] for row in inspections)
            _json(output/'source-inspections.json', inspections)
        _json(output/'project.json', project.to_dict())
        target = output/'roundtrip.cwscproj'
        session.save(target)
        with ProjectSession.open(target) as reopened:
            before = {p.internal_id: (p.name,p.part_position,p.quantity_total,p.category,p.material,p.canonical_part) for p in project.parts.values()}
            after = {p.internal_id: (p.name,p.part_position,p.quantity_total,p.category,p.material,p.canonical_part) for p in reopened.project.parts.values()}
            result['save_reopen_preserved'] = before == after
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-all', action='store_true')
    args=parser.parse_args(); inputs=args.root.resolve(); output=args.output.resolve()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    cases=manifest.get('files', [])
    if not cases or len({row['file'] for row in cases}) != len(cases):
        raise ValueError('Niet-lege unieke bestandsset vereist')
    rows=[]
    for index, case in enumerate(cases):
        start=time.monotonic(); path=(inputs/case['file']).resolve()
        row={'file':case['file'], 'expected_sha256':case['sha256'], 'status':'FAIL'}
        try:
            if not path.is_relative_to(inputs) or not path.is_file() or sha256(path) != case['sha256']:
                raise ValueError('Bronpad of bronhash wijkt af')
            if not case.get('expected'):
                raise ValueError('Onafhankelijke verwachtingen ontbreken')
            observed=observe(path, output/f'case-{index+1:03d}', args.native_all)
            checks={key: observed.get(key) == expected for key,expected in case['expected'].items()}
            row.update(observed=observed, expected=case['expected'], checks=checks,
                       input_unchanged=sha256(path)==case['sha256'])
            row['status']='PASS' if all(checks.values()) and row['input_unchanged'] else 'FAIL'
        except Exception as exc:
            row['error']=f'{type(exc).__name__}: {exc}'
        row['seconds']=round(time.monotonic()-start,3); rows.append(row)
        _json(output/'RESULTS.json', rows)
        print(f"{index+1}/{len(cases)} {row['status']} {case['file']}",flush=True)
    git=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True)
    dirty=subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True)
    report={'schema':'cws-private-recognition-acceptance-1','status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL',
            'manifest_sha256':sha256(args.manifest),'source_commit':git.stdout.strip(),
            'source_worktree_dirty':bool(dirty.stdout.strip()),'runtime':platform.platform(),
            'frozen':bool(getattr(sys,'frozen',False)),'installed_windows_exe_accepted':False,
            'native_all_requested':args.native_all,'files':rows,'full_product_release_approved':False}
    _json(output/'ACCEPTANCE.json',report)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
