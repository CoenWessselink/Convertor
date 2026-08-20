"""Deterministic vector scene for the Profile Nesting bar visualizer.

The scene is derived from persisted solver output and its immutable input
snapshot. It never edits or owns geometry. Both Tk rendering and SVG export use
this one scene so screen/export cannot drift into separate engineering truths.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any
import hashlib


@dataclass(frozen=True)
class BarPrimitive:
    kind: str
    x1_mm: float
    x2_mm: float = 0.0
    y1: float = 0.0
    y2: float = 1.0
    role: str = ""
    label: str = ""
    object_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BarScene:
    bar_id: str
    stock_length_mm: float
    height_units: float = 1.0
    primitives: list[BarPrimitive] = field(default_factory=list)
    selected_object_id: str = ""


PIECE_PALETTE = (
    "#f4cf5d", "#93c5fd", "#c4b5fd", "#67e8f9", "#fdba74",
    "#86efac", "#f0abfc", "#fda4af", "#a5b4fc", "#5eead4",
)


def piece_display_color(primitive: BarPrimitive, color_mode: str = "part") -> str:
    """Return a deterministic display-only colour for a piece primitive.

    Colour never participates in geometry or validation.  The key comes from
    persisted solver/snapshot metadata so the same plan renders consistently
    on screen and in SVG.
    """
    if primitive.role != "piece":
        return ""
    mode = color_mode if color_mode in {"part", "assembly", "batch", "heat", "status", "machine"} else "part"
    if mode == "status":
        status = str(primitive.metadata.get("status") or "").lower()
        if status in {"blocked", "failed", "ineligible"}:
            return "#fca5a5"
        if status in {"review", "unknown"}:
            return "#fdba74"
        return "#86efac"
    key = str(primitive.metadata.get(mode) or primitive.metadata.get("part") or primitive.object_id or "piece")
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return PIECE_PALETTE[digest[0] % len(PIECE_PALETTE)]


def _d(value: Any) -> dict[str, Any]:
    return dict(value or {}) if isinstance(value, dict) else {}


def _mm(value: Any, upm: int) -> float:
    return float(int(value or 0)) / float(upm)


def build_bar_scene(record: dict[str, Any], bar_id: str, *, selected_object_id: str = "") -> BarScene:
    snapshot = _d(record.get("input_snapshot")); upm = int(_d(snapshot.get("units")).get("units_per_mm") or 1000)
    lines = {str(_d(x).get("demand_line_id") or ""): _d(x) for x in list(snapshot.get("demand_lines") or [])}
    machines = {str(_d(x).get("profile_id") or ""): _d(x) for x in list(_d(snapshot.get("machine_snapshot")).get("profiles") or [])}
    bar = None
    for raw in list(_d(record.get("plan")).get("bars") or []):
        item = _d(raw)
        if str(item.get("bar_id") or "") == bar_id:
            bar = item; break
    if bar is None:
        return BarScene(bar_id=bar_id, stock_length_mm=0.0, selected_object_id=selected_object_id)
    length = _mm(bar.get("stock_length_units"), upm)
    scene = BarScene(bar_id=bar_id, stock_length_mm=length, selected_object_id=selected_object_id)
    manual=_d(record.get("manual_planning")); active_locks=[_d(x) for x in list(manual.get("locks") or []) if bool(_d(x).get("active",True))]
    bar_locked=any(str(x.get("scope") or "")=="bar" and str(x.get("bar_id") or "")==bar_id for x in active_locks)
    locked_pieces={str(x.get("instance_id") or ""):str(x.get("lock_id") or "") for x in active_locks if str(x.get("scope") or "")=="piece"}
    scene.primitives.append(BarPrimitive("rect", 0.0, length, 0.10, 0.90, role="stock", object_id=bar_id,metadata={"locked":bar_locked}))
    if bar_locked:
        scene.primitives.append(BarPrimitive("marker",0.0,0.0,0.01,0.99,role="lock",label="BAR LOCK",object_id=f"{bar_id}:lock"))
    head = _mm(bar.get("head_trim_units"), upm); tail = _mm(bar.get("tail_trim_units"), upm)
    if head > 0:
        scene.primitives.append(BarPrimitive("rect", 0.0, head, 0.10, 0.90, role="trim", label=f"head {head:.1f}", object_id=f"{bar_id}:head"))
    if tail > 0:
        scene.primitives.append(BarPrimitive("rect", max(0.0, length-tail), length, 0.10, 0.90, role="trim", label=f"tail {tail:.1f}", object_id=f"{bar_id}:tail"))
    machine = machines.get(str(bar.get("machine_profile_id") or ""), {})
    for idx, raw_zone in enumerate(list(machine.get("forbidden_clamp_zones") or []), start=1):
        z = _d(raw_zone); a=float(z.get("start_mm") or 0.0); b=float(z.get("end_mm") or 0.0)
        if b > a:
            scene.primitives.append(BarPrimitive("rect", a, b, 0.03, 0.97, role="forbidden", label="klemzone", object_id=f"{bar_id}:zone:{idx}"))
    transitions = {str(_d(x).get("transition_id") or ""): _d(x) for x in list(bar.get("transitions") or [])}
    placements = sorted((_d(x) for x in list(bar.get("placements") or [])), key=lambda x: int(x.get("sequence_index") or 0))
    for p in placements:
        line = lines.get(str(p.get("demand_line_id") or ""), {})
        x1 = _mm(p.get("physical_min_units"), upm); x2 = _mm(p.get("physical_max_units"), upm)
        if x2 < x1: x1, x2 = x2, x1
        pid = str(p.get("instance_id") or "")
        locked = pid in locked_pieces
        label = f"{int(p.get('sequence_index') or 0)} · {p.get('part_position') or pid[:8]} · {_mm(p.get('length_units'), upm):.1f}" + (" · LOCK" if locked else "")
        scene.primitives.append(BarPrimitive(
            "rect", x1, x2, 0.19, 0.81, role="piece", label=label, object_id=pid,
            metadata={
                "sequence": int(p.get("sequence_index") or 0),
                "orientation": str(p.get("orientation_id") or ""),
                "part": str(p.get("part_position") or line.get("part_position") or line.get("part_id") or pid),
                "assembly": ",".join(str(x) for x in list(line.get("assembly_marks") or [])),
                "batch": str(line.get("production_batch") or ""),
                "heat": str(line.get("heat_requirement") or ""),
                "status": str(line.get("eligibility_status") or ""),
                "machine": str(bar.get("machine_profile_id") or ""),
                "locked": locked,
                "lock_id": locked_pieces.get(pid, ""),
            },
        ))
        if locked:
            scene.primitives.append(BarPrimitive("marker",x1,x1,0.17,0.83,role="lock",label="LOCK",object_id=locked_pieces.get(pid, f"{pid}:lock")))
        ref_start = _mm(p.get("reference_start_units"), upm); ref_end = _mm(p.get("reference_end_units"), upm)
        start = _d(line.get("start_cut")); end = _d(line.get("end_cut"))
        scene.primitives.append(BarPrimitive("cut", ref_start, ref_start, 0.14, 0.86, role="cut", object_id=f"{pid}:start", metadata={"angle_deg": float(start.get("primary_angle_deg") or 0.0), "secondary_angle_deg": float(start.get("secondary_angle_deg") or 0.0)}))
        scene.primitives.append(BarPrimitive("cut", ref_end, ref_end, 0.14, 0.86, role="cut", object_id=f"{pid}:end", metadata={"angle_deg": float(end.get("primary_angle_deg") or 0.0), "secondary_angle_deg": float(end.get("secondary_angle_deg") or 0.0)}))
        transition = transitions.get(str(p.get("transition_after_id") or ""), {})
        if transition:
            kerf = _mm(transition.get("kerf_projection_units"), upm)
            if kerf > 0:
                scene.primitives.append(BarPrimitive("rect", ref_end, ref_end+kerf, 0.12, 0.88, role="kerf", label=f"kerf {kerf:.2f}", object_id=str(transition.get("transition_id") or "")))
            if bool(transition.get("common_cut", False)):
                scene.primitives.append(BarPrimitive("marker", ref_end, ref_end, 0.02, 0.98, role="common", label="COMMON CUT", object_id=str(transition.get("transition_id") or "")))
    remnant = _mm(bar.get("reusable_remnant_units"), upm); waste = _mm(bar.get("waste_units"), upm)
    residual = remnant if remnant > 0 else waste
    if residual > 0:
        start = max(0.0, length - tail - residual)
        scene.primitives.append(BarPrimitive("rect", start, start+residual, 0.10, 0.90, role="remnant" if remnant > 0 else "scrap", label=("rest" if remnant > 0 else "scrap") + f" {residual:.1f}", object_id=f"{bar_id}:residual"))
    scene.primitives.append(BarPrimitive("line", 0.0, length, 0.50, 0.50, role="centerline", object_id=f"{bar_id}:center"))
    return scene


def scene_to_svg(scene: BarScene, path: str | Path, *, width: int = 1400, height: int = 260, color_mode: str = "part") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    margin_x=44.0; top=36.0; bar_h=120.0; usable=max(1.0, width-2*margin_x); length=max(scene.stock_length_mm, 1e-9)
    def sx(x: float) -> float: return margin_x + usable * x / length
    def sy(v: float) -> float: return top + bar_h * v
    fills = {"stock":"#d7f5df","piece":"#f6d365","trim":"#94a3b8","kerf":"#0f172a","forbidden":"#fecaca","remnant":"#86efac","scrap":"#fca5a5"}
    strokes = {"cut":"#1e293b","common":"#16a34a","lock":"#7c3aed","centerline":"#64748b"}
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#f8fafc"/>']
    out.append(f'<text x="{margin_x}" y="22" font-family="Segoe UI,Arial" font-size="15" font-weight="700" fill="#122033">{escape(scene.bar_id)} · {scene.stock_length_mm:.1f} mm</text>')
    for p in scene.primitives:
        selected = p.object_id == scene.selected_object_id
        if p.kind == "rect":
            x=min(sx(p.x1_mm),sx(p.x2_mm)); w=abs(sx(p.x2_mm)-sx(p.x1_mm)); y=sy(p.y1); h=bar_h*(p.y2-p.y1)
            fill=piece_display_color(p, color_mode) if p.role == "piece" else fills.get(p.role,"#cbd5e1"); stroke="#2563eb" if selected else "#334155"; sw=3 if selected else 1
            opacity="0.42" if p.role=="forbidden" else "1"
            out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w,0.8):.2f}" height="{h:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>')
            if p.label and w > 42:
                out.append(f'<text x="{x+w/2:.2f}" y="{y+h/2+4:.2f}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="11" fill="#172033">{escape(p.label)}</text>')
        elif p.kind == "cut":
            x=sx(p.x1_mm); angle=float(p.metadata.get("angle_deg") or 0.0); shift=max(-24.0,min(24.0,angle/90.0*24.0))
            out.append(f'<line x1="{x-shift:.2f}" y1="{sy(p.y1):.2f}" x2="{x+shift:.2f}" y2="{sy(p.y2):.2f}" stroke="{strokes["cut"]}" stroke-width="2"/>')
        elif p.kind == "marker":
            x=sx(p.x1_mm); role=p.role if p.role in {"common","lock"} else "common"; label="LOCK" if role=="lock" else "COMMON"; text_fill="#6d28d9" if role=="lock" else "#166534"
            out.append(f'<line x1="{x:.2f}" y1="{sy(p.y1):.2f}" x2="{x:.2f}" y2="{sy(p.y2):.2f}" stroke="{strokes[role]}" stroke-width="4" stroke-dasharray="7 4"/>')
            out.append(f'<text x="{x+5:.2f}" y="{sy(0.07):.2f}" font-family="Segoe UI,Arial" font-size="10" fill="{text_fill}">{label}</text>')
        elif p.kind == "line":
            out.append(f'<line x1="{sx(p.x1_mm):.2f}" y1="{sy(p.y1):.2f}" x2="{sx(p.x2_mm):.2f}" y2="{sy(p.y2):.2f}" stroke="{strokes.get(p.role,"#64748b")}" stroke-width="1" stroke-dasharray="6 5"/>')
    # scale ticks
    for frac in (0,.25,.5,.75,1):
        x=sx(length*frac); out.append(f'<line x1="{x:.2f}" y1="{top+bar_h+8:.2f}" x2="{x:.2f}" y2="{top+bar_h+14:.2f}" stroke="#64748b"/>')
        out.append(f'<text x="{x:.2f}" y="{top+bar_h+30:.2f}" text-anchor="middle" font-family="Segoe UI,Arial" font-size="10" fill="#475569">{length*frac:.0f}</text>')
    out.append('</svg>')
    target.write_text("\n".join(out), encoding="utf-8")
    return target


__all__ = ["BarPrimitive", "BarScene", "build_bar_scene", "scene_to_svg", "piece_display_color", "PIECE_PALETTE"]
