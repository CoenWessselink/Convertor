#!/usr/bin/env python3
"""Headless V0 harness; graphical technology spike starts in Phase V1."""
from __future__ import annotations

from cws_viewer.selftest import run_self_test


if __name__ == "__main__":
    report = run_self_test(deep_native=False)
    print(report.to_json())
    raise SystemExit(0 if report.passed else 2)
