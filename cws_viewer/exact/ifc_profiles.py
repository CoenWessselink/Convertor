"""Exact parametric IFC profile reconstruction for V10 source isolation.

The project display provider intentionally accepts declared approximations for
large-model rendering. Exact manufacturing isolation must be stricter: known
parametric IFC profile definitions are reconstructed as analytical OCCT BREP,
while unsupported profile semantics remain explicitly warned/blocked.

Only source parameters are used. Profile names may be recorded as provenance,
but never replace IFC dimensions or radii in this builder.
"""
from __future__ import annotations

from pathlib import Path
import math

import cadquery as cq

import converter as nc1_core
from cws_convertor.importers.p21 import P21Entity
from cws_viewer.geometry.ifc_provider import (
    IfcShapeBuilder,
    UnsupportedIfcGeometry,
    _cross,
    _dot,
    _identity,
    _norm,
    _transform,
)


EXACT_IFC_PROFILE_BUILDER_VERSION = "cws-exact-ifc-profiles-v10.3"
_EPS = 1e-9


def _header(
    *,
    designation: str,
    profile_type: str,
    length: float,
    dim1: float,
    dim2: float,
    dim3: float,
    dim4: float,
    radius: float,
) -> nc1_core.Header:
    return nc1_core.Header(
        order_number="IFC-SOURCE",
        drawing_number="",
        part_number=designation or "IFC-PROFILE",
        position_number="",
        material="",
        quantity=1,
        profile=designation or profile_type,
        profile_type=profile_type,
        length=float(length),
        saw_length=float(length),
        dim1=float(dim1),
        dim2=float(dim2),
        dim3=float(dim3),
        dim4=float(dim4),
        radius=float(radius),
        weight=0.0,
        paint_area=0.0,
        web_miter_front=0.0,
        web_miter_rear=0.0,
        flange_miter_front=0.0,
        flange_miter_rear=0.0,
        info=[],
    )


def _profile_part(header: nc1_core.Header) -> nc1_core.NC1Part:
    return nc1_core.NC1Part(Path("__ifc_parametric_profile__.ifc"), header, [], [])


def _core_longitudinal_to_ifc_profile(
    shape: cq.Shape,
    *,
    width: float,
    height: float,
    centered_x: bool,
    centered_y: bool,
) -> cq.Shape:
    """Map core X-length/Y-width/Z-height coordinates to IFC XY/+Z sweep."""

    tx = -float(width) / 2.0 if centered_x else 0.0
    ty = -float(height) / 2.0 if centered_y else 0.0
    matrix = [
        [0.0, 1.0, 0.0, tx],
        [0.0, 0.0, 1.0, ty],
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]
    return _transform(shape, matrix)


def _rounded_hollow_rectangle(
    width: float,
    height: float,
    wall: float,
    depth: float,
    inner_radius: float,
    outer_radius: float,
) -> cq.Shape:
    if min(width, height, wall, depth) <= 0.0:
        raise UnsupportedIfcGeometry("Ongeldige IFC hollow-rechthoekparameters")
    inner_width = width - 2.0 * wall
    inner_height = height - 2.0 * wall
    if min(inner_width, inner_height) <= 0.0:
        raise UnsupportedIfcGeometry("IFC hollow-rechthoek heeft geen geldige binnenruimte")
    if outer_radius < -_EPS or inner_radius < -_EPS:
        raise UnsupportedIfcGeometry("Negatieve IFC-profielradius")
    if outer_radius > min(width, height) / 2.0 + 1e-7:
        raise UnsupportedIfcGeometry("Buitenradius overschrijdt halve profielmaat")
    if inner_radius > min(inner_width, inner_height) / 2.0 + 1e-7:
        raise UnsupportedIfcGeometry("Binnenradius overschrijdt halve binnenmaat")

    outer = cq.Workplane("XY").rect(width, height).extrude(depth)
    if outer_radius > _EPS:
        outer = outer.edges("|Z").fillet(outer_radius)
    inner = cq.Workplane("XY").rect(inner_width, inner_height).extrude(depth + 2.0).translate((0.0, 0.0, -1.0))
    if inner_radius > _EPS:
        inner = inner.edges("|Z").fillet(inner_radius)
    result = outer.cut(inner).val()
    if result is None or result.isNull() or not result.isValid():
        raise UnsupportedIfcGeometry("Exacte hollow-rechthoekopbouw leverde geen geldige BREP")
    return result


class ExactIfcShapeBuilder(IfcShapeBuilder):
    """IFC shape builder with analytical profile definitions where proven."""

    provider_version = EXACT_IFC_PROFILE_BUILDER_VERSION

    def _parametric_profile_prism(self, profile: P21Entity, depth: float) -> cq.Shape | None:
        kind = profile.type_name
        designation = profile.string(1)

        if kind == "IFCRECTANGLEPROFILEDEF":
            width = float(profile.number(3, 0.0) or 0.0)
            height = float(profile.number(4, 0.0) or 0.0)
            if min(width, height) <= 0.0:
                raise UnsupportedIfcGeometry("Ongeldige IFC-rechthoekprofielmaten")
            return cq.Workplane("XY").rect(width, height).extrude(depth).val()

        if kind == "IFCCIRCLEPROFILEDEF":
            radius = float(profile.number(3, 0.0) or 0.0)
            if radius <= 0.0:
                raise UnsupportedIfcGeometry("Ongeldige IFC-cirkelradius")
            return cq.Workplane("XY").circle(radius).extrude(depth).val()

        if kind == "IFCCIRCLEHOLLOWPROFILEDEF":
            radius = float(profile.number(3, 0.0) or 0.0)
            wall = float(profile.number(4, 0.0) or 0.0)
            if radius <= 0.0 or wall <= 0.0 or radius <= wall:
                raise UnsupportedIfcGeometry("Ongeldige IFC-buisparameters")
            outer = cq.Workplane("XY").circle(radius).extrude(depth)
            inner = cq.Workplane("XY").circle(radius - wall).extrude(depth + 2.0).translate((0.0, 0.0, -1.0))
            result = outer.cut(inner).val()
            if result is None or result.isNull() or not result.isValid():
                raise UnsupportedIfcGeometry("Exacte IFC-buisopbouw leverde geen geldige BREP")
            return result

        if kind == "IFCRECTANGLEHOLLOWPROFILEDEF":
            width = float(profile.number(3, 0.0) or 0.0)
            height = float(profile.number(4, 0.0) or 0.0)
            wall = float(profile.number(5, 0.0) or 0.0)
            inner_radius = float(profile.number(6, 0.0) or 0.0)
            outer_radius = float(profile.number(7, 0.0) or 0.0)
            return _rounded_hollow_rectangle(width, height, wall, depth, inner_radius, outer_radius)

        if kind == "IFCISHAPEPROFILEDEF":
            width = float(profile.number(3, 0.0) or 0.0)
            height = float(profile.number(4, 0.0) or 0.0)
            web = float(profile.number(5, 0.0) or 0.0)
            flange = float(profile.number(6, 0.0) or 0.0)
            fillet = float(profile.number(7, 0.0) or 0.0)
            header = _header(
                designation=designation,
                profile_type="I",
                length=depth,
                dim1=height,
                dim2=width,
                dim3=flange,
                dim4=web,
                radius=fillet,
            )
            part = _profile_part(header)
            result = nc1_core.build_i_profile(part).val()
            if result is None or result.isNull() or not result.isValid() or part.warnings:
                raise UnsupportedIfcGeometry(
                    "IFC I-profiel kon niet exact uit bronparameters worden opgebouwd"
                    + (": " + "; ".join(part.warnings) if part.warnings else "")
                )
            return _core_longitudinal_to_ifc_profile(
                result,
                width=width,
                height=height,
                centered_x=True,
                centered_y=True,
            )

        return None

    def _orient_sweep(self, shape: cq.Shape, profile: P21Entity, extrusion: P21Entity) -> cq.Shape:
        positioned = _transform(shape, self.axis2(profile.ref(2)))
        direction = self.direction(extrusion.ref(2), (0.0, 0.0, 1.0))
        z = [0.0, 0.0, 1.0]
        target = _norm(direction, (0.0, 0.0, 1.0))
        axis = _cross(z, target)
        dot = max(-1.0, min(1.0, _dot(z, target)))
        if math.sqrt(_dot(axis, axis)) > 1e-8:
            axis = _norm(axis)
            positioned = positioned.rotate((0.0, 0.0, 0.0), tuple(axis), math.degrees(math.acos(dot)))
        elif dot < 0.0:
            positioned = positioned.rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 180.0)
        return _transform(positioned, self.axis3(extrusion.ref(1)))

    def _extruded(self, e: P21Entity) -> cq.Shape:
        profile = self._entity(e.ref(0))
        depth = float(e.number(3, 0.0) or 0.0)
        if depth <= 0.0:
            raise UnsupportedIfcGeometry("Extrusiediepte ontbreekt")

        exact = self._parametric_profile_prism(profile, depth)
        if exact is not None:
            return self._orient_sweep(exact, profile, e)

        if profile.type_name in {"IFCARBITRARYCLOSEDPROFILEDEF", "IFCARBITRARYPROFILEDEFWITHVOIDS"}:
            curve_ids = [profile.ref(2)]
            if profile.type_name == "IFCARBITRARYPROFILEDEFWITHVOIDS":
                curve_ids.extend(profile.refs(3))
            curve_types = {
                self._entity(curve_id).type_name
                for curve_id in curve_ids
                if curve_id is not None
            }
            if any(kind != "IFCPOLYLINE" for kind in curve_types):
                self.warnings.append(
                    "IFC arbitrary-profile curves zijn bemonsterd; analytische broncurves nog niet exact opgebouwd"
                )
        return super()._extruded(e)


__all__ = ["EXACT_IFC_PROFILE_BUILDER_VERSION", "ExactIfcShapeBuilder"]
