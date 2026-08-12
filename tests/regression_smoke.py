from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq

from canonical_model import extract_part_from_ifc, strip_nc1_payload_bytes, strip_step_payload_bytes
from conversion import convert_nc1_to_step, step_to_nc1, __version__
from ifc_support import ifc_to_dstv, ifc_to_step, load_ifc_geometry, step_to_ifc
from material_database import MaterialDatabase
from profile_database import ProfileDatabase
from quantities import analyze_files, export_excel


def write_sample_nc1(path: Path) -> None:
    path.write_text(
        """ST
** SAMPLE_PLATE.nc1
  TEST
  SAMPLE_PLATE
  1
  SAMPLE_PLATE
  S235JR
  1
  STRIP10*220
  B
     240.00,240.00
     220.00
      10.00
      10.00
      10.00
       0.00
     80.000
      2.174
      0.000
      0.000
      0.000
      0.000




AK
  v       0.00u      0.00       0.00       0.00       0.00       0.00       0.00
        240.00       0.00       0.00       0.00       0.00       0.00       0.00
        240.00     220.00       0.00       0.00       0.00       0.00       0.00
          0.00     220.00       0.00       0.00       0.00       0.00       0.00
          0.00       0.00       0.00       0.00       0.00       0.00       0.00
BO
  v     120.00s    110.00      22.00
EN
""",
        encoding="ascii",
        newline="\r\n",
    )


def _shape_metrics(path: Path) -> tuple[float, float, tuple[float, float, float]]:
    shape = cq.importers.importStep(str(path)).val()
    box = shape.BoundingBox()
    return (
        float(shape.Volume()),
        float(shape.Area()),
        tuple(float(value) for value in (box.xlen, box.ylen, box.zlen)),
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nc1_step_v04_smoke_") as folder_name:
        folder = Path(folder_name)
        out = folder / "out"
        out.mkdir()
        nc1 = folder / "SAMPLE_PLATE.nc1"
        write_sample_nc1(nc1)
        original_nc1 = nc1.read_bytes()

        step = out / "SAMPLE_PLATE.step"
        part = convert_nc1_to_step(nc1, step)
        assert step.exists() and step.stat().st_size > 0
        assert part.header.profile_type == "B"

        reverse = out / "SAMPLE_PLATE_reverse.nc1"
        result = step_to_nc1(
            step,
            reverse,
            profile_database=ProfileDatabase(writable_copy=False),
            material="S355JR",
        )
        assert reverse.exists() and result.profile_type == "B"
        assert abs(result.volume_delta_percent) < 0.02
        assert strip_nc1_payload_bytes(reverse.read_bytes()) == original_nc1

        # Quantity + Excel export regression.
        materials = MaterialDatabase()
        profiles = ProfileDatabase(writable_copy=False)
        analysis = analyze_files(
            [step],
            fallback_material="S355JR",
            material_database=materials,
            profile_database=profiles,
        )
        assert analysis.items and analysis.total_mass_kg > 0
        xlsx = out / "hoeveelheden.xlsx"
        export_excel(xlsx, analysis, material_database=materials, profile_database=profiles)
        assert xlsx.exists() and xlsx.stat().st_size > 0

        # IFC is a hard smoke in v0.4. Converter-native IFC works without
        # IfcOpenShell and must contain both visible geometry and verified Pset.
        ifc = out / "SAMPLE_PLATE.ifc"
        ifc_result = step_to_ifc(step, ifc, material="S355JR")
        assert ifc.exists() and ifc_result.primary_output == ifc
        canonical = extract_part_from_ifc(ifc, strict=True)
        assert canonical is not None and canonical.attachment_bytes("step") is not None
        ifc_model = load_ifc_geometry(ifc)
        assert ifc_model.items and ifc_model.items[0].volume_mm3 > 0

        restored_step = out / "SAMPLE_PLATE_from_ifc.step"
        ifc_to_step(ifc, restored_step)
        assert strip_step_payload_bytes(restored_step.read_bytes()) == strip_step_payload_bytes(
            step.read_bytes()
        )
        before = _shape_metrics(step)
        after = _shape_metrics(restored_step)
        assert all(abs(first - second) <= 1e-7 * max(abs(first), 1.0) for first, second in zip(before[:2], after[:2]))
        assert max(abs(first - second) for first, second in zip(before[2], after[2])) <= 1e-7

        dstv_dir = out / "dstv_from_ifc"
        dstv_result = ifc_to_dstv(ifc, dstv_dir, strict_validation=True)
        restored_nc1 = [path for path in dstv_result.outputs if path.suffix.lower() in {".nc", ".nc1"}]
        assert restored_nc1 and not dstv_result.failures
        assert strip_nc1_payload_bytes(restored_nc1[0].read_bytes()) == original_nc1

        summary = {
            "version": __version__,
            "step": str(step),
            "reverse_nc1": str(reverse),
            "volume_delta_percent": result.volume_delta_percent,
            "quantity_items": len(analysis.items),
            "excel": str(xlsx),
            "ifc": str(ifc),
            "ifc_items": len(ifc_model.items),
            "ifc_payload_verified": True,
            "ifc_to_dstv_outputs": [str(path) for path in dstv_result.outputs],
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
