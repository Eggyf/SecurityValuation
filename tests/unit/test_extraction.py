"""Tests de :mod:`dcf_app.extraction`."""

from __future__ import annotations

from pathlib import Path

import pytest

from dcf_app.extraction import extract_financials, validate_extraction
from dcf_app.extraction.mapping import map_concept, normalize_concept
from dcf_app.extraction.orchestrator import extract_from_pdf
from dcf_app.models.financials import FinancialStatements


def test_normalize_concept() -> None:
    """Normaliza conceptos XBRL correctamente."""

    assert normalize_concept("us-gaap:Revenues") == "usgaaprevenues"
    assert normalize_concept("Revenue from Contract") == "revenuefromcontract"


def test_map_concept_income() -> None:
    """Mapea conceptos de cuenta de resultados."""

    assert map_concept("us-gaap:Revenues", "income") == "revenue"
    assert map_concept("us-gaap:NetIncomeLoss", "income") == "net_income"
    assert map_concept("us-gaap:OperatingIncomeLoss", "income") == "ebit"


def test_map_concept_balance() -> None:
    """Mapea conceptos de balance."""

    assert map_concept("us-gaap:Assets", "balance") == "total_assets"
    assert (
        map_concept("us-gaap:CashAndCashEquivalentsAtCarryingValue", "balance")
        == "cash_and_equivalents"
    )


def test_map_concept_unknown() -> None:
    """Concepto desconocido → None."""

    assert map_concept("unknown:Concept", "income") is None


def test_extract_from_pdf_returns_financials() -> None:
    """La extracción de PDF devuelve FinancialStatements."""
    pdf_path = Path("10-ks/MSFT/MSFT 10-K.pdf")
    if not pdf_path.exists():
        pytest.skip("PDF no disponible")
    result = extract_from_pdf(pdf_path)
    assert isinstance(result, FinancialStatements)
    assert result.company_name == "MSFT 10-K"


def test_validate_extraction_empty() -> None:
    """FinancialStatements sin datos útiles genera advertencias."""
    from datetime import date

    from dcf_app.models.fact import SourceKind, SourceRef
    from dcf_app.models.financials import BalanceSheet, CashFlowStatement, IncomeStatement

    _ = SourceRef(kind=SourceKind.TEXT_FALLBACK, location="test")
    income = IncomeStatement(
        fiscal_year=2024, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31)
    )
    balance = BalanceSheet(fiscal_year=2024, period_end=date(2024, 12, 31))
    cf = CashFlowStatement(
        fiscal_year=2024, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31)
    )
    fs = FinancialStatements(
        company_name="Test",
        income_statements=[income],
        balance_sheets=[balance],
        cash_flow_statements=[cf],
    )
    warnings = validate_extraction(fs)
    assert len(warnings) > 0
    assert any("Revenue" in w or "resultados" in w for w in warnings)


def test_extract_financials_unsupported_format() -> None:
    """Formato no soportado → ValueError."""
    with pytest.raises(ValueError, match="Formato no soportado"):
        extract_financials("test.txt")
