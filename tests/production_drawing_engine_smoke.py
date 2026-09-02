from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.drawings import (
    DRAWING_DOCUMENT_SCHEMA,
    DrawingBuildRequest,
    DrawingLinter,
    DrawingPrimitive,
    DrawingProjectionModel,
    ProductionDrawingEngine,
    ProductionDrawingRenderer,
    page_size_mm,
)


def _box_mesh() -> tuple[np.ndarray, np.ndarray]:
    vertices = np.asarray(
        (
            (0.0, 0.0, 0.0), (120.0, 0.0, 0.0), (120.0, 60.0, 0.0), (0.0, 60.0, 0.0),
            (0.0, 0.0, 20.0), (120.0, 0.0, 20.0), (120.0, 60.0, 20.0), (0.0, 60.0, 20.0),
        ),
        dtype=float,
    )
    triangles = np.asarray(
        (
            (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
            (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2),
            (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0),
        ),
        dtype=int,
    )
    return vertices, triangles


class ProductionDrawingEngineTests(unittest.TestCase):
    def test_occt_edge_sampler_uses_supported_curve_adaptor_api(self) -> None:
        class Point:
            def __init__(self, value: float) -> None:
                self.value = value

        class Curve:
            @staticmethod
            def FirstParameter() -> float:
                return 2.0

            @staticmethod
            def LastParameter() -> float:
                return 8.0

        class Edge:
            @staticmethod
            def _geomAdaptor() -> Curve:
                return Curve()

        calls: list[tuple[object, float, float, float]] = []

        class Sampler:
            def __init__(self, curve: object, deflection: float, start: float, end: float) -> None:
                calls.append((curve, deflection, start, end))

            @staticmethod
            def IsDone() -> bool:
                return True

            @staticmethod
            def NbPoints() -> int:
                return 3

            @staticmethod
            def Value(index: int) -> Point:
                return Point(float(index))

        points = DrawingProjectionModel._discretize_occt_edge(
            Edge(),
            0.05,
            sampler_factory=Sampler,
        )

        self.assertEqual([point.value for point in points], [1.0, 2.0, 3.0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1:], (0.05, 2.0, 8.0))

    def _request(self, **changes) -> DrawingBuildRequest:
        vertices, triangles = _box_mesh()
        values = dict(
            entity_id="P1",
            vertices=vertices,
            triangles=triangles,
            views=("front", "top", "side", "iso", "3d"),
            sheet_format="A3",
            orientation="portrait",
            unit="cm",
            dimension_mode="Productiematen",
            features=(
                {"feature_id": "H1", "kind": "hole", "parameters": {"x_mm": 30.0, "y_mm": 20.0, "diameter_mm": 18.0}},
                {"feature_id": "S1", "kind": "slot", "parameters": {"x_mm": 70.0, "y_mm": 20.0, "width_mm": 14.0, "length_mm": 34.0}},
                {"feature_id": "C1", "kind": "countersink", "parameters": {"x_mm": 95.0, "y_mm": 35.0, "diameter_mm": 12.0, "outer_diameter_mm": 24.0}},
                {"feature_id": "PCK1", "kind": "pocket", "parameters": {"x_mm": 50.0, "y_mm": 42.0, "width_mm": 20.0, "height_mm": 10.0}},
                {"feature_id": "M1", "kind": "miter", "parameters": {"x_mm": 120.0, "angle_deg": 45.0}},
                {"feature_id": "SC1", "kind": "scribe", "parameters": {"x_mm": 42.0, "y_mm": 12.0, "length_mm": 25.0}},
            ),
            dimensions=(
                {"id": "overall-x", "kind": "linear", "value_mm": 120.0, "critical": True},
                {"id": "overall-y", "kind": "linear", "value_mm": 60.0, "critical": True},
                {"id": "hole-001-diameter", "kind": "diameter", "value_mm": 18.0, "critical": True},
            ),
            manual_dimensions=(
                {"id": "manual-M1", "view": "front", "axis": "horizontal", "start": 0.0, "end": 45.0, "feature_id": "H1", "anchor_type": "feature_center"},
            ),
            title_block={"project": "CWS", "entity": "P1", "profile": "PL120x20", "material": "S355", "revision": "A", "status": "REVIEW"},
            revisions=({"revision": "A", "status": "REVIEW"},),
            bom=({"mark": "P1", "quantity": 2, "profile": "PL120x20", "material": "S355"},),
            notes=("Ontbramen.",),
        )
        values.update(changes)
        return DrawingBuildRequest(**values)

    def test_document_is_single_versioned_authority_for_all_content(self) -> None:
        document = ProductionDrawingEngine.build(self._request())
        self.assertEqual(document.schema_version, DRAWING_DOCUMENT_SCHEMA)
        self.assertEqual(document.orientation, "portrait")
        self.assertEqual((document.pages[0].width_mm, document.pages[0].height_mm), (297.0, 420.0))
        self.assertGreaterEqual(len(document.pages), 2)
        self.assertEqual(document.lint["dimension_coverage_percent"], 100.0)
        self.assertEqual(document.lint["feature_coverage_percent"], 100.0)
        rendered_text = [item.text for page in document.pages for item in page.primitives if item.kind == "text"]
        self.assertTrue(any("12 cm" in value for value in rendered_text))
        for expected in ("SLEUF", "VERZONKEN", "POCKET", "KOPSE SNEDE", "SCRIBE", "SECTION A-A", "DIMENSIONGRAPH", "MATERIAALLIJST", "REVISIETABEL"):
            self.assertTrue(any(expected in value for value in rendered_text), expected)
        for feature_id in ("H1", "S1", "C1", "PCK1", "M1", "SC1"):
            self.assertIn(f"DETAIL {feature_id}", rendered_text)

    def test_pdf_preview_and_embedded_document_are_the_same_content(self) -> None:
        document = ProductionDrawingEngine.build(self._request())
        with TemporaryDirectory(prefix="cws_production_drawing_") as directory:
            pdf = Path(directory) / "P1.pdf"
            png = Path(directory) / "P1.png"
            ProductionDrawingRenderer.render(document, pdf_path=pdf, png_path=png)
            restored = ProductionDrawingRenderer.load_embedded_document(pdf)
            self.assertEqual(restored.document_sha256, document.document_sha256)
            self.assertEqual(restored.visible_content_sha256, document.visible_content_sha256)
            self.assertEqual(len(restored.pages), len(document.pages))
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
            self.assertGreater(png.stat().st_size, 512)

    def test_all_iso_sheet_sizes_and_orientations_use_physical_dimensions(self) -> None:
        for sheet_format in ("A4", "A3", "A2", "A1", "A0"):
            for orientation in ("portrait", "landscape"):
                with self.subTest(sheet_format=sheet_format, orientation=orientation):
                    document = ProductionDrawingEngine.build(
                        self._request(
                            sheet_format=sheet_format,
                            orientation=orientation,
                            include_sections=False,
                            include_details=False,
                            bom=(),
                            notes=(),
                        )
                    )
                    self.assertEqual(
                        (document.pages[0].width_mm, document.pages[0].height_mm),
                        page_size_mm(sheet_format, orientation),
                    )

    def test_embedded_drawing_document_tamper_is_rejected(self) -> None:
        from pypdf import PdfReader, PdfWriter

        document = ProductionDrawingEngine.build(self._request())
        with TemporaryDirectory(prefix="cws_drawing_tamper_") as directory:
            pdf = Path(directory) / "P1.pdf"
            damaged = Path(directory) / "P1-damaged.pdf"
            ProductionDrawingRenderer.render_pdf(document, pdf)
            writer = PdfWriter()
            writer.clone_document_from_reader(PdfReader(str(pdf)))
            names = writer.root_object["/Names"].get_object()["/EmbeddedFiles"].get_object()["/Names"]
            changed = False
            for index in range(0, len(names), 2):
                if str(names[index]) != "cws-drawing-document.json":
                    continue
                stream = names[index + 1].get_object()["/EF"]["/F"].get_object()
                stream.set_data(b'{"schema_version":"damaged"}')
                changed = True
                break
            self.assertTrue(changed)
            with damaged.open("wb") as handle:
                writer.write(handle)
            with self.assertRaises((ValueError, TypeError)):
                ProductionDrawingRenderer.load_embedded_document(damaged)

    def test_linter_detects_clipping_and_annotation_collision(self) -> None:
        document = ProductionDrawingEngine.build(self._request())
        document.pages[0].primitives.extend(
            (
                DrawingPrimitive("text", "annotations", points=[[-5.0, 12.0]], text="BUITEN", semantic_id="outside"),
                DrawingPrimitive("text", "annotations", points=[[30.0, 30.0]], text="OVERLAP A", semantic_id="overlap-a"),
                DrawingPrimitive("text", "annotations", points=[[30.5, 30.0]], text="OVERLAP B", semantic_id="overlap-b"),
            )
        )
        document.document_sha256 = ""
        result = DrawingLinter.lint(document)
        codes = {issue.code for issue in result.issues}
        self.assertIn("DRAWING_CONTENT_CLIPPED", codes)
        self.assertIn("DRAWING_ANNOTATION_COLLISION", codes)
        self.assertFalse(result.release_ready)

    def test_mesh_fallback_is_explicitly_fail_closed(self) -> None:
        document = ProductionDrawingEngine.build(self._request())
        codes = {item["code"] for item in document.lint["issues"]}
        self.assertFalse(document.lint["release_ready"])
        self.assertIn("DRAWING_GEOMETRY_NOT_CANONICAL", codes)
        self.assertIn("DRAWING_EXACT_HLR_MISSING", codes)
        self.assertIn("DRAWING_GEOMETRY_STALE", codes)

    def test_release_ready_requires_and_accepts_all_exact_gates(self) -> None:
        visible = (np.asarray(((0.0, 0.0), (120.0, 0.0), (120.0, 60.0), (0.0, 60.0), (0.0, 0.0))),)
        section = (np.asarray(((0.0, 0.0), (60.0, 0.0), (60.0, 20.0), (0.0, 20.0), (0.0, 0.0))),)
        with (
            patch.object(DrawingProjectionModel, "edge_layers", return_value=(visible, (), "occt_hlr")),
            patch.object(DrawingProjectionModel, "exact_section_polylines", return_value=section),
        ):
            document = ProductionDrawingEngine.build(
                self._request(
                    geometry_basis="canonical_rebuild_brep",
                    geometry_sha256="b" * 64,
                    manufacturing_sha256="a" * 64,
                    expected_manufacturing_sha256="a" * 64,
                    canonical_rebuild_current=True,
                    canonical_payload_current=True,
                    roundtrip_current=True,
                    title_block={"project": "CWS", "entity": "P1", "profile": "PL120x20", "material": "S355", "revision": "A", "status": "released"},
                    exact_shape=object(),
                )
            )
        self.assertTrue(document.lint["release_ready"], document.lint["issues"])
        self.assertEqual("occt_brep_section", document.section_method)

    def test_large_dimension_schedule_creates_continuation_sheets(self) -> None:
        dimensions = tuple(
            {"id": f"production-{index:03d}", "kind": "linear", "value_mm": float(index + 1), "critical": True}
            for index in range(80)
        )
        document = ProductionDrawingEngine.build(
            self._request(dimensions=dimensions, features=(), bom=(), include_sections=False, include_details=False)
        )
        self.assertGreater(len(document.pages), 2)
        self.assertEqual(document.lint["dimension_coverage_percent"], 100.0)

    def test_coplanar_mesh_diagonal_is_not_a_drawing_edge(self) -> None:
        vertices = np.asarray(((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (10.0, 10.0, 0.0), (0.0, 10.0, 0.0)))
        triangles = np.asarray(((0, 1, 2), (0, 2, 3)))
        visible, hidden = DrawingProjectionModel._mesh_edge_layers(triangles, vertices, np.asarray((0.0, 0.0, 1.0)))
        self.assertEqual(set(visible), {(0, 1), (1, 2), (2, 3), (0, 3)})
        self.assertNotIn((0, 2), set(visible) | set(hidden))

    def test_iso_and_3d_are_distinct_projections(self) -> None:
        vertices, _triangles = _box_mesh()
        iso, _ = DrawingProjectionModel.project(vertices, "iso")
        review_3d, _ = DrawingProjectionModel.project(vertices, "3d")
        self.assertFalse(np.allclose(iso, review_3d))

    def test_native_occt_hlr_and_trusted_pdf_bind_the_same_document(self) -> None:
        try:
            import converter as core
            from conversion import build_shape
            from pdf_support import canonical_from_nc1, create_trusted_pdf, load_trusted_pdf
            from tests.regression_smoke import write_sample_nc1
        except ImportError as exc:
            self.skipTest(f"Native CadQuery/OCCT runtime ontbreekt: {exc}")

        with TemporaryDirectory(prefix="cws_native_drawing_") as directory:
            root = Path(directory)
            source = root / "native.nc1"
            target = root / "native.pdf"
            write_sample_nc1(source)
            canonical = canonical_from_nc1(source)
            shape = build_shape(core.parse_nc1(source)).val()
            raw_vertices, raw_triangles = shape.tessellate(0.08)
            vertices = np.asarray([point.toTuple() for point in raw_vertices], dtype=float)
            triangles = np.asarray(raw_triangles, dtype=int)
            geometry_sha256 = canonical.geometry_sha256()
            document = ProductionDrawingEngine.build(
                self._request(
                    entity_id=canonical.part_id,
                    vertices=vertices,
                    triangles=triangles,
                    views=("front", "top", "side", "iso"),
                    features=(),
                    dimensions=(
                        {"id": "overall-x", "kind": "linear", "value_mm": float(shape.BoundingBox().xlen), "critical": True},
                        {"id": "overall-y", "kind": "linear", "value_mm": float(shape.BoundingBox().ylen), "critical": True},
                    ),
                    manual_dimensions=(),
                    geometry_basis="canonical_rebuild_brep",
                    geometry_sha256=geometry_sha256,
                    manufacturing_sha256=geometry_sha256,
                    expected_manufacturing_sha256=geometry_sha256,
                    canonical_rebuild_current=True,
                    canonical_payload_current=True,
                    roundtrip_current=True,
                    title_block={
                        "project": "CWS native gate",
                        "entity": canonical.part_id,
                        "profile": canonical.header.profile or "NC1",
                        "material": canonical.header.material or "S355",
                        "revision": "A",
                        "status": "released",
                    },
                    exact_shape=shape,
                )
            )
            self.assertEqual("occt_hlr", document.hlr_method)
            self.assertEqual("occt_brep_section", document.section_method)
            self.assertTrue(document.lint["release_ready"], document.lint["issues"])

            result = create_trusted_pdf(canonical, target, drawing_document=document)
            verified = load_trusted_pdf(target, strict=True)
            restored = ProductionDrawingRenderer.load_embedded_document(target)
            self.assertEqual(document.document_sha256, restored.document_sha256)
            self.assertEqual(document.visible_content_sha256, restored.visible_content_sha256)
            self.assertEqual(document.document_sha256, result.details["drawing_document_sha256"])
            self.assertEqual(document.document_sha256, verified.details["manifest"]["drawing_document_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
