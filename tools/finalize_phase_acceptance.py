"""Compatibility entry point for the strict unified Phase-3 validator."""
from __future__ import annotations

import json

from build_phase3_validation import build_validation


def finalize() -> dict[str, object]:
    return build_validation()


if __name__ == "__main__":
    print(json.dumps(finalize(), indent=2, sort_keys=True))
