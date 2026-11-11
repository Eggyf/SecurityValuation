"""Interfaz Streamlit: subida del 10-K, revisión de datos, supuestos y resultados.

Ejecutar con: ``uv run streamlit run src/dcf_app/ui/app.py``
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import streamlit as st

from dcf_app.extraction import extract_ixbrl, extract_pdf_tables, extract_pdf_text
from dcf_app.models.assumptions import Assumptions, DiscountConvention, TerminalValueMethod
from dcf_app.models.fact import Scale
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
    """Extrae datos financieros de un archivo subido."""
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        if suffix in (".html", ".htm", ".xhtml"):
            data = extract_ixbrl(tmp_path)
            # Convertir facts a FinancialStatements (simplificado)
            return _facts_to_financials(data, uploaded_file.name)
        elif suffix == ".pdf":
            text = extract_pdf_text(tmp_path)
            tables = extract_pdf_tables(tmp_path)
            return _pdf_to_financials(text, tables, uploaded_file.name)
        else:
            st.error(f"Formato no soportado: {suffix}")
            return None
    except Exception as e:
        st.error(f"Error en la extracción: {e}")
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _facts_to_financials(data: dict[str, Any], file_name: str) -> FinancialStatements:
    """Convierte los facts extraídos a FinancialStatements (simplificado)."""
    from dcf_app.models.financials import (
        FinancialStatements,
    )

    # Por ahora, creamos un FinancialStatements vacío con el nombre de la empresa
    company = data.get("company_name") or file_name
    return FinancialStatements(
        company_name=company,
        income_statements=[],
        balance_sheets=[],
        cash_flow_statements=[],
    )


def _pdf_to_financials(
    text: str, tables: list[dict[str, Any]], file_name: str
) -> FinancialStatements:
    """Convierte datos extraídos de PDF a FinancialStatements (simplificado)."""
    from dcf_app.models.financials import (
        FinancialStatements,
    )

    company = file_name.replace(".pdf", "")
    return FinancialStatements(
        company_name=company,
        income_statements=[],
        balance_sheets=[],
        cash_flow_statements=[],
    )


def _fact_display(fact: Any) -> str:
    """Formatea un Fact para mostrar en la UI."""
    if fact is None or fact.value is None:
        return "—"
    val = fact.to_scale(Scale.MILLIONS)
    if val is None:
        return "—"
    return f"{val:,.2f} M"


def _render_validation_results(results: list[ValidationResult]) -> None:
    """Muestra los resultados de validación."""
    for r in results:
        if r.status == ValidationStatus.OK:
            st.success(f"✅ {r.name}: {r.message}")
        elif r.status == ValidationStatus.WARNING:
            st.warning(f"⚠️ {r.name}: {r.message}")
        else:
            st.error(f"❌ {r.name}: {r.message}")


def _render_assumptions_form() -> Assumptions | None:
    """Renderiza el formulario de supuestos y devuelve los valores."""
    st.subheader("Supuestos de valoración")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Proyección**")
        st.slider("Horizonte de proyección (años)", 3, 10, 5)
        initial_growth = (
            st.number_input("Crecimiento inicial de ingresos (%)", -5.0, 25.0, 10.0, 0.5) / 100
        )
        terminal_growth = st.number_input("Crecimiento terminal g (%)", 0.0, 5.0, 2.5, 0.1) / 100
        ebit_margin_target = st.number_input("Margen EBIT objetivo (%)", 0.0, 50.0, 25.0, 0.5) / 100

    with col2:
        st.markdown("**WACC**")
        risk_free = st.number_input("Tasa libre de riesgo Rf (%)", 0.0, 10.0, 4.0, 0.1) / 100
        beta = st.number_input("Beta del equity", 0.0, 3.0, 1.2, 0.1)
        erp = st.number_input("Prima de riesgo del mercado ERP (%)", 0.0, 15.0, 5.0, 0.5) / 100
        cost_of_debt = st.number_input("Coste de la deuda Kd (%)", 0.0, 15.0, 6.0, 0.5) / 100
        tax_rate = st.number_input("Tasa impositiva (%)", 0.0, 40.0, 21.0, 1.0) / 100

    st.markdown("**Datos de mercado**")
    col3, col4 = st.columns(2)
    with col3:
        market_cap = st.number_input("Capitalización de mercado (M USD)", 0.0, 1e6, 1000.0, 10.0)
        market_debt = st.number_input("Deuda a valor de mercado (M USD)", 0.0, 1e6, 200.0, 10.0)
    with col4:
        stock_price = st.number_input("Precio de la acción (USD)", 0.0, 1e4, 100.0, 1.0)
        shares = st.number_input("Acciones en circulación (M)", 0.0, 1e4, 100.0, 1.0)

    st.markdown("**Valor terminal**")
    terminal_method = st.selectbox(
        "Método de valor terminal",
        ["Gordon Growth", "Múltiplo de salida"],
    )
    exit_multiple = None
    if terminal_method == "Múltiplo de salida":
        exit_multiple = st.number_input("Múltiplo EV/EBITDA", 0.0, 50.0, 10.0, 0.5)

    st.markdown("**Convención de descuento**")
    convention = st.selectbox("Convención", ["Fin de año", "Mitad de año"])

    # Datos de la empresa (de los estados financieros si están disponibles)
    company_name = "Empresa"
    fiscal_year_end = "2024-12-31"
    if st.session_state.financials is not None:
        company_name = st.session_state.financials.company_name
        if st.session_state.financials.income_statements:
            fiscal_year_end = str(st.session_state.financials.income_statements[-1].period_end)

    try:
        assumptions = Assumptions(
            company_name=company_name,
            fiscal_year_end=fiscal_year_end,
            valuation_date=fiscal_year_end,
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
    st.dataframe(forecast_df, use_container_width=True)

    # Puente
    st.subheader("Puente EV → Equity")
    bridge_df = pd.DataFrame(
        list(result.bridge_breakdown.items()),
        columns=["Partida", "Valor (M USD)"],
    )
    st.dataframe(bridge_df, use_container_width=True)

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
        st.dataframe(sens_df, use_container_width=True)

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
        st.dataframe(sens_df, use_container_width=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Punto de entrada de la aplicación Streamlit."""
    st.title("📊 Valoración DCF desde Form 10-K")
    st.markdown(DISCLAIMER)

    tabs = st.tabs(["1. Subir 10-K", "2. Revisar datos", "3. Supuestos", "4. Resultados"])

    # --- Tab 1: Subir 10-K ---
    with tabs[0]:
        st.header("Subir archivo 10-K")
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

            # Mostrar estados financieros
            if financials.income_statements:
                st.subheader("Cuenta de resultados (último ejercicio)")
                last_income = financials.income_statements[-1]
                data = {
                    "Partida": [
                        "Revenue",
                        "COGS",
                        "Gross Profit",
                        "SG&A",
                        "R&D",
                        "D&A",
                        "EBIT",
                        "Interest",
                        "Pretax",
                        "Tax",
                        "Net Income",
                        "Diluted EPS",
                        "Diluted Shares",
                        "SBC",
                    ],
                    "Valor": [
                        _fact_display(last_income.revenue),
                        _fact_display(last_income.cogs),
                        _fact_display(last_income.gross_profit),
                        _fact_display(last_income.sga),
                        _fact_display(last_income.rd),
                        _fact_display(last_income.depreciation_amortization),
                        _fact_display(last_income.ebit),
                        _fact_display(last_income.interest_expense),
                        _fact_display(last_income.pretax_income),
                        _fact_display(last_income.income_tax_expense),
                        _fact_display(last_income.net_income),
                        _fact_display(last_income.diluted_eps),
                        _fact_display(last_income.diluted_weighted_shares),
                        _fact_display(last_income.sbc),
                    ],
                }
                import pandas as pd

                st.dataframe(pd.DataFrame(data), use_container_width=True)

            if financials.balance_sheets:
                st.subheader("Balance (último ejercicio)")
                last_balance = financials.balance_sheets[-1]
                data = {
                    "Partida": [
                        "Cash",
                        "ST Investments",
                        "AR",
                        "Inventory",
                        "AP",
                        "Accrued Liab",
                        "ST Debt",
                        "LT Debt",
                        "Leases (op. CP)",
                        "Leases (op. LP)",
                        "Preferred",
                        "NCI",
                        "Total Equity",
                        "Total Assets",
                        "Total Liabilities",
                    ],
                    "Valor": [
                        _fact_display(last_balance.cash_and_equivalents),
                        _fact_display(last_balance.short_term_investments),
                        _fact_display(last_balance.accounts_receivable),
                        _fact_display(last_balance.inventory),
                        _fact_display(last_balance.accounts_payable),
                        _fact_display(last_balance.accrued_liabilities),
                        _fact_display(last_balance.short_term_debt),
                        _fact_display(last_balance.long_term_debt),
                        _fact_display(last_balance.operating_lease_liabilities_current),
                        _fact_display(last_balance.operating_lease_liabilities_noncurrent),
                        _fact_display(last_balance.preferred_stock),
                        _fact_display(last_balance.non_controlling_interest),
                        _fact_display(last_balance.total_equity),
                        _fact_display(last_balance.total_assets),
                        _fact_display(last_balance.total_liabilities),
                    ],
                }
                st.dataframe(pd.DataFrame(data), use_container_width=True)

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
                    with st.spinner("Calculando DCF..."):
                        try:
                            result = run_dcf(assumptions, st.session_state.financials)
                            st.session_state.dcf_result = result
                            st.success("DCF calculado correctamente.")
                        except Exception as e:
                            st.error(f"Error en el DCF: {e}")

    # --- Tab 4: Resultados ---
    with tabs[3]:
        st.header("Resultados")
        if st.session_state.dcf_result is None:
            st.info("Ejecuta el DCF en la pestaña de Supuestos.")
        else:
            _render_results(st.session_state.dcf_result)

    # Disclaimer final
    st.markdown("---")
    st.markdown(DISCLAIMER)


if __name__ == "__main__":
    main()
