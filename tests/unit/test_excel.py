"""Tests de :mod:`dcf_app.export.excel`."""

from __future__ import annotations

import tempfile
from pathlib import Path

from dcf_app.export.excel import export_to_excel, export_to_excel_bytes
from dcf_app.models.assumptions import Assumptions, DiscountConvention
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
    from datetime import date

    return Fact(
        value=value, unit="USD", scale=Scale.MILLIONS, period_end=date(2024, 12, 31), source=_src()
    )


def _make_financials():
    from datetime import date

    income_2024 = IncomeStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        revenue=_fact(1000.0),
        ebit=_fact(200.0),
        depreciation_amortization=_fact(50.0),
    )
    balance = BalanceSheet(
        fiscal_year=2024,
        period_end=date(2024, 12, 31),
        cash_and_equivalents=_fact(50.0),
        short_term_investments=_fact(10.0),
        accounts_receivable=_fact(80.0),
        inventory=_fact(60.0),
        accounts_payable=_fact(40.0),
        short_term_debt=_fact(30.0),
        long_term_debt=_fact(170.0),
        preferred_stock=_fact(0.0),
        non_controlling_interest=_fact(0.0),
        total_equity=_fact(200.0),
        total_assets=_fact(500.0),
        total_liabilities=_fact(300.0),
    )
    cf = CashFlowStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        cfo=_fact(250.0),
        capex=_fact(-60.0),
        depreciation_amortization=_fact(50.0),
    )
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=[income_2024],
        balance_sheets=[balance],
        cash_flow_statements=[cf],
    )


def _make_assumptions():
    return Assumptions(
        company_name="Test Corp",
        fiscal_year_end="2024-12-31",
        valuation_date="2024-12-31",
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


def test_export_creates_file() -> None:
    """La exportación crea un archivo Excel."""
    financials = _make_financials()
    assumptions = _make_assumptions()
    result = run_dcf(assumptions, financials)

    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.xlsx"
        path = export_to_excel(result, financials, assumptions, output)
        assert path.exists()
        assert path.suffix == ".xlsx"


def test_export_has_sheets() -> None:
    """El Excel tiene las hojas esperadas."""
    import openpyxl

    financials = _make_financials()
    assumptions = _make_assumptions()
    result = run_dcf(assumptions, financials)

    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.xlsx"
        export_to_excel(result, financials, assumptions, output)
        wb = openpyxl.load_workbook(output)
        assert "Inputs" in wb.sheetnames
        assert "Financials" in wb.sheetnames
        assert "Projection" in wb.sheetnames
        assert "DCF" in wb.sheetnames
        assert "Sensitivities" in wb.sheetnames
        assert "Bridge" in wb.sheetnames


def test_export_to_excel_bytes_is_valid_xlsx() -> None:
    """Los bytes exportados son un xlsx valido con las 6 hojas.

    Camino que usa el boton de descarga de la UI: mismo contenido que
    ``export_to_excel`` sin tocar disco.
    """
    import io

    import openpyxl

    financials = _make_financials()
    assumptions = _make_assumptions()
    result = run_dcf(assumptions, financials)

    data = export_to_excel_bytes(result, financials, assumptions)

    assert isinstance(data, bytes)
    assert data[:2] == b"PK"  # firma zip/xlsx
    wb = openpyxl.load_workbook(io.BytesIO(data))
    assert wb.sheetnames == [
        "Inputs",
        "Financials",
        "Projection",
        "DCF",
        "Sensitivities",
        "Bridge",
    ]


def test_export_bytes_matches_file_export() -> None:
    """Los bytes y el archivo generado contienen las mismas hojas."""
    import io

    import openpyxl

    financials = _make_financials()
    assumptions = _make_assumptions()
    result = run_dcf(assumptions, financials)

    data = export_to_excel_bytes(result, financials, assumptions)
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "test.xlsx"
        export_to_excel(result, financials, assumptions, output)
        from_file = openpyxl.load_workbook(output).sheetnames

    assert openpyxl.load_workbook(io.BytesIO(data)).sheetnames == from_file
