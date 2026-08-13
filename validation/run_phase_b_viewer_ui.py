"""Validate the deterministic Phase-B viewer host UI and write its manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PROJECT_ID = "b7000000-0000-4000-8000-000000000001"
FIXTURE_TIMESTAMP = "2026-08-13T12:00:00+00:00"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import Assembly, Part, ProjectSession, SourceIdentity, ValidationIssue
from cws_convertor.ui.project_viewer import ProjectViewerPanel


def build_fixture(folder: Path) -> ProjectSession:
    source_path = folder / "fase-b-viewer.ifc"
    source_path.write_text("IFC deterministic phase B viewer fixture", encoding="ascii")
    session = ProjectSession.new("Groothuis te Tubbergen", created_by="ui-evidence")
    session.project.project_id = FIXTURE_PROJECT_ID
    session.project.created_at = FIXTURE_TIMESTAMP
    session.project.modified_at = FIXTURE_TIMESTAMP
    source = session.project.add_source_path(source_path, user="ui-evidence")
    source.imported_at = FIXTURE_TIMESTAMP
    source.original_path = ""
    source.analysis_status = "imported"
    source.semantic_import_complete = True
    source.import_strategy = "B_separate_solids"

    assembly = Assembly(
        internal_id="assembly-a1",
        name="Spant A",
        assembly_mark="A1",
        source_identity=SourceIdentity(
            source_file_id=source.source_id,
            source_format="IFC",
            source_sha256=source.sha256,
            source_entity_id="#100",
            assembly_mark="A1",
        ),
        created_at=FIXTURE_TIMESTAMP,
        modified_at=FIXTURE_TIMESTAMP,
    )
    session.project.add_entity(assembly, user="ui-evidence")
    specifications = (
        ("part-k12", "K12", "Dakligger", "HEA240", 5850.0, True, True),
        ("part-k14", "K14", "Randligger", "IPE300", 6200.0, True, False),
        ("part-k18", "K18", "Kolom", "HEB200", 3760.0, True, True),
        ("part-p07", "P07", "Voetplaat", "PL20", 420.0, False, False),
    )
    for index, (part_id, position, name, profile, length, selected, exact) in enumerate(
        specifications,
        start=1,
    ):
        part = Part(
            internal_id=part_id,
            name=name,
            assembly_ids=[assembly.internal_id],
            part_position=position,
            profile=profile,
            material="S355J2",
            length_mm=length,
            source_identity=SourceIdentity(
                source_file_id=source.source_id,
                source_format="IFC",
                source_sha256=source.sha256,
                source_entity_id=f"#{100 + index}",
                global_id=f"phase-b-{position.lower()}",
                part_position=position,
                assembly_mark="A1",
            ),
            geometry_descriptor={
                "source_geometry_hash": f"{index:x}" * 64,
                "source_inspection": {
                    "selection_verified": selected,
                    "production_geometry_exact": exact,
                    "geometry_kind": "native_brep" if exact else "triangulated_mesh",
                },
            },
            created_at=FIXTURE_TIMESTAMP,
            modified_at=FIXTURE_TIMESTAMP,
        )
        part.recompute_hashes()
        if not exact:
            part.validation_issues.append(
                ValidationIssue(
                    code=f"CWS-VIEW-{index:03d}",
                    message=(
                        "Gatpatroon nog handmatig bevestigen"
                        if not selected
                        else "Meshvolume binnen tolerantie bevestigen"
                    ),
                    severity="error" if not selected else "warning",
                    blocking=not selected,
                    entity_id=part.internal_id,
                )
            )
        session.project.add_entity(part, user="ui-evidence")
        assembly.part_ids.append(part.internal_id)
    session.project.audit_log.clear()
    session.project.modified_at = FIXTURE_TIMESTAMP
    session.project.validate()
    return session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "validation" / "results" / "phase-b-viewer-ui.json",
    )
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    root.withdraw()
    panel = ProjectViewerPanel(root)
    panel.pack(fill="both", expand=True)
    with tempfile.TemporaryDirectory(prefix="phase_b_viewer_") as folder_name:
        session = build_fixture(Path(folder_name))
        try:
            panel.load_project(session.project)
            panel.select_entity("part-k14")
            root.update_idletasks()
            manifest = json.loads(panel.export_visual_manifest())
            if manifest["entity_count"] != 5 or manifest["binding_count"] != 5:
                raise RuntimeError("viewer host entity/binding coverage is incomplete")
            if manifest["selected"]["steel_model_id"] != "part-k14":
                raise RuntimeError("deterministic viewer selection was not preserved")
            if manifest["accuracy"]["manual_validation_required"] != 1:
                raise RuntimeError("manual-validation accuracy evidence is missing")
            result = {
                "status": "passed",
                "ui": {
                    "workspace": "3D Viewer",
                    "model_tree": True,
                    "renderer_slot": True,
                    "validation_grid": True,
                    "properties_panel": True,
                    "accuracy_debug": True,
                    "renderer_connected": False,
                },
                "manifest": manifest,
            }
            args.output.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        finally:
            panel.destroy()
            session.close()
            root.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
