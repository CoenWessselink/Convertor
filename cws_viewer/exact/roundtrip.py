"""Format roundtrip evidence for the Exact Part Workbench.

The viewer never serializes production files directly from display geometry.
This service exports the exact canonical BREP through the existing CWS
converter modules, reimports the result, normalizes both shapes to their
confirmed/derived production frames and performs the deterministic exact
comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
from typing import Any, Callable

import cadquery as cq

from .catalog import build_exact_runtime, load_step_exact
from .compare import compare_exact_parts
from .model import CompareSeverity, ExactComparisonReport, ExactPartRuntime


class RoundtripState(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ExactRoundtripEvidence:
    format_name: str
    state: RoundtripState
    output_files: tuple[str, ...]
    comparison: ExactComparisonReport | None
    blocking_codes: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: tuple[tuple[str, str], ...] = ()

    @property
    def passed(self) -> bool:
        return self.state == RoundtripState.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_name": self.format_name,
            "state": self.state.value,
            "output_files": list(self.output_files),
            "comparison": None if self.comparison is None else self.comparison.to_dict(),
            "blocking_codes": list(self.blocking_codes),
            "warnings": list(self.warnings),
            "details": dict(self.details),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_runtime(runtime: ExactPartRuntime, *, part_id: str | None = None) -> ExactPartRuntime:
    """Return an exact runtime expressed in local production coordinates.

    CadQuery's :meth:`Plane.toLocalCoords` uses a rigid OCCT transformation and
    therefore preserves analytic circles, cylinders and BREP topology.  This
    is required for format roundtrips because NC1 and some STEP/IFC writers may
    legally choose a different world placement while preserving production
    geometry.
    """

    frame = runtime.snapshot.production_frame
    plane = cq.Plane(
        origin=frame.origin.to_tuple(),
        xDir=frame.x_axis.to_tuple(),
        normal=frame.z_axis.to_tuple(),
    )
    local_shape = plane.toLocalCoords(runtime.shape)
    # Production formats are allowed to choose a different world origin.
    # Normalize the exact local BREP to a zero-based bounding box so equal
    # manufacturing geometry compares independently of its source placement.
    box = local_shape.BoundingBox()
    local_shape = local_shape.translate(
        cq.Vector(-float(box.xmin), -float(box.ymin), -float(box.zmin))
    )
    return build_exact_runtime(
        local_shape,
        part_id=part_id or runtime.snapshot.part_id,
        source_name=f"{runtime.snapshot.source_name}:production-local",
    )


def compare_in_production_coordinates(
    source: ExactPartRuntime,
    target: ExactPartRuntime,
) -> ExactComparisonReport:
    return compare_exact_parts(
        normalized_runtime(source, part_id=source.snapshot.part_id),
        normalized_runtime(target, part_id=target.snapshot.part_id),
    )


class ExactRoundtripValidator:
    """Run strict STEP, NC1, converter-owned IFC and Trusted PDF roundtrips."""

    def __init__(self, canonical: ExactPartRuntime) -> None:
        self.canonical = canonical

    @staticmethod
    def _blocked(format_name: str, code: str, exc: Exception) -> ExactRoundtripEvidence:
        return ExactRoundtripEvidence(
            format_name=format_name,
            state=RoundtripState.BLOCKED,
            output_files=(),
            comparison=None,
            blocking_codes=(code,),
            warnings=(f"{type(exc).__name__}: {exc}",),
            details=(("error_type", type(exc).__name__),),
        )

    def _step_source(self, output: Path, stem: str = "canonical") -> Path:
        output.mkdir(parents=True, exist_ok=True)
        path = output / f"{stem}.step"
        cq.exporters.export(self.canonical.shape, str(path))
        return path

    def step(self, output_directory: str | Path) -> ExactRoundtripEvidence:
        output = Path(output_directory)
        try:
            step_path = self._step_source(output, "canonical_step")
            restored = load_step_exact(step_path, part_id=self.canonical.snapshot.part_id)
            comparison = compare_in_production_coordinates(self.canonical, restored)
            state = RoundtripState.PASS if comparison.overall == CompareSeverity.PASS else RoundtripState.FAIL
            codes = comparison.blocking_codes
            return ExactRoundtripEvidence(
                "STEP", state, (str(step_path),), comparison, codes,
                details=(("sha256", _sha256(step_path)), ("bytes", str(step_path.stat().st_size))),
            )
        except Exception as exc:
            return self._blocked("STEP", "CWS-EXACT-STEP-ROUNDTRIP-BLOCKED", exc)

    def nc1(
        self,
        output_directory: str | Path,
        *,
        material: str = "S235JR",
        preferred_profile: str = "",
    ) -> ExactRoundtripEvidence:
        output = Path(output_directory)
        try:
            from conversion import convert_nc1_to_step, step_to_nc1

            source_step = self._step_source(output, "canonical_nc1_source")
            nc1_path = output / "canonical.nc1"
            result = step_to_nc1(
                source_step,
                nc1_path,
                material=material,
                preferred_profile=preferred_profile,
                strict_validation=True,
            )
            restored_step = output / "canonical_from_nc1.step"
            convert_nc1_to_step(nc1_path, restored_step)
            restored = load_step_exact(restored_step, part_id=self.canonical.snapshot.part_id)
            comparison = compare_in_production_coordinates(self.canonical, restored)
            state = RoundtripState.PASS if comparison.overall == CompareSeverity.PASS else RoundtripState.FAIL
            codes = comparison.blocking_codes
            return ExactRoundtripEvidence(
                "NC1", state, (str(nc1_path), str(restored_step)), comparison, codes,
                warnings=tuple(getattr(result, "warnings", ()) or ()),
                details=(
                    ("nc1_sha256", _sha256(nc1_path)),
                    ("restored_step_sha256", _sha256(restored_step)),
                    ("profile", str(getattr(result, "profile_designation", ""))),
                    ("volume_delta_percent", str(getattr(result, "volume_delta_percent", ""))),
                ),
            )
        except Exception as exc:
            return self._blocked("NC1", "CWS-EXACT-NC1-ROUNDTRIP-BLOCKED", exc)

    def ifc(self, output_directory: str | Path, *, material: str = "S235JR") -> ExactRoundtripEvidence:
        output = Path(output_directory)
        try:
            from ifc_support import ifc_to_step, step_to_ifc

            source_step = self._step_source(output, "canonical_ifc_source")
            ifc_path = output / "canonical.ifc"
            exported = step_to_ifc(source_step, ifc_path, material=material)
            restored_step = output / "canonical_from_ifc.step"
            restored_result = ifc_to_step(ifc_path, restored_step)
            restored = load_step_exact(restored_step, part_id=self.canonical.snapshot.part_id)
            comparison = compare_in_production_coordinates(self.canonical, restored)
            state = RoundtripState.PASS if comparison.overall == CompareSeverity.PASS else RoundtripState.FAIL
            warnings = tuple(getattr(exported, "warnings", ()) or ()) + tuple(getattr(restored_result, "warnings", ()) or ())
            return ExactRoundtripEvidence(
                "IFC", state, (str(ifc_path), str(restored_step)), comparison, comparison.blocking_codes,
                warnings=warnings,
                details=(("ifc_sha256", _sha256(ifc_path)), ("restored_step_sha256", _sha256(restored_step))),
            )
        except Exception as exc:
            return self._blocked("IFC", "CWS-EXACT-IFC-ROUNDTRIP-BLOCKED", exc)

    def trusted_pdf(
        self,
        output_directory: str | Path,
        *,
        material: str = "S235JR",
        preferred_profile: str = "",
    ) -> ExactRoundtripEvidence:
        output = Path(output_directory)
        try:
            from pdf_support import load_trusted_pdf, pdf_to_step, step_to_pdf

            source_step = self._step_source(output, "canonical_pdf_source")
            pdf_path = output / "canonical_trusted.pdf"
            exported = step_to_pdf(
                source_step,
                pdf_path,
                material=material,
                preferred_profile=preferred_profile,
            )
            analysis = load_trusted_pdf(pdf_path, strict=True)
            restored_step = output / "canonical_from_pdf.step"
            restored_result = pdf_to_step(pdf_path, restored_step)
            restored = load_step_exact(restored_step, part_id=self.canonical.snapshot.part_id)
            comparison = compare_in_production_coordinates(self.canonical, restored)
            state = RoundtripState.PASS if comparison.overall == CompareSeverity.PASS else RoundtripState.FAIL
            warnings = tuple(getattr(exported, "warnings", ()) or ()) + tuple(getattr(restored_result, "warnings", ()) or ())
            return ExactRoundtripEvidence(
                "TRUSTED_PDF", state, (str(pdf_path), str(restored_step)), comparison, comparison.blocking_codes,
                warnings=warnings,
                details=(
                    ("pdf_sha256", _sha256(pdf_path)),
                    ("restored_step_sha256", _sha256(restored_step)),
                    ("pdf_mode", str(analysis.mode)),
                ),
            )
        except Exception as exc:
            return self._blocked("TRUSTED_PDF", "CWS-EXACT-TRUSTED-PDF-ROUNDTRIP-BLOCKED", exc)

    def run(
        self,
        output_directory: str | Path,
        *,
        formats: tuple[str, ...] = ("STEP", "NC1", "IFC", "TRUSTED_PDF"),
        material: str = "S235JR",
        preferred_profile: str = "",
    ) -> dict[str, ExactRoundtripEvidence]:
        output = Path(output_directory)
        methods: dict[str, Callable[[], ExactRoundtripEvidence]] = {
            "STEP": lambda: self.step(output / "step"),
            "NC1": lambda: self.nc1(output / "nc1", material=material, preferred_profile=preferred_profile),
            "IFC": lambda: self.ifc(output / "ifc", material=material),
            "TRUSTED_PDF": lambda: self.trusted_pdf(output / "trusted_pdf", material=material, preferred_profile=preferred_profile),
        }
        results: dict[str, ExactRoundtripEvidence] = {}
        for name in formats:
            key = str(name).upper()
            if key not in methods:
                raise ValueError(f"Onbekend roundtripformaat: {name}")
            results[key] = methods[key]()
        return results


__all__ = [
    "RoundtripState",
    "ExactRoundtripEvidence",
    "normalized_runtime",
    "compare_in_production_coordinates",
    "ExactRoundtripValidator",
]
