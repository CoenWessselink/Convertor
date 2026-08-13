"""Framework-neutral events emitted by a future viewer implementation."""
from __future__ import annotations

from dataclasses import dataclass

from cws_viewer.api.errors import ViewerContractError
from cws_viewer.contracts._validation import require_text
from cws_viewer.contracts.camera import CameraState
from cws_viewer.contracts.measurement import Measurement
from cws_viewer.contracts.selection import PickResult


@dataclass(frozen=True, slots=True)
class SceneLoadStarted:
    scene_hash: str


@dataclass(frozen=True, slots=True)
class SceneLoadProgress:
    scene_hash: str
    completed: int
    total: int
    message: str = ""

    def __post_init__(self) -> None:
        completed = int(self.completed)
        total = int(self.total)
        if completed < 0 or total < 0 or completed > total:
            raise ViewerContractError("Scene load progress is ongeldig")
        object.__setattr__(self, "completed", completed)
        object.__setattr__(self, "total", total)


@dataclass(frozen=True, slots=True)
class SceneReady:
    scene_hash: str


@dataclass(frozen=True, slots=True)
class SceneLoadFailed:
    scene_hash: str
    error_code: str
    message: str


@dataclass(frozen=True, slots=True)
class SelectionChanged:
    entity_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entity_ids",
            tuple(require_text(item, "entity_id") for item in self.entity_ids),
        )


@dataclass(frozen=True, slots=True)
class ObjectPicked:
    result: PickResult


@dataclass(frozen=True, slots=True)
class FeaturePicked:
    result: PickResult


@dataclass(frozen=True, slots=True)
class VisibilityChanged:
    entity_ids: tuple[str, ...]
    visible: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "entity_ids",
            tuple(require_text(item, "entity_id") for item in self.entity_ids),
        )


@dataclass(frozen=True, slots=True)
class CameraChanged:
    camera: CameraState


@dataclass(frozen=True, slots=True)
class SectionChanged:
    section_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "section_ids",
            tuple(require_text(item, "section_id") for item in self.section_ids),
        )


@dataclass(frozen=True, slots=True)
class MeasurementCreated:
    measurement: Measurement


@dataclass(frozen=True, slots=True)
class MeasurementInvalidated:
    measurement_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class CompareReady:
    source_scene_hash: str
    target_scene_hash: str


@dataclass(frozen=True, slots=True)
class ViewpointChanged:
    viewpoint_id: str


@dataclass(frozen=True, slots=True)
class RendererLost:
    reason: str


@dataclass(frozen=True, slots=True)
class ViewerDiagnostic:
    level: str
    code: str
    message: str


__all__ = [
    "CameraChanged",
    "CompareReady",
    "FeaturePicked",
    "MeasurementCreated",
    "MeasurementInvalidated",
    "ObjectPicked",
    "RendererLost",
    "SceneLoadFailed",
    "SceneLoadProgress",
    "SceneLoadStarted",
    "SceneReady",
    "SectionChanged",
    "SelectionChanged",
    "ViewerDiagnostic",
    "ViewpointChanged",
    "VisibilityChanged",
]
