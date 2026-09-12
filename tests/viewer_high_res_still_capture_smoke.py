from __future__ import annotations

from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend


class _Scheduler:
    def __init__(self) -> None:
        self.flushes = 0

    def flush(self) -> None:
        self.flushes += 1


class _CaptureProbe(VtkProjectMeshAdaptiveBackend):
    def __init__(self) -> None:
        self._render_scheduler = _Scheduler()
        self._interaction_quality_active = True
        self.transitions: list[bool] = []
        self.capture_scheduler_seen = object()
        self.capture_kwargs: dict[str, object] = {}

    def set_interaction_quality(self, interacting: bool) -> bool:
        requested = bool(interacting)
        self.transitions.append(requested)
        self._interaction_quality_active = requested
        return True


def test_capture_contract_forces_full_quality_and_restores_interaction(monkeypatch, tmp_path):
    backend = _CaptureProbe()
    scheduler = backend._render_scheduler

    def fake_capture(_self, output, **kwargs):
        backend.capture_scheduler_seen = backend._render_scheduler
        backend.capture_kwargs = dict(kwargs)
        assert backend._interaction_quality_active is False
        return output

    monkeypatch.setattr(
        'cws_viewer.backends.vtk_project_mesh_feel_v2.VtkProjectMeshFeelV2Backend.capture_png',
        fake_capture,
    )
    target = tmp_path / 'still.png'
    result = backend.capture_png(target, width=3840, height=2160)

    assert result == target
    assert scheduler.flushes == 1
    assert backend.capture_scheduler_seen is None
    assert backend.capture_kwargs == {'width': 3840, 'height': 2160}
    assert backend.transitions == [False, True]
    assert backend._interaction_quality_active is True
    assert backend._render_scheduler is scheduler


def test_capture_contract_keeps_idle_quality_idle(monkeypatch, tmp_path):
    backend = _CaptureProbe()
    backend._interaction_quality_active = False
    scheduler = backend._render_scheduler

    def fake_capture(_self, output, **kwargs):
        assert backend._render_scheduler is None
        assert backend._interaction_quality_active is False
        return output

    monkeypatch.setattr(
        'cws_viewer.backends.vtk_project_mesh_feel_v2.VtkProjectMeshFeelV2Backend.capture_png',
        fake_capture,
    )
    target = tmp_path / 'still.png'
    assert backend.capture_png(target, width=2560, height=1440) == target
    assert scheduler.flushes == 1
    assert backend.transitions == []
    assert backend._interaction_quality_active is False
    assert backend._render_scheduler is scheduler
