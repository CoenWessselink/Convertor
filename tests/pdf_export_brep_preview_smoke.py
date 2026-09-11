"""Real BREP/PDF regression; the example geometry is explicitly synthetic."""
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
import fitz
import cadquery as cq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from canonical_model import CanonicalPart,CanonicalHeader,CanonicalContour,CanonicalContourPoint,CanonicalHole
from pdf_support import render_part_pdf,PDFSupportError,_draw_isometric_profile
from cws_convertor.drawings.projection import DrawingProjectionModel


def part():
    return CanonicalPart(part_id='SYNTHETIC-PLATE',header=CanonicalHeader(profile='PL10*100',profile_type='B',length=200,dim1=100,dim2=10),
        contours=[CanonicalContour(kind='AK',face='v',points=[CanonicalContourPoint(x=x,q=y) for x,y in ((0,0),(200,0),(200,100),(0,100))])],
        holes=[CanonicalHole(face='v',x=40,q=40,diameter=14)])

def shape():
    return cq.Workplane('XY').box(200,100,10,centered=(False,False,False)).val().cut(cq.Solid.makeCylinder(7,10,cq.Vector(40,40,0)))


class BRepPDFTests(unittest.TestCase):
    def test_actual_plate_uses_shared_hlr_not_h_profile_art(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/'plate.pdf';solid=shape()
            with patch.object(DrawingProjectionModel,'_occt_hlr_polylines',wraps=DrawingProjectionModel._occt_hlr_polylines) as projection:
                render_part_pdf(part(),dest,exact_shape=solid)
            self.assertEqual(projection.call_count,1);self.assertIs(projection.call_args.args[0],solid)
            with fitz.open(dest) as d:
                text=d[0].get_text();self.assertIn('OCCT HLR',text);self.assertIn('PLATE - EDGE VIEW',text);self.assertNotIn('FLANGE',text)
                self.assertGreater(len(d[0].get_drawings()),25)
    def test_unknown_shape_produces_notice_not_invented_geometry(self):
        class RecordingCanvas:
            def __init__(self):self.strings=[]
            def setFont(self,*args):pass
            def drawString(self,x,y,text):self.strings.append(text)
        canvas=RecordingCanvas();_draw_isometric_profile(canvas,part(),x=0,y=0,width=200,height=100)
        self.assertIn('exact bronmodel ontbreekt',' '.join(canvas.strings))
    def test_failed_hlr_is_not_replaced_by_a_placeholder(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(DrawingProjectionModel,'_occt_hlr_polylines',side_effect=RuntimeError('deliberate failed BREP')):
            with self.assertRaises(PDFSupportError):render_part_pdf(part(),Path(folder)/'bad.pdf',exact_shape=shape())
    def test_visible_main_rectangle_matches_actual_declared_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            p=part();p.drawing.scale='1:5';dest=Path(folder)/'scale.pdf';render_part_pdf(p,dest,exact_shape=shape())
            with fitz.open(dest) as d:
                self.assertIn('SCALE 1:5',d[0].get_text())
                wanted=200*72/25.4/5
                lines=[item for drawing in d[0].get_drawings() for item in drawing['items'] if item[0]=='l']
                self.assertTrue(any(abs((line[2]-line[1]).x-wanted)<.01 and abs((line[2]-line[1]).y)<.01 for line in lines))
    def test_oversized_fixed_scale_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p=part();p.drawing.scale='1:1'
            with self.assertRaisesRegex(PDFSupportError,'past niet'):render_part_pdf(p,Path(folder)/'oversized.pdf',exact_shape=shape())
    def test_non_finite_projection_refuses_export(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(DrawingProjectionModel,'_occt_hlr_polylines',return_value=((np.array([[0.,0.],[float('nan'),1.]]),),())):
            with self.assertRaises(PDFSupportError):render_part_pdf(part(),Path(folder)/'nan.pdf',exact_shape=shape())
    def test_fresh_canonical_release_roundtrip_proves_exact_projection(self):
        from production_release_package_smoke import _released_project
        with tempfile.TemporaryDirectory() as folder:
            w=_released_project(Path(folder),part_id='B',part_position='B',assembly_id='A',assembly_mark='A')
            p=w.project.parts['B'];report=p.workbench['current_revision']['roundtrip_validation']
            self.assertEqual(report['status'],'passed')
            rows=report['formats']['pdf']['checks']
            self.assertTrue(any(c['property']=='pdf_exact_brep_projection' and c['status']=='passed' for c in rows))

class ExternalSourceScaleTests(unittest.TestCase):
    def reviewed(self, folder, output_scale=None):
        from pdf_support import analyze_external_pdf, apply_review
        from validation.pdf_fixtures import create_synthetic_lo4_pdf
        source=create_synthetic_lo4_pdf(Path(folder)/'external.pdf')
        analysis=analyze_external_pdf(source)
        self.assertEqual(analysis.detected_fields['scale'],'1:2')
        self.assertEqual(analysis.part.field_evidence['scale'].value,'1:2')
        self.assertEqual(analysis.part.drawing.scale,'auto')
        self.assertEqual(analysis.part.properties['source_drawing']['source_sha256'],analysis.source_sha256)
        values={} if output_scale is None else {'drawing.scale':output_scale}
        reviewed=apply_review(analysis,{'reviewed_by':'synthetic-regression',
            'confirm':['holes[0]','material'],'values':values})
        self.assertTrue(reviewed.production_export_allowed)
        return reviewed

    def test_source_scale_stays_provenance_and_auto_output_is_physically_true(self):
        from pdf_support import finalize_reviewed_analysis,load_trusted_pdf
        with tempfile.TemporaryDirectory() as folder:
            reviewed=self.reviewed(folder);target=Path(folder)/'output.pdf'
            finalize_reviewed_analysis(reviewed,target)
            saved=load_trusted_pdf(target).part
            self.assertEqual(saved.properties['source_drawing']['scale'],'1:2')
            self.assertEqual(saved.field_evidence['scale'].value,'1:2')
            self.assertEqual(reviewed.part.drawing.scale,'auto')
            with fitz.open(target) as doc:
                self.assertIn('SCALE 1:5',doc[0].get_text())
                wanted=120*72/25.4/5
                lines=[item for drawing in doc[0].get_drawings() for item in drawing['items'] if item[0]=='l']
                self.assertTrue(any(abs(abs((line[2]-line[1]).y)-wanted)<.01 and abs((line[2]-line[1]).x)<.01 for line in lines))

    def test_explicit_output_scale_is_applied_without_changing_source_evidence(self):
        from pdf_support import finalize_reviewed_analysis,load_trusted_pdf
        with tempfile.TemporaryDirectory() as folder:
            reviewed=self.reviewed(folder,'1:10');target=Path(folder)/'output.pdf'
            finalize_reviewed_analysis(reviewed,target)
            saved=load_trusted_pdf(target).part
            self.assertEqual(saved.drawing.scale,'1:10')
            self.assertEqual(saved.properties['source_drawing']['scale'],'1:2')
            with fitz.open(target) as doc:self.assertIn('SCALE 1:10',doc[0].get_text())

    def test_explicit_oversized_scale_is_not_silently_changed_to_auto(self):
        from pdf_support import finalize_reviewed_analysis
        with tempfile.TemporaryDirectory() as folder:
            reviewed=self.reviewed(folder,'1:1');target=Path(folder)/'output.pdf'
            with self.assertRaisesRegex(PDFSupportError,'past niet'):finalize_reviewed_analysis(reviewed,target)
            self.assertFalse(target.exists())
            self.assertEqual(reviewed.part.drawing.scale,'1:1')

    def test_output_review_field_is_distinct_from_source_scale_evidence(self):
        from review_workflow import collect_review_fields
        with tempfile.TemporaryDirectory() as folder:
            reviewed=self.reviewed(folder)
            row=next(f for f in collect_review_fields(reviewed.part) if f.path=='drawing.scale')
            self.assertIn('Uitvoerschaal',row.label)
            self.assertEqual(row.current_value,'auto')
            self.assertEqual(row.evidence_path,'scale')


if __name__=='__main__':unittest.main(verbosity=2)
