"""Tests de :mod:`dcf_app.valuation.forecast`."""

from __future__ import annotations

import math

import pytest

from dcf_app.valuation.forecast import (
    ForecastResult,
    build_forecast,
    project_capex,
    project_da,
    project_delta_nwc,
    project_ebit,
    project_ebit_margin,
    project_fcff,
    project_nopat,
    project_revenue,
)

# ---------------------------------------------------------------------------
# project_revenue
# ---------------------------------------------------------------------------


def test_project_revenue_single_year() -> None:
    """Un solo año: growth = g_inicial."""
    result = project_revenue(100.0, 0.10, 0.03, 1)
    assert len(result) == 1
    assert math.isclose(result[0], 110.0)


def test_project_revenue_two_years_fade() -> None:
    """Fade lineal: año 1 = g_inicial, año 2 = g_terminal."""
    result = project_revenue(100.0, 0.10, 0.03, 2)
    assert len(result) == 2
    # Año 1: 100 * 1.10 = 110
    assert math.isclose(result[0], 110.0)
    # Año 2: 110 * 1.03 = 113.3
    assert math.isclose(result[1], 113.3)


def test_project_revenue_five_years_fade() -> None:
    """Fade lineal en 5 años: g_0=10%, g_4=3%."""
    result = project_revenue(100.0, 0.10, 0.03, 5)
    assert len(result) == 5
    # g_0 = 0.10, g_1 = 0.0825, g_2 = 0.065, g_3 = 0.0475, g_4 = 0.03
    # Year 1: 100 * 1.10 = 110
    assert math.isclose(result[0], 110.0)
    # Year 2: 110 * 1.0825 = 119.075
    assert math.isclose(result[1], 119.075)
    # Year 5: 100 * 1.10 * 1.0825 * 1.065 * 1.0475 * 1.03
    expected_y5 = 100.0 * 1.10 * 1.0825 * 1.065 * 1.0475 * 1.03
    assert math.isclose(result[4], expected_y5)


def test_project_revenue_zero_horizon() -> None:
    """Horizonte 0 → lista vacía."""
    assert project_revenue(100.0, 0.10, 0.03, 0) == []


def test_project_revenue_negative_growth() -> None:
    """Crecimiento negativo (declive)."""
    result = project_revenue(100.0, -0.05, 0.02, 3)
    assert len(result) == 3
    # Año 1: 100 * 0.95 = 95
    assert math.isclose(result[0], 95.0)
    # Año 2: 95 * (1-0.015) = 93.575
    assert math.isclose(result[1], 93.575)
    # Año 3: 93.575 * (1+0.02) = 95.4465 (recupera por el fade positivo)
    assert math.isclose(result[2], 95.4465)


def test_project_revenue_constant_growth() -> None:
    """Si g_inicial = g_terminal, crecimiento constante."""
    result = project_revenue(100.0, 0.05, 0.05, 4)
    for i in range(1, 4):
        assert math.isclose(result[i] / result[i - 1], 1.05)


# ---------------------------------------------------------------------------
# project_ebit_margin
# ---------------------------------------------------------------------------


def test_project_ebit_margin_single_year() -> None:
    """Un solo año: margen = actual."""
    result = project_ebit_margin(0.15, 0.20, 1)
    assert len(result) == 1
    assert math.isclose(result[0], 0.15)


def test_project_ebit_margin_convergence() -> None:
    """Convergencia lineal en 5 años."""
    result = project_ebit_margin(0.15, 0.25, 5)
    assert len(result) == 5
    # Año 1: 0.15 (actual)
    assert math.isclose(result[0], 0.15)
    # Año 5: 0.25 (target)
    assert math.isclose(result[4], 0.25)
    # Monotonía creciente
    for i in range(1, 5):
        assert result[i] > result[i - 1]


def test_project_ebit_margin_zero_horizon() -> None:
    """Horizonte 0 → lista vacía."""
    assert project_ebit_margin(0.15, 0.20, 0) == []


def test_project_ebit_margin_no_change() -> None:
    """Si actual = target, margen constante."""
    result = project_ebit_margin(0.20, 0.20, 4)
    for m in result:
        assert math.isclose(m, 0.20)


# ---------------------------------------------------------------------------
# project_ebit
# ---------------------------------------------------------------------------


def test_project_ebit() -> None:
    """EBIT = Revenue × Margen."""
    revenue = [100.0, 110.0]
    margin = [0.20, 0.22]
    result = project_ebit(revenue, margin)
    assert math.isclose(result[0], 20.0)
    assert math.isclose(result[1], 24.2)


def test_project_ebit_length_mismatch() -> None:
    """Longitudes distintas → ValueError."""
    with pytest.raises(ValueError, match="Longitudes distintas"):
        project_ebit([100.0], [0.20, 0.22])


# ---------------------------------------------------------------------------
# project_nopat
# ---------------------------------------------------------------------------


def test_project_nopat() -> None:
    """NOPAT = EBIT × (1 − t)."""
    ebit = [20.0, 24.2]
    result = project_nopat(ebit, 0.21)
    assert math.isclose(result[0], 20.0 * 0.79)
    assert math.isclose(result[1], 24.2 * 0.79)


# ---------------------------------------------------------------------------
# project_da
# ---------------------------------------------------------------------------


def test_project_da() -> None:
    """D&A = Revenue × %D&A."""
    revenue = [100.0, 110.0]
    result = project_da(revenue, 0.05)
    assert math.isclose(result[0], 5.0)
    assert math.isclose(result[1], 5.5)


# ---------------------------------------------------------------------------
# project_capex
# ---------------------------------------------------------------------------


def test_project_capex() -> None:
    """CapEx = Revenue × %CapEx."""
    revenue = [100.0, 110.0]
    result = project_capex(revenue, 0.06)
    assert math.isclose(result[0], 6.0)
    assert math.isclose(result[1], 6.6)


# ---------------------------------------------------------------------------
# project_delta_nwc
# ---------------------------------------------------------------------------


def test_project_delta_nwc_with_base() -> None:
    """ΔNWC = (Revenue_t − Revenue_{t−1}) × %NWC, con base."""
    revenue = [110.0, 121.0]
    result = project_delta_nwc(revenue, 0.10, base_revenue=100.0)
    # Año 1: (110 - 100) * 0.10 = 1.0
    assert math.isclose(result[0], 1.0)
    # Año 2: (121 - 110) * 0.10 = 1.1
    assert math.isclose(result[1], 1.1)


def test_project_delta_nwc_without_base() -> None:
    """Sin base_revenue, se asume Revenue_{−1} = 0."""
    revenue = [110.0, 121.0]
    result = project_delta_nwc(revenue, 0.10)
    # Año 1: (110 - 0) * 0.10 = 11.0
    assert math.isclose(result[0], 11.0)
    # Año 2: (121 - 110) * 0.10 = 1.1
    assert math.isclose(result[1], 1.1)


def test_project_delta_nwc_empty() -> None:
    """Lista vacía → lista vacía."""
    assert project_delta_nwc([], 0.10) == []


# ---------------------------------------------------------------------------
# project_fcff
# ---------------------------------------------------------------------------


def test_project_fcff_hand_calculated() -> None:
    """FCFF calculado a mano para un caso simple de 1 año."""
    # Revenue=100, margin=0.20, tax=0.21, D&A=5%, CapEx=6%, NWC=10%, base=90
    revenue = [100.0]
    margin = [0.20]
    fcff = project_fcff(revenue, margin, 0.21, 0.05, 0.06, 0.10, base_revenue=90.0)
    # EBIT = 100 * 0.20 = 20
    # NOPAT = 20 * 0.79 = 15.8
    # D&A = 100 * 0.05 = 5
    # CapEx = 100 * 0.06 = 6
    # ΔNWC = (100 - 90) * 0.10 = 1.0
    # FCFF = 15.8 + 5 - 6 - 1.0 = 13.8
    assert math.isclose(fcff[0], 13.8)


def test_project_fcff_length_mismatch() -> None:
    """Longitudes distintas entre revenue y margin → ValueError."""
    with pytest.raises(ValueError, match="Longitudes distintas"):
        project_fcff([100.0, 110.0], [0.20], 0.21, 0.05, 0.06, 0.10)


# ---------------------------------------------------------------------------
# build_forecast
# ---------------------------------------------------------------------------


def test_build_forecast_structure() -> None:
    """build_forecast devuelve un ForecastResult con todas las listas."""
    result = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.20,
        margin_target=0.25,
        tax_rate=0.21,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=3,
        base_revenue=95.0,
    )
    assert isinstance(result, ForecastResult)
    assert len(result.revenue) == 3
    assert len(result.ebit_margin) == 3
    assert len(result.ebit) == 3
    assert len(result.nopat) == 3
    assert len(result.da) == 3
    assert len(result.capex) == 3
    assert len(result.delta_nwc) == 3
    assert len(result.fcff) == 3


def test_build_forecast_consistency() -> None:
    """Las listas de build_forecast son consistentes entre sí."""
    result = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.20,
        margin_target=0.25,
        tax_rate=0.21,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=3,
        base_revenue=95.0,
    )
    # EBIT = Revenue × Margen
    for r, m, e in zip(result.revenue, result.ebit_margin, result.ebit, strict=False):
        assert math.isclose(e, r * m)
    # NOPAT = EBIT × (1 − t)
    for e, n in zip(result.ebit, result.nopat, strict=False):
        assert math.isclose(n, e * 0.79)
    # FCFF = NOPAT + D&A − CapEx − ΔNWC
    for n, d, c, w, f in zip(
        result.nopat, result.da, result.capex, result.delta_nwc, result.fcff, strict=False
    ):
        assert math.isclose(f, n + d - c - w)


def test_build_forecast_no_base_revenue() -> None:
    """Sin base_revenue, se asume Revenue_{−1} = 0."""
    result = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.20,
        margin_target=0.25,
        tax_rate=0.21,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=3,
    )
    # Año 1: ΔNWC = (110 - 0) * 0.10 = 11.0
    assert math.isclose(result.delta_nwc[0], result.revenue[0] * 0.10)


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------


def test_revenue_monotonic_with_positive_growth() -> None:
    """Mayor crecimiento inicial → mayores ingresos (ceteris paribus)."""
    r1 = project_revenue(100.0, 0.05, 0.03, 5)
    r2 = project_revenue(100.0, 0.10, 0.03, 5)
    for a, b in zip(r1, r2, strict=False):
        assert b >= a


def test_fcff_monotonic_with_higher_margin() -> None:
    """Mayor margen objetivo → mayor FCFF (ceteris paribus)."""
    f1 = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.15,
        margin_target=0.20,
        tax_rate=0.21,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=5,
    )
    f2 = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.15,
        margin_target=0.25,
        tax_rate=0.21,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=5,
    )
    for a, b in zip(f1.fcff, f2.fcff, strict=False):
        assert b >= a


def test_fcff_monotonic_with_lower_tax() -> None:
    """Menor tasa impositiva → mayor FCFF (ceteris paribus)."""
    f1 = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.20,
        margin_target=0.25,
        tax_rate=0.30,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=5,
    )
    f2 = build_forecast(
        initial_revenue=100.0,
        growth_initial=0.10,
        growth_terminal=0.03,
        margin_current=0.20,
        margin_target=0.25,
        tax_rate=0.15,
        da_pct=0.05,
        capex_pct=0.06,
        nwc_pct=0.10,
        horizon=5,
    )
    for a, b in zip(f1.fcff, f2.fcff, strict=False):
        assert b >= a
