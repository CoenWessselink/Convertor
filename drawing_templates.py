"""Bedrijfs- en bladtemplates voor technische PDF-tekeningen.

De template bevat alleen presentatie-instellingen. Productiegeometrie en
maatwaarden blijven afkomstig uit het canonieke onderdeelmodel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
from typing import Any

MM_TO_PT = 72.0 / 25.4

SHEET_SIZES_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
}


@dataclass
class DrawingTemplate:
    template_id: str = "default"
    company_name: str = ""
    company_subtitle: str = ""
    logo_path: str = ""
    sheet_format: str = "A4"
    orientation: str = "landscape"
    projection_method: str = "first-angle"
    decimal_places: int = 1
    font_name: str = "helv"
    title_font_name: str = "helv"
    margin_mm: float = 8.0
    title_block_height_mm: float = 42.0
    parts_table_height_mm: float = 18.0
    line_width_mm: float = 0.25
    thin_line_width_mm: float = 0.13
    dimension_text_height_mm: float = 3.0
    normal_text_height_mm: float = 2.7
    title_text_height_mm: float = 4.0
    default_status: str = "CONCEPT"
    default_subject: str = "ONDERDEELTEKENING"
    default_notes: list[str] = field(default_factory=list)
    title_block_defaults: dict[str, Any] = field(default_factory=dict)

    def page_size_points(self) -> tuple[float, float]:
        key = self.sheet_format.upper()
        if key not in SHEET_SIZES_MM:
            raise ValueError(f"Onbekend bladformaat {self.sheet_format!r}")
        short_mm, long_mm = SHEET_SIZES_MM[key]
        if self.orientation.lower() == "landscape":
            width_mm, height_mm = long_mm, short_mm
        else:
            width_mm, height_mm = short_mm, long_mm
        return width_mm * MM_TO_PT, height_mm * MM_TO_PT

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DrawingTemplate":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})


def default_template_path() -> Path:
    return Path(__file__).resolve().parent / "templates" / "default_company.json"


def load_template(path: str | Path | None = None) -> DrawingTemplate:
    target = Path(path) if path else default_template_path()
    if not target.exists():
        return DrawingTemplate()
    data = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Tekeningtemplate {target} bevat geen JSON-object")
    return DrawingTemplate.from_dict(data)


def save_template(template: DrawingTemplate, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(template.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target
