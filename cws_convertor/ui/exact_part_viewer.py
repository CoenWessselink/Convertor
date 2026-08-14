"""Tk host for the integrated V6 exact OCCT Part Workbench viewer."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import queue
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Mapping

from cws_convertor.project import ProjectSession
from cws_convertor.viewer.v6_integration import (
    IntegratedExactPart,
    ViewerIntegrationBlocked,
    build_integrated_exact_part,
)
from cws_viewer.backends.occt_exact import OcctExactPartBackend
from cws_viewer.exact.model import SubshapeKind
from cws_viewer.exact.snapping import candidates_for_subshape
from cws_viewer.technology.contracts import NativeWindow


_SELECTION_KINDS = {
    "Vlak": SubshapeKind.FACE,
    "Rand": SubshapeKind.EDGE,
    "Punt": SubshapeKind.VERTEX,
}


class ExactPartViewerPanel(ttk.Frame):
    """Exact source/canonical review component; it never authorizes release."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        session_provider: Callable[[], ProjectSession | None],
        selection_callback: Callable[[Mapping[str, Any]], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=0)
        self.session_provider = session_provider
        self.selection_callback = selection_callback or (lambda _payload: None)
        self.status_callback = status_callback or (lambda _message: None)
        self.selection_kind_var = tk.StringVar(value="Vlak")
        self.status_var = tk.StringVar(value="Selecteer een onderdeel met exact bron-BREP")
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cws-exact-viewer")
        self._generation = 0
        self._part_id = ""
        self._request_key: tuple[str, str, str] | None = None
        self._integrated: IntegratedExactPart | None = None
        self._backend: OcctExactPartBackend | None = None
        self._resize_after_id: str | None = None
        self._load_events: queue.Queue[
            tuple[int, str, Future[IntegratedExactPart]]
        ] = queue.Queue()
        self._build_ui()
        self._poll_after_id: str | None = self.after(50, self._poll_load_events)

    @property
    def integrated(self) -> IntegratedExactPart | None:
        return self._integrated

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(self, padding=(6, 5))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(toolbar, text="Selectie").pack(side="left")
        selection = ttk.Combobox(
            toolbar,
            textvariable=self.selection_kind_var,
            values=tuple(_SELECTION_KINDS),
            state="readonly",
            width=8,
        )
        selection.pack(side="left", padx=(5, 9))
        selection.bind("<<ComboboxSelected>>", self._selection_kind_changed)
        ttk.Button(toolbar, text="Passend", command=self.fit_all).pack(side="left")
        ttk.Button(toolbar, text="Iso", command=self.set_isometric).pack(side="left", padx=(5, 0))
        ttk.Button(toolbar, text="Voor", command=self.set_front).pack(side="left", padx=(5, 0))
        ttk.Button(toolbar, text="Boven", command=self.set_top).pack(side="left", padx=(5, 0))
        ttk.Button(toolbar, text="Vergelijk exact", command=self.compare).pack(side="right")

        split = ttk.Panedwindow(self, orient="vertical")
        split.grid(row=1, column=0, sticky="nsew")
        viewer_frame = ttk.Frame(split)
        viewer_frame.columnconfigure(0, weight=1)
        viewer_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(
            viewer_frame,
            background="#101923",
            borderwidth=0,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Map>", self._canvas_mapped)
        self.canvas.bind("<Configure>", self._canvas_resized)
        self.canvas.bind("<Button-1>", self._canvas_clicked)
        split.add(viewer_frame, weight=5)

        evidence = ttk.Frame(split, padding=(5, 3))
        evidence.columnconfigure(0, weight=1)
        evidence.rowconfigure(0, weight=1)
        columns = ("kind", "geometry", "measure", "feature", "evidence")
        self.subshape_grid = ttk.Treeview(
            evidence,
            columns=columns,
            show="tree headings",
            selectmode="browse",
            height=6,
        )
        self.subshape_grid.heading("#0", text="Stabiel ID")
        for name, label, width in (
            ("kind", "Type", 70),
            ("geometry", "Geometrie", 110),
            ("measure", "Maat", 90),
            ("feature", "Feature", 150),
            ("evidence", "Bewijs", 95),
        ):
            self.subshape_grid.heading(name, text=label)
            self.subshape_grid.column(name, width=width, minwidth=55)
        self.subshape_grid.column("#0", width=210, minwidth=120)
        self.subshape_grid.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(evidence, orient="vertical", command=self.subshape_grid.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.subshape_grid.configure(yscrollcommand=scrollbar.set)
        self.subshape_grid.bind("<<TreeviewSelect>>", self._grid_selected)
        split.add(evidence, weight=2)

        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(7, 4)).grid(
            row=2, column=0, sticky="ew"
        )

    def load_part(self, part_id: str | None) -> None:
        value = str(part_id or "")
        session = self.session_provider()
        part = session.project.parts.get(value) if session is not None and value else None
        request_key = (
            value,
            str(getattr(part, "geometry_hash", "") or ""),
            str(getattr(part, "manufacturing_hash", "") or ""),
        )
        if value and request_key == self._request_key:
            return
        self._generation += 1
        generation = self._generation
        self._part_id = value
        self._request_key = request_key if value else None
        self._integrated = None
        self.subshape_grid.delete(*self.subshape_grid.get_children())
        self._dispose_backend()
        if not value:
            self.status_var.set("Selecteer een onderdeel met exact bron-BREP")
            return
        if session is None:
            self.status_var.set("Geen geopend project")
            return
        self.status_var.set("Exact source/canonical BREP wordt opgebouwd...")
        future = self._executor.submit(build_integrated_exact_part, session, value)
        future.add_done_callback(
            lambda item: self._load_events.put((generation, value, item))
        )

    def _poll_load_events(self) -> None:
        try:
            while True:
                generation, part_id, future = self._load_events.get_nowait()
                self._load_finished(generation, part_id, future)
        except queue.Empty:
            pass
        try:
            self._poll_after_id = self.after(50, self._poll_load_events)
        except tk.TclError:
            self._poll_after_id = None

    def _load_finished(
        self,
        generation: int,
        part_id: str,
        future: Future[IntegratedExactPart],
    ) -> None:
        if generation != self._generation or part_id != self._part_id:
            return
        try:
            integrated = future.result()
        except ViewerIntegrationBlocked as exc:
            message = f"Exacte viewer geblokkeerd: {exc} [{exc.code}]"
            self.status_var.set(message)
            self.status_callback(message)
            return
        except Exception as exc:
            message = f"Exacte viewer niet beschikbaar: {type(exc).__name__}: {exc}"
            self.status_var.set(message)
            self.status_callback(message)
            return
        self._integrated = integrated
        self._populate_subshapes()
        try:
            self._ensure_backend()
            assert self._backend is not None
            self._backend.load_parts(integrated.source, integrated.canonical)
            self._backend.set_selection_kind(_SELECTION_KINDS[self.selection_kind_var.get()])
        except Exception as exc:
            message = f"Exact BREP geladen; native weergave faalde: {type(exc).__name__}: {exc}"
            self.status_var.set(message)
            self.status_callback(message)
            self._dispose_backend()
            return
        snapshot = integrated.source.snapshot
        canonical_label = "met canonical overlay" if integrated.canonical is not None else "zonder canonical BREP"
        message = (
            f"Exact BREP: {snapshot.properties.face_count} vlakken, "
            f"{snapshot.properties.edge_count} randen, {snapshot.properties.vertex_count} punten; "
            f"{canonical_label}; productie blijft onder eigenaargates"
        )
        self.status_var.set(message)
        self.status_callback(message)

    def _populate_subshapes(self) -> None:
        self.subshape_grid.delete(*self.subshape_grid.get_children())
        if self._integrated is None:
            return
        snapshot = self._integrated.source.snapshot
        feature_by_subshape = {
            subshape_id: feature
            for feature in snapshot.features
            for subshape_id in feature.subshape_ids
        }
        for item in snapshot.subshapes:
            feature = feature_by_subshape.get(item.stable_id)
            self.subshape_grid.insert(
                "",
                "end",
                iid=item.stable_id,
                text=item.stable_id,
                values=(
                    item.kind.value,
                    item.geometry_type,
                    f"{item.measure:.6f}",
                    feature.feature_type if feature is not None else "-",
                    "exact_brep",
                ),
            )

    def _ensure_backend(self) -> None:
        if self._backend is not None:
            return
        self.update_idletasks()
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        backend = OcctExactPartBackend()
        backend.initialize(
            width=width,
            height=height,
            native_window=NativeWindow(int(self.canvas.winfo_id()), width, height),
        )
        self._backend = backend

    def _dispose_backend(self) -> None:
        backend, self._backend = self._backend, None
        if backend is not None:
            backend.dispose()

    def _selection_kind_changed(self, _event: Any = None) -> None:
        if self._backend is not None:
            self._backend.set_selection_kind(_SELECTION_KINDS[self.selection_kind_var.get()])

    def _canvas_mapped(self, _event: Any = None) -> None:
        if self._integrated is not None and self._backend is None:
            self.after_idle(self._reload_native_view)

    def _reload_native_view(self) -> None:
        if self._integrated is None:
            return
        try:
            self._ensure_backend()
            assert self._backend is not None
            self._backend.load_parts(self._integrated.source, self._integrated.canonical)
        except Exception as exc:
            self.status_var.set(f"Native exacte weergave faalde: {exc}")

    def _canvas_resized(self, event: tk.Event) -> None:
        if self._backend is None:
            return
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(80, self._apply_resize, event.width, event.height)

    def _apply_resize(self, width: int, height: int) -> None:
        self._resize_after_id = None
        if self._backend is not None:
            self._backend.resize(max(1, width), max(1, height))
            self._backend.render()

    def _canvas_clicked(self, event: tk.Event) -> None:
        if self._backend is None:
            return
        stable_id = self._backend.pick_at(int(event.x), int(event.y))
        if stable_id:
            self._select_subshape(stable_id, from_grid=False)

    def _grid_selected(self, _event: Any = None) -> None:
        selected = self.subshape_grid.selection()
        if selected:
            self._select_subshape(selected[0], from_grid=True)

    def _select_subshape(self, stable_id: str, *, from_grid: bool) -> None:
        if self._integrated is None:
            return
        service = self._integrated.service
        service.select_subshape(stable_id)
        if self._backend is not None:
            self._backend.highlight(stable_id)
        if not from_grid and self.subshape_grid.exists(stable_id):
            self.subshape_grid.selection_set(stable_id)
            self.subshape_grid.focus(stable_id)
            self.subshape_grid.see(stable_id)
        snapshot = self._integrated.source.snapshot
        descriptor = snapshot.subshape_by_id[stable_id]
        feature = next(
            (item for item in snapshot.features if stable_id in item.subshape_ids),
            None,
        )
        snaps = candidates_for_subshape(self._integrated.source, stable_id)
        payload = {
            "stable_id": stable_id,
            "kind": descriptor.kind.value,
            "geometry_type": descriptor.geometry_type,
            "feature_id": feature.feature_id if feature is not None else "",
            "feature_type": feature.feature_type if feature is not None else "",
            "diameter_mm": feature.diameter if feature is not None else None,
            "radius_mm": feature.radius if feature is not None else None,
            "snap_types": [item.snap_type.value for item in snaps],
            "evidence": "exact_brep",
        }
        self.selection_callback(payload)
        snap_text = ", ".join(payload["snap_types"][:4]) or "geen snap"
        self.status_var.set(f"{stable_id} geselecteerd; exact snapping: {snap_text}")

    def compare(self) -> None:
        if self._integrated is None:
            self.status_var.set("Geen exact onderdeel geladen")
            return
        result = self._integrated.validate_compare()
        if result["status"] == "blocked":
            self.status_var.set("Exacte vergelijking geblokkeerd: canonical BREP ontbreekt")
            return
        report = result["report"]
        delta = max(
            float(report["source_to_canonical_max_mm"]),
            float(report["canonical_to_source_max_mm"]),
        )
        self.status_var.set(
            f"Exact source/canonical: {str(result['status']).upper()}, max. afwijking {delta:.6f} mm"
        )

    def fit_all(self) -> None:
        if self._backend is not None:
            self._backend.fit_all()
            self._backend.render()

    def set_isometric(self) -> None:
        if self._backend is not None:
            self._backend.set_isometric_view()
            self._backend.fit_all()
            self._backend.render()

    def set_front(self) -> None:
        if self._backend is not None:
            self._backend.set_front_view()
            self._backend.render()

    def set_top(self) -> None:
        if self._backend is not None:
            self._backend.set_top_view()
            self._backend.render()

    def highlight_feature(self, kind: str, diameter_mm: float | None = None) -> bool:
        if self._integrated is None:
            return False
        matches = []
        for feature in self._integrated.source.snapshot.features:
            feature_type = feature.feature_type.lower()
            if kind == "hole":
                if "hole" not in feature_type and "cylind" not in feature_type:
                    continue
            elif kind.lower() not in feature_type:
                continue
            if diameter_mm is not None and feature.diameter is not None:
                if abs(float(feature.diameter) - float(diameter_mm)) > 1e-6:
                    continue
            matches.append(feature)
        if len(matches) != 1 or not matches[0].subshape_ids:
            return False
        self._select_subshape(matches[0].subshape_ids[0], from_grid=False)
        return True

    def clear(self) -> None:
        self._generation += 1
        self._part_id = ""
        self._request_key = None
        self._integrated = None
        self.subshape_grid.delete(*self.subshape_grid.get_children())
        self._dispose_backend()
        self.status_var.set("Selecteer een onderdeel met exact bron-BREP")

    def destroy(self) -> None:
        self._generation += 1
        if self._poll_after_id is not None:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._dispose_backend()
        self._executor.shutdown(wait=False, cancel_futures=True)
        super().destroy()


__all__ = ["ExactPartViewerPanel"]
