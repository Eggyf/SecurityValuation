"""Reverse DCF: qué crecimiento inicial de ingresos descuenta el precio de mercado."""
from __future__ import annotations

import dataclasses

from scipy.optimize import brentq

from dcf_reference import Inputs, run_dcf


def with_initial_growth(base: Inputs, g0: float) -> Inputs:
    """Fade lineal desde g0 hasta g (perpetuo) a lo largo del horizonte."""
    n = len(base.growth)
    path = [g0 + (base.g - g0) * (t / n) for t in range(1, n + 1)]
    return dataclasses.replace(base, growth=path)


def implied_initial_growth(base: Inputs, market_price: float,
                           lo: float = -0.10, hi: float = 0.40) -> float | None:
    f = lambda x: run_dcf(with_initial_growth(base, x)).price_per_share - market_price  # noqa: E731
    if f(lo) * f(hi) > 0:
        return None  # sin solución en el rango: informar, no inventar
    return brentq(f, lo, hi, xtol=1e-10)


if __name__ == "__main__":
    base = Inputs(revenue0=1000, growth=[0.0] * 5, ebit_margin=0.20, tax=0.21,
                  da_pct=0.04, capex_pct=0.05, nwc_pct_of_delta_rev=0.10,
                  wacc=0.09, g=0.025, cash=150, debt=400, diluted_shares=100)
    # Round-trip: fabricar un precio con g0 conocido y recuperarlo
    true_g0 = 0.12
    price = run_dcf(with_initial_growth(base, true_g0)).price_per_share
    found = implied_initial_growth(base, price)
    assert found is not None and abs(found - true_g0) < 1e-6, found
    # Precio imposible => None
    assert implied_initial_growth(base, 1e9) is None
    print(f"round-trip OK: precio={price:.2f}, g0 recuperado={found:.4%}")
