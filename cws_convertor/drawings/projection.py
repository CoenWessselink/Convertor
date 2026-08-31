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
    def basis(view: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if view == "front": return np.array((1.,0.,0.)),np.array((0.,1.,0.)),np.array((0.,0.,1.))
        if view == "top": return np.array((1.,0.,0.)),np.array((0.,0.,1.)),np.array((0.,-1.,0.))
        if view == "side": return np.array((0.,1.,0.)),np.array((0.,0.,1.)),np.array((1.,0.,0.))
        direction=np.array((1.,-1.,.78),dtype=float);direction/=np.linalg.norm(direction)
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

    @classmethod
    def view(cls,vertices:np.ndarray,triangles:np.ndarray,name:str)->ProjectedView:
        points,depths=cls.project(vertices,name);direction=cls.basis(name)[2]
        return ProjectedView(name,points,depths,direction,cls.visible_edges(triangles,vertices,direction))

    @classmethod
    def export_pdf(cls,path:str|Path,vertices:np.ndarray,triangles:np.ndarray,*,views:Sequence[str],sheet_mm:tuple[float,float],scale_denominator:int,title:str,metadata:Mapping[str,str]|None=None)->Path:
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        target=Path(path).expanduser().resolve();target.parent.mkdir(parents=True,exist_ok=True);page=(float(sheet_mm[0])*mm,float(sheet_mm[1])*mm);pdf=canvas.Canvas(str(target),pagesize=page,pageCompression=1);pdf.setTitle(title);pdf.setAuthor("CWS Convertor")
        width,height=page;margin=9*mm;header=15*mm;footer=24*mm;gap=4*mm;pdf.setStrokeColor(colors.HexColor("#244665"));pdf.setLineWidth(.45*mm);pdf.rect(margin,margin,width-2*margin,height-2*margin);pdf.setFont("Helvetica-Bold",12);pdf.drawString(margin+4*mm,height-margin-9*mm,title);pdf.setFont("Helvetica",7);pdf.drawRightString(width-margin-4*mm,height-margin-8*mm,f"Vectorprojectie | schaal 1:{scale_denominator}")
        area=(margin+3*mm,margin+footer,width-margin-3*mm,height-margin-header);count=max(1,len(views));columns=1 if count==1 else 2;rows=int(math.ceil(count/columns));cell_w=(area[2]-area[0]-gap*(columns-1))/columns;cell_h=(area[3]-area[1]-gap*(rows-1))/rows;labels={"front":"VOORAANZICHT","top":"BOVENAANZICHT","side":"ZIJAANZICHT","iso":"ISOMETRISCH","3d":"ISOMETRISCH"}
        for index,raw_view in enumerate(views):
            view_name="iso" if raw_view=="3d" else raw_view;row,column=divmod(index,columns);left=area[0]+column*(cell_w+gap);bottom=area[3]-(row+1)*cell_h-row*gap;pdf.setStrokeColor(colors.HexColor("#b8c8d6"));pdf.setLineWidth(.18*mm);pdf.rect(left,bottom,cell_w,cell_h);pdf.setFillColor(colors.HexColor("#1d466d"));pdf.setFont("Helvetica-Bold",7);pdf.drawString(left+2*mm,bottom+cell_h-5*mm,labels.get(raw_view,raw_view.upper()))
            projected=cls.view(np.asarray(vertices,dtype=float),np.asarray(triangles,dtype=int),view_name);center=(projected.points.min(axis=0)+projected.points.max(axis=0))*.5;drawing_scale=mm/max(1.,float(scale_denominator));cx=left+cell_w*.5;cy=bottom+cell_h*.48;screen=np.empty_like(projected.points);screen[:,0]=(projected.points[:,0]-center[0])*drawing_scale+cx;screen[:,1]=(projected.points[:,1]-center[1])*drawing_scale+cy;face_depths=projected.depths[triangles].mean(axis=1)
            for triangle_index in np.argsort(face_depths):
                triangle=triangles[int(triangle_index)];points=[(float(screen[int(vertex),0]),float(screen[int(vertex),1])) for vertex in triangle];path_object=pdf.beginPath();path_object.moveTo(*points[0]);path_object.lineTo(*points[1]);path_object.lineTo(*points[2]);path_object.close();pdf.setFillColor(colors.HexColor("#d8e0e8"));pdf.setStrokeColor(colors.HexColor("#8ca1b4"));pdf.setLineWidth(.08*mm);pdf.drawPath(path_object,fill=1,stroke=1)
            pdf.setStrokeColor(colors.HexColor("#173b5d"));pdf.setLineWidth(.22*mm)
            for first,second in projected.visible_edges:pdf.line(float(screen[first,0]),float(screen[first,1]),float(screen[second,0]),float(screen[second,1]))
            span=projected.points.max(axis=0)-projected.points.min(axis=0);pdf.setFont("Helvetica",6);pdf.setFillColor(colors.HexColor("#245b8d"));pdf.drawString(left+2*mm,bottom+2*mm,f"{span[0]:.1f} x {span[1]:.1f} mm")
        values=dict(metadata or {});pdf.setFillColor(colors.HexColor("#243d55"));pdf.setFont("Helvetica",6.5);pdf.drawString(margin+3*mm,margin+5*mm," | ".join(f"{key}: {value}" for key,value in values.items())[:220]);pdf.save()
        if not target.is_file() or target.stat().st_size<512:raise RuntimeError(f"Vector-PDF is niet aangemaakt: {target}")
        return target


__all__=["DrawingProjectionModel","ProjectedView"]
