"""Materiaalbibliotheek en materiaal-eigenschappen voor hoeveelheden en Excel."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
import sys
from typing import Any


def resource_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def normalise_material(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


@dataclass(frozen=True)
class MaterialDefinition:
    code: str
    name: str
    category: str
    density_kg_m3: float
    elastic_modulus_gpa: float
    poisson_ratio: float
    yield_strength_mpa: float
    tensile_strength_mpa: float
    thermal_expansion_1e6_k: float
    thermal_conductivity_w_mk: float
    specific_heat_j_kg_k: float
    standard: str = ""
    notes: str = ""
    aliases: tuple[str, ...] = ()

    @property
    def search_names(self) -> set[str]:
        return {normalise_material(self.code), *(normalise_material(item) for item in self.aliases)}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MaterialDatabase:
    """Read-only seed library. Values are indicative and must be checked per product thickness/certificate."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else resource_path("materials.json")
        data = json.loads(self.path.read_text(encoding="utf-8"))
        rows = data.get("materials", data) if isinstance(data, dict) else data
        self.materials = [
            MaterialDefinition(
                **{
                    **row,
                    "aliases": tuple(row.get("aliases", [])),
                }
            )
            for row in rows
        ]

    def find(self, code_or_name: str, default: str = "S355JR") -> MaterialDefinition:
        key = normalise_material(code_or_name)
        for item in self.materials:
            if key and key in item.search_names:
                return item
        if code_or_name and key:
            # IFC material names can contain a grade inside a longer description.
            for item in self.materials:
                if any(name and name in key for name in item.search_names):
                    return item
        default_key = normalise_material(default)
        for item in self.materials:
            if default_key in item.search_names:
                return item
        return self.materials[0]

    @property
    def codes(self) -> list[str]:
        return [item.code for item in self.materials]
