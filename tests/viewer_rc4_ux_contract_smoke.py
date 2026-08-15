from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import tempfile

from cws_viewer.model_grids import extract_project_model_grids
from cws_viewer.ui_qt.design_system import CWS_LIGHT, DEFAULT_THEME_KEY, LIGHT_QSS


def test_light_theme_is_product_default() -> None:
    assert DEFAULT_THEME_KEY == "cws_light"
    assert CWS_LIGHT.panel.lower() == "#ffffff"
    assert "QToolBar" in LIGHT_QSS and "QDockWidget" in LIGHT_QSS


def test_cockpit_and_navigation_sources_expose_required_controls() -> None:
    root = Path(__file__).resolve().parents[1]
    cockpit = (root / "cws_viewer" / "ui_qt" / "cockpit.py").read_text(encoding="utf-8")
    widget = (root / "cws_viewer" / "ui_qt" / "vtk_real_project_widget.py").read_text(encoding="utf-8")
    tools = (root / "cws_convertor" / "ui_qt" / "viewer_tools.py").read_text(encoding="utf-8")
    for token in (
        "Rotate", "Pan", "Walk", "Look", "Stamien", "Meten", "Doorsnede",
        "Explode", "Modelkleur", "Thema", "Volledig scherm",
    ):
        assert token in cockpit, token
    for token in (
        "Ctrl+U", "Ctrl+I", "Ctrl+O", "Ctrl+P", "Backspace", "Key_F11",
        "set_model_grids", "set_grid_level_visible", "select_rectangle",
    ):
        assert token in widget, token
    for token in (
        "Afstand", "Horizontaal", "Verticaal", "XYZ", "Clipping box",
        "Explode selectie", "Werkruimte opslaan",
    ):
        assert token in tools, token


def test_ifc_grid_axis_extraction() -> None:
    import ifcopenshell
    import ifcopenshell.guid

    with tempfile.TemporaryDirectory(prefix="cws-grid-smoke-") as temp:
        path = Path(temp) / "grid.ifc"
        model = ifcopenshell.file(schema="IFC4")
        p00 = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0))
        p10 = model.create_entity("IfcCartesianPoint", Coordinates=(10000.0, 0.0))
        p01 = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 8000.0))
        u_curve = model.create_entity("IfcPolyline", Points=(p00, p10))
        v_curve = model.create_entity("IfcPolyline", Points=(p00, p01))
        u_axis = model.create_entity("IfcGridAxis", AxisTag="A", AxisCurve=u_curve, SameSense=True)
        v_axis = model.create_entity("IfcGridAxis", AxisTag="1", AxisCurve=v_curve, SameSense=True)
        origin = model.create_entity("IfcCartesianPoint", Coordinates=(0.0, 0.0, 0.0))
        placement3d = model.create_entity("IfcAxis2Placement3D", Location=origin)
        local = model.create_entity("IfcLocalPlacement", RelativePlacement=placement3d)
        model.create_entity(
            "IfcGrid",
            GlobalId=ifcopenshell.guid.new(),
            Name="CWS Grid",
            ObjectPlacement=local,
            UAxes=(u_axis,),
            VAxes=(v_axis,),
            WAxes=(),
        )
        model.write(str(path))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        source = SimpleNamespace(
            source_id="source:grid",
            file_name=path.name,
            source_format="IFC",
            sha256=digest,
            size_bytes=path.stat().st_size,
            original_path=str(path),
            embedded_path="",
        )
        project = SimpleNamespace(sources={"source:grid": source})
        catalog = extract_project_model_grids(
            project,
            project_package_path=Path(temp) / "unused.cwscproj",
        )
        assert catalog.axis_count == 2, catalog
        assert catalog.levels == (0.0,), catalog.levels
        assert {axis.axis_tag for axis in catalog.axes} == {"A", "1"}
        assert catalog.default_visible_levels == (0.0,)


if __name__ == "__main__":
    test_light_theme_is_product_default()
    test_cockpit_and_navigation_sources_expose_required_controls()
    test_ifc_grid_axis_extraction()
    print("viewer_rc4_ux_contract_smoke: PASS")
