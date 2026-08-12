from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_project.baseline import inspect_model_file, iter_p21_statements, split_p21_args
from cws_project.model import ImportStrategy


MINIMAL_IFC = """ISO-10303-21;
HEADER;
FILE_NAME('sample.ifc','2026-01-01T00:00:00',('CWS'),('CWS'),'test','CWS Convertor','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCELEMENTASSEMBLY('guid',$,'PLAAT',$,$,$,$,'MLO4',.NOTDEFINED.,.NOTDEFINED.);
#2=IFCPLATE('guid2',$,'PLAAT','STRIP5*120',$,$,$,'LO4');
#3=IFCMECHANICALFASTENER('guid3',$,'Bolt assembly',$,$,$,$,'B1',14.,10.);
#4=IFCFASTENER('guid4',$,'Weld',$,$,$,$,'W1');
#5=IFCPROPERTYSINGLEVALUE('Length',$,IFCLENGTHMEASURE(160.),$);
#6=IFCPROPERTYSINGLEVALUE('MATERIAL',$,IFCLABEL('S235JR'),$);
#7=IFCPROPERTYSINGLEVALUE('Assembly/Cast unit weight',$,IFCMASSMEASURE(0.6),$);
#8=IFCPROPERTYSINGLEVALUE('Bolt hole diameter',$,IFCLENGTHMEASURE(14.),$);
#9=IFCRELAGGREGATES('rel',$,$,$,#1,(#2));
ENDSEC;
END-ISO-10303-21;
"""

MINIMAL_STEP = """ISO-10303-21;
HEADER;
FILE_NAME('part.step','2026-01-01T00:00:00',('CWS'),('CWS'),'test','test','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('2x voetplaat hoog','2x voetplaat hoog','',());
#2=PRODUCT_DEFINITION('design','',#3,#4);
#5=MANIFOLD_SOLID_BREP('one solid',#6);
#6=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class ProjectBaselineTests(unittest.TestCase):
    def test_statement_parser_handles_semicolon_in_string(self) -> None:
        with tempfile.TemporaryDirectory(prefix="p21_parser_") as folder_name:
            source = Path(folder_name) / "sample.step"
            source.write_text("#1=PRODUCT('A;B','Name','',());\n#2=CLOSED_SHELL('',());", encoding="utf-8")
            statements = list(iter_p21_statements(source))
            self.assertEqual(len(statements), 2)
            self.assertIn("A;B", statements[0])

    def test_argument_parser_handles_nested_typed_values(self) -> None:
        args = split_p21_args("'Name',$,IFCLABEL('MLO4'),(#1,#2)")
        self.assertEqual(len(args), 4)
        self.assertEqual(args[2], "IFCLABEL('MLO4')")

    def test_ifc_baseline_selects_semantic_strategy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ifc_baseline_") as folder_name:
            source = Path(folder_name) / "sample.ifc"
            source.write_text(MINIMAL_IFC, encoding="utf-8")
            result = inspect_model_file(source)
            self.assertEqual(result.import_strategy, ImportStrategy.SEMANTIC_STRUCTURE)
            self.assertEqual(result.class_summary["assemblies"], 1)
            self.assertEqual(result.class_summary["plates"], 1)
            self.assertEqual(result.class_summary["mechanical_fasteners"], 1)
            self.assertTrue(result.reference_checks["MLO4_found"])
            self.assertTrue(result.reference_checks["length_160_mm_found"])
            self.assertTrue(result.reference_checks["bolt_or_hole_diameter_14_mm_found"])

    def test_single_step_solid_is_not_split_by_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="step_baseline_") as folder_name:
            source = Path(folder_name) / "2x voetplaat hoog.step"
            source.write_text(MINIMAL_STEP, encoding="utf-8")
            result = inspect_model_file(source)
            self.assertEqual(result.product_count, 1)
            self.assertEqual(result.solid_count, 1)
            self.assertEqual(result.import_strategy, ImportStrategy.SEPARATE_SOLIDS)
            self.assertTrue(any("niet automatisch opsplitsen" in item for item in result.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
