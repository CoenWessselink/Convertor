"""Pure parser, dispatch, catalog and source-contract checks (no CAD proof)."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field, replace
import hashlib
import inspect
import io
import math
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli
from cws_convertor.conversion_service import (
    ConversionService, ConversionSource, ConversionPlanner,
    conversion_material_density, resolve_conversion_material,
)
from profile_database import ProfileDefinition


def _load_native_policy_boundaries(**injected):
    """Load actual boundary functions without importing the unavailable CAD runtime.

    Serializer and parser calls remain mocked; filesystem transactions and
    material density resolution execute normally. This is not CAD validation.
    """
    names = {"step_to_nc1", "profile_from_nc1", "StepToNC1Result"}
    tree = ast.parse((ROOT / "conversion.py").read_text(encoding="utf-8"))
    definitions = [node for node in tree.body if getattr(node, "name", "") in names]
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *definitions],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    namespace = dict(
        Path=Path, os=os, math=math, tempfile=tempfile, dataclass=dataclass,
        field=field, replace=replace, ProfileDefinition=ProfileDefinition,
        conversion_material_density=conversion_material_density,
    )
    namespace.update(injected)
    exec(compile(module, str(ROOT / "conversion.py"), "exec"), namespace)
    return namespace


def _native_result(namespace, source, output):
    return namespace["StepToNC1Result"](
        source=source, output=output, kind="fixture", part_number="part-1",
        profile_designation="fixture", profile_type="fixture", confidence=1,
        matched_by="mocked-serializer-boundary", source_volume=0,
        reconstructed_volume=0, volume_delta_percent=0, source_area=0,
        reconstructed_area=0, area_delta_percent=0,
    )


def _nc1_header(*, weight=2.7, material="1050A-H14"):
    return SimpleNamespace(
        profile="RHS100X50X5", profile_type="M", dim1=100, dim2=50,
        dim3=5, dim4=5, radius=0, weight=weight, material=material,
    )


class ConversionMaterialDefaultsTests(unittest.TestCase):
    def test_cli_material_is_empty_unless_explicitly_supplied(self):
        commands = ("step-to-nc1", "ifc-to-dstv", "dstv-to-ifc", "step-to-ifc",
            "step-to-pdf", "ifc-to-pdf", "pdf-to-nc1", "pdf-to-step", "pdf-to-ifc", "excel", "quantities")
        parser = cli.build_parser()
        for command in commands:
            with self.subTest(command=command):
                args = [command, "input.step"] + ([] if command == "quantities" else ["-o", "output"])
                self.assertEqual(parser.parse_args(args).material, "")
                self.assertEqual(parser.parse_args(args + ["--material", "S355JR"]).material, "S355JR")

    def test_cli_dispatch_does_not_invent_a_material(self):
        # This replaces only the physical serializer to test CLI argument flow;
        # no successful native export or geometry result is being asserted.
        captured = []
        def serializer(source, target, **kwargs):
            captured.append(kwargs["material"])
            raise ValueError("MATERIAL_REVIEW_REQUIRED")
        with tempfile.TemporaryDirectory(prefix="cws-cli-material-") as folder:
            source = Path(folder) / "part.step"
            source.write_text("contract fixture", encoding="utf-8")
            with patch.dict(sys.modules, {"conversion": SimpleNamespace(step_to_nc1=serializer)}), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = cli.main(["step-to-nc1", str(source), "-o", str(Path(folder) / "output")])
        self.assertEqual(captured, [""])
        self.assertEqual(result, cli.EXIT_FAILED)

    def test_service_dispatch_keeps_empty_material_and_reports_serializer_block(self):
        with tempfile.TemporaryDirectory(prefix="cws-service-material-") as folder:
            source = Path(folder) / "part.step"
            source.write_text("contract fixture", encoding="utf-8")
            record = ConversionSource(str(source), "STEP", hashlib.sha256(source.read_bytes()).hexdigest(),
                exact_source=True, trusted_payload=True, solid_count=1)
            plan = ConversionPlanner().plan_source(record, "step-ifc")
            service = ConversionService()
            with patch.object(service, "_serialize_file", side_effect=ValueError("MATERIAL_REVIEW_REQUIRED")) as serializer:
                result = service.convert_file(source, Path(folder) / "output", "step-ifc", plan=plan)
            self.assertEqual(serializer.call_args.kwargs["material"], "")
            self.assertNotEqual(result.status, "passed")

    def test_optional_unknown_material_never_becomes_steel(self):
        self.assertEqual(resolve_conversion_material(), "")
        self.assertEqual(resolve_conversion_material(source_material="CUSTOM-MAT-X"), "CUSTOM-MAT-X")

    def test_production_requires_known_material(self):
        for value in ("", "UNKNOWN-MATERIAL"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
                resolve_conversion_material(value, required=True)

    def test_source_metadata_wins_over_explicit_fallback(self):
        self.assertEqual(resolve_conversion_material("S355JR", source_material="S235JR", required=True), "S235JR")
        self.assertEqual(resolve_conversion_material("S355 JR", required=True), "S355JR")
        with self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
            resolve_conversion_material("S355JR", source_material="UNKNOWN-MATERIAL", required=True)

    def test_density_uses_catalog_material_and_correct_units(self):
        self.assertEqual(conversion_material_density("S355JR"), 7850.0)
        self.assertEqual(conversion_material_density("1050A-H14"), 2700.0)
        self.assertAlmostEqual(10.0 * conversion_material_density("1050A-H14") / 1000.0, 27.0)
        self.assertAlmostEqual(1000.0 * conversion_material_density("1050A-H14") / 1_000_000.0, 2.7)

    def test_missing_authoritative_density_blocks(self):
        with self.assertRaisesRegex(ValueError, "MATERIAL_DENSITY_REVIEW_REQUIRED"):
            conversion_material_density("C24")

    def test_service_signatures_do_not_supply_material(self):
        for method in ("convert_file", "convert_batch", "convert_project_selection"):
            self.assertEqual(inspect.signature(getattr(ConversionService, method)).parameters["material"].default, "")

    def test_native_and_ui_sources_contain_no_silent_material_defaults(self):
        # AST source contract only, not a substitute for native execution.
        for relative in ("conversion.py", "converter.py", "ifc_support.py", "app.py", "cws_viewer/exact/roundtrip.py"):
            module = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(module):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    arguments = node.args.posonlyargs + node.args.args
                    pairs = list(zip(arguments[-len(node.args.defaults):], node.args.defaults)) if node.args.defaults else []
                    pairs += list(zip(node.args.kwonlyargs, node.args.kw_defaults))
                    for argument, default in pairs:
                        if argument.arg == "material" and isinstance(default, ast.Constant):
                            self.assertNotIn(default.value, ("S235JR", "S355JR"), f"{relative}:{node.name}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "StringVar":
                    for keyword in node.keywords:
                        if keyword.arg == "value" and isinstance(keyword.value, ast.Constant):
                            self.assertNotIn(keyword.value.value, ("S235JR", "S355JR"), relative)


class ConversionTransactionBoundaryTests(unittest.TestCase):
    def test_failed_serializer_preserves_existing_output_and_cleans_stage(self):
        captured = []
        def reject(source, staged, **kwargs):
            staged = Path(staged)
            captured.append(staged)
            staged.write_bytes(b"REJECTED PARTIAL NC1")
            raise ValueError("MATERIAL_REVIEW_REQUIRED")
        namespace = _load_native_policy_boundaries(_step_to_nc1_staged=reject)
        with tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
            source = Path(folder) / "source.step"
            target = Path(folder) / "accepted.nc1"
            source.write_bytes(b"SOURCE STEP")
            target.write_bytes(b"ACCEPTED NC1")
            with self.assertRaisesRegex(ValueError, "MATERIAL_REVIEW_REQUIRED"):
                namespace["step_to_nc1"](source, target)
            self.assertEqual(target.read_bytes(), b"ACCEPTED NC1")
            self.assertEqual(source.read_bytes(), b"SOURCE STEP")
            self.assertEqual(captured[0].name, target.name)
            self.assertEqual(captured[0].parent.parent, target.parent)
            self.assertFalse(captured[0].exists())
            self.assertFalse(captured[0].parent.exists())

    def test_success_commits_expected_basename_and_returns_final_output(self):
        captured = []
        namespace = _load_native_policy_boundaries()
        def serialize(source, staged, **kwargs):
            staged = Path(staged)
            captured.append((staged, kwargs))
            staged.write_text(f"NC1 references {staged.name}", encoding="utf-8")
            return _native_result(namespace, source, staged)
        namespace["_step_to_nc1_staged"] = serialize
        with tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
            source = Path(folder) / "source.step"
            target = Path(folder) / "nested" / "part-1.nc1"
            source.write_bytes(b"SOURCE STEP")
            result = namespace["step_to_nc1"](
                source, target, material="S235JR", preferred_profile="IPE200",
                tolerance_mm=0.15, strict_validation=True, embed_converter_payload=True,
            )
            self.assertEqual(result.output, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "NC1 references part-1.nc1")
            self.assertEqual(captured[0][0].name, target.name)
            self.assertEqual(captured[0][1]["material"], "S235JR")
            self.assertEqual(captured[0][1]["preferred_profile"], "IPE200")
            self.assertEqual(captured[0][1]["tolerance_mm"], 0.15)
            self.assertTrue(captured[0][1]["strict_validation"])
            self.assertTrue(captured[0][1]["embed_converter_payload"])
            self.assertFalse(captured[0][0].parent.exists())

    def test_failed_new_output_does_not_leave_a_production_file(self):
        def reject(source, staged, **kwargs):
            Path(staged).write_bytes(b"INVALID NC1")
            raise ValueError("invalid geometry")
        namespace = _load_native_policy_boundaries(_step_to_nc1_staged=reject)
        with tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
            source = Path(folder) / "source.step"
            target = Path(folder) / "new.nc1"
            source.write_bytes(b"SOURCE STEP")
            with self.assertRaises(ValueError):
                namespace["step_to_nc1"](source, target)
            self.assertFalse(target.exists())

    def test_identical_source_symlink_and_hardlink_are_blocked_before_serializer(self):
        for mode in ("same_path", "symlink", "hardlink"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
                source = Path(folder) / "source.step"
                source.write_bytes(b"SOURCE STEP")
                target = source if mode == "same_path" else Path(folder) / "alias.nc1"
                if mode == "symlink":
                    try:
                        target.symlink_to(source)
                    except (OSError, NotImplementedError) as exc:
                        if os.name == "nt":
                            continue  # Windows may deny symlink creation without its developer mode.
                        raise exc
                elif mode == "hardlink":
                    os.link(source, target)
                serializer = Mock(side_effect=AssertionError("Source alias must block first"))
                namespace = _load_native_policy_boundaries(_step_to_nc1_staged=serializer)
                with self.assertRaises(ValueError):
                    namespace["step_to_nc1"](source, target)
                serializer.assert_not_called()
                self.assertEqual(source.read_bytes(), b"SOURCE STEP")

    def test_commit_failure_preserves_preexisting_output(self):
        namespace = _load_native_policy_boundaries()
        def serialize(source, staged, **kwargs):
            Path(staged).write_bytes(b"NEW NC1")
            return _native_result(namespace, source, staged)
        namespace["_step_to_nc1_staged"] = serialize
        with tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
            source = Path(folder) / "source.step"
            target = Path(folder) / "accepted.nc1"
            source.write_bytes(b"SOURCE STEP")
            target.write_bytes(b"ACCEPTED NC1")
            with patch("os.replace", side_effect=OSError("storage unavailable")):
                with self.assertRaisesRegex(OSError, "storage unavailable"):
                    namespace["step_to_nc1"](source, target)
            self.assertEqual(target.read_bytes(), b"ACCEPTED NC1")

    def test_missing_staged_artifact_preserves_preexisting_output(self):
        namespace = _load_native_policy_boundaries()
        namespace["_step_to_nc1_staged"] = lambda source, staged, **kwargs: _native_result(namespace, source, staged)
        with tempfile.TemporaryDirectory(prefix="cws-transaction-boundary-") as folder:
            source = Path(folder) / "source.step"
            target = Path(folder) / "accepted.nc1"
            source.write_bytes(b"SOURCE STEP")
            target.write_bytes(b"ACCEPTED NC1")
            with self.assertRaisesRegex(RuntimeError, "NC1_STAGING_ARTIFACT_MISSING"):
                namespace["step_to_nc1"](source, target)
            self.assertEqual(target.read_bytes(), b"ACCEPTED NC1")


class ProfileDensityBoundaryTests(unittest.TestCase):
    def _namespace(self, header, **kwargs):
        return _load_native_policy_boundaries(
            core=SimpleNamespace(parse_nc1=lambda path: SimpleNamespace(header=header)), **kwargs,
        )

    def test_aluminium_kg_per_metre_uses_its_density_for_section_area(self):
        namespace = self._namespace(_nc1_header())
        profile = namespace["profile_from_nc1"]("aluminium.nc1")
        self.assertAlmostEqual(profile.area_mm2, 1000.0)
        self.assertAlmostEqual(profile.mass_kg_m, 2.7)

    def test_positive_weight_without_authoritative_density_blocks(self):
        for material in ("", "UNKNOWN-MATERIAL", "C24"):
            with self.subTest(material=material):
                namespace = self._namespace(_nc1_header(material=material))
                with self.assertRaisesRegex(ValueError, "MATERIAL_.*REVIEW_REQUIRED"):
                    namespace["profile_from_nc1"]("unknown.nc1")

    def test_zero_weight_does_not_request_density_or_invent_weight_at_factory_boundary(self):
        # The section factory is a separate catalog concern. Verify that this
        # import boundary supplies no invented area/weight when the header has none.
        factory = Mock(side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
        namespace = self._namespace(_nc1_header(weight=0, material=""), ProfileDefinition=factory)
        with patch("cws_convertor.conversion_service.conversion_material_density", side_effect=AssertionError("No density needed")):
            profile = namespace["profile_from_nc1"]("zero.nc1")
        self.assertEqual(profile.area_mm2, 0)
        self.assertEqual(profile.mass_kg_m, 0)

    def test_actual_zero_weight_profile_retains_unresolved_mass_after_catalogue_defaults(self):
        namespace = self._namespace(_nc1_header(weight=0, material=""))
        with patch("cws_convertor.conversion_service.conversion_material_density", side_effect=AssertionError("No density needed")):
            profile = namespace["profile_from_nc1"]("zero.nc1")
        self.assertGreater(profile.area_mm2, 0)  # Geometry may establish area independently of material.
        self.assertEqual(profile.mass_kg_m, 0)
        self.assertEqual(profile.properties["mass_status"], "unresolved")
        self.assertEqual(profile.properties["mass_source"], "NC1.header.weight")
        self.assertEqual(profile.properties["source_material"], "")

    def test_nonfinite_and_negative_weight_are_rejected(self):
        for weight in (float("nan"), float("inf"), -float("inf"), -1):
            with self.subTest(weight=weight):
                namespace = self._namespace(_nc1_header(weight=weight))
                with self.assertRaises(ValueError):
                    namespace["profile_from_nc1"]("invalid.nc1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
