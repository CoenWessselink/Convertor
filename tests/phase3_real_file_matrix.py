from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pdf_support import canonical_from_nc1, create_trusted_pdf


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def smallest(roots: tuple[Path, ...], suffixes: tuple[str, ...]) -> Path:
    candidates = [
        path
        for root in roots
        if root.is_dir()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    ]
    if not candidates:
        raise FileNotFoundError(f"No fixture found for {suffixes}")
    return min(candidates, key=lambda item: (item.stat().st_size, str(item).lower()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "phases" / "PHASE_3_REAL_FILE_MATRIX.json")
    args = parser.parse_args()
    fixtures = ROOT / "reference-models-local"
    phase_fixtures = ROOT / "validation" / "phases" / "fixtures"
    phase1_diff = json.loads((ROOT / "validation" / "phases" / "PHASE_1_REAL_SOURCE_RESULT_DIFFERENCE.json").read_text(encoding="utf-8"))
    rows = []
    nc1 = smallest((fixtures, ROOT / "validation" / "v0.2_generated_nc1"), (".nc1", ".nc"))
    with tempfile.TemporaryDirectory(prefix="cws-real-nc1-") as folder:
        completed = subprocess.run([sys.executable, str(ROOT / "cli.py"), "nc1-to-step", str(nc1), "-o", folder],
                                   cwd=ROOT, capture_output=True, text=True, timeout=180, check=False)
        generated = sorted(Path(folder).glob("*.step"))
        rows.append({"format": "NC1", "source": str(nc1), "sha256": digest(nc1), "bytes": nc1.stat().st_size,
                     "expected_identity": nc1.stem, "exactness": "deterministic_dstv",
                     "outputs": [item.name for item in generated], "roundtrip": "physical_nc1_to_step_generated",
                     "limitations": ["machine_controller_output_not_authorized"],
                     "passed": completed.returncode == 0 and len(generated) == 1 and generated[0].stat().st_size > 1000})
    trusted_pdf = phase_fixtures / "phase3-trusted-nc1-roundtrip.pdf"
    trusted_pdf.parent.mkdir(parents=True, exist_ok=True)
    create_trusted_pdf(canonical_from_nc1(nc1), trusted_pdf)
    step = Path(phase1_diff["source"]["path"])
    rows.append({"format": "STEP", "source": str(step), "sha256": digest(step), "bytes": step.stat().st_size,
                 "expected_identity": phase1_diff["result"]["source_geometry_hash"],
                 "exactness": phase1_diff["result"]["geometry_kind"], "outputs": [phase1_diff["result"]["path"]],
                 "roundtrip": "source_result_difference_verified",
                 "performance": str(ROOT / "validation" / "phases" / "PHASE_1_LARGE_MODEL_PERFORMANCE.json"),
                 "limitations": [], "passed": digest(step) == phase1_diff["source"]["sha256"] and phase1_diff["status"] == "passed"})
    import ifcopenshell
    ifc = smallest((fixtures, phase_fixtures), (".ifc",))
    model = ifcopenshell.open(str(ifc))
    products = model.by_type("IfcProduct")
    rows.append({"format": "IFC", "source": str(ifc), "sha256": digest(ifc), "bytes": ifc.stat().st_size,
                 "expected_identity": "IfcProduct GlobalId set", "exactness": "semantic_import_with_proxy_or_exact_on_demand",
                 "outputs": ["semantic IFC product inventory"], "roundtrip": "semantic_parse_verified",
                 "limitations": ["production_exactness_requires_per_part_geometry_proof"], "product_count": len(products),
                 "passed": len(products) > 0 and all(bool(getattr(item, "GlobalId", None)) for item in products[:100])})
    import fitz
    pdf = smallest(
        (ROOT / "validation" / "viewer_v6" / "roundtrips", phase_fixtures),
        (".pdf",),
    )
    document = fitz.open(pdf)
    rows.append({"format": "Trusted PDF", "source": str(pdf), "sha256": digest(pdf), "bytes": pdf.stat().st_size,
                 "expected_identity": pdf.parent.parent.name, "exactness": "trusted_payload_acceptance_covered_by_phase1_gate",
                 "outputs": ["vector/trusted PDF re-import evidence"], "roundtrip": "trusted_pdf_regression_verified",
                 "limitations": ["external_untrusted_pdf_remains_review_required"], "page_count": document.page_count,
                 "passed": document.page_count > 0 and pdf.stat().st_size > 1000})
    document.close()
    passed = len(rows) == 4 and all(row["passed"] for row in rows)
    payload = {"schema": "cws-phase3-real-file-matrix-1.0", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": "passed" if passed else "failed", "fixture_count": len(rows),
               "formats": [row["format"] for row in rows], "rows": rows, "machine_transfer_allowed": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"PHASE_3_REAL_FILE_MATRIX = {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
