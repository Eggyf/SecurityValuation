"""Reverse DCF: qué descuenta el mercado (AGENTS.md §14.1).

Dado el precio de mercado, resuelve qué parámetro tendría que cumplirse
para que el DCF dé ese precio: crecimiento inicial de ingresos o margen
EBIT objetivo, manteniendo el resto fijo.

Usa ``scipy.optimize.brentq`` sobre ``precio_modelo(x) - precio_mercado``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.optimize import brentq

from dcf_app.models.assumptions import Assumptions
from dcf_app.models.financials import FinancialStatements
from dcf_app.valuation.dcf import run_dcf

logger = logging.getLogger(__name__)

# Rangos de búsqueda razonables
GROWTH_RANGE = (-0.10, 0.50)  # -10% a 50%
MARGIN_RANGE = (0.0, 0.60)  # 0% a 60%


@dataclass
class ReverseDCFResult:
    """Resultado del Reverse DCF."""

    parameter: str  # "growth" o "margin"
    implied_value: float | None  # valor implícito (None si no hay solución)
    market_price: float
    model_price: float | None  # precio del modelo con el valor implícito
    has_solution: bool
    message: str
    historical_comparison: dict[str, Any] | None = None


def _compute_historical_growth(financials: FinancialStatements) -> dict[str, Any]:
    """Calcula CAGR histórico a 3 y 5 años."""
    incomes = financials.income_statements
    if len(incomes) < 2:
        return {"cagr_3y": None, "cagr_5y": None}

    revenues = []
    for inc in incomes:
        if inc.revenue is not None and inc.revenue.value is not None:
            revenues.append(inc.revenue.value)

    if len(revenues) < 2:
        return {"cagr_3y": None, "cagr_5y": None}

    # CAGR a n años
    def cagr(start: float, end: float, years: int) -> float | None:
        if start <= 0 or years <= 0:
            return None
        return float((end / start) ** (1.0 / years) - 1.0)

    n = len(revenues) - 1
    cagr_n = cagr(revenues[0], revenues[-1], n)

    # Para 3 y 5 años, usar los disponibles
    cagr_3y = None
    cagr_5y = None
    if len(revenues) >= 4:
        cagr_3y = cagr(revenues[-4], revenues[-1], 3)
    if len(revenues) >= 6:
        cagr_5y = cagr(revenues[-6], revenues[-1], 5)
    elif len(revenues) >= 2:
        cagr_5y = cagr(revenues[0], revenues[-1], len(revenues) - 1)

    return {"cagr_3y": cagr_3y, "cagr_5y": cagr_5y, "cagr_available": cagr_n}


def _compute_historical_margins(financials: FinancialStatements) -> dict[str, float | None]:
    """Calcula margen EBIT máximo y medio históricos."""
    incomes = financials.income_statements
    margins = []
    for inc in incomes:
        if (
            inc.revenue is not None
            and inc.revenue.value is not None
            and inc.revenue.value != 0
            and inc.ebit is not None
            and inc.ebit.value is not None
        ):
            margins.append(inc.ebit.value / inc.revenue.value)

    if not margins:
        return {"max_margin": None, "avg_margin": None, "min_margin": None}

    return {
        "max_margin": max(margins),
        "avg_margin": sum(margins) / len(margins),
        "min_margin": min(margins),
    }


def reverse_dcf_growth(
    assumptions: Assumptions,
    financials: FinancialStatements,
    market_price: float,
    growth_range: tuple[float, float] = GROWTH_RANGE,
) -> ReverseDCFResult:
    """Resuelve el crecimiento inicial de ingresos implícito en el precio de mercado.

    Args:
        assumptions: supuestos de valoración (se copian, no se modifican).
        financials: estados financieros.
        market_price: precio de mercado por acción.
        growth_range: rango de búsqueda (min, max).

    Returns:
        ReverseDCFResult con el crecimiento implícito.
    """
    if market_price <= 0:
        return ReverseDCFResult(
            parameter="growth",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="El precio de mercado debe ser positivo.",
        )

    def model_price_for_growth(g: float) -> float:
        """Precio del modelo para un crecimiento inicial dado."""
        new_assumptions = assumptions.model_copy(update={"initial_revenue_growth": g})
        try:
            result = run_dcf(new_assumptions, financials)
            return result.price_per_share
        except (ValueError, ZeroDivisionError):
            return float("nan")

    def f(g: float) -> float:
        return model_price_for_growth(g) - market_price

    # Verificar cambio de signo
    try:
        f_low = f(growth_range[0])
        f_high = f(growth_range[1])
    except Exception:
        return ReverseDCFResult(
            parameter="growth",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="Error evaluando el modelo en el rango de búsqueda.",
        )

    if np.isnan(f_low) or np.isnan(f_high):
        return ReverseDCFResult(
            parameter="growth",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="El modelo no produce valores válidos en el rango de búsqueda.",
        )

    if f_low * f_high > 0:
        # Sin cambio de signo
        if f_low > 0:
            msg = (
                f"El mercado descuenta menos del {growth_range[0]:.1%} de crecimiento: "
                f"con crecimiento del {growth_range[0]:.1%} el modelo da "
                f"${f_low + market_price:.2f}, superior al precio de mercado "
                f"(${market_price:.2f})."
            )
        else:
            msg = (
                f"El mercado descuenta más del {growth_range[1]:.1%} de crecimiento: "
                f"con crecimiento del {growth_range[1]:.1%} el modelo da "
                f"${f_high + market_price:.2f}, inferior al precio de mercado "
                f"(${market_price:.2f})."
            )
        return ReverseDCFResult(
            parameter="growth",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message=msg,
        )

    # Resolver con brentq
    try:
        implied = brentq(f, growth_range[0], growth_range[1], xtol=1e-6, maxiter=100)
    except ValueError:
        return ReverseDCFResult(
            parameter="growth",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="No se pudo encontrar solución numérica.",
        )

    # Verificar
    model_price = model_price_for_growth(implied)

    hist = _compute_historical_growth(financials)
    hist["margins"] = _compute_historical_margins(financials)

    # Lectura neutral
    cagr_3y = hist.get("cagr_3y")
    if cagr_3y is not None:
        if implied > cagr_3y + 0.02:
            reading = (
                f"El mercado descuenta un crecimiento del {implied:.1%}, "
                f"superior al CAGR histórico de 3 años ({cagr_3y:.1%})."
            )
        elif implied < cagr_3y - 0.02:
            reading = (
                f"El mercado descuenta un crecimiento del {implied:.1%}, "
                f"inferior al CAGR histórico de 3 años ({cagr_3y:.1%})."
            )
        else:
            reading = (
                f"El mercado descuenta un crecimiento del {implied:.1%}, "
                f"en línea con el CAGR histórico de 3 años ({cagr_3y:.1%})."
            )
    else:
        reading = f"El mercado descuenta un crecimiento del {implied:.1%}."

    return ReverseDCFResult(
        parameter="growth",
        implied_value=implied,
        market_price=market_price,
        model_price=model_price,
        has_solution=True,
        message=reading,
        historical_comparison=hist,
    )


def reverse_dcf_margin(
    assumptions: Assumptions,
    financials: FinancialStatements,
    market_price: float,
    margin_range: tuple[float, float] = MARGIN_RANGE,
) -> ReverseDCFResult:
    """Resuelve el margen EBIT objetivo implícito en el precio de mercado.

    Args:
        assumptions: supuestos de valoración (se copian, no se modifican).
        financials: estados financieros.
        market_price: precio de mercado por acción.
        margin_range: rango de búsqueda (min, max).

    Returns:
        ReverseDCFResult con el margen implícito.
    """
    if market_price <= 0:
        return ReverseDCFResult(
            parameter="margin",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="El precio de mercado debe ser positivo.",
        )

    def model_price_for_margin(m: float) -> float:
        """Precio del modelo para un margen EBIT objetivo dado."""
        new_assumptions = assumptions.model_copy(update={"ebit_margin_target": m})
        try:
            result = run_dcf(new_assumptions, financials)
            return result.price_per_share
        except (ValueError, ZeroDivisionError):
            return float("nan")

    def f(m: float) -> float:
        return model_price_for_margin(m) - market_price

    try:
        f_low = f(margin_range[0])
        f_high = f(margin_range[1])
    except Exception:
        return ReverseDCFResult(
            parameter="margin",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="Error evaluando el modelo en el rango de búsqueda.",
        )

    if np.isnan(f_low) or np.isnan(f_high):
        return ReverseDCFResult(
            parameter="margin",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="El modelo no produce valores válidos en el rango de búsqueda.",
        )

    if f_low * f_high > 0:
        if f_low > 0:
            msg = (
                f"El mercado descuenta un margen inferior al {margin_range[0]:.1%}: "
                f"con margen del {margin_range[0]:.1%} el modelo da "
                f"${f_low + market_price:.2f}, superior al precio de mercado "
                f"(${market_price:.2f})."
            )
        else:
            msg = (
                f"El mercado descuenta un margen superior al {margin_range[1]:.1%}: "
                f"con margen del {margin_range[1]:.1%} el modelo da "
                f"${f_high + market_price:.2f}, inferior al precio de mercado "
                f"(${market_price:.2f})."
            )
        return ReverseDCFResult(
            parameter="margin",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message=msg,
        )

    try:
        implied = brentq(f, margin_range[0], margin_range[1], xtol=1e-6, maxiter=100)
    except ValueError:
        return ReverseDCFResult(
            parameter="margin",
            implied_value=None,
            market_price=market_price,
            model_price=None,
            has_solution=False,
            message="No se pudo encontrar solución numérica.",
        )

    model_price = model_price_for_margin(implied)

    hist = _compute_historical_margins(financials)

    max_margin = hist.get("max_margin")
    if max_margin is not None:
        if implied > max_margin + 0.02:
            reading = (
                f"El mercado descuenta un margen EBIT del {implied:.1%}, "
                f"superior al máximo histórico ({max_margin:.1%})."
            )
        elif implied < max_margin - 0.02:
            reading = (
                f"El mercado descuenta un margen EBIT del {implied:.1%}, "
                f"inferior al máximo histórico ({max_margin:.1%})."
            )
        else:
            reading = (
                f"El mercado descuenta un margen EBIT del {implied:.1%}, "
                f"en línea con el máximo histórico ({max_margin:.1%})."
            )
    else:
        reading = f"El mercado descuenta un margen EBIT del {implied:.1%}."

    return ReverseDCFResult(
        parameter="margin",
        implied_value=implied,
        market_price=market_price,
        model_price=model_price,
        has_solution=True,
        message=reading,
        historical_comparison=hist,
    )


__all__ = [
    "GROWTH_RANGE",
    "MARGIN_RANGE",
    "ReverseDCFResult",
    "reverse_dcf_growth",
    "reverse_dcf_margin",
]
