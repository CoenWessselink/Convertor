from __future__ import annotations

from cws_convertor.ui_qt.ui_v51_contract import CONTROL_INVENTORY, MAIN_LABELS, SCREEN_MANIFEST
from cws_convertor.ui_qt.design_system.icons import ICON_REGISTRY, icon_for_test_id
from cws_convertor.ui_qt.design_system.tokens import TOKENS


def main() -> int:
    controls = CONTROL_INVENTORY["controls"]
    test_ids = [item["test_id"] for item in controls]
    assert len(controls) == CONTROL_INVENTORY["count"] == 226
    assert len(test_ids) == len(set(test_ids))
    assert len(SCREEN_MANIFEST["screens"]) == 31
    assert tuple(MAIN_LABELS) == ("Project", "Viewer", "Productie", "Controle", "Uitvoer")
    assert TOKENS["colors"]["viewer_selection"] == "#F7C600"
    assert TOKENS["colors"]["ui_selection"] == "#CCE8FF"
    assert all(ICON_REGISTRY.has(icon_for_test_id(test_id)) for test_id in test_ids)
    print("UI_V52_FOUNDATION_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

