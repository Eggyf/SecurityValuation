"""Localización de secciones del 10-K (fallback textual) (AGENTS.md §6).

Se usa cuando el tag iXBRL no existe o el archivo es PDF/texto plano.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup


def find_section(html_or_text: str, section_name: str) -> str | None:
    """Busca una sección del 10-K por su nombre.

    Args:
        html_or_text: contenido HTML o texto del 10-K.
        section_name: nombre de la sección a buscar (p. ej. "Item 7", "Item 8").

    Returns:
        Texto de la sección encontrada, o None si no se encuentra.
    """
    # Intentar como HTML primero
    try:
        soup = BeautifulSoup(html_or_text, "lxml")
        text = soup.get_text(separator="\n")
    except Exception:
        text = html_or_text

    # Buscar la sección con regex
    pattern = re.compile(
        rf"(?i){re.escape(section_name)}\b.*?(?=Item\s+\d+[A-Z]?\.?\s|$)",
        re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        return match.group(0).strip()
    return None


def find_income_statement_section(text: str) -> str | None:
    """Busca la sección de la cuenta de resultados."""
    return find_section(text, "CONSOLIDATED STATEMENTS OF INCOME")


def find_balance_sheet_section(text: str) -> str | None:
    """Busca la sección del balance."""
    return find_section(text, "CONSOLIDATED BALANCE SHEETS")


def find_cash_flow_section(text: str) -> str | None:
    """Busca la sección del flujo de caja."""
    return find_section(text, "CONSOLIDATED STATEMENTS OF CASH FLOWS")


def find_notes_section(text: str) -> str | None:
    """Busca la sección de notas."""
    return find_section(text, "NOTES TO FINANCIAL STATEMENTS")


__all__ = [
    "find_balance_sheet_section",
    "find_cash_flow_section",
    "find_income_statement_section",
    "find_notes_section",
    "find_section",
]
