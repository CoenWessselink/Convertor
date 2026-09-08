"""Bind assembly solids to their actual component materials without guessing.

Assembly-wide material is intentionally empty. Each IFC element receives only
its source component's exact catalog identity, verified against OCCT topology.
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import re
from typing import Any

from material_database import MaterialDatabase
from ifc_native import _entity_blocks, _escape_ifc, _guid22, _split_ifc_args


def bind_component_materials(
    path: Path, compound: Any, components: Sequence[tuple[str, Any, Any]]
) -> None:
    """Assign grades to native IFC solids by exact OCCT shape identity.

    Input is (component mark, placed shape, released canonical part). Unknown,
    conflicting, missing, duplicate or unmatched component evidence is rejected.
    Nothing is inferred from color, tessellation, dimensions or file ordering.
    """
    catalog = MaterialDatabase()
    source = path.read_text(encoding="utf-8")
    if list(_entity_blocks(source, ("IFCRELASSOCIATESMATERIAL",))):
        raise ValueError("Assembly material must be component-bound, not inherited")
    owners: list[tuple[str, Any, str]] = []
    for mark, shape, canonical in components:
        values = (canonical.material, canonical.product.material_code, canonical.product.material_grade)
        resolved = [catalog.resolve(value) for value in values]
        if any(not result.resolved for result in resolved):
            raise ValueError(f"Missing or unknown exact material for assembly component {mark}")
        identities = {result.definition.code for result in resolved}
        if len(identities) != 1:
            raise ValueError(f"Conflicting materials for assembly component {mark}")
        solids = list(shape.Solids())
        if not solids:
            raise ValueError(f"Assembly component {mark} has no exact solid")
        owners.extend((str(mark), solid, next(iter(identities))) for solid in solids)
    solids = list(compound.Solids())
    elements = list(_entity_blocks(source, ("IFCPLATE", "IFCMEMBER", "IFCBEAM")))
    if not owners or len(owners) != len(solids) or len(elements) != len(solids):
        raise ValueError("Assembly solid/component/IFC element counts differ")
    bindings: list[tuple[int, str, str]] = []
    for solid, (element_id, entity_type, block) in zip(solids, elements):
        matches = [index for index, (_, owner, _) in enumerate(owners) if solid.isSame(owner)]
        if len(matches) != 1:
            raise ValueError("Assembly solid has missing or ambiguous component identity")
        mark, _, material = owners.pop(matches[0])
        arguments = _split_ifc_args(block)
        if len(arguments) != 9:
            raise ValueError("Unexpected IFC element schema")
        arguments[2] = arguments[7] = "'" + _escape_ifc(mark) + "'"
        original = f"#{element_id}={entity_type}{block};"
        if source.count(original) != 1:
            raise ValueError("IFC element identity is not unique")
        source = source.replace(original, f"#{element_id}={entity_type}({','.join(arguments)});", 1)
        bindings.append((element_id, mark, material))
    if owners:
        raise ValueError("Unassigned assembly components")
    next_id = max(map(int, re.findall(r"#(\d+)\s*=", source))) + 1
    lines: list[str] = []
    material_ids: dict[str, int] = {}
    for _, _, material in bindings:
        if material not in material_ids:
            material_ids[material] = next_id
            lines.append(f"#{next_id}=IFCMATERIAL('{_escape_ifc(material)}',$,$);")
            next_id += 1
    for element_id, mark, material in bindings:
        guid = _guid22(f"{element_id}:{mark}:{material}:material")
        lines.append(f"#{next_id}=IFCRELASSOCIATESMATERIAL('{guid}',#5,$,$,(#{element_id}),#{material_ids[material]});")
        next_id += 1
    marker = "ENDSEC;\nEND-ISO-10303-21;"
    if source.count(marker) != 1:
        raise ValueError("Invalid IFC closing section")
    path.write_text(source.replace(marker, "\n".join(lines) + "\n" + marker, 1), encoding="utf-8", newline="\n")
