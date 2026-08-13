from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] in {"project-export", "project-export-verify"}:
        from cws_export_cli import main as export_main
        return int(export_main(arguments))
    import cli as legacy_cli
    legacy_main = getattr(legacy_cli, "main", None)
    if not callable(legacy_main):
        raise RuntimeError("Bestaande CWS Convertor CLI bevat geen main()-functie")
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
    raise SystemExit(main())
