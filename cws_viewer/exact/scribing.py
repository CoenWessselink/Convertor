"""Deterministic contact-line proposals for production scribing review.

Scribing is deliberately separate from cutting geometry.  Proposals are
computed from intersections of two exact BREP shapes, never from a display
mesh.  Confirming a proposal changes review state only; it does not modify the
target or partner solid and cannot release machine output.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import datetime as dt
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cws_viewer.math3d import Vector3

from .model import ExactnessLevel, ExactPartRuntime


class ScribeOperation(StrEnum):
    SCRIBE = "scribe"
    MARK = "mark"


class ScribeStatus(StrEnum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ScribeProposal:
    proposal_id: str
    target_part_id: str
    partner_part_id: str
    operation: ScribeOperation
    geometry_type: str
    start: Vector3
    end: Vector3
    center: Vector3
    length_mm: float
    evidence: ExactnessLevel
    confidence: float = 1.0
    status: ScribeStatus = ScribeStatus.PROPOSED
    reviewer: str = ""
    review_reason: str = ""
    reviewed_at: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", ScribeOperation(self.operation))
        object.__setattr__(self, "evidence", ExactnessLevel(self.evidence))
        object.__setattr__(self, "status", ScribeStatus(self.status))
        if self.operation not in {ScribeOperation.SCRIBE, ScribeOperation.MARK}:
            raise ValueError("Scribe proposal mag geen snijbewerking zijn")
        if self.length_mm <= 0:
            raise ValueError("Scribe-lijnlengte moet positief zijn")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("Scribe confidence moet tussen 0 en 1 liggen")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "target_part_id": self.target_part_id,
            "partner_part_id": self.partner_part_id,
            "operation": self.operation.value,
            "geometry_type": self.geometry_type,
            "start": self.start.to_tuple(),
            "end": self.end.to_tuple(),
            "center": self.center.to_tuple(),
            "length_mm": self.length_mm,
            "evidence": self.evidence.value,
            "confidence": self.confidence,
            "status": self.status.value,
            "reviewer": self.reviewer,
            "review_reason": self.review_reason,
            "reviewed_at": self.reviewed_at,
        }


@dataclass(frozen=True, slots=True)
class ScribeAuditEntry:
    timestamp: str
    action: str
    proposal_id: str
    user: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "proposal_id": self.proposal_id,
            "user": self.user,
            "reason": self.reason,
        }


@dataclass(slots=True)
class ScribeProposalRuntime:
    proposal: ScribeProposal
    edge_shape: Any


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _vector(vertex: Any) -> Vector3:
    center = vertex.Center()
    return Vector3(float(center.x), float(center.y), float(center.z))


def _ordered_endpoints(edge: Any) -> tuple[Vector3, Vector3]:
    vertices = list(edge.Vertices())
    if len(vertices) < 2:
        center = edge.Center()
        point = Vector3(float(center.x), float(center.y), float(center.z))
        return point, point
    values = [_vector(item) for item in vertices[:2]]
    values.sort(key=lambda item: tuple(round(value, 9) for value in item.to_tuple()))
    return values[0], values[1]


def _proposal_id(
    target: ExactPartRuntime,
    partner: ExactPartRuntime,
    geometry_type: str,
    start: Vector3,
    end: Vector3,
    length_mm: float,
) -> str:
    payload = {
        "schema": "cws-scribe-proposal-v1",
        "target_geometry_hash": target.snapshot.exact_geometry_hash,
        "partner_geometry_hash": partner.snapshot.exact_geometry_hash,
        "geometry_type": geometry_type,
        "start": [round(value, 8) for value in start.to_tuple()],
        "end": [round(value, 8) for value in end.to_tuple()],
        "length_mm": round(float(length_mm), 8),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    return f"scribe-{digest}"


def propose_contact_lines(
    target: ExactPartRuntime,
    partner: ExactPartRuntime,
    *,
    operation: ScribeOperation = ScribeOperation.SCRIBE,
    minimum_length_mm: float = 0.01,
) -> tuple[ScribeProposalRuntime, ...]:
    """Return exact contact-line proposals from the BREP section operation.

    Multi-solid inputs remain blocked because a proposed contact line cannot be
    assigned to an unconfirmed manufacturing part safely.
    """

    if target.snapshot.properties.solid_count != 1:
        raise ValueError("CWS-SCRIBE-TARGET-AMBIGUOUS-MULTI-SOLID")
    if partner.snapshot.properties.solid_count != 1:
        raise ValueError("CWS-SCRIBE-PARTNER-AMBIGUOUS-MULTI-SOLID")
    if minimum_length_mm <= 0:
        raise ValueError("Minimum scribe-lijnlengte moet positief zijn")

    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS
    import cadquery as cq

    section = BRepAlgoAPI_Section(target.shape.wrapped, partner.shape.wrapped, False)
    section.Approximation(False)
    section.Build()
    if not section.IsDone() or section.Shape().IsNull():
        return ()

    unique: dict[str, ScribeProposalRuntime] = {}
    explorer = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
    while explorer.More():
        edge = cq.Edge(TopoDS.Edge_s(explorer.Current()))
        length = float(edge.Length())
        if length >= float(minimum_length_mm):
            start, end = _ordered_endpoints(edge)
            center_raw = edge.Center()
            center = Vector3(float(center_raw.x), float(center_raw.y), float(center_raw.z))
            geometry_type = str(edge.geomType()).upper()
            stable_id = _proposal_id(target, partner, geometry_type, start, end, length)
            proposal = ScribeProposal(
                proposal_id=stable_id,
                target_part_id=target.snapshot.part_id,
                partner_part_id=partner.snapshot.part_id,
                operation=operation,
                geometry_type=geometry_type,
                start=start,
                end=end,
                center=center,
                length_mm=length,
                evidence=ExactnessLevel.SOURCE_BREP,
                confidence=1.0,
            )
            unique[stable_id] = ScribeProposalRuntime(proposal, edge)
        explorer.Next()

    return tuple(
        unique[key]
        for key in sorted(
            unique,
            key=lambda item: (
                round(unique[item].proposal.center.z, 8),
                round(unique[item].proposal.center.y, 8),
                round(unique[item].proposal.center.x, 8),
                item,
            ),
        )
    )


class ScribingReviewService:
    def __init__(
        self,
        target: ExactPartRuntime,
        partner: ExactPartRuntime,
        proposals: tuple[ScribeProposalRuntime, ...] | None = None,
    ) -> None:
        self.target = target
        self.partner = partner
        values = proposals if proposals is not None else propose_contact_lines(target, partner)
        self._runtime_by_id = {item.proposal.proposal_id: item for item in values}
        self.audit: list[ScribeAuditEntry] = []
        self._target_hash = target.snapshot.exact_geometry_hash
        self._partner_hash = partner.snapshot.exact_geometry_hash

    @property
    def proposals(self) -> tuple[ScribeProposal, ...]:
        return tuple(self._runtime_by_id[key].proposal for key in sorted(self._runtime_by_id))

    @property
    def confirmed(self) -> tuple[ScribeProposal, ...]:
        return tuple(item for item in self.proposals if item.status == ScribeStatus.CONFIRMED)

    def edge_shape(self, proposal_id: str) -> Any:
        return self._runtime_by_id[proposal_id].edge_shape

    def _review(self, proposal_id: str, status: ScribeStatus, *, user: str, reason: str) -> None:
        if proposal_id not in self._runtime_by_id:
            raise KeyError(proposal_id)
        if not user.strip() or not reason.strip():
            raise ValueError("Scribe-review vereist gebruiker en reden")
        runtime = self._runtime_by_id[proposal_id]
        reviewed = replace(
            runtime.proposal,
            status=status,
            reviewer=user.strip(),
            review_reason=reason.strip(),
            reviewed_at=_utc(),
        )
        self._runtime_by_id[proposal_id] = ScribeProposalRuntime(reviewed, runtime.edge_shape)
        self.audit.append(ScribeAuditEntry(_utc(), f"scribe.{status.value}", proposal_id, user.strip(), reason.strip()))

    def confirm(self, proposal_id: str, *, user: str, reason: str) -> None:
        self._review(proposal_id, ScribeStatus.CONFIRMED, user=user, reason=reason)

    def reject(self, proposal_id: str, *, user: str, reason: str) -> None:
        self._review(proposal_id, ScribeStatus.REJECTED, user=user, reason=reason)

    def reset(self, proposal_id: str, *, user: str, reason: str) -> None:
        self._review(proposal_id, ScribeStatus.PROPOSED, user=user, reason=reason)

    def payload(self) -> dict[str, Any]:
        if self.target.snapshot.exact_geometry_hash != self._target_hash:
            raise ValueError("CWS-SCRIBE-TARGET-GEOMETRY-CHANGED")
        if self.partner.snapshot.exact_geometry_hash != self._partner_hash:
            raise ValueError("CWS-SCRIBE-PARTNER-GEOMETRY-CHANGED")
        return {
            "schema": "cws-scribing-review-1.0",
            "target_part_id": self.target.snapshot.part_id,
            "partner_part_id": self.partner.snapshot.part_id,
            "target_geometry_hash": self._target_hash,
            "partner_geometry_hash": self._partner_hash,
            "proposals": [item.to_dict() for item in self.proposals],
            "audit": [item.to_dict() for item in self.audit],
            "production_release_allowed": False,
        }

    def export_json(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self.payload(), indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            handle.write(data)
            temporary = Path(handle.name)
        os.replace(temporary, output)
        output.with_suffix(output.suffix + ".sha256").write_text(
            hashlib.sha256(data).hexdigest() + "\n", encoding="ascii"
        )
        return output


def render_scribing_preview(
    target: ExactPartRuntime,
    partner: ExactPartRuntime,
    service: ScribingReviewService,
    output: str | Path,
    *,
    width: int = 1200,
    height: int = 760,
) -> Path:
    """Render an offscreen review preview; exact proposal data remains BREP-based."""

    import numpy as np
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
    from .overlay import tessellate_shape

    def actor(shape: Any, color: tuple[float, float, float], opacity: float):
        vertices, triangles = tessellate_shape(shape)
        points = vtk.vtkPoints()
        array = numpy_to_vtk(np.ascontiguousarray(vertices), deep=True)
        array.SetNumberOfComponents(3)
        points.SetData(array)
        cells = vtk.vtkCellArray()
        offsets = np.arange(0, (len(triangles) + 1) * 3, 3, dtype=np.int64)
        cells.SetData(
            numpy_to_vtkIdTypeArray(offsets, deep=True),
            numpy_to_vtkIdTypeArray(triangles.ravel(), deep=True),
        )
        poly = vtk.vtkPolyData(); poly.SetPoints(points); poly.SetPolys(cells)
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputData(poly)
        result = vtk.vtkActor(); result.SetMapper(mapper)
        result.GetProperty().SetColor(*color); result.GetProperty().SetOpacity(opacity)
        result.GetProperty().EdgeVisibilityOn(); result.GetProperty().SetEdgeColor(0.03, 0.05, 0.08)
        return result

    window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.SetSize(width, height)
    renderer = vtk.vtkRenderer(); window.AddRenderer(renderer)
    renderer.SetBackground(0.035, 0.055, 0.085); renderer.SetBackground2(0.12, 0.16, 0.22); renderer.GradientBackgroundOn()
    renderer.AddActor(actor(target.shape, (0.10, 0.70, 0.92), 0.55))
    renderer.AddActor(actor(partner.shape, (0.70, 0.74, 0.80), 0.38))
    for proposal in service.proposals:
        line = vtk.vtkLineSource(); line.SetPoint1(*proposal.start.to_tuple()); line.SetPoint2(*proposal.end.to_tuple()); line.Update()
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(line.GetOutputPort())
        line_actor = vtk.vtkActor(); line_actor.SetMapper(mapper)
        color = (0.15, 0.95, 0.40) if proposal.status == ScribeStatus.CONFIRMED else (1.0, 0.55, 0.05)
        line_actor.GetProperty().SetColor(*color); line_actor.GetProperty().SetLineWidth(5.0)
        renderer.AddActor(line_actor)
    text = vtk.vtkTextActor()
    text.SetInput(
        f"CWS V6 Scribing review\n{target.snapshot.part_id} ↔ {partner.snapshot.part_id} | "
        f"{len(service.proposals)} exact contactlijnen | confirmed {len(service.confirmed)}\n"
        "Oranje = voorstel · groen = bevestigd · geen snijbewerking"
    )
    text.SetPosition(22, height - 88); text.GetTextProperty().SetFontSize(20); text.GetTextProperty().SetColor(0.95, 0.98, 1.0)
    renderer.AddActor2D(text)
    renderer.ResetCamera(); camera = renderer.GetActiveCamera(); camera.Azimuth(35); camera.Elevation(25); camera.Zoom(1.15)
    window.Render()
    capture = vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.SetInputBufferTypeToRGBA(); capture.ReadFrontBufferOff(); capture.Update()
    writer = vtk.vtkPNGWriter(); writer.SetInputConnection(capture.GetOutputPort())
    path = Path(output); path.parent.mkdir(parents=True, exist_ok=True); writer.SetFileName(str(path)); writer.Write()
    window.Finalize()
    return path


__all__ = [
    "ScribeOperation",
    "ScribeStatus",
    "ScribeProposal",
    "ScribeAuditEntry",
    "ScribeProposalRuntime",
    "propose_contact_lines",
    "ScribingReviewService",
    "render_scribing_preview",
]
