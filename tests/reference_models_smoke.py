from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import tracemalloc
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from converter import parse_nc1
from cws_convertor.project import inspect_model_file

FORMATS = {
    ".step": "STEP",
    ".stp": "STEP",
    ".ifc": "IFC",
    ".nc": "DSTV",
    ".nc1": "DSTV",
}
STATUSES = {"validated", "manual_validation_required"}


def extra_roots(name: str) -> list[Path]:
    return [Path(item) for item in os.environ.get(name, "").split(os.pathsep) if item]


MODEL_ROOTS = [
    (ROOT / "reference-models", False),
    (ROOT / "reference-models-local", True),
    *((path, True) for path in extra_roots("CWS_REFERENCE_MODEL_ROOTS")),
]
RESULT_ROOTS = [
    (ROOT / "reference-results", False),
    (ROOT / "reference-results-local", True),
    *((path, True) for path in extra_roots("CWS_REFERENCE_RESULT_ROOTS")),
]


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def discover_models() -> dict[str, tuple[Path, str, bool]]:
    models: dict[str, tuple[Path, str, bool]] = {}
    for root, confidential in MODEL_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            fmt = FORMATS.get(path.suffix.lower()) if path.is_file() else None
            if fmt:
                key = relative_path(path)
                if key in models:
                    raise AssertionError(f"Dubbel referentiemodelpad: {key}")
                models[key] = (path, fmt, confidential)
    return models


def load_expectations() -> list[tuple[Path, dict]]:
    expectations: list[tuple[Path, dict]] = []
    for root, _confidential in RESULT_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.expected.json"):
            expectations.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return expectations


def value_at_path(value: object, dotted_path: str) -> object:
    current = value
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def analyze_model(path: Path, fmt: str) -> dict:
    tracemalloc.start()
    started = time.perf_counter()
    if fmt == "DSTV":
        parsed = parse_nc1(path)
        parse_seconds = time.perf_counter() - started
        observation = {
            "source": {
                "filename": path.name,
                "format": fmt,
                "sizeBytes": path.stat().st_size,
                "sha256": sha256_file(path),
            },
            "model": {
                "profile": parsed.header.profile,
                "material": parsed.header.material,
                "dimensions": {
                    "length": parsed.header.length,
                    "dim1": parsed.header.dim1,
                    "dim2": parsed.header.dim2,
                    "dim3": parsed.header.dim3,
                    "dim4": parsed.header.dim4,
                },
                "holes": len(parsed.holes),
                "contours": len(parsed.contours),
                "unsupportedBlocks": sorted(set(parsed.unsupported_blocks)),
            },
            "warnings": list(parsed.warnings),
        }
    else:
        parsed = inspect_model_file(path, include_geometry=False)
        parse_seconds = time.perf_counter() - started
        observation = {
            "source": {
                "filename": path.name,
                "format": fmt,
                "sizeBytes": path.stat().st_size,
                "sha256": sha256_file(path),
            },
            "analysis": parsed.to_dict(),
        }
    total_seconds = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    observation["performance"] = {
        "parseMs": round(parse_seconds * 1000.0, 3),
        "totalMs": round(total_seconds * 1000.0, 3),
        "heapDeltaMb": round(peak / 1024.0 / 1024.0, 3),
    }
    return observation


def failure_message(model: str, property_name: str, expected: object, found: object, cause: str) -> str:
    return "\n".join(
        (
            f"Model: {model}",
            f"Eigenschap: {property_name}",
            f"Verwachte waarde: {expected!r}",
            f"Gevonden waarde: {found!r}",
            f"Vermoedelijke oorzaak: {cause}",
        )
    )


class ReferenceModelTests(unittest.TestCase):
    def test_catalog_pairing_and_validated_results(self) -> None:
        self.assertTrue((ROOT / "reference-models").is_dir())
        self.assertTrue((ROOT / "reference-results").is_dir())
        models = discover_models()
        expectations = load_expectations()
        by_model: dict[str, tuple[Path, dict]] = {}
        model_ids: set[str] = set()

        for result_path, expectation in expectations:
            with self.subTest(expected_result=relative_path(result_path)):
                self.assertEqual(expectation.get("schemaVersion"), 1)
                model = expectation.get("model") or {}
                validation = expectation.get("validation") or {}
                comparison = expectation.get("comparison")
                model_id = str(model.get("id") or "")
                model_path = str(model.get("path") or "")
                self.assertTrue(model_id, "model.id ontbreekt")
                self.assertNotIn(model_id, model_ids, f"Dubbel model.id: {model_id}")
                model_ids.add(model_id)
                self.assertTrue(model_path, "model.path ontbreekt")
                self.assertNotIn("\\", model_path, "Gebruik forward slashes in model.path")
                self.assertIn(model.get("format"), set(FORMATS.values()))
                self.assertIsInstance(model.get("confidential"), bool)
                self.assertIn(validation.get("status"), STATUSES)
                self.assertIsInstance(comparison, dict)
                self.assertNotIn(model_path, by_model, f"Dubbel expected-result voor {model_path}")
                by_model[model_path] = (result_path, expectation)

        missing_results = sorted(set(models) - set(by_model))
        missing_models = sorted(set(by_model) - set(models))
        self.assertEqual(
            missing_results,
            [],
            "Referentiemodellen zonder expected-result: " + ", ".join(missing_results),
        )
        self.assertEqual(
            missing_models,
            [],
            "Expected-results zonder model: " + ", ".join(missing_models),
        )

        for model_path, (result_path, expectation) in by_model.items():
            if expectation["validation"]["status"] != "validated":
                continue
            path, fmt, confidential = models[model_path]
            with self.subTest(validated_model=model_path):
                self.assertEqual(expectation["model"]["format"], fmt)
                self.assertEqual(expectation["model"]["confidential"], confidential)
                actual = analyze_model(path, fmt)
                comparison = expectation["comparison"]
                for property_name, expected in (comparison.get("exact") or {}).items():
                    found = value_at_path(actual, property_name)
                    self.assertEqual(
                        found,
                        expected,
                        failure_message(
                            model_path,
                            property_name,
                            expected,
                            found,
                            "Exacte golden value verschilt van de huidige analyse.",
                        ),
                    )
                for property_name, rule in (comparison.get("tolerance") or {}).items():
                    found = value_at_path(actual, property_name)
                    expected = rule.get("expected")
                    tolerance = float(rule.get("tolerance", 0.0))
                    self.assertIsInstance(
                        found,
                        (int, float),
                        failure_message(model_path, property_name, expected, found, "Numerieke waarde ontbreekt."),
                    )
                    self.assertLessEqual(
                        abs(float(found) - float(expected)),
                        tolerance,
                        failure_message(model_path, property_name, expected, found, "Tolerantie is overschreden."),
                    )
                metadata = comparison.get("metadata") or {}
                for property_name, rule in metadata.items():
                    if not isinstance(rule, dict) or rule.get("comparison") == "informational":
                        continue
                    found = value_at_path(actual, property_name)
                    if rule.get("comparison") == "exact":
                        self.assertEqual(
                            found,
                            rule.get("expected"),
                            failure_message(
                                model_path,
                                property_name,
                                rule.get("expected"),
                                found,
                                "Exact vergeleken metadata wijkt af.",
                            ),
                        )
                    elif rule.get("comparison") == "pattern":
                        pattern = str(rule.get("pattern") or "")
                        self.assertRegex(
                            str(found or ""),
                            re.compile(pattern),
                            failure_message(
                                model_path,
                                property_name,
                                pattern,
                                found,
                                "Metadata voldoet niet aan het verwachte patroon.",
                            ),
                        )
                performance = comparison.get("performance") or {}
                for key, actual_key in (
                    ("maxParseMs", "parseMs"),
                    ("maxTotalMs", "totalMs"),
                    ("maxHeapDeltaMb", "heapDeltaMb"),
                ):
                    if key in performance:
                        self.assertLessEqual(
                            actual["performance"][actual_key],
                            float(performance[key]),
                            failure_message(
                                model_path,
                                f"performance.{actual_key}",
                                f"<= {performance[key]}",
                                actual["performance"][actual_key],
                                "Performancegrens is overschreden.",
                            ),
                        )

        print(
            json.dumps(
                {
                    "models": len(models),
                    "expected_results": len(expectations),
                    "validated": sum(
                        item["validation"]["status"] == "validated"
                        for _path, item in expectations
                    ),
                    "manual_validation_required": sum(
                        item["validation"]["status"] == "manual_validation_required"
                        for _path, item in expectations
                    ),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
