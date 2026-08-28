from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Required release evidence is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Release evidence is not a JSON object: {path}")
    return payload


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def finalize(version: str) -> dict[str, Any]:
    release_dir = ROOT / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    artifact_paths = [
        release_dir / f"CWS_Convertor_Portable_{version}_x64.zip",
        release_dir / f"CWS_Convertor_Setup_{version}_x64.exe",
    ]
    for path in artifact_paths:
        if not path.is_file() or path.stat().st_size <= 0:
            raise FileNotFoundError(f"Release artifact is missing or empty: {path}")

    results = ROOT / "validation" / "results" / "windows-runtime"
    evidence_paths = {
        "source": results / "source-smokes" / "VIEWER_V9_FULL_SMOKE_SUMMARY.json",
        "dist": results / "dist-packaged-runtime.json",
        "portable": results / "portable-packaged-runtime.json",
        "installed": results / "installed-packaged-runtime.json",
    }
    evidence = {name: _load_json(path) for name, path in evidence_paths.items()}
    source = evidence["source"]
    source_counts = source.get("counts") if isinstance(source.get("counts"), dict) else source
    if int(source_counts.get("failed", -1)) != 0 or int(source_counts.get("timeout", -1)) != 0:
        raise RuntimeError("Source smoke summary is not green")
    if int(source_counts.get("passed", 0)) <= 0:
        raise RuntimeError("Source smoke summary contains no passing tests")
    for label in ("dist", "portable", "installed"):
        if str(evidence[label].get("status") or "").lower() != "passed":
            raise RuntimeError(f"{label} packaged-runtime evidence is not green")
        if bool(evidence[label].get("python_on_child_path", True)):
            raise RuntimeError(f"{label} packaged-runtime test did not isolate external Python")

    artifacts = [
        {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in artifact_paths
    ]
    checksum_text = "".join(f"{item['sha256']}  {item['name']}\n" for item in artifacts)
    checksum_path = release_dir / "SHA256SUMS.txt"
    checksum_tmp = checksum_path.with_suffix(checksum_path.suffix + ".tmp")
    checksum_tmp.write_text(checksum_text, encoding="ascii")
    os.replace(checksum_tmp, checksum_path)

    manifest = {
        "schema": "cws-windows-release-manifest-1.0",
        "application": "CWS Convertor",
        "version": version,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed",
        "artifacts": artifacts,
        "validation": {
            name: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(path),
                "status": "passed",
            }
            for name, path in evidence_paths.items()
        },
        "source_smokes": {
            "passed": int(source_counts.get("passed", 0)),
            "skipped": int(source_counts.get("skipped", 0)),
            "failed": int(source_counts.get("failed", 0)),
            "timeout": int(source_counts.get("timeout", 0)),
        },
        "safety_flags": {
            "allow_approximate_manufacturing": False,
            "allow_unsafe_export": False,
            "viewer_can_override_production_gate": False,
        },
    }
    _atomic_json(release_dir / "WINDOWS_RELEASE_MANIFEST.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize and verify CWS Windows release evidence")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    manifest = finalize(args.version)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
