from cws_viewer.backends.vtk_project_mesh_adaptive import VtkProjectMeshAdaptiveBackend


class _Mapper:
    def __init__(self):
        self.culling = None
        self.lod_count = None

    def SetCullingAndLOD(self, enabled):
        self.culling = bool(enabled)

    def SetNumberOfLOD(self, count):
        self.lod_count = int(count)


class _LegacyMapper:
    pass


def _backend():
    backend = object.__new__(VtkProjectMeshAdaptiveBackend)
    backend._native_culling_mapper_count = 0
    backend._native_culling_fallback_count = 0
    return backend


def test_native_instance_culling_keeps_exact_mesh_lod_count_zero():
    backend = _backend()
    mapper = _Mapper()
    assert backend._configure_native_instance_culling(mapper, instance_count=5725) is True
    assert mapper.culling is True
    assert mapper.lod_count == 0
    assert backend.native_instance_culling_stats == {"enabled_mappers": 1, "fallback_mappers": 0}


def test_native_instance_culling_stays_off_for_tiny_groups():
    backend = _backend()
    mapper = _Mapper()
    assert backend._configure_native_instance_culling(mapper, instance_count=64) is False
    assert mapper.culling is None
    assert mapper.lod_count is None
    assert backend.native_instance_culling_stats == {"enabled_mappers": 0, "fallback_mappers": 0}


def test_native_instance_culling_fails_safe_for_unsupported_mapper():
    backend = _backend()
    assert backend._configure_native_instance_culling(_LegacyMapper(), instance_count=5725) is False
    assert backend.native_instance_culling_stats == {"enabled_mappers": 0, "fallback_mappers": 1}


def test_real_vtk_glyph_mapper_accepts_culling_with_zero_lods():
    import vtk

    backend = _backend()
    points = vtk.vtkPoints()
    for index in range(64):
        points.InsertNextPoint(float(index % 8) * 2.0, float(index // 8) * 2.0, 0.0)
    instances = vtk.vtkPolyData()
    instances.SetPoints(points)
    source = vtk.vtkCubeSource()
    source.SetXLength(1.0)
    source.SetYLength(1.0)
    source.SetZLength(1.0)
    source.Update()
    mapper = vtk.vtkGlyph3DMapper()
    mapper.SetInputData(instances)
    mapper.SetSourceData(source.GetOutput())
    mapper.ScalingOff()
    assert backend._configure_native_instance_culling(mapper, instance_count=5725) is True
    assert bool(mapper.GetCullingAndLOD()) is True

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer = vtk.vtkRenderer()
    renderer.AddActor(actor)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(320, 240)
    window.AddRenderer(renderer)
    renderer.ResetCamera()
    window.Render()
