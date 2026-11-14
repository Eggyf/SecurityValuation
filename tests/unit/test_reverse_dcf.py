"""Tests de :mod:`dcf_app.valuation.reverse_dcf`."""

from __future__ import annotations

import math

import pytest

from dcf_app.models.assumptions import Assumptions
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf
from dcf_app.valuation.reverse_dcf import (
    reverse_dcf_growth,
    reverse_dcf_margin,
)


def _make_fact(value: float, unit: str = "USD") -> Fact:
    return Fact(
        value=value,
        unit=unit,
        scale=Scale.MILLIONS,
        period_start=None,
        period_end=__import__("datetime").date(2026, 12, 31),
        source=SourceRef(kind=SourceKind.TEXT_FALLBACK, location="test"),
    )


def _make_financials() -> FinancialStatements:
    """Crea estados financieros de ejemplo."""
    income = IncomeStatement(
        fiscal_year=2026,
        period_start=__import__("datetime").date(2026, 1, 1),
        period_end=__import__("datetime").date(2026, 12, 31),
        revenue=_make_fact(1000.0),
        ebit=_make_fact(250.0),
        net_income=_make_fact(200.0),
        diluted_eps=_make_fact(2.0, "USD_per_share"),
        diluted_weighted_shares=_make_fact(100.0, "shares"),
        depreciation_amortization=_make_fact(50.0),
    )
    balance = BalanceSheet(
        fiscal_year=2026,
        period_end=__import__("datetime").date(2026, 12, 31),
        cash_and_equivalents=_make_fact(100.0),
        total_assets=_make_fact(2000.0),
        total_liabilities=_make_fact(800.0),
        total_equity=_make_fact(1200.0),
        short_term_debt=_make_fact(50.0),
        long_term_debt=_make_fact(200.0),
    )
    cashflow = CashFlowStatement(
        fiscal_year=2026,
        period_start=__import__("datetime").date(2026, 1, 1),
        period_end=__import__("datetime").date(2026, 12, 31),
        cfo=_make_fact(300.0),
        capex=_make_fact(-100.0),
        depreciation_amortization=_make_fact(50.0),
        sbc=_make_fact(20.0),
    )
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=[income],
        balance_sheets=[balance],
        cash_flow_statements=[cashflow],
    )


def _make_assumptions() -> Assumptions:
    """Crea supuestos de ejemplo."""
    return Assumptions(
        company_name="Test Corp",
        fiscal_year_end=__import__("datetime").date(2026, 12, 31),
        valuation_date=__import__("datetime").date(2026, 12, 31),
        forecast_horizon=5,
        initial_revenue_growth=0.10,
        terminal_revenue_growth=0.025,
        ebit_margin_target=0.25,
        risk_free_rate=0.04,
        equity_beta=1.0,
        equity_risk_premium=0.05,
        market_equity_value=1000.0,
        market_debt_value=250.0,
        cost_of_debt=0.05,
        tax_rate=0.21,
        stock_price_current=10.0,
        shares_outstanding=100.0,
    )


class TestReverseDCFGrowth:
    """Tests para reverse_dcf_growth."""

    def test_round_trip(self) -> None:
        """Round-trip: generar precio con parámetros conocidos y recuperarlos."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        # Ejecutar DCF para obtener precio del modelo
        result = run_dcf(assumptions, financials)
        model_price = result.price_per_share

        if model_price <= 0:
            pytest.skip("El modelo da precio no positivo con estos supuestos")

        # Reverse DCF debería recuperar el crecimiento inicial
        r = reverse_dcf_growth(assumptions, financials, model_price)
        assert r.has_solution
        assert r.implied_value is not None
        assert math.isclose(r.implied_value, assumptions.initial_revenue_growth, abs_tol=1e-4)

    def test_no_solution_high_price(self) -> None:
        """Sin solución cuando el precio de mercado es muy alto."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        # Precio muy alto → sin solución en el rango
        r = reverse_dcf_growth(assumptions, financials, 1e6)
        assert not r.has_solution
        assert r.implied_value is None
        assert "descuenta" in r.message.lower() or "sin solución" in r.message.lower()

    def test_no_solution_negative_price(self) -> None:
        """Precio negativo → error."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        r = reverse_dcf_growth(assumptions, financials, -10.0)
        assert not r.has_solution
        assert "positivo" in r.message.lower()

    def test_monotonicity(self) -> None:
        """Mayor crecimiento implícito → mayor precio de mercado."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        # Ejecutar con dos precios diferentes
        result_low = run_dcf(assumptions, financials)
        if result_low.price_per_share <= 0:
            pytest.skip("Precio del modelo no positivo")

        # Precio más alto → crecimiento implícito mayor
        r_low = reverse_dcf_growth(assumptions, financials, result_low.price_per_share * 0.5)
        r_high = reverse_dcf_growth(assumptions, financials, result_low.price_per_share * 1.5)

        if r_low.has_solution and r_high.has_solution:
            assert r_low.implied_value < r_high.implied_value

    def test_historical_comparison(self) -> None:
        """El resultado incluye comparación histórica."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        result = run_dcf(assumptions, financials)
        if result.price_per_share <= 0:
            pytest.skip("Precio del modelo no positivo")

        r = reverse_dcf_growth(assumptions, financials, result.price_per_share)
        if r.has_solution:
            assert r.historical_comparison is not None


class TestReverseDCFMargins:
    """Tests para reverse_dcf_margin."""

    def test_round_trip(self) -> None:
        """Round-trip: generar precio con margen conocido y recuperarlo."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        result = run_dcf(assumptions, financials)
        model_price = result.price_per_share

        if model_price <= 0:
            pytest.skip("El modelo da precio no positivo con estos supuestos")

        r = reverse_dcf_margin(assumptions, financials, model_price)
        assert r.has_solution
        assert r.implied_value is not None
        assert math.isclose(r.implied_value, assumptions.ebit_margin_target, abs_tol=1e-4)

    def test_no_solution_high_price(self) -> None:
        """Sin solución cuando el precio de mercado es muy alto."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        r = reverse_dcf_margin(assumptions, financials, 1e6)
        assert not r.has_solution
        assert r.implied_value is None

    def test_no_solution_negative_price(self) -> None:
        """Precio negativo → error."""
        financials = _make_financials()
        assumptions = _make_assumptions()

        r = reverse_dcf_margin(assumptions, financials, -10.0)
        assert not r.has_solution
        assert "positivo" in r.message.lower()
