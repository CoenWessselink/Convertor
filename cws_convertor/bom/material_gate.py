"""Read-only BOM material evidence checks; never infer or confirm a grade."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from material_database import MaterialDatabase
from cws_convertor.production_export.utils import finite_number


def part_material_blockers(part: Any, catalog: MaterialDatabase | None = None) -> tuple[str, ...]:
    """Keep the BOM indicator consistent with exact catalog and workbench evidence.

    A display label, a stale normalized value or confidence alone is not proof.
    All supplied values must resolve to the same catalog identity. The caller
    may reuse one catalog for an entire snapshot; no model fields are changed.
    """
    database = catalog if catalog is not None else MaterialDatabase()
    issues: list[str] = []
    fields = ("material", "material_grade", "normalized_material")
    values = {key: str(getattr(part, key, "") or "").strip() for key in fields}
    identities: dict[str, str] = {}
    for key, value in values.items():
        if not value:
            issues.append(f"Materiaalbewijs ontbreekt: {key}")
            continue
        resolution = database.resolve(value)
        if not resolution.resolved:
            issues.append(f"Materiaal niet exact in catalogus: {key}={value}")
        else:
            identities[key] = resolution.definition.code
    if len(set(identities.values())) > 1:
        issues.append("Ruw materiaal, materiaalkwaliteit en genormaliseerd materiaal spreken elkaar tegen")
    confidence = finite_number(getattr(part, "material_confidence", None))
    if confidence is None or not 0.95 <= confidence <= 1.0:
        issues.append("Materiaalconfidence is niet productiegereed")
    workbench = getattr(part, "workbench", None)
    if isinstance(workbench, Mapping) and workbench:
        revision = workbench.get("current_revision") or {}
        properties = revision.get("production_properties") if isinstance(revision, Mapping) else None
        if not isinstance(properties, Mapping):
            issues.append("Actueel materiaalbewijs in de Part Workbench ontbreekt")
        else:
            expected = identities.get("normalized_material")
            for key in ("material", "material_grade"):
                value = properties.get(key)
                resolution = database.resolve(value)
                if not resolution.resolved or not expected or resolution.definition.code != expected:
                    issues.append(f"Part Workbench materiaalbewijs ontbreekt of wijkt af: {key}")
    return tuple(dict.fromkeys(issues))
