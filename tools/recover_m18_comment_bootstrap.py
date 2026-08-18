#!/usr/bin/env python3
"""Recover the exact frozen M18 runtime from checksum-bound PR comment parts.

This diagnostic never accepts a replacement authority identity.  A recovered
object is emitted only when both its byte size and SHA-256 match the frozen M18
runtime contract.
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
import tarfile
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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def padded_base64_data(value: bytes) -> bytes:
    data = bytes(item for item in value if item in B64_DATA)
    return data + (b"=" * ((-len(data)) % 4))


def decode_strict(value: bytes) -> bytes:
    return base64.b64decode(value, validate=True)


def load_parts() -> tuple[list[int], dict[int, dict[str, Any]]]:
    comments = json.loads((ROOT / "comments.json").read_text(encoding="utf-8"))
    parts: dict[int, dict[str, Any]] = {}
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
    totals = {int(item["total"]) for item in parts.values()}
    if len(totals) != 1:
        raise SystemExit(f"Inconsistent total counts: {sorted(totals)}")
    total = totals.pop()
    expected = list(range(1, total + 1))
    if sorted(parts) != expected:
        raise SystemExit(f"Incomplete bootstrap set: expected={expected} observed={sorted(parts)}")
    return expected, parts


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    expected, parts = load_parts()
    total = len(expected)
    report: dict[str, Any] = {
        "schema": "cws-u4-m18-comment-bootstrap-recovery-1.1",
        "target_sha256": TARGET,
        "target_size": TARGET_SIZE,
        "part_count": total,
        "parts": [],
        "candidates": [],
        "matches": [],
        "embedded_zip_findings": [],
        "decompression_findings": [],
    }

    decoded_by_part: dict[int, bytes] = {}
    for index in expected:
        item = parts[index]
        raw_b = item["payload_raw"].encode("utf-8")
        stripped_b = item["payload_stripped"].encode("utf-8")
        clean_b = item["payload_clean"]
        data_only = bytes(value for value in clean_b if value in B64_DATA)
        allowed_only = bytes(value for value in clean_b if value in B64_ALL)
        hashes = {
            "raw_text": sha256(raw_b),
            "stripped_text": sha256(stripped_b),
            "clean_text": sha256(clean_b),
            "data_only_text": sha256(data_only),
        }
        decode_attempts: dict[str, Any] = {}
        decoded: bytes | None = None
        for strategy, encoded in (
            ("clean-strict", allowed_only),
            ("data-only-repadded", padded_base64_data(data_only)),
        ):
            try:
                candidate = decode_strict(encoded)
                digest = sha256(candidate)
                decode_attempts[strategy] = {
                    "ok": True,
                    "size": len(candidate),
                    "sha256": digest,
                    "prefix_hex": candidate[:24].hex(),
                    "matches_declared": digest == item["declared_sha256"],
                }
                if decoded is None:
                    decoded = candidate
            except Exception as exc:  # diagnostic detail is intentional
                decode_attempts[strategy] = {
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        text_match_modes = [name for name, digest in hashes.items() if digest == item["declared_sha256"]]
        if decoded is not None:
            decoded_by_part[index] = decoded
        (ROOT / f"bootstrap_part_{index:02d}.txt").write_text(
            item["payload_stripped"] + "\n", encoding="utf-8"
        )
        if decoded is not None:
            (ROOT / f"bootstrap_part_{index:02d}.bin").write_bytes(decoded)
        report["parts"].append(
            {
                "index": index,
                "total": int(item["total"]),
                "comment_id": item["comment_id"],
                "comment_url": item["comment_url"],
                "declared_sha256": item["declared_sha256"],
                "raw_chars": len(item["payload_raw"]),
                "clean_chars": len(clean_b),
                "clean_mod4": len(clean_b) % 4,
                "invalid_non_whitespace_bytes": sorted(
                    {value for value in clean_b if value not in B64_ALL}
                ),
                "text_hashes": hashes,
                "declared_text_match_modes": text_match_modes,
                "decode_attempts": decode_attempts,
            }
        )

    binary_candidates: list[tuple[str, bytes]] = []

    def register(label: str, data: bytes, metadata: dict[str, Any] | None = None) -> bool:
        digest = sha256(data)
        record: dict[str, Any] = {
            "label": label,
            "size": len(data),
            "sha256": digest,
            "prefix_hex": data[:32].hex(),
            "suffix_hex": data[-32:].hex() if data else "",
        }
        if metadata:
            record.update(metadata)
        report["candidates"].append(record)
        exact = digest == TARGET and len(data) == TARGET_SIZE
        if exact:
            report["matches"].append(record)
            (ROOT / "m18_authority_runtime.zip").write_bytes(data)
        return exact

    ordered = [parts[index] for index in expected]
    joined_raw = "".join(item["payload_raw"] for item in ordered).encode("utf-8")
    joined_stripped = "".join(item["payload_stripped"] for item in ordered).encode("utf-8")
    joined_clean = b"".join(item["payload_clean"] for item in ordered)
    joined_allowed = bytes(value for value in joined_clean if value in B64_ALL)
    register("joined-raw-text", joined_raw)
    register("joined-stripped-text", joined_stripped)
    register("joined-clean-text", joined_clean)

    for label, encoded in (
        ("joined-clean-strict", joined_allowed),
        ("joined-data-only-repadded", padded_base64_data(joined_clean)),
    ):
        try:
            decoded = decode_strict(encoded)
            binary_candidates.append((label, decoded))
            register(label, decoded)
            (ROOT / f"{label}.bin").write_bytes(decoded)
        except Exception as exc:
            report["candidates"].append(
                {"label": label, "decode_error": f"{type(exc).__name__}: {exc}"}
            )

    if len(decoded_by_part) == total:
        segmented = b"".join(decoded_by_part[index] for index in expected)
        binary_candidates.append(("segmented-decoded-ordered", segmented))
        register("segmented-decoded-ordered", segmented)
        (ROOT / "segmented-decoded-ordered.bin").write_bytes(segmented)

    # Exhaustively test all segment orders when the set is small.  This is a
    # checksum search, not authority relaxation: only the frozen target wins.
    if total <= 8:
        for permutation in itertools.permutations(expected):
            if list(permutation) == expected:
                continue
            perm_label = "-".join(map(str, permutation))
            perm_clean = b"".join(parts[index]["payload_clean"] for index in permutation)
            try:
                decoded = decode_strict(padded_base64_data(perm_clean))
            except Exception:
                decoded = b""
            if decoded and sha256(decoded) == TARGET and len(decoded) == TARGET_SIZE:
                register(
                    "permuted-continuous-" + perm_label,
                    decoded,
                    {"permutation": list(permutation)},
                )
                binary_candidates.append(("permuted-continuous-" + perm_label, decoded))
                break
            if len(decoded_by_part) == total:
                segmented = b"".join(decoded_by_part[index] for index in permutation)
                if sha256(segmented) == TARGET and len(segmented) == TARGET_SIZE:
                    register(
                        "permuted-segmented-" + perm_label,
                        segmented,
                        {"permutation": list(permutation)},
                    )
                    binary_candidates.append(("permuted-segmented-" + perm_label, segmented))
                    break

    decompressors: tuple[tuple[str, Callable[[bytes], bytes]], ...] = (
        ("gzip", gzip.decompress),
        ("bz2", bz2.decompress),
        ("lzma", lzma.decompress),
        ("zlib", zlib.decompress),
        ("zlib-raw", lambda value: zlib.decompress(value, -zlib.MAX_WBITS)),
        ("zlib-gzip-auto", lambda value: zlib.decompress(value, zlib.MAX_WBITS | 32)),
    )
    seen_binary: set[str] = set()
    for label, data in list(binary_candidates):
        digest = sha256(data)
        if digest in seen_binary:
            continue
        seen_binary.add(digest)

        cursor = 0
        starts: list[int] = []
        while True:
            pos = data.find(b"PK\x03\x04", cursor)
            if pos < 0:
                break
            starts.append(pos)
            cursor = pos + 1
        for pos in starts[:200]:
            suffix = data[pos:]
            try:
                with zipfile.ZipFile(BytesIO(suffix)) as archive:
                    bad = archive.testzip()
                    names = archive.namelist()
                finding = {
                    "source": label,
                    "offset": pos,
                    "suffix_size": len(suffix),
                    "suffix_sha256": sha256(suffix),
                    "entry_count": len(names),
                    "crc_error": bad,
                    "first_entries": names[:12],
                }
                report["embedded_zip_findings"].append(finding)
                if finding["suffix_sha256"] == TARGET and len(suffix) == TARGET_SIZE:
                    register(f"embedded-zip-{label}-{pos}", suffix, finding)
            except Exception:
                pass

        for method, decoder in decompressors:
            try:
                output = decoder(data)
            except Exception:
                continue
            finding = {
                "source": label,
                "method": method,
                "size": len(output),
                "sha256": sha256(output),
                "prefix_hex": output[:32].hex(),
            }
            report["decompression_findings"].append(finding)
            register(f"decompressed-{method}-{label}", output)
            (ROOT / f"decompressed-{method}-{label}.bin").write_bytes(output)

        try:
            with tarfile.open(fileobj=BytesIO(data), mode="r:*") as archive:
                names = archive.getnames()
            report["decompression_findings"].append(
                {
                    "source": label,
                    "method": "tar",
                    "entry_count": len(names),
                    "first_entries": names[:12],
                }
            )
        except Exception:
            pass

    result_path = ROOT / "m18_authority_runtime.zip"
    recovered = result_path.is_file()
    if recovered:
        runtime = result_path.read_bytes()
        if len(runtime) != TARGET_SIZE or sha256(runtime) != TARGET:
            raise SystemExit("Internal recovery mismatch")
        with zipfile.ZipFile(BytesIO(runtime)) as archive:
            bad = archive.testzip()
            names = archive.namelist()
            if bad is not None:
                raise SystemExit(f"Recovered ZIP CRC error: {bad}")
            if "cws_m18_authority/__init__.py" not in names:
                raise SystemExit("Recovered ZIP misses cws_m18_authority/__init__.py")
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
            "payload_sha256": sha256(payload),
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

    report["status"] = "recovered" if recovered else "not_recovered"
    (ROOT / "diagnostic.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = [
        "# U4 M18 comment-bootstrap recovery",
        "",
        f"- Status: **{report['status']}**",
        f"- Parts: **{total}**",
        f"- Exact target: `{TARGET}` / `{TARGET_SIZE}` bytes",
        f"- Candidate records: **{len(report['candidates'])}**",
        f"- Embedded valid ZIP findings: **{len(report['embedded_zip_findings'])}**",
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
