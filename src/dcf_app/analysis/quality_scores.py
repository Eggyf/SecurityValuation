"""Scores de calidad y ratios financieros (AGENTS.md §14.2).

Piotroski F-Score, Altman Z-Score (3 variantes), Beneish M-Score,
calidad de beneficios, DuPont, ROIC y ratios operativos.

Reglas:
- No aplican a empresas financieras (bancos, aseguradoras).
- Devuelve siempre valor + desglose por componente + fórmula.
- Si falta una entrada, el score es None con la lista de entradas faltantes.
- Son señales de alerta, no veredictos de inversión.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes de entrada
# ---------------------------------------------------------------------------
@dataclass
class YearData:
    """Datos de un ejercicio para Piotroski y ratios."""

    net_income: float | None = None
    cfo: float | None = None
    total_assets: float | None = None
    total_equity: float | None = None
    cash: float | None = None
    long_term_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    shares_outstanding: float | None = None
    revenue: float | None = None
    gross_profit: float | None = None
    cogs: float | None = None
    ebit: float | None = None
    interest_expense: float | None = None
    accounts_receivable: float | None = None
    inventory: float | None = None
    accounts_payable: float | None = None
    depreciation: float | None = None
    ppe_net: float | None = None
    sga: float | None = None
    retained_earnings: float | None = None
    total_liabilities: float | None = None
    current_liabilities_total: float | None = None


@dataclass
class BeneishYear:
    """Datos de un ejercicio para Beneish M-Score."""

    receivables: float | None = None
    revenue: float | None = None
    cogs: float | None = None
    current_assets: float | None = None
    ppe_net: float | None = None
    total_assets: float | None = None
    depreciation: float | None = None
    sga: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    net_income_cont_ops: float | None = None
    cfo: float | None = None


@dataclass
class ScoreResult:
    """Resultado genérico de un score o ratio."""

    value: float | None = None
    components: dict[str, Any] = field(default_factory=dict)
    formula: str = ""
    missing: list[str] = field(default_factory=list)
    applicable: bool = True
    note: str = ""


# ---------------------------------------------------------------------------
# Piotroski F-Score (0-9)
# ---------------------------------------------------------------------------
def piotroski_f_score(
    cur: YearData, prev: YearData, prev_prev_total_assets: float | None
) -> ScoreResult:
    """Piotroski F-Score: 9 criterios binarios.

    Necesita dos ejercicios (y activos de t-2 para el ROA del año previo).
    """
    missing: list[str] = []

    # Verificar datos necesarios
    if cur.net_income is None or prev.total_assets is None:
        missing.append("net_income o total_assets (prev)")
    if cur.cfo is None:
        missing.append("cfo")
    if prev.net_income is None or prev_prev_total_assets is None:
        missing.append("net_income (prev) o total_assets (t-2)")
    if cur.long_term_debt is None or prev.long_term_debt is None:
        missing.append("long_term_debt")
    if cur.current_assets is None or cur.current_liabilities is None:
        missing.append("current_assets o current_liabilities")
    if prev.current_assets is None or prev.current_liabilities is None:
        missing.append("current_assets (prev) o current_liabilities (prev)")
    if cur.shares_outstanding is None or prev.shares_outstanding is None:
        missing.append("shares_outstanding")
    if cur.gross_profit is None or cur.revenue is None:
        missing.append("gross_profit o revenue")
    if prev.gross_profit is None or prev.revenue is None:
        missing.append("gross_profit (prev) o revenue (prev)")
    if prev.total_assets is None:
        missing.append("total_assets (prev)")

    if missing:
        return ScoreResult(
            value=None, missing=missing, formula="F-Score = suma de 9 criterios binarios"
        )

    # Calcular métricas
    roa = cur.net_income / prev.total_assets  # type: ignore[operator]
    roa_prev = prev.net_income / prev_prev_total_assets  # type: ignore[operator]
    lev = cur.long_term_debt / ((cur.total_assets + prev.total_assets) / 2)  # type: ignore[operator]
    lev_prev = prev.long_term_debt / prev.total_assets  # type: ignore[operator]
    cr = cur.current_assets / cur.current_liabilities  # type: ignore[operator]
    cr_prev = prev.current_assets / prev.current_liabilities  # type: ignore[operator]
    gm = cur.gross_profit / cur.revenue  # type: ignore[operator]
    gm_prev = prev.gross_profit / prev.revenue  # type: ignore[operator]
    at = cur.revenue / prev.total_assets  # type: ignore[operator]
    at_prev = prev.revenue / prev_prev_total_assets  # type: ignore[operator]

    components = {
        "ROA > 0": roa > 0,
        "CFO > 0": cur.cfo > 0,  # type: ignore[operator]
        "ΔROA > 0": roa > roa_prev,
        "CFO > NI": cur.cfo > cur.net_income,  # type: ignore[operator]
        "↓ Apalancamiento": lev < lev_prev,
        "↑ Ratio corriente": cr > cr_prev,
        "Sin emisión acciones": cur.shares_outstanding <= prev.shares_outstanding,  # type: ignore[operator]
        "↑ Margen bruto": gm > gm_prev,
        "↑ Rotación activos": at > at_prev,
    }

    score = sum(1 for v in components.values() if v)

    return ScoreResult(
        value=float(score),
        components=components,
        formula="F-Score = suma de 9 criterios binarios (0-9)",
    )


# ---------------------------------------------------------------------------
# Altman Z-Score
# ---------------------------------------------------------------------------
def altman_z_score(
    variant: str,
    working_capital: float | None,
    retained_earnings: float | None,
    ebit: float | None,
    equity: float | None,
    sales: float | None,
    total_assets: float | None,
    total_liabilities: float | None,
) -> ScoreResult:
    """Altman Z-Score con 3 variantes.

    variant: 'Z' (cotizada manufacturera), 'Zprime' (privada),
             'Zdoubleprime' (no manufacturera / emergentes).
    """
    missing: list[str] = []
    if working_capital is None:
        missing.append("working_capital")
    if retained_earnings is None:
        missing.append("retained_earnings")
    if ebit is None:
        missing.append("ebit")
    if equity is None:
        missing.append("equity")
    if total_assets is None or total_assets == 0:
        missing.append("total_assets")
    if total_liabilities is None or total_liabilities == 0:
        missing.append("total_liabilities")
    if variant in ("Z", "Zprime") and sales is None:
        missing.append("sales")

    if missing:
        return ScoreResult(value=None, missing=missing, formula="Z = variante * (X1..X5)")

    x1 = working_capital / total_assets  # type: ignore[operator]
    x2 = retained_earnings / total_assets  # type: ignore[operator]
    x3 = ebit / total_assets  # type: ignore[operator]
    x4 = equity / total_liabilities  # type: ignore[operator]

    if variant == "Z":
        x5 = sales / total_assets  # type: ignore[operator]
        z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
        zones = (1.81, 2.99)
        formula = "Z = 1.2·X1 + 1.4·X2 + 3.3·X3 + 0.6·X4 + 1.0·X5"
    elif variant == "Zprime":
        x5 = sales / total_assets  # type: ignore[operator]
        z = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5
        zones = (1.23, 2.90)
        formula = "Z' = 0.717·X1 + 0.847·X2 + 3.107·X3 + 0.420·X4 + 0.998·X5"
    elif variant == "Zdoubleprime":
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        zones = (1.10, 2.60)
        formula = "Z'' = 6.56·X1 + 3.26·X2 + 6.72·X3 + 1.05·X4"
        x5 = None
    else:
        return ScoreResult(value=None, missing=["variante desconocida"], formula="")

    if z < zones[0]:
        zone = "distress"
    elif z > zones[1]:
        zone = "safe"
    else:
        zone = "grey"

    components: dict[str, Any] = {"X1": x1, "X2": x2, "X3": x3, "X4": x4}
    if x5 is not None:
        components["X5"] = x5
    components["zone"] = zone
    components["zones"] = zones

    return ScoreResult(
        value=z,
        components=components,
        formula=formula,
        note=f"Variante {variant}: {zone} (umbrales {zones[0]}/{zones[1]})",
    )


# ---------------------------------------------------------------------------
# Beneish M-Score (8 variables)
# ---------------------------------------------------------------------------
def beneish_m_score(cur: BeneishYear, prev: BeneishYear, threshold: float = -1.78) -> ScoreResult:
    """Beneish M-Score de 8 variables. Requiere dos ejercicios consecutivos."""
    missing: list[str] = []
    fields = [
        "receivables", "revenue", "cogs", "current_assets", "ppe_net",
        "total_assets", "depreciation", "sga", "current_liabilities",
        "long_term_debt", "net_income_cont_ops", "cfo",
    ]
    for f in fields:
        if getattr(cur, f) is None:
            missing.append(f"{f} (actual)")
        if getattr(prev, f) is None:
            missing.append(f"{f} (anterior)")

    if missing:
        return ScoreResult(value=None, missing=missing, formula="M = -4.84 + 0.920·DSRI + ...")

    # Verificar divisiones por cero
    if cur.revenue == 0 or prev.revenue == 0:
        missing.append("revenue no puede ser 0")
    if cur.total_assets == 0 or prev.total_assets == 0:
        missing.append("total_assets no puede ser 0")

    if missing:
        return ScoreResult(value=None, missing=missing, formula="M = -4.84 + 0.920·DSRI + ...")

    def gm(y: BeneishYear) -> float:
        return (y.revenue - y.cogs) / y.revenue  # type: ignore[operator]

    try:
        dsri = (cur.receivables / cur.revenue) / (prev.receivables / prev.revenue)  # type: ignore[operator]
        gmi = gm(prev) / gm(cur)
        aqi_cur = 1 - (cur.current_assets + cur.ppe_net) / cur.total_assets  # type: ignore[operator]
        aqi_prev = 1 - (prev.current_assets + prev.ppe_net) / prev.total_assets  # type: ignore[operator]
        if aqi_prev == 0:
            raise ZeroDivisionError("AQI denom 0")
        aqi = aqi_cur / aqi_prev
        sgi = cur.revenue / prev.revenue  # type: ignore[operator]
        depi_num = prev.depreciation / (prev.depreciation + prev.ppe_net)  # type: ignore[operator]
        depi_den = cur.depreciation / (cur.depreciation + cur.ppe_net)  # type: ignore[operator]
        if depi_den == 0:
            raise ZeroDivisionError("DEPI denom 0")
        depi = depi_num / depi_den
        sgai_num = cur.sga / cur.revenue  # type: ignore[operator]
        sgai_den = prev.sga / prev.revenue  # type: ignore[operator]
        if sgai_den == 0:
            raise ZeroDivisionError("SGAI denom 0")
        sgai = sgai_num / sgai_den
        lvgi_num = (cur.current_liabilities + cur.long_term_debt) / cur.total_assets  # type: ignore[operator]
        lvgi_den = (prev.current_liabilities + prev.long_term_debt) / prev.total_assets  # type: ignore[operator]
        if lvgi_den == 0:
            raise ZeroDivisionError("LVGI denom 0")
        lvgi = lvgi_num / lvgi_den
        tata = (cur.net_income_cont_ops - cur.cfo) / cur.total_assets  # type: ignore[operator]
    except (ZeroDivisionError, TypeError):
        return ScoreResult(
            value=None,
            missing=["division por cero en calculo de Beneish"],
            formula="M = -4.84 + 0.920*DSRI + ...",
        )

    m = (
        -4.84
        + 0.920 * dsri
        + 0.528 * gmi
        + 0.404 * aqi
        + 0.892 * sgi
        + 0.115 * depi
        - 0.172 * sgai
        + 4.679 * tata
        - 0.327 * lvgi
    )

    components = {
        "DSRI": dsri,
        "GMI": gmi,
        "AQI": aqi,
        "SGI": sgi,
        "DEPI": depi,
        "SGAI": sgai,
        "LVGI": lvgi,
        "TATA": tata,
    }

    flag = m > threshold

    return ScoreResult(
        value=m,
        components=components,
        formula="M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI + 0.892*SGI "
            "+ 0.115*DEPI - 0.172*SGAI + 4.679*TATA - 0.327*LVGI",
        note=f"Umbral: {threshold}. "
        f"{'Posible manipulacion' if flag else 'Sin alerta'} "
        f"(M {'>' if flag else '<='} {threshold})",
    )


# ---------------------------------------------------------------------------
# Calidad de beneficios
# ---------------------------------------------------------------------------
def earnings_quality(
    net_income: float | None, cfo: float | None, avg_total_assets: float | None
) -> ScoreResult:
    """Calidad de beneficios: CFO/NI y ratio de devengos."""
    missing: list[str] = []
    if net_income is None:
        missing.append("net_income")
    if cfo is None:
        missing.append("cfo")
    if avg_total_assets is None or avg_total_assets == 0:
        missing.append("avg_total_assets")

    if missing:
        return ScoreResult(value=None, missing=missing, formula="CFO/NI y devengos")

    cfo_to_ni = cfo / net_income if net_income != 0 else None  # type: ignore[operator]
    accruals = (net_income - cfo) / avg_total_assets  # type: ignore[operator]

    return ScoreResult(
        value=cfo_to_ni,
        components={
            "cfo_to_net_income": cfo_to_ni,
            "accruals_ratio": accruals,
        },
        formula="CFO/NI = CFO / Beneficio neto; Devengos = (NI - CFO) / Activos medios",
    )


# ---------------------------------------------------------------------------
# Ratios financieros
# ---------------------------------------------------------------------------
def financial_ratios(
    data: YearData, prev_data: YearData | None = None, tax_rate: float | None = None
) -> dict[str, float | None]:
    """Calcula ratios financieros comunes.

    Returns dict con: gross_margin, ebit_margin, fcf_margin, roe, roic,
    dupont_margin, dupont_turnover, dupont_leverage, dso, dio, dpo,
    cash_conversion_cycle, interest_coverage, net_debt_to_ebitda,
    fcf_conversion.
    """
    r: dict[str, float | None] = {}

    revenue = data.revenue
    cogs = data.cogs
    gross_profit = data.gross_profit
    ebit = data.ebit
    net_income = data.net_income
    cfo = data.cfo

    # Márgenes
    if revenue and revenue != 0:
        r["gross_margin"] = gross_profit / revenue if gross_profit is not None else None
        r["ebit_margin"] = ebit / revenue if ebit is not None else None
        # FCF margin = (CFO - CapEx) / Revenue (aproximación)
        r["fcf_margin"] = None  # Se calcula con capex si está disponible
    else:
        r["gross_margin"] = None
        r["ebit_margin"] = None
        r["fcf_margin"] = None

    # ROE
    if net_income is not None and data.total_equity and data.total_equity != 0:
        r["roe"] = net_income / data.total_equity
    else:
        r["roe"] = None

    # DuPont (3 factores)
    if revenue and revenue != 0 and data.total_assets and data.total_assets != 0:
        net_margin = net_income / revenue if net_income is not None else None
        asset_turnover = revenue / data.total_assets
        leverage = (
            data.total_assets / data.total_equity
            if data.total_equity and data.total_equity != 0
            else None
        )
        r["dupont_margin"] = net_margin
        r["dupont_turnover"] = asset_turnover
        r["dupont_leverage"] = leverage
        if net_margin is not None and leverage is not None:
            r["roe_dupont"] = net_margin * asset_turnover * leverage
        else:
            r["roe_dupont"] = None
    else:
        r["dupont_margin"] = None
        r["dupont_turnover"] = None
        r["dupont_leverage"] = None
        r["roe_dupont"] = None

    # DSO, DIO, DPO, CCC
    if revenue and revenue != 0:
        r["dso"] = (
            (data.accounts_receivable / revenue * 365)
            if data.accounts_receivable is not None
            else None
        )
    else:
        r["dso"] = None

    if cogs and cogs != 0:
        r["dio"] = (data.inventory / cogs * 365) if data.inventory is not None else None
        r["dpo"] = (
            (data.accounts_payable / cogs * 365)
            if data.accounts_payable is not None
            else None
        )
    else:
        r["dio"] = None
        r["dpo"] = None

    dso = r.get("dso")
    dio = r.get("dio")
    dpo = r.get("dpo")
    if dso is not None and dio is not None and dpo is not None:
        r["cash_conversion_cycle"] = dso + dio - dpo
    else:
        r["cash_conversion_cycle"] = None

    # Cobertura de intereses
    if data.interest_expense and data.interest_expense != 0 and ebit is not None:
        r["interest_coverage"] = ebit / abs(data.interest_expense)
    else:
        r["interest_coverage"] = None

    # Deuda neta / EBITDA
    if ebit is not None and data.depreciation is not None:
        ebitda = ebit + data.depreciation
        if ebitda != 0:
            # Deuda neta = deuda total - caja
            total_debt = (data.long_term_debt or 0) + (data.current_liabilities or 0)
            cash = data.cash or 0
            net_debt = total_debt - cash
            r["net_debt_to_ebitda"] = net_debt / ebitda
        else:
            r["net_debt_to_ebitda"] = None
    else:
        r["net_debt_to_ebitda"] = None

    # Conversión de FCF (CFO / NI)
    if net_income and net_income != 0 and cfo is not None:
        r["fcf_conversion"] = cfo / net_income
    else:
        r["fcf_conversion"] = None

    # ROIC = NOPAT / Capital invertido
    # NOPAT = EBIT * (1 - tax_rate)
    # Capital invertido = Activos totales - Pasivos circulantes
    if ebit is not None and data.total_assets is not None and data.total_assets != 0:
        t = tax_rate if tax_rate is not None else 0.21
        nopat = ebit * (1 - t)
        invested_capital = (data.total_assets or 0) - (data.current_liabilities or 0)
        if invested_capital != 0:
            r["roic"] = nopat / invested_capital
        else:
            r["roic"] = None
    else:
        r["roic"] = None

    return r


# ---------------------------------------------------------------------------
# Función de conveniencia: no aplicable a empresas financieras
# ---------------------------------------------------------------------------
def is_financial_company(sic_code: str | None = None, sector: str | None = None) -> bool:
    """Determina si una empresa es financiera (no aplican los scores)."""
    if sector and "financial" in sector.lower():
        return True
    if sic_code:
        # SIC codes 6000-6999 son financieros
        try:
            sic = int(sic_code)
            if 6000 <= sic <= 6999:
                return True
        except (ValueError, TypeError):
            pass
    return False


__all__ = [
    "BeneishYear",
    "ScoreResult",
    "YearData",
    "altman_z_score",
    "beneish_m_score",
    "earnings_quality",
    "financial_ratios",
    "is_financial_company",
    "piotroski_f_score",
]
