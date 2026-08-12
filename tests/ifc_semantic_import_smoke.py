from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession

IFC_FIXTURE = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('semantic.ifc','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCPROJECT('PROJECT',$,'Project',$,$,$,$,(),$);
#2=IFCSITE('SITE',$,'Site',$,$,#100,$,$,.ELEMENT.,$,$,$,$,$);
#3=IFCBUILDING('BUILDING',$,'Building',$,$,#100,$,$,.ELEMENT.,$,$,$);
#4=IFCBUILDINGSTOREY('STOREY',$,'Level 1',$,$,#100,$,$,.ELEMENT.,0.);
#10=IFCELEMENTASSEMBLY('ASSEMBLY',$,'Assembly',$,$,#100,$,'MLO4',.USERDEFINED.);
#11=IFCPLATE('PART',$,'Plate',$,'STRIP5*120',#100,$,'LO4');
#12=IFCMECHANICALFASTENER('BOLT',$,'Bolt',$,$,#100,$,'B1',14.,50.);
#13=IFCFASTENER('WELD',$,'Weld',$,$,#100,$,'W1');
#20=IFCPROPERTYSINGLEVALUE('Assembly/Cast unit Mark',$,IFCLABEL('MLO4'),$);
#21=IFCPROPERTYSINGLEVALUE('Assembly/Cast unit weight',$,IFCMASSMEASURE(0.62),$);
#22=IFCPROPERTYSET('PSET-A',$,'Tekla Assembly',$,(#20,#21));
#23=IFCRELDEFINESBYPROPERTIES('RPA',$,$,$,(#10),#22);
#30=IFCPROPERTYSINGLEVALUE('Part position number',$,IFCLABEL('LO4'),$);
#31=IFCPROPERTYSINGLEVALUE('Profile',$,IFCLABEL('STRIP5*120'),$);
#32=IFCPROPERTYSINGLEVALUE('MATERIAL',$,IFCLABEL('S235JR'),$);
#33=IFCPROPERTYSINGLEVALUE('Length',$,IFCLENGTHMEASURE(160.),$);
#34=IFCPROPERTYSINGLEVALUE('Weight',$,IFCMASSMEASURE(0.62),$);
#35=IFCPROPERTYSET('PSET-P',$,'Tekla Part',$,(#30,#31,#32,#33,#34));
#36=IFCRELDEFINESBYPROPERTIES('RPP',$,$,$,(#11),#35);
#40=IFCMATERIAL('S235JR');
#41=IFCRELASSOCIATESMATERIAL('RM',$,$,$,(#11),#40);
#50=IFCRELAGGREGATES('RP',$,$,$,#1,(#2));
#51=IFCRELAGGREGATES('RS',$,$,$,#2,(#3));
#52=IFCRELAGGREGATES('RB',$,$,$,#3,(#4));
#53=IFCRELCONTAINEDINSPATIALSTRUCTURE('RC',$,$,$,(#10),#4);
#54=IFCRELAGGREGATES('RA',$,$,$,#10,(#11,#12,#13));
#55=IFCRELCONNECTSWITHREALIZINGELEMENTS('RW',$,$,$,$,#11,#11,(#13),$);
#100=IFCLOCALPLACEMENT($,#101);
#101=IFCAXIS2PLACEMENT3D(#102,$,$);
#102=IFCCARTESIANPOINT((0.,0.,0.));
ENDSEC;
END-ISO-10303-21;
"""


class IFCSemanticImportTests(unittest.TestCase):
    def test_ifc_hierarchy_properties_fastener_and_weld_are_materialised(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_ifc_semantic_") as folder_name:
            source = Path(folder_name) / "semantic.ifc"
            source.write_text(IFC_FIXTURE, encoding="utf-8")
            session = ProjectSession.new("IFC semantic")
            registration = session.register_sources([source], include_step_geometry=False)[0]
            result = session.semantic_import_source(registration.source.source_id)
            self.assertEqual(result.strategy, "A_semantic_structure")
            self.assertEqual(
                result.entity_counts,
                {
                    "assemblies": 1,
                    "parts": 1,
                    "fasteners": 1,
                    "welds": 1,
                    "total_materialised": 4,
                },
            )
            assembly = next(iter(session.project.assemblies.values()))
            part = next(iter(session.project.parts.values()))
            fastener = next(iter(session.project.fasteners.values()))
            weld = next(iter(session.project.welds.values()))
            self.assertEqual(assembly.assembly_mark, "MLO4")
            self.assertEqual(part.part_position, "LO4")
            self.assertEqual(part.profile, "STRIP5*120")
            self.assertEqual(part.material, "S235JR")
            self.assertAlmostEqual(part.length_mm, 160.0)
            self.assertAlmostEqual(part.mass_each_kg, 0.62)
            self.assertEqual(assembly.part_ids, [part.internal_id])
            self.assertEqual(part.assembly_ids, [assembly.internal_id])
            self.assertEqual(assembly.fastener_ids, [fastener.internal_id])
            self.assertEqual(assembly.weld_ids, [weld.internal_id])
            self.assertAlmostEqual(fastener.diameter_mm, 14.0)
            self.assertEqual(weld.connected_part_ids, [part.internal_id])
            self.assertEqual(result.evidence["MLO4_assembly_count"], 1)
            self.assertEqual(len(result.evidence["MLO4_LO4_links"]), 1)
            self.assertEqual(result.evidence["bolt_or_hole_diameter_14_count"], 1)
            self.assertFalse(result.production_export_allowed)
            self.assertFalse(part.nc1_eligible)
            session.project.validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
