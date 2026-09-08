"""Manufacturing Geometry Interpreter.

This package derives immutable manufacturing evidence from the existing source
geometry authority.  It does not mutate Project Model, SteelModel or Part
Workbench state and it never promotes approximate mesh evidence to production
truth.
"""

from .contracts import (
    GeometryProofStatus,
    InterpretationReadiness,
    MaterialEvidence,
    MaterialEvidenceStatus,
    ManufacturingInterpretationReport,
    ManufacturingInterpretationRequest,
)
from .project_link import ProjectPartSourceLinkError, build_project_part_request


def __getattr__(name: str):
    if name == "ManufacturingGeometryInterpreter":
        from .pipeline import ManufacturingGeometryInterpreter
        return ManufacturingGeometryInterpreter
    raise AttributeError(name)

__all__ = [
    "GeometryProofStatus",
    "InterpretationReadiness",
    "ManufacturingGeometryInterpreter",
    "ManufacturingInterpretationReport",
    "ManufacturingInterpretationRequest",
    "MaterialEvidence",
    "MaterialEvidenceStatus",
    "ProjectPartSourceLinkError",
    "build_project_part_request",
]
