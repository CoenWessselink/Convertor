"""Lokale, uitbreidbare profielendatabase voor de NC1 ↔ STEP/IFC-converter."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from cws_convertor.product import APP_SLUG
import json
import math
import os
import re
import shutil
import sys
from typing import Any, Iterable


def resource_path(filename: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / filename


def default_user_database_path() -> Path:
    """Return the CWS user database path and preserve legacy profile data.

    v0.5 stored the Linux/macOS user copy below ``~/.nc1_step_converter``.
    The CWS product identity uses ``~/.cws_convertor`` from v0.6 onward, but
    an existing legacy database is copied once instead of being silently lost.
    Windows already uses the central product slug below ``%APPDATA%``.
    """

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / APP_SLUG / "profiles.json"

    target = Path.home() / ".cws_convertor" / "profiles.json"
    legacy = Path.home() / ".nc1_step_converter" / "profiles.json"
    if not target.exists() and legacy.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, target)
    return target


def normalise_name(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


@dataclass
class ProfileDefinition:
    designation: str
    profile_type: str
    family: str
    dim1: float
    dim2: float
    dim3: float = 0.0
    dim4: float = 0.0
    radius: float = 0.0
    mass_kg_m: float = 0.0
    area_mm2: float = 0.0
    standard: str = ""
    aliases: list[str] = field(default_factory=list)
    source: str = "local"
    properties: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    catalogue_status: str = "local"

    def __post_init__(self) -> None:
        self.profile_type = self.profile_type.upper().strip()
        self.designation = self.designation.strip()
        self.family = self.family.strip() or self.profile_type
        self.dim1 = float(self.dim1 or 0.0)
        self.dim2 = float(self.dim2 or 0.0)
        self.dim3 = float(self.dim3 or 0.0)
        self.dim4 = float(self.dim4 or 0.0)
        self.radius = float(self.radius or 0.0)
        self.mass_kg_m = float(self.mass_kg_m or 0.0)
        self.area_mm2 = float(self.area_mm2 or 0.0)
        if self.area_mm2 <= 0:
            self.area_mm2 = self.calculated_area_mm2()
        if self.mass_kg_m <= 0 and self.area_mm2 > 0:
            self.mass_kg_m = self.area_mm2 * 0.00785

    @property
    def width(self) -> float:
        return self.dim1 if self.profile_type in {"RU", "RO"} else self.dim2

    @property
    def height(self) -> float:
        return self.dim1

    @property
    def search_names(self) -> set[str]:
        return {normalise_name(self.designation), *(normalise_name(alias) for alias in self.aliases)}

    def calculated_area_mm2(self) -> float:
        h, b, d3, d4, r = self.dim1, self.dim2, self.dim3, self.dim4, self.radius
        extra = max(r, 0.0) ** 2 * (1.0 - math.pi / 4.0)
        if self.profile_type == "B":
            return h * b
        if self.profile_type == "I":
            return 2.0 * b * d3 + max(h - 2.0 * d3, 0.0) * d4 + 4.0 * extra
        if self.profile_type in {"U", "C"}:
            return 2.0 * b * d3 + max(h - 2.0 * d3, 0.0) * d4 + 2.0 * extra
        if self.profile_type == "L":
            return h * d4 + b * d3 - d3 * d4 + extra
        if self.profile_type == "M":
            positive = [value for value in (d3, d4) if value > 0]
            t = min(positive) if positive else 0.0
            return max(0.0, h * b - max(h - 2.0 * t, 0.0) * max(b - 2.0 * t, 0.0))
        if self.profile_type == "RU":
            return math.pi * h * h / 4.0
        if self.profile_type == "RO":
            t = d3 if d3 > 0 else d4
            inner = max(h - 2.0 * t, 0.0)
            return math.pi * (h * h - inner * inner) / 4.0
        return 0.0


@dataclass
class ProfileMatch:
    profile: ProfileDefinition
    confidence: float
    dimension_error_mm: float
    area_error_percent: float
    matched_by: str


class ProfileDatabase:
    """Profielendatabase met seedbestand en een schrijfbare kopie in AppData."""

    def __init__(self, path: str | Path | None = None, *, writable_copy: bool = True) -> None:
        if path is not None:
            self.path = Path(path)
        elif writable_copy:
            self.path = default_user_database_path()
        else:
            self.path = resource_path("profiles.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            seed = resource_path("profiles.json")
            if seed.exists() and seed.resolve() != self.path.resolve():
                shutil.copy2(seed, self.path)
            else:
                self.path.write_text('{"schema_version": 1, "profiles": []}\n', encoding="utf-8")
        self.profiles: list[ProfileDefinition] = []
        self.load()

    def load(self) -> None:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        rows = data.get("profiles", data) if isinstance(data, dict) else data
        allowed = set(ProfileDefinition.__dataclass_fields__.keys())
        cleaned = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            extras = {k: v for k, v in row.items() if k not in allowed}
            clean = {k: v for k, v in row.items() if k in allowed}
            if extras:
                props = clean.setdefault("properties", {}) or {}
                props.update({f"extra.{k}": v for k, v in extras.items()})
                clean["properties"] = props
            cleaned.append(ProfileDefinition(**clean))
        self.profiles = cleaned

    def save(self) -> None:
        payload = {
            "schema_version": 2,
            "description": "Lokale profielendatabase voor STEP/IFC naar DSTV/NC1.",
            "profiles": [asdict(profile) for profile in sorted(self.profiles, key=lambda p: (p.profile_type, p.family, p.designation))],
        }
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def add_or_update(self, profile: ProfileDefinition) -> bool:
        key = (normalise_name(profile.designation), profile.profile_type)
        for index, existing in enumerate(self.profiles):
            if (normalise_name(existing.designation), existing.profile_type) == key:
                changed = existing != profile
                self.profiles[index] = profile
                if changed:
                    self.save()
                return changed
        self.profiles.append(profile)
        self.save()
        return True

    def add_many(self, profiles: Iterable[ProfileDefinition]) -> int:
        count = 0
        for profile in profiles:
            if self.add_or_update(profile):
                count += 1
        return count

    def find(self, designation: str) -> ProfileDefinition | None:
        key = normalise_name(designation)
        if not key:
            return None
        for profile in self.profiles:
            if key in profile.search_names:
                return profile
        for profile in self.profiles:
            if key in normalise_name(profile.designation):
                return profile
        return None

    def families(self) -> list[str]:
        return sorted({profile.family for profile in self.profiles if profile.family})

    def types(self) -> list[str]:
        return sorted({profile.profile_type for profile in self.profiles if profile.profile_type})

    def filtered(self, *, text: str = "", family: str = "Alle", profile_type: str = "Alle") -> list[ProfileDefinition]:
        key = normalise_name(text)
        family = family or "Alle"
        profile_type = profile_type or "Alle"
        rows: list[ProfileDefinition] = []
        for profile in self.profiles:
            if family != "Alle" and profile.family != family:
                continue
            if profile_type != "Alle" and profile.profile_type != profile_type:
                continue
            haystack = " ".join([profile.designation, profile.profile_type, profile.family, profile.standard, profile.source, profile.notes, *profile.aliases])
            if key and key not in normalise_name(haystack):
                continue
            rows.append(profile)
        return sorted(rows, key=lambda p: (p.profile_type, p.family, p.designation))

    def match(
        self,
        *,
        filename: str,
        signature_type: str,
        cross_extent_a: float,
        cross_extent_b: float,
        area_estimate_mm2: float,
        tolerance_mm: float = 1.0,
    ) -> ProfileMatch:
        signature_type = "U" if signature_type == "C" else signature_type
        candidates = [
            profile
            for profile in self.profiles
            if ("U" if profile.profile_type == "C" else profile.profile_type) == signature_type
        ]
        if not candidates:
            raise LookupError(f"Geen profielen van type {signature_type} in de profielendatabase")

        filename_key = normalise_name(Path(filename).stem)
        matches: list[ProfileMatch] = []
        for profile in candidates:
            expected_a, expected_b = profile.width, profile.height
            direct = max(abs(cross_extent_a - expected_a), abs(cross_extent_b - expected_b))
            swapped = max(abs(cross_extent_a - expected_b), abs(cross_extent_b - expected_a))
            dimension_error = min(direct, swapped)
            area_reference = max(profile.area_mm2, 1e-9)
            area_error = abs(area_estimate_mm2 - area_reference) / area_reference * 100.0
            hinted = any(name and name in filename_key for name in profile.search_names)

            dim_scale = max(tolerance_mm, 0.75, 0.0125 * max(expected_a, expected_b))
            dim_score = math.exp(-dimension_error / dim_scale)
            area_score = math.exp(-area_error / 5.0)
            confidence = 0.70 * dim_score + 0.30 * area_score
            if hinted:
                confidence = min(1.0, confidence + 0.18)
            matches.append(
                ProfileMatch(
                    profile,
                    confidence,
                    dimension_error,
                    area_error,
                    "bestandsnaam + geometrie" if hinted else "geometrie + doorsnede-oppervlak",
                )
            )

        best = max(matches, key=lambda item: item.confidence)
        max_dimension_error = max(2.0 * tolerance_mm, 0.03 * max(best.profile.width, best.profile.height))
        if best.dimension_error_mm > max_dimension_error or best.confidence < 0.48:
            raise LookupError(
                f"Geen betrouwbaar profiel gevonden. Beste kandidaat {best.profile.designation}: "
                f"maatverschil {best.dimension_error_mm:.2f} mm, oppervlakverschil "
                f"{best.area_error_percent:.2f}%, confidence {best.confidence:.0%}."
            )
        return best
