from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from cws_convertor.project.service import ProjectSession
from cws_viewer.adapters.source_geometry import ProjectGeometryCatalog, ProjectSourceResolver
from cws_viewer.contracts.geometry import TessellationSettings
from cws_viewer.geometry.isolated import IsolatedIfcMeshProvider


def run(project_path: Path, output_path: Path | None = None) -> dict[str, object]:
    started = time.perf_counter()
    session = ProjectSession.open(project_path, read_only=True)
    provider = IsolatedIfcMeshProvider(timeout_seconds=180.0)
    try:
        roots = tuple(Path(value).parent for value in session.source_paths.values())
        resolver = ProjectSourceResolver(
            session.project,
            project_package_path=project_path,
            search_roots=roots,
        )
        catalog = ProjectGeometryCatalog().build(
            session.project,
            resolver,
            verify_ifc_source_geometry=False,
        )
        requests = tuple(
            request
            for request in catalog.unique_requests(resolver)
            if request.source_format.upper() == "IFC"
        )
        batch_started = time.perf_counter()
        meshes = provider.load_many(requests, TessellationSettings())
        batch_seconds = time.perf_counter() - batch_started
        invalid = []
        for request in requests:
            mesh = meshes.get(request.geometry_id)
            if mesh is None:
                invalid.append(f"{request.geometry_id}: missing")
                continue
            if mesh.exactness != "source_tessellation":
                invalid.append(f"{request.geometry_id}: {mesh.exactness}")
            if mesh.vertex_count <= 0 or mesh.triangle_count <= 0:
                invalid.append(f"{request.geometry_id}: empty")
            if not np.isfinite(mesh.vertices).all():
                invalid.append(f"{request.geometry_id}: non-finite")
            metadata = dict(mesh.metadata)
            if not metadata.get("visual_profile_radii"):
                invalid.append(f"{request.geometry_id}: radii flag missing")
            if not metadata.get("visual_fastener_curves"):
                invalid.append(f"{request.geometry_id}: fastener flag missing")
        report: dict[str, object] = {
            "schema": "cws-full-acceptance-ifc-batch-1.0",
            "status": "PASS" if len(meshes) == len(requests) and not invalid else "FAIL",
            "project_path": str(project_path),
            "requested": len(requests),
            "returned": len(meshes),
            "batch_seconds": batch_seconds,
            "total_seconds": time.perf_counter() - started,
            "vertices": sum(mesh.vertex_count for mesh in meshes.values()),
            "triangles": sum(mesh.triangle_count for mesh in meshes.values()),
            "invalid": invalid,
            "transport": provider.transport_mode,
        }
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        provider.close()
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.project.expanduser().resolve(), args.output)
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
