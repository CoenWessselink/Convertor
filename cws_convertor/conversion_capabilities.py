"""Compatibility view over the central conversion planner.

New code must use :mod:`cws_convertor.conversion_service` directly. This
adapter retains the former registry API without maintaining a second policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from cws_convertor.conversion_service import (
    DEFAULT_CONVERSION_PLANNER,
    ROUTES,
    ConversionSource,
)


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


CAPABILITIES = tuple(
    ConversionCapability(
        route.source_format,
        route.target_format,
        route.direction,
        "part_or_assembly_package",
        ("plate", "profile", "round_bar"),
        ("hole", "outer_contour"),
        "central_target_specific_preflight",
        route.serializer,
        route.reimport_validator,
    )
    for route in ROUTES
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
        source = {"NC": "NC1", "DSTV": "NC1", "STP": "STEP"}.get(source, source)
        descriptor = ConversionSource(
            source_path="compatibility-preflight",
            source_format=source,
            source_sha256="",
            exact_source=bool(exact_source),
            trusted_payload=source == "NC1",
            part_form=str(part_form or "").lower(),
            features=tuple(str(value).lower() for value in features if str(value)),
            solid_count=1,
        )
        results = []
        by_direction = {item.direction: item for item in self.capabilities}
        for route in ROUTES:
            if route.source_format != source or route.direction not in by_direction:
                continue
            plan = DEFAULT_CONVERSION_PLANNER.plan_source(descriptor, route.direction)
            capability = by_direction[route.direction]
            unsupported = sorted(set(descriptor.features) - set(capability.supported_features))
            reasons = list(() if plan.executable else plan.blockers or (plan.status.value,))
            reasons.extend(f"unsupported_feature:{value}" for value in unsupported)
            results.append((capability, tuple(dict.fromkeys(reasons))))
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
