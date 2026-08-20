"""Safe versioned formula DSL for nesting time/cost evidence.

No Python eval/exec is used. Expressions are parsed with ``ast`` and interpreted
by a small whitelist evaluator. The DSL is deliberately numeric and bounded.
"""
from __future__ import annotations

import ast
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
from typing import Any

from .models import FormulaDefinition

MAX_EXPRESSION_LENGTH = 512
MAX_AST_NODES = 128
MAX_ABS_RESULT = Decimal("1e12")
SUPPORTED_VARIABLES = {
    "stock_length", "piece_length", "profile_width", "profile_height",
    "saw_angle", "cut_count", "common_cut_count", "hole_count",
    "tool_change_count", "travel_distance", "batch_size", "machine_feed",
    "setup_seconds", "handling_seconds", "kerf", "head_trim", "tail_trim", "material",
}

class SafeFormulaError(ValueError):
    pass


def _decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        return Decimal(int(value))
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SafeFormulaError(f"Niet-numerieke formulewaarde {value!r}") from exc
    if not out.is_finite():
        raise SafeFormulaError("Formule bevat NaN/Infinity")
    return out


def _sqrt(value: Decimal) -> Decimal:
    if value < 0:
        raise SafeFormulaError("sqrt van negatieve waarde")
    return value.sqrt()


def _round(value: Decimal, digits: Decimal = Decimal(0)) -> Decimal:
    places = int(digits)
    if places < -6 or places > 9:
        raise SafeFormulaError("round precisie buiten toegestane grens")
    quantum = Decimal(1).scaleb(-places)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)

_FUNCTIONS = {
    "min": lambda *args: min(args),
    "max": lambda *args: max(args),
    "abs": lambda x: abs(x),
    "sqrt": _sqrt,
    "round": _round,
    "ceil": lambda x: Decimal(math.ceil(x)),
    "floor": lambda x: Decimal(math.floor(x)),
}

_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load, ast.BinOp, ast.UnaryOp,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Call, ast.Compare, ast.Eq, ast.NotEq, ast.IfExp,
)


def validate_formula(definition: FormulaDefinition) -> str:
    if not definition.formula_id.strip() or not definition.purpose.strip():
        raise SafeFormulaError("Formula-ID en purpose zijn verplicht")
    expression = definition.expression.strip()
    if not expression or len(expression) > MAX_EXPRESSION_LENGTH:
        raise SafeFormulaError("Formule is leeg of te lang")
    declared = set(definition.allowed_variables)
    unknown_declared = declared - SUPPORTED_VARIABLES
    if unknown_declared:
        raise SafeFormulaError(f"Niet-ondersteunde formulevariabelen: {sorted(unknown_declared)}")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SafeFormulaError(f"Ongeldige formulesyntaxis: {exc.msg}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        raise SafeFormulaError("Formule is te complex")
    for node in nodes:
        if not isinstance(node, _ALLOWED_NODES):
            raise SafeFormulaError(f"Niet-toegestane formuleconstructie: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in declared and node.id not in _FUNCTIONS:
            raise SafeFormulaError(f"Niet-gedeclareerde variabele/functie: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCTIONS:
                raise SafeFormulaError("Alleen whitelisted functies zijn toegestaan")
            if node.keywords:
                raise SafeFormulaError("Keyword-argumenten zijn niet toegestaan")
    return definition.refresh_hash()


def _eval(node: ast.AST, values: dict[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Expression):
        return _eval(node.body, values)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return _decimal(node.value)
        if isinstance(node.value, str):
            return node.value
        raise SafeFormulaError("Alleen numerieke of tekstconstanten zijn toegestaan")
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise SafeFormulaError(f"Formulevariabele ontbreekt: {node.id}")
        return values[node.id]
    if isinstance(node, ast.Compare):
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise SafeFormulaError("Alleen enkelvoudige vergelijkingen zijn toegestaan")
        left, right = _eval(node.left, values), _eval(node.comparators[0], values)
        if isinstance(node.ops[0], ast.Eq): return left == right
        if isinstance(node.ops[0], ast.NotEq): return left != right
        raise SafeFormulaError("Alleen == en != zijn toegestaan")
    if isinstance(node, ast.IfExp):
        condition = _eval(node.test, values)
        if not isinstance(condition, bool): raise SafeFormulaError("Voorwaarde moet boolean zijn")
        return _eval(node.body if condition else node.orelse, values)
    if isinstance(node, ast.UnaryOp):
        v = _decimal(_eval(node.operand, values))
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp):
        left, right = _decimal(_eval(node.left, values)), _decimal(_eval(node.right, values))
        if isinstance(node.op, ast.Add): result = left + right
        elif isinstance(node.op, ast.Sub): result = left - right
        elif isinstance(node.op, ast.Mult): result = left * right
        elif isinstance(node.op, ast.Div):
            if right == 0: raise SafeFormulaError("Delen door nul")
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            if right == 0: raise SafeFormulaError("Delen door nul")
            result = Decimal(left // right)
        elif isinstance(node.op, ast.Mod):
            if right == 0: raise SafeFormulaError("Modulo door nul")
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if right != int(right) or abs(int(right)) > 6:
                raise SafeFormulaError("Exponent moet een geheel getal tussen -6 en 6 zijn")
            result = left ** int(right)
        else: raise SafeFormulaError("Niet-toegestane operator")
        if not result.is_finite() or abs(result) > MAX_ABS_RESULT:
            raise SafeFormulaError("Formuleresultaat buiten veilige grens")
        return result
    if isinstance(node, ast.Call):
        fn = _FUNCTIONS[node.func.id]  # type: ignore[union-attr]
        args = [_decimal(_eval(arg, values)) for arg in node.args]
        if not args:
            raise SafeFormulaError("Functie vereist argumenten")
        try:
            result = fn(*args)
        except SafeFormulaError:
            raise
        except Exception as exc:
            raise SafeFormulaError(f"Functiefout in {node.func.id}: {exc}") from exc  # type: ignore[union-attr]
        result = _decimal(result)
        if abs(result) > MAX_ABS_RESULT:
            raise SafeFormulaError("Formuleresultaat buiten veilige grens")
        return result
    raise SafeFormulaError(f"Niet-toegestane AST-node {type(node).__name__}")


def evaluate_formula(definition: FormulaDefinition, variables: dict[str, Any]) -> Decimal:
    validate_formula(definition)
    missing = set(definition.allowed_variables) - set(variables)
    if missing:
        raise SafeFormulaError(f"Ontbrekende formulevariabelen: {sorted(missing)}")
    values = {name: (str(variables[name]) if name == "material" else _decimal(variables[name])) for name in definition.allowed_variables}
    tree = ast.parse(definition.expression.strip(), mode="eval")
    result = _eval(tree, values)
    return _decimal(result)
