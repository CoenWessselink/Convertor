from __future__ import annotations

import hashlib

import cadquery as cq

from cws_convertor.manufacturing_interpreter import (
    GeometryProofStatus,
    InterpretationReadiness,
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.project.source_geometry import SourceGeometryInspection
from profile_database import ProfileDefinition


class FixtureProfiles:
    def __init__(self, profiles):
        self.profiles = tuple(profiles)


def inspection(shape, name: str, *, exact: bool = True):
    digest = hashlib.sha256(name.encode("ascii")).hexdigest()
    return SourceGeometryInspection(
        part_id=name,
        source_file_id=f"{name}.step",
        source_sha256=digest,
        source_geometry_hash=digest,
        status="exact" if exact else "approximate",
        scope="single_part",
        geometry_kind="native_brep" if exact else "mesh",
        selection_verified=True,
        production_geometry_exact=exact,
        native_shape=shape if exact else None,
    )


def main() -> int:
    shape = cq.Workplane("XY").rect(100.0, 10.0).extrude(1000.0).val()
    profiles = FixtureProfiles([
        ProfileDefinition("PL100X10", "B", "B", 100.0, 10.0, area_mm2=1000.0)
    ])
    service = ManufacturingGeometryInterpreter(profile_database=profiles)
    request = ManufacturingInterpretationRequest(inspection=inspection(shape, "plate"))
    first = service.analyze(request)
    second = service.analyze(request)
    assert first.readiness == InterpretationReadiness.REVIEW_REQUIRED, first.to_dict()
    assert "TARGET_REVIEW_REQUIRED:NC1" in first.blockers
    assert first.equivalence.status == GeometryProofStatus.PROVEN_BREP_EQUIVALENT
    assert first.profile.designation == "PL100X10"
    assert first.semantic_sha256 == second.semantic_sha256
    assert service.final_cache_hits == 1

    rotated = cq.Workplane(obj=shape).rotate((0, 0, 0), (0, 1, 0), 31).val()
    rotated_report = service.analyze(
        ManufacturingInterpretationRequest(inspection=inspection(rotated, "rotated"))
    )
    assert rotated_report.equivalence.status == GeometryProofStatus.PROVEN_BREP_EQUIVALENT
    assert rotated_report.profile.designation == "PL100X10"

    approximate = service.analyze(
        ManufacturingInterpretationRequest(inspection=inspection(None, "ifc-mesh", exact=False))
    )
    assert approximate.source_gate == GeometryProofStatus.BLOCKED_SOURCE_NOT_EXACT
    assert approximate.readiness == InterpretationReadiness.BLOCKED

    almost = cq.Workplane("XY").rect(100.3, 10.0).extrude(1000.0).val()
    almost_report = service.analyze(
        ManufacturingInterpretationRequest(inspection=inspection(almost, "almost"))
    )
    assert almost_report.profile.status == GeometryProofStatus.RECOGNITION_INCOMPLETE
    assert almost_report.readiness != InterpretationReadiness.READY
    print("MGI_PHASE1_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
