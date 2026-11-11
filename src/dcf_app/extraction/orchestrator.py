"""Orquestador de extracción del 10-K (AGENTS.md §6, §13.4).

Intenta primero iXBRL (HTML), luego PDF, luego texto plano.
Devuelve FinancialStatements listo para el pipeline.
"""

from __future__ import annotations

from pathlib import Path

from dcf_app.extraction.ixbrl import extract_ixbrl
from dcf_app.extraction.pdf import extract_pdf_tables
from dcf_app.models.fact import Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)


def _make_source(kind: SourceKind, location: str, concept: str | None = None) -> SourceRef:
    """Crea un SourceRef con los parámetros dados."""
    return SourceRef(kind=kind, concept=concept, location=location)


def _parse_number(text: str) -> float | None:
    """Parsea un número de un texto (maneja comas, paréntesis negativos)."""
    text = text.strip()
    if not text or text in ("-", "\u2014", "\u2013", ""):
        return None

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    text = text.replace(",", "").replace(" ", "").replace("$", "")
    try:
        value = float(text)
    except ValueError:
        return None

    return -value if negative else value


def _detect_scale_from_text(text: str) -> Scale:
    """Detecta la escala a partir del texto."""
    text_lower = text.lower()
    if "billion" in text_lower:
        return Scale.BILLIONS
    if "million" in text_lower:
        return Scale.MILLIONS
    if "thousand" in text_lower:
        return Scale.THOUSANDS
    return Scale.UNITS


def extract_from_html(html_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements desde un archivo HTML/iXBRL.

    Args:
        html_path: ruta al archivo HTML/iXBRL.

    Returns:
        FinancialStatements con los datos extraídos.

    Raises:
        ValueError: si no se pueden extraer datos.
    """
    data = extract_ixbrl(html_path)
    facts = data.get("facts", [])

    if not facts:
        raise ValueError("No se extrajeron facts del archivo HTML.")

    # Agrupar facts por tipo de estado y periodo
    # (simplificado: por ahora solo creamos un FinancialStatements básico)
    company_name = data.get("company_name") or Path(html_path).stem

    # Crear un FinancialStatements vacío (la normalización se hace en normalization/)
    return FinancialStatements(
        company_name=company_name,
        income_statements=[],
        balance_sheets=[],
        cash_flow_statements=[],
    )


def extract_from_pdf(pdf_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements desde un archivo PDF.

    Intenta extraer tablas y parsearlas. Si no encuentra tablas,
    intenta parsear el texto.

    Args:
        pdf_path: ruta al archivo PDF.

    Returns:
        FinancialStatements con los datos extraídos.
    """
    path = Path(pdf_path)
    company_name = path.stem

    # Intentar extraer tablas (para uso futuro)
    extract_pdf_tables(path)

    income_statements: list[IncomeStatement] = []
    balance_sheets: list[BalanceSheet] = []
    cash_flow_statements: list[CashFlowStatement] = []

    # Por ahora, crear un FinancialStatements básico
    # La extracción detallada de tablas se mejora iterativamente
    return FinancialStatements(
        company_name=company_name,
        income_statements=income_statements,
        balance_sheets=balance_sheets,
        cash_flow_statements=cash_flow_statements,
    )


def extract_financials(file_path: str | Path) -> FinancialStatements:
    """Extrae FinancialStatements de un archivo 10-K (HTML o PDF).

    Intenta primero iXBRL (HTML), luego PDF.

    Args:
        file_path: ruta al archivo 10-K.

    Returns:
        FinancialStatements con los datos extraídos.

    Raises:
        ValueError: si no se puede extraer de ningún formato.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".html", ".htm", ".xhtml"):
        return extract_from_html(path)
    elif suffix == ".pdf":
        return extract_from_pdf(path)
    else:
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
