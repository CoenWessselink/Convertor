"""Deterministic, fail-closed 2D plate nesting for manufacturing planning."""

from .core import (
    PlateLayout,
    PlateNestingPlan,
    PlateNestingValidation,
    PlatePart,
    PlatePlacement,
    StockPlate,
    solve_plate_nesting,
    validate_plate_nesting,
)
from .canonical import (
    PlateCutPlan, PlateGeometryRef, PlateNestDemand, PlateNestRun, PlateOrientationVariant,
    PlatePurchaseOption, PlateRemnant, PlateSolverEvidence, PlateStock, PlateValidationReport,
    solve_canonical_plate_nesting, validate_canonical_plate_nesting,
)

__all__ = [
    "PlateLayout",
    "PlateNestingPlan",
    "PlateNestingValidation",
    "PlatePart",
    "PlatePlacement",
    "StockPlate",
    "solve_plate_nesting",
    "validate_plate_nesting",
    "PlateCutPlan", "PlateGeometryRef", "PlateNestDemand", "PlateNestRun", "PlateOrientationVariant",
    "PlatePurchaseOption", "PlateRemnant", "PlateSolverEvidence", "PlateStock", "PlateValidationReport",
    "solve_canonical_plate_nesting", "validate_canonical_plate_nesting",
]
