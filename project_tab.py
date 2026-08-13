"""Functioneel Project / Productie-tabblad voor CWS Convertor v0.7.

Dit scherm is geen losse mock-up: het maakt/opent echte ``.cwscproj``-bestanden,
voert de deterministische IFC/STEP-nulmeting én expliciete semantische import uit,
sluit bronbestanden optioneel in en toont dezelfde data die via de CLI beschikbaar
is. Productie-export blijft geblokkeerd tot featurevalidatie is afgerond.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import json
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable

from cws_convertor.product import APP_NAME, PROJECT_FILE_EXTENSION
from cws_convertor.project import (
    BaselineAnalysis,
    JobCancelled,
    ProjectPackageError,
    ProjectService,
    ProjectSession,
    ProjectStore,
    write_baseline_report,
)
from cws_convertor.ui.part_workbench import PartWorkbenchPanel


class CWSProjectTab(ttk.Frame):
    AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000

    def __init__(
        self,
        master,
        *,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, padding=0)
        self.log_callback = log_callback or (lambda _message: None)
        self.store = ProjectStore()
        self.service = ProjectService(store=self.store)
        self.session: ProjectSession | None = None
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._busy = False
        self._busy_cancellable = False
        self._cancel_event = threading.Event()
        self._source_rows: dict[str, dict[str, Any]] = {}
        self._part_rows: dict[str, dict[str, Any]] = {}
        self._last_bom_snapshot: Any | None = None
        self.part_search = tk.StringVar(value="")
        self.part_category_filter = tk.StringVar(value="alle")
        self.embed_sources = tk.BooleanVar(value=True)
        self._build_ui()
        self.after(120, self._poll_events)
        self.after(self.AUTOSAVE_INTERVAL_MS, self._autosave_tick)
        self.refresh()

    # ------------------------------------------------------------------ style/UI
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = tk.Frame(self, bg="#122033", height=78)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(0, weight=1)
        title = tk.Label(
            header,
            text="Project / Productie",
            bg="#122033",
            fg="#f7fafc",
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="w", padx=22, pady=(13, 0))
        subtitle = tk.Label(
            header,
            text="Semantische IFC/STEP-structuur, onderdelen, bouten en lassen — met harde productiegate",
            bg="#122033",
            fg="#b8c7d9",
            font=("Segoe UI", 9),
            anchor="w",
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=22, pady=(0, 12))
        self.project_badge = tk.Label(
            header,
            text="GEEN PROJECT",
            bg="#334155",
            fg="#f8fafc",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
        )
        self.project_badge.grid(row=0, column=1, rowspan=2, padx=22)

        toolbar = ttk.Frame(self, padding=(16, 10))
        toolbar.grid(row=1, column=0, sticky="ew")
        self.new_button = ttk.Button(toolbar, text="＋ Nieuw project", command=self.new_project)
        self.new_button.pack(side="left")
        self.open_button = ttk.Button(toolbar, text="Openen", command=self.open_project)
        self.open_button.pack(side="left", padx=(6, 0))
        self.save_button = ttk.Button(toolbar, text="Opslaan", command=self.save_project)
        self.save_button.pack(side="left", padx=(6, 0))
        self.add_button = ttk.Button(
            toolbar,
            text="IFC / STEP toevoegen",
            command=self.add_model_files,
            style="CWS.Primary.TButton",
        )
        self.add_button.pack(side="left", padx=(18, 0))
        self.semantic_button = ttk.Button(
            toolbar,
            text="Semantisch importeren",
            command=self.semantic_import_selected,
            style="CWS.Primary.TButton",
        )
        self.semantic_button.pack(side="left", padx=(6, 0))
        self.classify_button = ttk.Button(
            toolbar, text="Classificeren", command=self.classify_parts,
            style="CWS.Primary.TButton",
        )
        self.classify_button.pack(side="left", padx=(6, 0))
        self.bom_button = ttk.Button(
            toolbar, text="BOM / Excel", command=self.build_and_export_bom,
            style="CWS.Primary.TButton",
        )
        self.bom_button.pack(side="left", padx=(6, 0))
        self.production_button = ttk.Button(
            toolbar,
            text="Productiepakket",
            command=self.export_production_package,
            style="CWS.Primary.TButton",
        )
        self.production_button.pack(side="left", padx=(6, 0))
        self.cancel_button = ttk.Button(
            toolbar,
            text="Annuleren",
            command=self.cancel_current_operation,
            state="disabled",
        )
        self.cancel_button.pack(side="left", padx=(6, 0))
        self.report_button = ttk.Button(toolbar, text="Nulmeting exporteren", command=self.export_baseline_report)
        self.report_button.pack(side="left", padx=(6, 0))
        self.extract_button = ttk.Button(toolbar, text="Bron uitpakken", command=self.extract_selected_source)
        self.extract_button.pack(side="left", padx=(6, 0))
        ttk.Checkbutton(
            toolbar,
            text="Bronnen insluiten",
            variable=self.embed_sources,
        ).pack(side="left", padx=(14, 0))
        self.project_path_label = ttk.Label(toolbar, text="", anchor="e")
        self.project_path_label.pack(side="right", fill="x", expand=True, padx=(18, 0))

        cards = ttk.Frame(self, padding=(16, 0, 16, 10))
        cards.grid(row=2, column=0, sticky="ew")
        for index in range(5):
            cards.columnconfigure(index, weight=1, uniform="cards")
        self.card_values: dict[str, tk.Label] = {}
        for index, (key, heading) in enumerate(
            (
                ("sources", "BRONBESTANDEN"),
                ("assemblies", "ASSEMBLIES"),
                ("parts", "ONDERDELEN"),
                ("warnings", "CONTROLEPUNTEN"),
                ("storage", "PROJECTOPSLAG"),
            )
        ):
            card = tk.Frame(cards, bg="#f8fafc", highlightbackground="#d8e1ea", highlightthickness=1)
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 5, 0))
            tk.Label(
                card,
                text=heading,
                bg="#f8fafc",
                fg="#64748b",
                font=("Segoe UI", 8, "bold"),
                anchor="w",
            ).pack(fill="x", padx=13, pady=(10, 1))
            value = tk.Label(
                card,
                text="—",
                bg="#f8fafc",
                fg="#122033",
                font=("Segoe UI", 15, "bold"),
                anchor="w",
                justify="left",
            )
            value.pack(fill="x", padx=13, pady=(0, 11))
            self.card_values[key] = value

        self.workspace = ttk.Notebook(self)
        self.workspace.grid(row=3, column=0, sticky="nsew", padx=16, pady=(0, 10))
        model_page = ttk.Frame(self.workspace)
        bom_page = ttk.Frame(self.workspace)
        workbench_page = ttk.Frame(self.workspace)
        self.workspace.add(model_page, text="  Model & bronnen  ")
        self.workspace.add(bom_page, text="  Classificatie & BOM  ")
        self.workspace.add(workbench_page, text="  Part Workbench  ")

        body = ttk.Panedwindow(model_page, orient="horizontal")
        body.pack(fill="both", expand=True)

        tree_box = ttk.LabelFrame(body, text="Projectstructuur", padding=6)
        tree_box.columnconfigure(0, weight=1)
        tree_box.rowconfigure(0, weight=1)
        self.project_tree = ttk.Treeview(tree_box, show="tree", selectmode="browse")
        self.project_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(tree_box, orient="vertical", command=self.project_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.project_tree.configure(yscrollcommand=tree_scroll.set)
        body.add(tree_box, weight=1)

        list_box = ttk.LabelFrame(body, text="Bronnen en importstrategie", padding=6)
        list_box.columnconfigure(0, weight=1)
        list_box.rowconfigure(0, weight=1)
        columns = ("format", "schema", "strategy", "products", "solids", "status")
        self.source_grid = ttk.Treeview(list_box, columns=columns, show="headings", selectmode="browse")
        labels = {
            "format": "Formaat",
            "schema": "Schema",
            "strategy": "Route",
            "products": "Objecten",
            "solids": "Solids",
            "status": "Status",
        }
        widths = {"format": 75, "schema": 205, "strategy": 175, "products": 78, "solids": 62, "status": 110}
        for column in columns:
            self.source_grid.heading(column, text=labels[column], command=lambda c=column: self._sort_sources(c, False))
            self.source_grid.column(column, width=widths[column], minwidth=55, anchor="w")
        self.source_grid.grid(row=0, column=0, sticky="nsew")
        grid_scroll = ttk.Scrollbar(list_box, orient="vertical", command=self.source_grid.yview)
        grid_scroll.grid(row=0, column=1, sticky="ns")
        self.source_grid.configure(yscrollcommand=grid_scroll.set)
        self.source_grid.bind("<<TreeviewSelect>>", self._source_selected)
        body.add(list_box, weight=3)

        detail_box = ttk.LabelFrame(body, text="Details / validatie", padding=6)
        detail_box.columnconfigure(0, weight=1)
        detail_box.rowconfigure(0, weight=1)
        self.details = tk.Text(
            detail_box,
            wrap="word",
            borderwidth=0,
            background="#fbfdff",
            foreground="#1e293b",
            font=("Segoe UI", 9),
            padx=10,
            pady=8,
            state="disabled",
        )
        self.details.grid(row=0, column=0, sticky="nsew")
        detail_scroll = ttk.Scrollbar(detail_box, orient="vertical", command=self.details.yview)
        detail_scroll.grid(row=0, column=1, sticky="ns")
        self.details.configure(yscrollcommand=detail_scroll.set)
        body.add(detail_box, weight=2)

        bom_page.columnconfigure(0, weight=1)
        bom_page.rowconfigure(2, weight=1)
        bom_header = tk.Frame(bom_page, bg="#eef4fa", height=58)
        bom_header.grid(row=0, column=0, sticky="ew")
        bom_header.grid_propagate(False)
        bom_header.columnconfigure(3, weight=1)
        tk.Label(
            bom_header, text="Zoeken", bg="#eef4fa", fg="#334155",
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, padx=(12, 6), pady=14)
        search_entry = ttk.Entry(bom_header, textvariable=self.part_search, width=30)
        search_entry.grid(row=0, column=1, sticky="w", pady=12)
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_classification_grid())
        ttk.Label(bom_header, text="Categorie").grid(row=0, column=2, padx=(16, 6))
        category_combo = ttk.Combobox(
            bom_header, textvariable=self.part_category_filter, state="readonly", width=18,
            values=("alle", "make_part", "purchased_item", "non_steel", "unknown", "reference"),
        )
        category_combo.grid(row=0, column=3, sticky="w")
        category_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_classification_grid())
        ttk.Button(
            bom_header, text="Selectie bevestigen",
            command=self.confirm_selected_classification,
        ).grid(row=0, column=4, padx=(8, 6), pady=10)
        ttk.Button(
            bom_header, text="BOM opnieuw bouwen", command=self.build_and_export_bom,
            style="CWS.Primary.TButton",
        ).grid(row=0, column=5, padx=(0, 12), pady=10)

        self.bom_kpi_label = tk.Label(
            bom_page,
            text="Nog niet geclassificeerd — productie-uitvoer blijft geblokkeerd",
            bg="#fff7e6", fg="#8a4b08", font=("Segoe UI", 10, "bold"),
            anchor="w", padx=12, pady=8,
        )
        self.bom_kpi_label.grid(row=1, column=0, sticky="ew")

        bom_body = ttk.Panedwindow(bom_page, orient="horizontal")
        bom_body.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        grid_frame = ttk.Frame(bom_body)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        part_columns = (
            "status", "category", "position", "assembly", "profile", "material",
            "length", "quantity", "mass", "confidence", "nc1", "warnings",
        )
        self.part_grid = ttk.Treeview(
            grid_frame, columns=part_columns, show="headings", selectmode="browse"
        )
        part_labels = {
            "status": "Status", "category": "Maak / inkoop", "position": "Pos.",
            "assembly": "Merk", "profile": "Profiel", "material": "Materiaal",
            "length": "Lengte", "quantity": "Aantal", "mass": "Massa",
            "confidence": "Confidence", "nc1": "NC1", "warnings": "Waarschuwingen",
        }
        widths = {
            "status": 105, "category": 115, "position": 75, "assembly": 75,
            "profile": 135, "material": 95, "length": 85, "quantity": 58,
            "mass": 75, "confidence": 84, "nc1": 60, "warnings": 220,
        }
        for column in part_columns:
            self.part_grid.heading(column, text=part_labels[column])
            self.part_grid.column(column, width=widths[column], minwidth=50, anchor="w")
        self.part_grid.grid(row=0, column=0, sticky="nsew")
        part_scroll_y = ttk.Scrollbar(grid_frame, orient="vertical", command=self.part_grid.yview)
        part_scroll_y.grid(row=0, column=1, sticky="ns")
        part_scroll_x = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.part_grid.xview)
        part_scroll_x.grid(row=1, column=0, sticky="ew")
        self.part_grid.configure(yscrollcommand=part_scroll_y.set, xscrollcommand=part_scroll_x.set)
        self.part_grid.bind("<<TreeviewSelect>>", self._part_selected)
        self.part_grid.tag_configure("ok", background="#edf8f2")
        self.part_grid.tag_configure("review", background="#fff8e8")
        self.part_grid.tag_configure("blocked", background="#fdecec")
        bom_body.add(grid_frame, weight=4)

        bom_detail_frame = ttk.LabelFrame(bom_body, text="Onderdeel / herkomst", padding=6)
        bom_detail_frame.columnconfigure(0, weight=1)
        bom_detail_frame.rowconfigure(0, weight=1)
        self.part_details = tk.Text(
            bom_detail_frame, wrap="word", borderwidth=0, background="#fbfdff",
            foreground="#1e293b", font=("Segoe UI", 9), padx=10, pady=8, state="disabled",
        )
        self.part_details.grid(row=0, column=0, sticky="nsew")
        bom_detail_scroll = ttk.Scrollbar(bom_detail_frame, orient="vertical", command=self.part_details.yview)
        bom_detail_scroll.grid(row=0, column=1, sticky="ns")
        self.part_details.configure(yscrollcommand=bom_detail_scroll.set)
        bom_body.add(bom_detail_frame, weight=2)

        workbench_page.columnconfigure(0, weight=1)
        workbench_page.rowconfigure(0, weight=1)
        self.part_workbench = PartWorkbenchPanel(
            workbench_page,
            session_provider=lambda: self.session,
            changed_callback=self._workbench_changed,
            selection_callback=self._select_part_from_workbench,
            status_callback=self._workbench_status,
        )
        self.part_workbench.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(self, padding=(16, 0, 16, 10))
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(1, weight=1)
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=180)
        self.progress.grid(row=0, column=0, sticky="w")
        self.status_label = ttk.Label(footer, text="Gereed", anchor="w")
        self.status_label.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.phase_label = ttk.Label(
            footer,
            text="Fase 4: Part Workbench",
            foreground="#64748b",
        )
        self.phase_label.grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------------ project actions
    def _replace_session(self, session: ProjectSession | None) -> None:
        if self.session is not None and self.session is not session:
            self.session.close()
        self.session = session

    def new_project(self) -> None:
        if not self._confirm_discard_dirty():
            return
        name = simpledialog.askstring("Nieuw CWS-project", "Projectnaam:", parent=self)
        if not name:
            return
        customer = simpledialog.askstring(
            "Nieuw CWS-project", "Klant/opdrachtgever (optioneel):", parent=self
        ) or ""
        order = simpledialog.askstring(
            "Nieuw CWS-project", "Order-/werknummer (optioneel):", parent=self
        ) or ""
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Nieuw CWS-project opslaan",
            defaultextension=PROJECT_FILE_EXTENSION,
            filetypes=[(f"{APP_NAME}-project", f"*{PROJECT_FILE_EXTENSION}")],
            initialfile=f"{name}{PROJECT_FILE_EXTENSION}",
        )
        if not path:
            return
        try:
            package = self.service.create_project(
                path,
                project_name=name,
                customer=customer,
                order_number=order,
                created_by="gui",
            )
            self._replace_session(ProjectSession.open(package.path, store=self.store))
            self.embed_sources.set(True)
            self.log_callback(f"Nieuw CWS-project gemaakt: {package.path}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Project maken", str(exc), parent=self)

    def open_project(self, path: str | Path | None = None) -> None:
        if not self._confirm_discard_dirty():
            return
        selected = str(path) if path else filedialog.askopenfilename(
            parent=self,
            title="CWS-project openen",
            filetypes=[
                (f"{APP_NAME}-project", f"*{PROJECT_FILE_EXTENSION}"),
                ("Alle bestanden", "*.*"),
            ],
        )
        if not selected:
            return
        try:
            candidate = self.store.find_autosave(selected)
            if candidate:
                if messagebox.askyesno(
                    "Autosave gevonden",
                    "Er is een nieuwere autosave. Wilt u die herstellen voordat het project wordt geopend?",
                    parent=self,
                ):
                    self.service.recover_autosave(selected)
            session = ProjectSession.open(selected, store=self.store)
            self._replace_session(session)
            embedded = bool(session.package and session.package.embedded_source_names())
            self.embed_sources.set(embedded or not session.project.sources)
            self.log_callback(f"CWS-project geopend: {session.path}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Project openen", str(exc), parent=self)

    def save_project(self) -> None:
        if self.session is None:
            messagebox.showinfo("Project", "Maak of open eerst een project.", parent=self)
            return
        try:
            target = self.session.save(
                embed_sources=self.embed_sources.get(),
                user="gui",
                revision_message="Handmatig opgeslagen",
            )
            self.status_label.configure(text=f"Opgeslagen: {target.name}")
            self.log_callback(f"CWS-project opgeslagen: {target}")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)

    def add_model_files(self) -> None:
        if self.session is None:
            messagebox.showinfo("Project", "Maak of open eerst een project.", parent=self)
            return
        paths = filedialog.askopenfilenames(
            parent=self,
            title="IFC- of STEP-model toevoegen",
            filetypes=[
                ("IFC / STEP", "*.ifc *.step *.stp"),
                ("IFC", "*.ifc"),
                ("STEP", "*.step *.stp"),
            ],
        )
        if not paths:
            return
        self._start_import([Path(item) for item in paths])

    def _start_import(self, paths: list[Path]) -> None:
        if self.session is None or self._busy or self.session.path is None:
            return
        try:
            if self.session.dirty:
                self.session.save(
                    embed_sources=self.embed_sources.get(),
                    user="gui",
                    revision_message="Voor bronimport",
                )
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)
            return
        self._set_busy(True, f"{len(paths)} model(len) analyseren…")
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)
                results = working.register_sources(
                    paths,
                    include_step_geometry=False,
                    user="gui",
                )
                working.save(
                    embed_sources=embed_sources,
                    user="gui",
                    revision_message=f"{len(results)} bronbestand(en) geïnventariseerd",
                )
                self.events.put(("import_ok", (working, results)))
                working = None  # ownership moves to the UI thread
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("Model toevoegen", str(exc))))

        threading.Thread(target=worker, daemon=True, name="cws-project-import").start()

    def semantic_import_selected(self) -> None:
        if self.session is None or not self.session.project.sources:
            messagebox.showinfo(
                "Semantische import",
                "Voeg eerst één of meer IFC/STEP-bronnen toe.",
                parent=self,
            )
            return
        selected = list(self.source_grid.selection())
        source_ids = selected or list(self.session.project.sources)
        labels = [self.session.project.sources[item].file_name for item in source_ids]
        question = (
            f"Semantische import uitvoeren voor {len(source_ids)} bronbestand(en)?\n\n"
            + "\n".join(f"• {item}" for item in labels[:6])
            + ("\n• …" if len(labels) > 6 else "")
            + "\n\nAssemblies, onderdelen, bouten, lassen, properties en placements "
            "worden gematerialiseerd. Productie-uitvoer blijft geblokkeerd totdat "
            "exacte productiefeatures zijn gevalideerd."
        )
        if not messagebox.askyesno("Semantische IFC/STEP-import", question, parent=self):
            return
        self._start_semantic_import(source_ids)

    def _start_semantic_import(self, source_ids: list[str]) -> None:
        if self.session is None or self._busy or self.session.path is None:
            return
        try:
            if self.session.dirty:
                self.session.save(
                    embed_sources=self.embed_sources.get(),
                    user="gui",
                    revision_message="Voor semantische import",
                )
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)
            return
        self._cancel_event.clear()
        self._set_busy(
            True,
            f"{len(source_ids)} bronbestand(en) semantisch importeren…",
            cancellable=True,
        )
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)

                def progress(done: float, total: int, message: str) -> None:
                    self.events.put(("semantic_progress", (done, total, message)))

                def cancel_check() -> None:
                    if self._cancel_event.is_set():
                        raise JobCancelled(
                            "Semantische import geannuleerd; het project is niet gewijzigd."
                        )

                results = working.semantic_import_sources(
                    source_ids,
                    user="gui",
                    progress_callback=progress,
                    cancel_check=cancel_check,
                )
                working.save(
                    embed_sources=embed_sources,
                    user="gui",
                    revision_message=f"{len(results)} bronbestand(en) semantisch geïmporteerd",
                )
                self.events.put(("semantic_ok", (working, results)))
                working = None
            except JobCancelled as exc:
                if working is not None:
                    working.close()
                self.events.put(("semantic_cancelled", str(exc)))
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("Semantische import", str(exc))))

        threading.Thread(
            target=worker,
            daemon=True,
            name="cws-project-semantic-import",
        ).start()

    def classify_parts(self) -> None:
        if self.session is None or not self.session.project.parts:
            messagebox.showinfo(
                "Classificatie",
                "Voer eerst de semantische IFC/STEP-import uit.",
                parent=self,
            )
            return
        if self._busy or self.session.path is None:
            return
        if not messagebox.askyesno(
            "Onderdelen classificeren",
            f"{APP_NAME} classificeert ieder object deterministisch als maakdeel, "
            "inkoopdeel, niet-staal, referentie of onbekend. Onzekere objecten blijven "
            "geblokkeerd. Doorgaan?",
            parent=self,
        ):
            return
        try:
            if self.session.dirty:
                self.session.save(
                    embed_sources=self.embed_sources.get(), user="gui",
                    revision_message="Voor classificatie",
                )
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)
            return
        self._set_busy(True, "Onderdelen classificeren en identiteit controleren…")
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)
                report = working.classify_parts(user="gui")
                working.save(
                    embed_sources=embed_sources, user="gui",
                    revision_message="Deterministische classificatie en productie-identiteit",
                )
                self.events.put(("classification_ok", (working, report)))
                working = None
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("Classificatie", str(exc))))

        threading.Thread(target=worker, daemon=True, name="cws-project-classification").start()

    def build_and_export_bom(self) -> None:
        if self.session is None or not self.session.project.parts:
            messagebox.showinfo("BOM", "Voer eerst semantische import en classificatie uit.", parent=self)
            return
        if self._busy or self.session.path is None:
            return
        output_dir = filedialog.askdirectory(parent=self, title="Map voor BOM-, Excel- en inkooppakket")
        if not output_dir:
            return
        try:
            if self.session.dirty:
                self.session.save(
                    embed_sources=self.embed_sources.get(), user="gui",
                    revision_message="Voor BOM-export",
                )
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)
            return
        self._set_busy(True, "BOM, inkooplijst, materiaalstaat en herkomstpakket bouwen…")
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)
                snapshot, outputs = working.export_bom(
                    output_dir, user="gui", package_name=None
                )
                working.save(
                    embed_sources=embed_sources, user="gui",
                    revision_message="BOM, inkoop en herkomstsnapshot bijgewerkt",
                )
                self.events.put(("bom_ok", (working, snapshot, outputs)))
                working = None
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("BOM / Excel", str(exc))))

        threading.Thread(target=worker, daemon=True, name="cws-project-bom").start()

    def export_production_package(self) -> None:
        if self.session is None or not self.session.project.parts:
            messagebox.showinfo(
                "Productiepakket",
                "Open eerst een project met vrijgegeven maakdelen.",
                parent=self,
            )
            return
        if self._busy or self.session.path is None:
            return
        output_dir = filedialog.askdirectory(
            parent=self,
            title="Map voor vrijgegeven productiepakketten",
        )
        if not output_dir:
            return
        try:
            if self.session.dirty:
                self.session.save(
                    embed_sources=self.embed_sources.get(),
                    user="gui",
                    revision_message="Voor productie-export",
                )
        except Exception as exc:
            messagebox.showerror("Project opslaan", str(exc), parent=self)
            return
        self._set_busy(
            True,
            "Vrijgaven controleren, alle partformaten opnieuw valideren en merkpakketten bouwen...",
        )
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)
                manifest, root, zip_path = working.export_production_package(
                    output_dir,
                    user="gui",
                )
                working.save(
                    embed_sources=embed_sources,
                    user="gui",
                    revision_message="Vrijgegeven productie-exportpakket gebouwd",
                )
                self.events.put(
                    ("production_export_ok", (working, manifest, root, zip_path))
                )
                working = None
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("Productiepakket", str(exc))))

        threading.Thread(
            target=worker,
            daemon=True,
            name="cws-project-production-export",
        ).start()

    def confirm_selected_classification(self) -> None:
        selected = list(self.part_grid.selection())
        if not selected or self.session is None or self.session.path is None:
            messagebox.showinfo("Classificatie", "Selecteer eerst één onderdeel.", parent=self)
            return
        part_id = selected[0]
        current = self.session.project.parts.get(part_id)
        if current is None:
            return
        category = simpledialog.askstring(
            "Classificatie bevestigen",
            "Categorie (make_part, purchased_item, non_steel, reference, unknown):",
            initialvalue=current.category, parent=self,
        )
        if not category:
            return
        category = category.strip().lower()
        allowed = {"make_part", "purchased_item", "non_steel", "reference", "unknown"}
        if category not in allowed:
            messagebox.showerror("Classificatie", f"Onbekende categorie: {category}", parent=self)
            return
        reason = simpledialog.askstring(
            "Classificatie bevestigen", "Reden voor auditlog:", parent=self
        )
        if not reason:
            return
        self._set_busy(True, f"Classificatie van {current.part_position or current.name} opslaan…")
        project_path = Path(self.session.path)
        embed_sources = self.embed_sources.get()

        def worker() -> None:
            working: ProjectSession | None = None
            try:
                working = ProjectSession.open(project_path, store=self.store)
                report = working.confirm_part_classification(
                    part_id, category, user="gui", reason=reason
                )
                working.save(
                    embed_sources=embed_sources, user="gui",
                    revision_message=f"Classificatie {part_id} bevestigd",
                )
                self.events.put(("classification_ok", (working, report)))
                working = None
            except Exception as exc:
                if working is not None:
                    working.close()
                self.events.put(("error", ("Classificatie bevestigen", str(exc))))

        threading.Thread(target=worker, daemon=True, name="cws-part-classification").start()

    def cancel_current_operation(self) -> None:
        if not self._busy or not self._busy_cancellable:
            return
        self._cancel_event.set()
        self.cancel_button.configure(state="disabled")
        self.status_label.configure(text="Annuleren… huidige importstap veilig afronden")

    def export_baseline_report(self) -> None:
        if self.session is None or not self.session.project.sources:
            messagebox.showinfo("Nulmeting", "Het project bevat nog geen IFC/STEP-bronnen.", parent=self)
            return
        initial = (self.session.path.stem if self.session.path else "CWS_project") + "_importnulmeting.json"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Importnulmeting exporteren",
            defaultextension=".json",
            filetypes=[("JSON-rapport", "*.json")],
            initialfile=initial,
        )
        if not path:
            return
        try:
            analyses = [
                BaselineAnalysis.from_dict(source.analysis)
                for source in self.session.project.sources.values()
                if source.analysis
            ]
            target = write_baseline_report(analyses, path)
            self.status_label.configure(text=f"Nulmeting opgeslagen: {target.name}")
            self.log_callback(f"Projectimport-nulmeting opgeslagen: {target}")
        except Exception as exc:
            messagebox.showerror("Nulmeting exporteren", str(exc), parent=self)

    def extract_selected_source(self) -> None:
        if self.session is None or self.session.package is None:
            return
        selected = self.source_grid.selection()
        if not selected:
            messagebox.showinfo("Bron uitpakken", "Selecteer eerst een bronbestand.", parent=self)
            return
        source_id = selected[0]
        source = self.session.project.sources.get(source_id)
        if source is None:
            return
        folder = filedialog.askdirectory(parent=self, title="Ingesloten bron uitpakken naar")
        if not folder:
            return
        try:
            target = Path(folder) / source.file_name
            if target.exists() and not messagebox.askyesno(
                "Bestand bestaat",
                f"{target.name} bestaat al. Overschrijven?",
                parent=self,
            ):
                return
            extracted = self.session.package.extract_source(source_id, target)
            self.status_label.configure(text=f"Bron uitgepakt: {extracted.name}")
            self.log_callback(f"Ingesloten bron uitgepakt: {extracted}")
        except Exception as exc:
            messagebox.showerror("Bron uitpakken", str(exc), parent=self)

    # ------------------------------------------------------------------ rendering
    def refresh(self) -> None:
        self.project_tree.delete(*self.project_tree.get_children())
        self.source_grid.delete(*self.source_grid.get_children())
        self.part_grid.delete(*self.part_grid.get_children())
        self._source_rows.clear()
        self._part_rows.clear()
        if self.session is None:
            self.part_workbench.clear()
            self.project_badge.configure(text="GEEN PROJECT", bg="#334155")
            self.project_path_label.configure(text="Maak of open een .cwscproj-project")
            self.card_values["sources"].configure(text="0")
            self.card_values["assemblies"].configure(text="0")
            self.card_values["parts"].configure(text="0")
            self.card_values["warnings"].configure(text="0")
            self.card_values["storage"].configure(text="Niet geopend")
            self.bom_kpi_label.configure(
                text="Nog geen project — open een .cwscproj-bestand",
                bg="#eef4fa", fg="#334155",
            )
            self._set_details(
                f"{APP_NAME}-projecten bewaren bronhashes, importstrategieën, "
                "auditgegevens en optioneel de volledige IFC/STEP-bronnen in één "
                "draagbaar .cwscproj-bestand."
            )
            return

        project = self.session.project
        summary = project.summary(include_expensive_hashes=False)
        badge_styles = {
            "validated": ("GEVALIDEERD", "#16835f"),
            "released": ("VRIJGEGEVEN", "#16835f"),
            "blocked": ("GEBLOKKEERD", "#b42318"),
            "review_required": ("CONTROLE NODIG", "#c27a12"),
            "obsolete": ("VERVALLEN", "#64748b"),
            "new": ("NIEUW", "#2563a6"),
        }
        badge_text, badge_color = badge_styles.get(project.status, (project.status.upper(), "#334155"))
        self.project_badge.configure(text=badge_text, bg=badge_color)
        self.project_path_label.configure(text=str(self.session.path or "Nog niet opgeslagen"))

        detected_assemblies = 0
        detected_parts = 0
        source_warning_count = 0
        for source in project.sources.values():
            analysis = dict(source.analysis or {})
            classes = dict(analysis.get("class_summary") or {})
            detected_assemblies += int(classes.get("assemblies", 0) or 0)
            detected_parts += sum(
                int(classes.get(key, 0) or 0)
                for key in (
                    "plates",
                    "beams",
                    "columns",
                    "members",
                    "footings",
                    "building_element_proxies",
                    "slabs",
                )
            )
            if source.source_format == "STEP":
                detected_parts += int(analysis.get("solid_count", 0) or 0)
            source_warning_count += len(source.warnings)

        blocking_count = len(project.blocking_issues())
        self.card_values["sources"].configure(text=str(len(project.sources)))
        self.card_values["assemblies"].configure(
            text=f"{len(project.assemblies)} actief\n{detected_assemblies} gedetecteerd"
            if detected_assemblies
            else str(len(project.assemblies))
        )
        if project.parts or project.fasteners or project.welds:
            self.card_values["parts"].configure(
                text=(
                    f"{len(project.parts)} actief\n"
                    f"{len(project.fasteners)} bouten · {len(project.welds)} lassen"
                )
            )
        else:
            self.card_values["parts"].configure(
                text=f"0 actief\n{detected_parts} gedetecteerd"
                if detected_parts
                else "0"
            )
        self.card_values["warnings"].configure(
            text=f"{blocking_count} blokkade(n)\n{source_warning_count} melding(en)"
        )
        try:
            file_size = self.session.path.stat().st_size if self.session.path else 0
            embedded_count = len(
                self.session.package.embedded_source_names()
                if self.session.package is not None
                else {}
            )
            self.card_values["storage"].configure(
                text=f"{file_size / 1024 / 1024:.1f} MB\n{embedded_count} bron(n) ingesloten"
            )
        except OSError:
            self.card_values["storage"].configure(text="Niet opgeslagen")

        root = self.project_tree.insert("", "end", text=project.project_name, open=True)
        sources_node = self.project_tree.insert(
            root, "end", text=f"Bronbestanden ({len(project.sources)})", open=True
        )
        assemblies_node = self.project_tree.insert(
            root, "end", text=f"Assemblies / merken ({len(project.assemblies)})", open=True
        )
        assembly_marks = Counter(
            item.assembly_mark or "(zonder merk)" for item in project.assemblies.values()
        )
        for mark, count in sorted(assembly_marks.items(), key=lambda item: (-item[1], item[0]))[:120]:
            self.project_tree.insert(assemblies_node, "end", text=f"{mark}  × {count}")
        if len(assembly_marks) > 120:
            self.project_tree.insert(
                assemblies_node,
                "end",
                text=f"… {len(assembly_marks) - 120} overige merken",
            )

        parts_node = self.project_tree.insert(
            root, "end", text=f"Onderdelen ({len(project.parts)})", open=True
        )
        part_types = Counter(item.part_type or "unknown" for item in project.parts.values())
        for part_type, count in sorted(part_types.items(), key=lambda item: (-item[1], item[0])):
            self.project_tree.insert(parts_node, "end", text=f"{part_type}: {count}")
        self.project_tree.insert(root, "end", text=f"Inkoopdelen ({len(project.purchased_items)})")
        self.project_tree.insert(root, "end", text=f"Bouten / fasteners ({len(project.fasteners)})")
        self.project_tree.insert(root, "end", text=f"Lassen ({len(project.welds)})")
        self.project_tree.insert(root, "end", text=f"Revisies ({len(project.revisions)})")
        validation_node = self.project_tree.insert(
            root, "end", text=f"Validatie ({blocking_count} blokkade(n))"
        )
        for issue in project.blocking_issues():
            self.project_tree.insert(validation_node, "end", text=issue.message)

        embedded_names = (
            self.session.package.embedded_source_names()
            if self.session.package is not None
            else {}
        )
        for source_id, source in project.sources.items():
            analysis = dict(source.analysis or {})
            source_node = self.project_tree.insert(sources_node, "end", text=source.file_name)
            semantic_counts = dict(source.metadata.get("semantic_entity_counts") or {})
            if source.semantic_import_complete:
                for label, key in (
                    ("Assemblies", "assemblies"),
                    ("Onderdelen", "parts"),
                    ("Bouten", "fasteners"),
                    ("Lassen", "welds"),
                ):
                    self.project_tree.insert(
                        source_node,
                        "end",
                        text=f"{label}: {int(semantic_counts.get(key, 0) or 0)}",
                    )
            route = source.import_strategy
            embedded = source_id in embedded_names
            if source.production_export_allowed:
                status = "Productie vrij"
            elif source.semantic_import_complete:
                status = "Import afgerond · geblokkeerd"
            else:
                status = "Ingesloten · review" if embedded else "Referentie · review"
            schema = source.schema
            if len(schema) > 30:
                schema = schema[:27] + "…"
            self.source_grid.insert(
                "",
                "end",
                iid=source_id,
                values=(
                    source.source_format,
                    schema,
                    route,
                    int(
                        semantic_counts.get("total_materialised", 0)
                        or analysis.get("product_count", 0)
                        or 0
                    ),
                    int(analysis.get("solid_count", 0) or 0),
                    status,
                ),
            )
            self._source_rows[source_id] = {
                "source_id": source.source_id,
                "file_name": source.file_name,
                "source_format": source.source_format,
                "sha256": source.sha256,
                "schema": source.schema,
                "import_strategy": source.import_strategy,
                "analysis_status": source.analysis_status,
                "semantic_import_complete": source.semantic_import_complete,
                "production_export_allowed": source.production_export_allowed,
                "embedded": embedded,
            }

        self._refresh_classification_grid()
        self.part_workbench.refresh()

        self._set_details(
            f"PROJECT\n{project.project_name}\n\n"
            f"Klant: {project.customer or '—'}\n"
            f"Order: {project.order_number or '—'}\n"
            f"Fase: {project.project_phase or '—'}\n"
            f"Project-ID: {project.project_id}\n"
            f"Schema: {project.schema_version}\n"
            f"Projecthash: {summary['semantic_sha256']}\n"
            f"Productiestatus: {project.status}\n"
            f"Blokkerende controles: {blocking_count}\n\n"
            "IFC/STEP-bronnen kunnen nu expliciet semantisch worden geïmporteerd. "
            "Daarbij worden bronhiërarchie, assemblies, onderdelen, bouten, lassen, "
            "properties en placements in het Canonical Project Model vastgelegd. "
            "Classificatie, productie-identiteit en BOM zijn nu onderdeel van dezelfde "
            "projectketen. NC1- en machine-uitvoer blijven bewust geblokkeerd totdat "
            "profiel, features, referentiezijden en roundtrip per onderdeel zijn gevalideerd."
        )
        self.status_label.configure(
            text="Project gereed" if not self.session.dirty else "Niet-opgeslagen wijzigingen"
        )

    def _refresh_classification_grid(self) -> None:
        self.part_grid.delete(*self.part_grid.get_children())
        self._part_rows.clear()
        if self.session is None:
            return
        project = self.session.project
        search = self.part_search.get().strip().lower()
        category_filter = self.part_category_filter.get().strip()
        classification = dict(project.settings.get("classification") or {})
        bom = dict(project.settings.get("bom") or {})
        bom_summary = dict(bom.get("summary") or {})
        category_counts = dict(classification.get("category_counts") or {})
        if bom_summary:
            blocked = int(bom_summary.get("blocking_conflict_count", 0) or 0)
            self.bom_kpi_label.configure(
                text=(
                    f"{bom_summary.get('part_group_count', 0)} unieke partregels  ·  "
                    f"{bom_summary.get('assembly_group_count', 0)} assemblymerken  ·  "
                    f"{bom_summary.get('purchase_group_count', 0)} inkoopgroepen  ·  "
                    f"{blocked} blokkades"
                ),
                bg="#fdecec" if blocked else "#edf8f2",
                fg="#9c0006" if blocked else "#166534",
            )
        elif classification:
            self.bom_kpi_label.configure(
                text=(
                    f"Classificatie: {category_counts.get('make_part', 0)} maakdelen  ·  "
                    f"{category_counts.get('purchased_item', 0)} inkoopdelen  ·  "
                    f"{classification.get('unknown_part_count', 0)} onbekend"
                ),
                bg="#fff7e6", fg="#8a4b08",
            )
        else:
            self.bom_kpi_label.configure(
                text="Nog niet geclassificeerd — productie-uitvoer blijft geblokkeerd",
                bg="#fff7e6", fg="#8a4b08",
            )
        values = sorted(
            project.parts.values(),
            key=lambda item: (item.part_position or "~", item.name, item.internal_id),
        )
        for part in values:
            if category_filter not in {"", "alle"} and part.category != category_filter:
                continue
            haystack = " ".join(
                [part.part_position, part.name, part.category, part.profile, part.material,
                 part.material_grade, part.normalized_profile, part.normalized_material,
                 part.source_identity.assembly_mark]
            ).lower()
            if search and search not in haystack:
                continue
            reasons = [issue.message for issue in part.blocking_issues()]
            tag = "blocked" if reasons else (
                "review" if part.classification_status in {"unclassified", "review_required"} else "ok"
            )
            assembly_marks = []
            for assembly_id in part.assembly_ids:
                assembly = project.assemblies.get(assembly_id)
                if assembly and assembly.assembly_mark:
                    assembly_marks.append(assembly.assembly_mark)
            self.part_grid.insert(
                "", "end", iid=part.internal_id, tags=(tag,),
                values=(
                    part.classification_status, part.category, part.part_position or "—",
                    ", ".join(sorted(set(assembly_marks))) or part.source_identity.assembly_mark or "—",
                    part.normalized_profile or part.profile or "—",
                    part.normalized_material or part.material_grade or part.material or "—",
                    f"{part.length_mm:.3f}", part.quantity_total, f"{part.mass_each_kg:.3f}",
                    f"{part.classification_confidence * 100:.0f}%",
                    "ja" if part.nc1_eligible else "nee",
                    " | ".join(reasons),
                ),
            )
            self._part_rows[part.internal_id] = {
                "part": part, "blocking_reasons": reasons, "assembly_marks": sorted(set(assembly_marks)),
            }

    def _part_selected(self, _event=None) -> None:
        selected = list(self.part_grid.selection())
        if not selected or self.session is None:
            return
        row = self._part_rows.get(selected[0])
        if not row:
            return
        part = row["part"]
        lines = [
            part.part_position or part.name or part.internal_id,
            "=" * 48,
            f"Categorie: {part.category}",
            f"Classificatiestatus: {part.classification_status}",
            f"Regel: {part.classification_rule_id or '—'}",
            f"Reden: {part.classification_reason or '—'}",
            f"Confidence: {part.classification_confidence * 100:.1f}%",
            "",
            f"Profiel: {part.normalized_profile or part.profile or '—'}",
            f"Materiaal: {part.normalized_material or part.material_grade or part.material or '—'}",
            f"Lengte: {part.length_mm:.3f} mm",
            f"Massa/stuk: {part.mass_each_kg:.3f} kg",
            f"Aantal: {part.quantity_total}",
            f"Assemblymerken: {', '.join(row['assembly_marks']) or '—'}",
            "",
            f"Geometry hash: {part.geometry_hash}",
            f"Manufacturing hash: {part.manufacturing_hash}",
            f"Production identity: {part.production_identity_hash or 'nog niet berekend'}",
            f"Bronentity: {part.source_identity.source_entity_id or '—'}",
            f"Bron-GlobalId: {part.source_identity.global_id or '—'}",
            "",
            "BLOKKADES",
        ]
        lines.extend(f"• {reason}" for reason in row["blocking_reasons"])
        if not row["blocking_reasons"]:
            lines.append("Geen classificatieblokkade; productiegate kan nog wel gesloten zijn.")
        self.part_details.configure(state="normal")
        self.part_details.delete("1.0", "end")
        self.part_details.insert("1.0", "\n".join(lines))
        self.part_details.configure(state="disabled")
        self.part_workbench.select_part(part.internal_id, notify=False)

    def _select_part_from_workbench(self, part_id: str) -> None:
        if not self.part_grid.exists(part_id):
            return
        self.part_grid.selection_set(part_id)
        self.part_grid.focus(part_id)
        self.part_grid.see(part_id)
        self._part_selected()

    def _workbench_changed(self) -> None:
        self.refresh()

    def _workbench_status(self, message: str) -> None:
        self.status_label.configure(text=message)
        self.log_callback(message)

    def _source_selected(self, _event=None) -> None:
        selected = self.source_grid.selection()
        if not selected or self.session is None:
            return
        source = self.session.project.sources.get(selected[0])
        if source is None:
            return
        analysis = dict(source.analysis or {})
        embedded = bool(
            self.session.package
            and selected[0] in self.session.package.embedded_source_names()
        )
        lines = [
            source.file_name,
            "=" * min(72, len(source.file_name)),
            f"Formaat: {source.source_format}",
            f"Schema: {source.schema or '—'}",
            f"Applicatie: {source.application or '—'}",
            f"SHA-256: {source.sha256}",
            f"Bestandsgrootte: {source.size_bytes / 1024 / 1024:.2f} MB",
            f"Ingesloten: {'ja' if embedded else 'nee'}",
            f"Importstrategie: {source.import_strategy}",
            f"Analysestatus: {source.analysis_status}",
            f"Semantische import compleet: {'ja' if source.semantic_import_complete else 'nee'}",
            f"Productie-export toegestaan: {'ja' if source.production_export_allowed else 'nee'}",
            f"Reden: {analysis.get('strategy_reason', '—')}",
            "",
            "KLASSEN / NULMETING",
        ]
        for key, value in sorted(dict(analysis.get("class_summary") or {}).items()):
            lines.append(f"• {key}: {value}")
        checks = dict(analysis.get("reference_checks") or {})
        if checks:
            lines.extend(["", "REFERENTIECONTROLES"])
            for key, value in checks.items():
                lines.append(f"• {key}: {json.dumps(value, ensure_ascii=False)}")
        geometry = dict(analysis.get("geometry_metrics") or {})
        if geometry:
            lines.extend(["", "CAD-GEOMETRIENULMETING"])
            for key, value in geometry.items():
                lines.append(f"• {key}: {value}")
        semantic = dict(analysis.get("semantic_import") or {})
        if semantic:
            lines.extend(["", "SEMANTISCHE IMPORT"])
            lines.append(f"• Importer: {semantic.get('importer_version', '—')}")
            lines.append(f"• Route: {semantic.get('strategy', source.import_strategy)}")
            for key, value in dict(semantic.get("entity_counts") or {}).items():
                lines.append(f"• {key}: {value}")
            evidence = dict(semantic.get("evidence") or {})
            for key in (
                "MLO4_assembly_count",
                "MLO4_LO4_links",
                "bolt_or_hole_diameter_14_count",
                "connected_weld_count",
                "product_count",
                "solid_root_count",
                "materialised_part_count",
            ):
                if key in evidence:
                    value = evidence[key]
                    if isinstance(value, (list, dict)):
                        value = json.dumps(value, ensure_ascii=False)
                    lines.append(f"• {key}: {value}")
            blocking = list(semantic.get("blocking_reasons") or [])
            if blocking:
                lines.extend(["", "PRODUCTIEGATE"])
                lines.extend(f"⛔ {item}" for item in blocking)
        issues = [
            issue
            for issue in self.session.project.validation_issues
            if issue.entity_id == source.source_id and not issue.resolved
        ]
        if source.warnings or issues:
            lines.extend(["", "CONTROLEPUNTEN"])
            lines.extend(f"⚠ {item}" for item in source.warnings)
            lines.extend(f"⛔ {item.message}" for item in issues if item.blocking)
        self._set_details("\n".join(lines))

    def _set_details(self, text: str) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def _sort_sources(self, column: str, reverse: bool) -> None:
        items = [(self.source_grid.set(item, column), item) for item in self.source_grid.get_children("")]

        def key(record):
            value = record[0]
            try:
                return (0, float(value))
            except (TypeError, ValueError):
                return (1, str(value).casefold())

        items.sort(key=key, reverse=reverse)
        for index, (_value, item) in enumerate(items):
            self.source_grid.move(item, "", index)
        self.source_grid.heading(column, command=lambda: self._sort_sources(column, not reverse))

    # ------------------------------------------------------------------ lifecycle
    def _set_busy(
        self,
        busy: bool,
        message: str = "",
        *,
        cancellable: bool = False,
    ) -> None:
        self._busy = busy
        self._busy_cancellable = bool(busy and cancellable)
        state = "disabled" if busy else "normal"
        for button in (
            self.new_button,
            self.open_button,
            self.save_button,
            self.add_button,
            self.semantic_button,
            self.classify_button,
            self.bom_button,
            self.production_button,
            self.report_button,
            self.extract_button,
        ):
            button.configure(state=state)
        self.cancel_button.configure(
            state="normal" if self._busy_cancellable else "disabled"
        )
        self.part_workbench.set_busy(busy)
        if busy:
            self.progress.start(10)
        else:
            self.progress.stop()
            self._cancel_event.clear()
        if message:
            self.status_label.configure(text=message)

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "import_ok":
                    session, results = payload
                    self._replace_session(session)
                    self._set_busy(False, f"{len(results)} bronbestand(en) toegevoegd en opgeslagen")
                    self.log_callback(
                        f"Projectimport-nulmeting gereed voor {len(results)} bestand(en): "
                        + ", ".join(item.source.file_name for item in results)
                    )
                    self.refresh()
                elif event == "semantic_progress":
                    done, total, message = payload
                    percentage = int(round((float(done) / max(1, int(total))) * 100.0))
                    self.status_label.configure(text=f"{percentage:3d}% · {message}")
                elif event == "semantic_ok":
                    session, results = payload
                    self._replace_session(session)
                    total = sum(
                        int(result.entity_counts.get("total_materialised", 0) or 0)
                        for result in results
                    )
                    self._set_busy(
                        False,
                        f"Semantische import gereed: {total} objecten gematerialiseerd",
                    )
                    self.log_callback(
                        f"Semantische IFC/STEP-import gereed voor {len(results)} bron(n); "
                        f"{total} objecten gematerialiseerd. Productiegate blijft actief."
                    )
                    self.refresh()
                elif event == "classification_ok":
                    session, report = payload
                    self._replace_session(session)
                    self._set_busy(
                        False,
                        f"Classificatie gereed: {report.classified_part_count} onderdelen, "
                        f"{report.review_required_count} te beoordelen",
                    )
                    self.workspace.select(1)
                    self.log_callback(
                        f"Classificatie gereed: {report.category_counts}; "
                        f"{report.identity_conflict_count} identiteitsconflicten."
                    )
                    self.refresh()
                elif event == "bom_ok":
                    session, snapshot, outputs = payload
                    self._replace_session(session)
                    self._last_bom_snapshot = snapshot
                    self._set_busy(
                        False,
                        f"BOM-pakket gereed: {snapshot.summary['part_group_count']} partregels",
                    )
                    self.workspace.select(1)
                    self.refresh()
                    package = next((path for name, path in outputs.items() if name.endswith('_PACKAGE.zip')), None)
                    messagebox.showinfo(
                        "BOM / Excel gereed",
                        f"Partregels: {snapshot.summary['part_group_count']}\n"
                        f"Assemblymerken: {snapshot.summary['assembly_group_count']}\n"
                        f"Inkoopgroepen: {snapshot.summary['purchase_group_count']}\n"
                        f"Blokkerende conflicten: {snapshot.summary['blocking_conflict_count']}\n\n"
                        f"Pakket: {package or 'uitvoermap'}",
                        parent=self,
                    )
                elif event == "production_export_ok":
                    session, manifest, root, zip_path = payload
                    self._replace_session(session)
                    ready = bool(manifest.summary.get("production_ready"))
                    self._set_busy(
                        False,
                        "Productiepakket gereed" if ready else "Productiepakket bevat blokkades",
                    )
                    self.refresh()
                    messagebox.showinfo(
                        "Productiepakket gereed",
                        f"Onderdelen: {manifest.summary['selected_parts']}\n"
                        f"Merkpakketten: {manifest.summary['assemblies']}\n"
                        f"Productieartefacten: {manifest.summary['production_artifacts_exported']}\n"
                        f"Status: {'VRIJGEGEVEN' if ready else 'GEBLOKKEERD / REVIEW'}\n\n"
                        f"Pakket: {zip_path or root}",
                        parent=self,
                    )
                elif event == "semantic_cancelled":
                    self._set_busy(False, "Semantische import geannuleerd; project ongewijzigd")
                    self.log_callback(str(payload))
                elif event == "error":
                    title, message = payload
                    self._set_busy(False, "Bewerking mislukt")
                    messagebox.showerror(title, message, parent=self)
        except queue.Empty:
            pass
        self.after(120, self._poll_events)

    def _autosave_tick(self) -> None:
        if self.session is not None and self.session.dirty and not self._busy:
            try:
                target = self.session.autosave()
                self.status_label.configure(text=f"Autosave: {target.name}")
            except Exception as exc:
                self.log_callback(f"WAARSCHUWING autosave mislukt: {exc}")
        self.after(self.AUTOSAVE_INTERVAL_MS, self._autosave_tick)

    def _confirm_discard_dirty(self) -> bool:
        if self.session is None or not self.session.dirty:
            return True
        answer = messagebox.askyesnocancel(
            "Niet-opgeslagen wijzigingen",
            "Wilt u de huidige wijzigingen opslaan voordat een ander project wordt geopend?",
            parent=self,
        )
        if answer is None:
            return False
        if answer:
            self.save_project()
            return self.session is not None and not self.session.dirty
        return True

    def destroy(self) -> None:
        self._cancel_event.set()
        if self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
            self.session = None
        super().destroy()


__all__ = ["CWSProjectTab"]
