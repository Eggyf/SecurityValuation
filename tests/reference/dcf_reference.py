"""Referencia independiente del motor DCF (AGENTS.md §9, skill finance-testing).

Implementación independiente del motor real, escrita a partir de
docs/methodology.md SIN copiar código de src/dcf_app/valuation/.
Se usa para contrastar el motor real en tests.

Convenciones: porcentajes como fracciones, importes en millones.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RefInputs:
    """Entradas del DCF de referencia."""

    revenue0: float  # ingresos del último año (millones)
    growth_initial: float  # crecimiento inicial (fracción)
    growth_terminal: float  # crecimiento terminal g (fracción)
    margin_current: float  # margen EBIT actual (fracción)
    margin_target: float  # margen EBIT objetivo (fracción)
    tax_rate: float  # tasa impositiva normalizada (fracción)
    da_pct: float  # D&A como % de ingresos
    capex_pct: float  # CapEx como % de ingresos
    nwc_pct: float  # NWC como % de Δingresos
    wacc: float  # WACC (fracción)
    g: float  # crecimiento perpetuo (fracción)
    cash: float = 0.0  # caja (millones)
    short_term_inv: float = 0.0  # inversiones CP (millones)
    debt: float = 0.0  # deuda financiera (millones)
    leases: float = 0.0  # leases financieros (millones)
    preferred: float = 0.0  # acciones preferentes (millones)
    nci: float = 0.0  # intereses minoritarios (millones)
    shares: float = 1.0  # acciones diluidas (millones)
    horizon: int = 5
    base_revenue: float | None = None
    mid_year: bool = False
    roic_terminal: float | None = None  # None → usa WACC
    terminal_method: str = "gordon"  # "gordon" o "multiple"
    exit_multiple: float | None = None


@dataclass
class RefResult:
    """Resultado del DCF de referencia."""

    revenue: list[float] = field(default_factory=list)
    ebit_margin: list[float] = field(default_factory=list)
    ebit: list[float] = field(default_factory=list)
    nopat: list[float] = field(default_factory=list)
    da: list[float] = field(default_factory=list)
    capex: list[float] = field(default_factory=list)
    delta_nwc: list[float] = field(default_factory=list)
    fcff: list[float] = field(default_factory=list)
    discount_factors: list[float] = field(default_factory=list)
    pv_fcff: float = 0.0
    terminal_value: float = 0.0
    pv_terminal: float = 0.0
    enterprise_value: float = 0.0
    equity_value: float = 0.0
    price_per_share: float = 0.0
    tv_share_of_ev: float = 0.0
    reinvestment_rate: float = 0.0


def run_ref_dcf(inp: RefInputs) -> RefResult:
    """Ejecuta el DCF de referencia (implementación independiente).

    Fórmulas (docs/methodology.md):
    - Fade: g_t = g0 + (g - g0) * t / max(n-1, 1)
    - Revenue_t = Revenue_{t-1} * (1 + g_t)
    - Margin_t = m0 + (m_target - m0) * t / max(n-1, 1)
    - EBIT = Revenue * margin
    - NOPAT = EBIT * (1 - tax)
    - D&A = Revenue * da_pct
    - CapEx = Revenue * capex_pct
    - ΔNWC = (Revenue_t - Revenue_{t-1}) * nwc_pct
    - FCFF = NOPAT + D&A - CapEx - ΔNWC
    - Terminal: NOPAT_(n+1) = NOPAT_n * (1+g); reinvestment = g/ROIC; FCFF_(n+1) = NOPAT_(n+1) * (1-reinv)
    - TV = FCFF_(n+1) / (WACC - g)
    - DF_t = 1/(1+WACC)^t (fin de año) o 1/(1+WACC)^(t-0.5) (mitad de año)
    """
    if inp.wacc <= inp.g:
        raise ValueError("WACC debe ser mayor que g")

    r = RefResult()
    roic = inp.roic_terminal if inp.roic_terminal is not None else inp.wacc
    reinv = inp.g / roic if roic > 0 else 0.0
    reinv = min(reinv, 1.0)
    r.reinvestment_rate = reinv

    prev_rev = inp.revenue0
    denom = max(inp.horizon - 1, 1)
    for t in range(inp.horizon):
        growth = inp.growth_initial + (inp.growth_terminal - inp.growth_initial) * t / denom
        margin = inp.margin_current + (inp.margin_target - inp.margin_current) * t / denom
        rev = prev_rev * (1 + growth)
        ebit = rev * margin
        nopat = ebit * (1 - inp.tax_rate)
        da = rev * inp.da_pct
        capex = rev * inp.capex_pct
        d_nwc = (rev - prev_rev) * inp.nwc_pct
        fcff = nopat + da - capex - d_nwc

        if inp.mid_year:
            t_disc = t + 1 - 0.5
        else:
            t_disc = t + 1
        df = 1.0 / (1 + inp.wacc) ** t_disc

        r.revenue.append(rev)
        r.ebit_margin.append(margin)
        r.ebit.append(ebit)
        r.nopat.append(nopat)
        r.da.append(da)
        r.capex.append(capex)
        r.delta_nwc.append(d_nwc)
        r.fcff.append(fcff)
        r.discount_factors.append(df)
        r.pv_fcff += fcff * df
        prev_rev = rev

    n = inp.horizon
    nopat_last = r.nopat[-1]
    nopat_next = nopat_last * (1 + inp.g)
    fcff_next = nopat_next * (1 - reinv)

    if inp.terminal_method == "gordon":
        r.terminal_value = fcff_next / (inp.wacc - inp.g)
    elif inp.terminal_method == "multiple" and inp.exit_multiple is not None:
        ebitda_last = r.ebit[-1] + r.da[-1]
        r.terminal_value = ebitda_last * inp.exit_multiple

    if inp.mid_year:
        t_tv = n - 0.5
    else:
        t_tv = float(n)
    r.pv_terminal = r.terminal_value / (1 + inp.wacc) ** t_tv

    r.enterprise_value = r.pv_fcff + r.pv_terminal
    r.equity_value = (
        r.enterprise_value + inp.cash + inp.short_term_inv - inp.debt - inp.leases - inp.preferred - inp.nci
    )
    r.price_per_share = r.equity_value / inp.shares
    r.tv_share_of_ev = r.pv_terminal / r.enterprise_value if r.enterprise_value != 0 else 0.0

    return r


# FCFF año 1 calculado a mano (caso base):
# Revenue_1 = 1000 * (1 + 0.10) = 1100
# EBIT_1 = 1100 * 0.20 = 220
# NOPAT_1 = 220 * (1 - 0.21) = 173.8
# D&A_1 = 1100 * 0.04 = 44
# CapEx_1 = 1100 * 0.05 = 55
# ΔNWC_1 = (1100 - 1000) * 0.10 = 10
# FCFF_1 = 173.8 + 44 - 55 - 10 = 152.8


__all__ = ["RefInputs", "RefResult", "run_ref_dcf"]