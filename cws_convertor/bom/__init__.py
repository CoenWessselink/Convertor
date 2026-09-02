"""Deterministic classification, BOM and procurement exports.

The public functions are intentionally lazy to avoid a circular import between
``cws_convertor.project.service`` and the BOM engine.
"""
from .models import (
    AssemblyBOMRow,
    BOMConflict,
    BOMSnapshot,
    BOMValidation,
    FastenerBOMRow,
    MaterialBOMRow,
    PartBOMRow,
    PurchaseBOMRow,
    WeldBOMRow,
)
from .production_hub import (
    ACTION_DEFINITIONS,
    BOMActionDefinition,
    BOMActionMatrix,
    BOMBatchPreflight,
    BOMBatchResult,
    BOMHubState,
    BOMProcurementService,
    BOMQueryClause,
    BOMRevisionDelta,
    BOMSavedSelection,
    BOMScopeEngine,
    BOMSelectionImpact,
    BOMSmartQuery,
    BOMStockAllocator,
    BOMStockSourceOption,
    BOMTransactionExecution,
    QUERY_FIELDS,
    QUERY_OPERATORS,
)


def build_bom_snapshot(*args, **kwargs):
    from .engine import build_bom_snapshot as implementation
    return implementation(*args, **kwargs)


def export_bom_package(*args, **kwargs):
    from .export import export_bom_package as implementation
    return implementation(*args, **kwargs)


def safe_spreadsheet_value(*args, **kwargs):
    from .export import safe_spreadsheet_value as implementation
    return implementation(*args, **kwargs)


__all__ = [
    "AssemblyBOMRow", "BOMConflict", "BOMSnapshot", "BOMValidation",
    "FastenerBOMRow", "MaterialBOMRow", "PartBOMRow", "PurchaseBOMRow",
    "WeldBOMRow", "build_bom_snapshot", "export_bom_package",
    "safe_spreadsheet_value",
    "ACTION_DEFINITIONS", "BOMActionDefinition", "BOMActionMatrix",
    "BOMBatchPreflight", "BOMBatchResult", "BOMHubState", "BOMProcurementService", "BOMQueryClause",
    "BOMRevisionDelta", "BOMSavedSelection", "BOMScopeEngine",
    "BOMSelectionImpact", "BOMSmartQuery", "BOMStockAllocator",
    "BOMStockSourceOption", "BOMTransactionExecution",
    "QUERY_FIELDS", "QUERY_OPERATORS",
]
