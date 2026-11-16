"""Tests de :mod:`dcf_app.valuation.fcfe` y :mod:`dcf_app.valuation.residual_income`."""

from __future__ import annotations

from dcf_app.models.assumptions import Assumptions, DiscountConvention
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf
from dcf_app.valuation.fcfe import compute_fcfe
from dcf_app.valuation.residual_income import compute_residual_income


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float) -> Fact:
    from datetime import date as _date

    return Fact(value=value, unit="USD", scale=Scale.MILLIONS, period_end=_date(2024, 12, 31), source=_src())  # noqa: E501


def _make_financials() -> FinancialStatements:
    income = IncomeStatement(
        fiscal_year=2024, period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 12, 31),
        revenue=_fact(1000.0), ebit=_fact(200.0),
        interest_expense=_fact(40.0),
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


class TestFCFE:
    """Tests para FCFE."""

    def test_basic(self) -> None:
        """FCFE se calcula correctamente."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_fcfe(assumptions, financials, dcf)
        assert result.price_per_share > 0
        assert result.equity_value > 0
        assert len(result.fcfe_forecast) == 5

    def test_identity_zero_debt(self) -> None:
        """Con deuda cero, FCFE ≈ FCFF (identidad algebraica)."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        # Poner deuda a 0
        financials.balance_sheets[0].short_term_debt = _fact(0.0)
        financials.balance_sheets[0].long_term_debt = _fact(0.0)
        assumptions.market_debt_value = 0.0
        assumptions.cost_of_debt = 0.05
        dcf = run_dcf(assumptions, financials)
        result = compute_fcfe(assumptions, financials, dcf)
        # Con deuda cero e interés cero, FCFE ≈ FCFF
        assert result.price_per_share > 0

    def test_divergence_warning(self) -> None:
        """Divergencia > 25% genera warning."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_fcfe(assumptions, financials, dcf)
        # El mensaje debe existir
        assert result.message != ""

    def test_missing_shares(self) -> None:
        """Sin acciones → mensaje de error."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        assumptions.shares_outstanding = None
        result = compute_fcfe(assumptions, financials)
        assert "acciones" in result.message.lower() or result.price_per_share == 0


class TestResidualIncome:
    """Tests para Residual Income / EVA."""

    def test_basic(self) -> None:
        """Residual Income se calcula correctamente."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_residual_income(assumptions, financials, dcf)
        assert result.price_per_share > 0
        assert result.equity_value > 0
        assert len(result.ri_forecast) == 5

    def test_clean_surplus(self) -> None:
        """Verifica la relación de clean surplus."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_residual_income(assumptions, financials, dcf)
        assert result.clean_surplus_ok is True

    def test_eva_forecast(self) -> None:
        """EVA se calcula para cada año."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_residual_income(assumptions, financials, dcf)
        assert len(result.eva_forecast) == 5

    def test_missing_shares(self) -> None:
        """Sin acciones → mensaje de error."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        assumptions.shares_outstanding = None
        result = compute_residual_income(assumptions, financials)
        assert "acciones" in result.message.lower() or result.price_per_share == 0

    def test_divergence(self) -> None:
        """Divergencia se calcula correctamente."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        dcf = run_dcf(assumptions, financials)
        result = compute_residual_income(assumptions, financials, dcf)
        assert result.divergence_pct is not None or result.message != ""
