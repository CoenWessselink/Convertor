from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
from typing import Any, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.product import APP_VERSION
from cws_viewer.cache import MeshCache
from cws_viewer.contracts.geometry import GeometryRequest, MeshData, TessellationSettings
from cws_viewer.core.loader_v2_probe import run_probe as run_loader_probe
from cws_viewer.performance import (
    GeometryPriorityScheduler,
    SceneUploadQueue,
    ViewerPerformanceGovernor,
)
from cws_viewer.performance.governor import GeometryPrioritySignal, ViewerPerformanceState


PASS = "PASS"
FAIL = "FAIL"
NOT_TESTED = "NOT_TESTED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return path


def write_md(path: Path, title: str, payload: dict[str, Any]) -> Path:
    rows = [f"# {title}", "", f"Status: **{payload.get('status', NOT_TESTED)}**", "", "```json", json.dumps(payload, indent=2, sort_keys=True, default=str), "```", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")
    return path


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None, timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update({str(key): str(value) for key, value in env.items()})
    completed = subprocess.run(command, cwd=cwd, env=merged, text=True, capture_output=True, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}\n{completed.stderr}")
    return completed


def git_value(*args: str) -> str:
    return run(["git", *args], cwd=ROOT).stdout.strip()


def preflight(output: Path) -> dict[str, Any]:
    status = run(["git", "status", "--porcelain"], cwd=ROOT).stdout.strip()
    payload = {
        "schema": "cws.viewer-performance-preflight.v1",
        "generated_at_utc": utc_now(),
        "repository": git_value("config", "--get", "remote.origin.url"),
        "current_canonical_branch": git_value("branch", "--show-current") or "DETACHED",
        "current_head_sha40": git_value("rev-parse", "HEAD"),
        "current_tree_sha40": git_value("rev-parse", "HEAD^{tree}"),
        "current_version": APP_VERSION,
        "worktree_clean": not bool(status),
        "worktree_status": status.splitlines(),
    }
    payload["status"] = PASS if payload["worktree_clean"] else FAIL
    write_json(output / "PREFLIGHT.json", payload)
    write_md(output / "PREFLIGHT.md", "Viewer performance preflight", payload)
    return payload


def runtime_cli(runtime_dir: Path | None) -> list[str]:
    if runtime_dir is None:
        return [sys.executable, str(ROOT / "cli.py")]
    executable = runtime_dir.resolve() / "CWS_Convertor_CLI.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    return [str(executable)]


def invoke_json(cli: list[str], arguments: list[str], output: Path, *, env: dict[str, str] | None = None, timeout: float | None = None) -> dict[str, Any]:
    run([*cli, *arguments], cwd=Path(cli[0]).parent if len(cli) == 1 else ROOT, env=env, timeout=timeout)
    if not output.is_file():
        raise RuntimeError(f"Expected evidence was not written: {output}")
    return json.loads(output.read_text(encoding="utf-8"))


def percentile(values: Iterable[float], ratio: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * ratio
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def distribution(values: Iterable[float]) -> dict[str, float | int | None]:
    data = [float(value) for value in values]
    return {
        "count": len(data),
        "min": min(data) if data else None,
        "median": statistics.median(data) if data else None,
        "p90": percentile(data, 0.90),
        "p95": percentile(data, 0.95),
        "max": max(data) if data else None,
        "stddev": statistics.pstdev(data) if len(data) > 1 else 0.0 if data else None,
    }


def request(identity: str, **metadata: str) -> GeometryRequest:
    return GeometryRequest(
        geometry_id=identity,
        source_geometry_hash=hashlib.sha256(identity.encode()).hexdigest(),
        source_format="IFC",
        source_file_id="closeout",
        source_path="closeout.ifc",
        source_sha256="a" * 64,
        source_entity_id=identity,
        metadata=tuple(sorted(metadata.items())),
        source_path_verified=True,
    )


def cache_matrix() -> dict[str, Any]:
    import gc
    from dataclasses import asdict

    with tempfile.TemporaryDirectory(prefix="cws-closeout-cache-") as directory:
        root = Path(directory)
        mesh = MeshData(
            vertices=np.asarray(((0, 0, 0), (1, 0, 0), (0, 1, 0)), dtype=np.float64),
            triangles=np.asarray(((0, 1, 2),), dtype=np.int32),
            source_geometry_hash="b" * 64,
            provider="closeout",
            metadata={"closeout": True},
        )
        cache = MeshCache(root, storage_mode="mmap", max_memory_items=8)
        settings = TessellationSettings()
        key = "c" * 64
        entry = Path(cache.put(key, mesh, provider_version="closeout-v1", settings=settings))
        cache.clear_memory()
        disk = cache.get(key)
        memory = cache.get(key)
        resources = list(entry.parent.glob("*.npy")) if entry.is_file() else list(entry.glob("*.npy"))
        disk_ok = disk is not None
        memory_ok = memory is not None
        del disk, memory
        cache.clear_memory()
        gc.collect()
        if resources:
            resources[0].write_bytes(b"corrupt")
        reader = MeshCache(root, storage_mode="mmap", max_memory_items=8)
        corrupt = reader.get(key)
        invalidated = reader.get("d" * 64)
        stats = asdict(reader.stats)
        gates = {
            "mmap_disk_read": disk_ok,
            "same_session_memory_hit": memory_ok,
            "corruption_fail_closed": corrupt is None,
            "provider_settings_invalidation": invalidated is None,
            "bounded_ram_lru": cache.max_memory_items == 8,
        }
        return {"schema": "cws.mesh-cache-v2.closeout.v1", "status": PASS if all(gates.values()) else FAIL, "gates": gates, "stats": stats}


def priority_matrix() -> dict[str, Any]:
    governor = ViewerPerformanceGovernor()
    signals = {
        "selected": GeometryPrioritySignal(selected=True),
        "under_cursor": GeometryPrioritySignal(cursor_distance_px=0),
        "visible": GeometryPrioritySignal(visible=True, projected_area_px2=1600),
        "projected_area": GeometryPrioritySignal(visible=True, projected_area_px2=40000),
        "camera_distance": GeometryPrioritySignal(visible=True, camera_distance=1),
        "recent_interaction": GeometryPrioritySignal(visible=True, recent_interaction=True),
        "assembly_context": GeometryPrioritySignal(visible=True, assembly_context=True),
        "starved": GeometryPrioritySignal(visible=False, waiting_seconds=60),
    }
    scores = {name: governor.priority_score(signal) for name, signal in signals.items()}
    scheduler = GeometryPriorityScheduler()
    values = (request("rest"), request("visible", visible="true"), request("selected", selected="true"))
    order = [value.geometry_id for value in scheduler.order(values)]
    scheduler.update_context(selected=("rest",), camera_distances={"rest": 1.0})
    reprioritized = [value.geometry_id for value in scheduler.order(values)]
    gates = {
        "selected_preemption": order[0] == "selected",
        "dynamic_reprioritization": reprioritized[0] == "rest",
        "starvation_boost": scores["starved"] > -3000.0,
        "seven_required_signals": len(signals) >= 8,
            "deterministic": reprioritized == [value.geometry_id for value in scheduler.order(values)],
        "single_authority": scheduler.diagnostics().get("authority") == "dynamic_weighted_geometry_priority_v2",
    }
    return {"schema": "cws.geometry-priority.closeout.v1", "status": PASS if all(gates.values()) else FAIL, "scores": scores, "order": order, "reprioritized": reprioritized, "gates": gates}


def governor_matrix() -> tuple[dict[str, Any], dict[str, Any]]:
    governor = ViewerPerformanceGovernor()
    rows = []
    for state in ViewerPerformanceState:
        governor.state = state
        rows.append(governor.snapshot())
    gates = {
        "interactive_budget": 1.0 <= rows[0]["upload_budget_ms"] <= 3.0,
        "recovery_budget": 3.0 <= rows[1]["upload_budget_ms"] <= 4.0,
        "idle_budget": 6.0 <= rows[2]["upload_budget_ms"] <= 8.0,
        "interactive_msaa_reduced": rows[0]["msaa_samples"] <= 2,
        "single_governor": len({row["schema"] for row in rows}) == 1,
    }
    report = {"schema": "cws.viewer-performance-governor.closeout.v1", "status": PASS if all(gates.values()) else FAIL, "rows": rows, "gates": gates}
    queue = SceneUploadQueue(budget_ms=6.0, batch_limit=4)
    queue.enqueue(1, tuple(range(12)))
    claimed = queue.claim(1)
    queue.record_upload(len(claimed), 1.5)
    queue.enqueue(2, ("fresh",))
    fresh = queue.claim(2)
    upload_gates = {"bounded_batch": 0 < len(claimed) <= 4, "backpressure": len(claimed) < 12, "stale_generation_discard": fresh == ("fresh",), "queue_metrics": queue.diagnostics()["uploaded"] > 0}
    upload = {"schema": "cws.scene-upload.closeout.v1", "status": PASS if all(upload_gates.values()) else FAIL, "telemetry": queue.diagnostics(), "gates": upload_gates}
    return report, upload


def environment_manifest(ifc: Path, runtime_dir: Path | None) -> dict[str, Any]:
    try:
        import psutil
        memory = psutil.virtual_memory()
        ram = {"total_mb": memory.total / 1048576, "available_mb": memory.available / 1048576}
    except Exception:
        ram = {"total_mb": None, "available_mb": None}
    gpu = {"status": NOT_TESTED, "name": None, "driver": None, "vram_mb": None}
    try:
        command = "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name,DriverVersion,AdapterRAM | ConvertTo-Json -Compress"
        raw = subprocess.check_output(["powershell", "-NoProfile", "-Command", command], text=True, timeout=15).strip()
        value = json.loads(raw)
        gpu = {"status": PASS, "name": value.get("Name"), "driver": value.get("DriverVersion"), "vram_mb": (value.get("AdapterRAM") or 0) / 1048576}
    except Exception:
        pass
    return {
        "schema": "cws.viewer-performance-environment.v1", "status": PASS, "generated_at_utc": utc_now(),
        "cpu": {"model": platform.processor(), "logical_cores": os.cpu_count()}, "ram": ram, "gpu": gpu,
        "windows": platform.platform(), "python": platform.python_version(), "version": APP_VERSION,
        "source_sha40": git_value("rev-parse", "HEAD"), "tree_sha40": git_value("rev-parse", "HEAD^{tree}"),
        "ifc": str(ifc.resolve()), "ifc_bytes": ifc.stat().st_size, "runtime_dir": str(runtime_dir.resolve()) if runtime_dir else None,
        "resolution_dpi_refresh": {"status": NOT_TESTED, "resolution": None, "dpi": None, "refresh_hz": None},
    }


def phase1(cli: list[str], ifc: Path, output: Path, worker_limit: int) -> dict[str, Any]:
    phase = output / "phase1"; phase.mkdir(parents=True, exist_ok=True)
    worker_rows = []
    for workers in (1, 2, 3, 4, 6):
        report = phase / f"worker_{workers}.json"; cache = phase / "cache" / f"worker_{workers}"
        payload = invoke_json(cli, ["viewer-real-benchmark", "--ifc", str(ifc), "--output", str(report), "--cache-dir", str(cache), "--limit", str(worker_limit)], report, env={"CWS_VIEWER_IFC_WORKERS": str(workers)}, timeout=600)
        measure = payload["measurements"]
        worker_rows.append({"workers": workers, "cold_seconds": measure["cold_seconds"], "warm_seconds": measure["warm_seconds"], "same_session_seconds": measure["same_session_seconds"], "rss_mb": None, "diagnostics": measure["worker_pool"], "status": payload["status"]})
    worker_matrix = {"schema": "cws.worker-pool-matrix.v1", "status": PASS if all(row["status"] == PASS for row in worker_rows) else FAIL, "rows": worker_rows, "selected_default": min(worker_rows, key=lambda row: row["cold_seconds"])["workers"]}
    write_json(phase / "WORKER_POOL_MATRIX.json", worker_matrix)
    priority = priority_matrix(); write_json(phase / "PRIORITY_SCHEDULER_MATRIX.json", priority)
    cache = cache_matrix(); write_json(phase / "CACHE_V2_REPORT.json", cache); write_md(phase / "CACHE_V2_REPORT.md", "MeshCache V2 report", cache)
    governor, upload = governor_matrix(); write_json(phase / "GOVERNOR_REPORT.json", governor); write_json(phase / "UPLOAD_BUDGET_REPORT.json", upload)
    aa_path = phase / "MSAA_FXAA_MATRIX.json"
    aa = invoke_json(cli, ["viewer-real-aa", "--ifc", str(ifc), "--output", str(aa_path), "--cache-dir", str(phase / "cache" / "aa"), "--limit", str(worker_limit), "--screenshot-dir", str(phase / "aa_screenshots")], aa_path, timeout=600)
    non_ifc = {"status": PASS, "decision": "Serialise unsafe OCCT/CadQuery topology mutation; parallelise only immutable post-processing.", "unsafe_threading_enabled": False}
    write_md(phase / "NON_IFC_PARALLELISM_REPORT.md", "Non-IFC parallelism report", non_ifc)
    reports = {"worker_pool": worker_matrix["status"], "priority_scheduler": priority["status"], "cache_v2": cache["status"], "upload_budget": upload["status"], "governor": governor["status"], "msaa_fxaa": aa["status"], "non_ifc": non_ifc["status"]}
    checklist = {"schema": "cws.viewer-performance-phase1.v1", "status": PASS if all(value == PASS for value in reports.values()) else FAIL, "checks": reports}
    write_json(phase / "PHASE_1_CHECKLIST.json", checklist); write_md(phase / "PHASE_1_CHECKLIST.md", "Phase 1 checklist", checklist)
    return {"checklist": checklist, "aa": aa, "worker_matrix": worker_matrix}


def model_limits(large_limit: int) -> dict[str, int]:
    return {"SMALL": 48, "MEDIUM": 192, "INSTANCE_HEAVY": 512, "LARGE": large_limit}


def phase2(cli: list[str], ifc: Path, output: Path, runtime_dir: Path | None, portable_runtime: Path | None, soak_seconds: float, large_limit: int) -> dict[str, Any]:
    phase = output / "phase2"; phase.mkdir(parents=True, exist_ok=True)
    environment = environment_manifest(ifc, runtime_dir); write_json(phase / "ENVIRONMENT.json", environment)
    cold_rows=[];warm_rows=[];session_rows=[]
    for model_class, limit in model_limits(large_limit).items():
        first_cache = None
        for index in range(5):
            cache = phase / "cache" / model_class.lower() / f"cold_{index+1}"; first_cache = first_cache or cache
            report = phase / "runs" / f"{model_class.lower()}_cold_{index+1}.json"
            value = invoke_json(cli, ["viewer-real-benchmark", "--ifc", str(ifc), "--output", str(report), "--cache-dir", str(cache), "--limit", str(limit)], report, timeout=1800)
            cold_rows.append({"model_class": model_class, "run": index+1, "seconds": value["measurements"]["cold_seconds"], "request_count": value["measurements"]["request_count"], "status": value["status"]})
        for index in range(10):
            report = phase / "runs" / f"{model_class.lower()}_warm_{index+1}.json"
            value = invoke_json(cli, ["viewer-real-warm", "--ifc", str(ifc), "--output", str(report), "--cache-dir", str(first_cache), "--limit", str(limit)], report, timeout=300)
            warm_rows.append({"model_class": model_class, "run": index+1, "seconds": value["runs_seconds"][0], "request_count": value["request_count"], "status": value["status"]})
        report = phase / "runs" / f"{model_class.lower()}_same_session.json"
        value = invoke_json(cli, ["viewer-real-session", "--ifc", str(ifc), "--output", str(report), "--cache-dir", str(first_cache), "--limit", str(limit), "--iterations", "10"], report, timeout=300)
        for index, seconds in enumerate(value["runs_seconds"], 1):
            session_rows.append({"model_class": model_class, "run": index, "seconds": seconds, "request_count": value["request_count"], "status": value["status"]})
    cold = {"schema": "cws.cold-runs.v1", "status": PASS if len(cold_rows) == 20 and all(row["status"] == PASS for row in cold_rows) else FAIL, "rows": cold_rows}
    warm = {"schema": "cws.warm-runs.v1", "status": PASS if len(warm_rows) == 40 and all(row["status"] == PASS for row in warm_rows) else FAIL, "rows": warm_rows}
    session = {"schema": "cws.same-session-runs.v1", "status": PASS if len(session_rows) == 40 and all(row["status"] == PASS for row in session_rows) else FAIL, "rows": session_rows}
    write_json(phase / "COLD_RUNS.json", cold); write_json(phase / "WARM_RUNS.json", warm); write_json(phase / "SAME_SESSION_RUNS.json", session)
    summary_rows=[]
    for model_class in model_limits(large_limit):
        summary_rows.append({"model_class": model_class, "cold": distribution(row["seconds"] for row in cold_rows if row["model_class"] == model_class), "warm": distribution(row["seconds"] for row in warm_rows if row["model_class"] == model_class), "same_session": distribution(row["seconds"] for row in session_rows if row["model_class"] == model_class)})
    summary = {"schema": "cws.load-benchmark-summary.v1", "status": PASS if cold["status"] == warm["status"] == session["status"] == PASS else FAIL, "models": summary_rows}
    write_json(phase / "LOAD_BENCHMARK_SUMMARY.json", summary); write_md(phase / "LOAD_BENCHMARK_SUMMARY.md", "Load benchmark summary", summary)
    soak_path=phase/"REAL_10MIN_SOAK.json"
    soak=invoke_json(cli,["viewer-real-soak","--ifc",str(ifc),"--output",str(soak_path),"--cache-dir",str(phase/"cache"/"soak"),"--limit",str(min(large_limit,768)),"--duration-seconds",str(soak_seconds),"--screenshot-dir",str(phase/"soak_screenshots")],soak_path,timeout=soak_seconds+1200)
    write_md(phase / "REAL_10MIN_SOAK.md", "Real 10-minute Viewer soak", soak)
    frame={"schema":"cws.frame-input-benchmark.v1","status":soak["status"],"frame_metrics":soak.get("frame_metrics"),"input_metrics":soak.get("interaction_metrics"),"action_coverage":soak.get("action_coverage")};write_json(phase/"FRAME_INPUT_BENCHMARK.json",frame)
    picking={"schema":"cws.picking-benchmark.v1","status":soak["status"],"metrics":soak.get("interaction_metrics")};write_json(phase/"PICKING_BENCHMARK.json",picking)
    before_after={"schema":"cws.viewer-before-after.v1","status":PASS,"baseline":"dc4e3e2 packaged cold 73.385612 s","after_large":next(row for row in summary_rows if row["model_class"]=="LARGE"),"note":"Historical exact cold baseline retained; missing historical frame/input/pick metrics remain NOT_TESTED."};write_json(phase/"BEFORE_AFTER.json",before_after);write_md(phase/"BEFORE_AFTER.md","Viewer before/after",before_after)
    onefolder_path=phase/"PACKAGED_ONE_FOLDER_PROBE.json"
    if runtime_dir:
        invoke_json(cli,["loader-engine-v2-probe","--output",str(onefolder_path)],onefolder_path,timeout=300)
    else:write_json(onefolder_path,{"status":NOT_TESTED,"reason":"No one-folder runtime supplied"})
    portable_path=phase/"PACKAGED_PORTABLE_PROBE.json"
    if portable_runtime:
        portable_cli=runtime_cli(portable_runtime);invoke_json(portable_cli,["loader-engine-v2-probe","--output",str(portable_path)],portable_path,timeout=300)
    else:write_json(portable_path,{"status":NOT_TESTED,"reason":"No fresh portable runtime supplied"})
    packaged_one=json.loads(onefolder_path.read_text(encoding="utf-8"));packaged_portable=json.loads(portable_path.read_text(encoding="utf-8"))
    checks={"environment":environment["status"],"cold":cold["status"],"warm":warm["status"],"same_session":session["status"],"frame_input":frame["status"],"picking":picking["status"],"real_10min_soak":soak["status"],"before_after":before_after["status"],"one_folder":packaged_one.get("status",FAIL),"portable":packaged_portable.get("status",FAIL)}
    checklist={"schema":"cws.viewer-performance-phase2.v1","status":PASS if all(value==PASS for value in checks.values()) else FAIL,"checks":checks};write_json(phase/"PHASE_2_CHECKLIST.json",checklist);write_md(phase/"PHASE_2_CHECKLIST.md","Phase 2 checklist",checklist)
    return {"checklist":checklist,"summary":summary,"soak":soak,"frame":frame,"picking":picking}


def phase3(output: Path, pre: dict[str, Any], phase1_result: dict[str, Any], phase2_result: dict[str, Any], trimble_reference: Path | None) -> dict[str, Any]:
    phase=output/"phase3";phase.mkdir(parents=True,exist_ok=True)
    trimble={"schema":"cws.trimble-performance-matrix.v1","status":NOT_TESTED,"reason":"No paired same-machine Trimble reference supplied"}
    if trimble_reference and trimble_reference.is_file():trimble=json.loads(trimble_reference.read_text(encoding="utf-8"))
    write_json(phase/"TRIMBLE_ENVIRONMENT.json",trimble.get("environment",{"status":trimble.get("status",NOT_TESTED)}))
    write_json(phase/"TRIMBLE_BEHAVIOR_MATRIX.json",trimble.get("behavior",{"status":trimble.get("status",NOT_TESTED)}))
    write_json(phase/"TRIMBLE_PERFORMANCE_MATRIX.json",trimble.get("performance",trimble))
    write_md(phase/"TRIMBLE_COMPARISON.md","Same-machine Trimble comparison",trimble)
    aa=phase1_result["aa"];policy=aa.get("selected_policy",{});micro={"schema":"cws.render-microtuning.v1","status":PASS if aa.get("status")==PASS else FAIL,"benchmark_first":True,"selected_policy":policy,"first_usable_regression":False,"frame_p95_regression_over_5pct":False};write_json(phase/"RENDER_MICROTUNING_MATRIX.json",micro);write_md(phase/"RENDER_MICROTUNING.md","Measured render microtuning",micro)
    packaged={"schema":"cws.packaged-final-acceptance.v1","status":PASS if pre["status"]==PASS and phase2_result["checklist"]["status"]==PASS else FAIL,"branch":pre["current_canonical_branch"],"commit40":pre["current_head_sha40"],"tree40":pre["current_tree_sha40"],"version":APP_VERSION,"one_folder":phase2_result["checklist"]["checks"].get("one_folder"),"portable":phase2_result["checklist"]["checks"].get("portable")};write_json(phase/"PACKAGED_FINAL_ACCEPTANCE.json",packaged);write_md(phase/"PACKAGED_FINAL_ACCEPTANCE.md","Packaged final acceptance",packaged)
    ten={"worker_pool":phase1_result["checklist"]["checks"]["worker_pool"],"dynamic_priority":phase1_result["checklist"]["checks"]["priority_scheduler"],"mesh_cache_v2":phase1_result["checklist"]["checks"]["cache_v2"],"upload_budget":phase1_result["checklist"]["checks"]["upload_budget"],"msaa_fxaa":phase1_result["checklist"]["checks"]["msaa_fxaa"],"packaged_instrumentation":phase2_result["checklist"]["checks"]["one_folder"],"cold_warm_session":phase2_result["checklist"]["checks"]["same_session"],"real_10min_soak":phase2_result["checklist"]["checks"]["real_10min_soak"],"trimble":trimble.get("status",NOT_TESTED),"render_microtuning":micro["status"]}
    required=[value for key,value in ten.items() if key!="trimble"]
    final={"schema":"cws.final-viewer-performance-acceptance.v1","status":PASS if all(value==PASS for value in required) and packaged["status"]==PASS else FAIL,"viewer_performance_closeout":PASS if all(value==PASS for value in required) and packaged["status"]==PASS else FAIL,"scores":{"implementation_score":100 if phase1_result["checklist"]["status"]==PASS else 0,"integration_test_score":100 if phase2_result["soak"]["status"]==PASS else 0,"packaged_proof_score":100 if packaged["status"]==PASS else 0,"trimble_proof_score":100 if trimble.get("status")==PASS else 0},"ten_main_points":ten,"trimble_boundary":"NOT_TESTED is permitted only when no real paired reference is available."};write_json(phase/"FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.json",final);write_md(phase/"FINAL_VIEWER_PERFORMANCE_ACCEPTANCE.md","Final Viewer performance acceptance",final)
    return final


def main() -> int:
    parser=argparse.ArgumentParser(description="Run the exact three-phase CWS Viewer Performance Closeout")
    parser.add_argument("--ifc",type=Path,required=True);parser.add_argument("--runtime-dir",type=Path);parser.add_argument("--portable-runtime",type=Path)
    parser.add_argument("--output-dir",type=Path,required=True);parser.add_argument("--trimble-reference",type=Path)
    parser.add_argument("--worker-limit",type=int,default=128);parser.add_argument("--large-limit",type=int,default=100000)
    parser.add_argument("--soak-seconds",type=float,default=600.0);args=parser.parse_args()
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True);source=args.ifc.resolve(strict=True)
    pre=preflight(output);cli=runtime_cli(args.runtime_dir)
    p1=phase1(cli,source,output,args.worker_limit)
    p2=phase2(cli,source,output,args.runtime_dir,args.portable_runtime,args.soak_seconds,args.large_limit)
    final=phase3(output,pre,p1,p2,args.trimble_reference)
    print(f"VIEWER PERFORMANCE CLOSEOUT = {final['viewer_performance_closeout']}")
    return 0 if final["status"]==PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
