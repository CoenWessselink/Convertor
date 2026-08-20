from __future__ import annotations

from pathlib import Path

from cws_convertor.project.classification import normalize_material, normalize_profile
from cws_convertor.product import APP_VERSION


def test_catalog_normalization_is_canonical() -> None:
    assert normalize_profile("HEA-300") == "HEA300"
    assert normalize_profile("IPE 200") == "IPE200"
    assert normalize_material("steel/S355JR") == "S355JR"


def test_release_version_is_0103() -> None:
    assert APP_VERSION == "0.10.3-beta-dev"


def test_intake_recognizes_file_contents(tmp_path: Path) -> None:
    from cws_convertor.ui_qt.workspace_pages import IntakeDashboard

    pdf = tmp_path / "drawing.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    step = tmp_path / "part.step"
    step.write_bytes(b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\n")
    ifc = tmp_path / "model.ifc"
    ifc.write_bytes(b"ISO-10303-21;\nHEADER;\nFILE_SCHEMA(('IFC4'));\n")
    assert IntakeDashboard._inspect_format(pdf) == ("PDF", "PDF-document herkend", True)
    assert IntakeDashboard._inspect_format(step)[2] is True
    assert IntakeDashboard._inspect_format(ifc) == ("IFC", "IFC4", True)


def test_converter_exposes_pdf_routes() -> None:
    source = Path("cws_convertor/ui_qt/converter_panel.py").read_text(encoding="utf-8")
    assert "pdf_to_nc1" in source
    assert "pdf_to_step" in source
    assert "pdf_to_ifc" in source


def test_single_drawing_workspace_route() -> None:
    source = Path("cws_convertor/ui_qt/u4_shell.py").read_text(encoding="utf-8")
    assert '(self.drawings_page, "Tekeningen")' not in source
    assert '"drawings": "pdf"' in source
