"""Canonical twelve-scope manufacturing export matrix."""
from __future__ import annotations

from dataclasses import dataclass

from cws_convertor.project.manufacturing_contracts import ExportScopeKind


@dataclass(frozen=True)
class ExportScopePolicy:
    backend_kind: str
    value_source: str
    requires_values: bool
    recursive_allowed: bool = False
    requires_explicit_full_project: bool = False
    fail_closed: bool = True


EXPORT_SCOPE_MATRIX: dict[ExportScopeKind, ExportScopePolicy] = {
    ExportScopeKind.SELECTION: ExportScopePolicy("current_selection", "selection", False),
    ExportScopeKind.SELECTED_PARTS: ExportScopePolicy("entity_ids", "entity_ids", True),
    ExportScopeKind.PART_MARK: ExportScopePolicy("part_positions", "part_marks", True),
    ExportScopeKind.ASSEMBLY: ExportScopePolicy("entity_ids", "assembly_ids", True, True),
    ExportScopeKind.ASSEMBLY_MARK: ExportScopePolicy("assembly_marks", "assembly_marks", True, True),
    ExportScopeKind.PHASE: ExportScopePolicy("project_phase", "phase_ids", True),
    ExportScopeKind.BATCH: ExportScopePolicy("batch", "batch_ids", True),
    ExportScopeKind.NESTING_RUN: ExportScopePolicy("nesting_run", "nesting_run_ids", True),
    ExportScopeKind.NESTING_BAR: ExportScopePolicy("nesting_bar", "nesting_bar_ids", True),
    ExportScopeKind.MACHINE_BATCH: ExportScopePolicy("entity_ids", "machine_batch_ids", True),
    ExportScopeKind.REVISION_DELTA: ExportScopePolicy("revision_delta", "entity_ids", True),
    ExportScopeKind.FULL_PROJECT: ExportScopePolicy("full_project", "explicit_confirmation", False, False, True),
}


def export_scope_policy(kind: ExportScopeKind | str) -> ExportScopePolicy:
    return EXPORT_SCOPE_MATRIX[ExportScopeKind(kind)]


def validate_export_scope_matrix() -> tuple[str, ...]:
    expected = set(ExportScopeKind)
    actual = set(EXPORT_SCOPE_MATRIX)
    issues: list[str] = []
    if actual != expected:
        issues.append("CWS.EXPORT.SCOPE_MATRIX_INCOMPLETE")
    if any(not policy.fail_closed for policy in EXPORT_SCOPE_MATRIX.values()):
        issues.append("CWS.EXPORT.SCOPE_NOT_FAIL_CLOSED")
    if not EXPORT_SCOPE_MATRIX[ExportScopeKind.FULL_PROJECT].requires_explicit_full_project:
        issues.append("CWS.EXPORT.FULL_PROJECT_NOT_EXPLICIT")
    return tuple(issues)


__all__ = ["EXPORT_SCOPE_MATRIX", "ExportScopePolicy", "export_scope_policy", "validate_export_scope_matrix"]
