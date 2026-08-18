#!/usr/bin/env python3
"""Recover the checksum-exact CWS M18 authority runtime from Git history and Actions artifacts.

The script is deliberately fail-closed: it only emits a recovered runtime when
both the byte length and SHA-256 match the frozen M18 authority identity.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from typing import Iterable

TARGET_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
TARGET_SIZE = 233_402
TARGET_B64_SHA256 = "a0919bab74740db04e25b3f2782abb8427fba1a84f06e3b6e3d849b03b3a1c8b"
TARGET_B64_SIZE = 311_204
TARGET_PACKAGE_INIT = "cws_m18_authority/__init__.py"
BASE64_DATA = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
BASE64_ALL = frozenset((*BASE64_DATA, ord("=")))
ZIP_LOCAL = b"PK\x03\x04"
ZIP_CENTRAL = b"PK\x01\x02"
ZIP_EOCD = b"PK\x05\x06"
KNOWN_BOOTSTRAP_OIDS = (
    "4021d4e43a6ceee21c959c9123dc634581c164af",
    "9c219047ae5a34393f529e812e90d714ff37f047",
)


@dataclass(frozen=True)
class Hit:
    source: str
    size: int
    sha256: str
    kind: str


@dataclass(frozen=True)
class Fragment:
    source: str
    length: int
    sha256: str
    starts_with_zip_b64: bool
    ends_with_padding: bool


class RecoveryScanner:
    def __init__(self, output: Path, token: str, repository: str) -> None:
        self.output = output
        self.token = token
        self.repository = repository
        self.exact_runtime: bytes | None = None
        self.hits: list[Hit] = []
        self.fragments: dict[str, tuple[str, bytes]] = {}
        self.artifacts: list[dict] = []
        self.artifact_downloads: list[dict] = []
        self.errors: list[str] = []
        self.stats = {
            "files_scanned": 0,
            "archives_scanned": 0,
            "zip_entries_scanned": 0,
            "git_blobs_scanned": 0,
            "artifact_archives_scanned": 0,
            "bytes_scanned": 0,
        }
        self._seen_binary_sha: set[str] = set()
        self._seen_archive_sha: set[str] = set()

    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def normalize_base64(data: bytes) -> bytes:
        return bytes(value for value in data if value in BASE64_ALL)

    @staticmethod
    def data_only_base64(data: bytes) -> bytes:
        return bytes(value for value in data if value in BASE64_DATA)

    @staticmethod
    def pad_base64(data: bytes) -> bytes:
        return data + (b"=" * ((-len(data)) % 4))

    def validate_runtime(self, data: bytes, source: str, kind: str) -> bool:
        digest = self.sha256(data)
        if len(data) != TARGET_SIZE or digest != TARGET_SHA256:
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
                bad = archive.testzip()
                names = set(archive.namelist())
                if bad is not None:
                    self.errors.append(f"{source}: exact bytes but CRC failure in {bad}")
                    return False
                if TARGET_PACKAGE_INIT not in names:
                    self.errors.append(f"{source}: exact bytes but {TARGET_PACKAGE_INIT} missing")
                    return False
        except Exception as exc:
            self.errors.append(f"{source}: exact bytes but ZIP validation failed: {type(exc).__name__}: {exc}")
            return False
        self.hits.append(Hit(source=source, size=len(data), sha256=digest, kind=kind))
        if self.exact_runtime is None:
            self.exact_runtime = data
        return True

    def record_fragment(self, source: str, normalized: bytes) -> None:
        if len(normalized) < 256:
            return
        # Keep bounded candidate strings. Very large Base64 files are still useful,
        # but arbitrary binary strings are not.
        if any(value not in BASE64_ALL for value in normalized):
            return
        digest = self.sha256(normalized)
        existing = self.fragments.get(digest)
        if existing is None or len(source) < len(existing[0]):
            self.fragments[digest] = (source, normalized)

    def try_base64(self, data: bytes, source: str) -> None:
        normalized = self.normalize_base64(data)
        if len(normalized) < 256:
            return
        self.record_fragment(source, normalized)

        candidates: list[tuple[str, bytes]] = []
        if len(normalized) % 4 == 0:
            try:
                candidates.append(("strict", base64.b64decode(normalized, validate=True)))
            except (binascii.Error, ValueError):
                pass
        data_only = self.data_only_base64(normalized)
        if data_only:
            try:
                candidates.append(("repadded", base64.b64decode(self.pad_base64(data_only), validate=True)))
            except (binascii.Error, ValueError):
                pass
        seen: set[str] = set()
        for strategy, decoded in candidates:
            digest = self.sha256(decoded)
            if digest in seen:
                continue
            seen.add(digest)
            if self.validate_runtime(decoded, source, f"base64-{strategy}"):
                return
            # A malformed historic transport can contain a valid ZIP prefix/suffix.
            if decoded.startswith(ZIP_LOCAL):
                self.record_binary_zip_fragments(decoded, source + f"#{strategy}")

    def record_binary_zip_fragments(self, data: bytes, source: str) -> None:
        if not data:
            return
        # Base64 of a true prefix is coordinate-compatible with canonical Base64.
        if data.startswith(ZIP_LOCAL):
            central = data.find(ZIP_CENTRAL)
            prefix = data if central < 0 else data[:central]
            if len(prefix) >= 192:
                self.record_fragment(source + "#zip-prefix-b64", base64.b64encode(prefix))
        # A complete central-directory suffix is useful for binary-coordinate
        # coverage even when the preceding payload is missing.
        central = data.find(ZIP_CENTRAL)
        if central >= 0 and ZIP_EOCD in data[central:]:
            suffix = data[central:]
            self.record_fragment(source + "#zip-central-suffix-b64", base64.b64encode(suffix))

    def scan_bytes(self, source: str, data: bytes, depth: int = 0) -> None:
        self.stats["files_scanned"] += 1
        self.stats["bytes_scanned"] += len(data)
        digest = self.sha256(data)
        if digest in self._seen_binary_sha:
            return
        self._seen_binary_sha.add(digest)

        if self.validate_runtime(data, source, "raw"):
            return

        # Direct Base64 text or a long Base64 run inside logs/manifests.
        if data:
            legal = sum(value in BASE64_ALL or value in b" \t\r\n" for value in data)
            if legal / len(data) >= 0.92:
                self.try_base64(data, source)
            else:
                for index, match in enumerate(re.finditer(rb"[A-Za-z0-9+/=\r\n\t ]{1024,}", data)):
                    self.try_base64(match.group(0), f"{source}#base64-run-{index}")

        # Scan ZIP/TSEP/whl artifacts recursively with strict bounds.
        if depth >= 5 or len(data) < 22:
            return
        looks_zip = data.startswith(ZIP_LOCAL) or ZIP_EOCD in data[-131_072:]
        if not looks_zip:
            return
        self.record_binary_zip_fragments(data, source)
        if digest in self._seen_archive_sha:
            return
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
                infos = archive.infolist()
                self._seen_archive_sha.add(digest)
                self.stats["archives_scanned"] += 1
                total_uncompressed = 0
                for info in infos:
                    if info.is_dir():
                        continue
                    if info.file_size > 350_000_000:
                        continue
                    total_uncompressed += info.file_size
                    if total_uncompressed > 1_500_000_000:
                        self.errors.append(f"{source}: archive scan stopped at 1.5 GB uncompressed")
                        break
                    try:
                        child = archive.read(info)
                    except Exception as exc:
                        self.errors.append(f"{source}!{info.filename}: read failed: {type(exc).__name__}: {exc}")
                        continue
                    self.stats["zip_entries_scanned"] += 1
                    self.scan_bytes(f"{source}!{info.filename}", child, depth + 1)
        except zipfile.BadZipFile:
            return
        except Exception as exc:
            self.errors.append(f"{source}: ZIP scan failed: {type(exc).__name__}: {exc}")

    def api_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "cws-m18-runtime-recovery",
            },
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))

    def api_bytes(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "cws-m18-runtime-recovery",
            },
        )
        with urllib.request.urlopen(request, timeout=240) as response:
            return response.read()

    @staticmethod
    def artifact_score(artifact: dict) -> tuple[int, str]:
        name = str(artifact.get("name", "")).lower()
        score = 0
        for word, points in (
            ("m18", 100),
            ("authority", 90),
            ("u2", 80),
            ("u3", 70),
            ("u4", 70),
            ("source", 60),
            ("portable", 50),
            ("windows", 30),
            ("convertor", 20),
            ("viewer", 10),
        ):
            if word in name:
                score += points
        return score, str(artifact.get("created_at", ""))

    def scan_actions_artifacts(self, max_total_bytes: int) -> None:
        if not self.token or not self.repository:
            self.errors.append("Actions artifact scan skipped: token/repository unavailable")
            return
        owner_repo = self.repository
        page = 1
        while page <= 20:
            url = f"https://api.github.com/repos/{owner_repo}/actions/artifacts?per_page=100&page={page}"
            try:
                payload = self.api_json(url)
            except Exception as exc:
                self.errors.append(f"Artifact listing page {page} failed: {type(exc).__name__}: {exc}")
                break
            items = list(payload.get("artifacts") or [])
            self.artifacts.extend(items)
            if len(items) < 100:
                break
            page += 1

        candidates = [
            item for item in self.artifacts
            if not bool(item.get("expired")) and int(item.get("size_in_bytes") or 0) > 0
        ]
        candidates.sort(key=self.artifact_score, reverse=True)
        total = 0
        for item in candidates:
            size = int(item.get("size_in_bytes") or 0)
            score, _ = self.artifact_score(item)
            # Always inspect highly relevant artifacts; bound lower-priority bulk.
            if size > 500_000_000:
                self.artifact_downloads.append({
                    "id": item.get("id"), "name": item.get("name"), "size": size,
                    "status": "skipped-too-large", "score": score,
                })
                continue
            if total + size > max_total_bytes and score < 100:
                self.artifact_downloads.append({
                    "id": item.get("id"), "name": item.get("name"), "size": size,
                    "status": "skipped-total-cap", "score": score,
                })
                continue
            try:
                archive_bytes = self.api_bytes(str(item.get("archive_download_url")))
            except Exception as exc:
                self.artifact_downloads.append({
                    "id": item.get("id"), "name": item.get("name"), "size": size,
                    "status": f"download-failed:{type(exc).__name__}", "score": score,
                })
                self.errors.append(
                    f"Artifact {item.get('id')} {item.get('name')}: {type(exc).__name__}: {exc}"
                )
                continue
            total += len(archive_bytes)
            self.stats["artifact_archives_scanned"] += 1
            self.artifact_downloads.append({
                "id": item.get("id"), "name": item.get("name"),
                "size": size, "downloaded": len(archive_bytes),
                "status": "scanned", "score": score,
            })
            self.scan_bytes(
                f"actions-artifact:{item.get('id')}:{item.get('name')}",
                archive_bytes,
                depth=0,
            )
            if self.exact_runtime is not None:
                # Continue through high-score artifacts only long enough to record
                # duplicate provenance, but avoid needless large downloads.
                max_total_bytes = min(max_total_bytes, total + 100_000_000)

    def scan_git(self) -> None:
        try:
            subprocess.run(
                ["git", "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--tags", "--prune"],
                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180,
            )
        except Exception as exc:
            self.errors.append(f"git fetch all refs failed: {type(exc).__name__}: {exc}")

        objects: dict[str, str] = {}
        try:
            output = subprocess.check_output(
                ["git", "rev-list", "--objects", "--all"],
                text=True, errors="replace", timeout=120,
            )
            for line in output.splitlines():
                oid, _, path = line.partition(" ")
                lower = path.lower()
                if (
                    "m18" in lower
                    or "scrib" in lower
                    or lower.endswith(".b64")
                    or lower.endswith(".tsep")
                ):
                    objects.setdefault(oid, path or f"object:{oid}")
        except Exception as exc:
            self.errors.append(f"git rev-list failed: {type(exc).__name__}: {exc}")

        for oid in KNOWN_BOOTSTRAP_OIDS:
            objects.setdefault(oid, f"known-bootstrap:{oid}")

        for oid, path in sorted(objects.items(), key=lambda item: item[1]):
            try:
                kind = subprocess.check_output(
                    ["git", "cat-file", "-t", oid], text=True, timeout=15
                ).strip()
                if kind != "blob":
                    continue
                size = int(subprocess.check_output(
                    ["git", "cat-file", "-s", oid], text=True, timeout=15
                ).strip())
                if size > 500_000_000:
                    continue
                data = subprocess.check_output(["git", "cat-file", "-p", oid], timeout=60)
            except Exception:
                continue
            self.stats["git_blobs_scanned"] += 1
            self.scan_bytes(f"git:{oid}:{path}", data)

        # Also scan relevant working-tree files in case the object path listing is
        # incomplete for the checked-out ref.
        for path in sorted(Path(".").rglob("*")):
            if not path.is_file():
                continue
            lower = path.as_posix().lower()
            if "m18" not in lower and not lower.endswith((".b64", ".zip", ".tsep")):
                continue
            try:
                if path.stat().st_size <= 500_000_000:
                    self.scan_bytes(f"worktree:{path.as_posix()}", path.read_bytes())
            except OSError:
                pass

    @staticmethod
    def overlap(a: bytes, b: bytes, minimum: int = 64) -> int:
        if len(a) < minimum or len(b) < minimum:
            return 0
        # Find occurrences of the right-hand 64-byte prefix near the tail of the
        # left-hand value. Random Base64 makes that anchor effectively unique and
        # avoids quadratic byte-by-byte suffix scans.
        anchor = b[:minimum]
        start = max(0, len(a) - len(b))
        position = a.find(anchor, start)
        best = 0
        while position >= 0:
            length = len(a) - position
            if minimum <= length <= len(b) and a[position:] == b[:length]:
                best = max(best, length)
            position = a.find(anchor, position + 1)
        return best

    def assemble_fragments(self) -> list[dict]:
        raw = [(source, value) for source, value in self.fragments.values()]
        # Remove fragments contained in a longer fragment.
        raw.sort(key=lambda item: len(item[1]), reverse=True)
        retained: list[tuple[list[str], bytes]] = []
        for source, value in raw:
            if any(value in existing for _, existing in retained):
                continue
            retained.append(([source], value))
            if len(retained) >= 400:
                break

        # Greedy exact-overlap assembly. It cannot manufacture missing bytes and
        # is used for diagnostics only; recovered authority still requires the
        # fixed SHA-256 identity.
        while True:
            best: tuple[int, int, int] | None = None
            for i, (_, left) in enumerate(retained):
                for j, (_, right) in enumerate(retained):
                    if i == j:
                        continue
                    ov = self.overlap(left, right)
                    if ov and (best is None or ov > best[0]):
                        best = (ov, i, j)
            if best is None:
                break
            ov, i, j = best
            left_sources, left = retained[i]
            right_sources, right = retained[j]
            merged = (left_sources + right_sources, left + right[ov:])
            retained = [
                item for index, item in enumerate(retained)
                if index not in (i, j)
            ]
            retained.append(merged)

        retained.sort(key=lambda item: len(item[1]), reverse=True)
        report: list[dict] = []
        for sources, value in retained[:50]:
            item = {
                "length": len(value),
                "sha256": self.sha256(value),
                "source_count": len(sources),
                "sources": sources[:20],
                "starts_with_canonical_zip_prefix": value.startswith(b"UEsDB"),
                "ends_with_padding": value.endswith(b"="),
            }
            # Only an exact full-length/identity Base64 transport is accepted.
            if len(value) == TARGET_B64_SIZE and self.sha256(value) == TARGET_B64_SHA256:
                try:
                    decoded = base64.b64decode(value, validate=True)
                except Exception as exc:
                    self.errors.append(f"Assembled canonical Base64 decode failed: {exc}")
                else:
                    if self.validate_runtime(decoded, "assembled-fragments", "assembled-base64"):
                        item["exact_runtime"] = True
            report.append(item)
        return report

    def emit(self) -> None:
        self.output.mkdir(parents=True, exist_ok=True)
        fragment_rows = [
            Fragment(
                source=source,
                length=len(value),
                sha256=digest,
                starts_with_zip_b64=value.startswith(b"UEsDB"),
                ends_with_padding=value.endswith(b"="),
            )
            for digest, (source, value) in self.fragments.items()
        ]
        fragment_rows.sort(key=lambda row: row.length, reverse=True)
        assembled = self.assemble_fragments()

        recovered = self.exact_runtime is not None
        if recovered:
            runtime = self.exact_runtime or b""
            runtime_path = self.output / "m18_authority_runtime.zip"
            runtime_path.write_bytes(runtime)
            encoded = base64.b64encode(runtime)
            assert len(encoded) == TARGET_B64_SIZE
            assert self.sha256(encoded) == TARGET_B64_SHA256
            (self.output / "m18_authority_runtime.b64").write_bytes(encoded)
            chunks = self.output / "m18_payload_canonical"
            chunks.mkdir(exist_ok=True)
            offsets = [16_000] + ([8_000] * 36) + [7_204]
            assert sum(offsets) == TARGET_B64_SIZE
            cursor = 0
            for index, size in enumerate(offsets, 1):
                payload = encoded[cursor:cursor + size]
                cursor += size
                (chunks / f"m18_authority_runtime.b64.{index:03d}").write_bytes(payload)
            assert cursor == len(encoded)

        report = {
            "schema": "cws-m18-runtime-recovery-v2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repository": self.repository,
            "target": {
                "runtime_size": TARGET_SIZE,
                "runtime_sha256": TARGET_SHA256,
                "base64_size": TARGET_B64_SIZE,
                "base64_sha256": TARGET_B64_SHA256,
            },
            "recovered": recovered,
            "hits": [asdict(hit) for hit in self.hits],
            "stats": self.stats,
            "artifact_count": len(self.artifacts),
            "artifact_downloads": self.artifact_downloads,
            "fragment_count": len(fragment_rows),
            "fragments": [asdict(row) for row in fragment_rows[:200]],
            "assembled_contigs": assembled,
            "errors": self.errors[:500],
        }
        (self.output / "recovery_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
        lines = [
            "# CWS M18 runtime recovery",
            "",
            f"- Recovered: **{recovered}**",
            f"- Target runtime: `{TARGET_SIZE}` bytes / `{TARGET_SHA256}`",
            f"- Actions artifacts listed: **{len(self.artifacts)}**",
            f"- Actions artifacts scanned: **{self.stats['artifact_archives_scanned']}**",
            f"- Git blobs scanned: **{self.stats['git_blobs_scanned']}**",
            f"- Candidate Base64 fragments: **{len(fragment_rows)}**",
            f"- Exact hits: **{len(self.hits)}**",
            "",
            "## Largest assembled contigs",
            "",
        ]
        for item in assembled[:15]:
            lines.append(
                f"- {item['length']} chars; sources={item['source_count']}; "
                f"sha256=`{item['sha256']}`"
            )
        if self.hits:
            lines.extend(["", "## Exact provenance", ""])
            for hit in self.hits:
                lines.append(f"- `{hit.source}` ({hit.kind})")
        if self.errors:
            lines.extend(["", "## Scanner warnings", ""])
            for value in self.errors[:25]:
                lines.append(f"- {value}")
        (self.output / "recovery_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="recovery-output")
    parser.add_argument("--max-artifact-bytes", type=int, default=1_500_000_000)
    parser.add_argument("--skip-artifacts", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    scanner = RecoveryScanner(output=output, token=token, repository=repository)
    scanner.scan_git()
    if not args.skip_artifacts:
        scanner.scan_actions_artifacts(max_total_bytes=args.max_artifact_bytes)
    scanner.emit()
    print((output / "recovery_report.md").read_text(encoding="utf-8"))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.write(f"recovered={'true' if scanner.exact_runtime is not None else 'false'}\n")
            handle.write(f"hit_count={len(scanner.hits)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
