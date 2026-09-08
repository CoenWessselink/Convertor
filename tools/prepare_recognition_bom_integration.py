"""Reproduce the reviewed recognition/BOM integration as Git objects only.

This one-time utility never commits, pushes, changes a branch ref or transfers
machine output. Immutable input and output fingerprints guard every source
file; publication and current-source Windows acceptance are separate steps.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BOM_HEAD = "528cf4326fc613746f1eb90354998492c656888d"
MERGE_BASE = "b91f768530ce54a5948606e80dd4a6628375f773"
BASE_FINGERPRINT = "0844b87608f3b989ff464b92c66c6c60045ae9975f5ddd1980c744f50360151a"
RESULT_FINGERPRINT = "1bcd6b02fdc20875296d74a8cc89c0545e46b71c3a1f5172f0e6e43c9b875374"
PATCH_SHA256 = "cd42fccd43921ba6cacb2e8bb21e5a8230be389c52c78aec2b3a9e86302fda0d"
PATHS = """.github/workflows/material-model-recognition.yml
cws_convertor/bom/__init__.py
cws_convertor/bom/engine.py
cws_convertor/bom/export.py
cws_convertor/bom/material_gate.py
cws_convertor/bom/models.py
cws_convertor/bom/production_hub.py
cws_convertor/bom/workspace.py
cws_convertor/integration/selftest.py
cws_convertor/machine_routing.py
cws_convertor/manufacturing/routing.py
cws_convertor/project/classification.py
cws_convertor/project/model.py
cws_convertor/ui_qt/bom_workspace.py
cws_convertor/ui_qt/main_window.py
cws_convertor/ui_qt/product_workspaces.py
cws_convertor/ui_qt/project_workspace.py
cws_convertor/ui_qt/u4_shell.py
cws_viewer/backends/vtk_project_mesh.py
cws_viewer/backends/vtk_project_mesh_feel.py
cws_viewer/backends/vtk_project_mesh_v14.py
cws_viewer/cache/__init__.py
cws_viewer/cache/render_resource_cache.py
cws_viewer/core/v14_controller.py
cws_viewer/geometry/loader.py
cws_viewer/ui_qt/qt_compat.py
cws_viewer/ui_qt/vtk_real_project_widget.py
cws_viewer/ui_qt/vtk_real_project_widget_feel_v2.py
docs/BOM_COMPLETE_IMPLEMENTATION.md
tests/bom_material_integration_smoke.py
tests/bom_production_hub_complete_smoke.py
tests/bom_production_hub_smoke.py
tests/part_workbench_roundtrip_smoke.py
tests/production_editor_smoke.py
tests/project_bom_smoke.py
tests/project_cli_smoke.py
tests/viewer_shared_cache_lasso_smoke.py
tools/capture_bom_production_hub.py
tools/run_material_model_recognition_acceptance.py
tools/verify_bom_completion.py""".splitlines()
EXTRA_PATHS = {
    ".github/workflows/material-model-recognition.yml",
    "cws_convertor/bom/material_gate.py",
    "cws_convertor/integration/selftest.py",
    "tests/bom_material_integration_smoke.py",
    "tests/part_workbench_roundtrip_smoke.py",
    "tests/production_editor_smoke.py",
    "tools/run_material_model_recognition_acceptance.py",
}


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def optional_blob(ref: str, path: str) -> bytes | None:
    listing = git("ls-tree", ref, "--", path).decode().strip()
    if not listing:
        return None
    mode, kind, sha = listing.split("\t", 1)[0].split()
    if mode != "100644" or kind != "blob":
        raise RuntimeError(f"Unsafe source object: {path}: {listing}")
    return git("cat-file", "blob", sha)


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fingerprint(values: dict[str, str | None]) -> str:
    payload = json.dumps(sorted(values.items()), separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parent = git("rev-parse", "HEAD").decode().strip()
    base_tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    git("fetch", "--depth=1", "origin", BOM_HEAD, MERGE_BASE)
    git("config", "core.autocrlf", "false")
    originals = {}
    for path in PATHS:
        pure = PurePosixPath(path)
        if pure.is_absolute() or ".." in pure.parts or "\\" in path:
            raise RuntimeError(f"Unsafe path: {path}")
        originals[path] = optional_blob("HEAD", path)
    observed = {path: blob_sha(data) if data is not None else None for path, data in originals.items()}
    if fingerprint(observed) != BASE_FINGERPRINT:
        raise RuntimeError("Input source changed; refusing to overwrite concurrent work: " + json.dumps(observed))
    for path, original in originals.items():
        target = ROOT / path
        if target.is_symlink():
            raise RuntimeError(f"Symlink target refused: {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if path not in EXTRA_PATHS:
            incoming = optional_blob(BOM_HEAD, path)
            if incoming is None:
                raise RuntimeError(f"Missing BOM source: {path}")
            if original is None or original == incoming:
                data = incoming
            else:
                ancestor = optional_blob(MERGE_BASE, path)
                if ancestor is None:
                    raise RuntimeError(f"Unresolved add/add: {path}")
                with tempfile.TemporaryDirectory() as folder:
                    paths = [Path(folder) / name for name in ("ours", "base", "bom")]
                    for temp, content in zip(paths, (original, ancestor, incoming)):
                        temp.write_bytes(content)
                    result = subprocess.run(["git", "merge-file", "-p", *map(str, paths)], capture_output=True)
                    if result.returncode:
                        raise RuntimeError(f"Unresolved merge: {path}")
                    data = result.stdout
            target.write_bytes(data)
        elif original is not None:
            target.write_bytes(original)
    patch = ROOT / "tools/recognition_bom_integration.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != PATCH_SHA256:
        raise RuntimeError("Patch integrity mismatch")
    git("apply", "--check", str(patch))
    git("apply", str(patch))
    results = {path: blob_sha((ROOT / path).read_bytes()) for path in PATHS}
    if fingerprint(results) != RESULT_FINGERPRINT:
        raise RuntimeError("Output differs from the reviewed source: " + json.dumps(results))
    entries, blobs = [], []
    for path, sha in results.items():
        data = (ROOT / path).read_bytes()
        if path.endswith(".py"):
            compile(data, path, "exec")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": sha})
        exists = subprocess.run(["git", "cat-file", "-e", sha], cwd=ROOT, capture_output=True).returncode == 0
        if not exists:
            blobs.append({"sha": sha, "content": base64.b64encode(data).decode("ascii")})
    result = {"parent": parent, "base_tree": base_tree, "entries": entries, "blobs": blobs,
              "result_fingerprint": RESULT_FINGERPRINT, "patch_sha256": PATCH_SHA256,
              "bom_head": BOM_HEAD, "merge_base": MERGE_BASE}
    output = ROOT / "build/recognition_bom_import/PREPARED_TREE.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps({"parent": parent, "verified_paths": len(entries), "new_blobs": len(blobs)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
