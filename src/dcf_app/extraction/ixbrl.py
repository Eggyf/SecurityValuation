"""Extraccion de datos financieros desde iXBRL (AGENTS.md §6).

Prioriza los tags ``ix:nonFraction`` sobre texto libre. Devuelve datos
estructurados con trazabilidad completa (concepto XBRL, periodo, escala).

Decisiones de diseno (docs/methodology.md):
- Los facts cuyo contexto tiene segmento/escenario (dimensiones XBRL:
  desgloses por producto, region, etc.) se descartan: no son valores de
  la empresa consolidada.
- Solo se aceptan facts con periodo resoluble; el resto se ignoran en
  lugar de romper la extraccion completa.
"""

from __future__ import annotations

import logging
import warnings
from datetime import date
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from dcf_app.extraction.mapping import is_company_extension
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef

# Suprimir warning de parseo XML como HTML (no afecta la extracción)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Escala iXBRL: atributo 'scale' → Scale
# ---------------------------------------------------------------------------
_SCALE_MAP: dict[str, Scale] = {
    "0": Scale.UNITS,
    "3": Scale.THOUSANDS,
    "6": Scale.MILLIONS,
    "9": Scale.BILLIONS,
}

_PERIOD_TAGS = ["xbrli:period", "period"]
_INSTANT_TAGS = ["xbrli:instant", "instant"]
_START_TAGS = ["xbrli:startdate", "startdate"]
_END_TAGS = ["xbrli:enddate", "enddate"]
_CONTEXT_TAGS = ["xbrli:context", "context"]
_SEGMENT_TAGS = ["xbrli:segment", "segment", "xbrli:scenario", "scenario"]


def _parse_scale(scale_attr: str | None) -> Scale:
    """Convierte el atributo 'scale' de iXBRL a Scale."""
    if scale_attr is None:
        return Scale.UNITS
    return _SCALE_MAP.get(str(scale_attr).strip(), Scale.UNITS)


def _find_child(parent: Tag, names: list[str]) -> Tag | None:
    """Busca el primer hijo con alguno de los nombres dados."""
    for name in names:
        child = parent.find(name)
        if isinstance(child, Tag):
            return child
    return None


def _parse_date(date_str: str) -> date | None:
    """Parsea una fecha ISO (YYYY-MM-DD); devuelve None si es invalida."""
    try:
        return date.fromisoformat(date_str.strip())
    except ValueError:
        return None


def _parse_period(context_ref: str, contexts: dict[str, Any]) -> tuple[date | None, date | None]:
    """Extrae (period_start, period_end) de un contexto XBRL.

    Devuelve (None, None) si el contexto no se puede resolver: el fact se
    descarta en lugar de romper la extraccion.
    """
    ctx = contexts.get(context_ref)
    if ctx is None:
        return None, None

    period = ctx.get("period", {})
    if "instant" in period:
        instant = _parse_date(period["instant"])
        return None, instant

    start = _parse_date(period["startDate"]) if period.get("startDate") else None
    end = _parse_date(period["endDate"]) if period.get("endDate") else None
    if end is None or (start is not None and start >= end):
        return None, None
    return start, end


def _parse_value(text: str, sign: str | None) -> float | None:
    """Parsea el valor numerico de un tag ix:nonFraction."""
    cleaned = text.strip().replace(",", "").replace(" ", "").replace("\xa0", "")
    if not cleaned or cleaned in ("-", "\u2014", "\u2013"):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None

    # Aplicar signo (atributo 'sign' de iXBRL)
    if sign == "-":
        value = -value

    return value


def _extract_contexts(soup: BeautifulSoup) -> dict[str, dict[str, Any]]:
    """Extrae los contextos XBRL del documento.

    Cada contexto guarda su periodo y si es dimensional (tiene
    segment/scenario): los facts dimensionales se descartan porque son
    desgloses, no valores de la empresa consolidada.
    """
    contexts: dict[str, dict[str, Any]] = {}
    for ctx in soup.find_all(_CONTEXT_TAGS):
        ctx_id = ctx.get("id")
        if not ctx_id:
            continue

        period: dict[str, str] = {}
        period_elem = _find_child(ctx, _PERIOD_TAGS)
        if period_elem is not None:
            instant = _find_child(period_elem, _INSTANT_TAGS)
            if instant is not None:
                period["instant"] = instant.get_text(strip=True)
            start = _find_child(period_elem, _START_TAGS)
            if start is not None:
                period["startDate"] = start.get_text(strip=True)
            end = _find_child(period_elem, _END_TAGS)
            if end is not None:
                period["endDate"] = end.get_text(strip=True)

        dimensional = _find_child(ctx, _SEGMENT_TAGS) is not None

        contexts[str(ctx_id)] = {"period": period, "dimensional": dimensional}
    return contexts


def extract_ixbrl(html_path: str | Path) -> dict[str, Any]:
    """Extrae datos financieros de un archivo HTML/iXBRL.

    Args:
        html_path: ruta al archivo HTML/iXBRL.

    Returns:
        Diccionario con:
        - "facts": lista de Fact extraidos (no dimensionales, con periodo
          resoluble y valor numerico)
        - "contexts": contextos XBRL parseados
        - "company_name": nombre de la empresa (si se encuentra)
        - "currency": moneda de reporte
    """
    path = Path(html_path)
    with path.open(encoding="utf-8", errors="replace") as f:
        soup = BeautifulSoup(f, "lxml")

    contexts = _extract_contexts(soup)

    facts: list[Fact] = []
    seen: set[tuple[str, date | None, date, float]] = set()
    skipped_dimensional = 0
    skipped_unresolved = 0

    for tag in soup.find_all("ix:nonfraction"):
        concept = tag.get("name", "")
        if not concept:
            continue

        context_ref = str(tag.get("contextref", ""))
        ctx = contexts.get(context_ref)
        if ctx is not None and ctx.get("dimensional"):
            skipped_dimensional += 1
            continue

        scale = _parse_scale(tag.get("scale"))
        sign_attr = tag.get("sign")
        unit_ref = str(tag.get("unitref", ""))

        period_start, period_end = _parse_period(context_ref, contexts)
        if period_end is None:
            skipped_unresolved += 1
            continue

        value = _parse_value(tag.get_text(), sign_attr)
        if value is None:
            continue

        # Determinar si es extension de la empresa
        kind = (
            SourceKind.IXBRL_EXTENSION if is_company_extension(str(concept)) else SourceKind.IXBRL
        )

        source = SourceRef(
            kind=kind,
            concept=str(concept),
            location=f"iXBRL tag: {concept}",
        )

        # Determinar unidad
        unit = _infer_unit(str(concept), unit_ref)

        # Evitar duplicados (mismo concepto, mismo periodo, mismo valor):
        # distintos contextRef pueden describir el mismo periodo.
        key = (str(concept), period_start, period_end, value)
        if key in seen:
            continue
        seen.add(key)

        facts.append(
            Fact(
                value=value,
                unit=unit,
                scale=scale,
                period_start=period_start,
                period_end=period_end,
                source=source,
            )
        )

    if skipped_dimensional or skipped_unresolved:
        logger.info(
            "iXBRL: %d facts descartados por dimensionalidad y %d por periodo "
            "no resoluble (%d aceptados)",
            skipped_dimensional,
            skipped_unresolved,
            len(facts),
        )

    company_name = _extract_company_name(soup)
    currency = _extract_currency(soup)

    return {
        "facts": facts,
        "contexts": contexts,
        "company_name": company_name,
        "currency": currency,
    }


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
    # En iXBRL real el nombre va inline: <ix:nonNumeric name="dei:EntityRegistrantName">
    for tag in soup.find_all("ix:nonnumeric"):
        name = str(tag.get("name", "")).lower()
        if name in ("dei:entityregistrantname", "deientityregistrantname"):
            text = tag.get_text(strip=True)
            if text:
                return str(text)
    # Fallback: tag directo dei:EntityRegistrantName (docs XBRL no-inline)
    for tag in soup.find_all("dei:entityregistrantname"):
        text = tag.get_text(strip=True)
        if text:
            return str(text)
    # Buscar en el titulo
    title = soup.find("title")
    if title:
        text = title.get_text(strip=True)
        if text and len(str(text)) < 100:
            return str(text)
    return None


def _extract_currency(soup: BeautifulSoup) -> str:
    """Extrae la moneda de reporte."""
    for unit in soup.find_all(["xbrli:unit", "unit"]):
        measure = _find_child(unit, ["xbrli:measure", "measure"])
        if measure is not None:
            text = measure.get_text(strip=True)
            if text.startswith("iso4217:"):
                return str(text).replace("iso4217:", "")
    return "USD"


__all__ = [
    "extract_ixbrl",
]
