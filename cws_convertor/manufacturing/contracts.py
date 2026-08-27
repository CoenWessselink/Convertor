"""Single public contract facade for phase-3 manufacturing consumers."""
from __future__ import annotations

from cws_convertor.project.manufacturing_contracts import ExportScope, ProductionInstanceIdentity
from cws_convertor.optimization.profile_nesting.models import PieceInstance

from .contact_model import ContactPatch
from .faces_model import FaceLocalFrame, ManufacturingFace
from .machine_capability_model import MachineCapabilityReport as MachineCapability
from .marking_model import MarkFeature as ManufacturingMark
from .marking_model import MarkSegment2D as MarkGeometry2D
from .marking_model import MarkingRuleSet as ManufacturingRuleSet
from .neutral_job_model import NeutralManufacturingJob
from .neutral_job_model import NeutralOperation as ManufacturingSequenceOperation


__all__ = [
    "ContactPatch",
    "ExportScope",
    "FaceLocalFrame",
    "MachineCapability",
    "ManufacturingFace",
    "ManufacturingMark",
    "ManufacturingRuleSet",
    "ManufacturingSequenceOperation",
    "MarkGeometry2D",
    "NeutralManufacturingJob",
    "PieceInstance",
    "ProductionInstanceIdentity",
]
