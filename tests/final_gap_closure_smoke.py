from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np

from cws_convertor.drawings import DrawingProjectionModel
from cws_convertor.manufacturing.routing import MachineRoutingService
from cws_convertor.output import DocumentOutputService
from cws_viewer.contracts.geometry import GeometryRequest, MeshData
from cws_viewer.geometry.loader import GeometryLoadCoordinator


def _request(root: Path, value: str) -> GeometryRequest:
    digest = "a" * 64
    return GeometryRequest(value, digest, "IFC", "fixture.ifc", str(root / "fixture.ifc"), digest, source_entity_id=value, source_path_verified=True)


class _BatchProvider:
    provider_version = "batch-test-v1"
    def __init__(self): self.batch_calls = 0; self.single_calls = 0
    def supports(self, request): return request.source_format == "IFC"
    def _mesh(self, request):
        vertices = np.array(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)), dtype=float); triangles = np.array(((0,1,2),), dtype=np.int32)
        return MeshData(vertices, triangles, request.source_geometry_hash, "test", "source_tessellation")
    def load(self, request, settings, *, cancel_check=None): self.single_calls += 1; return self._mesh(request)
    def load_many(self, requests, settings, *, cancel_check=None): self.batch_calls += 1; return {request.geometry_id:self._mesh(request) for request in requests}


def main() -> int:
    checks = {}
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw); (root / "fixture.ifc").write_text("IFC", encoding="ascii")
        provider = _BatchProvider(); coordinator = GeometryLoadCoordinator((provider,), max_workers=4)
        report = coordinator.load_many((_request(root, "A"), _request(root, "B")), allow_proxy=False)
        checks["ifc_batch_coordinator"] = provider.batch_calls == 1 and provider.single_calls == 0 and report.ready_count == 2
        vertices = np.array(((0.,0.,0.),(100.,0.,0.),(0.,50.,0.),(0.,0.,20.)), dtype=float); triangles = np.array(((0,1,2),(0,1,3),(0,2,3),(1,2,3)), dtype=np.int32)
        pdf = DrawingProjectionModel.export_pdf(root / "vector.pdf", vertices, triangles, views=("front","top","iso"), sheet_mm=(420.,297.), scale_denominator=2, title="CWS test")
        checks["vector_pdf"] = pdf.read_bytes().startswith(b"%PDF") and pdf.stat().st_size > 512
        record = DocumentOutputService.shared().register(pdf, kind="test", producer="smoke")
        checks["document_output_authority"] = bool(record.sha256) and record.path == pdf
        decision = MachineRoutingService().route("P1", {"V550":{"production_ready":True,"blocking_codes":[]}}); blocked = MachineRoutingService().route("P2", {"V623":{"production_ready":False,"blocking_codes":["NO_TOOL"]}})
        checks["machine_routing_authority"] = decision.eligible and decision.machine_id == "V550" and not blocked.eligible
    checks["all"] = all(checks.values()); output = Path("validation/final_gap_closure/RESULTS.json"); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps({"schema":"cws.final-gap-closure.v1","status":"PASS" if checks["all"] else "FAIL","checks":checks}, indent=2), encoding="utf-8")
    print(f"FINAL_GAP_CLOSURE={'PASS' if checks['all'] else 'FAIL'}"); return 0 if checks["all"] else 1


if __name__ == "__main__": raise SystemExit(main())
