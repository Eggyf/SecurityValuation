"""Tests de :mod:`dcf_app.models.assumptions`."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from dcf_app.models.assumptions import (
    Assumptions,
    DCFResult,
    DiscountConvention,
    GrowthMethod,
    Scenario,
    TerminalValueMethod,
)


def test_assumptions_minimal_valid() -> None:
    """Assumptions mínimas válidas."""
    assumptions = Assumptions(
        company_name="Acme Corp",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
    )
    assert assumptions.company_name == "Acme Corp"
    assert assumptions.scenario is Scenario.BASE
    assert assumptions.forecast_horizon == 5
    assert assumptions.growth_method is GrowthMethod.FADE_LINEAR
    assert assumptions.terminal_value_method is TerminalValueMethod.GORDON_GROWTH
    assert assumptions.discount_convention is DiscountConvention.END_OF_YEAR


def test_assumptions_growth_constraints() -> None:
    """Valida que g_terminal ≤ Rf."""
    # Caso válido
    Assumptions(
        company_name="Acme",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
        terminal_revenue_growth=0.02,
        risk_free_rate=0.03,
    )
    # Caso inválido: g > Rf (la validación de pydantic lo capta antes)
    with pytest.raises(PydanticValidationError, match=r"less than or equal to 0\.025"):
        Assumptions(
            company_name="Acme",
            fiscal_year_end="2024-12-31",
            valuation_date="2024-12-31",
            terminal_revenue_growth=0.04,
            risk_free_rate=0.03,
        )


def test_assumptions_growth_bounds() -> None:
    """Valida los límites de los porcentajes."""
    # Crecimiento inicial fuera de rango
    with pytest.raises(PydanticValidationError, match="greater than or equal to -0.05"):
        Assumptions(
            company_name="Acme",
            fiscal_year_end="2024-12-31",
            valuation_date="2024-12-31",
            initial_revenue_growth=-0.06,
        )
    with pytest.raises(PydanticValidationError, match=r"less than or equal to 0\.25"):
        Assumptions(
            company_name="Acme",
            fiscal_year_end="2024-12-31",
            valuation_date="2024-12-31",
            initial_revenue_growth=0.26,
        )


def test_wacc_property() -> None:
    """Prueba la propiedad calculada wacc."""
    assumptions = Assumptions(
        company_name="Acme",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
    )
    assert assumptions.wacc is None
    assumptions.wacc = 0.08  # type: ignore[attr-defined]
    assert assumptions.wacc == 0.08


def test_dcf_result_minimal_valid() -> None:
    """DCFResult mínima válida."""
    assumptions = Assumptions(
        company_name="Acme",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
    )
    result = DCFResult(
        assumptions=assumptions,
        forecast_years=[2025, 2026, 2027],
        revenue_forecast=[100.0, 110.0, 121.0],
        ebit_forecast=[20.0, 22.0, 24.2],
        nopat_forecast=[16.0, 17.6, 19.36],
        fcff_forecast=[10.0, 11.0, 12.1],
        capex_forecast=[5.0, 5.5, 6.05],
        delta_nwc_forecast=[1.0, 1.1, 1.21],
        terminal_value=100.0,
        terminal_value_method=TerminalValueMethod.GORDON_GROWTH,
        enterprise_value=150.0,
        equity_value=140.0,
        price_per_share=14.0,
        tv_percentage=0.6667,
    )
    assert result.assumptions is assumptions
    assert result.forecast_years == [2025, 2026, 2027]
    assert result.enterprise_value == 150.0
    assert result.price_per_share == 14.0
    assert result.is_reasonable is True  # TV < 75% EV, precios positivos


def test_dcf_result_unreasonable() -> None:
    """DCFResult no razonable (TV > 75% EV)."""
    assumptions = Assumptions(
        company_name="Acme",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
    )
    result = DCFResult(
        assumptions=assumptions,
        forecast_years=[2025],
        revenue_forecast=[100.0],
        ebit_forecast=[20.0],
        nopat_forecast=[16.0],
        fcff_forecast=[10.0],
        capex_forecast=[5.0],
        delta_nwc_forecast=[1.0],
        terminal_value=200.0,  # TV muy grande
        terminal_value_method=TerminalValueMethod.GORDON_GROWTH,
        enterprise_value=210.0,
        equity_value=200.0,
        price_per_share=20.0,
        tv_percentage=0.9524,  # > 75%
    )
    assert result.is_reasonable is False


def test_dcf_result_negative_prices() -> None:
    """DCFResult con precios negativos (no razonable)."""
    assumptions = Assumptions(
        company_name="Acme",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
    )
    result = DCFResult(
        assumptions=assumptions,
        forecast_years=[2025],
        revenue_forecast=[100.0],
        ebit_forecast=[20.0],
        nopat_forecast=[16.0],
        fcff_forecast=[10.0],
        capex_forecast=[5.0],
        delta_nwc_forecast=[1.0],
        terminal_value=100.0,
        terminal_value_method=TerminalValueMethod.GORDON_GROWTH,
        enterprise_value=110.0,
        equity_value=100.0,
        price_per_share=-10.0,  # precio negativo
        tv_percentage=0.9091,
    )
    assert result.is_reasonable is False


def test_scenarios_enum() -> None:
    """Valores del enum Scenario."""
    assert Scenario.BASE == "base"
    assert Scenario.BULL == "bull"
    assert Scenario.BEAR == "bear"


def test_growth_methods_enum() -> None:
    """Valores del enum GrowthMethod."""
    assert GrowthMethod.HISTORICAL_CAGR == "historical_cagr"
    assert GrowthMethod.USER_INPUT == "user_input"
    assert GrowthMethod.FADE_LINEAR == "fade_linear"


def test_terminal_value_methods_enum() -> None:
    """Valores del enum TerminalValueMethod."""
    assert TerminalValueMethod.GORDON_GROWTH == "gordon_growth"
    assert TerminalValueMethod.MULTIPLE == "multiple"


def test_discount_convention_enum() -> None:
    """Valores del enum DiscountConvention."""
    assert DiscountConvention.END_OF_YEAR == "end_of_year"
    assert DiscountConvention.MID_YEAR == "mid_year"
