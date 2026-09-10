"""Native regressions for scale consistency on sections and detail sheets."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import cadquery as cq
from cws_convertor.drawings import DrawingBuildRequest, ProductionDrawingEngine
from tests.production_drawing_engine_smoke import _box_mesh


class DrawingAllSheetScaleTests(unittest.TestCase):
    def request(self, **changes):
        vertices, triangles = _box_mesh()
        vertices *= np.asarray((1.0, 200.0 / 60.0, 10.0))
        values=dict(entity_id="SCALE-QA", vertices=vertices, triangles=triangles,
            exact_shape=cq.Workplane("XY").box(120,200,200,centered=(False,False,False)).val(),
            views=("front",), sheet_format="A4", scale_denominator=2,
            include_sections=True, include_details=False)
        values.update(changes)
        return DrawingBuildRequest(**values)

    def assert_visible_inside_views(self, document):
        for context in document.view_contexts:
            page=document.pages[context["page_number"]-1]
            left,top,right,bottom=context["rectangle"]
            primitives=[p for p in page.primitives if p.layer=="visible" and p.semantic_id.startswith(context["view_id"]+"-")]
            self.assertTrue(primitives,context["view_id"])
            for primitive in primitives:
                for x,y in primitive.points:
                    self.assertGreaterEqual(x,left-1e-6)
                    self.assertLessEqual(x,right+1e-6)
                    self.assertGreaterEqual(y,top-1e-6)
                    self.assertLessEqual(y,bottom+1e-6)

    def test_fixed_scale_must_fit_section_even_when_front_fits(self):
        for exact in (self.request().exact_shape,None):
            with self.subTest(native=exact is not None):
                request=self.request(exact_shape=exact)
                self.assertEqual(ProductionDrawingEngine.build(replace(request,include_sections=False)).scale_denominator,2)
                with self.assertRaisesRegex(ValueError,"Vaste schaal 1:2 past niet"):
                    ProductionDrawingEngine.build(request)

    def test_fitting_exact_and_review_sections_keep_stated_scale(self):
        for exact in (self.request().exact_shape,None):
            with self.subTest(native=exact is not None):
                document=ProductionDrawingEngine.build(self.request(exact_shape=exact,scale_denominator=5))
                self.assertEqual(document.scale_denominator,5)
                self.assertEqual({round(v["scale"],8) for v in document.view_contexts},{0.2})
                self.assert_visible_inside_views(document)

    def test_auto_preflights_all_sheet_cells(self):
        for exact in (self.request().exact_shape,None):
            document=ProductionDrawingEngine.build(self.request(exact_shape=exact,scale_denominator=None))
            self.assertGreaterEqual(document.scale_denominator,5)
            self.assertTrue(all(abs(v["scale"]-1/document.scale_denominator)<1e-9 for v in document.view_contexts))
            self.assert_visible_inside_views(document)

    def test_exact_section_never_silently_clamps_in_direct_route(self):
        request=self.request();page=ProductionDrawingEngine._base_page(2,"QA",297,210)
        with self.assertRaisesRegex(ValueError,"doorsnede A-A"):
            ProductionDrawingEngine._add_section_view(page,vertices=request.vertices,triangles=request.triangles,
                rectangle=(10,23,144.5,100.8),denominator=2,exact_shape=request.exact_shape)

    def test_detail_has_own_visible_scale_and_does_not_change_main_scale(self):
        features=({"feature_id":"H1","kind":"hole","parameters":{"x_mm":30,"y_mm":40,"diameter_mm":18}},)
        document=ProductionDrawingEngine.build(self.request(include_sections=False,include_details=True,features=features))
        self.assertEqual(document.scale_denominator,2)
        self.assertEqual(document.view_contexts[0]["scale"],0.5)
        details=[v for v in document.view_contexts if v.get("detail")]
        self.assertEqual(len(details),1)
        context=details[0];denominator=round(1/context["scale"])
        self.assertGreaterEqual(denominator,5)
        labels=[p.text for p in document.pages[context["page_number"]-1].primitives if p.kind=="text"]
        self.assertIn("DETAIL H1",labels)
        self.assertIn(f"SCHAAL 1:{denominator}",labels)
        self.assert_visible_inside_views(document)

    def test_every_overflow_detail_sheet_is_fit_and_labelled(self):
        features=tuple({"feature_id":f"H{i}","kind":"hole","parameters":{"x_mm":20+i*10,"y_mm":40,"diameter_mm":12}}
                       for i in range(1,7))
        document=ProductionDrawingEngine.build(self.request(include_sections=False,include_details=True,features=features))
        details=[v for v in document.view_contexts if v.get("detail")]
        self.assertEqual(len(details),6)
        for context in details:
            labels=[p.text for p in document.pages[context["page_number"]-1].primitives if p.kind=="text"]
            self.assertIn(f"DETAIL {context['feature_id']}",labels)
            scale_labels=[p.text for p in document.pages[context["page_number"]-1].primitives
                          if p.semantic_id==f"{context['feature_id']}-detail-scale"]
            self.assertEqual(scale_labels,[f"SCHAAL 1:{round(1/context['scale'])}"])
        self.assert_visible_inside_views(document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
