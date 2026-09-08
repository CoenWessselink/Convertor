"""Deterministic, evidence-based material identity resolution.

This module deliberately does not infer a material from geometry, density, a
profile family, or a partial substring.  A result is only resolved when the
complete normalized source value equals a catalog code or an explicit alias.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Iterable, Literal, Mapping, Protocol


MaterialResolutionStatus = Literal["exact", "alias", "unresolved"]


def normalize_material_key(value: Any) -> str:
    """Return the comparison key used by the material catalog.

    Whitespace and designation hyphens are harmless separators. Decimal
    points and slashes remain significant: grade 8.8 is not grade 88, and
    concrete C20/25 is not an arbitrary C2025 identifier.
    """

    text = str(value or "").upper().replace("–", "-").replace("—", "-")
    return re.sub(r"[\s_-]+", "", text)


class MaterialRecord(Protocol):
    code: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class MaterialResolution:
    """Auditable outcome of resolving one source material value."""

    raw_value: str
    normalized_value: str
    status: MaterialResolutionStatus
    confidence: float
    material_code: str = ""
    matched_value: str = ""
    reason: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    definition: Any | None = field(default=None, repr=False, compare=False)

    @property
    def resolved(self) -> bool:
        return self.definition is not None and self.status in {"exact", "alias"}

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("definition", None)
        return payload


class MaterialResolver:
    """Resolve exact codes and explicit aliases without unsafe guessing."""

    EXACT_CONFIDENCE = 1.0
    ALIAS_CONFIDENCE = 0.95

    def __init__(self, materials: Iterable[MaterialRecord], *, catalog_reference: str = "") -> None:
        self._materials = tuple(materials)
        self.catalog_reference = str(catalog_reference)
        self._codes: dict[str, MaterialRecord] = {}
        self._aliases: dict[str, tuple[MaterialRecord, str]] = {}

        for material in self._materials:
            code_key = normalize_material_key(material.code)
            if not code_key:
                raise ValueError("Materiaalcode mag niet leeg zijn")
            previous = self._codes.get(code_key)
            if previous is not None and previous.code != material.code:
                raise ValueError(f"Dubbele genormaliseerde materiaalcode: {previous.code} / {material.code}")
            self._codes[code_key] = material

        for material in self._materials:
            code_key = normalize_material_key(material.code)
            for alias in material.aliases:
                alias_key = normalize_material_key(alias)
                if not alias_key or alias_key == code_key:
                    continue
                code_collision = self._codes.get(alias_key)
                if code_collision is not None and code_collision.code != material.code:
                    raise ValueError(
                        f"Materiaalalias {alias!r} van {material.code} botst met code {code_collision.code}"
                    )
                alias_collision = self._aliases.get(alias_key)
                if alias_collision is not None and alias_collision[0].code != material.code:
                    raise ValueError(
                        f"Materiaalalias {alias!r} is ambigu voor "
                        f"{alias_collision[0].code} en {material.code}"
                    )
                if alias_collision is None:
                    self._aliases[alias_key] = (material, str(alias))

    def resolve(
        self,
        value: Any,
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> MaterialResolution:
        raw = str(value or "").strip()
        key = normalize_material_key(raw)
        evidence = dict(provenance or {})
        evidence.setdefault("resolver", "cws-material-resolver-v1")
        if self.catalog_reference:
            evidence.setdefault("catalog", self.catalog_reference)

        if not key:
            return MaterialResolution(
                raw_value=raw,
                normalized_value=key,
                status="unresolved",
                confidence=0.0,
                reason="Geen materiaalwaarde in de bron aanwezig.",
                provenance=evidence,
            )

        exact = self._codes.get(key)
        if exact is not None:
            return MaterialResolution(
                raw_value=raw,
                normalized_value=key,
                status="exact",
                confidence=self.EXACT_CONFIDENCE,
                material_code=exact.code,
                matched_value=exact.code,
                reason="Volledige bronwaarde komt exact overeen met een cataloguscode.",
                provenance=evidence,
                definition=exact,
            )

        alias_match = self._aliases.get(key)
        if alias_match is not None:
            material, alias = alias_match
            return MaterialResolution(
                raw_value=raw,
                normalized_value=key,
                status="alias",
                confidence=self.ALIAS_CONFIDENCE,
                material_code=material.code,
                matched_value=alias,
                reason="Volledige bronwaarde komt overeen met een expliciete catalogusalias.",
                provenance=evidence,
                definition=material,
            )

        return MaterialResolution(
            raw_value=raw,
            normalized_value=key,
            status="unresolved",
            confidence=0.0,
            reason="Geen exacte code of expliciete alias in de materiaalcatalogus.",
            provenance=evidence,
        )


__all__ = [
    "MaterialRecord",
    "MaterialResolution",
    "MaterialResolutionStatus",
    "MaterialResolver",
    "normalize_material_key",
]
