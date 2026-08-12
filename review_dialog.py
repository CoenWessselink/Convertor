"""Interactive, human-in-the-loop review dialog for external technical PDFs."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from pdf_support import PDFAnalysisResult, apply_review
from review_workflow import (
    ReviewField,
    build_review_payload,
    canonical_path,
    coerce_review_value,
    collect_review_fields,
    value_to_text,
)


class PDFReviewDialog(tk.Toplevel):
    """Modal source/model review with explicit corrections and confirmations."""

    def __init__(self, parent: tk.Misc, analysis: PDFAnalysisResult) -> None:
        super().__init__(parent)
        self.analysis = analysis
        self.result: dict[str, Any] | None = None
        self.reviewed_analysis: PDFAnalysisResult | None = None
        self.fields = collect_review_fields(analysis.part)
        self.pending_values: dict[str, Any] = {}
        self.confirmed: set[str] = set()
        self.answers: dict[str, Any] = {}
        self._field_by_iid: dict[str, ReviewField] = {}
        self._question_by_iid: dict[str, Any] = {}
        self._source_photo: tk.PhotoImage | None = None
        self._source_scale = 1.0
        self._source_page = 0
        self._page_count = max(1, len(analysis.pages))
        self._selected_model_path = ""

        self.title(f"Interactieve PDF-review - {Path(analysis.source).name}")
        self.geometry("1540x920")
        self.minsize(1180, 720)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        reviewer_default = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        self.reviewer = tk.StringVar(value=reviewer_default)
        self.field_value = tk.StringVar(value="")
        self.field_action = tk.StringVar(value="Selecteer een veld.")
        self.question_answer = tk.StringVar(value="")
        self.review_status = tk.StringVar(value="Nog niet gevalideerd")
        self.page_label = tk.StringVar(value="")

        self._build_ui()
        self._populate_fields()
        self._populate_questions()
        self.after_idle(self._initial_render)
        self.grab_set()
        self.focus_set()

    # --------------------------------------------------------------- layout
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Panedwindow(self, orient="horizontal")
        main.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        preview = ttk.Panedwindow(main, orient="vertical")
        controls = ttk.Frame(main, padding=(8, 0, 0, 0))
        main.add(preview, weight=3)
        main.add(controls, weight=4)

        source_frame = ttk.LabelFrame(preview, text="Bron-PDF", padding=5)
        model_frame = ttk.LabelFrame(preview, text="Deterministische 2D-reconstructie", padding=5)
        preview.add(source_frame, weight=3)
        preview.add(model_frame, weight=2)

        source_toolbar = ttk.Frame(source_frame)
        source_toolbar.pack(fill="x", pady=(0, 4))
        ttk.Button(source_toolbar, text="<", width=3, command=lambda: self._change_page(-1)).pack(side="left")
        ttk.Label(source_toolbar, textvariable=self.page_label).pack(side="left", padx=8)
        ttk.Button(source_toolbar, text=">", width=3, command=lambda: self._change_page(1)).pack(side="left")
        ttk.Button(source_toolbar, text="Bron openen", command=self._open_source).pack(side="right")

        source_holder = ttk.Frame(source_frame)
        source_holder.pack(fill="both", expand=True)
        source_holder.columnconfigure(0, weight=1)
        source_holder.rowconfigure(0, weight=1)
        self.source_canvas = tk.Canvas(source_holder, background="#f0f0f0", highlightthickness=0)
        self.source_canvas.grid(row=0, column=0, sticky="nsew")
        sy = ttk.Scrollbar(source_holder, orient="vertical", command=self.source_canvas.yview)
        sx = ttk.Scrollbar(source_holder, orient="horizontal", command=self.source_canvas.xview)
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        self.source_canvas.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        self.model_canvas = tk.Canvas(model_frame, background="white", highlightthickness=0)
        self.model_canvas.pack(fill="both", expand=True)
        self.model_canvas.bind("<Configure>", lambda _event: self._draw_model())

        controls.columnconfigure(0, weight=1)
        controls.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(controls)
        notebook.grid(row=0, column=0, sticky="nsew")
        fields_tab = ttk.Frame(notebook, padding=6)
        questions_tab = ttk.Frame(notebook, padding=6)
        notebook.add(fields_tab, text="Velden en features")
        notebook.add(questions_tab, text="Controlevragen")
        self._build_fields_tab(fields_tab)
        self._build_questions_tab(questions_tab)

        review_meta = ttk.LabelFrame(controls, text="Beoordeling", padding=8)
        review_meta.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        review_meta.columnconfigure(1, weight=1)
        ttk.Label(review_meta, text="Beoordeeld door:").grid(row=0, column=0, sticky="w")
        ttk.Entry(review_meta, textvariable=self.reviewer).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(review_meta, text="Opmerking:").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        self.comment = tk.Text(review_meta, height=3, wrap="word")
        self.comment.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        footer = ttk.Frame(controls)
        footer.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(footer, textvariable=self.review_status, wraplength=700).pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Review-JSON opslaan", command=self._save_json).pack(side="right", padx=3)
        ttk.Button(footer, text="Valideren en gebruiken", command=self._validate_and_accept).pack(side="right", padx=3)
        ttk.Button(footer, text="Annuleren", command=self._cancel).pack(side="right", padx=3)

    def _build_fields_tab(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        columns = ("category", "label", "value", "confidence", "status", "action")
        self.field_tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
        headings = {
            "category": "Categorie",
            "label": "Veld / feature",
            "value": "Huidige waarde",
            "confidence": "Confidence",
            "status": "Bronstatus",
            "action": "Reviewactie",
        }
        widths = {"category": 130, "label": 230, "value": 240, "confidence": 85, "status": 95, "action": 150}
        for column in columns:
            self.field_tree.heading(column, text=headings[column])
            self.field_tree.column(column, width=widths[column], anchor="w" if column not in {"confidence"} else "center")
        self.field_tree.grid(row=0, column=0, sticky="nsew")
        fy = ttk.Scrollbar(root, orient="vertical", command=self.field_tree.yview)
        fx = ttk.Scrollbar(root, orient="horizontal", command=self.field_tree.xview)
        fy.grid(row=0, column=1, sticky="ns")
        fx.grid(row=1, column=0, sticky="ew")
        self.field_tree.configure(yscrollcommand=fy.set, xscrollcommand=fx.set)
        self.field_tree.bind("<<TreeviewSelect>>", self._field_selected)
        self.field_tree.bind("<Double-1>", lambda _event: self.field_entry.focus_set())

        editor = ttk.LabelFrame(root, text="Expliciete correctie of bevestiging", padding=8)
        editor.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        editor.columnconfigure(1, weight=1)
        ttk.Label(editor, text="Nieuwe waarde:").grid(row=0, column=0, sticky="w")
        self.field_entry = ttk.Entry(editor, textvariable=self.field_value)
        self.field_entry.grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(editor, text="Correctie klaarzetten", command=self._stage_field_value).grid(row=0, column=2, padx=2)
        ttk.Button(editor, text="Huidige interpretatie bevestigen", command=self._confirm_field).grid(row=1, column=2, padx=2, pady=(6, 0))
        ttk.Button(editor, text="Actie wissen", command=self._clear_field_action).grid(row=1, column=1, sticky="e", padx=8, pady=(6, 0))
        ttk.Label(editor, textvariable=self.field_action, wraplength=640, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

    def _build_questions_tab(self, root: ttk.Frame) -> None:
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        columns = ("severity", "field", "question", "action")
        self.question_tree = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
        headings = {"severity": "Ernst", "field": "Veld", "question": "Vraag", "action": "Reviewactie"}
        widths = {"severity": 80, "field": 170, "question": 450, "action": 160}
        for column in columns:
            self.question_tree.heading(column, text=headings[column])
            self.question_tree.column(column, width=widths[column], anchor="w")
        self.question_tree.grid(row=0, column=0, sticky="nsew")
        qy = ttk.Scrollbar(root, orient="vertical", command=self.question_tree.yview)
        qx = ttk.Scrollbar(root, orient="horizontal", command=self.question_tree.xview)
        qy.grid(row=0, column=1, sticky="ns")
        qx.grid(row=1, column=0, sticky="ew")
        self.question_tree.configure(yscrollcommand=qy.set, xscrollcommand=qx.set)
        self.question_tree.bind("<<TreeviewSelect>>", self._question_selected)

        editor = ttk.LabelFrame(root, text="Antwoord", padding=8)
        editor.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        editor.columnconfigure(0, weight=1)
        self.answer_combo = ttk.Combobox(editor, textvariable=self.question_answer, state="normal")
        self.answer_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(editor, text="Antwoord / correctie klaarzetten", command=self._answer_question).grid(row=0, column=1, padx=2)
        ttk.Button(editor, text="Huidige broninterpretatie bevestigen", command=self._confirm_question).grid(row=1, column=1, padx=2, pady=(6, 0))
        self.question_detail = ttk.Label(editor, wraplength=700, justify="left")
        self.question_detail.grid(row=1, column=0, sticky="w", pady=(6, 0))

    # ------------------------------------------------------------- populate
    def _populate_fields(self) -> None:
        self._field_by_iid.clear()
        for item in self.field_tree.get_children():
            self.field_tree.delete(item)
        for index, field in enumerate(self.fields):
            iid = f"f{index}"
            self._field_by_iid[iid] = field
            confidence = "" if field.confidence is None else f"{field.confidence:.0%}"
            self.field_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    field.category,
                    field.label,
                    self._effective_value_text(field),
                    confidence,
                    field.status,
                    self._field_action_text(field),
                ),
            )

    def _populate_questions(self) -> None:
        self._question_by_iid.clear()
        for item in self.question_tree.get_children():
            self.question_tree.delete(item)
        for index, question in enumerate(self.analysis.part.validation.unresolved_questions):
            iid = f"q{index}"
            self._question_by_iid[iid] = question
            self.question_tree.insert(
                "",
                "end",
                iid=iid,
                values=(question.severity, question.field_path, question.prompt, self._question_action_text(question)),
            )

    def _refresh_rows(self) -> None:
        for iid, field in self._field_by_iid.items():
            values = list(self.field_tree.item(iid, "values"))
            values[2] = self._effective_value_text(field)
            values[5] = self._field_action_text(field)
            self.field_tree.item(iid, values=values)
        for iid, question in self._question_by_iid.items():
            values = list(self.question_tree.item(iid, "values"))
            values[3] = self._question_action_text(question)
            self.question_tree.item(iid, values=values)
        self._update_status()
        self._draw_model()

    # --------------------------------------------------------------- actions
    def _selected_field(self) -> ReviewField | None:
        selection = self.field_tree.selection()
        return self._field_by_iid.get(selection[0]) if selection else None

    def _selected_question(self):
        selection = self.question_tree.selection()
        return self._question_by_iid.get(selection[0]) if selection else None

    def _field_selected(self, _event=None) -> None:
        field = self._selected_field()
        if field is None:
            return
        value = self.pending_values.get(field.path, field.current_value)
        self.field_value.set(value_to_text(value))
        notes = []
        if field.editable:
            notes.append("Dit veld kan numeriek of tekstueel worden gecorrigeerd.")
        else:
            notes.append("Dit is een samengestelde geometrische feature; wijzig onderliggende punten/waarden.")
        if field.confirmable:
            notes.append("De huidige broninterpretatie kan expliciet worden bevestigd.")
        self.field_action.set(" ".join(notes))
        self._selected_model_path = field.path
        self._highlight_source(field)
        self._draw_model()

    def _stage_field_value(self) -> None:
        field = self._selected_field()
        if field is None:
            messagebox.showwarning("Geen veld", "Selecteer eerst een veld.", parent=self)
            return
        if not field.editable:
            messagebox.showwarning(
                "Niet direct wijzigbaar",
                "Wijzig de onderliggende contourpunten of gatvelden; vrije geometrie wordt niet uit tekst gegenereerd.",
                parent=self,
            )
            return
        try:
            value = coerce_review_value(self.field_value.get(), field.current_value)
        except Exception as exc:
            messagebox.showerror("Ongeldige waarde", str(exc), parent=self)
            return
        self.pending_values[field.path] = value
        for question_id in field.question_ids:
            self.answers[question_id] = value
        self.review_status.set(f"Correctie voor {field.label} staat klaar; validatie is nog vereist.")
        self._refresh_rows()

    def _confirm_field(self) -> None:
        field = self._selected_field()
        if field is None or not field.confirmable:
            messagebox.showwarning(
                "Geen bevestigbaar bronbewijs",
                "Selecteer een veld of feature met herleidbaar bronbewijs.",
                parent=self,
            )
            return
        self.confirmed.add(field.evidence_path)
        # Aliasvragen (bijvoorbeeld position -> header.position_number) worden
        # met een expliciet antwoord gesloten; exacte padvragen worden door
        # apply_review via de confirm-lijst gesloten.
        for question_id in field.question_ids:
            question = next(
                (item for item in self.analysis.part.validation.unresolved_questions if item.question_id == question_id),
                None,
            )
            if question is not None and question.field_path != field.evidence_path:
                self.answers[question_id] = self.pending_values.get(field.path, field.current_value)
        self.review_status.set(f"Broninterpretatie voor {field.label} is expliciet bevestigd.")
        self._refresh_rows()

    def _clear_field_action(self) -> None:
        field = self._selected_field()
        if field is None:
            return
        self.pending_values.pop(field.path, None)
        if field.evidence_path:
            self.confirmed.discard(field.evidence_path)
        for question_id in field.question_ids:
            self.answers.pop(question_id, None)
        self.field_value.set(value_to_text(field.current_value))
        self.review_status.set(f"Reviewactie voor {field.label} is gewist.")
        self._refresh_rows()

    def _question_selected(self, _event=None) -> None:
        question = self._selected_question()
        if question is None:
            return
        self.question_answer.set(value_to_text(self.answers.get(question.question_id, "")))
        self.answer_combo.configure(values=[str(item) for item in question.alternatives])
        detail = question.reason or "Deze vraag moet expliciet worden beantwoord voordat productie-export kan worden vrijgegeven."
        self.question_detail.configure(text=detail)
        field = self._find_field_for_question(question)
        if field is not None:
            self._selected_model_path = field.path
            self._highlight_source(field)
            self._draw_model()

    def _answer_question(self) -> None:
        question = self._selected_question()
        if question is None:
            messagebox.showwarning("Geen vraag", "Selecteer eerst een controlevraag.", parent=self)
            return
        raw = self.question_answer.get().strip()
        if not raw:
            messagebox.showwarning("Geen antwoord", "Vul een expliciet antwoord in.", parent=self)
            return
        mapped = canonical_path(question.field_path)
        field = next((item for item in self.fields if item.path == mapped and item.editable), None)
        value: Any = raw
        if field is not None:
            try:
                value = coerce_review_value(raw, field.current_value)
            except Exception as exc:
                messagebox.showerror("Ongeldig antwoord", str(exc), parent=self)
                return
            self.pending_values[field.path] = value
        self.answers[question.question_id] = value
        self.review_status.set(f"Antwoord op {question.question_id} staat klaar; deterministische validatie volgt.")
        self._refresh_rows()

    def _confirm_question(self) -> None:
        question = self._selected_question()
        if question is None:
            return
        field = self._find_field_for_question(question)
        if field is None or not field.confirmable:
            messagebox.showwarning(
                "Geen bevestigbaar bronbewijs",
                "Deze vraag vereist een concrete waarde of een geometrische correctie; er is geen bestaand evidenceveld om alleen te bevestigen.",
                parent=self,
            )
            return
        self.confirmed.add(field.evidence_path)
        if question.field_path != field.evidence_path:
            self.answers[question.question_id] = self.pending_values.get(field.path, field.current_value)
        self.review_status.set(f"Broninterpretatie voor vraag {question.question_id} is bevestigd.")
        self._refresh_rows()

    # ------------------------------------------------------------- validate
    def _payload(self) -> dict[str, Any]:
        return build_review_payload(
            self.analysis.part,
            reviewed_by=self.reviewer.get(),
            values=self.pending_values,
            confirm=self.confirmed,
            answers=self.answers,
            comment=self.comment.get("1.0", "end").strip(),
        )

    def _save_json(self) -> None:
        try:
            payload = self._payload()
        except Exception as exc:
            messagebox.showerror("Review-JSON", str(exc), parent=self)
            return
        source = Path(self.analysis.source)
        name = filedialog.asksaveasfilename(
            parent=self,
            title="Review-JSON opslaan",
            initialfile=f"{source.stem}.review.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not name:
            return
        Path(name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.review_status.set(f"Review-JSON opgeslagen: {name}")

    def _validate_and_accept(self) -> None:
        try:
            payload = self._payload()
            reviewed = apply_review(self.analysis, payload)
        except Exception as exc:
            messagebox.showerror("Reviewvalidatie", str(exc), parent=self)
            return
        if not reviewed.production_export_allowed:
            open_questions = [
                item.prompt for item in reviewed.part.validation.unresolved_questions if item.is_blocking()
            ]
            details = reviewed.errors + open_questions
            self.review_status.set("Review is nog onvolledig; productie-export blijft geblokkeerd.")
            messagebox.showwarning(
                "Review nog niet volledig",
                "De deterministische validatie blokkeert vrijgave:\n\n"
                + "\n".join(f"- {item}" for item in details[:16]),
                parent=self,
            )
            return
        self.result = payload
        self.reviewed_analysis = reviewed
        self.review_status.set("Review gevalideerd; productie-export is toegestaan.")
        self.grab_release()
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.reviewed_analysis = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    # -------------------------------------------------------------- helpers
    def _find_field_for_question(self, question) -> ReviewField | None:
        mapped = canonical_path(question.field_path)
        # Prefer the exact evidence feature (for example holes[0]) before a
        # related nested field.  This prevents a diameter edit from silently
        # standing in for confirmation of an entire hole position/reference.
        for item in self.fields:
            if item.evidence_path == question.field_path:
                return item
        for item in self.fields:
            if item.path == mapped:
                return item
        return next(
            (item for item in self.fields if question.question_id in item.question_ids),
            None,
        )

    def _effective_value_text(self, field: ReviewField) -> str:
        return value_to_text(self.pending_values.get(field.path, field.current_value))

    def _field_action_text(self, field: ReviewField) -> str:
        actions = []
        if field.path in self.pending_values:
            actions.append("gecorrigeerd")
        if field.evidence_path and field.evidence_path in self.confirmed:
            actions.append("bevestigd")
        return ", ".join(actions) or "-"

    def _question_action_text(self, question) -> str:
        if question.question_id in self.answers:
            return "beantwoord"
        field = self._find_field_for_question(question)
        if field is not None and field.evidence_path in self.confirmed:
            return "bevestigd"
        return "open"

    def _update_status(self) -> None:
        open_count = sum(
            self._question_action_text(question) == "open"
            for question in self.analysis.part.validation.unresolved_questions
            if question.severity == "blocking"
        )
        self.review_status.set(
            f"{len(self.pending_values)} correctie(s), {len(self.confirmed)} bevestiging(en), "
            f"{len(self.answers)} antwoord(en); nog {open_count} zichtbare blokkerende vraag/vragen."
        )

    # --------------------------------------------------------------- source
    def _initial_render(self) -> None:
        self._render_source_page(0)
        self._draw_model()
        self._update_status()

    def _change_page(self, delta: int) -> None:
        target = min(max(self._source_page + delta, 0), self._page_count - 1)
        self._render_source_page(target)

    def _render_source_page(self, index: int) -> None:
        self.source_canvas.delete("all")
        self._source_page = index
        self.page_label.set(f"Pagina {index + 1} / {self._page_count}")
        try:
            import pymupdf

            document = pymupdf.open(self.analysis.source)
            try:
                page = document[index]
                max_width = max(420, self.source_canvas.winfo_width() - 24)
                zoom = min(1.7, max(0.8, max_width / max(float(page.rect.width), 1.0)))
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
                encoded = base64.b64encode(pixmap.tobytes("png")).decode("ascii")
                self._source_photo = tk.PhotoImage(data=encoded)
                self._source_scale = float(pixmap.width) / float(page.rect.width)
                self.source_canvas.create_image(0, 0, image=self._source_photo, anchor="nw", tags=("page",))
                self.source_canvas.configure(scrollregion=(0, 0, pixmap.width, pixmap.height))
            finally:
                document.close()
        except Exception as exc:
            self._source_photo = None
            self.source_canvas.create_text(
                20,
                20,
                anchor="nw",
                width=max(300, self.source_canvas.winfo_width() - 40),
                text=f"Bronpreview kon niet worden geladen:\n{exc}",
            )
            self.source_canvas.configure(scrollregion=(0, 0, 600, 300))

    def _highlight_source(self, field: ReviewField) -> None:
        self.source_canvas.delete("evidence-highlight")
        evidence = self.analysis.part.field_evidence.get(field.evidence_path) if field.evidence_path else None
        if evidence is None or not evidence.bbox:
            return
        page = int(evidence.page or 1) - 1
        if page != self._source_page:
            self._render_source_page(page)
        x0, y0, x1, y1 = [float(value) * self._source_scale for value in evidence.bbox]
        pad = 4
        self.source_canvas.create_rectangle(
            x0 - pad,
            y0 - pad,
            x1 + pad,
            y1 + pad,
            outline="#d00000",
            width=3,
            tags=("evidence-highlight",),
        )
        self.source_canvas.tag_raise("evidence-highlight")
        self.source_canvas.xview_moveto(max(0.0, (x0 - 40) / max(1.0, float(self.source_canvas.bbox("all")[2]))))
        self.source_canvas.yview_moveto(max(0.0, (y0 - 40) / max(1.0, float(self.source_canvas.bbox("all")[3]))))

    def _open_source(self) -> None:
        path = Path(self.analysis.source)
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                import subprocess

                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Bron openen", str(exc), parent=self)

    # --------------------------------------------------------------- model
    def _draft_part(self):
        try:
            payload = build_review_payload(
                self.analysis.part,
                reviewed_by=self.reviewer.get().strip() or "preview",
                values=self.pending_values,
                confirm=self.confirmed,
                answers=self.answers,
                comment="interactive preview",
            )
            return apply_review(self.analysis, payload).part
        except Exception:
            return self.analysis.part

    def _draw_model(self) -> None:
        canvas = self.model_canvas
        canvas.delete("all")
        part = self._draft_part()
        width = max(320, canvas.winfo_width())
        height = max(200, canvas.winfo_height())
        margin = 34.0
        contour = next((item for item in part.contours if item.kind.upper() not in {"IK", "INNER"}), None)
        if contour is None or len(contour.points) < 3:
            canvas.create_text(width / 2, height / 2, text="Geen gesloten deterministische contour beschikbaar", anchor="center")
            return
        points = [(float(item.x), float(item.q)) for item in contour.points]
        xs = [item[0] for item in points]
        ys = [item[1] for item in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1.0)
        span_y = max(max_y - min_y, 1.0)
        scale = min((width - 2 * margin) / span_x, (height - 2 * margin - 24) / span_y)

        def map_point(x: float, y: float) -> tuple[float, float]:
            return margin + (x - min_x) * scale, height - margin - (y - min_y) * scale

        polygon: list[float] = []
        for x, y in points:
            px, py = map_point(x, y)
            polygon.extend((px, py))
        selected_contour = self._selected_model_path.startswith("contours[")
        canvas.create_polygon(
            polygon,
            fill="#e9eef5",
            outline="#c00000" if selected_contour else "#202020",
            width=3 if selected_contour else 2,
        )
        for index, point in enumerate(contour.points):
            px, py = map_point(float(point.x), float(point.q))
            selected_point = self._selected_model_path.startswith(f"contours[0].points[{index}]")
            radius = 5 if selected_point else 3
            canvas.create_oval(px - radius, py - radius, px + radius, py + radius, fill="#d00000" if selected_point else "#404040", outline="")
            if point.radius > 0:
                canvas.create_text(px + 8, py - 8, text=f"R {point.radius:g}", anchor="sw", font=("TkDefaultFont", 8))

        for index, hole in enumerate(part.holes):
            cx, cy = map_point(float(hole.x), float(hole.q))
            radius = max(2.0, float(hole.diameter) / 2.0 * scale)
            selected = self._selected_model_path.startswith(f"holes[{index}]")
            canvas.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                fill="white",
                outline="#d00000" if selected else "#202020",
                width=3 if selected else 2,
            )
            canvas.create_line(cx - radius - 6, cy, cx + radius + 6, cy, fill="#808080", dash=(3, 2))
            canvas.create_line(cx, cy - radius - 6, cx, cy + radius + 6, fill="#808080", dash=(3, 2))
            canvas.create_text(cx + radius + 5, cy - radius - 3, text=f"Ø{hole.diameter:g}", anchor="sw", font=("TkDefaultFont", 8))

        title = f"{part.header.position_number or part.part_id or '-'} | {part.header.profile or '-'} | {part.header.material or '-'}"
        canvas.create_text(margin, 10, text=title, anchor="nw", font=("TkDefaultFont", 10, "bold"))
        canvas.create_text(
            width - margin,
            10,
            text="REVIEWMODEL - NIET VRIJGEGEVEN",
            anchor="ne",
            fill="#a00000",
            font=("TkDefaultFont", 9, "bold"),
        )
