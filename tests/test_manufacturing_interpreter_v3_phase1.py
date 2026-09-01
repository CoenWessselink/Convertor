from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import cadquery as cq

from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.contracts import ENGINE_VERSION


def _inspection(shape: object, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        part_id=name,
        source_file_id=f"source-{name}",
        source_sha256=f"sha-{name}",
        source_geometry_hash=f"geometry-{name}",
        production_geometry_exact=True,
        selection_verified=True,
        native_shape=shape,
        geometry_kind="native_brep",
    )


def test_phase1_foundation_is_deterministic_and_complete() -> None:
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-phase1-") as cache_root:
        shape = cq.Workplane("XY").box(120.0, 40.0, 12.0).val()
        service = ManufacturingGeometryInterpreter(cache_root=Path(cache_root))
        request = ManufacturingInterpretationRequest(inspection=_inspection(shape, "plate"))

        first = service.analyze(request)
        second = service.analyze(request)

        assert first.engine_version == ENGINE_VERSION == "mgi-v3"
        assert first.manufacturing_frame is not None
        assert first.topology is not None and first.topology.analytic_groups
        assert len(first.section_stations) >= 1
        assert first.tolerance_policy_hash
        assert first.profile_database_hash
        assert first.evidence == second.evidence
        assert service.persistent_cache_hits >= 1


def test_phase1_source_gate_remains_fail_closed() -> None:
    with tempfile.TemporaryDirectory(prefix="cws-mgi-v3-source-gate-") as cache_root:
        inspection = _inspection(None, "mesh")
        inspection.production_geometry_exact = False
        inspection.geometry_kind = "MESH"
        report = ManufacturingGeometryInterpreter(cache_root=Path(cache_root)).analyze(
            ManufacturingInterpretationRequest(inspection=inspection)
        )
        assert report.readiness.value == "BLOCKED"
        assert report.manufacturing_frame is None
        assert report.tolerance_policy_hash


if __name__ == "__main__":
    test_phase1_foundation_is_deterministic_and_complete()
    test_phase1_source_gate_remains_fail_closed()
    print("PASS: MGI V3 phase 1 foundation")
