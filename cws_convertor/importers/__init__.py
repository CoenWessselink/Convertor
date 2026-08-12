"""Import boundary for CWS Convertor.

Phase 0/1 contains only a source-fact regression scanner. The semantic IFC/STEP
project importer is built in the next phase on top of the Project Model 2.0.
"""
from .reference_scan import (
    IFCReferenceScan,
    ReferenceValidationResult,
    STEPReferenceScan,
    scan_ifc,
    scan_step,
    validate_ifc_reference,
    validate_step_reference,
)

__all__ = [
    "IFCReferenceScan",
    "STEPReferenceScan",
    "ReferenceValidationResult",
    "scan_ifc",
    "scan_step",
    "validate_ifc_reference",
    "validate_step_reference",
]
