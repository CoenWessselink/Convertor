"""CWS UI Master V5.2 design-system authority."""

from .control_registry import ControlRegistry, scan_product_controls
from .icons import ICON_REGISTRY, IconRegistry, icon_for_test_id
from .preferences import UI_PREFERENCES_SCHEMA
from .stylesheet import V52_LIGHT_QSS, apply_v52_design_system
from .test_ids import get_ui_test_id, set_ui_test_id
from .tokens import TOKENS

__all__ = [
    "ControlRegistry",
    "ICON_REGISTRY",
    "IconRegistry",
    "TOKENS",
    "UI_PREFERENCES_SCHEMA",
    "V52_LIGHT_QSS",
    "apply_v52_design_system",
    "get_ui_test_id",
    "icon_for_test_id",
    "scan_product_controls",
    "set_ui_test_id",
]

