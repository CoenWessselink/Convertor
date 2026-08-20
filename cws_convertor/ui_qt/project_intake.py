from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Callable, Iterable

from PySide6 import QtCore

from conversion import convert_file
from cws_convertor.project import ProjectService


ProgressCallback = Callable[[int, str], None]


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", str(value or "").strip())
    return name.strip(" ._") or "Nieuw project"


def suggest_project_path(project_name: str, root: str | Path | None = None) -> Path:
    base = Path(root) if root else Path.home() / "Documents" / "CWS Convertor Projects"
    base.mkdir(parents=True, exist_ok=True)
    stem = _safe_name(project_name)
    candidate = base / f"{stem}.cwscproj"
    index = 2
    while candidate.exists():
        candidate = base / f"{stem} ({index}).cwscproj"
        index += 1
    return candidate


def build_project_from_models(
    paths: Iterable[str | Path],
    project_path: str | Path,
    project_name: str,
    project_number: str = "",
    material: str = "S355JR",
    user: str = "qt-gui",
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    def emit(percent: int, message: str) -> None:
        if progress:
            progress(max(0, min(100, int(percent))), message)

    inputs = [Path(value).expanduser().resolve() for value in paths]
    if not inputs:
        raise ValueError("Selecteer minimaal een IFC-, STEP- of NC1-bestand.")
    missing = [str(path) for path in inputs if not path.is_file()]
    if missing:
        raise FileNotFoundError("Niet gevonden: " + ", ".join(missing))
    allowed = {".ifc", ".step", ".stp", ".nc", ".nc1"}
    unsupported = [path.name for path in inputs if path.suffix.lower() not in allowed]
    if unsupported:
        raise ValueError("Niet ondersteund: " + ", ".join(unsupported))
    emit(3, f"Bronbestanden controleren ({len(inputs)} bestand(en))")

    target = Path(project_path).expanduser().resolve()
    if target.exists():
        raise FileExistsError(f"Project bestaat al: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    import_sources: list[Path] = []
    nc1_conversions: list[dict[str, object]] = []
    converted_root = target.parent / f"{target.stem}_converted_sources"
    for source in inputs:
        suffix = source.suffix.lower()
        if suffix not in {".nc", ".nc1"}:
            import_sources.append(source)
            continue
        converted_root.mkdir(parents=True, exist_ok=True)
        emit(10, f"NC1 naar STEP converteren: {source.name}")
        outputs, warnings, failures = convert_file(
            str(source),
            str(converted_root),
            "nc1-step",
            strict_validation=True,
        )
        if failures or not outputs:
            details = "; ".join(str(value) for value in failures) or "geen STEP-uitvoer"
            raise RuntimeError(f"NC1-conversie mislukt voor {source.name}: {details}")
        converted = Path(outputs[0]).resolve()
        import_sources.append(converted)
        nc1_conversions.append(
            {
                "source": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "converted_step": str(converted),
                "warnings": [str(value) for value in warnings],
            }
        )

    service = ProjectService()
    emit(22, "Canonical projectcontainer aanmaken")
    created = service.create_project(
        str(target),
        project_name=_safe_name(project_name),
        description=f"Materiaalbasis: {material or 'S355JR'}",
        order_number=str(project_number or ""),
        created_by=user,
    )
    close_created = getattr(created, "close", None)
    if callable(close_created):
        close_created()
    try:
        emit(30, "Bronbestanden registreren en insluiten")
        registrations = service.register_sources(
            str(target),
            [str(path) for path in import_sources],
            embed_sources=True,
            include_step_geometry=True,
            user=user,
        )

        source_ids = [
            str(
                getattr(
                    result.source,
                    "source_id",
                    getattr(result.source, "id", ""),
                )
            )
            for result in registrations
        ]
        source_ids = [value for value in source_ids if value]

        def semantic_progress(fraction: float, current: int, message: str) -> None:
            percent = 38 + int(max(0.0, min(1.0, fraction)) * 45)
            emit(percent, f"Semantisch model: {fraction:.0%} ({current}) {message}".strip())

        emit(38, "Semantisch model en onderdeelstructuur opbouwen")
        imports = service.semantic_import_sources(
            str(target),
            source_ids or None,
            embed_sources=True,
            user=user,
            progress_callback=semantic_progress,
        )
        if nc1_conversions:
            emit(86, "NC1-herkomst en conversiebewijs vastleggen")
            evidence = target.parent / f"{target.stem}_nc1_origin.json"
            evidence.write_text(json.dumps(nc1_conversions, indent=2), encoding="utf-8")
        summary: dict[str, int] = {}
        for result in imports:
            for name, count in result.entity_counts.items():
                summary[name] = summary.get(name, 0) + int(count)
    except Exception:
        if target.exists():
            target.unlink(missing_ok=True)
        raise

    emit(100, "Projectcontainer gereed voor Viewer V15")
    return {
        "status": "ok",
        "project": str(target),
        "inputs": [str(path) for path in inputs],
        "registrations": [asdict(value) if is_dataclass(value) else str(value) for value in registrations],
        "imports": [asdict(value) if is_dataclass(value) else str(value) for value in imports],
        "nc1_conversions": nc1_conversions,
        "summary": summary,
    }


class ModelIntakeWorker(QtCore.QObject):
    progress = QtCore.Signal(str)
    progress_detail = QtCore.Signal(int, str)
    completed = QtCore.Signal(str, object)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, paths: Iterable[str], target: str, options: dict[str, str]) -> None:
        super().__init__()
        self.paths = tuple(paths)
        self.target = target
        self.options = dict(options)

    @QtCore.Slot()
    def run(self) -> None:
        try:
            def report(percent: int, message: str) -> None:
                self.progress_detail.emit(percent, message)
                self.progress.emit(message)

            payload = build_project_from_models(
                self.paths,
                self.target,
                project_name=self.options.get("project_name", "Nieuw project"),
                project_number=self.options.get("project_number", ""),
                material=self.options.get("material", "S355JR"),
                progress=report,
            )
            self.completed.emit(self.target, payload)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
