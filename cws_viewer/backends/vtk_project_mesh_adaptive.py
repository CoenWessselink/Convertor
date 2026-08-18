"""Adaptive interaction-quality layer for the V15 Trimble-feel renderer.

The idle renderer keeps the high-quality V15 material, lighting and SSAO path.
During orbit, pan and wheel zoom the expensive screen-space pass and excessive
multisampling are temporarily reduced.  The widget restores full quality after
an idle debounce, so input latency wins while the final stationary image keeps
its normal engineering-review quality.
"""
from __future__ import annotations

from typing import Any

from cws_viewer.backends.vtk_project_mesh_feel_v2 import VtkProjectMeshFeelV2Backend


class VtkProjectMeshAdaptiveBackend(VtkProjectMeshFeelV2Backend):
    """V15 renderer with explicit interactive and idle quality states."""

    INTERACTIVE_MULTISAMPLES = 2
    MIN_IDLE_MULTISAMPLES = 4

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._interaction_quality_active = False
        self._idle_multisamples = 8

    @property
    def interaction_quality_active(self) -> bool:
        return bool(self._interaction_quality_active)

    def initialize(self, *, width: int, height: int) -> None:
        super().initialize(width=width, height=height)
        window = self._render_window
        if window is None:
            return
        try:
            configured = int(window.GetMultiSamples())
        except Exception:
            configured = 8
        self._idle_multisamples = max(self.MIN_IDLE_MULTISAMPLES, configured)

    def set_interaction_quality(self, interacting: bool) -> bool:
        """Switch quality without forcing an extra render.

        Returns ``True`` only when the state changed.  Rendering remains owned
        by the controller/widget frame scheduler, preventing duplicate renders
        for a single mouse event.
        """
        requested = bool(interacting)
        if requested == self._interaction_quality_active:
            return False

        renderer = self._renderer
        window = self._render_window
        if renderer is not None:
            try:
                renderer.SetPass(None if requested else self._ssao_pass)
            except Exception:
                # Not every VTK/OpenGL combination exposes render-pass switching.
                # The multisample path below still provides a safe degradation.
                pass
        if window is not None:
            try:
                samples = (
                    self.INTERACTIVE_MULTISAMPLES
                    if requested
                    else self._idle_multisamples
                )
                window.SetMultiSamples(int(samples))
            except Exception:
                pass

        self._interaction_quality_active = requested
        return True

    def clear_scene(self) -> None:
        self._interaction_quality_active = False
        super().clear_scene()


__all__ = ["VtkProjectMeshAdaptiveBackend"]
