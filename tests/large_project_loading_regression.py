from __future__ import annotations

import unittest
from types import SimpleNamespace

from cws_convertor.integration.workspace import _renderable_entity_count


class LargeProjectLoadingRegressionTests(unittest.TestCase):
    def test_large_canonical_project_uses_bounded_proxy_warm_start(self) -> None:
        project = SimpleNamespace(
            parts={f"part-{index}": object() for index in range(751)},
            purchased_items={},
            fasteners={"fastener": object()},
            welds={},
        )

        self.assertEqual(_renderable_entity_count(project), 752)


if __name__ == "__main__":
    unittest.main(verbosity=2)
