"""Extracción de datos financieros desde iXBRL (AGENTS.md §6).

Prioriza los tags ``ix:nonFraction`` sobre texto libre. Devuelve datos
estructurados con trazabilidad completa (concepto XBRL, periodo, escala).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from dcf_app.extraction.mapping import is_company_extension, map_concept
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef

# ---------------------------------------------------------------------------
# Escala iXBRL: atributo 'scale' → Scale
# ---------------------------------------------------------------------------
_SCALE_MAP: dict[str, Scale] = {
    "0": Scale.UNITS,
    "3": Scale.THOUSANDS,
    "6": Scale.MILLIONS,
    "9": Scale.BILLIONS,
}


def _parse_scale(scale_attr: str | None) -> Scale:
    """Convierte el atributo 'scale' de iXBRL a Scale."""
    if scale_attr is None:
        return Scale.UNITS
    return _SCALE_MAP.get(scale_attr.strip(), Scale.UNITS)


def _parse_period(context_ref: str, contexts: dict[str, Any]) -> tuple[date | None, date]:
    """Extrae period_start y period_end de un contexto XBRL."""
    ctx = contexts.get(context_ref, {})
    period = ctx.get("period", {})

    # Instant (balance)
    if "instant" in period:
        instant = _parse_date(period["instant"])
        return None, instant

    # Duration (P&L, flujo de caja)
    start = _parse_date(period.get("startDate")) if period.get("startDate") else None
    end = _parse_date(period.get("endDate")) if period.get("endDate") else None
    if end is None:
        raise ValueError(f"No se pudo parsear el periodo del contexto {context_ref}")
    return start, end


def _parse_date(date_str: str) -> date:
    """Parsea una fecha ISO (YYYY-MM-DD)."""
    return date.fromisoformat(date_str)


def _parse_value(text: str, scale: Scale, sign: str | None) -> float | None:
    """Parsea el valor numérico de un tag ix:nonFraction."""
    # Limpiar el texto: quitar comas, espacios, etc.
    cleaned = text.strip().replace(",", "").replace(" ", "")
    if not cleaned or cleaned == "-":
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None

    # Aplicar signo (atributo 'sign' de iXBRL)
    if sign == "-":
        value = -value

    return value


def _extract_contexts(soup: BeautifulSoup) -> dict[str, Any]:
    """Extrae los contextos XBRL del documento."""
    contexts: dict[str, Any] = {}
    for ctx in soup.find_all("xbrli:context"):
        ctx_id = ctx.get("id")
        if not ctx_id:
            continue

        period: dict[str, str] = {}
        period_elem = ctx.find("xbrli:period")
        if period_elem:
            instant = period_elem.find("xbrli:instant")
            if instant:
                period["instant"] = instant.get_text(strip=True)
            start = period_elem.find("xbrli:startdate")
            if start:
                period["startDate"] = start.get_text(strip=True)
            end = period_elem.find("xbrli:enddate")
            if end:
                period["endDate"] = end.get_text(strip=True)

        contexts[ctx_id] = {"period": period}
    return contexts


def extract_ixbrl(html_path: str | Path) -> dict[str, Any]:
    """Extrae datos financieros de un archivo HTML/iXBRL.

    Args:
        html_path: ruta al archivo HTML/iXBRL.

    Returns:
        Diccionario con:
        - "facts": lista de Fact extraídos
        - "contexts": contextos XBRL
        - "company_name": nombre de la empresa (si se encuentra)
        - "currency": moneda de reporte
    """
    path = Path(html_path)
    with path.open(encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    contexts = _extract_contexts(soup)

    facts: list[Fact] = []
    seen: set[tuple[str, str | None, str]] = set()

    for tag in soup.find_all("ix:nonfraction"):
        concept = tag.get("name", "")
        if not concept:
            continue

        context_ref = tag.get("contextref", "")
        scale_attr = tag.get("scale")
        sign_attr = tag.get("sign")
        unit_ref = tag.get("unitref", "")

        scale = _parse_scale(scale_attr)
        period_start, period_end = _parse_period(context_ref, contexts)

        value = _parse_value(tag.get_text(), scale, sign_attr)
        if value is None:
            continue

        # Determinar tipo de estado
        statement_type = _infer_statement_type(concept, context_ref, contexts)

        # Mapear concepto a campo normalizado (se usa en el pipeline de normalización)
        map_concept(concept, statement_type)

        # Determinar si es extensión de la empresa
        kind = SourceKind.IXBRL_EXTENSION if is_company_extension(concept) else SourceKind.IXBRL

        source = SourceRef(
            kind=kind,
            concept=concept,
            location=f"iXBRL tag: {concept}",
        )

        # Determinar unidad
        unit = _infer_unit(concept, unit_ref)

        fact = Fact(
            value=value,
            unit=unit,
            scale=scale,
            period_start=period_start,
            period_end=period_end,
            source=source,
        )

        # Evitar duplicados (mismo concepto + periodo + escala)
        key = (concept, context_ref, str(value))
        if key in seen:
            continue
        seen.add(key)

        facts.append(fact)

    # Extraer nombre de la empresa
    company_name = _extract_company_name(soup)

    # Extraer moneda
    currency = _extract_currency(soup, contexts)

    return {
        "facts": facts,
        "contexts": contexts,
        "company_name": company_name,
        "currency": currency,
    }


def _infer_statement_type(concept: str, context_ref: str, contexts: dict[str, Any]) -> str:
    """Infiere el tipo de estado financiero a partir del concepto y contexto."""
    concept_lower = concept.lower()

    # Balance: conceptos de activos/pasivos/patrimonio
    balance_keywords = [
        "assets",
        "liabilities",
        "equity",
        "cash",
        "receivable",
        "inventory",
        "payable",
        "debt",
        "lease",
        "preferred",
        "stockholder",
    ]
    # P&L: conceptos de ingresos/gastos
    income_keywords = [
        "revenue",
        "income",
        "expense",
        "cost",
        "profit",
        "margin",
        "earnings",
        "eps",
        "tax",
        "interest",
    ]
    # Flujo de caja
    cashflow_keywords = [
        "cashflow",
        "cashprovided",
        "cashused",
        "capitalexpenditure",
        "depreciation",
        "amortization",
    ]

    for kw in cashflow_keywords:
        if kw in concept_lower:
            # Verificar si es de periodo (duration) → flujo de caja
            ctx = contexts.get(context_ref, {})
            period = ctx.get("period", {})
            if "startDate" in period:
                return "cashflow"

    for kw in balance_keywords:
        if kw in concept_lower:
            ctx = contexts.get(context_ref, {})
            period = ctx.get("period", {})
            if "instant" in period:
                return "balance"

    for kw in income_keywords:
        if kw in concept_lower:
            return "income"

    return "income"  # default


def _infer_unit(concept: str, unit_ref: str) -> str:
    """Infiere la unidad a partir del concepto y la referencia de unidad."""
    concept_lower = concept.lower()
    if "pershare" in concept_lower or "earningspershare" in concept_lower:
        return "USD_per_share"
    if "shares" in concept_lower or "numberofshares" in concept_lower:
        return "shares"
    if "rate" in concept_lower or "margin" in concept_lower or "ratio" in concept_lower:
        return "ratio"
    return "USD"


def _extract_company_name(soup: BeautifulSoup) -> str | None:
    """Extrae el nombre de la empresa del documento."""
    # Buscar en tags dei:EntityRegistrantName
    for tag in soup.find_all("dei:entityregistrantname"):
        text = tag.get_text(strip=True)
        if text:
            return str(text)
    # Buscar en el título
    title = soup.find("title")
    if title:
        text = title.get_text(strip=True)
        if text and len(str(text)) < 100:
            return str(text)
    return None


def _extract_currency(soup: BeautifulSoup, contexts: dict[str, Any]) -> str:
    """Extrae la moneda de reporte."""
    for unit in soup.find_all("xbrli:unit"):
        measure = unit.find("xbrli:measure")
        if measure:
            text = measure.get_text(strip=True)
            if text.startswith("iso4217:"):
                return str(text).replace("iso4217:", "")
    return "USD"


__all__ = [
    "extract_ixbrl",
]
