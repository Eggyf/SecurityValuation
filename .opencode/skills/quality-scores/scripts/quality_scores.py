"""Referencia de Piotroski F-Score, Altman Z (3 variantes) y Beneish M (8 variables).

Cada función devuelve valor + desglose por componente. Entradas como floats en la
misma escala. NO aplica a empresas financieras (Altman, Beneish, Piotroski pierden
sentido con balances bancarios).
"""
from __future__ import annotations

from dataclasses import dataclass


# ------------------------------------------------------------------ Piotroski
@dataclass
class Year:
    net_income: float
    cfo: float
    total_assets: float
    long_term_debt: float
    current_assets: float
    current_liabilities: float
    shares_outstanding: float
    revenue: float
    gross_profit: float


def piotroski(cur: Year, prev: Year, prev_prev_total_assets: float) -> dict:
    """9 criterios binarios. `prev_prev_total_assets` = activos totales de t-2
    (para ROA del año previo sobre activos iniciales)."""
    roa = cur.net_income / prev.total_assets
    roa_prev = prev.net_income / prev_prev_total_assets
    lev = cur.long_term_debt / ((cur.total_assets + prev.total_assets) / 2)
    lev_prev = prev.long_term_debt / prev.total_assets
    cr = cur.current_assets / cur.current_liabilities
    cr_prev = prev.current_assets / prev.current_liabilities
    gm = cur.gross_profit / cur.revenue
    gm_prev = prev.gross_profit / prev.revenue
    at = cur.revenue / prev.total_assets
    at_prev = prev.revenue / prev_prev_total_assets
    parts = {
        "ROA > 0": roa > 0,
        "CFO > 0": cur.cfo > 0,
        "ΔROA > 0": roa > roa_prev,
        "CFO > Beneficio neto": cur.cfo > cur.net_income,
        "Δ Apalancamiento < 0": lev < lev_prev,
        "Δ Ratio corriente > 0": cr > cr_prev,
        "Sin emisión de acciones": cur.shares_outstanding <= prev.shares_outstanding,
        "Δ Margen bruto > 0": gm > gm_prev,
        "Δ Rotación de activos > 0": at > at_prev,
    }
    return {"score": sum(parts.values()), "components": parts}


# --------------------------------------------------------------------- Altman
def altman(variant: str, wc: float, re: float, ebit: float, equity: float,
           sales: float, total_assets: float, total_liabilities: float) -> dict:
    """variant: 'Z' (cotizada manufacturera; `equity` = capitalización de mercado),
    'Zprime' (privada; `equity` = valor contable) o 'Zdoubleprime' (no manufacturera
    / emergentes; `equity` = valor contable). Sin la constante de mercados emergentes."""
    x1, x2, x3 = wc / total_assets, re / total_assets, ebit / total_assets
    x4 = equity / total_liabilities
    x5 = sales / total_assets
    if variant == "Z":
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        zones = (1.81, 2.99)
    elif variant == "Zprime":
        z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
        zones = (1.23, 2.9)
    elif variant == "Zdoubleprime":
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        zones = (1.1, 2.6)
    else:
        raise ValueError("variante desconocida")
    zone = "distress" if z < zones[0] else "safe" if z > zones[1] else "grey"
    return {"z": z, "zone": zone, "zones": zones,
            "components": {"X1": x1, "X2": x2, "X3": x3, "X4": x4, "X5": x5}}


# -------------------------------------------------------------------- Beneish
@dataclass
class BYear:
    receivables: float
    revenue: float
    cogs: float
    current_assets: float
    ppe_net: float
    total_assets: float
    depreciation: float
    sga: float
    current_liabilities: float
    long_term_debt: float
    net_income_cont_ops: float
    cfo: float


def beneish(cur: BYear, prev: BYear, threshold: float = -1.78) -> dict:
    """M-Score de 8 variables. TATA simplificado = (NI operaciones continuas − CFO)/AT.
    Umbral habitual −1,78 (más sensible); −2,22 es menos conservador."""
    gm = lambda y: (y.revenue - y.cogs) / y.revenue  # noqa: E731
    dsri = (cur.receivables / cur.revenue) / (prev.receivables / prev.revenue)
    gmi = gm(prev) / gm(cur)
    aqi = (1 - (cur.current_assets + cur.ppe_net) / cur.total_assets) / (
        1 - (prev.current_assets + prev.ppe_net) / prev.total_assets)
    sgi = cur.revenue / prev.revenue
    depi = (prev.depreciation / (prev.depreciation + prev.ppe_net)) / (
        cur.depreciation / (cur.depreciation + cur.ppe_net))
    sgai = (cur.sga / cur.revenue) / (prev.sga / prev.revenue)
    lvgi = ((cur.current_liabilities + cur.long_term_debt) / cur.total_assets) / (
        (prev.current_liabilities + prev.long_term_debt) / prev.total_assets)
    tata = (cur.net_income_cont_ops - cur.cfo) / cur.total_assets
    m = (-4.84 + 0.920 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi
         + 0.115 * depi - 0.172 * sgai + 4.679 * tata - 0.327 * lvgi)
    return {"m": m, "flag": m > threshold, "threshold": threshold,
            "components": dict(DSRI=dsri, GMI=gmi, AQI=aqi, SGI=sgi, DEPI=depi,
                               SGAI=sgai, LVGI=lvgi, TATA=tata)}


# -------------------------------------------------------- Calidad de beneficios
def earnings_quality(net_income: float, cfo: float, avg_total_assets: float) -> dict:
    return {"cfo_to_net_income": cfo / net_income if net_income else None,
            "accruals_ratio": (net_income - cfo) / avg_total_assets}


if __name__ == "__main__":
    # Autotest con casos construidos a mano
    # Beneish: dos años idénticos => todos los índices = 1 (DSRI=GMI=AQI=SGI=DEPI=SGAI=LVGI=1)
    y = BYear(100, 1000, 600, 500, 400, 1200, 50, 150, 300, 200, 80, 80)
    r = beneish(y, y)
    esperado = (-4.84 + 0.920 + 0.528 + 0.404 + 0.892 + 0.115 - 0.172 + 4.679 * 0 - 0.327)
    assert abs(r["m"] - esperado) < 1e-9, r
    # Altman Z' con valores simples: X1=.2 X2=.3 X3=.1 X4=.5 X5=1
    a = altman("Zprime", wc=20, re=30, ebit=10, equity=50, sales=100,
               total_assets=100, total_liabilities=100)
    z_esp = 0.717 * .2 + 0.847 * .3 + 3.107 * .1 + 0.420 * .5 + 0.998 * 1
    assert abs(a["z"] - z_esp) < 1e-9, a
    # Piotroski: año mejora en todo => 9
    prev = Year(50, 60, 1000, 300, 400, 300, 100, 800, 300)
    cur = Year(100, 130, 1050, 250, 450, 300, 100, 950, 400)
    p = piotroski(cur, prev, prev_prev_total_assets=950)
    assert p["score"] == 9, p
    print("autotests OK:", round(r["m"], 3), round(a["z"], 3), p["score"])
