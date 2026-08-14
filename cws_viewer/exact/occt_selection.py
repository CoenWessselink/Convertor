"""OCCT subshape-selection bridge with stable CWS identifiers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import ExactPartRuntime, SubshapeKind


@dataclass(slots=True)
class OcctSubshapeSelectionBridge:
    runtime: ExactPartRuntime

    def stable_id_for_shape(self, selected_shape: Any) -> str | None:
        for stable_id, shape in self.runtime.shape_by_subshape_id.items():
            try:
                if selected_shape.IsSame(shape.wrapped if hasattr(shape, "wrapped") else shape):
                    return stable_id
            except Exception:
                try:
                    if hasattr(shape, "isSame") and shape.isSame(selected_shape):
                        return stable_id
                except Exception:
                    continue
        return None

    def shape_for_stable_id(self, stable_id: str) -> Any:
        return self.runtime.shape_by_subshape_id[stable_id]

    @staticmethod
    def selection_mode(kind: SubshapeKind) -> int:
        from OCP.AIS import AIS_Shape
        from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX

        mapping = {
            SubshapeKind.VERTEX: TopAbs_VERTEX,
            SubshapeKind.EDGE: TopAbs_EDGE,
            SubshapeKind.FACE: TopAbs_FACE,
        }
        if kind not in mapping:
            return 0
        return int(AIS_Shape.SelectionMode_s(mapping[kind]))

    @staticmethod
    def activate_context(context: Any, ais_shape: Any, kind: SubshapeKind) -> None:
        context.Deactivate(ais_shape)
        context.Activate(ais_shape, OcctSubshapeSelectionBridge.selection_mode(kind), True)

    def selected_stable_id(self, context: Any) -> str | None:
        context.InitSelected()
        if not context.MoreSelected() or not context.HasSelectedShape():
            return None
        return self.stable_id_for_shape(context.SelectedShape())


__all__ = ["OcctSubshapeSelectionBridge"]
