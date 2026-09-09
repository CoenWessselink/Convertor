"""Identity-bound STEP subshape transfer; never select by solid order or name."""
from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Any

_LOCK = RLock()
_READERS: OrderedDict[tuple[str, str], Any] = OrderedDict()


def resolve_step_roots(path: Path, sha256: str, entity_ids: tuple[int, ...]) -> tuple[Any, dict]:
    """Transfer explicitly labelled entities in the verified source unit context.

    NextNumberForLabel(exact=True) searches the original Part-21 identifier,
    NOT its in-memory rank. TransferOne then executes that explicit selection
    inside OCCT, avoiding binding-dependent copies of transient STEP handles.
    """
    import cadquery as cq
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from .baseline import sha256_file
    from cws_convertor.importers.p21 import P21Document

    if not entity_ids or len(set(entity_ids)) != len(entity_ids):
        raise ValueError("Geen unieke STEP-bronentiteiten geselecteerd")
    if sha256_file(path) != sha256:
        raise ValueError("STEP-bron gewijzigd voor native selectie")
    key = (str(path.resolve()), sha256)
    with _LOCK:
        if key not in _READERS:
            doc = P21Document.load(path)
            reader = STEPControl_Reader()
            if reader.ReadFile(str(path)) != IFSelect_RetDone:
                raise ValueError("Native STEP-reader weigert de bron")
            reader.SetSystemLengthUnit(1.0)
            # Transfer all roots first so representation-specific length units
            # are established before requesting the isolated BREP result.
            reader.TransferRoots()
            original_shapes = [cq.Shape.cast(reader.Shape(i)) for i in range(1, reader.NbShapes()+1)]
            stats = {"native_source_root_count": len(original_shapes),
                     "native_source_solid_count": sum(len(s.Solids()) for s in original_shapes)}
            _READERS[key] = (reader, doc, stats, {})
            while len(_READERS) > 3:
                _READERS.popitem(last=False)
        _READERS.move_to_end(key)
        reader, doc, stats, cache = _READERS[key]
        selected = []
        kinds = []
        for entity_id in entity_ids:
            entity = doc.get(entity_id)
            if entity is None or entity.type_name not in {
                "MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS", "FACETED_BREP",
                "SHELL_BASED_SURFACE_MODEL", "GEOMETRIC_CURVE_SET", "TESSELLATED_SOLID",
            }:
                raise ValueError(f"STEP-selector #{entity_id} is geen bronshape")
            kinds.append(entity.type_name)
            if entity_id not in cache:
                model = reader.StepModel()
                number = model.NextNumberForLabel(f"#{entity_id}", 0, True)
                if number <= 0 or model.NextNumberForLabel(f"#{entity_id}", number, True) != 0:
                    raise ValueError(f"Geen unieke native binding voor STEP #{entity_id}")
                reader.ClearShapes()
                if not reader.TransferOne(number) or reader.NbShapes() != 1:
                    raise ValueError(f"STEP-entiteit #{entity_id} kon niet exact worden overgedragen")
                shape = cq.Shape.cast(reader.OneShape())
                if shape.isNull() or not shape.isValid():
                    raise ValueError(f"Ongeldige bronshape #{entity_id}")
                cache[entity_id] = shape
            selected.append(cache[entity_id].copy())
        if sha256_file(path) != sha256:
            _READERS.pop(key, None)
            raise ValueError("STEP-bron gewijzigd tijdens native selectie")
        shape = selected[0] if len(selected) == 1 else cq.Compound.makeCompound(selected)
        # Recompute the canonical source subgraph fingerprint, rather than
        # trusting a matching but tampered locator/descriptor pair.
        from cws_convertor.importers.step_project import STEPSemanticProjectImporter
        semantic_hash = STEPSemanticProjectImporter._graph_descriptor(doc, list(entity_ids))["source_geometry_hash"]
        return shape, {**stats, "selected_semantic_sha256": semantic_hash, "selector_kind": "step_brep_roots",
                       "selector_entity_ids": [f"#{i}" for i in entity_ids],
                       "source_shape_types": kinds,
                       "selection_rule": "exact STEP label lookup and explicit OCCT entity transfer",
                       "coordinates": "source-local; project global_placement applied by consumer",
                       "length_unit": "mm"}
