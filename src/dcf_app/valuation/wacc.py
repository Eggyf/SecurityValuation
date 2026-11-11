"""Cálculo del WACC y factores de descuento (AGENTS.md §7.3 y §7.5).

Funciones puras: mismas entradas → mismas salidas; sin I/O, sin estado
global, sin aleatoriedad (AGENTS.md §8).
"""

from __future__ import annotations

from enum import StrEnum

from dcf_app.models.assumptions import DiscountConvention


class DiscountConventionStr(StrEnum):
    """Convención de descuento (espejo de ``DiscountConvention`` para uso en valuation)."""

    END_OF_YEAR = "end_of_year"
    MID_YEAR = "mid_year"


def capm_ke(
    risk_free_rate: float,
    beta: float,
    equity_risk_premium: float,
) -> float:
    """Coste del equity por CAPM (AGENTS.md §7.3).

    Fórmula:
        Ke = Rf + β x ERP

    Args:
        risk_free_rate: tasa libre de riesgo (fracción).
        beta: beta del equity (apalancada).
        equity_risk_premium: prima de riesgo del mercado (fracción).

    Returns:
        Coste del equity (fracción).
    """
    return risk_free_rate + beta * equity_risk_premium


def cost_of_debt(
    interest_expense: float,
    average_debt: float,
) -> float:
    """Coste de la deuda antes de impuestos (AGENTS.md §7.3).

    Fórmula:
        Kd = Intereses / Deuda media

    Args:
        interest_expense: gasto por intereses del ejercicio (millones).
        average_debt: deuda financiera media (millones).

    Returns:
        Coste de la deuda antes de impuestos (fracción).

    Raises:
        ValueError: si ``average_debt`` es cero o negativo.
    """
    if average_debt <= 0:
        raise ValueError("La deuda media debe ser positiva para calcular Kd.")
    return interest_expense / average_debt


def wacc(
    equity_value: float,
    debt_value: float,
    ke: float,
    kd: float,
    tax_rate: float,
) -> float:
    """WACC (Weighted Average Cost of Capital) (AGENTS.md §7.3).

    Fórmula:
        WACC = E/(D+E) x Ke + D/(D+E) x Kd x (1 - t)

    Args:
        equity_value: valor de mercado del equity (millones).
        debt_value: valor de mercado (o contable) de la deuda (millones).
        ke: coste del equity (fracción).
        kd: coste de la deuda antes de impuestos (fracción).
        tax_rate: tasa impositiva (fracción).

    Returns:
        WACC (fracción).

    Raises:
        ValueError: si ``equity_value + debt_value`` es cero.
    """
    total = equity_value + debt_value
    if total <= 0:
        raise ValueError("El valor total (equity + deuda) debe ser positivo.")
    weight_e = equity_value / total
    weight_d = debt_value / total
    return weight_e * ke + weight_d * kd * (1.0 - tax_rate)


def discount_factor(
    rate: float,
    year: int,
    convention: DiscountConvention | DiscountConventionStr = DiscountConvention.END_OF_YEAR,
) -> float:
    """Factor de descuento para un año dado (AGENTS.md §7.5).

    Fórmula:
        Fin de año:  DF_t = 1 / (1 + r)^t
        Mitad de año: DF_t = 1 / (1 + r)^(t - 0.5)

    Args:
        rate: tasa de descuento (WACC) (fracción).
        year: número de año (≥ 1).
        convention: convención de descuento.

    Returns:
        Factor de descuento.

    Raises:
        ValueError: si ``year < 1``.
    """
    if year < 1:
        raise ValueError("El año debe ser mayor o igual a 1.")
    if isinstance(convention, DiscountConventionStr):
        convention = DiscountConvention(convention.value)
    exponent = year - 0.5 if convention == DiscountConvention.MID_YEAR else float(year)
    return 1.0 / float((1.0 + rate) ** exponent)


def present_value(
    cash_flows: list[float],
    rate: float,
    convention: DiscountConvention | DiscountConventionStr = DiscountConvention.END_OF_YEAR,
) -> float:
    """Valor presente de una serie de flujos de caja (AGENTS.md §7.5).

    Fórmula:
        PV = Σ CF_t x DF_t

    Args:
        cash_flows: flujos de caja por año (millones).
        rate: tasa de descuento (WACC) (fracción).
        convention: convención de descuento.

    Returns:
        Valor presente (millones).
    """
    pv = 0.0
    for t, cf in enumerate(cash_flows, start=1):
        pv += cf * discount_factor(rate, t, convention)
    return pv


def terminal_value_gordon(
    fcff_next: float,
    wacc: float,
    g: float,
) -> float:
    """Valor terminal por Gordon Growth (AGENTS.md §7.4).

    Fórmula:
        TV = FCFF_{n+1} / (WACC - g)

    Args:
        fcff_next: FCFF del año n+1 (millones).
        wacc: WACC (fracción).
        g: crecimiento terminal (fracción).

    Returns:
        Valor terminal (millones).

    Raises:
        ValueError: si ``wacc <= g``.
    """
    if wacc <= g:
        raise ValueError(f"WACC ({wacc:.4f}) debe ser mayor que g ({g:.4f}).")
    return fcff_next / (wacc - g)


def terminal_value_multiple(
    ebitda_terminal: float,
    multiple: float,
) -> float:
    """Valor terminal por múltiplo de salida (AGENTS.md §7.4).

    Fórmula:
        TV = EBITDA_terminal x Múltiplo

    Args:
        ebitda_terminal: EBITDA del último año (millones).
        multiple: múltiplo EV/EBITDA.

    Returns:
        Valor terminal (millones).
    """
    return ebitda_terminal * multiple
