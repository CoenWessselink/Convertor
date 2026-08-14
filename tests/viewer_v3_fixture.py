from __future__ import annotations

from cws_viewer.fixtures.real_reference import load_lo4_reference_mesh


def load_lo4_mesh():
    return load_lo4_reference_mesh()


__all__ = ["load_lo4_mesh"]
