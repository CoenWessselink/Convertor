from __future__ import annotations


UI_PREFERENCES_SCHEMA = {
    "schema": "cws-ui-v5.2-preferences-v1",
    "defaults": {
        "theme": "Default Light",
        "density": "comfortable",
        "scale_percent": 100,
        "viewer_selection_color": "#F7C600",
        "ui_selection_color": "#CCE8FF",
        "reduced_motion": False,
        "remember_last_workspace": True,
    },
    "allowed": {
        "theme": ["Default Light"],
        "density": ["compact", "comfortable"],
        "scale_percent": [100, 125, 150, 175, 200],
    },
}

