"""Renderer capability negotiation without importing a renderer backend."""
from __future__ import annotations

from dataclasses import dataclass

from cws_viewer.api.errors import ViewerContractError
from cws_viewer.contracts._validation import require_text


@dataclass(frozen=True, slots=True)
class ViewerCapabilities:
    renderer_backend: str
    supports_large_mesh_scene: bool = False
    supports_exact_brep: bool = False
    supports_subshape_picking: bool = False
    supports_multi_section: bool = False
    supports_measurements: frozenset[str] = frozenset()
    supports_point_clouds: bool = False
    supports_offscreen_render: bool = False
    max_clip_planes: int = 0

    def __post_init__(self) -> None:
        if int(self.max_clip_planes) < 0:
            raise ViewerContractError("max_clip_planes mag niet negatief zijn")
        object.__setattr__(self, "renderer_backend", require_text(self.renderer_backend, "renderer_backend"))
        object.__setattr__(
            self,
            "supports_measurements",
            frozenset(require_text(item, "measurement capability") for item in self.supports_measurements),
        )
        object.__setattr__(self, "max_clip_planes", int(self.max_clip_planes))


__all__ = ["ViewerCapabilities"]
