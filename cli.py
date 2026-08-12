from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
from typing import Any, Callable

from cws_convertor.product import APP_NAME, APP_VERSION

from ai_support import AISettings
from conversion import __version__, convert_nc1_to_step, step_to_nc1
from ifc_support import dstv_to_ifc, ifc_to_dstv, ifc_to_step, step_to_ifc
from material_database import MaterialDatabase
from pdf_support import (
    DrawingTemplate,
    ExternalPDFExportBlocked,
    analyze_pdf,
    ifc_to_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    review_external_pdf,
    step_to_pdf,
    write_analysis_report,
)
from profile_database import ProfileDatabase
from quantities import analyze_files, export_excel
from cws_convertor.errors import CWSError
from cws_convertor.project import (
    ProjectPackageError,
    ProjectService,
    ProjectSession,
    inspect_model_file,
    write_baseline_report,
)


EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NO_INPUT = 2
EXIT_REVIEW_REQUIRED = 3


def _iter_inputs(items: list[str], extensions: set[str]):
    for item in items:
        path = Path(item)
        if path.is_dir():
            for candidate in sorted(path.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() in extensions:
                    yield candidate
        elif path.is_file() and (not extensions or path.suffix.lower() in extensions):
            yield path
        elif path.exists():
            print(f"WAARSCHUWING: overgeslagen wegens extensie: {path}", file=sys.stderr)
        else:
            print(f"WAARSCHUWING: niet gevonden: {path}", file=sys.stderr)


def _common_reverse_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--material", default="S355JR", help="Materiaal voor uitvoer/quantities")
    parser.add_argument("--order", default="STEP", help="Ordernummer voor DSTV/NC1-kopgegevens")
    parser.add_argument("--profile", default="", help="Forceer een profiel uit profiles.json; leeg = automatisch")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Profielherkenningstolerantie in mm")
    # Strikte veiligheidsvalidatie is vanaf v0.5 niet meer uitschakelbaar.


def _report_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json-report",
        default="",
        help="Schrijf een machineleesbaar JSON-rapport van de volledige opdracht",
    )


def _ai_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--ai-provider",
        choices=["none", "local-rules", "openai"],
        default="none",
        help="AI is alleen adviserend; geometrie en productie-export blijven deterministisch",
    )
    parser.add_argument("--ai-model", default="gpt-5.6", help="Modelnaam voor de optionele cloudprovider")
    parser.add_argument(
        "--allow-cloud-ai",
        action="store_true",
        help="Expliciete toestemming om de geselecteerde PDF-pagina's naar de cloudprovider te sturen",
    )
    parser.add_argument("--ai-audit-log", default="", help="Lokale JSONL-auditlog zonder klantinhoud")


def _template_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--template", default="", help="Optioneel JSON-bestand met DrawingTemplate-velden")


def _load_template(path: str) -> DrawingTemplate:
    if not path:
        return DrawingTemplate()
    source = Path(path)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Tekeningtemplate kan niet worden gelezen: {exc}") from exc
    allowed = set(DrawingTemplate.__dataclass_fields__)
    return DrawingTemplate(**{key: value for key, value in data.items() if key in allowed})


def _ai_settings(args: argparse.Namespace) -> AISettings:
    return AISettings(
        provider=getattr(args, "ai_provider", "none"),
        model=getattr(args, "ai_model", "gpt-5.6"),
        allow_cloud=bool(getattr(args, "allow_cloud_ai", False)),
        audit_log=getattr(args, "ai_audit_log", ""),
    )


def _write_aggregate_report(path: str, payload: dict[str, Any]) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"RAPPORT {target}")


def _print_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"     WAARSCHUWING: {warning}")


def _result_entry(source: Path, *, status: str, outputs: list[Path] | None = None, error: str = "", details: dict[str, Any] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "source": str(source),
        "status": status,
        "outputs": [str(item) for item in (outputs or [])],
        "error": error,
        "warnings": warnings or [],
        "details": details or {},
    }


def _exception_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, CWSError):
        return exc.to_dict()
    return {
        "code": "CWS-9001",
        "message": str(exc),
        "type": type(exc).__name__,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME}: NC1/DSTV ↔ STEP ↔ IFC ↔ technische PDF + projecten/productie"
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("nc1-to-step", help="Converteer .nc/.nc1 naar STEP")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _report_arg(p)

    p = sub.add_parser("step-to-nc1", help="Converteer STEP-platen en standaardprofielen naar DSTV/NC1")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)
    _report_arg(p)

    p = sub.add_parser("ifc-to-dstv", help="Converteer IFC-elementen naar meerdere DSTV/NC1-bestanden + manifest")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)
    _report_arg(p)

    p = sub.add_parser("dstv-to-ifc", help="Converteer .nc/.nc1 naar IFC")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    _report_arg(p)

    p = sub.add_parser("ifc-to-step", help="Converteer IFC naar STEP")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _report_arg(p)

    p = sub.add_parser("step-to-ifc", help="Converteer STEP naar IFC")
    p.add_argument("inputs", nargs="+", help="STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    _report_arg(p)

    p = sub.add_parser("nc1-to-pdf", help="Maak een vectoriële Trusted Converter PDF uit NC1/DSTV")
    p.add_argument("inputs", nargs="+", help="NC/NC1-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _template_args(p)
    _report_arg(p)

    p = sub.add_parser("step-to-pdf", help="Maak een vectoriële Trusted Converter PDF uit STEP")
    p.add_argument("inputs", nargs="+", help="STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    p.add_argument("--profile", default="")
    p.add_argument("--tolerance", type=float, default=1.0)
    _template_args(p)
    _report_arg(p)

    p = sub.add_parser("ifc-to-pdf", help="Maak één of meer technische PDF's uit IFC")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    _template_args(p)
    _report_arg(p)

    p = sub.add_parser("pdf-analyze", help="Analyseer Trusted of externe technische PDF en schrijf een reviewrapport")
    p.add_argument("inputs", nargs="+", help="PDF-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap voor JSON-rapporten")
    _ai_args(p)
    _report_arg(p)

    p = sub.add_parser("pdf-review", help="Pas expliciete menselijke review toe en maak een Trusted Converter PDF")
    p.add_argument("input", help="Externe technische PDF")
    p.add_argument("--review", required=True, help="JSON-bestand met bevestigingen/correcties")
    p.add_argument("-o", "--output", required=True, help="Uitvoer-PDF met embedded exact model")
    _ai_args(p)
    _template_args(p)
    _report_arg(p)

    for command, help_text in (
        ("pdf-to-nc1", "Converteer Trusted/volledig gevalideerde PDF naar NC1"),
        ("pdf-to-step", "Converteer Trusted/volledig gevalideerde PDF naar STEP"),
        ("pdf-to-ifc", "Converteer Trusted/volledig gevalideerde PDF naar IFC"),
    ):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("inputs", nargs="+", help="PDF-bestanden of mappen")
        p.add_argument("-o", "--output", required=True, help="Uitvoermap")
        p.add_argument("--material", default="S355JR")
        _ai_args(p)
        _report_arg(p)

    p = sub.add_parser("excel", help="Bepaal hoeveelheden uit IFC/STEP en schrijf Excel")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Excelbestand (.xlsx)")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")
    _report_arg(p)

    p = sub.add_parser("quantities", help="Toon hoeveelheden uit IFC/STEP als tekst")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")
    _report_arg(p)

    p = sub.add_parser("inspect-model", help="Maak een deterministische IFC/STEP-importnulmeting")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("--geometry", action="store_true", help="Lees STEP ook als CAD-solid voor volume, oppervlak en bbox")
    p.add_argument("--json-report", required=True, help="Uitvoerbestand voor de complete JSON-nulmeting")

    p = sub.add_parser(
        "project-new",
        aliases=["project-create"],
        help="Maak een nieuw draagbaar CWS Convertor-project",
    )
    p.add_argument("project", help="Doelbestand; .cwscproj wordt zo nodig toegevoegd")
    p.add_argument("--name", required=True, help="Projectnaam")
    p.add_argument("--customer", "--client", dest="customer", default="", help="Klant/opdrachtgever")
    p.add_argument("--order", default="", help="Order- of werknummer")
    p.add_argument("--description", default="", help="Projectomschrijving")
    p.add_argument("--phase", default="", help="Projectfase")
    p.add_argument("--user", default="", help="Gebruiker voor auditlog")
    _report_arg(p)

    p = sub.add_parser("project-info", help="Toon projectmetadata, statussen en aantallen")
    p.add_argument("project", help=".cwscproj-projectbestand")
    p.add_argument("--json", action="store_true", help="Schrijf de informatie als JSON naar stdout")
    _report_arg(p)

    p = sub.add_parser(
        "project-import-baseline",
        aliases=["project-add-source"],
        help="Registreer IFC/STEP-bronnen en voer de veilige importnulmeting uit",
    )
    p.add_argument("project", help="Bestaand .cwscproj-projectbestand")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("--geometry", action="store_true", help="Lees STEP ook als CAD-solid voor geometrienulmeting")
    p.add_argument("--no-embed", action="store_true", help="Sla hash/pad op zonder bronbestand in te sluiten")
    p.add_argument("--user", default="", help="Gebruiker voor auditlog")
    p.add_argument("--baseline-report", default="", help="Optioneel afzonderlijk JSON-rapport")
    _report_arg(p)

    p = sub.add_parser("project-sources", help="Toon alle bronbestanden en importstrategieën")
    p.add_argument("project", help=".cwscproj-projectbestand")
    p.add_argument("--json", action="store_true", help="Schrijf de lijst als JSON naar stdout")
    _report_arg(p)

    p = sub.add_parser("project-verify", help="Controleer ZIP, hashes, SQLite en Project Model")
    p.add_argument("project", help=".cwscproj-projectbestand")
    p.add_argument("--json", action="store_true", help="Schrijf het verificatierapport als JSON")
    _report_arg(p)

    p = sub.add_parser("project-export-json", help="Exporteer het canonieke Project Model als JSON")
    p.add_argument("project", help=".cwscproj-projectbestand")
    p.add_argument("-o", "--output", required=True, help="Uitvoerbestand (.json)")
    _report_arg(p)

    p = sub.add_parser("project-extract-source", help="Pak een ingesloten IFC/STEP-bron veilig uit")
    p.add_argument("project", help=".cwscproj-projectbestand")
    p.add_argument("source_id", help="Interne bron-ID uit project-sources")
    p.add_argument("-o", "--output", required=True, help="Uitvoerbestand of uitvoermap")
    p.add_argument("--overwrite", action="store_true")
    _report_arg(p)

    p = sub.add_parser("project-recover", help="Herstel de nieuwste geldige autosave")
    p.add_argument("project", help="Hoofdproject waarvoor een autosave bestaat")
    p.add_argument("-o", "--output", default="", help="Optioneel ander herstelbestand")
    _report_arg(p)

    p = sub.add_parser(
        "project-migrate",
        help="Schrijf een oud project expliciet als nieuw schema-2 .cwscproj-bestand",
    )
    p.add_argument("project", help="Oud of read-only .cwscproj-projectbestand")
    p.add_argument("-o", "--output", required=True, help="Nieuw doelbestand; bron wordt niet gewijzigd")
    _report_arg(p)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    failures = 0
    review_required = 0
    entries: list[dict[str, Any]] = []
    files: list[Path] = []

    # Project commands use exactly the same Project Model and package service
    # as the GUI.  Baseline registration is atomic: a failing source leaves the
    # existing .cwscproj untouched.
    service = ProjectService()

    if args.command in {"project-new", "project-create"}:
        try:
            package = service.create_project(
                args.project,
                project_name=args.name,
                description=args.description,
                customer=args.customer,
                order_number=args.order,
                project_phase=args.phase,
                created_by=args.user or "cli",
            )
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "project_file": str(package.path),
                "project": package.project.summary(),
                "manifest": package.manifest,
            }
            print(f"OK   Nieuw project: {package.path}")
            print(f"     Project-ID: {package.project.project_id}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT project maken: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-info":
        try:
            info = service.project_info(args.project)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                **info,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                summary = info["summary"]
                counts = summary["entity_counts"]
                print(f"{APP_NAME} project: {summary['project_name']}")
                print(f"Bestand: {info['path']}")
                print(
                    f"Status: {summary['status']} | bronnen: {summary['source_count']} | "
                    f"assemblies: {counts['assembly']} | onderdelen: {counts['part']}"
                )
                print(f"Blokkerende controles: {summary['blocking_issue_count']}")
                print(f"Projecthash: {summary['semantic_sha256']}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT project lezen: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-sources":
        try:
            info = service.project_info(args.project)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "project_file": info["path"],
                "sources": info["sources"],
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                for item in info["sources"]:
                    gate = "VRIJ" if item["production_export_allowed"] else "GEBLOKKEERD"
                    print(
                        f"{item['source_id']}\t{item['source_format']}\t"
                        f"{item['import_strategy']}\t{gate}\t{item['file_name']}\t{item['sha256']}"
                    )
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT projectbronnen lezen: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-verify":
        try:
            verification = service.verify_project(args.project)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "verification": verification,
                "checks": {
                    "zip_crc": True,
                    "manifest_entries_sha256": True,
                    "sqlite_integrity": True,
                    "snapshot_sha256": True,
                    "project_model": True,
                    "entity_references": True,
                },
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(f"GELDIG {verification['path']}")
                print(f"Projecthash: {verification['project']['semantic_sha256']}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"ONGELDIG project: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-export-json":
        try:
            with ProjectSession.open(args.project, read_only=True) as session:
                target = session.export_json(args.output)
                summary = session.project.summary()
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "output": str(target),
                "project": summary,
            }
            print(f"OK   Project Model JSON: {target}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT Project Model exporteren: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-extract-source":
        try:
            with ProjectSession.open(args.project, read_only=True) as session:
                record = session.project.sources.get(args.source_id)
                if record is None:
                    raise ProjectPackageError(f"Onbekende bron-ID {args.source_id}")
                output = Path(args.output)
                target = output / record.file_name if output.is_dir() or not output.suffix else output
                if target.exists() and not args.overwrite:
                    raise ProjectPackageError(f"Doelbestand bestaat al: {target}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if session.package is None:
                    raise ProjectPackageError("Projectpakket is niet geopend")
                extracted = session.package.extract_source(args.source_id, target)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "output": str(extracted),
            }
            print(f"OK   Bron uitgepakt: {extracted}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT bron uitpakken: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-recover":
        try:
            target = service.recover_autosave(args.project, args.output or None)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "output": str(target),
            }
            print(f"OK   Project hersteld: {target}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT autosave herstellen: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "project-migrate":
        try:
            package = service.migrate_project(args.project, args.output)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "source": str(args.project),
                "output": str(package.path),
                "project": package.project.summary(),
                "manifest": package.manifest,
            }
            print(f"OK   Project gemigreerd: {package.path}")
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(f"FOUT project migreren: {exc}", file=sys.stderr)
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "inspect-model":
        files = list(_iter_inputs(args.inputs, {".ifc", ".step", ".stp"}))
        if not files:
            print("Geen geschikte IFC/STEP-bestanden gevonden.", file=sys.stderr)
            return EXIT_NO_INPUT
        analyses = []
        for source in files:
            try:
                analysis = inspect_model_file(source, include_geometry=args.geometry)
                analyses.append(analysis)
                print(
                    f"OK   {source.name} | {analysis.import_strategy.value} | "
                    f"producten {analysis.product_count} | solids {analysis.solid_count}"
                )
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
        if failures:
            return EXIT_FAILED
        report = write_baseline_report(analyses, args.json_report)
        print(f"RAPPORT {report}")
        return EXIT_OK

    if args.command in {"project-import-baseline", "project-add-source"}:
        files = list(_iter_inputs(args.inputs, {".ifc", ".step", ".stp"}))
        if not files:
            print("Geen geschikte IFC/STEP-bestanden gevonden.", file=sys.stderr)
            return EXIT_NO_INPUT
        try:
            results = service.register_sources(
                args.project,
                files,
                embed_sources=not args.no_embed,
                include_step_geometry=args.geometry,
                user=args.user or "cli",
            )
            for result in results:
                analysis = result.analysis
                print(
                    f"OK   {analysis.file_name} | {analysis.import_strategy.value} | "
                    f"producten {analysis.product_count} | solids {analysis.solid_count}"
                )
            report_path = ""
            if args.baseline_report:
                report_path = str(
                    write_baseline_report(
                        [result.analysis for result in results],
                        args.baseline_report,
                    )
                )
                print(f"RAPPORT {report_path}")
            info = service.project_info(args.project)
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "passed",
                "project_file": info["path"],
                "project": info["summary"],
                "production_export_allowed": False,
                "semantic_import_pending": True,
                "analyses": [result.to_dict() for result in results],
                "baseline_report": report_path,
            }
            _write_aggregate_report(args.json_report, payload)
            return EXIT_OK
        except Exception as exc:
            payload = {
                "converter_version": APP_VERSION,
                "command": args.command,
                "status": "failed",
                "error": _exception_payload(exc),
            }
            print(
                "FOUT projectimport; bestaand project is niet gedeeltelijk opgeslagen: "
                f"{exc}",
                file=sys.stderr,
            )
            _write_aggregate_report(args.json_report, payload)
            return EXIT_FAILED

    if args.command == "nc1-to-step":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".nc", ".nc1"}))
        for source in files:
            try:
                target = output / f"{source.stem}.step"
                part = convert_nc1_to_step(source, target)
                print(f"OK   {source.name} -> {target.name}")
                _print_warnings(part.warnings)
                entries.append(_result_entry(source, status="passed", outputs=[target], warnings=list(part.warnings)))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command == "step-to-nc1":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        database = ProfileDatabase()
        files = list(_iter_inputs(args.inputs, {".step", ".stp"}))
        for source in files:
            try:
                target = output / f"{source.stem}.nc1"
                result = step_to_nc1(
                    source,
                    target,
                    material=args.material,
                    order_number=args.order,
                    profile_database=database,
                    preferred_profile=args.profile,
                    tolerance_mm=args.tolerance,
                    strict_validation=True,
                )
                print(f"OK   {source.name} -> {target.name} | {result.profile_designation} | confidence {result.confidence:.0%} | volume {result.volume_delta_percent:+.6f}%")
                _print_warnings(result.warnings)
                entries.append(_result_entry(source, status="passed", outputs=[target], warnings=result.warnings, details={"profile": result.profile_designation, "confidence": result.confidence, "volume_delta_percent": result.volume_delta_percent}))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command == "ifc-to-dstv":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        database = ProfileDatabase()
        files = list(_iter_inputs(args.inputs, {".ifc"}))
        for source in files:
            try:
                result = ifc_to_dstv(
                    source,
                    output / source.stem,
                    material=args.material,
                    order_number=args.order,
                    profile_database=database,
                    preferred_profile=args.profile,
                    tolerance_mm=args.tolerance,
                    strict_validation=True,
                )
                print(f"OK   {source.name} -> {len(result.outputs)} uitvoerbestand(en)")
                for target in result.outputs:
                    print(f"     UITVOER: {target}")
                _print_warnings(result.warnings)
                for failed in result.failures:
                    print(f"     NIET GECONVERTEERD: {failed}")
                failures += len(result.failures)
                entries.append(_result_entry(source, status="passed" if not result.failures else "partial", outputs=result.outputs, warnings=result.warnings, details=result.details, error=" | ".join(result.failures)))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command in {"dstv-to-ifc", "ifc-to-step", "step-to-ifc"}:
        mapping: dict[str, tuple[set[str], Callable[[Path, Path], Any], str]] = {
            "dstv-to-ifc": ({".nc", ".nc1"}, lambda source, target: dstv_to_ifc(source, target, material=args.material), ".ifc"),
            "ifc-to-step": ({".ifc"}, lambda source, target: ifc_to_step(source, target), ".step"),
            "step-to-ifc": ({".step", ".stp"}, lambda source, target: step_to_ifc(source, target, material=args.material), ".ifc"),
        }
        extensions, action, suffix = mapping[args.command]
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, extensions))
        for source in files:
            try:
                target = output / f"{source.stem}{suffix}"
                result = action(source, target)
                print(f"OK   {source.name} -> {result.primary_output.name if result.primary_output else len(result.outputs)}")
                _print_warnings(result.warnings)
                entries.append(_result_entry(source, status="passed", outputs=result.outputs, warnings=result.warnings, details=result.details))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command in {"nc1-to-pdf", "step-to-pdf", "ifc-to-pdf"}:
        extension_map = {
            "nc1-to-pdf": {".nc", ".nc1"},
            "step-to-pdf": {".step", ".stp"},
            "ifc-to-pdf": {".ifc"},
        }
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, extension_map[args.command]))
        template = _load_template(args.template)
        for source in files:
            try:
                if args.command == "nc1-to-pdf":
                    result = nc1_to_pdf(source, output / f"{source.stem}.pdf", template=template)
                elif args.command == "step-to-pdf":
                    result = step_to_pdf(source, output / f"{source.stem}.pdf", material=args.material, preferred_profile=args.profile, tolerance_mm=args.tolerance, template=template)
                else:
                    result = ifc_to_pdf(source, output / source.stem, material=args.material, template=template)
                print(f"OK   {source.name} -> {len(result.outputs)} PDF-bestand(en)")
                for target in result.outputs:
                    print(f"     UITVOER: {target}")
                _print_warnings(result.warnings)
                entries.append(_result_entry(source, status="passed", outputs=result.outputs, warnings=result.warnings, details=result.details))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command == "pdf-analyze":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".pdf"}))
        settings = _ai_settings(args)
        for source in files:
            try:
                analysis = analyze_pdf(source, ai_settings=settings)
                report = write_analysis_report(analysis, output / f"{source.stem}.analysis.json")
                status = "validated" if analysis.production_export_allowed else "review_required"
                print(f"OK   {source.name} -> {report.name} | {analysis.mode} | {status}")
                for question in analysis.part.validation.blocking_questions():
                    print(f"     VRAAG: {question.prompt}")
                if not analysis.production_export_allowed:
                    review_required += 1
                entries.append(_result_entry(source, status=status, outputs=[report], warnings=analysis.warnings, details={"mode": analysis.mode, "production_export_allowed": analysis.production_export_allowed, "question_count": len(analysis.part.validation.blocking_questions())}))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command == "pdf-review":
        files = [Path(args.input)] if Path(args.input).is_file() else []
        if files:
            source = files[0]
            try:
                result = review_external_pdf(
                    source,
                    args.review,
                    args.output,
                    ai_settings=_ai_settings(args),
                    template=_load_template(args.template),
                )
                print(f"OK   {source.name} -> {result.primary_output}")
                _print_warnings(result.warnings)
                entries.append(_result_entry(source, status="passed", outputs=result.outputs, warnings=result.warnings, details=result.details))
            except ExternalPDFExportBlocked as exc:
                review_required += 1
                print(f"CONTROLE VEREIST {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="review_required", error=str(exc)))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command in {"pdf-to-nc1", "pdf-to-step", "pdf-to-ifc"}:
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".pdf"}))
        settings = _ai_settings(args)
        suffix = {"pdf-to-nc1": ".nc1", "pdf-to-step": ".step", "pdf-to-ifc": ".ifc"}[args.command]
        for source in files:
            try:
                target = output / f"{source.stem}{suffix}"
                if args.command == "pdf-to-nc1":
                    result = pdf_to_nc1(source, target, ai_settings=settings)
                elif args.command == "pdf-to-step":
                    result = pdf_to_step(source, target, ai_settings=settings)
                else:
                    result = pdf_to_ifc(source, target, material=args.material, ai_settings=settings)
                print(f"OK   {source.name} -> {target.name}")
                _print_warnings(result.warnings)
                entries.append(_result_entry(source, status="passed", outputs=result.outputs, warnings=result.warnings, details=result.details))
            except ExternalPDFExportBlocked as exc:
                review_required += 1
                print(f"CONTROLE VEREIST {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="review_required", error=str(exc)))
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)
                entries.append(_result_entry(source, status="failed", error=str(exc)))

    elif args.command in {"excel", "quantities"}:
        files = list(_iter_inputs(args.inputs, {".ifc", ".step", ".stp"}))
        if files:
            try:
                materials = MaterialDatabase()
                profiles = ProfileDatabase()
                analysis = analyze_files(files, fallback_material=args.material, material_database=materials, profile_database=profiles)
                print(f"Regels: {len(analysis.items)} | totaal aantal: {analysis.total_quantity} | massa: {analysis.total_mass_kg:.3f} kg")
                for item in analysis.items:
                    print(f"{item.source_file}\t{item.name}\t{item.object_type}\t{item.profile}\t{item.material_code}\t{item.volume_mm3:.1f} mm3\t{item.mass_kg:.3f} kg")
                for warning in analysis.warnings:
                    print(f"WAARSCHUWING: {warning}")
                outputs: list[Path] = []
                if args.command == "excel":
                    target = export_excel(args.output, analysis, material_database=materials, profile_database=profiles)
                    outputs = [target]
                    print(f"EXCEL {target}")
                entries.append({"status": "passed", "outputs": [str(item) for item in outputs], "details": {"items": len(analysis.items), "total_quantity": analysis.total_quantity, "total_mass_kg": analysis.total_mass_kg}, "warnings": analysis.warnings})
            except Exception as exc:
                failures += 1
                print(f"FOUT hoeveelheden: {exc}", file=sys.stderr)
                entries.append({"status": "failed", "error": str(exc)})

    if not files:
        print("Geen geschikte invoerbestanden gevonden.", file=sys.stderr)
        return EXIT_NO_INPUT

    payload = {
        "converter_version": __version__,
        "command": args.command,
        "strict_validation": True,
        "summary": {
            "inputs": len(files),
            "failures": failures,
            "review_required": review_required,
        },
        "results": entries,
    }
    _write_aggregate_report(getattr(args, "json_report", ""), payload)
    if failures:
        return EXIT_FAILED
    if review_required:
        return EXIT_REVIEW_REQUIRED
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
