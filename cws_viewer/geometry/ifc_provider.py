"""Dependency-light IFC2x3 display geometry provider.

It reconstructs display BREP/CSG from source IFC items and tessellates them. It
never infers NC1/manufacturing features. Unsupported details are reported and
may fall back to an explicit proxy in the coordinator.
"""
from __future__ import annotations
from dataclasses import dataclass
import math, threading
from pathlib import Path
from typing import Iterable

import cadquery as cq
import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid
from OCP.gp import gp_Ax3, gp_Dir, gp_Pln, gp_Pnt, gp_Trsf

from cws_convertor.importers.ifc_project import _detect_units, _display_representation_ids
from cws_convertor.importers.p21 import P21Document, P21Entity
from cws_viewer.contracts.geometry import CancelCheck, GeometryRequest, MeshData, TessellationSettings

PROVIDER_VERSION='cws-ifc-display-v4'
_EPS=1e-9
class UnsupportedIfcGeometry(RuntimeError):pass

def _identity():return [[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.],[0.,0.,0.,1.]]
def _matmul(a,b):return [[sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]
def _inverse_rigid(m):
    r=[[m[i][j] for j in range(3)] for i in range(3)];t=[m[i][3] for i in range(3)];rt=[[r[j][i] for j in range(3)] for i in range(3)]
    it=[-sum(rt[i][j]*t[j] for j in range(3)) for i in range(3)]
    return [[*rt[0],it[0]],[*rt[1],it[1]],[*rt[2],it[2]],[0.,0.,0.,1.]]
def _norm(v,fallback=(0.,0.,1.)):
    x=[float(a) for a in v][:3];x += [0.]*(3-len(x));n=math.sqrt(sum(a*a for a in x));return list(fallback) if n<=_EPS else [a/n for a in x]
def _cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def _dot(a,b):return sum(a[i]*b[i] for i in range(3))
def _gp_transform(m):
    t=gp_Trsf();t.SetValues(m[0][0],m[0][1],m[0][2],m[0][3],m[1][0],m[1][1],m[1][2],m[1][3],m[2][0],m[2][1],m[2][2],m[2][3]);return t
def _transform(shape:cq.Shape,m):
    if m==_identity():return shape
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped,_gp_transform(m),True).Shape())
def _compound(shapes:Iterable[cq.Shape])->cq.Shape:
    vals=[s for s in shapes if s is not None and not s.isNull()]
    if not vals:raise UnsupportedIfcGeometry('Lege IFC-vorm')
    if len(vals)==1:return vals[0]
    return cq.Compound.makeCompound(vals)
def _clean(points,tol=1e-8):
    out=[]
    for p in points:
        v=(float(p[0]),float(p[1]))
        if not out or abs(v[0]-out[-1][0])>tol or abs(v[1]-out[-1][1])>tol:out.append(v)
    if len(out)>1 and abs(out[0][0]-out[-1][0])<=tol and abs(out[0][1]-out[-1][1])<=tol:out.pop()
    if len(out)<3:raise UnsupportedIfcGeometry('Profiel bevat minder dan drie punten')
    return out

def _polygon_prism(points,depth,inner=None):
    outer=cq.Workplane('XY').polyline(_clean(points)).close().extrude(depth)
    for hole in inner or ():
        cut=cq.Workplane('XY').polyline(_clean(hole)).close().extrude(depth)
        outer=outer.cut(cut)
    val=outer.val()
    if val is None:raise UnsupportedIfcGeometry('Profielextrusie is leeg')
    return val

def _rectangle(x,y,depth):return cq.Workplane('XY').rect(x,y).extrude(depth).val()
def _circle(radius,depth):return cq.Workplane('XY').circle(radius).extrude(depth).val()

@dataclass(slots=True)
class _IfcSession:
    document:P21Document; units_to_mm:float; builder:'IfcShapeBuilder'; lock:threading.RLock

class IfcShapeBuilder:
    def __init__(self,document:P21Document,settings:TessellationSettings)->None:
        self.document=document;self.settings=settings;self.shape_cache={};self.warning_cache={};self.active=set();self.warnings=[]
    def _entity(self,eid):
        if eid is None:raise UnsupportedIfcGeometry('Ontbrekende IFC-entity')
        return self.document.require(int(eid))
    def point(self,eid):
        e=self._entity(eid)
        if e.type_name!='IFCCARTESIANPOINT':raise UnsupportedIfcGeometry(f'#{eid} is geen punt')
        vals=e.scalar(0,[]) or []
        return [float(v) for v in vals]+[0.]*(3-len(vals))
    def direction(self,eid,fallback=(0.,0.,1.)):
        if eid is None:return list(fallback)
        e=self._entity(eid)
        if e.type_name!='IFCDIRECTION':return list(fallback)
        return _norm(e.scalar(0,[]) or [],fallback)
    def axis2(self,eid):
        if eid is None:return _identity()
        e=self._entity(eid)
        if e.type_name!='IFCAXIS2PLACEMENT2D':return _identity()
        p=self.point(e.ref(0));x=self.direction(e.ref(1),(1.,0.,0.));x=[x[0],x[1],0.];x=_norm(x,(1.,0.,0.));y=[-x[1],x[0],0.]
        return [[x[0],y[0],0.,p[0]],[x[1],y[1],0.,p[1]],[0.,0.,1.,p[2]],[0.,0.,0.,1.]]
    def axis3(self,eid):
        if eid is None:return _identity()
        e=self._entity(eid)
        if e.type_name=='IFCAXIS2PLACEMENT2D':return self.axis2(eid)
        if e.type_name!='IFCAXIS2PLACEMENT3D':return _identity()
        p=self.point(e.ref(0));z=self.direction(e.ref(1),(0.,0.,1.));x0=self.direction(e.ref(2),(1.,0.,0.));x=_norm([x0[i]-_dot(x0,z)*z[i] for i in range(3)],(1.,0.,0.));y=_norm(_cross(z,x),(0.,1.,0.));x=_norm(_cross(y,z),(1.,0.,0.))
        return [[x[0],y[0],z[0],p[0]],[x[1],y[1],z[1],p[1]],[x[2],y[2],z[2],p[2]],[0.,0.,0.,1.]]
    def transform_operator(self,eid):
        e=self._entity(eid);origin=self.point(e.ref(2));x=self.direction(e.ref(0),(1.,0.,0.));y0=self.direction(e.ref(1),(0.,1.,0.));z0=self.direction(e.ref(4),(0.,0.,1.)) if len(e.values)>4 else _cross(x,y0)
        x=_norm(x,(1.,0.,0.));z=_norm(z0,(0.,0.,1.));y=_norm(_cross(z,x),(0.,1.,0.));scale=float(e.number(3,1.0) or 1.0)
        return [[x[0]*scale,y[0]*scale,z[0]*scale,origin[0]],[x[1]*scale,y[1]*scale,z[1]*scale,origin[1]],[x[2]*scale,y[2]*scale,z[2]*scale,origin[2]],[0.,0.,0.,1.]]
    def _polyline2d(self,e:P21Entity):return [(self.point(pid)[0],self.point(pid)[1]) for pid in e.refs(0)]
    def _trim_angle(self,value,center):
        # trim lists can contain numeric parameters or cartesian-point refs
        vals=[]
        def walk(v):
            if isinstance(v,dict):
                if set(v)=={'ref'}:
                    p=self.point(int(v['ref'])); vals.append(math.atan2(p[1]-center[1],p[0]-center[0]));return
                if 'value' in v:walk(v['value']);return
                for x in v.values():walk(x)
            elif isinstance(v,(list,tuple)):
                for x in v:walk(x)
            elif isinstance(v,(int,float)):vals.append(float(v))
        walk(value);return vals[0] if vals else None
    def _curve_points(self,eid):
        e=self._entity(eid)
        if e.type_name=='IFCPOLYLINE':return self._polyline2d(e)
        if e.type_name=='IFCCOMPOSITECURVE':
            out=[]
            for sid in e.refs(0):
                seg=self._entity(sid);pts=self._curve_points(seg.ref(2));
                if seg.string(1).upper()=='F':pts=list(reversed(pts))
                if out and pts and math.dist(out[-1],pts[0])<1e-7:pts=pts[1:]
                out.extend(pts)
            return out
        if e.type_name=='IFCTRIMMEDCURVE':
            basis=self._entity(e.ref(0))
            if basis.type_name!='IFCCIRCLE':raise UnsupportedIfcGeometry(f'Trimcurvebasis {basis.type_name} niet ondersteund')
            m=self.axis2(basis.ref(0));center=(m[0][3],m[1][3]);r=float(basis.number(1,0) or 0)
            a0=self._trim_angle(e.value(1),center);a1=self._trim_angle(e.value(2),center)
            if a0 is None or a1 is None:raise UnsupportedIfcGeometry('Trimcurve mist hoek/eindpunt')
            sense=e.string(3).upper()!='F';twopi=2*math.pi
            if sense:
                while a1<=a0:a1+=twopi
            else:
                while a1>=a0:a1-=twopi
            steps=max(4,int(abs(a1-a0)/twopi*self.settings.circle_segments)+1)
            pts=[]
            for i in range(steps+1):
                a=a0+(a1-a0)*i/steps;lx=r*math.cos(a);ly=r*math.sin(a)
                pts.append((m[0][0]*lx+m[0][1]*ly+m[0][3],m[1][0]*lx+m[1][1]*ly+m[1][3]))
            return pts
        if e.type_name=='IFCCIRCLE':
            m=self.axis2(e.ref(0));r=float(e.number(1,0) or 0);n=self.settings.circle_segments
            return [(m[0][0]*r*math.cos(2*math.pi*i/n)+m[0][1]*r*math.sin(2*math.pi*i/n)+m[0][3],m[1][0]*r*math.cos(2*math.pi*i/n)+m[1][1]*r*math.sin(2*math.pi*i/n)+m[1][3]) for i in range(n)]
        raise UnsupportedIfcGeometry(f'Curve {e.type_name} niet ondersteund')
    def _profile_loops(self,e:P21Entity):
        kind=e.type_name;pos=self.axis2(e.ref(2)) if len(e.values)>2 else _identity()
        def apply(pts):return [(pos[0][0]*x+pos[0][1]*y+pos[0][3],pos[1][0]*x+pos[1][1]*y+pos[1][3]) for x,y in pts]
        holes=[]
        if kind=='IFCARBITRARYCLOSEDPROFILEDEF':outer=self._curve_points(e.ref(2));return outer,holes
        if kind=='IFCARBITRARYPROFILEDEFWITHVOIDS':outer=self._curve_points(e.ref(2));holes=[self._curve_points(r) for r in e.refs(3)];return outer,holes
        if kind=='IFCRECTANGLEPROFILEDEF':
            x=float(e.number(3,0) or 0);y=float(e.number(4,0) or 0);outer=apply([(-x/2,-y/2),(x/2,-y/2),(x/2,y/2),(-x/2,y/2)])
        elif kind=='IFCRECTANGLEHOLLOWPROFILEDEF':
            x=float(e.number(3,0) or 0);y=float(e.number(4,0) or 0);t=float(e.number(5,0) or 0);outer=apply([(-x/2,-y/2),(x/2,-y/2),(x/2,y/2),(-x/2,y/2)]);ix=max(x-2*t,_EPS);iy=max(y-2*t,_EPS);holes=[apply([(-ix/2,-iy/2),(-ix/2,iy/2),(ix/2,iy/2),(ix/2,-iy/2)])]
            if any(float(e.number(i,0) or 0)>0 for i in (6,7)):self.warnings.append('Hollow-rechthoekfillets als scherpe hoeken weergegeven')
        elif kind=='IFCCIRCLEPROFILEDEF':
            r=float(e.number(3,0) or 0);n=self.settings.circle_segments;outer=apply([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n)) for i in range(n)])
        elif kind=='IFCCIRCLEHOLLOWPROFILEDEF':
            r=float(e.number(3,0) or 0);t=float(e.number(4,0) or 0);n=self.settings.circle_segments;outer=apply([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n)) for i in range(n)]);ri=max(r-t,_EPS);holes=[apply([(ri*math.cos(-2*math.pi*i/n),ri*math.sin(-2*math.pi*i/n)) for i in range(n)])]
        elif kind=='IFCISHAPEPROFILEDEF':
            w=float(e.number(3,0) or 0);d=float(e.number(4,0) or 0);tw=float(e.number(5,0) or 0);tf=float(e.number(6,0) or 0);x=w/2;y=d/2;wx=tw/2
            outer=apply([(-x,-y),(x,-y),(x,-y+tf),(wx,-y+tf),(wx,y-tf),(x,y-tf),(x,y),(-x,y),(-x,y-tf),(-wx,y-tf),(-wx,-y+tf),(-x,-y+tf)])
            if float(e.number(7,0) or 0)>0:self.warnings.append('I-profielfillets als scherpe hoeken weergegeven')
        elif kind=='IFCLSHAPEPROFILEDEF':
            # IFC2x3 and newer define the parameterized profile origin at the
            # centre of its bounding box. Building the angle from (0, 0)
            # shifts every occurrence by half its width/depth and makes steel
            # connections visibly miss their intended product placement.
            d=float(e.number(3,0) or 0);w=float(e.number(4,d) or d);t=float(e.number(5,0) or 0);x=w/2;y=d/2
            outer=apply([(-x,-y),(x,-y),(x,-y+t),(-x+t,-y+t),(-x+t,y),(-x,y)])
            self.warnings.append('L-profiel zonder fillets/slopes weergegeven')
        elif kind=='IFCUSHAPEPROFILEDEF':
            # The U-profile coordinate origin is likewise the centre of the
            # bounding box. Keep the web on negative X and both flanges
            # symmetric around Y=0, matching the buildingSMART definition.
            d=float(e.number(3,0) or 0);w=float(e.number(4,0) or 0);tw=float(e.number(5,0) or 0);tf=float(e.number(6,0) or 0);x=w/2;y=d/2
            outer=apply([(-x,-y),(x,-y),(x,-y+tf),(-x+tw,-y+tf),(-x+tw,y-tf),(x,y-tf),(x,y),(-x,y)])
            self.warnings.append('U-profiel zonder fillets/slopes weergegeven')
        else:raise UnsupportedIfcGeometry(f'Profieltype {kind} niet ondersteund')
        return outer,holes
    def _extruded(self,e):
        profile=self._entity(e.ref(0));depth=float(e.number(3,0) or 0)
        if depth<=0:raise UnsupportedIfcGeometry('Extrusiediepte ontbreekt')
        outer,holes=self._profile_loops(profile);shape=_polygon_prism(outer,depth,holes)
        direction=self.direction(e.ref(2),(0.,0.,1.));
        # Base prism is +Z. Rotate Z to requested local direction.
        z=[0.,0.,1.];d=_norm(direction,(0.,0.,1.));axis=_cross(z,d);dot=max(-1.,min(1.,_dot(z,d)))
        if math.sqrt(_dot(axis,axis))>1e-8:
            axis=_norm(axis);angle=math.acos(dot);shape=shape.rotate((0,0,0),tuple(axis),math.degrees(angle))
        elif dot<0:shape=shape.rotate((0,0,0),(1,0,0),180)
        return _transform(shape,self.axis3(e.ref(1)))
    def _faceted(self,e):
        shell=self._entity(e.ref(0));faces=[]
        for fid in shell.refs(0):
            face_ent=self._entity(fid);loops=[]
            for bid in face_ent.refs(0):
                bound=self._entity(bid);loop=self._entity(bound.ref(0));pts=[self.point(pid) for pid in loop.refs(0)]
                if bound.string(1).upper()=='F':pts=list(reversed(pts))
                poly=BRepBuilderAPI_MakePolygon()
                for p in pts:poly.Add(gp_Pnt(*p[:3]))
                poly.Close();loops.append(poly.Wire())
            if not loops:continue
            maker=BRepBuilderAPI_MakeFace(loops[0])
            for hole in loops[1:]:maker.Add(hole)
            if maker.IsDone():faces.append(maker.Face())
        if not faces:raise UnsupportedIfcGeometry('Faceted BREP bevat geen geldige vlakken')
        try:
            b=BRep_Builder();shell_shape=TopoDS_Shell();b.MakeShell(shell_shape)
            for f in faces:b.Add(shell_shape,f)
            solid=TopoDS_Solid();b.MakeSolid(solid);b.Add(solid,shell_shape)
            shape=cq.Shape.cast(solid)
            if not shape.isNull():return shape
        except Exception:pass
        return cq.Compound.makeCompound([cq.Shape.cast(f) for f in faces])
    def _halfspace(self,e):
        surface=self._entity(e.ref(0))
        if surface.type_name!='IFCPLANE':raise UnsupportedIfcGeometry(f'Halfspace {surface.type_name} niet ondersteund')
        m=self.axis3(surface.ref(0));origin=[m[i][3] for i in range(3)];normal=[m[i][2] for i in range(3)];x=[m[i][0] for i in range(3)]
        plane=gp_Pln(gp_Ax3(gp_Pnt(*origin),gp_Dir(*normal),gp_Dir(*x)));face=BRepBuilderAPI_MakeFace(plane,-1e7,1e7,-1e7,1e7).Face();agreement=e.string(1).upper()!='F';side=-1. if agreement else 1.
        ref=gp_Pnt(origin[0]+normal[0]*side*1000,origin[1]+normal[1]*side*1000,origin[2]+normal[2]*side*1000)
        return cq.Shape.cast(BRepPrimAPI_MakeHalfSpace(face,ref).Solid())
    def _mapped(self,e,cancel):
        rm=self._entity(e.ref(0));rep=self._entity(rm.ref(1));shape=_compound(self.build(i,cancel_check=cancel) for i in rep.refs(3));return _transform(shape,_matmul(self.transform_operator(e.ref(1)),_inverse_rigid(self.axis3(rm.ref(0)))))
    def _boolean(self,e,cancel):
        a=self.build(e.ref(1),cancel_check=cancel);b=self.build(e.ref(2),cancel_check=cancel);op=e.string(0).upper()
        if op=='DIFFERENCE':res=BRepAlgoAPI_Cut(a.wrapped,b.wrapped).Shape()
        elif op=='UNION':res=BRepAlgoAPI_Fuse(a.wrapped,b.wrapped).Shape()
        elif op in {'INTERSECTION','INTERSECT'}:res=BRepAlgoAPI_Common(a.wrapped,b.wrapped).Shape()
        else:raise UnsupportedIfcGeometry(f'Booleanoperator {op} niet ondersteund')
        shape=cq.Shape.cast(res)
        if shape.isNull():raise UnsupportedIfcGeometry(f'Booleanresultaat {op} is leeg')
        return shape
    def build(self,eid,*,cancel_check=None):
        if cancel_check:cancel_check()
        if eid is None:raise UnsupportedIfcGeometry('Ontbrekende geometrie-entity')
        eid=int(eid)
        if eid in self.shape_cache:
            self.warnings.extend(self.warning_cache.get(eid,()))
            return self.shape_cache[eid]
        if eid in self.active:raise UnsupportedIfcGeometry(f'Cyclische geometrie bij #{eid}')
        warning_start=len(self.warnings)
        self.active.add(eid)
        try:
            e=self._entity(eid);kind=e.type_name
            if kind=='IFCEXTRUDEDAREASOLID':shape=self._extruded(e)
            elif kind in {'IFCFACETEDBREP','IFCMANIFOLDSOLIDBREP'}:shape=self._faceted(e)
            elif kind in {'IFCBOOLEANRESULT','IFCBOOLEANCLIPPINGRESULT'}:shape=self._boolean(e,cancel_check)
            elif kind=='IFCHALFSPACESOLID':shape=self._halfspace(e)
            elif kind=='IFCMAPPEDITEM':shape=self._mapped(e,cancel_check)
            elif kind in {'IFCSHAPEREPRESENTATION','IFCREPRESENTATION'}:
                children=[]
                for child_id in e.refs(3):
                    try:children.append(self.build(child_id,cancel_check=cancel_check))
                    except UnsupportedIfcGeometry as exc:self.warnings.append(f'IFC Body-detail #{child_id} overgeslagen: {exc}')
                if not children:raise UnsupportedIfcGeometry(f'IFC-representatie #{eid} bevat geen renderbare Body-geometrie')
                shape=_compound(children)
            else:raise UnsupportedIfcGeometry(f'IFC-geometrietype {kind} niet ondersteund')
            self.shape_cache[eid]=shape
            self.warning_cache[eid]=tuple(dict.fromkeys(self.warnings[warning_start:]))
            return shape
        finally:self.active.remove(eid)

class IfcMeshProvider:
    def __init__(self)->None:self._sessions={};self._lock=threading.RLock()
    @property
    def provider_version(self):return PROVIDER_VERSION
    def supports(self,request):return request.source_format.upper()=='IFC'
    def _session(self,request,settings):
        key=(request.source_sha256,settings.fingerprint)
        with self._lock:
            s=self._sessions.get(key)
            if s is None:
                doc=P21Document.load(Path(request.source_path));units=_detect_units(doc);s=_IfcSession(doc,float(units.length_to_mm),IfcShapeBuilder(doc,settings),threading.RLock());self._sessions[key]=s
            return s
    @staticmethod
    def _product_items(doc,source_entity_id):
        try:p=doc.require(int(str(source_entity_id).lstrip('#')))
        except (ValueError,KeyError):return ()
        d=doc.get(p.ref(6));
        if d is None:return ()
        shape_ids=_display_representation_ids(doc,d);items=[]
        for sid in shape_ids:
            s=doc.get(sid)
            if s:items.extend(s.refs(3))
        return tuple(items)
    @staticmethod
    def _tessellate(shapes,settings,scale):
        vv=[];tt=[]
        for shape in shapes:
            verts,tris=shape.tessellate(settings.linear_deflection_mm/max(scale,_EPS),settings.angular_deflection_rad);off=len(vv)
            vv.extend((float(p.x)*scale,float(p.y)*scale,float(p.z)*scale) for p in verts);tt.extend((a+off,b+off,c+off) for a,b,c in tris)
        if not vv or not tt:raise UnsupportedIfcGeometry('Tessellatie leverde geen driehoeken')
        return np.asarray(vv,np.float64),np.asarray(tt,np.int32)
    def load(self,request,settings,*,cancel_check=None):
        if not self.supports(request):raise UnsupportedIfcGeometry('IfcMeshProvider ondersteunt alleen IFC')
        s=self._session(request,settings)
        with s.lock:
            items=tuple(int(v) for v in request.source_item_ids if str(v).strip()) or self._product_items(s.document,request.source_entity_id)
            if not items:raise UnsupportedIfcGeometry('IFC-product bevat geen Body-items')
            before=len(s.builder.warnings);shapes=[]
            for item_id in items:
                try:shapes.append(s.builder.build(item_id,cancel_check=cancel_check))
                except UnsupportedIfcGeometry as exc:s.builder.warnings.append(f'IFC Body-item #{item_id} overgeslagen: {exc}')
            if not shapes:raise UnsupportedIfcGeometry('IFC-product bevat geen renderbare Body-geometrie')
            vertices,triangles=self._tessellate(shapes,settings,s.units_to_mm)
            warnings=tuple(dict.fromkeys(s.builder.warnings[before:]));exact='display_approximation' if warnings else 'source_tessellation'
        return MeshData(vertices,triangles,request.source_geometry_hash,f'IfcMeshProvider/{PROVIDER_VERSION}',exact,warnings,
                        {"source_format":"IFC","source_file_id":request.source_file_id,"source_entity_id":request.source_entity_id,"source_item_ids":list(request.source_item_ids),"units_to_mm":s.units_to_mm})

__all__=['IfcMeshProvider','IfcShapeBuilder','UnsupportedIfcGeometry','PROVIDER_VERSION']

# CWS exact display tessellation override.
# IfcOpenShell is authoritative for visual geometry; the legacy parser remains
# available only as an explicit compatibility fallback for malformed sources.
_LEGACY_IFC_MESH_LOAD = IfcMeshProvider.load
PROVIDER_VERSION = "cws-ifc-display-v5-ifcopenshell"


def _cws_ifcopenshell_load(self, request, settings, *, cancel_check=None):
    # Preserve explicitly injected provider sessions used by integrations and
    # contract tests. Normal runtime instances do not carry this override.
    if "_session" in getattr(self, "__dict__", {}):
        return _LEGACY_IFC_MESH_LOAD(
            self, request, settings, cancel_check=cancel_check
        )
    if str(getattr(request, "source_format", "")).lower() not in {"ifc", ".ifc"}:
        return _LEGACY_IFC_MESH_LOAD(
            self, request, settings, cancel_check=cancel_check
        )
    try:
        import hashlib
        import threading
        from pathlib import Path

        import ifcopenshell
        import ifcopenshell.geom
        import numpy as np

        if cancel_check is not None:
            cancel_check()

        source_path = Path(str(request.source_path))
        if not source_path.is_file():
            raise FileNotFoundError(source_path)

        if not hasattr(self, "_cws_ifcopenshell_lock"):
            self._cws_ifcopenshell_lock = threading.RLock()
            self._cws_ifcopenshell_models = {}

        cache_key = (str(source_path.resolve()), str(getattr(request, "source_sha256", "")))
        with self._cws_ifcopenshell_lock:
            model = self._cws_ifcopenshell_models.get(cache_key)
            if model is None:
                model = ifcopenshell.open(str(source_path))
                self._cws_ifcopenshell_models.clear()
                self._cws_ifcopenshell_models[cache_key] = model

        entity_token = str(getattr(request, "source_entity_id", "") or "").strip()
        entity = None
        numeric_token = entity_token[1:] if entity_token.startswith("#") else entity_token
        if numeric_token.isdigit():
            entity = model.by_id(int(numeric_token))
        if entity is None and entity_token:
            try:
                entity = model.by_guid(entity_token)
            except Exception:
                entity = None
        if entity is None:
            raise LookupError(f"IFC entity not found: {entity_token!r}")

        geom_settings = ifcopenshell.geom.settings()
        circle_segments = max(64, int(getattr(settings, "circle_segments", 24)) * 3)
        configured = {
            "use-world-coords": False,
            "weld-vertices": True,
            "no-normals": True,
            "circle-segments": circle_segments,
            "mesher-linear-deflection": min(
                0.00020,
                max(0.00001, float(getattr(settings, "linear_deflection_mm", 1.0)) / 4000.0),
            ),
            "mesher-angular-deflection": min(
                0.10,
                max(0.02, float(getattr(settings, "angular_deflection_rad", 0.35)) / 3.0),
            ),
            "precision": 1.0e-7,
        }
        for key, value in configured.items():
            try:
                geom_settings.set(key, value)
            except Exception:
                pass

        shape = ifcopenshell.geom.create_shape(geom_settings, entity)
        vertices = np.asarray(shape.geometry.verts, dtype=np.float64).reshape((-1, 3))
        triangles = np.asarray(shape.geometry.faces, dtype=np.int64).reshape((-1, 3))
        if vertices.size == 0 or triangles.size == 0:
            raise ValueError("IfcOpenShell returned empty geometry")
        if not np.isfinite(vertices).all():
            raise ValueError("IfcOpenShell returned non-finite vertices")

        vertices = np.ascontiguousarray(vertices * 1000.0)
        triangles = np.ascontiguousarray(triangles, dtype=np.int64)
        mesh_digest = hashlib.sha256(vertices.tobytes() + triangles.tobytes()).hexdigest()
        source_hash = str(getattr(request, "source_geometry_hash", "") or mesh_digest)
        metadata = dict(getattr(request, "metadata", {}) or {})
        metadata.update(
            {
                "geometry_engine": "ifcopenshell",
                "geometry_engine_version": getattr(ifcopenshell, "version", "unknown"),
                "source_file_id": str(getattr(request, "source_file_id", "")),
                "source_entity_id": entity_token,
                "circle_segments": circle_segments,
                "visual_profile_radii": True,
                "visual_fastener_curves": True,
                "legacy_fallback": False,
            }
        )
        if cancel_check is not None:
            cancel_check()
        return MeshData(
            vertices=vertices,
            triangles=triangles,
            source_geometry_hash=source_hash,
            provider=f"IfcMeshProvider/{PROVIDER_VERSION}",
            exactness="source_tessellation",
            warnings=(),
            metadata=metadata,
            mesh_hash=mesh_digest,
        )
    except Exception as exc:
        legacy = _LEGACY_IFC_MESH_LOAD(
            self, request, settings, cancel_check=cancel_check
        )
        try:
            from dataclasses import replace

            fallback_metadata = dict(getattr(legacy, "metadata", {}) or {})
            fallback_metadata.update(
                {
                    "geometry_engine": "legacy_fallback",
                    "legacy_fallback": True,
                    "ifcopenshell_error": f"{type(exc).__name__}: {exc}",
                }
            )
            return replace(
                legacy,
                warnings=tuple(getattr(legacy, "warnings", ()))
                + (f"IfcOpenShell fallback: {type(exc).__name__}: {exc}",),
                metadata=fallback_metadata,
            )
        except Exception:
            return legacy


IfcMeshProvider.load = _cws_ifcopenshell_load


def _cws_ifcopenshell_load_many(
    self,
    requests,
    settings,
    *,
    cancel_check=None,
    progress=None,
):
    """Batch-tessellate verified IFC products through one native iterator."""
    import hashlib
    import os
    from collections import defaultdict
    from pathlib import Path

    import ifcopenshell
    import ifcopenshell.geom
    import numpy as np

    values = tuple(requests)
    if not values:
        return {}
    grouped = defaultdict(list)
    for request in values:
        if str(request.source_format).upper() != "IFC":
            continue
        grouped[(str(Path(request.source_path).resolve()), request.source_sha256)].append(request)
    output = {}
    completed = 0
    total = sum(len(group) for group in grouped.values())
    for (source_path, source_sha256), group in grouped.items():
        if cancel_check is not None:
            cancel_check()
        model = ifcopenshell.open(source_path)
        by_entity_id = defaultdict(list)
        entities = []
        for request in group:
            token = str(request.source_entity_id or "").strip()
            entity = None
            numeric = token[1:] if token.startswith("#") else token
            if numeric.isdigit():
                entity = model.by_id(int(numeric))
            elif token:
                try:
                    entity = model.by_guid(token)
                except Exception:
                    entity = None
            if entity is not None:
                by_entity_id[int(entity.id())].append(request)
                entities.append(entity)

        geom_settings = ifcopenshell.geom.settings()
        configured = {
            "use-world-coords": False,
            "weld-vertices": True,
            "no-normals": True,
            "circle-segments": max(64, int(getattr(settings, "circle_segments", 24)) * 3),
            "mesher-linear-deflection": min(
                0.00020,
                max(0.00001, float(getattr(settings, "linear_deflection_mm", 1.0)) / 4000.0),
            ),
            "mesher-angular-deflection": min(
                0.10,
                max(0.02, float(getattr(settings, "angular_deflection_rad", 0.35)) / 3.0),
            ),
            "precision": 1.0e-7,
        }
        for key, value in configured.items():
            try:
                geom_settings.set(key, value)
            except Exception:
                pass
        iterator = ifcopenshell.geom.iterate(
            geom_settings,
            model,
            num_threads=max(1, min(8, int(os.cpu_count() or 1))),
            include=entities,
        )
        for shape in iterator:
            if cancel_check is not None:
                cancel_check()
            entity_requests = by_entity_id.get(int(shape.id), ())
            if not entity_requests:
                continue
            vertices = np.asarray(shape.geometry.verts, dtype=np.float64).reshape((-1, 3)).copy()
            triangles = np.asarray(shape.geometry.faces, dtype=np.int64).reshape((-1, 3)).copy()
            if vertices.size == 0 or triangles.size == 0:
                continue
            vertices *= 1000.0
            mesh_digest = hashlib.sha256(vertices.tobytes() + triangles.tobytes()).hexdigest()
            for request in entity_requests:
                metadata = dict(request.metadata_dict)
                metadata.update(
                    {
                        "geometry_engine": "ifcopenshell-iterator",
                        "geometry_engine_version": getattr(ifcopenshell, "version", "unknown"),
                        "source_file_id": request.source_file_id,
                        "source_entity_id": request.source_entity_id,
                        "visual_profile_radii": True,
                        "visual_fastener_curves": True,
                        "legacy_fallback": False,
                        "batch_tessellation": True,
                    }
                )
                mesh = MeshData(
                    vertices=vertices,
                    triangles=triangles,
                    source_geometry_hash=request.source_geometry_hash or mesh_digest,
                    provider=f"IfcMeshProvider/{PROVIDER_VERSION}",
                    exactness="source_tessellation",
                    warnings=(),
                    metadata=metadata,
                    mesh_hash=mesh_digest,
                )
                output[request.geometry_id] = mesh
                completed += 1
                if progress is not None:
                    progress(completed / max(total, 1), request.geometry_id)
    return output


IfcMeshProvider.load_many = _cws_ifcopenshell_load_many
