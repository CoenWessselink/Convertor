"""Pure adaptive-detail helpers shared by UI and tests."""
from __future__ import annotations
import math
from cws_viewer.contracts.enums import ProjectionType
from cws_viewer.contracts.state import CameraState
from cws_viewer.math3d import BoundingBox


def projected_extent_pixels(bounds: BoundingBox, camera: CameraState, viewport_height: float) -> float:
    """Conservative screen-space size estimate for one world-space bound."""
    height=max(1.0,float(viewport_height))
    extent=max(bounds.size.x,bounds.size.y,bounds.size.z,1e-6)
    if camera.projection == ProjectionType.ORTHOGRAPHIC:
        return height*extent/max(float(camera.ortho_scale),1e-6)
    distance=max((bounds.center-camera.position).length(),1e-6)
    denominator=2.0*distance*math.tan(math.radians(float(camera.field_of_view_deg))*0.5)
    return height*extent/max(denominator,1e-9)

__all__=["projected_extent_pixels"]
