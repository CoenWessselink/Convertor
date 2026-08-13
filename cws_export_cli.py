from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cws_convertor.production_export import RELEASE_FORMATS
from cws_convertor.production_export.verify import verify_export_directory, verify_export_zip
from cws_convertor.project import ProjectService


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="CWS_Convertor_Export_CLI",
        description="Veilige per-onderdeel- en per-merkexport voor CWS Convertor",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("project-export", help="Maak een gecontroleerd productie-/reviewpakket")
    export.add_argument("project")
    export.add_argument("--output", required=True)
    export.add_argument("--formats", default=",".join(RELEASE_FORMATS))
    export.add_argument("--part-id", action="append", default=[])
    export.add_argument("--assembly-mark", action="append", default=[])
    export.add_argument("--no-zip", action="store_true")
    export.add_argument("--no-blocked-review", action="store_true")
    export.add_argument(
        "--name-template",
        default="{project}_{assembly_mark}_{part_position}_{profile}_{revision}_{identity}",
    )
    export.add_argument("--json", action="store_true", dest="json_output")

    verify = sub.add_parser("project-export-verify", help="Controleer manifest, CRC en SHA-256")
    verify.add_argument("path")
    verify.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "project-export":
        manifest, root, zip_path = ProjectService().export_production_package(
            args.project,
            Path(args.output),
            formats=[f.strip() for f in args.formats.split(",") if f.strip()],
            part_ids=args.part_id,
            assembly_marks=args.assembly_mark,
            filename_template=args.name_template,
            create_zip=not args.no_zip,
            include_blocked_review_files=not args.no_blocked_review,
            user="export-cli",
        )
        result = {
            "output_directory": str(root),
            "zip": str(zip_path) if zip_path else "",
            "project_state_hash": manifest.project_state_hash,
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
