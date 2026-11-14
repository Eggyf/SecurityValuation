"""Sensibilidades del DCF (AGENTS.md §7.7).

Funciones puras: mismas entradas → mismas salidas; sin I/O, sin estado
global, sin aleatoriedad (AGENTS.md §8).
"""

from __future__ import annotations

from collections.abc import Callable

from dcf_app.models.assumptions import DiscountConvention, TerminalValueMethod
from dcf_app.valuation.bridge import (
    bridge_to_equity,
    price_per_share,
    treasury_stock_diluted_shares,
)
from dcf_app.valuation.forecast import build_forecast
from dcf_app.valuation.wacc import (
    discount_factor,
    present_value,
    terminal_value_gordon,
    terminal_value_multiple,
)


def _dcf_price(
    initial_revenue: float,
    growth_initial: float,
    growth_terminal: float,
    margin_current: float,
    margin_target: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    horizon: int,
    base_revenue: float | None,
    wacc: float,
    g: float,
    terminal_method: TerminalValueMethod,
    terminal_multiple: float | None,
    cash: float,
    short_term_investments: float,
    financial_debt: float,
    operating_leases: float,
    preferred_stock: float,
    non_controlling_interest: float,
    other_adjustments: float,
    basic_shares: float,
    options_outstanding: float,
    rsus_outstanding: float,
    avg_exercise_price: float,
    current_price: float,
    convention: DiscountConvention,
) -> float:
    """Calcula el precio por acción para un conjunto de parámetros (AGENTS.md §7).

    Esta función es el núcleo del DCF: proyecta flujos, calcula el valor
    terminal, descuenta y hace el puente EV → Equity → precio.

    Returns:
        Precio por acción (USD). Devuelve ``float('nan')`` si no es
        calculable (p. ej. WACC ≤ g).
    """
    try:
        # 1. Proyección de flujos
        forecast = build_forecast(
            initial_revenue=initial_revenue,
            growth_initial=growth_initial,
            growth_terminal=g,
            margin_current=margin_current,
            margin_target=margin_target,
            tax_rate=tax_rate,
            da_pct=da_pct,
            capex_pct=capex_pct,
            nwc_pct=nwc_pct,
            horizon=horizon,
            base_revenue=base_revenue,
        )

        # 2. Valor terminal
        if terminal_method == TerminalValueMethod.GORDON_GROWTH:
            # FCFF del año n+1 = FCFF_n x (1 + g)
            fcff_last = forecast.fcff[-1] if forecast.fcff else 0.0
            fcff_next = fcff_last * (1.0 + g)
            tv = terminal_value_gordon(fcff_next, wacc, g)
        else:
            # Múltiplo de salida: EBITDA_terminal x múltiplo
            # EBITDA ≈ EBIT + D&A
            ebit_last = forecast.ebit[-1] if forecast.ebit else 0.0
            da_last = forecast.da[-1] if forecast.da else 0.0
            ebitda_last = ebit_last + da_last
            mult = terminal_multiple if terminal_multiple is not None else 0.0
            tv = terminal_value_multiple(ebitda_last, mult)

        # 3. Valor presente de los FCFF
        pv_fcff = present_value(forecast.fcff, wacc, convention)

        # 4. Valor presente del valor terminal
        if forecast.fcff:
            tv_discount = discount_factor(wacc, len(forecast.fcff), convention)
        else:
            tv_discount = 1.0
        pv_tv = tv * tv_discount

        # 5. Enterprise Value
        ev = pv_fcff + pv_tv

        # 6. Puente EV → Equity
        equity = bridge_to_equity(
            enterprise_value=ev,
            cash_and_equivalents=cash,
            short_term_investments=short_term_investments,
            financial_debt=financial_debt,
            operating_leases=operating_leases,
            preferred_stock=preferred_stock,
            non_controlling_interest=non_controlling_interest,
            other_adjustments=other_adjustments,
        )

        # 7. Acciones diluidas
        diluted = treasury_stock_diluted_shares(
            basic_shares=basic_shares,
            options_outstanding=options_outstanding,
            rsus_outstanding=rsus_outstanding,
            avg_exercise_price=avg_exercise_price,
            current_price=current_price,
        )

        # 8. Precio por acción
        return price_per_share(equity, diluted)

    except (ValueError, ZeroDivisionError):
        return float("nan")


def sensitivity_2d(
    price_fn: Callable[[float, float], float],
    param1_values: list[float],
    param2_values: list[float],
) -> dict[tuple[float, float], float]:
    """Tabla de sensibilidad 2D genérica (AGENTS.md §7.7).

    Ejecuta ``price_fn(p1, p2)`` para cada combinación de ``param1_values``
    y ``param2_values``.

    Args:
        price_fn: función que calcula el precio por acción dados dos parámetros.
        param1_values: valores del primer parámetro (eje filas).
        param2_values: valores del segundo parámetro (eje columnas).

    Returns:
        Diccionario ``{(p1, p2): precio}``.
    """
    result: dict[tuple[float, float], float] = {}
    for p1 in param1_values:
        for p2 in param2_values:
            result[(p1, p2)] = price_fn(p1, p2)
    return result


def sensitivity_wacc_growth(
    # Parámetros de proyección (fijos)
    initial_revenue: float,
    margin_current: float,
    margin_target: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    horizon: int,
    base_revenue: float | None,
    # Puente (fijos)
    cash: float,
    short_term_investments: float,
    financial_debt: float,
    operating_leases: float,
    preferred_stock: float,
    non_controlling_interest: float,
    other_adjustments: float,
    basic_shares: float,
    options_outstanding: float,
    rsus_outstanding: float,
    avg_exercise_price: float,
    current_price: float,
    convention: DiscountConvention,
    terminal_method: TerminalValueMethod,
    terminal_multiple: float | None,
    # Rangos de sensibilidad
    wacc_values: list[float],
    growth_values: list[float],
    growth_initial_base: float | None = None,
) -> dict[tuple[float, float], float]:
    """Sensibilidad WACC x g → precio por acción (AGENTS.md §7.7).

    Todos los parámetros excepto wacc_values y growth_values son los
    valores fijos del DCF (proyección, puente, terminal, etc.).

    Returns:
        Diccionario con claves (wacc, g) y valores precio.
    """

    def price_fn(w: float, g_val: float) -> float:
        return _dcf_price(
            initial_revenue=initial_revenue,
            growth_initial=(
                growth_initial_base
                if growth_initial_base is not None
                else (growth_values[0] if growth_values else 0.05)
            ),
            growth_terminal=g_val,
            margin_current=margin_current,
            margin_target=margin_target,
            tax_rate=tax_rate,
            da_pct=da_pct,
            capex_pct=capex_pct,
            nwc_pct=nwc_pct,
            horizon=horizon,
            base_revenue=base_revenue,
            wacc=w,
            g=g_val,
            terminal_method=terminal_method,
            terminal_multiple=terminal_multiple,
            cash=cash,
            short_term_investments=short_term_investments,
            financial_debt=financial_debt,
            operating_leases=operating_leases,
            preferred_stock=preferred_stock,
            non_controlling_interest=non_controlling_interest,
            other_adjustments=other_adjustments,
            basic_shares=basic_shares,
            options_outstanding=options_outstanding,
            rsus_outstanding=rsus_outstanding,
            avg_exercise_price=avg_exercise_price,
            current_price=current_price,
            convention=convention,
        )

    return sensitivity_2d(price_fn, wacc_values, growth_values)


def sensitivity_margin_growth(
    # Parámetros de proyección (fijos excepto los que se varían)
    initial_revenue: float,
    margin_current: float,
    tax_rate: float,
    da_pct: float,
    capex_pct: float,
    nwc_pct: float,
    horizon: int,
    base_revenue: float | None,
    # WACC y terminal (fijos)
    wacc: float,
    g: float,
    terminal_method: TerminalValueMethod,
    terminal_multiple: float | None,
    # Puente (fijos)
    cash: float,
    short_term_investments: float,
    financial_debt: float,
    operating_leases: float,
    preferred_stock: float,
    non_controlling_interest: float,
    other_adjustments: float,
    basic_shares: float,
    options_outstanding: float,
    rsus_outstanding: float,
    avg_exercise_price: float,
    current_price: float,
    convention: DiscountConvention,
    # Rangos de sensibilidad
    margin_values: list[float],
    growth_values: list[float],
) -> dict[tuple[float, float], float]:
    """Sensibilidad margen EBIT objetivo x crecimiento inicial → precio (AGENTS.md §7.7).

    Todos los parámetros excepto margin_values y growth_values son los
    valores fijos del DCF (proyección, puente, terminal, etc.).

    Returns:
        Diccionario con claves (margen, crecimiento) y valores precio.
    """

    def price_fn(m: float, gr: float) -> float:
        return _dcf_price(
            initial_revenue=initial_revenue,
            growth_initial=gr,
            growth_terminal=g,
            margin_current=margin_current,
            margin_target=m,
            tax_rate=tax_rate,
            da_pct=da_pct,
            capex_pct=capex_pct,
            nwc_pct=nwc_pct,
            horizon=horizon,
            base_revenue=base_revenue,
            wacc=wacc,
            g=g,
            terminal_method=terminal_method,
            terminal_multiple=terminal_multiple,
            cash=cash,
            short_term_investments=short_term_investments,
            financial_debt=financial_debt,
            operating_leases=operating_leases,
            preferred_stock=preferred_stock,
            non_controlling_interest=non_controlling_interest,
            other_adjustments=other_adjustments,
            basic_shares=basic_shares,
            options_outstanding=options_outstanding,
            rsus_outstanding=rsus_outstanding,
            avg_exercise_price=avg_exercise_price,
            current_price=current_price,
            convention=convention,
        )

    return sensitivity_2d(price_fn, margin_values, growth_values)
