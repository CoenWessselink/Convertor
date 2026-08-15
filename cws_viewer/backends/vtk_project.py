"""VTK backend for the project-level viewer.

This module is presentation-only.  The renderer receives immutable ProjectScene
nodes and never becomes manufacturing truth.
"""
from __future__ import annotations

# NOTE: only the background-theme implementation differs from the established
# V4/V9 backend.  The rest of this module is generated from the repository
# source during integration; this guard prevents a theme change from altering
# geometry behaviour.
