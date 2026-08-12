from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

from ai_support import LocalSemanticProvider, OpenAIResponsesProvider
from conversion import __version__, convert_nc1_to_step, step_to_nc1
from ifc_support import dstv_to_ifc, ifc_to_dstv, ifc_to_step, step_to_ifc
from material_database import MaterialDatabase
from pdf_support import (
    PDFProductionBlockedError,
    analyze_external_pdf,
    ifc_to_pdf,
    inspect_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    step_to_pdf,
)
from profile_database import ProfileDatabase
from quantities import analyze_files, export_excel


def _iter_inputs(items: list[str], extensions: set[str]):
    seen: set[Path] = set()
    for item in items:
        path = Path(item)
        if path.is_dir():
            for candidate in sorted(path.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() in extensions and candidate not in seen:
                    seen.add(candidate)
                    yield candidate
        elif path.is_file() and (not extensions or path.suffix.lower() in extensions):
            if path not in seen:
                seen.add(path)
                yield path
        elif path.exists():
            print(f"WAARSCHUWING: overgeslagen wegens extensie: {path}", file=sys.stderr)
        else:
            print(f"WAARSCHUWING: niet gevonden: {path}", file=sys.stderr)


def _common_reverse_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--material", default="S355JR", help="Materiaal voor uitvoer/quantities")
    parser.add_argument("--order", default="STEP", help="Ordernummer voor DSTV/NC1-kopgegevens")
    parser.add_argument("--profile", default="", help="Forceer profiel uit profiles.json; leeg = automatisch")
    parser.add_argument("--tolerance", type=float, default=1.0, help="Profielherkenningstolerantie in mm")
    parser.add_argument(
        "--strict-validation",
        action="store_true",
        default=True,
        help="Altijd actief: onbetrouwbare productie-uitvoer wordt geweigerd",
    )


def _add_report_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Schrijf machineleesbare JSON naar stdout")
    parser.add_argument("--report", help="Schrijf het volledige JSON-rapport naar dit bestand")


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(v) for v in value]
    return value


def _emit_report(args: argparse.Namespace, records: list[dict[str, Any]]) -> None:
    report = {
        "software_version": __version__,
        "command": args.command,
        "records": records,
        "successes": sum(1 for item in records if item.get("status") == "ok"),
        "blocked": sum(1 for item in records if item.get("status") == "blocked"),
        "failures": sum(1 for item in records if item.get("status") == "error"),
    }
    raw = json.dumps(_serialize(report), ensure_ascii=False, indent=2, sort_keys=True)
    if getattr(args, "json", False):
        print(raw)
    if getattr(args, "report", None):
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(raw + "\n", encoding="utf-8")
        if not getattr(args, "json", False):
            print(f"RAPPORT {target}")


def _record_ok(source: Path, outputs: Iterable[Path], **details: Any) -> dict[str, Any]:
    return {
        "status": "ok",
        "source": str(source),
        "outputs": [str(item) for item in outputs],
        "details": details,
    }


def _record_error(source: Path, exc: Exception, status: str = "error") -> dict[str, Any]:
    return {"status": status, "source": str(source), "error": str(exc)}


def _ai_provider(args: argparse.Namespace):
    if args.ai_provider == "openai":
        return OpenAIResponsesProvider(
            model=args.ai_model,
            api_key=args.api_key or os.environ.get("OPENAI_API_KEY", ""),
        )
    return LocalSemanticProvider()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NC1/DSTV <-> STEP <-> IFC <-> Trusted PDF Converter + hoeveelheden/Excel"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("nc1-to-step", help="Converteer .nc/.nc1 naar STEP")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _add_report_args(p)

    p = sub.add_parser("step-to-nc1", help="Converteer STEP-platen en standaardprofielen naar DSTV/NC1")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)
    _add_report_args(p)

    p = sub.add_parser("ifc-to-dstv", help="Converteer IFC-elementen naar DSTV/NC1 + manifest")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)
    _add_report_args(p)

    p = sub.add_parser("dstv-to-ifc", help="Converteer .nc/.nc1 naar IFC")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    _add_report_args(p)

    p = sub.add_parser("ifc-to-step", help="Converteer IFC naar STEP")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _add_report_args(p)

    p = sub.add_parser("step-to-ifc", help="Converteer STEP naar IFC")
    p.add_argument("inputs", nargs="+", help="STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    _add_report_args(p)

    p = sub.add_parser("nc1-to-pdf", help="Maak vectoriële Trusted Converter PDF uit NC1/DSTV")
    p.add_argument("inputs", nargs="+", help="NC1-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--template", help="Bedrijfstemplate JSON")
    _add_report_args(p)

    p = sub.add_parser("step-to-pdf", help="Maak vectoriële Trusted Converter PDF uit STEP")
    p.add_argument("inputs", nargs="+", help="STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")
    p.add_argument("--template", help="Bedrijfstemplate JSON")
    _add_report_args(p)

    p = sub.add_parser("ifc-to-pdf", help="Maak per IFC-onderdeel een technische PDF")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--template", help="Bedrijfstemplate JSON")
    _add_report_args(p)

    for command, help_text in (
        ("pdf-to-nc1", "Herstel veilig NC1 uit een ongewijzigde Trusted Converter PDF"),
        ("pdf-to-step", "Herstel veilig STEP uit een ongewijzigde Trusted Converter PDF"),
        ("pdf-to-ifc", "Herstel veilig IFC uit een ongewijzigde Trusted Converter PDF"),
    ):
        p = sub.add_parser(command, help=help_text)
        p.add_argument("inputs", nargs="+", help="PDF-bestanden of mappen")
        p.add_argument("-o", "--output", required=True, help="Uitvoermap")
        _add_report_args(p)

    p = sub.add_parser("pdf-inspect", help="Controleer Trusted PDF-payload, hashes en zichtbare tekening")
    p.add_argument("inputs", nargs="+", help="PDF-bestanden of mappen")
    _add_report_args(p)

    p = sub.add_parser("pdf-analyze", help="Analyseer externe PDF lokaal of optioneel met cloud-AI")
    p.add_argument("inputs", nargs="+", help="PDF-bestanden of mappen")
    p.add_argument("--ai-provider", choices=["local", "openai"], default="local")
    p.add_argument("--allow-cloud-ai", action="store_true", help="Expliciete toestemming voor externe verwerking")
    p.add_argument("--ai-model", default="", help="Expliciet OpenAI-model; verplicht bij provider=openai")
    p.add_argument("--api-key", default="", help="Optioneel; bij voorkeur OPENAI_API_KEY gebruiken")
    p.add_argument("--report-dir", help="Schrijf één uitgebreid JSON-rapport per PDF")
    _add_report_args(p)

    p = sub.add_parser("excel", help="Bepaal hoeveelheden uit IFC/STEP en schrijf Excel")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Excelbestand (.xlsx)")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")
    _add_report_args(p)

    p = sub.add_parser("quantities", help="Toon hoeveelheden uit IFC/STEP")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")
    _add_report_args(p)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    records: list[dict[str, Any]] = []
    output = Path(getattr(args, "output", "."))
    if hasattr(args, "output") and args.command != "excel":
        output.mkdir(parents=True, exist_ok=True)

    extension_map = {
        "nc1-to-step": {".nc", ".nc1"},
        "step-to-nc1": {".step", ".stp"},
        "ifc-to-dstv": {".ifc"},
        "dstv-to-ifc": {".nc", ".nc1"},
        "ifc-to-step": {".ifc"},
        "step-to-ifc": {".step", ".stp"},
        "nc1-to-pdf": {".nc", ".nc1"},
        "step-to-pdf": {".step", ".stp"},
        "ifc-to-pdf": {".ifc"},
        "pdf-to-nc1": {".pdf"},
        "pdf-to-step": {".pdf"},
        "pdf-to-ifc": {".pdf"},
        "pdf-inspect": {".pdf"},
        "pdf-analyze": {".pdf"},
        "excel": {".ifc", ".step", ".stp"},
        "quantities": {".ifc", ".step", ".stp"},
    }
    files = list(_iter_inputs(args.inputs, extension_map[args.command]))
    if not files:
        print("Geen geschikte invoerbestanden gevonden.", file=sys.stderr)
        return 2

    if args.command == "nc1-to-step":
        for source in files:
            try:
                target = output / f"{source.stem}.step"
                part = convert_nc1_to_step(source, target)
                records.append(_record_ok(source, [target], warnings=part.warnings))
                if not args.json:
                    print(f"OK   {source.name} -> {target.name}")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "step-to-nc1":
        database = ProfileDatabase()
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
                records.append(_record_ok(source, [target], **_serialize(result)))
                if not args.json:
                    print(
                        f"OK   {source.name} -> {target.name} | {result.profile_designation} | "
                        f"confidence {result.confidence:.0%} | volume {result.volume_delta_percent:+.6f}%"
                    )
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "ifc-to-dstv":
        database = ProfileDatabase()
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
                status = "ok" if not result.failures else "error"
                record = _record_ok(source, result.outputs, warnings=result.warnings, failures=result.failures, details=result.details)
                record["status"] = status
                records.append(record)
                if not args.json:
                    print(f"OK   {source.name} -> {len(result.outputs)} uitvoerbestand(en)")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "dstv-to-ifc":
        for source in files:
            try:
                result = dstv_to_ifc(source, output / f"{source.stem}.ifc", material=args.material)
                records.append(_record_ok(source, result.outputs, warnings=result.warnings, details=result.details))
                if not args.json:
                    print(f"OK   {source.name} -> {result.primary_output}")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "ifc-to-step":
        for source in files:
            try:
                result = ifc_to_step(source, output / f"{source.stem}.step")
                records.append(_record_ok(source, result.outputs, warnings=result.warnings, details=result.details))
                if not args.json:
                    print(f"OK   {source.name} -> {result.primary_output}")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "step-to-ifc":
        for source in files:
            try:
                result = step_to_ifc(source, output / f"{source.stem}.ifc", material=args.material)
                records.append(_record_ok(source, result.outputs, warnings=result.warnings, details=result.details))
                if not args.json:
                    print(f"OK   {source.name} -> {result.primary_output}")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command in {"nc1-to-pdf", "step-to-pdf", "ifc-to-pdf"}:
        for source in files:
            try:
                if args.command == "nc1-to-pdf":
                    result = nc1_to_pdf(source, output / f"{source.stem}.pdf", template=args.template)
                elif args.command == "step-to-pdf":
                    result = step_to_pdf(source, output / f"{source.stem}.pdf", material=args.material, template=args.template)
                else:
                    result = ifc_to_pdf(source, output / source.stem, template=args.template)
                records.append(_record_ok(source, result.outputs, classification=result.classification, warnings=result.warnings, details=result.details))
                if not args.json:
                    print(f"OK   {source.name} -> {len(result.outputs)} PDF-bestand(en)")
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command in {"pdf-to-nc1", "pdf-to-step", "pdf-to-ifc"}:
        suffix = {"pdf-to-nc1": ".nc1", "pdf-to-step": ".step", "pdf-to-ifc": ".ifc"}[args.command]
        converter = {"pdf-to-nc1": pdf_to_nc1, "pdf-to-step": pdf_to_step, "pdf-to-ifc": pdf_to_ifc}[args.command]
        for source in files:
            try:
                result = converter(source, output / f"{source.stem}{suffix}")
                records.append(_record_ok(source, result.outputs, classification=result.classification, warnings=result.warnings, details=result.details))
                if not args.json:
                    print(f"OK   {source.name} -> {result.primary_output}")
            except PDFProductionBlockedError as exc:
                records.append(_record_error(source, exc, status="blocked"))
                print(f"GEBLOKKEERD {source.name}: {exc}", file=sys.stderr)
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "pdf-inspect":
        for source in files:
            inspection = inspect_pdf(source)
            status = "ok" if inspection.trusted_exact or inspection.classification == "external" else "error"
            records.append(
                {
                    "status": status,
                    "source": str(source),
                    "classification": inspection.classification,
                    "trusted_exact": inspection.trusted_exact,
                    "warnings": inspection.warnings,
                    "errors": inspection.errors,
                    "details": inspection.details,
                }
            )
            if not args.json:
                print(f"{inspection.classification.upper():15} {source}")

    elif args.command == "pdf-analyze":
        provider = _ai_provider(args)
        report_dir = Path(args.report_dir) if args.report_dir else None
        if report_dir:
            report_dir.mkdir(parents=True, exist_ok=True)
        for source in files:
            try:
                analysis = analyze_external_pdf(
                    source,
                    ai_provider=provider,
                    cloud_consent=bool(args.allow_cloud_ai),
                )
                record = {
                    "status": "ok",
                    "source": str(source),
                    "production_export_allowed": analysis.part.validation.production_export_allowed,
                    "warnings": analysis.warnings,
                    "part_id": analysis.part.part_id,
                    "confidence": analysis.part.recognition.get("confidence"),
                    "unresolved_questions": len(analysis.part.validation.unresolved_questions),
                }
                records.append(record)
                if report_dir:
                    target = report_dir / f"{source.stem}_pdf_analysis.json"
                    target.write_text(
                        json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    record["analysis_report"] = str(target)
                if not args.json:
                    print(
                        f"OK   {source.name} | part {analysis.part.part_id} | "
                        f"productie={'JA' if analysis.part.validation.production_export_allowed else 'GEBLOKKEERD'}"
                    )
            except Exception as exc:
                records.append(_record_error(source, exc))
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command in {"excel", "quantities"}:
        try:
            materials = MaterialDatabase()
            profiles = ProfileDatabase()
            analysis = analyze_files(
                files,
                fallback_material=args.material,
                material_database=materials,
                profile_database=profiles,
            )
            output_files: list[Path] = []
            if args.command == "excel":
                target = export_excel(args.output, analysis, material_database=materials, profile_database=profiles)
                output_files.append(target)
            records.append(
                {
                    "status": "ok",
                    "source": [str(item) for item in files],
                    "outputs": [str(item) for item in output_files],
                    "details": {
                        "items": len(analysis.items),
                        "total_quantity": analysis.total_quantity,
                        "total_mass_kg": analysis.total_mass_kg,
                        "warnings": analysis.warnings,
                    },
                }
            )
            if not args.json:
                print(
                    f"Regels: {len(analysis.items)} | totaal aantal: {analysis.total_quantity} | "
                    f"massa: {analysis.total_mass_kg:.3f} kg"
                )
        except Exception as exc:
            records.append(_record_error(Path(";".join(str(item) for item in files)), exc))
            print(f"FOUT hoeveelheden: {exc}", file=sys.stderr)

    _emit_report(args, records)
    if any(item.get("status") == "error" for item in records):
        return 1
    if any(item.get("status") == "blocked" for item in records):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
