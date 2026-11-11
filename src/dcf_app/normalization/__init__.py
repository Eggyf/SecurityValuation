"""Normalización de magnitudes: signos, escala, partidas no recurrentes y leases (AGENTS.md §6, §7).

Funciones puras que transforman datos extraídos en datos listos para el DCF.
"""

from __future__ import annotations

from dcf_app.models.fact import Fact, Scale


def normalize_sign(value: float, concept: str) -> float:
    """Normaliza el signo de una partida según su concepto.

    Algunas partidas del flujo de caja aparecen como negativas en el 10-K
    (p. ej. CapEx) pero deben ser positivas para el cálculo del FCFF.
    """
    concept_lower = concept.lower()
    # CapEx suele aparecer como pago negativo en el flujo de caja
    if (
        "capex" in concept_lower
        or "capital_expenditure" in concept_lower
        or "payments_to_acquire" in concept_lower
    ):
        return abs(value)
    # D&A y SBC son adiciones (positivas)
    if "depreciation" in concept_lower or "amortization" in concept_lower:
        return abs(value)
    return value


def normalize_scale(fact: Fact, target: Scale = Scale.MILLIONS) -> float | None:
    """Normaliza un Fact a la escala objetivo (AGENTS.md §2.6)."""
    return fact.to_scale(target)


def normalize_capex_sign(value: float) -> float:
    """CapEx siempre positivo para el cálculo del FCFF."""
    return abs(value)


def adjust_for_non_recurring(ebit: float, non_recurring_items: list[float]) -> float:
    """Ajusta el EBIT excluyendo partidas no recurrentes (AGENTS.md §7.1).

    Args:
        ebit: EBIT reportado (millones).
        non_recurring_items: lista de partidas no recurrentes (positivas = gasto).

    Returns:
        EBIT ajustado (millones).
    """
    total_adjustment = sum(non_recurring_items)
    return ebit - total_adjustment


def normalize_leases(
    operating_leases_current: float,
    operating_leases_noncurrent: float,
    finance_leases: float = 0.0,
) -> float:
    """Consolida los leases operativos y financieros (AGENTS.md §7.3).

    Args:
        operating_leases_current: leases operativos corrientes.
        operating_leases_noncurrent: leases operativos no corrientes.
        finance_leases: leases financieros.

    Returns:
        Total de leases tratados como deuda (millones).
    """
    return operating_leases_current + operating_leases_noncurrent + finance_leases


__all__ = [
    "adjust_for_non_recurring",
    "normalize_capex_sign",
    "normalize_leases",
    "normalize_scale",
    "normalize_sign",
]
