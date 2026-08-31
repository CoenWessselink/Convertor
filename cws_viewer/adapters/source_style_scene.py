"""Apply verified source presentation styles to the immutable viewer scene."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from cws_viewer.adapters.project_model import CwsProjectSceneAdapter
from cws_viewer.adapters.source_appearance import IfcAppearanceResolver
from cws_viewer.adapters.source_geometry import ProjectGeometryCatalog
from cws_viewer.contracts.enums import RenderMode
from cws_viewer.contracts.scene import ProjectScene, StyleDefinition
from cws_viewer.math3d import Rgba


class SourceAppearanceProjectSceneAdapter(CwsProjectSceneAdapter):
    """Decorate the normal canonical scene with source-owned display colours.

    Geometry, IDs, hierarchy and manufacturing hashes still come from the base
    CWS adapter. Only ``SceneNode.style_id`` and display styles are enriched.
    IFC objects without an explicit presentation colour receive a neutral IFC
    fallback instead of an arbitrary CWS category colour.
    """

    _IFC_NEUTRAL_STYLE_ID = "style-source-ifc-neutral"

    @staticmethod
    def _style_id(color: Any) -> str:
        rgba = tuple(
            int(round(max(0.0, min(1.0, float(value))) * 255.0))
            for value in (color.red, color.green, color.blue, color.alpha)
        )
        return "style-source-ifc-" + "".join(f"{value:02x}" for value in rgba)

    def build_scene(self, project: Any, options: Any = None, **kwargs: Any) -> ProjectScene:
        geometry_catalog = kwargs.get("geometry_catalog")
        enrich_source_appearance = bool(kwargs.pop("enrich_source_appearance", True))
        scene = super().build_scene(project, options, **kwargs)
        if not enrich_source_appearance:
            return scene
        report = self.last_report
        if geometry_catalog is None:
            return scene

        documents = dict(getattr(geometry_catalog, "_documents", {}) or {})
        resolvers: dict[str, IfcAppearanceResolver] = {}
        appearance_cache: dict[tuple[str, tuple[str, ...]], Any] = {}
        styles = {style.style_id: style for style in scene.styles}
        styles.setdefault(
            self._IFC_NEUTRAL_STYLE_ID,
            StyleDefinition(
                style_id=self._IFC_NEUTRAL_STYLE_ID,
                color=Rgba(0.58, 0.59, 0.60, 1.0),
                mode=RenderMode.SHADED_EDGES,
                line_width=0.65,
                tags=("source-presentation", "ifc-no-explicit-colour", "neutral-fallback"),
            ),
        )
        nodes = []
        changed = 0

        for node in scene.nodes:
            record = geometry_catalog.record_for_entity(str(node.entity_id))
            if record is None or str(record.source_format).upper() != "IFC":
                nodes.append(node)
                continue
            source_id = str(record.source_file_id)
            document = documents.get(source_id)
            if document is None:
                nodes.append(replace(node, style_id=self._IFC_NEUTRAL_STYLE_ID))
                changed += 1
                continue
            resolver = resolvers.get(source_id)
            if resolver is None:
                resolver = IfcAppearanceResolver(document)
                resolvers[source_id] = resolver
            source_item_ids = tuple(record.source_item_ids)
            if not source_item_ids:
                # Proxy-first catalogues intentionally skip the expensive IFC
                # dependency walk, so canonical descriptors can contain no
                # representation-item IDs.  Once the verified document is
                # available after exact loading, derive those IDs from the
                # immutable source entity instead of leaving the node neutral.
                _representation_id, source_item_ids, _geometry_hash = (
                    ProjectGeometryCatalog._ifc_items(
                        document,
                        str(record.source_entity_id),
                    )
                )
            key = (source_id, tuple(source_item_ids))
            if key not in appearance_cache:
                appearance_cache[key] = resolver.color_for_items(source_item_ids)
            appearance = appearance_cache[key]
            if appearance is None:
                nodes.append(replace(node, style_id=self._IFC_NEUTRAL_STYLE_ID))
                changed += 1
                continue

            style_id = self._style_id(appearance.color)
            if style_id not in styles:
                styles[style_id] = StyleDefinition(
                    style_id=style_id,
                    color=appearance.color,
                    mode=RenderMode.SHADED_EDGES,
                    line_width=0.65,
                    tags=(
                        "source-presentation",
                        "ifc-original-colour",
                        appearance.provenance,
                        appearance.source_style_id,
                    ),
                )
            nodes.append(replace(node, style_id=style_id))
            changed += 1

        if not changed:
            return scene

        enriched = ProjectScene.create(
            project_id=scene.project_id,
            revision_id=scene.revision_id,
            models=scene.models,
            nodes=tuple(nodes),
            geometry=scene.geometry,
            styles=tuple(styles.values()),
        )
        self.last_report = report
        return enriched


__all__ = ["SourceAppearanceProjectSceneAdapter"]
