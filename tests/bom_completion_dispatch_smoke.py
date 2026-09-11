from __future__ import annotations

"""Focused completion regressions for W03/W18 dispatcher semantics.

These tests deliberately use tiny fakes: they verify that the dispatcher does
not silently broaden scope or claim PASS when the existing canonical runtime
has no implementation. Full native behaviour remains covered by the Windows
installer acceptance suite.
"""

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
        self.printed = []
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
    def _print_pdf(self, path: str):
        self.printed.append(str(path))
        return True


class _Router:
    def open_workspace(self, route: str) -> bool:
        return route == "pdf"


def test_drawing_print_generates_pdf_before_native_print() -> None:
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
        outcome = dispatch._drawing(panel, "drawing.print", ("P1",), object())
        assert outcome.status == "passed"
        assert len(outcome.outputs) == 1
        assert Path(outcome.outputs[0]).suffix.lower() == ".pdf"
        assert page.printed == [outcome.outputs[0]]


def test_plate_compare_refuses_without_canonical_compare() -> None:
    page = SimpleNamespace(
        _job_id=None,
        set_context=lambda *args: None,
        scope_combo=SimpleNamespace(findData=lambda value: 0, setCurrentIndex=lambda value: None),
    )
    project = SimpleNamespace(parts={"P1": SimpleNamespace(profile="PL10")})
    workspace = SimpleNamespace(project=project)
    window = SimpleNamespace(
        plate_nesting_page=page,
        profiles_page=SimpleNamespace(),
        workspace_router=SimpleNamespace(open_workspace=lambda route: True),
        application_context=SimpleNamespace(selection=()),
    )
    panel = SimpleNamespace(window=window, _workspace=workspace)
    original = __import__("cws_convertor.optimization.plate_nesting.project_service", fromlist=["is_plate"])
    old = original.is_plate
    original.is_plate = lambda part: True
    try:
        try:
            dispatch._nesting(panel, "optimize.compare", ("P1",))
        except ValueError as exc:
            assert "nog niet aangesloten" in str(exc)
        else:
            raise AssertionError("plate compare must fail closed when no canonical compare exists")
    finally:
        original.is_plate = old


def test_profile_alternatives_use_existing_phase3_action() -> None:
    calls = []
    page = SimpleNamespace(
        _job_id=None,
        set_context=lambda *args: None,
        scope_combo=SimpleNamespace(findData=lambda value: 0, setCurrentIndex=lambda value: None),
        _analyse=lambda: None,
        _phase3_action=lambda name: calls.append(name),
    )
    project = SimpleNamespace(parts={"P1": SimpleNamespace(profile="HEA180")})
    workspace = SimpleNamespace(project=project)
    window = SimpleNamespace(
        plate_nesting_page=SimpleNamespace(),
        profiles_page=page,
        workspace_router=SimpleNamespace(open_workspace=lambda route: True),
        application_context=SimpleNamespace(selection=()),
    )
    panel = SimpleNamespace(window=window, _workspace=workspace)
    original = __import__("cws_convertor.optimization.plate_nesting.project_service", fromlist=["is_plate"])
    old = original.is_plate
    original.is_plate = lambda part: False
    try:
        outcome = dispatch._nesting(panel, "optimize.alternatives", ("P1",))
        assert outcome.status == "passed"
        assert calls == ["alternatives"]
    finally:
        original.is_plate = old


if __name__ == "__main__":
    test_drawing_print_generates_pdf_before_native_print()
    test_plate_compare_refuses_without_canonical_compare()
    test_profile_alternatives_use_existing_phase3_action()
    print("PASS: BOM completion dispatcher keeps W03/W18 intent explicit")
