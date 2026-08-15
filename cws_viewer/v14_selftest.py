"""Headless V14 contract smoke used in source and frozen Windows gates."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile

from cws_convertor.importers.p21 import P21Document
from cws_convertor.importers.ifc_grid import extract_ifc_grid_catalog_from_document
from cws_viewer.contracts.enums import BackgroundTheme, RenderMode
from cws_viewer.contracts.state import ViewerDisplayPreferences
from cws_viewer.review import MarkupKind, MarkupRecord, ReviewIssue, ReviewPackageBuilder, ReviewPackageVerifier
from cws_viewer.ui_qt.design_system import DEFAULT_THEME, THEMES, theme_qss


_GRID_IFC = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('grid.ifc','2026-08-15T00:00:00',('CWS'),('CWS'),'CWS','CWS','');
FILE_SCHEMA(('IFC2X3'));
ENDSEC;
DATA;
#1=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#10=IFCCARTESIANPOINT((0.,0.,3800.));
#11=IFCDIRECTION((0.,0.,1.));
#12=IFCDIRECTION((1.,0.,0.));
#13=IFCAXIS2PLACEMENT3D(#10,#11,#12);
#14=IFCLOCALPLACEMENT($,#13);
#20=IFCCARTESIANPOINT((0.,0.));
#21=IFCCARTESIANPOINT((10000.,0.));
#22=IFCPOLYLINE((#20,#21));
#23=IFCGRIDAXIS('1',#22,.T.);
#30=IFCCARTESIANPOINT((0.,0.));
#31=IFCCARTESIANPOINT((0.,8000.));
#32=IFCPOLYLINE((#30,#31));
#33=IFCGRIDAXIS('A',#32,.T.);
#40=IFCGRID('0123456789012345678901',$,'+3800',$,$,#14,$,(#23),(#33),());
ENDSEC;
END-ISO-10303-21;
"""


def run_v14_selftest() -> dict:
    prefs = ViewerDisplayPreferences()
    assert prefs.background_theme == BackgroundTheme.LIGHT
    assert prefs.render_mode == RenderMode.SHADED_EDGES
    assert DEFAULT_THEME in THEMES
    qss = theme_qss(DEFAULT_THEME)
    assert "QToolBar" in qss and "QTreeWidget" in qss and "QTableView" in qss

    # Import the actual shipped cockpit/backend/controller; this catches missing
    # V14 composition modules in PyInstaller before a physical user opens a file.
    from cws_viewer.ui_qt.cockpit import CwsViewerCockpitWindow  # noqa: F401
    from cws_viewer.backends.vtk_project_mesh_v14 import VtkProjectMeshV14Backend  # noqa: F401
    from cws_viewer.core.v14_controller import V14ViewerCoreController  # noqa: F401

    with tempfile.TemporaryDirectory(prefix="cws-v14-selftest-") as temp:
        root = Path(temp)
        ifc = root / "grid.ifc"
        ifc.write_text(_GRID_IFC, encoding="ascii")
        document = P21Document.load(ifc)
        grid = extract_ifc_grid_catalog_from_document(document, source_id="source:test")
        assert grid["grid_count"] == 1
        assert grid["axis_count"] == 2
        assert grid["grids"][0]["name"] == "+3800"
        assert abs(float(grid["grids"][0]["elevation_mm"]) - 3800.0) < 1e-9
        assert {axis["tag"] for axis in grid["grids"][0]["axes"]} == {"1", "A"}

        markup = MarkupRecord.create(MarkupKind.TEXT, text="Controle", world_points_mm=((1.0,2.0,3.0),))
        issue = ReviewIssue.create("Controlepunt", linked_entity_ids=("part:1",), markup_ids=(markup.markup_id,))
        package = root / "review.cwsreview"
        ReviewPackageBuilder().build(
            package,
            project={"project_id":"project:test","revision_id":"rev:test"},
            issues=(issue,), markups=(markup,),
        )
        manifest = ReviewPackageVerifier().verify(package)
        assert manifest["project_id"] == "project:test"
        assert manifest["counts"]["issues"] == 1
        package_sha = sha256(package.read_bytes()).hexdigest()

    return {
        "schema": "cws-viewer-v14-selftest-1.0",
        "status": "passed",
        "default_theme": DEFAULT_THEME,
        "available_themes": sorted(THEMES),
        "default_background": prefs.background_theme.value,
        "default_render_mode": prefs.render_mode.value if prefs.render_mode else None,
        "grid_count": grid["grid_count"],
        "grid_axis_count": grid["axis_count"],
        "review_package_sha256": package_sha,
        "cockpit_imported": True,
        "surface_backend_imported": True,
        "v14_controller_imported": True,
    }


def main() -> int:
    print(json.dumps(run_v14_selftest(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
