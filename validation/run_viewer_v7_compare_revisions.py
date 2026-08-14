#!/usr/bin/env python3
"""Run the CWS Viewer V7 compare/revision acceptance gate.

The gate combines:
- deterministic project revision classification on the real `.cwscproj` when available;
- dependency/artifact invalidation evidence;
- revision-safe viewer workspace and measurement reconciliation;
- exact source/canonical and roundtrip correspondence/deviation evidence;
- exact scribing revalidation;
- atomically written and checksum-verified JSON/CSV/ZIP evidence.

The script never authorises production output. Manufacturing changes remain
blocked until the normal CWS validation gates are rerun.
"""
from __future__ import annotations

import argparse
import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project.model import MachineJob, Part, ProjectModel, SourceIdentity, Transform3D
from cws_convertor.project.storage import ProjectStore
from cws_viewer.contracts.enums import SelectionLevel
from cws_viewer.contracts.scene import ProjectScene
from cws_viewer.contracts.state import CameraState, ViewerDisplayPreferences, Viewpoint
from cws_viewer.contracts.workspace import ViewerWorkspaceState
from cws_viewer.fixtures import build_synthetic_product_scene
from cws_viewer.math3d import Matrix4, Vector3
from cws_viewer.measurements import (
    ExactMeasurementAnchor,
    MeasurementCollection,
    MeasurementProof,
    MeasurementRecord,
)
from cws_viewer.revisions import (
    ChangeKind,
    CompareRelation,
    CorrespondenceMethod,
    ImpactKind,
    PlacementDelta,
    ProjectRevisionCompareReport,
    RevisionObjectChange,
    apply_revision_impact,
    build_exact_compare_bundle,
    build_revision_impact_plan,
    compare_project_revisions,
    reconcile_revision_state,
    render_deviation_heatmap,
    render_project_revision_overview,
    revalidate_scribing_review,
    verify_compare_manifest,
    verify_compare_package,
    write_compare_csv,
    write_compare_manifest,
    write_compare_package,
)
from cws_viewer.version import VIEWER_API_VERSION, VIEWER_PACKAGE_VERSION

REFERENCE_PROJECT_NAME = "CWS_Convertor_v0.7.0-alpha_REFERENCE_PROJECT.cwscproj"


def _default_project() -> Path:
    """Resolve the private reference without making CI depend on `/mnt/data`."""

    candidates: list[Path] = []
    explicit = os.environ.get("CWS_REFERENCE_PROJECT", "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())
    reference_root = os.environ.get("CWS_REFERENCE_ROOT", "").strip()
    if reference_root:
        candidates.append(Path(reference_root).expanduser() / REFERENCE_PROJECT_NAME)
    candidates.extend(
        [
            ROOT / "reference_inputs" / REFERENCE_PROJECT_NAME,
            ROOT.parent / "reference_inputs" / REFERENCE_PROJECT_NAME,
            Path("/mnt/data/CONVERTER_WORK/RELEASE_V070_SEMANTIC_IMPORT_FINAL")
            / REFERENCE_PROJECT_NAME,
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    # Return a portable, descriptive unresolved path. `--allow-missing-project`
    # may then create explicit synthetic CI evidence without claiming the
    # private real-project gate.
    return (ROOT / "reference_inputs" / REFERENCE_PROJECT_NAME).resolve()


DEFAULT_PROJECT = _default_project()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _contact_sheet(images: list[tuple[str, Path]], output: Path) -> None:
    opened: list[tuple[str, str, Image.Image]] = []
    for label, path in images:
        with Image.open(path) as source:
            opened.append((label, path.name, source.convert("RGB").copy()))
    card_w, card_h = 780, 510
    columns = 2
    rows = (len(opened) + columns - 1) // columns
    canvas = Image.new("RGB", (card_w * columns, card_h * rows), (13, 22, 35))
    draw = ImageDraw.Draw(canvas)
    try:
        title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        title_font = small_font = ImageFont.load_default()
    for index, (label, file_name, image) in enumerate(opened):
        col, row = index % columns, index // columns
        x0, y0 = col * card_w, row * card_h
        image.thumbnail((card_w - 28, card_h - 82), Image.Resampling.LANCZOS)
        x = x0 + (card_w - image.width) // 2
        y = y0 + 54
        canvas.paste(image, (x, y))
        draw.rectangle((x0, y0, x0 + card_w, y0 + 45), fill=(29, 47, 63))
        draw.text((x0 + 14, y0 + 12), label, fill=(235, 244, 250), font=title_font)
        draw.text((x0 + 14, y0 + card_h - 24), file_name, fill=(148, 171, 194), font=small_font)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def _real_project_revision(project: ProjectModel) -> tuple[ProjectModel, dict[str, Any]]:
    target = ProjectModel.from_dict(project.to_dict())
    lo4 = sorted(
        (
            part for part in target.parts.values()
            if (part.part_position or part.source_identity.part_position) == "LO4"
        ),
        key=lambda part: part.internal_id,
    )
    if len(lo4) < 4:
        raise RuntimeError(f"Verwacht vier LO4-instanties, gevonden: {len(lo4)}")

    moved = lo4[0]
    before_move_hash = moved.manufacturing_hash
    matrix = [list(row) for row in moved.global_placement.matrix]
    matrix[0][3] = float(matrix[0][3]) + 275.0
    matrix[1][3] = float(matrix[1][3]) + 125.0
    moved.global_placement = Transform3D(matrix)
    if moved.manufacturing_hash != before_move_hash:
        raise RuntimeError("Placement-only wijziging veranderde manufacturing hash")

    lo4_ids = {item.internal_id for item in lo4}
    material_part = next(
        part for part in target.parts.values()
        if part.internal_id not in lo4_ids
        and (part.material or part.normalized_material) in {"S235JR", "S355JR"}
        and part.profile
    )
    old_material = material_part.material or material_part.normalized_material
    material_part.material = "S355JR" if old_material != "S355JR" else "S235JR"
    material_part.material_grade = material_part.material
    material_part.normalized_material = material_part.material
    material_part.recompute_hashes()

    mirror_part = next(
        part for part in target.parts.values()
        if part.internal_id not in {moved.internal_id, material_part.internal_id}
        and part.profile
        and part.geometry_hash
    )
    mirror_part.mirrored = not bool(mirror_part.mirrored)
    mirror_part.recompute_hashes()

    quantity_part = lo4[1]
    quantity_part.quantity_total = int(quantity_part.quantity_total or 1) + 1
    quantity_part.export_status = "released"
    quantity_part.nc1_eligible = True
    quantity_part.properties["trusted_artifacts"] = {
        "nc1": "NC1-QUANTITY-KEEP",
        "production_pdf": "PDF-QUANTITY-REVIEW",
    }

    excluded = {
        moved.internal_id,
        material_part.internal_id,
        mirror_part.internal_id,
        quantity_part.internal_id,
    }
    removed = next(
        (
            part for part in target.parts.values()
            if part.internal_id not in excluded
            and part.source_identity.source_format.upper() == "STEP"
        ),
        None,
    )
    if removed is None:
        removed = next(part for part in target.parts.values() if part.internal_id not in excluded)
    removed_id = removed.internal_id
    for assembly_id in list(removed.assembly_ids):
        assembly = target.assemblies.get(assembly_id)
        if assembly is not None:
            assembly.part_ids = [item for item in assembly.part_ids if item != removed_id]
            if assembly.main_part_id == removed_id:
                assembly.main_part_id = assembly.part_ids[0] if assembly.part_ids else ""
    for fastener in target.fasteners.values():
        fastener.connected_part_ids = [item for item in fastener.connected_part_ids if item != removed_id]
    for weld in target.welds.values():
        weld.connected_part_ids = [item for item in weld.connected_part_ids if item != removed_id]
    for operation in target.production_operations.values():
        operation.part_ids = [item for item in operation.part_ids if item != removed_id]
    for job in target.machine_jobs.values():
        job.part_ids = [item for item in job.part_ids if item != removed_id]
    target.parts.pop(removed_id)

    added = Part(
        internal_id="v7-added-reference-part",
        name="V7 added validation part",
        part_position="V7-ADD-001",
        profile="STRIP8*80",
        normalized_profile="STRIP8*80",
        material="S355JR",
        material_grade="S355JR",
        normalized_material="S355JR",
        length_mm=777.0,
        geometry_descriptor={
            "source_geometry_hash": "7" * 64,
            "solid_count": 1,
            "volume_mm3": 497280.0,
            "area_mm2": 137792.0,
            "bbox_sorted_mm": [8.0, 80.0, 777.0],
            "primitive_counts": {"solids": 1, "faces": 6, "edges": 12},
            "profile_names": ["STRIP8*80"],
        },
        source_identity=SourceIdentity(
            source_format="V7_FIXTURE",
            source_sha256="7" * 64,
            source_entity_id="V7-ADD-001",
            part_position="V7-ADD-001",
        ),
        classification_status="confirmed",
        classification_method="deterministic_test_fixture",
        classification_confidence=1.0,
        profile_confidence=1.0,
        material_confidence=1.0,
    )
    added.recompute_hashes()
    target.parts[added.internal_id] = added

    moved.properties["trusted_artifacts"] = {"nc1": "NC1-MOVED-KEEP"}
    material_part.properties["trusted_artifacts"] = {
        "nc1": "NC1-MATERIAL-OLD",
        "step": "STEP-MATERIAL-OLD",
    }
    linked_assembly_id = material_part.assembly_ids[0] if material_part.assembly_ids else ""
    if linked_assembly_id and linked_assembly_id in target.assemblies:
        assembly = target.assemblies[linked_assembly_id]
        assembly.artifact_ids = ["V7-ASSEMBLY-DRAWING"]
        assembly.drawing_status = "released"
        assembly.production_status = "released"

    job_id = "V7-MACHINE-JOB"
    target.machine_jobs[job_id] = MachineJob(
        internal_id=job_id,
        name="V7 revision invalidation job",
        part_ids=[material_part.internal_id],
        simulation_status="passed",
        release_status="released",
        checksum="a" * 64,
    )
    planning_job_id = "V7-PLANNING-MACHINE-JOB"
    target.machine_jobs[planning_job_id] = MachineJob(
        internal_id=planning_job_id,
        name="V7 planning-only review job",
        part_ids=[quantity_part.internal_id],
        simulation_status="passed",
        release_status="released",
        checksum="c" * 64,
    )
    order_id = "V7-PRODUCTION-ORDER"
    target.production_orders[order_id] = {
        "part_ids": [material_part.internal_id],
        "status": "released",
    }
    optimization_id = "V7-OPTIMIZATION"
    target.settings.setdefault("optimization_results", {})[optimization_id] = {
        "part_ids": [material_part.internal_id],
        "status": "released",
    }
    planning_optimization_id = "V7-PLANNING-OPTIMIZATION"
    target.settings.setdefault("optimization_results", {})[planning_optimization_id] = {
        "part_ids": [quantity_part.internal_id],
        "status": "released",
    }
    planning_order_id = "V7-PLANNING-PRODUCTION-ORDER"
    target.production_orders[planning_order_id] = {
        "part_ids": [quantity_part.internal_id],
        "status": "released",
    }
    scribing_review_id = "V7-SCRIBING-REVIEW"
    target.settings.setdefault("scribing_reviews", {})[scribing_review_id] = {
        "target_part_id": material_part.internal_id,
        "partner_part_id": moved.internal_id,
        "status": "confirmed",
    }

    target.modified_at = project.modified_at
    target.validate()
    return target, {
        "moved_part_id": moved.internal_id,
        "moved_part_position": moved.part_position,
        "moved_manufacturing_hash_unchanged": moved.manufacturing_hash == before_move_hash,
        "material_part_id": material_part.internal_id,
        "material_before": old_material,
        "material_after": material_part.material,
        "mirror_part_id": mirror_part.internal_id,
        "mirror_after": mirror_part.mirrored,
        "quantity_part_id": quantity_part.internal_id,
        "quantity_after": quantity_part.quantity_total,
        "removed_part_id": removed_id,
        "removed_part_position": removed.part_position,
        "added_part_id": added.internal_id,
        "added_part_position": added.part_position,
        "linked_assembly_id": linked_assembly_id,
        "machine_job_id": job_id,
        "planning_machine_job_id": planning_job_id,
        "production_order_id": order_id,
        "planning_production_order_id": planning_order_id,
        "optimization_id": optimization_id,
        "planning_optimization_id": planning_optimization_id,
        "scribing_review_id": scribing_review_id,
        "lo4_ids": [part.internal_id for part in lo4],
    }


def _synthetic_project_revision() -> tuple[ProjectModel, ProjectModel, dict[str, Any]]:
    def make_part(part_id: str, position: str, *, material: str = "S355JR") -> Part:
        value = Part(
            internal_id=part_id,
            name=position,
            part_position=position,
            profile="HEA140",
            profile_type="I",
            material=material,
            material_grade=material,
            length_mm=1000.0,
            source_identity=SourceIdentity(
                source_format="SYNTHETIC",
                global_id=f"gid-{part_id}",
                part_position=position,
            ),
            geometry_descriptor={
                "source_geometry_hash": (part_id * 64)[:64],
                "solid_count": 1,
                "bbox_sorted_mm": [1000, 140, 133],
            },
            production_features=[{"kind": "hole", "diameter": 18.0, "x": 100.0, "q": 40.0}],
            classification_status="confirmed",
            classification_confidence=1.0,
            profile_confidence=1.0,
            material_confidence=1.0,
        )
        value.recompute_hashes()
        return value

    source = ProjectModel.new("V7 synthetic revision fixture")
    source.project_id = "99999999-9999-4999-8999-999999999999"
    for item in (
        make_part("MOVE", "MOVE1"),
        make_part("MAT", "MAT1"),
        make_part("MIRROR", "MIR1"),
        make_part("QTY", "QTY1"),
        make_part("REMOVE", "REMOVE1"),
    ):
        source.parts[item.internal_id] = item

    target = ProjectModel.from_dict(source.to_dict())
    before_hash = target.parts["MOVE"].manufacturing_hash
    target.parts["MOVE"].global_placement = Transform3D(
        [[1, 0, 0, 275], [0, 1, 0, 125], [0, 0, 1, 0], [0, 0, 0, 1]]
    )
    target.parts["MAT"].material = "S235JR"
    target.parts["MAT"].material_grade = "S235JR"
    target.parts["MAT"].normalized_material = "S235JR"
    target.parts["MAT"].recompute_hashes()
    target.parts["MIRROR"].mirrored = True
    target.parts["MIRROR"].recompute_hashes()
    target.parts["QTY"].quantity_total = int(target.parts["QTY"].quantity_total or 1) + 1
    target.parts["QTY"].export_status = "released"
    target.parts["QTY"].nc1_eligible = True
    target.parts["QTY"].properties["trusted_artifacts"] = {
        "nc1": "NC1-QTY-KEEP",
        "production_pdf": "PDF-QTY-REVIEW",
    }

    removed = target.parts.pop("REMOVE")
    added = make_part("ADD", "ADD1", material="S235JR")
    added.profile = "STRIP8*80"
    added.normalized_profile = "STRIP8*80"
    added.profile_type = "FLAT"
    added.length_mm = 777.0
    added.geometry_descriptor = {
        "source_geometry_hash": "7" * 64,
        "solid_count": 1,
        "volume_mm3": 497280.0,
        "area_mm2": 137792.0,
        "bbox_sorted_mm": [8.0, 80.0, 777.0],
        "primitive_counts": {"solids": 1, "faces": 6, "edges": 12},
        "profile_names": ["STRIP8*80"],
    }
    added.source_identity = SourceIdentity(
        source_format="V7_FIXTURE",
        source_sha256="7" * 64,
        source_entity_id="ADD1",
        part_position="ADD1",
    )
    added.recompute_hashes()
    target.parts[added.internal_id] = added

    target.parts["MOVE"].properties["trusted_artifacts"] = {"nc1": "NC1-MOVE-KEEP"}
    target.parts["MAT"].properties["trusted_artifacts"] = {
        "nc1": "NC1-MAT-OLD",
        "step": "STEP-MAT-OLD",
    }
    job_id = "V7-SYNTHETIC-MACHINE-JOB"
    target.machine_jobs[job_id] = MachineJob(
        internal_id=job_id,
        name="V7 synthetic invalidation job",
        part_ids=["MAT"],
        simulation_status="passed",
        release_status="released",
        checksum="b" * 64,
    )
    planning_job_id = "V7-SYNTHETIC-PLANNING-JOB"
    target.machine_jobs[planning_job_id] = MachineJob(
        internal_id=planning_job_id,
        name="V7 synthetic planning review job",
        part_ids=["QTY"],
        simulation_status="passed",
        release_status="released",
        checksum="c" * 64,
    )
    order_id = "V7-SYNTHETIC-PRODUCTION-ORDER"
    target.production_orders[order_id] = {"part_ids": ["MAT"], "status": "released"}
    optimization_id = "V7-SYNTHETIC-OPTIMIZATION"
    target.settings.setdefault("optimization_results", {})[optimization_id] = {
        "part_ids": ["MAT"],
        "status": "released",
    }
    planning_optimization_id = "V7-SYNTHETIC-PLANNING-OPTIMIZATION"
    target.settings.setdefault("optimization_results", {})[planning_optimization_id] = {
        "part_ids": ["QTY"],
        "status": "released",
    }
    planning_order_id = "V7-SYNTHETIC-PLANNING-ORDER"
    target.production_orders[planning_order_id] = {"part_ids": ["QTY"], "status": "released"}
    scribing_review_id = "V7-SYNTHETIC-SCRIBING-REVIEW"
    target.settings.setdefault("scribing_reviews", {})[scribing_review_id] = {
        "target_part_id": "MAT",
        "partner_part_id": "MOVE",
        "status": "confirmed",
    }
    target.validate()

    return source, target, {
        "moved_part_id": "MOVE",
        "moved_part_position": "MOVE1",
        "moved_manufacturing_hash_unchanged": target.parts["MOVE"].manufacturing_hash == before_hash,
        "material_part_id": "MAT",
        "material_before": "S355JR",
        "material_after": "S235JR",
        "mirror_part_id": "MIRROR",
        "mirror_after": True,
        "quantity_part_id": "QTY",
        "quantity_after": target.parts["QTY"].quantity_total,
        "removed_part_id": "REMOVE",
        "removed_part_position": removed.part_position,
        "added_part_id": "ADD",
        "added_part_position": "ADD1",
        "linked_assembly_id": "",
        "machine_job_id": job_id,
        "planning_machine_job_id": planning_job_id,
        "production_order_id": order_id,
        "planning_production_order_id": planning_order_id,
        "optimization_id": optimization_id,
        "planning_optimization_id": planning_optimization_id,
        "scribing_review_id": scribing_review_id,
        "lo4_ids": [],
    }


def _workspace_reconciliation_evidence() -> dict[str, Any]:
    old = build_synthetic_product_scene(12, revision_id="A")
    moved_id = "node:item:000001"
    changed_id = "node:item:000002"
    nodes = []
    for node in old.nodes:
        if node.node_id == moved_id:
            nodes.append(replace(node, transform=Matrix4.translation(Vector3(200, 0, 0))))
        elif node.node_id == changed_id:
            nodes.append(replace(node, geometry_hash="f" * 64, manufacturing_hash="e" * 64))
        else:
            nodes.append(node)
    models = tuple(replace(model, revision_id="B") for model in old.models)
    new = ProjectScene.create(
        project_id=old.project_id,
        revision_id="B",
        models=models,
        nodes=nodes,
        geometry=old.geometry,
        styles=old.styles,
    )
    old_moved = next(item for item in old.nodes if item.node_id == moved_id)
    new_moved = next(item for item in new.nodes if item.node_id == moved_id)
    old_changed = next(item for item in old.nodes if item.node_id == changed_id)
    new_changed = next(item for item in new.nodes if item.node_id == changed_id)

    def change(kind: ChangeKind, old_node, new_node, impact: ImpactKind, delta=None):
        return RevisionObjectChange(
            change_id=f"change-{old_node.node_id}",
            kind=kind,
            old_entity_id=old_node.entity_id,
            new_entity_id=new_node.entity_id,
            old_source_id=old_node.node_id,
            new_source_id=new_node.node_id,
            correspondence_method=CorrespondenceMethod.STABLE_ID,
            confidence=1.0,
            impacts=(impact,),
            old_geometry_hash=old_node.geometry_hash,
            new_geometry_hash=new_node.geometry_hash,
            old_manufacturing_hash=old_node.manufacturing_hash,
            new_manufacturing_hash=new_node.manufacturing_hash,
            placement_delta=delta,
        )

    report = ProjectRevisionCompareReport.create(
        project_id=old.project_id,
        old_revision_id="A",
        new_revision_id="B",
        relation=CompareRelation.REVISION,
        changes=(
            change(
                ChangeKind.MOVED,
                old_moved,
                new_moved,
                ImpactKind.PLACEMENT,
                PlacementDelta(Vector3(200, 0, 0), 200.0, 0.0, 200.0),
            ),
            change(ChangeKind.CHANGED, old_changed, new_changed, ImpactKind.GEOMETRY),
        ),
    )
    viewpoint = Viewpoint(
        viewpoint_id="v7-viewpoint",
        name="V7 revision inspection",
        camera=CameraState.default(),
        visible_node_ids=(moved_id, changed_id),
        hidden_node_ids=(),
        selected_node_ids=(changed_id,),
        section_planes=(),
        clipping_box=None,
        scene_hash=old.scene_hash,
    )
    workspace = ViewerWorkspaceState.create(
        project_id=old.project_id,
        scene_hash=old.scene_hash,
        camera=CameraState.default(),
        selection_level=SelectionLevel.PART,
        selected_node_ids=(moved_id, changed_id),
        hidden_node_ids=(),
        isolation_node_ids=(),
        ghost_context=False,
        transparency_by_node=(),
        color_by_node=(),
        display_preferences=ViewerDisplayPreferences(),
        section_planes=(),
        clipping_box=None,
        viewpoints=(viewpoint,),
        visibility_sets=(),
        accuracy_mode=True,
        active_viewpoint_id=viewpoint.viewpoint_id,
    )
    measurements = MeasurementCollection()
    for node, measurement_id in (
        (old_moved, "v7-moved-measurement"),
        (old_changed, "v7-changed-measurement"),
    ):
        local = Vector3.zero()
        world = node.transform.transform_point(local)
        anchor = ExactMeasurementAnchor(
            node_id=node.node_id,
            entity_id=node.entity_id,
            world_point=world,
            local_point=local,
            geometry_hash=node.geometry_hash,
            proof=MeasurementProof.ANALYTICAL_BREP,
        )
        measurements.add(MeasurementRecord(
            measurement_id=measurement_id,
            kind="coordinate",
            value=0.0,
            unit="mm",
            anchors=(anchor,),
            formatted_text="0",
            validity_hash="v7",
            proof=MeasurementProof.ANALYTICAL_BREP,
        ))
    mapped, updated, reconciliation = reconcile_revision_state(
        old,
        new,
        workspace,
        report,
        measurements=measurements,
        review_bindings={
            "v7-review-changed": {
                "entity_id": old_changed.entity_id,
                "geometry_hash": old_changed.geometry_hash,
            }
        },
    )
    return {
        "mapped_scene_hash": mapped.scene_hash,
        "expected_scene_hash": new.scene_hash,
        "reconciliation": reconciliation.to_dict(),
        "moved_measurement_world_x_mm": updated.records["v7-moved-measurement"].anchors[0].world_point.x,
        "moved_measurement_status": updated.records["v7-moved-measurement"].status.value,
        "changed_measurement_status": updated.records["v7-changed-measurement"].status.value,
    }


def run(project_path: Path, output: Path) -> dict[str, Any]:
    """Run V7 in two memory-bounded stages.

    The semantic project revision is processed before loading CadQuery/OCP/VTK,
    so a large project graph and the native exact geometry stack are not kept in
    RAM at the same time.
    """
    import gc

    output.mkdir(parents=True, exist_ok=True)
    screenshots = output / "screenshots"
    screenshots.mkdir(exist_ok=True)
    started = time.perf_counter()

    private_reference_available = project_path.is_file()
    open_started = time.perf_counter()
    if private_reference_available:
        package = ProjectStore().open(project_path, read_only=True)
        source_project = package.project
        target_project, mutation_evidence = _real_project_revision(source_project)
        private_reference_status = "passed"
    else:
        package = None
        source_project, target_project, mutation_evidence = _synthetic_project_revision()
        private_reference_status = "not_run_missing_private_reference"
    project_open_s = time.perf_counter() - open_started

    compare_started = time.perf_counter()
    project_report = compare_project_revisions(source_project, target_project)
    compare_s = time.perf_counter() - compare_started
    impact_plan = build_revision_impact_plan(source_project, target_project, project_report)
    applied_project = ProjectModel.from_dict(target_project.to_dict())
    applied_summary = apply_revision_impact(applied_project, impact_plan, user="viewer-v7-validation")

    manifest_path = write_compare_manifest(
        output / "REAL_PROJECT_COMPARE_MANIFEST.json",
        project_report,
        impact_plan=impact_plan,
    )
    manifest_verification = verify_compare_manifest(manifest_path)
    csv_path = write_compare_csv(output / "REAL_PROJECT_CHANGES.csv", project_report)
    overview = render_project_revision_overview(
        project_report, screenshots / "03_real_project_revision_overview.png"
    )
    _json(output / "REAL_PROJECT_IMPACT_PLAN.json", impact_plan.to_dict())
    _json(output / "REAL_PROJECT_MUTATION_EVIDENCE.json", mutation_evidence)
    _json(output / "REAL_PROJECT_IMPACT_APPLIED_SUMMARY.json", applied_summary)

    moved_change = next(item for item in project_report.changes if item.new_entity_id == mutation_evidence["moved_part_id"])
    material_change = next(item for item in project_report.changes if item.new_entity_id == mutation_evidence["material_part_id"])
    mirror_change = next(item for item in project_report.changes if item.new_entity_id == mutation_evidence["mirror_part_id"])
    quantity_change = next(item for item in project_report.changes if item.new_entity_id == mutation_evidence["quantity_part_id"])
    added_change = next(item for item in project_report.changes if item.new_entity_id == mutation_evidence["added_part_id"])
    removed_change = next(item for item in project_report.changes if item.old_entity_id == mutation_evidence["removed_part_id"])

    workspace_evidence = _workspace_reconciliation_evidence()
    _json(output / "REVISION_WORKSPACE_RECONCILIATION.json", workspace_evidence)

    project_gates = {
        "real_project_entity_counts_preserved": (
            len(source_project.parts) == 2432
            and len(source_project.assemblies) == 353
            and len(source_project.fasteners) == 723
            and len(source_project.welds) == 2654
        ) if private_reference_available else None,
        "four_lo4_instances_found": len(mutation_evidence["lo4_ids"]) == 4 if private_reference_available else None,
        "placement_only_classified_moved": moved_change.kind == ChangeKind.MOVED,
        "placement_only_reuse_allowed": moved_change.production_reuse_allowed,
        "placement_hash_unchanged": mutation_evidence["moved_manufacturing_hash_unchanged"],
        "material_change_detected": ImpactKind.MATERIAL in material_change.impacts,
        "material_change_reuse_blocked": not material_change.production_reuse_allowed,
        "mirror_change_detected": ImpactKind.MIRROR in mirror_change.impacts,
        "mirror_change_reuse_blocked": not mirror_change.production_reuse_allowed,
        "quantity_change_detected": ImpactKind.QUANTITY in quantity_change.impacts,
        "quantity_change_is_planning_only": (
            mutation_evidence["quantity_part_id"] in impact_plan.planning_changed_part_ids
            and mutation_evidence["quantity_part_id"] not in impact_plan.changed_part_ids
            and quantity_change.production_reuse_allowed
        ),
        "quantity_core_artifact_preserved": (
            applied_project.parts[mutation_evidence["quantity_part_id"]]
            .properties.get("trusted_artifacts", {})
            .get("nc1") in {"NC1-QUANTITY-KEEP", "NC1-QTY-KEEP"}
        ),
        "quantity_planning_artifact_reviewed": (
            "production_pdf" not in applied_project.parts[mutation_evidence["quantity_part_id"]]
            .properties.get("trusted_artifacts", {})
            and applied_project.parts[mutation_evidence["quantity_part_id"]].export_status == "released"
            and applied_project.parts[mutation_evidence["quantity_part_id"]].nc1_eligible
        ),
        "added_part_traceable": added_change.kind == ChangeKind.ADDED,
        "removed_part_traceable": removed_change.kind == ChangeKind.REMOVED,
        "compare_manifest_verified": manifest_verification["change_count"] == len(project_report.changes),
        "impact_invalidation_applied": applied_summary["changed_parts"] >= 2,
        "machine_job_invalidated": (
            mutation_evidence["machine_job_id"] in impact_plan.blocked_machine_job_ids
            and applied_project.machine_jobs[mutation_evidence["machine_job_id"]].release_status == "blocked"
        ),
        "planning_machine_job_requires_review": (
            mutation_evidence["planning_machine_job_id"] in impact_plan.review_machine_job_ids
            and applied_project.machine_jobs[mutation_evidence["planning_machine_job_id"]].release_status == "review_required"
            and applied_project.machine_jobs[mutation_evidence["planning_machine_job_id"]].checksum == ""
        ),
        "production_order_invalidated": (
            mutation_evidence["production_order_id"] in impact_plan.invalidated_production_order_ids
            and applied_project.production_orders[mutation_evidence["production_order_id"]]["status"] == "invalidated"
        ),
        "planning_production_order_invalidated": (
            mutation_evidence["planning_production_order_id"] in impact_plan.invalidated_production_order_ids
            and applied_project.production_orders[mutation_evidence["planning_production_order_id"]]["status"] == "invalidated"
        ),
        "optimization_invalidated": (
            mutation_evidence["optimization_id"] in impact_plan.invalidated_optimization_ids
            and applied_project.settings["optimization_results"][mutation_evidence["optimization_id"]]["status"] == "invalidated"
        ),
        "planning_optimization_invalidated": (
            mutation_evidence["planning_optimization_id"] in impact_plan.invalidated_optimization_ids
            and applied_project.settings["optimization_results"][mutation_evidence["planning_optimization_id"]]["status"] == "invalidated"
        ),
        "scribing_review_invalidated": (
            mutation_evidence["scribing_review_id"] in impact_plan.invalidated_scribing_review_ids
            and applied_project.settings["scribing_reviews"][mutation_evidence["scribing_review_id"]]["status"] == "invalidated"
        ),
        "embedded_artifacts_invalidated": applied_summary["invalidated_embedded_artifacts"] >= 2,
        "placement_only_artifact_preserved": "trusted_artifacts" in applied_project.parts[mutation_evidence["moved_part_id"]].properties,
        "workspace_scene_rebound": workspace_evidence["mapped_scene_hash"] == workspace_evidence["expected_scene_hash"],
        "workspace_changed_measurement_invalidated": workspace_evidence["changed_measurement_status"] == "invalidated",
        "workspace_moved_measurement_preserved": (
            workspace_evidence["moved_measurement_status"] == "valid"
            and abs(float(workspace_evidence["moved_measurement_world_x_mm"]) - 200.0) <= 1e-9
        ),
        "changed_parts_export_blocked": all(
            applied_project.parts[part_id].export_status == "blocked"
            for part_id in impact_plan.changed_part_ids
            if part_id in applied_project.parts
        ),
    }

    project_counts = {
        "assemblies": len(source_project.assemblies),
        "parts": len(source_project.parts),
        "fasteners": len(source_project.fasteners),
        "welds": len(source_project.welds),
    }
    project_change_counts = dict(project_report.counts)
    project_report_hash = project_report.manifest_sha256
    project_blocking_codes = list(project_report.blocking_codes)
    impact_payload = impact_plan.to_dict()

    del package, source_project, target_project, applied_project
    del moved_change, material_change, mirror_change, quantity_change, added_change, removed_change
    gc.collect()

    from cws_viewer.exact import ScribingReviewService, build_exact_runtime, build_plate, p1811_definition

    exact_source = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-source")
    exact_equal = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-canonical")
    exact_changed = build_exact_runtime(
        build_plate(p1811_definition(changed_hole_diameter=20)),
        part_id="P1811-hole-d20",
    )
    equal_bundle = build_exact_compare_bundle(exact_source, exact_equal, relation=CompareRelation.SOURCE_CANONICAL)
    changed_bundle = build_exact_compare_bundle(exact_source, exact_changed, relation=CompareRelation.REVISION)
    roundtrip_bundle = build_exact_compare_bundle(exact_source, exact_equal, relation=CompareRelation.ROUNDTRIP)
    if not equal_bundle.production_safe or not roundtrip_bundle.production_safe:
        raise RuntimeError("Exacte gelijke P1811-vergelijking faalde")
    if changed_bundle.production_safe:
        raise RuntimeError("Gewijzigd gat werd onterecht als production-safe beschouwd")

    equal_heatmap = render_deviation_heatmap(
        exact_source, exact_equal, equal_bundle.deviation, screenshots / "01_exact_equal.png"
    )
    changed_heatmap = render_deviation_heatmap(
        exact_source, exact_changed, changed_bundle.deviation, screenshots / "02_changed_hole.png"
    )
    _json(output / "P1811_SOURCE_CANONICAL_BUNDLE.json", equal_bundle.to_dict())
    _json(output / "P1811_CHANGED_HOLE_BUNDLE.json", changed_bundle.to_dict())
    _json(output / "P1811_ROUNDTRIP_BUNDLE.json", roundtrip_bundle.to_dict())

    import cadquery as cq

    scribe_target = build_exact_runtime(cq.Solid.makeBox(100, 80, 10), part_id="SCRIBE-TARGET")
    scribe_partner = build_exact_runtime(
        cq.Solid.makeBox(40, 40, 20, cq.Vector(20, 20, 10)), part_id="SCRIBE-PARTNER"
    )
    service = ScribingReviewService(scribe_target, scribe_partner)
    for proposal in service.proposals:
        service.confirm(proposal.proposal_id, user="viewer-v7-validation", reason="exact contact line checked")
    scribe_same = revalidate_scribing_review(service.payload(), scribe_target, scribe_partner)
    changed_partner = build_exact_runtime(
        cq.Solid.makeBox(50, 40, 20, cq.Vector(25, 20, 10)), part_id="SCRIBE-PARTNER-REV2"
    )
    scribe_changed = revalidate_scribing_review(service.payload(), scribe_target, changed_partner)
    if scribe_same.invalidated_count or scribe_changed.invalidated_count == 0:
        raise RuntimeError("Scribing revalidation gate mislukt")
    _json(output / "SCRIBING_REVALIDATION_SAME.json", scribe_same.to_dict())
    _json(output / "SCRIBING_REVALIDATION_CHANGED.json", scribe_changed.to_dict())

    compare_package = write_compare_package(
        output / "CWS_Viewer_V7_Compare_Evidence",
        project_report,
        impact_plan=impact_plan,
        exact_bundles={
            "p1811_source_canonical": equal_bundle,
            "p1811_changed_hole": changed_bundle,
            "p1811_roundtrip": roundtrip_bundle,
        },
        extra_files={
            "images/exact_equal.png": equal_heatmap,
            "images/changed_hole.png": changed_heatmap,
            "images/project_revision_overview.png": overview,
            "evidence/mutation.json": output / "REAL_PROJECT_MUTATION_EVIDENCE.json",
            "evidence/impact_applied.json": output / "REAL_PROJECT_IMPACT_APPLIED_SUMMARY.json",
            "evidence/workspace_reconciliation.json": output / "REVISION_WORKSPACE_RECONCILIATION.json",
        },
        zip_path=output / "CWS_Viewer_V7_Compare_Evidence.zip",
    )
    compare_package_verification = verify_compare_package(compare_package["zip"])

    gates = {
        "exact_equal_safe": equal_bundle.production_safe,
        "changed_hole_blocked": not changed_bundle.production_safe,
        "roundtrip_equal_safe": roundtrip_bundle.production_safe,
        "compare_package_verified": compare_package_verification["verified_files"] >= 10,
        **project_gates,
    }
    failed = [name for name, passed in gates.items() if passed is False]
    if failed:
        raise RuntimeError(f"V7 gate(s) mislukt: {failed}")

    contactsheet = output / "CWS_Viewer_V7_Compare_Revisions_Contactsheet.png"
    _contact_sheet(
        [
            ("Exact source ↔ canonical · PASS", equal_heatmap),
            ("Gewijzigd gat Ø18 → Ø20 · BLOCKED", changed_heatmap),
            (
                "Echt project · revision summary"
                if private_reference_available
                else "Synthetische revision summary",
                overview,
            ),
        ],
        contactsheet,
    )

    result = {
        "schema": "cws-viewer-v7-validation-1.0",
        "status": "passed" if private_reference_available else "passed_with_private_reference_not_run",
        "viewer_package_version": VIEWER_PACKAGE_VERSION,
        "viewer_api_version": VIEWER_API_VERSION,
        "platform": platform.platform(),
        "python": sys.version.replace("\n", " "),
        "project_path": str(project_path),
        "private_reference_status": private_reference_status,
        "project_sha256": _sha256(project_path) if private_reference_available else "",
        "timings_seconds": {
            "project_open": project_open_s,
            "project_compare": compare_s,
            "total": time.perf_counter() - started,
        },
        "real_project_counts": project_counts,
        "real_project_change_counts": project_change_counts,
        "real_project_report_hash": project_report_hash,
        "real_project_blocking_codes": project_blocking_codes,
        "impact": impact_payload,
        "impact_applied": applied_summary,
        "workspace_reconciliation": workspace_evidence,
        "compare_package": compare_package_verification,
        "mutation_evidence": mutation_evidence,
        "exact": {
            "equal_bundle_hash": equal_bundle.bundle_sha256,
            "roundtrip_bundle_hash": roundtrip_bundle.bundle_sha256,
            "changed_bundle_hash": changed_bundle.bundle_sha256,
            "equal_max_mm": equal_bundle.deviation.maximum_mm,
            "changed_max_mm": changed_bundle.deviation.maximum_mm,
            "changed_blocking_codes": list(changed_bundle.correspondence.blocking_codes),
        },
        "scribing": {
            "original_proposals": len(service.proposals),
            "preserved_same": scribe_same.preserved_count,
            "invalidated_changed": scribe_changed.invalidated_count,
            "production_release_allowed": False,
        },
        "gates": gates,
        "outputs": {
            "manifest": str(manifest_path),
            "csv": str(csv_path),
            "overview": str(overview),
            "equal_heatmap": str(equal_heatmap),
            "changed_heatmap": str(changed_heatmap),
            "contactsheet": str(contactsheet),
            "compare_package": str(compare_package["zip"]),
        },
    }
    _json(output / "VIEWER_V7_VALIDATION_RESULTS.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--output", type=Path, default=ROOT / "validation" / "viewer_v7")
    parser.add_argument("--allow-missing-project", action="store_true")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    if not project.is_file() and not args.allow_missing_project:
        parser.error(
            f"Privaat referentieproject ontbreekt: {project}. Gebruik --allow-missing-project "
            "uitsluitend voor expliciete synthetische CI-evidence."
        )
    result = run(project, args.output.expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
