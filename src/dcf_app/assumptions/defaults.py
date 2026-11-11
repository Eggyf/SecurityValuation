"""Valores por defecto de los supuestos derivados del 10-K (AGENTS.md §4, §7).

Lógica «históricos → proyección»: calcula los defaults que la UI
pre-rellena a partir de los estados financieros extraídos del documento.

Regla (AGENTS.md §2.1, §7.3): solo se sugieren datos que están en el 10-K.
Lo que no está en el documento queda ``None`` y la UI lo pide
explícitamente; nunca se sustituye por un valor típico.
"""

from __future__ import annotations

from dataclasses import dataclass

from dcf_app.models.fact import Fact, Scale
from dcf_app.models.financials import BalanceSheet, FinancialStatements, IncomeStatement

# Acotaciones de la metodología (AGENTS.md §7.1, §7.2).
CAGR_MIN = -0.05  # crecimiento inicial mínimo: -5 %
CAGR_MAX = 0.25  # crecimiento inicial máximo: 25 %
TAX_MIN = 0.15  # tasa impositiva mínima: 15 %
TAX_MAX = 0.30  # tasa impositiva máxima: 30 %


@dataclass(frozen=True)
class SuggestedDefaults:
    """Defaults sugeridos a partir del 10-K.

    ``None`` en un campo significa «no disponible en el documento»: la UI
    no debe pre-rellenarlo (no se inventa, AGENTS.md §2.1). Todas las
    cifras monetarias están en millones y las tasas como fracciones.
    """

    revenue_cagr: float | None
    ebit_margin_current: float | None
    effective_tax_rate: float | None
    diluted_weighted_shares: float | None  # millones de acciones
    book_debt: float | None  # deuda financiera contable, millones


def _millions(fact: Fact | None) -> float | None:
    """Valor del fact en millones; ``None`` si el fact falta."""
    if fact is None or fact.value is None:
        return None
    return fact.to_scale(Scale.MILLIONS)


def _revenue_cagr(income: list[IncomeStatement]) -> float | None:
    """CAGR de ingresos del primer al último ejercicio, acotado (§7.2).

    ``CAGR = (rev_n / rev_0) ** (1 / n) - 1``, con ``n`` = años entre el
    primer y el último ejercicio disponibles; acotado a ``[-5 %, 25 %]``.

    Returns:
        CAGR acotado, o ``None`` si no hay al menos dos ejercicios con
        ingresos positivos.
    """
    revenues = [_millions(s.revenue) for s in income]
    if len(revenues) < 2:
        return None
    first, last = revenues[0], revenues[-1]
    if first is None or last is None or first <= 0 or last <= 0:
        return None
    years = len(revenues) - 1
    # float(...): typeshed tipa ``float ** float`` como Any (puede dar complex)
    cagr = float((last / first) ** (1.0 / years) - 1.0)
    return max(CAGR_MIN, min(CAGR_MAX, cagr))


def _ebit_margin(income: IncomeStatement) -> float | None:
    """Margen EBIT del ejercicio: ``EBIT / Revenue``.

    Puede ser negativo (empresa en pérdidas); la UI decide cómo mostrarlo.
    """
    revenue = _millions(income.revenue)
    ebit = _millions(income.ebit)
    if revenue is None or revenue == 0 or ebit is None:
        return None
    return ebit / revenue


def _effective_tax_rate(income: list[IncomeStatement]) -> float | None:
    """Tasa impositiva efectiva media, acotada a ``[15 %, 30 %]`` (§7.1).

    Por ejercicio: ``t = IncomeTaxExpense / PretaxIncome``; el default es
    la media de los ejercicios con ambas cifras disponibles.
    """
    rates: list[float] = []
    for statement in income:
        tax = _millions(statement.income_tax_expense)
        pretax = _millions(statement.pretax_income)
        if tax is None or pretax is None or pretax == 0:
            continue
        rates.append(tax / pretax)
    if not rates:
        return None
    average = sum(rates) / len(rates)
    return max(TAX_MIN, min(TAX_MAX, average))


def _book_debt(balance: BalanceSheet) -> float | None:
    """Deuda financiera contable: corto + largo plazo (§7.3).

    Un importe ausente cuenta como 0 si el otro está presente (mismo
    criterio que el puente EV → Equity del motor). Si faltan ambos,
    ``None``: no se inventa.
    """
    short_term = _millions(balance.short_term_debt)
    long_term = _millions(balance.long_term_debt)
    if short_term is None and long_term is None:
        return None
    return (short_term or 0.0) + (long_term or 0.0)


def suggest_defaults(financials: FinancialStatements) -> SuggestedDefaults:
    """Calcula los defaults pre-rellenables desde el 10-K.

    Args:
        financials: estados financieros extraídos (pueden estar vacíos).

    Returns:
        :class:`SuggestedDefaults` con ``None`` en los campos sin datos.
    """
    income = financials.income_statements
    last_income = income[-1] if income else None
    last_balance = financials.balance_sheets[-1] if financials.balance_sheets else None

    return SuggestedDefaults(
        revenue_cagr=_revenue_cagr(income),
        ebit_margin_current=_ebit_margin(last_income) if last_income is not None else None,
        effective_tax_rate=_effective_tax_rate(income),
        diluted_weighted_shares=(
            _millions(last_income.diluted_weighted_shares) if last_income is not None else None
        ),
        book_debt=_book_debt(last_balance) if last_balance is not None else None,
    )


__all__ = [
    "CAGR_MAX",
    "CAGR_MIN",
    "TAX_MAX",
    "TAX_MIN",
    "SuggestedDefaults",
    "suggest_defaults",
]
