"""Single authority for document discovery, preview, export and printing."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from hashlib import sha256
from pathlib import Path
import threading
from typing import Iterable

@dataclass(frozen=True,slots=True)
class DocumentOutputRecord:
    path:Path;kind:str;producer:str;entity_ids:tuple[str,...];bytes:int;sha256:str
    def to_dict(self):
        payload=asdict(self);payload["path"]=str(self.path);return payload

class DocumentOutputService:
    _shared=None;_shared_lock=threading.RLock()
    def __init__(self):self._records={};self._lock=threading.RLock()
    @classmethod
    def shared(cls):
        with cls._shared_lock:
            if cls._shared is None:cls._shared=cls()
            return cls._shared
    def register(self,path:str|Path,*,kind:str,producer:str,entity_ids:Iterable[str]=()):
        target=Path(path).expanduser().resolve()
        if not target.is_file() or target.stat().st_size<=0:raise FileNotFoundError(f"Documentuitvoer ontbreekt: {target}")
        record=DocumentOutputRecord(target,str(kind),str(producer),tuple(dict.fromkeys(str(value) for value in entity_ids if str(value))),target.stat().st_size,sha256(target.read_bytes()).hexdigest())
        with self._lock:self._records[str(target).casefold()]=record
        return record
    def discover(self,roots:Iterable[str|Path]):
        for raw_root in roots:
            root=Path(raw_root).expanduser().resolve()
            if not root.is_dir():continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.casefold() in {".pdf",".png",".xlsx",".csv",".json"}:
                    try:self.register(path,kind=path.suffix.casefold().lstrip("."),producer="discovery")
                    except OSError:continue
        return self.records()
    def records(self):
        with self._lock:return tuple(sorted(self._records.values(),key=lambda item:(item.kind,item.path.name.casefold())))
    def export_widget_pdf(self,widget,path:str|Path,*,title:str):
        from cws_convertor.ui_qt.production_printing import export_widget_pdf
        return self.register(export_widget_pdf(widget,path,title=title),kind="pdf",producer="DocumentOutputService")
    def preview(self,path:str|Path):
        from PySide6 import QtCore,QtGui
        target=Path(path).expanduser().resolve()
        if not target.is_file():raise FileNotFoundError(target)
        return bool(QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(target))))
    def print(self,path:str|Path,*,parent=None):
        from cws_convertor.ui_qt.production_printing import print_pdf_file
        return print_pdf_file(path,parent=parent)

__all__=["DocumentOutputRecord","DocumentOutputService"]
