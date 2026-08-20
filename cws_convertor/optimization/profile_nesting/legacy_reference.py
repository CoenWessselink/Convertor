"""Illustrative machine data transcribed from supplied legacy screenshots.

These values are UX/domain references only and MUST remain blocked for
production until owner validation supplies the real machine specification.
"""
from __future__ import annotations
from .models import MachineOptimizationProfile, ToolDefinition


def illustrative_legacy_v623_reference() -> tuple[MachineOptimizationProfile, list[ToolDefinition]]:
    tools = [
        ToolDefinition(tool_id=f"legacy-v623-drill-{d:g}", tool_type="drill", material="HSS", diameter_mm=d,
                       allowed_machine_ids=["LEGACY-V623-REFERENCE"], status="active", maintenance_status="ok")
        for d in (6.8, 8.5, 10.5, 12, 14, 16, 17.5, 18, 20, 21, 22, 24, 26, 28, 32, 34, 38, 40, 11, 8, 33, 30)
    ]
    for tool in tools: tool.refresh_hash()
    profile = MachineOptimizationProfile(
        profile_id="legacy-screenshot-v623-reference-v1",
        machine_id="LEGACY-V623-REFERENCE",
        machine_group="screenshot_reference",
        revision="1",
        enabled=True,
        validation_status="manual_validation_required",
        supported_profile_types=["i", "u", "l", "t", "c", "box", "tube", "round", "flat"],
        supported_materials=["S235JR"],
        supported_operations=["saw", "drill"],
        supported_sides=["front", "bottom", "top", "back"],
        kerf_mm=2.7,
        head_trim_mm=30.0,
        min_saw_angle_deg=-60.0,
        max_saw_angle_deg=45.0,
        max_dimensions_mm={"width": 1250.0},
        clamp_width_left_mm=300.0,
        clamp_width_right_mm=300.0,
        safety_length_mm=30.0,
        max_hole_diameter_mm=40.0,
        tool_ids=[t.tool_id for t in tools],
        provenance={
            "source": "user_supplied_legacy_screenshots_2026-08-14",
            "status": "manual_validation_required",
            "warning": "Illustrative only; not a validated V623/VB1250/V550 machine specification.",
        },
    )
    profile.refresh_hash(tool_hashes={t.tool_id: t.configuration_hash for t in tools})
    return profile, tools
