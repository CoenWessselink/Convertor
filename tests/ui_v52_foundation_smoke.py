from __future__ import annotations

from cws_convertor.ui_qt.ui_v51_contract import CONTROL_INVENTORY, MAIN_LABELS, SCREEN_MANIFEST
from cws_convertor.ui_qt.design_system.icons import ICON_REGISTRY, icon_for_test_id
from cws_convertor.ui_qt.design_system.tokens import TOKENS
from cws_convertor.ui_qt.design_system.stylesheet import V52_DARK_QSS, V52_LIGHT_QSS


def main() -> int:
    controls = CONTROL_INVENTORY["controls"]
    test_ids = [item["test_id"] for item in controls]
    assert len(controls) == CONTROL_INVENTORY["count"] == 226
    assert len(test_ids) == len(set(test_ids))
    assert len(SCREEN_MANIFEST["screens"]) == 31
    assert tuple(MAIN_LABELS) == ("Project", "Viewer", "Productie", "Controle", "Uitvoer")
    assert TOKENS["colors"]["viewer_selection"] == "#F7C600"
    assert TOKENS["colors"]["ui_selection"] == "#CCE8FF"
    assert TOKENS["theme"] == "Default Light"
    assert TOKENS["colors"]["canvas"] == "#F4F7FA"
    assert TOKENS["colors"]["surface"] == "#FFFFFF"
    assert TOKENS["colors"]["nav_background"] == "#263C50"
    assert V52_LIGHT_QSS != V52_DARK_QSS
    assert "#F4F7FA" in V52_LIGHT_QSS and "#FFFFFF" in V52_LIGHT_QSS
    assert all(ICON_REGISTRY.has(icon_for_test_id(test_id)) for test_id in test_ids)
    print("UI_V52_FOUNDATION_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
