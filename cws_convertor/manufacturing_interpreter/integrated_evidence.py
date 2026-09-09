"""Executable-native regression evidence for manufacturing recognition.

Fixtures are deliberately synthetic and independently parameterized. They do
not authorize machine output or claim supplier/material certification.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


def run_recognition_evidence(output: str | Path) -> dict[str, Any]:
    import cadquery as cq
    from .pipeline import ManufacturingGeometryInterpreter
    from .contracts import ManufacturingInterpretationRequest, MaterialEvidence, MaterialEvidenceStatus
    from .cli import _step_inspection
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    interpreter = ManufacturingGeometryInterpreter(cache_root=output / 'cache')
    checks: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []

    def check(name: str, condition: bool, detail: Any = None) -> None:
        checks.append({'name': name, 'status': 'PASS' if condition else 'FAIL', 'detail': detail})

    def grade(inspection):
        return MaterialEvidence(status=MaterialEvidenceStatus.USER_CONFIRMED,
            material='S355JR', grade='S355JR', confidence=1.0,
            source='synthetic_fixture_declaration', source_path='native-regression.fixture',
            reason='Explicit synthetic declaration; not inferred from shape',
            evidence=(('confirmed_by', 'automated-synthetic-fixture'),
                      ('source_sha256', inspection.source_sha256), ('source_file_id', inspection.source_file_id)))

    def analyze(name, shape, expected):
        path = output / (name + '.step'); cq.exporters.export(shape, str(path))
        inspection = _step_inspection(path)
        request = ManufacturingInterpretationRequest(inspection=inspection, material_evidence=grade(inspection),
                                                     requested_outputs=('STEP', 'IFC', 'PDF'))
        report = interpreter.analyze(request)
        observed = {f.semantic_type.value for f in report.features}
        check(name + ':feature_classes', observed == set(expected), {'expected': sorted(expected), 'observed': sorted(observed)})
        check(name + ':two_way_geometry', report.equivalence.status.value == 'PROVEN_BREP_EQUIVALENT'
              and report.equivalence.two_way and report.equivalence.independent_reconstruction,
              report.equivalence.status.value)
        if report.hypotheses:
            chosen = set(report.hypotheses[0].positive_feature_ids) | set(report.hypotheses[0].negative_feature_ids)
            check(name + ':selected_feature_proof', {f.feature_id for f in report.features} == chosen
                  and report.hypotheses[0].feature_graph_id == report.feature_graph.graph_id)
        observations.append({'name': name, 'source_sha256': inspection.source_sha256,
            'readiness': report.readiness.value, 'blockers': list(report.blockers),
            'features': sorted(observed), 'equivalence': report.equivalence.status.value})
        return request, report

    plate = cq.Workplane('XY').box(320, 120, 20).val()
    round_bar = cq.Workplane('YZ').circle(23).extrude(350).val()
    tube = cq.Workplane('YZ').circle(38).circle(30).extrude(350).val()
    hole_tool = cq.Workplane('XY').center(35, 0).circle(6).extrude(70, both=True).val()
    recess = cq.Workplane('XY').center(35, 0).circle(11).extrude(6).translate((0, 0, 4)).val()
    cb = plate.cut(hole_tool.fuse(recess))
    notch = plate.cut(cq.Workplane('XY').box(45, 42, 50).translate((-147.5, -49, 0)).val())
    miter = plate.cut(cq.Workplane('XY').box(120, 240, 120).rotate((0, 0, 0), (0, 1, 0), 29).translate((194, 0, 0)).val())
    boss = cq.Workplane('XY').box(56, 46, 28).translate((35, 0, 24)).val()
    combined = plate.fuse(boss).cut(hole_tool)
    slot = cq.Workplane('XY').box(320, 120, 20).faces('>Z').workplane().slot2D(53, 14).cutThruAll().val()
    fixtures = [('round-no-drill', round_bar, ()), ('tube-no-drill', tube, ()),
                ('stepped-bore', cb, ('COUNTERBORE',)), ('slot', slot, ('SLOT',)),
                ('cope-low', notch, ('NOTCH',)), ('end-cut', miter, ('END_CUT',)),
                ('boss-with-drill', combined, ('ATTACHMENT_VOLUME', 'HOLE'))]
    for name, shape, expected in fixtures:
        analyze(name, shape, expected)
        if name in {'stepped-bore', 'cope-low', 'end-cut', 'boss-with-drill'}:
            analyze(name + '-rotated', shape.rotate((0, 0, 0), (1, 1, 1), 31), expected)
    analyze('cope-high', notch.rotate((0, 0, 0), (0, 0, 1), 180), ('NOTCH',))
    # Positive acceptance uses a real catalog-sized rectangle and explicit grade.
    request, report = analyze('plain-known', cq.Workplane('XY').box(400, 50, 10).val(), ())
    check('positive_geometry_ready', report.readiness.value == 'READY', report.blockers)
    unconfirmed = interpreter.analyze(replace(request, material_evidence=None))
    check('missing_material_never_ready', unconfirmed.readiness.value != 'READY' and 'MATERIAL_EVIDENCE_UNRESOLVED' in unconfirmed.blockers)
    conflict = interpreter.analyze(replace(request, material_evidence=replace(request.material_evidence, grade='S235JR')))
    check('conflicting_material_never_ready', conflict.readiness.value != 'READY')
    # Revoke source authority without changing its hash: cached PASS must not leak.
    for key, value in [('production_geometry_exact', False), ('selection_verified', False),
                       ('geometry_kind', 'proxy'), ('native_shape', None)]:
        revoked = interpreter.analyze(replace(request, inspection=replace(request.inspection, **{key: value})))
        check('revoked_cached_source:' + key, revoked.readiness.value == 'BLOCKED')
    again = interpreter.analyze(request)
    check('valid_cache_still_works', again.interpretation_id == report.interpretation_id and again.readiness.value == 'READY')
    machine = interpreter.analyze(replace(request, requested_outputs=('NC1', 'MACHINE_ROUTE')))
    check('no_machine_release_from_geometry', machine.readiness.value != 'READY'
          and any('MACHINE_ROUTE' in value for value in machine.blockers), machine.blockers)
    cube = cq.Workplane('XY').box(100, 100, 100).val()
    cube_request, cube_report = analyze('ambiguous-axis', cube, ())
    check('cube_requires_axis_review', cube_report.readiness.value != 'READY' and 'MANUFACTURING_AXIS_AMBIGUOUS' in cube_report.blockers)
    duplicate = output / 'two-solids.step';cq.exporters.export(cq.Compound.makeCompound([plate, plate.translate((500, 0, 0))]), str(duplicate))
    try:
        _step_inspection(duplicate)
    except ValueError as exc:
        check('multi_solid_import_rejected', 'isolatie vereist' in str(exc), str(exc))
    else:
        check('multi_solid_import_rejected', False)
    frozen = bool(getattr(sys, 'frozen', False))
    binding_path = Path(sys.executable).parent / 'BUILD_SOURCE.json'
    binding = json.loads(binding_path.read_text(encoding='utf-8')) if frozen and binding_path.is_file() else {}
    source = binding.get('source_commit')
    if not frozen:
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True)
        source = result.stdout.strip()
    with Path(sys.executable).open('rb') as f:
        executable_hash = hashlib.file_digest(f, 'sha256').hexdigest()
    payload = {'schema': 'cws-native-recognition-integration-1', 'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
        'checks': checks, 'observations': observations, 'source_commit': source,
        'frozen': frozen, 'executable_sha256': executable_hash,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'synthetic exact-BREP feature and safety regressions, not supplier accuracy or machine qualification',
        'machine_transfer_allowed': False, 'full_product_release_approved': False}
    (output / 'RECOGNITION_INTEGRATION.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return payload
