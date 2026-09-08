"""Materiaalbibliotheek en materiaal-eigenschappen voor hoeveelheden en Excel."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import sys
from typing import Any, Mapping

from cws_convertor.material_resolution import (
    MaterialResolution,
    MaterialResolver,
    normalize_material_key,
)


def resource_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def normalise_material(text: str) -> str:
    """Backward-compatible spelling for the resolver comparison key."""

    return normalize_material_key(text)


@dataclass(frozen=True)
class MaterialDefinition:
    code: str
    name: str
    category: str
    density_kg_m3: float
    elastic_modulus_gpa: float = 0.0
    poisson_ratio: float = 0.0
    yield_strength_mpa: float = 0.0
    tensile_strength_mpa: float = 0.0
    thermal_expansion_1e6_k: float = 0.0
    thermal_conductivity_w_mk: float = 0.0
    specific_heat_j_kg_k: float = 0.0
    standard: str = ""
    notes: str = ""
    aliases: tuple[str, ...] = ()
    density_status: str = "nominal"
    mass_calculation_allowed: bool = True

    @property
    def search_names(self) -> set[str]:
        return {normalise_material(self.code), *(normalise_material(item) for item in self.aliases)}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class MaterialDatabase:
    """Read-only seed library. Values are indicative and must be checked per product thickness/certificate."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else resource_path("materials.json")
        catalog_bytes = self.path.read_bytes()
        self.catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
        data = json.loads(catalog_bytes.decode("utf-8"))
        rows = data.get("materials", data) if isinstance(data, dict) else data
        property_templates = data.get("property_templates", {}) if isinstance(data, dict) else {}
        prepared_rows: list[dict[str, Any]] = []
        for source_row in rows:
            row = dict(source_row)
            template_name = str(row.pop("property_template", "") or "")
            if template_name and template_name not in property_templates:
                raise ValueError(f"Onbekend materiaal-property-template: {template_name}")
            template = dict(property_templates.get(template_name, {}))
            prepared_rows.append({**template, **row})
        self.materials = [
            MaterialDefinition(
                **{
                    **row,
                    "aliases": tuple(row.get("aliases", [])),
                }
            )
            for row in prepared_rows
        ]
        for material in self.materials:
            if material.mass_calculation_allowed and material.density_kg_m3 <= 0:
                raise ValueError(
                    f"Materiaal {material.code} staat massaberekening toe zonder positieve dichtheid"
                )

        self.resolver = MaterialResolver(
            self.materials,
            catalog_reference=f"{self.path.name}#sha256:{self.catalog_sha256}",
        )

    def resolve(
        self,
        code_or_name: Any,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> MaterialResolution:
        """Resolve a complete source value to an exact code, alias or unresolved result."""

        return self.resolver.resolve(code_or_name, provenance=provenance)

    def find(
        self,
        code_or_name: str,
        default: str | None = None,
    ) -> MaterialDefinition | None:
        """Return a catalog material without silently inventing one.

        ``find(value)`` now returns ``None`` for unknown values.  Legacy callers
        that intentionally want a fallback can still request it explicitly via
        ``find(value, default="S355JR")``.  An unknown default also returns
        ``None``; the first catalog row is never used as an implicit fallback.
        """

        resolution = self.resolve(code_or_name)
        if resolution.resolved:
            return resolution.definition
        if default is None:
            return None
        fallback = self.resolve(
            default,
            provenance={
                "source_kind": "explicit_find_default",
                "unresolved_value": str(code_or_name or ""),
            },
        )
        return fallback.definition if fallback.resolved else None

    @property
    def codes(self) -> list[str]:
        return [item.code for item in self.materials]


__all__ = [
    "MaterialDatabase",
    "MaterialDefinition",
    "MaterialResolution",
    "MaterialResolver",
    "normalise_material",
    "resource_path",
]
