from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession

SINGLE_STEP = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('2x voetplaat.step','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P-001','2x voetplaat','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""

ASSEMBLY_STEP = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('assembly.step','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=APPLICATION_CONTEXT('managed model');
#2=PRODUCT_CONTEXT('',#1,'mechanical');
#10=PRODUCT('ASM-1','Frame assembly','',(#2));
#11=PRODUCT_DEFINITION_FORMATION('','',#10);
#12=PRODUCT_DEFINITION('','',#11,$);
#20=PRODUCT('PART-1','Plate part','',(#2));
#21=PRODUCT_DEFINITION_FORMATION('','',#20);
#22=PRODUCT_DEFINITION('','',#21,$);
#30=NEXT_ASSEMBLY_USAGE_OCCURRENCE('OCC-1','Plate occurrence','',#12,#22,'P1');
#31=PRODUCT_DEFINITION_SHAPE('','',#30);
#32=SHAPE_DEFINITION_REPRESENTATION(#31,#33);
#33=ADVANCED_BREP_SHAPE_REPRESENTATION('',(#34),#35);
#34=MANIFOLD_SOLID_BREP('solid',#36);
#35=GEOMETRIC_REPRESENTATION_CONTEXT(3);
#36=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""

NO_SOLID_STEP = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('ambiguous.step','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('P-AMB','Ambiguous product without shape','',());
#2=PRODUCT_DEFINITION_FORMATION('','',#1);
#3=PRODUCT_DEFINITION('','',#2,$);
ENDSEC;
END-ISO-10303-21;
"""


class StepSemanticImportTests(unittest.TestCase):
    def test_single_product_single_solid_is_not_split_by_quantity_in_name(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_step_single_") as folder_name:
            source = Path(folder_name) / "2x voetplaat.step"
            source.write_text(SINGLE_STEP, encoding="utf-8")
            session = ProjectSession.new("Single STEP")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            result = session.semantic_import_source(registration.source.source_id)
            self.assertEqual(result.strategy, "B_separate_solids")
            self.assertEqual(result.entity_counts["parts"], 1)
            self.assertEqual(result.entity_counts["assemblies"], 0)
            self.assertTrue(result.evidence["filename_not_used_for_splitting"])
            self.assertTrue(any("niet automatisch gesplitst" in item for item in result.warnings))
            part = next(iter(session.project.parts.values()))
            self.assertEqual(part.name, "2x voetplaat")
            self.assertEqual(part.quantity_total, 1)
            self.assertFalse(part.nc1_eligible)
            self.assertFalse(result.production_export_allowed)
            session.project.validate()

    def test_ap242_occurrence_materialises_assembly_and_part_relation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_step_assembly_") as folder_name:
            source = Path(folder_name) / "assembly.step"
            source.write_text(ASSEMBLY_STEP, encoding="utf-8")
            session = ProjectSession.new("Assembly STEP")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            result = session.semantic_import_source(registration.source.source_id)
            self.assertEqual(result.strategy, "A_semantic_structure")
            self.assertEqual(result.entity_counts["assemblies"], 1)
            self.assertEqual(result.entity_counts["parts"], 1)
            assembly = next(iter(session.project.assemblies.values()))
            part = next(iter(session.project.parts.values()))
            self.assertEqual(assembly.name, "Frame assembly")
            self.assertEqual(part.name, "Plate occurrence")
            self.assertEqual(part.part_position, "P1")
            self.assertEqual(assembly.part_ids, [part.internal_id])
            self.assertEqual(part.assembly_ids, [assembly.internal_id])
            self.assertEqual(part.geometry_descriptor["solid_count"], 1)
            session.project.validate()

    def test_missing_solid_uses_strategy_c_without_inventing_geometry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_step_strategy_c_") as folder_name:
            source = Path(folder_name) / "ambiguous.step"
            source.write_text(NO_SOLID_STEP, encoding="utf-8")
            session = ProjectSession.new("Strategy C")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            result = session.semantic_import_source(registration.source.source_id)
            self.assertEqual(result.strategy, "C_fused_review")
            self.assertEqual(result.entity_counts["assemblies"], 0)
            self.assertEqual(result.entity_counts["parts"], 1)
            part = next(iter(session.project.parts.values()))
            self.assertEqual(part.part_type, "step_product_without_shape")
            self.assertEqual(part.geometry_descriptor["solid_count"], 0)
            self.assertEqual(part.properties["source_solid_count"], 0)
            self.assertTrue(result.evidence["ambiguous_geometry_review_required"])
            self.assertEqual(result.evidence["unshaped_product_count"], 1)
            self.assertTrue(any("geen betrouwbare BREP" in item for item in result.warnings))
            self.assertFalse(result.production_export_allowed)
            session.project.validate()

    def test_reimport_is_idempotent_and_keeps_stable_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_step_reimport_") as folder_name:
            source = Path(folder_name) / "single.step"
            source.write_text(SINGLE_STEP, encoding="utf-8")
            session = ProjectSession.new("Reimport")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            source_id = registration.source.source_id
            first = session.semantic_import_source(source_id)
            first_part = next(iter(session.project.parts.values()))
            snapshot = (
                first_part.internal_id,
                first_part.geometry_hash,
                first_part.manufacturing_hash,
            )
            second = session.semantic_import_source(source_id)
            second_part = next(iter(session.project.parts.values()))
            self.assertEqual(first.entity_counts, second.entity_counts)
            self.assertEqual(
                snapshot,
                (
                    second_part.internal_id,
                    second_part.geometry_hash,
                    second_part.manufacturing_hash,
                ),
            )
            self.assertEqual(len(session.project.parts), 1)
            session.project.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
