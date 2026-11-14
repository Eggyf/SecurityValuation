"""Orquestador de extracción del 10-K (AGENTS.md §6, §13.4).

Punto de entrada del pipeline de extracción:

- HTML/iXBRL → :func:`extract_ixbrl` + :func:`build_financial_statements`
  (vía preferida, tags ``ix:nonFraction``).
- PDF → :func:`extract_statements_from_pdf` (fallback por etiquetas,
  marcado ``text_fallback``).

Ambos caminos devuelven :class:`~dcf_app.models.financials.FinancialStatements`
con trazabilidad por cifra (AGENTS.md §2.3). Si falta alguno de los tres
estados, se devuelve un objeto con listas vacías y
:func:`validate_extraction` lo comunica (degradación segura, §2.8).
"""

from __future__ import annotations

import logging
from pathlib import Path

from dcf_app.extraction.ixbrl import extract_ixbrl
from dcf_app.extraction.pdf_statements import extract_statements_from_pdf
from dcf_app.extraction.statements import build_financial_statements
from dcf_app.models.financials import FinancialStatements
from dcf_app.models.notes import SupplementaryNotes

logger = logging.getLogger(__name__)

_HTML_SUFFIXES = {".html", ".htm", ".xhtml"}


def extract_from_html(html_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements desde un archivo HTML/iXBRL (vía preferida).

    Args:
        html_path: ruta al archivo HTML/iXBRL.

    Returns:
        FinancialStatements construido a partir de los facts iXBRL no
        dimensionales. Si no se pueden construir los tres estados, devuelve
        listas vacías (lo reporta :func:`validate_extraction`).
    """
    path = Path(html_path)
    data = extract_ixbrl(path)
    facts = data["facts"]

    company_name = data.get("company_name") or path.stem
    currency = data.get("currency") or "USD"
    basic_shares = data.get("basic_shares")

    if basic_shares is not None:
        notes = SupplementaryNotes(basic_shares_outstanding=basic_shares)
    else:
        notes = SupplementaryNotes()

    if not facts:
        logger.warning("iXBRL: no se extrajo ningun fact de %s", path.name)
        return FinancialStatements(
            company_name=company_name, reporting_currency=currency, notes=notes
        )

    return build_financial_statements(facts, company_name, currency, basic_shares=basic_shares)


def extract_from_pdf(pdf_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements desde un archivo PDF (fallback).

    Args:
        pdf_path: ruta al archivo PDF.

    Returns:
        FinancialStatements con las partidas localizadas (el resto queda en
        ``None``), marcadas como ``text_fallback``. Si falta algún estado,
        devuelve listas vacías.
    """
    return extract_statements_from_pdf(pdf_path)


def extract_financials(file_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements de un archivo 10-K (HTML o PDF).

    Args:
        file_path: ruta al archivo 10-K.

    Returns:
        FinancialStatements con los datos extraídos.

    Raises:
        ValueError: si el formato no está soportado.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in _HTML_SUFFIXES:
        return extract_from_html(path)
    if suffix == ".pdf":
        return extract_from_pdf(path)
    raise ValueError(f"Formato no soportado: {suffix}")


def validate_extraction(financials: FinancialStatements) -> list[str]:
    """Valida que la extracción haya producido datos útiles.

    Returns:
        Lista de advertencias (vacía si todo está bien).
    """
    warnings: list[str] = []

    if not financials.income_statements:
        warnings.append("No se extrajeron estados de resultados.")
    if not financials.balance_sheets:
        warnings.append("No se extrajeron balances.")
    if not financials.cash_flow_statements:
        warnings.append("No se extrajeron flujos de caja.")

    if financials.income_statements:
        last = financials.income_statements[-1]
        if last.revenue is None or last.revenue.value is None:
            warnings.append("No se encontró Revenue en el estado de resultados.")

    return warnings


__all__ = [
    "extract_financials",
    "extract_from_html",
    "extract_from_pdf",
    "validate_extraction",
]
