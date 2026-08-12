from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys
from typing import Any, Callable

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="NC1/DSTV ↔ STEP ↔ IFC ↔ technische PDF Converter + hoeveelheden/Excel"
    )
    parser.add_argument("--version", action="version", version=__version__)
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    failures = 0
    review_required = 0
    entries: list[dict[str, Any]] = []
    files: list[Path] = []

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
