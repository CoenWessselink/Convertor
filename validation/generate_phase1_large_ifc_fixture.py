"""Generate a deterministic large IFC acceptance project through IfcOpenShell."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def generate(path: Path, *, product_count: int = 5000) -> dict[str, object]:
    import ifcopenshell
    import ifcopenshell.api

    if product_count < 1000:
        raise ValueError("product_count must be at least 1000 for the large-model gate")
    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run(
        "root.create_entity", model, ifc_class="IfcProject", name="CWS Large Acceptance Project"
    )
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
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="Building")
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Storey")
    ifcopenshell.api.run("aggregate.assign_object", model, products=[site], relating_object=project)
    ifcopenshell.api.run("aggregate.assign_object", model, products=[building], relating_object=site)
    ifcopenshell.api.run("aggregate.assign_object", model, products=[storey], relating_object=building)
    products = [
        ifcopenshell.api.run(
            "root.create_entity",
            model,
            ifc_class="IfcPlate",
            name=f"Acceptance plate {index:05d}",
        )
        for index in range(product_count)
    ]
    representation = ifcopenshell.api.run(
        "geometry.add_wall_representation",
        model,
        context=body,
        length=2.0,
        height=1.0,
        thickness=0.1,
    )
    ifcopenshell.api.run(
        "geometry.assign_representation",
        model,
        product=products[0],
        representation=representation,
    )
    ifcopenshell.api.run(
        "spatial.assign_container", model, products=products, relating_structure=storey
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(path))
    payload = {
        "schema": "cws-phase1-large-ifc-fixture-1.0",
        "fixture_class": "deterministic_redistributable_large_ifc",
        "product_count": product_count,
        "bytes": path.stat().st_size,
        "path": str(path.resolve()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--product-count", type=int, default=5000)
    args = parser.parse_args()
    generate(args.output.expanduser().resolve(), product_count=args.product_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
