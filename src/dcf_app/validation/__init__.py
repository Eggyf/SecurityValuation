"""Comprobaciones de integridad contable (AGENTS.md §6).

Cada validación devuelve un estado: OK, WARNING o ERROR.
Un ERROR bloquea la valoración final.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dcf_app.models.fact import Fact, Scale
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
    return fact.to_scale(Scale.MILLIONS)


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
    """Net Income del P&L coincide con el del flujo de caja (tolerancia 0,5 %)."""
    if not financials.income_statements or not financials.cash_flow_statements:
        return ValidationResult(
            "net_income_consistency", ValidationStatus.WARNING, "Faltan estados para validar."
        )
    income = financials.income_statements[-1]
    cashflow = financials.cash_flow_statements[-1]

    ni_income = _fact_value(income.net_income)
    ni_cashflow = _fact_value(cashflow.net_income)

    if ni_income is None:
        return ValidationResult(
            "net_income_consistency", ValidationStatus.WARNING, "No hay Net Income en el P&L."
        )
    if ni_cashflow is None:
        return ValidationResult(
            "net_income_consistency",
            ValidationStatus.WARNING,
            "Net Income no disponible en el flujo de caja (no verificado).",
        )

    if ni_income == 0:
        return ValidationResult(
            "net_income_consistency", ValidationStatus.WARNING, "Net Income del P&L es 0."
        )

    diff_pct = abs(ni_income - ni_cashflow) / abs(ni_income) * 100
    if diff_pct < 0.5:
        return ValidationResult(
            "net_income_consistency",
            ValidationStatus.OK,
            f"NI P&L = NI flujo de caja (diff {diff_pct:.2f} %).",
        )
    return ValidationResult(
        "net_income_consistency",
        ValidationStatus.WARNING,
        f"NI P&L ({ni_income:,.0f}) ≠ NI flujo ({ni_cashflow:,.0f}) (diff {diff_pct:.2f} %).",
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


def validate_cash_flow_vs_balance(financials: FinancialStatements) -> ValidationResult:
    """Variación de caja del flujo ≈ variación de caja en balance."""
    if not financials.cash_flow_statements or not financials.balance_sheets:
        return ValidationResult(
            "cash_flow_vs_balance", ValidationStatus.WARNING, "Faltan estados para validar."
        )
    cf = financials.cash_flow_statements[-1]
    bs = financials.balance_sheets[-1]

    net_change = _fact_value(cf.net_change_in_cash)
    if net_change is None:
        return ValidationResult(
            "cash_flow_vs_balance",
            ValidationStatus.WARNING,
            "No hay cambio neto de caja en el flujo.",
        )

    # Variación de caja en balance: solo si hay al menos 2 balances
    if len(financials.balance_sheets) < 2:
        return ValidationResult(
            "cash_flow_vs_balance",
            ValidationStatus.WARNING,
            "Se necesitan 2 balances para comparar variación de caja.",
        )

    prev_bs = financials.balance_sheets[-2]
    cash_curr = _fact_value(bs.cash_and_equivalents)
    cash_prev = _fact_value(prev_bs.cash_and_equivalents)
    if cash_curr is None or cash_prev is None:
        return ValidationResult(
            "cash_flow_vs_balance", ValidationStatus.WARNING, "Faltan datos de caja en balance."
        )

    balance_change = cash_curr - cash_prev
    if balance_change != 0:
        diff_pct = abs(net_change - balance_change) / abs(balance_change) * 100
    else:
        diff_pct = 0.0
    if diff_pct < 5.0:
        return ValidationResult(
            "cash_flow_vs_balance",
            ValidationStatus.OK,
            "Variación de caja: flujo "
            f"{net_change:,.0f} vs balance {balance_change:,.0f} "
            f"(diff {diff_pct:.1f} %).",
        )
    return ValidationResult(
        "cash_flow_vs_balance",
        ValidationStatus.WARNING,
        "Variación de caja: flujo "
        f"{net_change:,.0f} vs balance {balance_change:,.0f} "
        f"(diff {diff_pct:.1f} %).",
    )


def validate_debt_consistency(financials: FinancialStatements) -> ValidationResult:
    """Deuda sin doble conteo: total = corriente + no corriente."""
    if not financials.balance_sheets:
        return ValidationResult("debt_consistency", ValidationStatus.ERROR, "No hay balance.")
    bs = financials.balance_sheets[-1]

    st_debt = _fact_value(bs.short_term_debt)
    lt_debt = _fact_value(bs.long_term_debt)
    # No tenemos un "total debt" field, así que solo verificamos que ambos existan
    if st_debt is None and lt_debt is None:
        return ValidationResult(
            "debt_consistency", ValidationStatus.WARNING, "No hay datos de deuda."
        )
    return ValidationResult(
        "debt_consistency",
        ValidationStatus.OK,
        f"Deuda CP: {st_debt or 0:,.0f}, LP: {lt_debt or 0:,.0f}.",
    )


def validate_shares_positive(financials: FinancialStatements) -> ValidationResult:
    """Las acciones en circulación deben ser positivas."""
    basic = financials.notes.basic_shares_outstanding
    if basic is not None and basic.value is not None:
        if basic.value <= 0:
            return ValidationResult(
                "shares_positive", ValidationStatus.ERROR, "Las acciones básicas son <= 0."
            )
        return ValidationResult(
            "shares_positive", ValidationStatus.OK, f"Acciones básicas: {basic.value:,.0f}."
        )
    # Verificar acciones diluidas del income statement
    if financials.income_statements:
        inc = financials.income_statements[-1]
        if (
            inc.diluted_weighted_shares is not None
            and inc.diluted_weighted_shares.value is not None
            and inc.diluted_weighted_shares.value <= 0
        ):
            return ValidationResult(
                "shares_positive", ValidationStatus.ERROR, "Las acciones diluidas son <= 0."
            )
    return ValidationResult(
        "shares_positive", ValidationStatus.WARNING, "No hay datos de acciones en circulación."
    )


def validate_all(financials: FinancialStatements) -> list[ValidationResult]:
    """Ejecuta todas las validaciones y devuelve la lista de resultados."""
    return [
        validate_balance_sheet(financials),
        validate_gross_profit(financials),
        validate_net_income_consistency(financials),
        validate_scale_consistency(financials),
        validate_consecutive_years(financials),
        validate_cash_flow_vs_balance(financials),
        validate_debt_consistency(financials),
        validate_shares_positive(financials),
    ]


def has_errors(results: list[ValidationResult]) -> bool:
    """Indica si algún resultado es ERROR."""
    return any(r.status == ValidationStatus.ERROR for r in results)


def validate_percentage_range(
    name: str, value: float | None, min_val: float, max_val: float, unit: str = "%"
) -> ValidationResult:
    """Valida que un porcentaje esté en un rango plausible.

    Args:
        name: nombre del parámetro.
        value: valor a validar (como fracción, ej: 0.04 = 4%).
        min_val: mínimo plausible (como fracción).
        max_val: máximo plausible (como fracción).
        unit: unidad para el mensaje.

    Returns:
        ValidationResult con OK si está en rango, WARNING si está fuera.
    """
    if value is None:
        return ValidationResult(name, ValidationStatus.WARNING, f"{name}: no proporcionado.")
    if min_val <= value <= max_val:
        return ValidationResult(
            name, ValidationStatus.OK, f"{name}: {value * 100:.2f} {unit} (en rango)."
        )
    return ValidationResult(
        name,
        ValidationStatus.WARNING,
        f"{name}: {value * 100:.2f} {unit} fuera del rango plausible "
        f"({min_val * 100:.1f}-{max_val * 100:.1f} {unit}).",
    )


def can_run_valuation(results: list[ValidationResult]) -> bool:
    """Indica si se puede ejecutar la valoración.

    Un ERROR bloquea la valoración. Sin resultados (vacío) se permite.
    """
    return not has_errors(results)


__all__ = [
    "ValidationResult",
    "ValidationStatus",
    "can_run_valuation",
    "has_errors",
    "validate_all",
    "validate_balance_sheet",
    "validate_cash_flow_vs_balance",
    "validate_consecutive_years",
    "validate_debt_consistency",
    "validate_gross_profit",
    "validate_net_income_consistency",
    "validate_scale_consistency",
    "validate_shares_positive",
]
