"""Deterministic production-oriented canonical plate editor.

This is intentionally not a free CAD modeler.  It supports a bounded set of
reviewable plate parameters and round holes.  Every modification is audited,
undoable and produces a fresh exact canonical BREP plus manufacturing hash.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import datetime as dt
import hashlib
import json
from typing import Any

from .builders import PlateDefinition, RoundHole, build_plate
from .catalog import build_exact_runtime
from .model import ExactPartRuntime


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True, slots=True)
class EditAuditEntry:
    timestamp: str
    user: str
    action: str
    reason: str
    before: str
    after: str


class CanonicalPlateEditor:
    def __init__(self, definition: PlateDefinition, *, part_id: str, material: str = "", profile: str = "") -> None:
        self.part_id = str(part_id)
        self.material = material.strip().upper()
        self.profile = profile.strip().upper()
        self.definition = definition
        self.audit: list[EditAuditEntry] = []
        self._undo: list[PlateDefinition] = []
        self._redo: list[PlateDefinition] = []

    @staticmethod
    def _definition_json(definition: PlateDefinition) -> str:
        payload = {
            "length_x": definition.length_x,
            "width_y": definition.width_y,
            "thickness_z": definition.thickness_z,
            "holes": [
                {"center_x": item.center_x, "center_y": item.center_y, "diameter": item.diameter}
                for item in definition.holes
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _apply(self, definition: PlateDefinition, *, user: str, action: str, reason: str) -> None:
        if not user.strip() or not reason.strip():
            raise ValueError("Canonical wijziging vereist gebruiker en reden")
        before = self._definition_json(self.definition)
        after = self._definition_json(definition)
        if before == after:
            return
        self._undo.append(self.definition)
        if len(self._undo) > 100:
            del self._undo[0]
        self._redo.clear()
        self.definition = definition
        self.audit.append(EditAuditEntry(_utc(), user.strip(), action, reason.strip(), before, after))

    def set_dimensions(self, *, length_x: float, width_y: float, thickness_z: float, user: str, reason: str) -> None:
        self._apply(
            PlateDefinition(float(length_x), float(width_y), float(thickness_z), self.definition.holes),
            user=user, action="plate.dimensions.changed", reason=reason,
        )

    def add_hole(self, hole: RoundHole, *, user: str, reason: str) -> None:
        self._apply(
            PlateDefinition(self.definition.length_x, self.definition.width_y, self.definition.thickness_z, self.definition.holes + (hole,)),
            user=user, action="hole.added", reason=reason,
        )

    def update_hole(self, index: int, hole: RoundHole, *, user: str, reason: str) -> None:
        values = list(self.definition.holes)
        values[int(index)] = hole
        self._apply(
            PlateDefinition(self.definition.length_x, self.definition.width_y, self.definition.thickness_z, tuple(values)),
            user=user, action="hole.updated", reason=reason,
        )

    def remove_hole(self, index: int, *, user: str, reason: str) -> None:
        values = list(self.definition.holes)
        del values[int(index)]
        self._apply(
            PlateDefinition(self.definition.length_x, self.definition.width_y, self.definition.thickness_z, tuple(values)),
            user=user, action="hole.removed", reason=reason,
        )

    def undo(self, *, user: str = "system") -> bool:
        if not self._undo:
            return False
        current = self.definition
        previous = self._undo.pop()
        self._redo.append(current)
        before = self._definition_json(current)
        after = self._definition_json(previous)
        self.definition = previous
        self.audit.append(EditAuditEntry(_utc(), user, "editor.undo", "Undo canonical edit", before, after))
        return True

    def redo(self, *, user: str = "system") -> bool:
        if not self._redo:
            return False
        current = self.definition
        following = self._redo.pop()
        self._undo.append(current)
        before = self._definition_json(current)
        after = self._definition_json(following)
        self.definition = following
        self.audit.append(EditAuditEntry(_utc(), user, "editor.redo", "Redo canonical edit", before, after))
        return True

    def runtime(self) -> ExactPartRuntime:
        return build_exact_runtime(build_plate(self.definition), part_id=self.part_id, source_name="canonical_plate_editor")

    def review_geometry_fingerprint(self) -> str:
        payload = {
            "schema": "cws-viewer-review-geometry-v1",
            "definition": json.loads(self._definition_json(self.definition)),
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def manufacturing_hash(self) -> str:
        raise RuntimeError(
            "Manufacturing identity is owned by CWS Convertor; "
            "use review_geometry_fingerprint() for viewer undo/redo tests"
        )


__all__ = ["EditAuditEntry", "CanonicalPlateEditor"]
