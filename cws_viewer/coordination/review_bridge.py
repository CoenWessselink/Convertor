"""Bridge T6 clash records into the existing T5 review service without widening T5 API."""
from __future__ import annotations

from typing import Any


class T6ReviewServiceBridge:
    """Forward all T5 review operations and add clash-aware issue creation.

    T5 remains a stable review contract.  T6 owns the extra clash reference and
    stores it on the mutable ReviewIssue record before normal T5 persistence.
    """

    def __init__(self, service: Any) -> None:
        self._service = service

    def __getattr__(self, name: str) -> Any:
        return getattr(self._service, name)

    def create_issue(self, *args: Any, linked_clash_ids=(), **kwargs: Any) -> Any:
        issue = self._service.create_issue(*args, **kwargs)
        values = tuple(dict.fromkeys(str(value) for value in linked_clash_ids if str(value)))
        if values:
            issue.linked_clash_ids = values
            issue.audit_events.append(
                {
                    "event": "clash_links_added",
                    "linked_clash_ids": list(values),
                    "actor": str(kwargs.get("created_by", "CWS Model Control")),
                    "utc": issue.updated_utc,
                }
            )
        return issue


__all__ = ["T6ReviewServiceBridge"]
