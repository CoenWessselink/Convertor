from __future__ import annotations

from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_model import CanonicalPart
from ifc_native import parse_native_ifc_meshes, write_native_ifc


class NativeIFCMaterialBindingTests(unittest.TestCase):
    def test_writer_omits_unknown_material_and_does_not_label_aluminium_steel(self):
        # Serializer unit test with explicit mesh input, not CAD fidelity proof.
        shape = SimpleNamespace(BoundingBox=lambda: SimpleNamespace(xlen=100, ylen=50, zlen=10))
        mesh = [(shape, np.array([[0., 0., 0.], [100., 0., 0.], [0., 50., 0.]]), np.array([[0, 1, 2]]))]
        with tempfile.TemporaryDirectory(prefix="cws-ifc-material-") as folder:
            target = Path(folder) / "test.ifc"
            with patch("ifc_native._solid_meshes", return_value=mesh):
                for material in ("", "6082-T6", "DUMMY"):
                    canonical = CanonicalPart(part_id="p1")
                    canonical.header.material = material
                    write_native_ifc(shape, target, name="unit-test", material=material, canonical=canonical)
                    text = target.read_text()
                    self.assertNotIn(",$,'Steel')", text)
                    self.assertEqual("=IFCMATERIAL(" in text, bool(material))
                    self.assertEqual("=IFCRELASSOCIATESMATERIAL(" in text, bool(material))
                    meshes = parse_native_ifc_meshes(target)
                    self.assertEqual(meshes[0].material, material)
                    if material == "6082-T6":
                        self.assertIn("'Aluminium'", text)
                canonical = CanonicalPart(part_id="conflict")
                canonical.header.material = "S355JR"
                with self.assertRaisesRegex(ValueError, "conflicteert"):
                    write_native_ifc(shape, target, name="conflict", material="S235JR", canonical=canonical)

    def test_parser_binds_each_material_and_does_not_use_first_declaration(self):
        data = """ISO-10303-21;
DATA;
#1=IFCCARTESIANPOINTLIST3D(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)));
#2=IFCTRIANGULATEDFACESET(#1,$,.T.,((1,2,3)),$);
#3=IFCSHAPEREPRESENTATION($,'Body','Tessellation',(#2));
#4=IFCPRODUCTDEFINITIONSHAPE($,$,(#3));
#5=IFCPLATE('A',$,'A',$,$,$,#4,$,.NOTDEFINED.);
#6=IFCPLATE('B',$,'B',$,$,$,#4,$,.NOTDEFINED.);
#7=IFCPLATE('C',$,'C',$,$,$,#4,$,.NOTDEFINED.);
#8=IFCPLATE('D',$,'D',$,$,$,#4,$,.NOTDEFINED.);
#10=IFCMATERIAL('S355JR',$,'steel');
#11=IFCMATERIAL('6082-T6',$,'aluminium');
#12=IFCRELASSOCIATESMATERIAL('R1',$,$,$,(#5,#8),#10);
#13=IFCRELASSOCIATESMATERIAL('R2',$,$,$,(#6,#8),#11);
ENDSEC;
END-ISO-10303-21;
"""
        with tempfile.TemporaryDirectory(prefix="cws-ifc-binding-") as folder:
            path = Path(folder) / "input.ifc"
            path.write_text(data)
            actual = {mesh.name: mesh.material for mesh in parse_native_ifc_meshes(path)}
        self.assertEqual(actual, {"A": "S355JR", "B": "6082-T6", "C": "", "D": ""})


if __name__ == "__main__":
    unittest.main(verbosity=2)
