"""Tests de :mod:`dcf_app.valuation.bridge`."""

from __future__ import annotations

import math

import pytest

from dcf_app.valuation.bridge import (
    bridge_summary,
    bridge_to_equity,
    price_per_share,
    treasury_stock_diluted_shares,
)

# ---------------------------------------------------------------------------
# treasury_stock_diluted_shares
# ---------------------------------------------------------------------------


def test_treasury_stock_no_options() -> None:
    """Sin opciones ni RSUs, acciones diluidas = básicas."""
    result = treasury_stock_diluted_shares(100.0, 0.0, 0.0, 50.0, 100.0)
    assert math.isclose(result, 100.0)


def test_treasury_stock_options_in_the_money() -> None:
    """Opciones in the money diluyen parcialmente."""
    # 10M opciones, exercise=50, price=100
    # dilución = 10 * (1 - 50/100) = 5M
    result = treasury_stock_diluted_shares(100.0, 10.0, 0.0, 50.0, 100.0)
    assert math.isclose(result, 105.0)


def test_treasury_stock_options_out_of_the_money() -> None:
    """Opciones out of the money no diluyen."""
    result = treasury_stock_diluted_shares(100.0, 10.0, 0.0, 150.0, 100.0)
    assert math.isclose(result, 100.0)


def test_treasury_stock_rsus_always_dilute() -> None:
    """RSUs siempre diluyen (sin precio de ejercicio)."""
    result = treasury_stock_diluted_shares(100.0, 0.0, 5.0, 50.0, 100.0)
    assert math.isclose(result, 105.0)


def test_treasury_stock_combined() -> None:
    """Opciones + RSUs combinados."""
    # 10M opciones (exercise=50, price=100) → dilución 5M
    # 5M RSUs → 5M
    # Total: 100 + 5 + 5 = 110M
    result = treasury_stock_diluted_shares(100.0, 10.0, 5.0, 50.0, 100.0)
    assert math.isclose(result, 110.0)


def test_treasury_stock_zero_price_raises() -> None:
    """Precio cero → ValueError."""
    with pytest.raises(ValueError, match="positivo"):
        treasury_stock_diluted_shares(100.0, 10.0, 0.0, 50.0, 0.0)


def test_treasury_stock_negative_price_raises() -> None:
    """Precio negativo → ValueError."""
    with pytest.raises(ValueError, match="positivo"):
        treasury_stock_diluted_shares(100.0, 10.0, 0.0, 50.0, -10.0)


def test_treasury_stock_zero_options() -> None:
    """Opciones cero no afectan."""
    result = treasury_stock_diluted_shares(100.0, 0.0, 0.0, 50.0, 100.0)
    assert math.isclose(result, 100.0)


# ---------------------------------------------------------------------------
# bridge_to_equity
# ---------------------------------------------------------------------------


def test_bridge_to_equity_basic() -> None:
    """Puente básico: EV + Caja − Deuda."""
    # EV=1000, Caja=50, Deuda=200 → Equity=850
    result = bridge_to_equity(1000.0, 50.0, financial_debt=200.0)
    assert math.isclose(result, 850.0)


def test_bridge_to_equity_full() -> None:
    """Puente completo con todas las partidas."""
    result = bridge_to_equity(
        enterprise_value=1000.0,
        cash_and_equivalents=50.0,
        short_term_investments=30.0,
        financial_debt=200.0,
        operating_leases=40.0,
        preferred_stock=10.0,
        non_controlling_interest=5.0,
        other_adjustments=-2.0,
    )
    # 1000 + 50 + 30 - 200 - 40 - 10 - 5 - 2 = 823
    expected = 1000.0 + 50.0 + 30.0 - 200.0 - 40.0 - 10.0 - 5.0 - 2.0
    assert math.isclose(result, expected)


def test_bridge_to_equity_no_adjustments() -> None:
    """Sin ajustes, Equity = EV + Caja."""
    result = bridge_to_equity(500.0, 20.0)
    assert math.isclose(result, 520.0)


def test_bridge_to_equity_negative_equity() -> None:
    """Equity puede ser negativo (empresa con más deuda que activos)."""
    result = bridge_to_equity(100.0, 10.0, financial_debt=200.0)
    assert math.isclose(result, -90.0)


# ---------------------------------------------------------------------------
# price_per_share
# ---------------------------------------------------------------------------


def test_price_per_share_basic() -> None:
    """Precio = Equity / Acciones diluidas."""
    result = price_per_share(1000.0, 100.0)
    assert math.isclose(result, 10.0)


def test_price_per_share_zero_shares_raises() -> None:
    """Acciones cero → ValueError."""
    with pytest.raises(ValueError, match="positivas"):
        price_per_share(1000.0, 0.0)


def test_price_per_share_negative_shares_raises() -> None:
    """Acciones negativas → ValueError."""
    with pytest.raises(ValueError, match="positivas"):
        price_per_share(1000.0, -5.0)


# ---------------------------------------------------------------------------
# bridge_summary
# ---------------------------------------------------------------------------


def test_bridge_summary_structure() -> None:
    """bridge_summary devuelve todas las partidas."""
    summary = bridge_summary(
        enterprise_value=1000.0,
        cash_and_equivalents=50.0,
        financial_debt=200.0,
    )
    assert "enterprise_value" in summary
    assert "cash_and_equivalents" in summary
    assert "financial_debt" in summary
    assert "equity_value" in summary
    assert math.isclose(summary["equity_value"], 850.0)


def test_bridge_summary_equity_matches_bridge() -> None:
    """El equity de bridge_summary coincide con bridge_to_equity."""
    kwargs = {
        "enterprise_value": 1000.0,
        "cash_and_equivalents": 50.0,
        "short_term_investments": 30.0,
        "financial_debt": 200.0,
        "operating_leases": 40.0,
        "preferred_stock": 10.0,
        "non_controlling_interest": 5.0,
        "other_adjustments": -2.0,
    }
    summary = bridge_summary(**kwargs)
    equity = bridge_to_equity(**kwargs)
    assert math.isclose(summary["equity_value"], equity)


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


def test_bridge_monotonic_with_higher_ev() -> None:
    """Mayor EV → mayor equity (ceteris paribus)."""
    e1 = bridge_to_equity(900.0, 50.0, financial_debt=200.0)
    e2 = bridge_to_equity(1100.0, 50.0, financial_debt=200.0)
    assert e2 > e1


def test_bridge_monotonic_with_more_debt() -> None:
    """Más deuda → menor equity (ceteris paribus)."""
    e1 = bridge_to_equity(1000.0, 50.0, financial_debt=100.0)
    e2 = bridge_to_equity(1000.0, 50.0, financial_debt=300.0)
    assert e2 < e1


def test_price_monotonic_with_more_shares() -> None:
    """Más acciones → menor precio (ceteris paribus)."""
    p1 = price_per_share(1000.0, 100.0)
    p2 = price_per_share(1000.0, 200.0)
    assert p2 < p1
