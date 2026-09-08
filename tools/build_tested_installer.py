"""Build and test an installer from an already-built exact-source Windows bundle.

The verdict covers installation, frozen runtime checks and uninstallation, not
universal model recognition or external machine qualification.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "installer_delivery"
RESULTS = OUT / "evidence"
DIST = ROOT / "dist" / "CWS_Convertor"
INSTALL = ROOT / "build" / "installer_runtime_test"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> int:
    if sys.platform != "win32":
        raise RuntimeError("The installer must be tested on Windows")
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if revision != os.environ.get("GITHUB_SHA", revision):
        raise RuntimeError("Checkout does not match requested source")
    if subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT).strip():
        raise RuntimeError("Tracked source changed before installer testing")
    sys.path.insert(0, str(ROOT))
    from cws_convertor.product import APP_VERSION
    evidence = {"schema": "cws-tested-installer-1.0", "source_commit": revision,
                "version": APP_VERSION, "status": "RUNNING", "checks": [],
                "full_product_release_approved": False,
                "scope": "Frozen Windows installer and runtime acceptance; broader source gates are separate",
                "machine_transfer_authorized": False}
    manifest = OUT / "INSTALLER_ACCEPTANCE.json"

    def persist() -> None:
        manifest.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")

    def run(label: str, command: list[str], timeout: int = 1200, env: dict | None = None) -> None:
        print("RUN " + label, flush=True)
        tick = time.monotonic()
        record = {"name": label, "command": command, "status": "RUNNING"}
        evidence["checks"].append(record)
        persist()
        with (RESULTS / (label + ".log")).open("w", encoding="utf-8") as log:
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=timeout, check=False)
                record.update(returncode=result.returncode, status="PASS" if result.returncode == 0 else "FAIL")
            except subprocess.TimeoutExpired:
                record.update(returncode=None, status="TIMEOUT")
                raise
            finally:
                record["seconds"] = round(time.monotonic() - tick, 3)
                persist()
        if result.returncode:
            raise RuntimeError(f"{label} failed: see {label}.log")
        print("PASS " + label, flush=True)

    try:
        for name in ("CWS_Convertor.exe", "CWS_Convertor_CLI.exe"):
            if not (DIST / name).is_file():
                raise FileNotFoundError(DIST / name)
        identity = {"source_commit": revision, "version": APP_VERSION,
                    "tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()}
        (DIST / "BUILD_IDENTITY.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
        run("dist_runtime", [sys.executable, "tests/packaged_runtime_smoke.py", "--runtime-dir", str(DIST),
                             "--label", "installer-dist", "--result-dir", str(RESULTS)])
        candidates = [Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6/ISCC.exe",
                      Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6/ISCC.exe"]
        compiler = next((path for path in candidates if path.is_file()), None)
        if compiler is None:
            raise FileNotFoundError("Inno Setup compiler missing")
        run("compile_installer", [str(compiler), "/DCommit7=" + revision[:7], "installer/CWS_Convertor.iss"], 1800)
        installer = ROOT / "dist_installer" / f"CWS_Convertor_Setup_{APP_VERSION}_{revision[:7]}_x64.exe"
        if not installer.is_file():
            raise FileNotFoundError(installer)
        if INSTALL.exists():
            raise RuntimeError("Installation test directory is not fresh")
        run("fresh_install", [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                               "/CURRENTUSER", "/TASKS=fileassoc", "/DIR=" + str(INSTALL),
                               "/LOG=" + str(RESULTS / "setup.log")])
        for name in ("CWS_Convertor.exe", "CWS_Convertor_CLI.exe", "BUILD_IDENTITY.json"):
            if digest(INSTALL / name) != digest(DIST / name):
                raise RuntimeError("Installed identity mismatch: " + name)
        run("installed_runtime", [sys.executable, "tests/packaged_runtime_smoke.py", "--runtime-dir", str(INSTALL),
                                  "--label", "installer-installed", "--result-dir", str(RESULTS), "--pdf12-evidence"])
        run("installed_associations", [sys.executable, "tests/windows_installer_association_smoke.py", "--runtime-dir", str(INSTALL)])
        run("installed_conversion_matrix", [sys.executable, "tests/conversion_one_phase_packaged_smoke.py",
                                             "--runtime-dir", str(INSTALL), "--output", str(RESULTS / "CONVERSION_MATRIX.json"),
                                             "--expected-sha", revision], 1800)
        clean = dict(os.environ)
        windows = Path(clean.get("SystemRoot", "C:/Windows"))
        clean["PATH"] = os.pathsep.join((str(windows / "System32"), str(windows), str(windows / "System32/Wbem")))
        clean.pop("PYTHONPATH", None)
        clean.pop("PYTHONHOME", None)
        project = OUT / "user-project-preservation.cwscproj"
        run("create_user_project", [str(INSTALL / "CWS_Convertor_CLI.exe"), "project-new", str(project), "--name", "Installer preservation test"], env=clean)
        project_hash = digest(project)
        run("reinstall", [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-",
                          "/CURRENTUSER", "/TASKS=fileassoc", "/DIR=" + str(INSTALL)])
        run("reinstalled_startup", [str(INSTALL / "CWS_Convertor.exe"), "--quick-self-test", "--report", str(RESULTS / "reinstalled-startup.json")], env=clean)
        run("uninstall", [str(INSTALL / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                          "/LOG=" + str(RESULTS / "uninstall.log")])
        deadline = time.monotonic() + 90
        while True:
            leftovers = [str(path) for path in INSTALL.rglob("*") if path.suffix.lower() in {".exe", ".dll", ".pyd"}]
            if not leftovers or time.monotonic() >= deadline:
                break
            time.sleep(0.5)
        if leftovers:
            raise RuntimeError("Critical installed files remain after uninstall: " + str(leftovers[:10]))
        run("association_cleanup", [sys.executable, "tests/windows_installer_association_smoke.py", "--runtime-dir", str(INSTALL), "--expect-absent"])
        if digest(project) != project_hash:
            raise RuntimeError("User project changed during reinstall or uninstall")
        evidence["user_project_preserved"] = True
        delivered = OUT / installer.name
        shutil.copy2(installer, delivered)
        evidence["installer"] = {"name": delivered.name, "bytes": delivered.stat().st_size,
                                 "sha256": digest(delivered), "authenticode_signed": False}
        evidence["status"] = "PASS"
        (OUT / "SHA256SUMS.txt").write_text(digest(delivered) + "  " + delivered.name + "\n", encoding="ascii")
    except Exception as exc:
        evidence["status"] = "FAIL"
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        print(evidence["error"], flush=True)
    finally:
        evidence["finished_at"] = datetime.now(timezone.utc).isoformat()
        persist()
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
