"""Standalone CWS Viewer V14 release-candidate entry point.

The proven rc3 launcher/worker transport remains unchanged. V14 only overrides
the visible release version before delegating to that certified launcher, so
IFC frozen-worker isolation cannot silently regress while the UX branch evolves.
"""
from __future__ import annotations

import json
import multiprocessing
import sys
multiprocessing.freeze_support()

import CWS_Viewer_Standalone as _base

PRODUCT = _base.PRODUCT
VERSION = "1.3.0-rc1"
_base.VERSION = VERSION


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--v14-self-test" in args:
        from cws_viewer.v14_selftest import run_v14_selftest
        payload = run_v14_selftest()
        payload.update({"product": PRODUCT, "version": VERSION, "frozen": bool(getattr(sys,"frozen",False))})
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _base.VERSION = VERSION
    return _base.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
