from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.importers.source_material_evidence import (
    SourceTextEvidence,
    analyze_source_material_document,
    collect_material_candidate_evidence,
    confirm_material_candidate_evidence,
    dxf_material_records,
)
from material_database import MaterialDatabase


def record(text: str, kind: str = "vector_text", field: str = "") -> SourceTextEvidence:
    return SourceTextEvidence(
        text=text, source_format="PDF", source_kind=kind,
        source_reference=f"drawing.pdf:page:2:{text}", confidence=0.99,
        page=2, bbox=(10, 20, 100, 40), field_name=field,
    )


def ascii_dxf(*entities: tuple[str, list[tuple[int, str]]]) -> str:
    rows = ["0", "SECTION", "2", "ENTITIES"]
    for kind, fields in entities:
        rows.extend(["0", kind])
        for code, value in fields:
            rows.extend([str(code), value])
    return "\n".join(rows + ["0", "ENDSEC", "0", "EOF"]) + "\n"


class SourceMaterialCandidateTests(unittest.TestCase):
    def test_catalog_coverage_requires_confirmation_and_preserves_location(self) -> None:
        for material in MaterialDatabase().materials:
            with self.subTest(material=material.code):
                evidence = collect_material_candidate_evidence([record(material.code)])
                self.assertEqual(evidence.selected_value, material.code)
                self.assertEqual(evidence.status, "candidate")
                self.assertLess(evidence.confidence, 0.95)
                self.assertFalse(evidence.material_grade_proven)
                self.assertEqual(evidence.review_status, "review_required")
                self.assertEqual(evidence.candidates[0].page, 2)
                self.assertEqual(evidence.candidates[0].bbox, (10, 20, 100, 40))

    def test_aliases_merge_and_conflicting_materials_clear_selection(self) -> None:
        alias = collect_material_candidate_evidence([record("PA6"), record("ERTALON6PLA")])
        self.assertEqual(alias.status, "candidate")
        self.assertEqual(alias.selected_value, "PA6")
        conflict = collect_material_candidate_evidence([record("S355JR"), record("S235JR")])
        self.assertEqual(conflict.status, "conflict")
        self.assertEqual(conflict.selected_value, "")
        self.assertFalse(conflict.material_grade_proven)

    def test_unknown_value_and_missing_evidence_have_no_default(self) -> None:
        for records in [[], [record("Unknown alloy 42", field="material")]]:
            result = collect_material_candidate_evidence(records)
            self.assertEqual(result.status, "unresolved")
            self.assertEqual(result.selected_value, "")
            self.assertEqual(result.confidence, 0.0)

    def test_geometry_and_colour_are_prohibited_evidence(self) -> None:
        result = collect_material_candidate_evidence([
            record("S355JR", "extrusion_geometry"),
            record("S355JR", "rgb_color"),
            record("S355JR", "attribute", "material_color"),
        ])
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(len(result.ignored_sources), 3)

    def test_profile_row_keeps_full_unknown_grade_without_prefix_guess(self) -> None:
        result = collect_material_candidate_evidence([record("IPE200 S355J2UNKNOWN 3000 2 A1")])
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.candidates[0].raw_value, "S355J2UNKNOWN")

    def test_dimension_like_number_in_profile_row_is_not_fastener_grade(self) -> None:
        result = collect_material_candidate_evidence([record("IPE200 8.8 3000")])
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.candidates, ())

    def test_explicit_labels_cover_multiple_families(self) -> None:
        for value in ["C24", "C30/37", "1.4404", "8.8", "ERTALON6PLA", "EN AW-6082-T6"]:
            with self.subTest(value=value):
                result = collect_material_candidate_evidence([record(f"Materiaal: {value}")])
                self.assertEqual(result.status, "candidate")

    def test_human_confirmation_preserves_conflict_evidence_and_reviewer(self) -> None:
        conflict = collect_material_candidate_evidence([record("S355JR"), record("S235JR")]).to_dict()
        confirmed = confirm_material_candidate_evidence(conflict, "S355JR", reviewer="engineer", reviewed_at="2026-09-08")
        self.assertEqual(confirmed["source_status"], "conflict")
        self.assertEqual(confirmed["status"], "human_confirmed")
        self.assertEqual(confirmed["candidates"], conflict["candidates"])
        self.assertEqual(confirmed["human_confirmation"]["reviewer"], "engineer")
        self.assertEqual(conflict["status"], "conflict")
        self.assertTrue(confirmed["material_grade_proven"])

    def test_confirmation_requires_known_material_and_reviewer(self) -> None:
        with self.assertRaises(ValueError):
            confirm_material_candidate_evidence({}, "Unknown alloy", reviewer="engineer", reviewed_at="2026-09-08")
        with self.assertRaises(ValueError):
            confirm_material_candidate_evidence({}, "S355JR", reviewer="", reviewed_at="2026-09-08")


class SourceMaterialDocumentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="cws_material_documents_")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_real_ascii_dxf_attribute_and_layer_candidates_with_hash(self) -> None:
        path = self.root / "plate.dxf"
        path.write_text(ascii_dxf(
            ("ATTRIB", [(5, "A1"), (2, "MATERIAL"), (1, "S355JR")]),
            ("LINE", [(5, "A2"), (8, "MAT_S355JR"), (62, "1")]),
        ), encoding="utf-8")
        result = analyze_source_material_document(path)
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["selected_value"], "S355JR")
        self.assertEqual(result["extraction_status"], "complete")
        self.assertEqual(result["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(result["scope"], "document_unassigned")
        self.assertTrue(result["part_assignment_required"])
        self.assertFalse(result["production_export_allowed"])
        self.assertTrue(any("ATTRIB:A1" in row["source_reference"] for row in result["candidates"]))
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_auxiliary_evidence_survives_real_project_save_reopen(self) -> None:
        from cws_convertor.project.service import ProjectSession
        source = self.root / "part.dxf"
        source.write_text(ascii_dxf(("TEXT", [(5, "11"), (1, "Materiaal: S355JR")])), encoding="utf-8")
        records = [{"source": str(source), "material_candidate_evidence": analyze_source_material_document(source)}]
        project_path = self.root / "proof.cwscproj"
        with ProjectSession.new("Materiaalbewijs") as session:
            session.project.settings["auxiliary_document_evidence"] = records
            session.save(project_path, create_backup=False)
        with ProjectSession.open(project_path) as reopened:
            self.assertEqual(reopened.project.settings["auxiliary_document_evidence"], records)
            self.assertEqual(len(reopened.project.parts), 0)

    def test_real_ascii_dxf_conflict_does_not_choose_first_grade(self) -> None:
        path = self.root / "conflict.dxf"
        path.write_text(ascii_dxf(
            ("TEXT", [(5, "11"), (1, "Materiaal: S235JR")]),
            ("MTEXT", [(5, "12"), (3, "{\\H1.0;Materiaal: "), (1, "S355JR}")]),
        ), encoding="utf-8")
        result = analyze_source_material_document(path)
        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["selected_value"], "")
        self.assertEqual(len(result["candidates"]), 2)

    def test_dxf_attdef_prompt_is_not_part_of_default_value(self) -> None:
        path = self.root / "attribute.dxf"
        path.write_text(ascii_dxf(("ATTDEF", [(2, "MATERIAL"), (3, "Enter grade"), (1, "S355JR")])), encoding="utf-8")
        self.assertEqual(analyze_source_material_document(path)["selected_value"], "S355JR")

    def test_geometry_only_dxf_has_no_material(self) -> None:
        path = self.root / "geometry.dxf"
        path.write_text(ascii_dxf(("LINE", [(5, "11"), (8, "0"), (62, "355"), (10, "8.8"), (20, "0")])), encoding="utf-8")
        result = analyze_source_material_document(path)
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["selected_value"], "")

    def test_binary_and_malformed_dxf_fail_closed(self) -> None:
        for name, contents in [("binary.dxf", b"AutoCAD Binary DXF\r\n\x1a\x00"), ("bad.dxf", b"0\nTEXT\n1\nS355JR\n")]:
            path = self.root / name
            path.write_bytes(contents)
            result = analyze_source_material_document(path)
            self.assertEqual(result["extraction_status"], "failed")
            self.assertEqual(result["status"], "unresolved")
            self.assertTrue(result["extraction_error"])

    @unittest.skipUnless(importlib.util.find_spec("pymupdf"), "PyMuPDF runtime missing")
    def test_real_pdf_text_is_extracted_with_page_bbox_and_conflict(self) -> None:
        import pymupdf
        path = self.root / "drawing.pdf"
        with pymupdf.open() as document:
            first = document.new_page()
            first.insert_text((20, 40), "Materiaal: S355JR")
            second = document.new_page()
            second.insert_text((20, 40), "Materiaal: S235JR")
            document.save(path)
        result = analyze_source_material_document(path)
        self.assertEqual(result["extraction_status"], "complete")
        self.assertEqual(result["status"], "conflict")
        self.assertEqual({row["page"] for row in result["candidates"]}, {1, 2})
        self.assertTrue(all(len(row["bbox"]) == 4 for row in result["candidates"]))
        self.assertEqual(result["selected_value"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
