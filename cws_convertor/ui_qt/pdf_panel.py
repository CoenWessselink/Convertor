"""Local-first PDF analysis panel integrated in the Qt main shell."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt


if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class PDFPanel(QtWidgets.QWidget):
        feature_highlight_requested = QtCore.Signal(str, str)

        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent)
            self.path: Path | None = None
            self._build()

        def _build(self) -> None:
            root = QtWidgets.QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            title = QtWidgets.QLabel("PDF / Tekening · lokale analyse")
            title.setStyleSheet("font-size:20px;font-weight:700")
            root.addWidget(title)
            note = QtWidgets.QLabel(
                "AI mag semantiek voorstellen; geometrie en productie-export blijven "
                "deterministisch, auditbaar en reviewplichtig."
            )
            note.setWordWrap(True)
            root.addWidget(note)

            row = QtWidgets.QHBoxLayout()
            self.path_edit = QtWidgets.QLineEdit(); self.path_edit.setReadOnly(True)
            choose = QtWidgets.QPushButton("PDF kiezen"); choose.clicked.connect(self._choose)
            analyse = QtWidgets.QPushButton("Analyseren"); analyse.clicked.connect(self._analyse)
            row.addWidget(self.path_edit, 1); row.addWidget(choose); row.addWidget(analyse)
            root.addLayout(row)

            bridge = QtWidgets.QGroupBox("PDF ↔ project/3D featurebinding")
            bridge_layout = QtWidgets.QGridLayout(bridge)
            self.entity_id = QtWidgets.QLineEdit()
            self.entity_id.setPlaceholderText("Canonical entity-ID")
            self.feature_id = QtWidgets.QLineEdit()
            self.feature_id.setPlaceholderText("Feature-ID uit dimension graph/review")
            highlight = QtWidgets.QPushButton("Markeer in projectviewer")
            highlight.clicked.connect(self._highlight)
            self.bridge_status = QtWidgets.QLabel(
                "Open een CWS-project om PDF-features via stabiele IDs met 3D te koppelen."
            )
            self.bridge_status.setWordWrap(True)
            bridge_layout.addWidget(QtWidgets.QLabel("Onderdeel"), 0, 0)
            bridge_layout.addWidget(self.entity_id, 0, 1)
            bridge_layout.addWidget(QtWidgets.QLabel("Feature"), 1, 0)
            bridge_layout.addWidget(self.feature_id, 1, 1)
            bridge_layout.addWidget(highlight, 0, 2, 2, 1)
            bridge_layout.addWidget(self.bridge_status, 2, 0, 1, 3)
            root.addWidget(bridge)

            self.output = QtWidgets.QPlainTextEdit(); self.output.setReadOnly(True)
            root.addWidget(self.output, 1)

        def load_pdf(self, value: str | Path) -> bool:
            path = Path(value).expanduser().resolve()
            if path.suffix.lower() != ".pdf" or not path.is_file():
                return False
            self.path = path
            self.path_edit.setText(str(path))
            return True

        def show_project_selection(self, selection: Any) -> None:
            primary = str(getattr(selection, "primary_entity_id", "") or "")
            feature = str(getattr(selection, "feature_id", "") or "")
            if primary:
                self.entity_id.setText(primary)
            if feature:
                self.feature_id.setText(feature)
            origin = str(getattr(selection, "origin", "application"))
            self.bridge_status.setText(
                f"Actieve projectselectie: {primary or 'geen'} · feature: {feature or 'geen'} · bron: {origin}"
            )

        def _highlight(self) -> None:
            entity_id = self.entity_id.text().strip()
            feature_id = self.feature_id.text().strip()
            if not entity_id or not feature_id:
                QtWidgets.QMessageBox.information(
                    self, "PDF-feature", "Vul een Canonical entity-ID en feature-ID in."
                )
                return
            self.feature_highlight_requested.emit(entity_id, feature_id)

        def _choose(self) -> None:
            name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Technische PDF kiezen", "", "PDF (*.pdf)"
            )
            if name:
                self.load_pdf(name)

        def _analyse(self) -> None:
            if self.path is None:
                QtWidgets.QMessageBox.information(self, "PDF", "Kies eerst een PDF.")
                return
            try:
                from ai_support import AISettings
                from pdf_support import analyze_pdf

                result = analyze_pdf(self.path, ai_settings=AISettings(provider="none"))
                payload = result.to_dict() if hasattr(result, "to_dict") else vars(result)
                self.output.setPlainText(
                    json.dumps(payload, indent=2, ensure_ascii=False, default=str)
                )
            except Exception as exc:
                QtWidgets.QMessageBox.critical(
                    self, "PDF-analyse", f"{type(exc).__name__}: {exc}"
                )

else:

    class PDFPanel:
        def __init__(self, *_: Any, **__: Any) -> None:
            require_qt()


__all__ = ["PDFPanel"]
