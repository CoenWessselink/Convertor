"""Display-only smooth-normal patch for the active V15/Adaptive mesh path.

Round IFC/STEP surfaces use interpolated point normals while structural corners
above the feature angle stay split and crisp. Canonical/source geometry is never
changed; only cached VTK render resources are affected.
"""
from __future__ import annotations

from cws_viewer.cache.render_resource_cache import SharedRenderResourceCache
from cws_viewer.backends.vtk_project_mesh_feel import VtkProjectMeshFeelBackend


def _ultra_smooth_mesh_polydata(self: VtkProjectMeshFeelBackend, geometry_id: str):
    vtk = self._vtk
    assert vtk is not None
    mesh = self.repository.require(geometry_id)

    def build():
        import numpy as np
        from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

        points = vtk.vtkPoints()
        points.SetData(numpy_to_vtk(mesh.vertices, deep=True))
        cells = mesh.triangles.astype("int64", copy=False)
        connectivity = numpy_to_vtkIdTypeArray(cells.ravel(), deep=True)
        offsets = numpy_to_vtkIdTypeArray(
            np.arange(0, (len(cells) + 1) * 3, 3, dtype=np.int64), deep=True
        )
        cell_array = vtk.vtkCellArray()
        cell_array.SetData(offsets, connectivity)
        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(cell_array)

        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(polydata)
        normals.ConsistencyOn()
        normals.AutoOrientNormalsOff()
        normals.SplittingOn()
        normals.SetFeatureAngle(float(self.FEATURE_ANGLE_DEG))
        normals.ComputePointNormalsOn()
        normals.ComputeCellNormalsOff()
        normals.NonManifoldTraversalOn()
        normals.Update()

        output = vtk.vtkPolyData()
        output.ShallowCopy(normals.GetOutput())
        return output

    output = SharedRenderResourceCache.get_or_create(
        self.repository,
        "polydata",
        f"{geometry_id}|mesh-feel-v2-ultra-smooth|{mesh.mesh_hash}",
        build,
    )
    self._cws_polydata_cache = getattr(self, "_cws_polydata_cache", {})
    self._cws_polydata_cache[str(geometry_id)] = output
    return output


def install_ultra_smooth_render_patch() -> None:
    if getattr(VtkProjectMeshFeelBackend, "_cws_ultra_smooth_patch", False):
        return
    VtkProjectMeshFeelBackend._mesh_polydata = _ultra_smooth_mesh_polydata
    VtkProjectMeshFeelBackend._cws_ultra_smooth_patch = True


install_ultra_smooth_render_patch()

__all__ = ["install_ultra_smooth_render_patch"]
