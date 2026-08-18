#!/usr/bin/env python3
"""Expand the checksum-verified CWS Part-First Foundation source overlay."""
from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import Path
from zipfile import ZipFile

EXPECTED_SHA256 = "068514d04f9b5b6ef5fc5ad28ac68e0e5cef99bbed9050c9cbe37c64adb8e37b"
EXPECTED_CHUNKS = 6


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--keep-zip", action="store_true")
    args = parser.parse_args()

    repo = args.repo.resolve()
    destination = (args.destination or repo).resolve()
    chunks = sorted((repo / ".foundation").glob("chunk-*.b64"))
    if len(chunks) != EXPECTED_CHUNKS:
        raise SystemExit(f"expected {EXPECTED_CHUNKS} chunks, found {len(chunks)}")

    encoded = "".join(path.read_text(encoding="ascii").strip() for path in chunks)
    payload = base64.b64decode(encoded, validate=True)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"checksum mismatch: expected {EXPECTED_SHA256}, got {actual}")

    destination.mkdir(parents=True, exist_ok=True)
    zip_path = destination / "CWS_Convertor_PartFirst_Foundation_SOURCE.zip"
    zip_path.write_bytes(payload)
    with ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"invalid source archive member: {bad}")
        archive.extractall(destination)
    if not args.keep_zip:
        zip_path.unlink()
    print(f"expanded verified foundation source into {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
