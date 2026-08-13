from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import (
    Part,
    ProjectModel,
    ProjectSession,
    ProjectValidationError,
    SourceIdentity,
)
from cws_convertor.project.canonical_rebuild import (
    build_canonical_shape,
    canonical_shape_metrics,
)
import cli


def line(start: tuple[float, float], end: tuple[float, float]) -> dict:
    return {"kind": "line", "start": list(start), "end": list(end)}


def rectangle(width: float, height: float) -> list[dict]:
    return [
        line((0.0, 0.0), (width, 0.0)),
        line((width, 0.0), (width, height)),
        line((width, height), (0.0, height)),
        line((0.0, height), (0.0, 0.0)),
    ]


def top_side() -> list[dict]:
    return [
        {
            "side_id": "v",
            "label": "Bovenzijde",
            "face_ref": "face:top",
            "confirmed": True,
        }
    ]


def plate_source_metrics() -> dict:
    radius = 7.0
    thickness = 10.0
    return {
        "scope": "exact_part",
        "fidelity": "native_brep",
        "production_geometry_exact": True,
        "solid_count": 1,
        "volume_mm3": 200.0 * 100.0 * thickness - math.pi * radius * radius * thickness,
        "area_mm2": (
            2.0 * (200.0 * 100.0 + 200.0 * thickness + 100.0 * thickness)
            - 2.0 * math.pi * radius * radius
            + 2.0 * math.pi * radius * thickness
        ),
        "bbox_mm": [200.0, 100.0, 10.0],
        "valid": True,
    }


def make_part(part_id: str, *, metrics: dict | None = None) -> Part:
    descriptor = {"source_geometry_hash": "b" * 64, "solid_count": 1}
    if metrics is not None:
        descriptor["cad_metrics"] = metrics
    part = Part(
        internal_id=part_id,
        name=part_id,
        part_position=part_id.upper(),
        source_identity=SourceIdentity(
            source_format="STEP",
            source_sha256="a" * 64,
            source_entity_id="#42",
            part_position=part_id.upper(),
        ),
        profile="PL10",
        material="S355JR",
        quantity_total=1,
        confidence=1.0,
        profile_confidence=1.0,
        geometry_descriptor=descriptor,
        properties={"source_solid_count": 1},
    )
    part.recompute_hashes()
    return part


def plate_changes() -> dict:
    return {
        "part_form": "plate",
        "recognition": {"candidate": "PL10*100", "confidence": 1.0, "confirmed": True},
        "dimensions": {"length_mm": 200.0, "thickness_mm": 10.0},
        "reference_sides": top_side(),
        "contours": [
            {
                "contour_id": "outer",
                "role": "outer",
                "closed": True,
                "segments": rectangle(200.0, 100.0),
            }
        ],
        "features": [
            {
                "feature_id": "hole-1",
                "kind": "hole",
                "reference_side": "v",
                "parameters": {
                    "x_mm": 40.0,
                    "y_mm": 40.0,
                    "diameter_mm": 14.0,
                    "through": True,
                },
            }
        ],
    }


class PartWorkbenchRoundtripTests(unittest.TestCase):
    def test_failed_revalidation_invalidates_current_roundtrip_artifacts(self) -> None:
        session = ProjectSession.new("Failed roundtrip rerun", created_by="tester")
        part = make_part("plate", metrics=plate_source_metrics())
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("plate", user="reviewer")
        session.update_part_workbench(
            "plate", plate_changes(), user="reviewer", reason="Plaat bevestigd"
        )
        session.rebuild_part_canonical("plate", user="reviewer")
        with tempfile.TemporaryDirectory(prefix="cws_roundtrip_rerun_") as folder:
            first = session.validate_part_roundtrips("plate", folder, user="reviewer")
            self.assertEqual(first["status"], "passed")
            with patch(
                "cws_convertor.project.roundtrip._run_one",
                side_effect=RuntimeError("synthetic export failure"),
            ):
                failed = session.validate_part_roundtrips("plate", folder, user="reviewer")
        self.assertEqual(failed["status"], "failed")
        self.assertTrue(
            all(
                item["status"] == "invalidated"
                and item["invalidated_reason"] == "roundtrip_revalidation_failed"
                for item in part.workbench["artifacts"].values()
            )
        )
        with self.assertRaises(ProjectValidationError):
            session.review_part_workbench("plate", user="reviewer", release=True)

    def test_cli_rebuild_and_roundtrip_commands_use_persisted_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_roundtrip_cli_") as folder_name:
            folder = Path(folder_name)
            project_path = folder / "roundtrip-cli.cwscproj"
            output = folder / "artifacts"
            session = ProjectSession.new("Roundtrip CLI", created_by="tester")
            part = make_part("plate", metrics=plate_source_metrics())
            session.project.add_entity(part, user="tester")
            session.start_part_workbench("plate", user="reviewer")
            session.update_part_workbench(
                "plate", plate_changes(), user="reviewer", reason="Plaat bevestigd"
            )
            session.save(project_path, embed_sources=False, user="reviewer")
            session.close()

            for arguments in (
                (
                    "project-rebuild-canonical",
                    str(project_path),
                    "plate",
                    "--user",
                    "cli-test",
                    "--json",
                ),
                (
                    "project-validate-roundtrips",
                    str(project_path),
                    "plate",
                    "--output",
                    str(output),
                    "--user",
                    "cli-test",
                    "--json",
                ),
            ):
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(list(arguments))
                self.assertEqual(
                    exit_code,
                    cli.EXIT_OK,
                    msg=f"stdout={stdout.getvalue()}\nstderr={stderr.getvalue()}",
                )

            with ProjectSession.open(project_path, read_only=True) as reopened:
                report = reopened.project.parts["plate"].workbench["current_revision"][
                    "roundtrip_validation"
                ]
                self.assertEqual(report["status"], "passed")
                self.assertEqual(len(list(output.iterdir())), 4)

    def test_all_format_roundtrips_persist_release_and_invalidate(self) -> None:
        session = ProjectSession.new("Roundtrip matrix", created_by="tester")
        part = make_part("plate", metrics=plate_source_metrics())
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("plate", user="reviewer")
        session.update_part_workbench(
            "plate", plate_changes(), user="reviewer", reason="Plaat bevestigd"
        )
        rebuilt = session.rebuild_part_canonical("plate", user="reviewer")
        self.assertEqual(rebuilt.report["status"], "passed")

        with tempfile.TemporaryDirectory(prefix="cws_roundtrip_") as folder_name:
            folder = Path(folder_name)
            report = session.validate_part_roundtrips(
                "plate",
                folder,
                user="reviewer",
                formats=("NC1", "STEP", "IFC", "PDF"),
            )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(set(report["formats"]), {"nc1", "step", "ifc", "pdf"})
            for format_name, result in report["formats"].items():
                with self.subTest(format=format_name):
                    self.assertEqual(result["status"], "passed")
                    self.assertTrue(result["payload_geometry_exact"])
                    self.assertTrue(Path(result["artifact_path"]).is_file())
                    self.assertTrue(result["artifact_sha256"])
                    self.assertTrue(result["checks"])

            state = part.workbench
            stored = state["current_revision"]["roundtrip_validation"]
            self.assertEqual(stored["status"], "passed")
            self.assertEqual(stored["manufacturing_hash"], part.manufacturing_hash)
            self.assertEqual(stored["report_sha256"], report["report_sha256"])
            self.assertEqual(len(state["artifacts"]), 4)

            session.review_part_workbench("plate", user="reviewer")
            session.review_part_workbench("plate", user="reviewer", release=True)
            self.assertTrue(part.nc1_eligible)
            self.assertEqual(part.export_status, "reviewed_pending_project_gate")

            project_path = folder / "roundtrip.cwscproj"
            session.save(project_path, embed_sources=False, user="reviewer")
            with ProjectSession.open(project_path, read_only=True) as reopened:
                restored = reopened.project.parts["plate"]
                self.assertEqual(
                    restored.workbench["current_revision"]["roundtrip_validation"][
                        "report_sha256"
                    ],
                    report["report_sha256"],
                )

            changed = plate_changes()["features"] + [
                {
                    "feature_id": "hole-2",
                    "kind": "hole",
                    "reference_side": "v",
                    "parameters": {
                        "x_mm": 160.0,
                        "y_mm": 40.0,
                        "diameter_mm": 14.0,
                        "through": True,
                    },
                }
            ]
            session.update_part_workbench(
                "plate", {"features": changed}, user="reviewer", reason="Gat toegevoegd"
            )
            current_part = session.project.parts["plate"]
            current = current_part.workbench["current_revision"]["roundtrip_validation"]
            self.assertEqual(current["status"], "invalidated")
            self.assertTrue(
                all(
                    item["status"] == "invalidated"
                    for item in current_part.workbench["artifacts"].values()
                )
            )
            with self.assertRaises(ProjectValidationError):
                session.review_part_workbench("plate", user="reviewer", release=True)

    def test_roundtrip_report_tampering_is_rejected(self) -> None:
        session = ProjectSession.new("Roundtrip tamper", created_by="tester")
        part = make_part("plate", metrics=plate_source_metrics())
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("plate", user="reviewer")
        session.update_part_workbench(
            "plate", plate_changes(), user="reviewer", reason="Plaat bevestigd"
        )
        session.rebuild_part_canonical("plate", user="reviewer")
        with tempfile.TemporaryDirectory(prefix="cws_roundtrip_tamper_") as folder:
            session.validate_part_roundtrips("plate", folder, user="reviewer")
        raw = session.project.to_dict()
        raw["parts"]["plate"]["workbench"]["current_revision"][
            "roundtrip_validation"
        ]["formats"]["step"]["status"] = "failed"
        with self.assertRaises(ProjectValidationError):
            ProjectModel.from_dict(raw)

    def test_arc_custom_section_and_worked_profile_rebuild(self) -> None:
        session = ProjectSession.new("Extended canonical forms", created_by="tester")

        arc = make_part("arc")
        session.project.add_entity(arc, user="tester")
        session.start_part_workbench("arc", user="reviewer")
        arc_changes = plate_changes()
        arc_changes["features"] = []
        arc_changes["contours"] = [
            {
                "contour_id": "arc-outer",
                "role": "outer",
                "closed": True,
                "segments": [
                    line((0.0, 0.0), (100.0, 0.0)),
                    line((100.0, 0.0), (100.0, 50.0)),
                    {
                        "kind": "arc",
                        "start": [100.0, 50.0],
                        "end": [0.0, 50.0],
                        "center": [50.0, 50.0],
                        "radius_mm": 50.0,
                        "clockwise": False,
                    },
                    line((0.0, 50.0), (0.0, 0.0)),
                ],
            }
        ]
        session.update_part_workbench(
            "arc", arc_changes, user="reviewer", reason="Halfronde plaat bevestigd"
        )
        arc_report = session.rebuild_part_canonical("arc", user="reviewer").report
        self.assertEqual(arc_report["build_status"], "built")
        self.assertAlmostEqual(
            arc_report["canonical_metrics"]["volume_mm3"],
            (100.0 * 50.0 + math.pi * 50.0 * 50.0 / 2.0) * 10.0,
            places=4,
        )
        self.assertEqual(arc_report["canonical_metrics"]["bbox_mm"], [100.0, 100.0, 10.0])

        custom = make_part("custom")
        session.project.add_entity(custom, user="tester")
        session.start_part_workbench("custom", user="reviewer")
        session.update_part_workbench(
            "custom",
            {
                "part_form": "custom",
                "recognition": {"candidate": "CUSTOM-50X30", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 1000.0},
                "reference_sides": top_side(),
                "contours": [
                    {
                        "contour_id": "section-outer",
                        "role": "outer",
                        "closed": True,
                        "segments": rectangle(50.0, 30.0),
                    }
                ],
                "features": [],
            },
            user="reviewer",
            reason="Custom doorsnede bevestigd",
        )
        custom_report = session.rebuild_part_canonical("custom", user="reviewer").report
        self.assertEqual(custom_report["build_status"], "built")
        self.assertAlmostEqual(custom_report["canonical_metrics"]["volume_mm3"], 1_500_000.0)

        profile = make_part("profile")
        session.project.add_entity(profile, user="tester")
        session.start_part_workbench("profile", user="reviewer")
        session.update_part_workbench(
            "profile",
            {
                "part_form": "profile",
                "recognition": {"candidate": "HEA 240", "confidence": 1.0, "confirmed": True},
                "dimensions": {"length_mm": 1000.0},
                "reference_sides": top_side(),
                "contours": [],
                "features": [
                    {
                        "feature_id": "web-hole",
                        "kind": "hole",
                        "reference_side": "v",
                        "parameters": {
                            "x_mm": 500.0,
                            "y_mm": 120.0,
                            "diameter_mm": 18.0,
                            "through": True,
                            "dstv_face": "v",
                        },
                    }
                ],
            },
            user="reviewer",
            reason="HEA met lijfgat bevestigd",
        )
        profile_report = session.rebuild_part_canonical("profile", user="reviewer").report
        self.assertEqual(profile_report["build_status"], "built")
        self.assertEqual(profile_report["canonical_metrics"]["solid_count"], 1)

        profile_shape, _warnings, _payload = build_canonical_shape(profile)
        profile.geometry_descriptor["cad_metrics"] = {
            **canonical_shape_metrics(profile_shape),
            "scope": "exact_part",
            "production_geometry_exact": True,
        }
        profile.recompute_hashes()
        profile_report = session.rebuild_part_canonical("profile", user="reviewer").report
        self.assertEqual(profile_report["status"], "passed")
        with tempfile.TemporaryDirectory(prefix="cws_profile_roundtrip_") as folder:
            roundtrip = session.validate_part_roundtrips(
                "profile", folder, user="reviewer"
            )
        self.assertEqual(roundtrip["status"], "passed", msg=str(roundtrip))

    def test_ambiguous_arc_and_self_intersection_are_blocking(self) -> None:
        session = ProjectSession.new("Contour validation", created_by="tester")
        part = make_part("invalid")
        session.project.add_entity(part, user="tester")
        session.start_part_workbench("invalid", user="reviewer")
        changes = plate_changes()
        changes["features"] = []
        changes["contours"] = [
            {
                "contour_id": "bow-tie",
                "role": "outer",
                "closed": True,
                "segments": [
                    line((0.0, 0.0), (100.0, 100.0)),
                    line((100.0, 100.0), (0.0, 100.0)),
                    line((0.0, 100.0), (100.0, 0.0)),
                    line((100.0, 0.0), (0.0, 0.0)),
                ],
            }
        ]
        state = session.update_part_workbench(
            "invalid", changes, user="reviewer", reason="Zelfsnijdende contour"
        )
        codes = {
            item["code"] for item in state["current_revision"]["validation_issues"]
        }
        self.assertIn("CWS-WB-SELF-INTERSECTION", codes)

        ambiguous = plate_changes()
        ambiguous["features"] = []
        ambiguous["contours"] = [
            {
                "contour_id": "ambiguous-arc",
                "role": "outer",
                "closed": True,
                "segments": [
                    line((0.0, 0.0), (100.0, 0.0)),
                    line((100.0, 0.0), (100.0, 50.0)),
                    {
                        "kind": "arc",
                        "start": [100.0, 50.0],
                        "end": [0.0, 50.0],
                        "center": [50.0, 50.0],
                        "radius_mm": 50.0,
                    },
                    line((0.0, 50.0), (0.0, 0.0)),
                ],
            }
        ]
        state = session.update_part_workbench(
            "invalid", ambiguous, user="reviewer", reason="Boogrichting ontbreekt"
        )
        codes = {
            item["code"] for item in state["current_revision"]["validation_issues"]
        }
        self.assertIn("CWS-WB-ARC-DIRECTION", codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
