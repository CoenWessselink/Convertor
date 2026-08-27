"""Single fail-closed capability registry for engineering conversions."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ConversionCapability:
    source_format: str
    target_format: str
    direction: str
    entity_scope: str
    part_forms: tuple[str, ...]
    supported_features: tuple[str, ...]
    exactness_requirement: str
    backend: str
    roundtrip_validator: str
    blockers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# The current physical serializers can only prove a semantic re-import for
# plain holes across every advertised family.  Richer workbench features stay
# canonical and visible, but are deliberately blocked until their target
# serializer and re-import comparator prove them losslessly.
_EXACT_FEATURES = ("hole",)


CAPABILITIES = (
    ConversionCapability("NC1", "STEP", "nc1-step", "part", ("plate", "profile"), ("hole",), "semantic_nc1", "canonical_roundtrip", "step_reimport"),
    ConversionCapability("NC1", "IFC", "nc1-ifc", "part", ("plate", "profile"), ("hole",), "semantic_nc1", "canonical_roundtrip", "ifc_reimport"),
    ConversionCapability("STEP", "NC1", "step-nc1", "part", ("plate", "profile"), ("hole",), "exact_native_brep", "canonical_roundtrip", "nc1_reimport"),
    ConversionCapability("STEP", "IFC", "step-ifc", "part", ("plate", "profile", "round_bar"), _EXACT_FEATURES, "exact_native_brep", "canonical_roundtrip", "ifc_reimport"),
    ConversionCapability("IFC", "STEP", "ifc-step", "part", ("plate", "profile", "round_bar"), _EXACT_FEATURES, "exact_part_geometry", "canonical_roundtrip", "step_reimport", ("triangulated_ifc_is_review_only",)),
    ConversionCapability("IFC", "NC1", "ifc-nc1", "part", ("plate", "profile"), ("hole",), "exact_part_geometry", "canonical_roundtrip", "nc1_reimport", ("triangulated_ifc_is_review_only",)),
    ConversionCapability("PDF", "STEP", "pdf-step", "part", ("plate", "profile", "round_bar"), _EXACT_FEATURES, "trusted_pdf_payload", "canonical_roundtrip", "step_reimport"),
    ConversionCapability("PDF", "NC1", "pdf-nc1", "part", ("plate", "profile"), ("hole",), "trusted_pdf_payload", "canonical_roundtrip", "nc1_reimport"),
    ConversionCapability("PDF", "IFC", "pdf-ifc", "part", ("plate", "profile", "round_bar"), _EXACT_FEATURES, "trusted_pdf_payload", "canonical_roundtrip", "ifc_reimport"),
)


class ConversionCapabilityRegistry:
    def __init__(self, capabilities: Iterable[ConversionCapability] = CAPABILITIES) -> None:
        self.capabilities = tuple(capabilities)

    def evaluate(
        self,
        *,
        source_format: str,
        part_form: str = "",
        features: Iterable[str] = (),
        exact_source: bool = True,
    ) -> tuple[tuple[ConversionCapability, tuple[str, ...]], ...]:
        source = str(source_format or "").upper().lstrip(".")
        feature_set = {str(value).lower() for value in features if str(value)}
        results = []
        for capability in self.capabilities:
            if capability.source_format != source:
                continue
            blockers = list(capability.blockers)
            if part_form and part_form not in capability.part_forms:
                blockers.append(f"part_form:{part_form}")
            unsupported = sorted(feature_set - set(capability.supported_features))
            blockers.extend(f"unsupported_feature:{value}" for value in unsupported)
            if capability.exactness_requirement in {"exact_native_brep", "exact_part_geometry"} and not exact_source:
                blockers.append("exact_source_geometry_required")
            results.append((capability, tuple(dict.fromkeys(blockers))))
        return tuple(results)

    def available_directions(self, **context: object) -> tuple[str, ...]:
        return tuple(
            capability.direction
            for capability, blockers in self.evaluate(**context)
            if not blockers
        )


DEFAULT_CAPABILITY_REGISTRY = ConversionCapabilityRegistry()


__all__ = [
    "CAPABILITIES",
    "ConversionCapability",
    "ConversionCapabilityRegistry",
    "DEFAULT_CAPABILITY_REGISTRY",
]
