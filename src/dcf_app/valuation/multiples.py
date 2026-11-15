"""Múltiplos de comparables y football field (AGENTS.md §14.4).

Calcula múltiplos de peers (EV/EBITDA, EV/EBIT, EV/Ventas, P/E)
usando mediana y cuartiles. Excluye múltiplos negativos o no significativos.
Aplica el mismo puente EV → equity → precio que el DCF.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PeerData:
    """Datos de un peer para cálculo de múltiplos."""

    name: str
    enterprise_value: float  # EV en millones
    ebitda: float | None = None
    ebit: float | None = None
    revenue: float | None = None
    net_income: float | None = None
    price: float | None = None
    shares: float | None = None


@dataclass
class MultipleResult:
    """Resultado de un múltiplo."""

    name: str  # "EV/EBITDA", "EV/EBIT", etc.
    values: list[float] = field(default_factory=list)  # múltiplos de peers válidos
    n_peers: int = 0  # peers que entraron
    n_excluded: int = 0  # peers excluidos (NM o negativos)
    median: float | None = None
    q1: float | None = None
    q3: float | None = None
    implied_ev: float | None = None  # EV implícito (mediana x métrica)
    implied_price: float | None = None  # precio implícito


def _compute_multiple(
    peers: list[PeerData],
    numerator_fn: Any,  # noqa: ANN401
    denominator_fn: Any,  # noqa: ANN401
    name: str,
) -> MultipleResult:
    """Calcula un múltiplo para una lista de peers.

    Args:
        peers: lista de peers con sus datos.
        numerator_fn: función que extrae el numerador (EV) de un peer.
        denominator_fn: función que extrae el denominador (EBITDA, etc.) de un peer.
        name: nombre del múltiplo.

    Returns:
        MultipleResult con mediana, cuartiles e implícitos.
    """
    result = MultipleResult(name=name)
    valid_multiples: list[float] = []

    for peer in peers:
        num = numerator_fn(peer)
        den = denominator_fn(peer)
        if den is None or den == 0:
            result.n_excluded += 1
            continue
        mult = num / den
        if mult <= 0 or mult != mult:  # NaN check
            result.n_excluded += 1
            continue
        valid_multiples.append(mult)

    result.values = valid_multiples
    result.n_peers = len(valid_multiples)

    if valid_multiples:
        sorted_vals = sorted(valid_multiples)
        n = len(sorted_vals)
        result.median = sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2  # noqa: E501
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        result.q1 = sorted_vals[q1_idx] if q1_idx < n else sorted_vals[0]
        result.q3 = sorted_vals[q3_idx] if q3_idx < n else sorted_vals[-1]

    return result


def compute_multiples(
    peers: list[PeerData],
    company_ebitda: float | None = None,
    company_ebit: float | None = None,
    company_revenue: float | None = None,
    company_net_income: float | None = None,
    company_shares: float | None = None,
    company_cash: float = 0.0,
    company_debt: float = 0.0,
    company_leases: float = 0.0,
    company_preferred: float = 0.0,
    company_nci: float = 0.0,
) -> list[MultipleResult]:
    """Calcula todos los múltiplos para una lista de peers.

    Args:
        peers: lista de peers.
        company_ebitda: EBITDA de la empresa (para EV implícito).
        company_ebit: EBIT de la empresa.
        company_revenue: ingresos de la empresa.
        company_net_income: beneficio neto de la empresa.
        company_shares: acciones de la empresa (para P/E).
        company_cash: caja de la empresa (para puente).
        company_debt: deuda de la empresa.
        company_leases: leases de la empresa.
        company_preferred: preferentes de la empresa.
        company_nci: minoritarios de la empresa.

    Returns:
        Lista de MultipleResult (EV/EBITDA, EV/EBIT, EV/Ventas, P/E).
    """
    results = []

    # EV/EBITDA
    r = _compute_multiple(
        peers,
        lambda p: p.enterprise_value,
        lambda p: p.ebitda,
        "EV/EBITDA",
    )
    if r.median is not None and company_ebitda is not None and company_ebitda > 0:
        r.implied_ev = r.median * company_ebitda
        r.implied_price = _bridge_to_price(r.implied_ev, company_cash, company_debt, company_leases, company_preferred, company_nci, company_shares)  # noqa: E501
    results.append(r)

    # EV/EBIT
    r = _compute_multiple(
        peers,
        lambda p: p.enterprise_value,
        lambda p: p.ebit,
        "EV/EBIT",
    )
    if r.median is not None and company_ebit is not None and company_ebit > 0:
        r.implied_ev = r.median * company_ebit
        r.implied_price = _bridge_to_price(r.implied_ev, company_cash, company_debt, company_leases, company_preferred, company_nci, company_shares)  # noqa: E501
    results.append(r)

    # EV/Ventas
    r = _compute_multiple(
        peers,
        lambda p: p.enterprise_value,
        lambda p: p.revenue,
        "EV/Ventas",
    )
    if r.median is not None and company_revenue is not None and company_revenue > 0:
        r.implied_ev = r.median * company_revenue
        r.implied_price = _bridge_to_price(r.implied_ev, company_cash, company_debt, company_leases, company_preferred, company_nci, company_shares)  # noqa: E501
    results.append(r)

    # P/E
    r = _compute_multiple(
        peers,
        lambda p: p.price * p.shares if p.price and p.shares else 0,
        lambda p: p.net_income,
        "P/E",
    )
    if r.median is not None and company_net_income is not None and company_net_income > 0 and company_shares:  # noqa: E501
        implied_equity = r.median * company_net_income
        r.implied_price = implied_equity / company_shares
    results.append(r)

    return results


def _bridge_to_price(
    ev: float,
    cash: float,
    debt: float,
    leases: float,
    preferred: float,
    nci: float,
    shares: float | None,
) -> float | None:
    """Puente EV → precio por acción."""
    if shares is None or shares <= 0:
        return None
    equity = ev + cash - debt - leases - preferred - nci
    return equity / shares


@dataclass
class FootballFieldRange:
    """Rango de un método para el football field."""

    method: str
    low: float
    high: float
    color: str = "#2563EB"


def build_football_field(
    dcf_low: float | None = None,
    dcf_high: float | None = None,
    mc_p25: float | None = None,
    mc_p75: float | None = None,
    multiple_ranges: list[tuple[str, float, float]] | None = None,
    market_low: float | None = None,
    market_high: float | None = None,
    market_price: float | None = None,
) -> list[FootballFieldRange]:
    """Construye los rangos para el football field.

    Args:
        dcf_low: mínimo de sensibilidad WACCxg.
        dcf_high: máximo de sensibilidad WACCxg.
        mc_p25: percentil 25 de Monte Carlo.
        mc_p75: percentil 75 de Monte Carlo.
        multiple_ranges: lista de (nombre, low, high) para múltiplos.
        market_low: mínimo del rango de 52 semanas.
        market_high: máximo del rango de 52 semanas.
        market_price: precio actual de mercado.

    Returns:
        Lista de FootballFieldRange.
    """
    ranges = []

    if dcf_low is not None and dcf_high is not None:
        ranges.append(FootballFieldRange("DCF (sensibilidad)", dcf_low, dcf_high, "#2563EB"))

    if mc_p25 is not None and mc_p75 is not None:
        ranges.append(FootballFieldRange("Monte Carlo (P25-P75)", mc_p25, mc_p75, "#7C3AED"))

    if multiple_ranges:
        for name, low, high in multiple_ranges:
            ranges.append(FootballFieldRange(f"Múltiplos ({name})", low, high, "#D97706"))

    if market_low is not None and market_high is not None:
        ranges.append(FootballFieldRange("Rango 52 semanas", market_low, market_high, "#6B7280"))

    return ranges


def create_football_field_chart(
    ranges: list[FootballFieldRange],
    market_price: float | None = None,
    title: str = "Football Field - Rango de valor por método",
) -> Any:  # noqa: ANN401
    """Crea el gráfico de football field con Plotly.

    Args:
        ranges: lista de rangos.
        market_price: precio de mercado (línea vertical).
        title: título del gráfico.

    Returns:
        Figura de Plotly.
    """
    import plotly.graph_objects as go

    fig = go.Figure()

    for _i, r in enumerate(ranges):
        fig.add_trace(
            go.Bar(
                x=[r.high - r.low],
                y=[r.method],
                base=[r.low],
                orientation="h",
                marker_color=r.color,
                name=r.method,
                text=[f"{r.low:,.0f} - {r.high:,.0f}"],
                textposition="inside",
            )
        )

    if market_price is not None:
        fig.add_vline(
            x=market_price,
            line_dash="dash",
            line_color="#111827",
            annotation_text=f"Precio hoy: {market_price:,.2f}",
            annotation_position="top",
        )

    fig.update_layout(
        title=title,
        xaxis_title="USD por acción",
        showlegend=False,
        height=max(200, len(ranges) * 60 + 100),
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        yaxis={"autorange": "reversed"},
    )
    return fig


__all__ = [
    "FootballFieldRange",
    "MultipleResult",
    "PeerData",
    "build_football_field",
    "compute_multiples",
    "create_football_field_chart",
]
