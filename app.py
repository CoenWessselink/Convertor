from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import math
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
from ai_support import LocalSemanticProvider, OpenAIResponsesProvider
from pdf_support import (
    PDFProductionBlockedError,
    analyze_external_pdf,
    ifc_to_pdf,
    inspect_pdf,
    nc1_to_pdf,
    pdf_to_ifc,
    pdf_to_nc1,
    pdf_to_step,
    render_pdf_pages,
    step_to_pdf,
)
from material_database import MaterialDatabase
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
    "pdf-to-nc1": "PDF → NC1 / DSTV",
    "pdf-to-step": "PDF → STEP",
    "pdf-to-ifc": "PDF → IFC",
    "nc1-to-pdf": "NC1 / DSTV → PDF",
    "step-to-pdf": "STEP → PDF",
    "ifc-to-pdf": "IFC → PDF",
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
    def __init__(self) -> None:
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
        self.quantity_files: list[Path] = []
        self.quantity_analysis: QuantityAnalysis | None = None
        self.files: list[Path] = []
        self.comparisons: list[ComparisonRecord] = []
        self.events: queue.Queue[tuple] = queue.Queue()
        self.quantity_events: queue.Queue[tuple] = queue.Queue()
        self.pdf_ai_events: queue.Queue[tuple] = queue.Queue()
        self.pdf_ai_file = tk.StringVar(value="")
        self.pdf_ai_use_cloud = tk.BooleanVar(value=False)
        self.pdf_ai_model = tk.StringVar(value="")
        self.pdf_ai_status = tk.StringVar(value="Selecteer een technische PDF.")
        self._pdf_preview_image: tk.PhotoImage | None = None
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

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.converter_tab = ttk.Frame(self.notebook, padding=12)
        self.preview_tab = ttk.Frame(self.notebook, padding=8)
        self.database_tab = ttk.Frame(self.notebook, padding=12)
        self.quantities_tab = ttk.Frame(self.notebook, padding=12)
        self.pdf_ai_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.converter_tab, text="Converter")
        self.notebook.add(self.preview_tab, text="Visuele vergelijking")
        self.notebook.add(self.pdf_ai_tab, text="PDF / AI controle")
        self.notebook.add(self.database_tab, text="Profielendatabase")
        self.notebook.add(self.quantities_tab, text="Hoeveelheden & Excel")

        self._build_converter_tab()
        self._build_preview_tab()
        self._build_pdf_ai_tab()
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
        self.strict_validation_check = ttk.Checkbutton(
            self.advanced_settings,
            text="Strikte veiligheidscontrole is verplicht; onbetrouwbare productie-uitvoer wordt geweigerd",
            variable=self.strict_validation,
            state="disabled",
        )
        self.strict_validation_check.grid(row=1, column=2, columnspan=4, sticky="w", pady=(8, 0))

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

    def _build_pdf_ai_tab(self) -> None:
        root = self.pdf_ai_tab
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        controls = ttk.LabelFrame(root, text="Technische PDF analyseren", padding=10)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)
        ttk.Label(controls, text="PDF-bestand:").grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.pdf_ai_file).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(controls, text="Kiezen", command=self._choose_pdf_ai_file).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(controls, text="Trusted PDF controleren", command=self._inspect_pdf_ai).grid(row=0, column=3, padx=(0, 6))
        self.pdf_ai_analyze_button = ttk.Button(controls, text="Analyseren", command=self._start_pdf_ai_analysis)
        self.pdf_ai_analyze_button.grid(row=0, column=4)

        privacy = ttk.Frame(controls)
        privacy.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(10, 0))
        ttk.Checkbutton(
            privacy,
            text="Cloud-AI gebruiken - ik geef expliciet toestemming om deze PDF extern te verwerken",
            variable=self.pdf_ai_use_cloud,
        ).pack(side="left")
        ttk.Label(privacy, text="Model:").pack(side="left", padx=(18, 4))
        ttk.Entry(privacy, textvariable=self.pdf_ai_model, width=26).pack(side="left")
        ttk.Label(
            privacy,
            text="API-sleutel via OPENAI_API_KEY; lokale analyse blijft standaard.",
        ).pack(side="left", padx=(10, 0))

        info = ttk.Label(
            root,
            text=(
                "AI interpreteert alleen tekst, titelblok, aanzichten, conflicten en controlevragen. "
                "Exacte contouren, gatposities, maatwaarden en NC1/STEP/IFC-export worden deterministisch "
                "berekend. Externe PDF's blijven geblokkeerd voor productie totdat alle kritische vragen zijn bevestigd."
            ),
            wraplength=1380,
            justify="left",
        )
        info.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        source_frame = ttk.LabelFrame(root, text="Bron-PDF", padding=6)
        source_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 4))
        source_frame.columnconfigure(0, weight=1)
        source_frame.rowconfigure(0, weight=1)
        self.pdf_preview_label = ttk.Label(source_frame, text="Nog geen PDF geselecteerd", anchor="center")
        self.pdf_preview_label.grid(row=0, column=0, sticky="nsew")

        result_frame = ttk.LabelFrame(root, text="Herkende gegevens, confidence en blokkades", padding=6)
        result_frame.grid(row=2, column=1, sticky="nsew", padx=(4, 0))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.pdf_ai_result = tk.Text(result_frame, wrap="word", state="disabled")
        self.pdf_ai_result.grid(row=0, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.pdf_ai_result.yview)
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.pdf_ai_result.configure(yscrollcommand=result_scroll.set)

        ttk.Label(root, textvariable=self.pdf_ai_status, anchor="w").grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

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

    # ------------------------------------------------------------ PDF / AI
    def _choose_pdf_ai_file(self) -> None:
        name = filedialog.askopenfilename(
            title="Selecteer technische PDF",
            filetypes=[("PDF", "*.pdf"), ("Alle bestanden", "*.*")],
        )
        if not name:
            return
        self.pdf_ai_file.set(name)
        self._load_pdf_ai_preview(Path(name))
        self.pdf_ai_status.set("PDF geladen. Kies lokale analyse of geef expliciet toestemming voor cloud-AI.")

    def _load_pdf_ai_preview(self, path: Path) -> None:
        try:
            images = render_pdf_pages(path, dpi=100, max_pages=1)
            if not images:
                raise ValueError("PDF bevat geen pagina's")
            encoded = base64.b64encode(images[0]).decode("ascii")
            image = tk.PhotoImage(data=encoded)
            factor = max(1, math.ceil(max(image.width() / 650, image.height() / 680)))
            if factor > 1:
                image = image.subsample(factor, factor)
            self._pdf_preview_image = image
            self.pdf_preview_label.configure(image=image, text="")
        except Exception as exc:
            self._pdf_preview_image = None
            self.pdf_preview_label.configure(image="", text=f"Preview kon niet worden geladen:\n{exc}")
    def _set_pdf_ai_text(self, text: str) -> None:
        self.pdf_ai_result.configure(state="normal")
        self.pdf_ai_result.delete("1.0", "end")
        self.pdf_ai_result.insert("1.0", text)
        self.pdf_ai_result.configure(state="disabled")

    def _inspect_pdf_ai(self) -> None:
        path = Path(self.pdf_ai_file.get()).expanduser()
        if not path.is_file():
            messagebox.showwarning("PDF", "Selecteer eerst een PDF-bestand.")
            return
        try:
            inspection = inspect_pdf(path)
            lines = [
                f"Classificatie: {inspection.classification}",
                f"Trusted exact: {'ja' if inspection.trusted_exact else 'nee'}",
            ]
            for key, value in sorted(inspection.details.items()):
                lines.append(f"{key}: {value}")
            if inspection.errors:
                lines.append("\nFouten:")
                lines.extend(f"- {item}" for item in inspection.errors)
            if inspection.warnings:
                lines.append("\nWaarschuwingen:")
                lines.extend(f"- {item}" for item in inspection.warnings)
            self._set_pdf_ai_text("\n".join(lines))
            self.pdf_ai_status.set(
                "Exacte embedded data gevalideerd." if inspection.trusted_exact else "Geen geldige exacte Trusted PDF-payload."
            )
        except Exception as exc:
            messagebox.showerror("Trusted PDF controleren", str(exc))

    def _start_pdf_ai_analysis(self) -> None:
        path = Path(self.pdf_ai_file.get()).expanduser()
        if not path.is_file():
            messagebox.showwarning("PDF", "Selecteer eerst een PDF-bestand.")
            return
        use_cloud = bool(self.pdf_ai_use_cloud.get())
        model = self.pdf_ai_model.get().strip()
        if use_cloud and not model:
            messagebox.showwarning("Cloud-AI", "Vul eerst een expliciet model in.")
            return
        self.pdf_ai_analyze_button.configure(state="disabled")
        self.pdf_ai_status.set("PDF wordt lokaal voorbereid en geanalyseerd...")
        thread = threading.Thread(
            target=self._pdf_ai_worker,
            args=(path, use_cloud, model),
            daemon=True,
        )
        thread.start()
        self.after(100, self._poll_pdf_ai_events)

    def _pdf_ai_worker(self, path: Path, use_cloud: bool, model: str) -> None:
        try:
            provider = (
                OpenAIResponsesProvider(model=model)
                if use_cloud
                else LocalSemanticProvider()
            )
            analysis = analyze_external_pdf(
                path,
                ai_provider=provider,
                cloud_consent=use_cloud,
            )
            self.pdf_ai_events.put(("result", analysis))
        except Exception as exc:
            self.pdf_ai_events.put(("error", str(exc)))

    def _format_pdf_ai_analysis(self, analysis) -> str:
        part = analysis.part
        lines = [
            f"Bestand: {analysis.source.name}",
            f"Onderdeel: {part.part_id}",
            f"Importmethode: {part.import_method}",
            f"Productie-export: {'VRIJGEGEVEN' if part.validation.production_export_allowed else 'GEBLOKKEERD'}",
            "",
            "Herkende velden:",
        ]
        for name, item in sorted(part.field_values.items()):
            status = "automatisch" if item.confidence >= 0.95 else "controle"
            lines.append(
                f"- {name}: {item.value} | confidence {item.confidence:.0%} | {status} | {item.method}"
            )
            if item.evidence:
                lines.append(f"    bron: {item.evidence}")
        if part.validation.errors:
            lines.extend(["", "Blokkerende fouten:"])
            lines.extend(f"- {item}" for item in part.validation.errors)
        open_questions = [
            item for item in part.validation.unresolved_questions
            if item.status.lower() not in {"resolved", "answered", "dismissed"}
        ]
        if open_questions:
            lines.extend(["", "Controlevragen:"])
            for item in open_questions:
                label = "BLOKKEREND" if item.blocking else "waarschuwing"
                lines.append(f"- [{label}] {item.message}")
        if analysis.ai is not None:
            lines.extend(["", f"AI-provider: {analysis.ai.provider}"])
            if analysis.ai.model:
                lines.append(f"Model: {analysis.ai.model}")
            for suggestion in analysis.ai.layout_suggestions:
                lines.append(f"- Layoutvoorstel: {suggestion}")
        if analysis.warnings:
            lines.extend(["", "Waarschuwingen:"])
            lines.extend(f"- {item}" for item in analysis.warnings)
        return "\n".join(lines)

    def _poll_pdf_ai_events(self) -> None:
        try:
            while True:
                event = self.pdf_ai_events.get_nowait()
                if event[0] == "result":
                    analysis = event[1]
                    self._set_pdf_ai_text(self._format_pdf_ai_analysis(analysis))
                    self.pdf_ai_status.set(
                        "Analyse klaar - productie geblokkeerd totdat kritische geometrie is bevestigd."
                        if not analysis.part.validation.production_export_allowed
                        else "Analyse klaar en vrijgegeven."
                    )
                    self.pdf_ai_analyze_button.configure(state="normal")
                    return
                if event[0] == "error":
                    self.pdf_ai_analyze_button.configure(state="normal")
                    self.pdf_ai_status.set("Analyse mislukt.")
                    messagebox.showerror("PDF / AI analyse", event[1])
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_pdf_ai_events)

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
            "step-to-nc1": "STEP → NC1 herkent platen en standaardprofielen via de profielendatabase. De NC1-uitvoer wordt opnieuw opgebouwd en volumetrisch gecontroleerd.",
            "ifc-to-dstv": "IFC → DSTV maakt per converteerbaar IFC-element een apart NC1-bestand en schrijft daarnaast een manifest met gelukte en geweigerde objecten.",
            "dstv-to-ifc": "DSTV/NC1 → IFC bouwt eerst een lokaal STEP-solid op en schrijft daarna een IFC-element met materiaal- en broneigenschappen.",
            "ifc-to-step": "IFC → STEP probeert eerst geverifieerde payload of analytische fitting; faceted fallback blijft onder strenge controle.",
            "step-to-ifc": "STEP → IFC schrijft zichtbare IFC-geometrie en een exacte canonieke converterpayload.",
            "pdf-to-nc1": "PDF → NC1 is exact voor een ongewijzigde Trusted Converter PDF. Externe PDF's worden eerst geanalyseerd en blijven geblokkeerd totdat kritische geometrie is bevestigd.",
            "pdf-to-step": "PDF → STEP is exact voor een ongewijzigde Trusted Converter PDF. AI mag geen STEP-geometrie genereren.",
            "pdf-to-ifc": "PDF → IFC is exact voor een ongewijzigde Trusted Converter PDF. Externe PDF's vereisen review en vrijgave.",
            "nc1-to-pdf": "NC1/DSTV → PDF maakt een vectoriële werktekening met maatvoering, stukregel, titelblok en gehashte exacte modeldata.",
            "step-to-pdf": "STEP → PDF maakt een vectoriële werktuigbouwkundige onderdeeltekening en sluit de exacte STEP/productiedata in.",
            "ifc-to-pdf": "IFC → PDF maakt per onderdeel een vectoriële technische PDF; converterpayload krijgt voorrang.",
        }
        self.note.configure(text=notes.get(selected, ""))
        if selected in {"step-to-nc1", "ifc-to-dstv"}:
            self.profile_combo.configure(state="readonly")
            self.strict_validation.set(self.strict_validation.get())
        else:
            self.profile_choice.set("Automatisch")
        if selected in {"nc1-to-step", "ifc-to-step"}:
            # Material/order/profile are less relevant but harmless; keep visible for clarity only when needed.
            pass

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
        worker = threading.Thread(
            target=self._worker,
            args=(
                list(self.files), output, self.direction.get(), self.material.get().strip() or "S355JR",
                self.order_number.get().strip() or "STEP", preferred, float(self.profile_tolerance.get()), True,
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
        strict_validation: bool,
    ) -> None:
        failures = 0
        for index, source in enumerate(files, start=1):
            try:
                outputs, warnings, failed_items = self._convert_one(source, output, direction, material, order_number, preferred_profile, tolerance, strict_validation)
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
                    if out.suffix.lower() in MODEL_SUFFIXES:
                        self.events.put(("converted", source, out, direction, DIRECTION_LABELS.get(direction, direction)))
            except PDFProductionBlockedError as exc:
                failures += 1
                self.events.put(("log", f"GEBLOKKEERD {source.name}: {exc}"))
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
        strict_validation: bool,
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
                strict_validation=strict_validation,
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
                strict_validation=strict_validation,
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
        if direction == "nc1-to-pdf":
            result = nc1_to_pdf(source, output / f"{source.stem}.pdf")
            return result.outputs, result.warnings, []
        if direction == "step-to-pdf":
            result = step_to_pdf(source, output / f"{source.stem}.pdf", material=material)
            return result.outputs, result.warnings, []
        if direction == "ifc-to-pdf":
            result = ifc_to_pdf(source, output / source.stem)
            return result.outputs, result.warnings, []
        if direction == "pdf-to-nc1":
            result = pdf_to_nc1(source, output / f"{source.stem}.nc1")
            return result.outputs, result.warnings, []
        if direction == "pdf-to-step":
            result = pdf_to_step(source, output / f"{source.stem}.step")
            return result.outputs, result.warnings, []
        if direction == "pdf-to-ifc":
            result = pdf_to_ifc(source, output / f"{source.stem}.ifc")
            return result.outputs, result.warnings, []
        return convert_file(
            source,
            output,
            direction,
            material=material,
            order_number=order_number,
            profile_database=self.profile_database,
            preferred_profile=preferred_profile,
            tolerance_mm=tolerance,
            strict_validation=strict_validation,
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
                    if self.auto_preview.get() and self.comparisons:
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


def launch_app() -> None:
    app = ConverterApp()
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser()
        if candidate.is_file():
            suffix = candidate.suffix.lower()
            direction_by_suffix = {
                ".nc": "nc1-to-step",
                ".nc1": "nc1-to-step",
                ".step": "step-to-nc1",
                ".stp": "step-to-nc1",
                ".ifc": "ifc-to-step",
            }
            if suffix == ".pdf":
                app.pdf_ai_file.set(str(candidate))
                app._load_pdf_ai_preview(candidate)
                app.notebook.select(app.pdf_ai_tab)
                app.pdf_ai_status.set("PDF via Windows-bestandsassociatie geopend; kies controleren of analyseren.")
            elif suffix in direction_by_suffix:
                app.direction.set(direction_by_suffix[suffix])
                app._direction_changed()
                app._add_files([candidate])
                app.output_directory.set(str(candidate.parent / "Converter_Output"))
    app.mainloop()


if __name__ == "__main__":
    launch_app()
