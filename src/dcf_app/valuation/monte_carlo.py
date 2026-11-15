"""Simulación Monte Carlo del DCF (AGENTS.md §14.3).

Simula miles de DCF variando los supuestos clave para obtener una
distribución de valor en vez de un número único.

Reproducible: numpy.random.default_rng(seed). Mismos inputs y semilla
→ mismos resultados.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from dcf_app.models.assumptions import Assumptions
from dcf_app.models.financials import FinancialStatements
from dcf_app.valuation.dcf import _compute_wacc, run_dcf

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    """Resultado de la simulación Monte Carlo."""

    n_simulations: int = 0
    n_valid: int = 0
    n_discarded: int = 0
    seed: int = 42
    prices: np.ndarray = field(default_factory=lambda: np.array([]))
    mean: float = 0.0
    median: float = 0.0
    p5: float = 0.0
    p25: float = 0.0
    p75: float = 0.0
    p95: float = 0.0
    prob_above_market: float | None = None
    market_price: float | None = None


def simulate(
    assumptions: Assumptions,
    financials: FinancialStatements,
    n: int = 10_000,
    seed: int = 42,
    growth_sd: float = 0.02,
    margin_sd: float = 0.03,
    wacc_sd: float = 0.01,
    g_perp_range: tuple[float, float, float] = (0.015, 0.025, 0.030),
    min_spread: float = 0.01,
    market_price: float | None = None,
) -> MonteCarloResult:
    """Ejecuta la simulación Monte Carlo sobre el DCF.

    Args:
        assumptions: supuestos base de valoración.
        financials: estados financieros.
        n: número de simulaciones.
        seed: semilla para reproducibilidad.
        growth_sd: desviación estándar del desplazamiento del crecimiento.
        margin_sd: desviación estándar del margen EBIT.
        wacc_sd: desviación estándar del WACC.
        g_perp_range: (min, moda, max) del crecimiento terminal (triangular).
        min_spread: mínimo WACC - g (regla de cordura).
        market_price: precio de mercado para calcular P(valor > precio).

    Returns:
        MonteCarloResult con la distribución de precios.
    """
    rng = np.random.default_rng(seed)
    prices: list[float] = []
    discarded = 0

    base_growth = assumptions.initial_revenue_growth or 0.05
    base_margin = assumptions.ebit_margin_target or 0.20
    base_wacc = assumptions.wacc_override

    if base_wacc is None:
        try:
            from dcf_app.valuation.dcf import _compute_historical_metrics

            metrics = _compute_historical_metrics(financials)
            base_wacc = _compute_wacc(assumptions, metrics)
        except (ValueError, KeyError):
            base_wacc = assumptions.risk_free_rate or 0.04
            if assumptions.equity_beta is not None and assumptions.equity_risk_premium is not None:
                base_wacc = (assumptions.risk_free_rate or 0.04) + (assumptions.equity_beta or 1.0) * (  # noqa: E501
                    assumptions.equity_risk_premium or 0.05
                )

    lo_g, mode_g, hi_g = g_perp_range

    for _ in range(n):
        d_growth = float(rng.normal(0, growth_sd))
        margin = float(np.clip(rng.normal(base_margin, margin_sd), 0.01, 0.60))
        wacc = float(np.clip(rng.normal(base_wacc, wacc_sd), 0.03, 0.20))
        g = float(rng.triangular(lo_g, mode_g, hi_g)) if lo_g < hi_g else lo_g

        if g >= wacc - min_spread:
            discarded += 1
            continue

        new_growth = base_growth + d_growth
        new_assumptions = assumptions.model_copy(
            update={
                "initial_revenue_growth": new_growth,
                "ebit_margin_target": margin,
                "terminal_revenue_growth": g,
                "wacc_override": wacc,
            }
        )

        try:
            result = run_dcf(new_assumptions, financials)
            prices.append(result.price_per_share)
        except (ValueError, ZeroDivisionError):
            discarded += 1
            continue

    prices_arr = np.array(prices) if prices else np.array([])

    mc_result = MonteCarloResult(
        n_simulations=n,
        n_valid=len(prices_arr),
        n_discarded=discarded,
        seed=seed,
        prices=prices_arr,
    )

    if len(prices_arr) > 0:
        mc_result.mean = float(np.mean(prices_arr))
        mc_result.median = float(np.median(prices_arr))
        mc_result.p5 = float(np.percentile(prices_arr, 5))
        mc_result.p25 = float(np.percentile(prices_arr, 25))
        mc_result.p75 = float(np.percentile(prices_arr, 75))
        mc_result.p95 = float(np.percentile(prices_arr, 95))

        if market_price is not None and market_price > 0:
            mc_result.prob_above_market = float(np.mean(prices_arr > market_price))
            mc_result.market_price = market_price

    return mc_result


__all__ = ["MonteCarloResult", "simulate"]
