"""Vector PDF renderer and exact raster preview for ``DrawingDocument``."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
from typing import Iterable

from .document import DrawingDocument, DrawingPrimitive


EMBEDDED_DOCUMENT_NAME = "cws-drawing-document.json"


def _visible_content_sha256(path: str | Path) -> str:
    from pypdf import PdfReader

    digest = sha256()
    reader = PdfReader(str(path))
    for page in reader.pages:
        contents = page.get_contents()
        if contents is not None:
            digest.update(contents.get_data())
    return digest.hexdigest()


class ProductionDrawingRenderer:
    LAYER_ORDER = (
        "sheet",
        "views",
        "hatch",
        "hidden",
        "visible",
        "centerlines",
        "annotations",
        "dimensions",
        "bom",
        "notes",
        "title",
    )

    @staticmethod
    def _paint_primitive(pdf, primitive: DrawingPrimitive, page_height_mm: float, mm: float) -> None:
        from reportlab.lib import colors

        def x(value: float) -> float:
            return float(value) * mm

        def y(value: float) -> float:
            return (float(page_height_mm) - float(value)) * mm

        pdf.saveState()
        pdf.setStrokeColor(colors.HexColor(primitive.color or "#173b5d"))
        pdf.setFillColor(colors.HexColor(primitive.fill or primitive.color or "#173b5d"))
        pdf.setLineWidth(max(0.03, float(primitive.width)) * mm)
        pdf.setDash([float(value) * mm for value in primitive.dash] if primitive.dash else [])
        if primitive.kind == "line" and len(primitive.points) >= 2:
            pdf.line(x(primitive.points[0][0]), y(primitive.points[0][1]), x(primitive.points[1][0]), y(primitive.points[1][1]))
        elif primitive.kind in {"polyline", "polygon"} and len(primitive.points) >= 2:
            path = pdf.beginPath()
            path.moveTo(x(primitive.points[0][0]), y(primitive.points[0][1]))
            for point in primitive.points[1:]:
                path.lineTo(x(point[0]), y(point[1]))
            if primitive.kind == "polygon":
                path.close()
            pdf.drawPath(path, fill=int(bool(primitive.fill)), stroke=1)
        elif primitive.kind == "rect" and len(primitive.points) >= 2:
            left, top = primitive.points[0]
            right, bottom = primitive.points[1]
            pdf.rect(
                x(left),
                y(bottom),
                x(right - left),
                x(bottom - top),
                fill=int(bool(primitive.fill)),
                stroke=1,
            )
        elif primitive.kind == "circle" and len(primitive.center) == 2:
            pdf.circle(x(primitive.center[0]), y(primitive.center[1]), x(primitive.radius), fill=int(bool(primitive.fill)), stroke=1)
        elif primitive.kind == "text" and len(primitive.points) == 1:
            font = "Helvetica-Bold" if primitive.bold else "Helvetica"
            pdf.setFont(font, max(1.0, float(primitive.font_size)) * mm)
            origin_x, origin_y = primitive.points[0]
            if primitive.rotation:
                pdf.translate(x(origin_x), y(origin_y))
                pdf.rotate(float(primitive.rotation))
                pdf.drawString(0.0, 0.0, primitive.text)
            else:
                pdf.drawString(x(origin_x), y(origin_y), primitive.text)
        pdf.restoreState()

    @classmethod
    def _write_visible_pdf(cls, document: DrawingDocument, path: Path) -> None:
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        first = document.pages[0]
        pdf = canvas.Canvas(str(path), pagesize=(first.width_mm * mm, first.height_mm * mm), pageCompression=1)
        pdf.setTitle(str(document.title_block.get("entity") or document.entity_id))
        pdf.setAuthor("CWS Convertor")
        pdf.setSubject(f"{document.schema_version} | {document.document_sha256}")
        order = {name: index for index, name in enumerate(cls.LAYER_ORDER)}
        for page_index, page in enumerate(document.pages):
            if page_index:
                pdf.setPageSize((page.width_mm * mm, page.height_mm * mm))
            for primitive in sorted(
                enumerate(page.primitives),
                key=lambda item: (order.get(item[1].layer, len(order)), item[0]),
            ):
                cls._paint_primitive(pdf, primitive[1], page.height_mm, mm)
            pdf.showPage()
        pdf.save()

    @staticmethod
    def _embed_document(document: DrawingDocument, source: Path, target: Path) -> None:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(str(source))
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer.add_attachment(EMBEDDED_DOCUMENT_NAME, document.canonical_json())
        writer.add_metadata(
            {
                "/CwsDrawingSchema": document.schema_version,
                "/CwsDrawingSha256": document.document_sha256,
                "/CwsVisibleContentSha256": document.visible_content_sha256,
                "/CwsManufacturingSha256": document.manufacturing_sha256,
                "/CwsReleaseReady": str(bool(document.lint.get("release_ready"))).lower(),
            }
        )
        temporary = target.with_name(f".{target.name}.embedding")
        with temporary.open("wb") as stream:
            writer.write(stream)
        os.replace(temporary, target)

    @classmethod
    def render_pdf(cls, document: DrawingDocument, path: str | Path) -> Path:
        document.validate()
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".cws_drawing_", dir=str(target.parent)) as directory:
            visible = Path(directory) / "visible.pdf"
            cls._write_visible_pdf(document, visible)
            document.visible_content_sha256 = _visible_content_sha256(visible)
            document.seal()
            cls._embed_document(document, visible, target)
        if not target.is_file() or target.stat().st_size < 1024:
            raise RuntimeError(f"Productietekening-PDF is niet aangemaakt: {target}")
        if _visible_content_sha256(target) != document.visible_content_sha256:
            raise RuntimeError("Zichtbare PDF-inhoud wijzigde tijdens het inbedden van DrawingDocument")
        restored = cls.load_embedded_document(target)
        if restored.document_sha256 != document.document_sha256:
            raise RuntimeError("Ingebed DrawingDocument wijkt af van de gerenderde tekening")
        return target

    @staticmethod
    def render_png(pdf_path: str | Path, path: str | Path, *, page_number: int = 0, width_px: int = 1800) -> Path:
        import fitz

        source = Path(pdf_path).expanduser().resolve()
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        document = fitz.open(str(source))
        if not 0 <= int(page_number) < document.page_count:
            document.close()
            raise IndexError("PDF-bladnummer valt buiten het document")
        page = document[int(page_number)]
        zoom = max(0.1, float(width_px) / max(1.0, float(page.rect.width)))
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        pixmap.save(str(target))
        document.close()
        if not target.is_file() or target.stat().st_size < 512:
            raise RuntimeError(f"Tekenvoorbeeld is niet aangemaakt: {target}")
        return target

    @classmethod
    def render(
        cls,
        document: DrawingDocument,
        *,
        pdf_path: str | Path | None = None,
        png_path: str | Path | None = None,
    ) -> tuple[Path | None, Path | None]:
        if pdf_path is None and png_path is None:
            return None, None
        final_pdf = Path(pdf_path).expanduser().resolve() if pdf_path is not None else None
        temporary_pdf: Path | None = None
        if final_pdf is None:
            png_target = Path(png_path).expanduser().resolve()
            png_target.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".cws_preview_", suffix=".pdf", dir=str(png_target.parent))
            os.close(descriptor)
            temporary_pdf = Path(name)
            render_target = temporary_pdf
        else:
            render_target = final_pdf
        try:
            cls.render_pdf(document, render_target)
            final_png = cls.render_png(render_target, png_path) if png_path is not None else None
        finally:
            if temporary_pdf is not None:
                temporary_pdf.unlink(missing_ok=True)
        return final_pdf, final_png

    @staticmethod
    def load_embedded_document(path: str | Path) -> DrawingDocument:
        from pypdf import PdfReader

        reader = PdfReader(str(Path(path).expanduser().resolve()))
        attachments = reader.attachments
        values: Iterable[bytes] | bytes | None = attachments.get(EMBEDDED_DOCUMENT_NAME)
        if values is None:
            raise ValueError("PDF bevat geen ingebed DrawingDocument")
        if isinstance(values, bytes):
            payload = values
        else:
            payload = next(iter(values), b"")
        if not payload:
            raise ValueError("Ingebed DrawingDocument is leeg")
        document = DrawingDocument.from_dict(json.loads(payload.decode("utf-8")))
        if document.visible_content_sha256 != _visible_content_sha256(path):
            raise ValueError("Zichtbare PDF-inhoud hoort niet bij het ingebedde DrawingDocument")
        return document


__all__ = ["EMBEDDED_DOCUMENT_NAME", "ProductionDrawingRenderer"]
