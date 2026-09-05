"""Persistent, renderer-neutral interactive drawing dimensions.

The Qt canvas is deliberately only an input surface.  This module owns the
dimension identities, exact projected anchors, transaction history and the
project persistence contract, so PNG, PDF and Trusted PDF consume the same
records as the editor.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence
from uuid import uuid4

from .document import DrawingDocument, DrawingPrimitive


DIMENSION_EDITOR_SCHEMA = "cws.drawing-dimension-editor.v2"
DIMENSION_SETTINGS_KEY = "drawing_dimension_editor_v2"
DEFAULT_STYLE_ID = "cws-standard"
DEFAULT_STYLE_VERSION = "2.0"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _point(value: Sequence[float] | None, *, size: int = 2) -> tuple[float, ...]:
    values = tuple(float(item) for item in (value or ()))
    if len(values) != size or any(not math.isfinite(item) for item in values):
        return ()
    return values


def _distance(left: Sequence[float], right: Sequence[float]) -> float:
    return math.hypot(float(right[0]) - float(left[0]), float(right[1]) - float(left[1]))


def _enum_value(enum_type: type[Enum], value: object, default: Enum) -> str:
    text = str(getattr(value, "value", value) or "")
    return text if text in {str(item.value) for item in enum_type} else str(default.value)


class DimensionKind(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    ALIGNED = "aligned"
    CHAIN = "chain"
    BASELINE = "baseline"
    ORDINATE_X = "ordinate_x"
    ORDINATE_Y = "ordinate_y"
    ANGLE = "angle"
    RADIUS = "radius"
    DIAMETER = "diameter"
    CENTER_DISTANCE = "center_distance"
    LEADER = "leader"
    TEXT = "text"


class DimensionState(str, Enum):
    RESOLVED = "RESOLVED"
    MOVED = "MOVED"
    ORPHANED = "ORPHANED"
    ORPHANED_VIEW = "ORPHANED_VIEW"
    CONFLICT = "CONFLICT"
    OVERRIDDEN = "OVERRIDDEN"
    STALE = "STALE"


class InteractionState(str, Enum):
    IDLE = "IDLE"
    TOOL_ARMED = "TOOL_ARMED"
    PICK_FIRST_ANCHOR = "PICK_FIRST_ANCHOR"
    PICK_NEXT_ANCHOR = "PICK_NEXT_ANCHOR"
    PLACE_DIMENSION_LINE = "PLACE_DIMENSION_LINE"
    PLACE_TEXT = "PLACE_TEXT"
    EDIT_SELECTED = "EDIT_SELECTED"
    DRAG_DIMENSION = "DRAG_DIMENSION"
    DRAG_TEXT = "DRAG_TEXT"
    REANCHOR_FIRST = "REANCHOR_FIRST"
    REANCHOR_SECOND = "REANCHOR_SECOND"
    CANCELLED = "CANCELLED"
    COMMITTED = "COMMITTED"


class SnapType(str, Enum):
    VERTEX = "vertex"
    ENDPOINT = "endpoint"
    MIDPOINT = "midpoint"
    NEAREST = "nearest"
    INTERSECTION = "intersection"
    CENTER = "center"
    TANGENT = "tangent"
    DATUM = "datum"
    FEATURE = "feature"
    EXISTING_ANCHOR = "existing_anchor"


class SnapFilter(str, Enum):
    ALL = "all"
    POINTS = "points"
    EDGES = "edges"
    CENTERS = "centers"
    CENTERLINES = "centerlines"
    FEATURES = "features"
    DIMENSIONS = "dimensions"
    TEXT_LEADERS = "text_leaders"


class DrawingRole(str, Enum):
    DRAFTER = "opsteller"
    CHECKER = "controleur"
    RELEASER = "vrijgever"
    READ_ONLY = "alleen_lezen"


@dataclass(slots=True)
class DimensionStyle:
    style_id: str = DEFAULT_STYLE_ID
    version: str = DEFAULT_STYLE_VERSION
    arrow_type: str = "closed_filled"
    arrow_size_mm: float = 2.5
    font_family: str = "Segoe UI"
    text_height_mm: float = 2.5
    line_width_mm: float = 0.2
    line_color: str = "#0066dc"
    extension_offset_mm: float = 1.0
    extension_overshoot_mm: float = 1.5
    chain_spacing_mm: float = 7.0
    decimals: int = 1
    decimal_separator: str = ","
    trailing_zeros: bool = False
    unit: str = "mm"
    text_position_mode: str = "centered"
    text_inside_arrows: str = "auto"
    space_fallback: str = "outside"
    diameter_symbol: str = "Ø"
    radius_prefix: str = "R"
    angle_suffix: str = "°"
    tolerance_format: str = "upper_lower"
    quantity_format: str = "{count}x {value}"
    rounding_rule: str = "half_up"
    minimum_text_height_mm: float = 2.0
    profile_scope: str = "standard"
    base_style_id: str = "cws-standard"
    approved_by: str = "CWS"
    extensions: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "arrow_size_mm",
            "text_height_mm",
            "line_width_mm",
            "extension_offset_mm",
            "extension_overshoot_mm",
            "chain_spacing_mm",
            "minimum_text_height_mm",
        ):
            setattr(self, name, float(getattr(self, name)))
        self.decimals = int(self.decimals)
        self.validate()

    def validate(self) -> None:
        if not self.style_id or not self.version or not self.font_family:
            raise ValueError("DimensionStyle vereist stijl-ID, versie en font")
        if self.arrow_size_mm <= 0 or self.text_height_mm < 2.0 or self.line_width_mm <= 0:
            raise ValueError("DimensionStyle bevat onleesbare of ongeldige papiermaten")
        if not 0 <= self.decimals <= 6 or self.decimal_separator not in {",", "."}:
            raise ValueError("DimensionStyle bevat ongeldige getalnotatie")
        if self.unit not in {"mm", "cm"} or self.profile_scope not in {"standard", "company", "project", "object"}:
            raise ValueError("DimensionStyle bevat een ongeldige eenheid of scope")
        if not (
            isinstance(self.line_color, str)
            and len(self.line_color) == 7
            and self.line_color.startswith("#")
            and all(character in "0123456789abcdefABCDEF" for character in self.line_color[1:])
        ):
            raise ValueError("DimensionStyle bevat een ongeldige lijnkleur")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def cws_standard(cls) -> "DimensionStyle":
        path = Path(__file__).with_name("styles") / "cws_standard_v2.json"
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any] | None) -> "DimensionStyle":
        allowed = set(cls.__dataclass_fields__)
        source = dict(raw or {})
        values = {key: value for key, value in source.items() if key in allowed}
        values["extensions"] = {
            **dict(source.get("extensions") or {}),
            **{key: value for key, value in source.items() if key not in allowed},
        }
        return cls(**values)


@dataclass(slots=True)
class DrawingAnchor:
    entity_id: str
    view_id: str
    sheet_id: str
    page_number: int
    anchor_type: str
    projected_point: tuple[float, float]
    sheet_point: tuple[float, float]
    feature_id: str = ""
    subshape_id: str = ""
    curve_parameter: float | None = None
    model_point: tuple[float, ...] = ()
    source_revision: str = ""
    geometry_sha256: str = ""
    manufacturing_sha256: str = ""
    proof: str = "review_projection"
    resolved: bool = True

    def __post_init__(self) -> None:
        self.entity_id = str(self.entity_id)
        self.view_id = str(self.view_id)
        self.sheet_id = str(self.sheet_id)
        self.page_number = max(1, int(self.page_number))
        self.anchor_type = _enum_value(SnapType, self.anchor_type, SnapType.NEAREST)
        self.projected_point = _point(self.projected_point)  # type: ignore[assignment]
        self.sheet_point = _point(self.sheet_point)  # type: ignore[assignment]
        self.model_point = tuple(float(item) for item in self.model_point)
        if not self.projected_point or not self.sheet_point:
            self.resolved = False

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["projected_point"] = list(self.projected_point)
        value["sheet_point"] = list(self.sheet_point)
        value["model_point"] = list(self.model_point)
        return value

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DrawingAnchor":
        data = dict(raw)
        data["projected_point"] = tuple(data.get("projected_point") or data.get("sheet_point") or ())
        data["sheet_point"] = tuple(data.get("sheet_point") or data.get("projected_point") or ())
        data["model_point"] = tuple(data.get("model_point") or ())
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(slots=True)
class InteractiveDimension:
    dimension_id: str
    kind: str
    entity_ids: tuple[str, ...]
    drawing_id: str
    view_id: str
    sheet_id: str
    page_number: int
    anchors: list[DrawingAnchor]
    nominal_value_mm: float
    line_position: tuple[float, float]
    text_position: tuple[float, float]
    line_projected_position: tuple[float, float] = ()
    text_projected_position: tuple[float, float] = ()
    label: str = ""
    prefix: str = ""
    suffix: str = ""
    tolerance_upper_mm: float | None = None
    tolerance_lower_mm: float | None = None
    visible: bool = True
    state: str = DimensionState.RESOLVED.value
    style_id: str = DEFAULT_STYLE_ID
    style_version: str = DEFAULT_STYLE_VERSION
    source_revision: str = ""
    drawing_revision: str = "draft-1"
    geometry_sha256: str = ""
    manufacturing_sha256: str = ""
    created_by: str = "system"
    modified_by: str = "system"
    created_at: str = field(default_factory=_now)
    modified_at: str = field(default_factory=_now)
    reference: bool = False
    inspection: bool = False
    override_reason: str = ""
    override_approved_by: str = ""
    note: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.dimension_id = str(self.dimension_id or uuid4())
        self.kind = _enum_value(DimensionKind, self.kind, DimensionKind.ALIGNED)
        self.entity_ids = tuple(dict.fromkeys(str(item) for item in self.entity_ids if str(item)))
        self.anchors = [item if isinstance(item, DrawingAnchor) else DrawingAnchor.from_dict(item) for item in self.anchors]
        self.nominal_value_mm = float(self.nominal_value_mm)
        self.line_position = _point(self.line_position)  # type: ignore[assignment]
        self.text_position = _point(self.text_position)  # type: ignore[assignment]
        self.line_projected_position = _point(self.line_projected_position)  # type: ignore[assignment]
        self.text_projected_position = _point(self.text_projected_position)  # type: ignore[assignment]
        self.state = _enum_value(DimensionState, self.state, DimensionState.RESOLVED)
        if not math.isfinite(self.nominal_value_mm) or self.nominal_value_mm < 0.0:
            raise ValueError("Nominale maat moet een eindige, niet-negatieve millimeterwaarde zijn")
        if not self.line_position or not self.text_position:
            raise ValueError("Maatlijn en tekstpositie ontbreken")

    @property
    def id(self) -> str:
        return self.dimension_id

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["entity_ids"] = list(self.entity_ids)
        value["line_position"] = list(self.line_position)
        value["text_position"] = list(self.text_position)
        value["line_projected_position"] = list(self.line_projected_position)
        value["text_projected_position"] = list(self.text_projected_position)
        value["anchors"] = [item.to_dict() for item in self.anchors]
        return value

    def to_render_dict(self) -> dict[str, Any]:
        value = self.to_dict()
        value.update(
            {
                "id": self.dimension_id,
                "schema": DIMENSION_EDITOR_SCHEMA,
                "critical": False,
                "feature_id": next((item.feature_id for item in self.anchors if item.feature_id), "part-envelope"),
                "subshape_id": next((item.subshape_id for item in self.anchors if item.subshape_id), ""),
                "anchor_type": "projected_geometry",
                "axis": "vertical" if self.kind in {DimensionKind.VERTICAL.value, DimensionKind.ORDINATE_Y.value} else "horizontal",
                "view": self.view_id,
            }
        )
        return value

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "InteractiveDimension":
        data = dict(raw)
        data["dimension_id"] = str(data.get("dimension_id") or data.get("id") or uuid4())
        data["entity_ids"] = tuple(data.get("entity_ids") or ([data.get("entity_id")] if data.get("entity_id") else ()))
        data["anchors"] = [DrawingAnchor.from_dict(item) for item in data.get("anchors") or ()]
        data["line_position"] = tuple(data.get("line_position") or (0.0, 0.0))
        data["text_position"] = tuple(data.get("text_position") or data["line_position"])
        data["line_projected_position"] = tuple(data.get("line_projected_position") or ())
        data["text_projected_position"] = tuple(data.get("text_projected_position") or ())
        allowed = set(cls.__dataclass_fields__)
        data["metadata"] = {
            **dict(data.get("metadata") or {}),
            **(
                {"extensions": {key: value for key, value in data.items() if key not in allowed}}
                if any(key not in allowed for key in data)
                else {}
            ),
        }
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass(frozen=True, slots=True)
class SnapCandidate:
    candidate_id: str
    point: tuple[float, float]
    snap_type: str
    label: str
    anchor: DrawingAnchor
    valid: bool = True
    reason: str = ""
    layer: str = "visible"


@dataclass(slots=True)
class DimensionEditorDocument:
    project_id: str
    entity_id: str
    drawing_id: str
    source_revision: str
    drawing_revision: str
    geometry_sha256: str
    manufacturing_sha256: str
    dimensions: list[InteractiveDimension] = field(default_factory=list)
    style: DimensionStyle = field(default_factory=DimensionStyle)
    status: str = "draft"
    lock_version: int = 0
    created_by: str = "system"
    modified_by: str = "system"
    created_at: str = field(default_factory=_now)
    modified_at: str = field(default_factory=_now)
    audit: list[dict[str, Any]] = field(default_factory=list)
    schema: str = DIMENSION_EDITOR_SCHEMA
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["style"] = self.style.to_dict()
        value["dimensions"] = [item.to_dict() for item in sorted(self.dimensions, key=lambda item: item.dimension_id)]
        value["audit"] = sorted(
            (dict(item) for item in self.audit),
            key=lambda item: (str(item.get("timestamp") or ""), str(item.get("transaction_id") or "")),
        )
        return value

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DimensionEditorDocument":
        data = dict(raw)
        schema = str(data.get("schema") or "")
        if schema and schema != DIMENSION_EDITOR_SCHEMA:
            raise ValueError(f"Niet-ondersteund maatvoeringsschema {schema!r}")
        data["style"] = DimensionStyle.from_dict(data.get("style"))
        data["dimensions"] = [InteractiveDimension.from_dict(item) for item in data.get("dimensions") or ()]
        allowed = set(cls.__dataclass_fields__)
        known = {key: value for key, value in data.items() if key in allowed}
        known["extensions"] = {
            **dict(data.get("extensions") or {}),
            **{key: value for key, value in data.items() if key not in allowed},
        }
        return cls(**known)

    def render_records(self) -> list[dict[str, Any]]:
        result = []
        for item in sorted(
            self.dimensions,
            key=lambda value: (int(value.metadata.get("cluster_order") or 0), value.dimension_id),
        ):
            record = item.to_render_dict()
            record["style"] = self.style.to_dict()
            result.append(record)
        return result


class DimensionEditorModel:
    """Transactional editor facade with deterministic undo/redo snapshots."""

    def __init__(self, document: DimensionEditorDocument, *, clock: Callable[[], str] = _now) -> None:
        self.document = document
        self.clock = clock
        self.selected_ids: set[str] = set()
        self._undo: list[tuple[str, list[InteractiveDimension]]] = []
        self._redo: list[tuple[str, list[InteractiveDimension]]] = []

    def _snapshot(self) -> list[InteractiveDimension]:
        return deepcopy(self.document.dimensions)

    def _begin(self, action: str) -> tuple[str, list[InteractiveDimension]]:
        if self.document.status == "released":
            raise PermissionError("Vrijgegeven maatvoering is alleen-lezen; start eerst een nieuwe conceptrevisie")
        return action, self._snapshot()

    def _commit(self, before: tuple[str, list[InteractiveDimension]], *, user: str, details: Mapping[str, Any] | None = None) -> None:
        action, snapshot = before
        self._undo.append((action, snapshot))
        self._redo.clear()
        timestamp = self.clock()
        self.document.modified_at = timestamp
        self.document.modified_by = user or "system"
        self.document.status = "draft"
        before_by_id = {item.dimension_id: item for item in snapshot}
        after_by_id = {item.dimension_id: item for item in self.document.dimensions}
        changes = []
        for dimension_id in sorted(set(before_by_id) | set(after_by_id)):
            old = before_by_id.get(dimension_id)
            new = after_by_id.get(dimension_id)
            old_dict = old.to_dict() if old is not None else None
            new_dict = new.to_dict() if new is not None else None
            if old_dict == new_dict:
                continue
            def audit_value(item: InteractiveDimension | None) -> dict[str, Any] | None:
                if item is None:
                    return None
                return {
                    "nominal_value_mm": item.nominal_value_mm,
                    "label": item.label,
                    "state": item.state,
                    "visible": item.visible,
                    "line_position": list(item.line_position),
                    "text_position": list(item.text_position),
                    "anchors": [anchor.to_dict() for anchor in item.anchors],
                }
            changes.append({"dimension_id": dimension_id, "old": audit_value(old), "new": audit_value(new)})
        audit_details = dict(details or {})
        audit_details["changes"] = changes
        self.document.audit.append(
            {
                "transaction_id": str(uuid4()),
                "timestamp": timestamp,
                "user": user or "system",
                "action": action,
                "dimension_ids": sorted(self.selected_ids),
                "details": audit_details,
            }
        )

    def _record_history_action(self, action: str, *, user: str, source_action: str) -> None:
        timestamp = self.clock()
        self.document.modified_at = timestamp
        self.document.modified_by = user or "system"
        self.document.status = "draft"
        self.document.audit.append(
            {
                "transaction_id": str(uuid4()),
                "timestamp": timestamp,
                "user": user or "system",
                "action": action,
                "dimension_ids": sorted(self.selected_ids),
                "details": {"source_action": source_action},
            }
        )

    def add(self, dimension: InteractiveDimension, *, user: str = "system") -> InteractiveDimension:
        if any(item.dimension_id == dimension.dimension_id for item in self.document.dimensions):
            raise ValueError(f"Dubbel maat-ID {dimension.dimension_id}")
        before = self._begin("dimension.add")
        self.document.dimensions.append(dimension)
        self.selected_ids = {dimension.dimension_id}
        self._commit(before, user=user)
        return dimension

    def begin_revision(self, *, reason: str, user: str = "system") -> str:
        if self.document.status != "released":
            return self.document.drawing_revision
        if not str(reason).strip():
            raise ValueError("Een wijzigingsreden is verplicht na vrijgave")
        released = list(self.document.extensions.get("released_revisions") or ())
        released.append(
            {
                "drawing_revision": self.document.drawing_revision,
                "released_at": self.document.modified_at,
                "dimensions": [item.to_dict() for item in self.document.dimensions],
            }
        )
        self.document.extensions["released_revisions"] = released
        current = self.document.drawing_revision
        digits = "".join(character for character in current if character.isdigit())
        self.document.drawing_revision = f"draft-{int(digits or 0) + 1}"
        self.document.status = "draft"
        for item in self.document.dimensions:
            item.drawing_revision = self.document.drawing_revision
        timestamp = self.clock()
        self.document.audit.append(
            {
                "transaction_id": str(uuid4()),
                "timestamp": timestamp,
                "user": user or "system",
                "action": "drawing.revision_forked",
                "dimension_ids": [],
                "details": {"reason": str(reason).strip(), "from_revision": current},
            }
        )
        return self.document.drawing_revision

    def release(self, *, role: str, user: str = "system") -> None:
        role_value = _enum_value(DrawingRole, role, DrawingRole.READ_ONLY)
        if role_value != DrawingRole.RELEASER.value:
            raise PermissionError("Alleen een vrijgever mag maatvoering vrijgeven")
        blocking = {
            DimensionState.ORPHANED.value,
            DimensionState.ORPHANED_VIEW.value,
            DimensionState.CONFLICT.value,
            DimensionState.STALE.value,
        }
        if any(item.state in blocking for item in self.document.dimensions):
            raise ValueError("Maatvoering met blokkerende status kan niet worden vrijgegeven")
        if any(
            item.state == DimensionState.OVERRIDDEN.value and not item.override_approved_by
            for item in self.document.dimensions
        ):
            raise ValueError("Een niet-goedgekeurde maattekstoverride blokkeert vrijgave")
        if any(
            anchor.proof not in {"canonical_projection", "non_geometric_annotation"}
            for item in self.document.dimensions
            for anchor in item.anchors
        ):
            raise ValueError("Niet-canoniek bewezen maatankers blokkeren vrijgave")
        style = self.document.style
        if style.profile_scope == "standard":
            if style.to_dict() != DimensionStyle.cws_standard().to_dict():
                raise ValueError("Gewijzigde CWS-standaardstijl blokkeert vrijgave")
        elif (
            style.profile_scope not in {"company", "project", "object"}
            or style.base_style_id != DEFAULT_STYLE_ID
            or not style.approved_by
        ):
            raise ValueError("Niet-goedgekeurde maatstijl blokkeert vrijgave")
        identifiers = [item.dimension_id for item in self.document.dimensions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Dubbele maat-ID's blokkeren vrijgave")
        if any(
            item.style_id != self.document.style.style_id
            or item.style_version != self.document.style.version
            or item.drawing_revision != self.document.drawing_revision
            or item.geometry_sha256 != self.document.geometry_sha256
            or item.manufacturing_sha256 != self.document.manufacturing_sha256
            or not item.anchors
            or any(
                not anchor.resolved
                or anchor.entity_id not in item.entity_ids
                or anchor.view_id != item.view_id
                or anchor.sheet_id != item.sheet_id
                or anchor.page_number != item.page_number
                or anchor.geometry_sha256 != self.document.geometry_sha256
                or anchor.manufacturing_sha256 != self.document.manufacturing_sha256
                for anchor in item.anchors
            )
            for item in self.document.dimensions
        ):
            raise ValueError("Inconsistente revisie-, stijl- of ankerbinding blokkeert vrijgave")
        self.document.status = "released"
        timestamp = self.clock()
        self.document.modified_at = timestamp
        self.document.modified_by = user or "system"
        self.document.audit.append(
            {
                "transaction_id": str(uuid4()),
                "timestamp": timestamp,
                "user": user or "system",
                "action": "drawing.dimension_revision_released",
                "dimension_ids": sorted(item.dimension_id for item in self.document.dimensions),
                "details": {"role": role_value, "drawing_revision": self.document.drawing_revision},
            }
        )

    def select(self, dimension_ids: Iterable[str], *, extend: bool = False) -> set[str]:
        existing = {item.dimension_id for item in self.document.dimensions}
        selected = {str(item) for item in dimension_ids if str(item) in existing}
        self.selected_ids = (self.selected_ids | selected) if extend else selected
        return set(self.selected_ids)

    def delete_selected(self, *, user: str = "system") -> int:
        if not self.selected_ids:
            return 0
        before = self._begin("dimension.delete")
        old_count = len(self.document.dimensions)
        self.document.dimensions = [item for item in self.document.dimensions if item.dimension_id not in self.selected_ids]
        removed = old_count - len(self.document.dimensions)
        if removed:
            self._commit(before, user=user, details={"removed": removed})
        self.selected_ids.clear()
        return removed

    def duplicate_selected(self, *, offset: Sequence[float] = (5.0, 5.0), user: str = "system") -> int:
        dx, dy = _point(offset)
        source = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not source:
            return 0
        before = self._begin("dimension.duplicate")
        created = []
        timestamp = self.clock()
        for item in source:
            clone = deepcopy(item)
            clone.dimension_id = str(uuid4())
            clone.line_position = (clone.line_position[0] + dx, clone.line_position[1] + dy)
            clone.text_position = (clone.text_position[0] + dx, clone.text_position[1] + dy)
            clone.line_projected_position = ()
            clone.text_projected_position = ()
            clone.created_at = timestamp
            clone.modified_at = timestamp
            clone.created_by = user or "system"
            clone.modified_by = user or "system"
            clone.metadata = {**clone.metadata, "duplicated_from": item.dimension_id}
            created.append(clone)
        self.document.dimensions.extend(created)
        self.selected_ids = {item.dimension_id for item in created}
        self._commit(before, user=user, details={"count": len(created)})
        return len(created)

    def copy_selected(self) -> list[dict[str, Any]]:
        return [
            item.to_dict()
            for item in self.document.dimensions
            if item.dimension_id in self.selected_ids
        ]

    def paste(
        self,
        values: Sequence[Mapping[str, Any]],
        *,
        offset: Sequence[float] = (5.0, 5.0),
        user: str = "system",
    ) -> int:
        if not values:
            return 0
        dx, dy = _point(offset)
        before = self._begin("dimension.paste")
        timestamp = self.clock()
        created: list[InteractiveDimension] = []
        for raw in values:
            clone = InteractiveDimension.from_dict(deepcopy(dict(raw)))
            source_id = clone.dimension_id
            clone.dimension_id = str(uuid4())
            clone.line_position = (clone.line_position[0] + dx, clone.line_position[1] + dy)
            clone.text_position = (clone.text_position[0] + dx, clone.text_position[1] + dy)
            clone.line_projected_position = ()
            clone.text_projected_position = ()
            clone.created_at = timestamp
            clone.modified_at = timestamp
            clone.created_by = user or "system"
            clone.modified_by = user or "system"
            clone.metadata = {**clone.metadata, "pasted_from": source_id}
            created.append(clone)
        self.document.dimensions.extend(created)
        self.selected_ids = {item.dimension_id for item in created}
        self._commit(before, user=user, details={"count": len(created)})
        return len(created)

    def align_selected(self, axis: str, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        axis_value = str(axis).lower()
        if len(targets) < 2 or axis_value not in {"horizontal", "vertical"}:
            return 0
        before = self._begin(f"dimension.align_{axis_value}")
        coordinate = sum(item.line_position[1 if axis_value == "horizontal" else 0] for item in targets) / len(targets)
        for item in targets:
            if axis_value == "horizontal":
                delta = coordinate - item.line_position[1]
                item.line_position = (item.line_position[0], coordinate)
                item.text_position = (item.text_position[0], item.text_position[1] + delta)
            else:
                delta = coordinate - item.line_position[0]
                item.line_position = (coordinate, item.line_position[1])
                item.text_position = (item.text_position[0] + delta, item.text_position[1])
            item.state = DimensionState.MOVED.value if item.state == DimensionState.RESOLVED.value else item.state
        self._commit(before, user=user, details={"axis": axis_value})
        return len(targets)

    def distribute_selected(self, axis: str, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        axis_value = str(axis).lower()
        if len(targets) < 3 or axis_value not in {"horizontal", "vertical"}:
            return 0
        coordinate_index = 0 if axis_value == "horizontal" else 1
        ordered = sorted(targets, key=lambda item: item.line_position[coordinate_index])
        start = ordered[0].line_position[coordinate_index]
        step = (ordered[-1].line_position[coordinate_index] - start) / (len(ordered) - 1)
        before = self._begin(f"dimension.distribute_{axis_value}")
        for index, item in enumerate(ordered):
            coordinate = start + index * step
            old = item.line_position[coordinate_index]
            delta = coordinate - old
            if coordinate_index == 0:
                item.line_position = (coordinate, item.line_position[1])
                item.text_position = (item.text_position[0] + delta, item.text_position[1])
            else:
                item.line_position = (item.line_position[0], coordinate)
                item.text_position = (item.text_position[0], item.text_position[1] + delta)
            item.state = DimensionState.MOVED.value if item.state == DimensionState.RESOLVED.value else item.state
        self._commit(before, user=user, details={"axis": axis_value})
        return len(targets)

    def mirror_selected(self, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets:
            return 0
        before = self._begin("dimension.mirror_side")
        for item in targets:
            points = [anchor.sheet_point for anchor in item.anchors]
            if not points:
                continue
            center = (
                sum(point[0] for point in points) / len(points),
                sum(point[1] for point in points) / len(points),
            )
            new_line = (2.0 * center[0] - item.line_position[0], 2.0 * center[1] - item.line_position[1])
            delta = (new_line[0] - item.line_position[0], new_line[1] - item.line_position[1])
            item.line_position = new_line
            item.text_position = (item.text_position[0] + delta[0], item.text_position[1] + delta[1])
            item.state = DimensionState.MOVED.value if item.state == DimensionState.RESOLVED.value else item.state
        self._commit(before, user=user)
        return len(targets)

    def change_cluster_order(self, delta: int, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets or not int(delta):
            return 0
        before = self._begin("dimension.cluster_order")
        for item in targets:
            item.metadata["cluster_order"] = int(item.metadata.get("cluster_order") or 0) + int(delta)
        self._commit(before, user=user, details={"delta": int(delta)})
        return len(targets)

    def set_leader_bend(
        self,
        point: Sequence[float],
        *,
        projected_point: Sequence[float] = (),
        user: str = "system",
    ) -> int:
        bend = _point(point)
        projected = _point(projected_point)
        targets = [
            item
            for item in self.document.dimensions
            if item.dimension_id in self.selected_ids and item.kind == DimensionKind.LEADER.value
        ]
        if not targets:
            return 0
        before = self._begin("dimension.leader_bend")
        for item in targets:
            item.metadata["leader_bend_points"] = [list(bend)]
            item.metadata["leader_bend_projected_points"] = [list(projected)] if projected else []
            item.state = DimensionState.MOVED.value if item.state == DimensionState.RESOLVED.value else item.state
        self._commit(
            before,
            user=user,
            details={"point": list(bend), "projected_point": list(projected)},
        )
        return len(targets)

    def set_angle_mode(self, mode: str, *, user: str = "system") -> int:
        mode_value = str(mode).lower()
        if mode_value not in {"inside", "outside", "supplementary"}:
            raise ValueError("Hoekmodus moet binnen, buiten of supplementair zijn")
        targets = [
            item
            for item in self.document.dimensions
            if item.dimension_id in self.selected_ids and item.kind == DimensionKind.ANGLE.value
        ]
        if not targets or all(item.metadata.get("angle_mode", "inside") == mode_value for item in targets):
            return 0
        before = self._begin("dimension.angle_mode")
        for item in targets:
            item.metadata["angle_mode"] = mode_value
            item.nominal_value_mm = calculate_nominal_value(item.kind, item.anchors, angle_mode=mode_value)
        self._commit(before, user=user, details={"mode": mode_value})
        return len(targets)

    def set_visibility(self, visible: bool, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets or all(item.visible == bool(visible) for item in targets):
            return 0
        before = self._begin("dimension.show" if visible else "dimension.hide")
        for item in targets:
            item.visible = bool(visible)
            item.modified_at = self.clock()
            item.modified_by = user or "system"
        self._commit(before, user=user)
        return len(targets)

    def move_selected(self, delta: Sequence[float], *, text_only: bool = False, user: str = "system") -> int:
        dx, dy = _point(delta)
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets or (dx == 0.0 and dy == 0.0):
            return 0
        before = self._begin("dimension.move_text" if text_only else "dimension.move")
        for item in targets:
            if not text_only:
                item.line_position = (item.line_position[0] + dx, item.line_position[1] + dy)
            item.text_position = (item.text_position[0] + dx, item.text_position[1] + dy)
            if item.state == DimensionState.RESOLVED.value:
                item.state = DimensionState.MOVED.value
            item.modified_at = self.clock()
            item.modified_by = user or "system"
        self._commit(before, user=user, details={"delta": [dx, dy]})
        return len(targets)

    def update_selected(self, changes: Mapping[str, Any], *, user: str = "system") -> int:
        editable = {
            "label", "prefix", "suffix", "tolerance_upper_mm", "tolerance_lower_mm",
            "reference", "inspection", "note", "visible",
        }
        values = {key: value for key, value in changes.items() if key in editable}
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets or not values:
            return 0
        before = self._begin("dimension.properties")
        for item in targets:
            for key, value in values.items():
                setattr(item, key, value)
            item.modified_at = self.clock()
            item.modified_by = user or "system"
        self._commit(before, user=user, details={"fields": sorted(values)})
        return len(targets)

    def update_style(
        self,
        style: DimensionStyle,
        *,
        reason: str,
        role: str,
        user: str = "system",
    ) -> int:
        if not str(reason).strip():
            raise ValueError("Een maatstijlwijziging vereist een reden")
        role_value = _enum_value(DrawingRole, role, DrawingRole.READ_ONLY)
        approved = role_value in {DrawingRole.CHECKER.value, DrawingRole.RELEASER.value}
        if style.profile_scope != "standard":
            style.base_style_id = DEFAULT_STYLE_ID
            style.approved_by = (user or "system") if approved else ""
        before = self._begin("dimension.style_changed")
        self.document.style = deepcopy(style)
        for item in self.document.dimensions:
            item.style_id = style.style_id
            item.style_version = style.version
            if item.state not in {DimensionState.ORPHANED.value, DimensionState.ORPHANED_VIEW.value}:
                item.state = DimensionState.STALE.value
        self._commit(
            before,
            user=user,
            details={
                "reason": str(reason).strip(),
                "style_id": style.style_id,
                "style_version": style.version,
                "scope": style.profile_scope,
                "approved": approved,
            },
        )
        return len(self.document.dimensions)

    def override_selected(
        self,
        *,
        display_text: str,
        reason: str,
        role: str,
        user: str = "system",
    ) -> int:
        """Override only the visible text; the geometric value remains authoritative."""

        text = str(display_text).strip()
        justification = str(reason).strip()
        if not text or not justification:
            raise ValueError("Een override vereist weergavetekst en een wijzigingsreden")
        targets = [item for item in self.document.dimensions if item.dimension_id in self.selected_ids]
        if not targets:
            return 0
        before = self._begin("dimension.override")
        role_value = _enum_value(DrawingRole, role, DrawingRole.READ_ONLY)
        approver = (user or "system") if role_value in {DrawingRole.CHECKER.value, DrawingRole.RELEASER.value} else ""
        for item in targets:
            item.label = text
            item.override_reason = justification
            item.override_approved_by = approver
            item.state = DimensionState.OVERRIDDEN.value
            item.modified_at = self.clock()
            item.modified_by = user or "system"
        self._commit(
            before,
            user=user,
            details={"approved": bool(approver), "role": role_value, "reason": justification},
        )
        return len(targets)

    def reset_layout(self, *, user: str = "system") -> int:
        targets = [item for item in self.document.dimensions if not self.selected_ids or item.dimension_id in self.selected_ids]
        if not targets:
            return 0
        before = self._begin("dimension.reset_layout")
        for index, item in enumerate(targets):
            points = [anchor.sheet_point for anchor in item.anchors]
            if points:
                x = sum(point[0] for point in points) / len(points)
                y = sum(point[1] for point in points) / len(points) + 8.0 + index * 2.0
                item.line_position = (x, y)
                item.text_position = (x, y - 1.8)
        self._commit(before, user=user)
        return len(targets)

    def reanchor(self, dimension_id: str, anchor_index: int, anchor: DrawingAnchor, *, user: str = "system") -> None:
        item = next(value for value in self.document.dimensions if value.dimension_id == dimension_id)
        if anchor_index < 0 or anchor_index >= len(item.anchors):
            raise IndexError("Ongeldige ankerindex")
        if (
            anchor.view_id != item.view_id
            or anchor.sheet_id != item.sheet_id
            or anchor.page_number != item.page_number
        ):
            raise ValueError("Een nieuw anker moet in hetzelfde aanzicht en op hetzelfde blad liggen")
        before = self._begin("dimension.reanchor")
        item.anchors[anchor_index] = anchor
        item.nominal_value_mm = calculate_nominal_value(
            item.kind,
            item.anchors,
            scale_denominator=1.0,
            angle_mode=str(item.metadata.get("angle_mode") or "inside"),
        )
        item.state = DimensionState.RESOLVED.value
        item.geometry_sha256 = anchor.geometry_sha256
        item.manufacturing_sha256 = anchor.manufacturing_sha256
        self.selected_ids = {dimension_id}
        self._commit(before, user=user, details={"anchor_index": anchor_index})

    def undo(self, *, user: str = "system") -> bool:
        if not self._undo:
            return False
        action, snapshot = self._undo.pop()
        self._redo.append((action, self._snapshot()))
        self.document.dimensions = snapshot
        self.selected_ids &= {item.dimension_id for item in snapshot}
        self._record_history_action("dimension.undo", user=user, source_action=action)
        return True

    def redo(self, *, user: str = "system") -> bool:
        if not self._redo:
            return False
        action, snapshot = self._redo.pop()
        self._undo.append((action, self._snapshot()))
        self.document.dimensions = snapshot
        self.selected_ids &= {item.dimension_id for item in snapshot}
        self._record_history_action("dimension.redo", user=user, source_action=action)
        return True

    def revalidate(self, drawing: DrawingDocument, *, valid_view_ids: Iterable[str]) -> dict[str, int]:
        views = set(valid_view_ids)
        candidates = build_snap_candidates(drawing, entity_id=self.document.entity_id)
        valid_subshapes = {item.anchor.subshape_id for item in candidates if item.anchor.subshape_id}
        valid_features = {
            str(item.get("feature_id") or item.get("id") or "")
            for item in drawing.features
            if str(item.get("feature_id") or item.get("id") or "")
        }
        counts = {state.value: 0 for state in DimensionState}
        for item in self.document.dimensions:
            if item.kind == DimensionKind.TEXT.value:
                item.state = DimensionState.RESOLVED.value
                counts[item.state] += 1
                continue
            if item.view_id not in views:
                item.state = DimensionState.ORPHANED_VIEW.value
            elif not item.anchors or any(not anchor.resolved for anchor in item.anchors):
                item.state = DimensionState.ORPHANED.value
            elif any(
                anchor.subshape_id
                and anchor.subshape_id not in valid_subshapes
                and (not anchor.feature_id or anchor.feature_id not in valid_features)
                for anchor in item.anchors
            ):
                item.state = DimensionState.ORPHANED.value
            elif item.geometry_sha256 != drawing.geometry_sha256 or item.manufacturing_sha256 != drawing.manufacturing_sha256:
                item.state = DimensionState.STALE.value
            else:
                expected = calculate_nominal_value(
                    item.kind,
                    item.anchors,
                    angle_mode=str(item.metadata.get("angle_mode") or "inside"),
                )
                if abs(expected - item.nominal_value_mm) > max(1.0e-6, abs(expected) * 1.0e-8):
                    item.state = DimensionState.OVERRIDDEN.value if item.override_reason else DimensionState.CONFLICT.value
                elif item.state not in {DimensionState.MOVED.value, DimensionState.OVERRIDDEN.value}:
                    item.state = DimensionState.RESOLVED.value
            counts[item.state] += 1
        return counts


class DimensionDocumentStore:
    """Persist editor documents in the canonical project settings payload."""

    @staticmethod
    def key(entity_id: str, drawing_id: str = "production") -> str:
        return f"{str(entity_id)}::{str(drawing_id)}"

    @classmethod
    def load(
        cls,
        project: Any,
        *,
        entity_id: str,
        drawing_id: str = "production",
        source_revision: str = "",
        geometry_sha256: str = "",
        manufacturing_sha256: str = "",
        user: str = "system",
    ) -> DimensionEditorDocument:
        root = dict(getattr(project, "settings", {}).get(DIMENSION_SETTINGS_KEY) or {})
        documents = dict(root.get("documents") or {})
        raw = documents.get(cls.key(entity_id, drawing_id))
        if isinstance(raw, Mapping):
            return DimensionEditorDocument.from_dict(raw)
        return DimensionEditorDocument(
            project_id=str(getattr(project, "project_id", "")),
            entity_id=str(entity_id),
            drawing_id=str(drawing_id),
            source_revision=str(source_revision),
            drawing_revision="draft-1",
            geometry_sha256=str(geometry_sha256),
            manufacturing_sha256=str(manufacturing_sha256),
            created_by=user or "system",
            modified_by=user or "system",
        )

    @classmethod
    def save(
        cls,
        project: Any,
        document: DimensionEditorDocument,
        *,
        expected_lock_version: int | None = None,
        user: str = "system",
    ) -> int:
        settings: MutableMapping[str, Any] = getattr(project, "settings")
        root = deepcopy(dict(settings.get(DIMENSION_SETTINGS_KEY) or {}))
        if root and str(root.get("schema") or DIMENSION_EDITOR_SCHEMA) != DIMENSION_EDITOR_SCHEMA:
            raise ValueError("Onbekend projectmaatvoeringsschema; opslag afgebroken")
        documents = dict(root.get("documents") or {})
        key = cls.key(document.entity_id, document.drawing_id)
        current = documents.get(key)
        current_version = int(dict(current or {}).get("lock_version") or 0)
        if expected_lock_version is not None and current_version != int(expected_lock_version):
            raise RuntimeError(
                "Maatvoering is intussen gewijzigd; silent last-write-wins is geblokkeerd "
                f"(opgeslagen versie {current_version}, geopende basis {int(expected_lock_version)}, "
                f"lokale documentversie {document.lock_version})"
            )
        document.lock_version = current_version + 1
        document.modified_at = _now()
        document.modified_by = user or "system"
        documents[key] = document.to_dict()
        settings[DIMENSION_SETTINGS_KEY] = {
            "schema": DIMENSION_EDITOR_SCHEMA,
            "documents": {name: documents[name] for name in sorted(documents)},
        }
        return document.lock_version

    @classmethod
    def migrate_legacy(
        cls,
        values: Sequence[Mapping[str, Any]],
        document: DimensionEditorDocument,
        *,
        user: str = "system",
    ) -> int:
        existing = {item.dimension_id for item in document.dimensions}
        added = 0
        for index, raw in enumerate(values, start=1):
            dimension_id = str(raw.get("id") or raw.get("dimension_id") or f"legacy-{index:03d}")
            if dimension_id in existing:
                continue
            start = float(raw.get("start") or 0.0)
            end = float(raw.get("end") or 0.0)
            vertical = str(raw.get("axis") or "horizontal") == "vertical"
            first_point = (0.0, start) if vertical else (start, 0.0)
            second_point = (0.0, end) if vertical else (end, 0.0)
            anchors = [
                DrawingAnchor(
                    entity_id=document.entity_id,
                    feature_id=str(raw.get("feature_id") or "part-envelope"),
                    subshape_id=str(raw.get("subshape_id") or ""),
                    view_id=str(raw.get("view") or "front"),
                    sheet_id="sheet-1",
                    page_number=1,
                    anchor_type=str(raw.get("anchor_type") or SnapType.DATUM.value),
                    projected_point=point,
                    sheet_point=point,
                    source_revision=document.source_revision,
                    geometry_sha256=document.geometry_sha256,
                    manufacturing_sha256=document.manufacturing_sha256,
                    proof="legacy_offset",
                )
                for point in (first_point, second_point)
            ]
            line = ((start + end) * 0.5, 8.0) if not vertical else (8.0, (start + end) * 0.5)
            document.dimensions.append(
                InteractiveDimension(
                    dimension_id=dimension_id,
                    kind=DimensionKind.VERTICAL.value if vertical else DimensionKind.HORIZONTAL.value,
                    entity_ids=(document.entity_id,),
                    drawing_id=document.drawing_id,
                    view_id=str(raw.get("view") or "front"),
                    sheet_id="sheet-1",
                    page_number=1,
                    anchors=anchors,
                    nominal_value_mm=abs(end - start),
                    line_position=line,
                    text_position=(line[0], line[1] - 1.8),
                    label=str(raw.get("label") or ""),
                    tolerance_upper_mm=float(raw.get("tolerance_mm") or 0.0),
                    tolerance_lower_mm=-float(raw.get("tolerance_mm") or 0.0),
                    state=DimensionState.STALE.value,
                    source_revision=document.source_revision,
                    geometry_sha256=document.geometry_sha256,
                    manufacturing_sha256=document.manufacturing_sha256,
                    created_by=user or "system",
                    modified_by=user or "system",
                    metadata={"migrated_from": "legacy_numeric_offset", "legacy": dict(raw)},
                )
            )
            existing.add(dimension_id)
            added += 1
        return added


def calculate_nominal_value(
    kind: str,
    anchors: Sequence[DrawingAnchor],
    *,
    scale_denominator: float = 1.0,
    angle_mode: str = "inside",
) -> float:
    if not anchors:
        return 0.0
    points = [anchor.projected_point for anchor in anchors]
    kind = _enum_value(DimensionKind, kind, DimensionKind.ALIGNED)
    if kind in {DimensionKind.RADIUS.value, DimensionKind.DIAMETER.value}:
        radius = float(anchors[0].curve_parameter or 0.0)
        return radius * (2.0 if kind == DimensionKind.DIAMETER.value else 1.0)
    if len(points) < 2:
        return 0.0
    if kind in {DimensionKind.HORIZONTAL.value, DimensionKind.ORDINATE_X.value}:
        return abs(points[1][0] - points[0][0])
    if kind in {DimensionKind.VERTICAL.value, DimensionKind.ORDINATE_Y.value}:
        return abs(points[1][1] - points[0][1])
    if kind == DimensionKind.ANGLE.value and len(points) >= 3:
        first = math.atan2(points[0][1] - points[1][1], points[0][0] - points[1][0])
        second = math.atan2(points[2][1] - points[1][1], points[2][0] - points[1][0])
        inside = abs(math.degrees(math.atan2(math.sin(second - first), math.cos(second - first))))
        if str(angle_mode).lower() == "outside":
            return 360.0 - inside
        if str(angle_mode).lower() == "supplementary":
            return abs(180.0 - inside)
        return inside
    if kind in {DimensionKind.CHAIN.value, DimensionKind.BASELINE.value} and len(points) > 2:
        return sum(_distance(left, right) for left, right in zip(points, points[1:]))
    return _distance(points[0], points[1])


def _view_contexts(document: DrawingDocument) -> list[dict[str, Any]]:
    contexts = list(getattr(document, "view_contexts", ()) or ())
    if contexts:
        return [dict(item) for item in contexts]
    result = []
    for page in document.pages:
        for primitive in page.primitives:
            if primitive.layer == "views" and primitive.kind == "rect" and primitive.semantic_id and len(primitive.points) == 2:
                result.append(
                    {
                        "view_id": primitive.semantic_id,
                        "view": primitive.semantic_id.split("-")[-2] if "-" in primitive.semantic_id else "front",
                        "page_number": page.number,
                        "sheet_id": f"sheet-{page.number}",
                        "rectangle": [*primitive.points[0], *primitive.points[1]],
                        "projected_center": [0.0, 0.0],
                        "sheet_center": [
                            (primitive.points[0][0] + primitive.points[1][0]) * 0.5,
                            (primitive.points[0][1] + primitive.points[1][1]) * 0.5 + 2.0,
                        ],
                        "scale": 1.0 / max(1, document.scale_denominator),
                    }
                )
    return result


def _inside(point: Sequence[float], rectangle: Sequence[float], tolerance: float = 0.5) -> bool:
    return (
        len(rectangle) == 4
        and float(rectangle[0]) - tolerance <= float(point[0]) <= float(rectangle[2]) + tolerance
        and float(rectangle[1]) - tolerance <= float(point[1]) <= float(rectangle[3]) + tolerance
    )


def _projected_point(point: Sequence[float], context: Mapping[str, Any]) -> tuple[float, float]:
    scale = float(context.get("scale") or 1.0)
    center = _point(context.get("projected_center")) or (0.0, 0.0)
    sheet_center = _point(context.get("sheet_center")) or (0.0, 0.0)
    return (
        (float(point[0]) - sheet_center[0]) / scale + center[0],
        -(float(point[1]) - sheet_center[1]) / scale + center[1],
    )


def build_snap_candidates(
    document: DrawingDocument,
    *,
    entity_id: str | None = None,
    snap_filter: str = SnapFilter.ALL.value,
    include_intersections: bool = True,
) -> list[SnapCandidate]:
    """Derive deterministic snap targets from vector drawing geometry."""

    filter_value = _enum_value(SnapFilter, snap_filter, SnapFilter.ALL)
    contexts = _view_contexts(document)
    canonical = (
        document.geometry_basis == "canonical_rebuild_brep"
        and document.hlr_method == "occt_hlr"
        and len(document.geometry_sha256) == 64
    )
    candidates: dict[tuple[int, int, str, str], SnapCandidate] = {}
    segments: list[tuple[tuple[float, float], tuple[float, float], dict[str, Any], DrawingPrimitive]] = []

    def context_for(page_number: int, point: Sequence[float], primitive: DrawingPrimitive) -> dict[str, Any] | None:
        prefix = primitive.semantic_id.rsplit("-visible-", 1)[0] if "-visible-" in primitive.semantic_id else ""
        values = [item for item in contexts if int(item.get("page_number") or 1) == page_number]
        if prefix:
            exact = next((item for item in values if str(item.get("view_id")) == prefix), None)
            if exact:
                return exact
        return next((item for item in values if _inside(point, item.get("rectangle") or ())), None)

    def allowed(layer: str, kind: str) -> bool:
        if filter_value == SnapFilter.ALL.value:
            return True
        if filter_value == SnapFilter.POINTS.value:
            return kind in {
                SnapType.VERTEX.value,
                SnapType.ENDPOINT.value,
                SnapType.MIDPOINT.value,
                SnapType.INTERSECTION.value,
                SnapType.TANGENT.value,
                SnapType.DATUM.value,
                SnapType.EXISTING_ANCHOR.value,
            }
        if filter_value == SnapFilter.EDGES.value:
            return layer in {"visible", "hidden"}
        if filter_value == SnapFilter.CENTERS.value:
            return kind == SnapType.CENTER.value
        if filter_value == SnapFilter.CENTERLINES.value:
            return layer == "centerlines"
        if filter_value == SnapFilter.FEATURES.value:
            return layer == "annotations"
        if filter_value == SnapFilter.DIMENSIONS.value:
            return layer == "dimensions"
        return layer in {"annotations", "notes"}

    def add(
        page_number: int,
        point: Sequence[float],
        kind: str,
        primitive: DrawingPrimitive,
        index: int,
        *,
        curve_parameter: float | None = None,
    ) -> None:
        context = context_for(page_number, point, primitive)
        if context is None or not allowed(primitive.layer, kind):
            return
        point_value = (float(point[0]), float(point[1]))
        entity_reference = next(
            (str(item).split(":", 1)[1] for item in primitive.refs if str(item).startswith("entity:") and ":" in str(item)),
            "",
        )
        feature_id = next((str(item) for item in primitive.refs if str(item) and not str(item).startswith("entity:")), "")
        subshape_id = str(primitive.semantic_id or f"{primitive.layer}-{index}")
        view_id = str(context.get("view_id") or context.get("view") or "front")
        anchor = DrawingAnchor(
            entity_id=str(entity_reference or entity_id or document.entity_id),
            feature_id=feature_id,
            subshape_id=subshape_id,
            view_id=view_id,
            sheet_id=str(context.get("sheet_id") or f"sheet-{page_number}"),
            page_number=page_number,
            anchor_type=kind,
            curve_parameter=curve_parameter,
            projected_point=_projected_point(point_value, context),
            sheet_point=point_value,
            source_revision=document.source_revision,
            geometry_sha256=document.geometry_sha256,
            manufacturing_sha256=document.manufacturing_sha256,
            proof="canonical_projection" if canonical else "review_projection",
        )
        key = (round(point_value[0] * 1000), round(point_value[1] * 1000), view_id, kind)
        candidates.setdefault(
            key,
            SnapCandidate(
                candidate_id=f"{page_number}:{view_id}:{anchor.entity_id}:{subshape_id}:{kind}:{index}",
                point=point_value,
                snap_type=kind,
                label=f"{kind} · {feature_id or subshape_id}",
                anchor=anchor,
                valid=True,
                layer=primitive.layer,
            ),
        )

    for page in document.pages:
        for primitive_index, primitive in enumerate(page.primitives):
            if primitive.layer not in {"visible", "hidden", "centerlines", "annotations", "dimensions"}:
                continue
            if primitive.kind in {"line", "polyline", "polygon"} and len(primitive.points) >= 2:
                points = [(float(point[0]), float(point[1])) for point in primitive.points]
                for segment_index, (left, right) in enumerate(zip(points, points[1:])):
                    if primitive.layer in {"visible", "centerlines", "annotations"}:
                        segments.append((left, right, context_for(page.number, left, primitive) or {}, primitive))
                    add(page.number, left, SnapType.ENDPOINT.value, primitive, primitive_index * 100 + segment_index * 3)
                    add(page.number, right, SnapType.ENDPOINT.value, primitive, primitive_index * 100 + segment_index * 3 + 1)
                    if primitive.layer == "dimensions":
                        add(page.number, left, SnapType.EXISTING_ANCHOR.value, primitive, primitive_index * 100 + segment_index * 5)
                        add(page.number, right, SnapType.EXISTING_ANCHOR.value, primitive, primitive_index * 100 + segment_index * 5 + 1)
                    add(
                        page.number,
                        ((left[0] + right[0]) * 0.5, (left[1] + right[1]) * 0.5),
                        SnapType.MIDPOINT.value,
                        primitive,
                        primitive_index * 100 + segment_index * 3 + 2,
                    )
            elif primitive.kind == "rect" and len(primitive.points) == 2 and primitive.layer != "views":
                left, top = primitive.points[0]
                right, bottom = primitive.points[1]
                for index, point in enumerate(((left, top), (right, top), (right, bottom), (left, bottom))):
                    add(page.number, point, SnapType.VERTEX.value, primitive, primitive_index * 10 + index)
                add(page.number, ((left + right) * 0.5, (top + bottom) * 0.5), SnapType.CENTER.value, primitive, primitive_index)
                if primitive.refs:
                    add(page.number, ((left + right) * 0.5, (top + bottom) * 0.5), SnapType.FEATURE.value, primitive, primitive_index)
            elif primitive.kind == "circle" and len(primitive.center) == 2:
                center = (float(primitive.center[0]), float(primitive.center[1]))
                context = context_for(page.number, center, primitive)
                projected_radius = float(primitive.radius) / max(float(dict(context or {}).get("scale") or 1.0), 1.0e-9)
                add(
                    page.number,
                    center,
                    SnapType.CENTER.value,
                    primitive,
                    primitive_index,
                    curve_parameter=projected_radius,
                )
                if primitive.refs:
                    add(
                        page.number,
                        center,
                        SnapType.FEATURE.value,
                        primitive,
                        primitive_index,
                        curve_parameter=projected_radius,
                    )
                for index, point in enumerate(
                    (
                        (center[0] - primitive.radius, center[1]),
                        (center[0] + primitive.radius, center[1]),
                        (center[0], center[1] - primitive.radius),
                        (center[0], center[1] + primitive.radius),
                    )
                ):
                    add(page.number, point, SnapType.ENDPOINT.value, primitive, primitive_index * 10 + index)
                    add(page.number, point, SnapType.TANGENT.value, primitive, primitive_index * 20 + index)

    for context_index, context in enumerate(contexts):
        sheet_center = _point(context.get("sheet_center"))
        if not sheet_center:
            continue
        marker = DrawingPrimitive(
            "line",
            "centerlines",
            points=[list(sheet_center), list(sheet_center)],
            refs=[document.entity_id],
            semantic_id=f"{context.get('view_id')}-datum",
        )
        add(int(context.get("page_number") or 1), sheet_center, SnapType.DATUM.value, marker, context_index)

    if include_intersections:
        for index, first in enumerate(segments):
            for second in segments[index + 1 :]:
                if first[2].get("view_id") != second[2].get("view_id"):
                    continue
                point = segment_intersection(first[0], first[1], second[0], second[1])
                if point is not None:
                    add(int(first[2].get("page_number") or 1), point, SnapType.INTERSECTION.value, first[3], index)
    return sorted(candidates.values(), key=lambda item: (item.anchor.page_number, item.anchor.view_id, item.point, item.snap_type, item.candidate_id))


def segment_intersection(
    first_start: Sequence[float],
    first_end: Sequence[float],
    second_start: Sequence[float],
    second_end: Sequence[float],
) -> tuple[float, float] | None:
    x1, y1 = (float(item) for item in first_start)
    x2, y2 = (float(item) for item in first_end)
    x3, y3 = (float(item) for item in second_start)
    x4, y4 = (float(item) for item in second_end)
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1.0e-9:
        return None
    first_t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denominator
    second_t = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denominator
    if not (-1.0e-8 <= first_t <= 1.0 + 1.0e-8 and -1.0e-8 <= second_t <= 1.0 + 1.0e-8):
        return None
    return (x1 + first_t * (x2 - x1), y1 + first_t * (y2 - y1))


def nearest_snap_candidate(
    document: DrawingDocument,
    point: Sequence[float],
    *,
    page_number: int = 1,
    entity_id: str | None = None,
    maximum_distance_sheet: float = 3.0,
) -> SnapCandidate | None:
    """Return the closest continuously projected point on a visible edge."""

    target = _point(point)
    if not target or not 1 <= int(page_number) <= len(document.pages):
        return None
    contexts = [item for item in _view_contexts(document) if int(item.get("page_number") or 1) == int(page_number)]
    canonical = (
        document.geometry_basis == "canonical_rebuild_brep"
        and document.hlr_method == "occt_hlr"
        and len(document.geometry_sha256) == 64
    )
    hits: list[tuple[float, tuple[float, float], DrawingPrimitive, dict[str, Any], int]] = []
    for primitive_index, primitive in enumerate(document.pages[int(page_number) - 1].primitives):
        if primitive.layer not in {"visible", "annotations", "centerlines"} or primitive.kind not in {"line", "polyline", "polygon"}:
            continue
        points = [(float(value[0]), float(value[1])) for value in primitive.points]
        for segment_index, (left, right) in enumerate(zip(points, points[1:])):
            dx, dy = right[0] - left[0], right[1] - left[1]
            length_squared = dx * dx + dy * dy
            if length_squared <= 1.0e-12:
                continue
            parameter = max(0.0, min(1.0, ((target[0] - left[0]) * dx + (target[1] - left[1]) * dy) / length_squared))
            nearest = (left[0] + parameter * dx, left[1] + parameter * dy)
            distance = _distance(target, nearest)
            if distance > float(maximum_distance_sheet):
                continue
            prefix = primitive.semantic_id.rsplit("-visible-", 1)[0] if "-visible-" in primitive.semantic_id else ""
            context = next((item for item in contexts if prefix and str(item.get("view_id") or "") == prefix), None)
            if context is None:
                context = next((item for item in contexts if _inside(nearest, item.get("rectangle") or ())), None)
            if context is not None:
                hits.append((distance, nearest, primitive, dict(context), primitive_index * 1000 + segment_index))
    if not hits:
        return None
    distance, nearest, primitive, context, identity = min(hits, key=lambda item: (item[0], item[2].semantic_id, item[4]))
    entity_reference = next(
        (str(item).split(":", 1)[1] for item in primitive.refs if str(item).startswith("entity:") and ":" in str(item)),
        "",
    )
    feature_id = next((str(item) for item in primitive.refs if str(item) and not str(item).startswith("entity:")), "")
    anchor = DrawingAnchor(
        entity_id=str(entity_reference or entity_id or document.entity_id),
        feature_id=feature_id,
        subshape_id=str(primitive.semantic_id or f"{primitive.layer}-{identity}"),
        view_id=str(context.get("view_id") or context.get("view") or "front"),
        sheet_id=str(context.get("sheet_id") or f"sheet-{page_number}"),
        page_number=int(page_number),
        anchor_type=SnapType.NEAREST.value,
        curve_parameter=None,
        projected_point=_projected_point(nearest, context),
        sheet_point=nearest,
        source_revision=document.source_revision,
        geometry_sha256=document.geometry_sha256,
        manufacturing_sha256=document.manufacturing_sha256,
        proof="canonical_projection" if canonical else "review_projection",
    )
    return SnapCandidate(
        candidate_id=f"{page_number}:{anchor.view_id}:{anchor.entity_id}:{anchor.subshape_id}:nearest:{identity}",
        point=nearest,
        snap_type=SnapType.NEAREST.value,
        label=f"nearest · {feature_id or anchor.subshape_id}",
        anchor=anchor,
        valid=True,
        layer=primitive.layer,
    )


class DimensionInteractionController:
    """Explicit CAD-like placement state machine, independent from Qt."""

    SINGLE_ANCHOR = {DimensionKind.RADIUS.value, DimensionKind.DIAMETER.value, DimensionKind.LEADER.value}
    THREE_ANCHOR = {DimensionKind.ANGLE.value}
    MULTI_ANCHOR = {DimensionKind.CHAIN.value, DimensionKind.BASELINE.value}

    def __init__(self) -> None:
        self.state = InteractionState.IDLE
        self.state_history: list[InteractionState] = [InteractionState.IDLE]
        self.kind = DimensionKind.ALIGNED.value
        self.anchors: list[DrawingAnchor] = []
        self.pointer: tuple[float, float] | None = None

    def set_state(self, state: InteractionState) -> InteractionState:
        self.state = state
        self.state_history.append(state)
        return state

    @property
    def instruction(self) -> str:
        if self.state in {InteractionState.IDLE, InteractionState.CANCELLED, InteractionState.COMMITTED}:
            return "Selecteer een maatgereedschap"
        if self.state in {InteractionState.TOOL_ARMED, InteractionState.PICK_FIRST_ANCHOR}:
            return "Selecteer eerste punt · Esc om te annuleren"
        if self.state == InteractionState.PICK_NEXT_ANCHOR:
            return "Selecteer volgende punt · Backspace één stap terug"
        if self.state in {InteractionState.PLACE_DIMENSION_LINE, InteractionState.PLACE_TEXT}:
            return "Plaats maatlijn of tekst · klik/Enter bevestigt"
        return "Maat bewerken · Esc om te annuleren"

    def arm(self, kind: str) -> None:
        self.kind = _enum_value(DimensionKind, kind, DimensionKind.ALIGNED)
        self.anchors.clear()
        self.pointer = None
        self.set_state(InteractionState.TOOL_ARMED)
        self.set_state(InteractionState.PLACE_TEXT if self.kind == DimensionKind.TEXT.value else InteractionState.PICK_FIRST_ANCHOR)

    def accept_anchor(self, anchor: DrawingAnchor) -> InteractionState:
        if self.state not in {InteractionState.PICK_FIRST_ANCHOR, InteractionState.PICK_NEXT_ANCHOR}:
            raise RuntimeError("Het gereedschap verwacht nu geen anker")
        if self.anchors and anchor.view_id != self.anchors[0].view_id:
            raise ValueError("Alle ankers moeten in hetzelfde aanzicht liggen")
        self.anchors.append(anchor)
        required = 1 if self.kind in self.SINGLE_ANCHOR else 3 if self.kind in self.THREE_ANCHOR else 2
        if len(self.anchors) >= required and self.kind not in self.MULTI_ANCHOR:
            self.set_state(InteractionState.PLACE_TEXT if self.kind in {DimensionKind.LEADER.value, DimensionKind.TEXT.value} else InteractionState.PLACE_DIMENSION_LINE)
        else:
            self.set_state(InteractionState.PICK_NEXT_ANCHOR)
        return self.state

    def finish_anchor_series(self) -> InteractionState:
        if self.kind not in self.MULTI_ANCHOR or len(self.anchors) < 2:
            raise ValueError("Een maatserie vereist minimaal twee ankers")
        self.set_state(InteractionState.PLACE_DIMENSION_LINE)
        return self.state

    def backspace(self) -> InteractionState:
        if self.anchors:
            self.anchors.pop()
        self.set_state(InteractionState.PICK_NEXT_ANCHOR if self.anchors else InteractionState.PICK_FIRST_ANCHOR)
        return self.state

    def cancel(self) -> None:
        self.anchors.clear()
        self.pointer = None
        self.set_state(InteractionState.CANCELLED)

    def place(
        self,
        point: Sequence[float],
        *,
        document: DimensionEditorDocument,
        user: str = "system",
        label: str = "",
    ) -> InteractiveDimension:
        if self.state not in {InteractionState.PLACE_DIMENSION_LINE, InteractionState.PLACE_TEXT}:
            raise RuntimeError("Ankers zijn nog niet compleet")
        position = _point(point)
        if not position:
            raise ValueError("Ongeldige plaatsingspositie")
        active_view_id = str(document.extensions.get("active_view_id") or "front")
        active_page = int(document.extensions.get("active_page_number") or 1)
        anchor = self.anchors[0] if self.anchors else DrawingAnchor(
            entity_id=document.entity_id,
            view_id=active_view_id,
            sheet_id=f"sheet-{active_page}",
            page_number=active_page,
            anchor_type=SnapType.DATUM.value,
            projected_point=position,
            sheet_point=position,
            source_revision=document.source_revision,
            geometry_sha256=document.geometry_sha256,
            manufacturing_sha256=document.manufacturing_sha256,
            proof="non_geometric_annotation",
        )
        placed_anchors = deepcopy(self.anchors) or ([deepcopy(anchor)] if self.kind == DimensionKind.TEXT.value else [])
        value = calculate_nominal_value(self.kind, self.anchors, angle_mode="inside")
        dimension_id = str(uuid4())
        metadata: dict[str, Any] = {}
        if self.kind == DimensionKind.ANGLE.value:
            metadata["angle_mode"] = "inside"
        if self.kind in self.MULTI_ANCHOR:
            metadata["segment_ids"] = [
                f"{dimension_id}:segment:{index + 1}"
                for index in range(max(0, len(placed_anchors) - 1))
            ]
        dimension = InteractiveDimension(
            dimension_id=dimension_id,
            kind=self.kind,
            entity_ids=tuple(dict.fromkeys(item.entity_id for item in placed_anchors)) or (document.entity_id,),
            drawing_id=document.drawing_id,
            view_id=anchor.view_id,
            sheet_id=anchor.sheet_id,
            page_number=anchor.page_number,
            anchors=placed_anchors,
            nominal_value_mm=value,
            line_position=position,
            text_position=(position[0], position[1] - 1.8),
            label=label,
            source_revision=document.source_revision,
            drawing_revision=document.drawing_revision,
            geometry_sha256=anchor.geometry_sha256,
            manufacturing_sha256=anchor.manufacturing_sha256,
            created_by=user or "system",
            modified_by=user or "system",
            style_id=document.style.style_id,
            style_version=document.style.version,
            metadata=metadata,
        )
        self.anchors.clear()
        self.set_state(InteractionState.COMMITTED)
        return dimension


__all__ = [
    "DEFAULT_STYLE_ID",
    "DEFAULT_STYLE_VERSION",
    "DIMENSION_EDITOR_SCHEMA",
    "DIMENSION_SETTINGS_KEY",
    "DimensionDocumentStore",
    "DimensionEditorDocument",
    "DimensionEditorModel",
    "DimensionInteractionController",
    "DimensionKind",
    "DimensionState",
    "DimensionStyle",
    "DrawingAnchor",
    "DrawingRole",
    "InteractionState",
    "InteractiveDimension",
    "SnapCandidate",
    "SnapFilter",
    "SnapType",
    "build_snap_candidates",
    "calculate_nominal_value",
    "nearest_snap_candidate",
    "segment_intersection",
]
