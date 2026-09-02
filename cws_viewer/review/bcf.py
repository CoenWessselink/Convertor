"""Schema-validated buildingSMART BCF 2.1 import/export primitives."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from math import sqrt
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from uuid import UUID, uuid5
import zipfile

from lxml import etree

from cws_viewer.contracts.enums import ProjectionType

BCF_VERSION = "2.1"
BCF_MIME_TYPE = "application/vnd.buildingsmart.bcf+zip"
_NAMESPACE = UUID("3987e7cd-54e0-4be8-a55b-8c03953342d2")
_SCHEMA_ROOT = Path(__file__).with_name("schemas") / "bcf_2_1"
_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _utc(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if raw.endswith("Z"):
        return raw
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _xml_bytes(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, _ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def _put(parent: etree._Element, name: str, value: Any) -> etree._Element:
    child = etree.SubElement(parent, name)
    child.text = str(value)
    return child


def _point(parent: etree._Element, name: str, vector: Any, *, scale: float = 1.0) -> None:
    node = etree.SubElement(parent, name)
    _put(node, "X", float(vector.x) * scale)
    _put(node, "Y", float(vector.y) * scale)
    _put(node, "Z", float(vector.z) * scale)


def _unit(vector: Any) -> tuple[float, float, float]:
    length = sqrt(float(vector.x) ** 2 + float(vector.y) ** 2 + float(vector.z) ** 2)
    if length <= 1e-12:
        return (0.0, 0.0, -1.0)
    return (float(vector.x) / length, float(vector.y) / length, float(vector.z) / length)


def _direction(parent: etree._Element, name: str, vector: Any) -> None:
    x, y, z = _unit(vector)
    node = etree.SubElement(parent, name)
    _put(node, "X", x)
    _put(node, "Y", y)
    _put(node, "Z", z)


@dataclass(frozen=True, slots=True)
class BcfTopicMapping:
    guid: str
    title: str
    description: str
    status: str
    priority: str
    author: str
    assigned_to: str
    related_entity_ids: tuple[str, ...]
    related_ifc_guids: tuple[str, ...] = ()
    comment_count: int = 0
    viewpoint_count: int = 0
    snapshot_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def map_review_topic(
    value: Any,
    *,
    project_id: str,
    ifc_guid_by_entity: Mapping[str, str] | None = None,
) -> BcfTopicMapping:
    """Map a CWS clash/review issue to stable BCF topic semantics."""
    if hasattr(value, "part_a_id"):
        entities = tuple(
            item for item in (
                str(getattr(value, "part_a_id", "")),
                str(getattr(value, "part_b_id", "")),
            ) if item
        )
        stable = str(getattr(value, "clash_fingerprint", "") or getattr(value, "clash_id", "") or repr(value))
        title = str(getattr(value, "title", "") or getattr(value, "clash_id", "Clash"))
        description = str(getattr(value, "description", "") or getattr(value, "classification_reason", ""))
        author = ""
        comments = list(getattr(value, "comments", ()) or ())
        viewpoints = list(getattr(value, "viewpoints", ()) or ())
        screenshots = list(getattr(value, "screenshots", ()) or ())
    else:
        entities = tuple(str(item) for item in getattr(value, "linked_entity_ids", ()) or ())
        stable = str(getattr(value, "issue_id", "") or repr(value))
        title = str(getattr(value, "title", "") or "Review issue")
        description = str(getattr(value, "description", "") or "")
        author = str(getattr(value, "created_by", "") or "")
        comments = list(getattr(value, "comments", ()) or ())
        viewpoints = [getattr(value, "viewpoint_id", None)] if getattr(value, "viewpoint_id", None) else []
        screenshots = list(getattr(value, "screenshots", ()) or ())
    lookup = ifc_guid_by_entity or {}
    ifc_guids = tuple(dict.fromkeys(str(lookup[item]) for item in entities if lookup.get(item)))
    return BcfTopicMapping(
        guid=str(uuid5(_NAMESPACE, f"{project_id}|{stable}")),
        title=title,
        description=description,
        status=str(getattr(value, "status", "open")),
        priority=str(getattr(value, "priority", "normal")),
        author=author,
        assigned_to=str(getattr(value, "assigned_to", getattr(value, "assignee", "")) or ""),
        related_entity_ids=entities,
        related_ifc_guids=ifc_guids,
        comment_count=len(comments),
        viewpoint_count=len(viewpoints),
        snapshot_count=len(screenshots),
    )


@dataclass(frozen=True, slots=True)
class BcfValidationReport:
    path: str
    version: str
    topic_count: int
    viewpoint_count: int
    validated_files: tuple[str, ...]


class BcfValidationError(ValueError):
    """Raised when a BCF archive is unsafe or does not pass the BCF 2.1 XSDs."""


class Bcf21Verifier:
    def __init__(self, *, schema_root: str | Path = _SCHEMA_ROOT) -> None:
        root = Path(schema_root)
        self._version = etree.XMLSchema(etree.parse(str(root / "version.xsd")))
        self._markup = etree.XMLSchema(etree.parse(str(root / "markup.xsd")))
        self._visinfo = etree.XMLSchema(etree.parse(str(root / "visinfo.xsd")))

    @staticmethod
    def _safe_names(archive: zipfile.ZipFile) -> tuple[str, ...]:
        infos = archive.infolist()
        if len(infos) > 10_000 or sum(info.file_size for info in infos) > 2 * 1024**3:
            raise BcfValidationError("BCF archive exceeds safe extraction limits")
        names = tuple(info.filename for info in infos)
        for name in names:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise BcfValidationError(f"Unsafe BCF archive path: {name}")
        if len(names) != len(set(names)):
            raise BcfValidationError("BCF archive contains duplicate paths")
        return names

    @staticmethod
    def _validate(schema: etree.XMLSchema, payload: bytes, name: str) -> None:
        try:
            parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
            document = etree.parse(BytesIO(payload), parser)
            schema.assertValid(document)
        except (etree.XMLSyntaxError, etree.DocumentInvalid) as exc:
            raise BcfValidationError(f"{name} is not valid BCF 2.1 XML: {exc}") from exc

    def verify(self, path: str | Path) -> BcfValidationReport:
        source = Path(path)
        try:
            with zipfile.ZipFile(source, "r") as archive:
                names = self._safe_names(archive)
                if "bcf.version" not in names:
                    raise BcfValidationError("BCF archive has no bcf.version")
                self._validate(self._version, archive.read("bcf.version"), "bcf.version")
                version_root = etree.fromstring(archive.read("bcf.version"))
                if version_root.get("VersionId") != BCF_VERSION:
                    raise BcfValidationError(f"Expected BCF {BCF_VERSION}")
                markups = tuple(name for name in names if name.endswith("/markup.bcf"))
                viewpoints = tuple(name for name in names if name.endswith(".bcfv"))
                if not markups:
                    raise BcfValidationError("BCF archive contains no topics")
                for name in markups:
                    self._validate(self._markup, archive.read(name), name)
                for name in viewpoints:
                    self._validate(self._visinfo, archive.read(name), name)
        except zipfile.BadZipFile as exc:
            raise BcfValidationError("Not a readable BCF ZIP archive") from exc
        validated = ("bcf.version", *markups, *viewpoints)
        return BcfValidationReport(str(source.resolve()), BCF_VERSION, len(markups), len(viewpoints), validated)


class Bcf21Exporter:
    """Write deterministic BCF 2.1 archives and promote only after XSD validation."""

    certified_version = BCF_VERSION

    def __init__(self, *, verifier: Bcf21Verifier | None = None) -> None:
        self.verifier = verifier or Bcf21Verifier()

    @staticmethod
    def _version_xml() -> bytes:
        return _xml_bytes(etree.Element("Version", VersionId=BCF_VERSION))

    @staticmethod
    def _viewpoint_xml(viewpoint: Any, *, guid: str, ifc_guids: Iterable[str]) -> bytes:
        root = etree.Element("VisualizationInfo", Guid=guid)
        guids = tuple(dict.fromkeys(item for item in ifc_guids if len(item) == 22))
        if guids:
            components = etree.SubElement(root, "Components")
            selection = etree.SubElement(components, "Selection")
            for ifc_guid in guids:
                etree.SubElement(selection, "Component", IfcGuid=ifc_guid)
            etree.SubElement(components, "Visibility", DefaultVisibility="true")
        camera = viewpoint.camera
        direction = camera.target - camera.position
        if camera.projection is ProjectionType.ORTHOGRAPHIC:
            camera_node = etree.SubElement(root, "OrthogonalCamera")
        else:
            camera_node = etree.SubElement(root, "PerspectiveCamera")
        _point(camera_node, "CameraViewPoint", camera.position, scale=0.001)
        _direction(camera_node, "CameraDirection", direction)
        _direction(camera_node, "CameraUpVector", camera.up)
        if camera.projection is ProjectionType.ORTHOGRAPHIC:
            _put(camera_node, "ViewToWorldScale", float(camera.ortho_scale) * 0.001)
        else:
            _put(camera_node, "FieldOfView", min(60.0, max(45.0, float(camera.field_of_view_deg))))
        return _xml_bytes(root)

    @staticmethod
    def _markup_xml(issue: Any, mapping: BcfTopicMapping, *, viewpoint_guid: str | None) -> bytes:
        root = etree.Element("Markup")
        topic = etree.SubElement(
            root,
            "Topic",
            Guid=mapping.guid,
            TopicType=str(getattr(issue, "severity", "issue")),
            TopicStatus=mapping.status,
        )
        _put(topic, "Title", mapping.title)
        _put(topic, "Priority", mapping.priority)
        for label in tuple(getattr(issue, "tags", ()) or ()):
            _put(topic, "Labels", label)
        _put(topic, "CreationDate", _utc(getattr(issue, "created_utc", None)))
        _put(topic, "CreationAuthor", mapping.author or "unknown@cws.local")
        updated = getattr(issue, "updated_utc", None)
        if updated:
            _put(topic, "ModifiedDate", _utc(updated))
            _put(topic, "ModifiedAuthor", mapping.author or "unknown@cws.local")
        due = getattr(issue, "due_date_utc", None)
        if due:
            _put(topic, "DueDate", _utc(due))
        if mapping.assigned_to:
            _put(topic, "AssignedTo", mapping.assigned_to)
        if mapping.description:
            _put(topic, "Description", mapping.description)
        for index, comment in enumerate(tuple(getattr(issue, "comments", ()) or ())):
            node = etree.SubElement(root, "Comment", Guid=str(uuid5(_NAMESPACE, f"{mapping.guid}|comment|{index}")))
            _put(node, "Date", _utc(getattr(comment, "created_utc", None)))
            _put(node, "Author", getattr(comment, "author", "") or "unknown@cws.local")
            _put(node, "Comment", getattr(comment, "text", ""))
            if viewpoint_guid:
                etree.SubElement(node, "Viewpoint", Guid=viewpoint_guid)
        if viewpoint_guid:
            node = etree.SubElement(root, "Viewpoints", Guid=viewpoint_guid)
            _put(node, "Viewpoint", "viewpoint.bcfv")
        return _xml_bytes(root)

    def export(
        self,
        output_path: str | Path,
        *,
        project_id: str,
        issues: Iterable[Any],
        viewpoints: Iterable[Any] = (),
        ifc_guid_by_entity: Mapping[str, str] | None = None,
    ) -> Path:
        output = Path(output_path)
        if output.suffix.casefold() not in {".bcf", ".bcfzip"}:
            output = output.with_suffix(".bcfzip")
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp")
        by_id = {str(item.viewpoint_id): item for item in viewpoints}
        issue_items = tuple(issues)
        if not issue_items:
            raise ValueError("BCF export requires at least one topic")
        with zipfile.ZipFile(temporary, "w") as archive:
            archive.writestr(_zip_info("bcf.version"), self._version_xml())
            for issue in issue_items:
                mapping = map_review_topic(issue, project_id=project_id, ifc_guid_by_entity=ifc_guid_by_entity)
                folder = f"{mapping.guid}/"
                viewpoint = by_id.get(str(getattr(issue, "viewpoint_id", "") or ""))
                viewpoint_guid = None
                if viewpoint is not None:
                    viewpoint_guid = str(uuid5(_NAMESPACE, f"{mapping.guid}|{viewpoint.viewpoint_id}"))
                archive.writestr(
                    _zip_info(folder + "markup.bcf"),
                    self._markup_xml(issue, mapping, viewpoint_guid=viewpoint_guid),
                )
                if viewpoint is not None and viewpoint_guid is not None:
                    archive.writestr(
                        _zip_info(folder + "viewpoint.bcfv"),
                        self._viewpoint_xml(viewpoint, guid=viewpoint_guid, ifc_guids=mapping.related_ifc_guids),
                    )
        try:
            self.verifier.verify(temporary)
            temporary.replace(output)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return output


# Compatibility name used by the extension point introduced before certification.
BcfExporterExtension = Bcf21Exporter


__all__ = [
    "BCF_VERSION",
    "BCF_MIME_TYPE",
    "BcfTopicMapping",
    "map_review_topic",
    "BcfValidationReport",
    "BcfValidationError",
    "Bcf21Verifier",
    "Bcf21Exporter",
    "BcfExporterExtension",
]
