"""Shared print and PDF export helpers for drawings and nesting workspaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtPrintSupport import QPrintDialog, QPrintPreviewDialog, QPrinter


def _printer(*, pdf_path: str | Path | None = None) -> QPrinter:
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageOrientation(QtGui.QPageLayout.Orientation.Landscape)
    printer.setFullPage(False)
    if pdf_path is not None:
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(Path(pdf_path).expanduser().resolve()))
    return printer


def _paint_widget(widget: QtWidgets.QWidget, printer: QPrinter, title: str = "") -> None:
    painter = QtGui.QPainter(printer)
    if not painter.isActive():
        raise RuntimeError("Printer painter kon niet worden gestart")
    page = printer.pageRect(QPrinter.Unit.DevicePixel)
    source = widget.rect()
    header = 180 if title else 0
    if title:
        painter.setFont(QtGui.QFont("Aptos", 14, QtGui.QFont.Weight.DemiBold))
        painter.drawText(QtCore.QRectF(page.left(), page.top(), page.width(), header), QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter, title)
    sx = page.width() / max(1.0, float(source.width()))
    sy = (page.height() - header) / max(1.0, float(source.height()))
    scale = min(sx, sy)
    painter.save()
    painter.translate(page.left(), page.top() + header)
    painter.scale(scale, scale)
    widget.render(painter, QtCore.QPoint(), QtGui.QRegion(), QtWidgets.QWidget.RenderFlag.DrawChildren)
    painter.restore()
    painter.end()


def export_widget_pdf(widget: QtWidgets.QWidget, path: str | Path, *, title: str = "") -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    _paint_widget(widget, _printer(pdf_path=target), title)
    if not target.is_file() or target.stat().st_size < 256:
        raise RuntimeError(f"PDF-export is niet aangemaakt: {target}")
    return target


def print_widget(widget: QtWidgets.QWidget, *, title: str, parent: QtWidgets.QWidget | None = None, preview: bool = False) -> bool:
    printer = _printer()
    if preview:
        dialog: Any = QPrintPreviewDialog(printer, parent)
        dialog.setWindowTitle(f"Afdrukvoorbeeld - {title}")
        dialog.paintRequested.connect(lambda device: _paint_widget(widget, device, title))
        dialog.exec()
        return True
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(f"Afdrukken - {title}")
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return False
    _paint_widget(widget, printer, title)
    return True


def print_pdf_file(path: str | Path, *, parent: QtWidgets.QWidget | None = None) -> bool:
    source = Path(path).expanduser().resolve()
    if not source.is_file() or source.suffix.casefold() != ".pdf":
        raise FileNotFoundError(f"PDF niet gevonden: {source}")
    try:
        from PySide6.QtPdf import QPdfDocument
    except ImportError as exc:
        raise RuntimeError("Qt PDF-renderer ontbreekt in deze runtime") from exc
    document = QPdfDocument(parent)
    document.load(str(source))
    if document.status() == QPdfDocument.Status.Error:
        raise RuntimeError(f"PDF kon niet worden geladen: {source}")
    printer = _printer()
    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle(f"PDF afdrukken - {source.name}")
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return False
    painter = QtGui.QPainter(printer)
    for page_number in range(document.pageCount()):
        if page_number:
            printer.newPage()
        target = printer.pageRect(QPrinter.Unit.DevicePixel)
        image = document.render(page_number, target.size().toSize())
        painter.drawImage(target, image)
    painter.end()
    return True


__all__ = ["export_widget_pdf", "print_pdf_file", "print_widget"]

