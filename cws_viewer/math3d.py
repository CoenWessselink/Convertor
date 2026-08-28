"""Small immutable math contracts for the viewer API.

These types deliberately avoid leaking renderer-specific vector/matrix classes
across the application boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .errors import ViewerError, ViewerErrorCode

_EPS = 1e-12


def _finite(value: float, *, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ViewerError(
            f"{label} bevat een niet-eindige waarde",
            code=ViewerErrorCode.TRANSFORM_INVALID,
            context={"label": label, "value": repr(value)},
        )
    return result


@dataclass(frozen=True, slots=True)
class Vector3:
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, label="Vector3.x"))
        object.__setattr__(self, "y", _finite(self.y, label="Vector3.y"))
        object.__setattr__(self, "z", _finite(self.z, label="Vector3.z"))

    @classmethod
    def zero(cls) -> "Vector3":
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def from_iterable(cls, values: Iterable[float]) -> "Vector3":
        data = tuple(values)
        if len(data) != 3:
            raise ValueError("Vector3 vereist exact drie waarden")
        return cls(*data)

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self * scalar

    def __truediv__(self, scalar: float) -> "Vector3":
        divisor = float(scalar)
        if abs(divisor) <= _EPS:
            raise ZeroDivisionError("Vector3 kan niet door nul worden gedeeld")
        return self * (1.0 / divisor)

    def __neg__(self) -> "Vector3":
        return Vector3(-self.x, -self.y, -self.z)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self) -> "Vector3":
        length = self.length()
        if length <= _EPS:
            raise ValueError("Nulvector kan niet worden genormaliseerd")
        return self * (1.0 / length)

    def almost_equal(self, other: "Vector3", *, tolerance: float = 1e-9) -> bool:
        return (self - other).length() <= float(tolerance)

    def rotated_about_axis(self, axis: "Vector3", angle_radians: float) -> "Vector3":
        """Rotate this vector using Rodrigues' formula."""

        unit = axis.normalized()
        angle = float(angle_radians)
        cosine = math.cos(angle)
        sine = math.sin(angle)
        return (
            self * cosine
            + unit.cross(self) * sine
            + unit * (unit.dot(self) * (1.0 - cosine))
        )


@dataclass(frozen=True, slots=True)
class Matrix4:
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        data = tuple(_finite(v, label="Matrix4") for v in self.values)
        if len(data) != 16:
            raise ViewerError(
                "Matrix4 vereist exact zestien waarden",
                code=ViewerErrorCode.TRANSFORM_INVALID,
                context={"value_count": len(data)},
            )
        object.__setattr__(self, "values", data)
        if not self.is_affine():
            raise ViewerError(
                "Viewertransform is geen geldige affiene 4×4-matrix",
                code=ViewerErrorCode.TRANSFORM_INVALID,
                context={"last_row": list(data[12:16])},
            )
        determinant = self.determinant3()
        if determinant <= _EPS:
            raise ViewerError(
                "Viewertransform moet rechtsgeldig en niet-singulier zijn",
                code=ViewerErrorCode.TRANSFORM_INVALID,
                context={"determinant": determinant},
            )

    @classmethod
    def identity(cls) -> "Matrix4":
        return cls(
            (
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
                0.0,
                0.0,
                0.0,
                0.0,
                1.0,
            )
        )

    @classmethod
    def translation(cls, offset: Vector3) -> "Matrix4":
        return cls.from_rows(
            (
                (1.0, 0.0, 0.0, offset.x),
                (0.0, 1.0, 0.0, offset.y),
                (0.0, 0.0, 1.0, offset.z),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

    @classmethod
    def from_rows(cls, rows: Sequence[Sequence[float]]) -> "Matrix4":
        if len(rows) != 4 or any(len(row) != 4 for row in rows):
            raise ValueError("Matrix4.from_rows vereist vier rijen met vier waarden")
        # CWS Project Model stores row-major matrices.  Keep that convention at
        # the contract boundary; renderers may transpose internally.
        return cls(tuple(float(value) for row in rows for value in row))

    def to_rows(self) -> tuple[tuple[float, float, float, float], ...]:
        return tuple(
            tuple(self.values[row * 4 : (row + 1) * 4])  # type: ignore[misc]
            for row in range(4)
        )

    def is_affine(self, tolerance: float = 1e-9) -> bool:
        row = self.values[12:16]
        return (
            abs(row[0]) <= tolerance
            and abs(row[1]) <= tolerance
            and abs(row[2]) <= tolerance
            and abs(row[3] - 1.0) <= tolerance
        )

    def determinant3(self) -> float:
        m = self.values
        return (
            m[0] * (m[5] * m[10] - m[6] * m[9])
            - m[1] * (m[4] * m[10] - m[6] * m[8])
            + m[2] * (m[4] * m[9] - m[5] * m[8])
        )

    def __matmul__(self, other: "Matrix4") -> "Matrix4":
        a = self.to_rows()
        b = other.to_rows()
        rows = tuple(
            tuple(sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4))
            for row in range(4)
        )
        return Matrix4.from_rows(rows)

    def inverse_rigid(self, *, tolerance: float = 1e-8) -> "Matrix4":
        """Return the inverse of a right-handed rigid transform.

        Project placements are expected to be rotations plus translation.  We
        reject scale/shear here instead of silently producing a wrong parent-
        relative transform for the scene graph.
        """

        rows = self.to_rows()
        axes = (
            Vector3(rows[0][0], rows[1][0], rows[2][0]),
            Vector3(rows[0][1], rows[1][1], rows[2][1]),
            Vector3(rows[0][2], rows[1][2], rows[2][2]),
        )
        for index, axis in enumerate(axes):
            if abs(axis.length() - 1.0) > tolerance:
                raise ViewerError(
                    "Viewertransform bevat schaal en kan niet als rigid transform worden geïnverteerd",
                    code=ViewerErrorCode.TRANSFORM_INVALID,
                    context={"axis": index, "length": axis.length()},
                )
        if any(abs(axes[a].dot(axes[b])) > tolerance for a, b in ((0, 1), (0, 2), (1, 2))):
            raise ViewerError(
                "Viewertransform bevat shear en kan niet als rigid transform worden geïnverteerd",
                code=ViewerErrorCode.TRANSFORM_INVALID,
            )
        rotation_t = (
            (rows[0][0], rows[1][0], rows[2][0]),
            (rows[0][1], rows[1][1], rows[2][1]),
            (rows[0][2], rows[1][2], rows[2][2]),
        )
        t = self.translation_vector
        tx = -(rotation_t[0][0] * t.x + rotation_t[0][1] * t.y + rotation_t[0][2] * t.z)
        ty = -(rotation_t[1][0] * t.x + rotation_t[1][1] * t.y + rotation_t[1][2] * t.z)
        tz = -(rotation_t[2][0] * t.x + rotation_t[2][1] * t.y + rotation_t[2][2] * t.z)
        return Matrix4.from_rows(
            (
                (*rotation_t[0], tx),
                (*rotation_t[1], ty),
                (*rotation_t[2], tz),
                (0.0, 0.0, 0.0, 1.0),
            )
        )

    @property
    def translation_vector(self) -> Vector3:
        return Vector3(self.values[3], self.values[7], self.values[11])

    def transform_point(self, point: Vector3) -> Vector3:
        m = self.values
        return Vector3(
            m[0] * point.x + m[1] * point.y + m[2] * point.z + m[3],
            m[4] * point.x + m[5] * point.y + m[6] * point.z + m[7],
            m[8] * point.x + m[9] * point.y + m[10] * point.z + m[11],
        )


@dataclass(frozen=True, slots=True)
class BoundingBox:
    minimum: Vector3
    maximum: Vector3

    def __post_init__(self) -> None:
        if (
            self.minimum.x > self.maximum.x
            or self.minimum.y > self.maximum.y
            or self.minimum.z > self.maximum.z
        ):
            raise ValueError("BoundingBox minimum mag maximum niet overschrijden")

    @classmethod
    def zero(cls) -> "BoundingBox":
        origin = Vector3.zero()
        return cls(origin, origin)

    @classmethod
    def from_dimensions(
        cls,
        x: float,
        y: float,
        z: float,
        *,
        origin: Vector3 | None = None,
    ) -> "BoundingBox":
        start = origin or Vector3.zero()
        return cls(start, Vector3(start.x + x, start.y + y, start.z + z))

    @property
    def size(self) -> Vector3:
        return self.maximum - self.minimum

    @property
    def center(self) -> Vector3:
        return (self.minimum + self.maximum) * 0.5

    def corners(self) -> tuple[Vector3, ...]:
        minimum, maximum = self.minimum, self.maximum
        return tuple(
            Vector3(x, y, z)
            for x in (minimum.x, maximum.x)
            for y in (minimum.y, maximum.y)
            for z in (minimum.z, maximum.z)
        )

    def transformed(self, matrix: Matrix4) -> "BoundingBox":
        points = tuple(matrix.transform_point(corner) for corner in self.corners())
        return BoundingBox(
            Vector3(
                min(point.x for point in points),
                min(point.y for point in points),
                min(point.z for point in points),
            ),
            Vector3(
                max(point.x for point in points),
                max(point.y for point in points),
                max(point.z for point in points),
            ),
        )

    def expanded(self, amount: float) -> "BoundingBox":
        margin = max(0.0, float(amount))
        delta = Vector3(margin, margin, margin)
        return BoundingBox(self.minimum - delta, self.maximum + delta)

    def union(self, other: "BoundingBox") -> "BoundingBox":
        return BoundingBox(
            Vector3(
                min(self.minimum.x, other.minimum.x),
                min(self.minimum.y, other.minimum.y),
                min(self.minimum.z, other.minimum.z),
            ),
            Vector3(
                max(self.maximum.x, other.maximum.x),
                max(self.maximum.y, other.maximum.y),
                max(self.maximum.z, other.maximum.z),
            ),
        )


@dataclass(frozen=True, slots=True)
class Rgba:
    red: float
    green: float
    blue: float
    alpha: float = 1.0

    def __post_init__(self) -> None:
        for field_name in ("red", "green", "blue", "alpha"):
            value = _finite(getattr(self, field_name), label=f"Rgba.{field_name}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} moet tussen 0 en 1 liggen")
            object.__setattr__(self, field_name, value)

    def to_tuple(self) -> tuple[float, float, float, float]:
        return (self.red, self.green, self.blue, self.alpha)


__all__ = ["Vector3", "Matrix4", "BoundingBox", "Rgba"]
