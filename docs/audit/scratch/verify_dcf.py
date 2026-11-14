"""Verificación independiente del motor DCF contra vectores de verificación."""

from __future__ import annotations

import math
from datetime import date

from dcf_app.models.assumptions import Assumptions, DiscountConvention, TerminalValueMethod
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float) -> Fact:
    return Fact(value=value, unit="USD", scale=Scale.MILLIONS, period_end=date(2024, 12, 31), source=_src())


def make_financials(revenue: float = 1000.0, ebit_margin: float = 0.20) -> FinancialStatements:
    """Crea financials que producen las métricas del vector de verificación."""
    # Para que el motor extraiga revenue=1000, ebit_margin=0.20, da_pct=0.04, etc.
    # Necesitamos al menos 1 income statement y 1 balance
    income = IncomeStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        revenue=_fact(revenue),
        ebit=_fact(revenue * ebit_margin),
        depreciation_amortization=_fact(revenue * 0.04),  # D&A 4%
    )
    balance = BalanceSheet(
        fiscal_year=2024,
        period_end=date(2024, 12, 31),
        cash_and_equivalents=_fact(150.0),
        short_term_investments=_fact(0.0),
        accounts_receivable=_fact(80.0),  # para NWC
        inventory=_fact(60.0),
        accounts_payable=_fact(40.0),
        short_term_debt=_fact(0.0),
        long_term_debt=_fact(400.0),
        total_equity=_fact(1000.0),
        total_assets=_fact(2000.0),
        total_liabilities=_fact(1000.0),
    )
    cf = CashFlowStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        cfo=_fact(300.0),
        capex=_fact(-50.0),  # CapEx 5% of revenue
        depreciation_amortization=_fact(revenue * 0.04),
        sbc=_fact(0.0),
    )
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=[income],
        balance_sheets=[balance],
        cash_flow_statements=[cf],
    )


def make_assumptions() -> Assumptions:
    """Crea supuestos para el vector de verificación."""
    return Assumptions(
        company_name="Test Corp",
        fiscal_year_end=date(2024, 12, 31),
        valuation_date=date(2024, 12, 31),
        forecast_horizon=5,
        initial_revenue_growth=0.10,
        terminal_revenue_growth=0.025,
        ebit_margin_target=0.20,
        risk_free_rate=0.0425,
        equity_beta=1.0,
        equity_risk_premium=0.05,
        market_equity_value=3000.0,
        market_debt_value=1000.0,
        cost_of_debt=0.05,
        tax_rate=0.21,
        stock_price_current=20.0,
        shares_outstanding=100.0,
        discount_convention=DiscountConvention.END_OF_YEAR,
        terminal_value_method=TerminalValueMethod.GORDON_GROWTH,
        # roic_terminal = wacc (default, conservador)
    )


if __name__ == "__main__":
    financials = make_financials()
    assumptions = make_assumptions()
    result = run_dcf(assumptions, financials)

    print(f"Revenue forecast: {[round(x, 1) for x in result.revenue_forecast]}")
    print(f"FCFF: {[round(x, 1) for x in result.fcff_forecast]}")
    print(f"EV: {result.enterprise_value:.1f}")
    print(f"Equity: {result.equity_value:.1f}")
    print(f"Price: {result.price_per_share:.2f}")
    print(f"TV: {result.terminal_value:.1f}")
    print(f"TV%: {result.tv_percentage:.1%}")
    print(f"Upside: {result.upside_downside}")
    print(f"Reinvestment rate: {result.reinvestment_rate}")