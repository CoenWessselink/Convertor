from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession
from cws_convertor.ui.exact_part_viewer import ExactPartViewerPanel
from cws_viewer.exact.model import SubshapeKind


def _rectangle(width: float, height: float) -> list[dict]:
    points = ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height))
    return [
        {"kind": "line", "start": list(point), "end": list(points[(index + 1) % 4])}
        for index, point in enumerate(points)
    ]


class ViewerV6TkExactIntegrationTests(unittest.TestCase):
    def test_integrated_part_workbench_opens_owner_source_and_canonical_brep(self) -> None:
        import cadquery as cq

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk native window ontbreekt: {exc}")
        root.geometry("980x680+10000+10000")
        with tempfile.TemporaryDirectory(prefix="cws_exact_tk_") as folder_name:
            source_path = Path(folder_name) / "plate.step"
            cq.exporters.export(cq.Solid.makeBox(100.0, 50.0, 10.0), str(source_path))
            session = ProjectSession.new("Integrated exact UI", created_by="test")
            panel = None
            try:
                registration = session.register_sources([source_path], include_step_geometry=True)[0]
                session.semantic_import_source(registration.source.source_id)
                part = next(iter(session.project.parts.values()))
                session.inspect_part_source_geometry(part.internal_id, user="test")
                session.start_part_workbench(part.internal_id, user="test")
                session.update_part_workbench(
                    part.internal_id,
                    {
                        "part_form": "plate",
                        "recognition": {"candidate": "PL10", "confidence": 1.0, "confirmed": True},
                        "dimensions": {"length_mm": 100.0, "thickness_mm": 10.0},
                        "reference_sides": [
                            {"side_id": "top", "label": "Bovenzijde", "face_ref": "owner:top", "confirmed": True}
                        ],
                        "contours": [
                            {"contour_id": "outer", "role": "outer", "closed": True, "segments": _rectangle(100.0, 50.0)}
                        ],
                        "features": [],
                    },
                    user="test",
                    reason="Exact UI fixture",
                )
                session.rebuild_part_canonical(part.internal_id, user="test")
                selections = []
                panel = ExactPartViewerPanel(
                    root,
                    session_provider=lambda: session,
                    selection_callback=selections.append,
                )
                panel.pack(fill="both", expand=True)
                root.update()
                panel.load_part(part.internal_id)
                deadline = time.monotonic() + 15.0
                while time.monotonic() < deadline and (
                    panel.integrated is None or panel._backend is None
                ):
                    root.update()
                    time.sleep(0.02)
                self.assertIsNotNone(panel.integrated)
                self.assertIsNotNone(panel._backend)
                self.assertGreater(len(panel.subshape_grid.get_children()), 0)
                face = next(
                    item
                    for item in panel.integrated.source.snapshot.subshapes
                    if item.kind == SubshapeKind.FACE
                )
                panel._select_subshape(face.stable_id, from_grid=False)
                self.assertEqual(face.stable_id, selections[-1]["stable_id"])
                self.assertEqual("exact_brep", selections[-1]["evidence"])
                self.assertFalse(panel.integrated.owner_gates()["production_release_allowed"])
            finally:
                if panel is not None:
                    panel.destroy()
                session.close()
                root.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
