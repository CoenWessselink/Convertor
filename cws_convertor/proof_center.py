"""Central validation and blocker-navigation contract for the Proof Center."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
from typing import Any

PROOF_CATEGORIES = ("geometry", "source_compare", "conversion", "drawing", "trusted_pdf", "manufacturing_faces", "contact", "marks", "machine_capability", "profile_nesting", "plate_nesting", "sequence", "export", "quality", "release")


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProofEvidence:
    evidence_id: str
    category: str
    status: str
    evidence_sha256: str
    workspace: str
    entity_id: str = ""
    feature_id: str = ""
    run_id: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        if self.category not in PROOF_CATEGORIES or self.status not in {"PASS", "FAIL", "BLOCKED", "STALE"} or len(self.evidence_sha256) != 64:
            raise ValueError("invalid proof evidence category/status/hash")


@dataclass
class ProofBlocker:
    blocker_id: str
    category: str
    code: str
    message: str
    workspace: str
    entity_id: str = ""
    feature_id: str = ""
    run_id: str = ""
    viewer_selection_ids: tuple[str, ...] = ()
    resolved: bool = False


@dataclass
class ProofCenter:
    evidence: dict[str, list[ProofEvidence]] = field(default_factory=dict)
    blockers: dict[str, ProofBlocker] = field(default_factory=dict)

    def record(self, item: ProofEvidence) -> None:
        values = [value for value in self.evidence.get(item.category, []) if value.evidence_id != item.evidence_id]
        self.evidence[item.category] = [*values, item]

    def add_blocker(self, blocker: ProofBlocker) -> None:
        if blocker.category not in PROOF_CATEGORIES or not blocker.blocker_id or not blocker.workspace:
            raise ValueError("proof blocker navigation is incomplete")
        self.blockers[blocker.blocker_id] = blocker

    def resolve(self, blocker_id: str) -> None:
        self.blockers[blocker_id].resolved = True

    def unresolved_blockers(self) -> tuple[ProofBlocker, ...]:
        return tuple(item for item in self.blockers.values() if not item.resolved)

    def navigation_target(self, blocker_id: str) -> dict[str, Any]:
        item = self.blockers[blocker_id]
        return {"workspace": item.workspace, "entity_id": item.entity_id, "feature_id": item.feature_id, "run_id": item.run_id, "viewer_selection_ids": list(item.viewer_selection_ids)}

    @property
    def release_allowed(self) -> bool:
        return not self.unresolved_blockers() and all(any(item.status == "PASS" for item in self.evidence.get(category, [])) for category in PROOF_CATEGORIES)

    @property
    def proof_sha256(self) -> str:
        return _digest(self.to_dict(include_hash=False))

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = {"schema": "cws-proof-center-1.0", "evidence": {key: [asdict(item) for item in values] for key, values in sorted(self.evidence.items())}, "blockers": {key: asdict(item) for key, item in sorted(self.blockers.items())}}
        if include_hash:
            payload["proof_sha256"] = _digest(payload)
        return payload

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProofCenter":
        center = cls({key: [ProofEvidence(**dict(item)) for item in values] for key, values in dict(value.get("evidence") or {}).items()}, {key: ProofBlocker(**dict(item)) for key, item in dict(value.get("blockers") or {}).items()})
        if value.get("proof_sha256") and value["proof_sha256"] != center.proof_sha256:
            raise ValueError("proof-center hash mismatch")
        return center


__all__ = ["PROOF_CATEGORIES", "ProofBlocker", "ProofCenter", "ProofEvidence"]
