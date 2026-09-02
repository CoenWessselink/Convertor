from __future__ import annotations

import argparse
from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import uuid


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic CycloneDX component inventory")
    parser.add_argument("output", nargs="?", default="build/evidence/cws-convertor-sbom.cdx.json")
    args = parser.parse_args()
    components = []
    for distribution in sorted(metadata.distributions(), key=lambda item: (item.metadata.get("Name") or "").lower()):
        name = distribution.metadata.get("Name") or "unknown"
        components.append(
            {
                "type": "library",
                "name": name,
                "version": distribution.version,
                "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{distribution.version}",
            }
        )
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'nl.cws.convertor:0.10.21')}",
        "version": 1,
        "metadata": {"timestamp": datetime.now(timezone.utc).isoformat(), "component": {"type": "application", "name": "CWS Convertor", "version": "0.10.21-beta-dev"}},
        "components": components,
    }
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
