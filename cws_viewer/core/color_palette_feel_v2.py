"""Refined deterministic colours for non-original viewer colour schemes.

Original mode never uses this palette; source IFC presentation colours remain
untouched.  The palette is only used when a user explicitly chooses Material,
Profile, Assembly, Phase, Source Model or another analytical colouring mode.
"""
from __future__ import annotations

from cws_viewer.math3d import Rgba

FEEL_V2_PALETTE = (
    Rgba(0.10, 0.55, 0.78),  # structural blue
    Rgba(0.91, 0.72, 0.05),  # warm yellow
    Rgba(0.05, 0.72, 0.72),  # cyan/teal
    Rgba(0.21, 0.63, 0.38),  # green
    Rgba(0.91, 0.43, 0.13),  # orange
    Rgba(0.31, 0.39, 0.66),  # indigo steel
    Rgba(0.73, 0.26, 0.34),  # red wine
    Rgba(0.42, 0.66, 0.13),  # lime/olive
    Rgba(0.55, 0.38, 0.74),  # violet
    Rgba(0.08, 0.63, 0.52),  # emerald
    Rgba(0.83, 0.55, 0.16),  # ochre
    Rgba(0.24, 0.49, 0.72),  # medium blue
    Rgba(0.70, 0.35, 0.62),  # magenta muted
    Rgba(0.17, 0.68, 0.82),  # sky cyan
    Rgba(0.56, 0.57, 0.27),  # moss
    Rgba(0.77, 0.41, 0.24),  # copper
    Rgba(0.28, 0.61, 0.58),  # desaturated teal
    Rgba(0.46, 0.52, 0.70),  # cool steel
)


def install_feel_v2_palette() -> None:
    from cws_viewer.core import color_schemes

    color_schemes._PALETTE = FEEL_V2_PALETTE


__all__ = ["FEEL_V2_PALETTE", "install_feel_v2_palette"]
