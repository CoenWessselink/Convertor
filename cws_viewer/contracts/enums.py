"""String enums persisted by the CWS Viewer contracts."""
from __future__ import annotations

from enum import StrEnum


class NodeKind(StrEnum):
    PROJECT = "project"
    GROUP = "group"
    MODEL = "model"
    ASSEMBLY = "assembly"
    PART = "part"
    PURCHASED_ITEM = "purchased_item"
    FASTENER = "fastener"
    WELD = "weld"
    REFERENCE = "reference"
    FEATURE = "feature"


class GeometryRepresentation(StrEnum):
    MESH_LOD = "mesh_lod"
    BREP = "brep"
    ANALYTICAL = "analytical"
    POINT_CLOUD = "point_cloud"


class SelectionLevel(StrEnum):
    MODEL = "model"
    ASSEMBLY = "assembly"
    PART = "part"
    FEATURE = "feature"


class SelectionOperation(StrEnum):
    REPLACE = "replace"
    ADD = "add"
    REMOVE = "remove"
    TOGGLE = "toggle"


class ProjectionType(StrEnum):
    PERSPECTIVE = "perspective"
    ORTHOGRAPHIC = "orthographic"


class StandardView(StrEnum):
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    ISOMETRIC = "isometric"


class RenderMode(StrEnum):
    SHADED = "shaded"
    SHADED_EDGES = "shaded_edges"
    WIREFRAME = "wireframe"
    HIDDEN_LINE = "hidden_line"


class ColorScheme(StrEnum):
    ORIGINAL = "original"
    CATEGORY = "category"
    MATERIAL = "material"
    PROFILE = "profile"
    STATUS = "status"
    PHASE = "phase"
    SOURCE_MODEL = "source_model"
    ASSEMBLY = "assembly"
    MONOCHROME = "monochrome"


class BackgroundTheme(StrEnum):
    DARK = "dark"
    SLATE = "slate"
    LIGHT = "light"


class MeasurementKind(StrEnum):
    POINT = "point"
    DISTANCE = "distance"
    HORIZONTAL_DISTANCE = "horizontal_distance"
    VERTICAL_DISTANCE = "vertical_distance"
    EDGE_LENGTH = "edge_length"
    PERPENDICULAR_DISTANCE = "perpendicular_distance"
    ANGLE = "angle"
    SLOPE = "slope"
    RADIUS = "radius"
    DIAMETER = "diameter"
    FACE_FACE = "face_face"
    COORDINATES = "coordinates"
    AREA = "area"
    VOLUME = "volume"


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


__all__ = [name for name in globals() if name[0].isupper()]
