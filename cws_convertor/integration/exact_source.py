"""Lightweight exact-source project service for viewer/background review.

This V14 service intentionally exposes only the read/review boundary required
by Exact Part Workbench and Model Control.  It opens the canonical CWS project,
re-verifies source bytes through ProjectSourceResolver and isolates exactly one
semantic part as source BREP.  No production-release action is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Iterable

from cws_convertor.project.service import ProjectSession
from cws_viewer.adapters.source_geometry import ProjectSourceResolver
from cws_viewer.exact.source_isolation import (
    DEFAULT_MAX_CATALOG_SUBSHAPES,
    SourceBrepIsolationResult,
    SourceBrepIsolator,
)


@dataclass(slots=True)
class ExactSourceProjectService:
    session: ProjectSession
    _temporary_directory: tempfile.TemporaryDirectory[str]
    search_roots: tuple[Path, ...]

    @classmethod
    def open(
        cls,
        project_path: str | Path,
        *,
        read_only: bool = True,
        source_search_roots: Iterable[str | Path] = (),
    ) -> "ExactSourceProjectService":
        session = ProjectSession.open(project_path, read_only=read_only)
        temporary = tempfile.TemporaryDirectory(prefix="cws-v14-exact-source-")
        roots = [Path(value).expanduser().resolve() for value in source_search_roots]
        roots.extend(path.parent for path in session.source_paths.values())
        return cls(
            session=session,
            _temporary_directory=temporary,
            search_roots=tuple(dict.fromkeys(roots)),
        )

    @property
    def project(self):
        return self.session.project

    @property
    def project_path(self) -> Path:
        if self.session.path is None:
            raise ValueError("Exact-source service vereist een opgeslagen project")
        return Path(self.session.path)

    def close(self) -> None:
        self.session.close()
        self._temporary_directory.cleanup()

    def __enter__(self) -> "ExactSourceProjectService":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def _part(self, part_id: str):
        part = self.project.parts.get(str(part_id))
        if part is None:
            raise KeyError(f"Onbekend onderdeel: {part_id}")
        return part

    def _resolver(self) -> ProjectSourceResolver:
        return ProjectSourceResolver(
            self.project,
            project_package_path=self.project_path,
            search_roots=self.search_roots,
            extraction_root=Path(self._temporary_directory.name) / "source-cache",
        )

    @staticmethod
    def _preflight(part, *, allow_heavy: bool) -> None:
        descriptor = dict(getattr(part, "geometry_descriptor", {}) or {})
        count = int(descriptor.get("graph_entity_count") or 0)
        if count > 50_000 and not allow_heavy:
            error = RuntimeError(
                f"Exacte isolatie vereist achtergrond/heavy mode: {count} grafiekentiteiten"
            )
            setattr(error, "code", "CWS-V14-LARGE-PART-BACKGROUND-ISOLATION-REQUIRED")
            raise error

    def isolate(
        self,
        part_id: str,
        *,
        allow_heavy: bool = False,
    ) -> tuple[object, Path, SourceBrepIsolationResult]:
        part = self._part(part_id)
        self._preflight(part, allow_heavy=allow_heavy)
        resolved = self._resolver().resolve(part.source_identity.source_file_id)
        max_subshapes = 100_000 if allow_heavy else DEFAULT_MAX_CATALOG_SUBSHAPES
        result = SourceBrepIsolator(max_catalog_subshapes=max_subshapes).isolate(
            part, resolved.path
        )
        return part, resolved.path, result


__all__ = ["ExactSourceProjectService"]
