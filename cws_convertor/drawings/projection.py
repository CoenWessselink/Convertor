"""Vector-native drawing projection authority."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True, slots=True)
class ProjectedView:
    name: str
    points: np.ndarray
    depths: np.ndarray
    direction: np.ndarray
    visible_edges: tuple[tuple[int, int], ...]


class DrawingProjectionModel:
    """Single deterministic authority for orthographic/isometric projections."""

    @staticmethod
    def _occt_point_coordinate(point: object, axis: int) -> float:
        """Read one coordinate from either an OCP ``gp_Pnt`` or CQ vector."""

        lower, upper = (("x", "X"), ("y", "Y"), ("z", "Z"))[axis]
        for name in (lower, upper):
            value = getattr(point, name, None)
            if value is not None:
                return float(value() if callable(value) else value)
        to_tuple = getattr(point, "toTuple", None)
        if callable(to_tuple):
            return float(to_tuple()[axis])
        raise TypeError(f"OCCT-punt bevat geen coördinaat voor as {axis}")

    @staticmethod
    def _discretize_occt_edge(
        edge: object,
        deflection: float,
        *,
        sampler_factory: object | None = None,
    ) -> tuple[object, ...]:
        """Sample a CadQuery edge through OCCT's curve adaptor.

        CadQuery 2.8 does not expose ``Edge.discretize``.  Its own SVG
        exporter samples HLR edges with ``GCPnts_QuasiUniformDeflection``;
        keep the drawing and section routes on that supported OCCT API too.
        ``sampler_factory`` is injectable so this compatibility boundary can
        be covered without requiring the native runtime on every developer
        machine.
        """

        if sampler_factory is None:
            from OCP.GCPnts import GCPnts_QuasiUniformDeflection

            sampler_factory = GCPnts_QuasiUniformDeflection
        curve = edge._geomAdaptor()
        sampler = sampler_factory(
            curve,
            float(deflection),
            curve.FirstParameter(),
            curve.LastParameter(),
        )
        if not sampler.IsDone():
            return ()
        return tuple(sampler.Value(index + 1) for index in range(sampler.NbPoints()))

    @staticmethod
    def basis(view: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if view == "front": return np.array((1.,0.,0.)),np.array((0.,1.,0.)),np.array((0.,0.,1.))
        if view == "top": return np.array((1.,0.,0.)),np.array((0.,0.,1.)),np.array((0.,-1.,0.))
        if view == "side": return np.array((0.,1.,0.)),np.array((0.,0.,1.)),np.array((1.,0.,0.))
        if view == "end": return np.array((0.,-1.,0.)),np.array((0.,0.,1.)),np.array((-1.,0.,0.))
        # ISO is an exact parallel isometric projection.  The separate 3D
        # review direction deliberately has a lower elevation, so the two UI
        # options no longer render the same view.
        direction=np.array((1.,-.62,.42) if view=="3d" else (1.,-1.,.78),dtype=float);direction/=np.linalg.norm(direction)
        u=np.array((1.,1.,0.),dtype=float);u/=np.linalg.norm(u);v=np.cross(direction,u);v/=np.linalg.norm(v)
        return u,v,direction

    @classmethod
    def project(cls,vertices:np.ndarray,view:str)->tuple[np.ndarray,np.ndarray]:
        u,v,direction=cls.basis(view);projected=np.column_stack((vertices@u,vertices@v));primary=np.array((float(u[0]),float(v[0])),dtype=float)
        if float(np.linalg.norm(primary))>1.e-9:
            angle=math.atan2(float(primary[1]),float(primary[0]));cosine,sine=math.cos(angle),math.sin(angle);projected=projected@np.array(((cosine,-sine),(sine,cosine)),dtype=float)
        return projected,vertices@direction

    @staticmethod
    def visible_edges(triangles:np.ndarray,vertices:np.ndarray,direction:np.ndarray)->tuple[tuple[int,int],...]:
        adjacency={};normals=[]
        for triangle_index,triangle in enumerate(triangles):
            a,b,c=(int(value) for value in triangle);normal=np.cross(vertices[b]-vertices[a],vertices[c]-vertices[a]);length=float(np.linalg.norm(normal));normals.append(normal/length if length>1.e-9 else np.zeros(3))
            for start,end in ((a,b),(b,c),(c,a)):
                edge=(start,end) if start<end else (end,start);adjacency.setdefault(edge,[]).append(triangle_index)
        front=[float(np.dot(normal,direction))>=-1.e-8 for normal in normals];result=set()
        for edge,faces in adjacency.items():
            if len(faces)==1 and front[faces[0]]:result.add(edge)
            elif len(faces)>1:
                first,second=faces[:2]
                if front[first]!=front[second] or (front[first] and float(np.dot(normals[first],normals[second]))<math.cos(math.radians(28.))):result.add(edge)
        return tuple(sorted(result))

    @staticmethod
    def _mesh_edge_layers(
        triangles: np.ndarray,
        vertices: np.ndarray,
        direction: np.ndarray,
    ) -> tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]:
        """Return feature/silhouette edges without coplanar triangulation lines."""

        adjacency: dict[tuple[int, int], list[int]] = {}
        normals: list[np.ndarray] = []
        for triangle_index, triangle in enumerate(np.asarray(triangles, dtype=int)):
            a, b, c = (int(value) for value in triangle)
            normal = np.cross(vertices[b] - vertices[a], vertices[c] - vertices[a])
            length = float(np.linalg.norm(normal))
            normals.append(normal / length if length > 1.0e-9 else np.zeros(3))
            for start, end in ((a, b), (b, c), (c, a)):
                edge = (start, end) if start < end else (end, start)
                adjacency.setdefault(edge, []).append(triangle_index)
        front = [float(np.dot(normal, direction)) >= -1.0e-8 for normal in normals]
        visible: set[tuple[int, int]] = set()
        hidden: set[tuple[int, int]] = set()
        crease_limit = math.cos(math.radians(1.0))
        for edge, faces in adjacency.items():
            if len(faces) == 1:
                (visible if front[faces[0]] else hidden).add(edge)
                continue
            first, second = faces[:2]
            silhouette = front[first] != front[second]
            crease = float(np.dot(normals[first], normals[second])) < crease_limit
            if not silhouette and not crease:
                continue
            if front[first] or front[second]:
                visible.add(edge)
            else:
                hidden.add(edge)
        return tuple(sorted(visible)), tuple(sorted(hidden))

    @classmethod
    def _occt_hlr_polylines(
        cls,
        exact_shape: object,
        view: str,
    ) -> tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...]]:
        """Run OCCT HLR and return projected visible/hidden edge polylines.

        Imports are local so mesh-only review remains usable in reduced
        environments.  Any HLR failure is reported to ``edge_layers`` which
        then uses the explicitly non-production mesh fallback.
        """

        import cadquery as cq
        from cadquery.occ_impl.shapes import TOLERANCE
        from OCP.BRepLib import BRepLib

        u, v, direction = cls.basis(view)

        def edge_points(compound: object) -> tuple[np.ndarray, ...]:
            result: list[np.ndarray] = []
            identities: set[tuple[tuple[float, float], ...]] = set()

            raw_compound = getattr(compound, "wrapped", compound)
            if compound is None or raw_compound.IsNull():
                return ()
            # HLR output needs explicit 3D curves before BRepAdaptor sampling;
            # this mirrors CadQuery 2.8's native SVG exporter and also avoids
            # null adaptors/segfaults in OCP.
            BRepLib.BuildCurves3d_s(raw_compound, TOLERANCE)
            wrapped_compound = compound if hasattr(compound, "Edges") else cq.Shape.cast(raw_compound)
            for edge in wrapped_compound.Edges():
                points = cls._discretize_occt_edge(edge, 0.05)
                # HLR returns geometry in its projection plane.  X/Y are
                # therefore already drawing coordinates; projecting a second
                # time would corrupt orthographic proportions.
                projected = np.asarray(
                    [
                        (
                            cls._occt_point_coordinate(point, 0),
                            cls._occt_point_coordinate(point, 1),
                        )
                        for point in points
                    ],
                    dtype=float,
                )
                if len(projected) < 2:
                    continue
                identity = tuple((round(float(point[0]), 6), round(float(point[1]), 6)) for point in projected)
                reverse = tuple(reversed(identity))
                if identity in identities or reverse in identities:
                    continue
                identities.add(identity)
                result.append(projected)
            return tuple(result)

        from OCP.HLRAlgo import HLRAlgo_Projector
        from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
        from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt

        algorithm = HLRBRep_Algo()
        wrapped = getattr(exact_shape, "wrapped", exact_shape)
        algorithm.Add(wrapped)
        axis = gp_Ax2(
            gp_Pnt(0.0, 0.0, 0.0),
            gp_Dir(float(direction[0]), float(direction[1]), float(direction[2])),
            gp_Dir(float(u[0]), float(u[1]), float(u[2])),
        )
        algorithm.Projector(HLRAlgo_Projector(axis))
        algorithm.Update()
        algorithm.Hide()
        extraction = HLRBRep_HLRToShape(algorithm)

        def collect(names: Sequence[str]) -> tuple[np.ndarray, ...]:
            result: list[np.ndarray] = []
            for name in names:
                method = getattr(extraction, name, None)
                if method is None:
                    continue
                compound = method()
                if compound is None or compound.IsNull():
                    continue
                result.extend(edge_points(compound))
            return tuple(result)

        visible = collect(("VCompound", "Rg1LineVCompound", "OutLineVCompound"))
        hidden = collect(("HCompound", "Rg1LineHCompound", "OutLineHCompound"))
        if not visible:
            raise RuntimeError("OCCT HLR leverde geen zichtbare randen")
        return visible, hidden

    @classmethod
    def edge_layers(
        cls,
        vertices: np.ndarray,
        triangles: np.ndarray,
        view: str,
        *,
        exact_shape: object | None = None,
    ) -> tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...], str]:
        if exact_shape is not None:
            try:
                visible, hidden = cls._occt_hlr_polylines(exact_shape, view)
                return visible, hidden, "occt_hlr"
            except Exception:
                # The linter keeps this fallback out of production release.
                pass
        direction = cls.basis(view)[2]
        visible_edges, hidden_edges = cls._mesh_edge_layers(
            np.asarray(triangles, dtype=int),
            np.asarray(vertices, dtype=float),
            direction,
        )
        projected, _depth = cls.project(np.asarray(vertices, dtype=float), view)
        visible = tuple(projected[[first, second]] for first, second in visible_edges)
        hidden = tuple(projected[[first, second]] for first, second in hidden_edges)
        return visible, hidden, "mesh_fallback"

    @staticmethod
    def exact_section_polylines(
        exact_shape: object,
        *,
        axis: str = "x",
        position: float | None = None,
    ) -> tuple[np.ndarray, ...]:
        """Intersect an exact BREP with a manufacturing-axis plane.

        The result is returned in section-plane coordinates and can therefore
        be hatched and rendered without consulting the viewer tessellation.
        """

        import cadquery as cq
        from cadquery.occ_impl.shapes import TOLERANCE
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
        from OCP.BRepLib import BRepLib
        from OCP.gp import gp_Dir, gp_Pln, gp_Pnt

        shape = exact_shape if hasattr(exact_shape, "BoundingBox") else cq.Shape.cast(exact_shape)
        bounds = shape.BoundingBox()
        axes = {
            "x": ((1.0, 0.0, 0.0), (float(bounds.xmin), float(bounds.xmax)), (1, 2)),
            "y": ((0.0, 1.0, 0.0), (float(bounds.ymin), float(bounds.ymax)), (0, 2)),
            "z": ((0.0, 0.0, 1.0), (float(bounds.zmin), float(bounds.zmax)), (0, 1)),
        }
        normal, limits, coordinates = axes.get(str(axis).lower(), axes["x"])
        cut_position = float(position) if position is not None else (limits[0] + limits[1]) * 0.5
        origin = [0.0, 0.0, 0.0]
        origin[{"x": 0, "y": 1, "z": 2}.get(str(axis).lower(), 0)] = cut_position
        plane = gp_Pln(gp_Pnt(*origin), gp_Dir(*normal))
        operation = BRepAlgoAPI_Section(getattr(shape, "wrapped", shape), plane, False)
        operation.Approximation(True)
        operation.Build()
        if not operation.IsDone() or operation.Shape().IsNull():
            raise RuntimeError("OCCT BREP-vlakdoorsnede kon niet worden opgebouwd")
        raw_section = operation.Shape()
        BRepLib.BuildCurves3d_s(raw_section, TOLERANCE)
        section = cq.Shape.cast(raw_section)
        result: list[np.ndarray] = []
        identities: set[tuple[tuple[float, float], ...]] = set()
        for edge in section.Edges():
            points = DrawingProjectionModel._discretize_occt_edge(edge, 0.03)
            projected = np.asarray(
                [
                    (
                        DrawingProjectionModel._occt_point_coordinate(point, coordinates[0]),
                        DrawingProjectionModel._occt_point_coordinate(point, coordinates[1]),
                    )
                    for point in points
                ],
                dtype=float,
            )
            if len(projected) < 2:
                continue
            identity = tuple((round(float(point[0]), 6), round(float(point[1]), 6)) for point in projected)
            if identity in identities or tuple(reversed(identity)) in identities:
                continue
            identities.add(identity)
            result.append(projected)
        if not result:
            raise RuntimeError("OCCT BREP-vlakdoorsnede bevat geen snijranden")
        return tuple(result)

    @classmethod
    def view(cls,vertices:np.ndarray,triangles:np.ndarray,name:str)->ProjectedView:
        points,depths=cls.project(vertices,name);direction=cls.basis(name)[2]
        return ProjectedView(name,points,depths,direction,cls.visible_edges(triangles,vertices,direction))

    @classmethod
    def export_pdf(cls,path:str|Path,vertices:np.ndarray,triangles:np.ndarray,*,views:Sequence[str],sheet_mm:tuple[float,float],scale_denominator:int,title:str,metadata:Mapping[str,str]|None=None)->Path:
        # Compatibility entry point: legacy callers now use the same
        # DrawingDocument and renderer as the active PDF / Tekening workspace.
        from .engine import DrawingBuildRequest, ProductionDrawingEngine
        from .renderer import ProductionDrawingRenderer

        width, height = (float(sheet_mm[0]), float(sheet_mm[1]))
        orientation = "landscape" if width >= height else "portrait"
        long_side, short_side = max(width, height), min(width, height)
        formats = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0), "A1": (841.0, 594.0), "A0": (1189.0, 841.0)}
        sheet_format = min(
            formats,
            key=lambda name: abs(formats[name][0] - long_side) + abs(formats[name][1] - short_side),
        )
        values = dict(metadata or {})
        entity = str(values.get("Onderdeel") or values.get("entity") or title)
        document = ProductionDrawingEngine.build(
            DrawingBuildRequest(
                entity_id=entity,
                vertices=np.asarray(vertices, dtype=float),
                triangles=np.asarray(triangles, dtype=int),
                views=views,
                sheet_format=sheet_format,
                orientation=orientation,
                scale_denominator=max(1, int(scale_denominator)),
                unit=str(values.get("Eenheid") or "mm").lower(),
                title_block={
                    "project": str(values.get("Project") or "CWS project"),
                    "entity": entity,
                    "profile": str(values.get("Profiel") or "Niet opgegeven"),
                    "material": str(values.get("Materiaal") or "Niet opgegeven"),
                    "revision": str(values.get("Revisie") or "-") ,
                    "status": str(values.get("Status") or "REVIEW"),
                },
                notes=("Compatibele mesh-review; productie-vrijgave vereist canonical rebuilt BREP.",),
            )
        )
        return ProductionDrawingRenderer.render_pdf(document, path)


__all__=["DrawingProjectionModel","ProjectedView"]
