"""Distinct, scalable native icons for the existing drawing tools."""
from __future__ import annotations
from typing import Any
from cws_viewer.ui_qt.qt_compat import require_qt


def dimension_icon(kind: str) -> Any:
    core, gui, _widgets = require_qt()
    image = gui.QPixmap(64, 64)
    image.fill(core.Qt.GlobalColor.transparent)
    image.setDevicePixelRatio(2.0)
    painter = gui.QPainter(image)
    painter.setRenderHint(gui.QPainter.RenderHint.Antialiasing, True)
    pen = gui.QPen(gui.QColor('#075fce'), 1.6)
    pen.setCapStyle(core.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(core.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    def line(*coords: float) -> None:
        painter.drawPolyline(gui.QPolygonF([core.QPointF(*coords[i:i+2]) for i in range(0,len(coords),2)]))

    def dim(y: float = 16, x1: float = 4, x2: float = 28) -> None:
        line(x1,y,x2,y)
        line(x1+4,y-3,x1,y,x1+4,y+3)
        line(x2-4,y-3,x2,y,x2-4,y+3)
        line(x1,y-7,x1,y+7)
        line(x2,y-7,x2,y+7)

    if kind == 'select':
        line(6,3,6,27,12,21,17,30,21,28,16,19,25,19,6,3)
    elif kind in {'horizontal','vertical','aligned'}:
        if kind != 'horizontal':
            painter.translate(16,16)
            painter.rotate(90 if kind == 'vertical' else -40)
            painter.translate(-16,-16)
        dim()
    elif kind == 'chain':
        dim(x2=16); dim(x1=16)
    elif kind == 'baseline':
        dim(y=11); dim(y=23,x2=19); line(4,3,4,30)
    elif kind in {'ordinate_x','ordinate_y'}:
        if kind == 'ordinate_y':
            painter.translate(16,16); painter.rotate(-90); painter.translate(-16,-16)
        line(4,26,28,26); line(5,29,5,5); line(13,26,13,12,21,12); line(23,26,23,5,29,5)
        painter.drawEllipse(core.QPointF(5,26),2,2)
    elif kind == 'angle':
        line(5,28,5,5,28,28,5,28)
        painter.drawArc(core.QRectF(-5,17,20,20),0,90*16)
    elif kind in {'radius','diameter'}:
        painter.drawEllipse(core.QRectF(5,5,22,22))
        if kind == 'diameter':
            line(4,28,28,4); line(4,23,4,28,9,28)
        else:
            line(16,16,27,5); line(22,5,27,5,27,10)
            painter.drawEllipse(core.QPointF(16,16),1,1)
    elif kind == 'center_distance':
        for x in (7,25):
            painter.drawEllipse(core.QPointF(x,21),4,4); line(x,15,x,28)
        dim(y=8,x1=7,x2=25)
    elif kind == 'leader':
        line(4,27,15,13,28,13); line(4,21,4,27,10,26); line(18,8,27,8)
    elif kind == 'text':
        line(7,26,16,5,25,26); line(11,19,21,19); line(5,29,27,29)
    else:
        painter.end()
        raise ValueError(f'Unknown drawing tool: {kind}')
    painter.end()
    return gui.QIcon(image)
