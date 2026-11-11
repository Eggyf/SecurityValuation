"""Extracción del 10-K: iXBRL, secciones y mapeo de conceptos."""

from dcf_app.extraction.ixbrl import extract_ixbrl
from dcf_app.extraction.mapping import (
    BALANCE_SHEET_MAP,
    CASH_FLOW_MAP,
    INCOME_STATEMENT_MAP,
    NOTES_MAP,
    is_company_extension,
    map_concept,
    normalize_concept,
)
from dcf_app.extraction.orchestrator import (
    extract_financials,
    extract_from_html,
    extract_from_pdf,
    validate_extraction,
)
from dcf_app.extraction.pdf import (
    extract_pdf_tables,
    extract_pdf_text,
    parse_financial_table,
)
from dcf_app.extraction.pdf_statements import extract_statements_from_pdf
from dcf_app.extraction.sections import (
    find_balance_sheet_section,
    find_cash_flow_section,
    find_income_statement_section,
    find_notes_section,
    find_section,
)
from dcf_app.extraction.statements import build_financial_statements

__all__ = [
    "BALANCE_SHEET_MAP",
    "CASH_FLOW_MAP",
    "INCOME_STATEMENT_MAP",
    "NOTES_MAP",
    "build_financial_statements",
    "extract_financials",
    "extract_from_html",
    "extract_from_pdf",
    "extract_ixbrl",
    "extract_pdf_tables",
    "extract_pdf_text",
    "extract_statements_from_pdf",
    "find_balance_sheet_section",
    "find_cash_flow_section",
    "find_income_statement_section",
    "find_notes_section",
    "find_section",
    "is_company_extension",
    "map_concept",
    "normalize_concept",
    "parse_financial_table",
    "validate_extraction",
]
