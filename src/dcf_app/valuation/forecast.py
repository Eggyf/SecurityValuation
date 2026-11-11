"""Proyección de flujos de caja para el DCF (AGENTS.md §7.2).

Funciones puras: mismas entradas → mismas salidas; sin I/O, sin estado
global, sin aleatoriedad (AGENTS.md §8).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ForecastResult(BaseModel):
    """Resultado de la proyección de flujos (AGENTS.md §7.2).

    Todos los valores en millones de USD (o en la unidad que se indique).
    """

    model_config = ConfigDict(extra="forbid")

    revenue: list[float]  # ingresos proyectados
    ebit_margin: list[float]  # margen EBIT por año
    ebit: list[float]  # EBIT = Revenue x Margen
    nopat: list[float]  # NOPAT = EBIT x (1 - t)
    da: list[float]  # D&A = Revenue x %D&A
    capex: list[float]  # CapEx = Revenue x %CapEx
    delta_nwc: list[float]  # ΔNWC = (Revenue_t - Revenue_{t-1}) x %NWC
    fcff: list[float]  # FCFF = NOPAT + D&A - CapEx - ΔNWC


def project_revenue(
    initial_revenue: float,
    growth_initial: float,
    growth_terminal: float,
    horizon: int,
) -> list[float]:
    """Proyecta ingresos con fade lineal del crecimiento.

    Fórmula:
        g_t = g_inicial + (g_terminal - g_inicial) x t / max(horizon - 1, 1)
        Revenue_t = Revenue_{t-1} x (1 + g_t)

    donde ``t = 0 … horizon - 1``. Con ``horizon = 1`` el fade no aplica y
    se usa ``g_inicial``.

    Args:
        initial_revenue: ingresos del último ejercicio (millones).
        growth_initial: crecimiento del primer año proyectado (fracción).
        growth_terminal: crecimiento del último año proyectado = g (fracción).
        horizon: número de años a proyectar (≥ 1).

    Returns:
        Lista de ``horizon`` ingresos proyectados (millones).
    """
    if horizon < 1:
        return []

    revenues: list[float] = []
    current = initial_revenue
    denom = max(horizon - 1, 1)
    for t in range(horizon):
        growth = growth_initial + (growth_terminal - growth_initial) * t / denom
        current = current * (1.0 + growth)
        revenues.append(current)
    return revenues


def project_ebit_margin(
    margin_current: float,
    margin_target: float,
    horizon: int,
) -> list[float]:
    """Converge el margen EBIT linealmente desde el actual al objetivo.

    Fórmula:
        m_t = m_actual + (m_objetivo - m_actual) x t / max(horizon - 1, 1)

    donde ``t = 0 … horizon - 1``. Con ``horizon = 1`` se mantiene
    ``m_actual``.

    Args:
        margin_current: margen EBIT del último ejercicio (fracción).
        margin_target: margen EBIT objetivo (fracción).
        horizon: número de años a proyectar (≥ 1).

    Returns:
        Lista de ``horizon`` márgenes EBIT proyectados (fracción).
    """
    if horizon < 1:
        return []

    margins: list[float] = []
    denom = max(horizon - 1, 1)
    for t in range(horizon):
        margin = margin_current + (margin_target - margin_current) * t / denom
        margins.append(margin)
    return margins


def project_ebit(revenue: list[float], ebit_margin: list[float]) -> list[float]:
    """EBIT = Revenue x Margen EBIT (AGENTS.md §7.1)."""
    if len(revenue) != len(ebit_margin):
        raise ValueError(
            f"Longitudes distintas: revenue={len(revenue)}, ebit_margin={len(ebit_margin)}."
        )
    return [r * m for r, m in zip(revenue, ebit_margin, strict=False)]


def project_nopat(ebit: list[float], tax_rate: float) -> list[float]:
    """NOPAT = EBIT x (1 - t) (AGENTS.md §7.1)."""
    return [e * (1.0 - tax_rate) for e in ebit]


def project_da(revenue: list[float], da_pct: float) -> list[float]:
    """D&A = Revenue x %D&A (AGENTS.md §7.2)."""
    return [r * da_pct for r in revenue]


def project_capex(revenue: list[float], capex_pct: float) -> list[float]:
    """CapEx = Revenue x %CapEx (AGENTS.md §7.2)."""
    return [r * capex_pct for r in revenue]


def project_delta_nwc(
    revenue: list[float],
    nwc_pct: float,
    base_revenue: float | None = None,
) -> list[float]:
    """Variación del capital circulante operativo.

    Fórmula:
        ΔNWC_t = (Revenue_t - Revenue_{t-1}) x %NWC

    Para ``t = 0`` se usa ``base_revenue`` (último ejercicio histórico) si
    se proporciona; en caso contrario se asume ``Revenue_{-1} = 0``.

    Args:
        revenue: ingresos proyectados (millones).
        nwc_pct: NWC como fracción de los ingresos.
        base_revenue: ingresos del último ejercicio histórico (millones).

    Returns:
        Lista de ``len(revenue)`` variaciones de NWC (millones).
    """
    deltas: list[float] = []
    prev = base_revenue if base_revenue is not None else 0.0
    for r in revenue:
        deltas.append((r - prev) * nwc_pct)
        prev = r
    return deltas


def project_fcff(
    revenue: list[float],
    ebit_margin: list[float],
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    base_revenue: float | None = None,
) -> list[float]:
    """Proyecta FCFF a partir de los supuestos.

    Fórmula (AGENTS.md §7.1):
        NOPAT = EBIT x (1 - t)
        FCFF  = NOPAT + D&A - CapEx - ΔNWC

    Args:
        revenue: ingresos proyectados (millones).
        ebit_margin: margen EBIT proyectado por año (fracción).
        tax_rate: tasa impositiva normalizada (fracción).
        da_pct: D&A como fracción de los ingresos.
        capex_pct: CapEx como fracción de los ingresos.
        nwc_pct: NWC como fracción de los ingresos.
        base_revenue: ingresos del último ejercicio histórico (millones).

    Returns:
        Lista de ``len(revenue)`` FCFF proyectados (millones).
    """
    ebit = project_ebit(revenue, ebit_margin)
    nopat = project_nopat(ebit, tax_rate)
    da = project_da(revenue, da_pct)
    capex = project_capex(revenue, capex_pct)
    delta_nwc = project_delta_nwc(revenue, nwc_pct, base_revenue)

    return [n + d - c - w for n, d, c, w in zip(nopat, da, capex, delta_nwc, strict=False)]


def build_forecast(
    initial_revenue: float,
    growth_initial: float,
    growth_terminal: float,
    margin_current: float,
    margin_target: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    horizon: int,
    base_revenue: float | None = None,
) -> ForecastResult:
    """Construye la proyección completa de flujos (AGENTS.md §7.2).

    Args:
        initial_revenue: ingresos del último ejercicio (millones).
        growth_initial: crecimiento inicial (fracción).
        growth_terminal: crecimiento terminal = g (fracción).
        margin_current: margen EBIT actual (fracción).
        margin_target: margen EBIT objetivo (fracción).
        tax_rate: tasa impositiva normalizada (fracción).
        da_pct: D&A como fracción de los ingresos.
        capex_pct: CapEx como fracción de los ingresos.
        nwc_pct: NWC como fracción de los ingresos.
        horizon: años a proyectar (3-10).
        base_revenue: ingresos del último ejercicio histórico (millones).

    Returns:
        :class:`ForecastResult` con todos los componentes proyectados.
    """
    revenue = project_revenue(initial_revenue, growth_initial, growth_terminal, horizon)
    ebit_margin = project_ebit_margin(margin_current, margin_target, horizon)
    ebit = project_ebit(revenue, ebit_margin)
    nopat = project_nopat(ebit, tax_rate)
    da = project_da(revenue, da_pct)
    capex = project_capex(revenue, capex_pct)
    delta_nwc = project_delta_nwc(revenue, nwc_pct, base_revenue)
    fcff = project_fcff(revenue, ebit_margin, tax_rate, da_pct, capex_pct, nwc_pct, base_revenue)

    return ForecastResult(
        revenue=revenue,
        ebit_margin=ebit_margin,
        ebit=ebit,
        nopat=nopat,
        da=da,
        capex=capex,
        delta_nwc=delta_nwc,
        fcff=fcff,
    )
