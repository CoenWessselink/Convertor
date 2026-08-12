"""Import boundary for CWS Convertor.

The lightweight reference scanners are imported eagerly.  Semantic importers
are loaded lazily to avoid a package-initialisation cycle between
``cws_convertor.importers`` and ``cws_convertor.project``.  GUI, CLI and tests
can still import the public names from this package.
"""
from __future__ import annotations

from typing import Any

from .reference_scan import (
    IFCReferenceScan,
    ReferenceValidationResult,
    STEPReferenceScan,
    scan_ifc,
    scan_step,
    validate_ifc_reference,
    validate_step_reference,
)

_LAZY_EXPORTS = {
    "SemanticCancelCheck": (".semantic", "SemanticCancelCheck"),
    "SemanticImportResult": (".semantic", "SemanticImportResult"),
    "SemanticProjectImporter": (".semantic", "SemanticProjectImporter"),
    "IFCSemanticProjectImporter": (".ifc_project", "IFCSemanticProjectImporter"),
    "STEPSemanticProjectImporter": (".step_project", "STEPSemanticProjectImporter"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    from importlib import import_module

    module = import_module(target[0], __name__)
    value = getattr(module, target[1])
    globals()[name] = value
    return value


__all__ = [
    "IFCReferenceScan",
    "STEPReferenceScan",
    "ReferenceValidationResult",
    "scan_ifc",
    "scan_step",
    "validate_ifc_reference",
    "validate_step_reference",
    *_LAZY_EXPORTS,
]
