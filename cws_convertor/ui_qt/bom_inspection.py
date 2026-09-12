"""Read-only, exact-entity details for the existing BOM inspector actions."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from cws_convertor.project.model import sha256_file

INSPECTION_ACTIONS = {"inspect.source", "inspect.assembly", "inspect.hashes"}


def inspect_entities(workspace: Any, action: str, entity_ids: tuple[str, ...]) -> dict[str, Any]:
    if action not in INSPECTION_ACTIONS:
        raise ValueError("Onbekende specifieke inspectieactie")
    ids = tuple(dict.fromkeys(entity_ids))
    project = workspace.project
    if not ids or any(not isinstance(key, str) or not key or project.get_entity(key) is None for key in ids):
        raise ValueError("Inspectie vereist bestaande geselecteerde canonieke IDs")
    records = []
    lines = [{"inspect.source": "Bronobjecten", "inspect.assembly": "Assemblycontext", "inspect.hashes": "Geometrie- en productiehashes"}[action]]
    source_hashes = {}
    for key in ids:
        entity = project.get_entity(key)
        record: dict[str, Any] = {"entity_id": key}
        lines.extend(("", f"Object: {key} · {entity.name or key}"))
        if action == "inspect.source":
            identity = asdict(entity.source_identity)
            source = project.sources.get(identity["source_file_id"])
            candidate = getattr(workspace.session, "source_paths", {}).get(identity["source_file_id"])
            if candidate is None and source is not None and source.original_path:
                candidate = source.original_path
            actual = ""
            path = Path(candidate) if candidate else None
            binding = "UNAVAILABLE"
            if path is not None:
                try:
                    resolved = str(path.resolve())
                    if resolved not in source_hashes:
                        source_hashes[resolved] = sha256_file(path)
                    actual = source_hashes[resolved]
                    expected = identity["source_sha256"]
                    binding = "MATCH" if source is not None and expected and actual == expected == source.sha256 else "CHANGED_OR_UNBOUND"
                except OSError:
                    binding = "UNAVAILABLE"
            record.update(source_identity=identity, source_file=str(path) if path else None,
                          actual_source_sha256=actual or None, binding=binding)
            lines.extend((
                f"Bronformaat: {identity['source_format'] or 'onbekend'}",
                f"Bronbestand-ID: {identity['source_file_id'] or 'niet gekoppeld'}",
                f"Bronobject-ID: {identity['source_entity_id'] or 'niet gekoppeld'}",
                f"GUID: {identity['global_id'] or '-'} · Occurrence: {identity['occurrence_id'] or '-'}",
                f"Bronbestand: {path or 'niet beschikbaar'}",
                f"Vastgelegde bron-SHA256: {identity['source_sha256'] or 'onbekend'}",
                f"Gelezen bron-SHA256: {actual or 'niet beschikbaar'}",
                f"Bronbinding: {binding} · inspectie verleent geen productieautoriteit",
            ))
        elif action == "inspect.assembly":
            memberships = tuple(getattr(entity, "assembly_ids", ()) or ())
            member_parts = tuple(getattr(entity, "part_ids", ()) or ())
            children = tuple(getattr(entity, "child_assembly_ids", ()) or ())
            parents = tuple(sorted(assembly.internal_id for assembly in project.assemblies.values()
                                   if key in assembly.part_ids or key in assembly.child_assembly_ids))
            links = {assembly_id: (assembly_id in project.assemblies and key in project.assemblies[assembly_id].part_ids)
                     for assembly_id in memberships}
            record.update(assembly_ids=list(memberships), parent_assembly_ids=list(parents),
                          part_ids=list(member_parts), child_assembly_ids=list(children), reciprocal_memberships=links)
            lines.extend((
                "Vastgelegde assemblies: " + (", ".join(memberships) or "geen"),
                "Ouderassemblies: " + (", ".join(parents) or "geen"),
                "Directe onderdelen: " + (", ".join(member_parts) or "geen"),
                "Subassemblies: " + (", ".join(children) or "geen"),
                "Wederkerige koppelingen: " + (", ".join(f"{identity}={'correct' if valid else 'inconsistent'}" for identity, valid in links.items()) or "niet van toepassing"),
                "Context getoond; de selectie is niet uitgebreid naar assemblyleden.",
            ))
        else:
            geometry = str(getattr(entity, "geometry_hash", "") or "")
            manufacturing = str(getattr(entity, "manufacturing_hash", "") or "")
            record.update(geometry_hash=geometry, manufacturing_hash=manufacturing,
                          source_sha256=entity.source_identity.source_sha256)
            lines.extend((f"Geometrie-SHA256: {geometry or 'niet beschikbaar'}",
                          f"Productie-SHA256: {manufacturing or 'niet beschikbaar'}",
                          f"Bron-SHA256: {entity.source_identity.source_sha256 or 'niet beschikbaar'}",
                          "Canonieke objecthashes; geen bewijs van machinekwalificatie of productievrijgave."))
        records.append(record)
    return {"action_id": action, "entity_ids": list(ids), "records": records, "text": "\n".join(lines),
            "production_release_allowed": False, "selection_widened": False}
