"""Tokens visuales y gráficos para la app (público principiante).

- Paleta con contraste comprobado (WCAG AA >= 4,5:1 en pares de texto): `python theme.py`.
- Los gráficos usan plotly con import perezoso (plotly NO estaba instalado al crear
  este archivo: las funciones de gráfico están sin ejecutar; revisa la API instalada).
- Valoración frente a precio: azul/naranja, NUNCA verde/rojo (no sugiere comprar/vender).
"""
from __future__ import annotations

LIGHT = {
    "bg": "#FFFFFF", "surface": "#F8FAFC", "text": "#1F2937", "muted": "#4B5563",
    "primary": "#1D4ED8", "primary_on": "#FFFFFF",
    "ok_text": "#166534", "ok_bg": "#DCFCE7",
    "warn_text": "#92400E", "warn_bg": "#FEF3C7",
    "error_text": "#991B1B", "error_bg": "#FEE2E2",
    "info_text": "#1E40AF", "info_bg": "#DBEAFE",
    "above": "#1D4ED8",      # valor estimado POR ENCIMA del precio (azul)
    "below": "#C2410C",      # valor estimado POR DEBAJO del precio (naranja)
    "range_fill": "#BFDBFE", "grid": "#E5E7EB", "price_line": "#111827",
}

DARK = {
    "bg": "#0F172A", "surface": "#1E293B", "text": "#E5E7EB", "muted": "#9CA3AF",
    "primary": "#60A5FA", "primary_on": "#0F172A",
    "ok_text": "#86EFAC", "ok_bg": "#14532D",
    "warn_text": "#FCD34D", "warn_bg": "#78350F",
    "error_text": "#FCA5A5", "error_bg": "#7F1D1D",
    "info_text": "#BFDBFE", "info_bg": "#1E3A8A",
    "above": "#60A5FA", "below": "#FB923C",
    "range_fill": "#1E3A8A", "grid": "#334155", "price_line": "#F8FAFC",
}

FONT = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"

# Pares (texto, fondo) que se usan juntos y deben cumplir AA (4,5:1)
TEXT_PAIRS = [
    ("text", "bg"), ("text", "surface"), ("muted", "bg"), ("muted", "surface"),
    ("primary_on", "primary"), ("ok_text", "ok_bg"), ("warn_text", "warn_bg"),
    ("error_text", "error_bg"), ("info_text", "info_bg"), ("primary", "bg"),
]


def _lin(c: int) -> float:
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def check_palette(palette: dict[str, str], name: str) -> list[str]:
    fails = []
    for fg, bg in TEXT_PAIRS:
        r = contrast_ratio(palette[fg], palette[bg])
        if r < 4.5:
            fails.append(f"{name}: {fg} sobre {bg} = {r:.2f}:1")
    return fails


# ------------------------------------------------------------------ Plotly
def plotly_layout(p: dict[str, str] = LIGHT) -> dict:
    """Diseño base: sin adornos, tipografía legible, rejilla suave."""
    return dict(
        font=dict(family=FONT, size=14, color=p["text"]),
        paper_bgcolor=p["bg"], plot_bgcolor=p["bg"],
        margin=dict(l=16, r=16, t=48, b=16),
        xaxis=dict(gridcolor=p["grid"], zeroline=False),
        yaxis=dict(gridcolor=p["grid"], zeroline=False),
        hoverlabel=dict(font_size=14),
    )


def value_range_chart(low: float, mid: float, high: float, price: float | None,
                      p: dict[str, str] = LIGHT):
    """Barra horizontal con el RANGO de valor estimado y el precio actual como línea."""
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[high - low], y=[""], base=[low], orientation="h",
                         marker_color=p["range_fill"], marker_line_color=p["primary"],
                         marker_line_width=2, showlegend=False,
                         hovertemplate=f"Rango estimado: {low:,.2f} a {high:,.2f}<extra></extra>"))
    fig.add_vline(x=mid, line_color=p["primary"], line_width=3,
                  annotation_text=f"Valor central {mid:,.2f}", annotation_position="top")
    if price is not None:
        fig.add_vline(x=price, line_color=p["price_line"], line_dash="dash",
                      annotation_text=f"Precio hoy {price:,.2f}", annotation_position="bottom")
    fig.update_layout(**plotly_layout(p), height=180, bargap=0.4)
    fig.update_yaxes(visible=False)
    return fig


def bridge_waterfall(items: list[tuple[str, float]], total_label: str,
                     p: dict[str, str] = LIGHT):
    """De 'valor de la empresa' a 'valor para el accionista'. items = [(etiqueta, importe)]
    con importes con signo (caja +, deuda −). El primero es el valor de empresa."""
    import plotly.graph_objects as go
    labels = [i[0] for i in items] + [total_label]
    values = [i[1] for i in items] + [0]
    measure = ["absolute"] + ["relative"] * (len(items) - 1) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measure,
        increasing=dict(marker_color=p["above"]), decreasing=dict(marker_color=p["below"]),
        totals=dict(marker_color=p["primary"]), connector=dict(line_color=p["grid"]),
        text=[f"{v:,.0f}" for v in values], textposition="outside"))
    fig.update_layout(**plotly_layout(p), height=360, showlegend=False)
    return fig


def sensitivity_heatmap(z: list[list[float | None]], x_labels: list[str],
                        y_labels: list[str], price: float | None,
                        p: dict[str, str] = LIGHT):
    """Mapa de calor de precio por acción (WACC × g). Celdas None = 'n/d'.
    Escala divergente azul/naranja centrada en el precio actual si existe."""
    import plotly.graph_objects as go
    fig = go.Figure(go.Heatmap(
        z=z, x=x_labels, y=y_labels, zmid=price,
        colorscale=[[0, p["below"]], [0.5, p["bg"]], [1, p["above"]]],
        texttemplate="%{z:.1f}", hoverongaps=False))
    fig.update_layout(**plotly_layout(p), height=380)
    return fig


if __name__ == "__main__":
    fails = check_palette(LIGHT, "claro") + check_palette(DARK, "oscuro")
    for pal, nm in ((LIGHT, "claro"), (DARK, "oscuro")):
        for fg, bg in TEXT_PAIRS:
            print(f"{nm:7} {fg:11} sobre {bg:8} {contrast_ratio(pal[fg], pal[bg]):5.2f}:1")
    assert not fails, fails
    print("paleta OK: todos los pares de texto >= 4,5:1")
