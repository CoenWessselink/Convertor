"""Validation for immutable CWS Viewer scene documents."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
import hashlib
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from cws_viewer.errors import ViewerError, ViewerErrorCode

if TYPE_CHECKING:  # pragma: no cover
    from cws_viewer.contracts.scene import ProjectScene

_ALLOWED_PAYLOAD_SCHEMES = frozenset({"cache", "project", "memory", "file"})


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(values)
    return sorted(key for key, count in counts.items() if count > 1)


def validate_payload_reference(payload_ref: str) -> None:
    parsed = urlsplit(str(payload_ref))
    if not parsed.scheme or parsed.scheme not in _ALLOWED_PAYLOAD_SCHEMES:
        raise ViewerError(
            "Viewer-payload gebruikt een niet-toegestaan URI-schema",
            code=ViewerErrorCode.GEOMETRY_PAYLOAD_UNSAFE,
            context={"payload_ref": payload_ref, "allowed": sorted(_ALLOWED_PAYLOAD_SCHEMES)},
        )
    decoded_path = parsed.path.replace("\\", "/")
    decoded_netloc = parsed.netloc.replace("\\", "/")
    if any(part == ".." for part in [*decoded_netloc.split("/"), *decoded_path.split("/")]):
        raise ViewerError(
            "Viewer-payload bevat padtraversal",
            code=ViewerErrorCode.GEOMETRY_PAYLOAD_UNSAFE,
            context={"payload_ref": payload_ref},
        )


def _validate_parent_cycles(parent_by_node: dict[str, str | None]) -> None:
    for start in parent_by_node:
        current = start
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                raise ViewerError(
                    "Scene graph bevat een parentcyclus",
                    code=ViewerErrorCode.SCENE_CYCLE,
                    context={"start_node_id": start, "cycle_node_id": current},
                )
            seen.add(current)
            current = parent_by_node.get(current)


def validate_project_scene(scene: "ProjectScene", *, verify_hash: bool = True) -> None:
    model_ids = [item.model_id for item in scene.models]
    node_ids = [item.node_id for item in scene.nodes]
    entity_ids = [item.entity_id for item in scene.nodes if item.selectable]
    geometry_ids = [item.geometry_id for item in scene.geometry]
    style_ids = [item.style_id for item in scene.styles]

    for label, values in (
        ("model_id", model_ids),
        ("node_id", node_ids),
        ("selectable entity_id", entity_ids),
        ("geometry_id", geometry_ids),
        ("style_id", style_ids),
    ):
        duplicates = _duplicates(values)
        if duplicates:
            raise ViewerError(
                f"Scene bevat dubbele {label}-waarden",
                code=ViewerErrorCode.SCENE_DUPLICATE_ID,
                context={"field": label, "duplicates": duplicates[:20]},
            )

    node_set = set(node_ids)
    geometry_set = set(geometry_ids)
    style_set = set(style_ids)
    parent_by_node: dict[str, str | None] = {}

    for node in scene.nodes:
        parent_by_node[node.node_id] = node.parent_node_id
        if node.parent_node_id is not None and node.parent_node_id not in node_set:
            raise ViewerError(
                "SceneNode verwijst naar een ontbrekende parent",
                code=ViewerErrorCode.SCENE_REFERENCE_MISSING,
                context={"node_id": node.node_id, "parent_node_id": node.parent_node_id},
            )
        if node.geometry_id is not None and node.geometry_id not in geometry_set:
            raise ViewerError(
                "SceneNode verwijst naar ontbrekende geometry",
                code=ViewerErrorCode.SCENE_REFERENCE_MISSING,
                context={"node_id": node.node_id, "geometry_id": node.geometry_id},
            )
        if node.style_id is not None and node.style_id not in style_set:
            raise ViewerError(
                "SceneNode verwijst naar ontbrekende style",
                code=ViewerErrorCode.SCENE_REFERENCE_MISSING,
                context={"node_id": node.node_id, "style_id": node.style_id},
            )

    _validate_parent_cycles(parent_by_node)

    for model in scene.models:
        for root_node_id in model.root_node_ids:
            if root_node_id not in node_set:
                raise ViewerError(
                    "SceneModel verwijst naar een ontbrekende rootnode",
                    code=ViewerErrorCode.SCENE_REFERENCE_MISSING,
                    context={"model_id": model.model_id, "root_node_id": root_node_id},
                )

    for resource in scene.geometry:
        validate_payload_reference(resource.payload_ref)
        for lod in resource.lods:
            validate_payload_reference(lod.payload_ref)

    calculated = scene.calculate_hash() if verify_hash else scene.scene_hash
    if not scene.scene_hash or not calculated or calculated.lower() != scene.scene_hash.lower():
        raise ViewerError(
            "Scenehash komt niet overeen met de contractinhoud",
            code=ViewerErrorCode.SCENE_HASH_MISMATCH,
            context={"expected": calculated, "actual": scene.scene_hash},
        )


def verify_geometry_payloads(
    scene: "ProjectScene",
    resolver: Callable[[str], bytes],
    *,
    maximum_bytes: int = 2 * 1024 * 1024 * 1024,
) -> dict[str, int]:
    """Resolve and verify geometry payloads without trusting renderer paths."""

    checked = 0
    total_bytes = 0
    seen_refs: set[tuple[str, str]] = set()
    references: list[tuple[str, str, int]] = []
    for resource in scene.geometry:
        references.append((resource.payload_ref, resource.content_hash, resource.byte_length))
        references.extend((lod.payload_ref, lod.content_hash, lod.byte_length) for lod in resource.lods)

    for payload_ref, expected_hash, expected_length in references:
        key = (payload_ref, expected_hash.lower())
        if key in seen_refs:
            continue
        seen_refs.add(key)
        validate_payload_reference(payload_ref)
        payload = resolver(payload_ref)
        if not isinstance(payload, bytes):
            raise TypeError("Payloadresolver moet bytes retourneren")
        total_bytes += len(payload)
        if total_bytes > maximum_bytes:
            raise ViewerError(
                "Viewer-payloadlimiet overschreden",
                code=ViewerErrorCode.GEOMETRY_PAYLOAD_UNSAFE,
                context={"total_bytes": total_bytes, "maximum_bytes": maximum_bytes},
            )
        if expected_length and len(payload) != expected_length:
            raise ViewerError(
                "Viewer-payloadgrootte wijkt af",
                code=ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                context={
                    "payload_ref": payload_ref,
                    "expected_length": expected_length,
                    "actual_length": len(payload),
                },
            )
        actual_hash = hashlib.sha256(payload).hexdigest()
        if actual_hash.lower() != expected_hash.lower():
            raise ViewerError(
                "Viewer-payloadhash wijkt af",
                code=ViewerErrorCode.GEOMETRY_HASH_MISMATCH,
                context={
                    "payload_ref": payload_ref,
                    "expected": expected_hash,
                    "actual": actual_hash,
                },
            )
        checked += 1

    return {"payload_count": checked, "total_bytes": total_bytes}


__all__ = ["validate_project_scene", "verify_geometry_payloads", "validate_payload_reference"]
