from __future__ import annotations
from pathlib import Path
from typing import Any
from PySide6.QtWidgets import QFileDialog

def choose_and_start_bom_export(page: Any) -> tuple[bool, str]:
    initial = str(page.output_dir.text()).strip() or str(Path.cwd() / "build" / "exports")
    selected = QFileDialog.getExistingDirectory(page, "Kies uitvoermap voor BOM-export", initial)
    if not selected:
        return False, "Export geannuleerd: geen uitvoermap gekozen; er zijn geen bestanden gegenereerd"
    target = Path(selected).expanduser()
    if not target.is_dir():
        return False, "Export geblokkeerd: gekozen uitvoermap bestaat niet"
    page.output_dir.setText(str(target.resolve()))
    page._generate()
    job_id = str(getattr(page, "current_background_job_id", "") or "")
    if not job_id:
        return False, "Export niet gestart: preflight of centrale JobManager blokkeerde Generate"
    return True, f"Export gestart in {target.resolve()} · job {job_id}"
