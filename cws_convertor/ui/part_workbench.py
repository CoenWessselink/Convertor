"""Tk-based Part Workbench bound to the versioned project service contract."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from cws_convertor.project import Part, ProjectSession


STATUS_COLORS = {
    "validated": ("GEVALIDEERD", "#166534", "#edf8f2"),
    "released": ("VRIJGEGEVEN", "#166534", "#edf8f2"),
    "review": ("CONTROLE NODIG", "#8a4b08", "#fff8e8"),
    "blocked": ("GEBLOKKEERD", "#9c0006", "#fdecec"),
    "idle": ("NIET GESTART", "#475569", "#eef4fa"),
}


def source_dimensions_mm(part: Part) -> tuple[float, float, float] | None:
    """Return trustworthy imported extents, without inventing missing dimensions."""

    descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, dict) else {}
    candidates = (
        descriptor.get("bbox_mm"),
        dict(descriptor.get("cad_metrics") or {}).get("bbox_mm"),
        dict(descriptor.get("source_mesh_metrics") or {}).get("bbox_mm"),
        descriptor.get("bbox_sorted_mm"),
    )
    for raw in candidates:
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            continue
        try:
            values = tuple(float(value) for value in raw)
        except (TypeError, ValueError):
            continue
        if all(math.isfinite(value) and value > 0.0 for value in values):
            return values
    return None


def rectangle_contour(width: float, height: float) -> dict[str, Any]:
    points = ((0.0, 0.0), (width, 0.0), (width, height), (0.0, height))
    segments = []
    for index, start in enumerate(points):
        segments.append(
            {
                "kind": "line",
                "start": list(start),
                "end": list(points[(index + 1) % len(points)]),
            }
        )
    return {
        "contour_id": "outer-1",
        "role": "outer",
        "closed": True,
        "segments": segments,
    }


def _short(value: Any, limit: int = 72) -> str:
    if value in (None, ""):
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


class PartWorkbenchPanel(ttk.Frame):
    """Integrated analytical editor; all persisted changes go through ProjectSession."""

    PART_FORMS = ("unknown", "plate", "profile", "round_bar", "custom")

    def __init__(
        self,
        master,
        *,
        session_provider: Callable[[], ProjectSession | None],
        changed_callback: Callable[[], None] | None = None,
        selection_callback: Callable[[str], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=0)
        self.session_provider = session_provider
        self.changed_callback = changed_callback or (lambda: None)
        self.selection_callback = selection_callback or (lambda _part_id: None)
        self.status_callback = status_callback or (lambda _message: None)
        self._selected_part_id = ""
        self._parts: dict[str, Part] = {}
        self._sort_reverse: dict[str, bool] = {}
        self._contours: list[dict[str, Any]] = []
        self._features: list[dict[str, Any]] = []
        self._reference_sides: list[dict[str, Any]] = []
        self._selected_hole_id = ""
        self._loading = False
        self._busy = False

        self.search_var = tk.StringVar(value="")
        self.form_filter_var = tk.StringVar(value="alle")
        self.user_var = tk.StringVar(value="gui")
        self.reason_var = tk.StringVar(value="Werkrevisie bijgewerkt")
        self.part_form_var = tk.StringVar(value="unknown")
        self.candidate_var = tk.StringVar(value="")
        self.confidence_var = tk.StringVar(value="0.000")
        self.length_var = tk.StringVar(value="0.000")
        self.thickness_var = tk.StringVar(value="0.000")
        self.diameter_var = tk.StringVar(value="0.000")
        self.recognition_confirmed_var = tk.BooleanVar(value=False)
        self.side_id_var = tk.StringVar(value="top")
        self.side_label_var = tk.StringVar(value="Bovenzijde")
        self.face_ref_var = tk.StringVar(value="unknown")
        self.side_confirmed_var = tk.BooleanVar(value=False)
        self.hole_x_var = tk.StringVar(value="0.000")
        self.hole_y_var = tk.StringVar(value="0.000")
        self.hole_diameter_var = tk.StringVar(value="14.000")
        self.hole_side_var = tk.StringVar(value="top")
        self.status_var = tk.StringVar(value="Geen onderdeel geselecteerd")
        self.canonical_status_var = tk.StringVar(value="Nog niet opgebouwd")

        self._build_ui()
        self.clear()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(8, 7))
        toolbar.grid(row=0, column=0, sticky="ew")
        self.start_button = ttk.Button(toolbar, text="Start", command=self.start_workbench)
        self.start_button.pack(side="left")
        self.apply_button = ttk.Button(
            toolbar, text="Toepassen", command=self.apply_changes, style="CWS.Primary.TButton"
        )
        self.apply_button.pack(side="left", padx=(5, 0))
        self.undo_button = ttk.Button(toolbar, text="Ongedaan", command=self.undo)
        self.undo_button.pack(side="left", padx=(12, 0))
        self.redo_button = ttk.Button(toolbar, text="Opnieuw", command=self.redo)
        self.redo_button.pack(side="left", padx=(5, 0))
        self.validate_button = ttk.Button(toolbar, text="Valideren", command=self.validate)
        self.validate_button.pack(side="left", padx=(12, 0))
        self.rebuild_button = ttk.Button(toolbar, text="Opbouwen", command=self.rebuild_canonical)
        self.rebuild_button.pack(side="left", padx=(5, 0))
        self.roundtrip_button = ttk.Button(toolbar, text="Roundtrips", command=self.validate_roundtrips)
        self.roundtrip_button.pack(side="left", padx=(5, 0))
        self.release_button = ttk.Button(toolbar, text="Vrijgeven", command=self.release)
        self.release_button.pack(side="left", padx=(5, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(toolbar, text="Passend", command=self.fit_view).pack(side="left")
        ttk.Button(toolbar, text="Iso", command=lambda: self.set_view(24, -58)).pack(side="left", padx=(5, 0))
        ttk.Button(toolbar, text="Voor", command=lambda: self.set_view(0, -90)).pack(side="left", padx=(5, 0))
        ttk.Button(toolbar, text="Boven", command=lambda: self.set_view(90, -90)).pack(side="left", padx=(5, 0))
        ttk.Label(toolbar, textvariable=self.status_var, anchor="e").pack(
            side="right", fill="x", expand=True, padx=(12, 0)
        )

        vertical = ttk.Panedwindow(self, orient="vertical")
        vertical.grid(row=1, column=0, sticky="nsew")
        upper = ttk.Panedwindow(vertical, orient="horizontal")
        lower = ttk.Frame(vertical)
        vertical.add(upper, weight=4)
        vertical.add(lower, weight=2)

        left = ttk.Frame(upper, padding=(6, 4))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        ttk.Label(left, text="Onderdelen", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        filters = ttk.Frame(left)
        filters.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        filters.columnconfigure(0, weight=1)
        search = ttk.Entry(filters, textvariable=self.search_var)
        search.grid(row=0, column=0, sticky="ew")
        search.bind("<KeyRelease>", lambda _event: self._refresh_part_grid())
        form_filter = ttk.Combobox(
            filters,
            textvariable=self.form_filter_var,
            values=("alle",) + self.PART_FORMS,
            state="readonly",
            width=11,
        )
        form_filter.grid(row=0, column=1, padx=(5, 0))
        form_filter.bind("<<ComboboxSelected>>", lambda _event: self._refresh_part_grid())
        columns = ("state", "position", "profile", "material", "length", "issues")
        self.part_grid = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        labels = {
            "state": "Status",
            "position": "Pos.",
            "profile": "Profiel / type",
            "material": "Mater.",
            "length": "Lengte",
            "issues": "!",
        }
        widths = {"state": 78, "position": 50, "profile": 90, "material": 62, "length": 60, "issues": 40}
        for column in columns:
            self.part_grid.heading(column, text=labels[column], command=lambda c=column: self._sort_parts(c))
            self.part_grid.column(column, width=widths[column], minwidth=45, anchor="w")
        self.part_grid.grid(row=2, column=0, sticky="nsew")
        part_scroll = ttk.Scrollbar(left, orient="vertical", command=self.part_grid.yview)
        part_scroll.grid(row=2, column=1, sticky="ns")
        self.part_grid.configure(yscrollcommand=part_scroll.set)
        self.part_grid.bind("<<TreeviewSelect>>", self._on_part_selected)
        self.part_grid.tag_configure("ok", background="#edf8f2")
        self.part_grid.tag_configure("review", background="#fff8e8")
        self.part_grid.tag_configure("blocked", background="#fdecec")
        self.part_grid.tag_configure("selected", background="#dbeafe")
        upper.add(left, weight=2)

        preview = ttk.Frame(upper, padding=(2, 4))
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(1, weight=1)
        preview_header = ttk.Frame(preview)
        preview_header.grid(row=0, column=0, sticky="ew", padx=6)
        ttk.Label(preview_header, text="Bronomhulling en analytisch model", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Label(preview_header, text="grijs: bron  |  kleur: werkrevisie", foreground="#64748b").pack(side="right")
        self.figure = Figure(figsize=(8.2, 4.1), dpi=100, constrained_layout=True)
        self.figure.patch.set_facecolor("#f8fafc")
        self.axis_3d = self.figure.add_subplot(121, projection="3d")
        self.axis_2d = self.figure.add_subplot(122)
        self.canvas = FigureCanvasTkAgg(self.figure, master=preview)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        upper.add(preview, weight=5)

        right = ttk.Frame(upper, padding=(6, 4))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(4, weight=1)
        self.state_badge = tk.Label(
            right,
            text="NIET GESTART",
            bg="#eef4fa",
            fg="#475569",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=7,
            anchor="w",
        )
        self.state_badge.grid(row=0, column=0, sticky="ew")
        ttk.Label(right, text="Onderdeelgegevens", font=("Segoe UI", 10, "bold")).grid(
            row=1, column=0, sticky="w", pady=(8, 4)
        )
        property_frame = ttk.Frame(right)
        property_frame.grid(row=2, column=0, sticky="ew")
        property_frame.columnconfigure(0, weight=1)
        self.property_grid = ttk.Treeview(property_frame, columns=("value",), show="tree headings", height=2)
        self.property_grid.heading("#0", text="Eigenschap")
        self.property_grid.heading("value", text="Waarde")
        self.property_grid.column("#0", width=125, minwidth=85)
        self.property_grid.column("value", width=185, minwidth=90)
        self.property_grid.grid(row=0, column=0, sticky="ew")
        property_scroll = ttk.Scrollbar(property_frame, orient="vertical", command=self.property_grid.yview)
        property_scroll.grid(row=0, column=1, sticky="ns")
        self.property_grid.configure(yscrollcommand=property_scroll.set)
        ttk.Label(right, text="Blokkerende controles", font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="nw", pady=(8, 4)
        )
        issue_frame = ttk.Frame(right)
        issue_frame.grid(row=4, column=0, sticky="nsew")
        issue_frame.columnconfigure(0, weight=1)
        issue_frame.rowconfigure(0, weight=1)
        self.issue_grid = ttk.Treeview(issue_frame, columns=("field", "message"), show="headings")
        self.issue_grid.heading("field", text="Veld")
        self.issue_grid.heading("message", text="Controle")
        self.issue_grid.column("field", width=100, minwidth=65)
        self.issue_grid.column("message", width=245, minwidth=120)
        self.issue_grid.grid(row=0, column=0, sticky="nsew")
        issue_scroll = ttk.Scrollbar(issue_frame, orient="vertical", command=self.issue_grid.yview)
        issue_scroll.grid(row=0, column=1, sticky="ns")
        self.issue_grid.configure(yscrollcommand=issue_scroll.set)
        upper.add(right, weight=2)

        lower.columnconfigure(0, weight=1)
        lower.rowconfigure(0, weight=1)
        self.editor_tabs = ttk.Notebook(lower)
        self.editor_tabs.grid(row=0, column=0, sticky="nsew", padx=6, pady=(4, 6))
        self._build_general_tab()
        self._build_extra_tab()
        self._build_canonical_tab()
        self._build_operations_tab()
        self._build_contours_tab()
        self._build_holes_tab()
        self._build_key_value_tab("Codes / merken", "codes_grid")
        self._build_key_value_tab("Prijzen", "prices_grid")
        self._build_key_value_tab("Bewerkingstijden", "times_grid")
        self._build_provenance_tab()

    def _build_general_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=10)
        self.editor_tabs.add(page, text="Algemeen")
        for column in (1, 3, 5):
            page.columnconfigure(column, weight=1)
        fields = (
            ("Vorm", ttk.Combobox(page, textvariable=self.part_form_var, values=self.PART_FORMS, state="readonly", width=18)),
            ("Kandidaat", ttk.Entry(page, textvariable=self.candidate_var)),
            ("Confidence", ttk.Spinbox(page, textvariable=self.confidence_var, from_=0.0, to=1.0, increment=0.05, width=10)),
            ("Zijde-ID", ttk.Entry(page, textvariable=self.side_id_var)),
            ("Zijdelabel", ttk.Entry(page, textvariable=self.side_label_var)),
            ("Bronvlak", ttk.Entry(page, textvariable=self.face_ref_var)),
            ("Lengte mm", ttk.Entry(page, textvariable=self.length_var)),
            ("Plaatdikte mm", ttk.Entry(page, textvariable=self.thickness_var)),
            ("Diameter mm", ttk.Entry(page, textvariable=self.diameter_var)),
        )
        for index, (label, widget) in enumerate(fields):
            row, pair = divmod(index, 3)
            ttk.Label(page, text=label).grid(row=row, column=pair * 2, sticky="w", padx=(0, 5), pady=4)
            widget.grid(row=row, column=pair * 2 + 1, sticky="ew", padx=(0, 14), pady=4)
        ttk.Checkbutton(page, text="Herkenning bevestigd", variable=self.recognition_confirmed_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(7, 0)
        )
        ttk.Checkbutton(page, text="Referentiezijde bevestigd", variable=self.side_confirmed_var).grid(
            row=3, column=2, columnspan=2, sticky="w", pady=(7, 0)
        )
        ttk.Label(page, text="Reden").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(page, textvariable=self.reason_var).grid(
            row=4, column=1, columnspan=3, sticky="ew", padx=(0, 14), pady=(8, 0)
        )
        ttk.Label(page, text="Gebruiker").grid(row=4, column=4, sticky="e", padx=(0, 5), pady=(8, 0))
        ttk.Entry(page, textvariable=self.user_var, width=14).grid(row=4, column=5, sticky="ew", pady=(8, 0))

    def _build_extra_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Extra info")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.extra_grid = ttk.Treeview(page, columns=("value", "source"), show="tree headings")
        self.extra_grid.heading("#0", text="Eigenschap")
        self.extra_grid.heading("value", text="Waarde")
        self.extra_grid.heading("source", text="Herkomst")
        self.extra_grid.column("#0", width=220)
        self.extra_grid.column("value", width=180)
        self.extra_grid.column("source", width=240)
        self.extra_grid.grid(row=0, column=0, sticky="nsew")

    def _build_canonical_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Canonical vergelijking")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        ttk.Label(page, textvariable=self.canonical_status_var, font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.canonical_grid = ttk.Treeview(
            page,
            columns=("expected", "found", "delta", "status"),
            show="tree headings",
        )
        self.canonical_grid.heading("#0", text="Eigenschap")
        self.canonical_grid.heading("expected", text="Bron / verwacht")
        self.canonical_grid.heading("found", text="Canonical / gevonden")
        self.canonical_grid.heading("delta", text="Verschil")
        self.canonical_grid.heading("status", text="Resultaat")
        self.canonical_grid.column("#0", width=180, minwidth=110)
        self.canonical_grid.column("expected", width=185, minwidth=100)
        self.canonical_grid.column("found", width=185, minwidth=100)
        self.canonical_grid.column("delta", width=150, minwidth=90)
        self.canonical_grid.column("status", width=150, minwidth=110)
        self.canonical_grid.grid(row=1, column=0, sticky="nsew")

    def _build_operations_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Bewerkingen")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.operation_grid = ttk.Treeview(
            page, columns=("kind", "side", "parameters"), show="tree headings"
        )
        self.operation_grid.heading("#0", text="ID")
        self.operation_grid.heading("kind", text="Type")
        self.operation_grid.heading("side", text="Zijde")
        self.operation_grid.heading("parameters", text="Parameters")
        self.operation_grid.column("#0", width=145)
        self.operation_grid.column("kind", width=100)
        self.operation_grid.column("side", width=100)
        self.operation_grid.column("parameters", width=460)
        self.operation_grid.grid(row=0, column=0, sticky="nsew")

    def _build_contours_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Hoeken / contouren")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.contour_grid = ttk.Treeview(
            page, columns=("role", "segments", "closed"), show="tree headings", selectmode="browse"
        )
        self.contour_grid.heading("#0", text="Contour-ID")
        self.contour_grid.heading("role", text="Rol")
        self.contour_grid.heading("segments", text="Segmenten")
        self.contour_grid.heading("closed", text="Gesloten")
        self.contour_grid.column("#0", width=180)
        self.contour_grid.column("role", width=100)
        self.contour_grid.column("segments", width=100)
        self.contour_grid.column("closed", width=90)
        self.contour_grid.grid(row=0, column=0, sticky="nsew")
        buttons = ttk.Frame(page)
        buttons.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(buttons, text="Bron-bbox als rechthoek", command=self.use_source_bbox).pack(side="left")
        ttk.Button(buttons, text="Contour verwijderen", command=self.remove_contour).pack(side="left", padx=(6, 0))

    def _build_holes_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Gaten")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.hole_grid = ttk.Treeview(
            page, columns=("side", "x", "y", "diameter", "through"), show="tree headings", selectmode="browse"
        )
        for column, label, width in (
            ("#0", "Gat-ID", 150), ("side", "Zijde", 95), ("x", "X mm", 95),
            ("y", "Y mm", 95), ("diameter", "Diameter mm", 110), ("through", "Doorlopend", 90),
        ):
            self.hole_grid.heading(column, text=label)
            self.hole_grid.column(column, width=width, minwidth=65)
        self.hole_grid.grid(row=0, column=0, sticky="nsew")
        self.hole_grid.bind("<<TreeviewSelect>>", self._on_hole_selected)
        editor = ttk.Frame(page)
        editor.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        for index, (label, variable, width) in enumerate(
            (("Zijde", self.hole_side_var, 12), ("X", self.hole_x_var, 10),
             ("Y", self.hole_y_var, 10), ("Diameter", self.hole_diameter_var, 10))
        ):
            ttk.Label(editor, text=label).pack(side="left", padx=(0 if index == 0 else 9, 4))
            ttk.Entry(editor, textvariable=variable, width=width).pack(side="left")
        ttk.Button(editor, text="Toevoegen / bijwerken", command=self.add_or_update_hole).pack(side="left", padx=(12, 0))
        ttk.Button(editor, text="Verwijderen", command=self.remove_hole).pack(side="left", padx=(6, 0))
        ttk.Button(editor, text="Nieuw", command=self.new_hole).pack(side="left", padx=(6, 0))

    def _build_key_value_tab(self, label: str, attribute: str) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text=label)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        grid = ttk.Treeview(page, columns=("value",), show="tree headings")
        grid.heading("#0", text="Eigenschap")
        grid.heading("value", text="Waarde")
        grid.column("#0", width=260)
        grid.column("value", width=520)
        grid.grid(row=0, column=0, sticky="nsew")
        setattr(self, attribute, grid)

    def _build_provenance_tab(self) -> None:
        page = ttk.Frame(self.editor_tabs, padding=6)
        self.editor_tabs.add(page, text="Herkomst / validatie")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        self.provenance_grid = ttk.Treeview(
            page, columns=("method", "confidence", "status", "source"), show="tree headings"
        )
        self.provenance_grid.heading("#0", text="Veld")
        self.provenance_grid.heading("method", text="Methode")
        self.provenance_grid.heading("confidence", text="Confidence")
        self.provenance_grid.heading("status", text="Status")
        self.provenance_grid.heading("source", text="Bronpad")
        self.provenance_grid.column("#0", width=210)
        self.provenance_grid.column("method", width=110)
        self.provenance_grid.column("confidence", width=90)
        self.provenance_grid.column("status", width=110)
        self.provenance_grid.column("source", width=340)
        self.provenance_grid.grid(row=0, column=0, sticky="nsew")

    def refresh(self, selected_part_id: str | None = None) -> None:
        session = self.session_provider()
        self._parts = dict(session.project.parts) if session is not None else {}
        target = selected_part_id or self._selected_part_id
        self._refresh_part_grid()
        if target in self._parts:
            self.select_part(target, notify=False)
        elif self._parts:
            self.select_part(next(iter(self._parts)), notify=False)
        else:
            self.clear()

    def clear(self) -> None:
        self._selected_part_id = ""
        self._contours = []
        self._features = []
        self._reference_sides = []
        self._set_controls_enabled(False)
        self.status_var.set("Geen onderdeel geselecteerd")
        self.canonical_status_var.set("Nog niet opgebouwd")
        self._set_badge("idle")
        for grid in self._all_detail_grids():
            grid.delete(*grid.get_children())
        self._render_preview(None)

    def _all_detail_grids(self) -> tuple[ttk.Treeview, ...]:
        return (
            self.property_grid,
            self.issue_grid,
            self.extra_grid,
            self.canonical_grid,
            self.operation_grid,
            self.contour_grid,
            self.hole_grid,
            self.codes_grid,
            self.prices_grid,
            self.times_grid,
            self.provenance_grid,
        )

    def _refresh_part_grid(self) -> None:
        selected = self._selected_part_id
        self.part_grid.delete(*self.part_grid.get_children())
        search = self.search_var.get().strip().lower()
        form_filter = self.form_filter_var.get().strip()
        for part in sorted(self._parts.values(), key=lambda item: (item.part_position or "~", item.name, item.internal_id)):
            revision = dict(part.workbench.get("current_revision") or {})
            part_form = str(revision.get("part_form") or "unknown")
            if form_filter not in {"", "alle"} and part_form != form_filter:
                continue
            haystack = " ".join(
                (part.name, part.part_position, part.profile, part.normalized_profile, part.material,
                 part.material_grade, part_form)
            ).lower()
            if search and search not in haystack:
                continue
            issues = list(revision.get("validation_issues") or [])
            if not part.workbench:
                state, tag = "niet gestart", "review"
            elif issues:
                state, tag = "geblokkeerd", "blocked"
            elif revision.get("review_status") in {"validated", "released"}:
                state, tag = str(revision.get("review_status")), "ok"
            else:
                state, tag = "controle", "review"
            self.part_grid.insert(
                "", "end", iid=part.internal_id, tags=(tag,),
                values=(state, part.part_position or "-", part.normalized_profile or part.profile or part_form,
                        part.normalized_material or part.material_grade or part.material or "-",
                        f"{part.length_mm:.3f}", len(issues)),
            )
        if selected and self.part_grid.exists(selected):
            self.part_grid.selection_set(selected)
            self.part_grid.focus(selected)

    def _sort_parts(self, column: str) -> None:
        reverse = not self._sort_reverse.get(column, False)
        self._sort_reverse[column] = reverse
        rows = [(self.part_grid.set(item, column), item) for item in self.part_grid.get_children("")]
        if column in {"length", "issues"}:
            def key(item: tuple[str, str]) -> float:
                try:
                    return float(item[0])
                except ValueError:
                    return 0.0
        else:
            def key(item: tuple[str, str]) -> str:
                return item[0].lower()
        rows.sort(key=key, reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.part_grid.move(item, "", index)

    def select_part(self, part_id: str, *, notify: bool = True) -> None:
        if part_id not in self._parts:
            return
        self._selected_part_id = part_id
        if self.part_grid.exists(part_id):
            self.part_grid.selection_set(part_id)
            self.part_grid.focus(part_id)
            self.part_grid.see(part_id)
        self._load_selected_part()
        if notify:
            self.selection_callback(part_id)

    def _on_part_selected(self, _event=None) -> None:
        selected = self.part_grid.selection()
        if selected and selected[0] != self._selected_part_id:
            self.select_part(selected[0])

    def _load_selected_part(self) -> None:
        part = self._current_part()
        if part is None:
            self.clear()
            return
        self._loading = True
        state = part.workbench
        revision = dict(state.get("current_revision") or {})
        recognition = dict(revision.get("recognition") or {})
        self.part_form_var.set(str(revision.get("part_form") or "unknown"))
        self.candidate_var.set(str(recognition.get("candidate") or part.normalized_profile or part.profile or ""))
        self.confidence_var.set(f"{float(recognition.get('confidence', part.profile_confidence or part.confidence or 0.0)):.3f}")
        dimensions = dict(revision.get("dimensions") or {})
        source_dimensions = source_dimensions_mm(part)
        source_sorted = sorted(source_dimensions, reverse=True) if source_dimensions else []
        fallback_length = part.length_mm or (source_sorted[0] if source_sorted else 0.0)
        fallback_thickness = source_sorted[-1] if source_sorted else 0.0
        self.length_var.set(f"{float(dimensions.get('length_mm', fallback_length) or 0.0):.3f}")
        self.thickness_var.set(f"{float(dimensions.get('thickness_mm', fallback_thickness) or 0.0):.3f}")
        self.diameter_var.set(f"{float(dimensions.get('diameter_mm', 0.0) or 0.0):.3f}")
        self.recognition_confirmed_var.set(bool(recognition.get("confirmed", False)))
        self._reference_sides = deepcopy(list(revision.get("reference_sides") or []))
        side = self._reference_sides[0] if self._reference_sides else {}
        self.side_id_var.set(str(side.get("side_id") or "top"))
        self.side_label_var.set(str(side.get("label") or "Bovenzijde"))
        self.face_ref_var.set(str(side.get("face_ref") or "unknown"))
        self.side_confirmed_var.set(bool(side.get("confirmed", False)))
        self._contours = deepcopy(list(revision.get("contours") or []))
        self._features = deepcopy(list(revision.get("features") or []))
        self._selected_hole_id = ""
        self._loading = False
        self._set_controls_enabled(True)
        self._populate_detail_grids(part, state, revision)
        self._render_preview(part)

    def _populate_detail_grids(self, part: Part, state: dict[str, Any], revision: dict[str, Any]) -> None:
        for grid in self._all_detail_grids():
            grid.delete(*grid.get_children())
        issues = list(revision.get("validation_issues") or [])
        if not state:
            badge = "idle"
        elif issues:
            badge = "blocked"
        elif revision.get("review_status") in {"validated", "released"}:
            badge = str(revision["review_status"])
        else:
            badge = "review"
        self._set_badge(badge)
        revision_number = int(revision.get("revision_number", 0) or 0)
        self.status_var.set(f"{part.part_position or part.name}  |  revisie {revision_number}  |  {len(issues)} blokkade(n)")
        properties = (
            ("Positie", part.part_position or part.name),
            ("Vorm", revision.get("part_form", "unknown")),
            ("Profiel", part.normalized_profile or part.profile),
            ("Materiaal", part.normalized_material or part.material_grade or part.material),
            ("Lengte mm", part.length_mm),
            ("Manufacturing hash", part.manufacturing_hash),
            ("NC1", "ja" if part.nc1_eligible else "nee"),
        )
        for label, value in properties:
            self.property_grid.insert("", "end", text=label, values=(_short(value),))
        for issue in issues:
            self.issue_grid.insert(
                "", "end", values=(_short(issue.get("field_path"), 36), _short(issue.get("message"), 110))
            )
        if state and not issues:
            self.issue_grid.insert("", "end", values=("-", "Geen blokkerende controles"))

        descriptor = part.geometry_descriptor if isinstance(part.geometry_descriptor, dict) else {}
        dimensions = source_dimensions_mm(part)
        extra = (
            ("Aantal", part.quantity_total, "projectmodel"),
            ("Lengte mm", part.length_mm, "projectmodel"),
            ("Massa per stuk kg", part.mass_each_kg, "projectmodel"),
            ("Oppervlakte per stuk m2", part.surface_area_each_m2, "projectmodel"),
            ("Bronafmetingen mm", dimensions, "geometry_descriptor"),
            ("Volume mm3", part.properties.get("volume_mm3"), "source properties"),
            ("Solids", descriptor.get("solid_count"), "geometry_descriptor"),
            ("Bronformaat", part.source_identity.source_format, "source identity"),
        )
        for label, value, source in extra:
            self.extra_grid.insert("", "end", text=label, values=(_short(value), source))
        self._refresh_draft_grids()

        codes = (
            ("Positienummer", part.part_position),
            ("Assemblymerk", part.source_identity.assembly_mark),
            ("Bronentity", part.source_identity.source_entity_id),
            ("Bron GlobalId", part.source_identity.global_id),
            ("Geometry hash", part.geometry_hash),
            ("Manufacturing hash", part.manufacturing_hash),
            ("Production identity", part.production_identity_hash),
        )
        for label, value in codes:
            self.codes_grid.insert("", "end", text=label, values=(_short(value, 120),))
        self._populate_matching_properties(self.prices_grid, part.properties, ("price", "cost", "prijs", "kosten"))
        self._populate_matching_properties(self.times_grid, part.properties, ("time", "duration", "tijd", "minutes", "hours"))
        provenance = dict(revision.get("field_provenance") or {})
        for field, value in sorted(provenance.items()):
            record = dict(value or {})
            self.provenance_grid.insert(
                "", "end", text=field,
                values=(record.get("method", ""), f"{float(record.get('confidence', 0.0)):.2f}",
                        record.get("status", ""), record.get("source_path", "")),
            )
        if not provenance:
            self.provenance_grid.insert("", "end", text="Nog geen gebruikerswijzigingen", values=("-", "-", "-", "-"))
        self._populate_canonical_result(state)

    def _populate_canonical_result(self, state: dict[str, Any]) -> None:
        record = dict(state.get("canonical_rebuild") or {})
        report = dict(record.get("report") or {})
        if not report:
            self.canonical_status_var.set("Nog niet opgebouwd")
            self.canonical_grid.insert(
                "", "end", text="Status", values=("-", "-", "-", "niet uitgevoerd")
            )
            return
        outcome = str(report.get("status") or "unknown")
        currency = str(record.get("status") or "invalidated")
        if currency != "current":
            self.canonical_status_var.set("ONGELDIG - werkrevisie is gewijzigd")
        elif outcome == "passed":
            self.canonical_status_var.set("GESLAAGD - canonical solid komt binnen tolerantie overeen")
        elif outcome == "failed":
            self.canonical_status_var.set("AFWIJKING - bron en canonical solid verschillen")
        elif outcome == "manual_validation_required":
            self.canonical_status_var.set("HANDMATIGE VALIDATIE VEREIST")
        else:
            self.canonical_status_var.set("GEBLOKKEERD - canonical solid niet opgebouwd")
        checks = list(dict(report.get("comparison") or {}).get("checks") or [])
        for check in checks:
            self.canonical_grid.insert(
                "",
                "end",
                text=str(check.get("property") or "?"),
                values=(
                    _short(check.get("expected"), 80),
                    _short(check.get("found"), 80),
                    _short(check.get("delta"), 80),
                    str(check.get("status") or "?"),
                ),
            )
        for reason in list(report.get("blocking_reasons") or []):
            self.canonical_grid.insert(
                "", "end", text="Blokkade", values=("-", "-", "-", _short(reason, 120))
            )
        if not checks and not list(report.get("blocking_reasons") or []):
            self.canonical_grid.insert("", "end", text="Status", values=("-", "-", "-", outcome))
        roundtrip = dict(dict(state.get("current_revision") or {}).get("roundtrip_validation") or {})
        for format_name in ("nc1", "step", "ifc", "pdf"):
            result = dict(dict(roundtrip.get("formats") or {}).get(format_name) or {})
            self.canonical_grid.insert(
                "",
                "end",
                text=f"Roundtrip {format_name.upper()}",
                values=(
                    "passed",
                    result.get("status", "not_run"),
                    "-",
                    _short(result.get("probable_cause") or result.get("artifact_path"), 120),
                ),
            )

    @staticmethod
    def _populate_matching_properties(grid: ttk.Treeview, properties: dict[str, Any], tokens: tuple[str, ...]) -> None:
        matches = [(key, value) for key, value in sorted(properties.items()) if any(token in key.lower() for token in tokens)]
        if not matches:
            grid.insert("", "end", text="Geen bronwaarde", values=("-",))
            return
        for key, value in matches:
            grid.insert("", "end", text=key, values=(_short(value, 120),))

    def _refresh_draft_grids(self) -> None:
        for grid in (self.operation_grid, self.contour_grid, self.hole_grid):
            grid.delete(*grid.get_children())
        for contour in self._contours:
            contour_id = str(contour.get("contour_id") or "")
            self.contour_grid.insert(
                "", "end", iid=contour_id or None, text=contour_id,
                values=(contour.get("role", ""), len(contour.get("segments") or []),
                        "ja" if contour.get("closed") else "nee"),
            )
        for feature in self._features:
            feature_id = str(feature.get("feature_id") or "")
            kind = str(feature.get("kind") or "")
            parameters = dict(feature.get("parameters") or {})
            self.operation_grid.insert(
                "", "end", text=feature_id,
                values=(kind, feature.get("reference_side", ""), _short(parameters, 100)),
            )
            if kind == "hole":
                self.hole_grid.insert(
                    "", "end", iid=feature_id or None, text=feature_id,
                    values=(feature.get("reference_side", ""), _short(parameters.get("x_mm")),
                            _short(parameters.get("y_mm")), _short(parameters.get("diameter_mm")),
                            "ja" if parameters.get("through", True) else "nee"),
                )

    def _set_controls_enabled(self, enabled: bool) -> None:
        part = self._current_part()
        active = bool(enabled and part is not None and not self._busy)
        state = part.workbench if part is not None else {}
        commands = list(state.get("commands") or [])
        cursor = int(state.get("command_cursor", 0) or 0)
        revision = dict(state.get("current_revision") or {})
        issues = list(revision.get("validation_issues") or [])
        self.start_button.configure(state="normal" if active and not state else "disabled")
        self.apply_button.configure(state="normal" if active else "disabled")
        self.undo_button.configure(state="normal" if active and cursor > 0 else "disabled")
        self.redo_button.configure(state="normal" if active and cursor < len(commands) else "disabled")
        self.validate_button.configure(
            state=(
                "normal"
                if active and state and not issues and revision.get("review_status") not in {"validated", "released"}
                else "disabled"
            )
        )
        self.rebuild_button.configure(state="normal" if active and state else "disabled")
        rebuild = dict(state.get("canonical_rebuild") or {})
        rebuild_report = dict(rebuild.get("report") or {})
        roundtrip = dict(revision.get("roundtrip_validation") or {})
        roundtrip_current = bool(
            roundtrip.get("status") == "passed"
            and roundtrip.get("manufacturing_hash") == (part.manufacturing_hash if part else "")
            and rebuild.get("status") == "current"
            and roundtrip.get("canonical_signature") == rebuild_report.get("canonical_signature")
        )
        self.roundtrip_button.configure(
            state=(
                "normal"
                if active and state and not issues and rebuild.get("status") == "current"
                and rebuild_report.get("status") == "passed"
                else "disabled"
            )
        )
        self.release_button.configure(
            state=(
                "normal"
                if active and roundtrip_current and revision.get("review_status") != "released"
                else "disabled"
            )
        )

    def set_busy(self, busy: bool) -> None:
        self._busy = bool(busy)
        self._set_controls_enabled(self._current_part() is not None)

    def _set_badge(self, status: str) -> None:
        text, foreground, background = STATUS_COLORS.get(status, STATUS_COLORS["review"])
        self.state_badge.configure(text=text, fg=foreground, bg=background)

    def _current_part(self) -> Part | None:
        return self._parts.get(self._selected_part_id)

    def _session(self) -> ProjectSession | None:
        return self.session_provider()

    def start_workbench(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        try:
            session.start_part_workbench(part.internal_id, user=self._user())
            self._notify_changed("Part Workbench gestart")
        except Exception as exc:
            self._show_error("Part Workbench starten", exc)

    def apply_changes(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        try:
            if not part.workbench:
                session.start_part_workbench(part.internal_id, user=self._user())
            confidence = float(self.confidence_var.get().replace(",", "."))
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("Confidence moet tussen 0 en 1 liggen")
            dimensions = {
                "length_mm": self._nonnegative_dimension(self.length_var.get(), "Lengte"),
                "thickness_mm": self._nonnegative_dimension(self.thickness_var.get(), "Plaatdikte"),
                "diameter_mm": self._nonnegative_dimension(self.diameter_var.get(), "Diameter"),
            }
            sides = deepcopy(self._reference_sides)
            current_side = {
                "side_id": self.side_id_var.get().strip(),
                "label": self.side_label_var.get().strip(),
                "face_ref": self.face_ref_var.get().strip(),
                "confirmed": self.side_confirmed_var.get(),
            }
            if sides:
                sides[0] = current_side
            elif current_side["side_id"]:
                sides.append(current_side)
            state = session.update_part_workbench(
                part.internal_id,
                {
                    "part_form": self.part_form_var.get(),
                    "recognition": {
                        "candidate": self.candidate_var.get().strip(),
                        "confidence": confidence,
                        "confirmed": self.recognition_confirmed_var.get(),
                    },
                    "dimensions": dimensions,
                    "reference_sides": sides,
                    "contours": deepcopy(self._contours),
                    "features": deepcopy(self._features),
                },
                user=self._user(),
                reason=self.reason_var.get().strip() or "Werkrevisie bijgewerkt",
            )
            issue_count = len(state["current_revision"].get("validation_issues") or [])
            self._notify_changed(f"Werkrevisie toegepast; {issue_count} blokkade(n)")
        except Exception as exc:
            self._show_error("Part Workbench bijwerken", exc)

    @staticmethod
    def _nonnegative_dimension(value: str, label: str) -> float:
        try:
            number = float(value.replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} moet numeriek zijn") from exc
        if not math.isfinite(number) or number < 0.0:
            raise ValueError(f"{label} moet nul of positief en eindig zijn")
        return number

    def undo(self) -> None:
        self._run_history_action("Ongedaan maken", lambda session, part: session.undo_part_workbench(part.internal_id, user=self._user()))

    def redo(self) -> None:
        self._run_history_action("Opnieuw uitvoeren", lambda session, part: session.redo_part_workbench(part.internal_id, user=self._user()))

    def _run_history_action(self, title: str, action: Callable[[ProjectSession, Part], Any]) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        try:
            action(session, part)
            self._notify_changed(title)
        except Exception as exc:
            self._show_error(title, exc)

    def validate(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        try:
            session.review_part_workbench(part.internal_id, user=self._user(), release=False)
            self._notify_changed("Werkrevisie gevalideerd; productie blijft wachten op roundtrip")
        except Exception as exc:
            self._show_error("Part Workbench valideren", exc)

    def rebuild_canonical(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        try:
            result = session.rebuild_part_canonical(part.internal_id, user=self._user())
            outcome = str(result.report.get("status") or "unknown")
            self._notify_changed(f"Canonical rebuild uitgevoerd: {outcome}")
        except Exception as exc:
            self._show_error("Canonical solid opbouwen", exc)

    def validate_roundtrips(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        initial = session.path.parent if session.path is not None else None
        folder = filedialog.askdirectory(
            parent=self,
            title="Map voor gevalideerde roundtripbestanden",
            initialdir=str(initial) if initial else None,
            mustexist=False,
        )
        if not folder:
            return
        self.set_busy(True)
        self.update_idletasks()
        try:
            report = session.validate_part_roundtrips(
                part.internal_id,
                folder,
                user=self._user(),
            )
            self._notify_changed(f"Roundtripmatrix uitgevoerd: {report.get('status', 'failed')}")
        except Exception as exc:
            self._show_error("Roundtripmatrix uitvoeren", exc)
        finally:
            self.set_busy(False)

    def release(self) -> None:
        session, part = self._require_selection()
        if session is None or part is None:
            return
        if not messagebox.askyesno(
            "Onderdeel vrijgeven",
            f"Onderdeel {part.part_position or part.name} voor productie vrijgeven?",
            parent=self,
        ):
            return
        try:
            session.review_part_workbench(part.internal_id, user=self._user(), release=True)
            self._notify_changed("Onderdeel voor productie vrijgegeven")
        except Exception as exc:
            self._show_error("Onderdeel vrijgeven", exc)

    def use_source_bbox(self) -> None:
        part = self._current_part()
        if part is None:
            return
        dimensions = source_dimensions_mm(part)
        if dimensions is None:
            self._show_error("Bron-bbox", ValueError("Dit onderdeel bevat geen betrouwbare bronafmetingen"))
            return
        width, height = sorted(dimensions, reverse=True)[:2]
        self.length_var.set(f"{max(dimensions):.3f}")
        self.thickness_var.set(f"{min(dimensions):.3f}")
        self._contours = [item for item in self._contours if item.get("role") != "outer"]
        self._contours.insert(0, rectangle_contour(width, height))
        self.part_form_var.set("plate")
        self._refresh_draft_grids()
        self._render_preview(part)
        self.status_var.set(f"Rechthoekkandidaat {width:.3f} x {height:.3f} mm; nog niet toegepast")

    def remove_contour(self) -> None:
        selected = self.contour_grid.selection()
        if not selected:
            return
        contour_id = selected[0]
        self._contours = [item for item in self._contours if str(item.get("contour_id")) != contour_id]
        self._refresh_draft_grids()
        self._render_preview(self._current_part())

    def new_hole(self) -> None:
        self._selected_hole_id = ""
        self.hole_grid.selection_remove(self.hole_grid.selection())
        self.hole_x_var.set("0.000")
        self.hole_y_var.set("0.000")
        self.hole_diameter_var.set("14.000")
        self.hole_side_var.set(self.side_id_var.get().strip() or "top")

    def _on_hole_selected(self, _event=None) -> None:
        selected = self.hole_grid.selection()
        if not selected:
            return
        self._selected_hole_id = selected[0]
        feature = next((item for item in self._features if item.get("feature_id") == self._selected_hole_id), None)
        if feature is None:
            return
        parameters = dict(feature.get("parameters") or {})
        self.hole_side_var.set(str(feature.get("reference_side") or "top"))
        self.hole_x_var.set(str(parameters.get("x_mm", 0.0)))
        self.hole_y_var.set(str(parameters.get("y_mm", 0.0)))
        self.hole_diameter_var.set(str(parameters.get("diameter_mm", 14.0)))

    def add_or_update_hole(self) -> None:
        try:
            x = float(self.hole_x_var.get().replace(",", "."))
            y = float(self.hole_y_var.get().replace(",", "."))
            diameter = float(self.hole_diameter_var.get().replace(",", "."))
            if not all(math.isfinite(value) for value in (x, y, diameter)) or diameter <= 0.0:
                raise ValueError("Gatwaarden moeten eindig zijn en diameter moet positief zijn")
        except ValueError as exc:
            self._show_error("Gat", exc)
            return
        feature_id = self._selected_hole_id or self._next_hole_id()
        feature = {
            "feature_id": feature_id,
            "kind": "hole",
            "reference_side": self.hole_side_var.get().strip() or self.side_id_var.get().strip(),
            "parameters": {"x_mm": x, "y_mm": y, "diameter_mm": diameter, "through": True},
        }
        index = next((index for index, item in enumerate(self._features) if item.get("feature_id") == feature_id), None)
        if index is None:
            self._features.append(feature)
        else:
            self._features[index] = feature
        self._selected_hole_id = feature_id
        self._refresh_draft_grids()
        if self.hole_grid.exists(feature_id):
            self.hole_grid.selection_set(feature_id)
        self._render_preview(self._current_part())

    def remove_hole(self) -> None:
        selected = self.hole_grid.selection()
        feature_id = selected[0] if selected else self._selected_hole_id
        if not feature_id:
            return
        self._features = [item for item in self._features if item.get("feature_id") != feature_id]
        self.new_hole()
        self._refresh_draft_grids()
        self._render_preview(self._current_part())

    def _next_hole_id(self) -> str:
        existing = {str(item.get("feature_id")) for item in self._features}
        number = 1
        while f"hole-{number}" in existing:
            number += 1
        return f"hole-{number}"

    def _require_selection(self) -> tuple[ProjectSession | None, Part | None]:
        session = self._session()
        part = self._current_part()
        if session is None or part is None:
            self._show_error("Part Workbench", ValueError("Selecteer eerst een onderdeel"))
            return None, None
        return session, part

    def _user(self) -> str:
        return self.user_var.get().strip() or "gui"

    def _notify_changed(self, message: str) -> None:
        selected = self._selected_part_id
        self.status_callback(message)
        self.changed_callback()
        self.refresh(selected)

    def _show_error(self, title: str, error: Exception) -> None:
        self.status_callback(f"{title}: {error}")
        messagebox.showerror(title, str(error), parent=self.winfo_toplevel())

    def set_view(self, elevation: float, azimuth: float) -> None:
        self.axis_3d.view_init(elev=elevation, azim=azimuth)
        self.canvas.draw_idle()

    def fit_view(self) -> None:
        self._render_preview(self._current_part())

    def _render_preview(self, part: Part | None) -> None:
        self.axis_3d.clear()
        self.axis_2d.clear()
        for axis in (self.axis_3d, self.axis_2d):
            axis.set_facecolor("#ffffff")
        self.axis_3d.set_title("3D vergelijking", fontsize=9)
        self.axis_2d.set_title("2D werkvlak", fontsize=9)
        self.axis_3d.set_axis_off()
        self.axis_2d.set_aspect("equal", adjustable="box")
        self.axis_2d.grid(True, color="#e2e8f0", linewidth=0.6)
        self.axis_2d.tick_params(labelsize=7, colors="#64748b")
        if part is None:
            self.axis_3d.text2D(0.5, 0.5, "Geen onderdeel", transform=self.axis_3d.transAxes, ha="center", color="#64748b")
            self.axis_2d.text(0.5, 0.5, "Geen analytisch model", transform=self.axis_2d.transAxes, ha="center", color="#64748b")
            self.canvas.draw_idle()
            return

        dimensions = source_dimensions_mm(part)
        if dimensions is not None:
            self._draw_box(dimensions, color="#94a3b8", alpha=0.16)
        else:
            self.axis_3d.text2D(0.5, 0.08, "Bronafmetingen niet beschikbaar", transform=self.axis_3d.transAxes, ha="center", color="#64748b", fontsize=8)

        polygon = self._outer_polygon()
        issues = list(dict(part.workbench.get("current_revision") or {}).get("validation_issues") or [])
        color = "#b42318" if issues else "#16835f"
        try:
            reviewed_thickness = float(self.thickness_var.get().replace(",", "."))
        except (TypeError, ValueError):
            reviewed_thickness = 0.0
        if polygon:
            thickness = reviewed_thickness if reviewed_thickness > 0.0 else (
                min(dimensions) if dimensions is not None else 0.0
            )
            z = thickness if thickness > 0.0 else 0.0
            vertices = [(x, y, z) for x, y in polygon[:-1]]
            self.axis_3d.add_collection3d(
                Poly3DCollection([vertices], facecolor=color, edgecolor="#0f172a", linewidth=1.0, alpha=0.42)
            )
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            self.axis_2d.plot(xs, ys, color=color, linewidth=2.0)
        for feature in self._features:
            if feature.get("kind") != "hole":
                continue
            parameters = dict(feature.get("parameters") or {})
            try:
                x = float(parameters.get("x_mm"))
                y = float(parameters.get("y_mm"))
                radius = float(parameters.get("diameter_mm")) / 2.0
            except (TypeError, ValueError):
                continue
            circle_x = [x + radius * math.cos(index * math.tau / 48.0) for index in range(49)]
            circle_y = [y + radius * math.sin(index * math.tau / 48.0) for index in range(49)]
            z = reviewed_thickness if reviewed_thickness > 0.0 else (
                min(dimensions) if dimensions is not None else 0.0
            )
            self.axis_3d.plot(circle_x, circle_y, [z] * len(circle_x), color="#2563a6", linewidth=1.5)
            self.axis_2d.plot(circle_x, circle_y, color="#2563a6", linewidth=1.5)
        self._fit_axes(dimensions, polygon)
        self.canvas.draw_idle()

    def _outer_polygon(self) -> list[tuple[float, float]]:
        contour = next((item for item in self._contours if item.get("role") == "outer"), None)
        if contour is None:
            return []
        segments = list(contour.get("segments") or [])
        if not segments or any(item.get("kind") != "line" for item in segments):
            return []
        points: list[tuple[float, float]] = []
        try:
            for segment in segments:
                start = segment["start"]
                points.append((float(start[0]), float(start[1])))
            end = segments[-1]["end"]
            points.append((float(end[0]), float(end[1])))
        except (KeyError, TypeError, ValueError, IndexError):
            return []
        return points

    def _draw_box(self, dimensions: tuple[float, float, float], *, color: str, alpha: float) -> None:
        x, y, z = dimensions
        points = ((0, 0, 0), (x, 0, 0), (x, y, 0), (0, y, 0), (0, 0, z), (x, 0, z), (x, y, z), (0, y, z))
        faces = (
            (points[0], points[1], points[2], points[3]), (points[4], points[5], points[6], points[7]),
            (points[0], points[1], points[5], points[4]), (points[1], points[2], points[6], points[5]),
            (points[2], points[3], points[7], points[6]), (points[3], points[0], points[4], points[7]),
        )
        self.axis_3d.add_collection3d(
            Poly3DCollection(faces, facecolor=color, edgecolor="#64748b", linewidth=0.7, alpha=alpha)
        )

    def _fit_axes(self, dimensions: tuple[float, float, float] | None, polygon: list[tuple[float, float]]) -> None:
        if polygon:
            xs = [point[0] for point in polygon]
            ys = [point[1] for point in polygon]
            x_max = max(xs) or 1.0
            y_max = max(ys) or 1.0
        elif dimensions is not None:
            x_max, y_max = dimensions[:2]
        else:
            x_max, y_max = 100.0, 100.0
        z_max = dimensions[2] if dimensions is not None else max(x_max, y_max) * 0.08
        margin_x = max(x_max * 0.08, 1.0)
        margin_y = max(y_max * 0.08, 1.0)
        self.axis_2d.set_xlim(-margin_x, x_max + margin_x)
        self.axis_2d.set_ylim(-margin_y, y_max + margin_y)
        self.axis_3d.set_xlim(0.0, max(x_max, 1.0))
        self.axis_3d.set_ylim(0.0, max(y_max, 1.0))
        self.axis_3d.set_zlim(0.0, max(z_max, 1.0))
        self.axis_3d.set_box_aspect((max(x_max, 1.0), max(y_max, 1.0), max(z_max, 1.0)))
        self.axis_3d.view_init(elev=24, azim=-58)


__all__ = ["PartWorkbenchPanel", "rectangle_contour", "source_dimensions_mm"]
