"""Native V3 regression proof for the existing production drawing workspace.

The geometric input is an explicitly synthetic two-member assembly. No render,
widget, save operation or input handler is replaced. Only the export directory
is redirected into the evidence folder. This is not visual acceptance against
an unavailable external specification or machine qualification.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


def assembly_workspace(session=None):
    import numpy as np
    from cws_convertor.project.service import ProjectSession
    from cws_convertor.project.model import Assembly, Part
    session = session or ProjectSession.new("V3 QA | synthetische assembly A1", created_by="v3-test")
    project = session.project
    if not project.parts:
        for key in ("P1", "P2"):
            part = Part(internal_id=key, part_position=key, name=key, material="S355JR", assembly_ids=["A1"], quantity_per_assembly={"A1": 1})
            part.recompute_hashes()
            project.add_entity(part)
        project.add_entity(Assembly(internal_id="A1", assembly_mark="A1", part_ids=["P1", "P2"], main_part_id="P1"))
    vertices = np.asarray(((0,0,0),(200,0,0),(200,60,0),(0,60,0),(0,0,12),(200,0,12),(200,60,12),(0,60,12)), dtype=float)
    triangles = np.asarray(((0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)), dtype=int)
    meshes = {key: SimpleNamespace(vertices=vertices.copy(), triangles=triangles.copy()) for key in ("P1", "P2")}
    nodes = {key: SimpleNamespace(geometry_id=key) for key in meshes}
    nodes["A1"] = SimpleNamespace(geometry_id=None)
    transforms = {}
    for key in nodes:
        matrix = np.eye(4)
        if key == "P2":
            matrix[0, 3] = 350.0
        transforms[key] = SimpleNamespace(to_rows=lambda matrix=matrix: matrix.tolist())
    return SimpleNamespace(project=project, session=session,
        interaction=SimpleNamespace(node_for_entity=lambda key: key),
        controller=SimpleNamespace(index=SimpleNamespace(node=lambda key: nodes[key], world_transform_by_node=transforms)),
        load_result=SimpleNamespace(repository=meshes))


def run_pdf_v3_completion_evidence(output: Path) -> dict:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtCore, QtWidgets, QtTest
    from cws_convertor.ui_qt.functional_workspaces import DrawingWorkspacePanel
    from cws_convertor.ui_qt.design_system.stylesheet import apply_v52_design_system
    from cws_convertor.project.service import ProjectSession
    from cws_convertor.ui_qt.runtime_typography import inspect_visible_text
    from cws_convertor.drawings import DrawingRole
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    apply_v52_design_system(app)
    host = QtWidgets.QMainWindow()
    host.setWindowTitle("CWS Convertor | bestaande PDF-werkplek | synthetische V3-regressie")
    host.resize(1680, 1120)
    panel = DrawingWorkspacePanel(host)
    panel._output_folder = lambda: output
    host.setCentralWidget(panel)
    host.show()
    checks, images = [], []
    def flush():
        for _ in range(3):
            app.processEvents()
    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append({"name": name, "status": "PASS"})
    def screenshot(name):
        flush()
        path = output / name
        glyphs = inspect_visible_text(host)
        check("actual visible text has no missing glyphs: " + name,
              glyphs["status"] == "passed" and glyphs["checked_glyphs"] > 0 and glyphs["missing_glyphs"] == 0)
        check("real Qt screenshot: " + name, host.grab().save(str(path), "PNG"))
        images.append({"file": name, "sha256": sha256(path.read_bytes()).hexdigest(), "origin": "QMainWindow.grab; existing DrawingWorkspacePanel", "glyph_evidence": glyphs})
    def click(control):
        position = QtCore.QPoint(9, control.height() // 2) if isinstance(control, QtWidgets.QCheckBox) else control.rect().center()
        QtTest.QTest.mouseClick(control, QtCore.Qt.MouseButton.LeftButton, pos=position)
        flush()
    def edit(field, value):
        control = panel.dimension_property_editors[field]
        control.setFocus()
        QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_A, QtCore.Qt.KeyboardModifier.ControlModifier)
        QtTest.QTest.keyClicks(control, value)
        QtTest.QTest.keyClick(control, QtCore.Qt.Key.Key_Return)
        flush()
    def dimension():
        return panel._dimension_document.dimensions[0]
    def normalized(value):
        # Project serialization canonicalizes floating point coordinates.
        if isinstance(value, float):
            return round(value, 9)
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [normalized(v) for v in value]
        return value
    workspace = assembly_workspace()
    try:
        panel.set_context(workspace, {"entity_id": "A1"})
        flush()
        check("assembly root without mesh stays selected", panel._entity_id == "A1" and panel._drawing_document.entity_id == "A1")
        refs = {ref for page in panel._drawing_document.pages for p in page.primitives for ref in p.refs}
        check("both separately transformed components rendered", {"entity:P1", "entity:P2"}.issubset(refs))
        check("assembly drawing type retained", panel._drawing_document.document_type == "assembly")
        check("synthetic mesh is not production release", panel._drawing_document.lint.get("release_ready") is not True)
        # Use physical Qt canvas clicks on two real geometric snap candidates.
        points = [c for c in panel._snap_candidates if c.valid and c.layer == "visible" and "front" in c.anchor.view_id and c.snap_type == "endpoint"]
        check("visible geometry snap candidates available", len(points) >= 2)
        first = min(points, key=lambda c: c.point[0])
        last = max(points, key=lambda c: c.point[0])
        check("distinct real projected geometry anchors", last.point[0] - first.point[0] > 30)
        click(panel.dimension_tool_buttons["horizontal"])
        for candidate in (first, last):
            point = panel.preview.sheet_to_widget(candidate.point).toPoint()
            QtTest.QTest.mouseMove(panel.preview, point)
            QtTest.QTest.mouseClick(panel.preview, QtCore.Qt.MouseButton.LeftButton, pos=point)
            flush()
        position = ((first.point[0] + last.point[0]) / 2, min(first.point[1], last.point[1]) - 14)
        QtTest.QTest.mouseClick(panel.preview, QtCore.Qt.MouseButton.LeftButton, pos=panel.preview.sheet_to_widget(position).toPoint())
        flush()
        check("three real canvas clicks create dimension", len(panel._dimension_document.dimensions) == 1)
        panel._dimension_model.select([dimension().dimension_id])
        panel.preview.set_selected_ids(panel._dimension_model.selected_ids)
        panel._update_dimension_properties()
        flush()
        nominal = dimension().nominal_value_mm
        anchor_records = [a.to_dict() for a in dimension().anchors]
        check("native inline prefix control enabled", isinstance(panel.dimension_property_editors["prefix"], QtWidgets.QLineEdit) and panel.dimension_property_editors["prefix"].isEnabled())
        edit("prefix", "QA ")
        check("keyboard edit committed directly without dialog", dimension().prefix == "QA ")
        edit("tolerance_upper_mm", "0,5")
        check("Dutch decimal tolerance accepted", dimension().tolerance_upper_mm == 0.5)
        click(panel.dimension_property_editors["inspection"])
        check("checkbox sets inspection property", dimension().inspection)
        check("display edits preserve authoritative nominal", dimension().nominal_value_mm == nominal)
        check("display edits preserve source anchors", normalized([a.to_dict() for a in dimension().anchors]) == normalized(anchor_records))
        screenshot("01-assembly-inline-properties.png")
        edit("tolerance_upper_mm", "nan")
        check("nonfinite tolerance refused", dimension().tolerance_upper_mm == 0.5)
        edit("label", "999")
        check("geometric text override without reason refused", dimension().label != "999")
        panel.dimension_property_editors["override_reason"].setText("V3 audit test - not approved for fabrication")
        edit("label", "QA 999")
        check("reasoned override records display text", dimension().label == "QA 999" and bool(dimension().override_reason))
        check("override does not change measured value", dimension().nominal_value_mm == nominal)
        check("drafter cannot auto-approve override", not dimension().override_approved_by)
        panel.preview.setFocus()
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Z, QtCore.Qt.KeyboardModifier.ControlModifier)
        flush()
        check("native Ctrl-Z restores previous display text", dimension().label != "QA 999")
        QtTest.QTest.keyClick(panel.preview, QtCore.Qt.Key.Key_Y, QtCore.Qt.KeyboardModifier.ControlModifier)
        flush()
        check("native Ctrl-Y restores audited override", dimension().label == "QA 999")
        panel.format.setCurrentText("A4")
        panel.scale.setCurrentText("1:1")
        flush()
        check("oversize fixed scale rejected visibly", "past niet" in panel.status.text())
        check("failed generation clears stale drawing", panel._drawing_document is None and panel._last_png is None)
        check("failed generation cannot show green linter", "geen gevalideerde" in panel.dimension_issue_summary.text())
        screenshot("02-fixed-scale-rejected.png")
        panel.scale.setCurrentText("1:10")
        flush()
        check("valid fixed scale not silently replaced", panel._drawing_document.scale_denominator == 10)
        panel._undo_dimensions()
        flush()
        check("undo restores rejected but exact prior sheet setting", panel.scale.currentText() == "1:1")
        panel._redo_dimensions()
        flush()
        check("redo restores fitting fixed scale", panel.scale.currentText() == "1:10")
        filename = workspace.session.save(output / "v3-native-proof.cwscproj", user="v3-test")
        expected = panel._dimension_document.to_dict()
        reopened = ProjectSession.open(filename)
        workspace2 = assembly_workspace(reopened)
        panel.set_context(workspace2, {"entity_id": "A1"})
        flush()
        check("real cwscproj reopened with persistent sheet format", panel.format.currentText() == "A4")
        check("real cwscproj reopened with exact fixed scale", panel.scale.currentText() == "1:10")
        check("reopen retains edits and audit", dimension().prefix == "QA " and dimension().label == "QA 999" and bool(panel._dimension_document.audit))
        check("reopen retains authoritative anchors", normalized([a.to_dict() for a in dimension().anchors]) == normalized(anchor_records))
        check("reopen retains lock version", panel._loaded_lock_version >= expected["lock_version"])
        panel._dimension_model.select([dimension().dimension_id]); panel._update_dimension_properties()
        screenshot("03-reopened-project.png")
        # Seed a locked revision as a negative-control fixture. Mesh review itself
        # may not be released; no release approval is fabricated by this test.
        panel._dimension_document.status = "released"
        check("locked revision fixture saved", panel._persist_dimension_editor("test.locked_revision_fixture"))
        before = panel._dimension_document.to_dict()
        panel._update_dimension_properties()
        check("released inspector disabled", not panel.dimension_property_editors["prefix"].isEnabled())
        panel.format.setCurrentText("A0"); flush()
        check("released sheet settings cannot change", panel.format.currentText() == "A4")
        panel._undo_dimensions(); flush()
        check("released undo cannot fork or mutate", panel._dimension_document.to_dict() == before)
        panel.refresh_preview(); flush()
        check("released preview cannot rewrite revision", panel._dimension_document.to_dict() == before)
        screenshot("04-released-revision-locked.png")
        # READ_ONLY role applies independently of file/session permissions.
        panel._dimension_document.status = "draft"
        workspace2.project.settings["drawing_user_roles"] = {"v3-test": DrawingRole.READ_ONLY.value}
        panel._update_dimension_properties()
        check("read-only role disables native inspector", not panel.dimension_property_editors["prefix"].isEnabled())
        snapshot = panel._dimension_document.to_dict()
        panel._delete_selected_dimensions()
        check("read-only role blocks delete", panel._dimension_document.to_dict() == snapshot)
        # Restore a real draft from the package rather than inventing a release.
        panel.set_context(assembly_workspace(ProjectSession.open(filename)), {"entity_id": "A1"}); flush()
        result = panel._generate(make_png=True, make_pdf=True)
        check("actual renderer exports PDF for complete assembly", result is not None and result.pdf_path.is_file() and result.document.entity_id == "A1")
        check("override/review remains blocked from production", not result.release_ready)
        # Verify complete wrapped table IDs and real exported page output,
        # not merely the project-side numeric model or a mock preview.
        table_text = [(page, p) for page in result.document.pages for p in page.primitives
                      if p.kind == "text" and "schedule:" + p.layer in p.refs]
        fragments = [p.text for page, p in table_text if p.semantic_id == dimension().dimension_id
                     and abs(p.points[0][0] - 11.0) < 1e-6]
        check("wrapped PDF table retains complete dimension ID", "".join(fragments) == dimension().dimension_id)
        fits = bool(table_text)
        for page, primitive in table_text:
            half = page.width_mm * 0.5
            left, right = (10.0, half - 4.0) if primitive.layer == "dimensions" else (half + 4.0, page.width_mm - 10.0)
            width = right - left
            edges = (left, left + width * .28, left + width * .70, right)
            x, y = primitive.points[0]
            column = min(range(3), key=lambda i: abs(x - edges[i] - 1.0))
            fits = fits and primitive.bounds()[2] <= edges[column + 1] - 1.0 + 1e-9 and y <= page.height_mm - 42.0
        check("PDF table text stays inside its columns and page", fits)
        from cws_convertor.drawings import ProductionDrawingRenderer
        rendered_table = ProductionDrawingRenderer.render_png(result.pdf_path, output / "05-exported-pdf-table.png", page_number=1)
        check("real exported PDF table raster available", rendered_table.is_file() and rendered_table.stat().st_size > 1024)
        pdf_renders = [{"file": rendered_table.name, "sha256": sha256(rendered_table.read_bytes()).hexdigest(),
                       "origin": "ProductionDrawingRenderer.render_png; actual exported PDF page 2, not a UI mockup"}]
        if getattr(sys, "frozen", False):
            binding = json.loads((Path(sys.executable).parent / "BUILD_SOURCE.json").read_text(encoding="utf-8"))
            source = binding["source_commit"]
            tree = binding["source_tree"]
            dirty = False
        else:
            root = Path(__file__).resolve().parents[2]
            source = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=root, text=True).strip()
            dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True).strip())
        report = {"schema": "cws-pdf-v3-native-proof-1.0", "status": "PASS", "source_commit": source,
            "source_tree": tree, "source_dirty": dirty, "frozen": bool(getattr(sys, "frozen", False)),
            "executable_sha256": sha256(Path(sys.executable).read_bytes()).hexdigest(),
            "checks": checks, "screenshots": images, "pdf_renders": pdf_renders, "production_release_allowed": False,
            "scope": "Existing DrawingWorkspacePanel, native Qt input, synthetic two-component geometry, real project save/reopen and PDF render",
            "external_v3_specification_verified": False,
            "limitations": ["Original V3 ZIP and reference images unavailable; no claim of full V3 visual conformity", "Synthetic geometry is review-only; not machine qualification"]}
        (output / "V3_NATIVE_EVIDENCE.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    finally:
        host.close()
        host.deleteLater()
        flush()
