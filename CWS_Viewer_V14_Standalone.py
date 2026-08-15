"""Standalone CWS Viewer V14 release-candidate entry point.

The proven rc3 launcher/worker transport remains unchanged.  V14 only overrides
the visible release version before delegating to that certified launcher, so
IFC frozen-worker isolation cannot silently regress while the UX branch evolves.
"""
from __future__ import annotations

import multiprocessing
multiprocessing.freeze_support()

import CWS_Viewer_Standalone as _base

PRODUCT = _base.PRODUCT
VERSION = "1.3.0-rc1"
_base.VERSION = VERSION


def main(argv: list[str] | None = None) -> int:
    _base.VERSION = VERSION
    return _base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
