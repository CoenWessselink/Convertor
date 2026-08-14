"""Small native-window hosts used only by the V1 spike and tests."""
from __future__ import annotations

from dataclasses import dataclass
import os
import platform
from typing import Any

from cws_viewer.technology.contracts import NativeWindow


@dataclass(slots=True)
class TkNativeWindowHost:
    """Create a real native drawable without coupling the backend to Tk.

    The production target is PySide6/Qt. Tk is available in the current Python
    runtime and provides a reliable native handle for Linux/Xvfb and Windows CI,
    allowing the OCCT renderer itself to be measured before the Qt package is
    available offline.
    """

    width: int = 960
    height: int = 720
    title: str = "CWS Viewer V1 native host"
    _root: Any | None = None

    def open(self) -> NativeWindow:
        if platform.system() == "Linux" and not os.environ.get("DISPLAY"):
            raise RuntimeError(
                "Een X-display is vereist voor de OCCT/V1-spike. Gebruik xvfb-run -a."
            )
        import tkinter as tk

        root = tk.Tk()
        root.title(self.title)
        root.geometry(f"{self.width}x{self.height}+0+0")
        root.update_idletasks()
        root.update()
        self._root = root
        return NativeWindow(
            handle=int(root.winfo_id()),
            width=self.width,
            height=self.height,
        )

    def process_events(self) -> None:
        if self._root is not None:
            self._root.update_idletasks()
            self._root.update()

    def close(self) -> None:
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None

    def __enter__(self) -> "TkNativeWindowHost":
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


__all__ = ["TkNativeWindowHost"]
