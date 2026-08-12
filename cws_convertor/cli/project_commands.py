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

from cws_convertor.product import PROJECT_FILE_EXTENSION
from cws_convertor.project import ProjectService

PROJECT_COMMANDS = {
    "project-create",
    "project-info",
    "project-register-sources",
    "project-validate",
    "project-migrate",
}


def add_project_parsers(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("project-create", help="Maak een CWS Convertor-projectpakket")
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
        else:
            raise ValueError(f"Onbekend projectcommando {command!r}")
    except Exception as exc:
        payload["error"] = f"{type(exc).__name__}: {exc}"
        _write_report(getattr(args, "json_report", ""), payload)
        return 1, payload

    _write_report(getattr(args, "json_report", ""), payload)
    return 0, payload


__all__ = ["PROJECT_COMMANDS", "add_project_parsers", "handle_project_command"]
