"""Tests de :mod:`dcf_app.models.financials`."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError as PydanticValidationError

from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)


def _income(fy: int) -> IncomeStatement:
    return IncomeStatement(fiscal_year=fy, period_start=date(fy, 1, 1), period_end=date(fy, 12, 31))


def _balance(fy: int) -> BalanceSheet:
    return BalanceSheet(fiscal_year=fy, period_end=date(fy, 12, 31))


def _cash_flow(fy: int) -> CashFlowStatement:
    return CashFlowStatement(
        fiscal_year=fy, period_start=date(fy, 1, 1), period_end=date(fy, 12, 31)
    )


def _statements(
    years: tuple[int, ...] = (2022, 2023, 2024),
    balance_years: tuple[int, ...] | None = None,
    cash_years: tuple[int, ...] | None = None,
) -> FinancialStatements:
    return FinancialStatements(
        company_name="Acme Corp",
        income_statements=[_income(year) for year in years],
        balance_sheets=[_balance(year) for year in (balance_years or years)],
        cash_flow_statements=[_cash_flow(year) for year in (cash_years or years)],
    )


def test_minimal_valid_statements_pass() -> None:
    statements = _statements()
    assert statements.fiscal_years == [2022, 2023, 2024]


def test_single_year_is_structurally_valid() -> None:
    # «Mínimo 3 ejercicios» es una comprobación de datos (validation/), no estructural.
    assert _statements(years=(2024,)).fiscal_years == [2024]


def test_all_partidas_may_be_missing() -> None:
    # Un 10-K incompleto no rompe el modelo: los huecos quedan en None (AGENTS.md §2.1).
    income = _income(2024)
    assert income.revenue is None
    assert income.net_income is None


def test_duplicate_fiscal_year_rejected() -> None:
    with pytest.raises(PydanticValidationError, match="duplicados"):
        _statements(years=(2023, 2023, 2024))


def test_unsorted_years_rejected() -> None:
    with pytest.raises(PydanticValidationError, match="ascendente"):
        _statements(years=(2024, 2023, 2022))


def test_balance_two_years_vs_income_three_is_valid() -> None:
    # Reg S-X: el balance presenta 2 ejercicios y el P&L/flujos 3.
    statements = _statements(years=(2022, 2023, 2024), balance_years=(2023, 2024))
    assert statements.fiscal_years == [2022, 2023, 2024]
    assert [b.fiscal_year for b in statements.balance_sheets] == [2023, 2024]


def test_misaligned_base_year_rejected() -> None:
    # El año base (más reciente) debe coincidir en los tres estados.
    with pytest.raises(PydanticValidationError, match="año base"):
        _statements(years=(2022, 2023, 2024), balance_years=(2024, 2025))


def test_empty_state_rejected() -> None:
    with pytest.raises(PydanticValidationError):
        FinancialStatements(
            company_name="Acme Corp",
            income_statements=[],
            balance_sheets=[_balance(2024)],
            cash_flow_statements=[_cash_flow(2024)],
        )


def test_income_requires_period_start() -> None:
    with pytest.raises(PydanticValidationError):
        IncomeStatement(fiscal_year=2024, period_end=date(2024, 12, 31))  # type: ignore[call-arg]


def test_notes_have_safe_defaults() -> None:
    statements = _statements()
    assert statements.notes.dilutive_securities.options_outstanding is None
    assert statements.notes.non_recurring_items == []
