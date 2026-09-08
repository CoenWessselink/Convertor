"""Pure presentation logic for auditable material review in the editor.

The module intentionally has no Qt dependency.  Candidate ranking, evidence
projection and bulk scoping can therefore be regression-tested on systems
where PySide6 is not installed.  Applying a decision remains the responsibility
of :class:`EditWorkspacePanel`, which delegates all manufacturing mutations to
``ProjectSession`` and Part Workbench.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, is_dataclass
from difflib import SequenceMatcher
import math
from typing import Any, Iterable, Mapping
from uuid import uuid4


def _text(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    from cws_convertor.material_resolution import normalize_material_key
    return normalize_material_key(_text(value))


def bounded_confidence(value: Any) -> float:
    """Return a display-safe confidence without consulting entity confidence."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number))


def selection_ids(selection: Any | None) -> tuple[str, ...]:
    if selection is None:
        return ()
    if isinstance(selection, Mapping):
        values = (
            selection.get("entity_ids")
            or selection.get("selected_entity_ids")
            or selection.get("part_ids")
            or ()
        )
        primary = selection.get("primary_entity_id") or selection.get("entity_id")
    else:
        values = ()
        for name in ("entity_ids", "selected_entity_ids", "part_ids", "ids"):
            values = getattr(selection, name, None) or ()
            if values:
                break
        primary = getattr(selection, "primary_entity_id", "") or getattr(selection, "entity_id", "")
    if isinstance(values, str):
        values = (values,)
    result = [str(value) for value in values if str(value)]
    if not result and primary:
        result.append(str(primary))
    return tuple(dict.fromkeys(result))


def raw_material(part: Any) -> str:
    return _text(getattr(part, "material_grade", "") or getattr(part, "material", ""))


def source_class(part: Any) -> str:
    properties = getattr(part, "properties", {}) or {}
    if not isinstance(properties, Mapping):
        properties = {}
    return _text(properties.get("ifc_entity_type") or getattr(part, "part_type", "")).upper()


def _resolution(database: Any, value: Any) -> tuple[str, str, float, str]:
    """Return ``(code, status, confidence, reason)`` without unsafe fallback."""

    if database is None or not _text(value):
        return "", "unresolved", 0.0, "Geen materiaalwaarde aanwezig."
    resolver = getattr(database, "resolve", None)
    if callable(resolver):
        result = resolver(value, provenance={"source_kind": "qt_material_review"})
        return (
            _text(getattr(result, "material_code", "")),
            _text(getattr(result, "status", "unresolved")) or "unresolved",
            bounded_confidence(getattr(result, "confidence", 0.0)),
            _text(getattr(result, "reason", "")),
        )
    key = _key(value)
    for item in getattr(database, "materials", ()):
        code_key = _key(getattr(item, "code", ""))
        aliases = {_key(alias) for alias in getattr(item, "aliases", ()) if _key(alias)}
        if key == code_key:
            return _text(item.code), "exact", 1.0, "Volledige waarde is een exacte cataloguscode."
        if key and key in aliases:
            return _text(item.code), "alias", 0.95, "Volledige waarde is een expliciete catalogusalias."
    return "", "unresolved", 0.0, "Geen exacte code of expliciete alias in de catalogus."


@dataclass(frozen=True, slots=True)
class MaterialCandidate:
    code: str
    name: str
    category: str
    standard: str
    catalog_match: float
    source_confidence: float
    match_status: str
    reason: str


def catalog_candidates(
    database: Any,
    query: Any,
    *,
    source_confidence: Any = 0.0,
    limit: int = 250,
) -> tuple[MaterialCandidate, ...]:
    """Rank catalog rows for human review; ranking never confirms a material."""

    materials = tuple(getattr(database, "materials", ()) or ())
    query_text = _text(query)
    query_key = _key(query_text)
    resolved_code, resolved_status, resolved_confidence, resolved_reason = _resolution(database, query_text)
    evidence_confidence = bounded_confidence(source_confidence)
    rows: list[MaterialCandidate] = []
    for material in materials:
        code = _text(getattr(material, "code", ""))
        names = [code, *[_text(value) for value in getattr(material, "aliases", ())]]
        keys = [_key(value) for value in names if _key(value)]
        if code == resolved_code:
            score = resolved_confidence
            status = resolved_status
            reason = resolved_reason
        elif not query_key:
            score = 0.0
            status = "catalogus"
            reason = "Catalogusoptie; geen bronmatch berekend."
        else:
            similarity = max(
                (SequenceMatcher(None, query_key, candidate).ratio() for candidate in keys),
                default=0.0,
            )
            contains = any(query_key in candidate or candidate in query_key for candidate in keys)
            score = min(0.89, max(similarity * 0.75, 0.70 if contains else 0.0))
            status = "suggestie"
            reason = "Zoeksuggestie voor handmatige beoordeling; geen automatische herkenning."
        searchable = " ".join(
            [
                code,
                _text(getattr(material, "name", "")),
                _text(getattr(material, "category", "")),
                _text(getattr(material, "standard", "")),
                *names[1:],
            ]
        ).upper()
        if query_text and score < 0.30 and query_text.upper() not in searchable:
            continue
        rows.append(
            MaterialCandidate(
                code=code,
                name=_text(getattr(material, "name", "")),
                category=_text(getattr(material, "category", "")),
                standard=_text(getattr(material, "standard", "")),
                catalog_match=score,
                source_confidence=evidence_confidence if code == resolved_code else 0.0,
                match_status=status,
                reason=reason,
            )
        )
    rows.sort(key=lambda row: (-row.catalog_match, row.code))
    return tuple(rows[: max(0, int(limit))])


@dataclass(frozen=True, slots=True)
class MaterialEvidence:
    source: str
    value: str
    method: str
    confidence: float
    provenance: str


def _plain_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    return {}


def material_evidence(part: Any | None) -> tuple[MaterialEvidence, ...]:
    if part is None:
        return ()
    result: list[MaterialEvidence] = []
    identity = getattr(part, "source_identity", None)
    source_format = _text(getattr(identity, "source_format", "")) or "ONBEKEND"
    source_entity = _text(getattr(identity, "source_entity_id", "")) or "-"
    confidence = bounded_confidence(getattr(part, "material_confidence", 0.0))
    for label, value in (
        ("Bronmateriaal", getattr(part, "material", "")),
        ("Materiaalkwaliteit", getattr(part, "material_grade", "")),
        ("Genormaliseerd", getattr(part, "normalized_material", "")),
    ):
        if _text(value):
            result.append(
                MaterialEvidence(label, _text(value), "projectveld", confidence, f"{source_format}:{source_entity}")
            )

    properties = getattr(part, "properties", {}) or {}
    if isinstance(properties, Mapping):
        ifc_materials = properties.get("ifc_materials") or ()
        if isinstance(ifc_materials, str):
            ifc_materials = (ifc_materials,)
        for value in ifc_materials:
            if _text(value):
                result.append(
                    MaterialEvidence("IFC-relatie", _text(value), "IfcRelAssociatesMaterial", confidence, source_entity)
                )
        for record in properties.get("ifc_material_semantics") or ():
            if not isinstance(record, Mapping):
                continue
            inherited = bool(record.get("inherited_from_type"))
            effective = bool(record.get("effective", True))
            role = _text(record.get("layer_category") or record.get("material_profile_category") or record.get("constituent_category"))
            trail = " / ".join(_text(value) for value in record.get("material_path_entity_ids") or ())
            result.append(MaterialEvidence(
                "IFC-type" if inherited else "IFC-onderdeel",
                _text(record.get("material_name")) or "-",
                _text(record.get("semantic_kind")) + (f" ({role})" if role else ""),
                confidence if effective else 0.0,
                f"#{record.get('association_entity_id', '-')} → {trail}; "
                + ("actieve bronverklaring" if effective else "overschreven typeverklaring; niet gebruikt"),
            ))
        resolution = properties.get("ifc_material_resolution") or {}
        if isinstance(resolution, Mapping):
            for record in resolution.get("property_evidence") or ():
                if isinstance(record, Mapping):
                    result.append(MaterialEvidence(
                        "IFC-property",
                        _text(record.get("value")),
                        _text(resolution.get("status")) or "bronverklaring",
                        bounded_confidence(resolution.get("confidence")) if record.get("effective", True) else 0.0,
                        f"#{record.get('source_entity_id', '-')}: {record.get('source_path', '-')}"
                        + (" (overschreven typeverklaring)" if not record.get("effective", True) else ""),
                    ))

    descriptor = getattr(part, "geometry_descriptor", {}) or {}
    if isinstance(descriptor, Mapping):
        recognition = descriptor.get("material_recognition") or {}
        if isinstance(recognition, Mapping):
            reason = _text(recognition.get("reason"))
            status = _text(recognition.get("status")) or "onbekend"
            value = _text(recognition.get("material") or recognition.get("candidate") or raw_material(part)) or "-"
            result.append(
                MaterialEvidence(
                    "Importherkenning",
                    value,
                    status,
                    bounded_confidence(recognition.get("confidence", 0.0)),
                    reason or f"{source_format}:{source_entity}",
                )
            )

    provenance_values = getattr(part, "field_provenance", {}) or {}
    if isinstance(provenance_values, Mapping):
        for field_path, provenance in sorted(provenance_values.items(), key=lambda item: str(item[0])):
            if "material" not in _text(field_path).lower():
                continue
            data = _plain_mapping(provenance)
            notes = data.get("notes") or ()
            if isinstance(notes, str):
                notes = (notes,)
            trail = " | ".join(
                value for value in (
                    _text(data.get("source_file_id")),
                    _text(data.get("source_entity_id")),
                    _text(data.get("source_path")),
                    "; ".join(_text(note) for note in notes if _text(note)),
                ) if value
            )
            result.append(
                MaterialEvidence(
                    _text(field_path),
                    raw_material(part) or "-",
                    _text(data.get("method") or data.get("status") or "provenance"),
                    bounded_confidence(data.get("confidence", 0.0)),
                    trail or "-",
                )
            )

    workbench = getattr(part, "workbench", {}) or {}
    revision = workbench.get("current_revision") if isinstance(workbench, Mapping) else {}
    recognition = revision.get("recognition") if isinstance(revision, Mapping) else {}
    review = recognition.get("material_review") if isinstance(recognition, Mapping) else {}
    if isinstance(review, Mapping) and review:
        result.append(
            MaterialEvidence(
                "Handmatige review",
                _text(review.get("candidate")) or "-",
                _text(review.get("status")) or "review",
                bounded_confidence(review.get("confidence", 0.0)),
                " | ".join(
                    value for value in (
                        _text(review.get("reviewer")),
                        _text(review.get("reason")),
                    ) if value
                ) or "-",
            )
        )
    return tuple(result)


def material_review_reasons(part: Any, database: Any) -> tuple[str, ...]:
    reasons: list[str] = []
    material = _text(getattr(part, "material", ""))
    grade = _text(getattr(part, "material_grade", ""))
    normalized = _text(getattr(part, "normalized_material", ""))
    raw = grade or material
    code, status, _confidence, _reason = _resolution(database, raw)
    if not raw:
        reasons.append("materiaal ontbreekt")
    elif status == "unresolved":
        reasons.append("geen exacte catalogusmatch")
    if material and grade:
        material_code = _resolution(database, material)[0] or _key(material)
        grade_code = _resolution(database, grade)[0] or _key(grade)
        if material_code != grade_code:
            reasons.append("materiaal en kwaliteit conflicteren")
    if normalized and code and _key(normalized) != _key(code):
        reasons.append("genormaliseerd materiaal wijkt af")
    if _text(getattr(part, "classification_status", "")) != "confirmed":
        reasons.append("classificatie niet handmatig bevestigd")
    if bounded_confidence(getattr(part, "material_confidence", 0.0)) < 1.0:
        reasons.append("materiaalconfidence lager dan 100%")
    return tuple(dict.fromkeys(reasons))


def review_queue_parts(project: Any, database: Any) -> tuple[Any, ...]:
    parts = getattr(project, "parts", {}) or {}
    values = parts.values() if isinstance(parts, Mapping) else parts
    result = [part for part in values if material_review_reasons(part, database)]
    return tuple(sorted(result, key=lambda part: (_text(getattr(part, "part_position", "")), _text(getattr(part, "internal_id", "")))))


def bulk_scope_part_ids(
    project: Any,
    scope: str,
    *,
    primary_part_id: str,
    selected_part_ids: Iterable[str] = (),
    queue_part_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    parts = getattr(project, "parts", {}) or {}
    if not isinstance(parts, Mapping):
        return ()
    primary = parts.get(str(primary_part_id))
    if scope == "selection":
        values = tuple(selected_part_ids) or ((primary_part_id,) if primary_part_id else ())
        return tuple(dict.fromkeys(str(value) for value in values if str(value) in parts))
    if scope == "queue_selection":
        return tuple(dict.fromkeys(str(value) for value in queue_part_ids if str(value) in parts))
    if primary is None:
        return ()
    if scope == "raw_material":
        group_key = _key(raw_material(primary))
        if not group_key:
            return ()
        predicate = lambda part: _key(raw_material(part)) == group_key
    elif scope == "source_class":
        group_key = source_class(primary)
        if not group_key:
            return ()
        predicate = lambda part: source_class(part) == group_key
    elif scope == "geometry":
        group_key = _text(getattr(primary, "geometry_hash", ""))
        if not group_key:
            return ()
        predicate = lambda part: _text(getattr(part, "geometry_hash", "")) == group_key
    else:
        return ()
    return tuple(sorted(_text(getattr(part, "internal_id", "")) for part in parts.values() if predicate(part)))


@dataclass(frozen=True, slots=True)
class BulkPreviewRow:
    part_id: str
    part_position: str
    raw_material: str
    source_class: str
    classification_status: str
    eligible: bool
    note: str


def build_bulk_preview(project: Any, part_ids: Iterable[str], database: Any) -> tuple[BulkPreviewRow, ...]:
    parts = getattr(project, "parts", {}) or {}
    if not isinstance(parts, Mapping):
        return ()
    rows: list[BulkPreviewRow] = []
    for part_id in dict.fromkeys(str(value) for value in part_ids):
        part = parts.get(part_id)
        if part is None:
            continue
        status = _text(getattr(part, "classification_status", ""))
        reasons = material_review_reasons(part, database)
        if status == "confirmed":
            eligible = False
            note = "Reeds bevestigd; alleen individueel wijzigen"
        elif not reasons:
            eligible = False
            note = "Geen materiaalreview nodig"
        else:
            eligible = True
            note = "; ".join(reasons)
        rows.append(
            BulkPreviewRow(
                part_id=part_id,
                part_position=_text(getattr(part, "part_position", "")) or part_id,
                raw_material=raw_material(part),
                source_class=source_class(part),
                classification_status=status or "unclassified",
                eligible=eligible,
                note=note,
            )
        )
    return tuple(rows)


_CLASSIFICATION_ATTRIBUTES = (
    "category",
    "classification_status",
    "classification_method",
    "classification_rule_id",
    "classification_reason",
    "classification_confidence",
    "normalized_profile",
    "normalized_material",
    "profile_confidence",
    "material_confidence",
    "production_identity_hash",
    "production_identity_version",
    "bom_group_key",
    "status",
    "export_status",
    "nc1_eligible",
)


def classification_snapshot(part: Any) -> dict[str, Any]:
    provenance = getattr(part, "field_provenance", {}) or {}
    category_provenance = provenance.get("category") if isinstance(provenance, Mapping) else None
    issues = []
    for issue in getattr(part, "validation_issues", ()) or ():
        if _text(getattr(issue, "code", "")).startswith("CWS-CLASSIFICATION-"):
            issues.append(asdict(issue) if is_dataclass(issue) else dict(issue))
    return {
        "attributes": {name: getattr(part, name, None) for name in _CLASSIFICATION_ATTRIBUTES},
        "field_provenance": {
            name: asdict(value) if is_dataclass(value) else deepcopy(value)
            for name, value in provenance.items()
            if name == "category" or "material" in name or "profile" in name
        } if isinstance(provenance, Mapping) else {},
        "category_provenance": (
            asdict(category_provenance)
            if is_dataclass(category_provenance)
            else dict(category_provenance)
            if isinstance(category_provenance, Mapping)
            else None
        ),
        "classification_issues": issues,
    }


def restore_classification_snapshot(part: Any, snapshot: Mapping[str, Any]) -> None:
    """Restore metadata that Part Workbench cannot undo through its own API."""

    from cws_convertor.project.model import FieldProvenance, ValidationIssue

    for name, value in dict(snapshot.get("attributes") or {}).items():
        if name in _CLASSIFICATION_ATTRIBUTES:
            setattr(part, name, value)
    provenance = getattr(part, "field_provenance", {})
    if not isinstance(provenance, dict):
        provenance = dict(provenance or {})
        part.field_provenance = provenance
    previous_fields = snapshot.get("field_provenance")
    if isinstance(previous_fields, Mapping):
        for name in tuple(provenance):
            if name == "category" or "material" in name or "profile" in name:
                provenance.pop(name, None)
        for name, previous in previous_fields.items():
            if isinstance(previous, Mapping):
                provenance[name] = FieldProvenance.from_dict(previous)
    else:
        previous = snapshot.get("category_provenance")
        if isinstance(previous, Mapping):
            provenance["category"] = FieldProvenance.from_dict(previous)
        else:
            provenance.pop("category", None)
    remaining = [
        issue for issue in (getattr(part, "validation_issues", ()) or ())
        if not _text(getattr(issue, "code", "")).startswith("CWS-CLASSIFICATION-")
    ]
    remaining.extend(ValidationIssue.from_dict(value) for value in snapshot.get("classification_issues", ()) or ())
    part.validation_issues = remaining


def part_fingerprint(part: Any) -> tuple[Any, ...]:
    # Freeze all evidence and release state, not only editable material text.
    # A changed category/profile/confidence must invalidate an earlier preview.
    if is_dataclass(part):
        from cws_convertor.project.model import stable_sha256
        return (_text(getattr(part, "internal_id", "")), stable_sha256(asdict(part)))
    workbench = getattr(part, "workbench", {}) or {}
    cursor = int(workbench.get("command_cursor") or 0) if isinstance(workbench, Mapping) else 0
    commands = list(workbench.get("commands") or ()) if isinstance(workbench, Mapping) else []
    command_id = _text(commands[cursor - 1].get("command_id")) if cursor and cursor <= len(commands) else ""
    return (
        _text(getattr(part, "internal_id", "")),
        _text(getattr(part, "material", "")),
        _text(getattr(part, "material_grade", "")),
        _text(getattr(part, "normalized_material", "")),
        _text(getattr(part, "classification_status", "")),
        _text(getattr(part, "manufacturing_hash", "")),
        cursor,
        command_id,
    )


def _copy_project_state(project: Any, snapshot: Any) -> None:
    """Copy validated state while retaining references held by other panels."""
    for descriptor in fields(project):
        current = getattr(project, descriptor.name)
        previous = getattr(snapshot, descriptor.name)
        if isinstance(current, dict) and isinstance(previous, dict):
            for key in tuple(current):
                if key not in previous:
                    current.pop(key)
            for key, value in previous.items():
                target = current.get(key)
                if is_dataclass(target) and type(target) is type(value):
                    for attribute in fields(value):
                        setattr(target, attribute.name, deepcopy(getattr(value, attribute.name)))
                else:
                    current[key] = deepcopy(value)
        else:
            setattr(project, descriptor.name, deepcopy(previous))


@dataclass(slots=True)
class StepRecognitionReviewJob:
    live_session: Any
    original_project: Any
    detached_session: Any
    fingerprint: str
    source_id: str
    part_id: str


def create_step_recognition_job(session: Any, part_id: str) -> StepRecognitionReviewJob:
    """Prepare a worker snapshot for one selected, semantically imported part."""
    from cws_convertor.project import ProjectModel, ProjectSession
    from cws_convertor.project.model import stable_sha256

    if bool(getattr(session, "read_only", False)):
        raise ValueError("Project is alleen-lezen")
    part = session.project.parts.get(part_id)
    if part is None or part.source_identity.source_format.upper() not in {"STEP", "STP"}:
        raise ValueError("Selecteer één geïmporteerd STEP-onderdeel")
    source_id = part.source_identity.source_file_id
    source = session.project.sources.get(source_id)
    if source is None or not source.semantic_import_complete:
        raise ValueError("STEP-bron is nog niet semantisch geïmporteerd")
    paths = dict(session.source_paths)
    paths[source_id] = session.resolve_source_path(source_id)
    payload = session.project.to_dict()
    detached = ProjectSession(
        store=session.store, project=ProjectModel.from_dict(payload), source_paths=paths
    )
    return StepRecognitionReviewJob(session, session.project, detached, stable_sha256(payload), source_id, part_id)


def apply_step_recognition_job(job: StepRecognitionReviewJob) -> None:
    """Publish a completed worker on the GUI thread, rejecting stale results."""
    from cws_convertor.project.model import stable_sha256

    session = job.live_session
    if (
        session.project is not job.original_project
        or bool(getattr(session, "read_only", False))
        or stable_sha256(session.project.to_dict()) != job.fingerprint
    ):
        raise ValueError("Project gewijzigd tijdens STEP-herkenning; resultaat niet toegepast")
    job.detached_session.project.validate()
    _copy_project_state(session.project, job.detached_session.project)
    session.dirty = True


@contextmanager
def material_review_transaction(session: Any):
    """Restore the entire in-memory model if a multi-step review fails.

    Classification may update identity conflicts on other parts as well.  A
    single snapshot therefore covers the project and preserves live entity
    identities during rollback. Nested calls share the outer transaction.
    """
    if getattr(session, "_material_review_transaction_active", False):
        yield
        return
    project = session.project
    snapshot = deepcopy(project)
    dirty = getattr(session, "dirty", None)
    session._material_review_transaction_active = True
    try:
        yield
    except Exception:
        session.project = project
        _copy_project_state(project, snapshot)
        if dirty is not None:
            session.dirty = dirty
        raise
    finally:
        session._material_review_transaction_active = False


def _atomic_review(operation):
    from functools import wraps

    @wraps(operation)
    def wrapped(session: Any, *args: Any, **kwargs: Any):
        with material_review_transaction(session):
            return operation(session, *args, **kwargs)
    return wrapped


def safe_profile_confidence(part: Any, revision: Mapping[str, Any]) -> float:
    """Keep profile confidence independent from generic entity confidence."""

    recognition = revision.get("recognition") if isinstance(revision, Mapping) else {}
    recognition = recognition if isinstance(recognition, Mapping) else {}
    if bool(recognition.get("confirmed")):
        return bounded_confidence(recognition.get("confidence", 0.0))
    return bounded_confidence(getattr(part, "profile_confidence", 0.0))


def _ensure_workbench_source_properties(session: Any, part_id: str, *, user: str) -> Any:
    """Make a new Workbench's undo baseline equal to the live source fields."""

    part = session.project.parts[part_id]
    source_properties = {
        "profile": _text(part.profile),
        "material": _text(part.material),
        "material_grade": _text(part.material_grade),
        "part_position": _text(part.part_position),
        "assembly_position": "",
    }
    if not isinstance(getattr(part, "workbench", None), dict) or not part.workbench:
        session.start_part_workbench(part_id, user=user)
        part = session.project.parts[part_id]
    revision = deepcopy(part.workbench.get("current_revision") or {})
    current = deepcopy(revision.get("production_properties") or {})
    aligned = {**current, **source_properties}
    if aligned != current:
        session.update_part_workbench(
            part_id,
            {"production_properties": aligned},
            user=user,
            reason="Workbench-undo-basis uit oorspronkelijke materiaalvelden vastgelegd",
        )
        part = session.project.parts[part_id]
    return part


@_atomic_review
def apply_material_confirmation(
    session: Any,
    part_id: str,
    *,
    candidate: str,
    category: str,
    reason: str,
    user: str = "qt-gui",
    database: Any = None,
) -> dict[str, Any]:
    """Apply one auditable catalog decision through the real session APIs."""

    from cws_convertor.project.classification import normalize_profile

    candidate = _text(candidate)
    category = _text(category)
    reason = _text(reason)
    if not candidate:
        raise ValueError("Materiaalbevestiging vereist een cataloguscode")
    if not reason:
        raise ValueError("Materiaalbevestiging vereist een reden")
    if category in {"", "unknown"}:
        raise ValueError("Materiaalbevestiging vereist een expliciete onderdeelcategorie")
    if database is None:
        from material_database import MaterialDatabase
        database = MaterialDatabase()
    resolved_code, status, _confidence, _reason = _resolution(database, candidate)
    if not resolved_code or status not in {"exact", "alias"}:
        raise ValueError("Materiaalbevestiging vereist een bestaande cataloguscode of expliciete alias")
    candidate = resolved_code
    part = session.project.parts[part_id]
    before_classification = classification_snapshot(part)
    part = _ensure_workbench_source_properties(session, part_id, user=user)
    revision = deepcopy(part.workbench.get("current_revision") or {})
    recognition = deepcopy(revision.get("recognition") or {})
    profile_confidence = safe_profile_confidence(part, revision)
    normalized_profile = normalize_profile(part.normalized_profile or part.profile)
    recognition["confidence"] = profile_confidence
    recognition["material_review"] = {
        "status": "confirmed",
        "candidate": candidate,
        "confidence": 1.0,
        "method": "manual_catalog_review",
        "reviewer": user,
        "reason": reason,
        "category": category,
        "normalized_profile": normalized_profile,
        "profile_confidence": profile_confidence,
        "previous_classification": before_classification,
    }
    properties = deepcopy(revision.get("production_properties") or {})
    properties.update(
        {
            "profile": normalized_profile or _text(part.profile),
            "material": candidate,
            "material_grade": candidate,
            "part_position": _text(part.part_position),
        }
    )
    questions = [
        deepcopy(question)
        for question in (revision.get("unresolved_questions") or ())
        if not isinstance(question, Mapping) or question.get("review_kind") != "material_candidate_rejected"
    ]
    state = session.update_part_workbench(
        part_id,
        {
            "recognition": recognition,
            "production_properties": properties,
            "unresolved_questions": questions,
        },
        user=user,
        reason=f"Materiaal {candidate} handmatig bevestigd: {reason}",
    )
    session.confirm_part_classification(
        part_id,
        category,
        user=user,
        reason=reason,
        normalized_material=candidate,
    )
    confirmed = session.project.parts[part_id]
    confirmed.profile_confidence = profile_confidence
    confirmed.material = candidate
    confirmed.material_grade = candidate
    confirmed.normalized_material = candidate
    commands = list(state.get("commands") or ())
    cursor = int(state.get("command_cursor") or 0)
    command_id = _text(commands[cursor - 1].get("command_id")) if cursor else ""
    return {
        "part_id": part_id,
        "command_id": command_id,
        "candidate": candidate,
        "before_classification": before_classification,
        "after_fingerprint": part_fingerprint(confirmed),
    }


@_atomic_review
def reject_material_confirmation(
    session: Any,
    part_id: str,
    *,
    candidate: str,
    reason: str,
    user: str = "qt-gui",
) -> dict[str, Any]:
    """Persist a rejected candidate as an unresolved, blocking review item."""

    candidate = _text(candidate)
    reason = _text(reason)
    if not candidate or not reason:
        raise ValueError("Materiaal weigeren vereist een kandidaat en een reden")
    part = _ensure_workbench_source_properties(session, part_id, user=user)
    revision = deepcopy(part.workbench.get("current_revision") or {})
    recognition = deepcopy(revision.get("recognition") or {})
    recognition["confidence"] = safe_profile_confidence(part, revision)
    recognition["material_review"] = {
        "status": "rejected",
        "candidate": candidate,
        "confidence": 0.0,
        "method": "manual_catalog_review",
        "reviewer": user,
        "reason": reason,
    }
    questions = [
        deepcopy(question)
        for question in (revision.get("unresolved_questions") or ())
        if not isinstance(question, Mapping) or question.get("review_kind") != "material_candidate_rejected"
    ]
    questions.append(
        {
            "question_id": str(uuid4()),
            "question": f"Materiaalvoorstel {candidate} is afgewezen: {reason}",
            "field_path": "production_properties.material",
            "review_kind": "material_candidate_rejected",
            "candidate": candidate,
            "reason": reason,
        }
    )
    properties = deepcopy(revision.get("production_properties") or {})
    properties.update(
        {
            "profile": _text(part.profile),
            "material": _text(part.material),
            "material_grade": _text(part.material_grade),
            "part_position": _text(part.part_position),
        }
    )
    return session.update_part_workbench(
        part_id,
        {
            "recognition": recognition,
            "production_properties": properties,
            "unresolved_questions": questions,
        },
        user=user,
        reason=f"Materiaalvoorstel {candidate} afgewezen: {reason}",
    )


def material_confirmation_at_cursor(part: Any) -> bool:
    workbench = getattr(part, "workbench", {}) or {}
    commands = list(workbench.get("commands") or ()) if isinstance(workbench, Mapping) else []
    cursor = int(workbench.get("command_cursor") or 0) if isinstance(workbench, Mapping) else 0
    if cursor <= 0 or cursor > len(commands):
        return False
    command = commands[cursor - 1]
    revision = dict(workbench.get("current_revision") or {})
    review = dict(dict(revision.get("recognition") or {}).get("material_review") or {})
    return bool(
        review.get("status") == "confirmed"
        and _text(command.get("reason")).startswith("Materiaal ")
        and {"recognition", "production_properties"}.issubset(command.get("changed_fields") or ())
    )


@_atomic_review
def undo_material_confirmation(
    session: Any,
    part_id: str,
    *,
    user: str = "qt-gui",
) -> dict[str, Any]:
    part = session.project.parts[part_id]
    if not material_confirmation_at_cursor(part):
        raise ValueError("Laatste workbench-commando is geen omkeerbare materiaalbevestiging")
    revision = dict((part.workbench or {}).get("current_revision") or {})
    review = dict(dict(revision.get("recognition") or {}).get("material_review") or {})
    snapshot = review.get("previous_classification")
    if not isinstance(snapshot, Mapping):
        raise ValueError("Materiaalbevestiging bevat geen classificatie-undo-informatie")
    state = session.undo_part_workbench(part_id, user=user)
    restored = session.project.parts[part_id]
    restore_classification_snapshot(restored, snapshot)
    session.project.audit(
        "material_review.confirmation_undone",
        user=user,
        entity_id=part_id,
        after_hash=restored.manufacturing_hash,
        details={"candidate": review.get("candidate"), "reason": review.get("reason")},
    )
    session.project.validate()
    return state


@_atomic_review
def redo_material_confirmation(
    session: Any,
    part_id: str,
    *,
    user: str = "qt-gui",
) -> dict[str, Any]:
    state = session.redo_part_workbench(part_id, user=user)
    part = session.project.parts[part_id]
    if not material_confirmation_at_cursor(part):
        return state
    revision = dict(state.get("current_revision") or {})
    review = dict(dict(revision.get("recognition") or {}).get("material_review") or {})
    candidate = _text(review.get("candidate"))
    category = _text(review.get("category")) or "unknown"
    reason = _text(review.get("reason")) or "Materiaalreview opnieuw toegepast"
    session.confirm_part_classification(
        part_id,
        category,
        user=user,
        reason=f"Opnieuw toegepast: {reason}",
        normalized_material=candidate,
    )
    confirmed = session.project.parts[part_id]
    confirmed.profile_confidence = bounded_confidence(review.get("profile_confidence", 0.0))
    confirmed.material = candidate
    confirmed.material_grade = candidate
    confirmed.normalized_material = candidate
    return state


__all__ = [
    "BulkPreviewRow",
    "MaterialCandidate",
    "MaterialEvidence",
    "apply_material_confirmation",
    "apply_step_recognition_job",
    "bounded_confidence",
    "build_bulk_preview",
    "bulk_scope_part_ids",
    "catalog_candidates",
    "classification_snapshot",
    "create_step_recognition_job",
    "material_confirmation_at_cursor",
    "material_evidence",
    "material_review_reasons",
    "material_review_transaction",
    "part_fingerprint",
    "raw_material",
    "redo_material_confirmation",
    "reject_material_confirmation",
    "restore_classification_snapshot",
    "review_queue_parts",
    "safe_profile_confidence",
    "selection_ids",
    "source_class",
    "undo_material_confirmation",
]
