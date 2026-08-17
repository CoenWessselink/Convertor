"""Versioned public workspace contract for the preview.2 desktop build."""
from __future__ import annotations

from typing import Any

from cws_viewer.ui_qt.cockpit_trimble_feel_v2 import trimble_feel_v2_workspace_contract

PREVIEW2_VERSION = "1.4.0-v15-preview.2"


def preview2_workspace_contract() -> dict[str, Any]:
    contract = trimble_feel_v2_workspace_contract()
    contract["version"] = PREVIEW2_VERSION
    contract.setdefault("feel_v2", {})["version"] = PREVIEW2_VERSION
    return contract


__all__ = ["PREVIEW2_VERSION", "preview2_workspace_contract"]
