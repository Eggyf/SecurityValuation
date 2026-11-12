"""Ejemplos de tests financieros (estilo pytest + hypothesis).

Adaptar los imports al motor real: `from dcf_app.valuation import ...`.
Aquí se usa `dcf_reference.py` (copia mínima) para que el ejemplo sea autocontenido.
"""
from __future__ import annotations

import dataclasses
import math

import pytest

from dcf_reference import Inputs, run_dcf

BASE = Inputs(
    revenue0=1000, growth=[0.10, 0.08, 0.06, 0.05, 0.04], ebit_margin=0.20,
    tax=0.21, da_pct=0.04, capex_pct=0.05, nwc_pct_of_delta_rev=0.10,
    wacc=0.09, g=0.025, cash=150, debt=400, diluted_shares=100,
)


# ------------------------------------------------------- 1. Caso calculado a mano
def test_fcff_year_1_by_hand():
    """Año 1: ingresos 1100; EBIT 220; NOPAT 173,8; D&A 44; CapEx 55; ΔNWC 10.
    FCFF = 173,8 + 44 − 55 − 10 = 152,8."""
    res = run_dcf(BASE)
    assert math.isclose(res.fcff[0], 152.8, abs_tol=1e-9)


def test_worked_example_matches_hand_calculation():
    res = run_dcf(BASE)
    assert math.isclose(res.enterprise_value, 2713.8, abs_tol=0.1)
    assert math.isclose(res.price_per_share, 24.64, abs_tol=0.01)


# ------------------------------------------------------- 2. Errores de dominio
def test_wacc_not_greater_than_g_raises():
    with pytest.raises(ValueError):
        run_dcf(dataclasses.replace(BASE, wacc=0.025, g=0.025))


# ------------------------------------------------------- 3. Identidades del puente
def test_bridge_with_no_debt_only_adds_cash():
    res = run_dcf(dataclasses.replace(BASE, debt=0.0))
    assert math.isclose(res.equity_value, res.enterprise_value + 150, rel_tol=1e-12)


def test_price_is_equity_over_shares():
    res = run_dcf(dataclasses.replace(BASE, diluted_shares=50))
    assert math.isclose(res.price_per_share, res.equity_value / 50, rel_tol=1e-12)


# ------------------------------------------------------- 4. Sensibilidad
def sensitivity(base: Inputs, waccs: list[float], gs: list[float]) -> dict:
    out = {}
    for w in waccs:
        for g in gs:
            out[(w, g)] = run_dcf(dataclasses.replace(base, wacc=w, g=g)).price_per_share \
                if w - g >= 0.01 else None   # celda inválida => None, no excepción
    return out


def test_sensitivity_center_equals_base():
    table = sensitivity(BASE, [0.08, 0.09, 0.10], [0.02, 0.025, 0.03])
    assert math.isclose(table[(0.09, 0.025)], run_dcf(BASE).price_per_share, rel_tol=1e-12)


def test_sensitivity_invalid_cells_are_none():
    table = sensitivity(BASE, [0.03], [0.025])
    assert table[(0.03, 0.025)] is None


# ------------------------------------------------------- 5. Convención de mitad de año
def test_mid_year_not_below_end_of_year_for_positive_flows():
    end = run_dcf(BASE).price_per_share
    mid = run_dcf(dataclasses.replace(BASE, mid_year=True)).price_per_share
    assert mid > end


# ------------------------------------------------------- 6. Propiedades (hypothesis)
hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st  # noqa: E402

# Rangos elegidos para que FCFF > 0 siempre (si no, la monotonía no es una ley).
valid_inputs = st.builds(
    lambda margin, growth, wacc, g: dataclasses.replace(
        BASE, ebit_margin=margin, growth=[growth] * 5, wacc=wacc, g=g),
    margin=st.floats(0.15, 0.40),
    growth=st.floats(0.0, 0.25),
    wacc=st.floats(0.06, 0.15),
    g=st.floats(0.0, 0.04),
).filter(lambda i: i.wacc - i.g >= 0.01)


@settings(max_examples=200, deadline=None)
@given(valid_inputs, st.floats(0.001, 0.02))
def test_higher_wacc_lowers_value(i, delta):
    higher = dataclasses.replace(i, wacc=i.wacc + delta)
    assert run_dcf(higher).price_per_share < run_dcf(i).price_per_share


@settings(max_examples=200, deadline=None)
@given(valid_inputs, st.floats(0.0005, 0.01))
def test_higher_g_raises_value_while_wacc_exceeds_g(i, delta):
    bumped = dataclasses.replace(i, g=i.g + delta)
    if bumped.wacc - bumped.g < 0.005:
        return
    assert run_dcf(bumped).price_per_share > run_dcf(i).price_per_share
