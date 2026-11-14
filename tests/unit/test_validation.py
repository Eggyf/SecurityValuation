"""Tests de :mod:`dcf_app.validation`."""

from __future__ import annotations

from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import BalanceSheet, FinancialStatements, IncomeStatement
from dcf_app.validation import (
    ValidationStatus,
    has_errors,
    validate_all,
    validate_balance_sheet,
    validate_consecutive_years,
    validate_gross_profit,
    validate_scale_consistency,
)


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float, scale: Scale = Scale.MILLIONS) -> Fact:
    from datetime import date

    return Fact(value=value, unit="USD", scale=scale, period_end=date(2024, 12, 31), source=_src())


def _make_financials_balanced() -> FinancialStatements:
    """Estados financieros con balance cuadrado."""
    income = IncomeStatement(
        fiscal_year=2024,
        period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 12, 31),
        revenue=_fact(1000.0),
        cogs=_fact(600.0),
        gross_profit=_fact(400.0),
    )
    balance = BalanceSheet(
        fiscal_year=2024,
        period_end=__import__("datetime").date(2024, 12, 31),
        total_assets=_fact(500.0),
        total_liabilities=_fact(300.0),
        total_equity=_fact(200.0),
    )
    from dcf_app.models.financials import CashFlowStatement

    cf = CashFlowStatement(
        fiscal_year=2024,
        period_start=__import__("datetime").date(2024, 1, 1),
        period_end=__import__("datetime").date(2024, 12, 31),
        cfo=_fact(100.0),
    )
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=[income],
        balance_sheets=[balance],
        cash_flow_statements=[cf],
    )


def test_validate_balance_sheet_ok() -> None:
    """Balance cuadrado → OK."""
    financials = _make_financials_balanced()
    result = validate_balance_sheet(financials)
    assert result.status == ValidationStatus.OK


def test_validate_balance_sheet_error() -> None:
    """Balance que no cuadra → ERROR."""
    financials = _make_financials_balanced()
    financials.balance_sheets[0].total_assets = _fact(1000.0)
    result = validate_balance_sheet(financials)
    assert result.status == ValidationStatus.ERROR


def test_validate_gross_profit_ok() -> None:
    """Gross Profit correcto → OK."""
    financials = _make_financials_balanced()
    result = validate_gross_profit(financials)
    assert result.status == ValidationStatus.OK


def test_validate_gross_profit_warning() -> None:
    """Gross Profit incorrecto → WARNING."""
    financials = _make_financials_balanced()
    financials.income_statements[0].gross_profit = _fact(500.0)
    result = validate_gross_profit(financials)
    assert result.status == ValidationStatus.WARNING


def test_validate_scale_consistency_ok() -> None:
    """Escala consistente → OK."""
    financials = _make_financials_balanced()
    result = validate_scale_consistency(financials)
    assert result.status == ValidationStatus.OK


def test_validate_consecutive_years_single() -> None:
    """Un solo año → WARNING."""
    financials = _make_financials_balanced()
    result = validate_consecutive_years(financials)
    assert result.status == ValidationStatus.WARNING


def test_validate_consecutive_years_multiple() -> None:
    """Múltiples años consecutivos → OK."""
    from datetime import date

    financials = _make_financials_balanced()
    # Agregar otro año
    income2 = IncomeStatement(
        fiscal_year=2023,
        period_start=date(2023, 1, 1),
        period_end=date(2023, 12, 31),
        revenue=_fact(1100.0),
    )
    balance2 = BalanceSheet(
        fiscal_year=2023,
        period_end=date(2023, 12, 31),
        total_assets=_fact(550.0),
        total_liabilities=_fact(330.0),
        total_equity=_fact(220.0),
    )
    from dcf_app.models.financials import CashFlowStatement

    cf2 = CashFlowStatement(
        fiscal_year=2023,
        period_start=date(2023, 1, 1),
        period_end=date(2023, 12, 31),
        cfo=_fact(110.0),
    )
    financials.income_statements.append(income2)
    financials.balance_sheets.append(balance2)
    financials.cash_flow_statements.append(cf2)
    result = validate_consecutive_years(financials)
    assert result.status == ValidationStatus.OK


def test_validate_all() -> None:
    """validate_all devuelve lista de resultados."""
    financials = _make_financials_balanced()
    results = validate_all(financials)
    assert len(results) == 8
    assert not has_errors(results)


def test_has_errors() -> None:
    """has_errors detecta errores."""
    financials = _make_financials_balanced()
    financials.balance_sheets[0].total_assets = _fact(1000.0)
    results = validate_all(financials)
    assert has_errors(results)
