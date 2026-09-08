"""Reproduce hash-verified follow-up edits as Git file objects; never update refs."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CHANGES = {}

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def edit(name, pairs):
    original = git('show', 'HEAD:' + name)
    text = original.decode('utf-8')
    for pair in pairs:
        old, new = pair[:2]
        count = pair[2] if len(pair) > 2 else 1
        if text.count(old) != count:
            raise RuntimeError('Ambiguous source patch: ' + name + ' ' + repr(old))
        text = text.replace(old, new)
    compile(text, name, 'exec')
    CHANGES[name] = text.encode('utf-8')

edit('ifc_native.py', [
    ('class NativeIFCParseError(ValueError):', '''@dataclass(frozen=True)
class NativeIFCComponent:
    """One explicitly identified assembly member, before any tessellation."""

    name: str
    material: str
    shape: cq.Shape


class NativeIFCParseError(ValueError):'''),
    ('def write_native_ifc(\n    shape: cq.Shape,', 'def write_native_ifc(\n    shape: cq.Shape | None,'),
    ('    tolerance_mm: float = 0.20,\n) -> Path:', '    tolerance_mm: float = 0.20,\n    components: Iterable[NativeIFCComponent] | None = None,\n) -> Path:'),
    ('    meshes = _solid_meshes(shape, tolerance_mm)\n    if not meshes:\n        raise ValueError("Model bevat geen exporteerbare solid/mesh")\n', '''    # Member/grade bindings are kept before tessellation. Do not reconstruct
    # them from the ordering of an already combined compound's solids.
    members = tuple(components) if components is not None else None
    meshes = []
    mesh_names: list[str] = []
    mesh_materials: list[str] = []
    if members is None:
        if shape is None:
            raise ValueError("Model bevat geen geometrie")
        meshes = _solid_meshes(shape, tolerance_mm)
        if not meshes:
            raise ValueError("Model bevat geen exporteerbare solid/mesh")
    elif shape is not None:
        raise ValueError("Geef componentgeometrie of één shape, niet beide")
'''),
    ('    material = str(material or canonical.material or "").strip()\n    definition', '''    material = str(material or canonical.material or "").strip()
    if members is not None:
        if declared_values or canonical.product.material_code:
            raise ValueError("Een samenstelling mag geen geërfde materiaalkwaliteit bevatten")
        if not members:
            raise ValueError("Samenstelling bevat geen componenten")
        seen_names: set[str] = set()
        for member in members:
            if not member.name.strip() or member.name in seen_names:
                raise ValueError("Componentnamen moeten uniek en niet leeg zijn")
            seen_names.add(member.name)
            resolution = database.resolve(member.material)
            if not resolution.resolved:
                raise ValueError("Componentmateriaal is niet exact bekend: " + member.name)
            member_meshes = _solid_meshes(member.shape, tolerance_mm)
            if not member_meshes:
                raise ValueError("Component bevat geen exporteerbare geometrie: " + member.name)
            for index, mesh in enumerate(member_meshes, start=1):
                meshes.append(mesh)
                mesh_names.append(member.name if len(member_meshes) == 1 else f"{member.name}_{index:03d}")
                mesh_materials.append(resolution.material_code)
    definition'''),
    ('    element_ids: list[int] = []\n    for index', '    element_ids: list[int] = []\n    component_material_refs: dict[str, list[int]] = {}\n    for index'),
    ('        element_name = name if len(meshes) == 1 else f"{name}_{index:03d}"\n        ifc_class', '''        element_name = name if len(meshes) == 1 else f"{name}_{index:03d}"
        if members is not None:
            element_name = mesh_names[index - 1]
            component_material_refs.setdefault(mesh_materials[index - 1], []).append(element_id)
        ifc_class'''),
    ('    properties: list[tuple[str, str, str]] = [', '''    for member_grade, ids in sorted(component_material_refs.items()):
        definition = database.resolve(member_grade).definition
        grade_id, relation_id = next_id, next_id + 1
        next_id += 2
        refs = ",".join(f"#{entity_id}" for entity_id in ids)
        lines.extend([
            f"#{grade_id}=IFCMATERIAL('{_escape_ifc(member_grade)}',$,'{_escape_ifc(definition.category)}');",
            f"#{relation_id}=IFCRELASSOCIATESMATERIAL("
            f"'{_guid22(name + ':component-material:' + member_grade)}',#5,$,$,({refs}),#{grade_id});",
        ])

    properties: list[tuple[str, str, str]] = ['''),
])
edit('cws_convertor/production_export/release.py', [
    ('            from ifc_native import write_native_ifc', '            from ifc_native import NativeIFCComponent, write_native_ifc'),
    ('                "parts": [item_by_id[part_id].to_dict() for part_id in part_ids],', '''                "parts": [{**item_by_id[part_id].to_dict(),
                           "material": canonicals[part_id].material,
                           "material_grade": canonicals[part_id].product.material_grade}
                          for part_id in part_ids],'''),
    ('            synthetic = canonicals[part_ids[0]].clone()', '''            # This record describes the assembly, not its first member. A
            # clone would also leak that member's grade, density and evidence.
            synthetic = CanonicalPart()'''),
    ('            synthetic.header.material = "MULTI"', '            synthetic.header.material = ""'),
    ('            synthetic.product.material_code = "MULTI"', '            synthetic.product.material_code = ""\n            synthetic.product.material_grade = ""'),
    ('            write_native_ifc(compound, assembly_ifc, name=mark, material="MULTI", canonical=synthetic)', '''            write_native_ifc(
                None, assembly_ifc, name=mark, material="", canonical=synthetic,
                components=[NativeIFCComponent(part.internal_id,
                            canonicals[part.internal_id].material, shape)
                            for part, (_part_name, shape) in zip(parts, transformed)],
            )'''),
])
edit('tools/build_tested_installer.py', [
    ("                                    '--expect-absent'], 180)", "                                    '--runtime-dir', str(STAGING), '--expect-absent'], 180)")
])
edit('runtime_diagnostics.py', [('            material="S355JR",', '            material="S355JR",\n            material_grade="S355JR",', 2)])
edit('tests/canonical_rebuild_smoke.py', [
    (f'            internal_id="{identity}",', f'            internal_id="{identity}",\n' + (f'            profile="{profile}",\n' if profile else '') + '            material="S355J2", material_grade="S355J2",')
    for identity, profile in [('part-1', ''), ('inner', 'PL10'), ('round', 'RU20'), ('profile', 'HEA240')]
])
for name in ['manufacturing_face_core', 'manufacturing_contact_core']:
    edit('tests/' + name + '_smoke.py', [('material="S235"', 'material="S235JR"'), ('"material": "S235"', '"material": "S235JR"')])
edit('tests/part_workbench_ui_smoke.py', [
    ('material="S355",', 'material="S355J2",\n            material_grade="S355J2",'),
    ('self.panel.material_var.set("S355")', 'self.panel.material_var.set("S355J2")'),
    ('self.assertEqual(part.material, "S355")', 'self.assertEqual(part.material, "S355J2")')
])
edit('tests/edit_workspace_ui_smoke.py', [('            material="S355JR",', '            material="S355JR",\n            material_grade="S355JR",')])
edit('tests/dimension_graph_smoke.py', [('"confirm": ["holes[0]"]', '"confirm": ["holes[0]", "material"]')])
edit('tests/review_workflow_smoke.py', [('confirm=["holes[0]"]', 'confirm=["holes[0]", "material"]', 3)])
edit('tests/viewer_v6_integration_smoke.py', [('                    "part_form": "plate",', '                    "part_form": "plate",\n                    "production_properties": {"profile": "PL10", "material": "S355J2", "material_grade": "S355J2"},')])
edit('tests/project_cli_smoke.py', [('self.assertEqual(APP_VERSION, "0.10.21-beta-dev")', 'self.assertEqual(APP_VERSION, "0.10.18-beta-dev")')])
keys = {
    'cws_convertor.ui_qt.bom_workspace._BomViewerPane': ['area_selection', 'lasso_selection', 'select_same_colour', 'shared_cache_summary', 'isolate_selection', 'show_all'],
    'cws_convertor.ui_qt.functional_workspaces.EditWorkspacePanel': ['start_selected_step_recognition', 'cancel_selected_step_recognition', 'accept_material_candidate', 'reject_material_candidate', 'preview_bulk_material', 'apply_bulk_material', 'undo_bulk_material'],
    'cws_convertor.ui_qt.product_workspaces.ProductionWorkflowPanel': ['refresh'],
    'cws_convertor.ui_qt.bom_workspace.BomWorkspacePanel': ['refresh'],
}
extra = ''.join(f'        "{owner}.{method}": (),\n' for owner, methods in keys.items() for method in methods)
extra += '        "cws_convertor.ui_qt.bom_workspace.BomWorkspacePanel.handle_ribbon": ("filter",),\n'
edit('tools/run_full_product_acceptance.py', [('    safe_method_arguments: dict[str, tuple[Any, ...]] = {', '    safe_method_arguments: dict[str, tuple[Any, ...]] = {\n' + extra)])
edit('tools/run_material_model_recognition_acceptance.py', [('    SuiteSpec("tests/material_model_acceptance_runner_smoke.py", "acceptance_integrity"),', '    SuiteSpec("tests/assembly_material_binding_smoke.py", "assembly_material_binding", ("cadquery",)),\n    SuiteSpec("tests/production_release_package_smoke.py", "assembly_release", ("cadquery",)),\n    SuiteSpec("tests/material_model_acceptance_runner_smoke.py", "acceptance_integrity"),')])
CHANGES['tests/assembly_material_binding_smoke.py'] = git('show', 'HEAD:tests/assembly_material_binding_smoke.py')
expected = {
'cws_convertor/production_export/release.py': '2e8f2d40f0ce82342a8aa0597d6078b69b384ab7',
'ifc_native.py': '9353807105862abaab9e0df7eef8b43c5065d4f2',
'runtime_diagnostics.py': '3aae7a5e5a4bf4be2816a58977c34ebdf157c723',
'tests/canonical_rebuild_smoke.py': '4fe421f4a02937c47a930b69cc96b9c2ad42b73b',
'tests/dimension_graph_smoke.py': '82f028dfaceb90bf6064466900bfc6e9f9d2f180',
'tests/edit_workspace_ui_smoke.py': 'ad488b4f3f989a5b0151f9d516a811627f1f4c19',
'tests/manufacturing_contact_core_smoke.py': '7e04ca5138c0db6dab508403f9e686855fa8c336',
'tests/manufacturing_face_core_smoke.py': 'abb6779bf4ea3bc4ea56a86fcbd6bdfc6ea3dfcd',
'tests/part_workbench_ui_smoke.py': 'f3cea057bef7fd536aa99fd1ffbb8d47fac4cb28',
'tests/project_cli_smoke.py': '2ccf16e1695eb4e90d8ebc0dbaea54b57aebbe28',
'tests/review_workflow_smoke.py': 'ecfd06ad7f6adc84e77558c2aa0bd9ee4069114e',
'tests/viewer_v6_integration_smoke.py': '86ce2558401e6f8fcce25efb3dddb9a257e4c15c',
'tools/build_tested_installer.py': 'd3a7b18dc842348301b8e9e013aeba6e4fea36a0',
'tools/run_full_product_acceptance.py': '67d511d6bb9efdbccb46471e9418422c5f3e1384',
'tools/run_material_model_recognition_acceptance.py': '79c999a22b3b7a4cbd6c104429ab675789abe5cc',
'tests/assembly_material_binding_smoke.py': '33f96dca37d04947a7e612f5ffcd6db15419c4ac',
}
if set(expected) != set(CHANGES):
    raise RuntimeError('Unexpected paths')
objects = []
for path, content in sorted(CHANGES.items()):
    sha = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
    if sha != expected[path]:
        raise RuntimeError('Reviewed output mismatch: ' + path + ' ' + sha)
    compile(content, path, 'exec')
    objects.append({'path': path, 'sha': sha, 'content': base64.b64encode(content).decode('ascii')})
output = ROOT / 'build/installer-followup'
output.mkdir(parents=True, exist_ok=True)
(output / 'objects.json').write_text(json.dumps({'parent': git('rev-parse', 'HEAD').decode().strip(), 'objects': objects}), encoding='utf-8')
print(json.dumps({'verified_files': len(objects), 'expected': expected}), flush=True)
