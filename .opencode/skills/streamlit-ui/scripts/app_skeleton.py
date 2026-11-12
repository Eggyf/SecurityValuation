"""Esqueleto de la UI Streamlit. SOLO comprobado sintácticamente (sin streamlit instalado).

La UI NO calcula finanzas: llama a servicios de dcf_app y muestra resultados.
Sustituye los `TODO` por llamadas reales a src/dcf_app/.
"""
from __future__ import annotations

import streamlit as st

from formatting import fmt_money, fmt_pct, fmt_price, pct_input_to_fraction

DISCLAIMER = (
    "Herramienta educativa y de análisis. No constituye asesoramiento financiero "
    "ni una recomendación de inversión. Los resultados dependen de los supuestos."
)

st.set_page_config(page_title="Valoración DCF desde 10-K", layout="wide")


def init_state() -> None:
    """Todas las claves de session_state se crean aquí, con prefijo `dcf_`."""
    defaults = {
        "dcf_statements": None,      # estados normalizados (modelo Pydantic)
        "dcf_assumptions": None,     # supuestos editables
        "dcf_validation": None,      # lista de resultados OK/WARNING/ERROR
        "dcf_result": None,          # resultado del motor
        "dcf_online": False,         # modo online: APAGADO por defecto
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def sidebar() -> None:
    with st.sidebar:
        st.title("DCF desde 10-K")
        st.toggle(
            "Modo online (descarga datos externos)", key="dcf_online",
            help="Apagado: solo se usa el 10-K local. Encendido: se pueden precargar "
                 "Rf, precio y comparables, siempre visibles y editables.",
        )
        st.divider()
        st.caption(DISCLAIMER)          # disclaimer SIEMPRE visible


def show_validation(results: list[dict] | None) -> bool:
    """Muestra avisos. Devuelve False si hay algún ERROR (bloquea la valoración)."""
    if not results:
        st.info("Aún no hay validaciones. Carga un 10-K.")
        return False
    ok = True
    for r in results:
        level, msg = r["level"], r["message"]
        if level == "ERROR":
            st.error(msg); ok = False
        elif level == "WARNING":
            st.warning(msg)
        else:
            st.success(msg)
    return ok


def tab_data() -> None:
    st.header("1. Datos del 10-K")
    uploaded = st.file_uploader("Sube el 10-K (HTML/iXBRL o PDF)", type=["htm", "html", "pdf"])
    if uploaded is not None:
        # TODO: statements = extraction.extract(uploaded.getvalue())
        st.write("Archivo recibido:", uploaded.name)
    if st.session_state.dcf_statements is not None:
        # Mostrar cada cifra con su FUENTE (concepto XBRL / sección) y confianza
        st.dataframe(st.session_state.dcf_statements.to_table())   # TODO


def tab_assumptions() -> None:
    st.header("2. Supuestos")
    st.caption("Todo supuesto es editable. Los valores por defecto indican su fuente.")
    c1, c2, c3 = st.columns(3)
    with c1:
        wacc = pct_input_to_fraction(st.number_input("WACC (%)", 0.0, 30.0, 9.0, 0.1))
        g = pct_input_to_fraction(st.number_input("g perpetuo (%)", 0.0, 6.0, 2.5, 0.1))
    with c2:
        tax = pct_input_to_fraction(st.number_input("Tasa impositiva (%)", 0.0, 50.0, 21.0, 0.5))
        margin = pct_input_to_fraction(st.number_input("Margen EBIT objetivo (%)", -20.0, 60.0, 20.0, 0.5))
    with c3:
        horizon = st.slider("Horizonte (años)", 3, 10, 5)
        mid_year = st.checkbox("Convención de mitad de año", value=False)
    if wacc - g < 0.01:
        st.error("WACC − g debe ser al menos 1 pp.")
    st.session_state.dcf_assumptions = dict(
        wacc=wacc, g=g, tax=tax, ebit_margin=margin, horizon=horizon, mid_year=mid_year)


def tab_results() -> None:
    st.header("3. Resultados")
    can_run = show_validation(st.session_state.dcf_validation)
    if not can_run:
        st.stop()   # un ERROR bloquea el precio: no mostrar cifras como fiables
    if st.button("Calcular DCF", type="primary"):
        # TODO: result = valuation.run(statements, assumptions)  (función pura, sin UI)
        pass
    res = st.session_state.dcf_result
    if res:
        a, b, c, d = st.columns(4)
        a.metric("Valor de empresa", fmt_money(res["ev"]))
        b.metric("Valor del equity", fmt_money(res["equity"]))
        c.metric("Precio por acción", fmt_price(res["price"]))
        d.metric("Peso del TV", fmt_pct(res["tv_share"]))
        if res["tv_share"] > 0.75:
            st.warning("El valor terminal supera el 75 % del valor de empresa.")


def main() -> None:
    init_state()
    sidebar()
    t1, t2, t3, t4 = st.tabs(["Datos", "Supuestos", "Resultados", "Sensibilidad"])
    with t1: tab_data()
    with t2: tab_assumptions()
    with t3: tab_results()
    with t4:
        st.header("4. Sensibilidad")
        st.caption("Tabla WACC × g. Las celdas con WACC − g < 1 pp se muestran como n/d.")
        # TODO: st.dataframe(sensitivity_table(...))
    st.divider()
    st.caption(DISCLAIMER)


main()   # Streamlit ejecuta el módulo como script en cada interacción
