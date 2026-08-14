"""Event contracts and a thread-safe in-process event bus for V0."""
from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, Callable, Generic, TypeVar
from uuid import uuid4

from .state import CameraState, JobHandle, PickResult, SelectionSet, utc_now_iso


@dataclass(frozen=True, slots=True)
class ViewerEvent:
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            object.__setattr__(self, "timestamp", utc_now_iso())


@dataclass(frozen=True, slots=True)
class SceneLoadStarted(ViewerEvent):
    project_id: str = ""


@dataclass(frozen=True, slots=True)
class SceneLoadProgress(ViewerEvent):
    progress: float = 0.0
    message: str = ""


@dataclass(frozen=True, slots=True)
class SceneReady(ViewerEvent):
    project_id: str = ""
    scene_hash: str = ""
    node_count: int = 0


@dataclass(frozen=True, slots=True)
class SceneLoadFailed(ViewerEvent):
    error: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class SelectionChanged(ViewerEvent):
    selection: SelectionSet | None = None


@dataclass(frozen=True, slots=True)
class ObjectPicked(ViewerEvent):
    pick: PickResult | None = None


@dataclass(frozen=True, slots=True)
class FeaturePicked(ViewerEvent):
    pick: PickResult | None = None


@dataclass(frozen=True, slots=True)
class VisibilityChanged(ViewerEvent):
    hidden_node_ids: tuple[str, ...] = ()
    visible_node_ids: tuple[str, ...] = ()
    ghosted_node_ids: tuple[str, ...] = ()
    isolation_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StyleChanged(ViewerEvent):
    affected_node_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CameraChanged(ViewerEvent):
    camera: CameraState | None = None


@dataclass(frozen=True, slots=True)
class SectionChanged(ViewerEvent):
    section_plane_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompareReady(ViewerEvent):
    source_scene_hash: str = ""
    target_scene_hash: str = ""


@dataclass(frozen=True, slots=True)
class DisplayPreferencesChanged(ViewerEvent):
    preferences: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AccuracyModeChanged(ViewerEvent):
    enabled: bool = False


@dataclass(frozen=True, slots=True)
class VisibilitySetChanged(ViewerEvent):
    visibility_set_id: str = ""
    action: str = ""


@dataclass(frozen=True, slots=True)
class ViewpointChanged(ViewerEvent):
    viewpoint_id: str = ""


@dataclass(frozen=True, slots=True)
class ColorSchemeChanged(ViewerEvent):
    scheme: str = "original"
    legend_count: int = 0


@dataclass(frozen=True, slots=True)
class WorkspaceChanged(ViewerEvent):
    action: str = ""
    item_id: str = ""
    message: str = ""
    state_hash: str = ""


@dataclass(frozen=True, slots=True)
class RendererLost(ViewerEvent):
    reason: str = ""


@dataclass(frozen=True, slots=True)
class ViewerDiagnostic(ViewerEvent):
    code: str = ""
    message: str = ""
    severity: str = "info"


@dataclass(frozen=True, slots=True)
class JobProgress(ViewerEvent):
    job: JobHandle | None = None


T = TypeVar("T", bound=ViewerEvent)


@dataclass(frozen=True, slots=True)
class Subscription:
    subscription_id: str
    unsubscribe: Callable[[], None]

    def close(self) -> None:
        self.unsubscribe()


class EventBus:
    """Small thread-safe event bus; renderer adapters can replace it later."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._handlers: dict[type[ViewerEvent], dict[str, Callable[[Any], None]]] = {}

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> Subscription:
        subscription_id = f"subscription-{uuid4()}"
        with self._lock:
            self._handlers.setdefault(event_type, {})[subscription_id] = handler

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(event_type)
                if handlers is not None:
                    handlers.pop(subscription_id, None)
                    if not handlers:
                        self._handlers.pop(event_type, None)

        return Subscription(subscription_id, unsubscribe)

    def emit(self, event: ViewerEvent) -> None:
        with self._lock:
            handlers = [
                handler
                for event_type, registered in self._handlers.items()
                if isinstance(event, event_type)
                for handler in registered.values()
            ]
        for handler in handlers:
            handler(event)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()


__all__ = [name for name in globals() if name[0].isupper()]
