"""Formato de cifras para la UI en español (coma decimal, punto de millar).

Los porcentajes se guardan como fracciones (0.0825); solo aquí se convierten a texto.
"""
from __future__ import annotations


def _es(number_text: str) -> str:
    """Convierte '1,234.5' (inglés) en '1.234,5' (español)."""
    return number_text.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_pct(x: float | None, decimals: int = 1) -> str:
    if x is None:
        return "n/d"
    return _es(f"{x * 100:,.{decimals}f}") + " %"


def fmt_money(x: float | None, decimals: int = 1, unit: str = "MM USD") -> str:
    if x is None:
        return "n/d"
    sign = "−" if x < 0 else ""
    return f"{sign}{_es(f'{abs(x):,.{decimals}f}')} {unit}".strip()


def fmt_price(x: float | None) -> str:
    if x is None:
        return "n/d"
    return _es(f"{x:,.2f}") + " USD"


def pct_input_to_fraction(value_in_percent: float) -> float:
    """Los widgets muestran 9.0 (%) pero el modelo usa 0.09."""
    return value_in_percent / 100.0


if __name__ == "__main__":
    assert fmt_pct(0.0825, 2) == "8,25 %", fmt_pct(0.0825, 2)
    assert fmt_pct(0.749) == "74,9 %"
    assert fmt_pct(None) == "n/d"
    assert fmt_money(2713.835) == "2.713,8 MM USD", fmt_money(2713.835)
    assert fmt_money(-12.5) == "−12,5 MM USD"
    assert fmt_money(1234567.891, 0, "") == "1.234.568"
    assert fmt_price(24.6383) == "24,64 USD"
    assert pct_input_to_fraction(9.0) == 0.09
    print("formatting OK")
