"""Construccion de FinancialStatements a partir de facts iXBRL (AGENTS.md §6).

Agrupa los facts extraidos por :mod:`dcf_app.extraction.ixbrl` en ejercicios
fiscales y los mapea a los campos normalizados via :mod:`dcf_app.extraction.mapping`.

Decisiones de diseno (docs/methodology.md):
- Solo entran en el P&L y el flujo de caja las duraciones anuales
  (300-380 dias): los 10-K incluyen tambien trimestres y acumulados en las
  notas, que no son el ejercicio fiscal completo.
- Los facts instantaneos alimentan el balance a esa fecha.
- Un concepto presente en los mapas de P&L y flujo de caja (D&A, SBC) se
  copia en ambos estados del ejercicio: es el mismo tag del documento.
- Ante conflictos (varios conceptos mapean al mismo campo con valores
  distintos) se prefiere el tag estandar us-gaap y, a igualdad, el primero
  en orden de documento. Determinista y auditable.
"""

from __future__ import annotations

import logging
import math
from datetime import date

from dcf_app.extraction.mapping import (
    BALANCE_SHEET_MAP,
    CASH_FLOW_MAP,
    INCOME_STATEMENT_MAP,
    is_company_extension,
    normalize_concept,
)
from dcf_app.models.fact import Fact
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)

logger = logging.getLogger(__name__)

# Ventana de dias que consideramos "un ejercicio fiscal" (52-53 semanas o ano civil).
MIN_ANNUAL_DAYS = 300
MAX_ANNUAL_DAYS = 380

# Ejercicios que se conservan por estado (los mas recientes).
MAX_YEARS_KEPT = 3

_STATEMENT_MAPS: dict[str, dict[str, str]] = {
    "income": INCOME_STATEMENT_MAP,
    "cashflow": CASH_FLOW_MAP,
}


def _normalized_local(concept: str) -> str:
    """Nombre local del concepto, normalizado para busqueda en los mapas."""
    local = concept.split(":")[-1] if ":" in concept else concept
    return normalize_concept(local)


def _candidate_fields(fact: Fact) -> list[tuple[str, str]]:
    """Devuelve [(tipo_estado, campo)] a los que mapea el fact.

    - Facts instantaneos: solo balance.
    - Facts de duracion anual: P&L y/o flujo de caja (un concepto puede
      estar en ambos mapas, p. ej. D&A o SBC).
    - Duraciones no anuales o conceptos sin mapeo: lista vacia.
    """
    concept = fact.source.concept or ""
    normalized = _normalized_local(concept)
    candidates: list[tuple[str, str]] = []

    if fact.is_instant:
        field = BALANCE_SHEET_MAP.get(normalized)
        if field:
            candidates.append(("balance", field))
        return candidates

    days = (fact.period_end - fact.period_start).days if fact.period_start else 0
    if not (MIN_ANNUAL_DAYS <= days <= MAX_ANNUAL_DAYS):
        return candidates

    for statement_type, mapping in _STATEMENT_MAPS.items():
        field = mapping.get(normalized)
        if field:
            candidates.append((statement_type, field))
    return candidates


def _assign(target: dict[str, Fact], field: str, fact: Fact) -> None:
    """Asigna un fact a un campo resolviendo conflictos de forma determinista.

    Regla: gana el tag estandar (no extension de empresa); a igualdad, el
    primero en orden de documento. Valores iguales no desplazan al existente.
    """
    existing = target.get(field)
    if existing is None:
        target[field] = fact
        return
    if math.isclose(existing.value or 0.0, fact.value or 0.0, rel_tol=1e-9, abs_tol=1e-9):
        return
    existing_concept = existing.source.concept or ""
    new_concept = fact.source.concept or ""
    if is_company_extension(existing_concept) and not is_company_extension(new_concept):
        target[field] = fact


def _pick_latest_periods(
    grouped: dict[tuple[date | None, date], dict[str, Fact]], max_years: int
) -> list[tuple[date | None, date]]:
    """Periodos (inicio, fin) mas recientes, ordenados por cierre."""
    return sorted(grouped.keys(), key=lambda p: p[1])[-max_years:]


def build_financial_statements(
    facts: list[Fact],
    company_name: str,
    currency: str = "USD",
    max_years: int = MAX_YEARS_KEPT,
) -> FinancialStatements:
    """Construye FinancialStatements a partir de facts iXBRL.

    Args:
        facts: facts extraidos del documento (con concepto en la fuente).
        company_name: nombre de la empresa.
        currency: moneda de reporte.
        max_years: ejercicios maximos a conservar por estado (los mas
            recientes).

    Returns:
        FinancialStatements con los ejercicios detectados. Puede devolver
        listas vacias si no hay facts mapeables; el llamador decide si eso
        es un error.
    """
    # Fact de duracion => period_start no es None, pero el tipo de Fact es
    # ``date | None``; ensanchamos la clave para no forzar el tipo en mypy.
    income: dict[tuple[date | None, date], dict[str, Fact]] = {}
    cashflow: dict[tuple[date | None, date], dict[str, Fact]] = {}
    balance: dict[date, dict[str, Fact]] = {}

    for fact in facts:
        if fact.value is None:
            continue
        for statement_type, field in _candidate_fields(fact):
            if statement_type == "balance":
                _assign(balance.setdefault(fact.period_end, {}), field, fact)
            elif statement_type == "income":
                _assign(income.setdefault((fact.period_start, fact.period_end), {}), field, fact)
            elif statement_type == "cashflow":
                _assign(cashflow.setdefault((fact.period_start, fact.period_end), {}), field, fact)

    income_list: list[IncomeStatement] = []
    for start, end in _pick_latest_periods(income, max_years):
        if start is None:  # duracion anual: siempre tiene inicio
            continue
        income_list.append(
            IncomeStatement(
                fiscal_year=end.year, period_start=start, period_end=end, **income[(start, end)]
            )
        )
    cashflow_list: list[CashFlowStatement] = []
    for start, end in _pick_latest_periods(cashflow, max_years):
        if start is None:  # duracion anual: siempre tiene inicio
            continue
        cashflow_list.append(
            CashFlowStatement(
                fiscal_year=end.year, period_start=start, period_end=end, **cashflow[(start, end)]
            )
        )
    balance_list: list[BalanceSheet] = []
    for as_of in sorted(balance.keys())[-max_years:]:
        balance_list.append(
            BalanceSheet(fiscal_year=as_of.year, period_end=as_of, **balance[as_of])
        )

    if not (income_list and balance_list and cashflow_list):
        # Degradacion segura (AGENTS.md §2.8): sin los tres estados no hay
        # valoracion posible; se devuelven vacios y el llamador avisa.
        logger.warning(
            "iXBRL sin estados completos: income=%d, balance=%d, cashflow=%d",
            len(income_list),
            len(balance_list),
            len(cashflow_list),
        )
        return FinancialStatements(
            company_name=company_name,
            reporting_currency=currency,
        )

    return FinancialStatements(
        company_name=company_name,
        reporting_currency=currency,
        income_statements=income_list,
        balance_sheets=balance_list,
        cash_flow_statements=cashflow_list,
    )


__all__ = [
    "MAX_ANNUAL_DAYS",
    "MAX_YEARS_KEPT",
    "MIN_ANNUAL_DAYS",
    "build_financial_statements",
]
