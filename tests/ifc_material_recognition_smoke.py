from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import ProjectSession
from cws_convertor.project.classification import (
    fastener_grade_candidates,
    normalize_fastener_grade,
    normalize_profile,
)


def _ifc(schema: str, data: str) -> str:
    return f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('recognition.ifc','2026-09-07T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('{schema}'));
ENDSEC;
DATA;
#1=IFCPROJECT('PROJECT',$,'Recognition',$,$,$,$,(),$);
{data.strip()}
ENDSEC;
END-ISO-10303-21;
"""


def _import_fixture(schema: str, data: str) -> ProjectSession:
    with tempfile.TemporaryDirectory(prefix="cws_ifc_recognition_") as folder_name:
        source = Path(folder_name) / "recognition.ifc"
        source.write_text(_ifc(schema, data), encoding="utf-8")
        session = ProjectSession.new("IFC recognition")
        registration = session.register_sources([source], include_step_geometry=False)[0]
        session.semantic_import_source(registration.source.source_id)
        return session


class IFCMaterialRecognitionTests(unittest.TestCase):
    def test_ifc4_tapering_preserves_both_profile_sets_and_conflict(self) -> None:
        session = _import_fixture("IFC4", """
#10=IFCBEAM('TAPER',$,'Taper',$,$,$,$,'T1',.BEAM.);
#30=IFCMATERIAL('S355JR',$,'steel');
#31=IFCMATERIAL('S235JR',$,'steel');
#32=IFCRECTANGLEPROFILEDEF(.AREA.,'Start',$,100.,200.);
#33=IFCRECTANGLEPROFILEDEF(.AREA.,'End',$,100.,100.);
#34=IFCMATERIALPROFILE('Start',$,#30,#32,$,$);
#35=IFCMATERIALPROFILE('End',$,#31,#33,$,$);
#36=IFCMATERIALPROFILESET('Start',$,(#34),$);
#37=IFCMATERIALPROFILESET('End',$,(#35),$);
#38=IFCMATERIALPROFILESETUSAGETAPERING(#36,5,6000.,#37,8);
#39=IFCRELASSOCIATESMATERIAL('REL',$,$,$,(#10),#38);
""")
        part = next(iter(session.project.parts.values()))
        self.assertEqual(part.properties["ifc_materials"], ["S355JR", "S235JR"])
        records = part.properties["ifc_material_semantics"]
        self.assertEqual([(item["tapering_end"], item["cardinal_point"]) for item in records], [("start", 5), ("end", 8)])
        self.assertEqual(part.material, "")
        self.assertTrue(any(issue.blocking and "AMBIGUOUS" in issue.code for issue in part.validation_issues))

    def test_layer_with_offsets_retains_thickness_and_role(self) -> None:
        session = _import_fixture("IFC4", """
#10=IFCPLATE('OFFSET',$,'Offset layer',$,$,$,$,'O1',.NOTDEFINED.);
#30=IFCMATERIAL('S355JR',$,'steel');
#31=IFCMATERIALLAYERWITHOFFSETS(#30,10.,.F.,'Core',$,'LoadBearing',80,.AXIS3.,(2.,3.));
#32=IFCMATERIALLAYERSET((#31),'Offset set',$);
#33=IFCRELASSOCIATESMATERIAL('REL',$,$,$,(#10),#32);
""")
        part = next(iter(session.project.parts.values()))
        component = part.properties["ifc_material_associations"][0]["components"][0]
        self.assertEqual(component["thickness_mm"], 10.0)
        self.assertEqual(component["category"], "LoadBearing")
        self.assertEqual(component["offset_values_mm"], [2.0, 3.0])

    def test_material_alias_is_not_false_conflict_but_duplicate_grades_are(self) -> None:
        session = _import_fixture("IFC4", """
#10=IFCBEAM('ALIAS',$,'Alias',$,$,$,$,'A1',.BEAM.);
#11=IFCBEAM('CONFLICT',$,'Conflict',$,$,$,$,'A2',.BEAM.);
#20=IFCPROPERTYSINGLEVALUE('Material',$,IFCLABEL('1.0045'),$);
#21=IFCPROPERTYSET('P1',$,'Material data',$,(#20));
#22=IFCRELDEFINESBYPROPERTIES('RP1',$,$,$,(#10),#21);
#23=IFCPROPERTYSINGLEVALUE('Material',$,IFCLABEL('S235JR'),$);
#24=IFCPROPERTYSINGLEVALUE('Material',$,IFCLABEL('S355JR'),$);
#25=IFCPROPERTYSET('P2',$,'Conflicting data',$,(#23,#24));
#26=IFCRELDEFINESBYPROPERTIES('RP2',$,$,$,(#11),#25);
#30=IFCMATERIAL('S355JR',$,'steel');
#31=IFCRELASSOCIATESMATERIAL('RM',$,$,$,(#10),#30);
""")
        parts = {part.source_identity.global_id: part for part in session.project.parts.values()}
        self.assertEqual(parts["ALIAS"].normalized_material, "S355JR")
        self.assertFalse(any(issue.code == "CWS-IFC-MATERIAL-CONFLICT" for issue in parts["ALIAS"].validation_issues))
        self.assertEqual(parts["CONFLICT"].material, "")
        self.assertEqual(len(parts["CONFLICT"].properties["ifc_material_resolution"]["property_evidence"]), 2)
        self.assertTrue(any(issue.code == "CWS-IFC-MATERIAL-CONFLICT" and issue.blocking for issue in parts["CONFLICT"].validation_issues))

    def test_exact_profile_aliases_and_fastener_tokens_fail_closed(self) -> None:
        expected = {
            "K60/4": "SHS60x60x4",
            "K120/80/4": "RHS120x80x4",
            "UNP160": "UPN160",
            "STRIP15*350": "FLAT350x15",
            "PL15*350": "FLAT350x15",
            "ROND6": "ROUND6",
        }
        for source, designation in expected.items():
            with self.subTest(source=source):
                self.assertEqual(normalize_profile(source), designation)
        self.assertEqual(normalize_profile("L200/15"), "L200/15")
        self.assertEqual(normalize_profile("R6"), "R6")
        self.assertEqual(normalize_profile("UNP160 extra"), "UNP160EXTRA")
        self.assertEqual(fastener_grade_candidates("4014-8.8"), ("8.8",))
        self.assertEqual(normalize_fastener_grade("STEEL/4.6"), "4.6")
        self.assertEqual(fastener_grade_candidates("18.8"), ())
        self.assertEqual(normalize_fastener_grade("8.8", "10.9"), "")

    def test_ifc4_type_material_and_pset_inheritance_with_occurrence_override(self) -> None:
        session = _import_fixture(
            "IFC4",
            """
#10=IFCBEAM('BEAM-A',$,'B-A',$,$,$,$,'A',.BEAM.);
#11=IFCBEAM('BEAM-B',$,'B-B',$,$,$,$,'B',.BEAM.);
#20=IFCPROPERTYSINGLEVALUE('Profile',$,IFCLABEL('HEA200'),$);
#21=IFCPROPERTYSET('PSET-T',$,'Type data',$,(#20));
#22=IFCBEAMTYPE('TYPE',$,'Beam type',$,$,(#21),(),$,$,.BEAM.);
#23=IFCRELDEFINESBYTYPE('RDT',$,$,$,(#10,#11),#22);
#24=IFCPROPERTYSINGLEVALUE('Profile',$,IFCLABEL('IPE200'),$);
#25=IFCPROPERTYSET('PSET-O',$,'Type data',$,(#24));
#26=IFCRELDEFINESBYPROPERTIES('RDP-O',$,$,$,(#11),#25);
#30=IFCMATERIAL('S355J2','Type steel','steel');
#31=IFCRELASSOCIATESMATERIAL('RAM-T',$,$,$,(#22),#30);
#32=IFCMATERIAL('S235JR','Occurrence steel','steel');
#33=IFCRELASSOCIATESMATERIAL('RAM-O',$,$,$,(#11),#32);
""",
        )
        parts = {
            item.source_identity.global_id: item
            for item in session.project.parts.values()
        }
        inherited = parts["BEAM-A"]
        overridden = parts["BEAM-B"]
        self.assertEqual(inherited.profile, "HEA200")
        self.assertEqual(inherited.material, "S355J2")
        self.assertEqual(inherited.properties["ifc_materials"], ["S355J2"])
        self.assertEqual(inherited.properties["ifc_type_entity_id"], "22")
        inherited_association = inherited.properties["ifc_material_associations"][0]
        self.assertEqual(inherited_association["scope"], "type")
        self.assertEqual(inherited_association["declared_on_entity_id"], "22")
        self.assertEqual(
            inherited.field_provenance["material"].method,
            "ifc_type_material_inheritance",
        )
        self.assertEqual(overridden.material, "S235JR")
        self.assertEqual(overridden.profile, "IPE200")
        self.assertEqual(overridden.properties["ifc_materials"], ["S235JR"])
        self.assertEqual(
            overridden.properties["ifc_material_associations"][0]["scope"],
            "occurrence",
        )
        self.assertEqual(len(overridden.properties["ifc_material_associations"]), 2)
        self.assertFalse(
            overridden.properties["ifc_material_associations"][1]["effective"]
        )

    def test_ifc4_material_profile_semantics_and_parametric_profile(self) -> None:
        session = _import_fixture(
            "IFC4",
            """
#10=IFCBEAM('BEAM-P',$,'Profile beam',$,$,$,#45,'P1',.BEAM.);
#30=IFCMATERIAL('S355J2','Hot rolled structural steel','steel');
#31=IFCISHAPEPROFILEDEF(.AREA.,'HEA200',$,200.,190.,6.5,10.,18.,$,$);
#32=IFCMATERIALPROFILE('Primary section','Main steel section',#30,#31,80,'LoadBearing');
#33=IFCMATERIALPROFILESET('HEA200 set','Profile set description',(#32),$);
#34=IFCMATERIALPROFILESETUSAGE(#33,5,6000.);
#35=IFCRELASSOCIATESMATERIAL('RAM-P',$,$,$,(#10),#34);
#40=IFCCARTESIANPOINT((0.,0.,0.));
#41=IFCDIRECTION((0.,0.,1.));
#42=IFCDIRECTION((1.,0.,0.));
#43=IFCAXIS2PLACEMENT3D(#40,#41,#42);
#44=IFCEXTRUDEDAREASOLID(#31,#43,#41,6000.);
#46=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-5,#43,$);
#47=IFCSHAPEREPRESENTATION(#46,'Body','SweptSolid',(#44));
#45=IFCPRODUCTDEFINITIONSHAPE($,$,(#47));
""",
        )
        part = next(iter(session.project.parts.values()))
        self.assertEqual(part.profile, "HEA200")
        self.assertEqual(part.material, "S355J2")
        self.assertEqual(part.properties["ifc_materials"], ["S355J2"])
        self.assertNotIn("Profile set description", part.properties["ifc_materials"])
        association = part.properties["ifc_material_associations"][0]
        self.assertEqual(association["kind"], "profile_set_usage")
        self.assertEqual(association["usage"]["cardinal_point"], 5.0)
        self.assertEqual(association["usage"]["reference_extent_mm"], 6000.0)
        component = association["components"][0]
        self.assertEqual(component["name"], "Primary section")
        self.assertEqual(component["category"], "LoadBearing")
        self.assertEqual(component["material"]["name"], "S355J2")
        descriptor = part.geometry_descriptor["profile_definitions"][0]
        self.assertEqual(descriptor["ifc_type"], "IFCISHAPEPROFILEDEF")
        self.assertEqual(descriptor["catalog_designation"], "HEA200")
        self.assertEqual(descriptor["parameters_mm"]["web_thickness"], 6.5)
        self.assertEqual(descriptor["parameters_mm"]["flange_thickness"], 10.0)

    def test_ifc4_layer_roles_preserve_all_materials_and_primary(self) -> None:
        session = _import_fixture(
            "IFC4",
            """
#10=IFCPLATE('PLATE-L',$,'Coated plate',$,$,$,$,'L1',.NOTDEFINED.);
#30=IFCMATERIAL('S355J2','Structural steel','steel');
#31=IFCMATERIAL('Z275','Zinc coating','zinc');
#32=IFCMATERIALLAYER(#30,5.,.F.,'Core','Structural plate','LoadBearing',80);
#33=IFCMATERIALLAYER(#31,0.02,.F.,'Coating','Hot-dip zinc','Finish',20);
#34=IFCMATERIALLAYERSET((#32,#33),'Coated plate set','Steel with zinc coating');
#35=IFCMATERIALLAYERSETUSAGE(#34,.AXIS3.,.POSITIVE.,-2.5,$);
#36=IFCRELASSOCIATESMATERIAL('RAM-L',$,$,$,(#10),#35);
""",
        )
        part = next(iter(session.project.parts.values()))
        self.assertEqual(part.material, "S355J2")
        self.assertEqual(part.properties["ifc_materials"], ["S355J2", "Z275"])
        association = part.properties["ifc_material_associations"][0]
        self.assertEqual(association["kind"], "layer_set_usage")
        self.assertEqual(association["set_name"], "Coated plate set")
        self.assertEqual(association["usage"]["offset_mm"], -2.5)
        self.assertEqual(
            [
                (
                    item["material"]["name"],
                    item["thickness_mm"],
                    item["category"],
                    item["priority"],
                )
                for item in association["components"]
            ],
            [
                ("S355J2", 5.0, "LoadBearing", 80.0),
                ("Z275", 0.02, "Finish", 20.0),
            ],
        )

    def test_ifc2x3_material_list_has_no_silent_primary(self) -> None:
        session = _import_fixture(
            "IFC2X3",
            """
#10=IFCPLATE('PLATE-M',$,'Multi material',$,$,$,$,'M1');
#30=IFCMATERIAL('S355J2');
#31=IFCMATERIAL('ZINC');
#32=IFCMATERIALLIST((#30,#31));
#33=IFCRELASSOCIATESMATERIAL('RAM-M',$,$,$,(#10),#32);
""",
        )
        part = next(iter(session.project.parts.values()))
        self.assertEqual(part.properties["ifc_materials"], ["S355J2", "ZINC"])
        self.assertEqual(part.material, "")
        self.assertEqual(part.material_grade, "")
        self.assertEqual(
            part.properties["ifc_material_associations"][0]["kind"],
            "material_list",
        )
        self.assertTrue(
            any(
                issue.code == "CWS-IFC-MATERIAL-PRIMARY-AMBIGUOUS"
                and issue.blocking
                for issue in part.validation_issues
            )
        )

    def test_ifc4_constituents_preserve_roles_and_fractions(self) -> None:
        session = _import_fixture(
            "IFC4",
            """
#10=IFCBUILDINGELEMENTPROXY('PANEL',$,'Sandwich panel',$,$,$,$,'P1',.ELEMENT.);
#30=IFCMATERIAL('S350GD','Steel facing','steel');
#31=IFCMATERIAL('PIR','Rigid foam','insulation');
#32=IFCMATERIALCONSTITUENT('Facing','Outer steel sheet',#30,0.15,'LoadBearing');
#33=IFCMATERIALCONSTITUENT('Core','Insulation core',#31,0.85,'Insulation');
#34=IFCMATERIALCONSTITUENTSET('Panel recipe','Two constituents',(#32,#33));
#35=IFCRELASSOCIATESMATERIAL('RAM-C',$,$,$,(#10),#34);
""",
        )
        part = next(iter(session.project.parts.values()))
        self.assertEqual(part.material, "S350GD")
        self.assertEqual(part.properties["ifc_materials"], ["S350GD", "PIR"])
        association = part.properties["ifc_material_associations"][0]
        self.assertEqual(association["kind"], "constituent_set")
        self.assertEqual(
            [
                (
                    item["name"],
                    item["material"]["name"],
                    item["fraction"],
                    item["category"],
                )
                for item in association["components"]
            ],
            [
                ("Facing", "S350GD", 0.15, "LoadBearing"),
                ("Core", "PIR", 0.85, "Insulation"),
            ],
        )

    def test_ifc2x3_fastener_grade_from_material_and_standard(self) -> None:
        session = _import_fixture(
            "IFC2X3",
            """
#10=IFCMECHANICALFASTENER('BOLT-A',$,'Bolt A',$,$,$,$,'B1',14.,50.);
#11=IFCMECHANICALFASTENER('BOLT-B',$,'Bolt B',$,$,$,$,'B2',16.,60.);
#12=IFCMECHANICALFASTENER('BOLT-C',$,'Bolt C',$,$,$,$,'B3',16.,60.);
#30=IFCMATERIAL('STEEL/8.8');
#31=IFCRELASSOCIATESMATERIAL('RAM-F',$,$,$,(#10,#12),#30);
#40=IFCPROPERTYSINGLEVALUE('Bolt standard',$,IFCLABEL('4014-8.8'),$);
#41=IFCPROPERTYSET('PSET-F',$,'Fastener data',$,(#40));
#42=IFCRELDEFINESBYPROPERTIES('RDP-F',$,$,$,(#11),#41);
#43=IFCPROPERTYSINGLEVALUE('Bolt grade',$,IFCLABEL('10.9'),$);
#44=IFCPROPERTYSET('PSET-C',$,'Conflicting data',$,(#43));
#45=IFCRELDEFINESBYPROPERTIES('RDP-C',$,$,$,(#12),#44);
""",
        )
        fasteners = {
            item.source_identity.global_id: item
            for item in session.project.fasteners.values()
        }
        self.assertEqual(fasteners["BOLT-A"].grade, "8.8")
        self.assertEqual(
            fasteners["BOLT-A"].field_provenance["grade"].source_path,
            "IfcRelAssociatesMaterial.RelatingMaterial.Name",
        )
        self.assertEqual(fasteners["BOLT-B"].standard, "4014-8.8")
        self.assertEqual(fasteners["BOLT-B"].grade, "8.8")
        self.assertEqual(
            fasteners["BOLT-B"].field_provenance["grade"].source_path,
            "Fastener data.Bolt standard",
        )
        self.assertEqual(fasteners["BOLT-C"].grade, "")
        self.assertTrue(
            any(
                issue.code == "CWS-IFC-FASTENER-GRADE-CONFLICT"
                for issue in fasteners["BOLT-C"].validation_issues
            )
        )

    def test_ifc4_non_catalog_parametric_profile_gets_stable_custom_descriptor(self) -> None:
        session = _import_fixture(
            "IFC4",
            """
#10=IFCBEAM('CUSTOM',$,'Custom RHS',$,$,$,#124,'C1',.BEAM.);
#90=IFCCARTESIANPOINT((0.,0.,0.));
#91=IFCDIRECTION((0.,0.,1.));
#92=IFCDIRECTION((1.,0.,0.));
#93=IFCAXIS2PLACEMENT3D(#90,#91,#92);
#94=IFCCARTESIANPOINT((0.,0.));
#95=IFCAXIS2PLACEMENT2D(#94,$);
#96=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-5,#93,$);
#120=IFCRECTANGLEHOLLOWPROFILEDEF(.AREA.,$,#95,77.,123.,4.3,6.,10.);
#121=IFCEXTRUDEDAREASOLID(#120,#93,#91,2400.);
#122=IFCSHAPEREPRESENTATION(#96,'Body','SweptSolid',(#121));
#124=IFCPRODUCTDEFINITIONSHAPE($,$,(#122));
""",
        )
        part = next(iter(session.project.parts.values()))
        self.assertTrue(part.profile.startswith("CUSTOM:IFCRECTANGLEHOLLOWPROFILEDEF"))
        self.assertEqual(part.normalized_profile, part.profile)
        self.assertLess(part.profile_confidence, 1.0)
        self.assertEqual(part.classification_status, "review_required")
        self.assertEqual(part.profile_type, "rhs")
        self.assertFalse(part.nc1_eligible)
        descriptor = part.geometry_descriptor["profile_definitions"][0]
        self.assertEqual(descriptor["resolution_status"], "custom_deterministic")
        self.assertEqual(descriptor["parameters_mm"]["width"], 77.0)
        self.assertEqual(descriptor["parameters_mm"]["depth"], 123.0)
        self.assertEqual(descriptor["parameters_mm"]["wall_thickness"], 4.3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
