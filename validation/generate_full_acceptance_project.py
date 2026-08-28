"""Build a redistributable exact-geometry project for full acceptance."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _set_guid(entity: object, key: str) -> None:
    import ifcopenshell

    if hasattr(entity, "GlobalId"):
        entity.GlobalId = ifcopenshell.guid.compress(uuid5(NAMESPACE_URL, key).hex)


def generate(project_path: Path, *, product_count: int = 1000) -> dict[str, object]:
    import ifcopenshell
    import ifcopenshell.api

    from cws_convertor.project import ProjectSession

    if product_count < 1000:
        raise ValueError("product_count must be at least 1000")
    project_path = project_path.resolve()
    source_path = project_path.with_suffix(".ifc")
    project_path.parent.mkdir(parents=True, exist_ok=True)

    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name="CWS Full Acceptance"
    )
    _set_guid(project, "cws-full-acceptance/project")
    ifcopenshell.api.run("unit.assign_unit", model)
    model_context = ifcopenshell.api.run("context.add_context", model, context_type="Model")
    body = ifcopenshell.api.run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model_context,
    )
    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuilding", name="Building"
    )
    storey = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcBuildingStorey", name="Storey"
    )
    for entity, name in ((site, "site"), (building, "building"), (storey, "storey")):
        _set_guid(entity, f"cws-full-acceptance/{name}")
    ifcopenshell.api.run("aggregate.assign_object", model, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", model, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", model, products=[storey], relating_object=building)

    products = []
    circle_profile = model.create_entity(
        "IfcCircleProfileDef",
        ProfileType="AREA",
        ProfileName="CWS-R80",
        Radius=0.08,
    )
    for index in range(product_count):
        product = ifcopenshell.api.run(
            "root.create_entity",
            model,
            ifc_class="IfcBeam",
            name=f"Acceptance profile {index:04d}",
        )
        _set_guid(product, f"cws-full-acceptance/profile/{index:04d}")
        if index % 20 == 0:
            representation = ifcopenshell.api.run(
                "geometry.add_profile_representation",
                model,
                context=body,
                profile=circle_profile,
                depth=2.0,
            )
        else:
            representation = ifcopenshell.api.run(
                "geometry.add_wall_representation",
                model,
                context=body,
                length=2.0 + (index % 8) * 0.1,
                height=0.2,
                thickness=0.08,
            )
        ifcopenshell.api.run(
            "geometry.assign_representation",
            model,
            product=product,
            representation=representation,
        )
        placement = np.eye(4)
        placement[0, 3] = float(index % 40) * 3.2
        placement[1, 3] = float(index // 40) * 0.6
        placement[2, 3] = float(index % 5) * 0.25
        ifcopenshell.api.run(
            "geometry.edit_object_placement", model, product=product, matrix=placement
        )
        products.append(product)
    ifcopenshell.api.run(
        "spatial.assign_container", model, products=products, relating_structure=storey
    )
    model.write(str(source_path))

    session = ProjectSession.new("CWS Full Acceptance")
    try:
        registration = session.register_sources([source_path], include_step_geometry=False)[0]
        result = session.semantic_import_source(registration.source.source_id)
        if int(result.entity_counts.get("parts", 0)) != product_count:
            raise RuntimeError(f"Imported {result.entity_counts.get('parts', 0)} of {product_count} parts")
        session.save(project_path, embed_sources=True, user="full-acceptance")
    finally:
        session.close()

    payload = {
        "schema": "cws-full-acceptance-fixture-1.0",
        "status": "PASS",
        "fixture_class": "deterministic_redistributable_exact_ifc_project",
        "product_count": product_count,
        "project_path": str(project_path),
        "project_bytes": project_path.stat().st_size,
        "project_sha256": sha256(project_path.read_bytes()).hexdigest(),
        "source_path": str(source_path),
        "source_bytes": source_path.stat().st_size,
        "source_sha256": sha256(source_path.read_bytes()).hexdigest(),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-project", type=Path, required=True)
    parser.add_argument("--product-count", type=int, default=1000)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    payload = generate(args.output_project.expanduser(), product_count=args.product_count)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
