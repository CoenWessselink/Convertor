from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cli
from cws_convertor.product import APP_NAME, APP_VERSION

STEP_FIXTURE = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION((''),'2;1');
FILE_NAME('CLI.step','2026-01-01T00:00:00',('CWS'),('CWS'),'Onshape','Onshape','');
FILE_SCHEMA(('AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF'));
ENDSEC;
DATA;
#1=PRODUCT('CLI','CLI','',());
#2=MANIFOLD_SOLID_BREP('solid',#3);
#3=CLOSED_SHELL('shell',());
ENDSEC;
END-ISO-10303-21;
"""


class ProjectCLITests(unittest.TestCase):
    def run_cli(self, *args: str, expected: int = 0) -> tuple[str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = cli.main(list(args))
        self.assertEqual(
            code,
            expected,
            msg=f"stdout:\n{stdout.getvalue()}\nstderr:\n{stderr.getvalue()}",
        )
        return stdout.getvalue(), stderr.getvalue()

    def test_full_project_command_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cws_cli_") as folder_name:
            folder = Path(folder_name)
            source = folder / "CLI.step"
            source.write_text(STEP_FIXTURE, encoding="utf-8")
            project_base = folder / "cli_project"
            create_report = folder / "create.json"
            self.run_cli(
                "project-new",
                str(project_base),
                "--name",
                "CLI project",
                "--customer",
                "CWS",
                "--order",
                "CLI-001",
                "--json-report",
                str(create_report),
            )
            project = project_base.with_suffix(".cwscproj")
            self.assertTrue(project.is_file())
            create_payload = json.loads(create_report.read_text(encoding="utf-8"))
            self.assertEqual(create_payload["status"], "passed")

            baseline_report = folder / "baseline.json"
            import_report = folder / "import.json"
            self.run_cli(
                "project-import-baseline",
                str(project),
                str(source),
                "--baseline-report",
                str(baseline_report),
                "--json-report",
                str(import_report),
            )
            imported = json.loads(import_report.read_text(encoding="utf-8"))
            self.assertEqual(imported["status"], "passed")
            self.assertFalse(imported["production_export_allowed"])
            self.assertTrue(imported["semantic_import_pending"])
            self.assertEqual(imported["analyses"][0]["analysis"]["product_count"], 1)
            self.assertFalse(imported["analyses"][0]["production_export_allowed"])

            info_stdout, _ = self.run_cli("project-info", str(project), "--json")
            info_payload = json.loads(info_stdout)
            self.assertEqual(info_payload["summary"]["project_name"], "CLI project")
            self.assertFalse(info_payload["summary"]["production_gate"]["allowed"])

            source_stdout, _ = self.run_cli("project-sources", str(project), "--json")
            sources_payload = json.loads(source_stdout)
            self.assertEqual(len(sources_payload["sources"]), 1)
            source_id = sources_payload["sources"][0]["source_id"]

            semantic_report = folder / "semantic.json"
            semantic_stdout, _ = self.run_cli(
                "project-import",
                str(project),
                "--source-id",
                source_id,
                "--json",
                "--json-report",
                str(semantic_report),
                expected=cli.EXIT_REVIEW_REQUIRED,
            )
            semantic_payload = json.loads(semantic_stdout)
            self.assertEqual(semantic_payload["status"], "review_required")
            self.assertEqual(semantic_payload["semantic_imports"][0]["entity_counts"]["parts"], 1)
            self.assertFalse(semantic_payload["production_export_allowed"])
            self.assertTrue(semantic_report.is_file())

            parts_stdout, _ = self.run_cli("project-list-parts", str(project), "--json")
            parts_payload = json.loads(parts_stdout)
            self.assertEqual(parts_payload["total_matching"], 1)
            self.assertEqual(parts_payload["parts"][0]["name"], "CLI")
            self.assertFalse(parts_payload["parts"][0]["nc1_eligible"])

            tree_stdout, _ = self.run_cli("project-tree", str(project), "--json")
            tree_payload = json.loads(tree_stdout)
            self.assertEqual(tree_payload["assembly_count"], 0)
            self.assertEqual(len(tree_payload["standalone_part_ids"]), 1)

            verify_stdout, _ = self.run_cli("project-verify", str(project), "--json")
            verify_payload = json.loads(verify_stdout)
            self.assertTrue(verify_payload["checks"]["zip_crc"])
            self.assertTrue(verify_payload["checks"]["sqlite_integrity"])

            model_json = folder / "project-model.json"
            self.run_cli("project-export-json", str(project), "-o", str(model_json))
            model_payload = json.loads(model_json.read_text(encoding="utf-8"))
            self.assertIn(source_id, model_payload["sources"])

            extract_dir = folder / "extracted"
            extract_dir.mkdir()
            self.run_cli(
                "project-extract-source",
                str(project),
                source_id,
                "-o",
                str(extract_dir),
            )
            self.assertEqual((extract_dir / source.name).read_bytes(), source.read_bytes())

    def test_version_identity(self) -> None:
        self.assertEqual(APP_NAME, "CWS Convertor")
        self.assertEqual(APP_VERSION, "0.8.1-alpha-dev")
        parser = cli.build_parser()
        self.assertIn("CWS Convertor", parser.description or "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
