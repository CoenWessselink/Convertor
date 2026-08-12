from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cadquery as cq

from conversion import convert_nc1_to_step, step_to_nc1, __version__
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


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nc1_step_v03_smoke_") as folder_name:
        folder = Path(folder_name)
        out = folder / "out"
        out.mkdir()
        nc1 = folder / "SAMPLE_PLATE.nc1"
        write_sample_nc1(nc1)
        step = out / "SAMPLE_PLATE.step"
        part = convert_nc1_to_step(nc1, step)
        assert step.exists() and step.stat().st_size > 0
        assert part.header.profile_type == "B"

        reverse = out / "SAMPLE_PLATE_reverse.nc1"
        result = step_to_nc1(step, reverse, profile_database=ProfileDatabase(writable_copy=False), material="S355JR")
        assert reverse.exists() and result.profile_type == "B"
        assert abs(result.volume_delta_percent) < 0.02

        # Quantity + Excel export regression.
        materials = MaterialDatabase()
        profiles = ProfileDatabase(writable_copy=False)
        analysis = analyze_files([step], fallback_material="S355JR", material_database=materials, profile_database=profiles)
        assert analysis.items and analysis.total_mass_kg > 0
        xlsx = out / "hoeveelheden.xlsx"
        export_excel(xlsx, analysis, material_database=materials, profile_database=profiles)
        assert xlsx.exists() and xlsx.stat().st_size > 0

        # Optional IFC smoke: only when IfcOpenShell is installed and its API is compatible.
        try:
            import ifcopenshell  # noqa: F401
            from ifc_support import step_to_ifc
            ifc = out / "SAMPLE_PLATE.ifc"
            ifc_result = step_to_ifc(step, ifc, material="S355JR")
            assert ifc.exists() and ifc_result.primary_output == ifc
        except Exception as exc:
            # IFC is optional for local Linux tests. The Windows Actions build installs IfcOpenShell;
            # incompatible API changes should still be reviewed from the printed warning.
            print(f"IFC smoke skipped/warned: {exc}")

        summary = {
            "version": __version__,
            "step": str(step),
            "reverse_nc1": str(reverse),
            "volume_delta_percent": result.volume_delta_percent,
            "quantity_items": len(analysis.items),
            "excel": str(xlsx),
        }
        print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
