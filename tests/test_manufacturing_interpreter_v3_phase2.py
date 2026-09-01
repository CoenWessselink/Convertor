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


if __name__ == "__main__":
    test_phase2_compound_hole_reconstruction_and_representability()
    test_phase2_promotion_is_confirmation_gated()
    print("PASS: MGI V3 phase 2 feature reconstruction")
