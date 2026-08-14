"""Application service for Exact Part Workbench review and validation gates."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from cws_viewer.math3d import Vector3

from .compare import compare_exact_parts
from .model import (
    CompareSeverity,
    ExactComparisonReport,
    ExactPartRuntime,
    ProductionFrame,
    ReferenceFace,
    WorkbenchStatus,
)


def _stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ExactPartWorkbenchService:
    def __init__(
        self,
        source: ExactPartRuntime,
        canonical: ExactPartRuntime | None = None,
        *,
        owner_manufacturing_hash: str = "",
    ) -> None:
        self.source = source
        self.canonical = canonical
        self.owner_manufacturing_hash = str(owner_manufacturing_hash or "").lower()
        self.selected_subshape_id: str | None = None
        self.comparison: ExactComparisonReport | None = None
        self.roundtrips: dict[str, Any] = {}
        self.audit: list[dict[str, str]] = []

    def select_subshape(self, stable_id: str | None) -> None:
        if stable_id is not None and stable_id not in self.source.snapshot.subshape_by_id:
            raise KeyError(stable_id)
        self.selected_subshape_id = stable_id

    def set_canonical(self, runtime: ExactPartRuntime, *, user: str = "", reason: str = "") -> None:
        self.canonical = runtime
        self.comparison = None
        self.roundtrips.clear()
        self.audit.append({"action": "set_canonical", "user": user, "reason": reason})

    def confirm_frame(self, *, user: str, reason: str) -> None:
        if not user.strip() or not reason.strip():
            raise ValueError("Framebevestiging vereist gebruiker en reden")
        frame = replace(self.source.snapshot.production_frame, confirmed=True, source="reviewed")
        self.source.snapshot = replace(self.source.snapshot, production_frame=frame)
        self.audit.append({"action": "confirm_frame", "user": user, "reason": reason})

    def set_frame(self, origin: Vector3, x_axis: Vector3, y_axis: Vector3, z_axis: Vector3, *, user: str, reason: str) -> None:
        if not user.strip() or not reason.strip():
            raise ValueError("Framewijziging vereist gebruiker en reden")
        frame = ProductionFrame(origin, x_axis, y_axis, z_axis, source="manual", confirmed=True)
        self.source.snapshot = replace(self.source.snapshot, production_frame=frame)
        self.audit.append({"action": "set_frame", "user": user, "reason": reason})

    def confirm_reference_face(self, role: str, face_id: str, *, user: str, reason: str) -> None:
        descriptor = self.source.snapshot.subshape_by_id.get(face_id)
        if descriptor is None or descriptor.kind.value != "face" or descriptor.normal is None:
            raise ValueError("Reference face moet een bestaand exact vlak zijn")
        if not user.strip() or not reason.strip():
            raise ValueError("Referentiezijdebevestiging vereist gebruiker en reden")
        refs = [item for item in self.source.snapshot.reference_faces if item.role != role]
        refs.append(ReferenceFace(role, face_id, descriptor.normal, True, "manual", user))
        refs.sort(key=lambda item: item.role)
        self.source.snapshot = replace(self.source.snapshot, reference_faces=tuple(refs))
        self.audit.append({"action": "confirm_reference_face", "user": user, "reason": reason, "role": role, "face_id": face_id})

    def validate(self) -> ExactComparisonReport:
        if self.canonical is None:
            raise ValueError("Geen canonical BREP beschikbaar")
        self.comparison = compare_exact_parts(self.source, self.canonical)
        status = WorkbenchStatus.GEOMETRY_VALIDATED if self.comparison.overall == CompareSeverity.PASS else WorkbenchStatus.BLOCKED
        self.source.snapshot = replace(self.source.snapshot, status=status)
        return self.comparison


    def run_roundtrips(
        self,
        output_directory: str | Path,
        *,
        formats: tuple[str, ...] = ("STEP", "NC1", "IFC", "TRUSTED_PDF"),
        material: str = "S235JR",
        preferred_profile: str = "",
    ) -> dict[str, Any]:
        if self.canonical is None:
            raise ValueError("Geen canonical BREP beschikbaar")
        from .roundtrip import ExactRoundtripValidator

        results = ExactRoundtripValidator(self.canonical).run(
            output_directory,
            formats=formats,
            material=material,
            preferred_profile=preferred_profile,
        )
        self.roundtrips.update(results)
        self.audit.append({
            "action": "run_roundtrips",
            "user": "system",
            "reason": ", ".join(f"{name}={item.state.value}" for name, item in results.items()),
        })
        return dict(results)

    def format_gates(self) -> dict[str, dict[str, Any]]:
        base = self.gate()
        result: dict[str, dict[str, Any]] = {
            "REVIEW_PDF": {
                "allowed": True,
                "blocking_codes": [],
                "warnings": base["blocking_codes"],
            },
            "PRODUCTION_PDF": {
                "allowed": False,
                "blocking_codes": ["CWS-EXACT-VIEWER-CANNOT-RELEASE-PRODUCTION"],
                "warnings": base["blocking_codes"],
            },
        }
        for name in ("STEP", "NC1", "IFC", "TRUSTED_PDF"):
            evidence = self.roundtrips.get(name)
            review_codes = list(base["review_blocking_codes"])
            if evidence is None:
                review_codes.append(f"CWS-EXACT-{name.replace('_', '-')}-ROUNDTRIP-NOT-RUN")
            elif not evidence.passed:
                review_codes.extend(evidence.blocking_codes or (f"CWS-EXACT-{name.replace('_', '-')}-ROUNDTRIP-FAILED",))
            review_ready = not review_codes
            result[name] = {
                "review_ready": review_ready,
                "allowed": False,
                "production_release_allowed": False,
                "blocking_codes": list(
                    dict.fromkeys(
                        [*review_codes, "CWS-EXACT-VIEWER-CANNOT-RELEASE-PRODUCTION"]
                    )
                ),
                "review_blocking_codes": list(dict.fromkeys(review_codes)),
                "warnings": [] if evidence is None else list(evidence.warnings),
            }
        return result

    def manufacturing_hash(self, **_legacy_arguments: str) -> str:
        """Return the identity supplied by the authoritative owner model."""

        digest = self.owner_manufacturing_hash
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise RuntimeError(
                "Manufacturing identity is owned by CWS Convertor; "
                "the viewer cannot calculate it independently"
            )
        return digest

    def gate(self) -> dict[str, Any]:
        codes: list[str] = []
        frame = self.source.snapshot.production_frame
        if not frame.confirmed:
            codes.append("CWS-EXACT-FRAME-UNCONFIRMED")
        required_roles = {"top", "start"}
        confirmed_roles = {item.role for item in self.source.snapshot.reference_faces if item.confirmed}
        for role in sorted(required_roles - confirmed_roles):
            codes.append(f"CWS-EXACT-REFERENCE-{role.upper()}-UNCONFIRMED")
        if self.canonical is None:
            codes.append("CWS-EXACT-CANONICAL-MISSING")
        if self.comparison is None:
            codes.append("CWS-EXACT-COMPARE-NOT-RUN")
        elif self.comparison.overall != CompareSeverity.PASS:
            codes.extend(self.comparison.blocking_codes)
        if self.source.snapshot.unresolved_questions:
            codes.append("CWS-EXACT-QUESTIONS-UNRESOLVED")
        review_ready = not codes
        production_codes = list(
            dict.fromkeys([*codes, "CWS-EXACT-VIEWER-CANNOT-RELEASE-PRODUCTION"])
        )
        return {
            "review_ready": review_ready,
            "production_ready": False,
            "blocking_codes": production_codes,
            "review_blocking_codes": list(dict.fromkeys(codes)),
            "status": "pass" if review_ready else "blocked",
        }


__all__ = ["ExactPartWorkbenchService"]
