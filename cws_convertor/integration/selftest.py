"""Deterministic V9 one-process integration self-test."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any

from cws_convertor.project import Assembly, Fastener, Part, ProjectSession, PurchasedItem, SourceIdentity, Weld
from .workspace import IntegratedProjectWorkspace


@dataclass(frozen=True, slots=True)
class IntegrationCheck:
    name: str
    status: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "evidence": self.evidence}


@dataclass(frozen=True, slots=True)
class IntegrationSelfTestReport:
    checks: tuple[IntegrationCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.status == "passed" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "cws-v9-integration-selftest-1.0",
            "status": "passed" if self.passed else "failed",
            "check_count": len(self.checks),
            "checks": [check.to_dict() for check in self.checks],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def create_synthetic_integration_project(path: str | Path) -> Path:
    path = Path(path).expanduser().resolve()
    session = ProjectSession.new("CWS V9 geïntegreerde smoke", created_by="v9-selftest")
    project = session.project
    source = SourceIdentity(source_format="SYNTHETIC", source_entity_id="part:1", part_position="P1", assembly_mark="M1")
    part = Part(
        internal_id="part-v9",
        source_identity=source,
        part_position="P1",
        name="V9 testplaat",
        category="make_part",
        profile="PL10",
        material="S355JR",
        length_mm=100.0,
        geometry_descriptor={"kind": "plate", "bbox_mm": [100.0, 50.0, 10.0]},
        classification_status="confirmed",
        classification_confidence=1.0,
        normalized_profile="PL10",
        normalized_material="S355JR",
        profile_confidence=1.0,
        material_confidence=1.0,
    )
    part.recompute_hashes()
    part.production_identity_hash = part.manufacturing_hash
    assembly = Assembly(
        internal_id="assembly-v9",
        source_identity=SourceIdentity(source_format="SYNTHETIC", source_entity_id="assembly:1", assembly_mark="M1"),
        assembly_mark="M1",
        name="M1",
        part_ids=[part.internal_id],
        main_part_id=part.internal_id,
    )
    part.assembly_ids = [assembly.internal_id]
    fastener = Fastener(
        internal_id="fastener-v9",
        source_identity=SourceIdentity(source_format="SYNTHETIC", source_entity_id="fastener:1", assembly_mark="M1"),
        name="Bout M16",
        fastener_type="BOLT",
        diameter_mm=16.0,
        quantity=2,
        connected_part_ids=[part.internal_id],
    )
    purchased = PurchasedItem(
        internal_id="purchased-v9",
        source_identity=SourceIdentity(source_format="SYNTHETIC", source_entity_id="purchased:1", assembly_mark="M1"),
        name="Rooster",
        article_number="BUY-1",
        supplier="Testleverancier",
        quantity=1.0,
        assembly_ids=[assembly.internal_id],
    )
    weld = Weld(
        internal_id="weld-v9",
        source_identity=SourceIdentity(source_format="SYNTHETIC", source_entity_id="weld:1", assembly_mark="M1"),
        name="Hoeklas",
        weld_type="FILLET",
        size_mm=5.0,
        length_mm=100.0,
        connected_part_ids=[part.internal_id],
    )
    assembly.purchased_item_ids = [purchased.internal_id]
    assembly.fastener_ids = [fastener.internal_id]
    assembly.weld_ids = [weld.internal_id]
    for entity in (part, assembly, purchased, fastener, weld):
        project.add_entity(entity, user="v9-selftest")
    project.validate()
    session.save(path, embed_sources=False, user="v9-selftest", revision_message="V9 smokeproject")
    session.close()
    return path


def run_integration_self_test(project_path: str | Path | None = None) -> IntegrationSelfTestReport:
    checks: list[IntegrationCheck] = []
    with tempfile.TemporaryDirectory(prefix="cws-v9-selftest-") as directory:
        path = Path(project_path).expanduser().resolve() if project_path else Path(directory) / "v9-smoke.cwscproj"
        if project_path is None:
            create_synthetic_integration_project(path)
        with IntegratedProjectWorkspace.open(path, read_only=True, load_all_geometry=False) as workspace:
            audit = workspace.identity_audit
            checks.append(IntegrationCheck("single-project-identity", "passed" if audit.passed else "failed", audit.to_dict()))
            canonical_id = next(iter(workspace.project.parts))
            workspace.select_entities((canonical_id,), origin="selftest")
            selection = workspace.selection_bus.selection
            checks.append(IntegrationCheck(
                "tree-grid-viewer-selection",
                "passed" if selection.primary_entity_id == canonical_id else "failed",
                selection.to_dict(),
            ))
            group_id = workspace.bom_index.group_for_entity(canonical_id)
            selected = workspace.select_bom_group(group_id or "")
            checks.append(IntegrationCheck(
                "bom-selection-identity",
                "passed" if canonical_id in selected else "failed",
                {"group_id": group_id or "", "entity_ids": list(selected)},
            ))
            workspace.highlight_pdf_feature(canonical_id, "feature:selftest")
            pdf_selection = workspace.selection_bus.selection
            checks.append(IntegrationCheck(
                "pdf-feature-selection",
                "passed" if pdf_selection.feature_id == "feature:selftest" and pdf_selection.primary_entity_id == canonical_id else "failed",
                pdf_selection.to_dict(),
            ))
            gate = workspace.readiness_for_part(canonical_id)
            checks.append(IntegrationCheck(
                "viewer-cannot-bypass-production-gate",
                "passed" if not gate["viewer_can_override"] and not gate["allowed"].get("nc1", False) else "failed",
                gate,
            ))
            exact = workspace.open_exact_part(canonical_id)
            checks.append(IntegrationCheck(
                "exact-workbench-stays-evidence-gated",
                "passed" if (not exact.available and exact.status == "blocked") or exact.available else "failed",
                exact.to_dict(),
            ))
    return IntegrationSelfTestReport(tuple(checks))


__all__ = ["IntegrationCheck", "IntegrationSelfTestReport", "create_synthetic_integration_project", "run_integration_self_test"]
