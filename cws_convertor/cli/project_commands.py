"""Reusable project command helpers for integrations.

The installed ``cli.py`` owns the complete command surface.  These helpers keep
one smaller importable command set for applications that embed the parser; they
use the same :mod:`cws_convertor.project` services and never maintain a second
project model.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cws_convertor.product import APP_NAME, PROJECT_FILE_EXTENSION
from cws_convertor.project import ProjectService

PROJECT_COMMANDS = {
    "project-create",
    "project-info",
    "project-register-sources",
    "project-validate",
    "project-migrate",
    "project-import-semantic",
    "project-list-parts",
    "project-list-assemblies",
    "project-export-steel-model",
}


def add_project_parsers(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("project-create", help=f"Maak een {APP_NAME}-projectpakket")
    parser.add_argument("name")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--customer", default="")
    parser.add_argument("--order", default="")
    parser.add_argument("--description", default="")
    parser.add_argument("--phase", default="")
    parser.add_argument("--user", default="")
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser("project-info", help="Toon project- en integriteitsinformatie")
    parser.add_argument("project")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser(
        "project-register-sources",
        help="Registreer IFC/STEP-bronnen en voer de deterministische nulmeting uit",
    )
    parser.add_argument("project")
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--geometry", action="store_true")
    parser.add_argument("--no-embed", action="store_true")
    parser.add_argument("--user", default="")
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser("project-validate", help="Valideer een .cwscproj-pakket")
    parser.add_argument("project")
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser("project-migrate", help="Migreer read-only project naar schema 2")
    parser.add_argument("project")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser(
        "project-import-semantic",
        help="Materialiseer IFC/STEP-assemblies, onderdelen, bouten en lassen",
    )
    parser.add_argument("project")
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--no-embed", action="store_true")
    parser.add_argument("--user", default="")
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser("project-list-parts", help="Lijst semantische onderdelen")
    parser.add_argument("project")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser("project-list-assemblies", help="Lijst semantische assemblies")
    parser.add_argument("project")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json-report", default="")

    parser = sub.add_parser(
        "project-export-steel-model",
        help="Exporteer SteelModel 1.0 en het viewer-hostcontract",
    )
    parser.add_argument("project")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--viewer-output", default="")
    parser.add_argument("--json-report", default="")


def _write_report(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def handle_project_command(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    service = ProjectService()
    command = str(args.command)
    payload: dict[str, Any] = {"command": command, "status": "failed"}
    try:
        if command == "project-create":
            package = service.create_project(
                args.output,
                project_name=args.name,
                description=args.description,
                customer=args.customer,
                order_number=args.order,
                project_phase=args.phase,
                created_by=args.user or "cli",
            )
            payload.update(
                status="passed",
                output=str(package.path),
                project=package.project.summary(),
            )
        elif command == "project-info":
            payload.update(status="passed", **service.project_info(args.project))
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif command == "project-register-sources":
            results = service.register_sources(
                args.project,
                args.inputs,
                embed_sources=not args.no_embed,
                include_step_geometry=args.geometry,
                user=args.user or "cli",
            )
            payload.update(
                status="passed",
                results=[item.to_dict() for item in results],
                project=service.project_info(args.project)["summary"],
            )
        elif command == "project-validate":
            payload.update(status="passed", verification=service.verify_project(args.project))
        elif command == "project-migrate":
            package = service.migrate_project(args.project, args.output)
            payload.update(
                status="passed",
                output=str(package.path),
                project=package.project.summary(),
            )
        elif command == "project-import-semantic":
            results = service.semantic_import(
                args.project,
                args.source_id or None,
                embed_sources=not args.no_embed,
                user=args.user or "cli",
            )
            payload.update(
                status="passed",
                results=[item.to_dict() for item in results],
                project=service.project_info(args.project)["summary"],
            )
        elif command == "project-list-parts":
            with service.open(args.project, read_only=True) as session:
                parts = [
                    {
                        "part_id": part.internal_id,
                        "source_id": part.source_identity.source_file_id,
                        "part_position": part.part_position,
                        "name": part.name,
                        "category": part.category,
                        "profile": part.profile,
                        "material": part.material,
                        "length_mm": part.length_mm,
                        "assembly_ids": list(part.assembly_ids),
                        "geometry_hash": part.geometry_hash,
                        "manufacturing_hash": part.manufacturing_hash,
                        "nc1_eligible": part.nc1_eligible,
                    }
                    for part in session.project.parts.values()
                    if not args.source_id
                    or part.source_identity.source_file_id == args.source_id
                ]
            parts.sort(key=lambda item: (item["part_position"], item["name"], item["part_id"]))
            total = len(parts)
            if args.limit > 0:
                parts = parts[: args.limit]
            payload.update(status="passed", total_matching=total, parts=parts)
        elif command == "project-list-assemblies":
            with service.open(args.project, read_only=True) as session:
                assemblies = [
                    {
                        "assembly_id": assembly.internal_id,
                        "source_id": assembly.source_identity.source_file_id,
                        "assembly_mark": assembly.assembly_mark,
                        "name": assembly.name,
                        "part_count": len(assembly.part_ids),
                        "fastener_count": len(assembly.fastener_ids),
                        "weld_count": len(assembly.weld_ids),
                        "total_weight_kg": assembly.total_weight_kg,
                    }
                    for assembly in session.project.assemblies.values()
                    if not args.source_id
                    or assembly.source_identity.source_file_id == args.source_id
                ]
            assemblies.sort(
                key=lambda item: (item["assembly_mark"], item["name"], item["assembly_id"])
            )
            total = len(assemblies)
            if args.limit > 0:
                assemblies = assemblies[: args.limit]
            payload.update(status="passed", total_matching=total, assemblies=assemblies)
        elif command == "project-export-steel-model":
            from cws_convertor.steel_model.adapter import build_steel_model_snapshot
            from cws_convertor.steel_model.viewer_boundary import build_viewer_host_snapshot

            with service.open(args.project, read_only=True) as session:
                steel_model = build_steel_model_snapshot(session.project)
            viewer_host = build_viewer_host_snapshot(steel_model)
            target = Path(args.output)
            viewer_target = (
                Path(args.viewer_output)
                if args.viewer_output
                else target.with_name(f"{target.stem}.viewer-host.json")
            )
            if target.resolve() == viewer_target.resolve():
                raise ValueError("SteelModel- en viewer-uitvoer moeten verschillen")
            target.parent.mkdir(parents=True, exist_ok=True)
            viewer_target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(steel_model.to_json_bytes())
            viewer_target.write_bytes(viewer_host.to_json_bytes())
            payload.update(
                status="passed",
                steel_model={
                    "output": str(target),
                    "schema_version": steel_model.schema_version,
                    "snapshot_sha256": steel_model.snapshot_sha256,
                    "entity_count": len(steel_model.entities),
                },
                viewer_host={
                    "output": str(viewer_target),
                    "contract_version": viewer_host.contract_version,
                    "snapshot_sha256": viewer_host.snapshot_sha256,
                    "binding_count": len(viewer_host.bindings),
                },
            )
        else:
            raise ValueError(f"Onbekend projectcommando {command!r}")
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
        _write_report(getattr(args, "json_report", ""), payload)
        return 1, payload

    _write_report(getattr(args, "json_report", ""), payload)
    return 0, payload


__all__ = ["PROJECT_COMMANDS", "add_project_parsers", "handle_project_command"]
