"""Bind native IDs to both integer and capsule variants of the OCP window ABI."""
from __future__ import annotations

import ctypes
import operator
from typing import Any


def _checked_handle(handle: int) -> int:
    if isinstance(handle, bool):
        raise ValueError("Native window handle must be a positive integer")
    value = operator.index(handle)
    if not 0 < value < (1 << (ctypes.sizeof(ctypes.c_void_p) * 8)):
        raise ValueError("Native window handle must fit a positive native pointer")
    return value


def native_handle_capsule(handle: int) -> Any:
    """Return an unnamed capsule for OCP builds using pointer bindings."""
    value = _checked_handle(handle)
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
    """Bind and read back the exact native ID; never accept a mismatched handle.

    OCP 7.9 Linux exposes an integer while other supported wheels expose a
    capsule. Only a rejected argument type selects the alternate ABI. Driver
    errors and failed readback still propagate to the native rendering gate.
    """
    value = _checked_handle(handle)
    keepalive: Any = value
    try:
        window.SetNativeHandle(value)
    except TypeError:
        keepalive = native_handle_capsule(value)
        window.SetNativeHandle(keepalive)
    native = window.NativeHandle()
    actual = native if isinstance(native, int) else capsule_pointer(native)
    if actual != value:
        raise RuntimeError("OCCT native window handle could not be verified")
    return keepalive


__all__ = ["bind_neutral_window", "capsule_pointer", "native_handle_capsule"]
