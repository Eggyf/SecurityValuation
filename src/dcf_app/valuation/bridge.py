"""Puente de Valor de Empresa (EV) a Valor del Equity y precio por acción (AGENTS.md §7.6).

Funciones puras: mismas entradas → mismas salidas; sin I/O, sin estado
global, sin aleatoriedad (AGENTS.md §8).
"""

from __future__ import annotations


def treasury_stock_diluted_shares(
    basic_shares: float,
    options_outstanding: float,
    rsus_outstanding: float,
    avg_exercise_price: float,
    current_price: float,
) -> float:
    """Acciones diluidas por el método de la acción de tesorería (AGENTS.md §7.6).

    Fórmula:
        Si current_price > avg_exercise_price (in the money):
            dilución_opciones = options x (1 - exercise_price / current_price)
        Si no:
            dilución_opciones = 0
        acciones_diluidas = basic_shares + dilución_opciones + rsus_outstanding

    Las opciones fuera de dinero (out of the money) no diluyen.

    Args:
        basic_shares: acciones básicas en circulación (millones).
        options_outstanding: opciones vivas (millones).
        rsus_outstanding: RSUs vivas (millones).
        avg_exercise_price: precio medio de ejercicio de las opciones (USD).
        current_price: precio actual de la acción (USD).

    Returns:
        Acciones diluidas (millones).

    Raises:
        ValueError: si ``current_price <= 0``.
    """
    if current_price <= 0:
        raise ValueError("El precio actual debe ser positivo.")

    # Opciones in the money: dilución neta por tesorería
    if avg_exercise_price < current_price and options_outstanding > 0:
        option_dilution = options_outstanding * (1.0 - avg_exercise_price / current_price)
    else:
        option_dilution = 0.0

    # RSUs siempre diluyen (no tienen precio de ejercicio)
    return basic_shares + option_dilution + rsus_outstanding


def bridge_to_equity(
    enterprise_value: float,
    cash_and_equivalents: float,
    short_term_investments: float = 0.0,
    financial_debt: float = 0.0,
    operating_leases: float = 0.0,
    preferred_stock: float = 0.0,
    non_controlling_interest: float = 0.0,
    other_adjustments: float = 0.0,
) -> float:
    """Puente de EV a Equity Value (AGENTS.md §7.6).

    Fórmula:
        Equity = EV + Caja + Inversiones CP
                - Deuda financiera - Leases operativos
                - Acciones preferentes - Intereses minoritarios
                ± otros ajustes

    Args:
        enterprise_value: valor de empresa (millones).
        cash_and_equivalents: caja y equivalentes (millones).
        short_term_investments: inversiones a corto plazo (millones).
        financial_debt: deuda financiera (millones).
        operating_leases: leases operativos tratados como deuda (millones).
        preferred_stock: acciones preferentes (millones).
        non_controlling_interest: intereses minoritarios (millones).
        other_adjustments: otros ajustes documentados (millones).

    Returns:
        Valor del equity (millones).
    """
    return (
        enterprise_value
        + cash_and_equivalents
        + short_term_investments
        - financial_debt
        - operating_leases
        - preferred_stock
        - non_controlling_interest
        + other_adjustments
    )


def price_per_share(
    equity_value: float,
    diluted_shares: float,
) -> float:
    """Precio por acción (AGENTS.md §7.6).

    Fórmula:
        Precio = Equity Value / Acciones diluidas

    Args:
        equity_value: valor del equity (millones).
        diluted_shares: acciones diluidas (millones).

    Returns:
        Precio por acción (USD).

    Raises:
        ValueError: si ``diluted_shares <= 0``.
    """
    if diluted_shares <= 0:
        raise ValueError("Las acciones diluidas deben ser positivas.")
    return equity_value / diluted_shares


def bridge_summary(
    enterprise_value: float,
    cash_and_equivalents: float,
    short_term_investments: float = 0.0,
    financial_debt: float = 0.0,
    operating_leases: float = 0.0,
    preferred_stock: float = 0.0,
    non_controlling_interest: float = 0.0,
    other_adjustments: float = 0.0,
) -> dict[str, float]:
    """Desglose del puente EV → Equity para mostrar en la UI (AGENTS.md §7.6).

    Returns:
        Diccionario con cada partida del puente y el equity value final.
    """
    equity = bridge_to_equity(
        enterprise_value=enterprise_value,
        cash_and_equivalents=cash_and_equivalents,
        short_term_investments=short_term_investments,
        financial_debt=financial_debt,
        operating_leases=operating_leases,
        preferred_stock=preferred_stock,
        non_controlling_interest=non_controlling_interest,
        other_adjustments=other_adjustments,
    )
    return {
        "enterprise_value": enterprise_value,
        "cash_and_equivalents": cash_and_equivalents,
        "short_term_investments": short_term_investments,
        "financial_debt": -financial_debt,
        "operating_leases": -operating_leases,
        "preferred_stock": -preferred_stock,
        "non_controlling_interest": -non_controlling_interest,
        "other_adjustments": other_adjustments,
        "equity_value": equity,
    }
