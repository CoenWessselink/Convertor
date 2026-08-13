"""Dependency-free numeric primitives used by the viewer API."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, TypeAlias

from cws_viewer.api.errors import ViewerContractError
from ._validation import finite_float

Vector3: TypeAlias = tuple[float, float, float]
Rgba: TypeAlias = tuple[float, float, float, float]
Matrix4: TypeAlias = tuple[
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
    tuple[float, float, float, float],
]

IDENTITY_MATRIX4: Matrix4 = (
    (1.0, 0.0, 0.0, 0.0),
    (0.0, 1.0, 0.0, 0.0),
    (0.0, 0.0, 1.0, 0.0),
    (0.0, 0.0, 0.0, 1.0),
)


def vector3(value: Iterable[object], label: str = "vector") -> Vector3:
    values = tuple(finite_float(item, label) for item in value)
    if len(values) != 3:
        raise ViewerContractError(f"{label} moet exact drie waarden bevatten")
    return values  # type: ignore[return-value]


def rgba(value: Iterable[object], label: str = "kleur") -> Rgba:
    values = tuple(finite_float(item, label) for item in value)
    if len(values) != 4:
        raise ViewerContractError(f"{label} moet exact vier waarden bevatten")
    if any(item < 0.0 or item > 1.0 for item in values):
        raise ViewerContractError(f"{label} moet waarden tussen 0 en 1 bevatten")
    return values  # type: ignore[return-value]


def matrix4(value: Iterable[Iterable[object]], label: str = "transform") -> Matrix4:
    rows = tuple(
        tuple(finite_float(item, f"{label}[{row_index}]") for item in row)
        for row_index, row in enumerate(value)
    )
    if len(rows) != 4 or any(len(row) != 4 for row in rows):
        raise ViewerContractError(f"{label} moet een 4x4-matrix zijn")
    if any(abs(rows[3][index] - expected) > 1e-9 for index, expected in enumerate((0.0, 0.0, 0.0, 1.0))):
        raise ViewerContractError(f"{label} moet een affine 4x4-matrix zijn")
    determinant = (
        rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
        - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
        + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0])
    )
    if determinant <= 1e-12:
        raise ViewerContractError(f"{label} moet eindig, niet-singulier en rechtshandig zijn")
    return rows  # type: ignore[return-value]


def nonzero_vector3(value: Iterable[object], label: str) -> Vector3:
    result = vector3(value, label)
    if math.sqrt(sum(component * component for component in result)) <= 1e-12:
        raise ViewerContractError(f"{label} mag geen nulvector zijn")
    return result


@dataclass(frozen=True, slots=True)
class BoundingBox:
    minimum: Vector3
    maximum: Vector3

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum", vector3(self.minimum, "bounding_box.minimum"))
        object.__setattr__(self, "maximum", vector3(self.maximum, "bounding_box.maximum"))
        if any(low > high for low, high in zip(self.minimum, self.maximum)):
            raise ViewerContractError("bounding_box.minimum ligt buiten maximum")

    def to_dict(self) -> dict[str, Any]:
        return {"minimum": list(self.minimum), "maximum": list(self.maximum)}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BoundingBox":
        return cls(minimum=value["minimum"], maximum=value["maximum"])


__all__ = [
    "BoundingBox",
    "IDENTITY_MATRIX4",
    "Matrix4",
    "Rgba",
    "Vector3",
    "matrix4",
    "nonzero_vector3",
    "rgba",
    "vector3",
]
