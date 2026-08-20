"""Deterministic objective stack for straight-cut profile nesting.

All solver-facing metrics are integers. Monetary values use micro-currency
units, preventing binary floating point from changing solver ordering.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from cws_convertor.project.model import stable_sha256
from .results import ObjectiveBreakdown

ALLOWED_METRICS = {
    "material_loss_units",
    "waste_units",
    "reusable_remnant_units",
    "gross_stock_units",
    "net_part_units",
    "bar_count",
    "purchase_bar_count",
    "physical_bar_count",
    "full_stock_bar_count",
    "remnant_bar_count",
    "setup_count",
    "cost_micros",
}


def default_objective_configuration(family: str = "waste") -> dict[str, Any]:
    key = str(family or "waste").strip().lower()
    presets: dict[str, list[str]] = {
        "waste": ["material_loss_units", "gross_stock_units", "bar_count", "cost_micros"],
        "minimal_waste": ["material_loss_units", "gross_stock_units", "bar_count", "cost_micros"],
        "cost": ["cost_micros", "material_loss_units", "bar_count", "gross_stock_units"],
        "minimal_cost": ["cost_micros", "material_loss_units", "bar_count", "gross_stock_units"],
        "stock_first": ["purchase_bar_count", "material_loss_units", "bar_count", "cost_micros"],
        "remnants_first": ["purchase_bar_count", "full_stock_bar_count", "material_loss_units", "bar_count", "cost_micros"],
        "bars": ["bar_count", "material_loss_units", "cost_micros", "gross_stock_units"],
        "minimal_bars": ["bar_count", "material_loss_units", "cost_micros", "gross_stock_units"],
        "proven": ["material_loss_units", "gross_stock_units", "bar_count", "cost_micros"],
        "proven_optimum": ["material_loss_units", "gross_stock_units", "bar_count", "cost_micros"],
        "fast": ["bar_count", "material_loss_units", "cost_micros", "gross_stock_units"],
    }
    metrics = presets.get(key, presets["waste"])
    return {
        "mode": "lexicographic",
        "family": key,
        "components": [
            {"metric": metric, "direction": "min", "priority": index + 1}
            for index, metric in enumerate(metrics)
        ],
    }


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Ongeldige {label}: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"{label} moet eindig zijn")
    return result


def validate_objective_configuration(configuration: dict[str, Any] | None, *, family: str = "waste") -> dict[str, Any]:
    config = dict(configuration or default_objective_configuration(family))
    mode = str(config.get("mode") or "lexicographic").strip().lower()
    if mode not in {"lexicographic", "weighted"}:
        raise ValueError("Objective mode moet lexicographic of weighted zijn")
    components = list(config.get("components") or [])
    if not components:
        raise ValueError("Objective stack bevat geen componenten")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(components):
        item = dict(raw or {})
        metric = str(item.get("metric") or "").strip()
        if metric not in ALLOWED_METRICS:
            raise ValueError(f"Onbekende objective metric {metric!r}")
        if metric in seen:
            raise ValueError(f"Objective metric {metric!r} komt dubbel voor")
        seen.add(metric)
        direction = str(item.get("direction") or "min").strip().lower()
        if direction not in {"min", "max"}:
            raise ValueError("Objective direction moet min of max zijn")
        record: dict[str, Any] = {
            "metric": metric,
            "direction": direction,
            "priority": int(item.get("priority") or index + 1),
        }
        if mode == "weighted":
            weight = _decimal(item.get("weight", 1), "objective weight")
            scale = _decimal(item.get("scale", 0), "objective scale")
            if weight < 0:
                raise ValueError("Objective weight mag niet negatief zijn")
            if scale <= 0:
                raise ValueError(
                    "Weighted objectives vereisen per component een expliciete positieve scale; "
                    "dit voorkomt verborgen schaalbias"
                )
            record["weight"] = format(weight, "f")
            record["scale"] = format(scale, "f")
        normalized.append(record)
    normalized.sort(key=lambda item: (int(item["priority"]), str(item["metric"])))
    result = {
        "mode": mode,
        "family": str(config.get("family") or family),
        "components": normalized,
    }
    result["configuration_hash"] = stable_sha256(result)
    return result


def objective_key(metrics: dict[str, int], configuration: dict[str, Any]) -> tuple[Any, ...]:
    config = validate_objective_configuration(configuration, family=str(configuration.get("family") or "waste"))
    if config["mode"] == "lexicographic":
        values: list[int] = []
        for item in config["components"]:
            value = int(metrics.get(item["metric"], 0))
            values.append(value if item["direction"] == "min" else -value)
        return tuple(values)
    score = Decimal(0)
    for item in config["components"]:
        raw = Decimal(int(metrics.get(item["metric"], 0)))
        scale = Decimal(item["scale"])
        weight = Decimal(item["weight"])
        normalized = raw / scale
        score += weight * (normalized if item["direction"] == "min" else -normalized)
    return (score,)


def evaluate_objective(metrics: dict[str, int], configuration: dict[str, Any]) -> ObjectiveBreakdown:
    config = validate_objective_configuration(configuration, family=str(configuration.get("family") or "waste"))
    key = objective_key(metrics, config)
    components: list[dict[str, Any]] = []
    for item in config["components"]:
        record = dict(item)
        record["raw_value"] = int(metrics.get(item["metric"], 0))
        if config["mode"] == "weighted":
            raw = Decimal(record["raw_value"])
            scale = Decimal(record["scale"])
            record["normalized_value"] = format(raw / scale, "f")
        components.append(record)
    return ObjectiveBreakdown(
        mode=config["mode"],
        components=components,
        raw_metrics={str(k): int(v) for k, v in sorted(metrics.items())},
        comparison_key=[format(value, "f") if isinstance(value, Decimal) else str(value) for value in key],
        weighted_score=(format(key[0], "f") if config["mode"] == "weighted" else ""),
        configuration_hash=str(config["configuration_hash"]),
    )
