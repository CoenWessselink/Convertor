"""Compatibility facade for complete IFC/STEP project import.

CWS Convertor 0.7 keeps the deterministic baseline scanner and adds the
transactional semantic materialisation boundary.  Existing integrations can
continue importing baseline helpers from this root module, while new callers
can use :func:`semantic_import_source` and the shared importer contracts.
"""
from cws_convertor.project.baseline import *  # noqa: F401,F403
from cws_convertor.project.semantic_import import (  # noqa: F401
    purge_source_entities,
    semantic_import_source,
    source_entity_ids,
)
from cws_convertor.importers.semantic import (  # noqa: F401
    SemanticImportError,
    SemanticImportResult,
    SemanticProgress,
    SemanticProjectImporter,
)
