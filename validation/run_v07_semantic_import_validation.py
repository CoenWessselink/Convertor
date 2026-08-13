"""Validate CWS Convertor 0.7 semantic IFC/STEP project import.

This phase materialises real source semantics into Canonical Project Model 2.1:
assemblies, parts, fasteners, welds, placements, properties and stable hashes.
It deliberately does *not* release NC1/machine output, because external-model
production features still require deterministic recognition and roundtrip
validation in the next phase.
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
from cws_convertor.project import BaselineAnalysis, ProjectSession, ProjectStore

EXPECTED_VERSION = "0.7.0-alpha"
EXPECTED_SCHEMA = "2.1"
IFC_NAME = "TAS_RVB Defensie onderbouw te Leeuwarden- Rev4 [definitief].ifc"
STEP_NAMES = (
    "Samenstel nieuw - 11864_Predeterminado (1).step",
    "Samenstel nieuw - 11881_Predeterminado (1).step",
    "Samenstel nieuw - 2x voetplaat hoog.step",
)
EXPECTED_SHA = {
    IFC_NAME: "c3ccd9b1db66f6db9e6a1141e52384f24946ca820739a408821ac93dc69aec3c",
    STEP_NAMES[0]: "82cd9aa753cd7e6687d996659ea9aa2978fa404b0501d58839497400f75ee6b5",
    STEP_NAMES[1]: "b63e4d47f40ab3ff50f50e88a57b3be5b32760359fb301b104f400a9fcb27dd8",
    STEP_NAMES[2]: "e5c460e13c892c1f3820f5bd0d2fd38a538206226b747cc54c3bc56f6e208a44",
}
EXPECTED_IFC_CLASSES = {
    "IFCELEMENTASSEMBLY": 353,
    "IFCPLATE": 1293,
    "IFCBEAM": 707,
    "IFCCOLUMN": 369,
    "IFCMECHANICALFASTENER": 723,
    "IFCFASTENER": 2654,
    "IFCFOOTING": 38,
    "IFCBUILDINGELEMENTPROXY": 19,
    "IFCSLAB": 3,
}
EXPECTED_IFC_MATERIALISED = {
    "assemblies": 353,
    "parts": 2429,
    "fasteners": 723,
    "welds": 2654,
    "total_materialised": 6159,
}
EXPECTED_MARKS = {"LA1": 71, "A1": 37, "MP1": 18, "MP2": 16}
SMOKES = (
    "tests/p21_graph_smoke.py",
    "tests/ifc_semantic_import_smoke.py",
    "tests/step_semantic_import_smoke.py",
    "tests/project_semantic_service_smoke.py",
    "tests/project_model_smoke.py",
    "tests/project_storage_smoke.py",
    "tests/project_baseline_smoke.py",
    "tests/project_jobs_smoke.py",
    "tests/project_service_smoke.py",
    "tests/project_cli_smoke.py",
    "tests/project_reference_files_smoke.py",
    "tests/regression_smoke.py",
    "tests/analytic_fitting_smoke.py",
    "tests/dimension_graph_smoke.py",
    "tests/pdf_ai_smoke.py",
    "tests/pdf_review_smoke.py",
    "tests/review_workflow_smoke.py",
)


@dataclass
class Check:
    name: str
    passed: bool
    expected: Any = None
    actual: Any = None
    details: str = ""


@dataclass
class Run:
    started_at: str
    checks: list[Check] = field(default_factory=list)
    timings_seconds: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    semantic_results: list[dict[str, Any]] = field(default_factory=list)
    project_summary: dict[str, Any] = field(default_factory=dict)
    performance: dict[str, Any] = field(default_factory=dict)

    def check(self, name: str, condition: bool, *, expected: Any = None, actual: Any = None, details: str = "") -> None:
        self.checks.append(Check(name, bool(condition), expected, actual, details))

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "project_schema_version": PROJECT_SCHEMA_VERSION,
            "started_at": self.started_at,
            "status": "passed" if self.passed else "failed",
            "summary": {
                "checks": len(self.checks),
                "passed": sum(item.passed for item in self.checks),
                "failed": sum(not item.passed for item in self.checks),
            },
            "checks": [asdict(item) for item in self.checks],
            "timings_seconds": dict(sorted(self.timings_seconds.items())),
            "artifacts": dict(sorted(self.artifacts.items())),
            "semantic_results": self.semantic_results,
            "project_summary": self.project_summary,
            "performance": self.performance,
        }


def utc_stamp() -> str:
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_output(path: Path) -> None:
    resolved = path.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents:
        raise ValueError("Validatie-uitvoer moet buiten de bronboom staan")
    if resolved.exists():
        shutil.rmtree(resolved)
    (resolved / "test_logs").mkdir(parents=True, exist_ok=True)
    (resolved / "extracted_sources").mkdir(parents=True, exist_ok=True)


def load_cached_analyses(cache: Path, paths: list[Path]) -> list[BaselineAnalysis]:
    payload = json.loads(cache.read_text(encoding="utf-8"))
    rows = list(payload.get("files") or payload.get("analyses") or [])
    by_name = {str(row.get("file_name") or ""): BaselineAnalysis.from_dict(row) for row in rows}
    result: list[BaselineAnalysis] = []
    for path in paths:
        analysis = by_name.get(path.name)
        if analysis is None:
            raise ValueError(f"Analyse-cache mist {path.name}")
        actual = sha256_file(path)
        if actual != analysis.sha256 or actual != EXPECTED_SHA[path.name]:
            raise ValueError(f"Bronhash/cache mismatch voor {path.name}")
        result.append(analysis)
    return result


def run_smoke(run: Run, output: Path, script: str) -> None:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=240,
        )
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(
            exc.cmd,
            124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\nTIMEOUT na 240 seconden",
        )
    elapsed = round(time.perf_counter() - started, 6)
    key = Path(script).stem
    run.timings_seconds[f"smoke:{key}"] = elapsed
    log = output / "test_logs" / f"{key}.log"
    log.write_text(
        f"COMMAND: {sys.executable} {ROOT / script}\n"
        f"EXITCODE: {result.returncode}\nSECONDS: {elapsed}\n\n"
        f"STDOUT\n{result.stdout}\nSTDERR\n{result.stderr}",
        encoding="utf-8",
    )
    run.artifacts[f"test_log:{key}"] = str(log)
    run.check(
        f"Smoke {script}",
        result.returncode == 0,
        expected=0,
        actual=result.returncode,
        details=(result.stdout + "\n" + result.stderr)[-3000:],
    )


def write_summary_csv(path: Path, results: list[dict[str, Any]], analyses: list[BaselineAnalysis]) -> None:
    baseline = {item.file_name: item for item in analyses}
    rows: list[dict[str, Any]] = []
    for item in results:
        analysis = baseline[item["file_name"]]
        counts = dict(item.get("entity_counts") or {})
        metrics = dict(analysis.geometry_metrics or {})
        bbox = list(metrics.get("bbox_mm") or ["", "", ""])
        bbox += [""] * (3 - len(bbox))
        rows.append({
            "file_name": item["file_name"],
            "format": item["source_format"],
            "schema": item.get("schema", ""),
            "strategy": item.get("strategy", ""),
            "assemblies": counts.get("assemblies", 0),
            "parts": counts.get("parts", 0),
            "fasteners": counts.get("fasteners", 0),
            "welds": counts.get("welds", 0),
            "total_materialised": counts.get("total_materialised", 0),
            "source_products": analysis.product_count,
            "source_solids": analysis.solid_count,
            "volume_mm3": metrics.get("volume_mm3", ""),
            "area_mm2": metrics.get("area_mm2", ""),
            "bbox_x_mm": bbox[0],
            "bbox_y_mm": bbox[1],
            "bbox_z_mm": bbox[2],
            "production_export_allowed": item.get("production_export_allowed", False),
            "sha256": analysis.sha256,
        })
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, run: Run, results: list[dict[str, Any]], analyses: list[BaselineAnalysis]) -> None:
    passed = sum(item.passed for item in run.checks)
    by_name = {item["file_name"]: item for item in results}
    ifc = by_name[IFC_NAME]
    lines = [
        f"# {APP_NAME} {APP_VERSION} — semantische IFC/STEP-projectimport",
        "",
        f"**Status:** {'GESLAAGD' if run.passed else 'MISLUKT'}  ",
        f"**Project Model-schema:** {PROJECT_SCHEMA_VERSION}  ",
        f"**Controles:** {passed}/{len(run.checks)} geslaagd  ",
        "",
        "## Bewezen scope",
        "",
        "- IFC2X3-productstructuur, assemblies, parts, fasteners en lasobjecten worden als actieve projectentiteiten gematerialiseerd;",
        "- `IfcRelAggregates`, placements, propertysets, materialen, marks en part positions blijven herleidbaar tot de bron;",
        "- AP242-producten en BREP-solids worden zonder fictieve opsplitsing gematerialiseerd;",
        "- geometry- en manufacturing hashes zijn placement-onafhankelijk en stabiel opgeslagen;",
        "- bronbytes worden vóór import en na projectextractie met SHA-256 gecontroleerd;",
        "- de volledige import is transactioneel: bij een fout blijft het project ongewijzigd;",
        "- productie-export blijft geblokkeerd tot classificatie, featureherkenning en roundtripvalidatie per onderdeel zijn afgerond.",
        "",
        "## Referentiemodellen",
        "",
        "| Bestand | Route | Assemblies | Onderdelen | Bouten | Lassen | Totaal | Productie |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in results:
        counts = item["entity_counts"]
        lines.append(
            f"| `{item['file_name']}` | `{item['strategy']}` | {counts.get('assemblies', 0)} | "
            f"{counts.get('parts', 0)} | {counts.get('fasteners', 0)} | "
            f"{counts.get('welds', 0)} | {counts.get('total_materialised', 0)} | "
            f"{'vrij' if item.get('production_export_allowed') else 'geblokkeerd'} |"
        )
    lines.extend([
        "",
        "## Tekla IFC-bewijs",
        "",
        f"- 353 assemblies, 2.429 materiaal-/bouwonderdelen, 723 mechanische bevestigingsmiddelen en 2.654 lasobjecten;",
        f"- bronrelatie `IFCRELAGGREGATES`: {ifc['relationship_counts'].get('IFCRELAGGREGATES', 0)};",
        f"- assemblymerk `MLO4`: {ifc['evidence'].get('MLO4_assembly_count', 0)} instanties;",
        f"- gekoppelde `MLO4`/`LO4`-relaties: {len(ifc['evidence'].get('MLO4_LO4_links', []))};",
        f"- Ø14-bout-/gatinformatie: {ifc['evidence'].get('bolt_or_hole_diameter_14_count', 0)} objecten;",
        f"- verbonden lasobjecten: {ifc['evidence'].get('connected_weld_count', 0)};",
        f"- herhaalde marks: `{json.dumps(ifc['evidence'].get('repeated_marks', {}), ensure_ascii=False)}`;",
        "- alle vier `LO4`-onderdelen behouden `STRIP5*120`, `S235JR`, lengte 160 mm en massa 0,62 kg per stuk.",
        "",
        "## STEP-bewijs",
        "",
        "De drie AP242-referenties blijven elk één product en één BREP-solid. Ook `2x voetplaat hoog` wordt niet op basis van de bestandsnaam gesplitst. Er ontstaat per bron exact één projectonderdeel en geen fictieve assembly.",
        "",
        "## Productiegate",
        "",
        "Deze release bewijst semantische materialisatie, niet productiefeatureherkenning voor willekeurige externe solids. NC1-, optimalisatie- en machine-uitvoer blijven daarom geblokkeerd. De volgende fase moet maakdeel/inkoopdeel-classificatie, profiel-/featureherkenning, BOM en per-part-validatie toevoegen.",
        "",
        "## Grote STEP-prestatiepoort",
        "",
        (
            f"`11881` is in een afzonderlijk proces semantisch geïmporteerd in "
            f"**{run.performance.get('elapsed_seconds', '—')} s** met een gemeten "
            f"piek van **{run.performance.get('max_rss_mb', '—')} MB RSS**. "
            "De vrijgavegrenzen zijn 120 s en 1.536 MB."
            if run.performance
            else "De afzonderlijke grote-modelprestatiepoort is in deze run overgeslagen."
        ),
        "",
        "## Testresultaten",
        "",
        "| Controle | Status |",
        "|---|---|",
    ])
    for check in run.checks:
        lines.append(f"| {check.name.replace('|', '/')} | {'✅' if check.passed else '❌'} |")
    lines.extend([
        "",
        "## Belangrijke beperking",
        "",
        "In deze Linuxomgeving is geen native Windows-installer gebouwd. De Windows-buildstraat is bijgewerkt, maar installer-EXE, portable Windows-ZIP en schone-machine-test blijven afzonderlijke vrijgavepoorten.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, default=Path("/mnt/data"))
    parser.add_argument("--cache", type=Path, default=Path("/mnt/data/CONVERTER_WORK/REFERENCE_IMPORT_BASELINE_MEASURED_CACHE.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-smokes", action="store_true")
    parser.add_argument("--skip-performance", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    prepare_output(output)
    run = Run(started_at=utc_stamp())
    print(f"[v0.7] Validatie-uitvoer: {output}", flush=True)

    run.check("Productnaam", APP_NAME == "SteelConverter", expected="SteelConverter", actual=APP_NAME)
    run.check("Applicatieversie", APP_VERSION == EXPECTED_VERSION, expected=EXPECTED_VERSION, actual=APP_VERSION)
    run.check("Projectschema", PROJECT_SCHEMA_VERSION == EXPECTED_SCHEMA, expected=EXPECTED_SCHEMA, actual=PROJECT_SCHEMA_VERSION)

    paths = [args.reference_root / IFC_NAME, *(args.reference_root / name for name in STEP_NAMES)]
    for path in paths:
        run.check(f"Bron aanwezig: {path.name}", path.is_file(), expected=True, actual=path.is_file())
        if path.is_file():
            actual_sha = sha256_file(path)
            run.check(f"Bronhash: {path.name}", actual_sha == EXPECTED_SHA[path.name], expected=EXPECTED_SHA[path.name], actual=actual_sha)

    analyses = load_cached_analyses(args.cache, paths)
    session = ProjectSession.new(
        "CWS semantische referentie-import",
        customer="CWS validatie",
        order_number="V070-SEMANTIC",
        created_by="validation",
    )
    registrations = session.register_analyses(zip(paths, analyses), user="validation")
    run.check("Vier geverifieerde bronnen geregistreerd", len(registrations) == 4, expected=4, actual=len(registrations))

    progress_rows: list[dict[str, Any]] = []
    def progress(done: int, total: int, message: str) -> None:
        progress_rows.append({"done": done, "total": total, "message": message, "time": utc_stamp()})
        print(f"[semantic {done}/{total}] {message}", flush=True)

    started = time.perf_counter()
    semantic = session.semantic_import_sources(user="validation", progress_callback=progress)
    run.timings_seconds["real_semantic_import"] = round(time.perf_counter() - started, 6)
    results = [item.to_dict() for item in semantic]
    run.semantic_results = results
    by_name = {item["file_name"]: item for item in results}
    run.check("Vier bronnen semantisch geïmporteerd", len(results) == 4, expected=4, actual=len(results))
    run.check(
        "Semantische importer schema 2.1",
        all(item.get("importer_version") == "2.1" for item in results),
        expected="2.1",
        actual=sorted({str(item.get("importer_version")) for item in results}),
    )

    ifc = by_name[IFC_NAME]
    run.check("IFC route A", ifc["strategy"] == "A_semantic_structure", expected="A_semantic_structure", actual=ifc["strategy"])
    run.check("IFC materialisatiecounts", ifc["entity_counts"] == EXPECTED_IFC_MATERIALISED, expected=EXPECTED_IFC_MATERIALISED, actual=ifc["entity_counts"])
    for key, value in EXPECTED_IFC_CLASSES.items():
        run.check(f"IFC bronklasse {key}", ifc["source_class_counts"].get(key) == value, expected=value, actual=ifc["source_class_counts"].get(key))
    run.check("IFCRELAGGREGATES behouden", ifc["relationship_counts"].get("IFCRELAGGREGATES") == 356, expected=356, actual=ifc["relationship_counts"].get("IFCRELAGGREGATES"))
    run.check("MLO4 instanties", ifc["evidence"].get("MLO4_assembly_count") == 4, expected=4, actual=ifc["evidence"].get("MLO4_assembly_count"))
    run.check("MLO4/LO4 links", len(ifc["evidence"].get("MLO4_LO4_links", [])) == 4, expected=4, actual=len(ifc["evidence"].get("MLO4_LO4_links", [])))
    run.check("Ø14-fasteners", ifc["evidence"].get("bolt_or_hole_diameter_14_count") == 4, expected=4, actual=ifc["evidence"].get("bolt_or_hole_diameter_14_count"))
    run.check("Verbonden lasobjecten", ifc["evidence"].get("connected_weld_count") == 2654, expected=2654, actual=ifc["evidence"].get("connected_weld_count"))
    run.check("Herhaalde marks", ifc["evidence"].get("repeated_marks") == EXPECTED_MARKS, expected=EXPECTED_MARKS, actual=ifc["evidence"].get("repeated_marks"))
    lo4 = list(ifc["evidence"].get("LO4_parts") or [])
    run.check("Vier LO4-onderdelen", len(lo4) == 4, expected=4, actual=len(lo4))
    run.check("LO4 profiel/material/maat/massa", all(item.get("profile") == "STRIP5*120" and item.get("material") == "S235JR" and abs(float(item.get("length_mm", 0)) - 160.0) < 1e-9 and abs(float(item.get("mass_each_kg", 0)) - 0.62) < 1e-9 for item in lo4), expected=True, actual=lo4)

    for name in STEP_NAMES:
        item = by_name[name]
        run.check(f"STEP route B: {name}", item["strategy"] == "B_separate_solids", expected="B_separate_solids", actual=item["strategy"])
        run.check(f"STEP één onderdeel: {name}", item["entity_counts"].get("parts") == 1 and item["entity_counts"].get("assemblies") == 0, expected={"parts": 1, "assemblies": 0}, actual=item["entity_counts"])
        run.check(f"STEP één product/solid: {name}", item["evidence"].get("product_count") == 1 and item["evidence"].get("solid_root_count") == 1, expected={"products": 1, "solids": 1}, actual={"products": item["evidence"].get("product_count"), "solids": item["evidence"].get("solid_root_count")})
        run.check(f"STEP bestandsnaam splitst niet: {name}", item["evidence"].get("filename_not_used_for_splitting") is True, expected=True, actual=item["evidence"].get("filename_not_used_for_splitting"))

    counts = session.project.entity_counts()
    run.check("Project assemblycount", counts["assembly"] == 353, expected=353, actual=counts["assembly"])
    run.check("Project partcount", counts["part"] == 2432, expected=2432, actual=counts["part"])
    run.check("Project fastenercount", counts["fastener"] == 723, expected=723, actual=counts["fastener"])
    run.check("Project weldcount", counts["weld"] == 2654, expected=2654, actual=counts["weld"])
    all_parts = list(session.project.parts.values())
    run.check("Alle onderdelen hebben geometry hash", all(bool(item.geometry_hash) for item in all_parts), expected=len(all_parts), actual=sum(bool(item.geometry_hash) for item in all_parts))
    run.check("Alle onderdelen hebben manufacturing hash", all(bool(item.manufacturing_hash) for item in all_parts), expected=len(all_parts), actual=sum(bool(item.manufacturing_hash) for item in all_parts))
    gate = session.project.production_gate()
    run.check("Productiegate blijft gesloten", gate.get("allowed") is False, expected=False, actual=gate)
    session.project.validate()
    run.check("Projectmodel valideert", True, expected=True, actual=True)

    progress_path = output / "semantic_import_progress.json"
    progress_path.write_text(json.dumps(progress_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    run.artifacts["semantic_progress"] = str(progress_path)

    evidence_path = output / "ifc_evidence.json"
    evidence_path.write_text(json.dumps(ifc["evidence"], ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    run.artifacts["ifc_evidence"] = str(evidence_path)

    project_path = output / "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"
    started = time.perf_counter()
    session.save(project_path, embed_sources=True, user="validation", revision_message="Semantische referentie-import v0.7")
    run.timings_seconds["save_and_verify_reference_project"] = round(
        time.perf_counter() - started, 6
    )
    run.artifacts["reference_project"] = str(project_path)
    package = session.package
    if package is None:
        raise RuntimeError("ProjectSession.save leverde geen geverifieerd pakket terug")
    reopened = package.project
    reopened.validate()
    run.project_summary = reopened.summary(include_expensive_hashes=False)
    run.check("Opgeslagen project valideert", True, expected=True, actual=True)
    run.check("Opgeslagen entitycounts gelijk", reopened.entity_counts() == counts, expected=counts, actual=reopened.entity_counts())
    manifest = package.manifest
    for key in ("project_sha256", "content_sha256", "revision_content_sha256", "manufacturing_state_sha256"):
        run.check(f"Projectmanifest bevat {key}", bool(manifest.get(key)), expected=True, actual=manifest.get(key, ""))

    embedded = package.embedded_source_names()
    run.check("Alle vier bronnen ingebed", len(embedded) == 4, expected=4, actual=len(embedded))
    for source_id, archive_name in embedded.items():
        source = reopened.sources[source_id]
        target = output / "extracted_sources" / source.file_name
        package.extract_source(source_id, target)
        actual_sha = sha256_file(target)
        run.check(f"Exacte bronextractie: {source.file_name}", actual_sha == source.sha256 == EXPECTED_SHA[source.file_name], expected=source.sha256, actual=actual_sha, details=archive_name)
    session.close()

    summary_csv = output / "semantic_import_summary.csv"
    write_summary_csv(summary_csv, results, analyses)
    run.artifacts["summary_csv"] = str(summary_csv)
    semantic_json = output / "semantic_results.json"
    semantic_json.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    run.artifacts["semantic_results"] = str(semantic_json)

    if not args.skip_smokes:
        for script in SMOKES:
            print(f"[smoke] {script}", flush=True)
            run_smoke(run, output, script)

    if not args.skip_performance:
        performance_path = output / "large_step_performance.json"
        performance_log = output / "test_logs" / "large_step_performance.log"
        started = time.perf_counter()
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "validation" / "run_v07_large_model_performance.py"),
                "--reference-root",
                str(args.reference_root),
                "--output",
                str(performance_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=180,
        )
        run.timings_seconds["large_step_performance_process"] = round(
            time.perf_counter() - started, 6
        )
        performance_log.write_text(
            f"EXITCODE: {process.returncode}\n\nSTDOUT\n{process.stdout}\nSTDERR\n{process.stderr}",
            encoding="utf-8",
        )
        run.artifacts["large_step_performance"] = str(performance_path)
        run.artifacts["large_step_performance_log"] = str(performance_log)
        try:
            run.performance = json.loads(performance_path.read_text(encoding="utf-8"))
        except Exception:
            run.performance = {}
        run.check(
            "Grote STEP-prestatiepoort",
            process.returncode == 0 and run.performance.get("status") == "passed",
            expected="passed",
            actual={
                "exit_code": process.returncode,
                "status": run.performance.get("status", "missing"),
                "elapsed_seconds": run.performance.get("elapsed_seconds"),
                "max_rss_mb": run.performance.get("max_rss_mb"),
            },
            details=(process.stdout + "\n" + process.stderr)[-3000:],
        )

    results_path = output / "results.json"
    report_path = output / "SEMANTIC_IMPORT_VALIDATIE_V0.7.md"
    run.artifacts["results"] = str(results_path)
    run.artifacts["report"] = str(report_path)
    write_report(report_path, run, results, analyses)
    results_path.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    checksum_path = output / "SHA256SUMS_VALIDATION.txt"
    files = sorted(path for path in output.rglob("*") if path.is_file() and path != checksum_path)
    checksum_path.write_text("\n".join(f"{sha256_file(path)}  {path.relative_to(output).as_posix()}" for path in files) + "\n", encoding="ascii")
    print(f"[v0.7] Status: {'GESLAAGD' if run.passed else 'MISLUKT'} ({sum(item.passed for item in run.checks)}/{len(run.checks)})", flush=True)
    print(f"[v0.7] Rapport: {report_path}", flush=True)
    return 0 if run.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
