"""V15 T5 review workspace service.

Saved views, markups and issues live in review state only.  The service never
changes Canonical Project Model geometry and never releases manufacturing data.
References that no longer resolve after a revision are flagged as stale rather
than silently remapped or deleted.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable

from cws_viewer.contracts.workspace import viewpoint_from_dict
from cws_viewer.core.serialization import stable_sha256
from cws_viewer.version import VIEWER_PREVIEW_VERSION

from .model import (
    MarkupAnchor,
    MarkupKind,
    MarkupRecord,
    ReviewAttachment,
    ReviewIssue,
    ReviewPriority,
    ReviewSeverity,
    ReviewStatus,
)
from .package import ReviewPackageBuilder
from .store import ReviewStore
from .bcf import Bcf21Exporter

V15_T5_SCHEMA = "cws-viewer-review-workspace-15.4"
V15_T5_VERSION = VIEWER_PREVIEW_VERSION


class ReferenceState(StrEnum):
    VALID = "valid"
    STALE = "stale"
    UNLINKED = "unlinked"


@dataclass(frozen=True, slots=True)
class ReviewReferenceHealth:
    issue_id: str
    state: ReferenceState
    missing_entity_ids: tuple[str, ...] = ()
    missing_markup_ids: tuple[str, ...] = ()
    missing_viewpoint_id: str | None = None
    stale_markup_ids: tuple[str, ...] = ()

    @property
    def is_stale(self) -> bool:
        return self.state is ReferenceState.STALE

    def to_dict(self) -> dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "state": self.state.value,
            "missing_entity_ids": list(self.missing_entity_ids),
            "missing_markup_ids": list(self.missing_markup_ids),
            "missing_viewpoint_id": self.missing_viewpoint_id,
            "stale_markup_ids": list(self.stale_markup_ids),
        }


def review_workspace_contract() -> dict[str, Any]:
    return {
        "schema": V15_T5_SCHEMA,
        "version": V15_T5_VERSION,
        "capabilities": {
            "saved_views_independent_from_issues": True,
            "saved_view_camera_visibility_sections_clipping": True,
            "markup_text": True,
            "markup_arrow": True,
            "markup_cloud": True,
            "markup_freehand_contract": True,
            "issues": True,
            "issue_status": True,
            "issue_priority": True,
            "issue_assignee": True,
            "issue_due_date": True,
            "issue_comments": True,
            "issue_attachments": True,
            "issue_optional_viewpoint_link": True,
            "review_checksum_store": True,
            "portable_cwsreview_export": True,
            "bcf_2_1_schema_validated_export": True,
            "stale_reference_detection": True,
            "silent_reference_remap": False,
            "review_mutates_canonical_geometry": False,
            "viewer_can_release_machine_output": False,
        },
    }


class V15ReviewWorkspaceService:
    def __init__(
        self,
        controller: Any,
        *,
        project_id: str,
        scene_hash: str,
        store_path: str | Path | None = None,
        project_metadata: dict[str, Any] | None = None,
    ) -> None:
        self.controller = controller
        self.project_id = str(project_id)
        self.scene_hash = str(scene_hash)
        self.store_path = None if store_path is None else Path(store_path)
        self.project_metadata = dict(project_metadata or {})
        self.markups: dict[str, MarkupRecord] = {}
        self.issues: dict[str, ReviewIssue] = {}
        self.loaded_scene_hash: str | None = None

    @property
    def review_hash(self) -> str:
        return stable_sha256(
            {
                "project_id": self.project_id,
                "scene_hash": self.loaded_scene_hash or self.scene_hash,
                "markups": [item.to_dict() for item in self.list_markups()],
                "issues": [item.to_dict() for item in self.list_issues()],
                "viewpoints": [item.viewpoint_id for item in self.controller.list_viewpoints()],
            }
        )

    def list_markups(self) -> tuple[MarkupRecord, ...]:
        return tuple(
            sorted(self.markups.values(), key=lambda item: (item.created_utc, item.markup_id))
        )

    def list_issues(self) -> tuple[ReviewIssue, ...]:
        return tuple(
            sorted(
                self.issues.values(),
                key=lambda item: (item.status, item.priority, item.title.casefold(), item.issue_id),
            )
        )

    def selected_entity_ids(self) -> tuple[str, ...]:
        index = self.controller.index
        values: list[str] = []
        for node_id in self.controller.get_selection():
            try:
                entity = str(index.node(node_id).entity_id or "")
            except Exception:
                entity = ""
            if entity:
                values.append(entity)
        return tuple(dict.fromkeys(values))

    def capture_view(self, name: str, *, owner: str = "") -> Any:
        return self.controller.save_viewpoint(str(name), owner=str(owner))

    def delete_view(self, viewpoint_id: str) -> None:
        # Intentional: issues are NOT deleted/rewritten here. Their optional
        # viewpoint link becomes stale and is reported by reference_health().
        self.controller.delete_viewpoint(str(viewpoint_id))

    def create_markup_from_pick(
        self,
        pick: Any,
        *,
        kind: MarkupKind | str = MarkupKind.TEXT,
        text: str = "",
        created_by: str = "",
        color: str = "#0b5bd3",
    ) -> MarkupRecord:
        node = self.controller.index.node(str(pick.node_id))
        point = pick.world_point
        anchor = MarkupAnchor(
            entity_id=str(pick.entity_id or node.entity_id or "") or None,
            node_id=str(pick.node_id),
            feature_id=(None if getattr(pick, "feature_id", None) in {None, ""} else str(pick.feature_id)),
            world_point_mm=(float(point.x), float(point.y), float(point.z)),
            geometry_hash=(None if not node.geometry_hash else str(node.geometry_hash)),
            evidence="display_pick",
        )
        markup = MarkupRecord.create(
            kind,
            text=str(text),
            anchors=(anchor,),
            world_points_mm=(anchor.world_point_mm,) if anchor.world_point_mm else (),
            created_by=str(created_by),
            color=str(color),
        )
        self.markups[markup.markup_id] = markup
        return markup

    def delete_markup(self, markup_id: str) -> None:
        self.markups.pop(str(markup_id), None)
        # Keep issue markup IDs unchanged. Missing markup references must remain
        # visible as stale evidence after review edits/revisions.

    def create_issue(
        self,
        title: str,
        *,
        description: str = "",
        severity: ReviewSeverity | str = ReviewSeverity.INFO,
        priority: ReviewPriority | str = ReviewPriority.NORMAL,
        created_by: str = "",
        linked_entity_ids: Iterable[str] | None = None,
        markup_ids: Iterable[str] = (),
        viewpoint_id: str | None = None,
        due_date_utc: str | None = None,
        tags: Iterable[str] = (),
    ) -> ReviewIssue:
        entities = self.selected_entity_ids() if linked_entity_ids is None else tuple(linked_entity_ids)
        issue = ReviewIssue.create(
            title,
            description=description,
            severity=severity,
            priority=priority,
            created_by=created_by,
            linked_entity_ids=entities,
            markup_ids=markup_ids,
            viewpoint_id=viewpoint_id,
            due_date_utc=due_date_utc,
            tags=tags,
        )
        self.issues[issue.issue_id] = issue
        return issue

    def delete_issue(self, issue_id: str) -> None:
        # Saved views and markups are independent review objects and remain.
        self.issues.pop(str(issue_id), None)

    def issue(self, issue_id: str) -> ReviewIssue:
        return self.issues[str(issue_id)]

    def set_status(self, issue_id: str, status: ReviewStatus | str, *, actor: str) -> None:
        self.issue(issue_id).set_status(status, actor=actor)

    def set_priority(self, issue_id: str, priority: ReviewPriority | str, *, actor: str) -> None:
        self.issue(issue_id).set_priority(priority, actor=actor)

    def assign(self, issue_id: str, user: str, *, actor: str) -> None:
        self.issue(issue_id).assign(user, actor=actor)

    def set_due_date(self, issue_id: str, due_date_utc: str | None, *, actor: str) -> None:
        self.issue(issue_id).set_due_date(due_date_utc, actor=actor)

    def add_comment(self, issue_id: str, author: str, text: str) -> None:
        self.issue(issue_id).add_comment(author, text)

    def link_viewpoint(self, issue_id: str, viewpoint_id: str | None, *, actor: str) -> None:
        self.issue(issue_id).link_viewpoint(viewpoint_id, actor=actor)

    def add_attachment(
        self,
        issue_id: str,
        path: str | Path,
        *,
        actor: str,
        media_type: str = "application/octet-stream",
    ) -> ReviewAttachment:
        attachment = ReviewAttachment.from_path(
            path, added_by=actor, media_type=media_type
        )
        self.issue(issue_id).add_attachment(attachment, actor=actor)
        return attachment

    def _existing_entity_ids(self) -> set[str]:
        return {
            str(node.entity_id)
            for node in self.controller.index.nodes_by_id.values()
            if node.entity_id not in {None, ""}
        }

    def _markup_is_stale(self, markup: MarkupRecord) -> bool:
        existing_nodes = set(self.controller.index.nodes_by_id)
        existing_entities = self._existing_entity_ids()
        for anchor in markup.anchors:
            if anchor.node_id and anchor.node_id not in existing_nodes:
                return True
            if anchor.entity_id and anchor.entity_id not in existing_entities:
                return True
            if anchor.node_id and anchor.geometry_hash:
                try:
                    current = str(self.controller.index.node(anchor.node_id).geometry_hash or "")
                except Exception:
                    return True
                if current and current != anchor.geometry_hash:
                    return True
        return False

    def reference_health(self, issue_id: str) -> ReviewReferenceHealth:
        issue = self.issue(issue_id)
        existing_entities = self._existing_entity_ids()
        missing_entities = tuple(
            sorted(entity for entity in issue.linked_entity_ids if entity not in existing_entities)
        )
        missing_markups = tuple(
            sorted(markup_id for markup_id in issue.markup_ids if markup_id not in self.markups)
        )
        stale_markups = tuple(
            sorted(
                markup_id
                for markup_id in issue.markup_ids
                if markup_id in self.markups and self._markup_is_stale(self.markups[markup_id])
            )
        )
        viewpoint_ids = {item.viewpoint_id for item in self.controller.list_viewpoints()}
        missing_view = (
            issue.viewpoint_id
            if issue.viewpoint_id and issue.viewpoint_id not in viewpoint_ids
            else None
        )
        stale = bool(missing_entities or missing_markups or stale_markups or missing_view)
        linked = bool(issue.linked_entity_ids or issue.markup_ids or issue.viewpoint_id)
        return ReviewReferenceHealth(
            issue_id=issue.issue_id,
            state=(
                ReferenceState.STALE
                if stale
                else (ReferenceState.VALID if linked else ReferenceState.UNLINKED)
            ),
            missing_entity_ids=missing_entities,
            missing_markup_ids=missing_markups,
            missing_viewpoint_id=missing_view,
            stale_markup_ids=stale_markups,
        )

    def reference_health_all(self) -> tuple[ReviewReferenceHealth, ...]:
        return tuple(self.reference_health(issue.issue_id) for issue in self.list_issues())

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.store_path
        if target is None:
            raise ValueError("Geen review store-pad ingesteld")
        self.store_path = target
        return ReviewStore(target).save(
            project_id=self.project_id,
            scene_hash=self.scene_hash,
            markups=self.list_markups(),
            issues=self.list_issues(),
            viewpoints=self.controller.list_viewpoints(),
            metadata={
                **self.project_metadata,
                "review_hash": self.review_hash,
                "production_machine_transfer_allowed": False,
            },
        )

    def load(self, path: str | Path | None = None) -> dict[str, Any]:
        target = Path(path) if path is not None else self.store_path
        if target is None:
            raise ValueError("Geen review store-pad ingesteld")
        data = ReviewStore(target).load(expected_project_id=self.project_id)
        self.store_path = target
        self.loaded_scene_hash = str(data.get("scene_hash") or "")
        self.markups = {
            item.markup_id: item
            for item in (MarkupRecord.from_dict(raw) for raw in data.get("markups", ()))
        }
        self.issues = {
            item.issue_id: item
            for item in (ReviewIssue.from_dict(raw) for raw in data.get("issues", ()))
        }
        loaded_views = tuple(viewpoint_from_dict(raw) for raw in data.get("viewpoints", ()))
        if loaded_views:
            current = self.controller.export_workspace_state()
            merged = {item.viewpoint_id: item for item in current.viewpoints}
            merged.update({item.viewpoint_id: item for item in loaded_views})
            state = replace(current, viewpoints=tuple(merged.values()), state_hash="")
            state = replace(state, state_hash=state.calculate_hash())
            self.controller.restore_workspace_state(state, allow_scene_mismatch=True)
        return {
            "project_id": self.project_id,
            "stored_scene_hash": self.loaded_scene_hash,
            "current_scene_hash": self.scene_hash,
            "exact_scene_match": self.loaded_scene_hash == self.scene_hash,
            "issues": len(self.issues),
            "markups": len(self.markups),
            "viewpoints": len(loaded_views),
            "stale_issues": sum(1 for item in self.reference_health_all() if item.is_stale),
        }

    def export_package(
        self,
        output_path: str | Path,
        *,
        assets_root: str | Path | None = None,
    ) -> Path:
        project = {
            "project_id": self.project_id,
            "scene_hash": self.scene_hash,
            **self.project_metadata,
        }
        return ReviewPackageBuilder().build(
            output_path,
            project=project,
            issues=self.list_issues(),
            markups=self.list_markups(),
            viewpoints=self.controller.list_viewpoints(),
            assets_root=assets_root,
        )

    def export_bcf(
        self,
        output_path: str | Path,
        *,
        ifc_guid_by_entity: dict[str, str] | None = None,
    ) -> Path:
        """Export review issues as an XSD-validated buildingSMART BCF 2.1 archive."""
        # Native IFC scenes already preserve GlobalId as the scene entity identity.
        # Merge that information (and optional project-adapter metadata) so the UI
        # export path never silently drops BCF component selections merely because
        # its caller did not construct a second lookup table.
        valid_ifc_chars = frozenset("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$")

        def is_ifc_guid(value: object) -> bool:
            text = str(value or "")
            return len(text) == 22 and all(character in valid_ifc_chars for character in text)

        resolved_mapping: dict[str, str] = {}
        metadata_mapping = self.project_metadata.get("ifc_guid_by_entity", {})
        if isinstance(metadata_mapping, dict):
            resolved_mapping.update(
                (str(entity), str(guid))
                for entity, guid in metadata_mapping.items()
                if is_ifc_guid(guid)
            )
        for node in self.controller.index.nodes_by_id.values():
            for candidate in (node.entity_id, node.source_entity_id):
                if is_ifc_guid(candidate):
                    resolved_mapping.setdefault(str(node.entity_id), str(candidate))
                    resolved_mapping.setdefault(str(node.node_id), str(candidate))
        if ifc_guid_by_entity:
            resolved_mapping.update(
                (str(entity), str(guid))
                for entity, guid in ifc_guid_by_entity.items()
                if is_ifc_guid(guid)
            )
        return Bcf21Exporter().export(
            output_path,
            project_id=self.project_id,
            issues=self.list_issues(),
            viewpoints=self.controller.list_viewpoints(),
            ifc_guid_by_entity=resolved_mapping,
        )


__all__ = [
    "ReferenceState",
    "ReviewReferenceHealth",
    "V15ReviewWorkspaceService",
    "V15_T5_SCHEMA",
    "V15_T5_VERSION",
    "review_workspace_contract",
]
