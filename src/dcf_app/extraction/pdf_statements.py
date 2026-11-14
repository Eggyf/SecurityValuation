"""Extraccion de estados financieros desde PDF por etiquetas (AGENTS.md §6).

Fallback cuando no hay HTML/iXBRL: localiza las paginas de los estados
financieros (Item 8) y parsea el texto con el patron tipico de los PDF
renderizados desde EDGAR: etiqueta en una linea y, a continuacion, un valor
por columna (una por ejercicio fiscal, en el orden de la cabecera).

Limitaciones conocidas (docs/methodology.md):
- Solo se parsea la primera pagina de cada estado; si el estado continua
  en la pagina siguiente, las partidas posteriores quedan en None.
- Los facts se marcan como ``text_fallback`` (confianza baja) con pagina y
  titulo como procedencia (AGENTS.md §2.3, §6).
- El inicio de ejercicio de la columna mas antigua se aproxima (cierre - 1
  ano + 1 dia) cuando el documento no aporta el cierre anterior.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pymupdf

from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Titulos de estados (fullmatch: evita "COMPREHENSIVE INCOME STATEMENTS")
# ---------------------------------------------------------------------------
_STATEMENT_TITLES: dict[str, re.Pattern[str]] = {
    "income": re.compile(
        r"(?:consolidated )?(?:statements? of (?:income|operations|earnings|comprehensive income)"
        r"|income statements?)",
        re.IGNORECASE,
    ),
    "balance": re.compile(
        r"(?:consolidated )?balance sheets?", re.IGNORECASE
    ),
    "cashflow": re.compile(
        r"(?:consolidated )?(?:statements? of cash flows?|cash flows? statements?)",
        re.IGNORECASE,
    ),
}

# Cabeceras genericas que aparecen entre el titulo y las columnas de fechas.
_GENERIC_HEADERS = {"year ended", "as of", "fiscal year", "for the year ended"}

_SCALE_RE = re.compile(r"\(\s*in\s+(millions|thousands|billions)", re.IGNORECASE)
_SCALES: dict[str, Scale] = {
    "millions": Scale.MILLIONS,
    "thousands": Scale.THOUSANDS,
    "billions": Scale.BILLIONS,
}

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

_HINT_RE = re.compile(r"^(?:year ended\s+)?([a-z]+)\s+(\d{1,2}),?$", re.IGNORECASE)
_FULL_DATE_RE = re.compile(r"^([a-z]+)\s+(\d{1,2}),\s*(\d{4})$", re.IGNORECASE)
_YEAR_RE = re.compile(r"^(\d{4})$")
_NUMBER_RE = re.compile(r"^[\$\s]*\(?\s*-?\d[\d,]*(?:\.\d+)?\s*\)?[\$\s]*$")
_DASHES = {"-", "--", "\u2014", "\u2013", "\u2212"}

_EPS_SECTION_RE = re.compile(r"^(?:earnings|net income) per share\b", re.IGNORECASE)
_SHARES_SECTION_RE = re.compile(r"^weighted average shares\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Etiquetas por estado. Patrones anclados al inicio de la linea; una linea
# que termina en ":" es cabecera de seccion, nunca etiqueta de valor.
# ---------------------------------------------------------------------------
# (patron, campo) o (patron, "sga_part") para componentes que se suman.
_INCOME_LABELS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^total revenue\b", re.I), "revenue"),
    (re.compile(r"^revenues?\b", re.I), "revenue"),
    (re.compile(r"^net sales\b", re.I), "revenue"),
    (re.compile(r"^total cost of revenue\b", re.I), "cogs"),
    (re.compile(r"^cost of revenue\b", re.I), "cogs"),
    (re.compile(r"^cost of goods sold\b", re.I), "cogs"),
    (re.compile(r"^cost of sales\b", re.I), "cogs"),
    (re.compile(r"^gross (?:margin|profit)\b", re.I), "gross_profit"),
    (re.compile(r"^research and development\b", re.I), "rd"),
    (re.compile(r"^sales and marketing\b", re.I), "sga_part"),
    (re.compile(r"^selling and marketing\b", re.I), "sga_part"),
    (re.compile(r"^general and administrative\b", re.I), "sga_part"),
    (re.compile(r"^sales, general and administrative\b", re.I), "sga"),
    (re.compile(r"^selling, general and administrative\b", re.I), "sga"),
    (re.compile(r"^operating income\b", re.I), "ebit"),
    (re.compile(r"^income from operations\b", re.I), "ebit"),
    (re.compile(r"^interest expense\b", re.I), "interest_expense"),
    (re.compile(r"^income before income tax(?:es)?\b", re.I), "pretax_income"),
    (re.compile(r"^earnings before income tax(?:es)?\b", re.I), "pretax_income"),
    (re.compile(r"^provision for income taxes\b", re.I), "income_tax_expense"),
    (re.compile(r"^income tax expense\b", re.I), "income_tax_expense"),
    (re.compile(r"^net income$", re.I), "net_income"),
    # 'Diluted' se resuelve por seccion (EPS vs acciones)
]

_BALANCE_LABELS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^cash and cash equivalents\b", re.I), "cash_and_equivalents"),
    (re.compile(r"^short[- ]term investments\b", re.I), "short_term_investments"),
    (re.compile(r"^marketable securities$", re.I), "short_term_investments"),
    (re.compile(r"^accounts receivable,? ?net\b", re.I), "accounts_receivable"),
    (re.compile(r"^receivables, net\b", re.I), "accounts_receivable"),
    (re.compile(r"^inventor(?:y|ies)\b", re.I), "inventory"),
    (re.compile(r"^other current assets\b", re.I), "other_current_assets"),
    (re.compile(r"^prepaid expenses and other current assets\b", re.I), "other_current_assets"),
    (re.compile(r"^accounts payable\b", re.I), "accounts_payable"),
    (re.compile(r"^accrued and other current liabilities\b", re.I), "accrued_liabilities"),
    (re.compile(r"^accrued liabilities\b", re.I), "accrued_liabilities"),
    (re.compile(r"^short[- ]term unearned revenue\b", re.I), "deferred_revenue"),
    (re.compile(r"^unearned revenue\b", re.I), "deferred_revenue"),
    (re.compile(r"^deferred revenue\b", re.I), "deferred_revenue"),
    (re.compile(r"^short[- ]term debt\b", re.I), "short_term_debt"),
    (re.compile(r"^current portion of long[- ]term debt\b", re.I), "short_term_debt"),
    (re.compile(r"^long[- ]term debt\b", re.I), "long_term_debt"),
    (
        re.compile(r"^operating lease liabilities, current\b", re.I),
        "operating_lease_liabilities_current",
    ),
    (
        re.compile(r"^current operating lease liabilities\b", re.I),
        "operating_lease_liabilities_current",
    ),
    (
        re.compile(r"^long[- ]term operating lease liabilities\b", re.I),
        "operating_lease_liabilities_noncurrent",
    ),
    (re.compile(r"^operating lease liabilities\b", re.I), "operating_lease_liabilities_noncurrent"),
    (re.compile(r"^finance lease liabilities\b", re.I), "finance_lease_liabilities"),
    (re.compile(r"^preferred stock\b", re.I), "preferred_stock"),
    (re.compile(r"^non[- ]controlling interest\b", re.I), "non_controlling_interest"),
    (re.compile(r"^total stockholders.? equity\b", re.I), "total_equity"),
    (re.compile(r"^total shareholders.? equity\b", re.I), "total_equity"),
    (re.compile(r"^total equity\b", re.I), "total_equity"),
    (re.compile(r"^total assets\b", re.I), "total_assets"),
    (re.compile(r"^total liabilities$", re.I), "total_liabilities"),
]

_CASHFLOW_LABELS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^net income$", re.I), "net_income"),
    (re.compile(r"^net cash from operations\b", re.I), "cfo"),
    (re.compile(r"^net cash provided by operating activities\b", re.I), "cfo"),
    (re.compile(r"^net cash used in operating activities\b", re.I), "cfo"),
    (re.compile(r"^cash flow from operating activities\b", re.I), "cfo"),
    (re.compile(r"^additions to property and equipment\b", re.I), "capex"),
    (re.compile(r"^purchases? (?:of|related to) property and equipment\b", re.I), "capex"),
    (re.compile(r"^payments? to acquire property, plant and equipment\b", re.I), "capex"),
    (re.compile(r"^capital expenditures\b", re.I), "capex"),
    (re.compile(r"^depreciation, amortization, and other\b", re.I), "depreciation_amortization"),
    (re.compile(r"^depreciation and amortization\b", re.I), "depreciation_amortization"),
    (re.compile(r"^depreciation, depletion and amortization\b", re.I), "depreciation_amortization"),
    (re.compile(r"^stock[- ]based compensation expense\b", re.I), "sbc"),
    (re.compile(r"^share[- ]based compensation\b", re.I), "sbc"),
    (re.compile(r"^net (?:increase|decrease|change) in cash\b", re.I), "net_change_in_cash"),
    (re.compile(r"^change in cash\b", re.I), "net_change_in_cash"),
]

_STATEMENT_LABELS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "income": _INCOME_LABELS,
    "balance": _BALANCE_LABELS,
    "cashflow": _CASHFLOW_LABELS,
}

_UNIT_BY_FIELD: dict[str, str] = {
    "diluted_eps": "USD_per_share",
    "diluted_weighted_shares": "shares",
}


def _normalize_line(text: str) -> str:
    """Normaliza una linea: espacios, comillas curvas y guiones tipograficos."""
    cleaned = (
        text.replace("\xa0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_number(text: str) -> float | None:
    """Parsea un numero tipico de estados financieros.

    Maneja comas, '$', espacios y parentesis como negativo.
    """
    cleaned = text.replace(",", "").replace("$", "").replace(" ", "")
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _month_number(name: str) -> int | None:
    """Numero de mes a partir del nombre o abreviatura."""
    return _MONTHS.get(name.lower().strip().strip("."))


def _find_statement_pages(doc: Any) -> dict[str, int]:  # noqa: ANN401 (borde del parseo)
    """Localiza la primera pagina de cada estado financiero."""
    found: dict[str, int] = {}
    # Primera pasada: buscar por título exacto (más fiable)
    for page_num, page in enumerate(doc):
        lines = [_normalize_line(t) for t in page.get_text().splitlines() if t.strip()]
        for line in lines[:25]:
            for statement_type, pattern in _STATEMENT_TITLES.items():
                if statement_type not in found and pattern.fullmatch(line):
                    found[statement_type] = page_num
                    break

    # Segunda pasada: fallback por palabras clave solo si no se encontró
    if len(found) < 3:
        for page_num, page in enumerate(doc):
            text = page.get_text()
            page_text_lower = text.lower()
            lines = [_normalize_line(t) for t in text.splitlines() if t.strip()]

            # Solo considerar páginas que no son MD&A (buscar "Item 8" o "Financial Statements")
            is_financial_page = any(
                "item 8" in line.lower() or "financial statements" in line.lower()
                for line in lines[:10]
            )

            if not is_financial_page:
                continue

            income_kw = ["revenue", "net income", "operating income", "cost of"]
            balance_kw = ["total assets", "total liabilities", "stockholders", "shareholders"]
            cashflow_kw = ["cash flow", "operating activities", "investing activities"]

            income_score = sum(1 for kw in income_kw if kw in page_text_lower)
            balance_score = sum(1 for kw in balance_kw if kw in page_text_lower)
            cashflow_score = sum(1 for kw in cashflow_kw if kw in page_text_lower)

            if income_score >= 3 and "income" not in found:
                found["income"] = page_num
            if balance_score >= 3 and "balance" not in found:
                found["balance"] = page_num
            if cashflow_score >= 2 and "cashflow" not in found:
                found["cashflow"] = page_num

    return found


def _parse_header(lines: list[str], title_idx: int) -> tuple[Scale, list[date], int]:
    """Parsea escala y columnas de fechas tras el titulo del estado.

    Returns:
        (escala, fechas de cierre por columna en orden de documento, indice
        de la primera linea del cuerpo).
    """
    scale = Scale.UNITS
    month_day: tuple[int, int] | None = None
    columns: list[date] = []
    i = title_idx + 1
    n = len(lines)
    while i < n:
        line = lines[i]
        if not line:
            i += 1
            continue
        scale_match = _SCALE_RE.search(line)
        if scale_match:
            scale = _SCALES.get(scale_match.group(1).lower(), Scale.UNITS)
            i += 1
            continue
        if line.lower().strip(",") in _GENERIC_HEADERS:
            i += 1
            continue
        full = _FULL_DATE_RE.match(line)
        if full:
            month = _month_number(full.group(1))
            if month is None:
                break
            columns.append(date(int(full.group(3)), month, int(full.group(2))))
            i += 1
            continue
        year = _YEAR_RE.match(line)
        if year:
            y = int(year.group(1))
            if month_day is not None:
                columns.append(date(y, month_day[0], month_day[1]))
            else:
                # Sin pista de mes/dia: cierre asumido a 31 de diciembre.
                columns.append(date(y, 12, 31))
            i += 1
            continue
        hint = _HINT_RE.match(line)
        if hint and not columns:
            month = _month_number(hint.group(1))
            if month is not None:
                month_day = (month, int(hint.group(2)))
                i += 1
                continue
        break
    return scale, columns, i


def _period_start_for(end: date, all_ends: list[date]) -> date:
    """Inicio del ejercicio: cierre anterior + 1 dia (o aproximacion)."""
    earlier = sorted(e for e in all_ends if e < end)
    if earlier:
        return earlier[-1] + timedelta(days=1)
    try:
        return end.replace(year=end.year - 1) + timedelta(days=1)
    except ValueError:  # 29 de febrero
        return date(end.year - 1, 3, 1)


def _match_label(line: str, labels: list[tuple[re.Pattern[str], str]]) -> str | None:
    """Devuelve el campo al que mapea una linea de etiqueta (o None)."""
    for pattern, field in labels:
        if pattern.match(line):
            return field
    return None


class _FieldCollector:
    """Acumula valores por (campo, fecha de cierre) mientras parsea la pagina."""

    def __init__(self, scale: Scale, source_template: str) -> None:
        self.scale = scale
        self.source_template = source_template
        self.plain: dict[str, dict[date, Fact]] = {}
        self.sga_parts: dict[date, list[float]] = {}
        self.sga_labels: dict[date, list[str]] = {}

    def _source(self, label: str) -> SourceRef:
        return SourceRef(
            kind=SourceKind.TEXT_FALLBACK, location=self.source_template.format(label=label)
        )

    def _record_fact(self, field: str, end: date, value: float, label: str) -> None:
        """Crea el Fact con la escala correcta para su campo.

        La escala del estado ("in millions") aplica a las cifras monetarias
        y a los conteos de acciones, pero NO a los importes por accion:
        "(In millions, except per share amounts)".
        """
        self.plain.setdefault(field, {})[end] = Fact(
            value=value,
            unit=_UNIT_BY_FIELD.get(field, "USD"),
            scale=Scale.UNITS if field == "diluted_eps" else self.scale,
            period_start=None,  # se asigna al construir el statement
            period_end=end,
            source=self._source(label),
        )

    def record(self, field: str, end: date, value: float, label: str) -> None:
        """Guarda un valor; los componentes de SG&A se acumulan aparte."""
        if field == "sga_part":
            self.sga_parts.setdefault(end, []).append(value)
            self.sga_labels.setdefault(end, []).append(label)
            return
        self._record_fact(field, end, value, label)

    def collect(self) -> dict[str, dict[date, Fact]]:
        """Fusiona los componentes de SG&A en un solo fact por ejercicio."""
        fields = dict(self.plain)
        for end, values in self.sga_parts.items():
            if "sga" in fields and end in fields["sga"]:
                continue  # la etiqueta directa de SG&A gana a los componentes
            joined = " + ".join(self.sga_labels[end])
            fields.setdefault("sga", {})[end] = Fact(
                value=sum(values),
                unit="USD",
                scale=self.scale,
                period_start=None,
                period_end=end,
                source=self._source(joined),
            )
        return fields


def _parse_statement_page(
    page_text: str, statement_type: str, page_num: int
) -> dict[str, dict[date, Fact]]:
    """Parsea una pagina de estado financiero a {campo: {cierre: Fact}}."""
    lines = [_normalize_line(t) for t in page_text.splitlines()]
    title_idx = -1
    for idx, line in enumerate(lines[:12]):
        if _STATEMENT_TITLES[statement_type].fullmatch(line):
            title_idx = idx
            break
    if title_idx < 0:
        return {}

    scale, columns, body_start = _parse_header(lines, title_idx)
    if not columns:
        logger.warning("PDF p.%d: no se detectaron columnas de ejercicios", page_num + 1)
        return {}

    source_template = f"PDF p. {page_num + 1}, {lines[title_idx].title()}: '{{label}}'"
    collector = _FieldCollector(scale, source_template)
    labels = _STATEMENT_LABELS[statement_type]

    pending: str | None = None
    pending_is_part = False
    pending_label = ""
    slot = 0
    section: str | None = None  # 'eps' | 'shares'

    for line in lines[body_start:]:
        if not line or line == "$":
            continue
        if line in _DASHES:
            if pending is not None and slot < len(columns):
                slot += 1  # guion = valor ausente; consume la columna
            continue
        if _NUMBER_RE.match(line):
            if pending is not None and slot < len(columns):
                value = _parse_number(line)
                if value is not None:
                    if pending_is_part:
                        collector.record("sga_part", columns[slot], value, pending_label)
                    else:
                        collector.record(pending or "", columns[slot], value, pending_label)
                slot += 1
                if slot >= len(columns):
                    pending = None
            continue

        # Linea con letras: etiqueta, cabecera de seccion o ruido.
        if _EPS_SECTION_RE.match(line):
            section = "eps"
            pending = None
            continue
        if _SHARES_SECTION_RE.match(line):
            section = "shares"
            pending = None
            continue
        if line.lower() in ("basic", "diluted"):
            if line.lower() == "diluted":
                if section == "eps":
                    pending, pending_is_part, pending_label = "diluted_eps", False, line
                elif section == "shares":
                    pending, pending_is_part, pending_label = "diluted_weighted_shares", False, line
                slot = 0
            else:
                pending = None
            continue
        if line.endswith(":"):
            pending = None  # cabecera de seccion, no etiqueta de valor
            continue
        field = _match_label(line, labels)
        if field is not None:
            pending = field
            pending_is_part = field == "sga_part"
            pending_label = line
            slot = 0
        else:
            pending = None

    return collector.collect()


def _extract_company_name(
    doc: Any,  # noqa: ANN401 (borde del parseo)
    pages_to_scan: int = 6,
) -> str | None:
    """Busca el nombre de la empresa en las primeras paginas (portada)."""
    company_re = re.compile(
        r"^[A-Z][A-Za-z0-9&.,'()\-\s]{2,60}"
        r"(?:Corporation|Incorporated|Inc\.?|Corp\.?|Company|Co\.|Limited|Ltd\.?|PLC|plc)\.?$",
        re.IGNORECASE,
    )
    for page in list(doc)[:pages_to_scan]:
        for raw in page.get_text().splitlines():
            line = _normalize_line(raw)
            if company_re.match(line) and len(line.split()) >= 2:
                return line
    return None


def extract_statements_from_pdf(pdf_path: str | Path) -> FinancialStatements:
    """Extrae los estados financieros de un 10-K en PDF.

    Args:
        pdf_path: ruta al PDF.

    Returns:
        FinancialStatements con las partidas localizadas (el resto queda en
        None) marcadas como ``text_fallback``.
    """
    path = Path(pdf_path)
    doc = pymupdf.open(str(path))  # type: ignore[no-untyped-call]
    try:
        statement_pages = _find_statement_pages(doc)
        company_name = _extract_company_name(doc) or path.stem

        income_fields: dict[str, dict[date, Fact]] = {}
        balance_fields: dict[str, dict[date, Fact]] = {}
        cashflow_fields: dict[str, dict[date, Fact]] = {}

        if "income" in statement_pages:
            page_num = statement_pages["income"]
            income_fields = _parse_statement_page(doc[page_num].get_text(), "income", page_num)  # type: ignore[no-untyped-call]
        if "balance" in statement_pages:
            page_num = statement_pages["balance"]
            balance_fields = _parse_statement_page(doc[page_num].get_text(), "balance", page_num)  # type: ignore[no-untyped-call]
        if "cashflow" in statement_pages:
            page_num = statement_pages["cashflow"]
            cashflow_fields = _parse_statement_page(doc[page_num].get_text(), "cashflow", page_num)  # type: ignore[no-untyped-call]
    finally:
        doc.close()  # type: ignore[no-untyped-call]

    def _years(fields: dict[str, dict[date, Fact]]) -> set[date]:
        ends: set[date] = set()
        for by_date in fields.values():
            ends.update(by_date.keys())
        return ends

    income_ends = _years(income_fields)
    cashflow_ends = _years(cashflow_fields)

    income_list: list[IncomeStatement] = []
    for end in sorted(income_ends):
        start = _period_start_for(end, sorted(income_ends))
        kwargs = {
            field: by_date[end].model_copy(update={"period_start": start})
            for field, by_date in income_fields.items()
            if end in by_date
        }
        income_list.append(
            IncomeStatement(fiscal_year=end.year, period_start=start, period_end=end, **kwargs)
        )

    cashflow_list: list[CashFlowStatement] = []
    for end in sorted(cashflow_ends):
        start = _period_start_for(end, sorted(cashflow_ends))
        kwargs = {
            field: by_date[end].model_copy(update={"period_start": start})
            for field, by_date in cashflow_fields.items()
            if end in by_date
        }
        cashflow_list.append(
            CashFlowStatement(fiscal_year=end.year, period_start=start, period_end=end, **kwargs)
        )

    balance_list: list[BalanceSheet] = []
    for end in sorted(_years(balance_fields)):
        kwargs = {f: by_date[end] for f, by_date in balance_fields.items() if end in by_date}
        balance_list.append(BalanceSheet(fiscal_year=end.year, period_end=end, **kwargs))

    if not (income_list and balance_list and cashflow_list):
        # Degradacion segura (AGENTS.md §2.8): sin los tres estados no hay
        # valoracion posible; se devuelven vacios y el llamador avisa.
        logger.warning(
            "PDF sin estados completos: income=%d, balance=%d, cashflow=%d",
            len(income_list),
            len(balance_list),
            len(cashflow_list),
        )
        return FinancialStatements(company_name=company_name)

    return FinancialStatements(
        company_name=company_name,
        income_statements=income_list,
        balance_sheets=balance_list,
        cash_flow_statements=cashflow_list,
    )


__all__ = [
    "extract_statements_from_pdf",
]
