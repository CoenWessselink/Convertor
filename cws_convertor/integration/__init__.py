"""CWS Convertor unified viewer/main-build integration services.

The package deliberately contains no GUI toolkit objects. It is the single
application boundary through which the Qt shell, CLI validation and automated
tests obtain one canonical project, one viewer scene, one property grid, one
BOM snapshot, one application-wide project/selection context and the U4
production-workflow snapshot.
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
    PRODUCTION_FORMATS,
    REVIEW_FORMATS,
    U4_SAFETY_FLAGS,
    U4_WORKFLOW_SCHEMA,
    ProductionPartStatus,
    ProductionWorkflowSnapshot,
    build_production_workflow_snapshot,
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
    "PRODUCTION_FORMATS",
    "PdfFeatureHighlightBridge",
    "ProductionPartStatus",
    "ProductionWorkflowSnapshot",
    "REVIEW_FORMATS",
    "U3_CONTEXT_SCHEMA",
    "U3_SAFETY_FLAGS",
    "U4_SAFETY_FLAGS",
    "U4_WORKFLOW_SCHEMA",
    "UnifiedApplicationContext",
    "UnifiedUiContextSnapshot",
    "WorkspaceLoadReport",
    "build_production_workflow_snapshot",
    "create_synthetic_integration_project",
    "run_integration_self_test",
]
