from __future__ import annotations

from pathlib import Path
import tempfile

from cws_viewer.core.loader_v2_probe import run_probe


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="cws-loader-v2-smoke-") as temporary:
        result = run_probe(Path(temporary) / "probe.json", require_frozen=False)
    assert result["status"] == "PASS", result
    assert result["summary"] == {"passed": 8, "total": 8}, result["summary"]
    print("LOADER_ENGINE_V2_SMOKE = 8/8 PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
