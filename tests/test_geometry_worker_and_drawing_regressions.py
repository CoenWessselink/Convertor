from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import CWS_Convertor_App
from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
from cws_viewer.geometry import frozen_worker


class GeometryWorkerAndDrawingRegressionTests(unittest.TestCase):
    def test_geometry_worker_service_is_dispatched_before_gui(self) -> None:
        captured: dict[str, object] = {}

        def fake_worker(*, host: str, port: int, token: str, root: Path) -> int:
            captured.update(host=host, port=port, token=token, root=root)
            return 73

        with TemporaryDirectory() as directory, patch.object(frozen_worker, "run_geometry_worker_service", fake_worker):
            root = Path(directory)
            result = CWS_Convertor_App.main([
                "--geometry-worker-service", "--worker-host", "127.0.0.1",
                "--worker-port", "43117", "--worker-token", "acceptance-token",
                "--worker-root", str(root),
            ])
            self.assertEqual(result, 73)
            self.assertEqual(captured, {"host": "127.0.0.1", "port": 43117, "token": "acceptance-token", "root": root})

    def test_frozen_worker_command_accepts_dash_leading_auth_token(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            command = frozen_worker._worker_command(
                executable="CWS_Convertor_CLI.exe",
                host="127.0.0.1",
                port=43117,
                token="-dash-leading-token",
                root=root,
            )
            self.assertIn("--worker-token=-dash-leading-token", command)
            self.assertNotIn("-dash-leading-token", command)

            captured: dict[str, object] = {}

            def fake_worker(*, host: str, port: int, token: str, root: Path) -> int:
                captured.update(host=host, port=port, token=token, root=root)
                return 74

            with patch.object(frozen_worker, "run_geometry_worker_service", fake_worker):
                result = CWS_Convertor_App.main(command[1:])
            self.assertEqual(result, 74)
            self.assertEqual(captured["token"], "-dash-leading-token")

    def test_iso_projection_keeps_manufacturing_axis_horizontal(self) -> None:
        vertices = np.array([
            [0.0, -50.0, -50.0], [0.0, 50.0, 50.0],
            [6400.0, -50.0, -50.0], [6400.0, 50.0, 50.0],
        ], dtype=float)
        projected, _depth = EngineeringDrawingGenerator._project(vertices, "iso")
        start_center = projected[:2].mean(axis=0)
        end_center = projected[2:].mean(axis=0)
        self.assertLess(abs(float(end_center[1] - start_center[1])), 1.0e-9)
        self.assertGreater(float(end_center[0] - start_center[0]), 4000.0)


if __name__ == "__main__":
    unittest.main()
