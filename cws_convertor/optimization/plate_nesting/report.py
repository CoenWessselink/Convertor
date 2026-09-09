"""Complete, fresh, contour-based planning PDF. Never a CNC drawing release."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import os
import tempfile
from .canonical import PlateGeometryRef, _placed_polygon
from .project_service import verify_saved_plan


def export_planning_pdf(project, record, target):
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.pagesizes import A4, landscape
    plan = verify_saved_plan(project, record)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, suffix='.pdf')
    os.close(fd)
    try:
        width, height = landscape(A4)
        canvas = Canvas(temporary, pagesize=(width, height), pageCompression=1)
        canvas.setTitle('CWS Plaatnesting - planningsrapport')
        geometry = {d['part_id']: PlateGeometryRef(**d['geometry']) for d in record['inputs']['demands']}
        quantities = Counter(p.part_id for layout in plan.layouts for p in layout.placements)
        for index, layout in enumerate(plan.layouts, 1):
            first = layout.placements[0]
            canvas.setFont('Helvetica-Bold', 15)
            canvas.drawString(32, height - 34, f'Plaatnesting | plaat {index}/{len(plan.layouts)}')
            canvas.setFont('Helvetica', 10)
            canvas.drawString(32, height - 55, f'{layout.stock_instance_id} | {first.grade} | {first.thickness_mm:g} mm | {layout.width_mm:g} x {layout.height_mm:g} mm')
            canvas.drawString(32, height - 72, f'Vraag: {plan.placed_count} exemplaren | deze plaat: {len(layout.placements)} | reservering: {record["reservation_id"][:24]}')
            scale = min((width - 90) / layout.width_mm, (height - 180) / layout.height_mm)
            x0, y0 = 40, 80
            canvas.setLineWidth(0.7)
            canvas.rect(x0, y0, layout.width_mm * scale, layout.height_mm * scale, fill=0)
            for part in layout.placements:
                polygon = _placed_polygon(part, geometry[part.part_id])
                path = canvas.beginPath()
                for ring in (polygon.exterior, *polygon.interiors):
                    coords = list(ring.coords)
                    path.moveTo(x0 + coords[0][0] * scale, y0 + coords[0][1] * scale)
                    for x, y in coords[1:]: path.lineTo(x0 + x * scale, y0 + y * scale)
                    path.close()
                canvas.drawPath(path, stroke=1, fill=0)
                center = polygon.representative_point()
                canvas.setFont('Helvetica', 7)
                canvas.drawCentredString(x0 + center.x * scale, y0 + center.y * scale, part.instance_id)
            canvas.setFont('Helvetica-Bold', 9)
            canvas.drawString(32, 48, 'ALLEEN PLANNING - geen CNC-/materiaalcertificaat- of productievrijgave')
            canvas.setFont('Helvetica', 7)
            canvas.drawString(32, 34, 'Plan SHA-256: ' + plan.plan_sha256)
            canvas.showPage()
        canvas.setFont('Helvetica-Bold', 15); canvas.drawString(32, height - 35, 'Hoeveelheden en geometriebasis')
        y = height - 60
        for item in record['inputs']['geometry_basis']:
            if y < 65:
                canvas.showPage(); y = height - 40; canvas.setFont('Helvetica', 9)
            canvas.setFont('Helvetica', 9)
            canvas.drawString(32, y, f"{item['id']} | {quantities[item['id']]} stuks | {item['basis']}")
            y -= 16
        canvas.save()
        verify_saved_plan(project, record)  # no stale report if caller changed data during rendering
        os.replace(temporary, target)
        return target
    finally:
        Path(temporary).unlink(missing_ok=True)
