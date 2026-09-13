from pathlib import Path
import tempfile
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cws_convertor.project import ProjectSession
# Two BREP bodies in ONE product, no child PRODUCT occurrences. Body count is
# explicitly two; physical make-part count is deliberately NOT asserted.
TEXT="""ISO-10303-21;HEADER;FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));ENDSEC;DATA;
#1=PRODUCT('Body_348','Body_348','',());
#2=PRODUCT_DEFINITION_FORMATION('','',#1);
#3=PRODUCT_DEFINITION('','',#2,$);
#4=PRODUCT_DEFINITION_SHAPE('','',#3);
#5=SHAPE_DEFINITION_REPRESENTATION(#4,#6);
#6=ADVANCED_BREP_SHAPE_REPRESENTATION('',(#7,#9),$);
#7=MANIFOLD_SOLID_BREP('body A',#8);#8=CLOSED_SHELL('',());
#9=MANIFOLD_SOLID_BREP('body B',#10);#10=CLOSED_SHELL('',());
ENDSEC;END-ISO-10303-21;"""
class ProductBodyTests(unittest.TestCase):
 def test_one_source_product_keeps_bodies_without_fabricating_bom_parts(self):
  with tempfile.TemporaryDirectory() as folder:
   source=Path(folder)/'product.stp';source.write_text(TEXT)
   with ProjectSession.new('body inventory') as session:
    registered=session.register_sources([source],include_step_geometry=False)[0].source
    result=session.semantic_import_source(registered.source_id)
    self.assertEqual(1,len(session.project.parts))
    part=next(iter(session.project.parts.values()))
    self.assertEqual(2,part.properties['source_solid_count'])
    self.assertEqual(['#7','#9'],part.geometry_descriptor['source_locator']['selector']['entity_ids'])
    self.assertEqual('REVIEW_REQUIRED',part.properties['body_decomposition_status'])
    self.assertIsNone(part.properties['physical_part_count'])
    self.assertFalse(part.nc1_eligible)
    target=session.save(Path(folder)/'saved.cwscproj')
   with ProjectSession.open(target) as reopened:
    self.assertEqual(1,len(reopened.project.parts))
    self.assertEqual(2,next(iter(reopened.project.parts.values())).properties['source_solid_count'])
if __name__=='__main__':unittest.main(verbosity=2)
