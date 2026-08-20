"""Deterministic integer-length kernel for profile nesting.

UI and persisted engineering values remain millimetres. Solver-facing values
are integers at an explicitly recorded resolution. Decimal is used at the
boundary so binary floating point never leaks into cutting-stock constraints.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import Any

DEFAULT_UNITS_PER_MM = 1000  # micrometre resolution
MAX_LENGTH_MM = Decimal("10000000")  # 10 km: defensive upper bound


class LengthKernelError(ValueError):
    """Raised when a length cannot safely enter the nesting kernel."""


@dataclass(frozen=True)
class QuantizedLength:
    input_mm: str
    units: int
    output_mm: str
    quantization_error_mm: str
    units_per_mm: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_mm": self.input_mm,
            "units": self.units,
            "output_mm": self.output_mm,
            "quantization_error_mm": self.quantization_error_mm,
            "units_per_mm": self.units_per_mm,
        }


@dataclass(frozen=True)
class LengthKernel:
    units_per_mm: int = DEFAULT_UNITS_PER_MM
    name: str = "micrometre"

    def __post_init__(self) -> None:
        if not isinstance(self.units_per_mm, int) or self.units_per_mm <= 0:
            raise LengthKernelError("units_per_mm moet een positief geheel getal zijn")

    @property
    def resolution_mm(self) -> Decimal:
        return Decimal(1) / Decimal(self.units_per_mm)

    def _decimal(self, value: Any) -> Decimal:
        if isinstance(value, float) and not math.isfinite(value):
            raise LengthKernelError("Lengte is NaN of oneindig")
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise LengthKernelError(f"Ongeldige lengte {value!r}") from exc
        if not result.is_finite():
            raise LengthKernelError("Lengte is NaN of oneindig")
        if result < 0:
            raise LengthKernelError("Negatieve lengte is niet toegestaan")
        if result > MAX_LENGTH_MM:
            raise LengthKernelError("Lengte overschrijdt de defensieve limiet")
        return result

    def quantize_mm(self, value: Any) -> QuantizedLength:
        source = self._decimal(value)
        raw_units = source * Decimal(self.units_per_mm)
        units = int(raw_units.to_integral_value(rounding=ROUND_HALF_UP))
        restored = Decimal(units) / Decimal(self.units_per_mm)
        error = restored - source
        return QuantizedLength(
            input_mm=format(source, "f"),
            units=units,
            output_mm=format(restored, "f"),
            quantization_error_mm=format(error, "f"),
            units_per_mm=self.units_per_mm,
        )

    def mm_to_units(self, value: Any) -> int:
        return self.quantize_mm(value).units


    def _signed_decimal(self, value: Any) -> Decimal:
        if isinstance(value, float) and not math.isfinite(value):
            raise LengthKernelError("Lengte is NaN of oneindig")
        try:
            result = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise LengthKernelError(f"Ongeldige lengte {value!r}") from exc
        if not result.is_finite():
            raise LengthKernelError("Lengte is NaN of oneindig")
        if abs(result) > MAX_LENGTH_MM:
            raise LengthKernelError("Lengte overschrijdt de defensieve limiet")
        return result

    def quantize_signed_mm(self, value: Any) -> QuantizedLength:
        """Quantize a signed geometric offset/delta using the same length grid.

        Stock lengths remain non-negative and continue to use ``quantize_mm``.
        This signed path exists only for local envelopes/transition offsets.
        """
        source = self._signed_decimal(value)
        raw_units = source * Decimal(self.units_per_mm)
        units = int(raw_units.to_integral_value(rounding=ROUND_HALF_UP))
        restored = Decimal(units) / Decimal(self.units_per_mm)
        error = restored - source
        return QuantizedLength(
            input_mm=format(source, "f"), units=units, output_mm=format(restored, "f"),
            quantization_error_mm=format(error, "f"), units_per_mm=self.units_per_mm,
        )

    def signed_mm_to_units(self, value: Any) -> int:
        return self.quantize_signed_mm(value).units

    def signed_units_to_mm_decimal(self, units: int) -> Decimal:
        if not isinstance(units, int):
            raise LengthKernelError("Solverlengte moet integer zijn")
        return Decimal(units) / Decimal(self.units_per_mm)

    def signed_units_to_mm(self, units: int) -> float:
        return float(self.signed_units_to_mm_decimal(units))

    def units_to_mm_decimal(self, units: int) -> Decimal:
        if not isinstance(units, int):
            raise LengthKernelError("Solverlengte moet integer zijn")
        if units < 0:
            raise LengthKernelError("Negatieve solverlengte is niet toegestaan")
        return Decimal(units) / Decimal(self.units_per_mm)

    def units_to_mm(self, units: int) -> float:
        return float(self.units_to_mm_decimal(units))

    def snapshot(self) -> dict[str, Any]:
        return {
            "kernel": "integer_length_v1",
            "name": self.name,
            "units_per_mm": self.units_per_mm,
            "resolution_mm": format(self.resolution_mm, "f"),
            "rounding": "ROUND_HALF_UP",
        }
