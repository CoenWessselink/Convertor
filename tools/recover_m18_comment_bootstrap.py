#!/usr/bin/env python3
"""Inspect and, only when complete, recover the checksum-bound M18 runtime.

A diagnostic success means the transport was inspected correctly.  It does not
mean the runtime was recovered.  Recovery is reported separately and requires
an exact byte-size and SHA-256 match with the frozen authority identity.
"""
from __future__ import annotations

import base64
import bz2
import gzip
import hashlib
import itertools
import json
import lzma
import os
import re
import string
import zlib
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable

ROOT = Path(os.environ.get("RECOVERY_ROOT", "recovery"))
TARGET = os.environ["TARGET_SHA256"].lower()
TARGET_SIZE = int(os.environ["TARGET_SIZE"])
HEADER = re.compile(
    r"^M18_BOOTSTRAP_V1\s+part=(\d+)/(\d+)\s+sha256=([0-9a-fA-F]{64})\n(.*)\Z",
    re.DOTALL,
)
B64_DATA = set((string.ascii_letters + string.digits + "+/").encode("ascii"))
B64_ALL = B64_DATA | {ord("=")}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def data_only_padded(value: bytes) -> bytes:
    data = bytes(item for item in value if item in B64_DATA)
    return data + (b"=" * ((-len(data)) % 4))


def strict_decode(value: bytes) -> bytes:
    return base64.b64decode(value, validate=True)


def parse_comments() -> tuple[int, dict[int, dict[str, Any]]]:
    comments = json.loads((ROOT / "comments.json").read_text(encoding="utf-8"))
    parts: dict[int, dict[str, Any]] = {}
    totals: set[int] = set()
    for comment in comments:
        body = str(comment.get("body") or "").replace("\r\n", "\n").replace("\r", "\n")
        match = HEADER.match(body)
        if not match:
            continue
        index = int(match.group(1))
        total = int(match.group(2))
        declared = match.group(3).lower()
        payload_raw = match.group(4)
        if index in parts:
            raise SystemExit(f"Duplicate bootstrap part {index}")
        totals.add(total)
        parts[index] = {
            "index": index,
            "total": total,
            "declared_sha256": declared,
            "comment_id": comment.get("id"),
            "comment_url": comment.get("html_url"),
            "payload_raw": payload_raw,
            "payload_stripped": payload_raw.strip(),
            "payload_clean": b"".join(payload_raw.encode("utf-8").split()),
        }
    if not parts:
        raise SystemExit("No M18_BOOTSTRAP_V1 comments found")
    if len(totals) != 1:
        raise SystemExit(f"Inconsistent total counts: {sorted(totals)}")
    return totals.pop(), parts


def validate_exact_zip(data: bytes) -> list[str]:
    if len(data) != TARGET_SIZE or digest(data) != TARGET:
        raise ValueError("candidate does not match frozen runtime identity")
    with zipfile.ZipFile(BytesIO(data)) as archive:
        bad = archive.testzip()
        names = archive.namelist()
    if bad is not None:
        raise ValueError(f"runtime ZIP CRC error: {bad}")
    if "cws_m18_authority/__init__.py" not in names:
        raise ValueError("runtime ZIP misses cws_m18_authority/__init__.py")
    return names


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    total, parts = parse_comments()
    observed = sorted(parts)
    expected = list(range(1, total + 1))
    missing = [index for index in expected if index not in parts]
    report: dict[str, Any] = {
        "schema": "cws-u4-m18-comment-bootstrap-recovery-1.2",
        "target_sha256": TARGET,
        "target_size": TARGET_SIZE,
        "declared_part_count": total,
        "observed_parts": observed,
        "missing_parts": missing,
        "transport_complete": not missing,
        "parts": [],
        "candidates": [],
        "matches": [],
        "decompression_findings": [],
    }

    decoded_by_part: dict[int, bytes] = {}
    for index in observed:
        item = parts[index]
        raw = item["payload_raw"].encode("utf-8")
        stripped = item["payload_stripped"].encode("utf-8")
        clean = item["payload_clean"]
        allowed = bytes(value for value in clean if value in B64_ALL)
        data = bytes(value for value in clean if value in B64_DATA)
        hashes = {
            "raw_text": digest(raw),
            "stripped_text": digest(stripped),
            "clean_text": digest(clean),
            "data_only_text": digest(data),
        }
        attempts: dict[str, Any] = {}
        first_decoded: bytes | None = None
        for strategy, encoded in (
            ("clean-strict", allowed),
            ("data-only-repadded", data_only_padded(data)),
        ):
            try:
                decoded = strict_decode(encoded)
                if first_decoded is None:
                    first_decoded = decoded
                attempts[strategy] = {
                    "ok": True,
                    "size": len(decoded),
                    "sha256": digest(decoded),
                    "prefix_hex": decoded[:32].hex(),
                    "matches_declared": digest(decoded) == item["declared_sha256"],
                }
            except Exception as exc:
                attempts[strategy] = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        if first_decoded is not None:
            decoded_by_part[index] = first_decoded
            (ROOT / f"bootstrap_part_{index:02d}.bin").write_bytes(first_decoded)
        (ROOT / f"bootstrap_part_{index:02d}.txt").write_text(
            item["payload_stripped"] + "\n", encoding="utf-8"
        )
        report["parts"].append(
            {
                "index": index,
                "total": total,
                "comment_id": item["comment_id"],
                "comment_url": item["comment_url"],
                "declared_sha256": item["declared_sha256"],
                "raw_chars": len(item["payload_raw"]),
                "clean_chars": len(clean),
                "clean_mod4": len(clean) % 4,
                "invalid_non_whitespace_bytes": sorted(
                    {value for value in clean if value not in B64_ALL}
                ),
                "text_hashes": hashes,
                "declared_text_match_modes": [
                    name for name, value in hashes.items() if value == item["declared_sha256"]
                ],
                "decode_attempts": attempts,
            }
        )

    binary_candidates: list[tuple[str, bytes]] = []

    def register(label: str, data: bytes, metadata: dict[str, Any] | None = None) -> bool:
        record: dict[str, Any] = {
            "label": label,
            "size": len(data),
            "sha256": digest(data),
            "prefix_hex": data[:32].hex(),
            "suffix_hex": data[-32:].hex() if data else "",
        }
        if metadata:
            record.update(metadata)
        report["candidates"].append(record)
        exact = record["sha256"] == TARGET and record["size"] == TARGET_SIZE
        if exact:
            validate_exact_zip(data)
            report["matches"].append(record)
            (ROOT / "m18_authority_runtime.zip").write_bytes(data)
        return exact

    if not missing:
        joined_clean = b"".join(parts[index]["payload_clean"] for index in expected)
        register("joined-clean-text", joined_clean)
        for label, encoded in (
            ("joined-clean-strict", bytes(value for value in joined_clean if value in B64_ALL)),
            ("joined-data-only-repadded", data_only_padded(joined_clean)),
        ):
            try:
                decoded = strict_decode(encoded)
            except Exception as exc:
                report["candidates"].append(
                    {"label": label, "decode_error": f"{type(exc).__name__}: {exc}"}
                )
                continue
            binary_candidates.append((label, decoded))
            register(label, decoded)
            (ROOT / f"{label}.bin").write_bytes(decoded)
        if len(decoded_by_part) == total:
            segmented = b"".join(decoded_by_part[index] for index in expected)
            binary_candidates.append(("segmented-decoded-ordered", segmented))
            register("segmented-decoded-ordered", segmented)
            (ROOT / "segmented-decoded-ordered.bin").write_bytes(segmented)

        if total <= 8:
            for permutation in itertools.permutations(expected):
                if list(permutation) == expected:
                    continue
                label = "-".join(map(str, permutation))
                clean = b"".join(parts[index]["payload_clean"] for index in permutation)
                try:
                    candidate = strict_decode(data_only_padded(clean))
                except Exception:
                    candidate = b""
                if candidate and register(
                    "permuted-continuous-" + label,
                    candidate,
                    {"permutation": list(permutation)},
                ):
                    binary_candidates.append(("permuted-continuous-" + label, candidate))
                    break
                if len(decoded_by_part) == total:
                    candidate = b"".join(decoded_by_part[index] for index in permutation)
                    if register(
                        "permuted-segmented-" + label,
                        candidate,
                        {"permutation": list(permutation)},
                    ):
                        binary_candidates.append(("permuted-segmented-" + label, candidate))
                        break

    decompressors: tuple[tuple[str, Callable[[bytes], bytes]], ...] = (
        ("gzip", gzip.decompress),
        ("bz2", bz2.decompress),
        ("lzma", lzma.decompress),
        ("zlib", zlib.decompress),
        ("zlib-raw", lambda value: zlib.decompress(value, -zlib.MAX_WBITS)),
        ("zlib-gzip-auto", lambda value: zlib.decompress(value, zlib.MAX_WBITS | 32)),
    )
    seen: set[str] = set()
    for label, data in binary_candidates:
        if digest(data) in seen:
            continue
        seen.add(digest(data))
        for method, decoder in decompressors:
            try:
                output = decoder(data)
            except Exception:
                continue
            finding = {
                "source": label,
                "method": method,
                "size": len(output),
                "sha256": digest(output),
                "prefix_hex": output[:32].hex(),
            }
            report["decompression_findings"].append(finding)
            register(f"decompressed-{method}-{label}", output)

    result = ROOT / "m18_authority_runtime.zip"
    recovered = result.is_file()
    if recovered:
        runtime = result.read_bytes()
        names = validate_exact_zip(runtime)
        encoded = base64.b64encode(runtime).decode("ascii")
        chunk_size = 16000
        chunks = [encoded[pos : pos + chunk_size] for pos in range(0, len(encoded), chunk_size)]
        canonical = ROOT / "canonical_payload"
        canonical.mkdir(exist_ok=True)
        for number, chunk in enumerate(chunks, 1):
            (canonical / f"m18_authority_runtime.b64.{number:03d}").write_text(
                chunk + "\n", encoding="ascii"
            )
        payload = "".join(chunks).encode("ascii")
        manifest = {
            "runtime_sha256": TARGET,
            "runtime_size": TARGET_SIZE,
            "payload_sha256": digest(payload),
            "payload_chars": len(payload),
            "chunk_count": len(chunks),
            "chunk_size": chunk_size,
            "zip_entries": len(names),
            "first_entries": names[:20],
        }
        (canonical / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        report["canonical_payload"] = manifest

    if recovered:
        status = "recovered"
    elif missing:
        status = "incomplete_transport"
    else:
        status = "complete_but_not_recovered"
    report["status"] = status
    (ROOT / "diagnostic.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = [
        "# U4 M18 comment-bootstrap recovery",
        "",
        f"- Diagnostic status: **{status}**",
        f"- Declared parts: **{total}**",
        f"- Observed parts: **{observed}**",
        f"- Missing parts: **{missing or 'none'}**",
        f"- Exact target: `{TARGET}` / `{TARGET_SIZE}` bytes",
        f"- Exact matches: **{len(report['matches'])}**",
        "",
        "## Part verification",
    ]
    for item in report["parts"]:
        summary.append(
            f"- part {item['index']}/{item['total']}: chars={item['clean_chars']}, "
            f"declared text matches={item['declared_text_match_modes'] or 'none'}, "
            f"invalid bytes={item['invalid_non_whitespace_bytes']}"
        )
    (ROOT / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
