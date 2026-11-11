"""Tests de :mod:`dcf_app.valuation.wacc`."""

from __future__ import annotations

import math

import pytest

from dcf_app.models.assumptions import DiscountConvention
from dcf_app.valuation.wacc import (
    capm_ke,
    cost_of_debt,
    discount_factor,
    present_value,
    terminal_value_gordon,
    terminal_value_multiple,
    wacc,
)

# ---------------------------------------------------------------------------
# capm_ke
# ---------------------------------------------------------------------------


def test_capm_ke_basic() -> None:
    """Ke = Rf + β × ERP."""
    # Rf=4%, β=1.2, ERP=5% → Ke = 0.04 + 1.2*0.05 = 0.10
    assert math.isclose(capm_ke(0.04, 1.2, 0.05), 0.10)


def test_capm_ke_zero_beta() -> None:
    """β=0 → Ke = Rf."""
    assert math.isclose(capm_ke(0.03, 0.0, 0.06), 0.03)


def test_capm_ke_high_beta() -> None:
    """β alto → Ke alto."""
    ke_low = capm_ke(0.04, 0.8, 0.05)
    ke_high = capm_ke(0.04, 1.5, 0.05)
    assert ke_high > ke_low


# ---------------------------------------------------------------------------
# cost_of_debt
# ---------------------------------------------------------------------------


def test_cost_of_debt_basic() -> None:
    """Kd = Intereses / Deuda media."""
    # 10M intereses / 100M deuda = 10%
    assert math.isclose(cost_of_debt(10.0, 100.0), 0.10)


def test_cost_of_debt_zero_debt_raises() -> None:
    """Deuda cero → ValueError."""
    with pytest.raises(ValueError, match="positiva"):
        cost_of_debt(5.0, 0.0)


def test_cost_of_debt_negative_debt_raises() -> None:
    """Deuda negativa → ValueError."""
    with pytest.raises(ValueError, match="positiva"):
        cost_of_debt(5.0, -10.0)


# ---------------------------------------------------------------------------
# wacc
# ---------------------------------------------------------------------------


def test_wacc_no_debt() -> None:
    """Sin deuda, WACC = Ke (AGENTS.md §7.3)."""
    ke = 0.10
    result = wacc(100.0, 0.0, ke, 0.05, 0.21)
    assert math.isclose(result, ke)


def test_wacc_no_equity() -> None:
    """Sin equity, WACC = Kd × (1 − t)."""
    kd = 0.06
    tax = 0.21
    result = wacc(0.0, 100.0, 0.10, kd, tax)
    assert math.isclose(result, kd * (1 - tax))


def test_wacc_basic() -> None:
    """WACC con pesos 60/40."""
    # E=60, D=40, Ke=10%, Kd=6%, t=21%
    # WACC = 0.6*0.10 + 0.4*0.06*0.79 = 0.06 + 0.01896 = 0.07896
    result = wacc(60.0, 40.0, 0.10, 0.06, 0.21)
    expected = 0.6 * 0.10 + 0.4 * 0.06 * 0.79
    assert math.isclose(result, expected)


def test_wacc_zero_total_raises() -> None:
    """Equity + deuda = 0 → ValueError."""
    with pytest.raises(ValueError, match="positivo"):
        wacc(0.0, 0.0, 0.10, 0.05, 0.21)


def test_wacc_higher_debt_increases_leverage_effect() -> None:
    """Más deuda → mayor efecto del escudo fiscal (ceteris paribus)."""
    w1 = wacc(80.0, 20.0, 0.10, 0.06, 0.21)
    w2 = wacc(50.0, 50.0, 0.10, 0.06, 0.21)
    # Con Kd < Ke, más deuda reduce el WACC (hasta cierto punto)
    assert w2 < w1


# ---------------------------------------------------------------------------
# discount_factor
# ---------------------------------------------------------------------------


def test_discount_factor_end_of_year() -> None:
    """DF_t = 1/(1+r)^t (fin de año)."""
    r = 0.10
    # Año 1: 1/1.10 = 0.90909...
    assert math.isclose(discount_factor(r, 1, DiscountConvention.END_OF_YEAR), 1.0 / 1.10)
    # Año 2: 1/1.10^2 = 0.82644...
    assert math.isclose(discount_factor(r, 2, DiscountConvention.END_OF_YEAR), 1.0 / 1.10**2)


def test_discount_factor_mid_year() -> None:
    """DF_t = 1/(1+r)^(t-0.5) (mitad de año)."""
    r = 0.10
    # Año 1: 1/1.10^0.5
    assert math.isclose(discount_factor(r, 1, DiscountConvention.MID_YEAR), 1.0 / 1.10**0.5)
    # Año 2: 1/1.10^1.5
    assert math.isclose(discount_factor(r, 2, DiscountConvention.MID_YEAR), 1.0 / 1.10**1.5)


def test_discount_factor_mid_year_higher_than_eoy() -> None:
    """Mitad de año → factor de descuento mayor (menos descuento)."""
    r = 0.10
    df_eoy = discount_factor(r, 3, DiscountConvention.END_OF_YEAR)
    df_mid = discount_factor(r, 3, DiscountConvention.MID_YEAR)
    assert df_mid > df_eoy


def test_discount_factor_zero_year_raises() -> None:
    """Año 0 → ValueError."""
    with pytest.raises(ValueError, match="mayor o igual a 1"):
        discount_factor(0.10, 0)


def test_discount_factor_negative_year_raises() -> None:
    """Año negativo → ValueError."""
    with pytest.raises(ValueError, match="mayor o igual a 1"):
        discount_factor(0.10, -1)


def test_discount_factor_string_convention() -> None:
    """Acepta string como convención."""
    r = 0.10
    assert math.isclose(
        discount_factor(r, 1, "mid_year"),
        discount_factor(r, 1, DiscountConvention.MID_YEAR),
    )


# ---------------------------------------------------------------------------
# present_value
# ---------------------------------------------------------------------------


def test_present_value_single_flow() -> None:
    """PV de un solo flujo."""
    cf = [100.0]
    pv = present_value(cf, 0.10, DiscountConvention.END_OF_YEAR)
    assert math.isclose(pv, 100.0 / 1.10)


def test_present_value_multiple_flows() -> None:
    """PV de múltiples flujos."""
    cf = [100.0, 110.0, 121.0]
    r = 0.10
    pv = present_value(cf, r, DiscountConvention.END_OF_YEAR)
    expected = 100.0 / 1.10 + 110.0 / 1.10**2 + 121.0 / 1.10**3
    assert math.isclose(pv, expected)


def test_present_value_empty() -> None:
    """Lista vacía → 0."""
    assert present_value([], 0.10) == 0.0


def test_present_value_mid_year() -> None:
    """PV con mitad de año."""
    cf = [100.0, 110.0]
    r = 0.10
    pv = present_value(cf, r, DiscountConvention.MID_YEAR)
    expected = 100.0 / 1.10**0.5 + 110.0 / 1.10**1.5
    assert math.isclose(pv, expected)


# ---------------------------------------------------------------------------
# terminal_value_gordon
# ---------------------------------------------------------------------------


def test_terminal_value_gordon_basic() -> None:
    """TV = FCFF_{n+1} / (WACC − g)."""
    fcff_next = 10.0
    wacc = 0.10
    g = 0.03
    tv = terminal_value_gordon(fcff_next, wacc, g)
    assert math.isclose(tv, 10.0 / (0.10 - 0.03))


def test_terminal_value_gordon_wacc_le_g_raises() -> None:
    """WACC ≤ g → ValueError."""
    with pytest.raises(ValueError, match="mayor que g"):
        terminal_value_gordon(10.0, 0.03, 0.03)
    with pytest.raises(ValueError, match="mayor que g"):
        terminal_value_gordon(10.0, 0.02, 0.03)


def test_terminal_value_gordon_higher_g_higher_tv() -> None:
    """Mayor g → mayor TV (mientras WACC > g)."""
    tv1 = terminal_value_gordon(10.0, 0.10, 0.02)
    tv2 = terminal_value_gordon(10.0, 0.10, 0.04)
    assert tv2 > tv1


def test_terminal_value_gordon_higher_wacc_lower_tv() -> None:
    """Mayor WACC → menor TV."""
    tv1 = terminal_value_gordon(10.0, 0.08, 0.03)
    tv2 = terminal_value_gordon(10.0, 0.12, 0.03)
    assert tv2 < tv1


# ---------------------------------------------------------------------------
# terminal_value_multiple
# ---------------------------------------------------------------------------


def test_terminal_value_multiple_basic() -> None:
    """TV = EBITDA × Múltiplo."""
    assert math.isclose(terminal_value_multiple(50.0, 8.0), 400.0)


def test_terminal_value_multiple_zero() -> None:
    """Múltiplo 0 → TV 0."""
    assert terminal_value_multiple(50.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


def test_wacc_monotonic_with_higher_ke() -> None:
    """Mayor Ke → mayor WACC (ceteris paribus)."""
    w1 = wacc(60.0, 40.0, 0.08, 0.06, 0.21)
    w2 = wacc(60.0, 40.0, 0.12, 0.06, 0.21)
    assert w2 > w1


def test_discount_factor_decreases_with_year() -> None:
    """Factor de descuento decrece con el año."""
    r = 0.10
    df1 = discount_factor(r, 1)
    df2 = discount_factor(r, 2)
    df3 = discount_factor(r, 3)
    assert df1 > df2 > df3


def test_discount_factor_decreases_with_rate() -> None:
    """Factor de descuento decrece con la tasa."""
    df_low = discount_factor(0.05, 3)
    df_high = discount_factor(0.15, 3)
    assert df_high < df_low
