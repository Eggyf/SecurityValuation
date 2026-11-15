"""Gráficos con Plotly para la app (beginner-visual-design)."""

from __future__ import annotations

import plotly.graph_objects as go


def range_chart(
    low: float,
    high: float,
    center: float,
    market_price: float | None = None,
    title: str = "Rango de valor",
    palette: dict[str, str] | None = None,
) -> go.Figure:
    """Gráfico de rango horizontal con precio de mercado.

    Args:
        palette: paleta de colores (no usada por ahora).

    Args:
        low: límite inferior del rango.
        high: límite superior del rango.
        center: valor central.
        market_price: precio de mercado (línea discontinua).
        title: título del gráfico (conclusión).

    Returns:
        Figura de Plotly.
    """
    fig = go.Figure()

    # Barra de rango
    fig.add_trace(
        go.Bar(
            x=[high - low],
            y=["Valor estimado"],
            base=[low],
            orientation="h",
            marker_color="#BFDBFE",
            name="Rango",
            text=[f"{low:,.0f} - {high:,.0f}"],
            textposition="inside",
        )
    )

    # Valor central
    fig.add_trace(
        go.Scatter(
            x=[center],
            y=["Valor estimado"],
            mode="markers",
            marker={"size": 12, "color": "#1D4ED8", "symbol": "diamond"},
            name="Valor central",
            text=[f"{center:,.2f}"],
            textposition="top center",
        )
    )

    # Precio de mercado
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
        height=200,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )
    return fig


def waterfall_chart(
    items: list[tuple[str, float]],
    title: str = "De negocio a acción",
) -> go.Figure:
    """Gráfico de cascada (waterfall).

    Args:
        items: lista de (etiqueta, valor) donde el valor puede ser positivo o negativo.
        title: título del gráfico.

    Returns:
        Figura de Plotly.
    """
    labels = [item[0] for item in items]
    values = [item[1] for item in items]

    fig = go.Figure(
        go.Waterfall(
            name="",
            orientation="v",
            measure=["relative"] * (len(items) - 1) + ["total"],
            x=labels,
            y=values,
            textposition="outside",
            text=[f"{v:,.0f}" for v in values],
            connector={"line": {"color": "#999999"}},
        )
    )

    fig.update_layout(
        title=title,
        yaxis_title="MM USD",
        showlegend=False,
        height=400,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )
    return fig


def sensitivity_heatmap(
    data: dict[tuple[float, float], float],
    title: str = "Mapa de sensibilidad",
    center_value: float | None = None,
) -> go.Figure:
    """Mapa de calor de sensibilidad WACC x g.

    Args:
        data: diccionario {(wacc, g): precio}.
        title: título del gráfico.
        center_value: valor central para centrar la escala de color.

    Returns:
        Figura de Plotly.
    """
    waccs = sorted({k[0] for k in data})
    gs = sorted({k[1] for k in data})

    z = []
    for w in waccs:
        row = []
        for g in gs:
            val = data.get((w, g), float("nan"))
            row.append(val if val == val else None)
        z.append(row)

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[f"{g:.1%}" for g in gs],
            y=[f"{w:.1%}" for w in waccs],
            colorscale="RdBu",
            text=[[f"{v:.2f}" if v is not None and v == v else "n/d" for v in row] for row in z],
            texttemplate="%{text}",
            hovertemplate="WACC: %{y}<br>g: %{x}<br>Precio: %{text}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Crecimiento terminal (g)",
        yaxis_title="WACC",
        height=400,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )
    return fig


def bar_comparison(
    labels: list[str],
    values: list[float],
    title: str = "Comparación",
    price_line: float | None = None,
) -> go.Figure:
    """Gráfico de barras para comparación (Reverse DCF)."""
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=["#1D4ED8", "#C2410C"],
            text=[f"{v:.1%}" for v in values],
            textposition="outside",
        )
    )

    if price_line is not None:
        fig.add_hline(y=price_line, line_dash="dash", line_color="#111827")

    fig.update_layout(
        title=title,
        yaxis_title="Porcentaje",
        showlegend=False,
        height=300,
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )
    return fig


__all__ = ["bar_comparison", "range_chart", "sensitivity_heatmap", "waterfall_chart"]
