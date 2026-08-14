"""Command-line diagnostics and contract self-test for CWS Viewer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core.diagnostics import collect_runtime_report, scan_for_forbidden_trimble_references
from .selftest import run_self_test
from .version import display_version


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cws_viewer")
    parser.add_argument("--version", action="store_true", help="Toon viewerversie")
    parser.add_argument("--diagnostics", action="store_true", help="Toon runtime-/backenddiagnostiek")
    parser.add_argument("--self-test", action="store_true", help="Voer contractselftest uit")
    parser.add_argument("--deep-native", action="store_true", help="Importeer en test native dependencies")
    parser.add_argument("--scan-root", type=Path, help="Controleer releaseboom op verboden Trimble-binaries")
    parser.add_argument("--json", action="store_true", help="Machineleesbare JSON-uitvoer")
    parser.add_argument("--output", type=Path, help="Schrijf hetzelfde rapport ook naar dit JSON-bestand")
    return parser


def _emit(text: str, output: Path | None) -> None:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
    print(text)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        print(display_version())
        return 0
    if args.self_test:
        report = run_self_test(deep_native=args.deep_native, scan_root=args.scan_root)
        text = report.to_json() if args.json else json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
        _emit(text, args.output)
        return 0 if report.passed else 2
    if args.diagnostics:
        report = collect_runtime_report(deep=args.deep_native, scan_root=args.scan_root)
        _emit(report.to_json(), args.output)
        return 0 if (not args.deep_native or report.all_required_ok) and not report.forbidden_reference_count else 2
    if args.scan_root:
        findings = scan_for_forbidden_trimble_references(args.scan_root)
        _emit(json.dumps({"findings": findings}, indent=2, ensure_ascii=False), args.output)
        return 0 if not findings else 2
    build_parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
