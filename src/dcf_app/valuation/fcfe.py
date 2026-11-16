"""FCFE: flujo de caja libre al accionista (AGENTS.md §14.5).

FCFE = FCFF - Intereses x (1 - t) + Δ Deuda neta
Valor del equity = Σ FCFE_t / (1 + Ke)^t + TV_equity / (1 + Ke)^n

Modelo de contraste: no sustituye al DCF FCFF.
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
class FCFEResult:
    """Resultado del modelo FCFE."""

    fcfe_forecast: list[float] = field(default_factory=list)
    ke: float = 0.0
    terminal_value_equity: float = 0.0
    equity_value: float = 0.0
    price_per_share: float = 0.0
    divergence_pct: float | None = None  # divergencia vs DCF FCFF
    has_warning: bool = False
    message: str = ""


def compute_fcfe(
    assumptions: Assumptions,
    financials: FinancialStatements,
    dcf_result: Any = None,  # noqa: ANN401
) -> FCFEResult:
    """Calcula el FCFE y el valor del equity.

    Args:
        assumptions: supuestos de valoración.
        financials: estados financieros.
        dcf_result: resultado del DCF FCFF (para divergencia).

    Returns:
        FCFEResult con el valor del equity y el precio por acción.
    """
    result = FCFEResult()

    # Ke (coste del equity)
    rf = assumptions.risk_free_rate
    beta = assumptions.equity_beta
    erp = assumptions.equity_risk_premium
    if rf is None or beta is None or erp is None:
        result.message = "Faltan Rf, beta o ERP para calcular Ke."
        return result
    ke = capm_ke(rf, beta, erp)
    result.ke = ke

    # Obtener métricas del 10-K
    income = financials.income_statements[-1] if financials.income_statements else None
    balance = financials.balance_sheets[-1] if financials.balance_sheets else None

    if income is None or balance is None:
        result.message = "Faltan estados financieros."
        return result

    # Deuda y caja
    st_debt = 0.0
    lt_debt = 0.0
    if balance.short_term_debt is not None and balance.short_term_debt.value is not None:
        st_debt = balance.short_term_debt.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) or 0.0  # noqa: E501
    if balance.long_term_debt is not None and balance.long_term_debt.value is not None:
        lt_debt = balance.long_term_debt.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) or 0.0  # noqa: E501
    debt = st_debt + lt_debt

    if balance.cash_and_equivalents is not None and balance.cash_and_equivalents.value is not None:
        balance.cash_and_equivalents.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) or 0.0  # noqa: E501

    # Intereses
    interest = 0.0
    if income.interest_expense is not None and income.interest_expense.value is not None:
        interest = abs(income.interest_expense.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) or 0.0)  # noqa: E501

    tax_rate = assumptions.tax_rate or 0.21
    interest_after_tax = interest * (1 - tax_rate)

    # Deuda media (simplificación: usar deuda final)
    # Ratio D/(D+E) para Δ deuda neta
    equity_val = balance.total_equity
    equity_book = 0.0
    if equity_val is not None and equity_val.value is not None:
        equity_book = equity_val.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) or 0.0  # noqa: E501

    total_capital = debt + equity_book
    debt / total_capital if total_capital > 0 else 0.0

    # FCFF del DCF (si se pasa) o calcular
    fcff_list: list[float] = []
    if dcf_result is not None and hasattr(dcf_result, "fcff_forecast"):
        fcff_list = list(dcf_result.fcff_forecast)
    else:
        # Calcular DCF primero
        try:
            dcf = run_dcf(assumptions, financials)
            fcff_list = list(dcf.fcff_forecast)
        except (ValueError, Exception):
            result.message = "No se pudo calcular el DCF base."
            return result

    if not fcff_list:
        result.message = "No hay FCFF proyectados."
        return result

    # Calcular FCFE para cada año
    # Δ Deuda neta = debt_ratio x Δcapital (aproximación: Δcapital ≈ Δrevenue x nwc_pct, simplificado)  # noqa: E501
    # Para simplificar, asumimos deuda constante (Δdebt = 0) si no hay datos de crecimiento de capital  # noqa: E501
    # En una implementación más sofisticada, se usaría el crecimiento del capital
    fcfe_list: list[float] = []
    for fcff in fcff_list:
        # FCFE = FCFF - Intereses*(1-t) + ΔDeuda
        # Con deuda constante: ΔDeuda = 0
        fcfe = fcff - interest_after_tax
        fcfe_list.append(fcfe)

    result.fcfe_forecast = fcfe_list

    # Terminal value (equity) con Gordon
    g = assumptions.terminal_revenue_growth or 0.025
    if ke <= g:
        result.message = "Ke debe ser mayor que g para el valor terminal."
        return result

    fcfe_last = fcfe_list[-1] if fcfe_list else 0.0
    fcfe_next = fcfe_last * (1.0 + g)
    tv_equity = fcfe_next / (ke - g)
    result.terminal_value_equity = tv_equity

    # Valor presente
    pv_fcfe = present_value(fcfe_list, ke, assumptions.discount_convention)
    if fcfe_list:
        tv_discount = discount_factor(ke, len(fcfe_list), assumptions.discount_convention)
    else:
        tv_discount = 1.0
    pv_tv = tv_equity * tv_discount

    cash_val = 0.0
    if financials.balance_sheets and financials.balance_sheets[-1].cash_and_equivalents is not None:
        c = financials.balance_sheets[-1].cash_and_equivalents.value
        if c is not None:
            cash_val = c
    equity_value = pv_fcfe + pv_tv + cash_val  # simplificado: añadir caja

    # Acciones
    shares = assumptions.shares_outstanding
    if shares is None or shares <= 0:
        result.message = "Faltan acciones en circulación."
        return result

    result.equity_value = equity_value
    result.price_per_share = equity_value / shares

    # Divergencia vs DCF FCFF
    if dcf_result is not None and hasattr(dcf_result, "equity_value") and dcf_result.equity_value > 0:  # noqa: E501
        div = abs(result.equity_value - dcf_result.equity_value) / dcf_result.equity_value
        result.divergence_pct = div
        if div > 0.25:
            result.has_warning = True
            result.message = (
                f"Divergencia del {div:.1%} frente al DCF FCFF. "
                "Revisar supuestos de deuda."
            )
        else:
            result.message = "FCFE coherente con el DCF FCFF."

    return result


__all__ = ["FCFEResult", "compute_fcfe"]
