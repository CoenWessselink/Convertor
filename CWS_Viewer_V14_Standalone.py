"""Standalone CWS Viewer V14 release-candidate entry point.

The proven rc3 launcher/worker transport remains unchanged. V14 overrides the
visible release version and, only for interactive desktop sessions, replaces
the cockpit runner with a progress-preserving V14 runner. Worker/self-test and
headless paths stay on the certified rc3 transport without importing GUI-heavy
modules unnecessarily.
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


def _install_interactive_v14_runner(args: list[str]) -> None:
    """Patch only the visible desktop cockpit path, never worker/CI services."""
    noninteractive = {
        "--version",
        "--self-test",
        "--quick-self-test",
        "--worker-self-test",
        "--multiprocessing-self-test",
        "--v14-self-test",
        "--geometry-worker-service",
        "--startup-smoke",
        "--ci-headless",
        "--gui-smoke",
    }
    if any(flag in args for flag in noninteractive):
        return
    from cws_viewer.ui_qt import cockpit
    from cws_viewer.ui_qt.cockpit_progress import run_cws_viewer_cockpit_with_progress

    cockpit.run_cws_viewer_cockpit = run_cws_viewer_cockpit_with_progress


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--v14-self-test" in args:
        from cws_viewer.v14_selftest import run_v14_selftest
        payload = run_v14_selftest()
        payload.update(
            {
                "product": PRODUCT,
                "version": VERSION,
                "frozen": bool(getattr(sys, "frozen", False)),
            }
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    _install_interactive_v14_runner(args)
    _base.VERSION = VERSION
    return _base.main(args)


if __name__ == "__main__":
    raise SystemExit(main())
