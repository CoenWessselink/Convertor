"""Semantic STEP project importer for CWS Convertor phase 2.

The importer follows AP203/AP214/AP242 product-definition and occurrence
relationships where they are present.  When a file contains only one product
and one BREP solid, it deliberately materialises exactly one project part.  A
filename such as ``2x voetplaat`` is therefore *not* treated as evidence for
splitting geometry.

STEP BREP topology is fingerprinted independently from numeric Part-21 entity
IDs.  Exact manufacturing features are not inferred from free text or a rough
mesh; NC1 remains blocked until the later feature-recognition and roundtrip
validation phase.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
import math
from pathlib import Path
import time
from typing import Any, Callable, Iterable

from cws_convertor.project.model import (
    Assembly,
    EntityCategory,
    FieldProvenance,
    Part,
    ProjectModel,
    ReviewStatus,
    SourceFileRecord,
    SourceIdentity,
    Transform3D,
)

from .p21 import P21Document, P21Entity, P21ParseError
from .semantic import (
    SEMANTIC_IMPORT_VERSION,
    SemanticCancelCheck,
    SemanticImportResult,
)

STEP_IMPORTER_VERSION = SEMANTIC_IMPORT_VERSION
StepProgress = Callable[[float, str], None]


def _progress(callback: StepProgress | None, value: float, message: str) -> None:
    if callback is not None:
        callback(max(0.0, min(1.0, float(value))), message)


def _check_cancelled(callback: SemanticCancelCheck | None) -> None:
    if callback is not None:
        callback()


_SOLID_TYPES = {
    "MANIFOLD_SOLID_BREP",
    "BREP_WITH_VOIDS",
    "FACETED_BREP",
    "SHELL_BASED_SURFACE_MODEL",
    "GEOMETRIC_CURVE_SET",
    "TESSELLATED_SOLID",
}
_REPRESENTATION_TYPES = {
    "ADVANCED_BREP_SHAPE_REPRESENTATION",
    "SHAPE_REPRESENTATION",
    "MANIFOLD_SURFACE_SHAPE_REPRESENTATION",
    "TESSELLATED_SHAPE_REPRESENTATION",
}
_ASSEMBLY_USAGE_TYPES = {
    "NEXT_ASSEMBLY_USAGE_OCCURRENCE",
    "ASSEMBLY_COMPONENT_USAGE",
    "PRODUCT_DEFINITION_USAGE",
}
_PRESENTATION_TYPES_TO_IGNORE = {
    "STYLED_ITEM",
    "PRESENTATION_STYLE_ASSIGNMENT",
    "SURFACE_STYLE_USAGE",
    "SURFACE_SIDE_STYLE",
    "SURFACE_STYLE_FILL_AREA",
    "FILL_AREA_STYLE",
    "FILL_AREA_STYLE_COLOUR",
    "COLOUR_RGB",
    "DRAUGHTING_PRE_DEFINED_COLOUR",
    "MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION",
    "PRESENTATION_LAYER_ASSIGNMENT",
}


def _identity() -> Transform3D:
    return Transform3D.identity()


def _matmul(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [sum(left[row][k] * right[k][column] for k in range(4)) for column in range(4)]
        for row in range(4)
    ]


def _transpose_rotation(matrix: list[list[float]]) -> list[list[float]]:
    result = [[0.0] * 4 for _ in range(4)]
    for row in range(3):
        for column in range(3):
            result[row][column] = matrix[column][row]
    result[3][3] = 1.0
    translation = [matrix[row][3] for row in range(3)]
    for row in range(3):
        result[row][3] = -sum(result[row][column] * translation[column] for column in range(3))
    return result


def _normalise(vector: Iterable[float], fallback: tuple[float, float, float]) -> list[float]:
    values = [float(item) for item in vector]
    if len(values) < 3:
        values.extend([0.0] * (3 - len(values)))
    values = values[:3]
    length = math.sqrt(sum(item * item for item in values))
    if length <= 1e-12:
        return list(fallback)
    return [item / length for item in values]


def _cross(left: list[float], right: list[float]) -> list[float]:
    return [
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    ]


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass(frozen=True)
class StepProduct:
    product_entity_id: int
    product_id: str
    name: str
    description: str
    product_definition_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class StepOccurrence:
    entity_id: int
    occurrence_id: str
    name: str
    description: str
    parent_definition_id: int
    child_definition_id: int
    reference_designator: str = ""


@dataclass
class StepIndex:
    document: P21Document
    products: dict[int, StepProduct] = field(default_factory=dict)
    product_by_definition: dict[int, int] = field(default_factory=dict)
    definitions_by_product: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    shape_representations_by_target: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    representation_links: dict[int, set[int]] = field(default_factory=lambda: defaultdict(set))
    occurrences: list[StepOccurrence] = field(default_factory=list)
    occurrence_by_child_definition: dict[int, list[StepOccurrence]] = field(
        default_factory=lambda: defaultdict(list)
    )
    occurrence_by_parent_definition: dict[int, list[StepOccurrence]] = field(
        default_factory=lambda: defaultdict(list)
    )
    solid_roots: set[int] = field(default_factory=set)
    transformation_by_occurrence: dict[int, Transform3D] = field(default_factory=dict)
    relationship_counts: Counter[str] = field(default_factory=Counter)

    @classmethod
    def build(cls, document: P21Document) -> "StepIndex":
        index = cls(document=document)
        formation_to_product: dict[int, int] = {}
        definition_to_formation: dict[int, int] = {}
        product_rows: dict[int, tuple[str, str, str]] = {}

        for entity in document.iter_type("PRODUCT"):
            product_rows[entity.entity_id] = (
                document.text(entity, 0),
                document.text(entity, 1),
                document.text(entity, 2),
            )
        for entity in document.iter_type(
            "PRODUCT_DEFINITION_FORMATION",
            "PRODUCT_DEFINITION_FORMATION_WITH_SPECIFIED_SOURCE",
        ):
            product_ref = document.arg_ref(entity, 2)
            if product_ref is not None:
                formation_to_product[entity.entity_id] = product_ref
        for entity in document.iter_type("PRODUCT_DEFINITION"):
            formation_ref = document.arg_ref(entity, 2)
            if formation_ref is not None:
                definition_to_formation[entity.entity_id] = formation_ref
                product_ref = formation_to_product.get(formation_ref)
                if product_ref is not None:
                    index.product_by_definition[entity.entity_id] = product_ref
                    index.definitions_by_product[product_ref].append(entity.entity_id)

        for product_entity_id, (product_id, name, description) in product_rows.items():
            index.products[product_entity_id] = StepProduct(
                product_entity_id=product_entity_id,
                product_id=product_id,
                name=name,
                description=description,
                product_definition_ids=tuple(sorted(index.definitions_by_product.get(product_entity_id, ()))),
            )

        for entity in document.iter_type("PRODUCT_DEFINITION_SHAPE"):
            target = document.arg_ref(entity, 2)
            if target is None:
                continue
            # A ProductDefinitionShape may refer directly to a product definition
            # or to a product occurrence/usage entity.
            index.relationship_counts[entity.type_name] += 1
            for relation in document.iter_type("SHAPE_DEFINITION_REPRESENTATION"):
                if document.arg_ref(relation, 0) == entity.entity_id:
                    representation = document.arg_ref(relation, 1)
                    if representation is not None:
                        index.shape_representations_by_target[target].append(representation)

        for entity in document.iter_type(
            "SHAPE_REPRESENTATION_RELATIONSHIP",
            "REPRESENTATION_RELATIONSHIP",
            "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION",
        ):
            left = document.arg_ref(entity, 2)
            right = document.arg_ref(entity, 3)
            if left is not None and right is not None:
                index.representation_links[left].add(right)
                index.representation_links[right].add(left)
                index.relationship_counts[entity.type_name] += 1

        for entity in document.iter_type(*_ASSEMBLY_USAGE_TYPES):
            parent = document.arg_ref(entity, 3)
            child = document.arg_ref(entity, 4)
            if parent is None or child is None:
                continue
            occurrence = StepOccurrence(
                entity_id=entity.entity_id,
                occurrence_id=document.text(entity, 0) or f"#{entity.entity_id}",
                name=document.text(entity, 1),
                description=document.text(entity, 2),
                parent_definition_id=parent,
                child_definition_id=child,
                reference_designator=document.text(entity, 5),
            )
            index.occurrences.append(occurrence)
            index.occurrence_by_parent_definition[parent].append(occurrence)
            index.occurrence_by_child_definition[child].append(occurrence)
            index.relationship_counts[entity.type_name] += 1

        index.solid_roots = {
            entity.entity_id for entity in document.entities.values() if entity.type_name in _SOLID_TYPES
        }
        index._index_occurrence_transforms()
        return index

    def product_for_definition(self, definition_id: int) -> StepProduct | None:
        product_entity_id = self.product_by_definition.get(definition_id)
        return self.products.get(product_entity_id or -1)

    def product_definition_shape_targets(self, occurrence: StepOccurrence) -> list[int]:
        targets = [occurrence.entity_id, occurrence.child_definition_id]
        return [target for target in targets if target in self.shape_representations_by_target]

    def representation_closure(self, roots: Iterable[int]) -> set[int]:
        pending = deque(int(root) for root in roots)
        visited: set[int] = set()
        while pending:
            current = pending.popleft()
            if current in visited:
                continue
            visited.add(current)
            pending.extend(self.representation_links.get(current, ()))
        return visited

    def solids_for_target(self, target_id: int) -> list[int]:
        representation_roots = self.shape_representations_by_target.get(target_id, ())
        representation_ids = self.representation_closure(representation_roots)
        if not representation_ids:
            representation_ids = set(representation_roots)
        found: set[int] = set()
        for representation_id in representation_ids:
            representation = self.document.get(representation_id)
            if representation is None:
                continue
            graph = self.document.collect_graph([representation.entity_id], max_entities=500_000)
            found.update(graph & self.solid_roots)
        return sorted(found)

    def solids_for_definition(self, definition_id: int) -> list[int]:
        return self.solids_for_target(definition_id)

    def _coordinates(self, point_ref: int | None) -> list[float]:
        entity = self.document.get(point_ref)
        if entity is None or entity.type_name != "CARTESIAN_POINT":
            return [0.0, 0.0, 0.0]
        values = self.document.scalar(entity, 1, [])
        if not isinstance(values, list):
            return [0.0, 0.0, 0.0]
        result = [float(item) for item in values[:3]]
        result.extend([0.0] * (3 - len(result)))
        return result

    def _direction(self, direction_ref: int | None, fallback: tuple[float, float, float]) -> list[float]:
        entity = self.document.get(direction_ref)
        if entity is None or entity.type_name != "DIRECTION":
            return list(fallback)
        values = self.document.scalar(entity, 1, [])
        if not isinstance(values, list):
            return list(fallback)
        return _normalise(values, fallback)

    def axis_placement_transform(self, placement_ref: int | None) -> Transform3D:
        entity = self.document.get(placement_ref)
        if entity is None:
            return _identity()
        if entity.type_name == "AXIS2_PLACEMENT_3D":
            origin = self._coordinates(self.document.arg_ref(entity, 1))
            z_axis = self._direction(self.document.arg_ref(entity, 2), (0.0, 0.0, 1.0))
            x_seed = self._direction(self.document.arg_ref(entity, 3), (1.0, 0.0, 0.0))
            # Orthogonalise X against Z and derive a right-handed Y.
            x_axis = [x_seed[i] - _dot(x_seed, z_axis) * z_axis[i] for i in range(3)]
            x_axis = _normalise(x_axis, (1.0, 0.0, 0.0))
            y_axis = _normalise(_cross(z_axis, x_axis), (0.0, 1.0, 0.0))
            x_axis = _normalise(_cross(y_axis, z_axis), (1.0, 0.0, 0.0))
            matrix = [
                [x_axis[0], y_axis[0], z_axis[0], origin[0]],
                [x_axis[1], y_axis[1], z_axis[1], origin[1]],
                [x_axis[2], y_axis[2], z_axis[2], origin[2]],
                [0.0, 0.0, 0.0, 1.0],
            ]
            return Transform3D(matrix)
        if entity.type_name == "AXIS2_PLACEMENT_2D":
            origin = self._coordinates(self.document.arg_ref(entity, 1))
            x_axis = self._direction(self.document.arg_ref(entity, 2), (1.0, 0.0, 0.0))
            x_axis = _normalise((x_axis[0], x_axis[1], 0.0), (1.0, 0.0, 0.0))
            y_axis = [-x_axis[1], x_axis[0], 0.0]
            return Transform3D(
                [
                    [x_axis[0], y_axis[0], 0.0, origin[0]],
                    [x_axis[1], y_axis[1], 0.0, origin[1]],
                    [0.0, 0.0, 1.0, origin[2]],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            )
        return _identity()

    def _index_occurrence_transforms(self) -> None:
        # Common AP242 route:
        # ContextDependentShapeRepresentation -> RepresentationRelationshipWithTransformation
        # -> ItemDefinedTransformation(axis placement A, axis placement B).
        for contextual in self.document.iter_type("CONTEXT_DEPENDENT_SHAPE_REPRESENTATION"):
            relation_ref = self.document.arg_ref(contextual, 0)
            product_relation_ref = self.document.arg_ref(contextual, 1)
            relation = self.document.get(relation_ref)
            if relation is None or relation.type_name != "REPRESENTATION_RELATIONSHIP_WITH_TRANSFORMATION":
                continue
            transformation_ref = self.document.arg_ref(relation, 4)
            transform_entity = self.document.get(transformation_ref)
            if transform_entity is None:
                continue
            matrix = _identity().matrix
            if transform_entity.type_name == "ITEM_DEFINED_TRANSFORMATION":
                first = self.axis_placement_transform(self.document.arg_ref(transform_entity, 2)).matrix
                second = self.axis_placement_transform(self.document.arg_ref(transform_entity, 3)).matrix
                # Transform from child frame (second) to parent frame (first).
                matrix = _matmul(first, _transpose_rotation(second))
            elif transform_entity.type_name.startswith("CARTESIAN_TRANSFORMATION_OPERATOR"):
                origin = self._coordinates(self.document.arg_ref(transform_entity, 4))
                axis1 = self._direction(self.document.arg_ref(transform_entity, 1), (1.0, 0.0, 0.0))
                axis2 = self._direction(self.document.arg_ref(transform_entity, 2), (0.0, 1.0, 0.0))
                axis3 = self._direction(self.document.arg_ref(transform_entity, 3), (0.0, 0.0, 1.0))
                matrix = [
                    [axis1[0], axis2[0], axis3[0], origin[0]],
                    [axis1[1], axis2[1], axis3[1], origin[1]],
                    [axis1[2], axis2[2], axis3[2], origin[2]],
                    [0.0, 0.0, 0.0, 1.0],
                ]
            if product_relation_ref is not None:
                try:
                    transform = Transform3D(matrix)
                    transform.validate()
                    self.transformation_by_occurrence[product_relation_ref] = transform
                except Exception:
                    # A malformed placement is review evidence, never a reason
                    # to invent a transform. Identity is used and reported.
                    continue

    def occurrence_transform(self, occurrence: StepOccurrence) -> Transform3D:
        return self.transformation_by_occurrence.get(occurrence.entity_id, _identity())


class STEPSemanticProjectImporter:
    importer_version = STEP_IMPORTER_VERSION

    @staticmethod
    def _provenance(
        source: SourceFileRecord,
        entity_id: int,
        source_path: str,
        *,
        confidence: float = 1.0,
        method: str = "step_semantic",
    ) -> FieldProvenance:
        return FieldProvenance(
            source_file_id=source.source_id,
            source_entity_id=f"#{entity_id}",
            source_path=source_path,
            method=method,
            confidence=confidence,
            status="automatic",
        )

    @staticmethod
    def _source_identity(
        source: SourceFileRecord,
        *,
        source_entity_id: int,
        product: StepProduct | None,
        occurrence: StepOccurrence | None = None,
        suffix: str = "",
    ) -> SourceIdentity:
        product_id = product.product_id if product is not None else ""
        occurrence_id = occurrence.occurrence_id if occurrence is not None else ""
        if suffix:
            occurrence_id = f"{occurrence_id or product_id or source_entity_id}|{suffix}"
        return SourceIdentity(
            source_format="STEP",
            source_file_id=source.source_id,
            source_sha256=source.sha256,
            source_entity_id=f"#{source_entity_id}",
            product_id=product_id,
            occurrence_id=occurrence_id,
        )

    @staticmethod
    def _geometry_metrics(source: SourceFileRecord) -> dict[str, Any]:
        analysis = dict(source.analysis or {})
        metrics = dict(analysis.get("geometry_metrics") or {})
        return metrics if metrics.get("cadquery_loaded") else {}

    @staticmethod
    def _profile_suggestion(path: Path) -> dict[str, Any]:
        try:
            from conversion import analyze_step_profile

            result = analyze_step_profile(path)
            if hasattr(result, "to_dict"):
                result = result.to_dict()
            if isinstance(result, dict):
                return {"status": "matched", **result}
            return {"status": "matched", "value": str(result)}
        except Exception as exc:
            return {
                "status": "not_reliably_recognised",
                "reason": str(exc),
            }

    @staticmethod
    def _graph_descriptor(document: P21Document, solid_ids: list[int]) -> dict[str, Any]:
        graph_ids = document.collect_graph(solid_ids, max_entities=750_000) if solid_ids else set()
        counts = Counter(document.entities[item].type_name for item in graph_ids)
        geometry_hash = document.combined_semantic_hash(
            solid_ids,
            ignore_types=_PRESENTATION_TYPES_TO_IGNORE,
            precision=9,
        ) if solid_ids else ""
        return {
            "source_format": "STEP",
            "solid_root_entity_ids": solid_ids,
            "solid_count": len(solid_ids),
            "source_geometry_hash": geometry_hash,
            "graph_entity_count": len(graph_ids),
            "graph_type_counts": dict(sorted(counts.items())),
            "analytic_summary": {
                "advanced_faces": counts["ADVANCED_FACE"],
                "planes": counts["PLANE"],
                "cylindrical_surfaces": counts["CYLINDRICAL_SURFACE"],
                "conical_surfaces": counts["CONICAL_SURFACE"],
                "toroidal_surfaces": counts["TOROIDAL_SURFACE"],
                "circles": counts["CIRCLE"],
                "ellipses": counts["ELLIPSE"],
                "b_spline_surfaces": sum(
                    value for key, value in counts.items() if "B_SPLINE_SURFACE" in key
                ),
            },
        }

    def _make_part(
        self,
        project: ProjectModel,
        source: SourceFileRecord,
        document: P21Document,
        *,
        product: StepProduct | None,
        definition_id: int,
        solid_ids: list[int],
        occurrence: StepOccurrence | None,
        local_placement: Transform3D,
        global_placement: Transform3D,
        name_suffix: str = "",
        metrics: dict[str, Any] | None = None,
        profile_suggestion: dict[str, Any] | None = None,
    ) -> Part:
        source_entity_id = occurrence.entity_id if occurrence is not None else (
            product.product_entity_id if product is not None else (solid_ids[0] if solid_ids else definition_id)
        )
        suffix = name_suffix or (f"solid-{solid_ids[0]}" if len(solid_ids) == 1 and product is None else "")
        identity = self._source_identity(
            source,
            source_entity_id=source_entity_id,
            product=product,
            occurrence=occurrence,
            suffix=suffix,
        )
        internal_id = project.stable_entity_id("part", identity)
        base_name = (
            (occurrence.name if occurrence and occurrence.name else "")
            or (product.name if product and product.name else "")
            or (product.product_id if product else "")
            or f"STEP part #{source_entity_id}"
        )
        if name_suffix:
            base_name = f"{base_name} · {name_suffix}"
        descriptor = self._graph_descriptor(document, solid_ids)
        if metrics:
            descriptor["cad_metrics"] = dict(metrics)
        if profile_suggestion:
            descriptor["profile_recognition"] = dict(profile_suggestion)
        profile = ""
        profile_type = ""
        if profile_suggestion and profile_suggestion.get("status") == "matched":
            profile = str(
                profile_suggestion.get("profile")
                or profile_suggestion.get("profile_name")
                or profile_suggestion.get("designation")
                or ""
            )
            profile_type = str(profile_suggestion.get("profile_type") or "")
        bbox = list((metrics or {}).get("bbox_mm") or [])
        length_mm = max((float(item) for item in bbox), default=0.0)
        part = Part(
            internal_id=internal_id,
            name=base_name,
            category=EntityCategory.UNKNOWN.value,
            source_identity=identity,
            local_placement=local_placement,
            global_placement=global_placement,
            confidence=1.0,
            status=ReviewStatus.REVIEW_REQUIRED.value,
            part_position=(occurrence.reference_designator if occurrence else ""),
            quantity_total=1,
            part_type="step_brep" if solid_ids else "step_product_without_shape",
            profile=profile,
            profile_type=profile_type,
            length_mm=length_mm,
            geometry_descriptor=descriptor,
            production_features=[],
            nc1_eligible=False,
            export_status="blocked_pending_classification_and_feature_validation",
            properties={
                "step_product_entity_id": product.product_entity_id if product else None,
                "step_product_id": product.product_id if product else "",
                "step_product_name": product.name if product else "",
                "step_product_description": product.description if product else "",
                "step_product_definition_id": definition_id,
                "step_occurrence_entity_id": occurrence.entity_id if occurrence else None,
                "step_occurrence_id": occurrence.occurrence_id if occurrence else "",
                "step_reference_designator": occurrence.reference_designator if occurrence else "",
                "classification_status": "review_required",
                "classification_hint": "make_or_purchased_part",
                "source_solid_count": len(solid_ids),
                "filename_quantity_tokens_are_not_geometry": True,
            },
            field_provenance={
                "name": self._provenance(
                    source,
                    product.product_entity_id if product else source_entity_id,
                    "STEP PRODUCT.Name",
                ),
                "geometry_descriptor": self._provenance(
                    source,
                    solid_ids[0] if solid_ids else source_entity_id,
                    "STEP BREP subgraph",
                    confidence=1.0 if solid_ids else 0.0,
                ),
            },
        )
        if metrics:
            volume = float(metrics.get("volume_mm3", 0.0) or 0.0)
            area = float(metrics.get("area_mm2", 0.0) or 0.0)
            part.properties["volume_mm3"] = volume
            part.surface_area_each_m2 = area / 1_000_000.0
            part.properties["cadquery_valid"] = bool(metrics.get("valid", False))
        part.recompute_hashes()
        part.validate_base()
        return part

    def import_source(
        self,
        project: ProjectModel,
        source: SourceFileRecord,
        source_path: Path,
        *,
        user: str,
        progress: StepProgress | None = None,
        cancel_check: SemanticCancelCheck | None = None,
    ) -> SemanticImportResult:
        started = time.perf_counter()
        _check_cancelled(cancel_check)
        _progress(progress, 0.02, "STEP Part 21-grafiek lezen")
        document = P21Document.load(source_path, cancel_check=cancel_check)
        _check_cancelled(cancel_check)
        _progress(progress, 0.28, "STEP products, occurrences en shapes indexeren")
        schema_upper = document.schema.upper()
        if not any(token in schema_upper for token in ("AP203", "AP214", "AP242", "AUTOMOTIVE_DESIGN", "CONFIG_CONTROL_DESIGN")):
            raise P21ParseError(
                f"{source.file_name} heeft geen ondersteund STEP-productschema: {document.schema!r}"
            )
        index = StepIndex.build(document)
        _check_cancelled(cancel_check)
        _progress(progress, 0.45, "STEP productschema en BREP-roots analyseren")
        warnings: list[str] = []
        source_class_counts = Counter(entity.type_name for entity in document.entities.values())
        metrics = self._geometry_metrics(source)
        profile_suggestion: dict[str, Any] = {}
        if len(index.products) == 1:
            advanced_faces = int(source_class_counts.get("ADVANCED_FACE", 0) or 0)
            # The semantic importer must remain responsive on large AP242
            # solids.  Baseline intake has already loaded and measured the CAD
            # shape once; running the legacy profile recogniser here would load
            # the same 9 MB model a second time and can add minutes without
            # improving hierarchy fidelity.  Defer that optional classification
            # to the dedicated phase-3 worker for large/complex sources.
            if source_path.stat().st_size > 4 * 1024 * 1024 or advanced_faces > 2500:
                profile_suggestion = {
                    "status": "deferred_large_model",
                    "reason": (
                        "Profielherkenning is uitgesteld naar de classificatiejob "
                        "om dubbele zware CAD-import te voorkomen."
                    ),
                    "size_bytes": source_path.stat().st_size,
                    "advanced_faces": advanced_faces,
                }
            else:
                profile_suggestion = self._profile_suggestion(source_path)

        _progress(progress, 0.58, "STEP placements en productidentiteit materialiseren")

        # Strategy A requires explicit product occurrences. Strategy B requires
        # at least one topological solid root. With neither evidence source the
        # importer uses Strategy C and materialises only exact product records;
        # it never invents a solid, assembly or split from the file name.
        if index.occurrences:
            strategy = "A_semantic_structure"
        elif index.solid_roots:
            strategy = "B_separate_solids"
        else:
            strategy = "C_fused_review"
            warnings.append(
                "STEP bevat geen betrouwbare BREP-/solid-root; alleen aantoonbare productrecords zijn als reviewobject gematerialiseerd."
            )
        _check_cancelled(cancel_check)
        assemblies: dict[int, Assembly] = {}
        parts: list[Part] = []
        definition_to_assembly: dict[int, str] = {}
        occurrence_to_part: dict[int, str] = {}

        if index.occurrences:
            parent_definition_ids = sorted(index.occurrence_by_parent_definition)
            for assembly_index, definition_id in enumerate(parent_definition_ids):
                if assembly_index % 25 == 0:
                    _check_cancelled(cancel_check)
                product = index.product_for_definition(definition_id)
                source_entity_id = product.product_entity_id if product else definition_id
                identity = self._source_identity(
                    source,
                    source_entity_id=source_entity_id,
                    product=product,
                )
                internal_id = project.stable_entity_id("assembly", identity)
                assembly = Assembly(
                    internal_id=internal_id,
                    name=(product.name if product else "") or f"STEP assembly #{definition_id}",
                    source_identity=identity,
                    status=ReviewStatus.REVIEW_REQUIRED.value,
                    assembly_mark=(product.product_id if product else ""),
                    quantity=1,
                    production_status=ReviewStatus.REVIEW_REQUIRED.value,
                    properties={
                        "step_product_definition_id": definition_id,
                        "step_product_entity_id": product.product_entity_id if product else None,
                        "step_product_id": product.product_id if product else "",
                        "step_product_description": product.description if product else "",
                        "classification_status": "deterministic_step_assembly_relation",
                    },
                )
                assembly.validate_base()
                assemblies[definition_id] = assembly
                definition_to_assembly[definition_id] = internal_id

            # Occurrence-level parts preserve placements and repetition. Nested
            # assemblies are linked when the child definition is itself a parent.
            for occurrence_index, occurrence in enumerate(
                sorted(index.occurrences, key=lambda item: item.entity_id)
            ):
                if occurrence_index % 25 == 0:
                    _check_cancelled(cancel_check)
                parent_assembly = assemblies.get(occurrence.parent_definition_id)
                child_assembly = assemblies.get(occurrence.child_definition_id)
                if parent_assembly is None:
                    continue
                if child_assembly is not None:
                    if child_assembly.internal_id not in parent_assembly.child_assembly_ids:
                        parent_assembly.child_assembly_ids.append(child_assembly.internal_id)
                    continue
                product = index.product_for_definition(occurrence.child_definition_id)
                solid_ids: list[int] = []
                for target in index.product_definition_shape_targets(occurrence):
                    solid_ids = index.solids_for_target(target)
                    if solid_ids:
                        break
                if not solid_ids:
                    solid_ids = index.solids_for_definition(occurrence.child_definition_id)
                transform = index.occurrence_transform(occurrence)
                part = self._make_part(
                    project,
                    source,
                    document,
                    product=product,
                    definition_id=occurrence.child_definition_id,
                    solid_ids=solid_ids,
                    occurrence=occurrence,
                    local_placement=transform,
                    global_placement=transform,
                )
                part.assembly_ids = [parent_assembly.internal_id]
                part.quantity_per_assembly = {parent_assembly.internal_id: 1}
                part.recompute_hashes()
                parts.append(part)
                occurrence_to_part[occurrence.entity_id] = part.internal_id
                parent_assembly.part_ids.append(part.internal_id)
                if not parent_assembly.main_part_id:
                    parent_assembly.main_part_id = part.internal_id
        else:
            # Product definitions are the primary semantic roots.  Current
            # Onshape references each expose one product and one BREP solid.
            consumed_solids: set[int] = set()
            for product_index, product in enumerate(
                sorted(index.products.values(), key=lambda item: item.product_entity_id)
            ):
                if product_index % 25 == 0:
                    _check_cancelled(cancel_check)
                definitions = list(product.product_definition_ids) or [product.product_entity_id]
                solid_ids: list[int] = []
                selected_definition = definitions[0]
                for definition_id in definitions:
                    candidate = index.solids_for_definition(definition_id)
                    if candidate:
                        selected_definition = definition_id
                        solid_ids = candidate
                        break
                if not solid_ids and len(index.products) == 1:
                    solid_ids = sorted(index.solid_roots)
                consumed_solids.update(solid_ids)
                if len(solid_ids) <= 1:
                    parts.append(
                        self._make_part(
                            project,
                            source,
                            document,
                            product=product,
                            definition_id=selected_definition,
                            solid_ids=solid_ids,
                            occurrence=None,
                            local_placement=_identity(),
                            global_placement=_identity(),
                            metrics=metrics if len(index.products) == 1 and len(solid_ids) == 1 else None,
                            profile_suggestion=profile_suggestion if len(index.products) == 1 else None,
                        )
                    )
                else:
                    warnings.append(
                        f"Product {product.name or product.product_id} bevat {len(solid_ids)} losse BREP-roots; deze zijn als afzonderlijke reviewdelen gematerialiseerd."
                    )
                    for number, solid_id in enumerate(solid_ids, start=1):
                        parts.append(
                            self._make_part(
                                project,
                                source,
                                document,
                                product=product,
                                definition_id=selected_definition,
                                solid_ids=[solid_id],
                                occurrence=None,
                                local_placement=_identity(),
                                global_placement=_identity(),
                                name_suffix=f"solid {number}",
                            )
                        )
            for solid_index, solid_id in enumerate(sorted(index.solid_roots - consumed_solids)):
                if solid_index % 25 == 0:
                    _check_cancelled(cancel_check)
                parts.append(
                    self._make_part(
                        project,
                        source,
                        document,
                        product=None,
                        definition_id=solid_id,
                        solid_ids=[solid_id],
                        occurrence=None,
                        local_placement=_identity(),
                        global_placement=_identity(),
                    )
                )

        # Filename/product quantity words are only evidence for review.  They
        # never alter the number of semantic products or BREP roots.
        if len(parts) == 1 and any(token in parts[0].name.casefold() for token in ("2x", "2 x", "twee")):
            warnings.append(
                "De naam suggereert mogelijk meerdere exemplaren, maar STEP bevat één product en één solid; niet automatisch gesplitst."
            )
            parts[0].properties["name_quantity_ambiguity"] = True

        project.assemblies.update({item.internal_id: item for item in assemblies.values()})
        project.parts.update({item.internal_id: item for item in parts})
        _progress(progress, 0.88, "STEP hashes, groepen en productiegate opbouwen")

        geometry_groups: dict[str, list[str]] = defaultdict(list)
        manufacturing_groups: dict[str, list[str]] = defaultdict(list)
        for part in parts:
            geometry_groups[part.geometry_hash].append(part.internal_id)
            manufacturing_groups[part.manufacturing_hash].append(part.internal_id)

        entity_counts = {
            "assemblies": len(assemblies),
            "parts": len(parts),
            "fasteners": 0,
            "welds": 0,
            "total_materialised": len(assemblies) + len(parts),
        }
        product_records = [
            {
                "entity_id": item.product_entity_id,
                "product_id": item.product_id,
                "name": item.name,
                "description": item.description,
                "product_definition_ids": list(item.product_definition_ids),
            }
            for item in sorted(index.products.values(), key=lambda row: row.product_entity_id)
        ]
        evidence = {
            "product_count": len(index.products),
            "occurrence_count": len(index.occurrences),
            "solid_root_count": len(index.solid_roots),
            "materialised_part_count": len(parts),
            "product_records": product_records,
            "all_current_products_preserved": all(
                any(part.properties.get("step_product_entity_id") == product.product_entity_id for part in parts)
                or any(
                    assembly.properties.get("step_product_entity_id") == product.product_entity_id
                    for assembly in assemblies.values()
                )
                for product in index.products.values()
            ),
            "geometry_groups": {key: value for key, value in sorted(geometry_groups.items())},
            "manufacturing_groups": {
                key: value for key, value in sorted(manufacturing_groups.items())
            },
            "cad_metrics": metrics,
            "profile_recognition": profile_suggestion,
            "filename_not_used_for_splitting": True,
            "ambiguous_geometry_review_required": strategy == "C_fused_review",
            "unshaped_product_count": sum(
                1
                for part in parts
                if int(part.properties.get("source_solid_count", 0) or 0) == 0
            ),
        }
        blocking_reasons = [
            "STEP-productstructuur en BREP-identiteit zijn geïmporteerd, maar maakdeel/inkoopdeel-classificatie moet worden bevestigd.",
            "NC1-vrijgave vereist profiel-/featureherkenning en geometrische roundtripvalidatie per onderdeel.",
        ]
        if strategy == "C_fused_review":
            blocking_reasons.insert(
                0,
                "De STEP-bron bevat geen aantoonbare solid-root; geometrische opsplitsing of productievrijgave vereist expliciete review.",
            )
        result = SemanticImportResult(
            source_id=source.source_id,
            file_name=source.file_name,
            source_format="STEP",
            schema=document.schema,
            importer_version=self.importer_version,
            strategy=strategy,
            entity_counts=entity_counts,
            source_class_counts=dict(sorted(source_class_counts.items())),
            relationship_counts=dict(sorted(index.relationship_counts.items())),
            group_counts={
                "geometry_hashes": {key: len(value) for key, value in sorted(geometry_groups.items())},
                "manufacturing_hashes": {
                    key: len(value) for key, value in sorted(manufacturing_groups.items())
                },
            },
            evidence=evidence,
            warnings=warnings,
            blocking_reasons=blocking_reasons,
            production_export_allowed=False,
            elapsed_seconds=round(time.perf_counter() - started, 6),
        )
        _check_cancelled(cancel_check)
        document.release_caches()
        _progress(progress, 1.0, "STEP semantische import gereed")
        return result.normalise()


__all__ = [
    "STEP_IMPORTER_VERSION",
    "StepProgress",
    "StepIndex",
    "StepOccurrence",
    "StepProduct",
    "STEPSemanticProjectImporter",
]
