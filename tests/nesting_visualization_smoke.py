from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6 import QtGui, QtWidgets

from cws_convertor.ui_qt.nesting_visualization import (
    PlateNestingVisualization,
    ProfileNestingVisualization,
)


def main() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    profile = ProfileNestingVisualization()
    profile.resize(1100, 520)
    profile.set_record(
        {
            "input_snapshot": {
                "units": {"units_per_mm": 1000},
                "demand_lines": [
                    {
                        "demand_line_id": "line-1",
                        "profile_name": "HEA220",
                    }
                ],
            },
            "plan": {
                "bars": [
                    {
                        "bar_id": "B01",
                        "stock_length_units": 12000000,
                        "head_trim_units": 10000,
                        "reusable_remnant_units": 3470000,
                        "waste_units": 0,
                        "placements": [
                            {
                                "instance_id": "IFC-PROFILE-1",
                                "part_position": "Pr1",
                                "demand_line_id": "line-1",
                                "start_units": 10000,
                                "length_units": 6532000,
                                "start_angle_deg": 0.0,
                                "end_angle_deg": 45.0,
                            },
                            {
                                "instance_id": "IFC-PROFILE-2",
                                "part_position": "Pr2",
                                "demand_line_id": "line-1",
                                "start_units": 6545000,
                                "length_units": 1985000,
                                "start_angle_deg": -45.0,
                                "end_angle_deg": 0.0,
                                "common_cut_with_previous": True,
                            },
                        ],
                    }
                ]
            },
        }
    )
    profile.show()
    app.processEvents()
    ProfileNestingVisualization.paintEvent(profile, QtGui.QPaintEvent(profile.rect()))
    profile_image = profile.grab().toImage()
    assert not profile_image.isNull()

    plate = PlateNestingVisualization()
    plate.resize(900, 540)
    plate.set_plan(
        {
            "layouts": [
                {
                    "width_mm": 3000.0,
                    "height_mm": 1500.0,
                    "placements": [
                        {
                            "part_id": "P36",
                            "x_mm": 25.0,
                            "y_mm": 25.0,
                            "width_mm": 382.14,
                            "height_mm": 230.0,
                        },
                        {
                            "part_id": "P37",
                            "x_mm": 425.0,
                            "y_mm": 25.0,
                            "width_mm": 120.0,
                            "height_mm": 80.0,
                        },
                    ],
                }
            ]
        }
    )
    plate.show()
    app.processEvents()
    PlateNestingVisualization.paintEvent(plate, QtGui.QPaintEvent(plate.rect()))
    plate_image = plate.grab().toImage()
    assert not plate_image.isNull()

    profile.close()
    plate.close()
    app.processEvents()
    print("nesting_visualization_smoke: PASS")


if __name__ == "__main__":
    main()
