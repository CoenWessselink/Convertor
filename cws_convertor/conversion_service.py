"""Central, fail-closed conversion planning and execution authority.

All NC1/STEP/IFC/PDF cross-format routes are registered here.  Legacy modules
remain physical serializers; UI, workers and compatibility entry points ask
this service for target-specific preflight before any artifact is written.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any, Callable, Iterable, Mapping, Sequence


PLANNER_VERSION = "cws-conversion-planner-v2"
EVIDENCE_SCHEMA = "cws.conversion.evidence.v2"
BATCH_SCHEMA = "cws.conversion.batch.v2"
FORMATS = ("NC1", "STEP", "IFC", "PDF")


class ConversionStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    SUPPORTED_WITH_LIMITS = "SUPPORTED_WITH_LIMITS"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class ConversionScope(str, Enum):
    PART = "part"
    PART_SPLIT = "part_split"
    ASSEMBLY_PACKAGE = "assembly_package"


@dataclass(frozen=True, slots=True)
class ConversionRoute:
    source_format: str
    target_format: str
    direction: str
    serializer: str
    reimport_validator: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _route(source: str, target: str) -> ConversionRoute:
    direction = f"{source.lower()}-{target.lower()}"
    return ConversionRoute(
        source_format=source,
        target_format=target,
        direction=direction,
        serializer=f"serializer:{direction}",
        reimport_validator=f"reimport:{target.lower()}",
    )


ROUTES = tuple(
    _route(source, target)
    for source in FORMATS
    for target in FORMATS
    if source != target
)
ROUTE_BY_DIRECTION = {item.direction: item for item in ROUTES}
ROUTE_BY_PAIR = {(item.source_format, item.target_format): item for item in ROUTES}


@dataclass(slots=True)
class ConversionSource:
    source_path: str
    source_format: str
    source_sha256: str
    scope: str = ConversionScope.PART.value
    exact_source: bool = False
    trusted_payload: bool = False
    part_form: str = ""
    features: tuple[str, ...] = ()
    solid_count: int = 0
    product_count: int = 1
    part_ids: tuple[str, ...] = ()
    assembly_ids: tuple[str, ...] = ()
    identity_relations: tuple[tuple[str, str], ...] = ()
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    mgi: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConversionPlan:
    plan_id: str
    planner_version: str
    route: ConversionRoute
    source: ConversionSource
    status: ConversionStatus
    scope: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    supported_features: tuple[str, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    proof_requirements: tuple[str, ...] = (
        "serializer",
        "physical_reimport",
        "geometry_compare",
        "semantic_compare",
        "evidence_reopen",
    )

    @property
    def executable(self) -> bool:
        return self.status in {
            ConversionStatus.SUPPORTED,
            ConversionStatus.SUPPORTED_WITH_LIMITS,
        }

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(slots=True)
class ConversionExecution:
    status: str
    source: str
    direction: str
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    evidence_path: str = ""
    plan: dict[str, Any] = field(default_factory=dict)
    proofs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalise_format(value: str | Path) -> str:
    text = str(value or "").strip().upper().lstrip(".")
    return {
        "NC": "NC1",
        "DSTV": "NC1",
        "STP": "STEP",
    }.get(text, text)


def normalise_direction(value: str) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("dstv", "nc1").replace("→", "-").replace("->", "-")
    text = text.replace("_", "-").replace("/", "-").replace(" ", "")
    text = text.replace("to", "-")
    while "--" in text:
        text = text.replace("--", "-")
    text = text.strip("-")
    if text == "nc-step":
        text = "nc1-step"
    return text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item) for item in values if str(item)))


def _canonical_features(part: Any) -> tuple[str, ...]:
    result: list[str] = []
    for contour in list(getattr(part, "contours", ()) or ()):
        result.append("inner_contour" if str(getattr(contour, "kind", "")).upper() == "IK" else "outer_contour")
        for point in list(getattr(contour, "points", ()) or ()):
            if abs(float(getattr(point, "radius", 0.0) or 0.0)) > 1e-9:
                result.append("contour_radius")
            if str(getattr(point, "notch", "") or ""):
                result.append("notch")
    for hole in list(getattr(part, "holes", ()) or ()):
        operation = str(getattr(hole, "operation", "") or "").lower()
        depth = float(getattr(hole, "depth", 0.0) or 0.0)
        if depth > 0:
            result.append("blind_hole")
        elif operation == "l":
            result.append("slot")
        elif operation == "g":
            result.append("countersink")
        elif operation == "m":
            result.append("counterbore")
        elif operation:
            result.append(f"hole_operation:{operation}")
        else:
            result.append("hole")
    result.extend(f"unsupported_block:{item}" for item in list(getattr(part, "unsupported_blocks", ()) or ()))
    return _unique(result)


def _workbench_features(part: Any) -> tuple[str, ...]:
    workbench = getattr(part, "workbench", {}) or {}
    revision = workbench.get("current_revision") if isinstance(workbench, Mapping) else {}
    result: list[str] = []
    if isinstance(revision, Mapping):
        for feature in list(revision.get("features") or []):
            if not isinstance(feature, Mapping):
                result.append("unknown")
                continue
            kind = str(feature.get("kind") or "unknown").strip().lower().replace("-", "_")
            parameters = dict(feature.get("parameters") or {})
            if kind == "hole" and not bool(parameters.get("through", True)):
                kind = "blind_hole"
            result.append(kind)
        for contour in list(revision.get("contours") or []):
            if isinstance(contour, Mapping):
                result.append("inner_contour" if contour.get("role") == "inner" else "outer_contour")
    if not result:
        for feature in list(getattr(part, "production_features", ()) or ()):
            if isinstance(feature, Mapping):
                result.append(str(feature.get("kind") or "unknown").lower())
    return _unique(result)


class ConversionPlanner:
    """Inspect sources and produce one target-specific, immutable plan."""

    def inspect_file(self, source_path: str | Path) -> ConversionSource:
        path = Path(source_path).expanduser().resolve()
        if not path.is_file():
            return ConversionSource(
                str(path), "", "", blockers=("SOURCE_FILE_NOT_FOUND",)
            )
        source_format = normalise_format(path.suffix)
        sha256 = _sha256_file(path)
        if source_format not in FORMATS:
            return ConversionSource(
                str(path), source_format, sha256, blockers=("UNSUPPORTED_SOURCE_FORMAT",)
            )
        try:
            if source_format == "NC1":
                return self._inspect_nc1(path, sha256)
            if source_format == "STEP":
                return self._inspect_step(path, sha256)
            if source_format == "IFC":
                return self._inspect_ifc(path, sha256)
            return self._inspect_pdf(path, sha256)
        except Exception as exc:
            return ConversionSource(
                str(path),
                source_format,
                sha256,
                blockers=(f"SOURCE_INSPECTION_FAILED:{type(exc).__name__}:{exc}",),
            )

    def _inspect_nc1(self, path: Path, sha256: str) -> ConversionSource:
        import converter
        from canonical_model import extract_part_from_nc1

        parsed = converter.parse_nc1(path)
        canonical = extract_part_from_nc1(path, strict=False)
        features = list(_canonical_features(parsed))
        if parsed.numberings:
            features.append("marking")
        if parsed.surface_marks:
            features.append("scribing")
        part_form = "plate" if parsed.header.profile_type == "B" else "profile"
        return ConversionSource(
            str(path),
            "NC1",
            sha256,
            exact_source=True,
            trusted_payload=canonical is not None,
            part_form=part_form,
            features=_unique(features),
            solid_count=1,
            part_ids=(parsed.header.position_number or parsed.header.part_number or path.stem,),
            warnings=tuple(parsed.warnings),
            metadata={
                "profile": parsed.header.profile,
                "profile_type": parsed.header.profile_type,
                "material": parsed.header.material,
                "quantity": parsed.header.quantity,
            },
        )

    def _inspect_step(self, path: Path, sha256: str) -> ConversionSource:
        from canonical_model import extract_part_from_step
        from cws_convertor.importers.p21 import P21Document
        from cws_convertor.importers.step_project import StepIndex

        document = P21Document.load(path)
        index = StepIndex.build(document)
        canonical = extract_part_from_step(path, strict=False)
        solid_count = len(index.solid_roots)
        exact_types = {"MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS"}
        root_types = {
            document.entities[item].type_name
            for item in index.solid_roots
            if item in document.entities
        }
        exact = bool(solid_count and root_types.issubset(exact_types))
        products = tuple(
            item.product_id or item.name or f"#{item.product_entity_id}"
            for item in index.products.values()
        )
        relations = tuple(
            (
                str(item.parent_definition_id),
                str(item.child_definition_id),
            )
            for item in index.occurrences
        )
        scope = (
            ConversionScope.ASSEMBLY_PACKAGE.value
            if index.occurrences
            else ConversionScope.PART_SPLIT.value
            if solid_count > 1
            else ConversionScope.PART.value
        )
        features = _canonical_features(canonical) if canonical is not None else ()
        source = ConversionSource(
            str(path),
            "STEP",
            sha256,
            scope=scope,
            exact_source=exact,
            trusted_payload=canonical is not None,
            part_form=(
                "plate"
                if canonical is not None and canonical.header.profile_type.upper() == "B"
                else "profile"
                if canonical is not None and canonical.header.profile_type
                else ""
            ),
            features=features,
            solid_count=solid_count,
            product_count=max(1, len(products)),
            part_ids=products,
            assembly_ids=tuple(item.occurrence_id for item in index.occurrences),
            identity_relations=relations,
            warnings=("STEP_MULTI_SOLID_SCOPE_REQUIRED",) if solid_count > 1 else (),
            blockers=("STEP_CONTAINS_NO_SOLID_ROOT",) if solid_count < 1 else (),
            metadata={"schema": document.schema, "root_types": sorted(root_types)},
        )
        if exact and solid_count == 1 and canonical is None:
            source.mgi = self._mgi_for_step(path, source)
        return source

    def _inspect_ifc(self, path: Path, sha256: str) -> ConversionSource:
        from canonical_model import extract_part_from_ifc
        from cws_convertor.importers.p21 import P21Document

        document = P21Document.load(path)
        if "IFC" not in document.schema.upper():
            raise ValueError("FILE_SCHEMA is geen IFC-schema")
        canonical = extract_part_from_ifc(path, strict=False)
        product_types = {
            "IFCBEAM", "IFCCOLUMN", "IFCMEMBER", "IFCPLATE", "IFCFOOTING",
            "IFCSTAIRFLIGHT", "IFCBUILDINGELEMENTPROXY", "IFCMECHANICALFASTENER",
        }
        product_ids = tuple(
            f"#{entity.entity_id}"
            for entity in document.entities.values()
            if entity.type_name in product_types
        )
        assembly_ids = tuple(
            f"#{entity.entity_id}"
            for entity in document.entities.values()
            if entity.type_name == "IFCELEMENTASSEMBLY"
        )
        relations: list[tuple[str, str]] = []
        for entity in document.iter_type("IFCRELAGGREGATES", "IFCRELNESTS"):
            parent = document.arg_ref(entity, 4)
            for child in document.arg_refs(entity, 5):
                if parent is not None:
                    relations.append((f"#{parent}", f"#{child}"))
        exact_solid_types = {"IFCEXTRUDEDAREASOLID", "IFCFACETEDBREP", "IFCADVANCEDBREP"}
        exact_count = sum(len(tuple(document.iter_type(item))) for item in exact_solid_types)
        tessellated = sum(len(tuple(document.iter_type(item))) for item in ("IFCTRIANGULATEDFACESET", "IFCPOLYGONALFACESET"))
        scope = ConversionScope.ASSEMBLY_PACKAGE.value if assembly_ids or relations else ConversionScope.PART_SPLIT.value if len(product_ids) > 1 else ConversionScope.PART.value
        return ConversionSource(
            str(path),
            "IFC",
            sha256,
            scope=scope,
            exact_source=bool(canonical is not None or (exact_count and not tessellated)),
            trusted_payload=canonical is not None,
            part_form=(
                "plate"
                if canonical is not None and canonical.header.profile_type.upper() == "B"
                else "profile"
                if canonical is not None and canonical.header.profile_type
                else ""
            ),
            features=_canonical_features(canonical) if canonical is not None else (),
            solid_count=max(exact_count, len(product_ids)),
            product_count=max(1, len(product_ids)),
            part_ids=product_ids,
            assembly_ids=assembly_ids,
            identity_relations=tuple(relations),
            warnings=("IFC_ASSEMBLY_IDENTITIES_RETAINED_IN_EVIDENCE_MANIFEST",) if scope == ConversionScope.ASSEMBLY_PACKAGE.value else (),
            blockers=("IFC_HAS_NO_CONVERTIBLE_PRODUCT",) if not product_ids and canonical is None else (),
            metadata={"schema": document.schema, "exact_item_count": exact_count, "tessellated_item_count": tessellated},
        )

    def _inspect_pdf(self, path: Path, sha256: str) -> ConversionSource:
        from pdf_support import load_trusted_pdf

        try:
            analysis = load_trusted_pdf(path, strict=True)
        except Exception as exc:
            return ConversionSource(
                str(path),
                "PDF",
                sha256,
                trusted_payload=False,
                blockers=("EXTERNAL_PDF_REVIEW_REQUIRED",),
                warnings=(f"TRUSTED_PDF_NOT_PROVEN:{type(exc).__name__}",),
            )
        canonical = analysis.part
        return ConversionSource(
            str(path),
            "PDF",
            sha256,
            exact_source=True,
            trusted_payload=True,
            part_form="plate" if canonical.header.profile_type.upper() == "B" else "profile",
            features=_canonical_features(canonical),
            solid_count=1,
            part_ids=(canonical.part_id or path.stem,),
            metadata={
                "canonical_sha256": analysis.details.get("manifest", {}).get("canonical_sha256", ""),
                "visible_sha256": analysis.details.get("manifest", {}).get("visible_sha256", ""),
                "production_export_allowed": bool(analysis.production_export_allowed),
            },
        )

    def _mgi_for_step(self, path: Path, source: ConversionSource) -> dict[str, Any]:
        try:
            import cadquery as cq
            from cws_convertor.manufacturing_interpreter import (
                ManufacturingGeometryInterpreter,
                ManufacturingInterpretationRequest,
            )
            from cws_convertor.project.canonical_rebuild import canonical_shape_metrics
            from cws_convertor.project.source_geometry import SourceGeometryInspection

            shape = cq.importers.importStep(str(path)).val()
            metrics = canonical_shape_metrics(shape)
            inspection = SourceGeometryInspection(
                part_id=path.stem,
                source_file_id=path.name,
                source_sha256=source.source_sha256,
                source_geometry_hash=_stable_hash(metrics),
                status="resolved_exact",
                scope="single_part",
                geometry_kind="step_brep",
                selection_verified=True,
                production_geometry_exact=True,
                metrics=metrics,
                native_shape=shape,
            )
            report = ManufacturingGeometryInterpreter().analyze(
                ManufacturingInterpretationRequest(
                    inspection=inspection,
                    requested_outputs=("NC1", "IFC", "STEP", "PDF"),
                )
            )
            representability = {
                item.target: item.status.value
                for item in getattr(getattr(report, "representability_report", None), "targets", ())
            }
            return {
                "report_hash": report.semantic_sha256,
                "readiness": report.readiness.value,
                "equivalence": report.equivalence.status.value,
                "blockers": list(report.blockers),
                "features": [item.semantic_type.value.lower() for item in report.features],
                "representability": representability,
                "authority": "ManufacturingGeometryInterpreter",
            }
        except Exception as exc:
            return {
                "readiness": "BLOCKED",
                "blockers": [f"MGI_EXECUTION_FAILED:{type(exc).__name__}:{exc}"],
                "authority": "ManufacturingGeometryInterpreter",
            }

    def source_from_project_part(
        self,
        part: Any,
        inspection: Any,
        *,
        project_path: str | Path,
    ) -> ConversionSource:
        source_format = normalise_format(getattr(part.source_identity, "source_format", ""))
        features = _workbench_features(part)
        metadata = {
            "project_path": str(Path(project_path).resolve()),
            "project_part_id": str(part.internal_id),
            "workbench_available": bool(getattr(part, "workbench", {})),
            "manufacturing_hash": str(getattr(part, "manufacturing_hash", "")),
            "assembly_ids": list(getattr(part, "assembly_ids", ()) or ()),
            "part_position": str(getattr(part, "part_position", "") or ""),
            "source_metrics": dict(getattr(inspection, "metrics", {}) or {}),
        }
        source = ConversionSource(
            source_path=str(Path(project_path).resolve()),
            source_format=source_format,
            source_sha256=str(getattr(inspection, "source_sha256", "") or ""),
            exact_source=bool(
                getattr(inspection, "production_geometry_exact", False)
                and getattr(inspection, "selection_verified", False)
                and getattr(inspection, "native_shape", None) is not None
            ),
            trusted_payload=bool(getattr(part, "canonical_part", None)),
            part_form=str(
                ((getattr(part, "workbench", {}) or {}).get("current_revision") or {}).get("part_form")
                or getattr(part, "part_type", "")
                or ""
            ).lower(),
            features=features,
            solid_count=int((getattr(inspection, "metrics", {}) or {}).get("solid_count") or 1),
            part_ids=(str(part.internal_id),),
            assembly_ids=tuple(str(item) for item in (getattr(part, "assembly_ids", ()) or ())),
            warnings=tuple(getattr(inspection, "warnings", ()) or ()),
            blockers=tuple(getattr(inspection, "blocking_reasons", ()) or ()) if not bool(getattr(inspection, "selection_verified", False)) else (),
            metadata=metadata,
        )
        if (
            source.exact_source
            and source_format in {"STEP", "IFC"}
            and not source.trusted_payload
            and not bool(metadata["workbench_available"])
        ):
            try:
                from cws_convertor.manufacturing_interpreter import (
                    ManufacturingGeometryInterpreter,
                    ManufacturingInterpretationRequest,
                )

                report = ManufacturingGeometryInterpreter().analyze(
                    ManufacturingInterpretationRequest(
                        inspection=inspection,
                        preferred_profile=str(getattr(part, "profile", "") or ""),
                        requested_outputs=("NC1", "IFC", "STEP", "PDF"),
                    )
                )
                source.mgi = {
                    "report_hash": report.semantic_sha256,
                    "readiness": report.readiness.value,
                    "equivalence": report.equivalence.status.value,
                    "blockers": list(report.blockers),
                    "features": [item.semantic_type.value.lower() for item in report.features],
                    "representability": {
                        item.target: item.status.value
                        for item in getattr(getattr(report, "representability_report", None), "targets", ())
                    },
                    "authority": "ManufacturingGeometryInterpreter",
                }
                if not source.features:
                    source.features = _unique(source.mgi.get("features", ()))
            except Exception as exc:
                source.mgi = {
                    "readiness": "BLOCKED",
                    "blockers": [f"MGI_EXECUTION_FAILED:{type(exc).__name__}:{exc}"],
                    "authority": "ManufacturingGeometryInterpreter",
                }
        return source

    def plan_file(self, source_path: str | Path, direction: str) -> ConversionPlan:
        source = self.inspect_file(source_path)
        return self.plan_source(source, direction)

    def plan_source(self, source: ConversionSource, direction: str) -> ConversionPlan:
        normalised = normalise_direction(direction)
        route = ROUTE_BY_DIRECTION.get(normalised)
        if route is None:
            placeholder = ConversionRoute(
                source.source_format,
                "",
                normalised,
                "",
                "",
            )
            return self._make_plan(
                placeholder,
                source,
                ConversionStatus.BLOCKED,
                blockers=("CONVERSION_ROUTE_NOT_REGISTERED",),
            )
        if route.source_format != source.source_format:
            return self._make_plan(
                route,
                source,
                ConversionStatus.BLOCKED,
                blockers=(
                    f"SOURCE_FORMAT_MISMATCH:expected={route.source_format}:found={source.source_format}",
                ),
            )

        blockers = list(source.blockers)
        warnings = list(source.warnings)
        features = set(source.features)
        unsupported: set[str] = set()
        status = ConversionStatus.SUPPORTED
        workbench_authority = bool(source.metadata.get("workbench_available"))
        if workbench_authority:
            warnings.append("PROJECT_WORKBENCH_TARGET_ROUNDTRIP_AUTHORITY")

        fatal_prefixes = ("unknown", "unsupported_block:", "hole_operation:")
        fatal = sorted(item for item in features if item.startswith(fatal_prefixes))
        if fatal:
            unsupported.update(fatal)
            blockers.extend(f"UNPROVEN_FEATURE:{item}" for item in fatal)

        # Current physical serializers do not reconstruct these losslessly
        # across every relevant target. Keep them visible, never false-green.
        if "blind_hole" in features:
            unsupported.add("blind_hole")
            blockers.append("BLIND_HOLE_SERIALIZER_REIMPORT_NOT_PROVEN")
        if source.source_format == "NC1" and "inner_contour" in features:
            unsupported.add("inner_contour")
            blockers.append("NC1_INNER_CONTOUR_SOLID_REBUILD_NOT_PROVEN")

        native_semantic_limits = {
            "marking", "scribing", "countersink", "counterbore", "slot",
            "cope", "cutout", "pocket", "end_cut", "miter_cut", "bevel", "chamfer",
        }
        limited = sorted(features & native_semantic_limits)
        if limited:
            warnings.extend(f"TARGET_NATIVE_SEMANTICS_LIMITED:{item}" for item in limited)
            status = ConversionStatus.SUPPORTED_WITH_LIMITS

        if source.source_format == "PDF" and not source.trusted_payload:
            blockers.append("EXTERNAL_PDF_REVIEW_REQUIRED")
            status = ConversionStatus.REVIEW

        if route.target_format == "NC1":
            if source.part_form and source.part_form not in {"plate", "profile"}:
                blockers.append(f"NC1_PART_FORM_NOT_PROVEN:{source.part_form}")
            if limited:
                # NC1 writers currently prove ordinary through holes and line
                # contours in the central project roundtrip. Other features may
                # exist in lower-level prototypes but are not centrally released.
                unsupported.update(limited)
                blockers.extend(f"NC1_SERIALIZER_REIMPORT_NOT_PROVEN:{item}" for item in limited)
            if (
                source.source_format in {"STEP", "IFC"}
                and not source.trusted_payload
                and not workbench_authority
            ):
                readiness = str(source.mgi.get("readiness") or "")
                target_status = str((source.mgi.get("representability") or {}).get("NC1") or "")
                if readiness != "READY" or target_status not in {"SUPPORTED", "SUPPORTED_WITH_LIMITS"}:
                    blockers.append("MGI_GEOMETRY_AND_NC1_REPRESENTABILITY_PROOF_REQUIRED")
                    status = ConversionStatus.REVIEW
                else:
                    status = ConversionStatus.SUPPORTED_WITH_LIMITS
                    warnings.append("HISTORY_FREE_SOURCE_INTERPRETED_BY_PROVEN_MGI")

        if source.solid_count > 1:
            if source.source_format == "STEP" and route.target_format in {"NC1", "PDF"}:
                if source.trusted_payload:
                    status = ConversionStatus.SUPPORTED_WITH_LIMITS
                    warnings.append("MULTI_SOLID_PART_SPLIT")
                else:
                    blockers.append("MULTI_SOLID_PER_PART_MGI_PROOF_REQUIRED")
                    status = ConversionStatus.REVIEW
            else:
                status = ConversionStatus.SUPPORTED_WITH_LIMITS if status == ConversionStatus.SUPPORTED else status
                warnings.append("MULTI_SOLID_ASSEMBLY_PACKAGE_WITH_IDENTITY_MANIFEST")

        if source.source_format == "IFC" and not source.trusted_payload and not workbench_authority:
            if not source.exact_source:
                blockers.append("TRIANGULATED_IFC_IS_REVIEW_ONLY")
                status = ConversionStatus.REVIEW
            elif route.target_format in {"NC1", "PDF"}:
                blockers.append("IFC_PER_PART_MANUFACTURING_SEMANTICS_REVIEW_REQUIRED")
                status = ConversionStatus.REVIEW
            else:
                status = ConversionStatus.SUPPORTED_WITH_LIMITS
                warnings.append("IFC_IDENTITY_PRESERVED_IN_MANIFEST;NATIVE_STEP_ASSEMBLY_SEMANTICS_LIMITED")

        if source.source_format == "STEP" and not source.trusted_payload and not workbench_authority:
            if not source.exact_source:
                blockers.append("EXACT_STEP_BREP_REQUIRED")
                status = ConversionStatus.REVIEW
            elif route.target_format in {"NC1", "PDF"} and status == ConversionStatus.SUPPORTED:
                status = ConversionStatus.SUPPORTED_WITH_LIMITS

        if route.target_format == "PDF":
            # PDF is permitted only with visible page proof after serialization;
            # it is never advertised as unrestricted native-CAD losslessness.
            status = ConversionStatus.SUPPORTED_WITH_LIMITS if status == ConversionStatus.SUPPORTED else status
            warnings.append("PDF_VISIBLE_VECTOR_CONTENT_PROOF_REQUIRED")

        if blockers and status not in {ConversionStatus.REVIEW}:
            status = ConversionStatus.BLOCKED
        if unsupported:
            status = ConversionStatus.BLOCKED

        scope = source.scope
        if source.solid_count > 1 and source.source_format == "STEP" and route.target_format in {"NC1", "PDF"}:
            scope = ConversionScope.PART_SPLIT.value
        elif source.solid_count > 1 or source.assembly_ids or source.identity_relations:
            scope = ConversionScope.ASSEMBLY_PACKAGE.value
        return self._make_plan(
            route,
            source,
            status,
            scope=scope,
            blockers=_unique(blockers),
            warnings=_unique(warnings),
            unsupported_features=tuple(sorted(unsupported)),
        )

    def _make_plan(
        self,
        route: ConversionRoute,
        source: ConversionSource,
        status: ConversionStatus,
        *,
        scope: str | None = None,
        blockers: Iterable[str] = (),
        warnings: Iterable[str] = (),
        unsupported_features: Iterable[str] = (),
    ) -> ConversionPlan:
        unsupported = _unique(unsupported_features)
        supported = tuple(sorted(set(source.features) - set(unsupported)))
        identity = {
            "planner": PLANNER_VERSION,
            "direction": route.direction,
            "source_sha256": source.source_sha256,
            "scope": scope or source.scope,
            "status": status.value,
            "features": list(source.features),
            "blockers": list(blockers),
        }
        return ConversionPlan(
            plan_id=f"conversion-plan:{_stable_hash(identity)[:24]}",
            planner_version=PLANNER_VERSION,
            route=route,
            source=source,
            status=status,
            scope=scope or source.scope,
            blockers=_unique(blockers),
            warnings=_unique(warnings),
            supported_features=supported,
            unsupported_features=unsupported,
        )


class ConversionService:
    """Execute only planner-approved routes and persist reopenable evidence."""

    def __init__(self, planner: ConversionPlanner | None = None) -> None:
        self.planner = planner or ConversionPlanner()

    def preflight(self, source_path: str | Path, direction: str) -> ConversionPlan:
        return self.planner.plan_file(source_path, direction)

    def convert_file(
        self,
        source_path: str | Path,
        output_directory: str | Path,
        direction: str,
        *,
        material: str = "S235JR",
        order_number: str = "CWS",
        profile_database: Any = None,
        preferred_profile: str = "",
        tolerance_mm: float = 1.0,
        strict_validation: bool = True,
        plan: ConversionPlan | None = None,
    ) -> ConversionExecution:
        source = Path(source_path).expanduser().resolve()
        output = Path(output_directory).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        active = plan or self.preflight(source, direction)
        if active.source.source_sha256 and _sha256_file(source) != active.source.source_sha256:
            return ConversionExecution(
                "failed",
                str(source),
                active.route.direction,
                failures=["SOURCE_CHANGED_AFTER_PREFLIGHT"],
                plan=active.to_dict(),
            )
        if not active.executable:
            return ConversionExecution(
                "blocked" if active.status == ConversionStatus.BLOCKED else "review_required",
                str(source),
                active.route.direction,
                warnings=list(active.warnings),
                failures=list(active.blockers),
                plan=active.to_dict(),
            )

        try:
            outputs, serializer_warnings, serializer_details = self._serialize_file(
                source,
                output,
                active,
                material=material,
                order_number=order_number,
                profile_database=profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
                strict_validation=strict_validation,
            )
            proofs = self._prove_outputs(active, outputs, serializer_details)
            failed_proofs = [name for name, proof in proofs.items() if proof.get("status") != "PASS"]
            if failed_proofs:
                raise RuntimeError("Bewijs afgekeurd: " + ", ".join(failed_proofs))
            evidence = self._write_evidence(
                output,
                active,
                outputs,
                warnings=[*active.warnings, *serializer_warnings],
                proofs=proofs,
                serializer_details=serializer_details,
            )
            verification = verify_evidence_manifest(evidence)
            if verification["status"] != "PASS":
                raise RuntimeError("EVIDENCE_REOPEN_FAILED:" + ";".join(verification["failures"]))
            proofs["evidence_reopen"] = verification
            return ConversionExecution(
                "passed",
                str(source),
                active.route.direction,
                outputs=[str(path.resolve()) for path in outputs],
                warnings=list(_unique((*active.warnings, *serializer_warnings))),
                evidence_path=str(evidence.resolve()),
                plan=active.to_dict(),
                proofs=proofs,
            )
        except Exception as exc:
            return ConversionExecution(
                "failed",
                str(source),
                active.route.direction,
                warnings=list(active.warnings),
                failures=[f"{type(exc).__name__}: {exc}"],
                plan=active.to_dict(),
            )

    def convert_batch(
        self,
        source_paths: Sequence[str | Path],
        output_directory: str | Path,
        direction: str,
        *,
        material: str = "S235JR",
        profile_database: Any = None,
        progress: Callable[[int, str, dict[str, Any]], None] | None = None,
        cancel_check: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        output = Path(output_directory).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        sources = [Path(item).expanduser().resolve() for item in source_paths]
        plans: list[ConversionPlan] = []
        for index, source in enumerate(sources, start=1):
            if cancel_check is not None:
                cancel_check()
            plans.append(self.preflight(source, direction))
            if progress is not None:
                progress(
                    int(index / max(1, len(sources)) * 20),
                    f"Preflight {index}/{len(sources)} · {source.name}",
                    {"stage": "preflight", "item": index, "total": len(sources)},
                )

        results: list[dict[str, Any]] = []
        for index, (source, plan) in enumerate(zip(sources, plans, strict=True), start=1):
            if cancel_check is not None:
                cancel_check()
            if progress is not None:
                progress(
                    20 + int((index - 1) / max(1, len(sources)) * 75),
                    f"Converteren {index}/{len(sources)} · {source.name}",
                    {"stage": "conversion", "item": index, "total": len(sources)},
                )
            item_output = output / _safe_name(source.stem)
            result = self.convert_file(
                source,
                item_output,
                direction,
                material=material,
                profile_database=profile_database,
                plan=plan,
            )
            results.append(result.to_dict())
            if progress is not None:
                progress(
                    20 + int(index / max(1, len(sources)) * 75),
                    f"{index}/{len(sources)} · {source.name} · {result.status}",
                    {"stage": result.status, "item": index, "total": len(sources)},
                )

        status = "passed" if results and all(item["status"] == "passed" for item in results) else "completed_with_failures"
        if not results:
            status = "blocked"
        batch = {
            "schema": BATCH_SCHEMA,
            "planner_version": PLANNER_VERSION,
            "status": status,
            "direction": normalise_direction(direction),
            "preflight_complete_before_execution": True,
            "item_failure_isolation": True,
            "results": results,
        }
        batch["manifest_sha256"] = _stable_hash(batch)
        manifest = output / "conversion_batch_manifest.json"
        _atomic_json(manifest, batch)
        if progress is not None:
            progress(100, "Batch afgerond", {"stage": status, "item": len(results), "total": len(results)})
        return {**batch, "manifest_path": str(manifest.resolve())}

    def convert_project_selection(
        self,
        project_path: str | Path,
        entity_id: str,
        output_directory: str | Path,
        direction: str,
        *,
        material: str = "S235JR",
    ) -> dict[str, Any]:
        from cws_convertor.project import ProjectSession

        project_file = Path(project_path).expanduser().resolve()
        output = Path(output_directory).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        session = ProjectSession.open(project_file, read_only=True)
        if entity_id in session.project.assemblies:
            assembly = session.project.assemblies[entity_id]
            results = []
            for part_id in assembly.part_ids:
                result = self._convert_project_part(
                    session,
                    project_file,
                    part_id,
                    output / _safe_name(assembly.assembly_mark or entity_id),
                    direction,
                    material=material,
                )
                results.append(result.to_dict())
            assembly_manifest = {
                "schema": "cws.conversion.assembly-package.v1",
                "assembly_id": entity_id,
                "assembly_mark": assembly.assembly_mark,
                "part_ids": list(assembly.part_ids),
                "child_assembly_ids": list(assembly.child_assembly_ids),
                "identity_preserved": True,
                "direction": normalise_direction(direction),
                "results": results,
                "status": "passed" if results and all(item["status"] == "passed" for item in results) else "completed_with_failures",
            }
            assembly_manifest["manifest_sha256"] = _stable_hash(assembly_manifest)
            path = output / f"{_safe_name(assembly.assembly_mark or entity_id)}_assembly_conversion_manifest.json"
            _atomic_json(path, assembly_manifest)
            return {**assembly_manifest, "manifest_path": str(path.resolve())}
        if entity_id not in session.project.parts:
            return {
                "status": "blocked",
                "results": [],
                "failures": [f"UNKNOWN_PROJECT_ENTITY:{entity_id}"],
            }
        result = self._convert_project_part(
            session,
            project_file,
            entity_id,
            output,
            direction,
            material=material,
        )
        return {"status": result.status, "results": [result.to_dict()]}

    def _convert_project_part(
        self,
        session: Any,
        project_path: Path,
        part_id: str,
        output: Path,
        direction: str,
        *,
        material: str,
    ) -> ConversionExecution:
        from cws_convertor.project.canonical_rebuild import rebuild_and_compare
        from cws_convertor.project.roundtrip import validate_target_roundtrip
        from cws_convertor.project.model import stable_sha256

        part = session.project.parts[part_id]
        try:
            inspection = session.inspect_part_source_geometry(part_id, persist=False)
        except Exception as exc:
            inspection = type(
                "UnavailableInspection",
                (),
                {
                    "source_sha256": part.source_identity.source_sha256,
                    "production_geometry_exact": False,
                    "selection_verified": False,
                    "native_shape": None,
                    "metrics": {},
                    "warnings": (),
                    "blocking_reasons": (f"SOURCE_INSPECTION_FAILED:{type(exc).__name__}:{exc}",),
                },
            )()
        source = self.planner.source_from_project_part(part, inspection, project_path=project_path)
        plan = self.planner.plan_source(source, direction)
        if not plan.executable:
            return ConversionExecution(
                "blocked" if plan.status == ConversionStatus.BLOCKED else "review_required",
                str(project_path),
                plan.route.direction,
                warnings=list(plan.warnings),
                failures=list(plan.blockers),
                plan=plan.to_dict(),
            )
        target_format = plan.route.target_format.lower()
        output.mkdir(parents=True, exist_ok=True)
        try:
            if part.workbench:
                rebuild = rebuild_and_compare(part)
                if rebuild.shape is None or rebuild.report.get("status") != "passed":
                    raise RuntimeError("CANONICAL_REBUILD_NOT_PROVEN")
                signature = str(rebuild.report.get("canonical_signature") or "")
                report = validate_target_roundtrip(
                    part,
                    rebuild.shape,
                    output,
                    canonical_signature=signature,
                    target_format=target_format,
                )
                format_result = dict(report.get("formats", {}).get(target_format) or {})
                if format_result.get("status") != "passed":
                    raise RuntimeError(str(format_result.get("probable_cause") or "TARGET_ROUNDTRIP_FAILED"))
                outputs = [Path(format_result["artifact_path"])]
                proofs = {
                    "serializer": {"status": "PASS", "authority": "project.target-roundtrip"},
                    "physical_reimport": {"status": "PASS", "report": report},
                    "geometry_compare": {"status": "PASS", "canonical_signature": signature},
                    "semantic_compare": {"status": "PASS", "manufacturing_hash": part.manufacturing_hash},
                }
            else:
                shape = getattr(inspection, "native_shape", None)
                if shape is None or not source.exact_source:
                    raise RuntimeError("EXACT_SELECTED_SOURCE_BREP_REQUIRED")
                signature = stable_sha256(
                    {
                        "source_sha256": inspection.source_sha256,
                        "source_geometry_hash": getattr(inspection, "source_geometry_hash", ""),
                        "metrics": getattr(inspection, "metrics", {}),
                    }
                )
                with tempfile.TemporaryDirectory(prefix="cws-project-selection-") as folder:
                    import cadquery as cq

                    isolated_step = Path(folder) / f"{_safe_name(part.part_position or part_id)}.step"
                    cq.exporters.export(shape, str(isolated_step), exportType="STEP")
                    derived = self.planner.inspect_file(isolated_step)
                    derived.source_sha256 = _sha256_file(isolated_step)
                    derived.part_ids = (part_id,)
                    derived.assembly_ids = tuple(part.assembly_ids)
                    derived.metadata.update(source.metadata)
                    derived_plan = self.planner.plan_source(
                        derived,
                        f"step-{plan.route.target_format.lower()}" if plan.route.target_format != "STEP" else "step-ifc",
                    )
                    if plan.route.target_format == "STEP":
                        target = output / f"{_safe_name(part.part_position or part_id)}.step"
                        cq.exporters.export(shape, str(target), exportType="STEP")
                        outputs = [target]
                        details = {"route": "exact-selected-source-brep", "canonical_signature": signature}
                    else:
                        if not derived_plan.executable:
                            raise RuntimeError(
                                "DERIVED_ISOLATED_STEP_PREFLIGHT_FAILED:"
                                + ";".join(derived_plan.blockers or (derived_plan.status.value,))
                            )
                        outputs, warnings, details = self._serialize_file(
                            isolated_step,
                            output,
                            derived_plan,
                            material=part.material or material,
                            order_number="PROJECT",
                            profile_database=None,
                            preferred_profile=part.profile,
                            tolerance_mm=1.0,
                            strict_validation=True,
                        )
                        plan.warnings = _unique((*plan.warnings, *warnings))
                proofs = self._prove_outputs(plan, outputs, details)
                if any(value.get("status") != "PASS" for value in proofs.values()):
                    raise RuntimeError("PROJECT_SELECTION_OUTPUT_PROOF_FAILED")

            evidence = self._write_evidence(
                output,
                plan,
                outputs,
                warnings=plan.warnings,
                proofs=proofs,
                serializer_details={
                    "project_id": session.project.project_id,
                    "part_id": part_id,
                    "assembly_ids": list(part.assembly_ids),
                },
            )
            reopen = verify_evidence_manifest(evidence)
            if reopen["status"] != "PASS":
                raise RuntimeError("PROJECT_EVIDENCE_REOPEN_FAILED")
            proofs["evidence_reopen"] = reopen
            return ConversionExecution(
                "passed",
                str(project_path),
                plan.route.direction,
                outputs=[str(item.resolve()) for item in outputs],
                warnings=list(plan.warnings),
                evidence_path=str(evidence.resolve()),
                plan=plan.to_dict(),
                proofs=proofs,
            )
        except Exception as exc:
            return ConversionExecution(
                "failed",
                str(project_path),
                plan.route.direction,
                warnings=list(plan.warnings),
                failures=[f"{type(exc).__name__}: {exc}"],
                plan=plan.to_dict(),
            )

    def _serialize_file(
        self,
        source: Path,
        output: Path,
        plan: ConversionPlan,
        *,
        material: str,
        order_number: str,
        profile_database: Any,
        preferred_profile: str,
        tolerance_mm: float,
        strict_validation: bool,
    ) -> tuple[list[Path], list[str], dict[str, Any]]:
        direction = plan.route.direction
        target = plan.route.target_format
        warnings: list[str] = []
        details: dict[str, Any] = {
            "route": direction,
            "scope": plan.scope,
            "serializer": plan.route.serializer,
        }

        if (
            plan.scope == ConversionScope.PART_SPLIT.value
            and plan.source.source_format == "STEP"
            and plan.source.solid_count > 1
            and target in {"NC1", "PDF"}
        ):
            return self._serialize_split_step(
                source,
                output,
                plan,
                material=material,
                order_number=order_number,
                profile_database=profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
                strict_validation=strict_validation,
            )

        if direction == "nc1-step":
            from conversion import convert_nc1_to_step

            artifact = output / f"{source.stem}.step"
            parsed = convert_nc1_to_step(source, artifact)
            outputs = [artifact]
            warnings.extend(parsed.warnings)
        elif direction == "step-nc1":
            from conversion import step_to_nc1

            artifact = output / f"{source.stem}.nc1"
            result = step_to_nc1(
                source,
                artifact,
                material=material,
                order_number=order_number,
                profile_database=profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
                strict_validation=strict_validation,
            )
            outputs = [result.output]
            warnings.extend(result.warnings)
            details.update(
                {
                    "matched_by": result.matched_by,
                    "confidence": result.confidence,
                    "volume_delta_percent": result.volume_delta_percent,
                }
            )
        elif direction == "ifc-step":
            from ifc_support import ifc_to_step

            result = ifc_to_step(source, output / f"{source.stem}.step")
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        elif direction == "step-ifc":
            from ifc_support import step_to_ifc

            result = step_to_ifc(source, output / f"{source.stem}.ifc", material=material)
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        elif direction == "nc1-ifc":
            from ifc_support import dstv_to_ifc

            result = dstv_to_ifc(source, output / f"{source.stem}.ifc", material=material)
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        elif direction == "ifc-nc1":
            from ifc_support import ifc_to_dstv

            result = ifc_to_dstv(
                source,
                output,
                material=material,
                order_number=order_number,
                profile_database=profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance_mm,
                strict_validation=strict_validation,
            )
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        elif direction in {"pdf-nc1", "pdf-step", "pdf-ifc"}:
            from pdf_support import pdf_to_ifc, pdf_to_nc1, pdf_to_step

            extension = ".nc1" if target == "NC1" else f".{target.lower()}"
            artifact = output / f"{source.stem}{extension}"
            if target == "NC1":
                result = pdf_to_nc1(source, artifact)
            elif target == "STEP":
                result = pdf_to_step(source, artifact)
            else:
                result = pdf_to_ifc(source, artifact, material=material)
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        elif direction in {"nc1-pdf", "step-pdf", "ifc-pdf"}:
            from pdf_support import ifc_to_pdf, nc1_to_pdf, step_to_pdf

            artifact = (
                output / f"{source.stem}_pdf_parts"
                if direction == "ifc-pdf" and plan.source.product_count > 1
                else output / f"{source.stem}.pdf"
            )
            if direction == "nc1-pdf":
                result = nc1_to_pdf(source, artifact)
            elif direction == "step-pdf":
                result = step_to_pdf(
                    source,
                    artifact,
                    material=material,
                    preferred_profile=preferred_profile,
                    tolerance_mm=tolerance_mm,
                )
            else:
                result = ifc_to_pdf(source, artifact, material=material)
            if result.failures:
                raise RuntimeError("; ".join(result.failures))
            outputs = list(result.outputs)
            warnings.extend(result.warnings)
            details.update(result.details)
        else:
            raise ValueError(f"Niet-geïmplementeerde centrale route {direction}")

        missing = [str(path) for path in outputs if not Path(path).is_file()]
        if missing:
            raise RuntimeError("Serializer rapporteerde ontbrekende uitvoer: " + ", ".join(missing))
        outputs = [Path(item).resolve() for item in outputs]
        if plan.scope == ConversionScope.ASSEMBLY_PACKAGE.value:
            identity_path = output / f"{_safe_name(source.stem)}_{target.lower()}_identity_manifest.json"
            identity = {
                "schema": "cws.conversion.identity-manifest.v1",
                "source_sha256": plan.source.source_sha256,
                "part_ids": list(plan.source.part_ids),
                "assembly_ids": list(plan.source.assembly_ids),
                "relations": [list(item) for item in plan.source.identity_relations],
                "target_format": target,
                "native_target_semantics": "limited" if plan.status == ConversionStatus.SUPPORTED_WITH_LIMITS else "preserved",
            }
            identity["manifest_sha256"] = _stable_hash(identity)
            _atomic_json(identity_path, identity)
            outputs.append(identity_path.resolve())
            details["identity_manifest"] = str(identity_path.resolve())
        return outputs, list(_unique(warnings)), details

    def _serialize_split_step(
        self,
        source: Path,
        output: Path,
        plan: ConversionPlan,
        *,
        material: str,
        order_number: str,
        profile_database: Any,
        preferred_profile: str,
        tolerance_mm: float,
        strict_validation: bool,
    ) -> tuple[list[Path], list[str], dict[str, Any]]:
        import cadquery as cq

        shape = cq.importers.importStep(str(source)).val()
        solids = list(shape.Solids())
        if len(solids) != plan.source.solid_count:
            raise RuntimeError(
                f"MULTI_SOLID_COUNT_CHANGED:preflight={plan.source.solid_count}:runtime={len(solids)}"
            )
        package = output / f"{_safe_name(source.stem)}_{plan.route.target_format.lower()}_parts"
        package.mkdir(parents=True, exist_ok=True)
        outputs: list[Path] = []
        warnings: list[str] = []
        items: list[dict[str, Any]] = []
        failures: list[str] = []
        with tempfile.TemporaryDirectory(prefix="cws-step-part-split-") as folder:
            for index, solid in enumerate(solids, start=1):
                isolated = Path(folder) / f"{source.stem}_{index:04d}.step"
                cq.exporters.export(solid, str(isolated), exportType="STEP")
                sub_direction = f"step-{plan.route.target_format.lower()}"
                sub_source = self.planner.inspect_file(isolated)
                sub_plan = self.planner.plan_source(sub_source, sub_direction)
                if not sub_plan.executable:
                    failures.append(
                        f"part {index}: " + "; ".join(sub_plan.blockers or (sub_plan.status.value,))
                    )
                    items.append({"index": index, "status": "blocked", "blockers": list(sub_plan.blockers)})
                    continue
                try:
                    item_outputs, item_warnings, _details = self._serialize_file(
                        isolated,
                        package,
                        sub_plan,
                        material=material,
                        order_number=order_number,
                        profile_database=profile_database,
                        preferred_profile=preferred_profile,
                        tolerance_mm=tolerance_mm,
                        strict_validation=strict_validation,
                    )
                    renamed: list[str] = []
                    for item_path in item_outputs:
                        if item_path.suffix.lower() not in {".nc", ".nc1", ".pdf"}:
                            continue
                        final = package / f"{source.stem}_{index:04d}{item_path.suffix.lower()}"
                        if item_path.resolve() != final.resolve():
                            item_path.replace(final)
                        outputs.append(final.resolve())
                        renamed.append(final.name)
                    warnings.extend(item_warnings)
                    items.append({"index": index, "status": "passed", "outputs": renamed})
                except Exception as exc:
                    failures.append(f"part {index}: {type(exc).__name__}: {exc}")
                    items.append({"index": index, "status": "failed", "error": str(exc)})
        manifest = {
            "schema": "cws.conversion.part-split.v1",
            "source_sha256": plan.source.source_sha256,
            "solid_count": len(solids),
            "target_format": plan.route.target_format,
            "items": items,
            "failures": failures,
            "status": "passed" if not failures and len(outputs) == len(solids) else "failed",
        }
        manifest["manifest_sha256"] = _stable_hash(manifest)
        manifest_path = package / "part_split_manifest.json"
        _atomic_json(manifest_path, manifest)
        outputs.append(manifest_path.resolve())
        if failures:
            raise RuntimeError("PART_SPLIT_INCOMPLETE:" + " | ".join(failures))
        return outputs, list(_unique(warnings)), {"route": "step-part-split", "part_split_manifest": str(manifest_path.resolve()), "items": items}

    def _prove_outputs(
        self,
        plan: ConversionPlan,
        outputs: Sequence[Path],
        serializer_details: Mapping[str, Any],
    ) -> dict[str, Any]:
        artifacts = [Path(item) for item in outputs]
        target_files = [item for item in artifacts if normalise_format(item.suffix) == plan.route.target_format]
        serializer = {
            "status": "PASS" if target_files and all(item.is_file() and item.stat().st_size > 0 for item in target_files) else "FAIL",
            "serializer": plan.route.serializer,
            "artifact_count": len(target_files),
        }
        reimport = self._physical_reimport(plan.route.target_format, target_files)
        geometry = self._geometry_compare(plan, target_files, reimport)
        semantics = self._semantic_compare(plan, target_files, serializer_details)
        return {
            "serializer": serializer,
            "physical_reimport": reimport,
            "geometry_compare": geometry,
            "semantic_compare": semantics,
        }

    def _physical_reimport(self, target_format: str, paths: Sequence[Path]) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        try:
            if not paths:
                raise RuntimeError("TARGET_ARTIFACT_MISSING")
            if target_format == "NC1":
                import converter
                from conversion import build_shape

                for path in paths:
                    parsed = converter.parse_nc1(path)
                    shape = build_shape(parsed).val()
                    checks.append({"path": str(path), "valid": bool(shape.isValid()), "solids": len(shape.Solids())})
            elif target_format == "STEP":
                import cadquery as cq

                for path in paths:
                    shape = cq.importers.importStep(str(path)).val()
                    checks.append({"path": str(path), "valid": bool(shape.isValid()), "solids": len(shape.Solids())})
            elif target_format == "IFC":
                from ifc_support import load_ifc_geometry

                for path in paths:
                    model = load_ifc_geometry(path)
                    checks.append({"path": str(path), "valid": bool(model.items), "items": len(model.items), "reader": model.reader})
            elif target_format == "PDF":
                from pdf_support import load_trusted_pdf, visible_pdf_sha256
                from pypdf import PdfReader

                for path in paths:
                    analysis = load_trusted_pdf(path, strict=True)
                    reader = PdfReader(str(path))
                    text = "\n".join((page.extract_text() or "") for page in reader.pages)
                    expected_holes = len(analysis.part.holes)
                    visible_holes = sum(1 for index in range(1, expected_holes + 1) if f"H{index}" in text)
                    checks.append(
                        {
                            "path": str(path),
                            "valid": bool(reader.pages),
                            "trusted_payload": analysis.mode == "trusted_exact",
                            "visible_sha256": visible_pdf_sha256(path),
                            "main_view_visible": "ELEVATION / MAIN VIEW" in text,
                            "expected_hole_labels": expected_holes,
                            "visible_hole_labels": visible_holes,
                        }
                    )
            passed = all(
                item.get("valid")
                and int(item.get("solids", item.get("items", 1)) or 0) > 0
                and item.get("main_view_visible", True)
                and item.get("visible_hole_labels", 0) == item.get("expected_hole_labels", 0)
                for item in checks
            )
            return {"status": "PASS" if passed else "FAIL", "validator": f"reimport:{target_format.lower()}", "checks": checks}
        except Exception as exc:
            return {"status": "FAIL", "validator": f"reimport:{target_format.lower()}", "checks": checks, "error": f"{type(exc).__name__}: {exc}"}

    def _geometry_compare(
        self,
        plan: ConversionPlan,
        target_files: Sequence[Path],
        reimport: Mapping[str, Any],
    ) -> dict[str, Any]:
        if reimport.get("status") != "PASS":
            return {"status": "FAIL", "reason": "PHYSICAL_REIMPORT_FAILED"}
        if plan.route.target_format == "PDF":
            visible = list(reimport.get("checks") or [])
            passed = bool(visible) and all(
                item.get("main_view_visible")
                and item.get("visible_hole_labels") == item.get("expected_hole_labels")
                and item.get("visible_sha256")
                for item in visible
            )
            return {
                "status": "PASS" if passed else "FAIL",
                "comparator": "pdf-visible-vector-content-v1",
                "checks": visible,
                "comparison_scope": "visible view + feature labels + trusted geometry payload",
            }
        source_metrics = _metrics_for_path(Path(plan.source.source_path), plan.source.source_format)
        if not source_metrics:
            source_metrics = dict(plan.source.metadata.get("source_metrics") or {}) or None
        target_metrics = _aggregate_metrics(
            [_metrics_for_path(path, plan.route.target_format) for path in target_files]
        )
        if not source_metrics or not target_metrics:
            return {"status": "FAIL", "reason": "GEOMETRY_METRICS_UNAVAILABLE"}
        expected_volume = float(source_metrics.get("volume_mm3") or 0.0)
        actual_volume = float(target_metrics.get("volume_mm3") or 0.0)
        expected_area = float(source_metrics.get("area_mm2") or 0.0)
        actual_area = float(target_metrics.get("area_mm2") or 0.0)
        volume_delta = _percent_delta(expected_volume, actual_volume)
        area_delta = _percent_delta(expected_area, actual_area)
        tolerance = 1.0 if "IFC" in {plan.source.source_format, plan.route.target_format} else 0.75
        passed = (
            expected_volume > 0
            and actual_volume > 0
            and abs(volume_delta) <= tolerance
            and (expected_area <= 0 or abs(area_delta) <= max(tolerance, 1.0))
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "comparator": "aggregate-brep-metrics-v1",
            "source_metrics": source_metrics,
            "target_metrics": target_metrics,
            "volume_delta_percent": volume_delta,
            "area_delta_percent": area_delta,
            "tolerance_percent": tolerance,
        }

    def _semantic_compare(
        self,
        plan: ConversionPlan,
        target_files: Sequence[Path],
        serializer_details: Mapping[str, Any],
    ) -> dict[str, Any]:
        source_part = _canonical_for_path(Path(plan.source.source_path), plan.source.source_format)
        restored = [
            part for part in (_canonical_for_path(path, plan.route.target_format) for path in target_files) if part is not None
        ]
        if source_part is not None:
            passed = bool(restored) and any(
                item.geometry_sha256() == source_part.geometry_sha256()
                and item.header.profile == source_part.header.profile
                and int(item.header.quantity or 1) == int(source_part.header.quantity or 1)
                for item in restored
            )
            return {
                "status": "PASS" if passed else "FAIL",
                "comparator": "canonical-geometry-and-production-fields-v1",
                "source_geometry_sha256": source_part.geometry_sha256(),
                "restored_geometry_sha256": [item.geometry_sha256() for item in restored],
                "fields": ["profile", "quantity", "geometry_sha256"],
            }
        identity_claimed = bool(plan.source.part_ids or plan.source.assembly_ids or plan.source.identity_relations)
        identity_manifest = str(serializer_details.get("identity_manifest") or "")
        identity_preserved = not identity_claimed or bool(identity_manifest and Path(identity_manifest).is_file()) or plan.scope == ConversionScope.PART.value
        return {
            "status": "PASS" if identity_preserved and bool(target_files) else "FAIL",
            "comparator": "source-identity-and-scope-manifest-v1",
            "comparison_scope": "geometry-only source; native manufacturing semantics not claimed",
            "part_ids": list(plan.source.part_ids),
            "assembly_ids": list(plan.source.assembly_ids),
            "relations": [list(item) for item in plan.source.identity_relations],
            "identity_manifest": identity_manifest,
            "native_target_semantics": "limited",
        }

    def _write_evidence(
        self,
        output: Path,
        plan: ConversionPlan,
        outputs: Sequence[Path],
        *,
        warnings: Iterable[str],
        proofs: Mapping[str, Any],
        serializer_details: Mapping[str, Any],
    ) -> Path:
        project_part_id = str(plan.source.metadata.get("project_part_id") or "")
        part_position = str(plan.source.metadata.get("part_position") or "")
        evidence_stem = (
            f"{part_position}_{project_part_id}"
            if project_part_id
            else Path(plan.source.source_path).stem
        )
        name = f"{_safe_name(evidence_stem)}_{plan.route.target_format.lower()}_conversion_evidence.json"
        path = output / name
        artifacts = []
        for item in outputs:
            artifact = Path(item).resolve()
            try:
                relative = artifact.relative_to(output.resolve()).as_posix()
            except ValueError:
                relative = artifact.name
            artifacts.append(
                {
                    "path": str(artifact),
                    "relative_path": relative,
                    "sha256": _sha256_file(artifact),
                    "size_bytes": artifact.stat().st_size,
                    "format": normalise_format(artifact.suffix),
                }
            )
        manifest = {
            "schema": EVIDENCE_SCHEMA,
            "authority": "cws_convertor.conversion_service.ConversionService",
            "plan": plan.to_dict(),
            "status": "passed",
            "warnings": list(_unique(warnings)),
            "serializer_details": dict(serializer_details),
            "proofs": dict(proofs),
            "artifacts": artifacts,
            "source": {
                "path": plan.source.source_path,
                "sha256": plan.source.source_sha256,
                "format": plan.source.source_format,
            },
        }
        manifest["manifest_sha256"] = _stable_hash(manifest)
        _atomic_json(path, manifest)
        return path


def _safe_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return clean or "conversion"


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _percent_delta(reference: float, candidate: float) -> float:
    return (candidate - reference) / reference * 100.0 if abs(reference) > 1e-12 else math.inf


def _shape_metrics(shape: Any) -> dict[str, Any]:
    box = shape.BoundingBox()
    return {
        "volume_mm3": float(shape.Volume()),
        "area_mm2": float(shape.Area()),
        "bbox_mm": sorted((float(box.xlen), float(box.ylen), float(box.zlen)), reverse=True),
        "solid_count": len(shape.Solids()),
        "valid": bool(shape.isValid()),
    }


def _metrics_for_path(path: Path, format_name: str) -> dict[str, Any] | None:
    format_name = normalise_format(format_name)
    try:
        if format_name == "NC1":
            import converter
            from conversion import build_shape

            return _shape_metrics(build_shape(converter.parse_nc1(path)).val())
        if format_name == "STEP":
            import cadquery as cq

            return _shape_metrics(cq.importers.importStep(str(path)).val())
        if format_name == "IFC":
            import numpy as np
            from ifc_support import load_ifc_geometry

            model = load_ifc_geometry(path)
            if not model.items:
                return None
            vertices = np.vstack([item.vertices_mm for item in model.items if len(item.vertices_mm)])
            lengths = vertices.max(axis=0) - vertices.min(axis=0)
            return {
                "volume_mm3": sum(float(item.volume_mm3) for item in model.items),
                "area_mm2": sum(float(item.area_mm2) for item in model.items),
                "bbox_mm": sorted((float(item) for item in lengths), reverse=True),
                "solid_count": len(model.items),
                "valid": True,
            }
        if format_name == "PDF":
            part = _canonical_for_path(path, "PDF")
            if part is None:
                return None
            step_bytes = part.attachment_bytes("step")
            nc1_bytes = part.attachment_bytes("nc1")
            with tempfile.TemporaryDirectory(prefix="cws-pdf-metrics-") as folder:
                if step_bytes:
                    candidate = Path(folder) / "payload.step"
                    candidate.write_bytes(step_bytes)
                    return _metrics_for_path(candidate, "STEP")
                if nc1_bytes:
                    candidate = Path(folder) / "payload.nc1"
                    candidate.write_bytes(nc1_bytes)
                    return _metrics_for_path(candidate, "NC1")
            metrics = dict(part.geometry.get("canonical_metrics") or {})
            return metrics or None
    except Exception:
        return None
    return None


def _aggregate_metrics(values: Iterable[dict[str, Any] | None]) -> dict[str, Any] | None:
    available = [dict(item) for item in values if item]
    if not available:
        return None
    if len(available) == 1:
        return available[0]
    return {
        "volume_mm3": sum(float(item.get("volume_mm3") or 0.0) for item in available),
        "area_mm2": sum(float(item.get("area_mm2") or 0.0) for item in available),
        "solid_count": sum(int(item.get("solid_count") or 0) for item in available),
        "valid": all(bool(item.get("valid", True)) for item in available),
        "aggregation": "per-part-sum",
    }


def _canonical_for_path(path: Path, format_name: str) -> Any | None:
    format_name = normalise_format(format_name)
    try:
        if format_name == "NC1":
            from canonical_model import extract_part_from_nc1
            from pdf_support import canonical_from_nc1

            return extract_part_from_nc1(path, strict=False) or canonical_from_nc1(path)
        if format_name == "STEP":
            from canonical_model import extract_part_from_step

            return extract_part_from_step(path, strict=False)
        if format_name == "IFC":
            from canonical_model import extract_part_from_ifc

            return extract_part_from_ifc(path, strict=False)
        if format_name == "PDF":
            from pdf_support import load_trusted_pdf

            return load_trusted_pdf(path, strict=True).part
    except Exception:
        return None
    return None


def verify_evidence_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    failures: list[str] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "FAIL", "failures": [f"MANIFEST_READ_FAILED:{type(exc).__name__}:{exc}"]}
    claimed = str(payload.pop("manifest_sha256", "") or "")
    actual = _stable_hash(payload)
    if not claimed or claimed != actual:
        failures.append("MANIFEST_HASH_MISMATCH")
    for artifact in list(payload.get("artifacts") or []):
        if not isinstance(artifact, Mapping):
            failures.append("INVALID_ARTIFACT_RECORD")
            continue
        relative = str(artifact.get("relative_path") or "")
        candidate = manifest_path.parent / relative if relative else Path(str(artifact.get("path") or ""))
        if not candidate.is_file():
            absolute = Path(str(artifact.get("path") or ""))
            candidate = absolute if absolute.is_file() else candidate
        if not candidate.is_file():
            failures.append(f"ARTIFACT_MISSING:{relative or artifact.get('path')}")
            continue
        if _sha256_file(candidate) != str(artifact.get("sha256") or ""):
            failures.append(f"ARTIFACT_HASH_MISMATCH:{candidate.name}")
    return {
        "status": "PASS" if not failures else "FAIL",
        "validator": "conversion-evidence-save-reopen-v1",
        "manifest_path": str(manifest_path),
        "failures": failures,
    }


DEFAULT_CONVERSION_PLANNER = ConversionPlanner()
DEFAULT_CONVERSION_SERVICE = ConversionService(DEFAULT_CONVERSION_PLANNER)


__all__ = [
    "BATCH_SCHEMA",
    "DEFAULT_CONVERSION_PLANNER",
    "DEFAULT_CONVERSION_SERVICE",
    "EVIDENCE_SCHEMA",
    "FORMATS",
    "PLANNER_VERSION",
    "ROUTES",
    "ROUTE_BY_DIRECTION",
    "ConversionExecution",
    "ConversionPlan",
    "ConversionPlanner",
    "ConversionRoute",
    "ConversionScope",
    "ConversionService",
    "ConversionSource",
    "ConversionStatus",
    "normalise_direction",
    "normalise_format",
    "verify_evidence_manifest",
]
