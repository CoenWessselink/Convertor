from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.importers.p21 import P21Document, P21ParseError


def _document(line_id: int, point_id: int, direction_id: int, vector_id: int) -> str:
    return f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('hash.step','2026-01-01T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#{point_id}=CARTESIAN_POINT('',(0.,0.,0.));
#{direction_id}=DIRECTION('',(1.,0.,0.));
#{vector_id}=VECTOR('',#{direction_id},1.);
#{line_id}=LINE('',#{point_id},#{vector_id});
ENDSEC;
END-ISO-10303-21;
"""


class P21GraphTests(unittest.TestCase):
    def test_large_streaming_parse_can_be_cancelled_cooperatively(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_p21_cancel_") as folder_name:
            path = Path(folder_name) / "large.step"
            entities = "\n".join(
                f"#{index}=CARTESIAN_POINT('',({index}.0,0.,0.));"
                for index in range(1, 1201)
            )
            path.write_text(
                "ISO-10303-21;\nHEADER;\n"
                "FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));\n"
                "ENDSEC;\nDATA;\n"
                + entities
                + "\nENDSEC;\nEND-ISO-10303-21;\n",
                encoding="utf-8",
            )
            calls = 0

            def cancel() -> None:
                nonlocal calls
                calls += 1
                if calls >= 2:
                    raise RuntimeError("cancelled")

            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                P21Document.load(path, cancel_check=cancel)
            self.assertGreaterEqual(calls, 2)

    def test_semantic_hash_is_independent_from_numeric_entity_ids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_p21_") as folder_name:
            folder = Path(folder_name)
            first = folder / "first.step"
            second = folder / "second.step"
            first.write_text(_document(4, 1, 2, 3), encoding="utf-8")
            second.write_text(_document(904, 901, 902, 903), encoding="utf-8")
            left = P21Document.load(first)
            right = P21Document.load(second)
            self.assertEqual(left.schema, right.schema)
            self.assertEqual(
                left.combined_semantic_hash([4]),
                right.combined_semantic_hash([904]),
            )
            self.assertEqual(left.collect_graph([4]), {1, 2, 3, 4})
            self.assertEqual(right.collect_graph([904]), {901, 902, 903, 904})

    def test_changed_geometry_changes_semantic_hash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_p21_changed_") as folder_name:
            folder = Path(folder_name)
            first = folder / "first.step"
            second = folder / "second.step"
            first.write_text(_document(4, 1, 2, 3), encoding="utf-8")
            changed = _document(4, 1, 2, 3).replace("(1.,0.,0.)", "(0.,1.,0.)")
            second.write_text(changed, encoding="utf-8")
            left = P21Document.load(first)
            right = P21Document.load(second)
            self.assertNotEqual(
                left.combined_semantic_hash([4]),
                right.combined_semantic_hash([4]),
            )

    def test_duplicate_entity_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_p21_invalid_") as folder_name:
            path = Path(folder_name) / "duplicate.step"
            path.write_text(
                _document(4, 1, 2, 3).replace(
                    "#4=LINE('',#1,#3);",
                    "#4=LINE('',#1,#3);\n#4=LINE('',#1,#3);",
                ),
                encoding="utf-8",
            )
            with self.assertRaises(P21ParseError):
                P21Document.load(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
