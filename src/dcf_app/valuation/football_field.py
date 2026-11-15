"""Football field chart (AGENTS.md §14.4).

Gráfico con un rango por método y una línea con el precio actual.
"""

from __future__ import annotations

from typing import Any

from dcf_app.valuation.multiples import FootballFieldRange


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

    for r in ranges:
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


__all__ = ["create_football_field_chart"]
