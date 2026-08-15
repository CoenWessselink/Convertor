"""Runtime proof for the crash-isolated IFC geometry worker.

The same high-level provider is exercised in every release gate. Source mode
uses multiprocessing spawn; a PyInstaller-frozen CWS Viewer uses the explicit
persistent subprocess service. No GPU/OpenGL window is required.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

from cws_viewer.contracts.geometry import GeometryRequest, TessellationSettings
from cws_viewer.geometry.isolated import IsolatedIfcMeshProvider

_MINIMAL_IFC = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('cws_worker_selftest.ifc','2026-08-15T00:00:00',('CWS'),('CWS'),'CWS Viewer','CWS','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#10=IFCCARTESIANPOINT((0.,0.,0.));
#11=IFCDIRECTION((0.,0.,1.));
#12=IFCDIRECTION((1.,0.,0.));
#13=IFCAXIS2PLACEMENT3D(#10,#11,#12);
#15=IFCCARTESIANPOINT((0.,0.));
#14=IFCAXIS2PLACEMENT2D(#15,$);
#20=IFCRECTANGLEPROFILEDEF(.AREA.,'CWS-TEST',#14,100.,50.);
#100=IFCEXTRUDEDAREASOLID(#20,#13,#11,10.);
ENDSEC;
END-ISO-10303-21;
"""


def run_isolated_ifc_worker_selftest() -> dict:
    with tempfile.TemporaryDirectory(prefix="cws-ifc-worker-selftest-") as temp:
        path = Path(temp) / "cws_worker_selftest.ifc"
        path.write_text(_MINIMAL_IFC, encoding="ascii")
        source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        geometry_sha = hashlib.sha256(b"CWS isolated IFC worker selftest geometry v1").hexdigest()
        request = GeometryRequest(
            geometry_id="geometry:cws-worker-selftest",
            source_geometry_hash=geometry_sha,
            source_format="IFC",
            source_file_id="source:cws-worker-selftest",
            source_path=str(path),
            source_sha256=source_sha,
            source_entity_id="100",
            source_item_ids=("100",),
        )
        provider = IsolatedIfcMeshProvider(timeout_seconds=30.0, start_method="spawn")
        transport = provider.transport_mode
        worker_pid = None
        worker_frozen = None
        worker_executable = ""
        try:
            mesh = provider.load(request, TessellationSettings())
            client = getattr(provider, "_frozen_client", None)
            if client is not None:
                worker_pid = getattr(client, "worker_pid", None)
                worker_frozen = getattr(client, "worker_frozen", None)
                worker_executable = str(getattr(client, "worker_executable", "") or "")
        finally:
            provider.close()
        if mesh.vertex_count < 8 or mesh.triangle_count < 12:
            raise RuntimeError(
                f"IFC-worker leverde onverwacht kleine mesh: {mesh.vertex_count} vertices / {mesh.triangle_count} triangles"
            )
        bounds = mesh.bounds
        assert bounds is not None
        size = bounds.size
        expected = (100.0, 50.0, 10.0)
        actual = (float(size.x), float(size.y), float(size.z))
        for got, want in zip(actual, expected):
            if abs(got - want) > 1e-5:
                raise RuntimeError(f"IFC-worker maat wijkt af: {actual} verwacht {expected}")
        return {
            "status": "passed",
            "transport": transport,
            "worker_pid": worker_pid,
            "worker_frozen": worker_frozen,
            "worker_executable": worker_executable,
            "provider": mesh.provider,
            "exactness": mesh.exactness,
            "vertex_count": mesh.vertex_count,
            "triangle_count": mesh.triangle_count,
            "bounds_mm": actual,
            "mesh_hash": mesh.mesh_hash,
            "warnings": list(mesh.warnings),
        }


__all__ = ["run_isolated_ifc_worker_selftest"]
