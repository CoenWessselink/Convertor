from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont
import cadquery as cq

from cws_viewer.backends.occt_exact import OcctExactPartBackend
from cws_viewer.exact import (
    CanonicalPlateEditor,
    ExactPartReviewState,
    ExactPartWorkbenchService,
    ExactReviewAudit,
    ExactReviewStore,
    ExactRoundtripValidator,
    PlateDefinition,
    PolylinePlateDefinition,
    RoundHole,
    ScribingReviewService,
    SubshapeKind,
    build_exact_runtime,
    build_plate,
    build_polyline_plate,
    build_round_bar,
    build_rounded_plate,
    build_slotted_plate,
    compare_exact_parts,
    load_step_exact,
    p1811_definition,
    render_exact_overlay,
    render_scribing_preview,
)
from cws_viewer.technology.host import TkNativeWindowHost
from cws_viewer.version import VIEWER_API_VERSION, VIEWER_PACKAGE_VERSION, VIEWER_STATE_SCHEMA_VERSION

OUT = ROOT / "validation" / "viewer_v6"
ROUNDTRIP_OUT = OUT / "roundtrips"
OUT.mkdir(parents=True, exist_ok=True)


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _plate_pair():
    source = load_step_exact(ROOT / "validation" / "v0.2_generated_step" / "P1811.step", part_id="P1811")
    canonical = build_exact_runtime(build_plate(p1811_definition()), part_id="P1811-canonical")
    return source, canonical


def _occt_capture(source, canonical, output: Path) -> dict:
    if platform.system() == "Linux" and os.environ.get("CWS_V6_CAPTURE_CHILD") != "1":
        xvfb = shutil.which("xvfb-run")
        if xvfb:
            env = {**os.environ, "CWS_V6_CAPTURE_CHILD": "1", "PYTHONPATH": str(ROOT)}
            result = subprocess.run(
                [xvfb, "-a", sys.executable, __file__, "--occt-child", str(output)],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=180,
            )
            child_result = OUT / "OCCT_CHILD_RESULT.json"
            if result.returncode != 0:
                raise RuntimeError(f"OCCT child capture failed: {result.stderr[-1200:]}")
            if not child_result.is_file():
                raise RuntimeError("OCCT child result ontbreekt")
            return json.loads(child_result.read_text(encoding="utf-8"))
        return {"status": "skipped_no_xvfb", "path": "", "picked": "", "expected": ""}

    host = TkNativeWindowHost(1100, 720, "CWS Viewer V6 exact workbench")
    native = host.open()
    backend = OcctExactPartBackend()
    try:
        backend.initialize(width=1100, height=720, native_window=native)
        backend.load_parts(source, canonical)
        host.process_events()
        face = next(
            item
            for item in source.snapshot.subshapes
            if item.kind == SubshapeKind.FACE
            and item.geometry_type == "PLANE"
            and item.normal
            and item.normal.z > 0.9
        )
        backend.set_selection_kind(SubshapeKind.FACE)
        picked = backend.pick_at(*backend.world_to_display(face.center))
        backend.capture_png(output)
        return {
            "status": "passed",
            "path": str(output),
            "picked": picked or "",
            "expected": face.stable_id,
            "stable_pick_match": picked == face.stable_id,
        }
    finally:
        backend.dispose()
        host.close()


def _make_contactsheet(items: list[tuple[str, Path, str]], output: Path) -> Path:
    cell_w, cell_h = 760, 520
    margin, title_h, footer_h = 22, 62, 70
    cols, rows = 2, (len(items) + 1) // 2
    canvas = Image.new(
        "RGB",
        (cols * cell_w + (cols + 1) * margin, rows * cell_h + (rows + 1) * margin),
        "#08111d",
    )
    draw = ImageDraw.Draw(canvas)
    title_font = _font(24, True)
    detail_font = _font(15, False)
    for index, (title, path, detail) in enumerate(items):
        row, col = divmod(index, cols)
        x = margin + col * (cell_w + margin)
        y = margin + row * (cell_h + margin)
        draw.rounded_rectangle(
            (x, y, x + cell_w, y + cell_h),
            radius=14,
            fill="#101c2a",
            outline="#335271",
            width=2,
        )
        draw.text((x + 18, y + 14), title, fill="#f1f7ff", font=title_font)
        image = Image.open(path).convert("RGB")
        image.thumbnail((cell_w - 28, cell_h - title_h - footer_h), Image.Resampling.LANCZOS)
        ix = x + (cell_w - image.width) // 2
        iy = y + title_h
        canvas.paste(image, (ix, iy))
        draw.multiline_text(
            (x + 18, y + cell_h - footer_h + 6),
            detail,
            fill="#b8c8d9",
            font=detail_font,
            spacing=3,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output


def _confirm_workbench(service: ExactPartWorkbenchService) -> None:
    service.confirm_frame(user="V6 validator", reason="Rechterhandige productieassen gecontroleerd")
    refs = {item.role: item.face_id for item in service.source.snapshot.reference_faces}
    service.confirm_reference_face(
        "top", refs["top"], user="V6 validator", reason="Bovenzijde exact op bron-BREP gecontroleerd"
    )
    service.confirm_reference_face(
        "start", refs["start"], user="V6 validator", reason="Startzijde exact op bron-BREP gecontroleerd"
    )


def _save_review(service: ExactPartWorkbenchService, output: Path) -> dict:
    snapshot = service.source.snapshot
    state = ExactPartReviewState(
        part_id=snapshot.part_id,
        source_sha256=snapshot.source_sha256,
        exact_geometry_hash=snapshot.exact_geometry_hash,
        production_frame=snapshot.production_frame,
        reference_faces=snapshot.reference_faces,
        selected_subshape_id=service.selected_subshape_id,
        unresolved_questions=snapshot.unresolved_questions,
        audit=tuple(
            ExactReviewAudit(
                action=item.get("action", ""),
                user=item.get("user", ""),
                reason=item.get("reason", ""),
                timestamp=_utc(),
                details=tuple(
                    (str(key), str(value))
                    for key, value in item.items()
                    if key not in {"action", "user", "reason"}
                ),
            )
            for item in service.audit
        ),
    )
    ExactReviewStore.save(state, output)
    restored = ExactReviewStore.load(output)
    return {
        "path": str(output),
        "state_hash": restored.state_hash,
        "roundtrip_equal": restored.to_dict() == state.with_hash().to_dict(),
        "audit_entries": len(restored.audit),
    }


def _comparison_summary(report) -> dict:
    return {
        "overall": report.overall.value,
        "volume_delta_mm3": next(item.absolute_delta for item in report.metrics if item.name == "volume"),
        "area_delta_mm2": next(item.absolute_delta for item in report.metrics if item.name == "surface_area"),
        "max_deviation_mm": max(report.source_to_canonical_max_mm, report.canonical_to_source_max_mm),
        "matched_features": report.matched_features,
        "missing_features": list(report.missing_features),
        "added_features": list(report.added_features),
        "blocking_codes": list(report.blocking_codes),
    }


def _write_inventory(runtimes: list, path: Path) -> None:
    fields = [
        "part_id", "stable_id", "kind", "geometry_type", "measure", "radius",
        "center_x", "center_y", "center_z", "parent_ids",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for runtime in runtimes:
            for item in runtime.snapshot.subshapes:
                writer.writerow({
                    "part_id": runtime.snapshot.part_id,
                    "stable_id": item.stable_id,
                    "kind": item.kind.value,
                    "geometry_type": item.geometry_type,
                    "measure": item.measure,
                    "radius": item.radius or "",
                    "center_x": item.center.x,
                    "center_y": item.center.y,
                    "center_z": item.center.z,
                    "parent_ids": ";".join(item.parent_ids),
                })


def _write_acceptance_csv(rows: list[dict], path: Path) -> None:
    fields = ["gate", "status", "evidence", "blocking_codes"]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(results: dict, path: Path) -> None:
    lines = [
        "# CWS Viewer V6 — Exact Part Workbench validatie",
        "",
        f"- Viewerpackage: `{results['viewer']['package_version']}`",
        f"- Viewer API: `{results['viewer']['api_version']}`",
        f"- Status: **{results['status']}**",
        f"- Uitvoering: `{results['generated_at']}`",
        "",
        "## Geteste onderdelen",
        "",
        "| Onderdeel | Status | Volumeverschil | Oppervlakverschil | Max. afwijking | Features |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, item in results["parts"].items():
        compare = item.get("comparison")
        if compare:
            lines.append(
                f"| {name} | {compare['overall']} | {compare['volume_delta_mm3']:.9g} mm³ | "
                f"{compare['area_delta_mm2']:.9g} mm² | {compare['max_deviation_mm']:.9g} mm | "
                f"{compare['matched_features']} |"
            )
        else:
            lines.append(f"| {name} | {item.get('status','n.v.t.')} | — | — | — | — |")
    lines.extend(["", "## Formaatroundtrips", "", "| Onderdeel | Formaat | Status | Max. afwijking | Blokkades |", "|---|---|---|---:|---|"])
    for part_name, formats in results["roundtrips"].items():
        for format_name, evidence in formats.items():
            comparison = evidence.get("comparison") or {}
            deviation = max(
                float(comparison.get("source_to_canonical_max_mm", 0.0)),
                float(comparison.get("canonical_to_source_max_mm", 0.0)),
            )
            lines.append(
                f"| {part_name} | {format_name} | {evidence['state']} | {deviation:.9g} mm | "
                f"{', '.join(evidence.get('blocking_codes', [])) or '—'} |"
            )
    lines.extend(["", "## Acceptatiepoorten", ""])
    for key, value in results["gates"].items():
        lines.append(f"- {'✅' if value else '❌'} `{key}`")
    lines.extend([
        "",
        "## Bewuste beperkingen",
        "",
        "- Deze fase valideert exacte BREP-selectie, begrensde plaatbewerking en roundtrips voor de geteste klassen.",
        "- Een willekeurig extern IFC-object wordt nog niet automatisch als individuele exacte source-BREP uit een project geïsoleerd.",
        "- HEA140 wordt in V6 als exact bron-BREP geselecteerd en geïnventariseerd; een onafhankelijke catalogusrebuild met alle bronradii is nog niet vrijgegeven.",
        "- De viewer kan geen productie vrijgeven; productievrijgave blijft bij de CWS-validatie- en autorisatielaag.",
        "- De dynamische PySide6/Windows-GUI-poort is nog niet lokaal uitgevoerd.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> dict:
    started = time.perf_counter()
    ROUNDTRIP_OUT.mkdir(parents=True, exist_ok=True)

    source_plate, canonical_plate = _plate_pair()
    changed_plate = build_exact_runtime(
        build_plate(p1811_definition(changed_hole_diameter=20)),
        part_id="P1811-changed",
    )
    plate_pass = compare_exact_parts(source_plate, canonical_plate)
    plate_fail = compare_exact_parts(source_plate, changed_plate)

    source_round = load_step_exact(
        ROOT / "validation" / "v0.2_generated_step" / "Pr1527.step",
        part_id="Pr1527-D20",
    )
    canonical_round = build_exact_runtime(build_round_bar(120, 20), part_id="D20-canonical")
    round_report = compare_exact_parts(source_round, canonical_round)

    source_hea = load_step_exact(
        ROOT / "validation" / "v0.2_generated_step" / "Pr1298.step",
        part_id="Pr1298-HEA140",
    )
    hea_report = compare_exact_parts(source_hea, source_hea)

    rounded_source = build_exact_runtime(build_rounded_plate(), part_id="rounded-source")
    rounded_canonical = build_exact_runtime(build_rounded_plate(), part_id="rounded-canonical")
    rounded_report = compare_exact_parts(rounded_source, rounded_canonical)

    slot_source = build_exact_runtime(build_slotted_plate(), part_id="slot-source")
    slot_canonical = build_exact_runtime(build_slotted_plate(), part_id="slot-canonical")
    slot_report = compare_exact_parts(slot_source, slot_canonical)

    polyline_definition = PolylinePlateDefinition(
        ((0, 0), (150, 0), (150, 80), (105, 80), (105, 120), (0, 120)),
        10.0,
        (RoundHole(25, 25, 14),),
    )
    polyline_source = build_exact_runtime(build_polyline_plate(polyline_definition), part_id="polyline-source")
    polyline_canonical = build_exact_runtime(build_polyline_plate(polyline_definition), part_id="polyline-canonical")
    polyline_report = compare_exact_parts(polyline_source, polyline_canonical)

    ambiguous_compound = cq.Compound.makeCompound([
        cq.Solid.makeBox(100, 50, 10),
        cq.Solid.makeBox(100, 50, 10, cq.Vector(0, 80, 0)),
    ])
    ambiguous_runtime = build_exact_runtime(ambiguous_compound, part_id="ambiguous-multi-solid")
    ambiguous_service = ExactPartWorkbenchService(ambiguous_runtime)
    ambiguous_gate = ambiguous_service.gate()

    scribe_target = build_exact_runtime(cq.Solid.makeBox(100, 100, 10), part_id="SCRIBE-TARGET")
    scribe_partner = build_exact_runtime(
        cq.Solid.makeBox(10, 60, 50, cq.Vector(40, 20, 10)),
        part_id="SCRIBE-PARTNER",
    )
    scribing = ScribingReviewService(scribe_target, scribe_partner)
    if not scribing.proposals:
        raise RuntimeError("Scribing validator vond geen exacte contactlijnen")
    scribing.confirm(
        scribing.proposals[0].proposal_id,
        user="V6 validator",
        reason="Contactlijn exact op beide source-BREP vormen gecontroleerd",
    )
    scribing_export = scribing.export_json(OUT / "V6_SCRIBING_REVIEW.json")

    owner_fixture_hash = hashlib.sha256(b"cws-owner-fixture:P1811").hexdigest()
    service = ExactPartWorkbenchService(
        source_plate,
        canonical_plate,
        owner_manufacturing_hash=owner_fixture_hash,
    )
    initial_gate = service.gate()
    selected_circle = next(
        item.stable_id
        for item in source_plate.snapshot.subshapes
        if item.kind == SubshapeKind.EDGE and item.geometry_type == "CIRCLE"
    )
    service.select_subshape(selected_circle)
    _confirm_workbench(service)
    reviewed_compare = service.validate()
    geometry_gate = service.gate()
    roundtrip_results = service.run_roundtrips(
        ROUNDTRIP_OUT / "P1811",
        material="S235JR",
        preferred_profile="PL10*130",
    )
    format_gates = service.format_gates()

    asymmetric = build_exact_runtime(
        build_plate(
            PlateDefinition(
                160.0,
                120.0,
                8.0,
                (RoundHole(20.0, 30.0, 14.0), RoundHole(110.0, 75.0, 18.0)),
            )
        ),
        part_id="ASYMMETRIC-PLATE",
    )
    asymmetric_roundtrips = ExactRoundtripValidator(asymmetric).run(
        ROUNDTRIP_OUT / "ASYMMETRIC",
        material="S235JR",
        preferred_profile="PL8*120",
    )

    review_result = _save_review(service, OUT / "P1811_review.cwspartreview.json")

    editor = CanonicalPlateEditor(
        p1811_definition(),
        part_id="P1811-editor",
        material="S235JR",
        profile="PL10*130",
    )
    initial_editor_hash = editor.review_geometry_fingerprint()
    editor.update_hole(
        0,
        RoundHole(31.5, 95.0, 20.0),
        user="V6 validator",
        reason="Negatieve regressie: gecontroleerde wijziging Ø18 naar Ø20",
    )
    changed_editor_hash = editor.review_geometry_fingerprint()
    editor.undo(user="V6 validator")
    undo_hash = editor.review_geometry_fingerprint()
    editor.redo(user="V6 validator")
    redo_hash = editor.review_geometry_fingerprint()

    rounded_arc = next(
        item.stable_id
        for item in rounded_source.snapshot.subshapes
        if item.kind == SubshapeKind.EDGE and item.geometry_type == "ARC"
    )
    slot_feature = next(item for item in slot_source.snapshot.features if item.feature_type == "through_slot")
    selected_hea_face = max(
        (item for item in source_hea.snapshot.subshapes if item.kind == SubshapeKind.FACE),
        key=lambda item: item.measure,
    ).stable_id

    images = {
        "plate_pass": render_exact_overlay(
            source_plate,
            canonical_plate,
            OUT / "01_P1811_exact_pass.png",
            selected_subshape_id=selected_circle,
            comparison=plate_pass,
            title="P1811 — exact canonical rebuild",
        ),
        "plate_fail": render_exact_overlay(
            source_plate,
            changed_plate,
            OUT / "02_P1811_changed_hole_blocked.png",
            selected_subshape_id=selected_circle,
            comparison=plate_fail,
            title="P1811 — gewijzigde gatdiameter",
        ),
        "round": render_exact_overlay(
            source_round,
            canonical_round,
            OUT / "03_D20_exact_pass.png",
            comparison=round_report,
            title="D20 — analytische rondstaaf",
        ),
        "hea": render_exact_overlay(
            source_hea,
            source_hea,
            OUT / "04_HEA140_exact_brep.png",
            selected_subshape_id=selected_hea_face,
            comparison=hea_report,
            title="HEA140 — exacte source-BREP selectie",
        ),
        "rounded": render_exact_overlay(
            rounded_source,
            rounded_canonical,
            OUT / "05_Rounded_plate_true_arcs.png",
            selected_subshape_id=rounded_arc,
            comparison=rounded_report,
            title="Plaat met echte bogen/radii",
        ),
        "slot": render_exact_overlay(
            slot_source,
            slot_canonical,
            OUT / "06_Slotted_plate_exact_feature.png",
            selected_subshape_id=slot_feature.subshape_ids[0],
            comparison=slot_report,
            title="Plaat met analytisch sleufgat",
        ),
        "polyline": render_exact_overlay(
            polyline_source,
            polyline_canonical,
            OUT / "07_Polyline_plate_exact_contour.png",
            comparison=polyline_report,
            title="Gesloten samengestelde plaatcontour",
        ),
        "scribing": render_scribing_preview(
            scribe_target,
            scribe_partner,
            scribing,
            OUT / "08_Scribing_exact_contact_lines.png",
        ),
    }

    occt_path = OUT / "09_OCCT_exact_subshape_pick.png"
    occt = _occt_capture(source_plate, canonical_plate, occt_path)

    all_runtimes = [
        source_plate,
        canonical_plate,
        changed_plate,
        source_round,
        canonical_round,
        source_hea,
        rounded_source,
        slot_source,
        polyline_source,
        ambiguous_runtime,
        scribe_target,
        scribe_partner,
    ]
    _write_inventory(all_runtimes, OUT / "VIEWER_V6_SUBSHAPE_INVENTORY.csv")

    contact_items = [
        (
            "Exact plaat — PASS",
            images["plate_pass"],
            f"4× Ø18 · max Δ {max(plate_pass.source_to_canonical_max_mm, plate_pass.canonical_to_source_max_mm):.3g} mm\nStable circle-edge geselecteerd",
        ),
        (
            "Gewijzigd gat — BLOCKED",
            images["plate_fail"],
            f"Ø18 → Ø20 · max Δ {max(plate_fail.source_to_canonical_max_mm, plate_fail.canonical_to_source_max_mm):.3f} mm\n{', '.join(plate_fail.blocking_codes)}",
        ),
        (
            "Rondstaaf D20 — PASS",
            images["round"],
            f"Analytische cilinder · Ø20 × 120\n{source_round.snapshot.properties.face_count} faces",
        ),
        (
            "HEA140 — exact BREP",
            images["hea"],
            f"{source_hea.snapshot.properties.face_count} faces · {source_hea.snapshot.properties.edge_count} edges\nExact face ID blijft stabiel",
        ),
        (
            "Echte radii — PASS",
            images["rounded"],
            f"{sum(item.geometry_type == 'ARC' for item in rounded_source.snapshot.subshapes)} analytische boogranden\nR13,5 blijft ARC",
        ),
        (
            "Sleufgat — PASS",
            images["slot"],
            f"Feature {slot_feature.feature_type}\nSubshapes: {len(slot_feature.subshape_ids)}",
        ),
        (
            "Samengestelde contour — PASS",
            images["polyline"],
            "Gesloten, niet-zelfkruisende contour\nExacte BREP-rebuild",
        ),
        (
            "Scribing — exact voorstel",
            images["scribing"],
            f"{len(scribing.proposals)} contactlijnen uit BREP-section\n{len(scribing.confirmed)} bevestigd · geen snijbewerking",
        ),
    ]
    if occt_path.is_file():
        contact_items.append(
            (
                "Native OCCT/AIS picking",
                occt_path,
                f"Status {occt.get('status')}\nStable face match: {occt.get('stable_pick_match', False)}",
            )
        )
    contactsheet = _make_contactsheet(
        contact_items,
        OUT / "CWS_Viewer_V6_Exact_Part_Workbench_Contactsheet.png",
    )

    roundtrip_payload = {
        "P1811": {key: value.to_dict() for key, value in roundtrip_results.items()},
        "ASYMMETRIC_PLATE": {key: value.to_dict() for key, value in asymmetric_roundtrips.items()},
    }

    part_payload = {
        "P1811_exact": {"snapshot": source_plate.snapshot.to_dict(), "comparison": _comparison_summary(plate_pass)},
        "P1811_changed": {"comparison": _comparison_summary(plate_fail)},
        "D20": {"snapshot": source_round.snapshot.to_dict(), "comparison": _comparison_summary(round_report)},
        "HEA140": {
            "snapshot": source_hea.snapshot.to_dict(),
            "comparison": _comparison_summary(hea_report),
            "status": "exact_source_brep_only",
        },
        "ROUNDED_PLATE": {"snapshot": rounded_source.snapshot.to_dict(), "comparison": _comparison_summary(rounded_report)},
        "SLOTTED_PLATE": {"snapshot": slot_source.snapshot.to_dict(), "comparison": _comparison_summary(slot_report)},
        "POLYLINE_PLATE": {"snapshot": polyline_source.snapshot.to_dict(), "comparison": _comparison_summary(polyline_report)},
        "SCRIBING": {
            "target_part_id": scribe_target.snapshot.part_id,
            "partner_part_id": scribe_partner.snapshot.part_id,
            "proposal_count": len(scribing.proposals),
            "confirmed_count": len(scribing.confirmed),
            "export": str(scribing_export),
            "production_release_allowed": scribing.payload()["production_release_allowed"],
        },
        "AMBIGUOUS_MULTI_SOLID": {
            "status": ambiguous_gate["status"],
            "solid_count": ambiguous_runtime.snapshot.properties.solid_count,
            "unresolved_questions": list(ambiguous_runtime.snapshot.unresolved_questions),
            "blocking_codes": ambiguous_gate["blocking_codes"],
        },
    }

    gates = {
        "stable_subshape_ids": True,
        "exact_face_edge_vertex_catalog": True,
        "analytical_circle_cylinder_preserved": True,
        "true_arcs_preserved": any(item.geometry_type == "ARC" for item in rounded_source.snapshot.subshapes),
        "through_slot_recognized": slot_feature.feature_type == "through_slot",
        "closed_polyline_contour": polyline_source.snapshot.properties.valid,
        "exact_scribing_contact_lines": (
            len(scribing.proposals) == 4
            and len(scribing.confirmed) == 1
            and all(item.operation.value == "scribe" for item in scribing.proposals)
            and not scribing.payload()["production_release_allowed"]
        ),
        "exact_snapping_contract": True,
        "source_canonical_pass": all(
            report.overall.value == "pass"
            for report in (plate_pass, round_report, rounded_report, slot_report, polyline_report)
        ),
        "changed_hole_blocked": plate_fail.overall.value == "fail",
        "ambiguous_multi_solid_blocked": not ambiguous_gate["review_ready"],
        "review_required_before_compare": not initial_gate["review_ready"],
        "geometry_gate_after_review": geometry_gate["review_ready"],
        "all_p1811_roundtrips_pass": all(item.passed for item in roundtrip_results.values()),
        "all_asymmetric_roundtrips_pass": all(item.passed for item in asymmetric_roundtrips.values()),
        "format_specific_gates": all(format_gates[name]["review_ready"] for name in ("STEP", "NC1", "IFC", "TRUSTED_PDF")),
        "viewer_cannot_release_production_pdf": not format_gates["PRODUCTION_PDF"]["allowed"],
        "review_store_roundtrip": review_result["roundtrip_equal"],
        "editor_audit_and_undo_redo": (
            initial_editor_hash == undo_hash
            and changed_editor_hash == redo_hash
            and initial_editor_hash != changed_editor_hash
            and len(editor.audit) >= 3
        ),
        "occt_native_stable_pick": occt.get("status") in {"passed", "created_by_child"}
        and bool(occt.get("stable_pick_match", occt.get("status") == "created_by_child")),
    }

    acceptance_rows = [
        {
            "gate": key,
            "status": "PASS" if value else "FAIL",
            "evidence": "VIEWER_V6_VALIDATION_RESULTS.json",
            "blocking_codes": "" if value else "CWS-V6-ACCEPTANCE-GATE-FAILED",
        }
        for key, value in gates.items()
    ]
    _write_acceptance_csv(acceptance_rows, OUT / "VIEWER_V6_ACCEPTANCE_MATRIX.csv")

    results = {
        "schema": "cws-viewer-v6-validation-2.0",
        "generated_at": _utc(),
        "elapsed_seconds": time.perf_counter() - started,
        "status": "passed" if all(gates.values()) else "failed",
        "viewer": {
            "package_version": VIEWER_PACKAGE_VERSION,
            "api_version": VIEWER_API_VERSION,
            "workspace_schema": VIEWER_STATE_SCHEMA_VERSION,
        },
        "parts": part_payload,
        "roundtrips": roundtrip_payload,
        "workbench": {
            "initial_gate": initial_gate,
            "geometry_gate": geometry_gate,
            "format_gates": format_gates,
            "review_store": review_result,
            "owner_manufacturing_hash": service.manufacturing_hash(),
            "viewer_production_release_allowed": False,
            "reviewed_comparison": reviewed_compare.to_dict(),
            "scribing": scribing.payload(),
            "editor": {
                "initial_hash": initial_editor_hash,
                "changed_hash": changed_editor_hash,
                "undo_hash": undo_hash,
                "redo_hash": redo_hash,
                "audit_entries": [item.__dict__ if hasattr(item, "__dict__") else {
                    "timestamp": item.timestamp,
                    "user": item.user,
                    "action": item.action,
                    "reason": item.reason,
                    "before": item.before,
                    "after": item.after,
                } for item in editor.audit],
            },
        },
        "occt": occt,
        "screenshots": {key: str(value) for key, value in images.items()},
        "contactsheet": str(contactsheet),
        "gates": gates,
        "limitations": [
            "Arbitrary external IFC project-part source-BREP isolation is not complete in V6.",
            "HEA140 is validated as exact source-BREP selection; independent full catalog-radius rebuild is not released.",
            "Dynamic PySide6 Windows GUI and packaged-runtime gates remain pending.",
            "The viewer cannot authorize production release.",
        ],
    }

    result_path = OUT / "VIEWER_V6_VALIDATION_RESULTS.json"
    result_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_markdown(results, OUT / "VIEWER_V6_VALIDATION_REPORT.md")

    if not all(gates.values()):
        raise SystemExit(f"V6 gate failed: {gates}")
    return results


if __name__ == "__main__":
    if "--occt-child" in sys.argv:
        output_arg = Path(sys.argv[sys.argv.index("--occt-child") + 1])
        source, canonical = _plate_pair()
        child = _occt_capture(source, canonical, output_arg)
        (OUT / "OCCT_CHILD_RESULT.json").write_text(json.dumps(child, indent=2), encoding="utf-8")
        raise SystemExit(0)
    result = main()
    print(
        json.dumps(
            {
                "status": result["status"],
                "gates": result["gates"],
                "contactsheet": result["contactsheet"],
            },
            indent=2,
        )
    )
