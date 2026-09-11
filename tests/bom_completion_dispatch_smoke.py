from __future__ import annotations

"""Focused completion regressions for W03/W18 dispatcher semantics.

These tests deliberately use tiny fakes: they verify that the dispatcher does
not silently broaden scope or claim PASS when the existing canonical runtime
has no implementation. Full native behaviour remains covered by the Windows
installer acceptance suite.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from cws_convertor.ui_qt import bom_action_dispatch as dispatch


class _Text:
    def __init__(self, value: str = "") -> None:
        self.value = value
    def text(self) -> str:
        return self.value


class _Page:
    def __init__(self, root: Path) -> None:
        self._entity_id = "P1"
        self.status = _Text("ok")
        self.scale = SimpleNamespace(setFocus=lambda: None)
        self.format = SimpleNamespace(setFocus=lambda: None)
        self._root = root
    def set_context(self, workspace, selection) -> None:
        pass
    def _generate(self, *, make_png: bool, make_pdf: bool):
        pdf = self._root / "drawing.pdf" if make_pdf else None
        png = self._root / "drawing.png" if make_png else None
        if pdf:
            pdf.write_bytes(b"%PDF-1.4\n")
        if png:
            png.write_bytes(b"png")
        return SimpleNamespace(pdf_path=pdf, png_path=png, document=SimpleNamespace())


class _Router:
    def open_workspace(self, route: str) -> bool:
        return route in {"pdf", "plate_nesting", "profile_nesting"}


def test_drawing_print_generates_pdf_but_does_not_fake_headless_print() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        page = _Page(root)
        window = SimpleNamespace(
            pdf_page=page,
            workspace_router=_Router(),
            application_context=SimpleNamespace(selection=()),
        )
        project = SimpleNamespace(parts={"P1": object()}, assemblies={})
        panel = SimpleNamespace(window=window, _workspace=SimpleNamespace(project=project))
        before_headless = os.environ.get("CWS_HEADLESS_GUI_SMOKE")
        os.environ["CWS_HEADLESS_GUI_SMOKE"] = "1"
        try:
            outcome = dispatch._drawing(panel, "drawing.print", ("P1",), object())
        finally:
            if before_headless is None:
                os.environ.pop("CWS_HEADLESS_GUI_SMOKE", None)
            else:
                os.environ["CWS_HEADLESS_GUI_SMOKE"] = before_headless
        assert outcome.status == "prepared"
        assert len(outcome.outputs) == 1
        assert Path(outcome.outputs[0]).suffix.lower() == ".pdf"
        assert Path(outcome.outputs[0]).is_file()
        assert "printerdialoog" in outcome.message


def _nest_panel(*, plate: bool, page) -> tuple[SimpleNamespace, object, object]:
    project = SimpleNamespace(parts={"P1": SimpleNamespace(profile="PL10" if plate else "HEA180")})
    workspace = SimpleNamespace(project=project)
    window = SimpleNamespace(
        plate_nesting_page=page if plate else SimpleNamespace(),
        profiles_page=page if not plate else SimpleNamespace(),
        workspace_router=_Router(),
        application_context=SimpleNamespace(selection=()),
    )
    panel = SimpleNamespace(window=window, _workspace=workspace)
    module = __import__("cws_convertor.optimization.plate_nesting.project_service", fromlist=["is_plate"])
    old = module.is_plate
    module.is_plate = lambda part: plate
    return panel, module, old


def test_plate_compare_refuses_without_canonical_compare() -> None:
    page = SimpleNamespace(
        _job_id=None,
        set_context=lambda *args: None,
        scope_combo=SimpleNamespace(findData=lambda value: 0, setCurrentIndex=lambda value: None),
    )
    panel, module, old = _nest_panel(plate=True, page=page)
    try:
        try:
            dispatch._nesting(panel, "optimize.compare", ("P1",))
        except ValueError as exc:
            assert "nog niet aangesloten" in str(exc)
        else:
            raise AssertionError("plate compare must fail closed when no canonical compare exists")
    finally:
        module.is_plate = old


def test_profile_compare_uses_existing_phase3_action_and_reads_status() -> None:
    calls = []
    status = _Text("Scenariovergelijking gereed")
    page = SimpleNamespace(
        _job_id=None,
        set_context=lambda *args: None,
        scope_combo=SimpleNamespace(findData=lambda value: 0, setCurrentIndex=lambda value: None),
        _analyse=lambda: None,
        _phase3_action=lambda name: calls.append(name),
        phase3_nesting_status=status,
    )
    panel, module, old = _nest_panel(plate=False, page=page)
    try:
        outcome = dispatch._nesting(panel, "optimize.compare", ("P1",))
        assert outcome.status == "passed"
        assert calls == ["compare"]
        assert outcome.message == "Scenariovergelijking gereed"
    finally:
        module.is_plate = old


def test_profile_alternatives_remain_fail_closed_without_canonical_executor() -> None:
    page = SimpleNamespace(
        _job_id=None,
        set_context=lambda *args: None,
        scope_combo=SimpleNamespace(findData=lambda value: 0, setCurrentIndex=lambda value: None),
        _analyse=lambda: None,
    )
    panel, module, old = _nest_panel(plate=False, page=page)
    try:
        try:
            dispatch._nesting(panel, "optimize.alternatives", ("P1",))
        except ValueError as exc:
            assert "geen canonieke uitvoerder" in str(exc)
        else:
            raise AssertionError("alternatives must stay fail-closed until a canonical executor exists")
    finally:
        module.is_plate = old


if __name__ == "__main__":
    test_drawing_print_generates_pdf_but_does_not_fake_headless_print()
    test_plate_compare_refuses_without_canonical_compare()
    test_profile_compare_uses_existing_phase3_action_and_reads_status()
    test_profile_alternatives_remain_fail_closed_without_canonical_executor()
    print("PASS: BOM completion dispatcher keeps W03/W18 intent explicit")
