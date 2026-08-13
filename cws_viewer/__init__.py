"""CWS Viewer Core contracts.

V0 intentionally contains no renderer and no semantic IFC/STEP importer. The
package defines the controlled boundary through which the CWS application will
later supply derived display data to a measured renderer backend.
"""

from .api import ViewerCapabilities, ViewerContractError, ViewerController, ViewerEditRequest
from .contracts import ProjectScene, SCENE_SCHEMA_VERSION

VIEWER_API_VERSION = "1.0.0"

__all__ = [
    "ProjectScene",
    "SCENE_SCHEMA_VERSION",
    "VIEWER_API_VERSION",
    "ViewerCapabilities",
    "ViewerContractError",
    "ViewerController",
    "ViewerEditRequest",
]
