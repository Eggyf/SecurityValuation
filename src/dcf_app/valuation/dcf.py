"""Orquestación del DCF: integra proyección, WACC, valor terminal, puente y sensibilidades.

Función principal: ``run_dcf(assumptions, financials) -> DCFResult``.
"""

from __future__ import annotations

import logging
from typing import Any

from dcf_app.models.assumptions import (
    Assumptions,
    DCFResult,
    TerminalValueMethod,
)
from dcf_app.models.fact import Fact, Scale
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.bridge import (
    bridge_to_equity,
    price_per_share,
    treasury_stock_diluted_shares,
)
from dcf_app.valuation.forecast import build_forecast
from dcf_app.valuation.sensitivity import sensitivity_margin_growth, sensitivity_wacc_growth
from dcf_app.valuation.wacc import (
    capm_ke,
    discount_factor,
    present_value,
    terminal_value_gordon,
    terminal_value_multiple,
    wacc,
)

logger = logging.getLogger(__name__)


def _extract_fact_value(fact: Fact | None, scale: Scale = Scale.MILLIONS) -> float:
    """Extrae el valor de un Fact en millones, o 0.0 si es None."""
    if fact is None or fact.value is None:
        return 0.0
    result = fact.to_scale(scale)
    return result if result is not None else 0.0


def _extract_latest_income(financials: FinancialStatements) -> IncomeStatement:
    """Extrae el último estado de resultados."""
    if not financials.income_statements:
        raise ValueError("Se requiere al menos un estado de resultados.")
    return financials.income_statements[-1]


def _extract_latest_balance(financials: FinancialStatements) -> BalanceSheet:
    """Extrae el último balance."""
    if not financials.balance_sheets:
        raise ValueError("Se requiere al menos un balance.")
    return financials.balance_sheets[-1]


def _extract_latest_cashflow(financials: FinancialStatements) -> CashFlowStatement:
    """Extrae el último estado de flujos de caja."""
    if not financials.cash_flow_statements:
        raise ValueError("Se requiere al menos un estado de flujos de caja.")
    return financials.cash_flow_statements[-1]


def _compute_historical_metrics(financials: FinancialStatements) -> dict[str, Any]:
    """Calcula métricas históricas de los estados financieros.

    Returns:
        Diccionario con: revenue, ebit_margin, da_pct, capex_pct, nwc_pct,
        cash, debt, leases, preferred, nci, short_term_investments, base_revenue.
    """
    income = _extract_latest_income(financials)
    balance = _extract_latest_balance(financials)
    cashflow = _extract_latest_cashflow(financials)

    # Revenue
    revenue = _extract_fact_value(income.revenue)
    if revenue == 0.0:
        raise ValueError("Los ingresos del último ejercicio son requeridos.")

    # EBIT margin
    ebit = _extract_fact_value(income.ebit)
    ebit_margin = ebit / revenue if revenue != 0 else 0.0

    # Interest expense
    interest_expense = _extract_fact_value(income.interest_expense)

    # D&A % (de cash flow o P&L)
    da_val = _extract_fact_value(cashflow.depreciation_amortization)
    if da_val == 0.0:
        da_val = _extract_fact_value(income.depreciation_amortization)
    da_pct = da_val / revenue if revenue != 0 else 0.0

    # CapEx %
    capex_val = _extract_fact_value(cashflow.capex)
    # CapEx suele ser negativo en el flujo de caja; tomamos valor absoluto
    capex_pct = abs(capex_val) / revenue if revenue != 0 else 0.0

    # NWC % (aproximación: (AR + Inventory - AP) / Revenue)
    ar = _extract_fact_value(balance.accounts_receivable)
    inv = _extract_fact_value(balance.inventory)
    ap = _extract_fact_value(balance.accounts_payable)
    nwc = ar + inv - ap
    nwc_pct = nwc / revenue if revenue != 0 else 0.0

    # Balance items
    cash = _extract_fact_value(balance.cash_and_equivalents)
    short_term_inv = _extract_fact_value(balance.short_term_investments)
    st_debt = _extract_fact_value(balance.short_term_debt)
    lt_debt = _extract_fact_value(balance.long_term_debt)
    debt = st_debt + lt_debt
    leases = (
        _extract_fact_value(balance.operating_lease_liabilities_current)
        + _extract_fact_value(balance.operating_lease_liabilities_noncurrent)
        + _extract_fact_value(balance.finance_lease_liabilities)
    )
    preferred = _extract_fact_value(balance.preferred_stock)
    nci = _extract_fact_value(balance.non_controlling_interest)

    # Patrimonio contable: proxy de los pesos del WACC si el usuario no
    # aporta el valor de mercado del equity (AGENTS.md §7.3).
    equity_value = _extract_fact_value(balance.total_equity)

    # Base revenue (año anterior para NWC)
    base_revenue: float | None = None
    if len(financials.income_statements) >= 2:
        prev_income = financials.income_statements[-2]
        base_revenue = _extract_fact_value(prev_income.revenue)
        if base_revenue == 0.0:
            base_revenue = None

    return {
        "revenue": revenue,
        "interest_expense": interest_expense,
        "ebit_margin": ebit_margin,
        "da_pct": da_pct,
        "capex_pct": capex_pct,
        "nwc_pct": nwc_pct,
        "cash": cash,
        "short_term_investments": short_term_inv,
        "debt": debt,
        "leases": leases,
        "preferred": preferred,
        "nci": nci,
        "equity_value": equity_value,
        "base_revenue": base_revenue,
    }


def _compute_wacc(assumptions: Assumptions, metrics: dict[str, float]) -> float:
    """Calcula el WACC a partir de los supuestos y métricas."""
    # Rf
    rf = assumptions.risk_free_rate
    if rf is None:
        raise ValueError("La tasa libre de riesgo (Rf) es requerida para el WACC.")

    # Beta
    beta = assumptions.equity_beta
    if beta is None:
        raise ValueError("El beta del equity es requerido para el WACC.")

    # ERP (prima de riesgo): input del usuario (AGENTS.md §7.3), no se
    # inventa; en v2 podrá precargarse de Damodaran (§13.2).
    erp = assumptions.equity_risk_premium
    if erp is None:
        raise ValueError("La prima de riesgo del mercado (ERP) es requerida para el WACC.")

    # Ke por CAPM
    ke = capm_ke(rf, beta, erp)

    # Kd
    kd = assumptions.cost_of_debt
    if kd is None:
        # Intentar calcular a partir de intereses/deuda
        interest = abs(metrics.get("interest_expense", 0.0))
        debt = metrics["debt"]
        if debt > 0 and interest > 0:
            kd = interest / debt
        else:
            raise ValueError(
                "El coste de la deuda (Kd) es requerido para el WACC. "
                "Proporcióñelo en los supuestos o aporte los intereses."
            )

    # Tax rate
    tax_rate = assumptions.tax_rate
    if tax_rate is None:
        raise ValueError("La tasa impositiva es requerida para el WACC.")

    # Pesos de mercado
    equity_value = assumptions.market_equity_value
    debt_value = assumptions.market_debt_value

    if equity_value is None or debt_value is None:
        # Usar valores contables como proxy (AGENTS.md §7.3)
        equity_value = metrics["equity_value"]
        debt_value = metrics["debt"]
        if equity_value == 0.0 and debt_value == 0.0:
            raise ValueError(
                "Se requiere el valor de mercado del equity y/o de la deuda "
                "para calcular los pesos del WACC."
            )

    return wacc(equity_value, debt_value, ke, kd, tax_rate)


def run_dcf(
    assumptions: Assumptions,
    financials: FinancialStatements,
) -> DCFResult:
    """Ejecuta el DCF completo (AGENTS.md §7).

    Args:
        assumptions: supuestos de valoración.
        financials: estados financieros extraídos del 10-K.

    Returns:
        :class:`DCFResult` con la proyección, valor terminal, puente y
        sensibilidades.

    Raises:
        ValueError: si faltan datos requeridos.
    """
    # 1. Extraer métricas históricas
    metrics = _compute_historical_metrics(financials)

    # 2. Calcular WACC
    wacc_val = _compute_wacc(assumptions, metrics)

    # 3. Parámetros de proyección
    initial_revenue = metrics["revenue"]
    growth_initial = assumptions.initial_revenue_growth
    if growth_initial is None:
        # Calcular CAGR de 3 años si hay datos suficientes
        if len(financials.income_statements) >= 2:
            revs = [_extract_fact_value(s.revenue) for s in financials.income_statements]
            if len(revs) >= 2 and revs[0] > 0:
                growth_initial = (revs[-1] / revs[0]) ** (1.0 / (len(revs) - 1)) - 1.0
                # Acotar a [-5%, 25%]
                growth_initial = max(-0.05, min(0.25, growth_initial))
            else:
                growth_initial = 0.05  # default
        else:
            growth_initial = 0.05  # default

    growth_terminal = assumptions.terminal_revenue_growth
    if growth_terminal is None:
        growth_terminal = 0.025  # default 2.5%

    margin_current = metrics["ebit_margin"]
    margin_target = assumptions.ebit_margin_target
    if margin_target is None:
        margin_target = margin_current  # default: mantener margen actual

    tax_rate = assumptions.tax_rate
    if tax_rate is None:
        raise ValueError("La tasa impositiva es requerida.")

    da_pct = metrics["da_pct"]
    capex_pct = metrics["capex_pct"]
    nwc_pct = metrics["nwc_pct"]
    horizon = assumptions.forecast_horizon
    base_revenue = metrics["base_revenue"]

    # 4. Construir proyección
    forecast = build_forecast(
        initial_revenue=initial_revenue,
        growth_initial=growth_initial,
        growth_terminal=growth_terminal,
        margin_current=margin_current,
        margin_target=margin_target,
        tax_rate=tax_rate,
        da_pct=da_pct,
        capex_pct=capex_pct,
        nwc_pct=nwc_pct,
        horizon=horizon,
        base_revenue=base_revenue,
    )

    # 5. Valor terminal
    terminal_method = assumptions.terminal_value_method
    g = growth_terminal

    # Validar WACC > g
    if wacc_val <= g:
        raise ValueError(
            f"WACC ({wacc_val:.4f}) debe ser mayor que g ({g:.4f}). "
            "Ajuste los supuestos."
        )

    # ROIC terminal (por defecto = WACC, sin exceso de rentabilidad)
    roic_terminal = assumptions.roic_terminal
    if roic_terminal is None:
        roic_terminal = wacc_val  # conservador: sin exceso de rentabilidad

    # Reinvestment rate = g / ROIC_terminal
    reinvestment_rate = g / roic_terminal if roic_terminal > 0 else 0.0
    reinvestment_rate = min(reinvestment_rate, 1.0)  # cap at 100%

    if terminal_method == TerminalValueMethod.GORDON_GROWTH:
        # FCFF terminal normalizado (AGENTS.md §7.4)
        nopat_last = forecast.nopat[-1] if forecast.nopat else 0.0
        nopat_next = nopat_last * (1.0 + g)
        fcff_next = nopat_next * (1.0 - reinvestment_rate)
        tv = terminal_value_gordon(fcff_next, wacc_val, g)
    else:
        ebit_last = forecast.ebit[-1] if forecast.ebit else 0.0
        da_last = forecast.da[-1] if forecast.da else 0.0
        ebitda_last = ebit_last + da_last
        mult = assumptions.exit_multiple_ebitda
        if mult is None:
            raise ValueError("Se requiere el múltiplo de salida para el método de múltiplo.")
        tv = terminal_value_multiple(ebitda_last, mult)

    # Verificar CapEx >= D&A en el año terminal
    if forecast.capex and forecast.da:
        capex_terminal = forecast.capex[-1]
        da_terminal = forecast.da[-1]
        if abs(capex_terminal) < abs(da_terminal):
            logger.warning(
                "CapEx terminal (%.0f) < D&A (%.0f): reinversión incoherente con g.",
                capex_terminal,
                da_terminal,
            )

    # 6. Valor presente de FCFF y TV
    pv_fcff = present_value(forecast.fcff, wacc_val, assumptions.discount_convention)
    if forecast.fcff:
        tv_discount = discount_factor(wacc_val, len(forecast.fcff), assumptions.discount_convention)
    else:
        tv_discount = 1.0
    pv_tv = tv * tv_discount

    # 7. Enterprise Value
    ev = pv_fcff + pv_tv

    # 8. Puente EV → Equity
    equity = bridge_to_equity(
        enterprise_value=ev,
        cash_and_equivalents=metrics["cash"],
        short_term_investments=metrics["short_term_investments"],
        financial_debt=metrics["debt"],
        operating_leases=metrics["leases"],
        preferred_stock=metrics["preferred"],
        non_controlling_interest=metrics["nci"],
    )

    # 9. Acciones diluidas
    # Acciones básicas: preferir las de la portada del 10-K (dei:EntityCommonStockSharesOutstanding)
    # sobre el input manual. Si no hay, usar el input del usuario.
    basic_shares = None
    bs_fact = financials.notes.basic_shares_outstanding
    if bs_fact is not None and bs_fact.value is not None:
        bs_val = bs_fact.to_scale(Scale.MILLIONS)
        if bs_val is not None and bs_val > 0:
            basic_shares = bs_val
    if basic_shares is None:
        basic_shares = assumptions.shares_outstanding
    if basic_shares is None:
        raise ValueError("Las acciones en circulación son requeridas.")

    current_price = assumptions.stock_price_current
    if current_price is None:
        raise ValueError("El precio actual de la acción es requerido.")

    options = assumptions.options_outstanding or 0.0
    rsus = assumptions.rsus_outstanding or 0.0
    avg_exercise = assumptions.average_option_exercise_price or 0.0

    diluted = treasury_stock_diluted_shares(
        basic_shares=basic_shares,
        options_outstanding=options,
        rsus_outstanding=rsus,
        avg_exercise_price=avg_exercise,
        current_price=current_price,
    )

    # 10. Precio por acción
    price = price_per_share(equity, diluted)

    # 11. Upside/downside
    upside = (price / current_price - 1.0) * 100.0 if current_price > 0 else None

    # 12. TV como % del EV
    tv_pct = pv_tv / ev if ev != 0 else 0.0

    # 13. Sensibilidades
    wacc_range = [wacc_val - 0.02, wacc_val - 0.01, wacc_val, wacc_val + 0.01, wacc_val + 0.02]
    growth_range = [g - 0.01, g, g + 0.01]

    sens_wacc_growth = sensitivity_wacc_growth(
        initial_revenue=initial_revenue,
        margin_current=margin_current,
        margin_target=margin_target,
        tax_rate=tax_rate,
        da_pct=da_pct,
        capex_pct=capex_pct,
        nwc_pct=nwc_pct,
        horizon=horizon,
        base_revenue=base_revenue,
        cash=metrics["cash"],
        short_term_investments=metrics["short_term_investments"],
        financial_debt=metrics["debt"],
        operating_leases=metrics["leases"],
        preferred_stock=metrics["preferred"],
        non_controlling_interest=metrics["nci"],
        other_adjustments=0.0,
        basic_shares=basic_shares,
        options_outstanding=options,
        rsus_outstanding=rsus,
        avg_exercise_price=avg_exercise,
        current_price=current_price,
        convention=assumptions.discount_convention,
        terminal_method=terminal_method,
        terminal_multiple=assumptions.exit_multiple_ebitda,
        wacc_values=wacc_range,
        growth_values=growth_range,
        growth_initial_base=growth_initial,
    )

    margin_range = [margin_target - 0.05, margin_target, margin_target + 0.05]
    growth_init_range = [growth_initial - 0.05, growth_initial, growth_initial + 0.05]

    sens_margin_growth = sensitivity_margin_growth(
        initial_revenue=initial_revenue,
        margin_current=margin_current,
        tax_rate=tax_rate,
        da_pct=da_pct,
        capex_pct=capex_pct,
        nwc_pct=nwc_pct,
        horizon=horizon,
        base_revenue=base_revenue,
        wacc=wacc_val,
        g=g,
        terminal_method=terminal_method,
        terminal_multiple=assumptions.exit_multiple_ebitda,
        cash=metrics["cash"],
        short_term_investments=metrics["short_term_investments"],
        financial_debt=metrics["debt"],
        operating_leases=metrics["leases"],
        preferred_stock=metrics["preferred"],
        non_controlling_interest=metrics["nci"],
        other_adjustments=0.0,
        basic_shares=basic_shares,
        options_outstanding=options,
        rsus_outstanding=rsus,
        avg_exercise_price=avg_exercise,
        current_price=current_price,
        convention=assumptions.discount_convention,
        margin_values=margin_range,
        growth_values=growth_init_range,
    )

    # 14. Desglose del puente
    bridge_breakdown = {
        "enterprise_value": ev,
        "cash_and_equivalents": metrics["cash"],
        "short_term_investments": metrics["short_term_investments"],
        "financial_debt": -metrics["debt"],
        "operating_leases": -metrics["leases"],
        "preferred_stock": -metrics["preferred"],
        "non_controlling_interest": -metrics["nci"],
        "equity_value": equity,
    }

    # 15. Construir DCFResult
    return DCFResult(
        assumptions=assumptions,
        forecast_years=list(
            range(
                financials.income_statements[-1].fiscal_year + 1,
                financials.income_statements[-1].fiscal_year + 1 + horizon,
            )
        ),
        revenue_forecast=forecast.revenue,
        ebit_forecast=forecast.ebit,
        nopat_forecast=forecast.nopat,
        fcff_forecast=forecast.fcff,
        capex_forecast=forecast.capex,
        delta_nwc_forecast=forecast.delta_nwc,
        terminal_value=tv,
        terminal_value_method=terminal_method,
        terminal_value_multiple=assumptions.exit_multiple_ebitda,
        enterprise_value=ev,
        equity_value=equity,
        price_per_share=price,
        upside_downside=upside,
        bridge_breakdown=bridge_breakdown,
        sensitivity_wacc_growth=sens_wacc_growth,
        sensitivity_margin_growth=sens_margin_growth,
        tv_percentage=tv_pct,
        reinvestment_rate=reinvestment_rate,
    )
