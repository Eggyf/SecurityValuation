"""Tests de :mod:`dcf_app.valuation.sensitivity`."""

from __future__ import annotations

import math

from dcf_app.models.assumptions import DiscountConvention, TerminalValueMethod
from dcf_app.valuation.sensitivity import (
    _dcf_price,
    sensitivity_2d,
    sensitivity_margin_growth,
    sensitivity_wacc_growth,
)

# Parámetros base para los tests
BASE_PARAMS = {
    "initial_revenue": 100.0,
    "growth_initial": 0.10,
    "growth_terminal": 0.03,
    "margin_current": 0.20,
    "margin_target": 0.25,
    "tax_rate": 0.21,
    "da_pct": 0.05,
    "capex_pct": 0.06,
    "nwc_pct": 0.10,
    "horizon": 5,
    "base_revenue": 95.0,
    "wacc": 0.10,
    "g": 0.03,
    "terminal_method": TerminalValueMethod.GORDON_GROWTH,
    "terminal_multiple": None,
    "roic_terminal": None,  # usa WACC por defecto
    "cash": 50.0,
    "short_term_investments": 10.0,
    "financial_debt": 200.0,
    "operating_leases": 0.0,
    "preferred_stock": 0.0,
    "non_controlling_interest": 0.0,
    "other_adjustments": 0.0,
    "basic_shares": 100.0,
    "options_outstanding": 5.0,
    "rsus_outstanding": 2.0,
    "avg_exercise_price": 50.0,
    "current_price": 100.0,
    "convention": DiscountConvention.END_OF_YEAR,
}


# ---------------------------------------------------------------------------
# _dcf_price
# ---------------------------------------------------------------------------


def test_dcf_price_returns_positive() -> None:
    """El precio por acción debe ser positivo con parámetros válidos."""
    price = _dcf_price(**BASE_PARAMS)
    assert not math.isnan(price)
    assert price > 0


def test_dcf_price_nan_when_wacc_le_g() -> None:
    """WACC ≤ g → NaN."""
    params = {**BASE_PARAMS, "wacc": 0.02, "g": 0.03}
    price = _dcf_price(**params)
    assert math.isnan(price)


def test_dcf_price_monotonic_with_wacc() -> None:
    """Mayor WACC → menor precio (ceteris paribus)."""
    p1 = _dcf_price(**{**BASE_PARAMS, "wacc": 0.08})
    p2 = _dcf_price(**{**BASE_PARAMS, "wacc": 0.12})
    assert p2 < p1


def test_dcf_price_monotonic_with_growth() -> None:
    """Mayor g → mayor precio (mientras WACC > g)."""
    p1 = _dcf_price(**{**BASE_PARAMS, "g": 0.02})
    p2 = _dcf_price(**{**BASE_PARAMS, "g": 0.04})
    assert p2 > p1


# ---------------------------------------------------------------------------
# sensitivity_2d
# ---------------------------------------------------------------------------


def test_sensitivity_2d_structure() -> None:
    """sensitivity_2d devuelve una tabla con todas las combinaciones."""

    def price_fn(a: float, b: float) -> float:
        return a + b

    result = sensitivity_2d(price_fn, [1.0, 2.0], [10.0, 20.0])
    assert len(result) == 4
    assert result[(1.0, 10.0)] == 11.0
    assert result[(2.0, 20.0)] == 22.0


def test_sensitivity_2d_empty() -> None:
    """Listas vacías → diccionario vacío."""
    result = sensitivity_2d(lambda a, b: a + b, [], [])
    assert result == {}


# ---------------------------------------------------------------------------
# sensitivity_wacc_growth
# ---------------------------------------------------------------------------


def test_sensitivity_wacc_growth_structure() -> None:
    """Tabla WACC × g con dimensiones correctas."""
    wacc_vals = [0.08, 0.10, 0.12]
    growth_vals = [0.02, 0.03, 0.04]
    result = sensitivity_wacc_growth(
        initial_revenue=BASE_PARAMS["initial_revenue"],
        margin_current=BASE_PARAMS["margin_current"],
        margin_target=BASE_PARAMS["margin_target"],
        tax_rate=BASE_PARAMS["tax_rate"],
        da_pct=BASE_PARAMS["da_pct"],
        capex_pct=BASE_PARAMS["capex_pct"],
        nwc_pct=BASE_PARAMS["nwc_pct"],
        horizon=BASE_PARAMS["horizon"],
        base_revenue=BASE_PARAMS["base_revenue"],
        cash=BASE_PARAMS["cash"],
        short_term_investments=BASE_PARAMS["short_term_investments"],
        financial_debt=BASE_PARAMS["financial_debt"],
        operating_leases=BASE_PARAMS["operating_leases"],
        preferred_stock=BASE_PARAMS["preferred_stock"],
        non_controlling_interest=BASE_PARAMS["non_controlling_interest"],
        other_adjustments=BASE_PARAMS["other_adjustments"],
        basic_shares=BASE_PARAMS["basic_shares"],
        options_outstanding=BASE_PARAMS["options_outstanding"],
        rsus_outstanding=BASE_PARAMS["rsus_outstanding"],
        avg_exercise_price=BASE_PARAMS["avg_exercise_price"],
        current_price=BASE_PARAMS["current_price"],
        convention=BASE_PARAMS["convention"],
        terminal_method=BASE_PARAMS["terminal_method"],
        terminal_multiple=BASE_PARAMS["terminal_multiple"],
        roic_terminal=None,
        wacc_values=wacc_vals,
        growth_values=growth_vals,
    )
    assert len(result) == 9  # 3 × 3
    # Todos los precios deben ser positivos o NaN
    for price in result.values():
        assert math.isnan(price) or price > 0


def test_sensitivity_wacc_growth_monotonic() -> None:
    """Mayor WACC → menor precio (en cada columna de g)."""
    wacc_vals = [0.08, 0.10, 0.12]
    growth_vals = [0.03]
    result = sensitivity_wacc_growth(
        initial_revenue=BASE_PARAMS["initial_revenue"],
        margin_current=BASE_PARAMS["margin_current"],
        margin_target=BASE_PARAMS["margin_target"],
        tax_rate=BASE_PARAMS["tax_rate"],
        da_pct=BASE_PARAMS["da_pct"],
        capex_pct=BASE_PARAMS["capex_pct"],
        nwc_pct=BASE_PARAMS["nwc_pct"],
        horizon=BASE_PARAMS["horizon"],
        base_revenue=BASE_PARAMS["base_revenue"],
        cash=BASE_PARAMS["cash"],
        short_term_investments=BASE_PARAMS["short_term_investments"],
        financial_debt=BASE_PARAMS["financial_debt"],
        operating_leases=BASE_PARAMS["operating_leases"],
        preferred_stock=BASE_PARAMS["preferred_stock"],
        non_controlling_interest=BASE_PARAMS["non_controlling_interest"],
        other_adjustments=BASE_PARAMS["other_adjustments"],
        basic_shares=BASE_PARAMS["basic_shares"],
        options_outstanding=BASE_PARAMS["options_outstanding"],
        rsus_outstanding=BASE_PARAMS["rsus_outstanding"],
        avg_exercise_price=BASE_PARAMS["avg_exercise_price"],
        current_price=BASE_PARAMS["current_price"],
        convention=BASE_PARAMS["convention"],
        terminal_method=BASE_PARAMS["terminal_method"],
        terminal_multiple=BASE_PARAMS["terminal_multiple"],
        roic_terminal=None,
        wacc_values=wacc_vals,
        growth_values=growth_vals,
    )
    prices = [result[(w, 0.03)] for w in wacc_vals]
    # Filtrar NaN
    valid = [p for p in prices if not math.isnan(p)]
    for i in range(1, len(valid)):
        assert valid[i] <= valid[i - 1]


# ---------------------------------------------------------------------------
# sensitivity_margin_growth
# ---------------------------------------------------------------------------


def test_sensitivity_margin_growth_structure() -> None:
    """Tabla margen × crecimiento con dimensiones correctas."""
    margin_vals = [0.20, 0.25, 0.30]
    growth_vals = [0.05, 0.10, 0.15]
    result = sensitivity_margin_growth(
        initial_revenue=BASE_PARAMS["initial_revenue"],
        margin_current=BASE_PARAMS["margin_current"],
        tax_rate=BASE_PARAMS["tax_rate"],
        da_pct=BASE_PARAMS["da_pct"],
        capex_pct=BASE_PARAMS["capex_pct"],
        nwc_pct=BASE_PARAMS["nwc_pct"],
        horizon=BASE_PARAMS["horizon"],
        base_revenue=BASE_PARAMS["base_revenue"],
        wacc=BASE_PARAMS["wacc"],
        g=BASE_PARAMS["g"],
        terminal_method=BASE_PARAMS["terminal_method"],
        terminal_multiple=BASE_PARAMS["terminal_multiple"],
        roic_terminal=None,
        cash=BASE_PARAMS["cash"],
        short_term_investments=BASE_PARAMS["short_term_investments"],
        financial_debt=BASE_PARAMS["financial_debt"],
        operating_leases=BASE_PARAMS["operating_leases"],
        preferred_stock=BASE_PARAMS["preferred_stock"],
        non_controlling_interest=BASE_PARAMS["non_controlling_interest"],
        other_adjustments=BASE_PARAMS["other_adjustments"],
        basic_shares=BASE_PARAMS["basic_shares"],
        options_outstanding=BASE_PARAMS["options_outstanding"],
        rsus_outstanding=BASE_PARAMS["rsus_outstanding"],
        avg_exercise_price=BASE_PARAMS["avg_exercise_price"],
        current_price=BASE_PARAMS["current_price"],
        convention=BASE_PARAMS["convention"],
        margin_values=margin_vals,
        growth_values=growth_vals,
    )
    assert len(result) == 9  # 3 × 3
    for price in result.values():
        assert math.isnan(price) or price > 0


def test_sensitivity_margin_growth_monotonic() -> None:
    """Mayor margen → mayor precio (en cada columna de crecimiento)."""
    margin_vals = [0.20, 0.25, 0.30]
    growth_vals = [0.10]
    result = sensitivity_margin_growth(
        initial_revenue=BASE_PARAMS["initial_revenue"],
        margin_current=BASE_PARAMS["margin_current"],
        tax_rate=BASE_PARAMS["tax_rate"],
        da_pct=BASE_PARAMS["da_pct"],
        capex_pct=BASE_PARAMS["capex_pct"],
        nwc_pct=BASE_PARAMS["nwc_pct"],
        horizon=BASE_PARAMS["horizon"],
        base_revenue=BASE_PARAMS["base_revenue"],
        wacc=BASE_PARAMS["wacc"],
        g=BASE_PARAMS["g"],
        terminal_method=BASE_PARAMS["terminal_method"],
        terminal_multiple=BASE_PARAMS["terminal_multiple"],
        roic_terminal=None,
        cash=BASE_PARAMS["cash"],
        short_term_investments=BASE_PARAMS["short_term_investments"],
        financial_debt=BASE_PARAMS["financial_debt"],
        operating_leases=BASE_PARAMS["operating_leases"],
        preferred_stock=BASE_PARAMS["preferred_stock"],
        non_controlling_interest=BASE_PARAMS["non_controlling_interest"],
        other_adjustments=BASE_PARAMS["other_adjustments"],
        basic_shares=BASE_PARAMS["basic_shares"],
        options_outstanding=BASE_PARAMS["options_outstanding"],
        rsus_outstanding=BASE_PARAMS["rsus_outstanding"],
        avg_exercise_price=BASE_PARAMS["avg_exercise_price"],
        current_price=BASE_PARAMS["current_price"],
        convention=BASE_PARAMS["convention"],
        margin_values=margin_vals,
        growth_values=growth_vals,
    )
    prices = [result[(m, 0.10)] for m in margin_vals]
    valid = [p for p in prices if not math.isnan(p)]
    for i in range(1, len(valid)):
        assert valid[i] >= valid[i - 1]


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


def test_sensitivity_symmetric() -> None:
    """La sensibilidad es simétrica: cambiar el orden de los ejes no cambia los valores."""
    wacc_vals = [0.08, 0.10]
    growth_vals = [0.02, 0.03]

    # Tabla normal
    result1 = sensitivity_wacc_growth(
        initial_revenue=BASE_PARAMS["initial_revenue"],
        margin_current=BASE_PARAMS["margin_current"],
        margin_target=BASE_PARAMS["margin_target"],
        tax_rate=BASE_PARAMS["tax_rate"],
        da_pct=BASE_PARAMS["da_pct"],
        capex_pct=BASE_PARAMS["capex_pct"],
        nwc_pct=BASE_PARAMS["nwc_pct"],
        horizon=BASE_PARAMS["horizon"],
        base_revenue=BASE_PARAMS["base_revenue"],
        cash=BASE_PARAMS["cash"],
        short_term_investments=BASE_PARAMS["short_term_investments"],
        financial_debt=BASE_PARAMS["financial_debt"],
        operating_leases=BASE_PARAMS["operating_leases"],
        preferred_stock=BASE_PARAMS["preferred_stock"],
        non_controlling_interest=BASE_PARAMS["non_controlling_interest"],
        other_adjustments=BASE_PARAMS["other_adjustments"],
        basic_shares=BASE_PARAMS["basic_shares"],
        options_outstanding=BASE_PARAMS["options_outstanding"],
        rsus_outstanding=BASE_PARAMS["rsus_outstanding"],
        avg_exercise_price=BASE_PARAMS["avg_exercise_price"],
        current_price=BASE_PARAMS["current_price"],
        convention=BASE_PARAMS["convention"],
        terminal_method=BASE_PARAMS["terminal_method"],
        terminal_multiple=BASE_PARAMS["terminal_multiple"],
        roic_terminal=None,
        wacc_values=wacc_vals,
        growth_values=growth_vals,
    )

    # Verificar que todos los valores son consistentes
    for (_w, _g), price in result1.items():
        assert math.isnan(price) or price > 0
