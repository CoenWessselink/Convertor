"""Portable `.cwsreview` package builder and verifier.

The package is a ZIP container with explicit JSON contracts and SHA-256
checksums.  It intentionally excludes source models by default; model
references are metadata only unless an explicit future option copies them.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
import zipfile

from .model import MarkupRecord, ReviewIssue

SCHEMA = "cws-review-package-1.0"
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n").encode("utf-8")


def _safe_name(value: str) -> str:
    name = PurePosixPath(str(value).replace("\\", "/")).name
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:180] or "asset.bin"


def _zip_write(z: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


class ReviewPackageBuilder:
    def build(
        self,
        output_path: str | Path,
        *,
        project: dict[str, Any],
        clashes: Iterable[Any] = (),
        issues: Iterable[ReviewIssue] = (),
        markups: Iterable[MarkupRecord] = (),
        model_references: Iterable[dict[str, Any]] = (),
        assets_root: str | Path | None = None,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        clashes_list = [r.to_dict() if hasattr(r, "to_dict") else dict(r) for r in clashes]
        issues_list = [i.to_dict() for i in issues]
        markups_list = [m.to_dict() for m in markups]
        comments = [dict(comment, issue_id=issue["issue_id"]) for issue in issues_list for comment in issue.get("comments", [])]
        comments += [dict(comment, clash_id=clash["clash_id"]) for clash in clashes_list for comment in clash.get("comments", [])]
        audit = [dict(event, issue_id=issue["issue_id"]) for issue in issues_list for event in issue.get("audit_events", [])]
        audit += [dict(event, clash_id=clash["clash_id"]) for clash in clashes_list for event in clash.get("audit_events", [])]
        files: dict[str, bytes] = {
            "project.json": _json_bytes(project),
            "clashes.json": _json_bytes(clashes_list),
            "issues.json": _json_bytes(issues_list),
            "comments.json": _json_bytes(comments),
            "audit.json": _json_bytes(audit),
            "markups.json": _json_bytes(markups_list),
            "model_references.json": _json_bytes(list(model_references)),
        }
        # Persist viewpoints as independent files for stable linking.
        for clash in clashes_list:
            for viewpoint in clash.get("viewpoints", []) or []:
                viewpoint_id = str(viewpoint.get("viewpoint_id") or "")
                if viewpoint_id:
                    files[f"viewpoints/{_safe_name(viewpoint_id)}.json"] = _json_bytes(viewpoint)
        root = Path(assets_root).resolve() if assets_root else None
        if root and root.is_dir():
            for clash in clashes_list:
                for shot in clash.get("screenshots", []) or []:
                    rel = str(shot.get("path") or "").strip()
                    directory = str(shot.get("asset_directory") or "").strip()
                    candidates = [root / rel]
                    if directory:
                        candidates.insert(0, root / directory / rel)
                    for candidate in candidates:
                        try:
                            resolved = candidate.resolve()
                            resolved.relative_to(root)
                        except Exception:
                            continue
                        if resolved.is_file():
                            files[f"screenshots/{_safe_name(resolved.name)}"] = resolved.read_bytes(); break
                for attachment in clash.get("attachments", []) or []:
                    rel = str(attachment.get("path") or "").strip()
                    if not rel: continue
                    candidate=(root/rel).resolve()
                    try:candidate.relative_to(root)
                    except Exception:continue
                    if candidate.is_file():files[f"attachments/{_safe_name(candidate.name)}"]=candidate.read_bytes()

        checksums = {name: sha256(data).hexdigest() for name, data in files.items()}
        manifest = {
            "schema_version": SCHEMA,
            "project_id": str(project.get("project_id") or ""),
            "revision_id": str(project.get("revision_id") or ""),
            "counts": {"clashes": len(clashes_list), "issues": len(issues_list), "markups": len(markups_list), "comments": len(comments)},
            "files": checksums,
            "source_models_embedded": False,
        }
        files["manifest.json"] = _json_bytes(manifest)
        checksums["manifest.json"] = sha256(files["manifest.json"]).hexdigest()
        files["SHA256SUMS.txt"] = ("\n".join(f"{digest}  {name}" for name, digest in sorted(checksums.items())) + "\n").encode("ascii")

        tmp = output.with_suffix(output.suffix + ".tmp")
        with zipfile.ZipFile(tmp, "w", allowZip64=True) as z:
            for name in sorted(files):
                _zip_write(z, name, files[name])
        tmp.replace(output)
        return output


class ReviewPackageVerifier:
    def verify(self, path: str | Path) -> dict[str, Any]:
        source=Path(path)
        with zipfile.ZipFile(source, "r") as z:
            if z.testzip() is not None:
                raise ValueError("CWS review package CRC error")
            names=set(z.namelist())
            if "manifest.json" not in names or "SHA256SUMS.txt" not in names:
                raise ValueError("CWS review package mist manifest/checksums")
            for name in names:
                pure=PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise ValueError("Onveilig pad in CWS review package")
            manifest=json.loads(z.read("manifest.json"))
            if manifest.get("schema_version") != SCHEMA:
                raise ValueError("Niet-ondersteund CWS review package schema")
            for name,digest in manifest.get("files",{}).items():
                if name not in names:
                    raise ValueError(f"Review package mist {name}")
                if sha256(z.read(name)).hexdigest()!=digest:
                    raise ValueError(f"Review package checksum mismatch: {name}")
            return manifest


__all__=["SCHEMA","ReviewPackageBuilder","ReviewPackageVerifier"]
