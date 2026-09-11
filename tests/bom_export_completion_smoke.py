from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6 import QtWidgets
from cws_convertor.ui_qt.bom_export_completion import choose_and_start_bom_export

class T:
    def __init__(self,v): self.v=v
    def text(self): return self.v
    def setText(self,v): self.v=v

class P(QtWidgets.QWidget):
    def __init__(self,v):
        super().__init__(); self.output_dir=T(v); self.current_background_job_id=""; self.calls=0
    def _generate(self):
        self.calls+=1; self.current_background_job_id="job"

if __name__ == "__main__":
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    p=P("")
    with patch("cws_convertor.ui_qt.bom_export_completion.QFileDialog.getExistingDirectory",return_value=""):
        started,_=choose_and_start_bom_export(p)
    assert not started and p.calls==0
    with TemporaryDirectory() as d:
        p=P(d)
        with patch("cws_convertor.ui_qt.bom_export_completion.QFileDialog.getExistingDirectory",return_value=d):
            started,_=choose_and_start_bom_export(p)
        assert started and p.calls==1 and p.current_background_job_id=="job"

    source=Path("cws_convertor/ui_qt/bom_action_dispatch.py").read_text(encoding="utf-8")
    assert "from cws_convertor.ui_qt.bom_export_completion import choose_and_start_bom_export" in source
    assert "started, message = choose_and_start_bom_export(page)" in source
    assert "Definitieve PASS/FAIL volgt uitsluitend via de bestaande Export Center-verificatie" in source
    print("PASS: BOM export continuation helper and dispatcher integration")
