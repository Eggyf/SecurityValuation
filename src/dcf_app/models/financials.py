"""Estados financieros extraídos del 10-K (AGENTS.md §6).

Un modelo por estado y ejercicio fiscal. Todas las partidas son
:class:`~dcf_app.models.fact.Fact` opcionales: si el 10-K no las incluye,
quedan en ``None`` y la aplicación las pide explícitamente en vez de
inventarlas (AGENTS.md §2.1).

Las comprobaciones de coherencia contable (activos = pasivos + patrimonio,
etc.) viven en ``validation/``; aquí solo se valida la estructura
(ejercicios únicos, ordenados y alineados entre estados).
"""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from dcf_app.models.fact import Fact
from dcf_app.models.notes import SupplementaryNotes


class IncomeStatement(BaseModel):
    """Cuenta de resultados de un ejercicio fiscal (magnitudes de periodo)."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: int
    period_start: date
    period_end: date

    revenue: Fact | None = None
    cogs: Fact | None = None
    gross_profit: Fact | None = None
    sga: Fact | None = None
    rd: Fact | None = None
    depreciation_amortization: Fact | None = None
    ebit: Fact | None = None  # Operating Income
    interest_expense: Fact | None = None
    pretax_income: Fact | None = None
    income_tax_expense: Fact | None = None
    net_income: Fact | None = None
    diluted_eps: Fact | None = None
    diluted_weighted_shares: Fact | None = None  # unit: 'shares'
    sbc: Fact | None = None  # gasto total del ejercicio


class BalanceSheet(BaseModel):
    """Balance a fecha de cierre (magnitudes instantáneas: sin ``period_start``)."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: int
    period_end: date

    cash_and_equivalents: Fact | None = None
    short_term_investments: Fact | None = None
    accounts_receivable: Fact | None = None
    inventory: Fact | None = None
    other_current_assets: Fact | None = None
    accounts_payable: Fact | None = None
    accrued_liabilities: Fact | None = None
    deferred_revenue: Fact | None = None
    short_term_debt: Fact | None = None  # incluye la porción corriente de la LP
    long_term_debt: Fact | None = None
    operating_lease_liabilities_current: Fact | None = None
    operating_lease_liabilities_noncurrent: Fact | None = None
    finance_lease_liabilities: Fact | None = None
    preferred_stock: Fact | None = None
    non_controlling_interest: Fact | None = None
    total_equity: Fact | None = None
    total_assets: Fact | None = None  # para la validación A = P + Patrimonio
    total_liabilities: Fact | None = None  # ídem


class CashFlowStatement(BaseModel):
    """Estado de flujos de caja de un ejercicio fiscal (magnitudes de periodo)."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: int
    period_start: date
    period_end: date

    net_income: Fact | None = None  # beneficio neto (primera linea del EFE)
    cfo: Fact | None = None  # caja de operaciones
    capex: Fact | None = None  # con el signo reportado (típicamente negativo)
    depreciation_amortization: Fact | None = None  # adición sin efecto de caja
    sbc: Fact | None = None  # adición sin efecto de caja
    change_in_working_capital: Fact | None = None  # agregado operativo
    net_change_in_cash: Fact | None = None  # para validar contra el balance


class FinancialStatements(BaseModel):
    """Estados financieros del 10-K: un ejercicio por entrada en cada estado.

    La exigencia de «mínimo 3 ejercicios consecutivos» es una comprobación de
    datos que vive en ``validation/``; aquí se valida solo la estructura.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1)
    cik: str | None = None
    reporting_currency: str = "USD"
    income_statements: list[IncomeStatement] = Field(default_factory=list)
    balance_sheets: list[BalanceSheet] = Field(default_factory=list)
    cash_flow_statements: list[CashFlowStatement] = Field(default_factory=list)
    notes: SupplementaryNotes = Field(default_factory=SupplementaryNotes)

    @property
    def fiscal_years(self) -> list[int]:
        """Ejercicios fiscales cubiertos, en orden ascendente."""
        return [statement.fiscal_year for statement in self.income_statements]

    @model_validator(mode="after")
    def _statements_aligned(self) -> Self:
        """Exige ejercicios únicos, ordenados y un año base común.

        Reg S-X: el balance de un 10-K presenta 2 ejercicios y el P&L y los
        flujos 3, así que NO se exigen conjuntos idénticos; se exige que el
        ejercicio más reciente (el año base de la valoración) esté presente
        en los tres estados, y que cada lista esté ordenada y sin duplicados.
        """
        statements_by_state: list[
            tuple[str, list[IncomeStatement] | list[BalanceSheet] | list[CashFlowStatement]]
        ] = [
            ("income_statements", self.income_statements),
            ("balance_sheets", self.balance_sheets),
            ("cash_flow_statements", self.cash_flow_statements),
        ]
        latest_years: list[int] = []
        for name, statements in statements_by_state:
            years = [statement.fiscal_year for statement in statements]
            if len(set(years)) != len(years):
                raise ValueError(f"{name}: ejercicios fiscales duplicados ({years}).")
            if years != sorted(years):
                raise ValueError(
                    f"{name}: los ejercicios deben estar en orden ascendente ({years})."
                )
            if years:
                latest_years.append(years[-1])
        non_empty = [bool(s) for _, s in statements_by_state]
        if any(non_empty) and not all(non_empty):
            raise ValueError(
                "Los tres estados deben estar presentes: no puede haber unos "
                "con datos y otros vacíos."
            )
        if latest_years and len(set(latest_years)) != 1:
            raise ValueError(
                "El ejercicio fiscal más reciente debe coincidir en los tres "
                f"estados (año base de la valoración): {latest_years}."
            )
        return self
