from __future__ import annotations

from pathlib import Path

from cws_convertor.manufacturing.machine_settings import (
    add_plate_stock,
    add_profile_stock,
    add_remnant,
    apply_machine_settings,
    parse_construsteel_machine_xml,
    return_remnant_to_stock,
    set_trade_lengths,
)
from cws_convertor.project.model import ProjectModel


MACHINE_XML = Path(r"C:\Users\c.wesselink\Desktop\VB1250 Zaag - V631 Boor.xml")


def test_vendor_machine_stock_plate_and_remnant_roundtrip(tmp_path: Path) -> None:
    project = ProjectModel.new("manufacturing-completion", created_by="test")
    imported = parse_construsteel_machine_xml(MACHINE_XML)
    profile_id = apply_machine_settings(project, imported, user="test")
    assert imported.name == "VB1250 Zaag - V631 Boor"
    assert imported.parameters["SAWBLADETHICKNESS"] == 2.7
    assert imported.parameters["MIN_ANGLE"] == -60.0
    assert imported.parameters["MAX_ANGLE"] == 45.0
    assert profile_id in project.profile_nesting_machine_profiles
    machine = project.profile_nesting_machine_profiles[profile_id]
    assert machine["common_cut_policy"] == "supported"
    assert {"i_profile", "l_profile", "u_profile"}.issubset(set(machine["supported_profile_types"]))

    trade_ids = set_trade_lengths(project, "HEA200", "STEEL", "S355JR", (6000, 12000, 15000), user="test")
    stock_id = add_profile_stock(project, "HEA200", "STEEL", "S355JR", 12000, 4, user="test")
    plate_id = add_plate_stock(project, "STEEL", "S355JR", 10, 2000, 6000, 3, user="test")
    remnant_id = add_remnant(project, "HEA200", "STEEL", "S355JR", 1650, stock_item_id=stock_id, user="test")
    project.remnants[remnant_id].status = "reserved"
    return_remnant_to_stock(project, remnant_id, user="test")
    assert len(trade_ids) == 3
    assert project.stock_items[stock_id].stock_length_mm == 12000
    assert project.stock_items[plate_id].plate_size_mm == [2000.0, 6000.0, 10.0]
    assert project.remnants[remnant_id].status == "available"
    project.validate()
