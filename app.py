from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from conversion import (
    __version__,
    convert_file,
    convert_nc1_to_step,
    import_profiles_from_nc1,
    step_to_nc1,
)
from ifc_support import dstv_to_ifc, ifc_available, ifc_to_dstv, ifc_to_step, step_to_ifc
from ai_support import AISettings
from material_database import MaterialDatabase
from pdf_support import (
    ExternalPDFExportBlocked,
    analyze_pdf,
    ifc_to_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    review_external_pdf,
    step_to_pdf,
    write_analysis_report,
)
from profile_database import ProfileDatabase
from quantities import QuantityAnalysis, analyze_files, export_excel
from visualization import ComparisonViewer


DIRECTION_LABELS = {
    "nc1-to-step": "NC1 / DSTV → STEP",
    "step-to-nc1": "STEP → NC1 / DSTV",
    "ifc-to-dstv": "IFC → DSTV / NC1",
    "dstv-to-ifc": "DSTV / NC1 → IFC",
    "ifc-to-step": "IFC → STEP",
    "step-to-ifc": "STEP → IFC",
    "pdf-to-nc1": "PDF / tekening → NC1 / DSTV",
    "pdf-to-step": "PDF / tekening → STEP",
    "pdf-to-ifc": "PDF / tekening → IFC",
    "nc1-to-pdf": "NC1 / DSTV → technische PDF",
    "step-to-pdf": "STEP → technische PDF",
    "ifc-to-pdf": "IFC → technische PDF",
}

MODEL_SUFFIXES = {".nc", ".nc1", ".step", ".stp", ".ifc"}


@dataclass
class ComparisonRecord:
    source: Path
    target: Path
    direction: str
    description: str

    @property
    def label(self) -> str:
        arrow = DIRECTION_LABELS.get(self.direction, self.direction)
        return f"{self.source.name}  |  {arrow}  |  {self.target.name}"


class ConverterApp(tk.Tk):
    def __init__(self, initial_files=()) -> None:
        super().__init__()
        self.title(f"NC1 ↔ STEP / IFC Converter v{__version__}")
        self.minsize(1220, 760)
        self.geometry("1500x900")

        self.direction = tk.StringVar(value="nc1-to-step")
        self.output_directory = tk.StringVar(value=str(Path.home() / "NC1_STEP_Output"))
        self.material = tk.StringVar(value="S355JR")
        self.order_number = tk.StringVar(value="STEP")
        self.profile_choice = tk.StringVar(value="Automatisch")
        self.profile_tolerance = tk.DoubleVar(value=1.0)
        self.strict_validation = tk.BooleanVar(value=True)
        self.auto_preview = tk.BooleanVar(value=True)
        self.profile_search = tk.StringVar(value="")
        self.profile_family = tk.StringVar(value="Alle")
        self.profile_type = tk.StringVar(value="Alle")
        self.quantity_material = tk.StringVar(value="S355JR")
        self.pdf_review_source = tk.StringVar(value="")
        self.pdf_review_file = tk.StringVar(value="")
        self.pdf_ai_provider = tk.StringVar(value="none")
        self.pdf_allow_cloud = tk.BooleanVar(value=False)
        self.pdf_analysis_result = None
        self.quantity_files: list[Path] = []
        self.quantity_analysis: QuantityAnalysis | None = None
        self.files: list[Path] = []
        self.comparisons: list[ComparisonRecord] = []
        self.events: queue.Queue[tuple] = queue.Queue()
        self.quantity_events: queue.Queue[tuple] = queue.Queue()
        self.pdf_events: queue.Queue[tuple] = queue.Queue()
        self._active_direction = self.direction.get()
        self.profile_database = ProfileDatabase()
        self.material_database = MaterialDatabase()

        self._build_ui()
        self._refresh_profile_controls()
        self._refresh_material_controls()
        self._direction_changed()
        if not ifc_available():
            self._write_log(
                "OPMERKING: IfcOpenShell is niet geïnstalleerd in deze omgeving. IFC-functies worden beschikbaar na installatie via requirements.txt."
            )
        startup_paths = [Path(value).expanduser() for value in initial_files if str(value).strip()]
        if startup_paths:
            self.after_idle(lambda: self._open_initial_files(startup_paths))

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.converter_tab = ttk.Frame(self.notebook, padding=12)
        self.preview_tab = ttk.Frame(self.notebook, padding=8)
        self.database_tab = ttk.Frame(self.notebook, padding=12)
        self.quantities_tab = ttk.Frame(self.notebook, padding=12)
        self.pdf_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.converter_tab, text="Converter")
        self.notebook.add(self.pdf_tab, text="PDF / Tekening")
        self.notebook.add(self.preview_tab, text="Visuele vergelijking")
        self.notebook.add(self.database_tab, text="Profielendatabase")
        self.notebook.add(self.quantities_tab, text="Hoeveelheden & Excel")

        self._build_converter_tab()
        self._build_pdf_tab()
        self._build_preview_tab()
        self._build_database_tab()
        self._build_quantities_tab()

    def _build_converter_tab(self) -> None:
        root = self.converter_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)
        root.rowconfigure(7, weight=1)

        direction_box = ttk.LabelFrame(root, text="Conversierichting", padding=10)
        direction_box.grid(row=0, column=0, sticky="ew")
        for idx, (value, label) in enumerate(DIRECTION_LABELS.items()):
            ttk.Radiobutton(
                direction_box,
                text=label,
                variable=self.direction,
                value=value,
                command=self._direction_changed,
            ).grid(row=idx // 3, column=idx % 3, sticky="w", padx=(0, 28), pady=2)

        buttons = ttk.Frame(root)
        buttons.grid(row=1, column=0, sticky="ew", pady=(12, 6))
        ttk.Button(buttons, text="Bestanden kiezen", command=self._choose_files).pack(side="left")
        ttk.Button(buttons, text="Map kiezen", command=self._choose_input_folder).pack(side="left", padx=6)
        ttk.Button(buttons, text="Lijst leegmaken", command=self._clear_files).pack(side="left")
        ttk.Button(buttons, text="Uitvoermap openen", command=lambda: self._open_path(Path(self.output_directory.get()))).pack(side="right")

        self.note = ttk.Label(root, wraplength=1320, justify="left")
        self.note.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        file_frame = ttk.LabelFrame(root, text="Invoerbestanden", padding=6)
        file_frame.grid(row=3, column=0, sticky="nsew")
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(0, weight=1)
        self.file_list = tk.Listbox(file_frame, selectmode="extended")
        self.file_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)
        ttk.Button(file_frame, text="Geselecteerde regels verwijderen", command=self._remove_selected).grid(row=1, column=0, sticky="w", pady=(6, 0))

        settings = ttk.LabelFrame(root, text="Uitvoer en conversie-instellingen", padding=10)
        settings.grid(row=4, column=0, sticky="ew", pady=(12, 6))
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="Uitvoermap:").grid(row=0, column=0, sticky="w")
        ttk.Entry(settings, textvariable=self.output_directory).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(settings, text="Kiezen", command=self._choose_output_folder).grid(row=0, column=2)

        self.advanced_settings = ttk.Frame(settings)
        self.advanced_settings.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        for column in range(6):
            self.advanced_settings.columnconfigure(column, weight=1 if column in {1, 3, 5} else 0)
        ttk.Label(self.advanced_settings, text="Materiaal:").grid(row=0, column=0, sticky="w")
        self.material_combo = ttk.Combobox(self.advanced_settings, textvariable=self.material, width=16)
        self.material_combo.grid(row=0, column=1, sticky="w", padx=(6, 18))
        ttk.Label(self.advanced_settings, text="Ordernummer:").grid(row=0, column=2, sticky="w")
        ttk.Entry(self.advanced_settings, textvariable=self.order_number, width=16).grid(row=0, column=3, sticky="w", padx=(6, 18))
        ttk.Label(self.advanced_settings, text="Profiel:").grid(row=0, column=4, sticky="w")
        self.profile_combo = ttk.Combobox(self.advanced_settings, textvariable=self.profile_choice, state="readonly", width=28)
        self.profile_combo.grid(row=0, column=5, sticky="ew", padx=(6, 0))
        ttk.Label(self.advanced_settings, text="Herkenningstolerantie (mm):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(self.advanced_settings, from_=0.1, to=10.0, increment=0.1, textvariable=self.profile_tolerance, width=8).grid(
            row=1, column=1, sticky="w", padx=(6, 18), pady=(8, 0)
        )
        ttk.Label(
            self.advanced_settings,
            text="Strikte veiligheidscontrole is verplicht en kan niet worden uitgeschakeld.",
        ).grid(row=1, column=2, columnspan=4, sticky="w", pady=(8, 0))

        preview_option = ttk.Frame(root)
        preview_option.grid(row=5, column=0, sticky="ew")
        ttk.Checkbutton(
            preview_option,
            text="Na afloop automatisch het laatste bestand links/rechts vergelijken",
            variable=self.auto_preview,
        ).pack(side="left")

        action = ttk.Frame(root)
        action.grid(row=6, column=0, sticky="ew", pady=(8, 8))
        self.convert_button = ttk.Button(action, text="Converteren", command=self._start_conversion)
        self.convert_button.pack(side="left")
        self.progress = ttk.Progressbar(action, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=12)
        self.status = ttk.Label(action, text="Gereed")
        self.status.pack(side="right")

        log_frame = ttk.LabelFrame(root, text="Conversielog", padding=6)
        log_frame.grid(row=7, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=8, wrap="word", state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=log_scroll.set)

    def _build_pdf_tab(self) -> None:
        """Functional review surface for external and Trusted Converter PDFs.

        The full side-by-side drawing editor is a later UI phase. This tab
        already exposes the safe workflow: deterministic analysis, confidence
        and provenance review, explicit questions, optional advisory AI and a
        reviewed Trusted PDF export.
        """

        root = self.pdf_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        source_box = ttk.LabelFrame(root, text="Technische PDF", padding=10)
        source_box.grid(row=0, column=0, sticky="ew")
        source_box.columnconfigure(1, weight=1)
        ttk.Label(source_box, text="Bron-PDF:").grid(row=0, column=0, sticky="w")
        ttk.Entry(source_box, textvariable=self.pdf_review_source).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(source_box, text="Kiezen", command=self._choose_pdf_review_source).grid(row=0, column=2)

        ttk.Label(source_box, text="AI-provider:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        provider = ttk.Combobox(
            source_box,
            textvariable=self.pdf_ai_provider,
            values=["none", "local-rules", "openai"],
            state="readonly",
            width=18,
        )
        provider.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))
        ttk.Checkbutton(
            source_box,
            text="Ik geef voor deze analyse expliciet toestemming voor cloudverwerking",
            variable=self.pdf_allow_cloud,
        ).grid(row=1, column=1, sticky="e", padx=8, pady=(8, 0))
        self.pdf_analyze_button = ttk.Button(source_box, text="Analyseren", command=self._start_pdf_analysis)
        self.pdf_analyze_button.grid(row=1, column=2, pady=(8, 0))

        action_box = ttk.Frame(root)
        action_box.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        ttk.Button(action_box, text="Analyse-JSON opslaan", command=self._save_pdf_analysis).pack(side="left")
        ttk.Label(action_box, text="Review-JSON:").pack(side="left", padx=(18, 4))
        ttk.Entry(action_box, textvariable=self.pdf_review_file, width=58).pack(side="left", fill="x", expand=True)
        ttk.Button(action_box, text="Kiezen", command=self._choose_pdf_review_file).pack(side="left", padx=4)
        ttk.Button(action_box, text="Reviewed Trusted PDF maken", command=self._review_pdf_to_trusted).pack(side="right")

        self.pdf_status = ttk.Label(
            root,
            text=(
                "Trusted PDF wordt exact gelezen. Externe PDF wordt lokaal als vector/raster geanalyseerd; "
                "onzekere productiegegevens blokkeren NC1/STEP/IFC-uitvoer."
            ),
            wraplength=1320,
            justify="left",
        )
        self.pdf_status.grid(row=2, column=0, sticky="ew", pady=(0, 6))

        split = ttk.Panedwindow(root, orient="horizontal")
        split.grid(row=3, column=0, sticky="nsew")
        fields_frame = ttk.LabelFrame(split, text="Herkende velden, provenance en confidence", padding=6)
        questions_frame = ttk.LabelFrame(split, text="Waarschuwingen en controlevragen", padding=6)
        split.add(fields_frame, weight=3)
        split.add(questions_frame, weight=2)
        fields_frame.columnconfigure(0, weight=1)
        fields_frame.rowconfigure(0, weight=1)
        columns = ("field", "value", "confidence", "method", "status", "page")
        self.pdf_field_tree = ttk.Treeview(fields_frame, columns=columns, show="headings")
        headings = {
            "field": "Veld",
            "value": "Waarde",
            "confidence": "Confidence",
            "method": "Methode",
            "status": "Status",
            "page": "Pagina",
        }
        widths = {"field": 180, "value": 260, "confidence": 90, "method": 180, "status": 90, "page": 60}
        for column in columns:
            self.pdf_field_tree.heading(column, text=headings[column])
            self.pdf_field_tree.column(column, width=widths[column], anchor="w" if column in {"field", "value", "method"} else "center")
        self.pdf_field_tree.grid(row=0, column=0, sticky="nsew")
        fy = ttk.Scrollbar(fields_frame, orient="vertical", command=self.pdf_field_tree.yview)
        fy.grid(row=0, column=1, sticky="ns")
        fx = ttk.Scrollbar(fields_frame, orient="horizontal", command=self.pdf_field_tree.xview)
        fx.grid(row=1, column=0, sticky="ew")
        self.pdf_field_tree.configure(yscrollcommand=fy.set, xscrollcommand=fx.set)

        questions_frame.columnconfigure(0, weight=1)
        questions_frame.rowconfigure(0, weight=1)
        self.pdf_questions = tk.Text(questions_frame, wrap="word", state="disabled")
        self.pdf_questions.grid(row=0, column=0, sticky="nsew")
        qy = ttk.Scrollbar(questions_frame, orient="vertical", command=self.pdf_questions.yview)
        qy.grid(row=0, column=1, sticky="ns")
        self.pdf_questions.configure(yscrollcommand=qy.set)

    # ---------------------------------------------------------- PDF review
    def _choose_pdf_review_source(self) -> None:
        name = filedialog.askopenfilename(
            title="Selecteer technische PDF",
            filetypes=[("PDF", "*.pdf"), ("Alle bestanden", "*.*")],
        )
        if not name:
            return
        self.pdf_review_source.set(name)
        self.pdf_analysis_result = None
        self._show_pdf_analysis(None)
        self.pdf_status.configure(text=f"Geselecteerd: {Path(name).name}. Start de analyse.")

    def _choose_pdf_review_file(self) -> None:
        name = filedialog.askopenfilename(
            title="Selecteer review-JSON",
            filetypes=[("JSON", "*.json"), ("Alle bestanden", "*.*")],
        )
        if name:
            self.pdf_review_file.set(name)

    def _pdf_ai_settings(self, *, audit_directory: Path | None = None) -> AISettings:
        provider = self.pdf_ai_provider.get().strip().lower() or "none"
        allow_cloud = bool(self.pdf_allow_cloud.get())
        if provider == "openai" and not allow_cloud:
            raise PermissionError(
                "OpenAI is geselecteerd, maar expliciete toestemming voor cloudverwerking ontbreekt."
            )
        audit_log = ""
        if audit_directory is not None:
            audit_directory.mkdir(parents=True, exist_ok=True)
            audit_log = str(audit_directory / "ai_audit.jsonl")
        return AISettings(provider=provider, allow_cloud=allow_cloud, audit_log=audit_log)

    def _start_pdf_analysis(self) -> None:
        source = Path(self.pdf_review_source.get()).expanduser()
        if not source.is_file() or source.suffix.lower() != ".pdf":
            messagebox.showwarning("Geen PDF", "Selecteer eerst een bestaand PDF-bestand.")
            return
        try:
            settings = self._pdf_ai_settings(
                audit_directory=Path(self.output_directory.get()).expanduser()
            )
        except PermissionError as exc:
            messagebox.showwarning("Cloud-AI niet toegestaan", str(exc))
            return
        self.pdf_analyze_button.configure(state="disabled")
        self.pdf_status.configure(text=f"Analyse bezig: {source.name} …")
        self.pdf_analysis_result = None
        self._show_pdf_analysis(None)
        worker = threading.Thread(
            target=self._pdf_analysis_worker,
            args=(source, settings),
            daemon=True,
        )
        worker.start()
        self.after(100, self._poll_pdf_events)

    def _pdf_analysis_worker(self, source: Path, settings: AISettings) -> None:
        try:
            analysis = analyze_pdf(source, ai_settings=settings)
            self.pdf_events.put(("analysis_done", analysis))
        except Exception as exc:
            self.pdf_events.put(("error", "PDF-analyse", str(exc)))

    def _poll_pdf_events(self) -> None:
        processed = False
        try:
            while True:
                event = self.pdf_events.get_nowait()
                processed = True
                kind = event[0]
                if kind == "analysis_done":
                    self.pdf_analyze_button.configure(state="normal")
                    self.pdf_analysis_result = event[1]
                    self._show_pdf_analysis(self.pdf_analysis_result)
                elif kind == "review_done":
                    self.pdf_analyze_button.configure(state="normal")
                    conversion_result, analysis = event[1], event[2]
                    self.pdf_analysis_result = analysis
                    self.pdf_review_source.set(str(conversion_result.primary_output or ""))
                    self._show_pdf_analysis(analysis)
                    messagebox.showinfo(
                        "Trusted PDF gemaakt",
                        "Reviewed Trusted Converter PDF opgeslagen:\n"
                        + str(conversion_result.primary_output),
                    )
                elif kind == "error":
                    self.pdf_analyze_button.configure(state="normal")
                    self.pdf_status.configure(text=f"{event[1]} mislukt")
                    messagebox.showerror(event[1], event[2])
        except queue.Empty:
            pass
        if self.pdf_analyze_button.instate(["disabled"]) or not processed:
            self.after(100, self._poll_pdf_events)

    @staticmethod
    def _display_value(value: object) -> str:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    def _show_pdf_analysis(self, analysis) -> None:
        for item in self.pdf_field_tree.get_children():
            self.pdf_field_tree.delete(item)
        self.pdf_questions.configure(state="normal")
        self.pdf_questions.delete("1.0", "end")
        if analysis is None:
            self.pdf_questions.configure(state="disabled")
            return

        part = analysis.part
        for field_path, evidence in sorted(part.field_evidence.items()):
            self.pdf_field_tree.insert(
                "",
                "end",
                values=(
                    field_path,
                    self._display_value(evidence.value),
                    f"{float(evidence.confidence):.0%}",
                    evidence.method,
                    evidence.status,
                    evidence.page or "",
                ),
            )
        if not part.field_evidence:
            for field_path, value in sorted(analysis.detected_fields.items()):
                self.pdf_field_tree.insert(
                    "",
                    "end",
                    values=(field_path, self._display_value(value), "", "detected", "", ""),
                )

        lines = [
            f"Modus: {analysis.mode}",
            "Productie-export: " + ("TOEGESTAAN" if analysis.production_export_allowed else "GEBLOKKEERD"),
            f"Onderdeel: {part.part_id or part.header.position_number or '-'}",
            f"Profiel: {part.header.profile or '-'} | materiaal: {part.header.material or '-'} | aantal: {part.header.quantity}",
            "",
        ]
        if part.validation.errors or analysis.errors:
            lines.append("FOUTEN")
            lines.extend(f"- {item}" for item in dict.fromkeys(part.validation.errors + analysis.errors))
            lines.append("")
        warnings = list(dict.fromkeys(part.validation.warnings + analysis.warnings + part.warnings))
        if warnings:
            lines.append("WAARSCHUWINGEN")
            lines.extend(f"- {item}" for item in warnings)
            lines.append("")
        questions = part.validation.unresolved_questions
        if questions:
            lines.append("CONTROLEVRAGEN")
            for question in questions:
                lines.append(
                    f"- [{question.status}/{question.severity}] {question.question_id}: {question.prompt}"
                )
                if question.alternatives:
                    lines.append("  Alternatieven: " + " | ".join(map(str, question.alternatives)))
                if question.reason:
                    lines.append("  Reden: " + question.reason)
            lines.append("")
        if analysis.ai is not None:
            lines.append(
                f"AI-advies: {analysis.ai.provider} / {analysis.ai.model}; "
                f"{len(analysis.ai.fields)} veldsuggestie(s), {len(analysis.ai.questions)} vraag/vragen."
            )
        self.pdf_questions.insert("1.0", "\n".join(lines))
        self.pdf_questions.configure(state="disabled")
        self.pdf_status.configure(
            text=(
                f"{Path(analysis.source).name}: {analysis.mode}; "
                f"{len(analysis.pages)} pagina('s); "
                + ("productie-export toegestaan" if analysis.production_export_allowed else "review vereist")
            )
        )

    def _save_pdf_analysis(self) -> None:
        if self.pdf_analysis_result is None:
            messagebox.showwarning("Geen analyse", "Analyseer eerst een PDF-bestand.")
            return
        source = Path(self.pdf_analysis_result.source)
        name = filedialog.asksaveasfilename(
            title="Analyse-JSON opslaan",
            initialfile=f"{source.stem}.analysis.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not name:
            return
        try:
            target = write_analysis_report(self.pdf_analysis_result, name)
            messagebox.showinfo("Analyse opgeslagen", f"Analyse opgeslagen:\n{target}")
        except Exception as exc:
            messagebox.showerror("Analyse opslaan", str(exc))

    def _review_pdf_to_trusted(self) -> None:
        source = Path(self.pdf_review_source.get()).expanduser()
        review = Path(self.pdf_review_file.get()).expanduser()
        if not source.is_file() or source.suffix.lower() != ".pdf":
            messagebox.showwarning("Geen PDF", "Selecteer eerst de externe bron-PDF.")
            return
        if not review.is_file() or review.suffix.lower() != ".json":
            messagebox.showwarning("Geen review", "Selecteer eerst een bestaand review-JSON-bestand.")
            return
        default = Path(self.output_directory.get()).expanduser() / f"{source.stem}_reviewed_trusted.pdf"
        name = filedialog.asksaveasfilename(
            title="Reviewed Trusted PDF opslaan",
            initialdir=str(default.parent),
            initialfile=default.name,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not name:
            return
        try:
            settings = self._pdf_ai_settings(audit_directory=Path(name).parent)
        except PermissionError as exc:
            messagebox.showwarning("Cloud-AI niet toegestaan", str(exc))
            return
        self.pdf_analyze_button.configure(state="disabled")
        self.pdf_status.configure(text=f"Review toepassen en Trusted PDF maken: {source.name} …")

        def worker() -> None:
            try:
                result = review_external_pdf(
                    source,
                    review,
                    name,
                    ai_settings=settings,
                )
                analysis = analyze_pdf(result.primary_output)
                self.pdf_events.put(("review_done", result, analysis))
            except Exception as exc:
                self.pdf_events.put(("error", "PDF-review", str(exc)))

        threading.Thread(target=worker, daemon=True).start()
        self.after(100, self._poll_pdf_events)

    def _build_preview_tab(self) -> None:
        top = ttk.Frame(self.preview_tab)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Conversieresultaat:").pack(side="left")
        self.comparison_choice = tk.StringVar()
        self.comparison_combo = ttk.Combobox(top, textvariable=self.comparison_choice, state="readonly", width=96)
        self.comparison_combo.pack(side="left", padx=8, fill="x", expand=True)
        self.comparison_combo.bind("<<ComboboxSelected>>", lambda _event: self._load_selected_comparison())
        ttk.Button(top, text="Laden", command=self._load_selected_comparison).pack(side="left")
        ttk.Button(top, text="Bron openen", command=lambda: self._open_comparison_path(False)).pack(side="left", padx=(8, 2))
        ttk.Button(top, text="Resultaat openen", command=lambda: self._open_comparison_path(True)).pack(side="left", padx=2)
        self.viewer = ComparisonViewer(self.preview_tab)
        self.viewer.pack(fill="both", expand=True)

    def _build_database_tab(self) -> None:
        header = ttk.Frame(self.database_tab)
        header.pack(fill="x", pady=(0, 8))
        self.database_path_label = ttk.Label(header, text=f"Database: {self.profile_database.path}")
        self.database_path_label.pack(side="left", fill="x", expand=True)
        ttk.Button(header, text="NC1-bestanden importeren", command=self._import_profile_files).pack(side="left", padx=2)
        ttk.Button(header, text="NC1-map importeren", command=self._import_profile_folder).pack(side="left", padx=2)
        ttk.Button(header, text="Herlaad", command=self._reload_profile_database).pack(side="left", padx=2)
        ttk.Button(header, text="Map openen", command=lambda: self._open_path(self.profile_database.path.parent)).pack(side="left", padx=2)

        filters = ttk.LabelFrame(self.database_tab, text="Zoeken en filteren", padding=8)
        filters.pack(fill="x", pady=(0, 8))
        filters.columnconfigure(1, weight=1)
        ttk.Label(filters, text="Zoektekst:").grid(row=0, column=0, sticky="w")
        search_entry = ttk.Entry(filters, textvariable=self.profile_search)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(6, 14))
        search_entry.bind("<KeyRelease>", lambda _event: self._refresh_profile_tree())
        ttk.Label(filters, text="Familie:").grid(row=0, column=2, sticky="w")
        self.family_combo = ttk.Combobox(filters, textvariable=self.profile_family, state="readonly", width=18)
        self.family_combo.grid(row=0, column=3, sticky="w", padx=(6, 14))
        self.family_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_profile_tree())
        ttk.Label(filters, text="Type:").grid(row=0, column=4, sticky="w")
        self.type_combo = ttk.Combobox(filters, textvariable=self.profile_type, state="readonly", width=10)
        self.type_combo.grid(row=0, column=5, sticky="w", padx=(6, 14))
        self.type_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_profile_tree())
        ttk.Button(filters, text="Reset", command=self._reset_profile_filters).grid(row=0, column=6, sticky="e")
        self.profile_count = ttk.Label(filters, text="")
        self.profile_count.grid(row=0, column=7, sticky="e", padx=(16, 0))

        columns = (
            "designation", "type", "family", "dim1", "dim2", "dim3", "dim4", "radius", "area", "mass", "standard", "status", "source",
        )
        tree_frame = ttk.Frame(self.database_tab)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.profile_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        headings = {
            "designation": "Profiel", "type": "Type", "family": "Serie", "dim1": "Maat 1", "dim2": "Maat 2",
            "dim3": "Maat 3", "dim4": "Maat 4", "radius": "Radius", "area": "mm²", "mass": "kg/m",
            "standard": "Norm", "status": "Status", "source": "Bron",
        }
        widths = {"designation": 140, "type": 55, "family": 90, "standard": 150, "status": 140, "source": 220}
        for column in columns:
            self.profile_tree.heading(column, text=headings[column])
            self.profile_tree.column(column, width=widths.get(column, 76), anchor="w" if column in {"designation", "family", "standard", "status", "source"} else "center")
        self.profile_tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.profile_tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.profile_tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.profile_tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self._refresh_profile_tree()

    def _build_quantities_tab(self) -> None:
        root = self.quantities_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)
        root.rowconfigure(5, weight=1)

        top = ttk.LabelFrame(root, text="IFC / STEP uploaden en hoeveelheden bepalen", padding=10)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Button(top, text="IFC/STEP-bestanden kiezen", command=self._choose_quantity_files).pack(side="left")
        ttk.Button(top, text="Map kiezen", command=self._choose_quantity_folder).pack(side="left", padx=6)
        ttk.Button(top, text="Lijst leegmaken", command=self._clear_quantity_files).pack(side="left")
        ttk.Label(top, text="Fallback materiaal:").pack(side="left", padx=(22, 6))
        self.quantity_material_combo = ttk.Combobox(top, textvariable=self.quantity_material, width=16)
        self.quantity_material_combo.pack(side="left")
        ttk.Button(top, text="Hoeveelheden bepalen", command=self._start_quantities).pack(side="left", padx=14)
        ttk.Button(top, text="Excel exporteren", command=self._export_quantities_excel).pack(side="left", padx=2)

        note = ttk.Label(
            root,
            text="Excel bevat tabbladen voor Hoeveelheden, Samenvatting, Materialen, Profielen, Eigenschappen en Waarschuwingen. Materiaal- en profielgegevens blijven controleplichtig voor productie.",
            wraplength=1300,
            justify="left",
        )
        note.grid(row=1, column=0, sticky="ew", pady=(8, 6))

        qfile_frame = ttk.LabelFrame(root, text="Bronbestanden", padding=6)
        qfile_frame.grid(row=2, column=0, sticky="nsew")
        qfile_frame.columnconfigure(0, weight=1)
        qfile_frame.rowconfigure(0, weight=1)
        self.quantity_file_list = tk.Listbox(qfile_frame, height=5, selectmode="extended")
        self.quantity_file_list.grid(row=0, column=0, sticky="nsew")
        qscroll = ttk.Scrollbar(qfile_frame, orient="vertical", command=self.quantity_file_list.yview)
        qscroll.grid(row=0, column=1, sticky="ns")
        self.quantity_file_list.configure(yscrollcommand=qscroll.set)

        summary = ttk.Frame(root)
        summary.grid(row=3, column=0, sticky="ew", pady=(8, 6))
        self.quantity_status = ttk.Label(summary, text="Nog geen analyse uitgevoerd.")
        self.quantity_status.pack(side="left")
        self.quantity_progress = ttk.Progressbar(summary, mode="indeterminate", length=220)
        self.quantity_progress.pack(side="right")

        columns = (
            "source", "type", "name", "class", "profile", "material", "qty", "length", "width", "height", "volume", "mass", "warnings",
        )
        result_frame = ttk.LabelFrame(root, text="Hoeveelheden", padding=6)
        result_frame.grid(row=5, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.quantity_tree = ttk.Treeview(result_frame, columns=columns, show="headings")
        headings = {
            "source": "Bron", "type": "Soort", "name": "Naam", "class": "Klasse", "profile": "Profiel",
            "material": "Materiaal", "qty": "Aantal", "length": "Lengte", "width": "Breedte", "height": "Hoogte/dikte",
            "volume": "Volume mm³", "mass": "Massa kg", "warnings": "Waarschuwingen",
        }
        widths = {"source": 220, "name": 200, "warnings": 360, "volume": 120, "mass": 100}
        for column in columns:
            self.quantity_tree.heading(column, text=headings[column])
            self.quantity_tree.column(column, width=widths.get(column, 95), anchor="w" if column in {"source", "name", "warnings"} else "center")
        self.quantity_tree.grid(row=0, column=0, sticky="nsew")
        qy = ttk.Scrollbar(result_frame, orient="vertical", command=self.quantity_tree.yview)
        qy.grid(row=0, column=1, sticky="ns")
        qx = ttk.Scrollbar(result_frame, orient="horizontal", command=self.quantity_tree.xview)
        qx.grid(row=1, column=0, sticky="ew")
        self.quantity_tree.configure(yscrollcommand=qy.set, xscrollcommand=qx.set)

    # ------------------------------------------------------------ conversion
    def _direction_changed(self) -> None:
        selected = self.direction.get()
        if selected != self._active_direction and self.files:
            self.files.clear()
            self._refresh_file_list()
            self._write_log("Invoerlijst leeggemaakt na wijzigen van de conversierichting.")
        self._active_direction = selected
        notes = {
            "nc1-to-step": "NC1/DSTV → STEP ondersteunt platen, I/HEA-profielen, U/C-profielen, hoeklijnen, RHS/SHS-kokers, massief rond en ronde buizen.",
            "step-to-nc1": "STEP → NC1 herkent platen en standaardprofielen via de profielendatabase. De NC1-uitvoer wordt opnieuw opgebouwd en verplicht geometrisch gecontroleerd.",
            "ifc-to-dstv": "IFC → DSTV maakt per veilig converteerbaar IFC-element een apart NC1-bestand. De strikte veiligheidscontrole kan niet worden uitgeschakeld.",
            "dstv-to-ifc": "DSTV/NC1 → IFC schrijft zichtbare IFC-geometrie plus een gehashte canonieke converterpayload voor betrouwbare terugconversie.",
            "ifc-to-step": "IFC → STEP gebruikt bij converter-eigen IFC eerst de geverifieerde analytische payload; externe IFC volgt de veilige geometrische fallback.",
            "step-to-ifc": "STEP → IFC schrijft een semantisch element met materiaal, broneigenschappen, quantities en exacte converterpayload wanneer classificatie veilig is.",
            "pdf-to-nc1": "Alleen een geldige Trusted Converter PDF of een volledig menselijk gereviewde externe tekening mag naar productie-NC1. Onzekere velden blokkeren de uitvoer.",
            "pdf-to-step": "PDF → STEP loopt via het canonieke model en een verplicht gevalideerde NC1/analytische solid-route. AI levert uitsluitend adviessuggesties.",
            "pdf-to-ifc": "PDF → IFC loopt via het gevalideerde canonieke model en bewaart de exacte productiedata in de IFC-payload.",
            "nc1-to-pdf": "NC1 → PDF maakt een vectoriële technische tekening met titelblok, stukregel, maatvoering en embedded exact model.",
            "step-to-pdf": "STEP → PDF classificeert het profiel/plaatdeel veilig en maakt een Trusted Converter PDF. Niet-classificeerbare STEP blijft concept.",
            "ifc-to-pdf": "IFC → PDF maakt één PDF per onderdeel wanneer het IFC meerdere elementen bevat; converterpayload heeft prioriteit.",
        }
        self.note.configure(text=notes.get(selected, ""))
        if selected in {"step-to-nc1", "ifc-to-dstv", "step-to-pdf"}:
            self.profile_combo.configure(state="readonly")
        else:
            self.profile_choice.set("Automatisch")
            self.profile_combo.configure(state="disabled")
        self.strict_validation.set(True)

    def _extensions(self) -> tuple[set[str], list[tuple[str, str]]]:
        mapping = {
            "nc1-to-step": ({".nc", ".nc1"}, [("DSTV/NC1", "*.nc *.nc1"), ("Alle bestanden", "*.*")]),
            "step-to-nc1": ({".step", ".stp"}, [("STEP", "*.step *.stp"), ("Alle bestanden", "*.*")]),
            "ifc-to-dstv": ({".ifc"}, [("IFC", "*.ifc"), ("Alle bestanden", "*.*")]),
            "dstv-to-ifc": ({".nc", ".nc1"}, [("DSTV/NC1", "*.nc *.nc1"), ("Alle bestanden", "*.*")]),
            "ifc-to-step": ({".ifc"}, [("IFC", "*.ifc"), ("Alle bestanden", "*.*")]),
            "step-to-ifc": ({".step", ".stp"}, [("STEP", "*.step *.stp"), ("Alle bestanden", "*.*")]),
            "pdf-to-nc1": ({".pdf"}, [("PDF", "*.pdf"), ("Alle bestanden", "*.*")]),
            "pdf-to-step": ({".pdf"}, [("PDF", "*.pdf"), ("Alle bestanden", "*.*")]),
            "pdf-to-ifc": ({".pdf"}, [("PDF", "*.pdf"), ("Alle bestanden", "*.*")]),
            "nc1-to-pdf": ({".nc", ".nc1"}, [("DSTV/NC1", "*.nc *.nc1"), ("Alle bestanden", "*.*")]),
            "step-to-pdf": ({".step", ".stp"}, [("STEP", "*.step *.stp"), ("Alle bestanden", "*.*")]),
            "ifc-to-pdf": ({".ifc"}, [("IFC", "*.ifc"), ("Alle bestanden", "*.*")]),
        }
        return mapping[self.direction.get()]

    def _choose_files(self) -> None:
        _, filters = self._extensions()
        names = filedialog.askopenfilenames(title="Selecteer invoerbestanden", filetypes=filters)
        self._add_files(Path(name) for name in names)

    def _open_initial_files(self, paths) -> None:
        """Open bestanden die via Windows-dubbelklik/contextmenu zijn meegegeven."""

        existing = [Path(path).resolve() for path in paths if Path(path).is_file()]
        if not existing:
            return
        first = existing[0]
        suffix = first.suffix.lower()
        if suffix == ".pdf":
            self.pdf_review_source.set(str(first))
            self.notebook.select(self.pdf_tab)
            self.pdf_status.configure(text=f"Geopend via Windows: {first.name}. Analyse wordt gestart.")
            self._write_log(f"PDF geopend via bestandskoppeling: {first}")
            self.after(150, self._start_pdf_analysis)
            return

        direction_by_suffix = {
            ".nc": "nc1-to-step",
            ".nc1": "nc1-to-step",
            ".step": "step-to-nc1",
            ".stp": "step-to-nc1",
            ".ifc": "ifc-to-dstv",
        }
        direction = direction_by_suffix.get(suffix)
        if direction is None:
            messagebox.showwarning(
                "Niet-ondersteund bestand",
                f"Het bestandstype {suffix or '(zonder extensie)'} kan niet automatisch worden geopend.",
            )
            return
        self.direction.set(direction)
        self._direction_changed()
        matching = [path for path in existing if path.suffix.lower() in self._extensions()[0]]
        self._add_files(matching)
        self.notebook.select(self.converter_tab)
        self._write_log(
            f"{len(matching)} bestand(en) geopend via Windows-bestandskoppeling; "
            f"voorgestelde route: {DIRECTION_LABELS[direction]}."
        )

    def _choose_input_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecteer invoermap")
        if not folder:
            return
        extensions, _ = self._extensions()
        self._add_files(path for path in sorted(Path(folder).iterdir()) if path.suffix.lower() in extensions)

    def _add_files(self, paths) -> None:
        known = {path.resolve() for path in self.files}
        extensions, _ = self._extensions()
        for path in paths:
            path = Path(path)
            if path.is_file() and path.suffix.lower() in extensions and path.resolve() not in known:
                self.files.append(path)
                known.add(path.resolve())
        self.files.sort(key=lambda item: item.name.lower())
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        self.file_list.delete(0, "end")
        for path in self.files:
            self.file_list.insert("end", str(path))
        self.status.configure(text=f"{len(self.files)} bestand(en)")

    def _clear_files(self) -> None:
        self.files.clear()
        self._refresh_file_list()

    def _remove_selected(self) -> None:
        selected = set(self.file_list.curselection())
        self.files = [path for index, path in enumerate(self.files) if index not in selected]
        self._refresh_file_list()

    def _choose_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecteer uitvoermap", initialdir=self.output_directory.get())
        if folder:
            self.output_directory.set(folder)

    def _write_log(self, text: str) -> None:
        if not hasattr(self, "log"):
            return
        self.log.configure(state="normal")
        self.log.insert("end", text.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _start_conversion(self) -> None:
        if not self.files:
            messagebox.showwarning("Geen bestanden", "Selecteer eerst één of meer invoerbestanden.")
            return
        output = Path(self.output_directory.get()).expanduser()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Uitvoermap", f"De uitvoermap kan niet worden aangemaakt:\n{exc}")
            return
        self.convert_button.configure(state="disabled")
        self.progress.configure(maximum=len(self.files), value=0)
        self.status.configure(text="Bezig…")
        self._write_log("— Nieuwe conversieronde —")
        preferred = self.profile_choice.get()
        if preferred == "Automatisch":
            preferred = ""
        provider = self.pdf_ai_provider.get().strip().lower() or "none"
        allow_cloud = bool(self.pdf_allow_cloud.get())
        if self.direction.get().startswith("pdf-to") and provider == "openai" and not allow_cloud:
            messagebox.showwarning(
                "Cloud-AI niet toegestaan",
                "OpenAI is geselecteerd, maar expliciete toestemming voor deze PDF-analyse ontbreekt.",
            )
            self.convert_button.configure(state="normal")
            self.status.configure(text="Gereed")
            return
        if not self.direction.get().startswith("pdf-to"):
            provider = "none"
            allow_cloud = False
        ai_settings = AISettings(
            provider=provider,
            allow_cloud=allow_cloud,
            audit_log=str(output / "ai_audit.jsonl"),
        )
        self._conversion_comparison_start = len(self.comparisons)
        worker = threading.Thread(
            target=self._worker,
            args=(
                list(self.files), output, self.direction.get(), self.material.get().strip() or "S355JR",
                self.order_number.get().strip() or "STEP", preferred, float(self.profile_tolerance.get()), ai_settings,
            ),
            daemon=True,
        )
        worker.start()
        self.after(100, self._poll_events)

    def _worker(
        self,
        files: list[Path],
        output: Path,
        direction: str,
        material: str,
        order_number: str,
        preferred_profile: str,
        tolerance: float,
        ai_settings: AISettings,
    ) -> None:
        failures = 0
        for index, source in enumerate(files, start=1):
            try:
                outputs, warnings, failed_items = self._convert_one(
                    source, output, direction, material, order_number, preferred_profile, tolerance, ai_settings
                )
                if failed_items:
                    failures += len(failed_items)
                self.events.put(("log", f"OK   {source.name} → {len(outputs)} uitvoerbestand(en)"))
                for out in outputs:
                    self.events.put(("log", f"     UITVOER: {out.name}"))
                for warning in warnings:
                    self.events.put(("log", f"     WAARSCHUWING: {warning}"))
                for fail in failed_items:
                    self.events.put(("log", f"     NIET GECONVERTEERD: {fail}"))
                for out in outputs:
                    if source.suffix.lower() in MODEL_SUFFIXES and out.suffix.lower() in MODEL_SUFFIXES:
                        self.events.put(("converted", source, out, direction, DIRECTION_LABELS.get(direction, direction)))
            except ExternalPDFExportBlocked as exc:
                failures += 1
                self.events.put(("log", f"REVIEW VEREIST {source.name}: {exc}"))
            except Exception as exc:
                failures += 1
                self.events.put(("log", f"FOUT {source.name}: {exc}"))
            self.events.put(("progress", index))
        self.events.put(("done", len(files), failures, str(output)))

    def _convert_one(
        self,
        source: Path,
        output: Path,
        direction: str,
        material: str,
        order_number: str,
        preferred_profile: str,
        tolerance: float,
        ai_settings: AISettings,
    ) -> tuple[list[Path], list[str], list[str]]:
        if direction == "nc1-to-step":
            target = output / f"{source.stem}.step"
            part = convert_nc1_to_step(source, target)
            return [target], list(part.warnings), []
        if direction == "step-to-nc1":
            target = output / f"{source.stem}.nc1"
            result = step_to_nc1(
                source,
                target,
                material=material,
                order_number=order_number,
                profile_database=self.profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance,
                strict_validation=True,
            )
            warnings = [
                f"{result.profile_designation}; confidence {result.confidence:.0%}; volumeverschil {result.volume_delta_percent:+.6f}%"
            ] + list(result.warnings)
            return [target], warnings, []
        if direction == "ifc-to-dstv":
            result = ifc_to_dstv(
                source,
                output / source.stem,
                material=material,
                order_number=order_number,
                profile_database=self.profile_database,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance,
                strict_validation=True,
            )
            return result.outputs, result.warnings, result.failures
        if direction == "dstv-to-ifc":
            result = dstv_to_ifc(source, output / f"{source.stem}.ifc", material=material)
            return result.outputs, result.warnings, result.failures
        if direction == "ifc-to-step":
            result = ifc_to_step(source, output / f"{source.stem}.step")
            return result.outputs, result.warnings, result.failures
        if direction == "step-to-ifc":
            result = step_to_ifc(source, output / f"{source.stem}.ifc", material=material)
            return result.outputs, result.warnings, result.failures
        if direction == "pdf-to-nc1":
            result = pdf_to_nc1(source, output / f"{source.stem}.nc1", ai_settings=ai_settings)
            return result.outputs, result.warnings, result.failures
        if direction == "pdf-to-step":
            result = pdf_to_step(source, output / f"{source.stem}.step", ai_settings=ai_settings)
            return result.outputs, result.warnings, result.failures
        if direction == "pdf-to-ifc":
            result = pdf_to_ifc(
                source,
                output / f"{source.stem}.ifc",
                material=material,
                ai_settings=ai_settings,
            )
            return result.outputs, result.warnings, result.failures
        if direction == "nc1-to-pdf":
            result = nc1_to_pdf(source, output / f"{source.stem}.pdf")
            return result.outputs, result.warnings, result.failures
        if direction == "step-to-pdf":
            result = step_to_pdf(
                source,
                output / f"{source.stem}.pdf",
                material=material,
                preferred_profile=preferred_profile,
                tolerance_mm=tolerance,
            )
            return result.outputs, result.warnings, result.failures
        if direction == "ifc-to-pdf":
            result = ifc_to_pdf(source, output / source.stem, material=material)
            return result.outputs, result.warnings, result.failures
        return convert_file(
            source,
            output,
            direction,
            material=material,
            order_number=order_number,
            profile_database=self.profile_database,
            preferred_profile=preferred_profile,
            tolerance_mm=tolerance,
            strict_validation=True,
        )

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "log":
                    self._write_log(event[1])
                elif kind == "progress":
                    self.progress.configure(value=event[1])
                elif kind == "converted":
                    self._add_comparison(ComparisonRecord(event[1], event[2], event[3], event[4]))
                elif kind == "done":
                    total, failed, output = event[1:]
                    self.convert_button.configure(state="normal")
                    self.status.configure(text=f"Klaar: {total} bronbestand(en), {failed} fout/niet-converteerbaar")
                    self._write_log(f"Klaar. Uitvoer: {output}")
                    if self.auto_preview.get() and len(self.comparisons) > getattr(self, "_conversion_comparison_start", 0):
                        self.comparison_combo.current(len(self.comparisons) - 1)
                        self.after(50, self._load_selected_comparison)
                        self.notebook.select(self.preview_tab)
                    if failed:
                        messagebox.showwarning("Conversie voltooid", f"Voltooid met {failed} fout/niet-converteerbare item(s). Zie het log.")
                    else:
                        messagebox.showinfo("Conversie voltooid", "Conversie voltooid zonder fouten.")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    # -------------------------------------------------------------- preview
    def _add_comparison(self, record: ComparisonRecord) -> None:
        self.comparisons.append(record)
        self.comparison_combo.configure(values=[item.label for item in self.comparisons])
        self.comparison_combo.current(len(self.comparisons) - 1)

    def _selected_comparison(self) -> ComparisonRecord | None:
        index = self.comparison_combo.current()
        return self.comparisons[index] if 0 <= index < len(self.comparisons) else None

    def _load_selected_comparison(self) -> None:
        record = self._selected_comparison()
        if record is None:
            messagebox.showinfo("Geen vergelijking", "Voer eerst een conversie uit.")
            return
        self.status.configure(text="3D-vergelijking laden…")
        self.update_idletasks()
        try:
            self.viewer.show_paths(
                record.source,
                record.target,
                source_title=f"Origineel bestand\n{record.source.name}",
                target_title=f"Geconverteerd bestand\n{record.target.name}",
            )
            self.status.configure(text="Vergelijking geladen")
        except Exception as exc:
            self.status.configure(text="Vergelijking mislukt")
            messagebox.showerror("3D-vergelijking", f"De modellen konden niet worden weergegeven:\n{exc}")

    def _open_comparison_path(self, target: bool) -> None:
        record = self._selected_comparison()
        if record is not None:
            self._open_path(record.target if target else record.source)

    @staticmethod
    def _open_path(path: Path) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif os.name == "posix":
                subprocess.Popen(["xdg-open", str(path)])
            else:
                raise OSError("Bestand openen wordt op dit platform niet ondersteund")
        except Exception as exc:
            messagebox.showerror("Openen", f"Kan niet openen:\n{path}\n\n{exc}")

    # ------------------------------------------------------------ profiles
    def _refresh_profile_controls(self) -> None:
        names = ["Automatisch"] + [profile.designation for profile in sorted(self.profile_database.profiles, key=lambda p: p.designation)]
        if hasattr(self, "profile_combo"):
            self.profile_combo.configure(values=names)
        if self.profile_choice.get() not in names:
            self.profile_choice.set("Automatisch")
        families = ["Alle"] + self.profile_database.families()
        types = ["Alle"] + self.profile_database.types()
        if hasattr(self, "family_combo"):
            self.family_combo.configure(values=families)
            if self.profile_family.get() not in families:
                self.profile_family.set("Alle")
        if hasattr(self, "type_combo"):
            self.type_combo.configure(values=types)
            if self.profile_type.get() not in types:
                self.profile_type.set("Alle")

    def _refresh_material_controls(self) -> None:
        codes = self.material_database.codes
        if hasattr(self, "material_combo"):
            self.material_combo.configure(values=codes)
        if hasattr(self, "quantity_material_combo"):
            self.quantity_material_combo.configure(values=codes)

    def _reset_profile_filters(self) -> None:
        self.profile_search.set("")
        self.profile_family.set("Alle")
        self.profile_type.set("Alle")
        self._refresh_profile_tree()

    def _refresh_profile_tree(self) -> None:
        if not hasattr(self, "profile_tree"):
            return
        rows = self.profile_database.filtered(text=self.profile_search.get(), family=self.profile_family.get(), profile_type=self.profile_type.get())
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        for profile in rows:
            self.profile_tree.insert(
                "",
                "end",
                values=(
                    profile.designation,
                    profile.profile_type,
                    profile.family,
                    f"{profile.dim1:g}",
                    f"{profile.dim2:g}",
                    f"{profile.dim3:g}",
                    f"{profile.dim4:g}",
                    f"{profile.radius:g}",
                    f"{profile.area_mm2:.1f}",
                    f"{profile.mass_kg_m:.3f}",
                    profile.standard,
                    profile.catalogue_status,
                    profile.source,
                ),
            )
        if hasattr(self, "profile_count"):
            self.profile_count.configure(text=f"{len(rows)} / {len(self.profile_database.profiles)} profielen")

    def _reload_profile_database(self) -> None:
        try:
            self.profile_database.load()
            self._refresh_profile_controls()
            self._refresh_profile_tree()
        except Exception as exc:
            messagebox.showerror("Profielendatabase", str(exc))

    def _import_profile_files(self) -> None:
        names = filedialog.askopenfilenames(title="Selecteer NC1-profielen", filetypes=[("DSTV/NC1", "*.nc *.nc1"), ("Alle bestanden", "*.*")])
        if names:
            self._import_profiles([Path(name) for name in names])

    def _import_profile_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecteer map met NC1-profielen")
        if folder:
            self._import_profiles([Path(folder)])

    def _import_profiles(self, paths: list[Path]) -> None:
        try:
            count, errors = import_profiles_from_nc1(paths, self.profile_database)
            self._refresh_profile_controls()
            self._refresh_profile_tree()
            message = f"{count} profieldefinitie(s) toegevoegd of bijgewerkt."
            if errors:
                message += "\n\nNiet gelezen:\n" + "\n".join(errors[:12])
            messagebox.showinfo("Profielen geïmporteerd", message)
        except Exception as exc:
            messagebox.showerror("Profielen importeren", str(exc))

    # ------------------------------------------------------------ quantities
    def _quantity_filters(self) -> list[tuple[str, str]]:
        return [("IFC / STEP", "*.ifc *.step *.stp"), ("IFC", "*.ifc"), ("STEP", "*.step *.stp"), ("Alle bestanden", "*.*")]

    def _choose_quantity_files(self) -> None:
        names = filedialog.askopenfilenames(title="Selecteer IFC/STEP-bestanden", filetypes=self._quantity_filters())
        self._add_quantity_files(Path(name) for name in names)

    def _choose_quantity_folder(self) -> None:
        folder = filedialog.askdirectory(title="Selecteer map met IFC/STEP-bestanden")
        if folder:
            self._add_quantity_files(path for path in sorted(Path(folder).iterdir()) if path.suffix.lower() in {".ifc", ".step", ".stp"})

    def _add_quantity_files(self, paths) -> None:
        known = {path.resolve() for path in self.quantity_files}
        for path in paths:
            path = Path(path)
            if path.is_file() and path.suffix.lower() in {".ifc", ".step", ".stp"} and path.resolve() not in known:
                self.quantity_files.append(path)
                known.add(path.resolve())
        self.quantity_files.sort(key=lambda p: p.name.lower())
        self._refresh_quantity_file_list()

    def _refresh_quantity_file_list(self) -> None:
        self.quantity_file_list.delete(0, "end")
        for path in self.quantity_files:
            self.quantity_file_list.insert("end", str(path))
        self.quantity_status.configure(text=f"{len(self.quantity_files)} IFC/STEP-bestand(en) geselecteerd.")

    def _clear_quantity_files(self) -> None:
        self.quantity_files.clear()
        self.quantity_analysis = None
        self._refresh_quantity_file_list()
        self._refresh_quantity_tree(None)

    def _start_quantities(self) -> None:
        if not self.quantity_files:
            messagebox.showwarning("Geen bestanden", "Selecteer eerst één of meer IFC/STEP-bestanden.")
            return
        self.quantity_progress.start(12)
        self.quantity_status.configure(text="Hoeveelheden bepalen…")
        worker = threading.Thread(target=self._quantity_worker, args=(list(self.quantity_files), self.quantity_material.get().strip() or "S355JR"), daemon=True)
        worker.start()
        self.after(100, self._poll_quantity_events)

    def _quantity_worker(self, files: list[Path], material: str) -> None:
        try:
            analysis = analyze_files(files, fallback_material=material, material_database=self.material_database, profile_database=self.profile_database)
            self.quantity_events.put(("done", analysis))
        except Exception as exc:
            self.quantity_events.put(("error", str(exc)))

    def _poll_quantity_events(self) -> None:
        try:
            event = self.quantity_events.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_quantity_events)
            return
        self.quantity_progress.stop()
        if event[0] == "done":
            self.quantity_analysis = event[1]
            self._refresh_quantity_tree(self.quantity_analysis)
            self.quantity_status.configure(
                text=(
                    f"Gereed: {len(self.quantity_analysis.items)} regels, "
                    f"totaal {self.quantity_analysis.total_mass_kg:.3f} kg, "
                    f"waarschuwingen {len(self.quantity_analysis.warnings)}."
                )
            )
        else:
            self.quantity_status.configure(text="Hoeveelheden mislukt")
            messagebox.showerror("Hoeveelheden", event[1])

    def _refresh_quantity_tree(self, analysis: QuantityAnalysis | None) -> None:
        for item in self.quantity_tree.get_children():
            self.quantity_tree.delete(item)
        if analysis is None:
            return
        for item in analysis.items:
            self.quantity_tree.insert(
                "",
                "end",
                values=(
                    item.source_file,
                    item.source_type,
                    item.name,
                    item.object_type,
                    item.profile,
                    item.material_code,
                    item.quantity,
                    f"{item.length_mm:.2f}",
                    f"{item.width_mm:.2f}",
                    f"{item.height_mm:.2f}",
                    f"{item.volume_mm3:.1f}",
                    f"{item.mass_kg:.3f}",
                    " | ".join(item.warnings),
                ),
            )

    def _export_quantities_excel(self) -> None:
        if self.quantity_analysis is None:
            if not self.quantity_files:
                messagebox.showwarning("Geen analyse", "Bepaal eerst de hoeveelheden of selecteer IFC/STEP-bestanden.")
                return
            try:
                self.quantity_analysis = analyze_files(
                    self.quantity_files,
                    fallback_material=self.quantity_material.get().strip() or "S355JR",
                    material_database=self.material_database,
                    profile_database=self.profile_database,
                )
                self._refresh_quantity_tree(self.quantity_analysis)
            except Exception as exc:
                messagebox.showerror("Hoeveelheden", str(exc))
                return
        default = Path(self.output_directory.get()).expanduser() / "IFC_STEP_hoeveelheden.xlsx"
        name = filedialog.asksaveasfilename(
            title="Excel export opslaan",
            initialfile=default.name,
            initialdir=str(default.parent),
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not name:
            return
        try:
            path = export_excel(name, self.quantity_analysis, material_database=self.material_database, profile_database=self.profile_database)
            self.quantity_status.configure(text=f"Excel opgeslagen: {path}")
            messagebox.showinfo("Excel export", f"Excel-bestand opgeslagen:\n{path}")
        except Exception as exc:
            messagebox.showerror("Excel export", str(exc))


if __name__ == "__main__":
    ConverterApp(sys.argv[1:]).mainloop()
