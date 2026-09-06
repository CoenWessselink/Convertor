from __future__ import annotations

import os
import sys


_NATIVE_VIEWER_EVIDENCE_COMMANDS = frozenset({
    "viewer-real-benchmark",
    "viewer-real-soak",
    "viewer-real-warm",
    "viewer-real-session",
    "viewer-real-aa",
})


def _requires_frozen_native_fast_exit(arguments: list[str]) -> bool:
    return bool(
        getattr(sys, "frozen", False)
        and arguments
        and arguments[0] in _NATIVE_VIEWER_EVIDENCE_COMMANDS
    )


def _flush_standard_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            try:
                stream.flush()
            except (AttributeError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in {"project-export", "project-export-verify"}:
        from cws_export_cli import main as export_main
        return int(export_main(arguments))
    import cli as legacy_cli
    legacy_main = getattr(legacy_cli, "main", None)
    if not callable(legacy_main):
        raise RuntimeError("Bestaande SteelConverter CLI bevat geen main()-functie")
    try:
        result = legacy_main(arguments)
    except TypeError:
        previous = sys.argv
        try:
            sys.argv = [previous[0], *arguments]
            result = legacy_main()
        finally:
            sys.argv = previous
    return int(result or 0)


if __name__ == "__main__":
    forwarded = list(sys.argv[1:])
    exit_code = main(forwarded)
    if _requires_frozen_native_fast_exit(forwarded):
        _flush_standard_streams()
        os._exit(exit_code)
    raise SystemExit(exit_code)
