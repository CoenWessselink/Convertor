"""Restore the frozen M18 runtime from its checksum-addressed Git blobs."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile


REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "CoenWessselink/Convertor")
PAYLOAD_SHA256 = "a0919bab74740db04e25b3f2782abb8427fba1a84f06e3b6e3d849b03b3a1c8b"
RUNTIME_SHA256 = "62c1a043a63dd0628769ad0e10d68afdf890406ca6f001cf354c2d6e84b94ae1"
RUNTIME_SIZE = 233402
CURRENT_RUNTIME = Path(__file__).resolve().parents[1] / "cws_convertor/manufacturing/m18_authority_runtime.zip"
PARTS = (
    ("4021d4e43a6ceee21c959c9123dc634581c164af", 16000),
    ("9c219047ae5a34393f529e812e90d714ff37f047", 8000),
    ("fb4358bdad1ca8f1da78de3ae87440d1bfbaeb46", 8000),
    ("5c5b093dc68b8f74719eb73ca1f7f07c1f9a3422", 8000),
    ("7ec41a26aa2b5aa623e4bc5e0b0206687d7fedc8", 8000),
    ("7132049bd418941f34bf40071dafbb54590158b0", 8000),
    ("2ea12272e8564f134bbb22c3e9351df82dcd9d1f", 8000),
    ("5da789652693a41d2096cb1a6425afa7994b49b5", 8000),
    ("bdd1ee5878a23f98947af1f77fdcf0bf1d2d1c8e", 8000),
    ("12f6b1020cd5641e973a08a886f4123450bcd13f", 8000),
    ("164d2469debf46e00e75d35f10e5cbb126578e0d", 8000),
    ("7e4925559ec60c4c811adf9e7edf73f60251973b", 8000),
    ("9516353e2e3c46671639a860ed76aced6b476b78", 8000),
    ("5cf95617a7c8905371a1ee8fdac627d7fbf62153", 8000),
    ("8ef00cbf52b492db253ba453b02b1e7a11f5058a", 8000),
    ("e8a74625f098e4470981ebdd73182422e8567212", 8000),
    ("04ada1db42d84184de1ec17bec0418e31468cbae", 8000),
    ("7b2921fc6bbe0ab3c96478ec1a8b577017ace98e", 8000),
    ("6c30bae699982648718371361c82785f3bf02264", 8000),
    ("548b5042b9900bdf618d05f97e1c34f0760ae4c9", 8000),
    ("a2b87c5a9035eaf8f27ba7f27af1a03efa6a91fa", 8000),
    ("e68c89a46222645e260299e91e23780819c9de9d", 8000),
    ("5bd3ac216d880fbd86bc19023f4a768e804a0ecd", 8000),
    ("338c865ac3fca61055bb7b3f31951fc55139d21b", 8000),
    ("36ada82794809cefcef13ce31ff987496f6dcc84", 8000),
    ("30245f012f720a34f583fcc16568ee19fc9010a6", 8000),
    ("be17ec4b2e5481afef46858e0a3832f78e5108a0", 8000),
    ("e8f7eab8041828b2954a0e97fc6f0647e52c5425", 8000),
    ("06fd625eba0398c229ea347240e272b9eea89f21", 8000),
    ("65ec0c5a46bf9c8e260098af298a2c9690d651a0", 8000),
    ("0eccdd563bd2da73ddde9986abb426043a1a062d", 8000),
    ("4554a2b563ec56364f43a22c7bb07590dde3013b", 8000),
    ("94b37434297f1dee95ce1195b3461cf79131e996", 8000),
    ("4ed2fcd3cbd90c32c7ed32cefe99e6b36ba07164", 8000),
    ("bcbaa88a8d5d5e801769674d8a12c23534c1a781", 8000),
    ("d2ca87990a8bf0bfa847b94cb413b3facabda46b", 8000),
    ("cf9c44ca48f22ba2767a1618a10309c7c97fec4d", 8000),
    ("b892c246132486b0367eebb128729ee007bd5685", 7204),
)


def _local_blob(oid: str) -> bytes | None:
    git = shutil.which("git")
    if not git:
        return None
    completed = subprocess.run([git, "cat-file", "blob", oid], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return completed.stdout if completed.returncode == 0 else None


def _remote_blob(oid: str) -> bytes:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or _git_credential_token()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/git/blobs/{oid}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "CWS-Convertor-M18-Restore/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("encoding") != "base64":
        raise RuntimeError(f"Unexpected blob encoding for {oid}")
    return base64.b64decode(str(payload.get("content") or ""), validate=False)


def _git_credential_token() -> str:
    git = shutil.which("git")
    if not git:
        return ""
    completed = subprocess.run(
        [git, "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode != 0:
        return ""
    values = dict(
        line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line
    )
    return str(values.get("password") or "")


def _file_evidence(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"path": str(path), "present": False}
    payload = path.read_bytes()
    return {
        "path": str(path),
        "present": True,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _write_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("cws_convertor/manufacturing/m18_authority_runtime.zip"))
    parser.add_argument("--report", type=Path, default=Path("build/evidence/m18_authority_restore.json"))
    args = parser.parse_args()
    chunks: list[bytes | None] = []
    sources: list[dict[str, object]] = []
    for index, (oid, expected_size) in enumerate(PARTS, 1):
        chunk = _local_blob(oid)
        source = "git-object"
        if chunk is None:
            source = "github-blob-api"
            try:
                chunk = _remote_blob(oid)
            except Exception as exc:
                chunks.append(None)
                sources.append(
                    {
                        "part": index,
                        "oid": oid,
                        "expected_bytes": expected_size,
                        "source": source,
                        "status": "unavailable",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
        if len(chunk) != expected_size:
            chunks.append(None)
            sources.append(
                {
                    "part": index,
                    "oid": oid,
                    "expected_bytes": expected_size,
                    "observed_bytes": len(chunk),
                    "source": source,
                    "status": "size_mismatch",
                }
            )
            continue
        chunks.append(chunk)
        sources.append(
            {
                "part": index,
                "oid": oid,
                "expected_bytes": expected_size,
                "observed_bytes": len(chunk),
                "source": source,
                "status": "available",
            }
        )
    unavailable = [item for item in sources if item["status"] != "available"]
    report: dict[str, object] = {
        "schema": "cws-m18-authority-restore-1.1",
        "repository": REPOSITORY,
        "status": "blocked_external_evidence" if unavailable else "checking",
        "expected": {
            "payload_sha256": PAYLOAD_SHA256,
            "runtime_sha256": RUNTIME_SHA256,
            "runtime_bytes": RUNTIME_SIZE,
            "parts": len(PARTS),
        },
        "observed_current_runtime": _file_evidence(CURRENT_RUNTIME),
        "available_parts": len(PARTS) - len(unavailable),
        "unavailable_parts": len(unavailable),
        "parts": sources,
        "safety": {
            "machine_observed_by_cws": False,
            "deployment_transport_authorized": False,
            "direct_machine_transfer": False,
            "machine_transfer_allowed": False,
        },
    }
    if unavailable:
        _write_report(args.report, report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "available_parts": report["available_parts"],
                    "unavailable_parts": report["unavailable_parts"],
                    "report": str(args.report),
                },
                sort_keys=True,
            )
        )
        return 2
    payload = b"".join(chunk for chunk in chunks if chunk is not None)
    if len(payload) != 311204 or hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA256:
        report["status"] = "payload_checksum_mismatch"
        report["observed_payload"] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        _write_report(args.report, report)
        print(json.dumps({"status": report["status"], "report": str(args.report)}, sort_keys=True))
        return 3
    runtime = base64.b64decode(payload, validate=True)
    if len(runtime) != RUNTIME_SIZE or hashlib.sha256(runtime).hexdigest() != RUNTIME_SHA256:
        report["status"] = "runtime_checksum_mismatch"
        report["observed_runtime"] = {
            "bytes": len(runtime),
            "sha256": hashlib.sha256(runtime).hexdigest(),
        }
        _write_report(args.report, report)
        print(json.dumps({"status": report["status"], "report": str(args.report)}, sort_keys=True))
        return 4
    required = {
        "cws_m18_authority/__init__.py",
        "cws_m18_authority/release_gate.py",
        "cws_m18_authority/deployment_assurance.py",
    }
    with zipfile.ZipFile(Path(os.devnull) if False else __import__("io").BytesIO(runtime)) as archive:
        bad = archive.testzip()
        names = set(archive.namelist())
    if bad is not None or not required.issubset(names):
        raise RuntimeError(f"M18 runtime ZIP validation failed: {bad or sorted(required - names)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(runtime)
    report["status"] = "pass"
    report["output"] = _file_evidence(args.output)
    report["zip_entries"] = len(names)
    _write_report(args.report, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "runtime_sha256": RUNTIME_SHA256,
                "runtime_bytes": len(runtime),
                "zip_entries": len(names),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
