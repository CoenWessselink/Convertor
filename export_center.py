from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cws_convertor.product import APP_NAME
from cws_convertor.production_export import ExportRequest, ProductionExportEngine, load_project_snapshot
from cws_convertor.production_export.readiness import ReadinessGate
from cws_convertor.production_export.utils import get_value, iter_values


class ExportCenterTab(ttk.Frame):
    """Veilige, visueel rustige exportcentrale voor CWS Convertor."""

    BG = "#F4F6F8"
    CARD = "#FFFFFF"
    TEXT = "#16202A"
    MUTED = "#617182"
    ACCENT = "#2457D6"
    GOOD = "#177245"
    WARN = "#B76E00"
    BAD = "#B42318"

    def __init__(self, master, *, product_version: str = "0.8.0-alpha"):
        self._configure_styles(master)
        super().__init__(master, padding=18, style="CWS.Background.TFrame")
        self.product_version = product_version
        self.project_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status = tk.StringVar(value="Kies een .cwscproj-project om de productiegate te beoordelen.")
        self.metrics = {
            "parts": tk.StringVar(value="—"),
            "ready": tk.StringVar(value="—"),
            "blocked": tk.StringVar(value="—"),
            "packages": tk.StringVar(value="—"),
        }
        self.formats = {
            "json": tk.BooleanVar(value=True),
            "review_pdf": tk.BooleanVar(value=True),
            "nc1": tk.BooleanVar(value=True),
            "step": tk.BooleanVar(value=True),
            "ifc": tk.BooleanVar(value=True),
            "production_pdf": tk.BooleanVar(value=True),
        }
        self._loaded_project = None
        self._build()

    @classmethod
    def _configure_styles(cls, master) -> None:
        style = ttk.Style(master)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("CWS.Background.TFrame", background=cls.BG)
        style.configure("CWS.Card.TFrame", background=cls.CARD, relief="flat")
        style.configure("CWS.Title.TLabel", background=cls.BG, foreground=cls.TEXT, font=("Segoe UI Semibold", 20))
        style.configure("CWS.Subtitle.TLabel", background=cls.BG, foreground=cls.MUTED, font=("Segoe UI", 10))
        style.configure("CWS.Logo.TLabel", background=cls.ACCENT, foreground="#FFFFFF", font=("Segoe UI Black", 13), padding=(10, 7))
        style.configure("CWS.CardTitle.TLabel", background=cls.CARD, foreground=cls.MUTED, font=("Segoe UI Semibold", 9))
        style.configure("CWS.CardValue.TLabel", background=cls.CARD, foreground=cls.TEXT, font=("Segoe UI Semibold", 18))
        style.configure("CWS.CardHint.TLabel", background=cls.CARD, foreground=cls.MUTED, font=("Segoe UI", 8))
        style.configure("CWS.Accent.TButton", font=("Segoe UI Semibold", 10), padding=(18, 10), background=cls.ACCENT, foreground="#FFFFFF")
        style.map("CWS.Accent.TButton", background=[("active", "#1847BE"), ("disabled", "#9AA8C8")])
        style.configure("CWS.Secondary.TButton", font=("Segoe UI", 9), padding=(10, 7))
        style.configure("CWS.Treeview", rowheight=29, font=("Segoe UI", 9), background="#FFFFFF", fieldbackground="#FFFFFF", foreground=cls.TEXT)
        style.configure("CWS.Treeview.Heading", font=("Segoe UI Semibold", 9), background="#E9EEF4", foreground=cls.TEXT, relief="flat")
        style.map("CWS.Treeview", background=[("selected", "#DCE7FF")], foreground=[("selected", cls.TEXT)])
        style.configure("CWS.TLabelframe", background=cls.CARD, bordercolor="#D8E0E8", relief="solid")
        style.configure("CWS.TLabelframe.Label", background=cls.CARD, foreground=cls.TEXT, font=("Segoe UI Semibold", 10))
        style.configure("CWS.TCheckbutton", background=cls.CARD, foreground=cls.TEXT, font=("Segoe UI", 9))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        header = ttk.Frame(self, style="CWS.Background.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(2, weight=1)
        ttk.Label(header, text="CWS", style="CWS.Logo.TLabel").grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        ttk.Label(header, text="Productiepakketten", style="CWS.Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(
            header,
            text="Per onderdeel en per merk — gecontroleerd, traceerbaar en reproduceerbaar",
            style="CWS.Subtitle.TLabel",
        ).grid(row=1, column=1, sticky="w", pady=(1, 0))
        ttk.Label(header, text=f"v{self.product_version}", style="CWS.Subtitle.TLabel").grid(row=0, column=3, sticky="e")

        metrics = ttk.Frame(self, style="CWS.Background.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(16, 12))
        for col in range(4):
            metrics.columnconfigure(col, weight=1, uniform="metric")
        cards = [
            ("Onderdelen", "parts", "in huidige selectie"),
            ("Productie-ready", "ready", "alle gates geslaagd"),
            ("Geblokkeerd", "blocked", "actie of bronbewijs nodig"),
            ("Merkpakketten", "packages", "assembly-/merkstructuur"),
        ]
        for col, (title, key, hint) in enumerate(cards):
            card = ttk.Frame(metrics, padding=(14, 11), style="CWS.Card.TFrame")
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 5, 0 if col == 3 else 5))
            ttk.Label(card, text=title.upper(), style="CWS.CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=self.metrics[key], style="CWS.CardValue.TLabel").pack(anchor="w", pady=(2, 0))
            ttk.Label(card, text=hint, style="CWS.CardHint.TLabel").pack(anchor="w")

        source = ttk.LabelFrame(self, text="1  Project en uitvoermap", padding=12, style="CWS.TLabelframe")
        source.grid(row=2, column=0, sticky="ew")
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text="Project", background=self.CARD).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(source, textvariable=self.project_path).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(source, text="Openen…", style="CWS.Secondary.TButton", command=self._choose_project).grid(row=0, column=2, padx=(8, 0), pady=4)
        ttk.Label(source, text="Uitvoer", background=self.CARD).grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(source, textvariable=self.output_path).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(source, text="Kiezen…", style="CWS.Secondary.TButton", command=self._choose_output).grid(row=1, column=2, padx=(8, 0), pady=4)

        formats = ttk.LabelFrame(self, text="2  Uitvoerformaten", padding=12, style="CWS.TLabelframe")
        formats.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        labels = {
            "json": "Onderdeeldata · JSON",
            "review_pdf": "Review-PDF",
            "nc1": "NC1 / DSTV",
            "step": "STEP",
            "ifc": "IFC",
            "production_pdf": "Productietekening · PDF",
        }
        for index, (key, label) in enumerate(labels.items()):
            ttk.Checkbutton(formats, text=label, variable=self.formats[key], style="CWS.TCheckbutton").grid(
                row=index // 3, column=index % 3, sticky="w", padx=(0, 34), pady=4
            )

        gate = ttk.LabelFrame(self, text="3  Productiegate en uitvoerstatus", padding=10, style="CWS.TLabelframe")
        gate.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        gate.rowconfigure(0, weight=1)
        gate.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(gate, columns=("status", "aantal"), show="tree headings", height=9, style="CWS.Treeview")
        self.tree.heading("#0", text="Controle")
        self.tree.heading("status", text="Status")
        self.tree.heading("aantal", text="Aantal")
        self.tree.column("#0", width=560)
        self.tree.column("status", width=170, anchor="center")
        self.tree.column("aantal", width=100, anchor="e")
        self.tree.tag_configure("good", foreground=self.GOOD)
        self.tree.tag_configure("warning", foreground=self.WARN)
        self.tree.tag_configure("blocked", foreground=self.BAD)
        self.tree.tag_configure("info", foreground=self.ACCENT)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(gate, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self, style="CWS.Background.TFrame")
        footer.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status, style="CWS.Subtitle.TLabel", wraplength=820).grid(row=0, column=0, sticky="w")
        self.export_button = ttk.Button(footer, text="Pakket bouwen", style="CWS.Accent.TButton", command=self._start_export)
        self.export_button.grid(row=0, column=1, padx=(12, 0))

    def _choose_project(self) -> None:
        value = filedialog.askopenfilename(filetypes=[("CWS-project", "*.cwscproj"), ("Alle bestanden", "*.*")])
        if value:
            self.project_path.set(value)
            if not self.output_path.get():
                self.output_path.set(str(Path(value).parent / "CWS_Exports"))
            self._preflight()

    def _choose_output(self) -> None:
        value = filedialog.askdirectory()
        if value:
            self.output_path.set(value)

    def _preflight(self) -> None:
        try:
            loaded = load_project_snapshot(self.project_path.get())
            self._loaded_project = loaded
            parts = iter_values(get_value(loaded.snapshot, "parts", "project_parts", default=[]))
            assemblies = iter_values(get_value(loaded.snapshot, "assemblies", "project_assemblies", default=[]))
            gate = ReadinessGate()
            requested = [key for key, variable in self.formats.items() if variable.get()]
            ready = 0
            blocked = 0
            for part in parts:
                assessment = gate.assess(part, requested)
                if assessment.production_ready:
                    ready += 1
                else:
                    blocked += 1
            self.metrics["parts"].set(f"{len(parts):,}".replace(",", "."))
            self.metrics["ready"].set(f"{ready:,}".replace(",", "."))
            self.metrics["blocked"].set(f"{blocked:,}".replace(",", "."))
            self.metrics["packages"].set(f"{len(assemblies):,}".replace(",", "."))
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.tree.insert("", "end", text="Projectmodel, bronhash en opslagintegriteit", values=("Gevalideerd", len(parts)), tags=("good",))
            self.tree.insert("", "end", text="Productieformaten worden afzonderlijk per onderdeel beoordeeld", values=("Strenge modus", ready), tags=("info",))
            self.tree.insert("", "end", text="Onderdelen met onopgeloste productiegate", values=("Geblokkeerd", blocked), tags=("blocked" if blocked else "good",))
            self.tree.insert("", "end", text="Geblokkeerde formaten krijgen geen leeg of geschat bestand", values=("Veilig", ""), tags=("good",))
            self.tree.insert("", "end", text="Review-PDF bevat altijd zichtbare vrijgavestatus", values=("Traceerbaar", ""), tags=("good",))
            self.status.set(f"{len(parts)} onderdelen beoordeeld. Productie-export blijft per formaat afhankelijk van exact bronbewijs.")
        except Exception as exc:
            self._loaded_project = None
            self.status.set(str(exc))

    def _start_export(self) -> None:
        if not self.project_path.get() or not self.output_path.get():
            messagebox.showerror(APP_NAME, "Kies eerst een project en uitvoermap.")
            return
        selected = [key for key, variable in self.formats.items() if variable.get()]
        if not selected:
            messagebox.showerror(APP_NAME, "Selecteer minimaal één formaat.")
            return
        self.export_button.configure(state="disabled")
        self.status.set("Productiegate controleren en pakket atomisch opbouwen…")
        threading.Thread(target=self._run_export, args=(selected,), daemon=True).start()

    def _run_export(self, selected: list[str]) -> None:
        try:
            loaded = self._loaded_project or load_project_snapshot(self.project_path.get())
            request = ExportRequest(output_dir=Path(self.output_path.get()), formats=selected)
            manifest, root, zip_path = ProductionExportEngine(product_version=self.product_version).export_project(
                loaded.snapshot, request
            )
            summary = json.dumps(manifest.summary, ensure_ascii=False, indent=2)
            self.after(0, lambda: messagebox.showinfo(
                APP_NAME,
                f"Pakket gebouwd:\n{zip_path or root}\n\n{summary}",
            ))
            self.after(0, lambda: self.status.set("Pakket gereed. Controleer manifest en blokkades vóór vrijgave."))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror(APP_NAME, str(exc)))
            self.after(0, lambda: self.status.set(f"Export mislukt: {exc}"))
        finally:
            self.after(0, lambda: self.export_button.configure(state="normal"))


def main() -> None:
    root = tk.Tk()
    root.title(f"{APP_NAME} - Productiepakketten")
    root.geometry("1120x800")
    root.minsize(900, 650)
    ExportCenterTab(root).pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
