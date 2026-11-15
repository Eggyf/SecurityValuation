"""Tema oscuro/claro para la app."""

from __future__ import annotations

DARK_CSS = """
<style>
/* Fondo principal */
.stApp { background-color: #0F172A; color: #E5E7EB; }
.stApp > header { background-color: #0F172A; }

/* Sidebar */
section[data-testid="stSidebar"] { background-color: #1E293B; }
section[data-testid="stSidebar"] * { color: #E5E7EB; }

/* Texto general */
p, span, label, div { color: #E5E7EB; }

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background-color: #334155; color: #E5E7EB; border-color: #475569;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #60A5FA;
}

/* Botones */
.stButton button {
    background-color: #1D4ED8; color: #FFFFFF; border: none;
}
.stButton button:hover { background-color: #2563EB; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background-color: #1E293B; }
.stTabs [data-baseweb="tab"] { color: #9CA3AF; }
.stTabs [aria-selected="true"] { color: #60A5FA; border-bottom-color: #60A5FA; }

/* Métricas */
[data-testid="stMetricValue"] { color: #E5E7EB; }
[data-testid="stMetricLabel"] { color: #9CA3AF; }

/* Expanders */
.streamlit-expanderHeader { color: #E5E7EB; background-color: #1E293B; }
.streamlit-expanderContent { background-color: #0F172A; }

/* DataFrames */
.stDataFrame { background-color: #1E293B; }
.stDataFrame th { background-color: #334155; color: #E5E7EB; }
.stDataFrame td { color: #E5E7EB; }

/* Avisos */
.stAlert { background-color: #1E293B; color: #E5E7EB; }

/* Sliders */
.stSlider [data-baseweb="slider"] { background-color: #334155; }

/* Radio buttons */
.stRadio label { color: #E5E7EB; }

/* Markdown */
.stMarkdown { color: #E5E7EB; }

/* Captions */
.stCaption { color: #9CA3AF; }
</style>
"""

LIGHT_CSS = ""  # Usar tema por defecto de Streamlit

PALETTES = {
    "light": {
        "bg": "#FFFFFF", "surface": "#F8FAFC", "text": "#1F2937", "muted": "#4B5563",
        "primary": "#1D4ED8", "primary_on": "#FFFFFF",
        "above": "#1D4ED8", "below": "#C2410C",
        "range_fill": "#BFDBFE", "grid": "#E5E7EB", "price_line": "#111827",
    },
    "dark": {
        "bg": "#0F172A", "surface": "#1E293B", "text": "#E5E7EB", "muted": "#9CA3AF",
        "primary": "#60A5FA", "primary_on": "#0F172A",
        "above": "#60A5FA", "below": "#FB923C",
        "range_fill": "#1E3A8A", "grid": "#334155", "price_line": "#F8FAFC",
    },
}


def get_css(theme: str) -> str:
    """Devuelve el CSS para el tema indicado."""
    if theme == "dark":
        return DARK_CSS
    return ""


def get_palette(theme: str) -> dict[str, str]:
    """Devuelve la paleta de colores para el tema indicado."""
    return PALETTES.get(theme, PALETTES["light"])


__all__ = ["DARK_CSS", "LIGHT_CSS", "PALETTES", "get_css", "get_palette"]
