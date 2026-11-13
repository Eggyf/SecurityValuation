"""Interfaz Streamlit: subida del 10-K, revisión de datos, supuestos y resultados.

Ejecutar con: ``uv run streamlit run src/dcf_app/ui/app.py``
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import streamlit as st

from dcf_app.assumptions.defaults import suggest_defaults
from dcf_app.data_sources import (
    get_cik_from_ticker,
    get_damodaran_erp,
    get_edgar_provider,
    get_market_data,
    get_risk_free_rate,
)
from dcf_app.data_sources.base import InvalidTickerError, NetworkError
from dcf_app.export import export_to_excel_bytes
from dcf_app.extraction import extract_financials, validate_extraction
from dcf_app.models.assumptions import Assumptions, DiscountConvention, TerminalValueMethod
from dcf_app.models.fact import Fact, Scale
from dcf_app.models.financials import FinancialStatements
from dcf_app.validation import ValidationResult, ValidationStatus, has_errors, validate_all
from dcf_app.valuation import run_dcf

# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DCF desde 10-K",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Estado de sesión
# ---------------------------------------------------------------------------
if "financials" not in st.session_state:
    st.session_state.financials = None
if "assumptions" not in st.session_state:
    st.session_state.assumptions = None
if "dcf_result" not in st.session_state:
    st.session_state.dcf_result = None
if "dcf_assumptions" not in st.session_state:
    st.session_state.dcf_assumptions = None
if "validation_results" not in st.session_state:
    st.session_state.validation_results = []
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------
DISCLAIMER = (
    "⚠️ **Aviso legal:** Esta herramienta es un ejercicio de modelización financiera. "
    "No constituye asesoramiento financiero, de inversión ni fiscal. "
    "Los resultados dependen de los supuestos introducidos por el usuario."
)


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------


def _extract_from_file(uploaded_file: Any) -> FinancialStatements | None:
    """Extrae datos financieros de un archivo subido (AGENTS.md §6).

    Delega en el orquestador: iXBRL si es HTML, parser de etiquetas si es
    PDF. Muestra las advertencias de la extracción (degradación segura,
    AGENTS.md §2.8).
    """
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in (".html", ".htm", ".xhtml", ".pdf"):
        st.error(f"Formato no soportado: {suffix}")
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        financials = extract_financials(tmp_path)
        for warning in validate_extraction(financials):
            st.warning(warning)
        return financials
    except Exception as e:
        st.error(f"Error en la extracción: {e}")
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _download_from_edgar(ticker: str) -> FinancialStatements | None:
    """Descarga y extrae los ultimos 10-K de un ticker desde EDGAR.

    Descarga hasta 3 anios para tener datos suficientes para los scores
    (Piotroski necesita t-2, Beneish necesita 2 ejercicios).

    Args:
        ticker: simbodo de la empresa (ej: "AAPL").

    Returns:
        FinancialStatements o None si falla.
    """
    try:
        with st.spinner(f"Buscando {ticker} en EDGAR..."):
            cik = get_cik_from_ticker(ticker)
            st.info(f"CIK: {cik}")

            provider = get_edgar_provider()
            filings = provider.get_recent_filings(cik, "10-K", n=3)
            if not filings:
                st.error(f"No se encontro ningun 10-K para {ticker}")
                return None

            all_financials = []
            for filing in filings:
                accession = filing.get("accessionNumber")
                primary_doc = filing.get("primaryDocument")
                report_date = filing.get("reportDate", "")
                if not isinstance(accession, str):
                    st.warning("Accession number inválido, saltando...")
                    continue
                st.info(f"Descargando 10-K: {accession} ({report_date})")

                filing_result = provider.download_filing(
                    accession,
                    cik=cik,
                    primary_document=(
                        primary_doc if isinstance(primary_doc, str) else None
                    ),
                )
                if not isinstance(filing_result.data, bytes):
                    st.warning(f"No se pudo descargar {accession}")
                    continue

                suffix = ".html"
                if isinstance(primary_doc, str) and primary_doc.lower().endswith(".pdf"):
                    suffix = ".pdf"

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(filing_result.data)
                    tmp_path = tmp.name

                try:
                    fs = extract_financials(tmp_path)
                    all_financials.append(fs)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            if not all_financials:
                st.error("No se pudo extraer ningun 10-K")
                return None

            latest = all_financials[0]
            for warning in validate_extraction(latest):
                st.warning(warning)

            return latest

    except InvalidTickerError as e:
        st.error(f"Ticker invalido: {e}")
        return None
    except NetworkError as e:
        st.error(f"Error de red con EDGAR: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado descargando desde EDGAR: {e}")
        return None


def _fact_display(fact: Fact | None) -> str:
    """Formatea un Fact para mostrar en la UI, según su unidad.

    - Moneda: normalizada a millones (AGENTS.md §2.6).
    - ``USD_per_share``: valor por acción tal cual (sin reescalar).
    - ``shares``: millones de acciones.
    - ``ratio``: porcentaje.
    """
    if fact is None or fact.value is None:
        return "—"

    if fact.unit == "USD_per_share":
        return f"${fact.value:,.2f}"
    if fact.unit == "shares":
        millions = fact.to_scale(Scale.MILLIONS)
        return "—" if millions is None else f"{millions:,.1f} M acc."
    if fact.unit == "ratio":
        return f"{fact.value:.1%}"

    millions = fact.to_scale(Scale.MILLIONS)
    if millions is None:
        return "—"
    symbol = "$" if fact.unit.startswith("USD") else f"{fact.unit} "
    return f"{symbol}{millions:,.1f} M"


def _fact_source(fact: Fact | None) -> str:
    """Procedencia de una cifra para mostrar en la UI (AGENTS.md §2.3)."""
    if fact is None or fact.value is None:
        return ""
    return fact.source.location or fact.source.concept or ""


def _render_statement_table(title: str, rows: list[tuple[str, Fact | None]]) -> None:
    """Renderiza una tabla de partidas con valor y fuente (trazabilidad)."""
    import pandas as pd

    st.subheader(title)
    st.dataframe(
        pd.DataFrame(
            {
                "Partida": [label for label, _ in rows],
                "Valor": [_fact_display(fact) for _, fact in rows],
                "Fuente": [_fact_source(fact) for _, fact in rows],
            }
        ),
        width="stretch",
    )


def _render_validation_results(results: list[ValidationResult]) -> None:
    """Muestra los resultados de validación."""
    for r in results:
        if r.status == ValidationStatus.OK:
            st.success(f"✅ {r.name}: {r.message}")
        elif r.status == ValidationStatus.WARNING:
            st.warning(f"⚠️ {r.name}: {r.message}")
        else:
            st.error(f"❌ {r.name}: {r.message}")


def _pct(value: float | None) -> float | None:
    """Convierte un porcentaje del widget a fracción (AGENTS.md §8)."""
    return None if value is None else value / 100.0


def _missing_market_inputs(assumptions: Assumptions) -> list[str]:
    """Inputs obligatorios que no están en el 10-K (AGENTS.md §7.3).

    La UI los muestra vacíos y exige rellenarlos antes de ejecutar el DCF:
    no se sustituyen por valores típicos (AGENTS.md §2.1).
    """
    missing: list[str] = []
    if assumptions.risk_free_rate is None:
        missing.append("Rf (tasa libre de riesgo)")
    if assumptions.equity_beta is None:
        missing.append("Beta del equity")
    if assumptions.equity_risk_premium is None:
        missing.append("ERP (prima de riesgo)")
    if assumptions.cost_of_debt is None:
        missing.append("Kd (coste de la deuda)")
    if assumptions.tax_rate is None:
        missing.append("Tasa impositiva")
    if assumptions.market_equity_value is None:
        missing.append("Capitalización de mercado")
    if assumptions.stock_price_current is None:
        missing.append("Precio de la acción")
    if assumptions.shares_outstanding is None:
        missing.append("Acciones en circulación")
    return missing


def _render_assumptions_form() -> Assumptions | None:
    """Renderiza el formulario de supuestos y devuelve los valores.

    Los defaults se pre-rellenan solo con datos del 10-K (AGENTS.md §7.1,
    §7.2), con un caption que indica su origen. Los inputs de mercado que
    no están en el documento se muestran vacíos y son obligatorios para
    ejecutar el DCF (§7.3).
    """
    st.subheader("Supuestos de valoración")

    # Intentar precargar datos de mercado (FRED + Twelve Data + Damodaran)
    rf_default = None
    try:
        rf_val = get_risk_free_rate()
        if rf_val is not None:
            rf_default = rf_val
            st.caption(f"📡 Rf precargada desde FRED (DGS10): {rf_val:.2f} %")
    except Exception:
        pass

    erp_default = None
    try:
        erp_val = get_damodaran_erp()
        if erp_val is not None:
            erp_default = erp_val * 100.0  # Convertir a porcentaje
            st.caption(f"📡 ERP precargada desde Damodaran: {erp_val:.2%}")
    except Exception:
        pass

    # Precargar precio y market cap desde Twelve Data
    price_default = None
    market_cap_default = None
    shares_default_td = None
    ticker_for_market = st.session_state.get("edgar_ticker", "")
    if ticker_for_market:
        try:
            md = get_market_data(ticker_for_market)
            if md:
                price_default = md.get("price")
                market_cap_default = md.get("market_cap")
                shares_default_td = md.get("shares_outstanding")
                if price_default:
                    st.caption(f"📡 Precio precargado desde FMP: ${price_default:.2f}")
                if market_cap_default:
                    st.caption(f"📡 Market cap precargado: {market_cap_default:,.0f} M")
        except Exception:
            pass

    # Calcular coste de la deuda aproximado desde el 10-K
    kd_default = None
    financials_for_kd = st.session_state.financials
    if (
        financials_for_kd is not None
        and financials_for_kd.income_statements
        and financials_for_kd.balance_sheets
    ):
        try:
            last_income = financials_for_kd.income_statements[-1]
            interest = None
            if (
                last_income.interest_expense is not None
                and last_income.interest_expense.value is not None
            ):
                from dcf_app.models.fact import Scale as FactScale
                interest = last_income.interest_expense.to_scale(FactScale.MILLIONS)
            last_balance = financials_for_kd.balance_sheets[-1]
            st_debt = 0.0
            lt_debt = 0.0
            if (
                last_balance.short_term_debt is not None
                and last_balance.short_term_debt.value is not None
            ):
                st_debt = last_balance.short_term_debt.to_scale(FactScale.MILLIONS) or 0.0
            if (
                last_balance.long_term_debt is not None
                and last_balance.long_term_debt.value is not None
            ):
                lt_debt = last_balance.long_term_debt.to_scale(FactScale.MILLIONS) or 0.0
            total_debt = st_debt + lt_debt
            if interest is not None and total_debt > 0:
                kd_default = (interest / total_debt) * 100.0
                if kd_default > 15:
                    kd_default = 15.0  # Cap at 15%
                st.caption(f"📡 Kd aproximado (intereses/deuda del 10-K): {kd_default:.2f} %")
        except Exception:
            pass

    financials = st.session_state.financials
    suggested = suggest_defaults(financials) if financials is not None else None
    income_years: tuple[int, int] | None = None
    if financials is not None and financials.income_statements:
        statements = financials.income_statements
        income_years = (statements[0].fiscal_year, statements[-1].fiscal_year)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Proyección**")
        horizon = st.slider("Horizonte de proyección (años)", 3, 10, 5)

        growth_pct = 5.0
        if suggested is not None and suggested.revenue_cagr is not None:
            growth_pct = suggested.revenue_cagr * 100.0
        initial_growth = (
            st.number_input("Crecimiento inicial de ingresos (%)", -5.0, 25.0, growth_pct, 0.5)
            / 100.0
        )
        if suggested is not None and suggested.revenue_cagr is not None and income_years:
            st.caption(
                f"Sugerido por el 10-K: CAGR FY{income_years[0]}-{income_years[1]} = "
                f"{suggested.revenue_cagr:.1%} (acotado a [-5 %, 25 %], AGENTS.md §7.2)."
            )
        else:
            st.caption("Sin histórico suficiente en el 10-K; ajústalo manualmente.")

        terminal_growth = st.number_input("Crecimiento terminal g (%)", 2.0, 2.5, 2.5, 0.05) / 100.0
        st.caption("Rango de metodología §7.4: 2,0-2,5 %, nunca superior a Rf.")

        margin_pct = 25.0
        if suggested is not None and suggested.ebit_margin_current is not None:
            margin = suggested.ebit_margin_current * 100.0
            if 0.0 <= margin <= 90.0:
                margin_pct = margin
        ebit_margin_target = (
            st.number_input("Margen EBIT objetivo (%)", 0.0, 90.0, margin_pct, 0.5) / 100.0
        )
        if suggested is not None and suggested.ebit_margin_current is not None:
            if suggested.ebit_margin_current < 0:
                st.warning(
                    "El EBIT del último ejercicio es negativo: la v1 no cubre este caso "
                    "(AGENTS.md §15)."
                )
            else:
                st.caption(
                    f"Sugerido: margen EBIT actual del 10-K = {suggested.ebit_margin_current:.1%}."
                )

    with col2:
        st.markdown("**WACC**")
        risk_free = _pct(
            st.number_input(
                "Tasa libre de riesgo Rf (%)",
                0.0,
                10.0,
                rf_default,
                0.1,
                help="Bono del Tesoro de EE. UU. a 10 años. No está en el 10-K (AGENTS.md §7.3).",
            )
        )
        beta = st.number_input(
            "Beta del equity",
            0.0,
            3.0,
            None,
            0.1,
            help="Beta apalancada. No está en el 10-K (AGENTS.md §7.3).",
        )
        erp = _pct(
            st.number_input(
                "Prima de riesgo del mercado ERP (%)",
                0.0,
                15.0,
                erp_default,
                0.5,
                help="Referencia: datasets de Damodaran. No está en el 10-K (AGENTS.md §7.3).",
            )
        )
        cost_of_debt = _pct(
            st.number_input(
                "Coste de la deuda Kd (%)",
                0.0,
                15.0,
                kd_default,
                0.5,
                help="Aproximación: intereses / deuda total (del 10-K).",
            )
        )

        tax_pct = None
        if suggested is not None and suggested.effective_tax_rate is not None:
            tax_pct = suggested.effective_tax_rate * 100.0
        tax_rate = _pct(st.number_input("Tasa impositiva (%)", 15.0, 30.0, tax_pct, 1.0))
        if suggested is not None and suggested.effective_tax_rate is not None:
            st.caption(
                f"Sugerida: efectiva media del 10-K = {suggested.effective_tax_rate:.1%} "
                "(acotada a [15 %, 30 %], AGENTS.md §7.1)."
            )
        else:
            st.caption("Sin datos de impuestos en el 10-K; introdúcela manualmente.")

    st.markdown("**Datos de mercado** — no están en el 10-K (AGENTS.md §7.3)")
    col3, col4 = st.columns(2)
    with col3:
        market_cap = st.number_input(
            "Capitalización de mercado (M USD)",
            0.0,
            1e8,
            market_cap_default,
            10.0,
            help="Aproximación si no la conoces: precio x acciones en circulación.",
        )
        debt_default = suggested.book_debt if suggested is not None else None
        market_debt = st.number_input(
            "Deuda (M USD)",
            0.0,
            1e8,
            debt_default,
            10.0,
            help="Por defecto, la deuda contable del balance (ST+LT), editable.",
        )
        if debt_default is not None:
            st.caption(f"Pre-rellenada con la deuda contable del balance: {debt_default:,.0f} M.")
    with col4:
        stock_price = st.number_input(
            "Precio de la acción (USD)",
            0.0,
            1e4,
            price_default,
            1.0,
            help="Precio actual; necesario para el upside/downside y la dilución (AGENTS.md §7.6).",
        )
        shares_default = suggested.diluted_weighted_shares if suggested is not None else None
        if shares_default_td is not None and shares_default is None:
            shares_default = shares_default_td / 1e6  # Convertir a millones
        shares = st.number_input(
            "Acciones en circulación (M)",
            0.0,
            1e6,
            shares_default,
            1.0,
            help="Número exacto si lo tienes; el 10-K solo aporta las medias diluidas.",
        )
        if shares_default is not None:
            st.caption(
                f"Pre-rellenadas con las medias diluidas del 10-K: {shares_default:,.0f} M "
                "(aproximación; ajústalas si tienes el dato exacto)."
            )

    st.markdown("**Valor terminal**")
    terminal_method = st.selectbox(
        "Método de valor terminal",
        ["Gordon Growth", "Múltiplo de salida"],
    )
    exit_multiple = None
    if terminal_method == "Múltiplo de salida":
        exit_multiple = st.number_input("Múltiplo EV/EBITDA", 0.0, 50.0, 10.0, 0.5)
        st.caption("Supuesto tuyo; los peers llegarán en v2 (AGENTS.md §14.4).")

    st.markdown("**Convención de descuento**")
    convention = st.selectbox("Convención", ["Fin de año", "Mitad de año"])

    # Datos de la empresa (de los estados financieros si están disponibles)
    company_name = "Empresa"
    fiscal_year_end = date(2024, 12, 31)
    if financials is not None:
        company_name = financials.company_name
        if financials.income_statements:
            fiscal_year_end = financials.income_statements[-1].period_end

    try:
        assumptions = Assumptions(
            company_name=company_name,
            fiscal_year_end=fiscal_year_end,
            valuation_date=fiscal_year_end,
            forecast_horizon=horizon,
            initial_revenue_growth=initial_growth,
            terminal_revenue_growth=terminal_growth,
            ebit_margin_target=ebit_margin_target,
            risk_free_rate=risk_free,
            equity_beta=beta,
            equity_risk_premium=erp,
            market_equity_value=market_cap,
            market_debt_value=market_debt,
            cost_of_debt=cost_of_debt,
            tax_rate=tax_rate,
            stock_price_current=stock_price,
            shares_outstanding=shares,
            terminal_value_method=(
                TerminalValueMethod.GORDON_GROWTH
                if terminal_method == "Gordon Growth"
                else TerminalValueMethod.MULTIPLE
            ),
            exit_multiple_ebitda=exit_multiple,
            discount_convention=(
                DiscountConvention.END_OF_YEAR
                if convention == "Fin de año"
                else DiscountConvention.MID_YEAR
            ),
        )
        return assumptions
    except Exception as e:
        st.error(f"Error en los supuestos: {e}")
        return None


def _render_results(result: Any) -> None:
    """Muestra los resultados del DCF."""
    st.subheader("Resultados de la valoración")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Enterprise Value (M USD)", f"{result.enterprise_value:,.0f}")
    with col2:
        st.metric("Equity Value (M USD)", f"{result.equity_value:,.0f}")
    with col3:
        st.metric("Precio por acción (USD)", f"{result.price_per_share:,.2f}")

    if result.upside_downside is not None:
        color = "green" if result.upside_downside > 0 else "red"
        st.markdown(f"**Upside/Downside vs. mercado:** :{color}[{result.upside_downside:+.1f} %]")

    # Aviso de cordura
    if not result.is_reasonable:
        st.warning("El resultado puede no ser razonable (TV > 75% del EV, precio negativo, etc.).")
    if result.tv_percentage > 0.75:
        st.warning(f"⚠️ El valor terminal representa el {result.tv_percentage:.1%} del EV (> 75%).")

    # Proyección
    st.subheader("Proyección de flujos (FCFF)")
    import pandas as pd

    forecast_df = pd.DataFrame(
        {
            "Año": result.forecast_years,
            "Ingresos": result.revenue_forecast,
            "EBIT": result.ebit_forecast,
            "NOPAT": result.nopat_forecast,
            "FCFF": result.fcff_forecast,
            "CapEx": result.capex_forecast,
            "ΔNWC": result.delta_nwc_forecast,
        }
    )
    st.dataframe(forecast_df, width="stretch")

    # Puente
    st.subheader("Puente EV → Equity")
    bridge_df = pd.DataFrame(
        list(result.bridge_breakdown.items()),
        columns=["Partida", "Valor (M USD)"],
    )
    st.dataframe(bridge_df, width="stretch")

    # Sensibilidades
    st.subheader("Sensibilidad: WACC x g → Precio por acción")
    if result.sensitivity_wacc_growth:
        # Convertir a matriz
        waccs = sorted({k[0] for k in result.sensitivity_wacc_growth})
        gs = sorted({k[1] for k in result.sensitivity_wacc_growth})
        matrix = []
        for w in waccs:
            row = []
            for g in gs:
                val = result.sensitivity_wacc_growth.get((w, g), float("nan"))
                row.append(f"{val:.2f}" if val == val else "N/A")
            matrix.append(row)
        sens_df = pd.DataFrame(
            matrix, index=[f"{w:.1%}" for w in waccs], columns=[f"{g:.1%}" for g in gs]
        )
        st.dataframe(sens_df, width="stretch")

    st.subheader("Sensibilidad: Margen EBIT x Crecimiento → Precio por acción")
    if result.sensitivity_margin_growth:
        margins = sorted({k[0] for k in result.sensitivity_margin_growth})
        growths = sorted({k[1] for k in result.sensitivity_margin_growth})
        matrix = []
        for m in margins:
            row = []
            for gr in growths:
                val = result.sensitivity_margin_growth.get((m, gr), float("nan"))
                row.append(f"{val:.2f}" if val == val else "N/A")
            matrix.append(row)
        sens_df = pd.DataFrame(
            matrix, index=[f"{m:.1%}" for m in margins], columns=[f"{gr:.1%}" for gr in growths]
        )
        st.dataframe(sens_df, width="stretch")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Punto de entrada de la aplicación Streamlit."""
    st.title("📊 Valoración DCF desde Form 10-K")
    st.markdown(DISCLAIMER)

    # Guía rápida para usuarios no financieros
    with st.expander("📖 ¿Cómo usar esta app? (guía rápida)", expanded=False):
        st.markdown(
            """
            **Esta app valora empresas usando el método DCF (Flujo de Caja Descontado).**

            **Pasos:**
            1. **Subir 10-K** (pestaña 1): Sube el PDF/HTML, o descárgalo desde EDGAR.
            2. **Revisar datos** (pestaña 2): Verifica los datos financieros extraídos.
            3. **Supuestos** (pestaña 3): Ajusta crecimiento, márgenes, WACC, etc.
            4. **Resultados** (pestaña 4): Ve el valor de la empresa y exporta a Excel.
            5. **Reverse DCF** (pestaña 5): Descubre qué descuenta el mercado.
            6. **Calidad** (pestaña 6): Scores de salud financiera (Piotroski, Altman, Beneish).

            **¿No sabes qué poner en los supuestos?**
            - **Rf**: Ya se precarga desde FRED (bono del Tesoro USA a 10 años).
            - **Beta**: Búscala en Yahoo Finance → "Statistics" → "Beta".
            - **ERP**: Ya se precarga desde Damodaran (~4%). Puedes usar 5% como referencia.
            - **Kd**: Intereses pagados / Deuda total (del 10-K).
            - **Market Cap, Precio, Acciones**: Se precargan desde FMP si introduces el ticker.

            **⚠️ Esto no es asesoramiento financiero.** Los resultados dependen de tus supuestos.
            """
        )

    tabs = st.tabs(
        [
            "1. Subir 10-K",
            "2. Revisar datos",
            "3. Supuestos",
            "4. Resultados",
            "5. Reverse DCF",
            "6. Calidad",
        ]
    )

    # --- Tab 1: Subir 10-K ---
    with tabs[0]:
        st.header("Subir archivo 10-K")

        # Modo online/offline
        online_mode = st.checkbox(
            "Modo online (descargar desde EDGAR)", value=st.session_state.get("online_mode", False)
        )
        st.session_state.online_mode = online_mode

        if online_mode:
            st.markdown("**⚠️ Requisitos modo online:**")
            st.markdown("- Variable de entorno `SEC_USER_AGENT` configurada (ver `.env.example`)")
            st.markdown("- Conexión a internet")
            st.markdown("- EDGAR puede limitar a 10 peticiones/s")

            ticker_input = (
                st.text_input(
                    "Introduce el ticker (ej: AAPL, MSFT)",
                    value=st.session_state.get("edgar_ticker", ""),
                )
                .upper()
                .strip()
            )
            st.session_state.edgar_ticker = ticker_input

            if ticker_input and st.button("Buscar en EDGAR"):
                if not ticker_input:
                    st.error("Introduce un ticker")
                else:
                    financials = _download_from_edgar(ticker_input)
                    if financials is not None:
                        st.session_state.financials = financials
                        st.session_state.uploaded_file_name = f"{ticker_input}_10-K_EDGAR"
                        st.session_state.validation_results = validate_all(financials)
                        st.success(f"10-K de {ticker_input} descargado y extraído correctamente.")
                        st.info(f"Empresa: {financials.company_name}")
                        if financials.income_statements:
                            st.info(f"Ejercicios: {financials.fiscal_years}")
                        else:
                            st.warning(
                                "No se encontraron estados financieros. Introduce los datos manualmente en la pestaña de Supuestos."  # noqa: E501
                            )
                        st.rerun()

        # Subida local (siempre disponible)
        st.markdown("---")
        st.subheader("O: sube un archivo local")
        uploaded = st.file_uploader(
            "Selecciona un archivo 10-K (HTML o PDF)",
            type=["html", "htm", "xhtml", "pdf"],
        )
        if uploaded is not None and st.button("Extraer datos"):
            with st.spinner("Extrayendo datos..."):
                financials = _extract_from_file(uploaded)
                if financials is not None:
                    st.session_state.financials = financials
                    st.session_state.uploaded_file_name = uploaded.name
                    st.session_state.validation_results = validate_all(financials)
                    st.success("Datos extraídos correctamente.")
                    st.info(f"Empresa: {financials.company_name}")
                    if financials.income_statements:
                        st.info(f"Ejercicios: {financials.fiscal_years}")
                    else:
                        st.warning(
                            "No se encontraron estados financieros. Introduce los datos manualmente en la pestaña de Supuestos."  # noqa: E501
                        )

    # --- Tab 2: Revisar datos ---
    with tabs[1]:
        st.header("Revisar datos extraídos")
        if st.session_state.financials is None:
            st.info("Sube un archivo 10-K en la pestaña anterior.")
        else:
            financials = st.session_state.financials
            st.markdown(f"**Empresa:** {financials.company_name}")
            if financials.income_statements:
                st.markdown(f"**Ejercicios:** {financials.fiscal_years}")

            # Mostrar estados financieros (ultimo ejercicio de cada estado)
            if financials.income_statements:
                last_income = financials.income_statements[-1]
                _render_statement_table(
                    f"Cuenta de resultados (FY{last_income.fiscal_year})",
                    [
                        ("Revenue", last_income.revenue),
                        ("COGS", last_income.cogs),
                        ("Gross Profit", last_income.gross_profit),
                        ("SG&A", last_income.sga),
                        ("R&D", last_income.rd),
                        ("D&A", last_income.depreciation_amortization),
                        ("EBIT", last_income.ebit),
                        ("Interest Expense", last_income.interest_expense),
                        ("Pretax Income", last_income.pretax_income),
                        ("Income Tax", last_income.income_tax_expense),
                        ("Net Income", last_income.net_income),
                        ("Diluted EPS", last_income.diluted_eps),
                        ("Diluted Shares", last_income.diluted_weighted_shares),
                        ("SBC", last_income.sbc),
                    ],
                )

            if financials.balance_sheets:
                last_balance = financials.balance_sheets[-1]
                _render_statement_table(
                    f"Balance (FY{last_balance.fiscal_year})",
                    [
                        ("Cash & Equivalents", last_balance.cash_and_equivalents),
                        ("ST Investments", last_balance.short_term_investments),
                        ("Accounts Receivable", last_balance.accounts_receivable),
                        ("Inventory", last_balance.inventory),
                        ("Accounts Payable", last_balance.accounts_payable),
                        ("Accrued Liabilities", last_balance.accrued_liabilities),
                        ("ST Debt", last_balance.short_term_debt),
                        ("LT Debt", last_balance.long_term_debt),
                        (
                            "Leases op. (corriente)",
                            last_balance.operating_lease_liabilities_current,
                        ),
                        (
                            "Leases op. (no corriente)",
                            last_balance.operating_lease_liabilities_noncurrent,
                        ),
                        ("Preferred Stock", last_balance.preferred_stock),
                        ("Non-controlling Interest", last_balance.non_controlling_interest),
                        ("Total Equity", last_balance.total_equity),
                        ("Total Assets", last_balance.total_assets),
                        ("Total Liabilities", last_balance.total_liabilities),
                    ],
                )

            if financials.cash_flow_statements:
                last_cash = financials.cash_flow_statements[-1]
                _render_statement_table(
                    f"Flujo de caja (FY{last_cash.fiscal_year})",
                    [
                        ("CFO", last_cash.cfo),
                        ("CapEx", last_cash.capex),
                        ("D&A", last_cash.depreciation_amortization),
                        ("SBC", last_cash.sbc),
                        ("Net Change in Cash", last_cash.net_change_in_cash),
                    ],
                )

            # Validaciones
            st.subheader("Validaciones de integridad")
            if st.session_state.validation_results:
                _render_validation_results(st.session_state.validation_results)
                if has_errors(st.session_state.validation_results):
                    st.error("Hay errores de validación. La valoración puede no ser fiable.")

    # --- Tab 3: Supuestos ---
    with tabs[2]:
        st.header("Supuestos de valoración")
        assumptions = _render_assumptions_form()
        if assumptions is not None:
            st.session_state.assumptions = assumptions
            if st.button("Ejecutar DCF"):
                if st.session_state.financials is None:
                    st.error("Primero sube un archivo 10-K en la pestaña 1.")
                else:
                    missing = _missing_market_inputs(assumptions)
                    if missing:
                        st.warning(
                            "Faltan inputs que no están en el 10-K (AGENTS.md §7.3): "
                            + ", ".join(missing)
                            + ". Rellénalos arriba antes de ejecutar."
                        )
                    else:
                        with st.spinner("Calculando DCF..."):
                            try:
                                result = run_dcf(assumptions, st.session_state.financials)
                                st.session_state.dcf_result = result
                                st.session_state.dcf_assumptions = assumptions
                                st.success("DCF calculado correctamente.")
                            except Exception as e:
                                st.error(f"Error en el DCF: {e}")

    # --- Tab 4: Resultados ---
    with tabs[3]:
        st.header("Resultados")
        result = st.session_state.dcf_result
        if result is None:
            st.info("Ejecuta el DCF en la pestaña de Supuestos.")
        else:
            _render_results(result)

            # Exportación a Excel (AGENTS.md §1: informe UI + Excel).
            st.subheader("Exportar a Excel")
            financials = st.session_state.financials
            assumptions_used = st.session_state.dcf_assumptions
            if financials is None or assumptions_used is None:
                st.warning("Faltan datos de sesión para exportar; vuelve a ejecutar el DCF.")
            else:
                try:
                    data = export_to_excel_bytes(result, financials, assumptions_used)
                    company = "".join(c if c.isalnum() else "_" for c in financials.company_name)
                    fiscal_year = (
                        financials.income_statements[-1].fiscal_year
                        if financials.income_statements
                        else ""
                    )
                    st.download_button(
                        "⬇️ Descargar informe Excel (fórmulas vivas)",
                        data=data,
                        file_name=f"DCF_{company}_{fiscal_year}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception as e:
                    st.error(f"Error generando el Excel: {e}")

    # --- Tab 5: Reverse DCF ---
    with tabs[4]:
        st.header("Reverse DCF — ¿Qué descuenta el mercado?")
        st.markdown(
            "Dado el precio de mercado, resuelve qué crecimiento o margen "
            "tendría que cumplirse para que el DCF dé ese precio."
        )

        result = st.session_state.dcf_result
        financials = st.session_state.financials
        assumptions = st.session_state.assumptions

        if result is None or financials is None or assumptions is None:
            st.info("Ejecuta primero el DCF en la pestaña de Supuestos.")
        else:
            market_price = assumptions.stock_price_current
            if market_price is None or market_price <= 0:
                st.warning("Introduce el precio de la acción en los Supuestos.")
            else:
                st.markdown(f"**Precio de mercado:** ${market_price:.2f}")

                if st.button("Calcular Reverse DCF"):
                    from dcf_app.valuation.reverse_dcf import (
                        reverse_dcf_growth,
                        reverse_dcf_margin,
                    )

                    with st.spinner("Calculando..."):
                        r_growth = reverse_dcf_growth(assumptions, financials, market_price)
                        r_margin = reverse_dcf_margin(assumptions, financials, market_price)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Crecimiento inicial implícito")
                        if r_growth.has_solution and r_growth.implied_value is not None:
                            st.metric("Crecimiento implícito", f"{r_growth.implied_value:.1%}")
                            st.markdown(r_growth.message)
                            if r_growth.historical_comparison:
                                hist = r_growth.historical_comparison
                                cagr_3y = hist.get("cagr_3y")
                                if cagr_3y is not None:
                                    st.caption(f"CAGR 3 años histórico: {cagr_3y:.1%}")
                                cagr_5y = hist.get("cagr_5y")
                                if cagr_5y is not None:
                                    st.caption(f"CAGR 5 años histórico: {cagr_5y:.1%}")
                        else:
                            st.warning(r_growth.message)

                    with col2:
                        st.subheader("Margen EBIT implícito")
                        if r_margin.has_solution and r_margin.implied_value is not None:
                            st.metric("Margen EBIT implícito", f"{r_margin.implied_value:.1%}")
                            st.markdown(r_margin.message)
                            if r_margin.historical_comparison:
                                hist = r_margin.historical_comparison
                                max_m = hist.get("max_margin")
                                if max_m is not None:
                                    st.caption(f"Margen EBIT máximo histórico: {max_m:.1%}")
                                avg_m = hist.get("avg_margin")
                                if avg_m is not None:
                                    st.caption(f"Margen EBIT medio histórico: {avg_m:.1%}")
                        else:
                            st.warning(r_margin.message)

    # --- Tab 6: Calidad ---
    with tabs[5]:
        st.header("Scores de calidad y ratios")
        st.markdown(
            "Piotroski F-Score, Altman Z-Score, Beneish M-Score y ratios "
            "financieros. Son señales de alerta, no veredictos de inversión."
        )

        financials = st.session_state.financials
        if financials is None:
            st.info("Sube un 10-K en la pestaña 1 para ver los scores.")
        else:
            from dcf_app.analysis import (
                altman_z_score,
                beneish_m_score,
                earnings_quality,
                extract_beneish_years,
                extract_year_data,
                financial_ratios,
                piotroski_f_score,
            )

            cur = extract_year_data(financials, -1)
            prev = (
                extract_year_data(financials, -2)
                if len(financials.income_statements) >= 2
                else None
            )

            # Piotroski (necesita 2 ejercicios)
            if prev is not None:
                try:
                    prev_prev_assets = None
                    if len(financials.income_statements) >= 3:
                        prev_prev = extract_year_data(financials, -3)
                        prev_prev_assets = prev_prev.total_assets
                    piot = piotroski_f_score(cur, prev, prev_prev_assets)
                    st.subheader("Piotroski F-Score")
                    if piot.value is not None:
                        st.metric("F-Score", f"{piot.value:.0f} / 9")
                        with st.expander("Desglose"):
                            for k, v in piot.components.items():
                                st.write(f"- {k}: {'✅' if v else '❌'}")
                    else:
                        st.warning(f"Datos insuficientes: {', '.join(piot.missing)}")
                except Exception as e:
                    st.warning(f"No se pudo calcular Piotroski: {e}")

            # Altman Z-Score
            try:
                wc = (
                    (cur.current_assets or 0) - (cur.current_liabilities_total or 0)
                    if cur.current_assets and cur.current_liabilities_total
                    else None
                )
                z = altman_z_score(
                    "Zdoubleprime",
                    working_capital=wc,
                    retained_earnings=cur.retained_earnings,
                    ebit=cur.ebit,
                    equity=cur.total_equity,  # valor contable
                    sales=cur.revenue,
                    total_assets=cur.total_assets,
                    total_liabilities=cur.total_liabilities,
                )
                st.subheader("Altman Z-Score (Z'')")
                if z.value is not None:
                    st.metric("Z-Score", f"{z.value:.2f}")
                    st.caption(f"Zona: {z.components.get('zone', 'N/A')}")
                    with st.expander("Componentes"):
                        for k, v in z.components.items():
                            if k not in ("zone", "zones"):
                                if isinstance(v, float):
                                    st.write(f"- {k}: {v:.4f}")
                                else:
                                    st.write(f"- {k}: {v}")
                else:
                    st.warning(f"Datos insuficientes: {', '.join(z.missing)}")
            except Exception as e:
                st.warning(f"No se pudo calcular Altman Z: {e}")

            # Beneish M-Score
            try:
                beneish_years = extract_beneish_years(financials)
                if beneish_years is not None:
                    m = beneish_m_score(beneish_years[1], beneish_years[0])
                    st.subheader("Beneish M-Score")
                    if m.value is not None:
                        st.metric("M-Score", f"{m.value:.2f}")
                        st.caption(m.note)
                        with st.expander("Componentes"):
                            for k, v in m.components.items():
                                st.write(f"- {k}: {v:.4f}")
                    else:
                        st.warning(f"Datos insuficientes: {', '.join(m.missing)}")
                else:
                    st.info("Se necesitan 2 ejercicios para Beneish M-Score.")
            except Exception as e:
                st.warning(f"No se pudo calcular Beneish M: {e}")

            # Calidad de beneficios
            try:
                if (
                    cur.net_income is not None
                    and cur.cfo is not None
                    and cur.total_assets is not None
                ):
                    eq = earnings_quality(cur.net_income, cur.cfo, cur.total_assets)
                    st.subheader("Calidad de beneficios")
                    if eq.value is not None:
                        st.metric("CFO / Beneficio neto", f"{eq.value:.2f}")
                        accruals = eq.components.get("accruals_ratio")
                        if accruals is not None:
                            st.caption(f"Ratio de devengos: {accruals:.4f}")
                    else:
                        st.warning(f"Datos insuficientes: {', '.join(eq.missing)}")
                else:
                    st.info("Se necesitan NI, CFO y activos totales.")
            except Exception as e:
                st.warning(f"No se pudo calcular calidad de beneficios: {e}")

            # Ratios financieros
            try:
                ratios = financial_ratios(cur)
                st.subheader("Ratios financieros")
                ratio_cols = st.columns(3)
                with ratio_cols[0]:
                    if ratios.get("gross_margin") is not None:
                        st.metric("Margen bruto", f"{ratios['gross_margin']:.1%}")
                    if ratios.get("ebit_margin") is not None:
                        st.metric("Margen EBIT", f"{ratios['ebit_margin']:.1%}")
                    if ratios.get("roe") is not None:
                        st.metric("ROE", f"{ratios['roe']:.1%}")
                with ratio_cols[1]:
                    if ratios.get("dso") is not None:
                        st.metric("DSO (días)", f"{ratios['dso']:.0f}")
                    if ratios.get("dio") is not None:
                        st.metric("DIO (días)", f"{ratios['dio']:.0f}")
                    if ratios.get("dpo") is not None:
                        st.metric("DPO (días)", f"{ratios['dpo']:.0f}")
                with ratio_cols[2]:
                    if ratios.get("cash_conversion_cycle") is not None:
                        st.metric("CCC (días)", f"{ratios['cash_conversion_cycle']:.0f}")
                    if ratios.get("interest_coverage") is not None:
                        st.metric("Cobertura intereses", f"{ratios['interest_coverage']:.1f}x")
                    if ratios.get("fcf_conversion") is not None:
                        st.metric("Conversión FCF", f"{ratios['fcf_conversion']:.2f}")
            except Exception as e:
                st.warning(f"No se pudieron calcular los ratios: {e}")

    # Disclaimer final
    st.markdown("---")
    st.markdown(DISCLAIMER)


if __name__ == "__main__":
    main()
