#!/usr/bin/env python3
"""Collect repository evidence relevant to exact M18 runtime recovery.

The collector is read-only.  It stores unique historical blobs, their paths and
commit/ref context so the recovery can be reproduced without relying on UI
truncation or copied binary text.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("EVIDENCE_ROOT", "recovery/evidence"))
MAX_BLOB_SIZE = int(os.environ.get("EVIDENCE_MAX_BLOB_SIZE", str(5 * 1024 * 1024)))
TARGET_SHA256 = os.environ.get(
    "TARGET_SHA256",
    "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1",
).lower()
KEYWORDS = (
    "m18",
    "authority",
    "bootstrap",
    "payload",
    "scribing",
    "u4-",
    "unified-u2",
)
CONTENT_MARKERS = (
    TARGET_SHA256.encode("ascii"),
    b"M18_BOOTSTRAP_V1",
    b"m18_authority_runtime",
    b"cws_m18_authority",
)


def run(*args: str, check: bool = True) -> bytes:
    result = subprocess.run(args, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")[:180] or "unnamed"


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    blobs_dir = ROOT / "git_blobs"
    blobs_dir.mkdir(exist_ok=True)

    refs = run("git", "for-each-ref", "--format=%(refname) %(objectname) %(subject)").decode(
        "utf-8", errors="replace"
    )
    (ROOT / "refs.txt").write_text(refs, encoding="utf-8")
    log = run(
        "git",
        "log",
        "--all",
        "--decorate=full",
        "--date=iso-strict",
        "--format=COMMIT %H%nPARENTS %P%nDATE %ad%nREFS %D%nSUBJECT %s%nBODY%n%b%nEND-COMMIT",
    ).decode("utf-8", errors="replace")
    (ROOT / "all_commit_messages.txt").write_text(log, encoding="utf-8")

    object_lines = run("git", "rev-list", "--objects", "--all").decode(
        "utf-8", errors="surrogateescape"
    ).splitlines()
    paths_by_oid: dict[str, set[str]] = defaultdict(set)
    for line in object_lines:
        oid, separator, path = line.partition(" ")
        if separator:
            paths_by_oid[oid].add(path)
    (ROOT / "rev_list_objects.txt").write_text("\n".join(object_lines) + "\n", encoding="utf-8")

    metadata: list[dict[str, Any]] = []
    exact_matches: list[dict[str, Any]] = []
    marker_matches: list[dict[str, Any]] = []
    for oid, paths in sorted(paths_by_oid.items()):
        relevant_path = any(any(keyword in path.lower() for keyword in KEYWORDS) for path in paths)
        try:
            object_type = run("git", "cat-file", "-t", oid).decode("ascii").strip()
        except subprocess.CalledProcessError:
            continue
        if object_type != "blob":
            continue
        size = int(run("git", "cat-file", "-s", oid).decode("ascii").strip())
        if size > MAX_BLOB_SIZE:
            if relevant_path:
                metadata.append(
                    {
                        "oid": oid,
                        "size": size,
                        "paths": sorted(paths),
                        "stored": False,
                        "reason": "size_limit",
                    }
                )
            continue
        data = run("git", "cat-file", "blob", oid)
        digest = hashlib.sha256(data).hexdigest()
        markers = [marker.decode("ascii") for marker in CONTENT_MARKERS if marker in data]
        relevant = relevant_path or bool(markers) or digest == TARGET_SHA256
        if not relevant:
            continue
        suffix = ".txt" if b"\x00" not in data[:8192] else ".bin"
        output = blobs_dir / f"{oid}{suffix}"
        output.write_bytes(data)
        record = {
            "oid": oid,
            "size": size,
            "sha256": digest,
            "paths": sorted(paths),
            "stored": True,
            "file": str(output.relative_to(ROOT)),
            "markers": markers,
        }
        metadata.append(record)
        if digest == TARGET_SHA256:
            exact_matches.append(record)
        if markers:
            marker_matches.append(record)

    # Record every historical commit that touched the key payload paths.  This
    # gives exact ordering and makes branch-only objects visible in diagnostics.
    path_history: dict[str, list[str]] = {}
    interesting_paths = sorted(
        {
            path
            for paths in paths_by_oid.values()
            for path in paths
            if any(keyword in path.lower() for keyword in KEYWORDS)
        }
    )
    for path in interesting_paths:
        try:
            commits = run("git", "log", "--all", "--format=%H", "--", path).decode("ascii").split()
        except subprocess.CalledProcessError:
            commits = []
        if commits:
            path_history[path] = commits

    report = {
        "schema": "cws-m18-recovery-evidence-1.0",
        "target_sha256": TARGET_SHA256,
        "max_blob_size": MAX_BLOB_SIZE,
        "object_count": len(paths_by_oid),
        "stored_blob_count": sum(1 for item in metadata if item.get("stored")),
        "exact_matches": exact_matches,
        "marker_matches": marker_matches,
        "blobs": metadata,
        "path_history": path_history,
    }
    (ROOT / "git_evidence.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "object_count": report["object_count"],
                "stored_blob_count": report["stored_blob_count"],
                "exact_match_count": len(exact_matches),
                "marker_match_count": len(marker_matches),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
