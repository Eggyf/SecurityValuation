"""Tema oscuro/claro para la app."""

from __future__ import annotations

LIGHT = {
    "bg": "#FFFFFF", "surface": "#F8FAFC", "text": "#1F2937", "muted": "#4B5563",
    "primary": "#1D4ED8", "primary_on": "#FFFFFF",
    "above": "#1D4ED8", "below": "#C2410C",
    "range_fill": "#BFDBFE", "grid": "#E5E7EB", "price_line": "#111827",
    "positive": "#0F766E", "negative": "#B91C1C",
}

DARK = {
    "bg": "#0F172A", "surface": "#1E293B", "text": "#E5E7EB", "muted": "#94A3B8",
    "primary": "#2563EB", "primary_on": "#0F172A",
    "above": "#60A5FA", "below": "#FB923C",
    "range_fill": "#1E3A8A", "grid": "#334155", "price_line": "#F8FAFC",
    "positive": "#2DD4BF", "negative": "#F87171",
}

FONT = "Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"


def get_palette(base: str) -> dict[str, str]:
    """Devuelve la paleta LIGHT o DARK según el tema activo.

    Args:
        base: "dark" para tema oscuro, cualquier otro valor para claro.

    Returns:
        Diccionario con los tokens de color.
    """
    if base == "dark":
        return DARK
    return LIGHT


DARK_CSS = """
<style>
.stApp { background-color: #0F172A; color: #E5E7EB; }
.stApp > header { background-color: #0F172A; }
section[data-testid="stSidebar"] { background-color: #1E293B; }
section[data-testid="stSidebar"] * { color: #E5E7EB; }
.stTabs [data-baseweb="tab-list"] { background-color: #1E293B; }
.stTabs [data-baseweb="tab"] { color: #94A3B8; }
.stTabs [aria-selected="true"] { color: #60A5FA; border-bottom-color: #60A5FA; }
[data-testid="stMetricValue"] { color: #E5E7EB; }
[data-testid="stMetricLabel"] { color: #94A3B8; }
.stCaption { color: #94A3B8; }
details { background-color: #1E293B; }
details summary { color: #E5E7EB; }
.stDataFrame th { background-color: #334155; color: #E5E7EB; }
.stDataFrame td { color: #E5E7EB; }
input, textarea, select { background-color: #334155; color: #E5E7EB; border-color: #475569; }
.stButton button { background-color: #2563EB; color: #FFFFFF; }
.stButton button:hover { background-color: #1D4ED8; }
</style>
"""


def get_css(theme: str) -> str:
    """Devuelve el CSS para el tema indicado."""
    if theme == "dark":
        return DARK_CSS
    return ""


__all__ = ["DARK", "DARK_CSS", "FONT", "LIGHT", "get_css", "get_palette"]
