from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .test_ids import PRODUCT_CONTROL_PROPERTY, get_ui_test_id


@dataclass(frozen=True)
class RegisteredControl:
    test_id: str
    qt_type: str
    object_name: str


class ControlRegistry:
    def __init__(self) -> None:
        self._controls: dict[str, RegisteredControl] = {}

    def register(self, control: Any) -> RegisteredControl:
        test_id = get_ui_test_id(control)
        if not test_id:
            raise ValueError("Productcontrol mist ui_test_id")
        if test_id in self._controls:
            raise ValueError(f"Dubbele ui_test_id: {test_id}")
        record = RegisteredControl(
            test_id=test_id,
            qt_type=type(control).__name__,
            object_name=str(control.objectName() or ""),
        )
        self._controls[test_id] = record
        return record

    def values(self) -> tuple[RegisteredControl, ...]:
        return tuple(self._controls[key] for key in sorted(self._controls))


def scan_product_controls(root: Any) -> tuple[RegisteredControl, ...]:
    """Scan only explicitly marked product controls; Qt internals are excluded."""
    registry = ControlRegistry()
    candidates: Iterable[Any] = (root, *root.findChildren(type(root).__mro__[-2])) if False else root.findChildren(object)
    for control in candidates:
        if not bool(control.property(PRODUCT_CONTROL_PROPERTY)):
            continue
        registry.register(control)
    return registry.values()

