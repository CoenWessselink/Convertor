"""Analytic cut-plane, section-envelope and transition geometry for phase 4.

The module works in the canonical local production frame: X is the stock/part
length axis, Y/Z span the cross-section.  A cut plane is stored as a normalized
plane ``n.x * x + n.y * y + n.z * z + d = 0``.  User-facing primary/secondary
angles are a deterministic representation of the plane slopes:

    x = tan(primary) * y + tan(secondary) * z + reference_offset

Known circles remain analytic.  Exact polygon sections use support functions on
vertices.  A bounding-rectangle fallback is explicitly marked review whenever
it could overestimate a compound-cut envelope; it is never labelled exact.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

from cws_convertor.project.model import stable_sha256
from .models import CutRequirement, CutStatus, CutTransition, OrientationVariant
from .units import LengthKernel

_EPS = 1e-12
_FACE_NORMALS = {
    "front": (0.0, 1.0, 0.0),
    "back": (0.0, -1.0, 0.0),
    "top": (0.0, 0.0, 1.0),
    "bottom": (0.0, 0.0, -1.0),
}


class AngleGeometryError(ValueError):
    """Raised when exact angle geometry cannot be established safely."""


@dataclass(frozen=True)
class CanonicalPlane:
    nx: float
    ny: float
    nz: float
    d: float
    primary_angle_deg: float
    secondary_angle_deg: float
    reference_offset_mm: float
    source: str
    plane_hash: str

    def coefficients(self) -> tuple[float, float, float, float]:
        return (self.nx, self.ny, self.nz, self.d)

    def x_function(self) -> tuple[float, float, float]:
        if abs(self.nx) <= _EPS:
            raise AngleGeometryError("Zaagvlak is parallel aan de stock-as en kan geen prismatisch uiteinde definiëren")
        return (-self.ny / self.nx, -self.nz / self.nx, -self.d / self.nx)


@dataclass(frozen=True)
class SectionSupport:
    status: str
    kind: str
    min_value_mm: float
    max_value_mm: float
    method: str
    section_hash: str
    evidence: dict[str, Any]


@dataclass(frozen=True)
class AxialEnvelope:
    status: str
    min_offset_mm: float
    max_offset_mm: float
    min_offset_units: int
    max_offset_units: int
    method: str
    evidence: dict[str, Any]
    envelope_hash: str


@dataclass(frozen=True)
class OrientationGeometry:
    variant: OrientationVariant
    start_plane: CanonicalPlane
    end_plane: CanonicalPlane
    start_envelope: AxialEnvelope
    end_envelope: AxialEnvelope


@dataclass(frozen=True)
class TransitionGeometry:
    transition: CutTransition
    left_end_envelope: AxialEnvelope
    right_start_envelope: AxialEnvelope


def _finite(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AngleGeometryError(f"Ongeldige {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise AngleGeometryError(f"{label} moet eindig zijn")
    return result


def _normalise_plane(values: Iterable[Any], *, source: str = "plane") -> CanonicalPlane:
    raw = list(values)
    if len(raw) != 4:
        raise AngleGeometryError("Zaagvlak moet exact vier plane-coëfficiënten bevatten")
    nx, ny, nz, d = (_finite(v, "plane-coëfficiënt") for v in raw)
    norm = math.sqrt(nx * nx + ny * ny + nz * nz)
    if norm <= _EPS:
        raise AngleGeometryError("Zaagvlaknormaal heeft nul lengte")
    nx, ny, nz, d = nx / norm, ny / norm, nz / norm, d / norm
    # A single canonical sign keeps hashes and angle recovery deterministic.
    if nx < -_EPS or (abs(nx) <= _EPS and (ny < -_EPS or (abs(ny) <= _EPS and nz < 0))):
        nx, ny, nz, d = -nx, -ny, -nz, -d
    if abs(nx) <= _EPS:
        raise AngleGeometryError("Zaagvlak is parallel aan de X-as")
    primary = math.degrees(math.atan(-ny / nx))
    secondary = math.degrees(math.atan(-nz / nx))
    offset = -d / nx
    payload = {
        "plane": [round(nx, 15), round(ny, 15), round(nz, 15), round(d, 15)],
        "convention": "local_xyz_unit_normal",
    }
    return CanonicalPlane(
        nx=nx, ny=ny, nz=nz, d=d,
        primary_angle_deg=primary, secondary_angle_deg=secondary,
        reference_offset_mm=offset, source=source,
        plane_hash=stable_sha256(payload),
    )


def plane_from_angles(primary_angle_deg: float, secondary_angle_deg: float, *, reference_offset_mm: float = 0.0) -> CanonicalPlane:
    primary = _finite(primary_angle_deg, "primaire zaaghoek")
    secondary = _finite(secondary_angle_deg, "secundaire zaaghoek")
    # +/-90° makes tan singular and cannot describe an end plane for a prism.
    if abs(abs(primary) - 90.0) < 1e-9 or abs(abs(secondary) - 90.0) < 1e-9:
        raise AngleGeometryError("Zaaghoek van 90° t.o.v. het normale eindvlak is niet geldig")
    a = math.tan(math.radians(primary))
    b = math.tan(math.radians(secondary))
    # x - a*y - b*z - offset = 0
    return _normalise_plane((1.0, -a, -b, -_finite(reference_offset_mm, "plane offset")), source="angles")


def canonical_plane(cut: CutRequirement | dict[str, Any], *, require_exact: bool = True) -> CanonicalPlane:
    data = asdict(cut) if isinstance(cut, CutRequirement) else dict(cut or {})
    status = str(data.get("status") or CutStatus.REVIEW.value)
    if require_exact and status != CutStatus.EXACT.value:
        raise AngleGeometryError(f"Zaagvlakstatus is {status!r}, niet exact")
    plane = list(data.get("plane") or [])
    if plane:
        canonical = _normalise_plane(plane, source="plane")
    else:
        canonical = plane_from_angles(
            data.get("primary_angle_deg", 0.0),
            data.get("secondary_angle_deg", 0.0),
            reference_offset_mm=data.get("plane_reference_offset_mm", 0.0),
        )
    return canonical


def canonicalize_cut_requirement(cut: CutRequirement, *, reference: str = "") -> CutRequirement:
    """Normalize an exact cut requirement without inventing missing geometry."""
    if reference and not cut.reference:
        cut.reference = reference
    if float(cut.finish_allowance_mm or 0.0) < 0:
        raise AngleGeometryError("Finish-/slijptoegift mag niet negatief zijn")
    if cut.status == CutStatus.EXACT.value:
        plane = canonical_plane(cut)
        cut.plane = [plane.nx, plane.ny, plane.nz, plane.d]
        cut.primary_angle_deg = plane.primary_angle_deg
        cut.secondary_angle_deg = plane.secondary_angle_deg
        cut.plane_reference_offset_mm = plane.reference_offset_mm
        cut.plane_convention = "local_xyz_unit_normal"
    cut.refresh_hash()
    return cut


def cut_support_level(cut: CutRequirement | dict[str, Any]) -> str:
    plane = canonical_plane(cut)
    p = abs(plane.primary_angle_deg)
    s = abs(plane.secondary_angle_deg)
    if p <= 1e-9 and s <= 1e-9:
        return "straight"
    if p <= 1e-9 or s <= 1e-9:
        return "single_axis_miter"
    return "compound"


def projected_kerf_mm(cut: CutRequirement | dict[str, Any], blade_thickness_mm: float) -> float:
    plane = canonical_plane(cut)
    thickness = _finite(blade_thickness_mm, "zaagbladdikte")
    if thickness < 0:
        raise AngleGeometryError("Zaagbladdikte mag niet negatief zijn")
    return thickness / abs(plane.nx)

def projected_finish_allowance_mm(cut: CutRequirement | dict[str, Any]) -> float:
    data = asdict(cut) if isinstance(cut, CutRequirement) else dict(cut or {})
    allowance = _finite(data.get("finish_allowance_mm", 0.0) or 0.0, "finish-/slijptoegift")
    if allowance < 0:
        raise AngleGeometryError("Finish-/slijptoegift mag niet negatief zijn")
    plane = canonical_plane(cut)
    return allowance / abs(plane.nx)


def _dimension(dimensions: dict[str, Any], *names: str) -> float | None:
    lowered = {str(k).strip().lower(): v for k, v in dimensions.items()}
    for name in names:
        if name.lower() in lowered:
            try:
                value = float(lowered[name.lower()])
            except (TypeError, ValueError):
                continue
            if math.isfinite(value) and value > 0:
                return value
    return None


def _profile_polygon_from_dimensions(ptype: str, dims: dict[str, Any]) -> list[tuple[float, float]] | None:
    """Return exact support vertices when standard section dimensions prove them.

    The vertices need not be ordered for a support-function calculation; all
    significant cross-section corners are sufficient.  We deliberately do not
    infer flange/web thicknesses from profile names.
    """
    width = _dimension(dims, "width", "width_mm", "b")
    height = _dimension(dims, "height", "height_mm", "h")
    tw = _dimension(dims, "web_thickness", "web_thickness_mm", "tw", "t_w")
    tf = _dimension(dims, "flange_thickness", "flange_thickness_mm", "tf", "t_f")
    t = _dimension(dims, "thickness", "thickness_mm", "t")
    if not width or not height:
        return None
    b2, h2 = width / 2.0, height / 2.0
    if ptype in {"i", "i_profile", "hea", "heb", "hem", "ipe"} and tw and tf and tw <= width and 2 * tf <= height:
        w2 = tw / 2.0
        return [
            (-b2,-h2),(b2,-h2),(b2,-h2+tf),(w2,-h2+tf),(w2,h2-tf),(b2,h2-tf),(b2,h2),(-b2,h2),
            (-b2,h2-tf),(-w2,h2-tf),(-w2,-h2+tf),(-b2,-h2+tf),
        ]
    if ptype in {"u", "u_profile", "upn", "unp", "c", "c_profile"} and tw and tf and tw <= width and 2 * tf <= height:
        left=-b2; web_right=left+tw
        return [
            (left,-h2),(b2,-h2),(b2,-h2+tf),(web_right,-h2+tf),(web_right,h2-tf),(b2,h2-tf),(b2,h2),(left,h2),
        ]
    if ptype in {"l", "l_profile", "angle"} and t and t <= min(width,height):
        left=-b2; bottom=-h2
        return [(left,bottom),(b2,bottom),(b2,bottom+t),(left+t,bottom+t),(left+t,h2),(left,h2)]
    if ptype in {"t", "t_profile"} and tw and tf and tw <= width and tf <= height:
        w2=tw/2.0
        return [(-b2,h2-tf),(b2,h2-tf),(b2,h2),(-b2,h2),(-b2,h2-tf),(-w2,h2-tf),(-w2,-h2),(w2,-h2),(w2,h2-tf)]
    return None


def _section_definition(line: dict[str, Any]) -> dict[str, Any]:
    explicit = dict(line.get("section_geometry") or {})
    if explicit:
        kind = str(explicit.get("kind") or explicit.get("type") or "").strip().lower()
        if kind in {"polygon", "wire"}:
            vertices = []
            for raw in list(explicit.get("vertices_yz") or explicit.get("vertices") or []):
                if isinstance(raw, dict):
                    y, z = raw.get("y"), raw.get("z")
                else:
                    try:
                        y, z = raw[0], raw[1]
                    except Exception:
                        raise AngleGeometryError("Section polygon bevat een ongeldig vertex")
                vertices.append((_finite(y, "section y"), _finite(z, "section z")))
            if len(vertices) < 3:
                raise AngleGeometryError("Exact section polygon vereist minimaal drie vertices")
            return {"kind": "polygon", "vertices": vertices, "status": "exact", "source": "explicit_section_geometry"}
        if kind in {"circle", "round"}:
            radius = explicit.get("radius_mm")
            if radius is None and explicit.get("diameter_mm") is not None:
                radius = float(explicit["diameter_mm"]) / 2.0
            radius = _finite(radius, "section radius")
            if radius <= 0:
                raise AngleGeometryError("Cirkelradius moet positief zijn")
            center = explicit.get("center_yz") or [0.0, 0.0]
            return {"kind": "circle", "radius": radius, "center": (_finite(center[0], "center y"), _finite(center[1], "center z")), "status": "exact", "source": "explicit_section_geometry"}
        if kind in {"rectangle", "box"}:
            width = _finite(explicit.get("width_mm"), "section width")
            height = _finite(explicit.get("height_mm"), "section height")
            if width <= 0 or height <= 0:
                raise AngleGeometryError("Rechthoeksectie vereist positieve breedte/hoogte")
            center = explicit.get("center_yz") or [0.0, 0.0]
            return {"kind": "rectangle", "width": width, "height": height, "center": (_finite(center[0], "center y"), _finite(center[1], "center z")), "status": "exact", "source": "explicit_section_geometry"}
        raise AngleGeometryError(f"Niet-ondersteund section_geometry-kind {kind!r}")

    dims = dict(line.get("profile_dimensions_mm") or {})
    ptype = str(line.get("profile_type") or "").strip().lower()
    if ptype in {"round", "round_bar", "chs", "tube", "pipe"}:
        diameter = _dimension(dims, "diameter", "diameter_mm", "outside_diameter", "outer_diameter", "d")
        if diameter:
            return {"kind": "circle", "radius": diameter / 2.0, "center": (0.0, 0.0), "status": "exact", "source": "profile_dimensions"}
    width = _dimension(dims, "width", "width_mm", "b")
    height = _dimension(dims, "height", "height_mm", "h")
    if ptype in {"flat", "strip"}:
        height = height or _dimension(dims, "thickness", "thickness_mm", "t")
        if width and height:
            return {"kind":"rectangle","width":width,"height":height,"center":(0.0,0.0),"status":"exact","source":"profile_dimensions"}
    if ptype in {"rhs", "shs", "box"} and width and height:
        return {"kind":"rectangle","width":width,"height":height,"center":(0.0,0.0),"status":"exact","source":"profile_outer_support"}
    polygon = _profile_polygon_from_dimensions(ptype, dims)
    if polygon:
        return {"kind":"polygon","vertices":polygon,"status":"exact","source":"standard_profile_dimensions"}
    # Width/height alone is enough to bound a standard section, but for an
    # open/asymmetric section it is not exact for arbitrary compound slopes.
    if width and height:
        return {"kind":"bounds","width":width,"height":height,"center":(0.0,0.0),"status":"review","source":"profile_bounds_only"}
    raise AngleGeometryError("Geen betrouwbare doorsnedegeometrie voor verstekenvelope beschikbaar")

def _support_linear(section: dict[str, Any], a: float, b: float, c: float = 0.0) -> SectionSupport:
    kind = section["kind"]
    source = str(section.get("source") or "")
    if kind == "polygon":
        values = [a * y + b * z + c for y, z in section["vertices"]]
        status, method = "exact", "polygon_vertex_support"
    elif kind in {"rectangle", "bounds"}:
        cy, cz = section.get("center", (0.0, 0.0))
        w, h = float(section["width"]), float(section["height"])
        corners = [
            (cy - w / 2.0, cz - h / 2.0),
            (cy - w / 2.0, cz + h / 2.0),
            (cy + w / 2.0, cz - h / 2.0),
            (cy + w / 2.0, cz + h / 2.0),
        ]
        values = [a * y + b * z + c for y, z in corners]
        if kind == "bounds" and abs(a) > _EPS and abs(b) > _EPS:
            status, method = "review", "conservative_bounding_rectangle"
        else:
            status, method = "exact", "rectangular_support" if kind == "rectangle" else "single_axis_bounds_support"
    elif kind == "circle":
        cy, cz = section.get("center", (0.0, 0.0))
        center_value = a * cy + b * cz + c
        radial = float(section["radius"]) * math.sqrt(a * a + b * b)
        values = [center_value - radial, center_value + radial]
        status, method = "exact", "analytic_circle_support"
    else:
        raise AngleGeometryError(f"Onbekende sectiemethode {kind!r}")
    payload = {
        "kind": kind, "status": status, "method": method,
        "min": min(values), "max": max(values), "source": source,
    }
    return SectionSupport(
        status=status, kind=kind, min_value_mm=min(values), max_value_mm=max(values),
        method=method, section_hash=stable_sha256(payload), evidence={"source": source},
    )


def axial_envelope(line: dict[str, Any], cut: CutRequirement | dict[str, Any], *, kernel: LengthKernel | None = None, require_exact: bool = True) -> AxialEnvelope:
    kernel = kernel or LengthKernel()
    plane = canonical_plane(cut, require_exact=require_exact)
    a, b, c = plane.x_function()
    section = _section_definition(line)
    support = _support_linear(section, a, b, c)
    if require_exact and support.status != "exact":
        raise AngleGeometryError("Doorsnede-envelope is alleen conservatief; exact versteknesting wordt geblokkeerd")
    min_u = kernel.signed_mm_to_units(support.min_value_mm)
    max_u = kernel.signed_mm_to_units(support.max_value_mm)
    payload = {
        "plane_hash": plane.plane_hash,
        "section_hash": support.section_hash,
        "status": support.status,
        "min_units": min_u,
        "max_units": max_u,
        "units_per_mm": kernel.units_per_mm,
    }
    return AxialEnvelope(
        status=support.status,
        min_offset_mm=support.min_value_mm,
        max_offset_mm=support.max_value_mm,
        min_offset_units=min_u,
        max_offset_units=max_u,
        method=support.method,
        evidence={"plane_hash": plane.plane_hash, "section_support": support.evidence, "section_method": support.method},
        envelope_hash=stable_sha256(payload),
    )


def _matmul3(matrix: tuple[tuple[float, float, float], ...], vector: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(sum(matrix[i][j] * vector[j] for j in range(3)) for i in range(3))  # type: ignore[return-value]


def _rotation_x(deg: float) -> tuple[tuple[float, float, float], ...]:
    r = math.radians(deg); c, s = math.cos(r), math.sin(r)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _end_for_end_matrix() -> tuple[tuple[float, float, float], ...]:
    # 180° around local Z: proper rotation, right-handed, reverses X and Y.
    return ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0))


def _matrix_mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _transform_plane_relative(plane: CanonicalPlane, matrix) -> CanonicalPlane:
    # Proper orthogonal rotation: normal transforms with R. Relative d remains.
    normal = _matmul3(matrix, (plane.nx, plane.ny, plane.nz))
    return _normalise_plane((*normal, plane.d), source="orientation_transform")


def _face_mapping(matrix) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for name, normal in _FACE_NORMALS.items():
        transformed = _matmul3(matrix, normal)
        best = max(_FACE_NORMALS.items(), key=lambda item: sum(transformed[i] * item[1][i] for i in range(3)))
        dot = sum(transformed[i] * best[1][i] for i in range(3))
        if dot >= 1.0 - 1e-8:
            mapping[name] = best[0]
    return mapping


def _parse_orientation(name: str) -> tuple[bool, float]:
    key = str(name or "as_modeled").strip().lower()
    if key in {"as_modeled", "none", "rotate_0", "rotation_0"}:
        return False, 0.0
    if key in {"end_for_end", "reversed", "reverse", "flip_end_for_end"}:
        return True, 0.0
    if key.startswith("end_for_end_rotate_"):
        return True, _finite(key.rsplit("_", 1)[-1], "oriëntatiehoek")
    if key.startswith("rotate_") or key.startswith("rotation_"):
        return False, _finite(key.rsplit("_", 1)[-1], "oriëntatiehoek")
    raise AngleGeometryError(f"Onbekende oriëntatievariant {name!r}")


def _section_vertices(section: dict[str, Any]) -> list[tuple[float, float]] | None:
    kind=section.get("kind")
    if kind=="polygon": return list(section.get("vertices") or [])
    if kind in {"rectangle","bounds"}:
        cy,cz=section.get("center",(0.0,0.0)); w=float(section["width"]); h=float(section["height"])
        return [(cy-w/2,cz-h/2),(cy-w/2,cz+h/2),(cy+w/2,cz-h/2),(cy+w/2,cz+h/2)]
    return None


def _section_invariant(line: dict[str, Any], matrix, tolerance_mm: float = 1e-6) -> tuple[bool, dict[str, Any]]:
    """Prove cross-section invariance under a proposed orientation transform."""
    try: section=_section_definition(line)
    except AngleGeometryError as exc: return False,{"method":"section_unavailable","reason":str(exc)}
    if section.get("status")!="exact": return False,{"method":"section_not_exact"}
    if section.get("kind")=="circle":
        cy,cz=section.get("center",(0.0,0.0)); transformed=_matmul3(matrix,(0.0,float(cy),float(cz)))
        ok=abs(transformed[1]-float(cy))<=tolerance_mm and abs(transformed[2]-float(cz))<=tolerance_mm
        return ok,{"method":"analytic_circle_symmetry","center_preserved":ok}
    vertices=_section_vertices(section)
    if not vertices: return False,{"method":"unsupported_symmetry_proof"}
    transformed=[]
    for y,z in vertices:
        v=_matmul3(matrix,(0.0,float(y),float(z))); transformed.append((v[1],v[2]))
    def match(point, pool):
        return any(abs(point[0]-q[0])<=tolerance_mm and abs(point[1]-q[1])<=tolerance_mm for q in pool)
    ok=all(match(v,vertices) for v in transformed) and all(match(v,transformed) for v in vertices)
    return ok,{"method":"exact_vertex_set_symmetry","vertex_count":len(vertices),"symmetric":ok}


def _angle_equivalent(value: float, allowed: Iterable[Any], tolerance: float) -> bool:
    def norm(v: float) -> float:
        return ((v % 360.0) + 360.0) % 360.0
    target = norm(value)
    for raw in allowed:
        candidate = norm(_finite(raw, "machine rotatie"))
        diff = abs(target - candidate)
        diff = min(diff, 360.0 - diff)
        if diff <= max(tolerance, 1e-8):
            return True
    return False


def build_orientation_variants(line: dict[str, Any], machine: dict[str, Any], *, kernel: LengthKernel | None = None, require_exact: bool = True) -> list[OrientationGeometry]:
    """Build only explicitly permitted, geometry-backed orientation variants."""
    kernel = kernel or LengthKernel()
    allowed = [str(v) for v in list(line.get("allowed_orientations") or ["as_modeled"])]
    machine_rotations = list(machine.get("allowed_rotations_deg") or [0.0])
    tolerance = float(machine.get("angle_tolerance_deg", 0.01) or 0.01)
    supported_sides = {str(v) for v in list(machine.get("supported_sides") or [])}
    features = list(line.get("relevant_features") or [])
    evidence_map = dict(line.get("orientation_equivalence_evidence") or {})
    output: list[OrientationGeometry] = []
    for orientation_name in sorted(set(allowed), key=lambda x: (x != "as_modeled", x)):
        try:
            end_for_end, rotation = _parse_orientation(orientation_name)
        except AngleGeometryError:
            continue
        if not _angle_equivalent(rotation, machine_rotations, tolerance):
            continue
        matrix = _rotation_x(rotation)
        if end_for_end:
            matrix = _matrix_mul(matrix, _end_for_end_matrix())
        mapping = _face_mapping(matrix)
        reachable: list[str] = []
        features_mapped = True
        for index, feature in enumerate(features):
            side = str((feature or {}).get("side") or (feature or {}).get("face") or "")
            if side:
                mapped = mapping.get(side)
                if not mapped or (supported_sides and mapped not in supported_sides):
                    features_mapped = False
                    break
            elif orientation_name != "as_modeled":
                # Rotating a feature whose side is unknown would silently change
                # production reachability.  Keep as-modelled possible but block
                # non-trivial variants.
                features_mapped = False
                break
            reachable.append(str((feature or {}).get("feature_id") or (feature or {}).get("id") or index))
        explicit_evidence = dict(evidence_map.get(orientation_name) or {})
        explicitly_blocked = explicit_evidence.get("proven") is False or explicit_evidence.get("status") == "blocked"
        section_symmetric, section_evidence = _section_invariant(line, matrix, tolerance_mm=max(float(machine.get("machine_tolerance_mm",0.1) or 0.1),1e-9))
        explicit_section_proof = bool(explicit_evidence.get("production_equivalent") is True and explicit_evidence.get("section_mapping_proven") is True)
        if orientation_name != "as_modeled" and not (section_symmetric or explicit_section_proof):
            continue
        if explicitly_blocked or not features_mapped:
            continue
        start_raw = CutRequirement(**{k: v for k, v in dict(line.get("start_cut") or {}).items() if k in CutRequirement.__dataclass_fields__})
        end_raw = CutRequirement(**{k: v for k, v in dict(line.get("end_cut") or {}).items() if k in CutRequirement.__dataclass_fields__})
        canonicalize_cut_requirement(start_raw, reference="start")
        canonicalize_cut_requirement(end_raw, reference="end")
        if end_for_end:
            old_start, old_end = start_raw, end_raw
            start_plane = _transform_plane_relative(canonical_plane(old_end), matrix)
            end_plane = _transform_plane_relative(canonical_plane(old_start), matrix)
            start_raw, end_raw = _cut_from_plane(old_end, start_plane, "start"), _cut_from_plane(old_start, end_plane, "end")
        else:
            start_plane = _transform_plane_relative(canonical_plane(start_raw), matrix)
            end_plane = _transform_plane_relative(canonical_plane(end_raw), matrix)
            start_raw, end_raw = _cut_from_plane(start_raw, start_plane, "start"), _cut_from_plane(end_raw, end_plane, "end")
        production_equivalence = "exact" if (orientation_name == "as_modeled" or features_mapped) else "review"
        variant = OrientationVariant(
            variant_id=orientation_name,
            transform={"matrix": [[round(v, 15) for v in row] for row in matrix], "convention": "part_local_to_stock_local"},
            end_for_end=end_for_end,
            rotation_about_length_deg=rotation,
            face_mapping=mapping,
            start_cut=start_raw,
            end_cut=end_raw,
            reachable_features=reachable,
            compatible_machine_ids=[str(machine.get("machine_id") or "")],
            production_equivalence=production_equivalence,
            equivalence_evidence={
                "source": "canonical_allowed_orientations",
                "all_features_mapped": features_mapped,
                "explicit": explicit_evidence,
                "section_symmetry": section_evidence,
                "section_equivalence_proven": bool(section_symmetric or explicit_section_proof),
            },
            mirrored=False,
        )
        start_env = axial_envelope(line, variant.start_cut, kernel=kernel, require_exact=require_exact)
        end_env = axial_envelope(line, variant.end_cut, kernel=kernel, require_exact=require_exact)
        if require_exact and (start_env.status != "exact" or end_env.status != "exact"):
            continue
        # Persist derived long/short-point offsets for UI/audit while keeping
        # the plane itself as the geometric source of truth.
        variant.start_cut.short_point_mm = float(start_env.min_offset_mm)
        variant.start_cut.long_point_mm = float(start_env.max_offset_mm)
        variant.end_cut.short_point_mm = float(end_env.min_offset_mm)
        variant.end_cut.long_point_mm = float(end_env.max_offset_mm)
        variant.start_cut.refresh_hash(); variant.end_cut.refresh_hash(); variant.refresh_hash()
        output.append(OrientationGeometry(variant=variant, start_plane=canonical_plane(variant.start_cut), end_plane=canonical_plane(variant.end_cut), start_envelope=start_env, end_envelope=end_env))
    return output


def _cut_from_plane(template: CutRequirement, plane: CanonicalPlane, reference: str) -> CutRequirement:
    cut = CutRequirement(**{k: v for k, v in asdict(template).items() if k in CutRequirement.__dataclass_fields__})
    cut.reference = reference
    cut.plane = [plane.nx, plane.ny, plane.nz, plane.d]
    cut.primary_angle_deg = plane.primary_angle_deg
    cut.secondary_angle_deg = plane.secondary_angle_deg
    cut.plane_reference_offset_mm = plane.reference_offset_mm
    cut.plane_convention = "local_xyz_unit_normal"
    cut.refresh_hash()
    return cut


def _support_difference(line: dict[str, Any], left: CanonicalPlane, right: CanonicalPlane, *, require_exact: bool = True) -> SectionSupport:
    la, lb, lc = left.x_function(); ra, rb, rc = right.x_function()
    section = _section_definition(line)
    support = _support_linear(section, la - ra, lb - rb, lc - rc)
    if require_exact and support.status != "exact":
        raise AngleGeometryError("Transition support is alleen conservatief; exacte sequence wordt geblokkeerd")
    return support


def _parallel_cut_slopes(left: CanonicalPlane, right: CanonicalPlane, tolerance_deg: float) -> bool:
    return (
        abs(left.primary_angle_deg - right.primary_angle_deg) <= tolerance_deg
        and abs(left.secondary_angle_deg - right.secondary_angle_deg) <= tolerance_deg
    )


def prove_common_cut(left_line: dict[str, Any], right_line: dict[str, Any], left: OrientationGeometry, right: OrientationGeometry, machine: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    angle_tol = max(float(machine.get("angle_tolerance_deg", 0.01) or 0.01), 1e-9)
    linear_tol = max(float(left.variant.end_cut.tolerance_mm or 0.0), float(right.variant.start_cut.tolerance_mm or 0.0), float(machine.get("machine_tolerance_mm", 0.1) or 0.1))
    reasons: list[str] = []
    if str(machine.get("common_cut_policy") or "blocked") != "supported":
        reasons.append("machine_common_cut_not_supported")
    if not left.variant.end_cut.common_cut_allowed or not right.variant.start_cut.common_cut_allowed:
        reasons.append("part_common_cut_not_explicitly_allowed")
    if left.variant.production_equivalence != "exact" or right.variant.production_equivalence != "exact":
        reasons.append("orientation_not_exact")
    # Plane coefficients are canonicalised to a stable sign, so the physical
    # material-side opposition is carried by the explicit end/start semantics.
    # A shared cut is only admissible between an end surface and a start surface.
    if str(left.variant.end_cut.reference or "") != "end" or str(right.variant.start_cut.reference or "") != "start":
        reasons.append("cut_surface_semantics_not_opposed")
    if not _parallel_cut_slopes(left.end_plane, right.start_plane, angle_tol):
        reasons.append("cut_planes_not_parallel")
    if abs(float(left.variant.end_cut.finish_allowance_mm) - float(right.variant.start_cut.finish_allowance_mm)) > linear_tol:
        reasons.append("finish_allowance_mismatch")
    if any(bool((f or {}).get("blocks_common_cut")) for f in list(left_line.get("relevant_features") or []) + list(right_line.get("relevant_features") or [])):
        reasons.append("feature_blocks_common_cut")
    if str(left_line.get("section_hash") or "") != str(right_line.get("section_hash") or ""):
        reasons.append("section_hash_mismatch")
    proof = {
        "status": "exact" if not reasons else "blocked",
        "reasons": reasons,
        "left_end_cut_hash": left.variant.end_cut.requirement_hash,
        "right_start_cut_hash": right.variant.start_cut.requirement_hash,
        "machine_configuration_hash": str(machine.get("configuration_hash") or ""),
        "angle_tolerance_deg": angle_tol,
        "linear_tolerance_mm": linear_tol,
        "surface_semantics": {
            "left": str(left.variant.end_cut.reference or ""),
            "right": str(right.variant.start_cut.reference or ""),
            "opposed_by_end_start_reference": str(left.variant.end_cut.reference or "") == "end" and str(right.variant.start_cut.reference or "") == "start",
        },
    }
    proof["proof_hash"] = stable_sha256(proof)
    return not reasons, proof


def build_transition(
    left_line: dict[str, Any],
    right_line: dict[str, Any],
    left_instance_id: str,
    left: OrientationGeometry,
    right_instance_id: str,
    right: OrientationGeometry,
    machine: dict[str, Any],
    *,
    kernel: LengthKernel | None = None,
    allow_common_cut: bool = True,
    require_exact: bool = True,
) -> TransitionGeometry:
    kernel = kernel or LengthKernel()
    if str(left_line.get("section_hash") or "") != str(right_line.get("section_hash") or ""):
        raise AngleGeometryError("Transition vereist dezelfde section identity")
    support = _support_difference(left_line, left.end_plane, right.start_plane, require_exact=require_exact)
    geometry_delta_mm = support.max_value_mm
    blade = _finite(machine.get("kerf_mm", 0.0), "zaagbladdikte")
    left_kerf = projected_kerf_mm(left.variant.end_cut, blade)
    right_kerf = projected_kerf_mm(right.variant.start_cut, blade)
    common_ok, proof = prove_common_cut(left_line, right_line, left, right, machine) if allow_common_cut else (False, {"status": "disabled", "reasons": ["solver_common_cut_disabled"]})
    if common_ok:
        kerf_mm = max(left_kerf, right_kerf)
        cut_count = 1
    else:
        kerf_mm = left_kerf + right_kerf
        cut_count = 2
    miter_extra = _finite(machine.get("extra_miter_loss_mm", 0.0), "extra miter loss")
    left_miter = cut_support_level(left.variant.end_cut) != "straight"
    right_miter = cut_support_level(right.variant.start_cut) != "straight"
    left_finish = projected_finish_allowance_mm(left.variant.end_cut)
    right_finish = projected_finish_allowance_mm(right.variant.start_cut)
    if common_ok:
        machine_extra_mm = miter_extra if (left_miter or right_miter) else 0.0
    else:
        machine_extra_mm = miter_extra * int(left_miter) + miter_extra * int(right_miter)
    # Finish allowance remains part material until the later finishing step and
    # therefore increases required reference spacing even for a shared cut.
    extra_loss_mm = machine_extra_mm + left_finish + right_finish
    geom_u = kernel.signed_mm_to_units(geometry_delta_mm)
    # Quantise per physical saw movement. Two independent cuts are two
    # independently quantised blade projections; this avoids a one-grid-unit
    # drift caused by summing binary floats before the integer boundary.
    if common_ok:
        kerf_u = kernel.mm_to_units(max(left_kerf, right_kerf))
    else:
        kerf_u = kernel.mm_to_units(left_kerf) + kernel.mm_to_units(right_kerf)
    finish_u = kernel.mm_to_units(left_finish) + kernel.mm_to_units(right_finish)
    if common_ok:
        machine_extra_u = kernel.mm_to_units(miter_extra if (left_miter or right_miter) else 0.0)
    else:
        machine_extra_u = (kernel.mm_to_units(miter_extra) if left_miter else 0) + (kernel.mm_to_units(miter_extra) if right_miter else 0)
    extra_u = finish_u + machine_extra_u
    gap_u = geom_u + kerf_u + extra_u
    transition = CutTransition(
        transition_id=stable_sha256({
            "left": left_instance_id, "right": right_instance_id,
            "lv": left.variant.variant_hash, "rv": right.variant.variant_hash,
            "machine": machine.get("configuration_hash") or machine.get("machine_id"),
            "common": common_ok,
        })[:32],
        left_instance_id=left_instance_id,
        right_instance_id=right_instance_id,
        left_variant_id=left.variant.variant_id,
        right_variant_id=right.variant.variant_id,
        machine_id=str(machine.get("machine_id") or ""),
        geometry_delta_units=geom_u,
        kerf_projection_units=kerf_u,
        extra_loss_units=extra_u,
        required_reference_gap_units=gap_u,
        physical_spacing_units=gap_u,
        cut_count=cut_count,
        common_cut=common_ok,
        cut_angles_deg=[
            [left.end_plane.primary_angle_deg, left.end_plane.secondary_angle_deg],
            [right.start_plane.primary_angle_deg, right.start_plane.secondary_angle_deg],
        ],
        proof_status="exact" if support.status == "exact" else "review",
        proof={**proof, "transition_support_method": support.method, "transition_support_status": support.status, "geometry_delta_mm": geometry_delta_mm, "left_finish_allowance_projected_mm": left_finish, "right_finish_allowance_projected_mm": right_finish, "machine_extra_loss_mm": machine_extra_mm},
    )
    transition.refresh_hash()
    return TransitionGeometry(transition=transition, left_end_envelope=left.end_envelope, right_start_envelope=right.start_envelope)


def cut_consumption_units(cut: CutRequirement, machine: dict[str, Any], kernel: LengthKernel) -> tuple[int, int]:
    kerf = projected_kerf_mm(cut, machine.get("kerf_mm", 0.0))
    machine_extra = float(machine.get("extra_miter_loss_mm", 0.0) or 0.0) if cut_support_level(cut) != "straight" else 0.0
    finish = projected_finish_allowance_mm(cut)
    return kernel.mm_to_units(kerf), kernel.mm_to_units(machine_extra) + kernel.mm_to_units(finish)


def start_cut_consumption_units(orientation: OrientationGeometry, machine: dict[str, Any], kernel: LengthKernel) -> tuple[int, int]:
    return cut_consumption_units(orientation.variant.start_cut, machine, kernel)


def final_cut_consumption_units(orientation: OrientationGeometry, machine: dict[str, Any], kernel: LengthKernel) -> tuple[int, int]:
    return cut_consumption_units(orientation.variant.end_cut, machine, kernel)


def cut_interval_units(reference_x_units: int, envelope: AxialEnvelope, kerf_units: int, extra_loss_units: int = 0) -> tuple[int, int]:
    start = reference_x_units + envelope.min_offset_units
    end = reference_x_units + envelope.max_offset_units + max(0, int(kerf_units)) + max(0, int(extra_loss_units))
    return min(start, end), max(start, end)


__all__ = [
    "AngleGeometryError", "CanonicalPlane", "SectionSupport", "AxialEnvelope",
    "OrientationGeometry", "TransitionGeometry", "plane_from_angles", "canonical_plane",
    "canonicalize_cut_requirement", "cut_support_level", "projected_kerf_mm",
    "projected_finish_allowance_mm", "axial_envelope",
    "build_orientation_variants", "prove_common_cut", "build_transition",
    "cut_consumption_units", "start_cut_consumption_units",
    "final_cut_consumption_units", "cut_interval_units",
]
