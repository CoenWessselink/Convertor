"""Validate the CWS Convertor v0.6 project foundation on real models.

This release proves the phase-0/1 foundation: central product identity,
Canonical Project Model 2.0, deterministic IFC/STEP intake evidence, portable
``.cwscproj`` storage, integrity/recovery and a production gate.  It does not
claim that the complete IFC assembly tree or STEP solids have already been
materialised as production-ready ProjectModel entities; that is phase 2.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_NAME, APP_VERSION, PROJECT_SCHEMA_VERSION
from cws_convertor.project import (
    BaselineAnalysis,
    ProjectService,
    ProjectSession,
    ProjectStore,
    inspect_model_file,
    write_baseline_report,
)

EXPECTED_VERSION = "0.6.0-beta"
EXPECTED_IFC_SHA = "c3ccd9b1db66f6db9e6a1141e52384f24946ca820739a408821ac93dc69aec3c"
EXPECTED_IFC_COUNTS = {
    "assemblies": 353,
    "plates": 1293,
    "beams": 707,
    "columns": 369,
    "mechanical_fasteners": 723,
    "weld_fastener_objects": 2654,
    "footings": 38,
    "building_element_proxies": 19,
    "slabs": 3,
}
EXPECTED_REFERENCE_CHECKS = (
    "MLO4_found",
    "LO4_found",
    "STRIP5*120_found",
    "S235JR_found",
    "length_160_mm_found",
    "assembly_weight_0_6_kg_found",
    "bolt_or_hole_diameter_14_mm_found",
)
EXPECTED_MARK_COUNTS = {"LA1": 71, "A1": 37, "MP1": 18, "MP2": 16}
EXPECTED_STEPS: dict[str, dict[str, Any]] = {
    "Samenstel nieuw - 11864_Predeterminado (1).step": {
        "sha256": "82cd9aa753cd7e6687d996659ea9aa2978fa404b0501d58839497400f75ee6b5",
        "product_name": "11864_Predeterminado",
        "advanced_faces": 118,
        "circles": 117,
        "cylindrical_surfaces": 37,
        "volume_mm3": 88099.93767261282,
        "area_mm2": 17894.326001384652,
        "bbox_mm": [77.23850525203673, 177.5000001, 30.12018514437291],
    },
    "Samenstel nieuw - 11881_Predeterminado (1).step": {
        "sha256": "b63e4d47f40ab3ff50f50e88a57b3be5b32760359fb301b104f400a9fcb27dd8",
        "product_name": "11881_Predeterminado",
        "advanced_faces": 2582,
        "circles": 662,
        "cylindrical_surfaces": 341,
        "volume_mm3": 1189644.7121358362,
        "area_mm2": 223999.72014984238,
        "bbox_mm": [335.928939571977, 177.928939571977, 121.00000020016367],
    },
    "Samenstel nieuw - 2x voetplaat hoog.step": {
        "sha256": "e5c460e13c892c1f3820f5bd0d2fd38a538206226b747cc54c3bc56f6e208a44",
        "product_name": "2x voetplaat hoog",
        "advanced_faces": 14,
        "circles": 16,
        "cylindrical_surfaces": 8,
        "volume_mm3": 2125965.1350322,
        "area_mm2": 249433.68104726117,
        "bbox_mm": [607.0, 20.000000200000002, 178.0],
    },
}
PROJECT_SMOKES = (
    "tests/project_model_smoke.py",
    "tests/project_storage_smoke.py",
    "tests/project_baseline_smoke.py",
    "tests/project_cli_smoke.py",
    "tests/project_jobs_smoke.py",
    "tests/project_service_smoke.py",
    "tests/project_reference_files_smoke.py",
)


@dataclass
class Check:
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    details: str = ""


@dataclass
class ValidationRun:
    started_at: str
    app_name: str = APP_NAME
    app_version: str = APP_VERSION
    project_schema_version: str = PROJECT_SCHEMA_VERSION
    checks: list[Check] = field(default_factory=list)
    analyses: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    timings_seconds: dict[str, float] = field(default_factory=dict)

    def check(
        self,
        name: str,
        condition: bool,
        *,
        expected: Any = None,
        actual: Any = None,
        details: str = "",
    ) -> None:
        self.checks.append(Check(name, bool(condition), expected, actual, details))

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "app_name": self.app_name,
            "app_version": self.app_version,
            "project_schema_version": self.project_schema_version,
            "status": "passed" if self.passed else "failed",
            "summary": {
                "checks": len(self.checks),
                "passed": sum(item.passed for item in self.checks),
                "failed": sum(not item.passed for item in self.checks),
            },
            "checks": [asdict(item) for item in self.checks],
            "analyses": self.analyses,
            "artifacts": dict(sorted(self.artifacts.items())),
            "timings_seconds": dict(sorted(self.timings_seconds.items())),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close_enough(
    actual: float,
    expected: float,
    *,
    absolute: float = 1e-6,
    relative: float = 1e-9,
) -> bool:
    return abs(actual - expected) <= max(absolute, abs(expected) * relative)


def _run_smoke(run: ValidationRun, output: Path, script: str) -> None:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            exc.cmd,
            124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\nTIMEOUT na 180 seconden",
        )
    elapsed = round(time.perf_counter() - started, 6)
    run.timings_seconds[script] = elapsed
    log_name = Path(script).stem + ".log"
    log_path = output / "test_logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"COMMAND: {sys.executable} {ROOT / script}\n"
        f"EXITCODE: {result.returncode}\n"
        f"SECONDS: {elapsed}\n\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}",
        encoding="utf-8",
    )
    run.artifacts[f"test_log:{Path(script).stem}"] = str(log_path)
    run.check(
        f"Smoke {script}",
        result.returncode == 0,
        expected=0,
        actual=result.returncode,
        details=(result.stdout + "\n" + result.stderr)[-4000:],
    )


def _run_command_check(
    run: ValidationRun,
    output: Path,
    *,
    name: str,
    command: list[str],
    log_name: str,
    timing_key: str,
) -> None:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            exc.cmd,
            124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\nTIMEOUT na 120 seconden",
        )
    elapsed = round(time.perf_counter() - started, 6)
    run.timings_seconds[timing_key] = elapsed
    log_path = output / "test_logs" / log_name
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"COMMAND: {' '.join(command)}\n"
        f"EXITCODE: {result.returncode}\n"
        f"SECONDS: {elapsed}\n\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}",
        encoding="utf-8",
    )
    run.artifacts[f"test_log:{timing_key}"] = str(log_path)
    run.check(
        name,
        result.returncode == 0,
        expected=0,
        actual=result.returncode,
        details=(result.stdout + "\n" + result.stderr)[-4000:],
    )


def _prepare_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents:
        raise ValueError("Validatie-uitvoer moet buiten de bronboom staan")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)



def _load_cached_analyses(cache_path: Path, source_paths: list[Path]) -> list[BaselineAnalysis]:
    """Load measured analyses only when filename and SHA-256 still match.

    Loading the largest AP242 BREP through OpenCascade is deliberately part of
    the first measurement run but expensive for repeated release packaging.
    A cache can never be attached to changed source bytes: each filename and
    SHA-256 is verified again before it is accepted.
    """

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    rows = list(payload.get("files") or payload.get("analyses") or [])
    by_name = {
        str(row.get("file_name") or ""): BaselineAnalysis.from_dict(row)
        for row in rows
    }
    analyses: list[BaselineAnalysis] = []
    for source in source_paths:
        analysis = by_name.get(source.name)
        if analysis is None:
            raise ValueError(f"Analyse-cache mist {source.name}")
        actual_sha = sha256_file(source)
        if analysis.sha256 != actual_sha:
            raise ValueError(
                f"Analyse-cache hoort niet bij de huidige bytes van {source.name}: "
                f"{analysis.sha256} != {actual_sha}"
            )
        analyses.append(analysis)
    return analyses

def _write_analysis_csv(path: Path, analyses: list[BaselineAnalysis]) -> None:
    rows: list[dict[str, Any]] = []
    for item in analyses:
        metrics = item.geometry_metrics
        bbox = list(metrics.get("bbox_mm") or ["", "", ""])
        bbox += [""] * max(0, 3 - len(bbox))
        rows.append(
            {
                "file_name": item.file_name,
                "source_format": item.source_format,
                "schema": item.schema,
                "strategy": item.import_strategy.value,
                "product_count": item.product_count,
                "solid_count": item.solid_count,
                "assembly_relation_count": item.assembly_relation_count,
                "volume_mm3": metrics.get("volume_mm3", ""),
                "area_mm2": metrics.get("area_mm2", ""),
                "bbox_x_mm": bbox[0],
                "bbox_y_mm": bbox[1],
                "bbox_z_mm": bbox[2],
                "warnings": " | ".join(item.warnings),
                "sha256": item.sha256,
            }
        )
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, run: ValidationRun, analyses: list[BaselineAnalysis]) -> None:
    passed = sum(item.passed for item in run.checks)
    lines = [
        f"# {APP_NAME} {APP_VERSION} — Project Foundation-validatie",
        "",
        f"**Status:** {'GESLAAGD' if run.passed else 'MISLUKT'}  ",
        f"**Project Model:** {PROJECT_SCHEMA_VERSION}  ",
        f"**Controles:** {passed}/{len(run.checks)} geslaagd  ",
        "",
        "## Bewezen scope",
        "",
        f"- centrale productidentiteit **{APP_NAME}**;",
        "- Canonical Project Model 2.0 met stabiele bron- en entity-identiteit;",
        "- deterministische selectie van IFC/STEP-importstrategie A/B/C;",
        "- echte nulmeting op één groot Tekla IFC-model en drie AP242 STEP-modellen;",
        "- draagbare ZIP+SQLite `.cwscproj` met SHA-256, CRC en SQLite-integriteitscontrole;",
        "- embedded bronnen en previews, veilige extractie, revisies, audit, autosave en herstel;",
        "- productiepoort blijft gesloten zolang semantische import/validatie niet is afgerond.",
        "",
        "## Referentiebestanden",
        "",
        "| Bestand | Route | Producten | Solids | Assemblagerelaties | SHA-256 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for analysis in analyses:
        lines.append(
            f"| `{analysis.file_name}` | `{analysis.import_strategy.value}` | "
            f"{analysis.product_count} | {analysis.solid_count} | "
            f"{analysis.assembly_relation_count} | `{analysis.sha256}` |"
        )
    lines.extend(
        [
            "",
            "## IFC-nulmeting",
            "",
            "| Objectgroep | Aantal |",
            "|---|---:|",
        ]
    )
    ifc = next(item for item in analyses if item.source_format == "IFC")
    for key, value in EXPECTED_IFC_COUNTS.items():
        lines.append(f"| {key} | {ifc.class_summary.get(key, 0)} |")
    lines.extend(
        [
            "",
            "## Controles",
            "",
            "| Controle | Resultaat | Verwacht | Werkelijk |",
            "|---|---|---|---|",
        ]
    )
    for item in run.checks:
        expected = json.dumps(item.expected, ensure_ascii=False) if item.expected is not None else ""
        actual = json.dumps(item.actual, ensure_ascii=False) if item.actual is not None else ""
        lines.append(
            f"| {item.name.replace('|', '/')} | {'✅' if item.passed else '❌'} | "
            f"{expected.replace('|', '/')} | {actual.replace('|', '/')} |"
        )
    lines.extend(
        [
            "",
            "## Eerlijke begrenzing",
            "",
            "Deze fase inventariseert en bewaart de echte modellen, kiest veilig importstrategie A/B/C en legt bronstructuur en geometrische nulmetingen vast. De IFC-assemblyboom en STEP-solids zijn nog niet als actieve, productie-vrijgegeven assemblies/onderdelen in het Project Model aangemaakt. BOM-, NC1-, optimalisatie- en machine-export vanuit complete modellen blijven daarom geblokkeerd. Dat is de volgende bouwfase.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_checksums(output: Path) -> Path:
    checksum_path = output / "SHA256SUMS.txt"
    lines: list[str] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path == checksum_path:
            continue
        relative = path.relative_to(output).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return checksum_path


def validate(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    _prepare_output(output)
    source_paths = [Path(item).expanduser().resolve() for item in args.inputs]
    run = ValidationRun(started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    run.check("Productnaam", APP_NAME == "SteelConverter", expected="SteelConverter", actual=APP_NAME)
    run.check("Prereleaseversie", APP_VERSION == EXPECTED_VERSION, expected=EXPECTED_VERSION, actual=APP_VERSION)
    run.check(
        "Vier referentiebestanden aanwezig",
        len(source_paths) == 4 and all(path.is_file() for path in source_paths),
        expected=4,
        actual=sum(path.is_file() for path in source_paths),
    )
    if len(source_paths) != 4 or not all(path.is_file() for path in source_paths):
        raise FileNotFoundError("Geef exact het Tekla IFC-bestand en de drie STEP-referenties op")

    print("[1/8] Referentiebestanden analyseren", flush=True)
    cache_value = str(getattr(args, "analysis_cache", "") or "").strip()
    if cache_value:
        cache_path = Path(cache_value).expanduser().resolve()
        started = time.perf_counter()
        analyses = _load_cached_analyses(cache_path, source_paths)
        run.timings_seconds["analysis_cache_load"] = round(time.perf_counter() - started, 6)
        run.artifacts["analysis_cache_input"] = str(cache_path)
        run.check(
            "Gemeten analyse-cache past exact bij bronhashes",
            len(analyses) == len(source_paths),
            expected=len(source_paths),
            actual=len(analyses),
        )
    else:
        analyses = []
        for source in source_paths:
            started = time.perf_counter()
            analysis = inspect_model_file(
                source,
                include_geometry=source.suffix.lower() in {".step", ".stp"},
            )
            run.timings_seconds[f"inspect:{source.name}"] = round(time.perf_counter() - started, 6)
            analyses.append(analysis)
    run.analyses.extend(analysis.to_dict() for analysis in analyses)

    baseline_path = output / "REFERENCE_IMPORT_BASELINE.json"
    write_baseline_report(analyses, baseline_path, title=f"{APP_NAME} {APP_VERSION} referentienulmeting")
    baseline_csv = output / "reference_baseline.csv"
    _write_analysis_csv(baseline_csv, analyses)
    run.artifacts["reference_baseline_json"] = str(baseline_path)
    run.artifacts["reference_baseline_csv"] = str(baseline_csv)

    print("[2/8] Verwachte IFC/STEP-nulmetingen controleren", flush=True)
    ifc = next(item for item in analyses if item.source_format == "IFC")
    run.check("IFC SHA-256", ifc.sha256 == EXPECTED_IFC_SHA, expected=EXPECTED_IFC_SHA, actual=ifc.sha256)
    run.check("IFC schema IFC2X3", ifc.schema == "IFC2X3", expected="IFC2X3", actual=ifc.schema)
    run.check("IFC semantische importstrategie", ifc.import_strategy.value == "A_semantic_structure", expected="A_semantic_structure", actual=ifc.import_strategy.value)
    for key, expected in EXPECTED_IFC_COUNTS.items():
        actual = int(ifc.class_summary.get(key, -1))
        run.check(f"IFC nulmeting {key}", actual == expected, expected=expected, actual=actual)
    run.check("IFC gefacetteerde BREP nulmeting", int(ifc.entity_counts.get("IFCFACETEDBREP", -1)) == 328, expected=328, actual=ifc.entity_counts.get("IFCFACETEDBREP"))
    for key in EXPECTED_REFERENCE_CHECKS:
        actual = bool(ifc.reference_checks.get(key))
        run.check(f"IFC referentie {key}", actual, expected=True, actual=actual)
    repeated = dict(ifc.reference_checks.get("repeated_mark_counts") or {})
    for mark, expected in EXPECTED_MARK_COUNTS.items():
        run.check(f"Herhaald merk {mark}", int(repeated.get(mark, -1)) == expected, expected=expected, actual=repeated.get(mark))

    for analysis in (item for item in analyses if item.source_format == "STEP"):
        expected = EXPECTED_STEPS.get(analysis.file_name)
        if expected is None:
            run.check(f"Onverwacht STEP-bestand {analysis.file_name}", False, expected=list(EXPECTED_STEPS), actual=analysis.file_name)
            continue
        run.check(f"{analysis.file_name}: SHA-256", analysis.sha256 == expected["sha256"], expected=expected["sha256"], actual=analysis.sha256)
        run.check(f"{analysis.file_name}: AP242", analysis.schema.startswith("AP242"), expected="AP242*", actual=analysis.schema)
        run.check(f"{analysis.file_name}: één product", analysis.product_count == 1, expected=1, actual=analysis.product_count)
        run.check(f"{analysis.file_name}: één BREP-solid", analysis.solid_count == 1, expected=1, actual=analysis.solid_count)
        run.check(f"{analysis.file_name}: geen assemblyrelatie", analysis.assembly_relation_count == 0, expected=0, actual=analysis.assembly_relation_count)
        run.check(f"{analysis.file_name}: geen fictieve assembly", analysis.import_strategy.value == "B_separate_solids", expected="B_separate_solids", actual=analysis.import_strategy.value)
        run.check(f"{analysis.file_name}: productnaam", analysis.reference_checks.get("product_names") == [expected["product_name"]], expected=[expected["product_name"]], actual=analysis.reference_checks.get("product_names"))
        for key in ("advanced_faces", "circles", "cylindrical_surfaces"):
            run.check(f"{analysis.file_name}: {key}", int(analysis.class_summary.get(key, -1)) == int(expected[key]), expected=expected[key], actual=analysis.class_summary.get(key))
        metrics = analysis.geometry_metrics
        run.check(f"{analysis.file_name}: CAD-solid geladen", bool(metrics.get("cadquery_loaded")), expected=True, actual=metrics.get("cadquery_loaded"))
        run.check(f"{analysis.file_name}: CAD-solid geldig", bool(metrics.get("valid")), expected=True, actual=metrics.get("valid"))
        for key in ("volume_mm3", "area_mm2"):
            actual = float(metrics.get(key, float("nan")))
            wanted = float(expected[key])
            run.check(f"{analysis.file_name}: {key}", close_enough(actual, wanted), expected=wanted, actual=actual)
        bbox = list(metrics.get("bbox_mm") or [])
        run.check(f"{analysis.file_name}: bbox bevat 3 assen", len(bbox) == 3, expected=3, actual=len(bbox))
        for index, wanted in enumerate(expected["bbox_mm"]):
            actual = float(bbox[index]) if index < len(bbox) else float("nan")
            run.check(f"{analysis.file_name}: bbox as {index + 1}", close_enough(actual, float(wanted)), expected=wanted, actual=actual)

    footplate = next(item for item in analyses if "2x voetplaat" in item.file_name)
    run.check(
        "2x voetplaat wordt niet op naam gesplitst",
        footplate.product_count == 1
        and footplate.solid_count == 1
        and any("niet automatisch opsplitsen" in warning for warning in footplate.warnings),
        expected="1 product, 1 solid, expliciete waarschuwing",
        actual={"product_count": footplate.product_count, "solid_count": footplate.solid_count, "warnings": footplate.warnings},
    )

    print("[3/8] Draagbaar .cwscproj-project maken", flush=True)
    project_path = output / f"CWS_Convertor_{APP_VERSION}_Reference_Project.cwscproj"
    session = ProjectService.create(
        project_path,
        "CWS referentieproject",
        client="CWS",
        order_number="V060-REFERENCE",
        description="Deterministische IFC/STEP-nulmeting; semantische import bewust nog geblokkeerd.",
        project_phase="Projectfundament",
        created_by="validation",
    )
    registered = session.register_analyses(zip(source_paths, analyses), user="validation")
    preview_path = output / "CWS_PROJECT_OVERVIEW.svg"
    preview_path.write_text(
        "<svg xmlns='http://www.w3.org/2000/svg' width='960' height='540' viewBox='0 0 960 540'>"
        "<rect width='960' height='540' fill='#101820'/>"
        "<rect x='36' y='36' width='888' height='468' rx='22' fill='#17242f' stroke='#4aa3ff' stroke-width='2'/>"
        f"<text x='72' y='110' fill='white' font-family='Segoe UI,Arial' font-size='42' font-weight='700'>{APP_NAME}</text>"
        "<text x='72' y='157' fill='#a9c7df' font-family='Segoe UI,Arial' font-size='22'>Project Foundation — referentieproject</text>"
        "<text x='72' y='235' fill='white' font-family='Segoe UI,Arial' font-size='28'>4 bronmodellen veilig geïnventariseerd</text>"
        "<text x='72' y='287' fill='#9fb3c5' font-family='Segoe UI,Arial' font-size='20'>1 × Tekla IFC2X3  •  3 × STEP AP242</text>"
        "<text x='72' y='339' fill='#ffbd4a' font-family='Segoe UI,Arial' font-size='20'>Productie-export geblokkeerd tot semantische import is gevalideerd</text>"
        f"<text x='72' y='432' fill='#7bd88f' font-family='Segoe UI,Arial' font-size='18'>Project Model {PROJECT_SCHEMA_VERSION}  •  {APP_VERSION}</text>"
        "</svg>",
        encoding="utf-8",
    )
    session.preview_paths[preview_path.name] = preview_path
    saved = session.save(
        embed_sources=True,
        user="validation",
        revision_message="Vier echte referentiemodellen ingesloten",
    )
    project_id = session.project.project_id
    revision_count = len(session.project.revisions)
    session.close()
    run.artifacts["project_package"] = str(saved)
    run.artifacts["project_preview"] = str(preview_path)
    run.check("Vier bronnen geregistreerd", len(registered) == 4, expected=4, actual=len(registered))

    print("[4/8] Package, SQLite en embedded bronnen verifiëren", flush=True)
    service = ProjectService()
    verification = service.verify_project(saved)
    verification_path = output / "PROJECT_PACKAGE_VERIFICATION.json"
    verification_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    run.artifacts["package_verification"] = str(verification_path)
    store = ProjectStore()
    package = store.open(saved, read_only=True)
    summary = package.project.summary()
    gate = package.project.production_gate()
    run.check("ZIP CRC geldig", bool(verification.get("checks", {}).get("zip_crc")), expected=True, actual=verification.get("checks", {}).get("zip_crc"))
    run.check("SQLite-integriteit geldig", bool(verification.get("checks", {}).get("sqlite_integrity")), expected=True, actual=verification.get("checks", {}).get("sqlite_integrity"))
    run.check("Project Model schema 2.0", package.project.schema_version == PROJECT_SCHEMA_VERSION, expected=PROJECT_SCHEMA_VERSION, actual=package.project.schema_version)
    run.check("Project-ID stabiel", package.project.project_id == project_id, expected=project_id, actual=package.project.project_id)
    run.check("Vier bronnen in package", len(package.project.sources) == 4, expected=4, actual=len(package.project.sources))
    run.check("Vier bronnen embedded", len(package.embedded_source_names()) == 4, expected=4, actual=len(package.embedded_source_names()))
    run.check("Projectpreview embedded", package.preview_names() == ["previews/CWS_PROJECT_OVERVIEW.svg"], expected=["previews/CWS_PROJECT_OVERVIEW.svg"], actual=package.preview_names())
    run.check("Revisiehistorie aanwezig", revision_count >= 2, expected=">=2", actual=revision_count)
    run.check("Productiepoort bewust gesloten", not gate["allowed"], expected=False, actual=gate["allowed"])
    run.check("Vier semantische importblokkades", len(gate["source_failures"]) == 4, expected=4, actual=len(gate["source_failures"]))
    run.check("Actieve assemblies nog nul", summary["entity_counts"]["assembly"] == 0, expected=0, actual=summary["entity_counts"]["assembly"])
    run.check("Actieve onderdelen nog nul", summary["entity_counts"]["part"] == 0, expected=0, actual=summary["entity_counts"]["part"])

    extract_root = output / "extracted_sources"
    extract_root.mkdir(exist_ok=True)
    original_by_hash = {sha256_file(path): path for path in source_paths}
    for source_id, record in package.project.sources.items():
        extracted = package.extract_source(source_id, extract_root / record.file_name)
        actual_hash = sha256_file(extracted)
        run.check(f"Embedded bron exact: {record.file_name}", actual_hash == record.sha256 and actual_hash in original_by_hash, expected=record.sha256, actual=actual_hash)

    extracted_preview = package.extract_entry(
        "previews/CWS_PROJECT_OVERVIEW.svg",
        output / "extracted_preview" / "CWS_PROJECT_OVERVIEW.svg",
    )
    run.check(
        "Embedded preview exact",
        sha256_file(extracted_preview) == sha256_file(preview_path),
        expected=sha256_file(preview_path),
        actual=sha256_file(extracted_preview),
    )

    model_json = output / "PROJECT_MODEL_2_0.json"
    model_json.write_bytes(package.project.to_json_bytes())
    run.artifacts["project_model_json"] = str(model_json)

    print("[5/8] Autosave en herstel controleren", flush=True)
    main_hash_before = sha256_file(saved)
    autosession = ProjectSession.open(saved)
    autosession.project.description += " Autosave-test."
    autosession.dirty = True
    autosave = autosession.autosave()
    autosession.close()
    run.artifacts["autosave"] = str(autosave)
    autosave_package = store.open(autosave, read_only=True)
    run.check("Autosave overschrijft hoofdproject niet", sha256_file(saved) == main_hash_before, expected=main_hash_before, actual=sha256_file(saved))
    run.check("Autosave is lichtgewicht", len(autosave_package.embedded_source_names()) == 0, expected=0, actual=len(autosave_package.embedded_source_names()))
    run.check("Autosave bewaart preview", autosave_package.preview_names() == ["previews/CWS_PROJECT_OVERVIEW.svg"], expected=["previews/CWS_PROJECT_OVERVIEW.svg"], actual=autosave_package.preview_names())
    recovered_path = output / f"CWS_Convertor_{APP_VERSION}_Recovered_Project.cwscproj"
    service.recover_autosave(saved, recovered_path)
    recovered = store.open(recovered_path, read_only=True)
    run.artifacts["recovered_project"] = str(recovered_path)
    run.check("Herstel voegt vier geverifieerde embedded bronnen terug", len(recovered.embedded_source_names()) == 4, expected=4, actual=len(recovered.embedded_source_names()))
    run.check("Herstel bewaart preview", recovered.preview_names() == ["previews/CWS_PROJECT_OVERVIEW.svg"], expected=["previews/CWS_PROJECT_OVERVIEW.svg"], actual=recovered.preview_names())
    run.check("Herstel bewaart autosavewijziging", recovered.project.description.endswith("Autosave-test."), expected=True, actual=recovered.project.description)

    print("[6/8] Project-CLI-contract controleren", flush=True)
    cli_info = output / "cli_project_info.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "cli.py"), "project-info", str(saved), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    cli_info.write_text(result.stdout, encoding="utf-8")
    run.artifacts["cli_project_info"] = str(cli_info)
    run.check("CLI project-info", result.returncode == 0, expected=0, actual=result.returncode, details=result.stderr[-2000:])
    try:
        cli_payload = json.loads(result.stdout)
    except Exception:
        cli_payload = {}
    run.check("CLI ziet gesloten productiepoort", cli_payload.get("summary", {}).get("production_gate", {}).get("allowed") is False, expected=False, actual=cli_payload.get("summary", {}).get("production_gate", {}).get("allowed"))

    print("[7/8] Project-smoketests, compilecontrole en GUI-start uitvoeren", flush=True)
    for smoke in PROJECT_SMOKES:
        _run_smoke(run, output, smoke)
    _run_command_check(
        run,
        output,
        name="Compilecontrole volledige bronboom",
        command=[sys.executable, "-m", "compileall", "-q", "."],
        log_name="compileall.log",
        timing_key="compileall",
    )
    gui_code = (
        "from app import ConverterApp; "
        "app=ConverterApp(); app.update_idletasks(); "
        "app.destroy(); print('GUI smoke OK')"
    )
    gui_command = [sys.executable, "-c", gui_code]
    if sys.platform != "win32" and shutil.which("xvfb-run"):
        gui_command = ["xvfb-run", "-a", "-s", "-screen 0 1600x1000x24", *gui_command]
    _run_command_check(
        run,
        output,
        name="GUI opstart- en afsluitsmoke",
        command=gui_command,
        log_name="gui_smoke.log",
        timing_key="gui_smoke",
    )

    print("[8/8] Rapporten en checksums schrijven", flush=True)
    report_path = output / "PROJECT_FOUNDATION_VALIDATIE_V0.6.md"
    _write_report(report_path, run, analyses)
    run.artifacts["report"] = str(report_path)
    result_path = output / "results.json"
    run.artifacts["results"] = str(result_path)
    result_path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    checksum_path = _write_checksums(output)
    run.artifacts["checksums"] = str(checksum_path)
    # Refresh results once so it contains the checksum artifact path.  The
    # checksum list intentionally records the prior deterministic results
    # bytes; it is regenerated immediately afterwards to match final bytes.
    result_path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_checksums(output)

    print(json.dumps(run.to_dict()["summary"], ensure_ascii=False), flush=True)
    return 0 if run.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs=4, help="Tekla IFC gevolgd door de drie STEP-referenties")
    parser.add_argument("--output", required=True, help="Nieuwe validatiemap buiten de bronboom")
    parser.add_argument("--analysis-cache", default="", help="Optioneel eerder gemeten baseline-JSON; alleen geaccepteerd bij exacte bronhashes")
    return parser


if __name__ == "__main__":
    raise SystemExit(validate(build_parser().parse_args()))
