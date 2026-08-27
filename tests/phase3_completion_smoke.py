from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.manufacturing.contracts import (
    ExportScope,
    ManufacturingFace,
    ManufacturingMark,
    ManufacturingRuleSet,
    ManufacturingSequenceOperation,
    NeutralManufacturingJob,
    ProductionInstanceIdentity,
)
from cws_convertor.manufacturing.faces_model import ManufacturingFace as FaceSource
from cws_convertor.manufacturing.marking_model import MarkFeature, MarkingRuleSet
from cws_convertor.manufacturing.neutral_job_model import NeutralOperation, NeutralOperationKind
from cws_convertor.project.manufacturing_contracts import ExportScopeKind, HASH_LAYERS, ManufacturingHashChain


def main() -> None:
    assert ManufacturingFace is FaceSource
    assert ManufacturingMark is MarkFeature
    assert ManufacturingRuleSet is MarkingRuleSet
    assert ManufacturingSequenceOperation is NeutralOperation
    assert ExportScope(ExportScopeKind.SELECTION).is_empty_selection
    assert len(tuple(ExportScopeKind)) == 12
    assert len(HASH_LAYERS) == 12
    chain = ManufacturingHashChain()
    for index, layer in enumerate(HASH_LAYERS):
        chain.set(layer, {"index": index})
    invalidated = chain.set("contact_hash", {"index": "changed"})
    assert invalidated == HASH_LAYERS[4:]
    assert tuple(chain.snapshot()) == HASH_LAYERS[:4]
    chain.require_through("contact_hash")
    identity = ProductionInstanceIdentity("project", "part", "piece", mirrored=True)
    assert len(identity.stable_key) == 64
    assert NeutralManufacturingJob is not None
    assert {
        "load",
        "clamp",
        "reorient",
        "reclamp",
        "mark",
        "scribe",
        "pop",
        "text",
        "drill",
        "punch",
        "contour",
        "saw",
        "common_cut",
        "sever",
        "unload",
    } == {kind.value for kind in NeutralOperationKind}
    print("phase3_completion_smoke: PASS")


if __name__ == "__main__":
    main()
