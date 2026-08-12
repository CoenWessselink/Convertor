"""Canonical project and production-preparation foundation for CWS Convertor.

The package intentionally exposes only the verified v0.6 project API.  The
semantic IFC/STEP importer is a later phase; source registration in this phase
records deterministic evidence and blocks production export until that import
has completed.
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
from .service import ProjectService, ProjectSession, SourceRegistrationResult

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
]
