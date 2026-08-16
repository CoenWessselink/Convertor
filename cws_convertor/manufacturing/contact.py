"""Exact, relation-driven ContactPatch extraction for CWS manufacturing.

No global N² scan is performed here. Candidate pairs come from assembly
main/secondary relations, welds and fasteners. Exact OCCT BREP evidence is then
used to decide whether an actual surface contact exists.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Mapping

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Trsf

from cws_convertor.project.canonical_rebuild import build_canonical_shape
from cws_convertor.project.model import ProjectModel, stable_sha256

from .contact_model import ContactPatch, ContactRelationType, ContactResolutionReport
from .faces import ManufacturingFaceResolver
from .faces_model import FaceResolutionReport, ManufacturingFace

CONTACT_NOT_FOUND = "CWS-MARK-004"
CONTACT_WRONG_GEOMETRY = "CWS-MARK-005"
CONTACT_AMBIGUOUS = "CWS-MARK-002"

ShapeProvider = Callable[[str], cq.Shape]


def _apply_transform(shape: cq.Shape, matrix: list[list[float]]) -> cq.Shape:
    trsf = gp_Trsf()
    trsf.SetValues(
        float(matrix[0][0]), float(matrix[0][1]), float(matrix[0][2]), float(matrix[0][3]),
        float(matrix[1][0]), float(matrix[1][1]), float(matrix[1][2]), float(matrix[1][3]),
        float(matrix[2][0]), float(matrix[2][1]), float(matrix[2][2]), float(matrix[2][3]),
    )
    transformed = BRepBuilderAPI_Transform(shape.wrapped, trsf, True).Shape()
    result = cq.Shape.cast(transformed)
    if result is None or result.isNull():
        raise RuntimeError("Contact-transform leverde een lege shape op")
    return result


def _world_to_local(matrix: list[list[float]], point: tuple[float, float, float]) -> tuple[float, float, float]:
    delta = (
        point[0] - float(matrix[0][3]),
        point[1] - float(matrix[1][3]),
        point[2] - float(matrix[2][3]),
    )
    return (
        float(matrix[0][0]) * delta[0] + float(matrix[1][0]) * delta[1] + float(matrix[2][0]) * delta[2],
        float(matrix[0][1]) * delta[0] + float(matrix[1][1]) * delta[1] + float(matrix[2][1]) * delta[2],
        float(matrix[0][2]) * delta[0] + float(matrix[1][2]) * delta[1] + float(matrix[2][2]) * delta[2],
    )


def _local_to_world(matrix: list[list[float]], point: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        float(matrix[0][0]) * x + float(matrix[0][1]) * y + float(matrix[0][2]) * z + float(matrix[0][3]),
        float(matrix[1][0]) * x + float(matrix[1][1]) * y + float(matrix[1][2]) * z + float(matrix[1][3]),
        float(matrix[2][0]) * x + float(matrix[2][1]) * y + float(matrix[2][2]) * z + float(matrix[2][3]),
    )


def _point_tuple(point: Any) -> tuple[float, float, float]:
    return (float(point.x), float(point.y), float(point.z))


def _sample_edge(edge: cq.Edge) -> list[tuple[float, float, float]]:
    geom = str(edge.geomType() or "").upper()
    if geom == "LINE":
        vertices = edge.Vertices()
        if len(vertices) >= 2:
            return [_point_tuple(vertices[0].Center()), _point_tuple(vertices[-1].Center())]
    count = 32 if geom in {"CIRCLE", "ELLIPSE"} else 20
    return [_point_tuple(edge.positionAt(index / count)) for index in range(count + 1)]


def _wire_loop(wire: cq.Wire) -> tuple[tuple[float, float, float], ...]:
    result: list[tuple[float, float, float]] = []
    for edge in wire.Edges():
        for point in _sample_edge(edge):
            if result and math.dist(result[-1], point) <= 1e-7:
                continue
            result.append(point)
    if result and math.dist(result[0], result[-1]) > 1e-7:
        result.append(result[0])
    return tuple(result)


def _common_face(left: cq.Shape, right: cq.Shape) -> tuple[cq.Face | None, float]:
    op = BRepAlgoAPI_Common(left.wrapped, right.wrapped)
    op.Build()
    if not op.IsDone():
        return None, 0.0
    shape = cq.Shape.cast(op.Shape())
    if shape is None or shape.isNull():
        return None, 0.0
    faces = list(shape.Faces())
    face = max(faces, key=lambda item: float(item.Area()), default=None)
    if face is None:
        return None, 0.0
    area = max(0.0, float(face.Area()))
    return (face, area) if area > 1e-8 else (None, 0.0)


def _solid_common_volume(left: cq.Shape, right: cq.Shape) -> float:
    op = BRepAlgoAPI_Common(left.wrapped, right.wrapped)
    op.Build()
    if not op.IsDone():
        return 0.0
    shape = cq.Shape.cast(op.Shape())
    if shape is None or shape.isNull():
        return 0.0
    try:
        return max(0.0, float(shape.Volume()))
    except Exception:
        return 0.0


def _distance(left: cq.Shape, right: cq.Shape) -> float | None:
    solver = BRepExtrema_DistShapeShape(left.wrapped, right.wrapped)
    solver.Perform()
    if not solver.IsDone():
        return None
    return max(0.0, float(solver.Value()))


@dataclass(slots=True)
class _PairEvidence:
    a: str
    b: str
    assembly_ids: set[str] = field(default_factory=set)
    assembly_main_ids: set[str] = field(default_factory=set)
    weld_ids: set[str] = field(default_factory=set)
    fastener_ids: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)

    @property
    def key(self) -> tuple[str, str]:
        left, right = sorted((self.a, self.b))
        return left, right

    @property
    def explicit(self) -> bool:
        return bool(self.weld_ids or self.fastener_ids)

    def main_secondary(self) -> tuple[str, str] | None:
        valid = [item for item in self.assembly_main_ids if item in {self.a, self.b}]
        unique = sorted(set(valid))
        if len(unique) == 1:
            main = unique[0]
            return main, self.b if main == self.a else self.a
        if not unique:
            left, right = sorted((self.a, self.b))
            return left, right
        return None


class ExactContactGeometryEngine:
    def __init__(
        self,
        project: ProjectModel,
        *,
        shape_provider: ShapeProvider | None = None,
        face_reports: Mapping[str, FaceResolutionReport] | None = None,
        contact_tolerance_mm: float = 0.05,
        penetration_tolerance_mm3: float = 1e-6,
    ) -> None:
        self.project = project
        self.shape_provider = shape_provider
        self.face_reports = dict(face_reports or {})
        self.contact_tolerance_mm = max(0.0, float(contact_tolerance_mm))
        self.penetration_tolerance_mm3 = max(0.0, float(penetration_tolerance_mm3))
        self._local_shapes: dict[str, cq.Shape] = {}
        self._world_shapes: dict[str, cq.Shape] = {}
        self._world_faces: dict[str, tuple[tuple[int, cq.Shape], ...]] = {}

    def _local_shape(self, part_id: str) -> cq.Shape:
        if part_id in self._local_shapes:
            return self._local_shapes[part_id]
        if self.shape_provider is not None:
            shape = self.shape_provider(part_id)
        else:
            shape, _warnings, _payload = build_canonical_shape(self.project.parts[part_id])
        if shape is None or shape.isNull() or not shape.isValid() or len(shape.Solids()) != 1:
            raise RuntimeError(f"Onderdeel {part_id} heeft geen exact enkel canonical solid")
        self._local_shapes[part_id] = shape
        return shape

    def _world_shape(self, part_id: str) -> cq.Shape:
        if part_id not in self._world_shapes:
            part = self.project.parts[part_id]
            part.global_placement.validate()
            self._world_shapes[part_id] = _apply_transform(self._local_shape(part_id), part.global_placement.matrix)
        return self._world_shapes[part_id]

    def _world_face_shapes(self, part_id: str) -> tuple[tuple[int, cq.Shape], ...]:
        if part_id not in self._world_faces:
            matrix = self.project.parts[part_id].global_placement.matrix
            self._world_faces[part_id] = tuple(
                (index, _apply_transform(face, matrix))
                for index, face in enumerate(self._local_shape(part_id).Faces(), start=1)
            )
        return self._world_faces[part_id]

    def _face_report(self, part_id: str) -> FaceResolutionReport:
        if part_id not in self.face_reports:
            self.face_reports[part_id] = ManufacturingFaceResolver().resolve(
                self.project.parts[part_id],
                shape=self._local_shape(part_id),
            )
        return self.face_reports[part_id]

    def candidate_pairs(self) -> tuple[_PairEvidence, ...]:
        pairs: dict[tuple[str, str], _PairEvidence] = {}

        def ensure(a: str, b: str) -> _PairEvidence | None:
            if not a or not b or a == b or a not in self.project.parts or b not in self.project.parts:
                return None
            key = tuple(sorted((a, b)))
            if key not in pairs:
                pairs[key] = _PairEvidence(a=key[0], b=key[1])
            return pairs[key]

        for assembly in self.project.assemblies.values():
            main = str(assembly.main_part_id or "")
            if not main:
                continue
            for secondary in assembly.part_ids:
                if secondary == main:
                    continue
                pair = ensure(main, secondary)
                if pair is None:
                    continue
                pair.assembly_ids.add(assembly.internal_id)
                pair.assembly_main_ids.add(main)
                pair.sources.add("assembly_main_secondary")

        for weld in self.project.welds.values():
            ids = [str(item) for item in weld.connected_part_ids if str(item) in self.project.parts]
            for index, a in enumerate(ids):
                for b in ids[index + 1 :]:
                    pair = ensure(a, b)
                    if pair is not None:
                        pair.weld_ids.add(weld.internal_id)
                        pair.sources.add("weld_relation")

        for fastener in self.project.fasteners.values():
            ids = [str(item) for item in fastener.connected_part_ids if str(item) in self.project.parts]
            for index, a in enumerate(ids):
                for b in ids[index + 1 :]:
                    pair = ensure(a, b)
                    if pair is not None:
                        pair.fastener_ids.add(fastener.internal_id)
                        pair.sources.add("fastener_relation")

        return tuple(pairs[key] for key in sorted(pairs))

    @staticmethod
    def _face_by_index(report: FaceResolutionReport, index: int) -> ManufacturingFace | None:
        ref = f"canonical_brep:face:{index}"
        return next((face for face in report.faces if face.source_geometry_ref == ref), None)

    def _contact_for_pair(self, pair: _PairEvidence) -> tuple[ContactPatch | None, tuple[str, ...], tuple[str, ...]]:
        main_secondary = pair.main_secondary()
        if main_secondary is None:
            return None, (CONTACT_AMBIGUOUS,), (f"Pair {pair.a}/{pair.b} heeft conflicterende assembly-main relaties.",)
        main_id, secondary_id = main_secondary
        left = self._world_shape(main_id)
        right = self._world_shape(secondary_id)
        penetration = _solid_common_volume(left, right)
        if penetration > self.penetration_tolerance_mm3:
            return None, (CONTACT_WRONG_GEOMETRY,), (
                f"{main_id}/{secondary_id} penetreert {penetration:.6f} mm³; contactvlak wordt niet afgeleid.",
            )
        gap = _distance(left, right)
        if gap is None:
            return None, (CONTACT_NOT_FOUND,), (f"Exacte minimumafstand voor {main_id}/{secondary_id} kon niet worden bepaald.",)
        if gap > self.contact_tolerance_mm:
            message = (
                f"{main_id}/{secondary_id} heeft {gap:.4f} mm afstand; "
                f"contacttolerantie is {self.contact_tolerance_mm:.4f} mm."
            )
            return None, (CONTACT_NOT_FOUND,) if pair.explicit else (), (message,)

        best: tuple[float, int, int, cq.Face] | None = None
        for main_index, main_face in self._world_face_shapes(main_id):
            for secondary_index, secondary_face in self._world_face_shapes(secondary_id):
                common, area = _common_face(main_face, secondary_face)
                if common is not None and (best is None or area > best[0]):
                    best = (area, main_index, secondary_index, common)
        if best is None:
            message = (
                f"{main_id}/{secondary_id} ligt binnen afstandstolerantie maar heeft geen exact 2D BREP-contactvlak; "
                "punt-/randcontact wordt niet naar scribing opgewaardeerd."
            )
            return None, (CONTACT_NOT_FOUND,) if pair.explicit else (), (message,)

        area, main_index, secondary_index, common_face = best
        main_report = self._face_report(main_id)
        secondary_report = self._face_report(secondary_id)
        main_face = self._face_by_index(main_report, main_index)
        secondary_face = self._face_by_index(secondary_report, secondary_index)
        if main_face is None or secondary_face is None:
            return None, (CONTACT_AMBIGUOUS,), ("Exact contactoppervlak kon niet naar canonical ManufacturingFace IDs worden gekoppeld.",)

        world_loops = tuple(loop for loop in (_wire_loop(wire) for wire in common_face.Wires()) if loop)
        if not world_loops:
            return None, (CONTACT_AMBIGUOUS,), ("Exact contactoppervlak bevat geen bruikbare gesloten boundary-loop.",)
        main_matrix = self.project.parts[main_id].global_placement.matrix
        secondary_matrix = self.project.parts[secondary_id].global_placement.matrix
        main_projected: list[tuple[tuple[float, float], ...]] = []
        secondary_projected: list[tuple[tuple[float, float], ...]] = []
        for loop in world_loops:
            main_loop: list[tuple[float, float]] = []
            secondary_loop: list[tuple[float, float]] = []
            for point in loop:
                main_local = _world_to_local(main_matrix, point)
                secondary_local = _world_to_local(secondary_matrix, point)
                main_uvn = main_face.local_frame.to_local(main_local)
                secondary_uvn = secondary_face.local_frame.to_local(secondary_local)
                if abs(main_uvn[2]) > 2e-4 or abs(secondary_uvn[2]) > 2e-4:
                    return None, (CONTACT_WRONG_GEOMETRY,), ("Contactboundary ligt niet op beide gekozen canonical face-frames.",)
                main_loop.append((main_uvn[0], main_uvn[1]))
                secondary_loop.append((secondary_uvn[0], secondary_uvn[1]))
            main_projected.append(tuple(main_loop))
            secondary_projected.append(tuple(secondary_loop))

        relation_type = (
            ContactRelationType.WELDED_CONTACT
            if pair.weld_ids
            else ContactRelationType.BOLTED_CONTACT
            if pair.fastener_ids
            else ContactRelationType.PROJECTED_ATTACHMENT
            if pair.assembly_ids
            else ContactRelationType.GEOMETRIC_TOUCH
        )
        local_identity = {
            "main": main_id,
            "secondary": secondary_id,
            "main_face": main_face.face_id,
            "secondary_face": secondary_face.face_id,
            "relation_type": relation_type.value,
            "main_boundary": main_projected,
            "secondary_boundary": secondary_projected,
            "area_mm2": round(area, 6),
        }
        contact_id = "CP-" + stable_sha256({"assembly_ids": sorted(pair.assembly_ids), **local_identity})[:20].upper()
        patch = ContactPatch(
            contact_id=contact_id,
            assembly_id=sorted(pair.assembly_ids)[0] if pair.assembly_ids else "",
            main_part_id=main_id,
            secondary_part_id=secondary_id,
            main_face_id=main_face.face_id,
            secondary_face_id=secondary_face.face_id,
            source_relation=tuple(sorted(pair.sources)),
            relation_type=relation_type,
            exact_boundary_world_mm=world_loops,
            projected_boundary_main_2d=tuple(main_projected),
            projected_boundary_secondary_2d=tuple(secondary_projected),
            area_mm2=area,
            gap_mm=gap,
            penetration_mm3=penetration,
            weld_ids=tuple(sorted(pair.weld_ids)),
            fastener_ids=tuple(sorted(pair.fastener_ids)),
            proof_status="verified",
            tolerance_profile={
                "contact_tolerance_mm": self.contact_tolerance_mm,
                "penetration_tolerance_mm3": self.penetration_tolerance_mm3,
            },
            provenance={
                "algorithm": "cws-exact-contact-1.0",
                "geometry_source": "canonical_occt_brep",
                "relation_sources": sorted(pair.sources),
                "no_global_n_squared_scan": True,
                "face_mapping": "canonical_local_face_index_transformed_individually",
            },
        )
        return patch, (), ()

    def resolve(self) -> ContactResolutionReport:
        patches: list[ContactPatch] = []
        blockers: list[str] = []
        warnings: list[str] = []
        candidates = self.candidate_pairs()
        for pair in candidates:
            try:
                patch, pair_blockers, pair_warnings = self._contact_for_pair(pair)
            except Exception as exc:
                patch, pair_blockers, pair_warnings = None, (CONTACT_WRONG_GEOMETRY,), (
                    f"Exacte contactanalyse {pair.a}/{pair.b} mislukte fail-closed: {type(exc).__name__}: {exc}",
                )
            if patch is not None:
                patches.append(patch)
            blockers.extend(pair_blockers)
            warnings.extend(pair_warnings)
        patches.sort(key=lambda item: (item.assembly_id, item.main_part_id, item.secondary_part_id, item.contact_id))
        return ContactResolutionReport.create(
            project_id=self.project.project_id,
            candidate_pairs=tuple(pair.key for pair in candidates),
            patches=tuple(patches),
            blocking_codes=tuple(blockers),
            warnings=tuple(warnings),
            contact_tolerance_mm=self.contact_tolerance_mm,
            penetration_tolerance_mm3=self.penetration_tolerance_mm3,
        )


class ContactPatchValidator:
    """Independent projection and face-reference validation."""

    def validate(
        self,
        project: ProjectModel,
        report: ContactResolutionReport,
        face_reports: Mapping[str, FaceResolutionReport],
        *,
        tolerance_mm: float = 1e-4,
    ) -> tuple[str, ...]:
        issues: list[str] = []
        seen: set[str] = set()
        for patch in report.patches:
            if patch.contact_id in seen:
                issues.append(f"CWS-MARK-002: dubbel contact-ID {patch.contact_id}")
            seen.add(patch.contact_id)
            main_report = face_reports.get(patch.main_part_id)
            secondary_report = face_reports.get(patch.secondary_part_id)
            if main_report is None or secondary_report is None:
                issues.append(f"CWS-MARK-001: face report ontbreekt voor {patch.contact_id}")
                continue
            main_face = next((face for face in main_report.faces if face.face_id == patch.main_face_id), None)
            secondary_face = next((face for face in secondary_report.faces if face.face_id == patch.secondary_face_id), None)
            if main_face is None or secondary_face is None:
                issues.append(f"CWS-MARK-002: face referentie ontbreekt voor {patch.contact_id}")
                continue
            if patch.penetration_mm3 > report.penetration_tolerance_mm3:
                issues.append(f"CWS-MARK-005: penetratie in {patch.contact_id}")
            if patch.gap_mm > report.contact_tolerance_mm + tolerance_mm:
                issues.append(f"CWS-MARK-004: gap buiten tolerantie in {patch.contact_id}")
            if len(patch.exact_boundary_world_mm) != len(patch.projected_boundary_main_2d) or len(patch.exact_boundary_world_mm) != len(patch.projected_boundary_secondary_2d):
                issues.append(f"CWS-MARK-005: boundary loop count mismatch {patch.contact_id}")
                continue
            main_matrix = project.parts[patch.main_part_id].global_placement.matrix
            secondary_matrix = project.parts[patch.secondary_part_id].global_placement.matrix
            for world_loop, main_loop, secondary_loop in zip(
                patch.exact_boundary_world_mm,
                patch.projected_boundary_main_2d,
                patch.projected_boundary_secondary_2d,
            ):
                if not (len(world_loop) == len(main_loop) == len(secondary_loop)):
                    issues.append(f"CWS-MARK-005: boundary point count mismatch {patch.contact_id}")
                    continue
                for world, main_uv, secondary_uv in zip(world_loop, main_loop, secondary_loop):
                    main_local = main_face.local_frame.from_local(main_uv[0], main_uv[1], 0.0)
                    secondary_local = secondary_face.local_frame.from_local(secondary_uv[0], secondary_uv[1], 0.0)
                    main_world = _local_to_world(main_matrix, main_local)
                    secondary_world = _local_to_world(secondary_matrix, secondary_local)
                    if math.dist(main_world, world) > tolerance_mm:
                        issues.append(f"CWS-MARK-005: main projection mismatch {patch.contact_id}")
                        break
                    if math.dist(secondary_world, world) > tolerance_mm:
                        issues.append(f"CWS-MARK-005: secondary projection mismatch {patch.contact_id}")
                        break
        return tuple(issues)


class ContactGeometryService:
    def __init__(self, project: ProjectModel, **engine_kwargs: Any) -> None:
        self.project = project
        self.engine = ExactContactGeometryEngine(project, **engine_kwargs)
        self.validator = ContactPatchValidator()

    def build(self, *, persist: bool = False) -> ContactResolutionReport:
        report = self.engine.resolve()
        validation = self.validator.validate(self.project, report, self.engine.face_reports)
        if validation:
            report = ContactResolutionReport.create(
                project_id=report.project_id,
                candidate_pairs=report.candidate_pairs,
                patches=report.patches,
                blocking_codes=tuple(report.blocking_codes) + tuple(item.split(":", 1)[0] for item in validation),
                warnings=tuple(report.warnings) + validation,
                contact_tolerance_mm=report.contact_tolerance_mm,
                penetration_tolerance_mm3=report.penetration_tolerance_mm3,
                algorithm_version=report.algorithm_version,
            )
        if persist:
            self.project.settings["manufacturing_contacts"] = {
                "schema": "cws-contact-store-1.0",
                "report_sha256": report.report_sha256,
                "report": report.to_dict(),
                "production_marking_released": False,
            }
        return report


__all__ = [
    "ExactContactGeometryEngine",
    "ContactPatchValidator",
    "ContactGeometryService",
    "CONTACT_NOT_FOUND",
    "CONTACT_WRONG_GEOMETRY",
    "CONTACT_AMBIGUOUS",
]
