"""Selected-object review batches, using the existing production drawing engine.

Rendering runs against copied project/mesh inputs. Only a current, completely
verified batch is published on the GUI thread. This never releases a revision.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from types import SimpleNamespace
from typing import Any, Iterable
from uuid import uuid4

import numpy as np

from cws_convertor.project.model import stable_sha256
from cws_convertor.project.jobs import JobCancelled
from .interactive import DIMENSION_EDITOR_SCHEMA, DimensionDocumentStore

SCHEMA = "cws-drawing-review-batch-1"
MAX_BATCH_ENTITIES = 250


def _digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _revision(project: Any) -> str:
    data = deepcopy(project.to_dict())
    for key in ("app_version", "modified_at", "audit_log", "revisions"):
        data.pop(key, None)
    # Normal live previews refresh these derived fields. They are not input.
    # Workbench releases and saved editor/sheet settings remain in the hash.
    for family in ("parts", "assemblies", "purchased_items", "fasteners", "welds"):
        for entity in data.get(family, {}).values():
            entity.get("properties", {}).pop("drawing_state", None)
            entity.pop("drawing_status", None)
    hub = data.get("settings", {}).get("bom_production_hub", {})
    for key in ("history", "batch_results", "scoped_requests"):
        hub.pop(key, None)
    return stable_sha256(data)


def _geometry(workspace: Any, ids: tuple[str, ...]) -> tuple[Any, str]:
    from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
    project = workspace.project
    required = set(ids) & set(project.parts)
    optional: set[str] = set()
    generator = EngineeringDrawingGenerator(workspace)
    for key in ids:
        if key in project.assemblies:
            for member, kind in generator._assembly_members(project.assemblies[key]).items():
                (optional if kind == "weld" else required).add(member)
    mesh_by_node, nodes, transforms, entity_nodes = {}, {}, {}, {}
    digest = hashlib.sha256()
    for key in sorted(required | optional):
        try:
            node_id = workspace.interaction.node_for_entity(key)
            node = workspace.controller.index.node(node_id)
            mesh = workspace.load_result.repository.get(node.geometry_id)
            vertices = np.array(mesh.vertices, dtype="<f8", copy=True).reshape((-1, 3))
            triangles = np.array(mesh.triangles, dtype="<i8", copy=True).reshape((-1, 3))
            if not len(vertices) or not len(triangles) or not np.isfinite(vertices).all():
                raise ValueError("lege of niet-eindige mesh")
            if np.min(triangles) < 0 or np.max(triangles) >= len(vertices):
                raise ValueError("mesh bevat ongeldige indices")
            transform = np.asarray(
                workspace.controller.index.world_transform_by_node[node_id].to_rows(), dtype="<f8"
            ).copy()
            if transform.shape != (4, 4) or not np.isfinite(transform).all():
                raise ValueError("ongeldige plaatsing")
        except Exception as exc:
            if key in required:
                raise ValueError(f"Batchtekening mist componentgeometrie {key}: {exc}") from exc
            continue
        for array in (vertices, triangles, transform):
            array.setflags(write=False)
        # IDs are collision-free in this immutable adapter. No alternate geometry
        # reconstruction, selection bus or second viewer is introduced.
        entity_nodes[key] = key
        nodes[key] = SimpleNamespace(geometry_id=key)
        mesh_by_node[key] = SimpleNamespace(vertices=vertices, triangles=triangles)
        transforms[key] = SimpleNamespace(to_rows=lambda matrix=transform: matrix.tolist())
        for value in (key.encode(), vertices.tobytes(), triangles.tobytes(), transform.tobytes()):
            digest.update(len(value).to_bytes(8, "little"))
            digest.update(value)
    frozen = SimpleNamespace(
        interaction=SimpleNamespace(node_for_entity=entity_nodes.__getitem__),
        controller=SimpleNamespace(index=SimpleNamespace(node=nodes.__getitem__, world_transform_by_node=transforms)),
        load_result=SimpleNamespace(repository=mesh_by_node),
    )
    return frozen, digest.hexdigest()


@dataclass(frozen=True)
class DrawingBatchSnapshot:
    workspace: Any
    entity_ids: tuple[str, ...]
    project_revision: str
    geometry_sha256: str
    defaults: dict[str, Any]


@dataclass(frozen=True)
class StagedDrawingBatch:
    staging: Path
    destination: Path
    manifest_sha256: str


def exact_drawing_batch_ids(project: Any, row_ids: Iterable[str], selection_ids: Iterable[str]) -> tuple[str, ...]:
    """Do not expand a selected occurrence to its highlighted aggregate BOM row."""
    rows, selected = set(row_ids), set(selection_ids)
    known = set(project.parts) | set(project.assemblies)
    if not rows or not rows.issubset(known) or (selected and not selected.issubset(known)):
        raise ValueError("Tekenbatch bevat ontbrekende of niet-tekenbare objecten")
    result = rows.intersection(selected) if selected else rows
    if not result:
        raise ValueError("BOM-regels en expliciete tekeningselectie komen niet overeen")
    return tuple(sorted(result))


def prepare_drawing_batch(workspace: Any, entity_ids: Iterable[str], defaults: dict | None = None) -> DrawingBatchSnapshot:
    supplied = tuple(entity_ids)
    if any(not isinstance(key, str) or not key for key in supplied):
        raise ValueError("Batch vereist expliciete canonieke object-IDs")
    ids = tuple(sorted(set(supplied)))
    if not ids or len(ids) > MAX_BATCH_ENTITIES:
        raise ValueError(f"Selecteer 1 t/m {MAX_BATCH_ENTITIES} objecten voor een batch")
    known = set(workspace.project.parts) | set(workspace.project.assemblies)
    if not set(ids).issubset(known):
        raise ValueError("Batch bevat verwijderde of niet-tekenbare objecten")
    before = _revision(workspace.project)
    frozen, geometry_hash = _geometry(workspace, ids)
    frozen.project = deepcopy(workspace.project)
    if _revision(workspace.project) != before or _revision(frozen.project) != before:
        raise ValueError("Project gewijzigd tijdens het vastleggen van de tekenbatch")
    return DrawingBatchSnapshot(frozen, ids, before, geometry_hash, deepcopy(defaults or {}))


def _options(snapshot: DrawingBatchSnapshot, key: str) -> dict:
    project = snapshot.workspace.project
    entity = project.get_entity(key)
    editor = DimensionDocumentStore.load(
        project, entity_id=key, manufacturing_sha256=str(getattr(entity, "manufacturing_hash", "")),
        source_revision=str(getattr(entity, "revision", "") or "A"),
    )
    if editor.entity_id != key or editor.project_id != project.project_id:
        raise ValueError("Opgeslagen maatdocument hoort bij een ander project/object")
    sheet = deepcopy(snapshot.defaults)
    sheet.update(editor.extensions.get("sheet_settings") or {})
    views = sheet.get("views", ("front", "top", "side", "iso"))
    if (sheet.get("format", "A3") not in {"A4", "A3", "A2", "A1", "A0"}
            or sheet.get("orientation", "landscape") not in {"landscape", "portrait"}
            or sheet.get("unit", "mm") not in {"mm", "cm"}
            or not isinstance(views, (list, tuple)) or not views
            or any(view not in {"front", "top", "side", "end", "iso", "3d"} for view in views)):
        raise ValueError("Opgeslagen bladinstellingen zijn ongeldig; geen stille vervanging")
    return {
        "sheet_format": str(sheet.get("format", "A3")),
        "orientation": str(sheet.get("orientation", "landscape")),
        "scale_label": str(sheet.get("scale", "Auto")),
        "unit": str(sheet.get("unit", "mm")),
        "views": tuple(sheet.get("views", ("front", "top", "side", "iso"))),
        "dimensions": bool(sheet.get("dimensions", True)),
        "title_block": bool(sheet.get("title_block", True)),
        "dimension_mode": str(sheet.get("dimension_mode", "Hoofdmaten")),
        "include_sections": bool(sheet.get("sections", True)),
        "include_details": bool(sheet.get("details", True)),
        "manual_dimensions": tuple(editor.render_records()),
        "dimension_style": editor.style.to_dict(),
        "dimension_audit": tuple(editor.audit),
        "dimension_editor_schema": DIMENSION_EDITOR_SCHEMA,
        "dimension_editor_status": editor.status,
    }


def stage_drawing_batch(context: Any, snapshot: DrawingBatchSnapshot, directory: str | Path) -> StagedDrawingBatch:
    from pypdf import PdfReader, PdfWriter
    from cws_convertor.ui_qt.engineering_drawing import EngineeringDrawingGenerator
    from .linter import DrawingLinter

    parent = Path(directory).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".cws-drawing-batch-", dir=parent))
    destination = parent / ("CWS_Tekenbatch_" + uuid4().hex)
    try:
        generator = EngineeringDrawingGenerator(snapshot.workspace)
        manifest = {
            "schema": SCHEMA, "project_id": snapshot.workspace.project.project_id,
            "source_revision": snapshot.project_revision, "geometry_sha256": snapshot.geometry_sha256,
            "entity_ids": list(snapshot.entity_ids), "status": "verified_review",
            "production_release_granted": False, "documents": [], "files": {},
        }
        merged = PdfWriter()
        try:
            page_number = 1
            for index, key in enumerate(snapshot.entity_ids):
                context.check_cancelled()
                if not context.is_current_generation():
                    raise JobCancelled("Een nieuwere tekenbatch heeft deze opdracht vervangen")
                folder = stage / f"{index+1:04d}-{hashlib.sha256(key.encode()).hexdigest()[:12]}"
                options = _options(snapshot, key)
                result = generator.generate(folder, entity_id=key, make_pdf=True, make_png=False,
                                            record_output=False, **options)
                document = result.document
                if document is None or document.entity_id != key:
                    raise ValueError("Tekenengine retourneerde een andere/ontbrekende documentidentiteit")
                document.validate()
                lint = DrawingLinter.lint(document).to_dict()
                if stable_sha256(lint) != stable_sha256(document.lint):
                    raise ValueError("Tekenbatch heeft inconsistent linterbewijs")
                pdf = Path(result.pdf_path).resolve()
                if not pdf.is_relative_to(stage) or not pdf.is_file():
                    raise ValueError("Tekenbestand ontbreekt of verlaat de private batchmap")
                item = PdfReader(str(pdf))
                if len(item.pages) != result.page_count or len(item.pages) < 1:
                    raise ValueError("PDF-bladenaantal komt niet overeen met de tekening")
                merged.append(item, outline_item=key, import_outline=False)
                first = page_number
                page_number += len(item.pages)
                manifest["documents"].append({
                    "entity_id": key, "file": pdf.relative_to(stage).as_posix(), "sha256": _digest(pdf),
                    "document_sha256": document.document_sha256,
                    "first_page": first, "page_count": result.page_count, "scale": result.scale_label,
                    "sheet_format": document.sheet_format, "orientation": document.orientation,
                    "document_type": document.document_type, "lint": lint,
                })
                context.update((index+1) / (len(snapshot.entity_ids)+1), f"Tekening {index+1}/{len(snapshot.entity_ids)}: {key}")
            merged.add_metadata({"/Title": "CWS geselecteerde tekenbatch", "/Subject": "Reviewbatch; geen nieuwe productie- of machinevrijgave"})
            merged.write(str(stage / "Tekeningen.pdf"))
            manifest["page_count"] = len(merged.pages)
        finally:
            merged.close()
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                manifest["files"][path.relative_to(stage).as_posix()] = _digest(path)
        (stage / "BATCH_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        result = StagedDrawingBatch(stage, destination, _digest(stage / "BATCH_MANIFEST.json"))
        verify_staged_batch(result)
        context.check_cancelled()
        return result
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def verify_staged_batch(result: StagedDrawingBatch) -> dict:
    from pypdf import PdfReader
    manifest_path = result.staging / "BATCH_MANIFEST.json"
    if _digest(manifest_path) != result.manifest_sha256:
        raise ValueError("Batchmanifest gewijzigd na de generatie")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema"] != SCHEMA or manifest["production_release_granted"] is not False:
        raise ValueError("Ongeldige reviewbatch")
    ids = manifest["entity_ids"]
    if not ids or len(ids) != len(set(ids)) or [d["entity_id"] for d in manifest["documents"]] != ids:
        raise ValueError("Batch bevat ontbrekende/dubbele/verkeerde objecten")
    actual = {p.relative_to(result.staging).as_posix() for p in result.staging.rglob("*") if p.is_file()}
    if actual != set(manifest["files"]) | {"BATCH_MANIFEST.json"}:
        raise ValueError("Onverwachte of ontbrekende batchbestanden")
    for relative, expected in manifest["files"].items():
        safe = PurePosixPath(relative)
        target = result.staging.joinpath(*safe.parts)
        if safe.is_absolute() or ".." in safe.parts or not target.resolve().is_relative_to(result.staging.resolve()):
            raise ValueError("Onveilig batchpad")
        if _digest(target) != expected:
            raise ValueError("Batchbestand gewijzigd: " + relative)
    merged = PdfReader(str(result.staging / "Tekeningen.pdf"))
    if len(merged.pages) != sum(d["page_count"] for d in manifest["documents"]) or len(merged.pages) != manifest["page_count"]:
        raise ValueError("Gecombineerde PDF mist bladen")
    return manifest


def publish_drawing_batch(result: StagedDrawingBatch, snapshot: DrawingBatchSnapshot,
                          workspace: Any, *, cancelled: bool = False) -> dict:
    try:
        if cancelled:
            raise JobCancelled()
        if _revision(workspace.project) != snapshot.project_revision:
            raise ValueError("Project of maatvoering gewijzigd; tekenbatch niet gepubliceerd")
        if _geometry(workspace, snapshot.entity_ids)[1] != snapshot.geometry_sha256:
            raise ValueError("Viewer-geometrie gewijzigd; tekenbatch niet gepubliceerd")
        manifest = verify_staged_batch(result)
        if result.destination.exists():
            raise ValueError("Bestaande tekenbatch wordt niet overschreven")
        result.staging.rename(result.destination)
        return {"directory": str(result.destination),
                "pdf": str(result.destination / "Tekeningen.pdf"),
                "manifest": str(result.destination / "BATCH_MANIFEST.json"),
                "manifest_sha256": result.manifest_sha256,
                "entity_ids": list(snapshot.entity_ids), "page_count": manifest["page_count"],
                "production_release_granted": False}
    finally:
        if result.staging.exists():
            shutil.rmtree(result.staging, ignore_errors=True)
