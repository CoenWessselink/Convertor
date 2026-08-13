from __future__ import annotations

import io
import textwrap
from typing import Any

from .utils import finite_number, get_value


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _minimal_pdf(lines: list[str]) -> bytes:
    # Deterministic, dependency-free A4 PDF with searchable text.
    commands = ["BT", "/F1 10 Tf", "50 790 Td"]
    first = True
    for line in lines:
        for wrapped in textwrap.wrap(str(line), width=95) or [""]:
            if not first:
                commands.append("0 -14 Td")
            commands.append(f"({_pdf_escape(wrapped)}) Tj")
            first = False
    commands.append("ET")
    content = "\n".join(commands).encode("latin-1", errors="replace")
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{index} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.write(
        f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return out.getvalue()


def create_review_pdf(part: Any, *, blocked_reasons: list[str], product_version: str) -> bytes:
    part_id = str(get_value(part, "id", "part_id", "internal_id", default=""))
    position = str(get_value(part, "part_position", "position", "mark", default=""))
    profile = str(get_value(part, "normalized_profile", "profile", "profile_name", default=""))
    material = str(get_value(part, "normalized_material", "material", "material_name", default=""))
    length = finite_number(get_value(part, "length", "length_mm", default=None))
    mass = finite_number(get_value(part, "mass", "mass_kg", default=None))
    lines = [
        "CWS CONVERTOR — ONDERDEELREVIEW",
        f"Versie: {product_version}",
        "STATUS: NIET VRIJGEGEVEN VOOR PRODUCTIE" if blocked_reasons else "STATUS: GEVALIDEERD",
        "",
        f"Onderdeel-ID: {part_id}",
        f"Positie: {position or '-'}",
        f"Profiel: {profile or '-'}",
        f"Materiaal: {material or '-'}",
        f"Lengte: {length:.3f} mm" if length is not None else "Lengte: -",
        f"Massa: {mass:.3f} kg" if mass is not None else "Massa: -",
        "",
        "Blokkades:" if blocked_reasons else "Validatie:",
    ]
    lines.extend(f"- {reason}" for reason in (blocked_reasons or ["Geen blokkerende melding"]))
    lines.extend([
        "",
        "Dit document is automatisch opgebouwd uit het Canonical Project Model.",
        "Het document is geen machinebestand en heft geen productiegate op.",
    ])
    return _minimal_pdf(lines)
