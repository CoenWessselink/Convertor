"""Uitgebreide Matplotlib/Tk-viewer voor bron/resultaatvergelijking.

Functies:
- assenvrije CAD-weergave;
- gekoppeld roteren en zoomen;
- scrollwielzoom;
- fit, standaardaanzichten en weergavemodi;
- omhullende doos en eenvoudige snede/clipping;
- punt-tot-punt meten op tessellatievertices;
- PNG-screenshot en kopiëren van modelinformatie.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import proj3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from conversion import load_shape, shape_metrics


@dataclass
class MeshData:
    vertices: np.ndarray
    triangles: np.ndarray
    metrics: dict[str, object]
    source: Path | None = None


def _canonical_mesh(points: np.ndarray) -> np.ndarray:
    centered = points - points.mean(axis=0)
    if len(points) < 4:
        return centered
    covariance = np.cov(centered, rowvar=False)
    _, eigenvectors = np.linalg.eigh(covariance)
    candidates = [eigenvectors[:, index] for index in range(3)]
    extents = [float(np.ptp(centered @ axis)) for axis in candidates]
    order = np.argsort(extents)[::-1]
    axes: list[np.ndarray] = []
    for index in order:
        axis = candidates[int(index)]
        largest = int(np.argmax(np.abs(axis)))
        if axis[largest] < 0:
            axis = -axis
        axes.append(axis)
    matrix = np.column_stack(axes)
    transformed = centered @ matrix
    # Guarantee a right-handed visual coordinate system.
    if np.linalg.det(matrix) < 0:
        transformed[:, 2] *= -1.0
    return transformed - (transformed.min(axis=0) + transformed.max(axis=0)) / 2.0


def _mesh_metrics(vertices: np.ndarray, triangles: np.ndarray) -> dict[str, object]:
    polygons = vertices[triangles]
    cross = np.cross(polygons[:, 1] - polygons[:, 0], polygons[:, 2] - polygons[:, 0])
    area = float(np.linalg.norm(cross, axis=1).sum() * 0.5)
    volume = abs(float(np.einsum("ij,ij->i", polygons[:, 0], np.cross(polygons[:, 1], polygons[:, 2])).sum() / 6.0))
    bbox = tuple(sorted((float(value) for value in np.ptp(vertices, axis=0)), reverse=True))
    return {"volume": volume, "area": area, "bbox": bbox, "solids": 1}


def mesh_from_shape(shape, tolerance: float = 0.8) -> MeshData:
    vertices, triangles = shape.tessellate(tolerance, 0.25)
    points = np.asarray([vertex.toTuple() for vertex in vertices], dtype=float)
    faces = np.asarray(triangles, dtype=int)
    if len(points) == 0 or len(faces) == 0:
        raise ValueError("Geen renderbare driehoeksgeometrie gevonden")
    return MeshData(_canonical_mesh(points), faces, shape_metrics(shape))


def mesh_from_path(path: str | Path, tolerance: float = 0.8) -> MeshData:
    source = Path(path)
    if source.suffix.lower() == ".ifc":
        from ifc_support import combined_mesh
        points, faces, metrics = combined_mesh(source)
        return MeshData(_canonical_mesh(points), np.asarray(faces, dtype=int), metrics, source)
    mesh = mesh_from_shape(load_shape(source), tolerance=tolerance)
    mesh.source = source
    return mesh


class ComparisonViewer(ttk.Frame):
    VIEW_MODES = ("Gearceerd + randen", "Gearceerd", "Draadmodel", "Transparant")

    def __init__(self, master) -> None:
        super().__init__(master, padding=6)
        self.left_mesh: MeshData | None = None
        self.right_mesh: MeshData | None = None
        self._last_axis = None
        self._syncing = False
        self._measure_enabled = False
        self._measure_points: dict[object, list[np.ndarray]] = {}
        self._measure_artists: dict[object, list[object]] = {}
        self._bbox_artists: dict[object, list[object]] = {}
        self._collections: dict[object, Poly3DCollection] = {}
        self._titles: dict[object, str] = {}

        self.view_mode = tk.StringVar(value=self.VIEW_MODES[0])
        self.sync_views = tk.BooleanVar(value=True)
        self.show_bbox = tk.BooleanVar(value=False)
        self.clip_axis = tk.StringVar(value="Geen")
        self.clip_percent = tk.DoubleVar(value=100.0)
        self.measure_status = tk.StringVar(value="Meten uit")

        self._build_toolbar()

        self.figure = Figure(figsize=(11, 5.2), dpi=100, constrained_layout=True)
        self.figure.patch.set_facecolor("#f1f1f1")
        self.left_axis = self.figure.add_subplot(121, projection="3d")
        self.right_axis = self.figure.add_subplot(122, projection="3d")
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, pady=(5, 0))

        self.info = tk.StringVar(value="Na een conversie verschijnt hier links het bronbestand en rechts het resultaat.")
        ttk.Label(self, textvariable=self.info, justify="left", wraplength=1500).pack(fill="x", pady=(5, 0))
        self.hint = tk.StringVar(
            value="Bediening: linkermuisknop slepen = roteren, middel/rechter slepen = verschuiven/zoomen, scroll = zoomen."
        )
        ttk.Label(self, textvariable=self.hint, foreground="#555555").pack(fill="x", pady=(2, 0))

        self.canvas.mpl_connect("motion_notify_event", self._synchronise_view)
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("button_release_event", self._on_button_release)
        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("key_press_event", self._on_key)
        self.clear()

    def _build_toolbar(self) -> None:
        first = ttk.Frame(self)
        first.pack(fill="x")
        ttk.Button(first, text="Passend", command=self.fit_all).pack(side="left", padx=(0, 2))
        ttk.Button(first, text="Zoom +", command=lambda: self.zoom(0.82)).pack(side="left", padx=2)
        ttk.Button(first, text="Zoom −", command=lambda: self.zoom(1.22)).pack(side="left", padx=2)
        ttk.Separator(first, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(first, text="Isometrisch", command=lambda: self.set_view(25, -55)).pack(side="left", padx=2)
        ttk.Button(first, text="Voor", command=lambda: self.set_view(0, -90)).pack(side="left", padx=2)
        ttk.Button(first, text="Boven", command=lambda: self.set_view(90, -90)).pack(side="left", padx=2)
        ttk.Button(first, text="Zij", command=lambda: self.set_view(0, 0)).pack(side="left", padx=2)
        ttk.Separator(first, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(first, text="Weergave:").pack(side="left")
        mode = ttk.Combobox(first, textvariable=self.view_mode, values=self.VIEW_MODES, state="readonly", width=20)
        mode.pack(side="left", padx=4)
        mode.bind("<<ComboboxSelected>>", lambda _event: self.redraw())
        ttk.Checkbutton(first, text="Aanzichten koppelen", variable=self.sync_views).pack(side="left", padx=8)
        ttk.Button(first, text="PNG opslaan", command=self.save_screenshot).pack(side="right", padx=2)
        ttk.Button(first, text="Info kopiëren", command=self.copy_info).pack(side="right", padx=2)

        second = ttk.Frame(self)
        second.pack(fill="x", pady=(4, 0))
        self.measure_button = ttk.Button(second, text="Meten", command=self.toggle_measure)
        self.measure_button.pack(side="left", padx=(0, 2))
        ttk.Button(second, text="Meting wissen", command=self.clear_measurements).pack(side="left", padx=2)
        ttk.Label(second, textvariable=self.measure_status).pack(side="left", padx=8)
        ttk.Separator(second, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Checkbutton(second, text="Omhullende doos", variable=self.show_bbox, command=self.redraw).pack(side="left")
        ttk.Separator(second, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(second, text="Snede:").pack(side="left")
        clip = ttk.Combobox(second, textvariable=self.clip_axis, values=("Geen", "Lengte", "Breedte", "Hoogte"), state="readonly", width=10)
        clip.pack(side="left", padx=4)
        clip.bind("<<ComboboxSelected>>", lambda _event: self.redraw())
        ttk.Scale(second, from_=5, to=100, variable=self.clip_percent, command=lambda _value: self._clip_changed()).pack(
            side="left", fill="x", expand=True, padx=6
        )
        self.clip_label = ttk.Label(second, text="100%", width=6)
        self.clip_label.pack(side="left")

    def clear(self) -> None:
        self.left_mesh = None
        self.right_mesh = None
        self._titles = {}
        self._measure_points.clear()
        self._measure_artists.clear()
        for axis, title in ((self.left_axis, "Origineel bestand"), (self.right_axis, "Geconverteerd bestand")):
            axis.clear()
            axis.set_title(title)
            axis.text2D(0.5, 0.5, "Nog geen model", transform=axis.transAxes, ha="center", va="center")
            self._hide_axis(axis)
        self.canvas.draw_idle()

    @staticmethod
    def _hide_axis(axis) -> None:
        axis.set_axis_off()
        axis.grid(False)
        try:
            axis.set_proj_type("ortho")
        except Exception:
            pass

    def _filtered_faces(self, mesh: MeshData) -> np.ndarray:
        axis_name = self.clip_axis.get()
        if axis_name == "Geen" or self.clip_percent.get() >= 99.9:
            return mesh.triangles
        axis_index = {"Lengte": 0, "Breedte": 1, "Hoogte": 2}.get(axis_name)
        if axis_index is None:
            return mesh.triangles
        coords = mesh.vertices[:, axis_index]
        minimum, maximum = float(coords.min()), float(coords.max())
        limit = minimum + (maximum - minimum) * float(self.clip_percent.get()) / 100.0
        centroids = mesh.vertices[mesh.triangles][:, :, axis_index].mean(axis=1)
        selected = mesh.triangles[centroids <= limit + 1e-9]
        return selected if len(selected) else mesh.triangles[:1]

    def _draw_mesh(self, axis, mesh: MeshData, title: str) -> None:
        axis.clear()
        faces = self._filtered_faces(mesh)
        polygons = mesh.vertices[faces]
        mode = self.view_mode.get()
        if mode == "Gearceerd":
            face_color, edge_color, line_width = (0.51, 0.61, 0.74, 0.96), "none", 0.0
        elif mode == "Draadmodel":
            face_color, edge_color, line_width = (0.65, 0.72, 0.82, 0.02), (0.10, 0.18, 0.28, 0.90), 0.42
        elif mode == "Transparant":
            face_color, edge_color, line_width = (0.42, 0.58, 0.78, 0.22), (0.10, 0.18, 0.28, 0.45), 0.24
        else:
            face_color, edge_color, line_width = (0.51, 0.61, 0.74, 0.90), (0.12, 0.16, 0.22, 0.34), 0.16
        collection = Poly3DCollection(polygons, linewidths=line_width, edgecolors=edge_color)
        collection.set_facecolor(face_color)
        axis.add_collection3d(collection)
        self._collections[axis] = collection
        self._titles[axis] = title
        axis.set_title(title, pad=10)
        self._fit_axis(axis, mesh)
        axis.view_init(elev=25, azim=-55)
        self._hide_axis(axis)
        if self.show_bbox.get():
            self._draw_bbox(axis, mesh)

    @staticmethod
    def _fit_axis(axis, mesh: MeshData, margin: float = 1.12) -> None:
        minima = mesh.vertices.min(axis=0)
        maxima = mesh.vertices.max(axis=0)
        center = (minima + maxima) / 2.0
        extents = np.maximum(maxima - minima, 1e-6)
        span = max(float(np.max(extents)) * margin / 2.0, 1.0)
        axis.set_xlim(center[0] - span, center[0] + span)
        axis.set_ylim(center[1] - span, center[1] + span)
        axis.set_zlim(center[2] - span, center[2] + span)
        axis.set_box_aspect((1, 1, 1))

    def _draw_bbox(self, axis, mesh: MeshData) -> None:
        minima = mesh.vertices.min(axis=0)
        maxima = mesh.vertices.max(axis=0)
        x0, y0, z0 = minima
        x1, y1, z1 = maxima
        corners = np.array([
            [x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
            [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1],
        ])
        edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
        artists=[]
        for a,b in edges:
            line, = axis.plot(*zip(corners[a], corners[b]), linestyle="--", linewidth=0.75, alpha=0.55)
            artists.append(line)
        self._bbox_artists[axis]=artists

    @staticmethod
    def _percent(first: float, second: float) -> float:
        return (second - first) / first * 100.0 if abs(first) > 1e-12 else 0.0

    def show_paths(
        self,
        source: str | Path,
        target: str | Path,
        *,
        source_title: str = "Origineel",
        target_title: str = "Geconverteerd",
    ) -> None:
        source, target = Path(source), Path(target)
        self.left_mesh = mesh_from_path(source)
        self.right_mesh = mesh_from_path(target)
        self._titles = {
            self.left_axis: f"{source_title}\n{source.name}",
            self.right_axis: f"{target_title}\n{target.name}",
        }
        self.redraw(reset_view=True)
        volume_delta = self._percent(float(self.left_mesh.metrics["volume"]), float(self.right_mesh.metrics["volume"]))
        area_delta = self._percent(float(self.left_mesh.metrics["area"]), float(self.right_mesh.metrics["area"]))
        left_bbox = tuple(float(value) for value in self.left_mesh.metrics["bbox"])
        right_bbox = tuple(float(value) for value in self.right_mesh.metrics["bbox"])
        bbox_text = " / ".join(f"{left_bbox[index]:.2f}→{right_bbox[index]:.2f}" for index in range(3))
        self.info.set(
            f"Volume: {self.left_mesh.metrics['volume']:.3f} → {self.right_mesh.metrics['volume']:.3f} mm³ "
            f"({volume_delta:+.6f}%)   |   Oppervlak: {self.left_mesh.metrics['area']:.3f} → "
            f"{self.right_mesh.metrics['area']:.3f} mm² ({area_delta:+.6f}%)\n"
            f"Gesorteerde omhullende maten bron→resultaat: {bbox_text} mm. "
            "Beide modellen zijn voor de vergelijking automatisch op hun hoofdrichtingen uitgelijnd."
        )
        self.clear_measurements(redraw=False)
        self.canvas.draw_idle()

    def redraw(self, *, reset_view: bool = False) -> None:
        old_views = {
            self.left_axis: (self.left_axis.elev, self.left_axis.azim, self.left_axis.get_xlim3d(), self.left_axis.get_ylim3d(), self.left_axis.get_zlim3d()),
            self.right_axis: (self.right_axis.elev, self.right_axis.azim, self.right_axis.get_xlim3d(), self.right_axis.get_ylim3d(), self.right_axis.get_zlim3d()),
        }
        for axis, mesh in ((self.left_axis, self.left_mesh), (self.right_axis, self.right_mesh)):
            if mesh is None:
                continue
            self._draw_mesh(axis, mesh, self._titles.get(axis, "Model"))
            if not reset_view:
                elev, azim, xlim, ylim, zlim = old_views[axis]
                axis.view_init(elev=elev, azim=azim)
                axis.set_xlim3d(xlim); axis.set_ylim3d(ylim); axis.set_zlim3d(zlim)
                self._hide_axis(axis)
        self.clear_measurements(redraw=False)
        self.canvas.draw_idle()

    def fit_all(self) -> None:
        for axis, mesh in ((self.left_axis, self.left_mesh), (self.right_axis, self.right_mesh)):
            if mesh is not None:
                self._fit_axis(axis, mesh)
                self._hide_axis(axis)
        self.canvas.draw_idle()

    def set_view(self, elevation: float, azimuth: float) -> None:
        for axis in (self.left_axis, self.right_axis):
            axis.view_init(elev=elevation, azim=azimuth)
            self._hide_axis(axis)
        self.canvas.draw_idle()

    def zoom(self, factor: float, axis=None) -> None:
        axes = [axis] if axis is not None and not self.sync_views.get() else [self.left_axis, self.right_axis]
        if axis is None and not self.sync_views.get():
            axes = [self._last_axis or self.left_axis]
        for current in axes:
            if current is None:
                continue
            for getter, setter in (
                (current.get_xlim3d, current.set_xlim3d),
                (current.get_ylim3d, current.set_ylim3d),
                (current.get_zlim3d, current.set_zlim3d),
            ):
                low, high = getter()
                center = (low + high) / 2.0
                half = max((high - low) * factor / 2.0, 1e-6)
                setter(center - half, center + half)
            self._hide_axis(current)
        self.canvas.draw_idle()

    def _on_scroll(self, event) -> None:
        if event.inaxes not in {self.left_axis, self.right_axis}:
            return
        self._last_axis = event.inaxes
        factor = 0.84 if event.button == "up" else 1.19
        self.zoom(factor, event.inaxes)

    def _on_button_press(self, event) -> None:
        if event.inaxes in {self.left_axis, self.right_axis}:
            self._last_axis = event.inaxes
        if self._measure_enabled and event.button == 1 and event.inaxes in {self.left_axis, self.right_axis}:
            self._pick_measure_point(event)

    def _on_button_release(self, event) -> None:
        if self.sync_views.get() and event.inaxes in {self.left_axis, self.right_axis}:
            self._copy_view(event.inaxes)

    def _synchronise_view(self, event) -> None:
        if self._syncing or not self.sync_views.get() or event.button not in {1, 2, 3}:
            return
        if event.inaxes not in {self.left_axis, self.right_axis}:
            return
        self._copy_view(event.inaxes, draw=False)
        self.canvas.draw_idle()

    def _copy_view(self, source, *, draw: bool = True) -> None:
        target = self.right_axis if source is self.left_axis else self.left_axis
        self._syncing = True
        try:
            target.view_init(elev=source.elev, azim=source.azim, roll=getattr(source, "roll", 0))
            self._hide_axis(source); self._hide_axis(target)
            if draw:
                self.canvas.draw_idle()
        finally:
            self._syncing = False

    def toggle_measure(self) -> None:
        self._measure_enabled = not self._measure_enabled
        self.measure_button.configure(text="Meten actief" if self._measure_enabled else "Meten")
        self.measure_status.set("Klik twee punten op hetzelfde model" if self._measure_enabled else "Meten uit")
        self.hint.set(
            "Meetmodus: klik twee zichtbare meshpunten op links of rechts; Esc wist de meting."
            if self._measure_enabled
            else "Bediening: linkermuisknop slepen = roteren, middel/rechter slepen = verschuiven/zoomen, scroll = zoomen."
        )

    def _pick_measure_point(self, event) -> None:
        axis = event.inaxes
        mesh = self.left_mesh if axis is self.left_axis else self.right_mesh
        if mesh is None:
            return
        xs, ys, _zs = proj3d.proj_transform(
            mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2], axis.get_proj()
        )
        display = axis.transData.transform(np.column_stack((xs, ys)))
        distances = np.hypot(display[:, 0] - event.x, display[:, 1] - event.y)
        index = int(np.argmin(distances))
        if float(distances[index]) > 28.0:
            self.measure_status.set("Geen modelpunt dichtbij; zoom verder in en klik opnieuw")
            return
        point = mesh.vertices[index].copy()
        points = self._measure_points.setdefault(axis, [])
        if len(points) >= 2:
            self._clear_axis_measure(axis)
            points = self._measure_points.setdefault(axis, [])
        points.append(point)
        artist = axis.scatter([point[0]], [point[1]], [point[2]], s=36, depthshade=False)
        self._measure_artists.setdefault(axis, []).append(artist)
        if len(points) == 1:
            self.measure_status.set("Eerste punt gekozen; kies tweede punt")
        else:
            first, second = points
            delta = second - first
            distance = float(np.linalg.norm(delta))
            line, = axis.plot(
                [first[0], second[0]], [first[1], second[1]], [first[2], second[2]], linewidth=2.2
            )
            midpoint = (first + second) / 2.0
            text = axis.text(midpoint[0], midpoint[1], midpoint[2], f" {distance:.3f} mm ", fontsize=9)
            self._measure_artists[axis].extend([line, text])
            self.measure_status.set(
                f"Afstand {distance:.3f} mm | ΔL {delta[0]:+.3f} | ΔB {delta[1]:+.3f} | ΔH {delta[2]:+.3f}"
            )
        self._hide_axis(axis)
        self.canvas.draw_idle()

    def _clear_axis_measure(self, axis) -> None:
        for artist in self._measure_artists.get(axis, []):
            try:
                artist.remove()
            except Exception:
                pass
        self._measure_artists[axis] = []
        self._measure_points[axis] = []

    def clear_measurements(self, *, redraw: bool = True) -> None:
        for axis in (getattr(self, "left_axis", None), getattr(self, "right_axis", None)):
            if axis is not None:
                self._clear_axis_measure(axis)
        self.measure_status.set("Klik twee punten op hetzelfde model" if self._measure_enabled else "Meten uit")
        if redraw and hasattr(self, "canvas"):
            self.canvas.draw_idle()

    def _clip_changed(self) -> None:
        self.clip_label.configure(text=f"{self.clip_percent.get():.0f}%")
        if self.clip_axis.get() != "Geen":
            self.redraw()

    def save_screenshot(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Viewerafbeelding opslaan",
            defaultextension=".png",
            filetypes=[("PNG-afbeelding", "*.png")],
        )
        if not filename:
            return
        try:
            self.figure.savefig(filename, dpi=180, bbox_inches="tight")
        except Exception as exc:
            messagebox.showerror("PNG opslaan", str(exc))

    def copy_info(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self.info.get() + "\n" + self.measure_status.get())
            self.update()
            self.measure_status.set("Modelinformatie naar klembord gekopieerd")
        except Exception as exc:
            messagebox.showerror("Kopiëren", str(exc))

    def _on_key(self, event) -> None:
        key = (event.key or "").lower()
        if key == "f":
            self.fit_all()
        elif key == "i":
            self.set_view(25, -55)
        elif key == "1":
            self.set_view(0, -90)
        elif key == "2":
            self.set_view(90, -90)
        elif key == "3":
            self.set_view(0, 0)
        elif key == "m":
            self.toggle_measure()
        elif key in {"escape", "esc"}:
            self.clear_measurements()
