"""Atomic persistence for Exact Part Workbench review state."""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

from cws_viewer.math3d import Vector3

from .model import ProductionFrame, ReferenceFace


def _stable_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _vec(value: Iterable[float]) -> Vector3:
    return Vector3.from_iterable(value)


@dataclass(frozen=True, slots=True)
class ExactReviewAudit:
    action: str
    user: str
    reason: str
    timestamp: str
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class ExactPartReviewState:
    part_id: str
    source_sha256: str
    exact_geometry_hash: str
    production_frame: ProductionFrame
    reference_faces: tuple[ReferenceFace, ...]
    selected_subshape_id: str | None = None
    unresolved_questions: tuple[str, ...] = ()
    audit: tuple[ExactReviewAudit, ...] = ()
    schema_version: str = "cws-exact-review-1.0"
    state_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "reference_faces", tuple(self.reference_faces))
        object.__setattr__(self, "unresolved_questions", tuple(self.unresolved_questions))
        object.__setattr__(self, "audit", tuple(self.audit))

    def payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "part_id": self.part_id,
            "source_sha256": self.source_sha256,
            "exact_geometry_hash": self.exact_geometry_hash,
            "production_frame": self.production_frame.to_dict(),
            "reference_faces": [
                {
                    "role": item.role,
                    "face_id": item.face_id,
                    "normal": item.normal.to_tuple(),
                    "confirmed": item.confirmed,
                    "provenance": item.provenance,
                    "reviewer": item.reviewer,
                }
                for item in self.reference_faces
            ],
            "selected_subshape_id": self.selected_subshape_id,
            "unresolved_questions": list(self.unresolved_questions),
            "audit": [
                {
                    "action": item.action,
                    "user": item.user,
                    "reason": item.reason,
                    "timestamp": item.timestamp,
                    "details": dict(item.details),
                }
                for item in self.audit
            ],
        }

    def with_hash(self) -> "ExactPartReviewState":
        return replace(self, state_hash=_stable_hash(self.payload()))

    def to_dict(self) -> dict[str, Any]:
        value = self.payload()
        value["state_hash"] = self.state_hash or _stable_hash(value)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactPartReviewState":
        frame = value["production_frame"]
        state = cls(
            part_id=str(value["part_id"]),
            source_sha256=str(value["source_sha256"]),
            exact_geometry_hash=str(value["exact_geometry_hash"]),
            production_frame=ProductionFrame(
                origin=_vec(frame["origin"]), x_axis=_vec(frame["x_axis"]),
                y_axis=_vec(frame["y_axis"]), z_axis=_vec(frame["z_axis"]),
                source=str(frame.get("source", "review")), confirmed=bool(frame.get("confirmed", False)),
            ),
            reference_faces=tuple(
                ReferenceFace(
                    role=str(item["role"]), face_id=str(item["face_id"]),
                    normal=_vec(item["normal"]), confirmed=bool(item.get("confirmed", False)),
                    provenance=str(item.get("provenance", "review")), reviewer=str(item.get("reviewer", "")),
                )
                for item in value.get("reference_faces", ())
            ),
            selected_subshape_id=value.get("selected_subshape_id"),
            unresolved_questions=tuple(str(item) for item in value.get("unresolved_questions", ())),
            audit=tuple(
                ExactReviewAudit(
                    action=str(item["action"]), user=str(item.get("user", "")),
                    reason=str(item.get("reason", "")), timestamp=str(item.get("timestamp", "")),
                    details=tuple((str(k), str(v)) for k, v in dict(item.get("details", {})).items()),
                )
                for item in value.get("audit", ())
            ),
            schema_version=str(value.get("schema_version", "cws-exact-review-1.0")),
            state_hash=str(value.get("state_hash", "")),
        )
        expected = _stable_hash(state.payload())
        if state.state_hash != expected:
            raise ValueError("Exact Part review state hash klopt niet")
        return state


class ExactReviewStore:
    @staticmethod
    def save(state: ExactPartReviewState, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        state = state.with_hash()
        data = json.dumps(state.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")
        with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
            handle.write(data)
            temp = Path(handle.name)
        os.replace(temp, output)
        output.with_suffix(output.suffix + ".sha256").write_text(hashlib.sha256(data).hexdigest() + "\n", encoding="ascii")
        return output

    @staticmethod
    def load(path: str | Path) -> ExactPartReviewState:
        source = Path(path)
        data = source.read_bytes()
        sidecar = source.with_suffix(source.suffix + ".sha256")
        if sidecar.is_file():
            expected = sidecar.read_text(encoding="ascii").strip().split()[0]
            actual = hashlib.sha256(data).hexdigest()
            if actual != expected:
                raise ValueError("Exact Part review bestandchecksum klopt niet")
        return ExactPartReviewState.from_dict(json.loads(data.decode("utf-8")))


__all__ = ["ExactReviewAudit", "ExactPartReviewState", "ExactReviewStore"]
