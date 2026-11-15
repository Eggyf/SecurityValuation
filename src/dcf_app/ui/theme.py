"""Tema oscuro/claro para la app."""

from __future__ import annotations

# Paleta simplificada: azul + ámbar (complementarios, accesibles)
LIGHT_CSS = ""  # Usar tema por defecto de Streamlit

DARK_CSS = """
<style>
/* Fondo y texto principal */
.stApp, .stApp > div, .main {
    background-color: #0F172A !important;
    color: #E2E8F0 !important;
}
.stApp > header { background-color: #0F172A !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #1E293B !important;
}
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }

/* Texto */
h1, h2, h3, h4, h5, h6, p, span, label, div, li, td, th {
    color: #E2E8F0 !important;
}

/* Inputs */
input, textarea, select {
    background-color: #334155 !important;
    color: #E2E8F0 !important;
    border-color: #475569 !important;
}
input:focus, textarea:focus, select:focus {
    border-color: #60A5FA !important;
    box-shadow: 0 0 0 1px #60A5FA !important;
}

/* Botones */
button[kind="primary"], .stButton > button {
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: none !important;
}
button[kind="primary"]:hover, .stButton > button:hover {
    background-color: #1D4ED8 !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    color: #94A3B8 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #60A5FA !important;
    border-bottom-color: #60A5FA !important;
}

/* Métricas */
[data-testid="stMetricValue"] { color: #E2E8F0 !important; }
[data-testid="stMetricLabel"] { color: #94A3B8 !important; }
[data-testid="stMetricDelta"] { color: #94A3B8 !important; }

/* Expanders */
details { background-color: #1E293B !important; border-color: #334155 !important; }
details summary { color: #E2E8F0 !important; }
details > div { background-color: #0F172A !important; }

/* DataFrames / tablas */
.stDataFrame, .stTable { background-color: #1E293B !important; }
.stDataFrame th, .stTable th { background-color: #334155 !important; color: #E2E8F0 !important; }
.stDataFrame td, .stTable td { color: #E2E8F0 !important; }

/* Avisos */
.stAlert { background-color: #1E293B !important; color: #E2E8F0 !important; }
div[data-testid="stAlert"] { background-color: #1E293B !important; }

/* Sliders */
.stSlider [data-baseweb="slider"] { background-color: #334155 !important; }
.stSlider [role="slider"] { background-color: #2563EB !important; }

/* Radio / checkbox */
.stRadio label, .stCheckbox label { color: #E2E8F0 !important; }

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }

/* Markdown */
.stMarkdown { color: #E2E8F0 !important; }

/* Selectbox */
.stSelectbox [data-baseweb="select"] { background-color: #334155 !important; }
.stSelectbox [data-baseweb="select"] * { color: #E2E8F0 !important; }

/* Number input */
.stNumberInput [data-baseweb="input"] { background-color: #334155 !important; }
.stNumberInput [data-baseweb="input"] * { color: #E2E8F0 !important; }

/* Text input */
.stTextInput [data-baseweb="input"] { background-color: #334155 !important; }
.stTextInput [data-baseweb="input"] * { color: #E2E8F0 !important; }

/* File uploader */
.stFileUploader { background-color: #1E293B !important; }

/* Progress bar */
.stProgress > div > div { background-color: #2563EB !important; }

/* Dividers */
hr { border-color: #334155 !important; }
</style>
"""

PALETTES = {
    "light": {
        "bg": "#FFFFFF", "surface": "#F8FAFC", "text": "#1F2937", "muted": "#4B5563",
        "primary": "#2563EB", "primary_on": "#FFFFFF",
        "above": "#2563EB", "below": "#C2410C",
        "range_fill": "#BFDBFE", "grid": "#E5E7EB", "price_line": "#111827",
    },
    "dark": {
        "bg": "#0F172A", "surface": "#1E293B", "text": "#E2E8F0", "muted": "#94A3B8",
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
