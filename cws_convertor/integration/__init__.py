"""CWS Convertor unified viewer/main-build integration services.

The package deliberately contains no GUI toolkit objects.  It is the single
application boundary through which the Qt shell, CLI validation and automated
tests obtain one canonical project, one viewer scene, one property grid, one
BOM snapshot, one application-wide project/selection context and — from U4 —
one production workflow coordinator over the existing release engine.
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
from .ui_context import (
    U3_CONTEXT_SCHEMA,
    U3_SAFETY_FLAGS,
    UnifiedApplicationContext,
    UnifiedUiContextSnapshot,
)
from .production_workflow import (
    DEFAULT_WORKFLOW_FORMATS,
    ProductionPartReadiness,
    ProductionWorkflowCoordinator,
    ProductionWorkflowPlan,
    ProductionWorkflowReceipt,
    U4_RECEIPT_SCHEMA,
    U4_SAFETY_FLAGS,
    U4_WORKFLOW_SCHEMA,
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
    "DEFAULT_WORKFLOW_FORMATS",
    "ExactPartOpenResult",
    "IdentityAuditReport",
    "IntegrationCheck",
    "IntegrationSelfTestReport",
    "IntegratedProjectWorkspace",
    "PdfFeatureHighlightBridge",
    "ProductionPartReadiness",
    "ProductionWorkflowCoordinator",
    "ProductionWorkflowPlan",
    "ProductionWorkflowReceipt",
    "U3_CONTEXT_SCHEMA",
    "U3_SAFETY_FLAGS",
    "U4_RECEIPT_SCHEMA",
    "U4_SAFETY_FLAGS",
    "U4_WORKFLOW_SCHEMA",
    "UnifiedApplicationContext",
    "UnifiedUiContextSnapshot",
    "WorkspaceLoadReport",
    "create_synthetic_integration_project",
    "run_integration_self_test",
]
