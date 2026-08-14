"""CWS Convertor V9 viewer/main-build integration services.

The package deliberately contains no GUI toolkit objects.  It is the single
application boundary through which the Qt shell, CLI validation and automated
tests obtain one canonical project, one viewer scene, one property grid and one
BOM snapshot.
"""
from .selftest import (
    IntegrationCheck,
    IntegrationSelfTestReport,
    create_synthetic_integration_project,
    run_integration_self_test,
)
from .selection import (
    ApplicationSelection,
    ApplicationSelectionBus,
    BomSelectionIndex,
    BomSelectionRecord,
    PdfFeatureHighlightBridge,
)
from .workspace import (
    ExactPartOpenResult,
    IdentityAuditReport,
    IntegratedProjectWorkspace,
    WorkspaceLoadReport,
)

__all__ = [
    "ApplicationSelection",
    "ApplicationSelectionBus",
    "BomSelectionIndex",
    "BomSelectionRecord",
    "ExactPartOpenResult",
    "IdentityAuditReport",
    "IntegrationCheck",
    "IntegrationSelfTestReport",
    "IntegratedProjectWorkspace",
    "PdfFeatureHighlightBridge",
    "create_synthetic_integration_project",
    "run_integration_self_test",
    "WorkspaceLoadReport",
]
