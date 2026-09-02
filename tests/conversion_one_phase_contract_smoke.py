from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.conversion_service import (
    DEFAULT_CONVERSION_PLANNER,
    FORMATS,
    ROUTES,
    ConversionScope,
    ConversionSource,
    ConversionStatus,
)


class ConversionOnePhaseContractTests(unittest.TestCase):
    def test_registry_contains_every_cross_format_route_exactly_once(self) -> None:
        expected = {
            f"{source.lower()}-{target.lower()}"
            for source in FORMATS
            for target in FORMATS
            if source != target
        }
        self.assertEqual(12, len(ROUTES))
        self.assertEqual(expected, {route.direction for route in ROUTES})

    def test_planner_exposes_only_the_four_product_statuses(self) -> None:
        self.assertEqual(
            {"SUPPORTED", "SUPPORTED_WITH_LIMITS", "REVIEW", "BLOCKED"},
            {item.value for item in ConversionStatus},
        )

        supported = DEFAULT_CONVERSION_PLANNER.plan_source(
            ConversionSource(
                "part.nc1", "NC1", "a" * 64, exact_source=True,
                part_form="plate", features=("hole", "outer_contour"), solid_count=1,
            ),
            "nc1-step",
        )
        limited = DEFAULT_CONVERSION_PLANNER.plan_source(supported.source, "nc1-pdf")
        review = DEFAULT_CONVERSION_PLANNER.plan_source(
            ConversionSource(
                "drawing.pdf", "PDF", "b" * 64,
                blockers=("EXTERNAL_PDF_REVIEW_REQUIRED",),
            ),
            "pdf-step",
        )
        blocked = DEFAULT_CONVERSION_PLANNER.plan_source(
            ConversionSource(
                "unsafe.nc1", "NC1", "c" * 64, exact_source=True,
                part_form="plate", features=("unsupported_block:sc",), solid_count=1,
            ),
            "nc1-step",
        )
        self.assertEqual(ConversionStatus.SUPPORTED, supported.status)
        self.assertEqual(ConversionStatus.SUPPORTED_WITH_LIMITS, limited.status)
        self.assertEqual(ConversionStatus.REVIEW, review.status)
        self.assertEqual(ConversionStatus.BLOCKED, blocked.status)
        self.assertTrue(supported.executable)
        self.assertFalse(review.executable)
        self.assertFalse(blocked.executable)

    def test_all_trusted_ordinary_routes_are_executable(self) -> None:
        for source_format in FORMATS:
            source = ConversionSource(
                f"part.{source_format.lower()}",
                source_format,
                source_format.lower() * 16,
                exact_source=True,
                trusted_payload=source_format in {"STEP", "IFC", "PDF"},
                part_form="plate",
                features=("hole", "outer_contour"),
                solid_count=1,
                product_count=1,
                part_ids=("P1",),
            )
            for target_format in FORMATS:
                if target_format == source_format:
                    continue
                plan = DEFAULT_CONVERSION_PLANNER.plan_source(
                    source,
                    f"{source_format.lower()}-{target_format.lower()}",
                )
                self.assertTrue(plan.executable, plan.to_dict())
                if target_format == "PDF":
                    self.assertEqual(ConversionStatus.SUPPORTED_WITH_LIMITS, plan.status)

    def test_multi_solid_is_split_packaged_or_explicitly_reviewed(self) -> None:
        trusted = ConversionSource(
            "multi.step", "STEP", "d" * 64,
            exact_source=True, trusted_payload=True, solid_count=3,
            scope=ConversionScope.PART_SPLIT.value,
        )
        split = DEFAULT_CONVERSION_PLANNER.plan_source(trusted, "step-nc1")
        package = DEFAULT_CONVERSION_PLANNER.plan_source(trusted, "step-ifc")
        self.assertEqual(ConversionScope.PART_SPLIT.value, split.scope)
        self.assertIn("MULTI_SOLID_PART_SPLIT", split.warnings)
        self.assertEqual(ConversionScope.ASSEMBLY_PACKAGE.value, package.scope)
        self.assertIn("MULTI_SOLID_ASSEMBLY_PACKAGE_WITH_IDENTITY_MANIFEST", package.warnings)

        history_free = ConversionSource(
            "multi.step", "STEP", "e" * 64,
            exact_source=True, trusted_payload=False, solid_count=3,
        )
        reviewed = DEFAULT_CONVERSION_PLANNER.plan_source(history_free, "step-nc1")
        self.assertEqual(ConversionStatus.REVIEW, reviewed.status)
        self.assertIn("MULTI_SOLID_PER_PART_MGI_PROOF_REQUIRED", reviewed.blockers)

    def test_ui_worker_and_legacy_entry_all_use_the_central_service(self) -> None:
        ui = (ROOT / "cws_convertor/ui_qt/converter_panel.py").read_text(encoding="utf-8")
        worker = (ROOT / "cws_convertor/conversion_worker.py").read_text(encoding="utf-8")
        legacy = (ROOT / "conversion.py").read_text(encoding="utf-8")
        roundtrip = (ROOT / "cws_convertor/project/roundtrip.py").read_text(encoding="utf-8")
        for direction in {route.direction for route in ROUTES}:
            self.assertIn(f'"{direction}"', ui)
        self.assertNotIn("allowed = allowed or", ui)
        self.assertIn("DEFAULT_CONVERSION_SERVICE.preflight", ui)
        self.assertIn('"sources": [str(source) for source in self.files]', ui)
        self.assertIn("DEFAULT_CONVERSION_SERVICE.convert_batch", worker)
        self.assertIn("preflight_complete_before_execution", (ROOT / "cws_convertor/conversion_service.py").read_text(encoding="utf-8"))
        self.assertIn("DEFAULT_CONVERSION_SERVICE.convert_file", legacy)
        self.assertIn("def validate_target_roundtrip", roundtrip)
        self.assertIn('"validation_scope"', roundtrip)
        self.assertIn("_visible_pdf_checks", roundtrip)


if __name__ == "__main__":
    unittest.main(verbosity=2)
