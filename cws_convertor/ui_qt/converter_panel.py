"""Functional converter panel for the primary CWS Convertor Qt application."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cws_viewer.ui_qt.qt_compat import qt_available, require_qt

if qt_available():
    QtCore, QtGui, QtWidgets = require_qt()

    class _ConversionWorker(QtCore.QObject):
        progress = QtCore.Signal(str)
        finished = QtCore.Signal(dict)
        failed = QtCore.Signal(str)

        def __init__(self, files: tuple[Path, ...], output: Path, direction: str, material: str) -> None:
            super().__init__(); self.files=files; self.output=output; self.direction=direction; self.material=material

        @QtCore.Slot()
        def run(self) -> None:
            try:
                from conversion import convert_file
                results=[]
                for index, source in enumerate(self.files, start=1):
                    self.progress.emit(f"{index}/{len(self.files)} · {source.name}")
                    outputs, warnings, failures = convert_file(
                        source, self.output, self.direction, material=self.material,
                        strict_validation=True,
                    )
                    results.append({
                        "source": str(source), "outputs": [str(p) for p in outputs],
                        "warnings": list(warnings), "failures": list(failures),
                    })
                self.finished.emit({"status":"passed","results":results})
            except Exception as exc:
                self.failed.emit(f"{type(exc).__name__}: {exc}")

    class ConverterPanel(QtWidgets.QWidget):
        """Small but real front-end over the proven deterministic conversion core."""
        def __init__(self, parent: Any | None = None) -> None:
            super().__init__(parent); self._thread=None; self._worker=None; self._files=[]; self._workspace=None; self._selection=None; self._build_ui()

        def _build_ui(self) -> None:
            root=QtWidgets.QVBoxLayout(self); root.setContentsMargins(12,12,12,12)
            title=QtWidgets.QLabel("Converteren")
            title.setObjectName("workspaceTitle")
            root.addWidget(title)
            self.selection_context=QtWidgets.QLabel("Bron: losse modelbestanden")
            self.selection_context.setObjectName("selectionContext")
            root.addWidget(self.selection_context)
            form=QtWidgets.QFormLayout()
            self.direction=QtWidgets.QComboBox()
            for label,value in (
                ("NC1 / DSTV → STEP","nc1-to-step"),("STEP → NC1 / DSTV","step-to-nc1"),
                ("IFC → STEP","ifc-to-step"),("STEP → IFC","step-to-ifc"),
                ("IFC → NC1 / DSTV","ifc-to-dstv"),("NC1 / DSTV → IFC","dstv-to-ifc"),
            ): self.direction.addItem(label,value)
            self.material=QtWidgets.QComboBox(); self.material.setEditable(True); self.material.addItems(["S235JR","S355JR","S355J2"])
            self.output=QtWidgets.QLineEdit(str(Path.home()/"CWS Convertor uitvoer"))
            output_row=QtWidgets.QHBoxLayout(); output_row.addWidget(self.output,1)
            browse=QtWidgets.QPushButton("Kies map"); browse.clicked.connect(self._choose_output); output_row.addWidget(browse)
            output_widget=QtWidgets.QWidget(); output_widget.setLayout(output_row)
            form.addRow("Richting",self.direction); form.addRow("Materiaal",self.material); form.addRow("Uitvoermap",output_widget)
            root.addLayout(form)
            buttons=QtWidgets.QHBoxLayout()
            add=QtWidgets.QPushButton("Bestanden toevoegen"); add.clicked.connect(self._choose_files)
            clear=QtWidgets.QPushButton("Lijst wissen"); clear.clicked.connect(self._clear)
            self.run_button=QtWidgets.QPushButton("Converteren"); self.run_button.clicked.connect(self._run)
            self.run_button.setStyleSheet("background:#2563a6;color:white;font-weight:700;padding:7px")
            buttons.addWidget(add); buttons.addWidget(clear); buttons.addStretch(1); buttons.addWidget(self.run_button); root.addLayout(buttons)
            self.files=QtWidgets.QListWidget(); self.files.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection); root.addWidget(self.files,1)
            self.status=QtWidgets.QLabel("Geen bestanden geselecteerd"); root.addWidget(self.status)
            self.log=QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(2000); root.addWidget(self.log,1)

        def set_project_selection(self, workspace: Any | None, selection: Any | None) -> None:
            """Show the shared selection without creating a second project model."""
            self._workspace = workspace
            self._selection = selection
            entity_id = str(getattr(selection, "primary_entity_id", "") or "")
            if workspace is None:
                self.selection_context.setText("Bron: losse modelbestanden")
                return
            if not entity_id:
                self.selection_context.setText(f"Project: {workspace.project.project_name} | geen object geselecteerd")
                return
            entity = workspace.project.parts.get(entity_id)
            name = str(getattr(entity, "part_position", "") or entity_id)
            self.selection_context.setText(f"Project: {workspace.project.project_name} | selectie: {name} | {entity_id}")

        def add_files(self, paths) -> None:
            """Add shell-/application-provided model files without starting conversion."""
            allowed = {".nc", ".nc1", ".step", ".stp", ".ifc"}
            for value in paths:
                path = Path(value).expanduser().resolve()
                if path.suffix.lower() not in allowed or not path.is_file():
                    continue
                if path not in self._files:
                    self._files.append(path)
                    self.files.addItem(str(path))
            self.status.setText(f"{len(self._files)} bestanden")

        def _choose_files(self) -> None:
            names,_=QtWidgets.QFileDialog.getOpenFileNames(self,"Modelbestanden kiezen","","Modelbestanden (*.nc *.nc1 *.step *.stp *.ifc)")
            self.add_files(names)

        def _choose_output(self) -> None:
            name=QtWidgets.QFileDialog.getExistingDirectory(self,"Uitvoermap",self.output.text())
            if name: self.output.setText(name)

        def _clear(self) -> None:
            self._files.clear(); self.files.clear(); self.status.setText("Geen bestanden geselecteerd")

        def _run(self) -> None:
            if not self._files:
                QtWidgets.QMessageBox.information(self,"Converteren","Selecteer eerst bestanden."); return
            target=Path(self.output.text()).expanduser(); target.mkdir(parents=True,exist_ok=True)
            self.run_button.setEnabled(False); self.log.appendPlainText("Conversie gestart …")
            thread=QtCore.QThread(self); worker=_ConversionWorker(tuple(self._files),target,str(self.direction.currentData()),self.material.currentText())
            worker.moveToThread(thread); thread.started.connect(worker.run)
            worker.progress.connect(self.status.setText)
            worker.finished.connect(self._finished); worker.failed.connect(self._failed)
            worker.finished.connect(thread.quit); worker.failed.connect(thread.quit)
            worker.finished.connect(worker.deleteLater); worker.failed.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater); thread.finished.connect(lambda:setattr(self,"_thread",None)); thread.finished.connect(lambda:setattr(self,"_worker",None))
            self._worker=worker
            self._thread=thread; thread.start()

        @QtCore.Slot(dict)
        def _finished(self,payload:dict) -> None:
            self.run_button.setEnabled(True)
            for row in payload.get("results",[]):
                self.log.appendPlainText(f"✓ {Path(row['source']).name}")
                for output in row.get("outputs",[]): self.log.appendPlainText(f"  → {output}")
                for warning in row.get("warnings",[]): self.log.appendPlainText(f"  WAARSCHUWING: {warning}")
                for failure in row.get("failures",[]): self.log.appendPlainText(f"  MISLUKT: {failure}")
            self.status.setText("Conversie afgerond")

        @QtCore.Slot(str)
        def _failed(self,message:str) -> None:
            self.run_button.setEnabled(True); self.status.setText("Conversie mislukt"); self.log.appendPlainText(f"FOUT: {message}")
            QtWidgets.QMessageBox.critical(self,"Conversie mislukt",message)

else:
    class ConverterPanel:
        def __init__(self,*_:Any,**__:Any)->None: require_qt()

__all__=["ConverterPanel"]
