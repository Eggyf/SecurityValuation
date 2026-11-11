"""Tests de :mod:`dcf_app.assumptions.defaults` (AGENTS.md §7.1, §7.2).

Casos calculados a mano en cada docstring; los defaults solo pueden venir
del 10-K, nunca de valores tipicos (AGENTS.md §2.1).
"""

from __future__ import annotations

from datetime import date

from dcf_app.assumptions.defaults import suggest_defaults
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float, unit: str = "USD", scale: Scale = Scale.MILLIONS) -> Fact:
    return Fact(
        value=value,
        unit=unit,
        scale=scale,
        period_end=date(2024, 12, 31),
        source=_src(),
    )


def _income(
    year: int,
    revenue: float | None,
    ebit: float | None = None,
    tax: float | None = None,
    pretax: float | None = None,
) -> IncomeStatement:
    """IncomeStatement de un ejercicio con las cifras dadas."""
    return IncomeStatement(
        fiscal_year=year,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        revenue=None if revenue is None else _fact(revenue),
        ebit=None if ebit is None else _fact(ebit),
        income_tax_expense=None if tax is None else _fact(tax),
        pretax_income=None if pretax is None else _fact(pretax),
    )


def _balance(
    year: int,
    short_term_debt: float | None,
    long_term_debt: float | None,
) -> BalanceSheet:
    """BalanceSheet con solo la deuda financiera."""
    return BalanceSheet(
        fiscal_year=year,
        period_end=date(year, 12, 31),
        short_term_debt=None if short_term_debt is None else _fact(short_term_debt),
        long_term_debt=None if long_term_debt is None else _fact(long_term_debt),
    )


def _financials(
    income: list[IncomeStatement],
    balances: list[BalanceSheet],
) -> FinancialStatements:
    """FinancialStatements con los estados dados.

    ``FinancialStatements`` exige los tres estados presentes (o todos
    vacíos) y el mismo último ejercicio (Reg S-X), así que los estados
    que falten se rellenan con ejercicios sin cifras.
    """
    years = sorted({s.fiscal_year for s in income} | {s.fiscal_year for s in balances})
    if not years:
        return FinancialStatements(company_name="Test Corp")
    income_complete = income or [_income(y, None) for y in years]
    balances_complete = balances or [_balance(y, None, None) for y in years]
    cashflows = [
        CashFlowStatement(
            fiscal_year=y,
            period_start=date(y, 1, 1),
            period_end=date(y, 12, 31),
        )
        for y in years
    ]
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=income_complete,
        balance_sheets=balances_complete,
        cash_flow_statements=cashflows,
    )


def test_revenue_cagr_three_years() -> None:
    """CAGR 800 -> 1000 en 2 anos: (1000/800)^0.5 - 1 = 11.8034 %."""
    income = [
        _income(2022, 800.0, ebit=160.0, tax=16.0, pretax=80.0),
        _income(2023, 900.0, ebit=180.0, tax=18.0, pretax=90.0),
        _income(2024, 1000.0, ebit=200.0, tax=20.0, pretax=100.0),
    ]
    defaults = suggest_defaults(_financials(income, [_balance(2024, 30.0, 170.0)]))

    assert defaults.revenue_cagr is not None
    assert abs(defaults.revenue_cagr - ((1000.0 / 800.0) ** 0.5 - 1.0)) < 1e-9


def test_revenue_cagr_clamped_high() -> None:
    """CAGR 100 -> 500 en 1 ano = +400 % -> acotado a 25 % (AGENTS.md §7.2)."""
    income = [_income(2023, 100.0), _income(2024, 500.0)]
    defaults = suggest_defaults(_financials(income, []))

    assert defaults.revenue_cagr == 0.25


def test_revenue_cagr_clamped_low() -> None:
    """CAGR 1000 -> 700 -> 490 en 2 anos = -30 % -> acotado a -5 %."""
    income = [_income(2022, 1000.0), _income(2023, 700.0), _income(2024, 490.0)]
    defaults = suggest_defaults(_financials(income, []))

    assert defaults.revenue_cagr == -0.05


def test_revenue_cagr_insufficient_data() -> None:
    """Con un solo ejercicio o revenue faltante no hay CAGR (None)."""
    defaults_one = suggest_defaults(_financials([_income(2024, 1000.0)], []))
    defaults_none = suggest_defaults(_financials([_income(2023, None), _income(2024, 100.0)], []))

    assert defaults_one.revenue_cagr is None
    assert defaults_none.revenue_cagr is None


def test_ebit_margin_current() -> None:
    """Margen EBIT del ultimo ejercicio: 200 / 1000 = 20 %."""
    income = [_income(2023, 800.0, ebit=100.0), _income(2024, 1000.0, ebit=200.0)]
    defaults = suggest_defaults(_financials(income, []))

    assert defaults.ebit_margin_current is not None
    assert abs(defaults.ebit_margin_current - 0.20) < 1e-9


def test_ebit_margin_negative_is_reported_not_hidden() -> None:
    """EBIT negativo se informa como margen negativo (decide la UI)."""
    income = [_income(2024, 1000.0, ebit=-50.0)]
    defaults = suggest_defaults(_financials(income, []))

    assert defaults.ebit_margin_current is not None
    assert defaults.ebit_margin_current < 0


def test_ebit_margin_missing() -> None:
    """Sin EBIT o sin revenue no hay margen (None)."""
    defaults = suggest_defaults(_financials([_income(2024, 1000.0)], []))

    assert defaults.ebit_margin_current is None


def test_effective_tax_rate_average_and_clamp() -> None:
    """Media de t = tax/pretax por ejercicio, acotada a [15 %, 30 %].

    - 20 % y 30 % -> media 25 % (sin acotar).
    - 35 % y 45 % -> media 40 % -> acotada a 30 %.
    - 5 % y 7 % -> media 6 % -> acotada a 15 %.
    """
    mixed = suggest_defaults(
        _financials(
            [
                _income(2023, 900.0, tax=18.0, pretax=90.0),  # 20 %
                _income(2024, 1000.0, tax=30.0, pretax=100.0),  # 30 %
            ],
            [],
        )
    )
    high = suggest_defaults(
        _financials(
            [
                _income(2023, 900.0, tax=31.5, pretax=90.0),  # 35 %
                _income(2024, 1000.0, tax=45.0, pretax=100.0),  # 45 %
            ],
            [],
        )
    )
    low = suggest_defaults(
        _financials(
            [
                _income(2023, 900.0, tax=4.5, pretax=90.0),  # 5 %
                _income(2024, 1000.0, tax=7.0, pretax=100.0),  # 7 %
            ],
            [],
        )
    )

    assert mixed.effective_tax_rate is not None
    assert abs(mixed.effective_tax_rate - 0.25) < 1e-9
    assert high.effective_tax_rate == 0.30
    assert low.effective_tax_rate == 0.15


def test_effective_tax_rate_missing() -> None:
    """Sin tax o pretax en ningun ejercicio -> None (no se inventa)."""
    defaults = suggest_defaults(_financials([_income(2024, 1000.0)], []))

    assert defaults.effective_tax_rate is None


def test_book_debt() -> None:
    """Deuda contable: ST + LT del ultimo balance; parcial si falta uno."""
    both = suggest_defaults(_financials([], [_balance(2024, 30.0, 170.0)]))
    only_lt = suggest_defaults(_financials([], [_balance(2024, None, 170.0)]))
    none = suggest_defaults(_financials([], [_balance(2024, None, None)]))

    assert both.book_debt == 200.0
    assert only_lt.book_debt == 170.0
    assert none.book_debt is None


def test_diluted_shares_rescaled_to_millions() -> None:
    """Las acciones se sugieren en millones via Fact.to_scale."""
    income = IncomeStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        diluted_weighted_shares=_fact(7_453_000_000.0, unit="shares", scale=Scale.UNITS),
    )

    defaults = suggest_defaults(_financials([income], []))

    assert defaults.diluted_weighted_shares == 7453.0


def test_empty_financials_all_none() -> None:
    """Sin estados extraidos, ningun default se inventa (AGENTS.md §2.1)."""
    defaults = suggest_defaults(FinancialStatements(company_name="Test Corp"))

    assert defaults.revenue_cagr is None
    assert defaults.ebit_margin_current is None
    assert defaults.effective_tax_rate is None
    assert defaults.diluted_weighted_shares is None
    assert defaults.book_debt is None
