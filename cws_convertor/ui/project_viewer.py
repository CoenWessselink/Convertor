"""SteelModel-bound project viewer host for the desktop application."""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Mapping

from cws_convertor.project.model import ProjectModel
from cws_convertor.steel_model.adapter import build_steel_model_snapshot
from cws_convertor.steel_model.contracts import AccuracyStatus, SteelValidationRecord
from cws_convertor.steel_model.viewer_boundary import (
    ViewerHandshake,
    build_viewer_host_snapshot,
)
from cws_convertor.viewer.workspace import ACCURACY_LABELS, ViewerTreeNode, ViewerWorkspaceState


ACCURACY_TAGS: Mapping[str, str] = {
    AccuracyStatus.EXACT.value: "accuracy_exact",
    AccuracyStatus.TOLERANCE_VERIFIED.value: "accuracy_tolerance",
    AccuracyStatus.APPROXIMATE.value: "accuracy_approximate",
    AccuracyStatus.MANUAL_VALIDATION_REQUIRED.value: "accuracy_manual",
    AccuracyStatus.NOT_APPLICABLE.value: "accuracy_na",
}


class ProjectViewerPanel(ttk.Frame):
    """Project tree, properties and validation around a controlled renderer slot."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        selection_callback: Callable[[str], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=0)
        self.selection_callback = selection_callback or (lambda _steel_model_id: None)
        self.status_callback = status_callback or (lambda _message: None)
        self.state: ViewerWorkspaceState | None = None
        self._project: ProjectModel | None = None
        self._tree_to_model_id: dict[str, str] = {}
        self._model_to_tree_id: dict[str, str] = {}
        self._issue_to_model_id: dict[str, str] = {}
        self._renderer_handshake: ViewerHandshake | None = None
        self._renderer_command: Callable[[str, dict[str, Any]], None] | None = None
        self.search_var = tk.StringVar(value="")
        self.accuracy_mode_var = tk.BooleanVar(value=True)
        self.renderer_status_var = tk.StringVar(value="Renderer niet gekoppeld")
        self.selection_status_var = tk.StringVar(value="Geen object geselecteerd")
        self._build_ui()
        self._render_empty_state()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.grid(row=0, column=0, sticky="ew")
        self.select_button = ttk.Button(
            toolbar,
            text="Selecteren",
            command=lambda: self._run_renderer_command(
                "selection.begin", {"mode": "object"}
            ),
            state="disabled",
        )
        self.select_button.pack(side="left")
        self.fit_button = ttk.Button(
            toolbar,
            text="Passend",
            command=lambda: self._run_renderer_command("camera.fit_all"),
            state="disabled",
        )
        self.fit_button.pack(side="left", padx=(5, 0))
        self.iso_button = ttk.Button(
            toolbar,
            text="Iso",
            command=lambda: self._run_renderer_command(
                "camera.standard_view", {"view": "isometric"}
            ),
            state="disabled",
        )
        self.iso_button.pack(side="left", padx=(5, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        self.measure_button = ttk.Button(
            toolbar,
            text="Meten",
            command=lambda: self._run_renderer_command(
                "measurement.begin", {"kind": "distance"}
            ),
            state="disabled",
        )
        self.measure_button.pack(side="left")
        self.section_button = ttk.Button(
            toolbar,
            text="Doorsnede",
            command=lambda: self._run_renderer_command("section.begin"),
            state="disabled",
        )
        self.section_button.pack(side="left", padx=(5, 0))
        self.compare_button = ttk.Button(
            toolbar,
            text="Vergelijken",
            command=lambda: self._run_renderer_command("compare.open"),
            state="disabled",
        )
        self.compare_button.pack(side="left", padx=(5, 0))
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Checkbutton(
            toolbar,
            text="Nauwkeurigheid / debug",
            variable=self.accuracy_mode_var,
            command=self._refresh_center_status,
        ).pack(side="left")
        ttk.Label(toolbar, textvariable=self.renderer_status_var, anchor="e").pack(
            side="right", fill="x", expand=True, padx=(12, 0)
        )

        body = ttk.Panedwindow(self, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew")

        tree_panel = ttk.Frame(body, width=260)
        tree_panel.columnconfigure(0, weight=1)
        tree_panel.rowconfigure(2, weight=1)
        ttk.Label(tree_panel, text="Modelstructuur", style="Heading.TLabel").grid(
            row=0, column=0, sticky="ew", padx=8, pady=(8, 5)
        )
        search = ttk.Frame(tree_panel)
        search.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        search.columnconfigure(0, weight=1)
        search_entry = ttk.Entry(search, textvariable=self.search_var)
        search_entry.grid(row=0, column=0, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_tree())
        self.tree = ttk.Treeview(tree_panel, show="tree", selectmode="browse")
        self.tree.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        tree_scroll = ttk.Scrollbar(tree_panel, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=2, column=1, sticky="ns", pady=(0, 8))
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self._tree_selected)
        self.tree.tag_configure("accuracy_exact", foreground="#166534")
        self.tree.tag_configure("accuracy_tolerance", foreground="#1d4ed8")
        self.tree.tag_configure("accuracy_approximate", foreground="#9a5b08")
        self.tree.tag_configure("accuracy_manual", foreground="#a31515")
        self.tree.tag_configure("accuracy_na", foreground="#64748b")
        body.add(tree_panel, weight=1)

        center = ttk.Panedwindow(body, orient="vertical")
        scene = ttk.Frame(center)
        scene.columnconfigure(0, weight=1)
        scene.rowconfigure(0, weight=1)
        self.scene_canvas = tk.Canvas(
            scene,
            background="#171b19",
            highlightthickness=0,
            borderwidth=0,
        )
        self.scene_canvas.grid(row=0, column=0, sticky="nsew")
        self.scene_canvas.bind("<Configure>", lambda _event: self._draw_scene_status())
        center.add(scene, weight=5)

        issues_panel = ttk.Frame(center, height=155)
        issues_panel.columnconfigure(0, weight=1)
        issues_panel.rowconfigure(1, weight=1)
        issue_header = ttk.Frame(issues_panel, padding=(8, 5))
        issue_header.grid(row=0, column=0, sticky="ew")
        ttk.Label(issue_header, text="Validatie", style="Heading.TLabel").pack(side="left")
        self.issue_summary_label = ttk.Label(issue_header, text="Geen project")
        self.issue_summary_label.pack(side="right")
        issue_columns = ("severity", "object", "code", "message")
        self.issue_grid = ttk.Treeview(
            issues_panel,
            columns=issue_columns,
            show="headings",
            selectmode="browse",
            height=5,
        )
        for column, label, width in (
            ("severity", "Status", 90),
            ("object", "Object", 105),
            ("code", "Code", 120),
            ("message", "Controle", 480),
        ):
            self.issue_grid.heading(column, text=label)
            self.issue_grid.column(column, width=width, minwidth=65, anchor="w")
        self.issue_grid.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        issue_scroll = ttk.Scrollbar(issues_panel, orient="vertical", command=self.issue_grid.yview)
        issue_scroll.grid(row=1, column=1, sticky="ns", pady=(0, 8))
        self.issue_grid.configure(yscrollcommand=issue_scroll.set)
        self.issue_grid.bind("<<TreeviewSelect>>", self._issue_selected)
        self.issue_grid.tag_configure("error", background="#fdecec")
        self.issue_grid.tag_configure("warning", background="#fff8e8")
        self.issue_grid.tag_configure("information", background="#edf5fb")
        center.add(issues_panel, weight=2)
        body.add(center, weight=4)

        properties = ttk.Frame(body, width=330)
        properties.columnconfigure(0, weight=1)
        properties.rowconfigure(2, weight=1)
        ttk.Label(properties, text="Eigenschappen", style="Heading.TLabel").grid(
            row=0, column=0, sticky="ew", padx=8, pady=(8, 5)
        )
        self.selection_header = tk.Label(
            properties,
            textvariable=self.selection_status_var,
            bg="#eef2f0",
            fg="#26342d",
            anchor="w",
            justify="left",
            padx=10,
            pady=8,
            font=("Segoe UI", 9, "bold"),
        )
        self.selection_header.grid(row=1, column=0, sticky="ew", padx=8)
        property_frame = ttk.Frame(properties)
        property_frame.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=8)
        property_frame.columnconfigure(0, weight=1)
        property_frame.rowconfigure(0, weight=1)
        self.property_grid = ttk.Treeview(
            property_frame,
            columns=("property", "value"),
            show="headings",
            selectmode="none",
        )
        self.property_grid.heading("property", text="Eigenschap")
        self.property_grid.heading("value", text="Waarde")
        self.property_grid.column("property", width=120, minwidth=80, anchor="w")
        self.property_grid.column("value", width=195, minwidth=100, anchor="w")
        self.property_grid.grid(row=0, column=0, sticky="nsew")
        property_scroll = ttk.Scrollbar(
            property_frame, orient="vertical", command=self.property_grid.yview
        )
        property_scroll.grid(row=0, column=1, sticky="ns")
        self.property_grid.configure(yscrollcommand=property_scroll.set)
        body.add(properties, weight=2)

        footer = ttk.Frame(self, padding=(8, 5))
        footer.grid(row=2, column=0, sticky="ew")
        self.model_summary_label = ttk.Label(footer, text="Geen SteelModel geladen")
        self.model_summary_label.pack(side="left")
        self.trace_label = ttk.Label(footer, text="", anchor="e")
        self.trace_label.pack(side="right", fill="x", expand=True, padx=(12, 0))

    def load_project(self, project: ProjectModel | None) -> None:
        selected_id = self.state.selected_id if self.state else ""
        self._project = project
        if project is None:
            self.state = None
            self._renderer_handshake = None
            self._renderer_command = None
            self.renderer_status_var.set("Renderer niet gekoppeld")
            self._render_empty_state()
            return
        steel_model = build_steel_model_snapshot(project)
        viewer_host = build_viewer_host_snapshot(steel_model)
        state = ViewerWorkspaceState(steel_model, viewer_host)
        if self._renderer_handshake is not None:
            report = state.register_handshake(self._renderer_handshake)
            if not report["compatible"]:
                self._renderer_command = None
        self.state = state
        if selected_id and state.entity(selected_id) is not None:
            state.select(selected_id)
        if self._renderer_command is not None and state.renderer_compatible:
            if not self._run_renderer_command(
                "scene.load",
                state.scene_payload(),
                require_attached=False,
            ):
                self._renderer_command = None
        self._refresh_all()

    def register_renderer_handshake(self, handshake: ViewerHandshake) -> dict[str, Any]:
        return self.attach_renderer(handshake, None)

    def attach_renderer(
        self,
        handshake: ViewerHandshake,
        command_handler: Callable[[str, dict[str, Any]], None] | None,
    ) -> dict[str, Any]:
        self._renderer_handshake = handshake
        self._renderer_command = command_handler
        if self.state is None:
            return {
                "compatible": False,
                "component_name": handshake.component_name,
                "component_version": handshake.component_version,
                "missing_capabilities": [],
                "errors": ["no project loaded"],
            }
        report = self.state.register_handshake(handshake)
        if not report["compatible"]:
            self._renderer_command = None
        elif self._renderer_command is not None:
            loaded = self._run_renderer_command(
                "scene.load",
                self.state.scene_payload(),
                require_attached=False,
            )
            report["scene_loaded"] = loaded
            if not loaded:
                self._renderer_command = None
        self._refresh_renderer_controls()
        self._refresh_center_status()
        return report

    def detach_renderer(self) -> None:
        self._renderer_handshake = None
        self._renderer_command = None
        if self._project is not None:
            self.load_project(self._project)
        else:
            self._render_empty_state()

    def select_entity(
        self,
        steel_model_id: str,
        *,
        notify: bool = False,
        sync_renderer: bool = True,
    ) -> bool:
        if self.state is None or self.state.entity(steel_model_id) is None:
            return False
        self.state.select(steel_model_id)
        tree_id = self._model_to_tree_id.get(steel_model_id)
        if tree_id and self.tree.exists(tree_id):
            self.tree.selection_set(tree_id)
            self.tree.focus(tree_id)
            self.tree.see(tree_id)
        self._refresh_selection()
        if sync_renderer and self.state.selected_binding is not None:
            self._run_renderer_command(
                "selection.set",
                {"viewer_node_ids": [self.state.selected_binding.viewer_node_id]},
                require_attached=False,
            )
        if notify:
            self.selection_callback(steel_model_id)
        return True

    def select_viewer_node(self, viewer_node_id: str) -> dict[str, Any]:
        if self.state is None:
            return {}
        payload = self.state.select_viewer_node(viewer_node_id)
        self.select_entity(
            str(payload["steel_model_id"]),
            notify=True,
            sync_renderer=False,
        )
        return payload

    def set_busy(self, busy: bool) -> None:
        self.select_button.configure(state="disabled" if busy else "normal")
        if busy:
            for button in (
                self.fit_button,
                self.iso_button,
                self.measure_button,
                self.section_button,
                self.compare_button,
            ):
                button.configure(state="disabled")
        else:
            self._refresh_renderer_controls()

    def _refresh_all(self) -> None:
        self._refresh_tree()
        self._refresh_renderer_controls()
        self._refresh_issues()
        self._refresh_selection()
        self._refresh_center_status()
        if self.state is None:
            return
        summary = self.state.accuracy_summary()
        self.model_summary_label.configure(
            text=(
                f"SteelModel 1.0  |  {len(self.state.steel_model.sources)} bron(n)  |  "
                f"{len(self.state.steel_model.entities)} objecten  |  "
                f"{summary.review_count} accuracy-controle(s)"
            )
        )

    def _refresh_tree(self) -> None:
        previous = self.state.selected_id if self.state else ""
        self.tree.delete(*self.tree.get_children())
        self._tree_to_model_id.clear()
        self._model_to_tree_id.clear()
        if self.state is None:
            return

        def insert(parent: str, node: ViewerTreeNode) -> None:
            tag = ACCURACY_TAGS.get(node.accuracy_status, "accuracy_na")
            tree_id = self.tree.insert(
                parent,
                "end",
                text=node.label,
                open=not parent,
                tags=(tag,) if node.steel_model_id else (),
            )
            if node.steel_model_id:
                self._tree_to_model_id[tree_id] = node.steel_model_id
                self._model_to_tree_id[node.steel_model_id] = tree_id
            for child in node.children:
                insert(tree_id, child)

        for root in self.state.tree(self.search_var.get()):
            insert("", root)
        if previous in self._model_to_tree_id:
            tree_id = self._model_to_tree_id[previous]
            self.tree.selection_set(tree_id)
            self.tree.focus(tree_id)

    def _refresh_renderer_controls(self) -> None:
        state = self.state
        compatible = bool(state and state.renderer_compatible and self._renderer_command)
        if state is None:
            self.renderer_status_var.set("Renderer niet gekoppeld")
        elif compatible:
            report = state.handshake_report
            self.renderer_status_var.set(
                f"{report['component_name']} {report['component_version']} gekoppeld"
            )
        else:
            self.renderer_status_var.set("Viewer-host gereed | rendereroverdracht vereist")
        capabilities = {
            self.select_button: "selection.sync",
            self.fit_button: "camera.standard_views",
            self.iso_button: "camera.standard_views",
            self.measure_button: "measurement.state",
            self.section_button: "section.planes",
            self.compare_button: "compare.models",
        }
        for button, capability in capabilities.items():
            button.configure(
                state=(
                    "normal"
                    if state is not None
                    and self._renderer_command is not None
                    and state.capability_available(capability)
                    else "disabled"
                )
            )

    def _refresh_issues(self) -> None:
        self.issue_grid.delete(*self.issue_grid.get_children())
        self._issue_to_model_id.clear()
        if self.state is None:
            self.issue_summary_label.configure(text="Geen project")
            return
        issues = self.state.issues(steel_model_id="")
        blocking = sum(1 for item in issues if item.blocking)
        warnings = sum(1 for item in issues if item.severity == "warning")
        self.issue_summary_label.configure(
            text=f"{blocking} blokkade(n) | {warnings} waarschuwing(en)"
        )
        for issue in issues:
            object_label = self._issue_object_label(issue)
            row_id = self.issue_grid.insert(
                "",
                "end",
                values=(
                    "Blokkeert" if issue.blocking else issue.severity.title(),
                    object_label,
                    issue.code,
                    issue.message,
                ),
                tags=(issue.severity,),
            )
            self._issue_to_model_id[row_id] = issue.steel_model_id

    def _refresh_selection(self) -> None:
        self.property_grid.delete(*self.property_grid.get_children())
        if self.state is None or self.state.selected_entity is None:
            self.selection_status_var.set("Geen object geselecteerd")
            self.trace_label.configure(text="")
            return
        payload = self.state.selection_payload()
        props = dict(payload.get("display_properties") or {})
        identifier = (
            props.get("part_position")
            or props.get("assembly_mark")
            or payload.get("name")
            or payload["steel_model_id"]
        )
        self.selection_status_var.set(
            f"{identifier}\n{payload['accuracy_label']}"
        )
        self.trace_label.configure(
            text=(
                f"{payload.get('source_format') or 'intern'} "
                f"{payload.get('source_entity_id') or '-'}  ->  "
                f"{payload['steel_model_id']}  ->  "
                f"{payload['viewer_node_id'][:8]}..."
            )
        )
        sections = (
            (
                "Identiteit",
                (
                    ("Type", payload["entity_type"]),
                    ("Naam", payload.get("name") or "-"),
                    ("Posnummer", props.get("part_position") or props.get("assembly_mark") or "-"),
                    ("Categorie", payload.get("category") or "-"),
                    ("Status", payload.get("status") or "-"),
                ),
            ),
            (
                "Product",
                (
                    ("Profiel", props.get("profile") or "-"),
                    ("Materiaal", props.get("material_grade") or props.get("material") or "-"),
                    ("Lengte", self._format_number(props.get("length_mm"), "mm")),
                    ("Massa/stuk", self._format_number(props.get("mass_each_kg"), "kg")),
                    ("Aantal", props.get("quantity_total") or props.get("quantity") or "-"),
                ),
            ),
            (
                "Herkomst",
                (
                    ("Bronbestand", payload.get("source_file_name") or "-"),
                    ("Bronobject", payload.get("source_entity_id") or "-"),
                    ("SteelModel ID", payload["steel_model_id"]),
                    ("Viewer node", payload["viewer_node_id"]),
                    ("Eenheid", self.state.steel_model.units),
                ),
            ),
            (
                "Nauwkeurigheid",
                (
                    ("Status", payload["accuracy_label"]),
                    ("Geometriesoort", payload.get("geometry_kind") or "-"),
                    ("Geometriehash", self._short_hash(payload.get("geometry_hash"))),
                    ("Meshhash", self._short_hash(payload.get("viewer_geometry_content_sha256"))),
                    ("Issues", len(payload.get("validation_issue_codes") or ())),
                ),
            ),
        )
        for heading, values in sections:
            self.property_grid.insert("", "end", values=(heading, ""), tags=("section",))
            for label, value in values:
                self.property_grid.insert("", "end", values=(label, value))
        self.property_grid.tag_configure("section", background="#e8eeea")

    def _refresh_center_status(self) -> None:
        self._draw_scene_status()

    def _draw_scene_status(self) -> None:
        canvas = self.scene_canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        center_x = width / 2
        center_y = height / 2
        canvas.create_line(0, height - 34, width, height - 34, fill="#313834")
        if self.state is None:
            title = "Open of maak een project"
            detail = "De 3D Viewer wordt rechtstreeks uit het SteelModel opgebouwd."
        elif not self.state.renderer_compatible or self._renderer_command is None:
            title = "Viewer-host gereed"
            detail = (
                "De gecontroleerde renderer is nog niet gekoppeld.\n"
                "Modelboom, properties, brontrace en validatie gebruiken al het echte SteelModel."
            )
        else:
            title = "Renderer gekoppeld"
            detail = "De renderer kan de gevalideerde scene via ViewerHost 1.0 laden."
        canvas.create_text(
            center_x,
            center_y - 18,
            text=title,
            fill="#f0f3f1",
            font=("Segoe UI", 15, "bold"),
        )
        canvas.create_text(
            center_x,
            center_y + 20,
            text=detail,
            fill="#aeb8b2",
            font=("Segoe UI", 9),
            justify="center",
            width=max(260, width - 90),
        )
        if self.state is not None and self.accuracy_mode_var.get():
            payload = self.state.selection_payload()
            debug = (
                f"SteelModel {self.state.steel_model.schema_version} | "
                f"ViewerHost {self.state.viewer_host.contract_version} | "
                f"units {self.state.steel_model.units}"
            )
            if payload:
                debug += (
                    f" | selected {payload['steel_model_id']} | "
                    f"accuracy {payload['accuracy_status']}"
                )
            canvas.create_text(
                10,
                height - 17,
                text=debug,
                fill="#d5ddd8",
                font=("Consolas", 8),
                anchor="w",
            )

    def _tree_selected(self, _event=None) -> None:
        selected = list(self.tree.selection())
        if not selected:
            return
        steel_model_id = self._tree_to_model_id.get(selected[0], "")
        if self.state is not None and self.state.selected_id == steel_model_id:
            return
        if steel_model_id:
            self.select_entity(steel_model_id, notify=True)

    def _run_renderer_command(
        self,
        command: str,
        payload: dict[str, Any] | None = None,
        *,
        require_attached: bool = True,
    ) -> bool:
        if (
            self._renderer_command is None
            or self.state is None
            or not self.state.renderer_compatible
        ):
            if require_attached:
                self.status_callback("Rendereroverdracht is nog niet gekoppeld")
            return False
        try:
            self._renderer_command(command, dict(payload or {}))
            return True
        except Exception as exc:
            self.status_callback(f"Renderercommando {command} mislukt: {exc}")
            return False

    def _issue_selected(self, _event=None) -> None:
        selected = list(self.issue_grid.selection())
        if not selected:
            return
        steel_model_id = self._issue_to_model_id.get(selected[0], "")
        if steel_model_id and self.state and self.state.entity(steel_model_id):
            self.select_entity(steel_model_id, notify=True)

    def _issue_object_label(self, issue: SteelValidationRecord) -> str:
        if not issue.steel_model_id or self.state is None:
            return "Project"
        entity = self.state.entity(issue.steel_model_id)
        if entity is not None:
            props = entity.display_properties
            return str(
                props.get("part_position")
                or props.get("assembly_mark")
                or entity.name
                or entity.steel_model_id
            )
        source = next(
            (
                item
                for item in self.state.steel_model.sources
                if item.source_id == issue.steel_model_id
            ),
            None,
        )
        return source.file_name if source else issue.steel_model_id

    def _render_empty_state(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.issue_grid.delete(*self.issue_grid.get_children())
        self.property_grid.delete(*self.property_grid.get_children())
        self._tree_to_model_id.clear()
        self._model_to_tree_id.clear()
        self._issue_to_model_id.clear()
        self.issue_summary_label.configure(text="Geen project")
        self.model_summary_label.configure(text="Geen SteelModel geladen")
        self.selection_status_var.set("Geen object geselecteerd")
        self.trace_label.configure(text="")
        self._refresh_renderer_controls()
        self._draw_scene_status()

    @staticmethod
    def _short_hash(value: Any) -> str:
        text = str(value or "")
        return f"{text[:12]}..." if text else "niet aangeleverd"

    @staticmethod
    def _format_number(value: Any, unit: str) -> str:
        try:
            return f"{float(value):,.3f} {unit}".replace(",", " ")
        except (TypeError, ValueError):
            return "-"

    def export_visual_manifest(self) -> str:
        if self.state is None:
            return "{}"
        return json.dumps(self.state.visual_manifest(), indent=2, sort_keys=True)


__all__ = ["ProjectViewerPanel"]
