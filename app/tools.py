"""Deterministic tools: weather (Open-Meteo), safe math, static FX rates."""

from __future__ import annotations

import ast
import operator
from typing import Any

import requests
from agents import function_tool

SUPPORTED_CURRENCIES = frozenset({"USD", "EUR", "ILS", "GBP"})

# ILS value of 1 unit of each currency (deterministic coursework anchors; not live market data).
_ILS_PER_UNIT: dict[str, float] = {
    "ILS": 1.0,
    "USD": 3.65,  # ~1 USD = 3.65 ILS
    "EUR": 4.05,  # ~1 EUR = 4.05 ILS
    "GBP": 4.70,  # ~1 GBP = 4.70 ILS
}


class _SafeEval(ast.NodeVisitor):
    """Evaluate a limited arithmetic AST."""

    def visit(self, node: ast.AST) -> float:  # type: ignore[override]
        if isinstance(node, ast.Expression):
            return self.visit(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("Only numeric constants are allowed")
        if isinstance(node, ast.BinOp):
            left = self.visit(node.left)
            right = self.visit(node.right)
            op = node.op
            if isinstance(op, ast.Add):
                return left + right
            if isinstance(op, ast.Sub):
                return left - right
            if isinstance(op, ast.Mult):
                return left * right
            if isinstance(op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("division by zero")
                return left / right
            raise ValueError("Unsupported binary operator")
        if isinstance(node, ast.UnaryOp):
            v = self.visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.USub):
                return -v
            raise ValueError("Unsupported unary operator")
        if isinstance(node, ast.Tuple):
            raise ValueError("Tuples are not allowed in expressions")
        raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def _evaluate_expression(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    return _SafeEval().visit(tree)


def _geocode_city(city: str) -> tuple[float, float, str] | None:
    params = {"name": city.strip(), "count": 1, "language": "en", "format": "json"}
    r = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params=params,
        timeout=12,
    )
    r.raise_for_status()
    data = r.json()
    results = data.get("results") or []
    if not results:
        return None
    row = results[0]
    lat, lon = float(row["latitude"]), float(row["longitude"])
    label = row.get("name", city)
    country = row.get("country_code", "")
    display = f"{label}" + (f", {country}" if country else "")
    return lat, lon, display


def _current_weather(lat: float, lon: float) -> dict[str, Any]:
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
        },
        timeout=12,
    )
    r.raise_for_status()
    return r.json()


@function_tool
def get_weather(city: str) -> str:
    """Fetch current weather for a city using Open-Meteo (geocoding + forecast)."""
    if not city or not str(city).strip():
        return "Error: city name must not be empty."
    try:
        geo = _geocode_city(str(city))
        if geo is None:
            return f"Could not geocode city: {city!r}. Try another spelling."
        lat, lon, label = geo
        payload = _current_weather(lat, lon)
        cw = payload.get("current_weather") or {}
        temp = cw.get("temperature")
        code = cw.get("weathercode")
        wind = cw.get("windspeed")
        parts = [f"City: {label}", f"Coordinates: lat={lat:.4f}, lon={lon:.4f}"]
        if temp is not None:
            parts.append(f"Temperature (°C): {temp}")
        if code is not None:
            parts.append(f"Weather code (WMO): {code}")
        if wind is not None:
            parts.append(f"Wind speed: {wind} km/h")
        return " | ".join(parts)
    except requests.RequestException as e:
        return f"Weather service error: {e}"


@function_tool
def calculate_math(expression: str) -> str:
    """Evaluate a safe arithmetic expression (+, -, *, /, parentheses, decimals)."""
    if not expression or not str(expression).strip():
        return "Error: empty expression."
    try:
        value = _evaluate_expression(str(expression).strip())
        if value == int(value):
            return str(int(value))
        return str(value)
    except ZeroDivisionError:
        return "Error: division by zero."
    except (SyntaxError, ValueError, TypeError) as e:
        return f"Error: invalid expression ({e})."


@function_tool
def get_exchange_rate(
    from_currency: str,
    to_currency: str,
    amount: float = 1.0,
) -> str:
    """Convert amount via static ILS anchors (cross-rates = ratio of ILS-per-unit values)."""
    fc = str(from_currency).upper().strip()
    tc = str(to_currency).upper().strip()
    if fc not in SUPPORTED_CURRENCIES or tc not in SUPPORTED_CURRENCIES:
        return (
            f"Error: unsupported currency pair ({from_currency!r} -> {to_currency!r}). "
            f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
        )
    if amount <= 0:
        return "Error: amount must be positive."
    ils_per_fc = _ILS_PER_UNIT[fc]
    ils_per_tc = _ILS_PER_UNIT[tc]
    cross = ils_per_fc / ils_per_tc if ils_per_tc != 0 else 0.0
    converted = amount * cross
    return (
        f"Rate {fc}->{tc}: {cross:.6g} (static ILS-based mapping) | "
        f"Converted amount: {converted:.6g} {tc}"
    )
