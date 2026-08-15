"""CWS Viewer 1.2.0-rc4 product entrypoint.

RC4 deliberately wraps the proven standalone runtime instead of editing the
large rc3 launcher during the usability release.  Private frozen IFC worker
arguments, self-tests and startup behaviour remain identical; only the release
identity is promoted before main() is entered.
"""
from __future__ import annotations

import CWS_Viewer_Standalone as _runtime

_runtime.VERSION = "1.2.0-rc4"


def main() -> int:
    return int(_runtime.main())


if __name__ == "__main__":
    raise SystemExit(main())
