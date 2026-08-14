"""Bounded undo/redo history for display-only viewer state."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class HistoryEntry(Generic[T]):
    action: str
    before: T
    after: T


class ViewerHistory(Generic[T]):
    def __init__(self, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("Historylimiet moet positief zijn")
        self.limit = int(limit)
        self._undo: list[HistoryEntry[T]] = []
        self._redo: list[HistoryEntry[T]] = []

    def record(self, action: str, before: T, after: T) -> None:
        if before == after:
            return
        self._undo.append(HistoryEntry(str(action), before, after))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        self._redo.clear()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> T:
        if not self._undo:
            raise IndexError("Geen vieweractie om ongedaan te maken")
        entry = self._undo.pop(); self._redo.append(entry); return entry.before

    def redo(self) -> T:
        if not self._redo:
            raise IndexError("Geen vieweractie om opnieuw uit te voeren")
        entry = self._redo.pop(); self._undo.append(entry); return entry.after

    def clear(self) -> None:
        self._undo.clear(); self._redo.clear()


__all__ = ["HistoryEntry", "ViewerHistory"]
