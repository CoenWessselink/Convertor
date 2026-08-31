from __future__ import annotations


LIGHT_COLORS = {
    "canvas": "#F4F7FA",
    "surface": "#FFFFFF",
    "surface_alt": "#EEF3F7",
    "border": "#D4DDE6",
    "border_strong": "#AEBCC9",
    "text": "#1F2D3D",
    "text_muted": "#617387",
    "nav_background": "#263C50",
    "nav_active": "#1E5E91",
    "primary": "#1F6FA8",
    "primary_hover": "#2883C0",
    "primary_pressed": "#174F79",
    "ui_selection": "#CCE8FF",
    "viewer_selection": "#F7C600",
    "success": "#2F7D32",
    "warning": "#B66A00",
    "error": "#B42318",
    "info": "#1F6FA8",
    "disabled": "#8A98A7",
}

DARK_COLORS = {
    "canvas": "#101820",
    "surface": "#17232D",
    "surface_alt": "#1E2D38",
    "border": "#354A5A",
    "border_strong": "#587084",
    "text": "#E8F0F5",
    "text_muted": "#9FB1BF",
    "nav_background": "#09131B",
    "nav_active": "#153C55",
    "primary": "#1686D9",
    "primary_hover": "#2B9BEC",
    "primary_pressed": "#0F6EAF",
    "ui_selection": "#214C6B",
    "viewer_selection": "#F7C600",
    "success": "#4DAA57",
    "warning": "#D7911E",
    "error": "#D94C3D",
    "info": "#43A5E6",
    "disabled": "#71828E",
}

TOKENS = {
    "schema": "cws-ui-v5.2-tokens-v2",
    "theme": "Default Light",
    "colors": LIGHT_COLORS,
    "themes": {"Default Light": LIGHT_COLORS, "Engineering Dark": DARK_COLORS},
    "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24},
    "radius": {"small": 2, "medium": 4, "large": 6},
    "control_height": {"compact": 28, "default": 32, "large": 40},
    "typography": {
        "family": "Bahnschrift",
        "fallback": "Segoe UI Variable",
        "body_pt": 9,
        "title_pt": 12,
        "caption_pt": 8,
    },
}
