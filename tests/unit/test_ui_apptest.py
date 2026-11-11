"""Smoke tests de la UI con streamlit AppTest (AGENTS.md §5, §12).

Comprueban que la app renderiza sin excepciones con datos en sesion, que
los defaults se pre-rellenan desde el 10-K y que el boton de descarga del
Excel aparece tras ejecutar el DCF.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dcf_app.models.assumptions import Assumptions, DiscountConvention
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf

APP = Path(__file__).resolve().parents[2] / "src" / "dcf_app" / "ui" / "app.py"


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float) -> Fact:
    return Fact(
        value=value, unit="USD", scale=Scale.MILLIONS, period_end=date(2024, 12, 31), source=_src()
    )


def _make_financials() -> FinancialStatements:
    """Estados sinteticos 2022-2024 (revenue 800/900/1000, EBIT 20 %)."""
    incomes = [
        IncomeStatement(
            fiscal_year=year,
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            revenue=_fact(revenue),
            ebit=_fact(revenue * 0.2),
            income_tax_expense=_fact(_tax),
            pretax_income=_fact(_pretax),
        )
        for year, revenue, _tax, _pretax in [
            (2022, 800.0, 16.0, 80.0),
            (2023, 900.0, 18.0, 90.0),
            (2024, 1000.0, 20.0, 100.0),
        ]
    ]
    balances = [
        BalanceSheet(
            fiscal_year=year,
            period_end=date(year, 12, 31),
            cash_and_equivalents=_fact(50.0),
            short_term_investments=_fact(10.0),
            accounts_receivable=_fact(80.0),
            inventory=_fact(60.0),
            accounts_payable=_fact(40.0),
            short_term_debt=_fact(30.0),
            long_term_debt=_fact(170.0),
            total_equity=_fact(400.0),
        )
        for year in (2023, 2024)
    ]
    cashflows = [
        CashFlowStatement(
            fiscal_year=year,
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            cfo=_fact(250.0),
            capex=_fact(-60.0),
            depreciation_amortization=_fact(50.0),
        )
        for year in (2022, 2023, 2024)
    ]
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=incomes,
        balance_sheets=balances,
        cash_flow_statements=cashflows,
    )


def _make_assumptions() -> Assumptions:
    return Assumptions(
        company_name="Test Corp",
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
        discount_convention=DiscountConvention.END_OF_YEAR,
    )


def test_app_renders_empty() -> None:
    """Sin datos en sesion, la app renderiza las 4 pestanas sin excepciones."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()

    assert not at.exception
    assert len(at.tabs) == 4
    assert len(at.download_button) == 0


def test_app_prefills_defaults_from_10k() -> None:
    """Con un 10-K en sesion, los widgets muestran los defaults sugeridos.

    El caption del crecimiento debe citar el CAGR del historico
    (800 -> 1000 en 2 anos: 11.8 %), no un valor inventado.
    """
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.session_state["financials"] = _make_financials()
    at.run()

    assert not at.exception
    captions = [c.value for c in at.caption]
    assert any("CAGR FY2022" in text and "11.8%" in text for text in captions)


def test_app_renders_result_with_excel_download() -> None:
    """Tras ejecutar el DCF, la pestana 4 ofrece la descarga del Excel."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    financials = _make_financials()
    assumptions = _make_assumptions()
    result = run_dcf(assumptions, financials)
    at.session_state["financials"] = financials
    at.session_state["assumptions"] = assumptions
    at.session_state["dcf_result"] = result
    at.session_state["dcf_assumptions"] = assumptions
    at.run()

    assert not at.exception
    assert len(at.download_button) == 1
    assert "Descargar informe Excel" in at.download_button[0].label
