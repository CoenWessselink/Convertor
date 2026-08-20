"""Persisted Profile Nesting desktop-state contract for phase 5.

The state is intentionally presentation-only. It never changes canonical part,
cut, stock or solver geometry. The UI may remember layout and selection, but
all engineering values are always rebuilt from the current project/run data.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from cws_convertor.project.model import ProjectModel, stable_sha256, utc_now_iso

PROFILE_NESTING_UI_SCHEMA_VERSION = "1.1"


@dataclass
class GridLayout:
    grid_id: str
    column_order: list[str] = field(default_factory=list)
    hidden_columns: list[str] = field(default_factory=list)
    column_widths: dict[str, int] = field(default_factory=dict)
    sort_column: str = ""
    sort_descending: bool = False
    group_by: str = ""
    filters: dict[str, str] = field(default_factory=dict)


@dataclass
class ProfileNestingUIState:
    schema_version: str = PROFILE_NESTING_UI_SCHEMA_VERSION
    scenario_family: str = "waste"
    scenario_id: str = "ui-waste"
    mode: str = "production"
    stock_policy: str = "stock_remnants_purchase"
    backend: str = "auto"
    selected_machine_id: str = ""
    selected_machine_profile_id: str = ""
    selected_run_id: str = ""
    selected_bar_id: str = ""
    selected_piece_instance_id: str = ""
    selected_lock_id: str = ""
    manual_edit_mode: bool = True
    active_center_tab: str = "input"
    active_right_tab: str = "errors"
    color_mode: str = "part"
    zoom: float = 1.0
    pan_mm: float = 0.0
    layouts: dict[str, GridLayout] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now_iso)
    state_hash: str = ""

    def refresh_hash(self) -> str:
        payload = asdict(self)
        payload.pop("updated_at", None)
        payload.pop("state_hash", None)
        self.state_hash = stable_sha256(payload)
        return self.state_hash

    def to_dict(self) -> dict[str, Any]:
        self.refresh_hash()
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "ProfileNestingUIState":
        data = dict(raw or {})
        schema = str(data.get("schema_version") or PROFILE_NESTING_UI_SCHEMA_VERSION)
        if schema == "1.0":
            data["schema_version"] = PROFILE_NESTING_UI_SCHEMA_VERSION
            data.setdefault("selected_lock_id", "")
            data.setdefault("manual_edit_mode", True)
        elif schema != PROFILE_NESTING_UI_SCHEMA_VERSION:
            raise ValueError(f"Niet-ondersteund profielnesting-UI-schema {schema!r}")
        layouts_raw = dict(data.pop("layouts", {}) or {})
        layouts: dict[str, GridLayout] = {}
        for key, value in layouts_raw.items():
            if isinstance(value, GridLayout):
                layouts[str(key)] = value
            elif isinstance(value, dict):
                layouts[str(key)] = GridLayout(**dict(value))
        data["layouts"] = layouts
        allowed = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        state = cls(**{k: v for k, v in data.items() if k in allowed})
        stored = str(state.state_hash or "")
        if stored:
            expected = stored
            state.refresh_hash()
            if state.state_hash != expected:
                raise ValueError("Profile Nesting UI-state hash is ongeldig")
        else:
            state.refresh_hash()
        return state


def load_ui_state(project: ProjectModel) -> ProfileNestingUIState:
    raw = dict(project.profile_nesting_settings or {}).get("ui_state")
    try:
        return ProfileNestingUIState.from_dict(raw if isinstance(raw, dict) else None)
    except ValueError:
        # Corrupt presentation state may not block the canonical project. Reset it
        # deterministically and leave an audit trail instead of guessing values.
        state = ProfileNestingUIState()
        state.refresh_hash()
        return state


def save_ui_state(project: ProjectModel, state: ProfileNestingUIState, *, user: str = "gui") -> None:
    before = stable_sha256(project.profile_nesting_settings) if project.profile_nesting_settings else ""
    state.updated_at = utc_now_iso()
    project.profile_nesting_settings["ui_state"] = state.to_dict()
    after = stable_sha256(project.profile_nesting_settings)
    project.audit(
        "profile_nesting.ui_state_saved",
        user=user or "gui",
        before_hash=before,
        after_hash=after,
        details={"ui_schema": PROFILE_NESTING_UI_SCHEMA_VERSION},
    )


__all__ = [
    "PROFILE_NESTING_UI_SCHEMA_VERSION",
    "GridLayout",
    "ProfileNestingUIState",
    "load_ui_state",
    "save_ui_state",
]
