"""Single authority for mapping product actions to five primary workspaces."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PRIMARY_WORKSPACES = ("project", "viewer", "production", "control", "output")
PRIMARY_LABELS = ("Project", "Viewer", "Productie", "Controle", "Uitvoer")


@dataclass(frozen=True, slots=True)
class ContextActionBinding:
    route: str
    primary: str
    page: Any
    primary_page: Any
    host: Any | None = None


class ContextActionService:
    """Resolve every legacy/product command through one primary workspace map."""

    def __init__(self) -> None:
        self._bindings: dict[str, ContextActionBinding] = {}
        self._primary_routes: dict[Any, str] = {}

    def register(
        self,
        route: str,
        *,
        primary: str,
        page: Any,
        primary_page: Any,
        host: Any | None = None,
    ) -> ContextActionBinding:
        key = str(route).strip().lower()
        primary_key = str(primary).strip().lower()
        if primary_key not in PRIMARY_WORKSPACES:
            raise ValueError(f"Unknown primary workspace: {primary}")
        if not key:
            raise ValueError("Route cannot be empty")
        binding = ContextActionBinding(key, primary_key, page, primary_page, host)
        self._bindings[key] = binding
        self._primary_routes.setdefault(primary_page, primary_key)
        return binding

    def resolve(self, route: str) -> ContextActionBinding | None:
        return self._bindings.get(str(route).strip().lower())

    def activate(self, route: str) -> ContextActionBinding | None:
        binding = self.resolve(route)
        if binding is None:
            return None
        if binding.host is not None and binding.page is not binding.host:
            binding.host.setCurrentWidget(binding.page)
        return binding

    def route_for_primary_page(self, page: Any) -> str:
        return self._primary_routes.get(page, "")

    def contract(self) -> dict[str, Any]:
        return {
            "primary_workspaces": list(PRIMARY_WORKSPACES),
            "primary_labels": list(PRIMARY_LABELS),
            "routes": {
                key: {"primary": binding.primary, "has_subworkspace": binding.host is not None}
                for key, binding in sorted(self._bindings.items())
            },
        }
