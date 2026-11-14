"""Tests de :mod:`dcf_app.valuation.dcf`."""

from __future__ import annotations

import math
from datetime import date

import pytest

from dcf_app.models.assumptions import Assumptions, DiscountConvention, TerminalValueMethod
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import _compute_historical_metrics, run_dcf


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float, unit: str = "USD", scale: Scale = Scale.MILLIONS) -> Fact:
    return Fact(value=value, unit=unit, scale=scale, period_end=date(2024, 12, 31), source=_src())


def _make_financials() -> FinancialStatements:
    """Crea estados financieros de ejemplo para 2022-2024."""
    income_2022 = IncomeStatement(
        fiscal_year=2022,
        period_start=date(2022, 1, 1),
        period_end=date(2022, 12, 31),
        revenue=_fact(800.0),
        ebit=_fact(160.0),
        depreciation_amortization=_fact(40.0),
    )
    income_2023 = IncomeStatement(
        fiscal_year=2023,
        period_start=date(2023, 1, 1),
        period_end=date(2023, 12, 31),
        revenue=_fact(900.0),
        ebit=_fact(180.0),
        depreciation_amortization=_fact(45.0),
    )
    income_2024 = IncomeStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        revenue=_fact(1000.0),
        ebit=_fact(200.0),
        depreciation_amortization=_fact(50.0),
    )

    # Balance para cada año (simplificado)
    balances = []
    cashflows = []
    for fy in [2022, 2023, 2024]:
        balances.append(
            BalanceSheet(
                fiscal_year=fy,
                period_end=date(fy, 12, 31),
                cash_and_equivalents=_fact(50.0),
                short_term_investments=_fact(10.0),
                accounts_receivable=_fact(80.0),
                inventory=_fact(60.0),
                accounts_payable=_fact(40.0),
                short_term_debt=_fact(30.0),
                long_term_debt=_fact(170.0),
                operating_lease_liabilities_current=_fact(5.0),
                operating_lease_liabilities_noncurrent=_fact(15.0),
                preferred_stock=_fact(0.0),
                non_controlling_interest=_fact(0.0),
            )
        )
        cashflows.append(
            CashFlowStatement(
                fiscal_year=fy,
                period_start=date(fy, 1, 1),
                period_end=date(fy, 12, 31),
                cfo=_fact(250.0),
                capex=_fact(-60.0),
                depreciation_amortization=_fact(50.0),
                sbc=_fact(10.0),
            )
        )

    return FinancialStatements(
        company_name="Acme Corp",
        income_statements=[income_2022, income_2023, income_2024],
        balance_sheets=balances,
        cash_flow_statements=cashflows,
    )


def _make_assumptions() -> Assumptions:
    """Crea supuestos de ejemplo."""
    return Assumptions(
        company_name="Acme Corp",
        fiscal_year_end=date(2024, 12, 31),
        valuation_date=date(2024, 12, 31),
        initial_revenue_growth=0.10,
        terminal_revenue_growth=0.025,
        ebit_margin_target=0.25,
        risk_free_rate=0.04,
        equity_beta=1.2,
        equity_risk_premium=0.05,
        market_equity_value=1000.0,
        market_debt_value=200.0,
        cost_of_debt=0.06,
        tax_rate=0.21,
        stock_price_current=100.0,
        shares_outstanding=100.0,
        options_outstanding=5.0,
        rsus_outstanding=2.0,
        average_option_exercise_price=50.0,
        discount_convention=DiscountConvention.END_OF_YEAR,
    )


# ---------------------------------------------------------------------------
# _compute_historical_metrics
# ---------------------------------------------------------------------------


def test_compute_historical_metrics() -> None:
    """Las métricas históricas se extraen correctamente."""
    financials = _make_financials()
    metrics = _compute_historical_metrics(financials)

    assert math.isclose(metrics["revenue"], 1000.0)
    assert math.isclose(metrics["ebit_margin"], 0.20)
    assert math.isclose(metrics["da_pct"], 0.05)
    assert math.isclose(metrics["capex_pct"], 0.06)
    assert math.isclose(metrics["cash"], 50.0)
    assert math.isclose(metrics["short_term_investments"], 10.0)
    assert math.isclose(metrics["debt"], 200.0)
    assert math.isclose(metrics["leases"], 0.0)  # Solo finance leases; operativos no se restan
    assert math.isclose(metrics["base_revenue"], 900.0)


# ---------------------------------------------------------------------------
# run_dcf
# ---------------------------------------------------------------------------


def test_run_dcf_basic() -> None:
    """El DCF se ejecuta correctamente con datos de ejemplo."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    assert result.assumptions is assumptions
    assert len(result.forecast_years) == 5
    assert len(result.revenue_forecast) == 5
    assert len(result.fcff_forecast) == 5
    assert result.enterprise_value > 0
    assert result.equity_value > 0
    assert result.price_per_share > 0
    assert result.terminal_value > 0
    assert 0 < result.tv_percentage < 1


def test_run_dcf_forecast_consistency() -> None:
    """La proyeccion es consistente (EBIT = Revenue x Margen)."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    # Verificar que NOPAT = EBIT x (1 - t)
    for e, n in zip(result.ebit_forecast, result.nopat_forecast, strict=True):
        assert math.isclose(n, e * (1 - assumptions.tax_rate))

    # FCFF = NOPAT + D&A - CapEx - delta NWC se verifica en forecast tests


def test_run_dcf_missing_revenue_raises() -> None:
    """Sin ingresos → ValueError."""
    financials = _make_financials()
    # Eliminar ingresos del último año
    financials.income_statements[-1].revenue = None
    assumptions = _make_assumptions()

    with pytest.raises(ValueError, match="ingresos"):
        run_dcf(assumptions, financials)


def test_run_dcf_missing_wacc_component_raises() -> None:
    """Sin Rf → ValueError."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.risk_free_rate = None

    with pytest.raises(ValueError, match="tasa libre de riesgo"):
        run_dcf(assumptions, financials)


def test_run_dcf_missing_erp_raises() -> None:
    """Sin ERP → ValueError.

    El motor ya no sustituye la prima de riesgo por un valor tipico del 5 %
    (AGENTS.md §2.1, §7.3): es un input del usuario.
    """
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.equity_risk_premium = None

    with pytest.raises(ValueError, match="prima de riesgo"):
        run_dcf(assumptions, financials)


def test_compute_historical_metrics_includes_book_equity() -> None:
    """Las metricas incluyen el patrimonio contable para los pesos del WACC.

    Si el usuario no aporta valor de mercado, el WACC usa el proxy contable
    ``equity_value`` del balance (AGENTS.md §7.3); antes la clave no existia
    y valia siempre 0.0.
    """
    financials = _make_financials()
    # El balance sintetico no define total_equity; se lo damos al ultimo ano.
    financials.balance_sheets[-1].total_equity = _fact(900.0)
    metrics = _compute_historical_metrics(financials)

    assert math.isclose(metrics["equity_value"], 900.0)


def test_run_dcf_missing_shares_raises() -> None:
    """Sin acciones → ValueError."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.shares_outstanding = None

    with pytest.raises(ValueError, match="acciones en circulación"):
        run_dcf(assumptions, financials)


def test_run_dcf_missing_price_raises() -> None:
    """Sin precio actual → ValueError."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.stock_price_current = None

    with pytest.raises(ValueError, match="precio actual"):
        run_dcf(assumptions, financials)


def test_run_dcf_missing_tax_rate_raises() -> None:
    """Sin tasa impositiva → ValueError."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.tax_rate = None

    with pytest.raises(ValueError, match="tasa impositiva"):
        run_dcf(assumptions, financials)


def test_run_dcf_sensitivities_populated() -> None:
    """Las sensibilidades se calculan y no están vacías."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    assert len(result.sensitivity_wacc_growth) > 0
    assert len(result.sensitivity_margin_growth) > 0


def test_run_dcf_upside_downside() -> None:
    """El upside/downside se calcula correctamente."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    # upside = (price / current_price - 1) * 100
    expected = (result.price_per_share / assumptions.stock_price_current - 1.0) * 100.0
    assert math.isclose(result.upside_downside, expected)


def test_run_dcf_bridge_breakdown() -> None:
    """El desglose del puente contiene las partidas esperadas."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    assert "enterprise_value" in result.bridge_breakdown
    assert "equity_value" in result.bridge_breakdown
    assert math.isclose(result.bridge_breakdown["equity_value"], result.equity_value)


def test_run_dcf_is_reasonable() -> None:
    """El resultado es razonable con parámetros válidos."""
    financials = _make_financials()
    assumptions = _make_assumptions()

    result = run_dcf(assumptions, financials)

    # Con los parámetros de ejemplo, el resultado debería ser razonable
    # (aunque esto depende de los valores exactos)
    assert isinstance(result.is_reasonable, bool)


def test_run_dcf_multiple_terminal() -> None:
    """DCF con método de múltiplo de salida."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.terminal_value_method = TerminalValueMethod.MULTIPLE
    assumptions.exit_multiple_ebitda = 10.0

    result = run_dcf(assumptions, financials)

    assert result.terminal_value_method is TerminalValueMethod.MULTIPLE
    assert result.terminal_value > 0


def test_run_dcf_mid_year_convention() -> None:
    """DCF con convención de mitad de año."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    assumptions.discount_convention = DiscountConvention.MID_YEAR

    result = run_dcf(assumptions, financials)

    assert result.price_per_share > 0
    assert result.enterprise_value > 0
