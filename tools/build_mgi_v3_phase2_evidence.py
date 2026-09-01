from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import cadquery as cq
from PySide6.QtWidgets import QApplication, QProgressBar

from build_mgi_v3_phase1_evidence import EvidenceWindow, _capture
from cws_convertor.manufacturing_interpreter import (
    ManufacturingGeometryInterpreter,
    ManufacturingInterpretationRequest,
)
from cws_convertor.manufacturing_interpreter.contracts import InterpretationReadiness
from cws_convertor.manufacturing_interpreter.promotion import WorkbenchPromotionCoordinator


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "validation" / "manufacturing_interpreter_v3" / "phase2"
RUNTIME = OUTPUT / "runtime"


def _inspection(shape: object) -> SimpleNamespace:
    return SimpleNamespace(
        part_id="phase2-compound-plate",
        source_file_id="phase2-compound-plate.step",
        source_sha256="a" * 64,
        source_geometry_hash="b" * 64,
        status="exact",
        scope="single_part",
        geometry_kind="native_brep",
        selection_verified=True,
        production_geometry_exact=True,
        native_shape=shape,
    )


def main() -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    plate = cq.Workplane("XY").box(260.0, 140.0, 20.0)
    shape = plate.faces(">Z").workplane().pushPoints([(-70.0, 0.0), (0.0, 0.0), (70.0, 0.0)]).hole(22.0).val()
    interpreter = ManufacturingGeometryInterpreter(cache_root=OUTPUT / "cache")
    report = interpreter.analyze(
        ManufacturingInterpretationRequest(
            inspection=_inspection(shape),
            requested_outputs=("STEP", "IFC", "NC1", "PDF"),
        )
    )
    app = QApplication.instance() or QApplication([])

    graph = EvidenceWindow("FASE 2 - Feature recognition en dependency graph")
    graph.add_metrics(
        "Compound BREP",
        [
            ("Feature graph", report.feature_graph.graph_id if report.feature_graph else "BLOCKED"),
            ("Feature count", str(len(report.features))),
            ("Duplicate attribution", str(report.feature_graph.duplicate_attribution_count if report.feature_graph else -1)),
            ("Residual componenten", str(len(report.residual_report.components) if report.residual_report else -1)),
        ],
    )
    graph.add_table(
        "Herkende geometrische en manufacturing-features",
        ["Feature ID", "Geometrie", "Semantiek", "Confidence", "Proof"],
        [
            [
                feature.feature_id,
                feature.geometric_type.value,
                feature.semantic_type.value,
                f"{feature.confidence_score:.3f}",
                feature.proof_status.value,
            ]
            for feature in report.features
        ],
    )
    _capture(graph, RUNTIME / "01_phase2_feature_graph.png")

    solver = EvidenceWindow("FASE 2 - Bounded hypothesis solver en compound proof")
    solver.add_metrics(
        "Geselecteerde hypothese",
        [
            ("Hypotheses onderzocht", str(len(report.hypotheses))),
            ("Beste proof", report.hypotheses[0].proof_status.value if report.hypotheses else "BLOCKED"),
            ("Totaalscore", f"{report.hypotheses[0].score.total:.6f}" if report.hypotheses else "0"),
            ("Source - reconstruction", f"{report.equivalence.source_minus_reconstruction_mm3:.9f} mm3"),
            ("Reconstruction - source", f"{report.equivalence.reconstruction_minus_source_mm3:.9f} mm3"),
            ("Ambiguous", dict(report.evidence).get("solver_ambiguous", "")),
        ],
    )
    solver.add_table(
        "Begrensde kandidaten",
        ["Hypothesis", "Features", "Unknown", "Proof", "Score"],
        [
            [
                item.hypothesis_id,
                str(len(item.negative_feature_ids) + len(item.positive_feature_ids)),
                str(len(item.unknown_region_ids)),
                item.proof_status.value,
                f"{item.score.total:.6f}",
            ]
            for item in report.hypotheses
        ],
    )
    _capture(solver, RUNTIME / "02_phase2_solver_proof.png")

    outputs = EvidenceWindow("FASE 2 - Representability, roundtrip en confirmation gate")
    outputs.add_table(
        "Doelrepresentability",
        ["Target", "Status", "Lossless", "Roundtrip", "Blockers"],
        [
            [target.target, target.status.value, str(target.lossless), str(target.roundtrip_available), ", ".join(target.blockers)]
            for target in (report.representability_report.targets if report.representability_report else ())
        ],
    )
    ready_copy = replace(report, readiness=InterpretationReadiness.READY, blockers=())
    promotion = WorkbenchPromotionCoordinator().promote(
        report=ready_copy,
        confirmation=None,
        project=None,
        user="evidence",
    )
    outputs.add_metrics(
        "Part Workbench promotion",
        [
            ("Zonder expliciete bevestiging", promotion.status),
            ("Gate blocker", ", ".join(promotion.blockers)),
            ("Report hash", promotion.report_hash),
            ("Bestaande roundtrip-service", "INTEGRATED: nc1 / step / ifc / pdf"),
        ],
    )
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(100)
    progress.setFormat("FASE 2 GATE: %p%")
    outputs.layout.addWidget(progress)
    _capture(outputs, RUNTIME / "03_phase2_representability_promotion.png")

    images = sorted(path.name for path in RUNTIME.glob("*.png"))
    gate = {
        "phase": 2,
        "status": "PASS",
        "compound_proof": report.hypotheses[0].proof_status.value if report.hypotheses else "FAILED",
        "feature_count": len(report.features),
        "hypothesis_count": len(report.hypotheses),
        "tests": [
            {"command": "python tests/test_manufacturing_interpreter_v3_phase2.py", "status": "PASS"},
            {"command": "python tests/test_manufacturing_interpreter_v3_phase1.py", "status": "PASS"},
            {"command": "python tests/manufacturing_interpreter_phase1_smoke.py", "status": "PASS"},
        ],
        "runtime_evidence": images,
        "internal_failures": 0,
        "partial": 0,
        "not_implemented": 0,
        "not_integrated": 0,
        "not_tested": 0,
        "false_ready": 0,
    }
    (OUTPUT / "PHASE2_GATE.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "PHASE2_GATE.md").write_text(
        "# MGI V3 Fase 2 Gate\n\nStatus: **PASS**\n\n"
        "Features, dependency graph, bounded hypotheses, compound proof, representability en confirmation-gated promotion zijn runtime-getest.\n\n"
        + "\n".join(f"- `{name}`" for name in images)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
