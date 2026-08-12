from __future__ import annotations

from pathlib import Path
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import JobManager


class ProjectJobManagerTests(unittest.TestCase):
    def test_completed_job_reports_progress_and_result(self) -> None:
        manager = JobManager(max_workers=1)
        events = []
        manager.add_listener(lambda record: events.append(record.to_dict()))
        try:
            def action(context):
                context.update(0.25, "Bronnen controleren", files=2)
                context.update(0.75, "Projectpakket schrijven")
                return {"status": "ok"}

            job_id = manager.submit("project-test", action, description="Testjob")
            result = manager.wait(job_id, timeout=5)
            record = manager.get(job_id)
            self.assertEqual(result, {"status": "ok"})
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.progress, 1.0)
            self.assertEqual(record.metadata["files"], 2)
            self.assertTrue(any(item["status"] == "running" for item in events))
            self.assertEqual(events[-1]["status"], "completed")
        finally:
            manager.shutdown()

    def test_cancellation_is_explicit(self) -> None:
        manager = JobManager(max_workers=1)
        started = threading.Event()
        try:
            def action(context):
                started.set()
                for index in range(200):
                    context.update(index / 200.0, "Langlopende test")
                    time.sleep(0.005)
                return "should-not-complete"

            job_id = manager.submit("project-cancel", action)
            self.assertTrue(started.wait(timeout=2))
            self.assertTrue(manager.cancel(job_id))
            self.assertIsNone(manager.wait(job_id, timeout=5))
            record = manager.get(job_id)
            self.assertEqual(record.status, "cancelled")
            self.assertTrue(record.finished_at)
        finally:
            manager.shutdown(cancel_pending=True)

    def test_failed_job_keeps_error_and_listener_failure_isolated(self) -> None:
        manager = JobManager(max_workers=1)
        manager.add_listener(lambda _record: (_ for _ in ()).throw(RuntimeError("UI verdwenen")))
        try:
            def action(_context):
                raise ValueError("testfout")

            job_id = manager.submit("project-fail", action)
            with self.assertRaises(ValueError):
                manager.wait(job_id, timeout=5)
            record = manager.get(job_id)
            self.assertEqual(record.status, "failed")
            self.assertIn("ValueError: testfout", record.error)
        finally:
            manager.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
