"""Helpers for binding Python integer window IDs to OCCT capsule APIs."""
from __future__ import annotations

import ctypes
from typing import Any


def native_handle_capsule(handle: int) -> Any:
    """Return the unnamed capsule expected by current OCP window bindings."""

    value = int(handle)
    if value <= 0:
        raise ValueError("Native window handle must be positive")
    create = ctypes.pythonapi.PyCapsule_New
    create.restype = ctypes.py_object
    create.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p)
    return create(ctypes.c_void_p(value), None, None)


def capsule_pointer(capsule: Any) -> int:
    """Read an unnamed capsule pointer for deterministic binding checks."""

    get_pointer = ctypes.pythonapi.PyCapsule_GetPointer
    get_pointer.restype = ctypes.c_void_p
    get_pointer.argtypes = (ctypes.py_object, ctypes.c_char_p)
    value = get_pointer(capsule, None)
    return int(value or 0)


def bind_neutral_window(window: Any, handle: int) -> Any:
    """Bind an OCCT Aspect_NeutralWindow and verify the exact native ID."""

    capsule = native_handle_capsule(handle)
    window.SetNativeHandle(capsule)
    if capsule_pointer(window.NativeHandle()) != int(handle):
        raise RuntimeError("OCCT native window handle could not be verified")
    return capsule


__all__ = ["bind_neutral_window", "capsule_pointer", "native_handle_capsule"]
