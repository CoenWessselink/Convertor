"""Volledige regressie- en focusroundtripvalidatie voor v0.5.

De runner schrijft per bestand meetresultaten naar JSON/CSV en bewaart alle
relevante tussenbestanden. Er wordt nergens een onveilige validatiebypass
gebruikt.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq

import converter as core
from canonical_model import extract_part_from_ifc
from conversion import __version__, build_shape, convert_nc1_to_step, step_to_nc1
from ifc_support import dstv_to_ifc, ifc_to_dstv, ifc_to_step, step_to_ifc
from profile_database import ProfileDatabase
from validation.geometric_compare import compare_step, shape_metrics, step_feature_summary
from validation.semantic_compare import compare_nc1, nc1_summary


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value):
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _find_reference(reference_folder: Path, stem: str, extensions: tuple[str, ...]) -> Path | None:
    for extension in extensions:
        candidate = reference_folder / f"{stem}{extension}"
        if candidate.exists():
            return candidate
    return None


def _direct_nc1_regression(
    files: list[Path],
    output: Path,
    reference_step: Path | None,
    database: ProfileDatabase,
) -> list[dict]:
    rows: list[dict] = []
    output.mkdir(parents=True, exist_ok=True)
    for source in files:
        target = output / f"{source.stem}.step"
        row = {"source": source.name, "route": "NC1->STEP", "status": "failed"}
        try:
            part = convert_nc1_to_step(source, target)
            source_shape = build_shape(part).val()
            target_shape = cq.importers.importStep(str(target)).val()
            source_metrics = {
                "volume_mm3": float(source_shape.Volume()),
                "area_mm2": float(source_shape.Area()),
            }
            target_metrics = shape_metrics(target)
            volume_delta = (
                (target_metrics["volume_mm3"] - source_metrics["volume_mm3"])
                / source_metrics["volume_mm3"]
                * 100.0
            )
            reference = (
                _find_reference(reference_step, source.stem, (".step", ".stp"))
                if reference_step
                else None
            )
            reference_delta = None
            if reference is not None:
                reference_metrics = shape_metrics(reference)
                reference_delta = (
                    (target_metrics["volume_mm3"] - reference_metrics["volume_mm3"])
                    / reference_metrics["volume_mm3"]
                    * 100.0
                )
            payload = None
            from canonical_model import extract_part_from_step

            payload = extract_part_from_step(target, strict=True)
            row.update(
                status="passed" if abs(volume_delta) <= 1e-9 and (reference_delta is None or abs(reference_delta) <= 1e-9) else "different",
                profile=part.header.profile,
                profile_type=part.header.profile_type,
                holes=len(part.holes),
                contours=len(part.contours),
                volume_delta_percent=volume_delta,
                reference_volume_delta_percent=reference_delta,
                payload_valid=payload is not None,
                output=str(target.relative_to(output.parent)),
                output_sha256=_sha256(target),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _direct_step_regression(
    files: list[Path],
    output: Path,
    reference_nc1: Path | None,
    database: ProfileDatabase,
) -> list[dict]:
    rows: list[dict] = []
    output.mkdir(parents=True, exist_ok=True)
    for source in files:
        target = output / f"{source.stem}.nc1"
        rebuilt_step = output / f"{source.stem}_rebuild.step"
        row = {"source": source.name, "route": "STEP->NC1", "status": "failed"}
        try:
            result = step_to_nc1(
                source,
                target,
                material="S355JR",
                order_number="STEP",
                profile_database=database,
                strict_validation=True,
            )
            convert_nc1_to_step(target, rebuilt_step)
            comparison = compare_step(source, rebuilt_step, profile_database=database)
            reference = (
                _find_reference(reference_nc1, source.stem, (".nc1", ".nc"))
                if reference_nc1
                else None
            )
            reference_equal = None
            if reference is not None:
                reference_comparison = compare_nc1(reference, target)
                # Materiaal/order kan bewust verschillen; voor v0.2-regressie tellen
                # productiefeatures en geometrie, niet de aangeleverde fallbackkop.
                reference_equal = bool(
                    reference_comparison["holes_equal"]
                    and reference_comparison["contours_equal"]
                    and reference_comparison["max_dimension_delta_mm"] <= 0.01
                    and abs(reference_comparison["volume_delta_percent"]) <= 0.001
                )
            parsed = core.parse_nc1(target)
            row.update(
                status="passed" if comparison["passed"] and reference_equal is not False else "different",
                kind=result.kind,
                profile=result.profile_designation,
                profile_type=result.profile_type,
                confidence=result.confidence,
                matched_by=result.matched_by,
                holes=len(parsed.holes),
                contours=len(parsed.contours),
                contour_points=sum(len(contour.geometry_points) for contour in parsed.contours),
                volume_delta_percent=comparison["volume_delta_percent"],
                area_delta_percent=comparison["area_delta_percent"],
                max_aligned_dimension_delta_mm=comparison["max_aligned_dimension_delta_mm"],
                reference_semantic_equal=reference_equal,
                output=str(target.relative_to(output.parent)),
                output_sha256=_sha256(target),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _focus_nc1_roundtrip(files: list[Path], output: Path, database: ProfileDatabase) -> list[dict]:
    rows: list[dict] = []
    for source in files:
        case = output / source.stem
        case.mkdir(parents=True, exist_ok=True)
        ifc = case / f"{source.stem}_stage1.ifc"
        step = case / f"{source.stem}_stage2.step"
        final = case / f"{source.stem}_stage3_final.nc1"
        row = {"source": source.name, "route": "NC1->IFC->STEP->NC1", "status": "failed"}
        try:
            first = dstv_to_ifc(source, ifc)
            second = ifc_to_step(ifc, step)
            third = step_to_nc1(
                step,
                final,
                material=core.parse_nc1(source).header.material or "S235JR",
                order_number=core.parse_nc1(source).header.order_number or "ROUNDTRIP",
                profile_database=database,
                strict_validation=True,
            )
            comparison = compare_nc1(source, final)
            payload = extract_part_from_ifc(ifc, strict=True)
            source_summary = comparison["source"]
            row.update(
                status="passed" if comparison["passed"] else "different",
                profile=source_summary["header"]["profile"],
                profile_type=source_summary["header"]["profile_type"],
                material=source_summary["header"]["material"],
                quantity=source_summary["header"]["quantity"],
                holes=source_summary["hole_count"],
                contours=source_summary["contour_count"],
                contour_points=source_summary["contour_point_count"],
                holes_equal=comparison["holes_equal"],
                contours_equal=comparison["contours_equal"],
                metadata_equal=comparison["all_metadata_equal"],
                volume_delta_percent=comparison["volume_delta_percent"],
                area_delta_percent=comparison["area_delta_percent"],
                max_dimension_delta_mm=comparison["max_dimension_delta_mm"],
                max_bbox_delta_mm=comparison["max_bbox_delta_mm"],
                payload_valid=payload is not None,
                payload_schema=payload.schema_version,
                payload_source_sha256=payload.source_sha256,
                ifc_preview_volume_delta_percent=first.details.get("preview_volume_delta_percent"),
                ifc_to_step_route=second.details.get("route"),
                final_conversion_route=third.matched_by,
                output_nc1_sha256=_sha256(final),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _focus_step_roundtrip(files: list[Path], output: Path, database: ProfileDatabase) -> list[dict]:
    rows: list[dict] = []
    for source in files:
        case = output / source.stem
        case.mkdir(parents=True, exist_ok=True)
        ifc = case / f"{source.stem}_stage1.ifc"
        nc_folder = case / "stage2_dstv"
        final = case / f"{source.stem}_stage3_final.step"
        row = {"source": source.name, "route": "STEP->IFC->NC1->STEP", "status": "failed"}
        try:
            first = step_to_ifc(source, ifc, material="S355JR")
            second = ifc_to_dstv(
                ifc,
                nc_folder,
                material="S355JR",
                order_number="ROUNDTRIP",
                profile_database=database,
                strict_validation=True,
            )
            if second.failures:
                raise ValueError("; ".join(second.failures))
            nc1 = next(path for path in second.outputs if path.suffix.lower() == ".nc1")
            convert_nc1_to_step(nc1, final)
            comparison = compare_step(source, final, profile_database=database)
            parsed = core.parse_nc1(nc1)
            payload = extract_part_from_ifc(ifc, strict=True)
            row.update(
                status="passed" if comparison["passed"] else "different",
                profile=parsed.header.profile,
                profile_type=parsed.header.profile_type,
                material=parsed.header.material,
                quantity=parsed.header.quantity,
                holes=len(parsed.holes),
                contours=len(parsed.contours),
                contour_points=sum(len(contour.geometry_points) for contour in parsed.contours),
                holes_equal=comparison["holes_equal"],
                profile_equal=comparison["profile_equal"],
                profile_type_equal=comparison["profile_type_equal"],
                contour_compact=comparison["contour_compact"],
                volume_delta_percent=comparison["volume_delta_percent"],
                area_delta_percent=comparison["area_delta_percent"],
                max_aligned_dimension_delta_mm=comparison["max_aligned_dimension_delta_mm"],
                raw_bbox_delta_mm=comparison["bbox_delta_mm"],
                payload_valid=payload is not None,
                payload_schema=payload.schema_version,
                recognition_confidence=payload.recognition.get("confidence"),
                ifc_preview_volume_delta_percent=first.details.get("preview_volume_delta_percent"),
                ifc_to_dstv_route=second.details.get("route"),
                output_step_sha256=_sha256(final),
            )
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["traceback"] = traceback.format_exc()
        rows.append(row)
    return rows


def _report_markdown(summary: dict, focus_rows: list[dict]) -> str:
    lines = [
        f"# Roundtrip- en regressievalidatie v{__version__}",
        "",
        "Deze validatie is daadwerkelijk uitgevoerd zonder `strict_validation` uit te schakelen.",
        "Converter-eigen IFC-bestanden bevatten zichtbare IFC4-tessellatie plus een gehashte canonieke payload in `Pset_NC1StepConverter`.",
        "",
        "## Samenvatting",
        "",
        "| Testgroep | Geslaagd | Totaal |",
        "|---|---:|---:|",
        f"| NC1 → STEP regressie | {summary['direct_nc1_passed']} | {summary['direct_nc1_total']} |",
        f"| STEP → NC1 regressie | {summary['direct_step_passed']} | {summary['direct_step_total']} |",
        f"| NC1 → IFC → STEP → NC1 | {summary['focus_nc1_passed']} | {summary['focus_nc1_total']} |",
        f"| STEP → IFC → NC1 → STEP | {summary['focus_step_passed']} | {summary['focus_step_total']} |",
        "",
        "## Acht focusbestanden",
        "",
        "| Bron | Keten | Status | Profiel | Gaten | Contourpunten | Volume Δ | Oppervlak Δ | Max. uitgelijnde maat Δ |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in focus_rows:
        dimension = row.get("max_aligned_dimension_delta_mm", row.get("max_dimension_delta_mm"))
        lines.append(
            "| {source} | {route} | **{status}** | {profile} | {holes} | {points} | {volume:+.9f}% | {area:+.9f}% | {dimension:.6f} mm |".format(
                source=row.get("source", ""),
                route=row.get("route", ""),
                status=row.get("status", ""),
                profile=row.get("profile", "—"),
                holes=row.get("holes", 0),
                points=row.get("contour_points", 0),
                volume=float(row.get("volume_delta_percent") or 0.0),
                area=float(row.get("area_delta_percent") or 0.0),
                dimension=float(dimension or 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Beoordeling",
            "",
            "- Byte-identieke STEP-bestanden zijn niet vereist; headers en entiteitsnummers kunnen wijzigen.",
            "- Voor NC1 worden gaten, contouren, kopgegevens en nominale maten semantisch vergeleken.",
            "- Voor STEP-profielen worden profieltype, profielbenaming, gaten, volume en uitgelijnde nominale profielmaten vergeleken; de ruwe wereld-bounding-box kan door lokale DSTV-oriëntatie afwijken.",
            "- De IFC-preview blijft getesselleerd, maar productiefeatures worden bij converter-eigen IFC niet uit die mesh teruggeraden: de geverifieerde canonieke payload heeft prioriteit.",
            "",
            "Volledige meetgegevens staan in `results.json`; compacte tabellen staan in de drie CSV-bestanden.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handover-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path)
    args = parser.parse_args()

    handover = args.handover_root.resolve()
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    complete = handover / "03_TEST_INPUTS" / "COMPLETE_DATASET"
    focus = handover / "03_TEST_INPUTS" / "ROUNDTRIP_FOCUS"
    nc1_files = sorted((complete / "NC_Files").glob("*.nc1")) + sorted((complete / "NC_Files").glob("*.nc"))
    step_files = sorted((complete / "STP_files").glob("*.stp")) + sorted((complete / "STP_files").glob("*.step"))
    focus_nc1 = sorted((focus / "NC1").glob("*.nc1"))
    focus_step = sorted((focus / "STEP").glob("*.stp")) + sorted((focus / "STEP").glob("*.step"))
    database = ProfileDatabase(writable_copy=False)

    reference_step = args.reference_root / "step" if args.reference_root else None
    reference_nc1 = args.reference_root / "nc1" if args.reference_root else None

    direct_nc1 = _direct_nc1_regression(
        nc1_files,
        output / "direct_nc1_to_step",
        reference_step,
        database,
    )
    direct_step = _direct_step_regression(
        step_files,
        output / "direct_step_to_nc1",
        reference_nc1,
        database,
    )
    focus_nc1_rows = _focus_nc1_roundtrip(
        focus_nc1,
        output / "roundtrip_nc1_ifc_step_nc1",
        database,
    )
    focus_step_rows = _focus_step_roundtrip(
        focus_step,
        output / "roundtrip_step_ifc_nc1_step",
        database,
    )

    summary = {
        "converter_version": __version__,
        "direct_nc1_total": len(direct_nc1),
        "direct_nc1_passed": sum(row["status"] == "passed" for row in direct_nc1),
        "direct_step_total": len(direct_step),
        "direct_step_passed": sum(row["status"] == "passed" for row in direct_step),
        "focus_nc1_total": len(focus_nc1_rows),
        "focus_nc1_passed": sum(row["status"] == "passed" for row in focus_nc1_rows),
        "focus_step_total": len(focus_step_rows),
        "focus_step_passed": sum(row["status"] == "passed" for row in focus_step_rows),
    }
    all_rows = direct_nc1 + direct_step + focus_nc1_rows + focus_step_rows
    summary["all_passed"] = all(row["status"] == "passed" for row in all_rows)
    result = {
        "summary": summary,
        "direct_nc1_to_step": direct_nc1,
        "direct_step_to_nc1": direct_step,
        "focus_nc1_ifc_step_nc1": focus_nc1_rows,
        "focus_step_ifc_nc1_step": focus_step_rows,
    }
    (output / "results.json").write_text(
        json.dumps(_json_safe(result), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_csv(output / "regression_nc1_to_step.csv", direct_nc1)
    _write_csv(output / "regression_step_to_nc1.csv", direct_step)
    _write_csv(output / "roundtrip_focus.csv", focus_nc1_rows + focus_step_rows)
    (output / "ROUNDTRIP_VALIDATIE_V05.md").write_text(
        _report_markdown(summary, focus_nc1_rows + focus_step_rows),
        encoding="utf-8",
    )
    checksum_lines = []
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_lines.append(f"{_sha256(path)}  {path.relative_to(output).as_posix()}")
    (output / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="ascii")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
