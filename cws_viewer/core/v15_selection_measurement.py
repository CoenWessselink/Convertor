"""V15 T4 selection, picking, snapping and measurement services.

This layer intentionally keeps review measurements separate from canonical
manufacturing truth. Display/mesh picks remain review evidence; only exact BREP
or canonical-feature anchors can become production-eligible according to the
existing measurement contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.measurements import (
    ExactMeasurementAnchor,
    MeasurementProof,
    MeasurementRecord,
    MeasurementSettings,
    SnapType,
    angle_three_points,
    diameter,
    distance,
    radius,
)
from cws_viewer.exact.snapping import anchor_from_candidate, snap
from cws_viewer.math3d import Vector3

V15_T4_SCHEMA = "cws-viewer-selection-measurement-15.3"
V15_T4_VERSION = "1.4.0-v15-preview.1"


@dataclass(frozen=True, slots=True)
class InteractionToleranceProfile:
    """Picking/snap tolerance only; never a fabrication acceptance tolerance."""

    name: str
    snap_tolerance_mm: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tolerance profile vereist naam")
        if not 0.01 <= float(self.snap_tolerance_mm) <= 100.0:
            raise ValueError("Snap tolerance moet 0.01..100 mm zijn")


TOLERANCE_PROFILES: dict[str, InteractionToleranceProfile] = {
    "fine": InteractionToleranceProfile("Fijn", 1.0),
    "normal": InteractionToleranceProfile("Normaal", 5.0),
    "coarse": InteractionToleranceProfile("Grof", 10.0),
}


def selection_measurement_contract() -> dict[str, Any]:
    return {
        "schema": V15_T4_SCHEMA,
        "version": V15_T4_VERSION,
        "capabilities": {
            "point_selection": True,
            "area_selection": True,
            "multi_selection": True,
            "hierarchy_aware_picking": True,
            "selection_levels": [item.value for item in SelectionLevel],
            "select_all_visible": True,
            "invert_visible_selection": True,
            "grouped_properties": True,
            "property_search": True,
            "property_copy": True,
            "project_pick_measurement_proof": True,
            "exact_brep_snapping": True,
            "snap_tolerance_profiles": True,
            "snap_feedback": True,
            "distance_measurement": True,
            "angle_measurement": True,
            "radius_diameter_measurement": True,
            "measurement_export_review_state": True,
            "ai_derived_dimensions": False,
        },
        "safety": {
            "interaction_tolerances_are_production_tolerances": False,
            "display_proxy_production_eligible": False,
            "viewer_can_release_machine_output": False,
        },
    }


class V15SelectionMeasurementService:
    def __init__(
        self,
        controller: Any,
        *,
        mesh_repository: Any | None = None,
        tolerance_profile: InteractionToleranceProfile = TOLERANCE_PROFILES["normal"],
    ) -> None:
        self.controller = controller
        self.mesh_repository = mesh_repository
        self.tolerance_profile = tolerance_profile

    def set_tolerance_profile(self, profile: str | InteractionToleranceProfile) -> None:
        if isinstance(profile, InteractionToleranceProfile):
            self.tolerance_profile = profile
            return
        try:
            self.tolerance_profile = TOLERANCE_PROFILES[str(profile)]
        except KeyError as exc:
            raise ValueError(f"Onbekend tolerance profile: {profile}") from exc

    def set_selection_level(self, level: SelectionLevel) -> SelectionLevel:
        value = SelectionLevel(level)
        self.controller.set_selection_level(value)
        current = self.controller.get_selection()
        if current:
            promoted = self._promote(current, value)
            self.controller.set_selection(promoted, mode="replace")
        return value

    def _promote(
        self, node_ids: Iterable[str], level: SelectionLevel | None = None
    ) -> tuple[str, ...]:
        requested = level or self.controller.session.selection_level
        index = self.controller.index
        return tuple(
            dict.fromkeys(
                index.selectable_node_for_level(str(node_id), requested)
                for node_id in node_ids
            )
        )

    def visible_selectable(self) -> tuple[str, ...]:
        index = self.controller.index
        visible, _ghosted = self.controller.session.visible_and_ghosted(index)
        renderable = [
            node_id
            for node_id in visible
            if node_id in index.nodes_by_id
            and index.nodes_by_id[node_id].geometry_id is not None
            and index.nodes_by_id[node_id].selectable
        ]
        return self._promote(renderable)

    def select_all_visible(self) -> tuple[str, ...]:
        values = self.visible_selectable()
        self.controller.set_selection(values, mode="replace")
        return values

    def invert_visible_selection(self) -> tuple[str, ...]:
        visible = self.visible_selectable()
        selected = set(self.controller.get_selection())
        values = tuple(node_id for node_id in visible if node_id not in selected)
        self.controller.set_selection(values, mode="replace")
        return values

    def apply_area_nodes(
        self,
        node_ids: Iterable[str],
        *,
        mode: str = "replace",
    ) -> tuple[str, ...]:
        values = self._promote(node_ids)
        self.controller.set_selection(values, mode=mode)
        return values

    def clear_selection(self) -> None:
        self.controller.set_selection((), mode="replace")

    def _proof_for_node(self, node_id: str) -> MeasurementProof:
        node = self.controller.index.node(str(node_id))
        if node.geometry_id is None or self.mesh_repository is None:
            return MeasurementProof.DISPLAY_PROXY
        mesh = self.mesh_repository.get(node.geometry_id)
        exactness = str(getattr(mesh, "exactness", "") or "") if mesh is not None else ""
        if mesh is None or exactness in {"display_proxy", "display_approximation"}:
            return MeasurementProof.DISPLAY_PROXY
        return MeasurementProof.VERIFIED_MESH

    def anchor_from_project_pick(self, pick: Any) -> ExactMeasurementAnchor:
        node = self.controller.index.node(str(pick.node_id))
        return ExactMeasurementAnchor(
            node_id=node.node_id,
            entity_id=node.entity_id,
            source_entity_id=str(pick.source_entity_id or node.source_entity_id or ""),
            feature_id=getattr(pick, "feature_id", None),
            subshape_type=getattr(pick, "subshape_type", None),
            subshape_id=getattr(pick, "subshape_id", None),
            world_point=pick.world_point,
            local_point=pick.local_point,
            geometry_hash=node.geometry_hash,
            snap_type=SnapType.NEAREST,
            proof=self._proof_for_node(node.node_id),
            normal=getattr(pick, "normal", None),
        )

    def exact_snap_anchor(
        self,
        runtime: Any,
        query: Vector3,
        *,
        allowed: Iterable[SnapType] | None = None,
        tolerance_mm: float | None = None,
    ) -> ExactMeasurementAnchor | None:
        tolerance = (
            self.tolerance_profile.snap_tolerance_mm
            if tolerance_mm is None
            else float(tolerance_mm)
        )
        candidate = snap(runtime, query, allowed=allowed, tolerance_mm=tolerance)
        return None if candidate is None else anchor_from_candidate(runtime, candidate)

    def add_distance(
        self,
        first: ExactMeasurementAnchor,
        second: ExactMeasurementAnchor,
        *,
        settings: MeasurementSettings | None = None,
    ) -> MeasurementRecord:
        record = distance(first, second, settings or self.controller.get_measurement_settings())
        self.controller.add_measurement(record)
        return record

    def add_angle(
        self,
        first: ExactMeasurementAnchor,
        vertex: ExactMeasurementAnchor,
        third: ExactMeasurementAnchor,
        *,
        settings: MeasurementSettings | None = None,
    ) -> MeasurementRecord:
        record = angle_three_points(
            first,
            vertex,
            third,
            settings or self.controller.get_measurement_settings(),
        )
        self.controller.add_measurement(record)
        return record

    def add_radius(
        self,
        anchor: ExactMeasurementAnchor,
        *,
        settings: MeasurementSettings | None = None,
    ) -> MeasurementRecord:
        record = radius(anchor, settings or self.controller.get_measurement_settings())
        self.controller.add_measurement(record)
        return record

    def add_diameter(
        self,
        anchor: ExactMeasurementAnchor,
        *,
        settings: MeasurementSettings | None = None,
    ) -> MeasurementRecord:
        record = diameter(anchor, settings or self.controller.get_measurement_settings())
        self.controller.add_measurement(record)
        return record


__all__ = [
    "InteractionToleranceProfile",
    "TOLERANCE_PROFILES",
    "V15SelectionMeasurementService",
    "V15_T4_SCHEMA",
    "V15_T4_VERSION",
    "selection_measurement_contract",
]
