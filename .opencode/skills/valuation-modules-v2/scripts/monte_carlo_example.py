"""Monte Carlo sobre el DCF. Versión sencilla (bucle), suficiente como referencia."""
from __future__ import annotations

import dataclasses

import numpy as np

from dcf_reference import Inputs, run_dcf


def simulate(base: Inputs, n: int = 10_000, seed: int = 42,
             g_sd: float = 0.02, margin_sd: float = 0.03, wacc_sd: float = 0.01,
             g_perp_range: tuple[float, float, float] = (0.015, 0.025, 0.030),
             min_spread: float = 0.01) -> dict:
    rng = np.random.default_rng(seed)
    prices: list[float] = []
    discarded = 0
    for _ in range(n):
        d_growth = rng.normal(0, g_sd)
        margin = float(np.clip(rng.normal(base.ebit_margin, margin_sd), 0.01, 0.6))
        wacc = float(np.clip(rng.normal(base.wacc, wacc_sd), 0.03, 0.2))
        lo_g, mode_g, hi_g = g_perp_range
        # triangular exige lo < hi; con rango degenerado, g es constante
        g = float(rng.triangular(lo_g, mode_g, hi_g)) if lo_g < hi_g else lo_g
        if g >= wacc - min_spread:          # regla de cordura: WACC - g >= 1 pp
            discarded += 1
            continue
        sim = dataclasses.replace(
            base, growth=[x + d_growth for x in base.growth],
            ebit_margin=margin, wacc=wacc, g=g)
        prices.append(run_dcf(sim).price_per_share)
    p = np.array(prices)
    return {
        "n_valid": len(p), "n_discarded": discarded, "mean": p.mean(),
        "median": float(np.median(p)),
        "p5": float(np.percentile(p, 5)), "p25": float(np.percentile(p, 25)),
        "p75": float(np.percentile(p, 75)), "p95": float(np.percentile(p, 95)),
        "prices": p,
    }


if __name__ == "__main__":
    base = Inputs(revenue0=1000, growth=[0.10, 0.08, 0.06, 0.05, 0.04],
                  ebit_margin=0.20, tax=0.21, da_pct=0.04, capex_pct=0.05,
                  nwc_pct_of_delta_rev=0.10, wacc=0.09, g=0.025,
                  cash=150, debt=400, diluted_shares=100)
    a = simulate(base, n=2000, seed=7)
    b = simulate(base, n=2000, seed=7)
    assert np.allclose(a["prices"], b["prices"]), "misma semilla => mismo resultado"
    # Con varianza cero (y g degenerado) reproduce el DCF determinista
    z = simulate(base, n=50, seed=1, g_sd=0, margin_sd=0, wacc_sd=0,
                 g_perp_range=(0.025, 0.025, 0.025))
    det = run_dcf(base).price_per_share
    assert np.allclose(z["prices"], det), (z["prices"][:3], det)
    assert a["p5"] < a["median"] < a["p95"]
    print(f"OK. Determinista={det:.2f}  MC mediana={a['median']:.2f}  "
          f"P5-P95=({a['p5']:.2f}, {a['p95']:.2f})  descartadas={a['n_discarded']}")
