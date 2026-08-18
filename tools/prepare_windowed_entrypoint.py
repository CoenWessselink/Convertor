#!/usr/bin/env python3
"""Make the foundation entrypoint safe for a PyInstaller windowed executable."""
from pathlib import Path

path = Path("CWS_Convertor_Foundation.py")
text = path.read_text(encoding="utf-8")
marker = "multiprocessing.freeze_support()\n"
patch = """multiprocessing.freeze_support()\n\n# PyInstaller windowed builds do not provide stdout/stderr.\nif sys.stdout is None:\n    sys.stdout = open(\"NUL\", \"w\", encoding=\"utf-8\")\nif sys.stderr is None:\n    sys.stderr = open(\"NUL\", \"w\", encoding=\"utf-8\")\n"""
if patch not in text:
    if marker not in text:
        raise SystemExit("freeze_support marker missing")
    text = text.replace(marker, patch, 1)
    path.write_text(text, encoding="utf-8")
print("windowed entrypoint prepared")
