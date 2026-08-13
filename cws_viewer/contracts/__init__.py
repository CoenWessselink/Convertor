"""Immutable data contracts shared by CWS Convertor and Viewer Core."""

from .camera import CameraState, ProjectionType, ScreenshotOptions, StandardView
from .compare import CompareAssignment, CompareScene, CompareStatus
from .geometry import GeometryResource, MeshLod
from .measurement import Measurement, MeasurementAnchor, MeasurementKind, MeasurementStatus
from .primitives import BoundingBox, IDENTITY_MATRIX4, Matrix4, Rgba, Vector3
from .scene import (
    ColorAssignment,
    ProjectScene,
    SCENE_SCHEMA_VERSION,
    SceneModel,
    SceneNode,
    ScenePatch,
    StyleDefinition,
)
from .section import ClippingBox, SectionPlane
from .selection import PickResult, SelectionLevel
from .viewpoint import Viewpoint

__all__ = [
    "BoundingBox",
    "CameraState",
    "ClippingBox",
    "ColorAssignment",
    "CompareAssignment",
    "CompareScene",
    "CompareStatus",
    "GeometryResource",
    "IDENTITY_MATRIX4",
    "Matrix4",
    "Measurement",
    "MeasurementAnchor",
    "MeasurementKind",
    "MeasurementStatus",
    "MeshLod",
    "PickResult",
    "ProjectionType",
    "ProjectScene",
    "Rgba",
    "SCENE_SCHEMA_VERSION",
    "SceneModel",
    "SceneNode",
    "ScenePatch",
    "ScreenshotOptions",
    "SectionPlane",
    "SelectionLevel",
    "StandardView",
    "StyleDefinition",
    "Vector3",
    "Viewpoint",
]
