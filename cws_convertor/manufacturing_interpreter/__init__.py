"""Manufacturing Geometry Interpreter.

This package derives immutable manufacturing evidence from the existing source
geometry authority.  It does not mutate Project Model, SteelModel or Part
Workbench state and it never promotes approximate mesh evidence to production
truth.
"""

from .contracts import (
    GeometryProofStatus,
    InterpretationReadiness,
    ManufacturingInterpretationReport,
    ManufacturingInterpretationRequest,
)
from .service import ManufacturingGeometryInterpreter

__all__ = [
    "GeometryProofStatus",
    "InterpretationReadiness",
    "ManufacturingGeometryInterpreter",
    "ManufacturingInterpretationReport",
    "ManufacturingInterpretationRequest",
]

