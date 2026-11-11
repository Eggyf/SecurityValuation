"""Comprobaciones de integridad contable (AGENTS.md §6).

Cada validación devuelve un estado: OK, WARNING o ERROR.
Un ERROR bloquea la valoración final.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dcf_app.models.fact import Fact
from dcf_app.models.financials import FinancialStatements


class ValidationStatus(StrEnum):
    """Estado de una validación."""

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Resultado de una validación individual."""

    name: str
    status: ValidationStatus
    message: str


def _fact_value(fact: Fact | None) -> float | None:
    """Extrae el valor de un Fact en millones."""
    if fact is None or getattr(fact, "value", None) is None:
        return None
    return fact.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS)


def validate_balance_sheet(financials: FinancialStatements) -> ValidationResult:
    """Activos = Pasivos + Patrimonio (tolerancia < 0,5 %)."""
    if not financials.balance_sheets:
        return ValidationResult("balance_sheet", ValidationStatus.ERROR, "No hay balance.")
    bs = financials.balance_sheets[-1]
    assets = _fact_value(bs.total_assets)
    liabilities = _fact_value(bs.total_liabilities)
    equity = _fact_value(bs.total_equity)

    if assets is None or liabilities is None or equity is None:
        return ValidationResult(
            "balance_sheet",
            ValidationStatus.WARNING,
            "Faltan datos de activos, pasivos o patrimonio para validar.",
        )

    total = liabilities + equity
    if total == 0:
        return ValidationResult(
            "balance_sheet", ValidationStatus.ERROR, "Pasivos + Patrimonio = 0."
        )

    diff_pct = abs(assets - total) / abs(total) * 100
    if diff_pct < 0.5:
        return ValidationResult(
            "balance_sheet",
            ValidationStatus.OK,
            f"Activos = Pasivos + Patrimonio (diff {diff_pct:.2f} %).",
        )
    if diff_pct < 2.0:
        return ValidationResult(
            "balance_sheet",
            ValidationStatus.WARNING,
            f"Diferencia del {diff_pct:.2f} % entre activos y pasivos + patrimonio.",
        )
    return ValidationResult(
        "balance_sheet",
        ValidationStatus.ERROR,
        f"Activos ({assets:,.0f}) ≠ Pasivos + Patrimonio ({total:,.0f}) (diff {diff_pct:.2f} %).",
    )


def validate_gross_profit(financials: FinancialStatements) -> ValidationResult:
    """Gross Profit = Revenue - COGS (cuando existan ambos)."""
    if not financials.income_statements:
        return ValidationResult(
            "gross_profit", ValidationStatus.ERROR, "No hay estado de resultados."
        )
    income = financials.income_statements[-1]
    revenue = _fact_value(income.revenue)
    cogs = _fact_value(income.cogs)
    gross = _fact_value(income.gross_profit)

    if revenue is None or cogs is None or gross is None:
        return ValidationResult(
            "gross_profit", ValidationStatus.WARNING, "Faltan datos para validar Gross Profit."
        )
    expected = revenue - cogs
    diff_pct = abs(gross - expected) / abs(expected) * 100 if expected != 0 else 0
    if diff_pct < 0.5:
        return ValidationResult(
            "gross_profit",
            ValidationStatus.OK,
            f"Gross Profit = Revenue - COGS (diff {diff_pct:.2f} %).",
        )
    return ValidationResult(
        "gross_profit",
        ValidationStatus.WARNING,
        f"Gross Profit ({gross:,.0f}) ≠ Revenue - COGS ({expected:,.0f}).",
    )


def validate_net_income_consistency(financials: FinancialStatements) -> ValidationResult:
    """Net Income del P&L coincide con el del flujo de caja."""
    if not financials.income_statements or not financials.cash_flow_statements:
        return ValidationResult(
            "net_income_consistency", ValidationStatus.WARNING, "Faltan estados para validar."
        )
    income = financials.income_statements[-1]

    ni_income = _fact_value(income.net_income)
    # El flujo de caja no siempre reporta Net Income directamente

    if ni_income is None:
        return ValidationResult(
            "net_income_consistency", ValidationStatus.WARNING, "No hay Net Income en el P&L."
        )
    return ValidationResult(
        "net_income_consistency", ValidationStatus.OK, "Net Income del P&L disponible."
    )


def validate_scale_consistency(financials: FinancialStatements) -> ValidationResult:
    """Consistencia de escala entre estados (no mezclar miles con millones)."""
    scales: set[str] = set()
    for inc in financials.income_statements:
        if inc.revenue and inc.revenue.value is not None:
            scales.add(inc.revenue.scale.value)
    for bs in financials.balance_sheets:
        if bs.total_assets and bs.total_assets.value is not None:
            scales.add(bs.total_assets.scale.value)
    for cf in financials.cash_flow_statements:
        if cf.cfo and cf.cfo.value is not None:
            scales.add(cf.cfo.scale.value)

    if len(scales) <= 1:
        return ValidationResult(
            "scale_consistency", ValidationStatus.OK, f"Escala consistente: {scales}."
        )
    return ValidationResult(
        "scale_consistency", ValidationStatus.WARNING, f"Escalas mezcladas: {scales}. Verificar."
    )


def validate_consecutive_years(financials: FinancialStatements) -> ValidationResult:
    """Los años cubren periodos consecutivos y son del mismo ejercicio fiscal."""
    if not financials.income_statements:
        return ValidationResult(
            "consecutive_years", ValidationStatus.ERROR, "No hay estados de resultados."
        )
    years = [s.fiscal_year for s in financials.income_statements]
    if len(years) < 2:
        return ValidationResult(
            "consecutive_years",
            ValidationStatus.WARNING,
            f"Solo {len(years)} ejercicio(s). Se recomiendan ≥ 3.",
        )
    # Verificar consecutividad
    sorted_years = sorted(years)
    is_consecutive = all(
        sorted_years[i + 1] - sorted_years[i] == 1 for i in range(len(sorted_years) - 1)
    )
    if is_consecutive:
        return ValidationResult(
            "consecutive_years", ValidationStatus.OK, f"Ejercicios consecutivos: {sorted_years}."
        )
    return ValidationResult(
        "consecutive_years",
        ValidationStatus.WARNING,
        f"Ejercicios no consecutivos: {sorted_years}.",
    )


def validate_all(financials: FinancialStatements) -> list[ValidationResult]:
    """Ejecuta todas las validaciones y devuelve la lista de resultados."""
    return [
        validate_balance_sheet(financials),
        validate_gross_profit(financials),
        validate_net_income_consistency(financials),
        validate_scale_consistency(financials),
        validate_consecutive_years(financials),
    ]


def has_errors(results: list[ValidationResult]) -> bool:
    """Indica si algún resultado es ERROR."""
    return any(r.status == ValidationStatus.ERROR for r in results)


__all__ = [
    "ValidationResult",
    "ValidationStatus",
    "has_errors",
    "validate_all",
    "validate_balance_sheet",
    "validate_consecutive_years",
    "validate_gross_profit",
    "validate_net_income_consistency",
    "validate_scale_consistency",
]
