"""Automatische hoeveelheden uit STEP/IFC en professionele Excel-export."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from cws_convertor.product import APP_NAME
import json
import tempfile
from typing import Any, Iterable

import cadquery as cq

from material_database import MaterialDatabase, MaterialDefinition
from profile_database import ProfileDatabase


@dataclass
class QuantityItem:
    source_file: str
    source_type: str
    item_id: str
    name: str
    object_type: str
    profile: str
    material_code: str
    material_name: str
    quantity: int
    length_mm: float
    width_mm: float
    height_mm: float
    surface_area_mm2: float
    volume_mm3: float
    density_kg_m3: float
    mass_kg: float
    guid: str = ""
    tag: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class QuantityAnalysis:
    sources: list[Path]
    items: list[QuantityItem]
    warnings: list[str] = field(default_factory=list)

    @property
    def total_quantity(self) -> int:
        return sum(max(item.quantity, 1) for item in self.items)

    @property
    def total_volume_mm3(self) -> float:
        return sum(item.volume_mm3 * max(item.quantity, 1) for item in self.items)

    @property
    def total_mass_kg(self) -> float:
        return sum(item.mass_kg * max(item.quantity, 1) for item in self.items)


def _sorted_bbox(shape: cq.Shape) -> tuple[float, float, float]:
    box = shape.BoundingBox()
    return tuple(sorted((float(box.xlen), float(box.ylen), float(box.zlen)), reverse=True))


def _profile_for_single_step(source: Path, profile_database: ProfileDatabase) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    try:
        import converter as core
        plate = core.analyze_step_plate(source)
        return f"PL{core._fmt_number(plate.thickness)}*{core._fmt_number(plate.width)}", "IfcPlate", warnings
    except Exception:
        pass
    try:
        from conversion import analyze_step_profile
        analysis = analyze_step_profile(source, profile_database=profile_database, tolerance_mm=1.5)
        warnings.extend(analysis.warnings)
        return analysis.profile.designation, "IfcMember", warnings
    except Exception as exc:
        warnings.append(f"Profiel niet automatisch herkend: {exc}")
        return "", "Solid", warnings


def extract_step_quantities(
    path: str | Path,
    *,
    material_code: str = "S355JR",
    material_database: MaterialDatabase | None = None,
    profile_database: ProfileDatabase | None = None,
) -> QuantityAnalysis:
    source = Path(path)
    materials = material_database or MaterialDatabase()
    profiles = profile_database or ProfileDatabase()
    material = materials.find(material_code)
    shape = cq.importers.importStep(str(source)).val()
    solids = list(shape.Solids())
    if not solids:
        solids = [shape]
    items: list[QuantityItem] = []
    warnings: list[str] = []
    shared_profile, shared_type, profile_warnings = ("", "Solid", [])
    if len(solids) == 1:
        shared_profile, shared_type, profile_warnings = _profile_for_single_step(source, profiles)
        warnings.extend(profile_warnings)

    for index, solid in enumerate(solids, start=1):
        length, width, height = _sorted_bbox(solid)
        volume = float(solid.Volume())
        area = float(solid.Area())
        mass = volume / 1e9 * material.density_kg_m3
        name = source.stem if len(solids) == 1 else f"{source.stem}_{index:03d}"
        items.append(
            QuantityItem(
                source_file=source.name,
                source_type="STEP",
                item_id=str(index),
                name=name,
                object_type=shared_type if len(solids) == 1 else "Solid",
                profile=shared_profile if len(solids) == 1 else "",
                material_code=material.code,
                material_name=material.name,
                quantity=1,
                length_mm=length,
                width_mm=width,
                height_mm=height,
                surface_area_mm2=area,
                volume_mm3=volume,
                density_kg_m3=material.density_kg_m3,
                mass_kg=mass,
                properties={
                    "STEP": {
                        "SolidIndex": index,
                        "SolidCount": len(solids),
                        "BoundingBoxSorted_mm": [length, width, height],
                    }
                },
                warnings=list(profile_warnings) if len(solids) == 1 else [],
            )
        )
    return QuantityAnalysis([source], items, warnings)


def extract_ifc_quantities(
    path: str | Path,
    *,
    fallback_material: str = "S355JR",
    material_database: MaterialDatabase | None = None,
) -> QuantityAnalysis:
    from ifc_support import load_ifc_geometry

    source = Path(path)
    materials = material_database or MaterialDatabase()
    model = load_ifc_geometry(source)
    items: list[QuantityItem] = []
    warnings = list(model.warnings)
    for index, element in enumerate(model.items, start=1):
        material = materials.find(element.material_name or fallback_material, default=fallback_material)
        length, width, height = element.bbox_mm
        volume = element.volume_mm3
        area = element.area_mm2
        mass = volume / 1e9 * material.density_kg_m3
        profile = _find_profile_text(element.properties) or _find_profile_text(element.quantities)
        props = {
            "IFC property sets": element.properties,
            "IFC quantities": element.quantities,
        }
        items.append(
            QuantityItem(
                source_file=source.name,
                source_type="IFC",
                item_id=str(index),
                name=element.name,
                object_type=element.ifc_class,
                profile=profile,
                material_code=material.code,
                material_name=element.material_name or material.name,
                quantity=1,
                length_mm=length,
                width_mm=width,
                height_mm=height,
                surface_area_mm2=area,
                volume_mm3=volume,
                density_kg_m3=material.density_kg_m3,
                mass_kg=mass,
                guid=element.guid,
                tag=element.tag,
                properties=props,
                warnings=list(element.warnings),
            )
        )
    return QuantityAnalysis([source], items, warnings)


def _find_profile_text(value: Any) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(token in key_lower for token in ("profile", "section", "crosssection")) and isinstance(item, (str, int, float)):
                return str(item)
            result = _find_profile_text(item)
            if result:
                return result
    elif isinstance(value, (list, tuple)):
        for item in value:
            result = _find_profile_text(item)
            if result:
                return result
    return ""


def analyze_files(
    paths: Iterable[str | Path],
    *,
    fallback_material: str = "S355JR",
    material_database: MaterialDatabase | None = None,
    profile_database: ProfileDatabase | None = None,
) -> QuantityAnalysis:
    materials = material_database or MaterialDatabase()
    profiles = profile_database or ProfileDatabase()
    all_items: list[QuantityItem] = []
    warnings: list[str] = []
    sources: list[Path] = []
    for item in paths:
        path = Path(item)
        if path.is_dir():
            candidates = sorted(
                candidate
                for candidate in path.iterdir()
                if candidate.is_file() and candidate.suffix.lower() in {".step", ".stp", ".ifc"}
            )
        else:
            candidates = [path]
        for source in candidates:
            try:
                if source.suffix.lower() == ".ifc":
                    result = extract_ifc_quantities(source, fallback_material=fallback_material, material_database=materials)
                elif source.suffix.lower() in {".step", ".stp"}:
                    result = extract_step_quantities(
                        source,
                        material_code=fallback_material,
                        material_database=materials,
                        profile_database=profiles,
                    )
                else:
                    continue
                sources.extend(result.sources)
                all_items.extend(result.items)
                warnings.extend(f"{source.name}: {warning}" for warning in result.warnings)
            except Exception as exc:
                warnings.append(f"{source.name}: hoeveelheden niet bepaald: {exc}")
    if not all_items:
        detail = "\n".join(warnings[:10])
        raise ValueError("Geen hoeveelheden konden worden bepaald." + (f"\n{detail}" if detail else ""))
    return QuantityAnalysis(sources, all_items, warnings)


def _flatten(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _flatten(f"{prefix}.{key}" if prefix else str(key), item, output)
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _flatten(f"{prefix}[{index}]", item, output)
    else:
        output[prefix] = value


def export_excel(
    output_path: str | Path,
    analysis: QuantityAnalysis,
    *,
    material_database: MaterialDatabase | None = None,
    profile_database: ProfileDatabase | None = None,
) -> Path:
    try:
        import xlsxwriter
    except Exception as exc:
        raise RuntimeError("Excel-export vereist XlsxWriter. Start start_converter.bat opnieuw.") from exc

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    materials = material_database or MaterialDatabase()
    profiles = profile_database or ProfileDatabase()
    workbook = xlsxwriter.Workbook(str(target))
    workbook.set_properties(
        {
            "title": "Hoeveelheden IFC / STEP",
            "subject": "Automatische hoeveelheden en materiaaleigenschappen",
            "author": APP_NAME,
            "comments": "Controleer waarden voor productie tegen bronmodel, norm en materiaalcertificaat.",
        }
    )
    fmt_header = workbook.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1})
    fmt_sub = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
    fmt_text = workbook.add_format({"border": 1})
    fmt_num = workbook.add_format({"border": 1, "num_format": "0.000"})
    fmt_int = workbook.add_format({"border": 1, "num_format": "0"})
    fmt_warn = workbook.add_format({"border": 1, "font_color": "#9C5700", "bg_color": "#FFEB9C", "text_wrap": True})
    fmt_note = workbook.add_format({"italic": True, "font_color": "#666666", "text_wrap": True})
    fmt_total = workbook.add_format({"bold": True, "top": 2, "num_format": "0.000"})

    # Hoeveelheden
    sheet = workbook.add_worksheet("Hoeveelheden")
    headers = [
        "Bronbestand", "Bronsoort", "Item", "Naam", "IFC-klasse / type", "GUID", "Tag", "Profiel",
        "Materiaalcode", "Materiaalomschrijving", "Aantal", "Lengte mm", "Breedte mm", "Hoogte/dikte mm",
        "Oppervlak mm²", "Volume mm³", "Dichtheid kg/m³", "Massa per stuk kg", "Totale massa kg", "Waarschuwingen",
    ]
    for col, text in enumerate(headers):
        sheet.write(0, col, text, fmt_header)
    for row, item in enumerate(analysis.items, start=1):
        values = [
            item.source_file, item.source_type, item.item_id, item.name, item.object_type, item.guid, item.tag, item.profile,
            item.material_code, item.material_name, item.quantity, item.length_mm, item.width_mm, item.height_mm,
            item.surface_area_mm2, item.volume_mm3, item.density_kg_m3, item.mass_kg,
        ]
        for col, value in enumerate(values):
            if col == 10:
                sheet.write_number(row, col, int(value), fmt_int)
            elif col >= 11 and isinstance(value, (int, float)):
                sheet.write_number(row, col, float(value), fmt_num)
            else:
                sheet.write(row, col, value, fmt_text)
        # Formula uses quantity * volume (mm³) / 1e9 * density.
        formula = f"=K{row+1}*P{row+1}/1000000000*Q{row+1}"
        sheet.write_formula(row, 18, formula, fmt_num, item.mass_kg * item.quantity)
        warning_text = " | ".join(item.warnings)
        sheet.write(row, 19, warning_text, fmt_warn if warning_text else fmt_text)
    total_row = len(analysis.items) + 2
    sheet.write(total_row, 17, "Totaal:", fmt_total)
    if analysis.items:
        sheet.write_formula(total_row, 18, f"=SUM(S2:S{len(analysis.items)+1})", fmt_total, analysis.total_mass_kg)
    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(len(analysis.items), 1), len(headers) - 1)
    widths = [28,10,8,28,20,24,14,18,15,30,8,13,13,15,16,16,16,17,17,55]
    for index, width in enumerate(widths):
        sheet.set_column(index, index, width)

    # Samenvatting
    summary = workbook.add_worksheet("Samenvatting")
    summary.write(0, 0, "Kengetal", fmt_header)
    summary.write(0, 1, "Waarde", fmt_header)
    summary_rows = [
        ("Aantal bronbestanden", len({item.source_file for item in analysis.items})),
        ("Aantal regels/objecten", len(analysis.items)),
        ("Totaal aantal", analysis.total_quantity),
        ("Totaal volume mm³", analysis.total_volume_mm3),
        ("Totaal volume m³", analysis.total_volume_mm3 / 1e9),
        ("Totale massa kg", analysis.total_mass_kg),
        ("Totale massa ton", analysis.total_mass_kg / 1000.0),
        ("Aantal waarschuwingen", len(analysis.warnings) + sum(bool(item.warnings) for item in analysis.items)),
    ]
    for row, (label, value) in enumerate(summary_rows, start=1):
        summary.write(row, 0, label, fmt_text)
        if isinstance(value, (int, float)):
            summary.write_number(row, 1, float(value), fmt_num)
        else:
            summary.write(row, 1, value, fmt_text)
    summary.write(len(summary_rows)+2, 0, "Controleopmerking", fmt_sub)
    summary.merge_range(
        len(summary_rows)+3, 0, len(summary_rows)+5, 4,
        "Hoeveelheden zijn geometrisch bepaald uit de aangeleverde IFC/STEP-bestanden. "
        "Materiaalsterkte, dichtheid, radii, coatings, toleranties en aantallen moeten voor productie worden gecontroleerd "
        "tegen het bronmodel, de actuele norm, fabrikantgegevens en materiaalcertificaten.", fmt_note,
    )
    summary.set_column(0, 0, 32)
    summary.set_column(1, 1, 22)

    # Materialen: all material properties as explicitly requested.
    material_sheet = workbook.add_worksheet("Materialen")
    material_headers = [
        "Code", "Naam", "Categorie", "Dichtheid kg/m³", "E-modulus GPa", "Poisson", "Vloeigrens MPa",
        "Treksterkte MPa", "Uitzetting 10⁻⁶/K", "Warmtegeleiding W/mK", "Soortelijke warmte J/kgK",
        "Norm", "Aliassen", "Opmerkingen",
    ]
    for col, text in enumerate(material_headers):
        material_sheet.write(0, col, text, fmt_header)
    for row, item in enumerate(materials.materials, start=1):
        values = [
            item.code, item.name, item.category, item.density_kg_m3, item.elastic_modulus_gpa, item.poisson_ratio,
            item.yield_strength_mpa, item.tensile_strength_mpa, item.thermal_expansion_1e6_k,
            item.thermal_conductivity_w_mk, item.specific_heat_j_kg_k, item.standard, ", ".join(item.aliases), item.notes,
        ]
        for col, value in enumerate(values):
            material_sheet.write(row, col, value, fmt_num if isinstance(value, (int, float)) else fmt_text)
    material_sheet.freeze_panes(1, 0)
    material_sheet.autofilter(0, 0, max(len(materials.materials), 1), len(material_headers)-1)
    material_sheet.set_column(0, 2, 24)
    material_sheet.set_column(3, 10, 18)
    material_sheet.set_column(11, 13, 35)

    # Profiles catalogue.
    profile_sheet = workbook.add_worksheet("Profielen")
    profile_headers = [
        "Profiel", "Type", "Familie", "Maat 1", "Maat 2", "Maat 3", "Maat 4", "Radius",
        "Oppervlak mm²", "Massa kg/m", "Norm", "Status", "Bron", "Aliassen", "Notities", "Extra eigenschappen JSON",
    ]
    for col, text in enumerate(profile_headers):
        profile_sheet.write(0, col, text, fmt_header)
    for row, profile in enumerate(profiles.profiles, start=1):
        values = [
            profile.designation, profile.profile_type, profile.family, profile.dim1, profile.dim2, profile.dim3,
            profile.dim4, profile.radius, profile.area_mm2, profile.mass_kg_m, profile.standard,
            profile.catalogue_status, profile.source, ", ".join(profile.aliases), profile.notes,
            json.dumps(profile.properties, ensure_ascii=False),
        ]
        for col, value in enumerate(values):
            profile_sheet.write(row, col, value, fmt_num if isinstance(value, (int, float)) else fmt_text)
    profile_sheet.freeze_panes(1, 0)
    profile_sheet.autofilter(0, 0, max(len(profiles.profiles), 1), len(profile_headers)-1)
    profile_sheet.set_column(0, 2, 18)
    profile_sheet.set_column(3, 9, 13)
    profile_sheet.set_column(10, 15, 34)

    # Flatten all source properties into a long list.
    prop_sheet = workbook.add_worksheet("Eigenschappen")
    prop_headers = ["Bronbestand", "Item", "Naam", "GUID", "Eigenschapspad", "Waarde"]
    for col, text in enumerate(prop_headers):
        prop_sheet.write(0, col, text, fmt_header)
    out_row = 1
    for item in analysis.items:
        flat: dict[str, Any] = {}
        _flatten("", item.properties, flat)
        for key, value in flat.items():
            prop_sheet.write_row(out_row, 0, [item.source_file, item.item_id, item.name, item.guid, key, str(value)], fmt_text)
            out_row += 1
    prop_sheet.freeze_panes(1, 0)
    prop_sheet.autofilter(0, 0, max(out_row-1, 1), len(prop_headers)-1)
    prop_sheet.set_column(0, 3, 28)
    prop_sheet.set_column(4, 4, 52)
    prop_sheet.set_column(5, 5, 60)

    # Warnings log.
    warning_sheet = workbook.add_worksheet("Waarschuwingen")
    warning_sheet.write(0, 0, "Nr.", fmt_header)
    warning_sheet.write(0, 1, "Melding", fmt_header)
    all_warnings = list(analysis.warnings)
    for item in analysis.items:
        all_warnings.extend(f"{item.source_file} / {item.name}: {w}" for w in item.warnings)
    for row, warning in enumerate(all_warnings, start=1):
        warning_sheet.write_number(row, 0, row, fmt_int)
        warning_sheet.write(row, 1, warning, fmt_warn)
    warning_sheet.set_column(0, 0, 8)
    warning_sheet.set_column(1, 1, 120)

    workbook.close()
    return target
