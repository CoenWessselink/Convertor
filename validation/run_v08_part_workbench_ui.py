from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import ImageGrab

from cws_convertor.project import Part, ProjectSession, SourceIdentity
from project_tab import CWSProjectTab


def build_demo_session() -> ProjectSession:
    session = ProjectSession.new("SteelConverter Workbench", created_by="validation")
    samples = (
        ("part-plate", "P101", "Voetplaat", "PL15", "S355", (420.0, 260.0, 15.0)),
        ("part-profile", "B201", "Hoofdligger", "HEA240", "S355", (6400.0, 240.0, 230.0)),
        ("part-review", "P102", "Kopplaat", "PL12", "S235", (300.0, 180.0, 12.0)),
    )
    for index, (part_id, position, name, profile, material, bbox) in enumerate(samples, start=1):
        cad_metrics = {"bbox_mm": list(bbox), "valid": True}
        if part_id == "part-plate":
            radius = 11.0
            hole_count = 4
            length, width, thickness = bbox
            cad_metrics.update(
                {
                    "scope": "part",
                    "solid_count": 1,
                    "volume_mm3": length * width * thickness
                    - hole_count * math.pi * radius * radius * thickness,
                    "area_mm2": 2.0 * (length * width + length * thickness + width * thickness)
                    - 2.0 * hole_count * math.pi * radius * radius
                    + hole_count * 2.0 * math.pi * radius * thickness,
                }
            )
        part = Part(
            internal_id=part_id,
            name=name,
            part_position=position,
            source_identity=SourceIdentity(
                source_format="STEP",
                source_sha256=f"{index}" * 64,
                source_entity_id=f"#{100 + index}",
                part_position=position,
            ),
            profile=profile,
            material=material,
            length_mm=max(bbox),
            mass_each_kg=48.75 if index == 1 else 0.0,
            surface_area_each_m2=0.24 if index == 1 else 0.0,
            confidence=0.94,
            profile_confidence=0.94,
            geometry_descriptor={
                "source_geometry_hash": str(index + 3) * 64,
                "cad_metrics": cad_metrics,
                "solid_count": 1,
            },
            properties={"source_solid_count": 1},
        )
        part.recompute_hashes()
        session.project.add_entity(part, user="validation")

    session.start_part_workbench("part-plate", user="validation")
    session.update_part_workbench(
        "part-plate",
        {
            "part_form": "plate",
            "recognition": {"candidate": "PL15", "confidence": 0.94, "confirmed": True},
            "dimensions": {"length_mm": 420.0, "thickness_mm": 15.0, "diameter_mm": 0.0},
            "reference_sides": [
                {"side_id": "top", "label": "Bovenzijde", "face_ref": "face:top", "confirmed": True}
            ],
            "contours": [
                {
                    "contour_id": "outer-1",
                    "role": "outer",
                    "closed": True,
                    "segments": [
                        {"kind": "line", "start": [0.0, 0.0], "end": [420.0, 0.0]},
                        {"kind": "line", "start": [420.0, 0.0], "end": [420.0, 260.0]},
                        {"kind": "line", "start": [420.0, 260.0], "end": [0.0, 260.0]},
                        {"kind": "line", "start": [0.0, 260.0], "end": [0.0, 0.0]},
                    ],
                }
            ],
            "features": [
                {
                    "feature_id": f"hole-{number}",
                    "kind": "hole",
                    "reference_side": "top",
                    "parameters": {"x_mm": x, "y_mm": y, "diameter_mm": 22.0, "through": True},
                }
                for number, (x, y) in enumerate(
                    ((45.0, 45.0), (375.0, 45.0), (375.0, 215.0), (45.0, 215.0)), start=1
                )
            ],
        },
        user="validation",
        reason="Visuele Workbench-validatie",
    )
    session.rebuild_part_canonical("part-plate", user="validation")
    return session


def configure_style(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure(".", font=("Segoe UI", 9))
    style.configure("TNotebook.Tab", padding=(12, 7), font=("Segoe UI", 9, "bold"))
    style.configure("Treeview", rowheight=25, background="#ffffff", fieldbackground="#ffffff")
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(6, 6))
    style.configure(
        "CWS.Primary.TButton",
        background="#2563a6",
        foreground="#ffffff",
        padding=(12, 7),
        font=("Segoe UI", 9, "bold"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Open de geintegreerde v0.8 Part Workbench-validatiefixture.")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--seconds", type=float, default=4.0)
    args = parser.parse_args()

    root = tk.Tk()
    root.title("CWS Convertor - Part Workbench validatie")
    root.geometry("1500x900+40+30")
    root.minsize(1220, 760)
    root.attributes("-topmost", True)
    configure_style(root)
    session = build_demo_session()
    tab = CWSProjectTab(root)
    tab.pack(fill="both", expand=True)
    tab._replace_session(session)
    tab.refresh()
    tab.workspace.select(2)
    tab.part_workbench.select_part("part-plate", notify=False)
    tab.part_workbench.editor_tabs.select(2)

    def capture() -> None:
        if args.screenshot is None:
            return
        root.update_idletasks()
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        root.lift()
        root.focus_force()
        ImageGrab.grab(window=root.winfo_id(), scale_down=True).save(args.screenshot)

    root.after(900, capture)
    root.after(max(1500, int(args.seconds * 1000)), root.destroy)
    try:
        root.mainloop()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
