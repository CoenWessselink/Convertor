from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from cws_convertor.project.jobs import JobManager
from cws_convertor.ui_qt.phase3_workspaces import Phase3ExportCenterPanel, ProfileNestingPanel, ScribingWorkspacePanel


def main() -> None:
    app = QApplication.instance() or QApplication([])
    manager = JobManager(max_workers=1)
    scribing = ScribingWorkspacePanel()
    nesting = ProfileNestingPanel()
    export = Phase3ExportCenterPanel(object(), job_manager=manager)
    assert [scribing.phase3_scribing_tabs.tabText(i) for i in range(scribing.phase3_scribing_tabs.count())] == list(
        ScribingWorkspacePanel.TAB_NAMES
    )
    assert nesting.phase3_nesting_tabs.count() == len(ProfileNestingPanel.EXTRA_TABS) + 3
    assert nesting.phase3_nesting_tabs.tabText(nesting.phase3_nesting_tabs.count() - 3) == "Realistisch zaagbeeld"
    assert nesting.phase3_nesting_tabs.tabText(nesting.phase3_nesting_tabs.count() - 2) == "Plaatnesting"
    assert nesting.phase3_nesting_tabs.tabText(nesting.phase3_nesting_tabs.count() - 1) == "Machine-instellingen"
    assert export.job_manager is manager
    assert export.scope.count() == 12
    export._preflight()
    assert "scopeverbreding is verboden" in export.blockers.toPlainText() or "geen actief project" in export.blockers.toPlainText()
    manager.shutdown(wait=True, cancel_pending=True)
    scribing.deleteLater()
    nesting.deleteLater()
    export.deleteLater()
    app.processEvents()
    print("phase3_workspaces_gui_smoke: PASS")


if __name__ == "__main__":
    main()
