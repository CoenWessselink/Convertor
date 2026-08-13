"""Canonical project and production-preparation API for CWS Convertor.

Project Model 2.x supports deterministic source intake, semantic IFC/STEP
materialisation and the portable ``.cwscproj`` package.  Semantic import does
not bypass feature-level production validation.
"""
from .model import (
    Assembly,
    AuditEvent,
    EntityCategory,
    Fastener,
    FieldProvenance,
    ImportStrategy,
    MachineJob,
    MachineProfile,
    Part,
    ProductionOperation,
    ProjectModel,
    ProjectValidationError,
    PurchasedItem,
    Remnant,
    ReviewStatus,
    SourceFileRecord,
    SourceIdentity,
    StockItem,
    Transform3D,
    ValidationIssue,
    Weld,
)
from .storage import ProjectPackage, ProjectPackageError, ProjectStore
from .jobs import JobCancelled, JobContext, JobManager, JobRecord
from .baseline import (
    BaselineAnalysis,
    BaselineInspectionError,
    inspect_model_file,
    write_baseline_report,
)
from .service import (
    ProjectService,
    ProjectSession,
    SemanticImportResult,
    SourceRegistrationResult,
)
from .workbench import (
    WORKBENCH_SCHEMA_VERSION,
    evaluate_workbench_revision,
    workbench_geometry_payload,
)
from .source_geometry import (
    SOURCE_INSPECTION_SCHEMA_VERSION,
    SOURCE_LOCATOR_SCHEMA_VERSION,
    SourceGeometryError,
    SourceGeometryInspection,
    inspect_part_source_geometry,
    source_locator_for_part,
)

__all__ = [
    "ProjectModel",
    "ProjectValidationError",
    "Assembly",
    "Part",
    "PurchasedItem",
    "Fastener",
    "Weld",
    "StockItem",
    "Remnant",
    "ProductionOperation",
    "MachineProfile",
    "MachineJob",
    "SourceFileRecord",
    "SourceIdentity",
    "Transform3D",
    "FieldProvenance",
    "ImportStrategy",
    "ValidationIssue",
    "AuditEvent",
    "EntityCategory",
    "ReviewStatus",
    "ProjectPackage",
    "ProjectPackageError",
    "ProjectStore",
    "JobCancelled",
    "JobContext",
    "JobManager",
    "JobRecord",
    "BaselineAnalysis",
    "BaselineInspectionError",
    "inspect_model_file",
    "write_baseline_report",
    "ProjectService",
    "ProjectSession",
    "SourceRegistrationResult",
    "SemanticImportResult",
    "WORKBENCH_SCHEMA_VERSION",
    "evaluate_workbench_revision",
    "workbench_geometry_payload",
    "SOURCE_INSPECTION_SCHEMA_VERSION",
    "SOURCE_LOCATOR_SCHEMA_VERSION",
    "SourceGeometryError",
    "SourceGeometryInspection",
    "inspect_part_source_geometry",
    "source_locator_for_part",
]
