"""Extracción de datos financieros desde PDF (fallback) (AGENTS.md §6, §7).

Se usa cuando no hay archivo HTML/iXBRL disponible. La extracción es
menos precisa que iXBRL y se marca con ``source="text_fallback"`` y
menor confianza.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pymupdf

from dcf_app.extraction.mapping import map_concept
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef


def _parse_number(text: str) -> float | None:
    """Parsea un número de un texto (maneja comas, paréntesis negativos)."""
    text = text.strip()
    if not text or text == "-" or text == "\u2014" or text == "\u2013":
        return None

    # Paréntesis indican negativo
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]

    # Eliminar comas y espacios
    text = text.replace(",", "").replace(" ", "").replace("$", "")

    try:
        value = float(text)
    except ValueError:
        return None

    return -value if negative else value


def _detect_scale(text: str) -> Scale:
    """Detecta la escala a partir del texto (ej. '(In millions)')."""
    text_lower = text.lower()
    if "billion" in text_lower:
        return Scale.BILLIONS
    if "million" in text_lower:
        return Scale.MILLIONS
    if "thousand" in text_lower:
        return Scale.THOUSANDS
    return Scale.UNITS


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Extrae todo el texto de un PDF."""
    path = Path(pdf_path)
    doc = pymupdf.open(str(path))  # type: ignore
    text_parts = []
    for page in doc:  # type: ignore
        text_parts.append(page.get_text())
    doc.close()  # type: ignore
    return "\n".join(text_parts)


def extract_pdf_tables(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Extrae tablas de un PDF usando pymupdf.

    Returns:
        Lista de diccionarios con 'page', 'headers', 'rows'.
    """
    path = Path(pdf_path)
    doc = pymupdf.open(str(path))  # type: ignore
    tables = []

    for page_num, page in enumerate(doc):  # type: ignore
        tabs = page.find_tables()
        for tab in tabs.tables:
            extracted = tab.extract()
            if not extracted or len(extracted) < 2:
                continue
            headers = [str(h).strip() if h else "" for h in extracted[0]]
            rows = []
            for row in extracted[1:]:
                rows.append([str(c).strip() if c else "" for c in row])
            tables.append(
                {
                    "page": page_num,
                    "headers": headers,
                    "rows": rows,
                }
            )

    doc.close()  # type: ignore
    return tables


def parse_financial_table(
    table: dict[str, Any],
    statement_type: str,
    source_location: str,
) -> list[Fact]:
    """Parsea una tabla financiera extraída de PDF.

    Intenta mapear las filas a conceptos XBRL y crear Facts.
    """
    facts: list[Fact] = []
    headers = table["headers"]
    rows = table["rows"]

    # Detectar escala del encabezado
    scale = Scale.UNITS
    for h in headers:
        if "million" in h.lower():
            scale = Scale.MILLIONS
            break
        if "thousand" in h.lower():
            scale = Scale.THOUSANDS
            break
        if "billion" in h.lower():
            scale = Scale.BILLIONS
            break

    # Detectar columnas de años (números de 4 dígitos)
    year_cols: list[tuple[int, int]] = []
    for col_idx, h in enumerate(headers):
        year_match = re.search(r"(20\d{2})", h)
        if year_match:
            year_cols.append((col_idx, int(year_match.group(1))))

    if not year_cols:
        return facts

    for row in rows:
        if not row or not row[0]:
            continue

        concept_raw = row[0].strip()
        if not concept_raw:
            continue

        # Mapear concepto a campo normalizado
        field_name = map_concept(concept_raw, statement_type)

        if field_name is None:
            continue

        for col_idx, year in year_cols:
            if col_idx >= len(row):
                continue
            value = _parse_number(row[col_idx])
            if value is None:
                continue

            fact = Fact(
                value=value,
                unit="USD",
                scale=scale,
                period_start=None,
                period_end=__import__("datetime").date(year, 12, 31),
                source=SourceRef(
                    kind=SourceKind.TEXT_FALLBACK,
                    location=source_location,
                ),
            )
            facts.append(fact)

    return facts


__all__ = [
    "extract_pdf_tables",
    "extract_pdf_text",
    "parse_financial_table",
]
