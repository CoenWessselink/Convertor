from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import cadquery as cq

from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.contracts import (
    GeometryProofStatus,
    ManufacturingSemanticType,
)
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator


def _inspection(shape: object, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        part_id=name,
        source_file_id=f"{name}.step",
        source_sha256=f"sha-{name}",
        source_geometry_hash=f"geometry-{name}",
        status="exact",
        scope="single_part",
        geometry_kind="native_brep",
        selection_verified=True,
        production_geometry_exact=True,
        native_shape=shape,
    )


def test_phase2_compound_hole_reconstruction_and_representability() -> None:
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-phase2-") as cache_root:
        plate = cq.Workplane("XY").box(240.0, 100.0, 16.0)
        shape = plate.faces(">Z").workplane().pushPoints([(-70.0, 0.0), (0.0, 0.0), (70.0, 0.0)]).hole(24.0).val()
        report = ManufacturingGeometryInterpreter(cache_root=Path(cache_root)).analyze(
            ManufacturingInterpretationRequest(
                inspection=_inspection(shape, "plate-with-hole"),
                requested_outputs=("STEP", "IFC", "NC1", "PDF"),
            )
        )
        assert report.feature_graph is not None
        assert report.feature_graph.duplicate_attribution_count == 0
        assert report.features
        assert sum(feature.semantic_type == ManufacturingSemanticType.HOLE for feature in report.features) == 3
        assert report.hypotheses
        assert len(report.hypotheses) <= 64
        assert report.hypotheses[0].proof_status in {
            GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
            GeometryProofStatus.PROVEN_WITHIN_POLICY,
        }
        assert report.representability_report is not None
        assert {target.target for target in report.representability_report.targets} == {"STEP", "IFC", "NC1", "PDF"}


def test_phase2_promotion_is_confirmation_gated() -> None:
    report = SimpleNamespace(readiness=SimpleNamespace(value="BLOCKED"))
    from cws_convertor.manufacturing_interpreter.contracts import InterpretationReadiness

    report.readiness = InterpretationReadiness.BLOCKED
    result = WorkbenchPromotionCoordinator().promote(
        report=report,
        confirmation=None,
        project=None,
        user="test",
    )
    assert result.status == "BLOCKED"
    assert "INTERPRETATION_NOT_READY" in result.blockers


def _report(shape: object, name: str):
    with tempfile.TemporaryDirectory(prefix=f"cws-mgi-v3-{name}-") as cache_root:
        return ManufacturingGeometryInterpreter(cache_root=Path(cache_root)).analyze(
            ManufacturingInterpretationRequest(
                inspection=_inspection(shape, name),
                requested_outputs=("STEP", "IFC", "NC1", "PDF"),
            )
        )


def test_phase2_slot_counterbore_prism_and_multi_extrusion() -> None:
    slot = (
        cq.Workplane("XY")
        .box(220.0, 100.0, 18.0)
        .faces(">Z")
        .workplane()
        .slot2D(56.0, 18.0)
        .cutThruAll()
        .val()
    )
    slot_report = _report(slot, "slot")
    assert any(feature.semantic_type.value == "SLOT" for feature in slot_report.features)
    assert slot_report.hypotheses[0].proof_status in {
        GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
        GeometryProofStatus.PROVEN_WITHIN_POLICY,
    }

    counterbore = (
        cq.Workplane("XY")
        .box(200.0, 90.0, 20.0)
        .faces(">Z")
        .workplane()
        .hole(18.0, depth=20.0)
        .faces(">Z")
        .workplane()
        .hole(34.0, depth=5.0)
        .val()
    )
    counterbore_report = _report(counterbore, "counterbore")
    assert any(feature.semantic_type.value == "COUNTERBORE" for feature in counterbore_report.features)
    assert counterbore_report.hypotheses[0].proof_status in {
        GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
        GeometryProofStatus.PROVEN_WITHIN_POLICY,
    }

    base = cq.Workplane("XY").box(220.0, 70.0, 20.0).val()
    notch_tool = cq.Workplane("XY").box(35.0, 30.0, 12.0).translate((92.5, 0.0, 4.0)).val()
    notch_report = _report(base.cut(notch_tool), "notch")
    assert any(feature.geometric_type.value == "PRISMATIC_SUBTRACTION" for feature in notch_report.features)
    assert notch_report.hypotheses[0].proof_status in {
        GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
        GeometryProofStatus.PROVEN_WITHIN_POLICY,
    }

    crossing = cq.Workplane("XY").box(45.0, 130.0, 20.0).val()
    multi_report = _report(base.fuse(crossing), "multi-extrusion")
    assert sum(feature.geometric_type.value == "POSITIVE_PRISM" for feature in multi_report.features) >= 1
    assert multi_report.hypotheses[0].proof_status in {
        GeometryProofStatus.PROVEN_BREP_EQUIVALENT,
        GeometryProofStatus.PROVEN_WITHIN_POLICY,
    }


if __name__ == "__main__":
    test_phase2_compound_hole_reconstruction_and_representability()
    test_phase2_promotion_is_confirmation_gated()
    test_phase2_slot_counterbore_prism_and_multi_extrusion()
    print("PASS: MGI V3 phase 2 feature reconstruction")
