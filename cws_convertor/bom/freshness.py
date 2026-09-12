"""Bind a BOM view to canonical project content without audit/cache feedback."""
from __future__ import annotations

from copy import copy
from typing import Any


_BOM_CACHE_FIELDS = {"schema_version", "snapshot_sha256", "generated_at", "summary", "validation"}
_HUB_VIEW_FIELDS = {
    "history", "undo", "batch_results", "saved_selections", "smart_queries", "basket_entity_ids",
    "revision_baseline", "scoped_requests", "edit_intents", "viewer_reviews", "machine_reviews",
    "last_machine_review_action", "production_reviews", "export_reviews", "optimization_reviews",
}


def bom_source_content_sha256(project: Any) -> str:
    """Use the canonical revision fingerprint on a detached settings view.

    Unknown settings remain bound. Stock assignments, purchase orders, external
    releases, routing and machine evidence are business input, never audit noise.
    Only known UI bookkeeping and the derived snapshot cache are omitted.
    """
    detached = copy(project)
    settings = dict(project.settings)
    for name, ignored in (("bom", _BOM_CACHE_FIELDS), ("bom_production_hub", _HUB_VIEW_FIELDS)):
        if isinstance(settings.get(name), dict):
            value = {key: item for key, item in settings[name].items() if key not in ignored}
            if name == "bom_production_hub":
                # Opening the hub materialises these empty schema defaults.
                for key in ("stock_assignments", "purchase_orders", "external_releases"):
                    if not value.get(key):
                        value.pop(key, None)
            if value:
                settings[name] = value
            else:
                settings.pop(name, None)
    detached.settings = settings
    return detached.revision_content_sha256()


def require_current_bom_snapshot(snapshot: Any, project: Any) -> None:
    if snapshot is None or project is None or snapshot.project_id != project.project_id:
        raise ValueError("BOM en actief project komen niet overeen; bouw de BOM opnieuw op")
    source_hash = snapshot.summary.get("source_content_sha256")
    if not source_hash or source_hash != bom_source_content_sha256(project):
        raise ValueError("Projectinhoud is gewijzigd sinds de BOM-opbouw; bouw de BOM opnieuw op vóór deze actie")
    if not snapshot.snapshot_sha256 or copy(snapshot).refresh_hash() != snapshot.snapshot_sha256:
        raise ValueError("BOM-snapshot is gewijzigd of ongeldig; bouw de BOM opnieuw op vóór deze actie")
