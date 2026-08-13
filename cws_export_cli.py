from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cws_convertor.production_export import ExportRequest, ProductionExportEngine, load_project_snapshot
from cws_convertor.production_export.verify import verify_export_directory, verify_export_zip


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="CWS_Convertor_Export_CLI",
        description="Veilige per-onderdeel- en per-merkexport voor CWS Convertor",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("project-export", help="Maak een gecontroleerd productie-/reviewpakket")
    export.add_argument("project")
    export.add_argument("--output", required=True)
    export.add_argument("--formats", default="json,review_pdf,nc1,step,ifc,production_pdf")
    export.add_argument("--part-id", action="append", default=[])
    export.add_argument("--assembly-mark", action="append", default=[])
    export.add_argument("--no-zip", action="store_true")
    export.add_argument("--no-blocked-review", action="store_true")
    export.add_argument("--json", action="store_true", dest="json_output")

    verify = sub.add_parser("project-export-verify", help="Controleer manifest, CRC en SHA-256")
    verify.add_argument("path")
    verify.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "project-export":
        loaded = load_project_snapshot(args.project)
        request = ExportRequest(
            output_dir=Path(args.output),
            formats=[f.strip() for f in args.formats.split(",") if f.strip()],
            part_ids=set(args.part_id),
            assembly_marks=set(args.assembly_mark),
            include_blocked_review_files=not args.no_blocked_review,
            create_zip=not args.no_zip,
        )
        manifest, root, zip_path = ProductionExportEngine().export_project(loaded.snapshot, request)
        result = {
            "output_directory": str(root),
            "zip": str(zip_path) if zip_path else "",
            "source_sha256": loaded.source_sha256,
            "summary": manifest.summary,
            "manifest_sha256": manifest.manifest_sha256,
        }
        if args.json_output:
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"Exportmap: {root}")
            if zip_path:
                print(f"ZIP: {zip_path}")
            print(json.dumps(manifest.summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if manifest.summary.get("production_ready") else 3
    if args.command == "project-export-verify":
        source = Path(args.path)
        result = verify_export_zip(source) if source.suffix.lower() == ".zip" else verify_export_directory(source)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
