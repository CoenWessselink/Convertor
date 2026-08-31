from __future__ import annotations

from typing import Any


UI_TEST_ID_PROPERTY = "ui_test_id"
PRODUCT_CONTROL_PROPERTY = "cws_product_control"


def set_ui_test_id(control: Any, test_id: str) -> Any:
    value = str(test_id).strip()
    if not value:
        raise ValueError("ui_test_id mag niet leeg zijn")
    control.setProperty(UI_TEST_ID_PROPERTY, value)
    control.setProperty(PRODUCT_CONTROL_PROPERTY, True)
    return control


def get_ui_test_id(control: Any) -> str:
    return str(control.property(UI_TEST_ID_PROPERTY) or "").strip()

