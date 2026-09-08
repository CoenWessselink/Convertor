"""Exact profile index equivalence, decimal safety and snapshot invalidation."""
from __future__ import annotations

from pathlib import Path
import re
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cws_convertor.project import classification as target
from profile_database import ProfileDefinition


def row(designation: str, *aliases: str) -> ProfileDefinition:
    return ProfileDefinition(designation, "I", "fixture", 200, 100, aliases=list(aliases))


class ProfileCatalogLookupSmoke(unittest.TestCase):
    def test_all_literal_catalogue_names_and_aliases_keep_legacy_results(self) -> None:
        rows = target._profile_catalog().profiles
        legacy = [(item.designation, item.search_names) for item in rows]
        queries = sorted({name for item in rows for name in (item.designation, *item.aliases)})
        self.assertGreater(len(queries), 2800)
        for query in queries:
            keys = {re.sub(r"[^A-Z0-9]", "", value.upper()) for value in target._profile_lookup_candidates(query) if value}
            matches = {designation for designation, names in legacy if keys.intersection(names)}
            before = next(iter(matches)) if len(matches) == 1 else ""
            self.assertEqual(target._catalog_profile(query), before, query)

    def test_decimal_points_are_not_erased_into_a_different_wall_thickness(self) -> None:
        for query, expected in (
            ("SHS20x20x1.5", "SHS20x20x1.5"),
            ("SHS20x20x1,5", "SHS20x20x1.5"),
            ("SHS20x20x15", ""),
            ("RHS40x20x15", ""),
            ("CHS269x23", ""),
            ("CHS26.9x2.3", "CHS26.9x2.3"),
            ("SHS20x20x1-5", ""),
        ):
            with self.subTest(query=query):
                self.assertEqual(target._catalog_profile(query), expected)

    def test_decimal_and_integer_dimensions_can_be_distinct_catalogue_rows(self) -> None:
        catalogue = SimpleNamespace(profiles=[row("SHS20x20x1.5"), row("SHS20x20x15")])
        with patch.object(target, "_profile_catalog", return_value=catalogue):
            self.assertEqual(target._catalog_profile("SHS20x20x1.5"), "SHS20x20x1.5")
            self.assertEqual(target._catalog_profile("SHS20x20x15"), "SHS20x20x15")

    def test_supported_display_and_workshop_aliases_remain_exact(self) -> None:
        for query, expected in (
            ("HEA 200", "HEA200"), ("HEA-200", "HEA200"),
            ("UNP160", "UPN160"), ("UNP-160", "UPN160"),
            ("STRIP10*100", "FLAT100x10"), ("STRIP10×100", "FLAT100x10"),
            ("SHS20*20*1.5", "SHS20x20x1.5"),
        ):
            with self.subTest(query=query):
                self.assertEqual(target._catalog_profile(query), expected)
        catalogue = SimpleNamespace(profiles=[row("SHS60x60x3"), row("L60x60x6"), row("ROUND20")])
        with patch.object(target, "_profile_catalog", return_value=catalogue):
            self.assertEqual(target._catalog_profile("K60/3"), "SHS60x60x3")
            self.assertEqual(target._catalog_profile("L60/6"), "L60x60x6")
            self.assertEqual(target._catalog_profile("Ø20"), "ROUND20")

    def test_every_candidate_and_alias_conflict_remains_unresolved(self) -> None:
        catalogue = SimpleNamespace(profiles=[row("K60/3"), row("SHS60x60x3")])
        with patch.object(target, "_profile_catalog", return_value=catalogue):
            self.assertEqual(target._catalog_profile("K60/3"), "")
            catalogue.profiles = [row("HEA200", "SPECIAL"), row("HEA220", "SPECIAL")]
            self.assertEqual(target._catalog_profile("SPECIAL"), "")
            catalogue.profiles = [row("HEA200", "SPECIAL"), row("HEA200", "SPECIAL")]
            self.assertEqual(target._catalog_profile("SPECIAL"), "HEA200")

    def test_snapshot_detects_direct_mutation_append_and_reload(self) -> None:
        catalogue = SimpleNamespace(profiles=[row("HEA200", "SPECIAL")])
        with patch.object(target, "_profile_catalog", return_value=catalogue):
            self.assertEqual(target._catalog_profile("SPECIAL"), "HEA200")
            catalogue.profiles.append(row("HEA220", "SPECIAL"))
            self.assertEqual(target._catalog_profile("SPECIAL"), "")
            catalogue.profiles[1].aliases[:] = ["NEW"]
            self.assertEqual(target._catalog_profile("SPECIAL"), "HEA200")
            self.assertEqual(target._catalog_profile("NEW"), "HEA220")
            catalogue.profiles[1].designation = "HEA240"
            self.assertEqual(target._catalog_profile("NEW"), "HEA240")
            catalogue.profiles = [row("HEA300", "SPECIAL")]
            self.assertEqual(target._catalog_profile("SPECIAL"), "HEA300")

    def test_index_and_entries_are_immutable(self) -> None:
        index = target._catalog_profile_index((("HEA200", ("SPECIAL",)),))
        with self.assertRaises(TypeError):
            index["SPECIAL"] = frozenset({"HEA300"})
        with self.assertRaises(AttributeError):
            index["SPECIAL"].add("HEA300")

    def test_slashes_and_unknown_text_cannot_be_discarded_for_a_match(self) -> None:
        catalogue = SimpleNamespace(profiles=[row("L100/10"), row("HEA200")])
        with patch.object(target, "_profile_catalog", return_value=catalogue):
            self.assertEqual(target._catalog_profile("L100/10"), "L100/10")
            for query in ("L10010", "HEA", "HEA200UNKNOWN", "HEA?200"):
                self.assertEqual(target._catalog_profile(query), "", query)


if __name__ == "__main__":
    unittest.main(verbosity=2)
