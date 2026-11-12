"""Implementación de referencia, mínima y determinista, de un DCF FCFF.

Sirve para (1) contrastar cálculos del motor real y (2) generar casos de test
calculados a mano. NO sustituye al motor de `src/dcf_app/valuation/`.

Convenciones: porcentajes como fracciones (0.09 = 9 %), importes en millones.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Inputs:
    revenue0: float                    # ingresos del último año real
    growth: list[float]                # crecimiento por año proyectado
    ebit_margin: float                 # margen EBIT (constante en este ejemplo)
    tax: float                         # tasa impositiva normalizada
    da_pct: float                      # D&A como % de ingresos
    capex_pct: float                   # CapEx como % de ingresos
    nwc_pct_of_delta_rev: float        # ΔNWC = pct × Δingresos
    wacc: float
    g: float                           # crecimiento perpetuo
    cash: float = 0.0
    debt: float = 0.0
    leases: float = 0.0                # solo si se tratan como deuda
    preferred: float = 0.0
    minorities: float = 0.0
    diluted_shares: float = 1.0
    mid_year: bool = False


@dataclass
class Result:
    revenue: list[float] = field(default_factory=list)
    fcff: list[float] = field(default_factory=list)
    discount_factors: list[float] = field(default_factory=list)
    pv_fcff: float = 0.0
    terminal_value: float = 0.0
    pv_terminal: float = 0.0
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    price_per_share: float = 0.0
    tv_share_of_ev: float = 0.0


def run_dcf(i: Inputs) -> Result:
    if i.wacc <= i.g:
        raise ValueError("WACC debe ser mayor que g")
    r = Result()
    prev_rev = i.revenue0
    for k, gr in enumerate(i.growth, start=1):
        rev = prev_rev * (1 + gr)
        ebit = rev * i.ebit_margin
        nopat = ebit * (1 - i.tax)
        da = rev * i.da_pct
        capex = rev * i.capex_pct
        d_nwc = (rev - prev_rev) * i.nwc_pct_of_delta_rev
        fcff = nopat + da - capex - d_nwc
        t = k - 0.5 if i.mid_year else float(k)
        df = 1 / (1 + i.wacc) ** t
        r.revenue.append(rev)
        r.fcff.append(fcff)
        r.discount_factors.append(df)
        r.pv_fcff += fcff * df
        prev_rev = rev
    n = len(i.growth)
    # Valor terminal (Gordon) sobre FCFF_{n+1} = FCFF_n * (1+g). Simplificación:
    # en producción preferir un FCFF terminal normalizado (reinversión = g/ROIC).
    r.terminal_value = r.fcff[-1] * (1 + i.g) / (i.wacc - i.g)
    # Con Gordon y convención de mitad de año, los flujos perpetuos también llegan
    # a mitad de año: el TV se descuenta a n-0.5. (Con múltiplo de salida se
    # descontaría a n, porque el múltiplo valora la empresa a fin de año n.)
    t_tv = n - 0.5 if i.mid_year else float(n)
    r.pv_terminal = r.terminal_value / (1 + i.wacc) ** t_tv
    r.enterprise_value = r.pv_fcff + r.pv_terminal
    r.equity_value = (
        r.enterprise_value + i.cash - i.debt - i.leases - i.preferred - i.minorities
    )
    r.price_per_share = r.equity_value / i.diluted_shares
    r.tv_share_of_ev = r.pv_terminal / r.enterprise_value
    return r


if __name__ == "__main__":
    base = Inputs(
        revenue0=1000, growth=[0.10, 0.08, 0.06, 0.05, 0.04], ebit_margin=0.20,
        tax=0.21, da_pct=0.04, capex_pct=0.05, nwc_pct_of_delta_rev=0.10,
        wacc=0.09, g=0.025, cash=150, debt=400, diluted_shares=100,
    )
    res = run_dcf(base)
    print("rev", [round(x,1) for x in res.revenue])
    print("fcff", [round(x,1) for x in res.fcff])
    print("df", [round(x,4) for x in res.discount_factors])
    print(f"PV_FCFF={res.pv_fcff:.1f} TV={res.terminal_value:.1f} PV_TV={res.pv_terminal:.1f}")
    print(f"EV={res.enterprise_value:.1f}  Equity={res.equity_value:.1f}  "
          f"Precio={res.price_per_share:.2f}  TV%EV={res.tv_share_of_ev:.1%}")
    import dataclasses
    for g, w in [(0.02,0.09),(0.03,0.09),(0.025,0.08),(0.025,0.10)]:
        rr = run_dcf(dataclasses.replace(base, g=g, wacc=w))
        print(f"g={g} wacc={w} -> precio {rr.price_per_share:.2f}")
    rr = run_dcf(dataclasses.replace(base, mid_year=True))
    print("mid-year precio", round(rr.price_per_share,2))
