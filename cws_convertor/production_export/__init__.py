"""Safe per-part and per-assembly production package export.

The deterministic readiness and manifest layers remain importable in audit or
server environments without the optional native CAD runtime.  The heavy
release engine is loaded only when it is actually requested.
"""
from .engine import ExportRequest, ProductionExportEngine, SUPPORTED_FORMATS
from .models import (
    ArtifactResult,
    ArtifactStatus,
    AssemblyPackageResult,
    ExportItemResult,
    ExportManifest,
    ExportStatus,
    GateMessage,
)
from .readiness import ReadinessAssessment, ReadinessGate
from .project_loader import LoadedProject, ProjectLoadError, load_project_snapshot
from .verify import ExportVerificationError, verify_export_directory, verify_export_zip

CORE_FORMATS = ("nc1", "step", "ifc", "production_pdf")
RELEASE_FORMATS = (
    "nc1", "step", "ifc", "production_pdf", "dxf", "csv",
    "label_pdf", "preview_png", "json",
)


def __getattr__(name: str):
    if name == "ProjectProductionExportEngine":
        from .release import ProjectProductionExportEngine

        globals()[name] = ProjectProductionExportEngine
        return ProjectProductionExportEngine
    raise AttributeError(name)

__all__ = [
    "ArtifactResult", "ArtifactStatus", "AssemblyPackageResult",
    "ExportItemResult", "ExportManifest", "ExportRequest", "ExportStatus",
    "ExportVerificationError", "GateMessage", "ReadinessAssessment",
    "LoadedProject", "ProductionExportEngine", "ProjectLoadError",
    "ReadinessGate", "SUPPORTED_FORMATS",
    "load_project_snapshot",
    "CORE_FORMATS", "RELEASE_FORMATS", "ProjectProductionExportEngine",
    "verify_export_directory", "verify_export_zip",
]
