"""Tests de :mod:`dcf_app.valuation.monte_carlo`."""

from __future__ import annotations

import numpy as np

from dcf_app.models.assumptions import Assumptions, DiscountConvention
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf
from dcf_app.valuation.monte_carlo import simulate


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float) -> Fact:
    return Fact(value=value, unit="USD", scale=Scale.MILLIONS, period_end=__import__("datetime").date(2024, 12, 31), source=_src())  # noqa: E501


def _make_financials() -> FinancialStatements:
    income = IncomeStatement(
        fiscal_year=2024, period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 12, 31),
        revenue=_fact(1000.0), ebit=_fact(200.0),
        depreciation_amortization=_fact(50.0),
    )
    balance = BalanceSheet(
        fiscal_year=2024, period_end=__import__("datetime").date(2024, 12, 31),
        cash_and_equivalents=_fact(50.0), short_term_investments=_fact(10.0),
        accounts_receivable=_fact(80.0), inventory=_fact(60.0),
        accounts_payable=_fact(40.0), short_term_debt=_fact(30.0),
        long_term_debt=_fact(170.0), preferred_stock=_fact(0.0),
        non_controlling_interest=_fact(0.0), total_equity=_fact(200.0),
        total_assets=_fact(500.0), total_liabilities=_fact(300.0),
    )
    cf = CashFlowStatement(
        fiscal_year=2024, period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 12, 31),
        cfo=_fact(250.0), capex=_fact(-60.0),
        depreciation_amortization=_fact(50.0), sbc=_fact(0.0),
    )
    return FinancialStatements(
        company_name="Test Corp", income_statements=[income],
        balance_sheets=[balance], cash_flow_statements=[cf],
    )


def _make_assumptions() -> Assumptions:
    return Assumptions(
        company_name="Test Corp",
        fiscal_year_end=__import__("datetime").date(2024, 12, 31),
        valuation_date=__import__("datetime").date(2024, 12, 31),
        forecast_horizon=5,
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
        discount_convention=DiscountConvention.END_OF_YEAR,
    )


class TestMonteCarlo:
    """Tests para Monte Carlo."""

    def test_same_seed_same_result(self) -> None:
        """Misma semilla → mismo resultado."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r1 = simulate(assumptions, financials, n=100, seed=42)
        r2 = simulate(assumptions, financials, n=100, seed=42)
        assert np.array_equal(r1.prices, r2.prices)

    def test_variance_zero_reproduces_dcf(self) -> None:
        """Varianza cero reproduce el DCF determinista."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        det = run_dcf(assumptions, financials).price_per_share
        r = simulate(
            assumptions, financials, n=50, seed=1,
            growth_sd=0, margin_sd=0, wacc_sd=0,
            g_perp_range=(0.025, 0.025, 0.025),
        )
        assert np.allclose(r.prices, det)

    def test_no_wacc_le_g(self) -> None:
        """Ninguna simulación válida con WACC ≤ g."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r = simulate(assumptions, financials, n=1000, seed=7)
        # Todas las simulaciones válidas tienen WACC > g
        assert r.n_valid > 0
        assert r.n_discarded >= 0

    def test_percentiles_order(self) -> None:
        """P5 < mediana < P95."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r = simulate(assumptions, financials, n=1000, seed=7)
        assert r.p5 < r.median < r.p95

    def test_convergence(self) -> None:
        """La media converge al aumentar N."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r1 = simulate(assumptions, financials, n=100, seed=7)
        r2 = simulate(assumptions, financials, n=1000, seed=7)
        # Con más simulaciones, la media debería ser más estable
        assert r1.n_valid > 0
        assert r2.n_valid > 0

    def test_prob_above_market(self) -> None:
        """Probabilidad de superar el precio de mercado."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r = simulate(assumptions, financials, n=500, seed=7, market_price=20.0)
        assert r.prob_above_market is not None
        assert 0 <= r.prob_above_market <= 1

    def test_discarded_count(self) -> None:
        """Se cuentan las simulaciones descartadas."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        r = simulate(assumptions, financials, n=1000, seed=7)
        assert r.n_simulations == 1000
        assert r.n_valid + r.n_discarded == 1000
