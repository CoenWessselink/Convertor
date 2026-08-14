from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_viewer.properties import (
    FilterOperator,
    GridFilter,
    GridGroupSpec,
    GridQuery,
    GridScope,
    GridSort,
    ProjectGridModel,
)


def _part(index: int):
    blocked = index % 17 == 0
    material = "S355JR" if index % 3 else "S235JR"
    profile = ("HEA140", "HEA160", "STRIP5*120", "D20")[index % 4]
    assembly = f"M{index // 100:04d}"
    return SimpleNamespace(
        internal_id=f"part-{index:06d}",
        status="blocked" if blocked else "validated",
        category="make_part",
        part_position=f"P{index:06d}",
        assembly_ids=[assembly],
        name=f"Onderdeel {index:06d}",
        profile=profile,
        normalized_profile=profile,
        material=material,
        normalized_material=material,
        length_mm=float(500 + index % 7500),
        quantity_total=1 + index % 4,
        mass_each_kg=float((index % 250) / 10.0),
        surface_area_each_m2=float((index % 100) / 100.0),
        classification_status="confirmed" if not blocked else "review_required",
        export_status="blocked" if blocked else "ready",
        nc1_eligible=not blocked,
        validation_issues=(() if not blocked else (SimpleNamespace(code="CWS-TEST-BLOCK", message="Controle vereist"),)),
        source_identity=SimpleNamespace(
            source_entity_id=str(index + 1),
            source_format="ifc",
            assembly_mark=assembly,
            part_position=f"P{index:06d}",
        ),
        confidence=1.0,
        geometry_hash=("a" * 64),
        manufacturing_hash=("b" * 64),
    )


class ViewerV8GridQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.project = SimpleNamespace(
            project_phase="Productie",
            parts={f"part-{index:06d}": _part(index) for index in range(20_000)},
            assemblies={},
            purchased_items={},
            fasteners={},
            welds={},
        )
        started = time.perf_counter()
        cls.model = ProjectGridModel(cls.project)
        cls.build_ms = (time.perf_counter() - started) * 1000.0

    def test_virtual_query_filter_sort_group_and_footer(self) -> None:
        query = GridQuery(
            text="HEA",
            filters=(
                GridFilter("material", FilterOperator.EQ, "S355JR"),
                GridFilter("length_mm", FilterOperator.BETWEEN, 1000, 5000),
            ),
            sorts=(GridSort("length_mm", descending=True), GridSort("part_position")),
            groups=(GridGroupSpec("profile"), GridGroupSpec("assembly_mark")),
        )
        result = self.model.execute(query)
        self.assertGreater(result.row_count, 0)
        self.assertLess(result.elapsed_ms, 1500.0)
        page = result.rows_page(0, 50)
        self.assertEqual(50, len(page))
        self.assertTrue(all("HEA" in str(row.get("profile")) for row in page))
        self.assertTrue(all(row.get("material") == "S355JR" for row in page))
        lengths = [float(row.get("length_mm")) for row in page]
        self.assertEqual(lengths, sorted(lengths, reverse=True))
        self.assertTrue(result.groups)
        self.assertEqual(result.row_count, result.footer.row_count)
        total_mass = next(item.value for item in result.footer.aggregates if item.key == "total_mass_kg")
        expected = sum(float(row.get("total_mass_kg")) for row in result.iter_rows())
        self.assertAlmostEqual(float(total_mass), expected, places=6)

    def test_in_filter_is_case_insensitive_for_sequences(self) -> None:
        result = self.model.execute(
            GridQuery(
                filters=(
                    GridFilter(
                        "part_position",
                        FilterOperator.IN,
                        ("P000007", "p000008"),
                    ),
                )
            )
        )
        self.assertEqual(2, result.row_count)
        self.assertEqual(
            {"P000007", "P000008"},
            {str(row.get("part_position")) for row in result.iter_rows()},
        )

    def test_scopes_are_deterministic(self) -> None:
        selected = tuple(f"part-{index:06d}" for index in range(0, 200, 7))
        visible = tuple(f"part-{index:06d}" for index in range(1000))
        self.model.set_scope_state(visible_entity_ids=visible, selected_entity_ids=selected)
        self.assertEqual(len(visible), self.model.execute(GridQuery(scope=GridScope.VISIBLE)).row_count)
        self.assertEqual(len(selected), self.model.execute(GridQuery(scope=GridScope.SELECTED)).row_count)
        blocked = self.model.execute(GridQuery(scope=GridScope.BLOCKED))
        self.assertGreater(blocked.row_count, 0)
        self.assertTrue(all(bool(row.get("blocked")) for row in blocked.iter_rows()))

    def test_20k_baseline_is_reasonably_bounded(self) -> None:
        # Development guardrail, not an end-user SLA.
        self.assertEqual(20_000, len(self.model.rows))
        self.assertLess(self.build_ms, 5000.0)
        first = self.model.execute(GridQuery(sorts=(GridSort("part_position"),)))
        second = self.model.execute(GridQuery(sorts=(GridSort("part_position"),)))
        self.assertEqual(first.row_indices, second.row_indices)
        self.assertLess(second.elapsed_ms, 1500.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
