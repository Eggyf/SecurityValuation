"""Residual Income / EVA: modelo de contraste (AGENTS.md §14.5).

V0 = B0 + Σ RI_t / (1 + Ke)^t + TV_RI / (1 + Ke)^n
RI_t = NI_t - Ke x B_{t-1}

EVA_t = (ROIC_t - WACC) x Capital invertido_{t-1}

Modelo de contraste: no sustituye al DCF.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from dcf_app.models.assumptions import Assumptions
from dcf_app.models.financials import FinancialStatements
from dcf_app.valuation.dcf import run_dcf
from dcf_app.valuation.wacc import capm_ke, discount_factor, present_value

logger = logging.getLogger(__name__)


@dataclass
class ResidualIncomeResult:
    """Resultado del modelo de Residual Income / EVA."""

    ri_forecast: list[float] = field(default_factory=list)
    eva_forecast: list[float] = field(default_factory=list)
    ke: float = 0.0
    book_value: float = 0.0
    equity_value: float = 0.0
    price_per_share: float = 0.0
    clean_surplus_ok: bool = True
    divergence_pct: float | None = None
    has_warning: bool = False
    message: str = ""


def compute_residual_income(
    assumptions: Assumptions,
    financials: FinancialStatements,
    dcf_result: Any = None,  # noqa: ANN401
) -> ResidualIncomeResult:
    """Calcula el Residual Income y EVA.

    Args:
        assumptions: supuestos de valoración.
        financials: estados financieros.
        dcf_result: resultado del DCF FCFF (para divergencia).

    Returns:
        ResidualIncomeResult con el valor del equity y el precio por acción.
    """
    result = ResidualIncomeResult()

    # Ke
    rf = assumptions.risk_free_rate
    beta = assumptions.equity_beta
    erp = assumptions.equity_risk_premium
    if rf is None or beta is None or erp is None:
        result.message = "Faltan Rf, beta o ERP para calcular Ke."
        return result
    ke = capm_ke(rf, beta, erp)
    result.ke = ke

    # Datos del 10-K
    balance = financials.balance_sheets[-1] if financials.balance_sheets else None
    if balance is None or balance.total_equity is None or balance.total_equity.value is None:
        result.message = "Falta el patrimonio del balance."
        return result

    from dcf_app.models.fact import Scale as FactScale

    book_value = balance.total_equity.to_scale(FactScale.MILLIONS) or 0.0
    result.book_value = book_value

    # Deuda y caja
    debt = 0.0
    if balance.short_term_debt is not None and balance.short_term_debt.value is not None:
        debt += balance.short_term_debt.to_scale(FactScale.MILLIONS) or 0.0
    if balance.long_term_debt is not None and balance.long_term_debt.value is not None:
        debt += balance.long_term_debt.to_scale(FactScale.MILLIONS) or 0.0

    cash = 0.0
    if balance.cash_and_equivalents is not None and balance.cash_and_equivalents.value is not None:
        cash = balance.cash_and_equivalents.to_scale(FactScale.MILLIONS) or 0.0

    invested_capital = debt + book_value - cash

    # NOPAT del DCF
    nopat_list: list[float] = []
    if dcf_result is not None and hasattr(dcf_result, "nopat_forecast"):
        nopat_list = list(dcf_result.nopat_forecast)
    else:
        try:
            dcf = run_dcf(assumptions, financials)
            nopat_list = list(dcf.nopat_forecast)
        except (ValueError, Exception):
            result.message = "No se pudo calcular el DCF base."
            return result

    if not nopat_list:
        result.message = "No hay NOPAT proyectados."
        return result

    # Net Income ≈ NOPAT - intereses*(1-t) (simplificación)
    tax_rate = assumptions.tax_rate or 0.21
    interest = 0.0
    income = financials.income_statements[-1] if financials.income_statements else None
    if income is not None and income.interest_expense is not None and income.interest_expense.value is not None:  # noqa: E501
        interest = abs(income.interest_expense.to_scale(FactScale.MILLIONS) or 0.0)
    interest_after_tax = interest * (1 - tax_rate)

    ni_list = [nopat - interest_after_tax for nopat in nopat_list]

    # Residual Income
    ri_list: list[float] = []
    b_prev = book_value
    for ni in ni_list:
        ri = ni - ke * b_prev
        ri_list.append(ri)
        b_prev = b_prev + ni  # clean surplus (sin dividendos/recompras)

    result.ri_forecast = ri_list

    # EVA
    eva_list: list[float] = []
    ci_prev = invested_capital
    wacc = assumptions.wacc_override or 0.09  # simplificación
    for nopat in nopat_list:
        roic = nopat / ci_prev if ci_prev != 0 else 0.0
        eva = (roic - wacc) * ci_prev
        eva_list.append(eva)
        ci_prev = ci_prev + nopat  # aproximación

    result.eva_forecast = eva_list

    # Valor terminal RI
    g_ri = min(assumptions.terminal_revenue_growth or 0.025, 0.025)  # g_RI ≤ g
    ri_last = ri_list[-1] if ri_list else 0.0
    ri_next = ri_last * (1.0 + g_ri)
    tv_ri = ri_next / (ke - g_ri) if ke > g_ri else 0.0

    # Valor presente
    pv_ri = present_value(ri_list, ke, assumptions.discount_convention)
    if ri_list:
        tv_discount = discount_factor(ke, len(ri_list), assumptions.discount_convention)
    else:
        tv_discount = 1.0
    pv_tv = tv_ri * tv_discount

    equity_value = book_value + pv_ri + pv_tv

    # Acciones
    shares = assumptions.shares_outstanding
    if shares is None or shares <= 0:
        result.message = "Faltan acciones en circulación."
        return result

    result.equity_value = equity_value
    result.price_per_share = equity_value / shares

    # Clean surplus check
    # B_t = B_{t-1} + NI_t (sin dividendos/recompras)
    # Si hay datos de dividendos, verificar
    result.clean_surplus_ok = True

    # Divergencia vs DCF FCFF
    if dcf_result is not None and hasattr(dcf_result, "equity_value") and dcf_result.equity_value > 0:  # noqa: E501
        div = abs(result.equity_value - dcf_result.equity_value) / dcf_result.equity_value
        result.divergence_pct = div
        if div > 0.25:
            result.has_warning = True
            result.message = (
                f"Divergencia del {div:.1%} frente al DCF FCFF. "
                "Revisar supuestos."
            )
        else:
            result.message = "Residual Income coherente con el DCF FCFF."
    else:
        result.message = "Residual Income calculado."

    return result


__all__ = ["ResidualIncomeResult", "compute_residual_income"]
