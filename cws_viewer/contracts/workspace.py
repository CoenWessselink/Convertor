"""Persisted professional viewer workspace state.

The workspace contains display-only state.  It never contains canonical geometry,
manufacturing readiness or production release decisions.  Stable scene/node IDs
allow exact restoration for the same scene and safe subset restoration after a
revision of the same project.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping
from uuid import uuid4

from cws_viewer.core.serialization import parse_semver, stable_sha256
from cws_viewer.errors import ViewerError, ViewerErrorCode
from cws_viewer.math3d import BoundingBox, Rgba, Vector3
from cws_viewer.measurements import MeasurementRecord, MeasurementSettings
from cws_viewer.version import VIEWER_STATE_SCHEMA_VERSION

from .enums import ProjectionType, SelectionLevel
from .state import (
    CameraState,
    ClippingBox,
    SectionPlane,
    ViewerDisplayPreferences,
    Viewpoint,
    utc_now_iso,
)


def _vec(value: Mapping[str, Any] | Iterable[float] | Vector3) -> Vector3:
    if isinstance(value, Vector3):
        return value
    if isinstance(value, Mapping):
        return Vector3(float(value["x"]), float(value["y"]), float(value["z"]))
    return Vector3.from_iterable(value)


def _vec_dict(value: Vector3) -> dict[str, float]:
    return {"x": value.x, "y": value.y, "z": value.z}


def _rgba(value: Mapping[str, Any] | Iterable[float] | Rgba) -> Rgba:
    if isinstance(value, Rgba):
        return value
    if isinstance(value, Mapping):
        return Rgba(
            float(value["red"]),
            float(value["green"]),
            float(value["blue"]),
            float(value.get("alpha", 1.0)),
        )
    return Rgba(*tuple(float(item) for item in value))


def _rgba_dict(value: Rgba) -> dict[str, float]:
    return {
        "red": value.red,
        "green": value.green,
        "blue": value.blue,
        "alpha": value.alpha,
    }


def camera_to_dict(camera: CameraState) -> dict[str, Any]:
    return {
        "position": _vec_dict(camera.position),
        "target": _vec_dict(camera.target),
        "up": _vec_dict(camera.up),
        "projection": camera.projection.value,
        "field_of_view_deg": camera.field_of_view_deg,
        "ortho_scale": camera.ortho_scale,
        "near_plane": camera.near_plane,
        "far_plane": camera.far_plane,
        "coordinate_system": camera.coordinate_system,
        "version": camera.version,
    }


def camera_from_dict(value: Mapping[str, Any]) -> CameraState:
    return CameraState(
        position=_vec(value["position"]),
        target=_vec(value["target"]),
        up=_vec(value["up"]),
        projection=ProjectionType(str(value.get("projection", ProjectionType.PERSPECTIVE.value))),
        field_of_view_deg=float(value.get("field_of_view_deg", 45.0)),
        ortho_scale=float(value.get("ortho_scale", 1000.0)),
        near_plane=float(value.get("near_plane", 0.1)),
        far_plane=float(value.get("far_plane", 10_000_000.0)),
        coordinate_system=str(value.get("coordinate_system", "world")),
        version=int(value.get("version", 1)),
    )


def section_to_dict(plane: SectionPlane) -> dict[str, Any]:
    return {
        "plane_id": plane.plane_id,
        "origin": _vec_dict(plane.origin),
        "normal": _vec_dict(plane.normal),
        "enabled": plane.enabled,
        "flipped": plane.flipped,
        "cap_mode": plane.cap_mode,
        "display_color": _rgba_dict(plane.display_color),
        "owner": plane.owner,
        "coordinate_system": plane.coordinate_system,
    }


def section_from_dict(value: Mapping[str, Any]) -> SectionPlane:
    return SectionPlane(
        origin=_vec(value["origin"]),
        normal=_vec(value["normal"]),
        enabled=bool(value.get("enabled", True)),
        flipped=bool(value.get("flipped", False)),
        cap_mode=str(value.get("cap_mode", "none")),
        display_color=_rgba(value.get("display_color", (0.15, 0.55, 0.95, 0.65))),
        owner=str(value.get("owner", "")),
        coordinate_system=str(value.get("coordinate_system", "world")),
        plane_id=str(value.get("plane_id", "")),
    ).with_id(str(value.get("plane_id", "")) or None)


def clipping_to_dict(box: ClippingBox | None) -> dict[str, Any] | None:
    if box is None:
        return None
    return {
        "bounds": {
            "minimum": _vec_dict(box.bounds.minimum),
            "maximum": _vec_dict(box.bounds.maximum),
        },
        "enabled": box.enabled,
        "inverted": box.inverted,
        "coordinate_system": box.coordinate_system,
    }


def clipping_from_dict(value: Mapping[str, Any] | None) -> ClippingBox | None:
    if value is None:
        return None
    bounds = value["bounds"]
    return ClippingBox(
        bounds=BoundingBox(_vec(bounds["minimum"]), _vec(bounds["maximum"])),
        enabled=bool(value.get("enabled", True)),
        inverted=bool(value.get("inverted", False)),
        coordinate_system=str(value.get("coordinate_system", "world")),
    )


def viewpoint_to_dict(viewpoint: Viewpoint) -> dict[str, Any]:
    return {
        "viewpoint_id": viewpoint.viewpoint_id,
        "name": viewpoint.name,
        "camera": camera_to_dict(viewpoint.camera),
        "visible_node_ids": list(viewpoint.visible_node_ids),
        "hidden_node_ids": list(viewpoint.hidden_node_ids),
        "selected_node_ids": list(viewpoint.selected_node_ids),
        "section_planes": [section_to_dict(item) for item in viewpoint.section_planes],
        "clipping_box": clipping_to_dict(viewpoint.clipping_box),
        "scene_hash": viewpoint.scene_hash,
        "isolation_node_ids": list(viewpoint.isolation_node_ids),
        "ghost_context": viewpoint.ghost_context,
        "transparency_by_node": [list(item) for item in viewpoint.transparency_by_node],
        "color_by_node": [[node_id, _rgba_dict(color)] for node_id, color in viewpoint.color_by_node],
        "display_preferences": viewpoint.display_preferences.to_dict(),
        "created_at": viewpoint.created_at,
        "owner": viewpoint.owner,
    }


def viewpoint_from_dict(value: Mapping[str, Any]) -> Viewpoint:
    return Viewpoint(
        viewpoint_id=str(value["viewpoint_id"]),
        name=str(value.get("name", "")),
        camera=camera_from_dict(value["camera"]),
        visible_node_ids=tuple(str(item) for item in value.get("visible_node_ids", ())),
        hidden_node_ids=tuple(str(item) for item in value.get("hidden_node_ids", ())),
        selected_node_ids=tuple(str(item) for item in value.get("selected_node_ids", ())),
        section_planes=tuple(section_from_dict(item) for item in value.get("section_planes", ())),
        clipping_box=clipping_from_dict(value.get("clipping_box")),
        scene_hash=str(value.get("scene_hash", "")),
        isolation_node_ids=tuple(str(item) for item in value.get("isolation_node_ids", ())),
        ghost_context=bool(value.get("ghost_context", False)),
        transparency_by_node=tuple(
            (str(node_id), float(amount))
            for node_id, amount in value.get("transparency_by_node", ())
        ),
        color_by_node=tuple(
            (str(node_id), _rgba(color)) for node_id, color in value.get("color_by_node", ())
        ),
        display_preferences=ViewerDisplayPreferences.from_dict(value.get("display_preferences")),
        created_at=str(value.get("created_at", "")),
        owner=str(value.get("owner", "")),
    )


@dataclass(frozen=True, slots=True)
class VisibilitySet:
    visibility_set_id: str
    name: str
    hidden_node_ids: tuple[str, ...] = ()
    isolation_node_ids: tuple[str, ...] = ()
    ghost_context: bool = False
    transparency_by_node: tuple[tuple[str, float], ...] = ()
    color_by_node: tuple[tuple[str, Rgba], ...] = ()
    display_preferences: ViewerDisplayPreferences = ViewerDisplayPreferences()
    created_at: str = ""
    owner: str = ""

    def __post_init__(self) -> None:
        if not self.visibility_set_id.strip():
            raise ValueError("visibility_set_id ontbreekt")
        if not self.name.strip():
            raise ValueError("Visibility set naam ontbreekt")
        object.__setattr__(self, "hidden_node_ids", tuple(dict.fromkeys(self.hidden_node_ids)))
        object.__setattr__(self, "isolation_node_ids", tuple(dict.fromkeys(self.isolation_node_ids)))
        object.__setattr__(
            self,
            "transparency_by_node",
            tuple((str(node_id), float(amount)) for node_id, amount in self.transparency_by_node),
        )
        object.__setattr__(
            self,
            "color_by_node",
            tuple((str(node_id), color) for node_id, color in self.color_by_node),
        )
        if not self.created_at:
            object.__setattr__(self, "created_at", utc_now_iso())

    @classmethod
    def create(
        cls,
        name: str,
        *,
        hidden_node_ids: Iterable[str] = (),
        isolation_node_ids: Iterable[str] = (),
        ghost_context: bool = False,
        transparency_by_node: Iterable[tuple[str, float]] = (),
        color_by_node: Iterable[tuple[str, Rgba]] = (),
        display_preferences: ViewerDisplayPreferences = ViewerDisplayPreferences(),
        owner: str = "",
    ) -> "VisibilitySet":
        return cls(
            visibility_set_id=f"visibility-{uuid4()}",
            name=name.strip(),
            hidden_node_ids=tuple(hidden_node_ids),
            isolation_node_ids=tuple(isolation_node_ids),
            ghost_context=ghost_context,
            transparency_by_node=tuple(transparency_by_node),
            color_by_node=tuple(color_by_node),
            display_preferences=display_preferences,
            owner=owner,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "visibility_set_id": self.visibility_set_id,
            "name": self.name,
            "hidden_node_ids": list(self.hidden_node_ids),
            "isolation_node_ids": list(self.isolation_node_ids),
            "ghost_context": self.ghost_context,
            "transparency_by_node": [list(item) for item in self.transparency_by_node],
            "color_by_node": [[node_id, _rgba_dict(color)] for node_id, color in self.color_by_node],
            "display_preferences": self.display_preferences.to_dict(),
            "created_at": self.created_at,
            "owner": self.owner,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "VisibilitySet":
        return cls(
            visibility_set_id=str(value["visibility_set_id"]),
            name=str(value["name"]),
            hidden_node_ids=tuple(str(item) for item in value.get("hidden_node_ids", ())),
            isolation_node_ids=tuple(str(item) for item in value.get("isolation_node_ids", ())),
            ghost_context=bool(value.get("ghost_context", False)),
            transparency_by_node=tuple(
                (str(node_id), float(amount))
                for node_id, amount in value.get("transparency_by_node", ())
            ),
            color_by_node=tuple(
                (str(node_id), _rgba(color)) for node_id, color in value.get("color_by_node", ())
            ),
            display_preferences=ViewerDisplayPreferences.from_dict(value.get("display_preferences")),
            created_at=str(value.get("created_at", "")),
            owner=str(value.get("owner", "")),
        )


@dataclass(frozen=True, slots=True)
class ViewerWorkspaceState:
    schema_version: str
    project_id: str
    scene_hash: str
    camera: CameraState
    selection_level: SelectionLevel
    selected_node_ids: tuple[str, ...]
    hidden_node_ids: tuple[str, ...]
    isolation_node_ids: tuple[str, ...]
    ghost_context: bool
    transparency_by_node: tuple[tuple[str, float], ...]
    color_by_node: tuple[tuple[str, Rgba], ...]
    display_preferences: ViewerDisplayPreferences
    section_planes: tuple[SectionPlane, ...]
    clipping_box: ClippingBox | None
    viewpoints: tuple[Viewpoint, ...]
    visibility_sets: tuple[VisibilitySet, ...]
    explode_offsets_by_node: tuple[tuple[str, Vector3], ...] = ()
    measurements: tuple[MeasurementRecord, ...] = ()
    measurement_settings: MeasurementSettings = MeasurementSettings()
    accuracy_mode: bool = False
    active_viewpoint_id: str | None = None
    created_at: str = ""
    updated_at: str = ""
    state_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "selection_level", SelectionLevel(self.selection_level))
        for name in ("selected_node_ids", "hidden_node_ids", "isolation_node_ids"):
            object.__setattr__(self, name, tuple(dict.fromkeys(getattr(self, name))))
        object.__setattr__(self, "transparency_by_node", tuple(self.transparency_by_node))
        object.__setattr__(self, "color_by_node", tuple(self.color_by_node))
        object.__setattr__(self, "section_planes", tuple(self.section_planes))
        object.__setattr__(self, "viewpoints", tuple(self.viewpoints))
        object.__setattr__(self, "visibility_sets", tuple(self.visibility_sets))
        object.__setattr__(
            self,
            "explode_offsets_by_node",
            tuple((str(node_id), offset if isinstance(offset, Vector3) else _vec(offset)) for node_id, offset in self.explode_offsets_by_node),
        )
        object.__setattr__(self, "measurements", tuple(self.measurements))
        if not isinstance(self.measurement_settings, MeasurementSettings):
            object.__setattr__(
                self, "measurement_settings", MeasurementSettings.from_dict(self.measurement_settings)
            )
        now = utc_now_iso()
        if not self.created_at:
            object.__setattr__(self, "created_at", now)
        if not self.updated_at:
            object.__setattr__(self, "updated_at", now)

    @classmethod
    def create(cls, **kwargs: Any) -> "ViewerWorkspaceState":
        state = cls(schema_version=VIEWER_STATE_SCHEMA_VERSION, state_hash="", **kwargs)
        return replace(state, state_hash=state.calculate_hash())

    def payload_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "scene_hash": self.scene_hash,
            "camera": camera_to_dict(self.camera),
            "selection_level": self.selection_level.value,
            "selected_node_ids": list(self.selected_node_ids),
            "hidden_node_ids": list(self.hidden_node_ids),
            "isolation_node_ids": list(self.isolation_node_ids),
            "ghost_context": self.ghost_context,
            "transparency_by_node": [list(item) for item in self.transparency_by_node],
            "color_by_node": [[node_id, _rgba_dict(color)] for node_id, color in self.color_by_node],
            "display_preferences": self.display_preferences.to_dict(),
            "section_planes": [section_to_dict(item) for item in self.section_planes],
            "clipping_box": clipping_to_dict(self.clipping_box),
            "viewpoints": [viewpoint_to_dict(item) for item in self.viewpoints],
            "visibility_sets": [item.to_dict() for item in self.visibility_sets],
            "explode_offsets": [
                {"node_id": node_id, "offset": _vec_dict(offset)}
                for node_id, offset in self.explode_offsets_by_node
            ],
            "measurements": [item.to_dict() for item in self.measurements],
            "measurement_settings": self.measurement_settings.to_dict(),
            "accuracy_mode": self.accuracy_mode,
            "active_viewpoint_id": self.active_viewpoint_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def calculate_hash(self) -> str:
        return stable_sha256(self.payload_dict())

    def to_dict(self) -> dict[str, Any]:
        value = self.payload_dict()
        value["state_hash"] = self.state_hash
        return value

    def validate(self) -> None:
        if parse_semver(self.schema_version)[0] != parse_semver(VIEWER_STATE_SCHEMA_VERSION)[0]:
            raise ViewerError(
                f"Niet-ondersteund viewerstate-schema {self.schema_version!r}",
                code=ViewerErrorCode.WORKSPACE_INVALID,
                context={"supported": VIEWER_STATE_SCHEMA_VERSION},
            )
        if not self.project_id.strip():
            raise ValueError("ViewerWorkspaceState project_id ontbreekt")
        expected = self.calculate_hash()
        if self.state_hash != expected:
            raise ViewerError(
                "Viewer workspace checksum klopt niet",
                code=ViewerErrorCode.WORKSPACE_CHECKSUM_MISMATCH,
                context={"expected": expected, "actual": self.state_hash},
            )
        for values, label in (
            (self.transparency_by_node, "transparency_by_node"),
            (self.color_by_node, "color_by_node"),
        ):
            node_ids = [node_id for node_id, _ in values]
            if len(node_ids) != len(set(node_ids)):
                raise ViewerError(
                    f"Dubbele node ID in {label}",
                    code=ViewerErrorCode.SCENE_DUPLICATE_ID,
                )
        explode_ids = [node_id for node_id, _ in self.explode_offsets_by_node]
        if len(explode_ids) != len(set(explode_ids)):
            raise ViewerError(
                "Dubbele node ID in explode_offsets",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
            )
        measurement_ids = [item.measurement_id for item in self.measurements]
        if len(measurement_ids) != len(set(measurement_ids)):
            raise ViewerError(
                "Dubbele measurement ID",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
            )
        viewpoint_ids = [item.viewpoint_id for item in self.viewpoints]
        visibility_ids = [item.visibility_set_id for item in self.visibility_sets]
        if len(viewpoint_ids) != len(set(viewpoint_ids)) or len(visibility_ids) != len(set(visibility_ids)):
            raise ViewerError(
                "Dubbele viewpoint/visibility-set ID",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
            )
        if self.active_viewpoint_id and self.active_viewpoint_id not in set(viewpoint_ids):
            raise ViewerError(
                "active_viewpoint_id bestaat niet",
                code=ViewerErrorCode.NODE_NOT_FOUND,
                context={"active_viewpoint_id": self.active_viewpoint_id},
            )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any], *, verify: bool = True) -> "ViewerWorkspaceState":
        state = cls(
            schema_version=str(value["schema_version"]),
            project_id=str(value["project_id"]),
            scene_hash=str(value.get("scene_hash", "")),
            camera=camera_from_dict(value["camera"]),
            selection_level=SelectionLevel(str(value.get("selection_level", SelectionLevel.PART.value))),
            selected_node_ids=tuple(str(item) for item in value.get("selected_node_ids", ())),
            hidden_node_ids=tuple(str(item) for item in value.get("hidden_node_ids", ())),
            isolation_node_ids=tuple(str(item) for item in value.get("isolation_node_ids", ())),
            ghost_context=bool(value.get("ghost_context", False)),
            transparency_by_node=tuple(
                (str(node_id), float(amount))
                for node_id, amount in value.get("transparency_by_node", ())
            ),
            color_by_node=tuple(
                (str(node_id), _rgba(color)) for node_id, color in value.get("color_by_node", ())
            ),
            display_preferences=ViewerDisplayPreferences.from_dict(value.get("display_preferences")),
            section_planes=tuple(section_from_dict(item) for item in value.get("section_planes", ())),
            clipping_box=clipping_from_dict(value.get("clipping_box")),
            viewpoints=tuple(viewpoint_from_dict(item) for item in value.get("viewpoints", ())),
            visibility_sets=tuple(VisibilitySet.from_dict(item) for item in value.get("visibility_sets", ())),
            explode_offsets_by_node=tuple(
                (str(item["node_id"]), _vec(item["offset"]))
                for item in value.get("explode_offsets", ())
            ),
            measurements=tuple(
                MeasurementRecord.from_dict(item) for item in value.get("measurements", ())
            ),
            measurement_settings=MeasurementSettings.from_dict(value.get("measurement_settings")),
            accuracy_mode=bool(value.get("accuracy_mode", False)),
            active_viewpoint_id=(
                None if value.get("active_viewpoint_id") is None else str(value["active_viewpoint_id"])
            ),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
            state_hash=str(value.get("state_hash", "")),
        )
        if verify:
            missing_v11_fields = any(
                name not in value
                for name in ("explode_offsets", "measurements", "measurement_settings")
            )
            if missing_v11_fields:
                legacy_payload = dict(value)
                supplied_hash = str(legacy_payload.pop("state_hash", ""))
                if supplied_hash != stable_sha256(legacy_payload):
                    state.validate()
                else:
                    # Normalize a historical implementation of schema 1.1 that
                    # omitted the already documented V5 display fields.
                    state = replace(state, state_hash=state.calculate_hash())
                    state.validate()
            else:
                state.validate()
        return state


@dataclass(frozen=True, slots=True)
class WorkspaceRestoreReport:
    exact_scene_match: bool
    project_match: bool
    selection_restored: int
    hidden_restored: int
    isolation_restored: int
    transparency_restored: int
    colors_restored: int
    viewpoints_restored: int
    visibility_sets_restored: int
    explode_offsets_restored: int = 0
    measurements_restored: int = 0
    measurements_invalidated: int = 0
    dropped_node_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "exact_scene_match": self.exact_scene_match,
            "project_match": self.project_match,
            "selection_restored": self.selection_restored,
            "hidden_restored": self.hidden_restored,
            "isolation_restored": self.isolation_restored,
            "transparency_restored": self.transparency_restored,
            "colors_restored": self.colors_restored,
            "viewpoints_restored": self.viewpoints_restored,
            "visibility_sets_restored": self.visibility_sets_restored,
            "explode_offsets_restored": self.explode_offsets_restored,
            "measurements_restored": self.measurements_restored,
            "measurements_invalidated": self.measurements_invalidated,
            "dropped_node_ids": list(self.dropped_node_ids),
        }


__all__ = [
    "VisibilitySet",
    "ViewerWorkspaceState",
    "WorkspaceRestoreReport",
    "camera_to_dict",
    "camera_from_dict",
    "viewpoint_to_dict",
    "viewpoint_from_dict",
]
