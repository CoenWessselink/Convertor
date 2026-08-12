from __future__ import annotations

import argparse
from pathlib import Path
import sys

from conversion import __version__, convert_nc1_to_step, step_to_nc1
from ifc_support import dstv_to_ifc, ifc_to_dstv, ifc_to_step, step_to_ifc
from material_database import MaterialDatabase
from profile_database import ProfileDatabase
from quantities import analyze_files, export_excel


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
    parser.add_argument("--no-strict-validation", action="store_true", help="Schakel harde volume-afkeurgrens uit")


def main() -> int:
    parser = argparse.ArgumentParser(description="NC1/DSTV ↔ STEP ↔ IFC Converter + hoeveelheden/Excel")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("nc1-to-step", help="Converteer .nc/.nc1 naar STEP")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")

    p = sub.add_parser("step-to-nc1", help="Converteer STEP-platen en standaardprofielen naar DSTV/NC1")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)

    p = sub.add_parser("ifc-to-dstv", help="Converteer IFC-elementen naar meerdere DSTV/NC1-bestanden + manifest")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    _common_reverse_args(p)

    p = sub.add_parser("dstv-to-ifc", help="Converteer .nc/.nc1 naar IFC")
    p.add_argument("inputs", nargs="+", help="Bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")

    p = sub.add_parser("ifc-to-step", help="Converteer IFC naar STEP")
    p.add_argument("inputs", nargs="+", help="IFC-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")

    p = sub.add_parser("step-to-ifc", help="Converteer STEP naar IFC")
    p.add_argument("inputs", nargs="+", help="STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Uitvoermap")
    p.add_argument("--material", default="S355JR")

    p = sub.add_parser("excel", help="Bepaal hoeveelheden uit IFC/STEP en schrijf Excel")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("-o", "--output", required=True, help="Excelbestand (.xlsx)")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")

    p = sub.add_parser("quantities", help="Toon hoeveelheden uit IFC/STEP als tekst")
    p.add_argument("inputs", nargs="+", help="IFC/STEP-bestanden of mappen")
    p.add_argument("--material", default="S355JR", help="Fallback materiaal")

    args = parser.parse_args()
    failures = 0

    if args.command == "nc1-to-step":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".nc", ".nc1"}))
        for source in files:
            try:
                target = output / f"{source.stem}.step"
                part = convert_nc1_to_step(source, target)
                print(f"OK   {source.name} -> {target.name}")
                for warning in part.warnings:
                    print(f"     WAARSCHUWING: {warning}")
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

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
                    strict_validation=not args.no_strict_validation,
                )
                print(f"OK   {source.name} -> {target.name} | {result.profile_designation} | confidence {result.confidence:.0%} | volume {result.volume_delta_percent:+.6f}%")
                for warning in result.warnings:
                    print(f"     WAARSCHUWING: {warning}")
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

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
                    strict_validation=not args.no_strict_validation,
                )
                print(f"OK   {source.name} -> {len(result.outputs)} uitvoerbestand(en)")
                for target in result.outputs:
                    print(f"     UITVOER: {target}")
                for warning in result.warnings:
                    print(f"     WAARSCHUWING: {warning}")
                for failed in result.failures:
                    print(f"     NIET GECONVERTEERD: {failed}")
                failures += len(result.failures)
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "dstv-to-ifc":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".nc", ".nc1"}))
        for source in files:
            try:
                result = dstv_to_ifc(source, output / f"{source.stem}.ifc", material=args.material)
                print(f"OK   {source.name} -> {result.primary_output.name if result.primary_output else len(result.outputs)}")
                for warning in result.warnings:
                    print(f"     WAARSCHUWING: {warning}")
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "ifc-to-step":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".ifc"}))
        for source in files:
            try:
                result = ifc_to_step(source, output / f"{source.stem}.step")
                print(f"OK   {source.name} -> {result.primary_output.name if result.primary_output else len(result.outputs)}")
                for warning in result.warnings:
                    print(f"     WAARSCHUWING: {warning}")
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

    elif args.command == "step-to-ifc":
        output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
        files = list(_iter_inputs(args.inputs, {".step", ".stp"}))
        for source in files:
            try:
                result = step_to_ifc(source, output / f"{source.stem}.ifc", material=args.material)
                print(f"OK   {source.name} -> {result.primary_output.name if result.primary_output else len(result.outputs)}")
                for warning in result.warnings:
                    print(f"     WAARSCHUWING: {warning}")
            except Exception as exc:
                failures += 1
                print(f"FOUT {source.name}: {exc}", file=sys.stderr)

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
                if args.command == "excel":
                    target = export_excel(args.output, analysis, material_database=materials, profile_database=profiles)
                    print(f"EXCEL {target}")
            except Exception as exc:
                failures += 1
                print(f"FOUT hoeveelheden: {exc}", file=sys.stderr)
        else:
            print("Geen geschikte invoerbestanden gevonden.", file=sys.stderr)
            return 2

    files = locals().get("files", [])
    if not files:
        print("Geen geschikte invoerbestanden gevonden.", file=sys.stderr)
        return 2
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
