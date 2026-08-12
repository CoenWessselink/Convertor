"""Deterministic PDF fixtures for regression validation.

The LO4 fixture is synthetic and is only based on the source values described
in the supplied reference drawing. It is not a binary or visual copy of the
Tekla PDF. This distinction is retained in every validation report.
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def create_synthetic_lo4_pdf(
    path: str | Path,
    *,
    hole_callout_diameter_mm: float = 14.0,
    hole_geometry_diameter_mm: float = 14.0,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(target), pagesize=(page_width, page_height), pageCompression=0)
    pdf.setLineWidth(1.0)
    pdf.rect(10 * mm, 10 * mm, page_width - 20 * mm, page_height - 20 * mm)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(36, page_height - 42, "Pos Profiel Materiaal Lengte Aantal Merk")
    pdf.drawString(36, page_height - 58, "LO4 STRIP5*120 S235JR 160 4 MLO4")
    pdf.drawString(36, page_height - 76, "Totaal aantal keer uit te voeren: 4")
    pdf.drawString(36, page_height - 94, "Schaal: 1:2")
    pdf.drawString(36, page_height - 112, "Formaat: A4")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(36, page_height - 134, "LOSSE PLAAT")
    pdf.setFont("Helvetica", 10)
    callout = f"1*Ø{hole_callout_diameter_mm:g}".replace(".", ",")
    pdf.drawString(500, page_height - 75, callout)
    pdf.drawString(500, page_height - 93, "R 13,5")
    pdf.drawString(500, page_height - 111, "R 13,5")

    # 160 x 120 mm at 1:2 -> 320 x 240 PDF points in this synthetic fixture.
    # The two left corners are true R13.5 mm cubic curves (27 pt at 1:2).
    x0, x1 = 160.0, 480.0
    y0, y1 = 210.0, 450.0
    radius_pt = 27.0
    kappa = 0.5522847498307936
    path_obj = pdf.beginPath()
    path_obj.moveTo(x0 + radius_pt, y0)
    path_obj.lineTo(x1, y0)
    path_obj.lineTo(x1, y1)
    path_obj.lineTo(x0 + radius_pt, y1)
    path_obj.curveTo(
        x0 + radius_pt - kappa * radius_pt,
        y1,
        x0,
        y1 - radius_pt + kappa * radius_pt,
        x0,
        y1 - radius_pt,
    )
    path_obj.lineTo(x0, y0 + radius_pt)
    path_obj.curveTo(
        x0,
        y0 + radius_pt - kappa * radius_pt,
        x0 + radius_pt - kappa * radius_pt,
        y0,
        x0 + radius_pt,
        y0,
    )
    pdf.drawPath(path_obj, stroke=1, fill=0)

    # Hole centre 20 mm from the lower-left production datum. At scale 1:2,
    # one model millimetre is represented by two PDF points in this fixture.
    pdf.circle(200.0, 250.0, hole_geometry_diameter_mm, stroke=1, fill=0)

    # A title-block rectangle helps verify that the outline selector rejects
    # page borders and drawing frames.
    pdf.rect(page_width - 300.0, 20.0, 270.0, 110.0)
    pdf.showPage()
    pdf.save()
    return target
