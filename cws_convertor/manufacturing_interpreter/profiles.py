from __future__ import annotations

from typing import Any, Iterable

from .contracts import CrossSectionSignature, GeometryProofStatus, ProfileRecognition
from .topology import linear_tolerance, relative_tolerance


def profile_definitions(database: Any) -> tuple[Any, ...]:
    for name in ("profiles", "definitions", "items", "_profiles", "_definitions"):
        value = getattr(database, name, None)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if isinstance(value, dict):
            return tuple(value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return tuple(value)
    return ()


def _candidate_dimensions(profile: Any) -> tuple[float, float]:
    kind = str(getattr(profile, "profile_type", "")).upper()
    first = abs(float(getattr(profile, "dim1", 0.0) or 0.0))
    second = abs(float(getattr(profile, "dim2", 0.0) or 0.0))
    if kind in {"RU", "RO"}:
        return (first, first)
    return tuple(sorted((first, second), reverse=True))


def recognize_profile(
    section: CrossSectionSignature,
    database: Any,
    policy: Any,
    preferred_profile: str = "",
) -> ProfileRecognition:
    definitions = profile_definitions(database)
    preferred = preferred_profile.strip().upper()
    family = section.inferred_family.upper()
    compatible = []
    for profile in definitions:
        designation = str(getattr(profile, "designation", ""))
        profile_type = str(getattr(profile, "profile_type", "")).upper()
        profile_family = str(getattr(profile, "family", "")).upper()
        if preferred and designation.upper() != preferred:
            continue
        if family not in {profile_type, profile_family}:
            continue
        expected_width, expected_height = _candidate_dimensions(profile)
        dim_delta = max(
            abs(section.width_mm - expected_width),
            abs(section.height_mm - expected_height),
        )
        expected_area = abs(float(getattr(profile, "area_mm2", 0.0) or 0.0))
        area_delta = abs(section.area_mm2 - expected_area) if expected_area else 0.0
        dim_allowed = max(
            linear_tolerance(policy),
            max(expected_width, expected_height) * relative_tolerance(policy),
        )
        area_allowed = max(
            linear_tolerance(policy) ** 2,
            expected_area * relative_tolerance(policy),
        ) if expected_area else float("inf")
        score = max(dim_delta / dim_allowed, area_delta / area_allowed)
        compatible.append((score, designation, profile, dim_delta, area_delta))

    compatible.sort(key=lambda item: (item[0], item[1]))
    if not compatible:
        return ProfileRecognition(
            status=GeometryProofStatus.RECOGNITION_INCOMPLETE,
            family=family,
            reason="Geen geometrisch compatibel catalogusprofiel in de bestaande ProfileDatabase",
        )

    best = compatible[0]
    accepted = best[0] <= 1.0
    ambiguous = (
        accepted
        and len(compatible) > 1
        and compatible[1][0] <= 1.0
        and abs(compatible[1][0] - best[0]) <= 1e-12
    )
    if ambiguous:
        return ProfileRecognition(
            status=GeometryProofStatus.AMBIGUOUS,
            family=family,
            candidates=tuple(item[1] for item in compatible if item[0] <= 1.0),
            reason="Meerdere catalogusprofielen zijn geometrisch niet onderscheidbaar",
        )
    if not accepted:
        return ProfileRecognition(
            status=GeometryProofStatus.RECOGNITION_INCOMPLETE,
            family=family,
            dimension_delta_mm=best[3],
            area_delta_mm2=best[4],
            candidates=tuple(item[1] for item in compatible[:5]),
            reason="Beste catalogusprofiel valt buiten het centrale tolerantiebeleid",
        )

    profile = best[2]
    confidence = max(0.0, min(1.0, 1.0 - best[0]))
    return ProfileRecognition(
        status=GeometryProofStatus.PROVEN_WITHIN_POLICY,
        designation=best[1],
        profile_type=str(getattr(profile, "profile_type", "")),
        family=str(getattr(profile, "family", "")) or family,
        confidence=confidence,
        dimension_delta_mm=best[3],
        area_delta_mm2=best[4],
        candidates=(best[1],),
        reason="Geometrie matcht exact binnen de centrale tolerance policy",
    )

