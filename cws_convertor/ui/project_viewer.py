"""SteelModel-bound project viewer host for the desktop application."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import json
import queue
import threading
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
from cws_convertor.viewer.mesh_resources import (
    ViewerMeshResource,
    build_viewer_mesh_resource,
)
from cws_convertor.viewer.progressive_loader import (
    ProgressiveMeshLoadCancelled,
    ProgressiveMeshLoadPlan,
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
        self._builtin_renderer: Any | None = None
        self._mesh_provider: Callable[..., Any] | None = None
        self._mesh_generation = 0
        self._mesh_plan: ProgressiveMeshLoadPlan | None = None
        self._mesh_cancel_event = threading.Event()
        self._mesh_events: queue.Queue[tuple[int, str, Any, Exception | None]] = queue.Queue()
        self._mesh_executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="cws-viewer-mesh",
        )
        self._mesh_completion_reported_generation = -1
        self._mesh_poll_after_id: str | None = None
        self._resize_after_id: str | None = None
        self._scene_photo: Any | None = None
        self._scene_rendered = False
        self._scene_message = ""
        self._mouse_origin: tuple[int, int] | None = None
        self._mouse_previous: tuple[int, int] | None = None
        self._mouse_dragged = False
        self.search_var = tk.StringVar(value="")
        self.accuracy_mode_var = tk.BooleanVar(value=True)
        self.renderer_status_var = tk.StringVar(value="Renderer niet gekoppeld")
        self.selection_status_var = tk.StringVar(value="Geen object geselecteerd")
        self.mesh_progress_var = tk.DoubleVar(value=0.0)
        self.mesh_status_var = tk.StringVar(value="")
        self._build_ui()
        self._render_empty_state()
        self._mesh_poll_after_id = self.after(100, self._poll_mesh_events)

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
            command=self._accuracy_mode_changed,
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
        self.scene_canvas.bind("<Configure>", self._scene_configured)
        self.scene_canvas.bind("<Map>", self._scene_mapped)
        self.scene_canvas.bind("<ButtonPress-1>", self._scene_button_press)
        self.scene_canvas.bind("<B1-Motion>", self._scene_drag)
        self.scene_canvas.bind("<ButtonRelease-1>", self._scene_button_release)
        self.scene_canvas.bind("<MouseWheel>", self._scene_mouse_wheel)
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
        footer.columnconfigure(0, weight=1)
        self.model_summary_label = ttk.Label(footer, text="Geen SteelModel geladen")
        self.model_summary_label.grid(row=0, column=0, sticky="w")
        mesh_status = ttk.Frame(footer)
        mesh_status.grid(row=0, column=1, sticky="e")
        self.mesh_cancel_button = ttk.Button(
            mesh_status,
            text="Laden stoppen",
            command=lambda: self.cancel_mesh_requests(clear_plan=False),
            state="disabled",
        )
        self.mesh_cancel_button.pack(side="right")
        self.mesh_progress = ttk.Progressbar(
            mesh_status,
            mode="determinate",
            variable=self.mesh_progress_var,
            maximum=1.0,
            length=130,
        )
        self.mesh_progress.pack(side="right", padx=(8, 6))
        self.mesh_status_label = ttk.Label(mesh_status, textvariable=self.mesh_status_var)
        self.mesh_status_label.pack(side="right", padx=(12, 0))
        self.trace_label = ttk.Label(footer, text="", anchor="e")
        self.trace_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 0))

    def load_project(
        self,
        project: ProjectModel | None,
        *,
        mesh_provider: Callable[..., Any] | None = None,
    ) -> None:
        selected_id = self.state.selected_id if self.state else ""
        self.cancel_mesh_requests(clear_plan=True)
        self._mesh_provider = mesh_provider
        self._project = project
        if project is None:
            self.state = None
            self._renderer_handshake = None
            self._renderer_command = None
            self.renderer_status_var.set("Renderer niet gekoppeld")
            self._scene_rendered = False
            self._scene_photo = None
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
        if (
            self._mesh_provider is not None
            and self._renderer_command is None
            and self.scene_canvas.winfo_ismapped()
        ):
            self._ensure_builtin_renderer()
        self._refresh_all()
        self._start_progressive_mesh_loading()

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
            else:
                self._start_progressive_mesh_loading()
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

    def _ensure_builtin_renderer(self) -> None:
        if self.state is None or self._mesh_provider is None:
            return
        try:
            if self._builtin_renderer is None:
                from cws_convertor.viewer.vtk_backend import VtkOffscreenRenderer

                self._builtin_renderer = VtkOffscreenRenderer(
                    image_callback=self._renderer_image_ready,
                    selection_callback=self.select_viewer_node,
                    width=max(64, self.scene_canvas.winfo_width()),
                    height=max(64, self.scene_canvas.winfo_height()),
                )
            report = self.attach_renderer(
                self._builtin_renderer.handshake,
                self._builtin_renderer.command,
            )
            if not report.get("compatible"):
                self.status_callback(
                    "Ingebouwde mesh-renderer geweigerd: "
                    + "; ".join(report.get("errors") or ())
                )
        except Exception as exc:
            self._builtin_renderer = None
            self._renderer_handshake = None
            self._renderer_command = None
            self.status_callback(f"Ingebouwde mesh-renderer niet beschikbaar: {exc}")

    def cancel_mesh_requests(self, *, clear_plan: bool = True) -> None:
        plan = self._mesh_plan
        was_loading = bool(plan is not None and not plan.is_finished)
        self._mesh_cancel_event.set()
        if plan is not None:
            plan.cancel()
        self._mesh_generation += 1
        self._mesh_cancel_event = threading.Event()
        if clear_plan:
            self._mesh_plan = None
        elif was_loading:
            self.status_callback("Progressief laden van projectmeshes gestopt")
        self._refresh_mesh_progress()

    def _mesh_entity_ids(self) -> tuple[str, ...]:
        state = self.state
        if state is None:
            return ()
        result: list[str] = []
        for entity in state.steel_model.entities:
            binding = state.binding(entity.steel_model_id)
            if (
                entity.entity_type == "part"
                and binding is not None
                and binding.viewer_geometry_id
                and state.mesh_resource(entity.steel_model_id) is None
            ):
                result.append(entity.steel_model_id)
        return tuple(result)

    def _start_progressive_mesh_loading(self) -> None:
        if (
            self.state is None
            or self._mesh_provider is None
            or self._renderer_command is None
            or not self.scene_canvas.winfo_ismapped()
            or self._mesh_plan is not None
        ):
            return
        max_in_flight = max(
            1,
            min(2, int(getattr(self._mesh_provider, "viewer_max_concurrency", 1))),
        )
        self._mesh_plan = ProgressiveMeshLoadPlan(
            self._mesh_entity_ids(),
            max_in_flight=max_in_flight,
            patch_batch_size=4,
        )
        selected = self.state.selected_entity
        if selected is not None:
            self._mesh_plan.prioritize(selected.steel_model_id)
        self._dispatch_mesh_requests()
        self._refresh_mesh_progress()

    def _request_selected_mesh(self) -> None:
        state = self.state
        entity = state.selected_entity if state is not None else None
        binding = state.selected_binding if state is not None else None
        if (
            state is None
            or self._mesh_provider is None
            or entity is None
            or binding is None
            or entity.entity_type != "part"
            or not binding.viewer_geometry_id
            or not self.scene_canvas.winfo_ismapped()
            or self._renderer_command is None
            or state.mesh_resource(entity.steel_model_id) is not None
        ):
            return

        plan = self._mesh_plan
        if plan is None:
            self._start_progressive_mesh_loading()
            plan = self._mesh_plan
        if plan is not None and plan.cancel_requested:
            self._mesh_generation += 1
            self._mesh_cancel_event = threading.Event()
            provider_limit = max(
                1,
                min(2, int(getattr(self._mesh_provider, "viewer_max_concurrency", 1))),
            )
            plan = ProgressiveMeshLoadPlan(
                (entity.steel_model_id,),
                max_in_flight=provider_limit,
                patch_batch_size=1,
                mode="selection_only",
            )
            self._mesh_plan = plan
        if plan is not None:
            plan.prioritize(entity.steel_model_id)
            self._dispatch_mesh_requests()
            self._refresh_mesh_progress()

    def _dispatch_mesh_requests(self) -> None:
        state = self.state
        provider = self._mesh_provider
        plan = self._mesh_plan
        if state is None or provider is None or plan is None or plan.cancel_requested:
            return
        generation = self._mesh_generation
        cancel_event = self._mesh_cancel_event
        project_id = state.steel_model.project_id
        accepts_cancel = bool(getattr(provider, "viewer_accepts_cancel", False))
        for steel_model_id in plan.claim():
            entity = state.entity(steel_model_id)
            binding = state.binding(steel_model_id)
            if entity is None or binding is None:
                plan.mark_failed(steel_model_id, "SteelModel-binding ontbreekt")
                continue

            def load(
                entity_id: str = steel_model_id,
                source_entity=entity,
                source_binding=binding,
            ) -> None:
                def cancel_check() -> None:
                    if cancel_event.is_set():
                        raise ProgressiveMeshLoadCancelled(
                            f"Mesh laden geannuleerd voor {entity_id}"
                        )

                try:
                    cancel_check()
                    supplied = (
                        provider(entity_id, cancel_check=cancel_check)
                        if accepts_cancel
                        else provider(entity_id)
                    )
                    cancel_check()
                    resource = (
                        supplied
                        if isinstance(supplied, ViewerMeshResource)
                        else build_viewer_mesh_resource(
                            supplied,
                            project_id=project_id,
                            entity=source_entity,
                            binding=source_binding,
                        )
                    )
                    cancel_check()
                    self._mesh_events.put((generation, entity_id, resource, None))
                except Exception as exc:
                    self._mesh_events.put((generation, entity_id, None, exc))

            self._mesh_executor.submit(load)

    def _poll_mesh_events(self) -> None:
        resources: list[tuple[str, ViewerMeshResource]] = []
        failures: list[tuple[str, Exception]] = []
        try:
            while True:
                generation, steel_model_id, resource, error = self._mesh_events.get_nowait()
                if generation != self._mesh_generation:
                    continue
                plan = self._mesh_plan
                if (
                    plan is None
                    or self.state is None
                    or self.state.entity(steel_model_id) is None
                ):
                    continue
                if error is not None:
                    if plan.mark_failed(steel_model_id, error):
                        failures.append((steel_model_id, error))
                    continue
                resources.append((steel_model_id, resource))
        except queue.Empty:
            pass

        state = self.state
        plan = self._mesh_plan
        if resources and state is not None and plan is not None:
            first_resource = not bool(state.visual_manifest()["mesh_resource_count"])
            attached_any = False
            for start in range(0, len(resources), plan.patch_batch_size):
                batch = resources[start : start + plan.patch_batch_size]
                entity_ids = [item[0] for item in batch]
                batch_resources = [item[1] for item in batch]
                accepted: list[tuple[list[str], dict[str, Any]]] = []
                try:
                    if self._renderer_command is None:
                        raise RuntimeError("renderer is niet gekoppeld")
                    patch = state.attach_mesh_resources(batch_resources)
                    accepted.append((entity_ids, patch))
                except Exception as batch_error:
                    if len(batch) == 1 or self._renderer_command is None:
                        for entity_id in entity_ids:
                            if plan.mark_failed(entity_id, batch_error):
                                failures.append((entity_id, batch_error))
                    else:
                        # Preserve valid neighbours when one resource poisons an
                        # otherwise atomic batch.
                        for entity_id, resource in batch:
                            try:
                                patch = state.attach_mesh_resources((resource,))
                                accepted.append(([entity_id], patch))
                            except Exception as item_error:
                                if plan.mark_failed(entity_id, item_error):
                                    failures.append((entity_id, item_error))
                for accepted_ids, patch in accepted:
                    for entity_id in accepted_ids:
                        plan.mark_loaded(entity_id)
                    attached_any = True
                    try:
                        self._renderer_command("scene.patch", patch)
                    except Exception:
                        try:
                            self._renderer_command("scene.load", state.scene_payload())
                        except Exception as exc:
                            self._scene_message = f"Meshpatch geweigerd: {exc}"
                            self.status_callback(f"Viewer-meshpatch geweigerd: {exc}")
            if attached_any:
                try:
                    assert self._renderer_command is not None
                    if first_resource:
                        self._renderer_command(
                            "camera.standard_view", {"view": "isometric"}
                        )
                    if state.selected_binding is not None:
                        self._renderer_command(
                            "selection.set",
                            {"viewer_node_ids": [state.selected_binding.viewer_node_id]},
                        )
                    self._refresh_selection()
                except Exception as exc:
                    self.status_callback(f"Viewerselectie na meshpatch mislukt: {exc}")

        for steel_model_id, error in failures:
            self.status_callback(
                f"Viewer-mesh voor {steel_model_id} niet geladen: {error}"
            )
        self._dispatch_mesh_requests()
        self._refresh_mesh_progress()
        try:
            self._mesh_poll_after_id = self.after(100, self._poll_mesh_events)
        except tk.TclError:
            self._mesh_poll_after_id = None

    def _refresh_mesh_progress(self) -> None:
        plan = self._mesh_plan
        if plan is None:
            self.mesh_progress_var.set(0.0)
            self.mesh_status_var.set("")
            self.mesh_cancel_button.configure(state="disabled")
            return
        progress = plan.manifest(include_runtime=True)
        total = int(progress["total"])
        loaded = int(progress["loaded"])
        failed = int(progress["failed"])
        pending = int(progress["pending"])
        cancelled = int(progress["cancelled"])
        self.mesh_progress_var.set(float(progress["progress_ratio"]))
        suffix = f" | {failed} fout(en)" if failed else ""
        if progress["status"] == "cancelled":
            label = f"Gestopt | {loaded}/{total}"
        elif progress["mode"] == "selection_only":
            label = f"Selectie | {loaded}/{total}{suffix}"
        else:
            label = f"Mesh | {loaded}/{total}{suffix}"
        self.mesh_status_var.set(label)
        self._scene_message = (
            f"Projectmesh: {loaded}/{total} geladen | "
            f"{pending} bezig | {failed} niet beschikbaar"
        )
        loading = progress["status"] in {"queued", "loading"}
        self.mesh_cancel_button.configure(state="normal" if loading else "disabled")
        if (
            not loading
            and not cancelled
            and total
            and self._mesh_completion_reported_generation != self._mesh_generation
        ):
            self._mesh_completion_reported_generation = self._mesh_generation
            self.status_callback(
                f"Projectmeshes geladen: {loaded}/{total}; niet beschikbaar: {failed}"
            )
        self._draw_scene_status()

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
        self._request_selected_mesh()
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
                f"{report['component_name']} {report['component_version']} "
                + ("gekoppeld" if report.get("complete") else "mesh-kern gekoppeld")
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

    def _accuracy_mode_changed(self) -> None:
        if self.state is not None and self.state.capability_available("accuracy_debug"):
            self._run_renderer_command(
                "accuracy_debug.set",
                {"enabled": bool(self.accuracy_mode_var.get())},
                require_attached=False,
            )
        self._draw_scene_status()

    def _renderer_image_ready(
        self,
        png: bytes,
        _telemetry: Mapping[str, Any],
    ) -> None:
        from PIL import Image, ImageTk

        image = Image.open(BytesIO(png)).convert("RGB")
        self._scene_photo = ImageTk.PhotoImage(image, master=self.scene_canvas)
        self.scene_canvas.delete("scene-image")
        image_id = self.scene_canvas.create_image(
            0,
            0,
            image=self._scene_photo,
            anchor="nw",
            tags=("scene-image",),
        )
        self.scene_canvas.tag_lower(image_id)
        self._scene_rendered = True
        self._draw_scene_status()

    def _scene_configured(self, _event=None) -> None:
        if self._resize_after_id is not None:
            try:
                self.after_cancel(self._resize_after_id)
            except tk.TclError:
                pass
        self._resize_after_id = self.after(80, self._resize_builtin_renderer)

    def _scene_mapped(self, _event=None) -> None:
        if self._mesh_provider is not None and self._renderer_command is None:
            self._ensure_builtin_renderer()
        self._start_progressive_mesh_loading()
        self._request_selected_mesh()

    def _resize_builtin_renderer(self) -> None:
        self._resize_after_id = None
        renderer = self._active_builtin_renderer()
        if renderer is None:
            self._draw_scene_status()
            return
        width = self.scene_canvas.winfo_width()
        height = self.scene_canvas.winfo_height()
        if width >= 64 and height >= 64:
            renderer.resize(width, height)

    def _active_builtin_renderer(self) -> Any | None:
        handler_owner = getattr(self._renderer_command, "__self__", None)
        return self._builtin_renderer if handler_owner is self._builtin_renderer else None

    def _scene_button_press(self, event: tk.Event) -> None:
        if self._active_builtin_renderer() is None:
            return
        self._mouse_origin = (int(event.x), int(event.y))
        self._mouse_previous = self._mouse_origin
        self._mouse_dragged = False

    def _scene_drag(self, event: tk.Event) -> None:
        renderer = self._active_builtin_renderer()
        if renderer is None or self._mouse_previous is None:
            return
        current = (int(event.x), int(event.y))
        delta_x = current[0] - self._mouse_previous[0]
        delta_y = current[1] - self._mouse_previous[1]
        if abs(delta_x) + abs(delta_y) >= 2:
            self._mouse_dragged = True
            renderer.orbit(delta_x, -delta_y)
        self._mouse_previous = current

    def _scene_button_release(self, event: tk.Event) -> None:
        renderer = self._active_builtin_renderer()
        if renderer is not None and self._mouse_origin is not None and not self._mouse_dragged:
            renderer.pick(int(event.x), int(event.y))
        self._mouse_origin = None
        self._mouse_previous = None
        self._mouse_dragged = False

    def _scene_mouse_wheel(self, event: tk.Event) -> None:
        renderer = self._active_builtin_renderer()
        if renderer is None:
            return
        renderer.zoom(1.15 if int(event.delta) > 0 else 1.0 / 1.15)

    def _draw_scene_status(self) -> None:
        canvas = self.scene_canvas
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        center_x = width / 2
        center_y = height / 2
        canvas.delete("scene-overlay")
        if not self._scene_rendered:
            canvas.delete("all")
        if self.state is None:
            title = "Open of maak een project"
            detail = "Geen scene geladen"
        elif not self.state.renderer_compatible or self._renderer_command is None:
            title = "Viewer-host gereed"
            detail = "Gecontroleerde renderer niet gekoppeld"
        else:
            title = ""
            detail = self._scene_message or "Geen mesh geladen"
        if not self._scene_rendered:
            canvas.create_text(
                center_x,
                center_y - 18,
                text=title,
                fill="#f0f3f1",
                font=("Segoe UI", 15, "bold"),
                tags=("scene-overlay",),
            )
            canvas.create_text(
                center_x,
                center_y + 20,
                text=detail,
                fill="#aeb8b2",
                font=("Segoe UI", 9),
                justify="center",
                width=max(260, width - 90),
                tags=("scene-overlay",),
            )
        else:
            canvas.create_rectangle(
                0,
                0,
                width,
                28,
                fill="#111714",
                outline="",
                stipple="gray50",
                tags=("scene-overlay",),
            )
            canvas.create_text(
                10,
                14,
                text=detail,
                fill="#e2e8e4",
                font=("Segoe UI", 8),
                anchor="w",
                tags=("scene-overlay",),
            )
        canvas.create_line(
            0,
            height - 34,
            width,
            height - 34,
            fill="#313834",
            tags=("scene-overlay",),
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
                tags=("scene-overlay",),
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
        self.mesh_progress_var.set(0.0)
        self.mesh_status_var.set("")
        self.mesh_cancel_button.configure(state="disabled")
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
        value = self.state.visual_manifest()
        if self._mesh_plan is not None:
            value["progressive_mesh_load"] = self._mesh_plan.manifest(
                include_runtime=True
            )
        if self._builtin_renderer is not None:
            value["builtin_renderer_telemetry"] = self._builtin_renderer.telemetry()
        return json.dumps(value, indent=2, sort_keys=True)

    def destroy(self) -> None:
        self.cancel_mesh_requests()
        for after_id in (self._mesh_poll_after_id, self._resize_after_id):
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except tk.TclError:
                    pass
        self._mesh_poll_after_id = None
        self._resize_after_id = None
        self._mesh_executor.shutdown(wait=False, cancel_futures=True)
        if self._builtin_renderer is not None:
            try:
                self._builtin_renderer.close()
            except Exception:
                pass
            self._builtin_renderer = None
        super().destroy()


__all__ = ["ProjectViewerPanel"]
