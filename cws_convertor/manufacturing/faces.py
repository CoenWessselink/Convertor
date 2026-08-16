"""Deterministic ManufacturingFace extraction from reviewed canonical solids."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable

import cadquery as cq

from cws_convertor.project.canonical_rebuild import CanonicalRebuildError, build_canonical_shape
from cws_convertor.project.model import Part, ProjectValidationError, stable_sha256
from cws_convertor.project.workbench import validate_workbench_state

from .faces_model import (
    MANUFACTURING_FACE_ALGORITHM,
    FaceLocalFrame,
    FaceProofStatus,
    FaceResolutionReport,
    ManufacturingFace,
    ManufacturingFaceRole,
    SurfaceType,
)

CWS_FACE_MISSING_WORKBENCH = "CWS-MARK-001"
CWS_FACE_AMBIGUOUS_ROLE = "CWS-MARK-002"
CWS_FACE_NONPLANAR_UNSUPPORTED = "CWS-MARK-003"

NORMAL_TOLERANCE = 1e-6
POSITION_TOLERANCE_MIN_MM = 1e-5


def _tuple3(vector: Any) -> tuple[float, float, float]:
    return (float(vector.x), float(vector.y), float(vector.z))


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(left * right for left, right in zip(a, b))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _normalise(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = _length(vector)
    if length <= 1e-12:
        raise ValueError("Nulvector kan niet worden genormaliseerd")
    return tuple(value / length for value in vector)


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[index] - b[index] for index in range(3))


def _quant(value: float, digits: int = 7) -> float:
    return round(float(value), digits)


def _surface_type(face: cq.Face) -> SurfaceType:
    geom = str(face.geomType() or "").upper()
    if geom == "PLANE":
        return SurfaceType.PLANE
    if geom == "CYLINDER":
        return SurfaceType.CYLINDER
    if geom == "CONE":
        return SurfaceType.CONE
    if geom in {"SPHERE", "TORUS", "BSPLINE", "BEZIER"}:
        return SurfaceType.ANALYTIC_OTHER
    return SurfaceType.UNSUPPORTED


def _frame_for_face(face: cq.Face, surface: SurfaceType) -> FaceLocalFrame:
    origin = _tuple3(face.Center())
    if surface == SurfaceType.PLANE:
        normal = _normalise(_tuple3(face.normalAt()))
    else:
        # For a cylindrical/other surface this frame is only a local review
        # anchor; it is never advertised as a flat manufacturing map.
        try:
            normal = _normalise(_tuple3(face.normalAt()))
        except Exception:
            normal = (0.0, 0.0, 1.0)

    # Production X is preferred for every longitudinal surface. End faces use
    # +Y as deterministic tangent. This keeps frames placement-independent.
    preferred = (1.0, 0.0, 0.0)
    if abs(_dot(preferred, normal)) > 0.95:
        preferred = (0.0, 1.0, 0.0)
    projection = tuple(preferred[index] - _dot(preferred, normal) * normal[index] for index in range(3))
    if _length(projection) <= 1e-10:
        preferred = (0.0, 0.0, 1.0)
        projection = tuple(preferred[index] - _dot(preferred, normal) * normal[index] for index in range(3))
    u_axis = _normalise(projection)
    v_axis = _normalise(_cross(normal, u_axis))
    # u x v = n for v = n x u.
    return FaceLocalFrame(origin_mm=origin, u_axis=u_axis, v_axis=v_axis, normal=normal)


def _sample_edge(edge: cq.Edge) -> list[tuple[float, float, float]]:
    geom = str(edge.geomType() or "").upper()
    if geom == "LINE":
        vertices = edge.Vertices()
        if len(vertices) >= 2:
            return [_tuple3(vertices[0].Center()), _tuple3(vertices[-1].Center())]
    # Analytical curves remain analytical in the BREP. This sampled outline is
    # strictly a viewer/persistence aid and is excluded from face truth claims.
    count = 24 if geom in {"CIRCLE", "ELLIPSE"} else 16
    return [_tuple3(edge.positionAt(index / count)) for index in range(count + 1)]


def _wire_points(wire: cq.Wire) -> tuple[tuple[float, float, float], ...]:
    result: list[tuple[float, float, float]] = []
    for edge in wire.Edges():
        for point in _sample_edge(edge):
            if result and math.dist(result[-1], point) <= 1e-8:
                continue
            result.append(point)
    if result and math.dist(result[0], result[-1]) > 1e-8:
        result.append(result[0])
    return tuple(result)


def _boundary_loops(face: cq.Face, frame: FaceLocalFrame) -> tuple[
    tuple[tuple[float, float], ...],
    tuple[tuple[tuple[float, float, float], ...], ...],
]:
    loops_xyz: list[tuple[tuple[float, float, float], ...]] = []
    loops_2d: list[tuple[tuple[float, float], ...]] = []
    for wire in face.Wires():
        xyz = _wire_points(wire)
        if not xyz:
            continue
        loops_xyz.append(xyz)
        loops_2d.append(tuple((frame.to_local(point)[0], frame.to_local(point)[1]) for point in xyz))
    return tuple(loops_2d), tuple(loops_xyz)


@dataclass(slots=True)
class _FaceInfo:
    index: int
    face: cq.Face
    surface: SurfaceType
    normal: tuple[float, float, float]
    center: tuple[float, float, float]
    area: float
    bbox: tuple[float, float, float, float, float, float]
    role: ManufacturingFaceRole = ManufacturingFaceRole.CUSTOM
    canonical_kind: str = "unclassified"
    dstv_candidates: tuple[str, ...] = ()
    confidence: float = 1.0
    proof_status: FaceProofStatus = FaceProofStatus.VERIFIED
    orientation_class: str = ""


def _face_info(index: int, face: cq.Face) -> _FaceInfo:
    surface = _surface_type(face)
    center = _tuple3(face.Center())
    bounds = face.BoundingBox()
    bbox = (
        float(bounds.xmin), float(bounds.xmax),
        float(bounds.ymin), float(bounds.ymax),
        float(bounds.zmin), float(bounds.zmax),
    )
    try:
        normal = _normalise(_tuple3(face.normalAt()))
    except Exception:
        normal = (0.0, 0.0, 0.0)
    return _FaceInfo(
        index=index,
        face=face,
        surface=surface,
        normal=normal,
        center=center,
        area=float(face.Area()),
        bbox=bbox,
    )


def _axis(normal: tuple[float, float, float]) -> tuple[str, int] | None:
    values = (abs(normal[0]), abs(normal[1]), abs(normal[2]))
    maximum = max(values)
    if maximum < 1.0 - NORMAL_TOLERANCE:
        return None
    index = values.index(maximum)
    return ("xyz"[index], 1 if normal[index] >= 0.0 else -1)


def _is_near(value: float, target: float, span: float) -> bool:
    return abs(value - target) <= max(POSITION_TOLERANCE_MIN_MM, abs(span) * 2e-6)


def _assign_end_faces(infos: list[_FaceInfo], xmin: float, xmax: float, xspan: float) -> None:
    for info in infos:
        if info.surface != SurfaceType.PLANE:
            continue
        axis = _axis(info.normal)
        if axis == ("x", -1) and _is_near(info.center[0], xmin, xspan):
            info.role = ManufacturingFaceRole.END_START
            info.canonical_kind = "part_end_start"
            info.orientation_class = "transverse_end"
        elif axis == ("x", 1) and _is_near(info.center[0], xmax, xspan):
            info.role = ManufacturingFaceRole.END_FINISH
            info.canonical_kind = "part_end_finish"
            info.orientation_class = "transverse_end"


def _largest_axis_face(
    infos: list[_FaceInfo],
    axis_name: str,
    sign: int,
    *,
    exclude_extreme: tuple[float, float, float] | None = None,
) -> _FaceInfo | None:
    candidates = [
        info for info in infos
        if info.surface == SurfaceType.PLANE
        and info.role == ManufacturingFaceRole.CUSTOM
        and _axis(info.normal) == (axis_name, sign)
    ]
    if exclude_extreme is not None:
        lo, hi, span = exclude_extreme
        center_index = {"x": 0, "y": 1, "z": 2}[axis_name]
        interior = [
            info for info in candidates
            if not _is_near(info.center[center_index], lo, span)
            and not _is_near(info.center[center_index], hi, span)
        ]
        if interior:
            candidates = interior
    return max(candidates, key=lambda item: item.area, default=None)


def _assign_i_faces(infos: list[_FaceInfo], bounds: cq.BoundBox) -> None:
    yspan, zspan = float(bounds.ylen), float(bounds.zlen)
    for info in infos:
        if info.surface != SurfaceType.PLANE or info.role != ManufacturingFaceRole.CUSTOM:
            continue
        axis = _axis(info.normal)
        if axis == ("z", 1):
            if _is_near(info.center[2], float(bounds.zmax), zspan):
                info.role, info.canonical_kind = ManufacturingFaceRole.TOP_OUTER, "top_flange_outer"
                info.dstv_candidates = ("o",)
            else:
                info.role, info.canonical_kind = ManufacturingFaceRole.BOTTOM_INNER, "bottom_flange_inner"
        elif axis == ("z", -1):
            if _is_near(info.center[2], float(bounds.zmin), zspan):
                info.role, info.canonical_kind = ManufacturingFaceRole.BOTTOM_OUTER, "bottom_flange_outer"
                info.dstv_candidates = ("u",)
            else:
                info.role, info.canonical_kind = ManufacturingFaceRole.TOP_INNER, "top_flange_inner"
    for sign, role in ((-1, ManufacturingFaceRole.WEB_LEFT), (1, ManufacturingFaceRole.WEB_RIGHT)):
        face = _largest_axis_face(
            infos,
            "y",
            sign,
            exclude_extreme=(float(bounds.ymin), float(bounds.ymax), yspan),
        )
        if face is not None:
            face.role = role
            face.canonical_kind = "web_planar_side"
            face.dstv_candidates = ("v", "h")
            face.proof_status = FaceProofStatus.REVIEW_REQUIRED
            face.confidence = 0.95


def _assign_u_faces(infos: list[_FaceInfo], bounds: cq.BoundBox) -> None:
    zspan = float(bounds.zlen)
    for info in infos:
        if info.surface != SurfaceType.PLANE or info.role != ManufacturingFaceRole.CUSTOM:
            continue
        axis = _axis(info.normal)
        if axis == ("z", 1):
            if _is_near(info.center[2], float(bounds.zmax), zspan):
                info.role, info.canonical_kind = ManufacturingFaceRole.TOP_OUTER, "upper_flange_outer"
                info.dstv_candidates = ("o",)
            else:
                info.role, info.canonical_kind = ManufacturingFaceRole.BOTTOM_INNER, "lower_flange_inner"
        elif axis == ("z", -1):
            if _is_near(info.center[2], float(bounds.zmin), zspan):
                info.role, info.canonical_kind = ManufacturingFaceRole.BOTTOM_OUTER, "lower_flange_outer"
                info.dstv_candidates = ("u",)
            else:
                info.role, info.canonical_kind = ManufacturingFaceRole.TOP_INNER, "upper_flange_inner"
    for sign, role, kind in (
        (-1, ManufacturingFaceRole.WEB_LEFT, "channel_web_outer"),
        (1, ManufacturingFaceRole.WEB_RIGHT, "channel_web_inner"),
    ):
        face = _largest_axis_face(infos, "y", sign)
        if face is not None:
            face.role = role
            face.canonical_kind = kind
            face.dstv_candidates = ("v", "h")
            face.proof_status = FaceProofStatus.REVIEW_REQUIRED
            face.confidence = 0.95


def _assign_l_faces(infos: list[_FaceInfo]) -> None:
    vertical = _largest_axis_face(infos, "y", -1)
    horizontal = _largest_axis_face(infos, "z", -1)
    if vertical is not None:
        vertical.role = ManufacturingFaceRole.LEG_A_OUTER
        vertical.canonical_kind = "angle_vertical_leg_outer"
        vertical.dstv_candidates = ("v", "h")
        vertical.proof_status = FaceProofStatus.REVIEW_REQUIRED
        vertical.confidence = 0.95
    if horizontal is not None:
        horizontal.role = ManufacturingFaceRole.LEG_B_OUTER
        horizontal.canonical_kind = "angle_horizontal_leg_outer"
        horizontal.dstv_candidates = ("o", "u")
        horizontal.proof_status = FaceProofStatus.REVIEW_REQUIRED
        horizontal.confidence = 0.95


def _assign_m_faces(infos: list[_FaceInfo], bounds: cq.BoundBox) -> None:
    spans = {"y": float(bounds.ylen), "z": float(bounds.zlen)}
    limits = {
        "y": (float(bounds.ymin), float(bounds.ymax)),
        "z": (float(bounds.zmin), float(bounds.zmax)),
    }
    mapping = {
        ("z", 1): (ManufacturingFaceRole.TOP_OUTER, "box_top_outer", ("o",)),
        ("z", -1): (ManufacturingFaceRole.BOTTOM_OUTER, "box_bottom_outer", ("u",)),
        ("y", -1): (ManufacturingFaceRole.LONGITUDINAL_PRIMARY, "box_side_a_outer", ("v",)),
        ("y", 1): (ManufacturingFaceRole.LONGITUDINAL_SECONDARY, "box_side_b_outer", ("h",)),
    }
    for info in infos:
        if info.surface != SurfaceType.PLANE or info.role != ManufacturingFaceRole.CUSTOM:
            continue
        axis = _axis(info.normal)
        if axis not in mapping:
            continue
        axis_name, sign = axis
        center_index = 1 if axis_name == "y" else 2
        target = limits[axis_name][1 if sign > 0 else 0]
        if not _is_near(info.center[center_index], target, spans[axis_name]):
            info.canonical_kind = "box_inner_wall"
            continue
        role, kind, dstv = mapping[axis]
        info.role, info.canonical_kind, info.dstv_candidates = role, kind, dstv


def _assign_plate_faces(infos: list[_FaceInfo], bounds: cq.BoundBox) -> None:
    zspan = float(bounds.zlen)
    for info in infos:
        if info.surface != SurfaceType.PLANE or info.role != ManufacturingFaceRole.CUSTOM:
            continue
        axis = _axis(info.normal)
        if axis == ("z", 1) and _is_near(info.center[2], float(bounds.zmax), zspan):
            info.role = ManufacturingFaceRole.PLATE_FRONT
            info.canonical_kind = "plate_front"
            info.dstv_candidates = ("v", "h")
            info.proof_status = FaceProofStatus.REVIEW_REQUIRED
            info.confidence = 0.95
        elif axis == ("z", -1) and _is_near(info.center[2], float(bounds.zmin), zspan):
            info.role = ManufacturingFaceRole.PLATE_BACK
            info.canonical_kind = "plate_back"
            info.dstv_candidates = ("v", "h")
            info.proof_status = FaceProofStatus.REVIEW_REQUIRED
            info.confidence = 0.95
        else:
            info.canonical_kind = "plate_edge"


def _assign_round_faces(infos: list[_FaceInfo]) -> None:
    for info in infos:
        if info.role != ManufacturingFaceRole.CUSTOM:
            continue
        if info.surface == SurfaceType.CYLINDER:
            info.role = ManufacturingFaceRole.ROUND_SURFACE
            info.canonical_kind = "round_longitudinal_surface"
            info.orientation_class = "rotational"
            info.dstv_candidates = ()
            info.proof_status = FaceProofStatus.REVIEW_REQUIRED
            info.confidence = 0.90


def _assign_generic_kinds(infos: list[_FaceInfo]) -> None:
    for info in infos:
        if info.canonical_kind != "unclassified":
            continue
        if info.surface == SurfaceType.PLANE:
            axis = _axis(info.normal)
            info.canonical_kind = "planar_custom" if axis else "planar_oblique_custom"
            info.orientation_class = "longitudinal" if axis and axis[0] != "x" else "custom"
        elif info.surface == SurfaceType.CYLINDER:
            info.canonical_kind = "cylindrical_custom"
            info.orientation_class = "rotational"
        else:
            info.canonical_kind = f"{info.surface.value}_custom"
            info.proof_status = FaceProofStatus.REVIEW_REQUIRED
            info.confidence = min(info.confidence, 0.80)


def _confirmed_side_map(part: Part) -> dict[str, str]:
    if not part.workbench:
        return {}
    revision = dict(part.workbench.get("current_revision") or {})
    result: dict[str, str] = {}
    for item in list(revision.get("reference_sides") or []):
        if not bool(item.get("confirmed")):
            continue
        side = str(item.get("side_id") or "").lower()
        face_ref = str(item.get("face_ref") or "")
        if side in {"v", "h", "o", "u"} and face_ref:
            result[face_ref] = side
    return result


def _face_geometry_fingerprint(info: _FaceInfo, frame: FaceLocalFrame) -> dict[str, Any]:
    return {
        "surface_type": info.surface.value,
        "normal": [_quant(value) for value in info.normal],
        "center": [_quant(value) for value in info.center],
        "area_mm2": _quant(info.area, 5),
        "bbox": [_quant(value, 5) for value in info.bbox],
        "frame": frame.to_dict(),
    }


class ManufacturingFaceResolver:
    def resolve(self, part: Part, *, shape: cq.Shape | None = None) -> FaceResolutionReport:
        if not part.workbench:
            return FaceResolutionReport.create(
                part_id=part.internal_id,
                source_geometry_hash=part.geometry_hash,
                manufacturing_hash=part.manufacturing_hash,
                profile_type=part.profile_type,
                part_form="unknown",
                faces=(),
                blocking_codes=(CWS_FACE_MISSING_WORKBENCH,),
                warnings=("Part Workbench ontbreekt; manufacturing faces worden niet gegokt.",),
            )
        validate_workbench_state(part, part.workbench)
        revision = dict(part.workbench.get("current_revision") or {})
        part_form = str(revision.get("part_form") or "unknown")
        source_geometry_hash = str(
            dict(part.workbench.get("source_geometry") or {}).get("source_geometry_hash")
            or part.geometry_hash
        )
        warnings: list[str] = []
        if shape is None:
            try:
                shape, build_warnings, _payload = build_canonical_shape(part)
                warnings.extend(build_warnings)
            except (CanonicalRebuildError, ProjectValidationError, ValueError) as exc:
                return FaceResolutionReport.create(
                    part_id=part.internal_id,
                    source_geometry_hash=source_geometry_hash,
                    manufacturing_hash=part.manufacturing_hash,
                    profile_type=part.profile_type,
                    part_form=part_form,
                    faces=(),
                    blocking_codes=(CWS_FACE_MISSING_WORKBENCH,),
                    warnings=(f"Canonical solid kon niet veilig worden opgebouwd: {exc}",),
                )
        if shape is None or shape.isNull() or not shape.isValid() or len(shape.Solids()) != 1:
            raise ProjectValidationError("ManufacturingFace resolver vereist exact één geldig canonical solid")

        bounds = shape.BoundingBox()
        infos = [_face_info(index, face) for index, face in enumerate(shape.Faces(), start=1)]
        _assign_end_faces(infos, float(bounds.xmin), float(bounds.xmax), float(bounds.xlen))

        profile_type = str(part.profile_type or "").upper()
        if part_form == "plate" or profile_type == "B":
            _assign_plate_faces(infos, bounds)
        elif profile_type == "I":
            _assign_i_faces(infos, bounds)
        elif profile_type in {"U", "C"}:
            _assign_u_faces(infos, bounds)
        elif profile_type == "L":
            _assign_l_faces(infos)
        elif profile_type in {"M", "RHS", "SHS"}:
            _assign_m_faces(infos, bounds)
        elif profile_type in {"RO", "RU", "CHS"} or part_form == "round_bar":
            _assign_round_faces(infos)
        elif part_form == "custom":
            warnings.append("Custom profiel: vlakrollen blijven custom tot expliciete gebruikersmapping.")
        else:
            warnings.append(
                f"Profieltype {profile_type or '?'} heeft geen bewezen semantische face-mapper; vlakrollen blijven custom."
            )
        _assign_generic_kinds(infos)

        confirmed = _confirmed_side_map(part)
        faces: list[ManufacturingFace] = []
        for info in infos:
            frame = _frame_for_face(info.face, info.surface)
            loops_2d, loops_xyz = _boundary_loops(info.face, frame)
            source_ref = f"canonical_brep:face:{info.index}"
            candidates = info.dstv_candidates
            exact_side = confirmed.get(source_ref)
            proof_status = info.proof_status
            confidence = info.confidence
            if exact_side:
                candidates = (exact_side,)
                proof_status = FaceProofStatus.VERIFIED
                confidence = 1.0
            fingerprint = _face_geometry_fingerprint(info, frame)
            geometry_hash = stable_sha256(fingerprint)
            face_id = "MF-" + stable_sha256(
                {
                    "part_id": part.internal_id,
                    "source_geometry_hash": source_geometry_hash,
                    "face": fingerprint,
                }
            )[:20].upper()
            faces.append(
                ManufacturingFace(
                    face_id=face_id,
                    part_id=part.internal_id,
                    semantic_role=info.role,
                    canonical_kind=info.canonical_kind,
                    source_geometry_ref=source_ref,
                    local_frame=frame,
                    surface_type=info.surface,
                    boundary_loops_2d=loops_2d,
                    outline_loops_part_mm=loops_xyz,
                    area_mm2=info.area,
                    orientation_class=info.orientation_class,
                    material_side="outer" if "outer" in info.canonical_kind else ("inner" if "inner" in info.canonical_kind else ""),
                    accessible_from=(info.role.value,) if info.role != ManufacturingFaceRole.CUSTOM else (),
                    dstv_side_candidates=candidates,
                    confidence=confidence,
                    proof_status=proof_status,
                    provenance={
                        "algorithm": MANUFACTURING_FACE_ALGORITHM,
                        "source_geometry_hash": source_geometry_hash,
                        "canonical_brep_face_index": info.index,
                        "dstv_mapping_confirmed": bool(exact_side),
                        "sampled_outline_is_display_only": True,
                    },
                    geometry_hash=geometry_hash,
                )
            )
        faces.sort(key=lambda item: (item.semantic_role.value, item.canonical_kind, item.face_id))
        return FaceResolutionReport.create(
            part_id=part.internal_id,
            source_geometry_hash=source_geometry_hash,
            manufacturing_hash=part.manufacturing_hash,
            profile_type=profile_type,
            part_form=part_form,
            faces=tuple(faces),
            warnings=tuple(warnings),
        )


class ManufacturingFaceValidator:
    """Independent structural/geometric validation of a resolved face set."""

    def validate(self, part: Part, report: FaceResolutionReport) -> tuple[str, ...]:
        issues: list[str] = []
        if report.part_id != part.internal_id:
            issues.append("CWS-MARK-001: face report hoort bij een ander onderdeel")
        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()
        for face in report.faces:
            if face.face_id in seen_ids:
                issues.append(f"CWS-MARK-002: dubbel face_id {face.face_id}")
            seen_ids.add(face.face_id)
            if face.geometry_hash in seen_hashes:
                # Duplicate planar/coincident faces are never silently accepted.
                issues.append(f"CWS-MARK-002: dubbele face geometry {face.face_id}")
            seen_hashes.add(face.geometry_hash)
            try:
                face.local_frame.validate()
            except ValueError as exc:
                issues.append(f"CWS-MARK-002: {face.face_id}: {exc}")
            for loop_2d, loop_3d in zip(face.boundary_loops_2d, face.outline_loops_part_mm):
                if len(loop_2d) != len(loop_3d):
                    issues.append(f"CWS-MARK-002: {face.face_id}: 2D/3D boundary mismatch")
                    continue
                for point_2d, point_3d in zip(loop_2d, loop_3d):
                    local = face.local_frame.to_local(point_3d)
                    if abs(local[2]) > 2e-5 and face.surface_type == SurfaceType.PLANE:
                        issues.append(f"CWS-MARK-005: {face.face_id}: boundary ligt niet op vlak")
                        break
                    if math.dist((local[0], local[1]), point_2d) > 2e-5:
                        issues.append(f"CWS-MARK-005: {face.face_id}: face-local projectie mismatch")
                        break
            if face.semantic_role == ManufacturingFaceRole.ROUND_SURFACE and face.dstv_side_candidates:
                issues.append(f"CWS-MARK-010: {face.face_id}: ronde surface heeft ongeldige vlakke DSTV-mapping")
        return tuple(issues)


class DstvFaceMappingAdapter:
    """Resolve a canonical face to a DSTV side only when exactly proven."""

    def map_face(self, face: ManufacturingFace) -> dict[str, Any]:
        candidates = tuple(face.dstv_side_candidates)
        if len(candidates) == 1 and face.proof_status == FaceProofStatus.VERIFIED:
            return {
                "status": "verified",
                "face_id": face.face_id,
                "dstv_side": candidates[0],
                "blocking_code": "",
            }
        return {
            "status": "blocked",
            "face_id": face.face_id,
            "dstv_side": "",
            "candidates": list(candidates),
            "blocking_code": "CWS-MARK-010",
            "reason": "DSTV-side is niet exact en eenduidig bevestigd voor deze canonical manufacturing face",
        }


class ManufacturingFaceService:
    def __init__(self) -> None:
        self.resolver = ManufacturingFaceResolver()
        self.validator = ManufacturingFaceValidator()

    def build(self, part: Part, *, persist: bool = True) -> FaceResolutionReport:
        report = self.resolver.resolve(part)
        validation = self.validator.validate(part, report)
        if validation:
            report = FaceResolutionReport.create(
                part_id=report.part_id,
                source_geometry_hash=report.source_geometry_hash,
                manufacturing_hash=report.manufacturing_hash,
                profile_type=report.profile_type,
                part_form=report.part_form,
                faces=report.faces,
                blocking_codes=tuple(report.blocking_codes) + tuple(code.split(":", 1)[0] for code in validation),
                warnings=tuple(report.warnings) + validation,
                algorithm_version=report.algorithm_version,
            )
        if persist and part.workbench:
            part.workbench["manufacturing_faces"] = {
                "schema": "cws-manufacturing-face-store-1.0",
                "source_geometry_hash": report.source_geometry_hash,
                "manufacturing_hash": report.manufacturing_hash,
                "report_sha256": report.report_sha256,
                "status": "current" if report.passed else "blocked",
                "report": report.to_dict(),
            }
        return report

    @staticmethod
    def load_current(part: Part) -> FaceResolutionReport | None:
        raw = dict(part.workbench.get("manufacturing_faces") or {}) if part.workbench else {}
        report = dict(raw.get("report") or {})
        if not report:
            return None
        if raw.get("source_geometry_hash") != str(dict(part.workbench.get("source_geometry") or {}).get("source_geometry_hash") or part.geometry_hash):
            return None
        if raw.get("manufacturing_hash") != part.manufacturing_hash:
            return None
        faces = tuple(ManufacturingFace.from_dict(item) for item in list(report.get("faces") or []))
        return FaceResolutionReport(
            part_id=str(report.get("part_id") or part.internal_id),
            source_geometry_hash=str(report.get("source_geometry_hash") or ""),
            manufacturing_hash=str(report.get("manufacturing_hash") or ""),
            profile_type=str(report.get("profile_type") or ""),
            part_form=str(report.get("part_form") or ""),
            faces=faces,
            blocking_codes=tuple(report.get("blocking_codes") or ()),
            warnings=tuple(report.get("warnings") or ()),
            algorithm_version=str(report.get("algorithm_version") or MANUFACTURING_FACE_ALGORITHM),
            report_sha256=str(report.get("report_sha256") or ""),
        )


__all__ = [
    "ManufacturingFaceResolver",
    "ManufacturingFaceValidator",
    "DstvFaceMappingAdapter",
    "ManufacturingFaceService",
]
