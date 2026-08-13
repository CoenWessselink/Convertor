from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from .pdf_report import create_review_pdf
from .utils import as_dict, canonical_json_bytes, get_value


class ArtifactUnavailable(RuntimeError):
    pass


def _read_artifact(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, Path):
        return value.read_bytes()
    if isinstance(value, str):
        path = Path(value).expanduser()
        if path.is_file():
            return path.read_bytes()
        if value.startswith("base64:"):
            return base64.b64decode(value.split(":", 1)[1], validate=True)
    if isinstance(value, dict):
        if "bytes_base64" in value:
            return base64.b64decode(str(value["bytes_base64"]), validate=True)
        if "path" in value:
            path = Path(str(value["path"])).expanduser()
            if path.is_file():
                return path.read_bytes()
    raise ArtifactUnavailable("Vertrouwd artefact is niet als bytes of bestaand pad beschikbaar")


def media_type(fmt: str) -> str:
    return {
        "nc1": "text/plain",
        "step": "model/step",
        "stp": "model/step",
        "ifc": "application/x-step",
        "production_pdf": "application/pdf",
        "review_pdf": "application/pdf",
        "json": "application/json",
        "csv": "text/csv",
        "dxf": "image/vnd.dxf",
        "label_pdf": "application/pdf",
        "preview_png": "image/png",
        "assembly_pdf": "application/pdf",
        "assembly_step": "model/step",
        "assembly_ifc": "application/x-step",
        "assembly_zip": "application/zip",
        "source": "application/octet-stream",
    }.get(fmt, "application/octet-stream")


def extension(fmt: str) -> str:
    return {
        "nc1": ".nc1",
        "step": ".step",
        "stp": ".step",
        "ifc": ".ifc",
        "production_pdf": ".pdf",
        "review_pdf": ".pdf",
        "json": ".json",
        "csv": ".csv",
        "dxf": ".dxf",
        "label_pdf": ".pdf",
        "preview_png": ".png",
        "source": ".bin",
    }.get(fmt, f".{fmt}")


def create_artifact(
    part: Any,
    fmt: str,
    *,
    trusted_artifacts: dict[str, Any],
    blocked_reasons: list[str],
    product_version: str,
) -> tuple[bytes, str]:
    fmt = fmt.lower()
    if fmt == "json":
        return canonical_json_bytes(as_dict(part)), "canonical-project-model"
    if fmt == "review_pdf":
        return create_review_pdf(part, blocked_reasons=blocked_reasons, product_version=product_version), "review-report"
    if fmt in trusted_artifacts:
        return _read_artifact(trusted_artifacts[fmt]), "trusted-artifact"
    canonical = get_value(part, "canonical_part", "canonical_payload", "canonical_model")
    if canonical is not None:
        # The actual geometry exporters are intentionally not emulated here.  A
        # validated converter adapter must supply the bytes and the roundtrip
        # result before this path is enabled.
        raise ArtifactUnavailable(
            f"Canoniek model aanwezig, maar geen gevalideerde {fmt.upper()}-adapter met roundtripbewijs geregistreerd"
        )
    raise ArtifactUnavailable(f"Geen vertrouwd {fmt.upper()}-artefact aanwezig")
