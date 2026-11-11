"""Golden tests de extraccion end-to-end (AGENTS.md §9).

Fixtures (``tests/fixtures/``):

- ``sample_ixbrl.html``: 10-K sintetico con los casos dificiles del parser
  iXBRL: contexto dimensional, duracion trimestral, fact duplicado y
  conflicto de conceptos con valor distinto.
- ``msft_statements.pdf`` / ``nvda_statements.pdf``: recortes con la portada
  y las paginas de los estados financieros de los 10-K reales (documentos
  publicos de la SEC). Los valores ancla estan verificados a mano contra el
  documento; si un test falla es porque el parser cambio de comportamiento
  y hay que entender por que (AGENTS.md §10.5).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from dcf_app.extraction import extract_from_html, extract_from_pdf, validate_extraction
from dcf_app.extraction.ixbrl import extract_ixbrl
from dcf_app.extraction.statements import _assign
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

MSFT_PDF = FIXTURES / "msft_statements.pdf"
NVDA_PDF = FIXTURES / "nvda_statements.pdf"
IXBRL_HTML = FIXTURES / "sample_ixbrl.html"


class _HasFiscalYear(Protocol):
    """Statement con ejercicio fiscal (los tres tipos lo cumplen)."""

    fiscal_year: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _millions(fact: Fact | None) -> float | None:
    """Valor del fact en millones; None si falta el fact."""
    if fact is None:
        return None
    return fact.to_scale(Scale.MILLIONS)


def _fy[T: _HasFiscalYear](statements: list[T], year: int) -> T:
    """Devuelve el statement del ejercicio pedido."""
    for statement in statements:
        if statement.fiscal_year == year:
            return statement
    raise AssertionError(f"No existe el ejercicio {year}")


def _fact(concept: str, value: float) -> Fact:
    """Fact minimo para tests de resolucion de conflictos."""
    return Fact(
        value=value,
        unit="USD",
        scale=Scale.MILLIONS,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31),
        source=SourceRef(kind=SourceKind.IXBRL, concept=concept, location="test"),
    )


# ---------------------------------------------------------------------------
# Golden test iXBRL (fixture sintetico)
# ---------------------------------------------------------------------------


def test_golden_ixbrl_company_and_years() -> None:
    """Empresa, moneda y ejercicios extraidos del fixture iXBRL."""
    financials = extract_from_html(IXBRL_HTML)

    assert financials.company_name == "Golden Sample Corporation"
    assert financials.reporting_currency == "USD"
    assert [s.fiscal_year for s in financials.income_statements] == [2024, 2025, 2026]
    assert [s.fiscal_year for s in financials.balance_sheets] == [2025, 2026]
    assert [s.fiscal_year for s in financials.cash_flow_statements] == [2024, 2025, 2026]
    assert validate_extraction(financials) == []


def test_golden_ixbrl_income_anchors() -> None:
    """Valores del P&L FY2026 (ultimo ejercicio) contra el fixture."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.income_statements, 2026)

    assert fy2026.period_start == date(2026, 1, 1)
    assert fy2026.period_end == date(2026, 12, 31)
    assert _millions(fy2026.revenue) == 1210.0
    assert _millions(fy2026.cogs) == 484.0
    assert _millions(fy2026.gross_profit) == 726.0
    assert _millions(fy2026.sga) == 121.0
    assert _millions(fy2026.rd) == 170.0
    assert _millions(fy2026.ebit) == 435.0
    assert _millions(fy2026.interest_expense) == 24.0
    assert _millions(fy2026.pretax_income) == 411.0
    assert _millions(fy2026.income_tax_expense) == 82.0
    assert _millions(fy2026.net_income) == 329.0
    # Trazabilidad (AGENTS.md §2.3): concepto y tipo de fuente
    assert fy2026.revenue is not None
    assert fy2026.revenue.source.concept == "us-gaap:Revenues"
    assert fy2026.revenue.source.kind == SourceKind.IXBRL


def test_golden_ixbrl_eps_and_shares() -> None:
    """EPS diluido y acciones diluidas con unidad y escala correctas."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.income_statements, 2026)

    assert fy2026.diluted_eps is not None
    assert fy2026.diluted_eps.value == 3.29
    assert fy2026.diluted_eps.unit == "USD_per_share"

    assert fy2026.diluted_weighted_shares is not None
    assert _millions(fy2026.diluted_weighted_shares) == 100.0
    assert fy2026.diluted_weighted_shares.unit == "shares"


def test_golden_ixbrl_balance_anchors() -> None:
    """Valores del balance (instantes) contra el fixture."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.balance_sheets, 2026)
    fy2025 = _fy(financials.balance_sheets, 2025)

    assert fy2026.period_end == date(2026, 12, 31)
    # Cifra instantanea: el Fact no tiene inicio de periodo (AGENTS.md §6)
    assert fy2026.cash_and_equivalents is not None
    assert fy2026.cash_and_equivalents.period_start is None
    assert fy2026.cash_and_equivalents.is_instant
    assert _millions(fy2026.cash_and_equivalents) == 500.0
    assert _millions(fy2026.short_term_investments) == 200.0
    assert _millions(fy2026.accounts_receivable) == 300.0
    assert _millions(fy2026.inventory) == 150.0
    assert _millions(fy2026.total_assets) == 2000.0
    assert _millions(fy2026.accounts_payable) == 250.0
    assert _millions(fy2026.long_term_debt) == 800.0
    assert _millions(fy2026.total_equity) == 950.0

    assert _millions(fy2025.cash_and_equivalents) == 450.0
    assert _millions(fy2025.total_assets) == 1800.0


def test_golden_ixbrl_cash_flow_anchors() -> None:
    """Valores del flujo de caja FY2026 contra el fixture."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.cash_flow_statements, 2026)

    assert _millions(fy2026.cfo) == 484.0
    # CapEx: signo respetado (pago negativo, AGENTS.md §6)
    assert _millions(fy2026.capex) == -140.0
    # D&A y SBC se copian al flujo de caja desde el mismo tag
    assert _millions(fy2026.depreciation_amortization) == 100.0
    assert _millions(fy2026.sbc) == 70.0


def test_golden_ixbrl_da_sbc_copied_to_income() -> None:
    """D&A y SBC aparecen tambien en el P&L (conceptos en ambos mapas)."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.income_statements, 2026)

    assert _millions(fy2026.depreciation_amortization) == 100.0
    assert _millions(fy2026.sbc) == 70.0


def test_golden_ixbrl_dimensional_fact_discarded() -> None:
    """El revenue dimensional (700, desglose por producto) no llega al modelo."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.income_statements, 2026)

    # Si el fact dimensional se colara, revenue seria 700, no 1210.
    assert _millions(fy2026.revenue) == 1210.0


def test_golden_ixbrl_quarterly_fact_discarded() -> None:
    """La duracion trimestral (Q1, 300) no entra en el P&L anual."""
    financials = extract_from_html(IXBRL_HTML)

    # Solo los 3 ejercicios anuales; ningun grupo trimestral.
    assert len(financials.income_statements) == 3
    assert [s.fiscal_year for s in financials.income_statements] == [2024, 2025, 2026]


def test_golden_ixbrl_duplicate_fact_collapsed() -> None:
    """El fact duplicado (mismo concepto/periodo/valor) se colapsa."""
    data = extract_ixbrl(IXBRL_HTML)
    revenues_facts = [
        f
        for f in data["facts"]
        if f.source.concept == "us-gaap:Revenues" and f.period_end == date(2026, 12, 31)
    ]
    # FY2026: un fact anual (el duplicado exacto se colapsa); el trimestral
    # y el dimensional se excluyen antes (periodo/segmento distintos).
    assert len(revenues_facts) == 1
    assert revenues_facts[0].value == 1210.0


def test_golden_ixbrl_concept_conflict_first_document_order_wins() -> None:
    """SalesRevenueNet (1500, despues en el documento) no desplaza a Revenues."""
    financials = extract_from_html(IXBRL_HTML)
    fy2026 = _fy(financials.income_statements, 2026)

    assert _millions(fy2026.revenue) == 1210.0


# ---------------------------------------------------------------------------
# Reglas de resolucion de conflictos (unit tests de _assign)
# ---------------------------------------------------------------------------


def test_assign_first_fact_wins_between_standard_concepts() -> None:
    """Dos conceptos estandar con valor distinto: gana el primero asignado."""
    target: dict[str, Fact] = {}
    _assign(target, "revenue", _fact("us-gaap:Revenues", 1210.0))
    _assign(target, "revenue", _fact("us-gaap:SalesRevenueNet", 1500.0))

    assert target["revenue"].value == 1210.0


def test_assign_standard_concept_displaces_extension() -> None:
    """El tag estandar us-gaap desplaza a una extension de la empresa."""
    target: dict[str, Fact] = {}
    _assign(target, "revenue", _fact("gs:TotalRevenues", 1500.0))
    _assign(target, "revenue", _fact("us-gaap:Revenues", 1210.0))

    assert target["revenue"].source.concept == "us-gaap:Revenues"
    assert target["revenue"].value == 1210.0


def test_assign_equal_value_does_not_displace() -> None:
    """Valores iguales: el fact existente se conserva (no hay conflicto real)."""
    target: dict[str, Fact] = {}
    _assign(target, "revenue", _fact("us-gaap:Revenues", 1210.0))
    _assign(target, "revenue", _fact("us-gaap:SalesRevenueNet", 1210.0))

    assert target["revenue"].source.concept == "us-gaap:Revenues"


# ---------------------------------------------------------------------------
# Golden tests PDF (recortes de 10-K reales de la SEC)
# ---------------------------------------------------------------------------


def test_golden_msft_pdf() -> None:
    """MSFT FY2026: valores ancla verificados contra el 10-K (PDF p. 73/75/76)."""
    financials = extract_from_pdf(MSFT_PDF)

    assert financials.company_name == "MICROSOFT CORPORATION"
    assert [s.fiscal_year for s in financials.income_statements] == [2024, 2025, 2026]
    assert [s.fiscal_year for s in financials.balance_sheets] == [2025, 2026]
    assert [s.fiscal_year for s in financials.cash_flow_statements] == [2024, 2025, 2026]

    income = _fy(financials.income_statements, 2026)
    assert income.period_start == date(2025, 7, 1)
    assert income.period_end == date(2026, 6, 30)
    assert _millions(income.revenue) == 331839.0
    assert _millions(income.cogs) == 106374.0
    assert _millions(income.gross_profit) == 225465.0
    assert _millions(income.rd) == 35562.0
    # SG&A partido en dos etiquetas: se suma (Sales and marketing + G&A)
    assert _millions(income.sga) == 34666.0
    assert _millions(income.ebit) == 155237.0
    assert _millions(income.pretax_income) == 165934.0
    assert _millions(income.income_tax_expense) == 32185.0
    assert _millions(income.net_income) == 133749.0
    assert income.diluted_eps is not None
    assert income.diluted_eps.value == 17.95
    assert _millions(income.diluted_weighted_shares) == 7453.0

    balance = _fy(financials.balance_sheets, 2026)
    assert balance.period_end == date(2026, 6, 30)
    assert _millions(balance.cash_and_equivalents) == 20935.0
    assert _millions(balance.short_term_investments) == 55908.0
    assert _millions(balance.accounts_receivable) == 80876.0
    assert _millions(balance.inventory) == 1397.0
    assert _millions(balance.accounts_payable) == 42416.0
    assert _millions(balance.deferred_revenue) == 72965.0
    assert _millions(balance.short_term_debt) == 9227.0
    assert _millions(balance.long_term_debt) == 31067.0
    assert _millions(balance.total_equity) == 442387.0
    assert _millions(balance.total_assets) == 758376.0
    assert _millions(balance.total_liabilities) == 315989.0

    cash = _fy(financials.cash_flow_statements, 2026)
    assert cash.period_start == date(2025, 7, 1)
    assert _millions(cash.cfo) == 182935.0
    assert _millions(cash.capex) == -115948.0
    assert _millions(cash.depreciation_amortization) == 38534.0
    assert _millions(cash.sbc) == 12405.0

    # Trazabilidad (AGENTS.md §2.3): fuente text_fallback con pagina
    assert income.revenue is not None
    assert income.revenue.source.kind == SourceKind.TEXT_FALLBACK
    assert income.revenue.source.location is not None
    assert "PDF p." in income.revenue.source.location


def test_golden_nvda_pdf() -> None:
    """NVDA FY2026: valores ancla verificados contra el 10-K (PDF p. 71/73/75)."""
    financials = extract_from_pdf(NVDA_PDF)

    assert financials.company_name == "NVIDIA CORPORATION"
    assert [s.fiscal_year for s in financials.income_statements] == [2024, 2025, 2026]
    assert [s.fiscal_year for s in financials.balance_sheets] == [2025, 2026]
    assert [s.fiscal_year for s in financials.cash_flow_statements] == [2024, 2025, 2026]

    income = _fy(financials.income_statements, 2026)
    assert income.period_end == date(2026, 1, 25)
    assert _millions(income.revenue) == 215938.0
    assert _millions(income.cogs) == 62475.0
    assert _millions(income.gross_profit) == 153463.0
    assert _millions(income.rd) == 18497.0
    assert _millions(income.sga) == 4579.0
    assert _millions(income.ebit) == 130387.0
    assert _millions(income.interest_expense) == -259.0
    assert _millions(income.pretax_income) == 141450.0
    assert _millions(income.income_tax_expense) == 21383.0
    assert _millions(income.net_income) == 120067.0
    assert income.diluted_eps is not None
    assert income.diluted_eps.value == 4.90
    assert _millions(income.diluted_weighted_shares) == 24514.0

    balance = _fy(financials.balance_sheets, 2026)
    assert balance.period_end == date(2026, 1, 25)
    assert _millions(balance.cash_and_equivalents) == 10605.0
    assert _millions(balance.short_term_investments) == 51951.0
    assert _millions(balance.accounts_receivable) == 38466.0
    assert _millions(balance.inventory) == 21403.0
    assert _millions(balance.accounts_payable) == 9812.0
    assert _millions(balance.short_term_debt) == 999.0
    assert _millions(balance.long_term_debt) == 7469.0
    assert _millions(balance.total_equity) == 157293.0
    assert _millions(balance.total_assets) == 206803.0
    assert _millions(balance.total_liabilities) == 49510.0

    cash = _fy(financials.cash_flow_statements, 2026)
    assert _millions(cash.cfo) == 102718.0
    assert _millions(cash.capex) == -6042.0
    assert _millions(cash.depreciation_amortization) == 2843.0
    assert _millions(cash.sbc) == 6386.0
    assert _millions(cash.net_change_in_cash) == 2016.0
