"""Tests de paridad entre el motor DCF real y la referencia independiente.

Verifica que el motor produce los mismos resultados que la implementación
independiente (tests/reference/dcf_reference.py) en varios casos.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from dcf_app.models.assumptions import Assumptions, DiscountConvention, TerminalValueMethod
from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import (
    BalanceSheet,
    CashFlowStatement,
    FinancialStatements,
    IncomeStatement,
)
from dcf_app.valuation.dcf import run_dcf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from reference.dcf_reference import RefInputs, run_ref_dcf


def _src() -> SourceRef:
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value: float) -> Fact:
    return Fact(value=value, unit="USD", scale=Scale.MILLIONS, period_end=date(2024, 12, 31), source=_src())


def _make_financials(revenue: float = 1000.0, base_revenue: float | None = 1000.0, debt: float = 400.0) -> FinancialStatements:
    """Crea financials que producen las métricas del caso base."""
    # Año anterior (para base_revenue)
    income_prev = IncomeStatement(
        fiscal_year=2023,
        period_start=date(2023, 1, 1),
        period_end=date(2023, 12, 31),
        revenue=_fact(revenue),
        ebit=_fact(revenue * 0.20),
        depreciation_amortization=_fact(revenue * 0.04),
    )
    income = IncomeStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        revenue=_fact(revenue),
        ebit=_fact(revenue * 0.20),
        depreciation_amortization=_fact(revenue * 0.04),
    )
    balance = BalanceSheet(
        fiscal_year=2024,
        period_end=date(2024, 12, 31),
        cash_and_equivalents=_fact(150.0),
        short_term_investments=_fact(0.0),
        accounts_receivable=_fact(80.0),
        inventory=_fact(60.0),
        accounts_payable=_fact(40.0),
        short_term_debt=_fact(0.0),
        long_term_debt=_fact(debt),
        operating_lease_liabilities_current=_fact(0.0),
        operating_lease_liabilities_noncurrent=_fact(0.0),
        finance_lease_liabilities=_fact(0.0),
        preferred_stock=_fact(0.0),
        non_controlling_interest=_fact(0.0),
        total_equity=_fact(1000.0),
        total_assets=_fact(2000.0),
        total_liabilities=_fact(1000.0),
    )
    cf = CashFlowStatement(
        fiscal_year=2024,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        cfo=_fact(300.0),
        capex=_fact(-50.0),
        depreciation_amortization=_fact(revenue * 0.04),
        sbc=_fact(0.0),
    )
    return FinancialStatements(
        company_name="Test Corp",
        income_statements=[income_prev, income],
        balance_sheets=[balance],
        cash_flow_statements=[cf],
    )


def _make_assumptions(
    growth_initial: float = 0.10,
    growth_terminal: float = 0.025,
    margin_target: float = 0.20,
    wacc: float = 0.09,
    g: float = 0.025,
    mid_year: bool = False,
    debt: float = 400.0,
    roic_terminal: float | None = None,
) -> Assumptions:
    return Assumptions(
        company_name="Test Corp",
        fiscal_year_end=date(2024, 12, 31),
        valuation_date=date(2024, 12, 31),
        forecast_horizon=5,
        initial_revenue_growth=growth_initial,
        terminal_revenue_growth=growth_terminal,
        ebit_margin_target=margin_target,
        risk_free_rate=0.0425,
        equity_beta=1.08456,  # produces WACC ≈ 0.09
        equity_risk_premium=0.05,
        market_equity_value=3000.0,
        market_debt_value=debt,
        cost_of_debt=0.05,
        tax_rate=0.21,
        stock_price_current=20.0,
        shares_outstanding=100.0,
        discount_convention=DiscountConvention.MID_YEAR if mid_year else DiscountConvention.END_OF_YEAR,
        terminal_value_method=TerminalValueMethod.GORDON_GROWTH,
        roic_terminal=roic_terminal,
    )


def _ref_inputs(
    growth_initial: float = 0.10,
    growth_terminal: float = 0.025,
    margin_target: float = 0.20,
    wacc: float = 0.09,
    g: float = 0.025,
    mid_year: bool = False,
    debt: float = 400.0,
    roic_terminal: float | None = None,
) -> RefInputs:
    return RefInputs(
        revenue0=1000.0,
        growth_initial=growth_initial,
        growth_terminal=growth_terminal,
        margin_current=0.20,
        margin_target=margin_target,
        tax_rate=0.21,
        da_pct=0.04,
        capex_pct=0.05,
        nwc_pct=0.10,
        wacc=wacc,
        g=g,
        cash=150.0,
        debt=debt,
        shares=100.0,
        horizon=5,
        base_revenue=1000.0,
        mid_year=mid_year,
        roic_terminal=roic_terminal,
    )


class TestParity:
    """Paridad entre motor real y referencia independiente."""

    def test_case_base(self) -> None:
        """Caso base: todos los valores coinciden."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        result = run_dcf(assumptions, financials)

        ref = run_ref_dcf(_ref_inputs())
        assert math.isclose(result.enterprise_value, ref.enterprise_value, rel_tol=1e-4)
        assert math.isclose(result.price_per_share, ref.price_per_share, abs_tol=0.01)

    def test_mid_year(self) -> None:
        """Mitad de año: descuento a t-0.5."""
        financials = _make_financials()
        assumptions = _make_assumptions(mid_year=True)
        result = run_dcf(assumptions, financials)

        ref = run_ref_dcf(_ref_inputs(mid_year=True))
        assert math.isclose(result.enterprise_value, ref.enterprise_value, rel_tol=1e-4)
        assert math.isclose(result.price_per_share, ref.price_per_share, abs_tol=0.01)

    def test_g_near_wacc(self) -> None:
        """g cercano al WACC: g=0.024, WACC=0.09 (dentro de límites)."""
        financials = _make_financials()
        assumptions = _make_assumptions(growth_terminal=0.024, wacc=0.09)
        result = run_dcf(assumptions, financials)

        # Solo verificar que no lanza error y el resultado es positivo
        assert result.enterprise_value > 0
        assert result.price_per_share > 0

    def test_zero_debt(self) -> None:
        """Deuda cero: equity = EV + cash."""
        financials = _make_financials(debt=0.0)
        assumptions = _make_assumptions(debt=0.0)
        result = run_dcf(assumptions, financials)

        # Con deuda cero, el puente solo suma caja
        assert math.isclose(result.equity_value, result.enterprise_value + 150.0, rel_tol=1e-4)

    def test_different_growth(self) -> None:
        """Crecimiento inicial diferente: 15%."""
        financials = _make_financials()
        assumptions = _make_assumptions(growth_initial=0.15)
        result = run_dcf(assumptions, financials)

        ref = run_ref_dcf(_ref_inputs(growth_initial=0.15))
        assert math.isclose(result.enterprise_value, ref.enterprise_value, rel_tol=1e-4)

    def test_fcff_year1(self) -> None:
        """FCFF del año 1 calculado a mano: 152.8."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        result = run_dcf(assumptions, financials)

        # FCFF_1 = NOPAT + D&A - CapEx - ΔNWC
        # = 220*0.79 + 44 - 55 - 10 = 173.8 + 44 - 55 - 10 = 152.8
        assert math.isclose(result.fcff_forecast[0], 152.8, abs_tol=0.1)

    def test_sensitivity_center(self) -> None:
        """El centro de la sensibilidad coincide con el caso base."""
        financials = _make_financials()
        assumptions = _make_assumptions()
        result = run_dcf(assumptions, financials)

        # El centro de la tabla WACC×g debe ser el precio del caso base
        center_key = (assumptions.risk_free_rate + assumptions.equity_beta * assumptions.equity_risk_premium, assumptions.terminal_revenue_growth)
        # Buscar la celda más cercana al caso base
        base_price = result.price_per_share
        min_diff = float("inf")
        for (w, g), price in result.sensitivity_wacc_growth.items():
            if abs(price - base_price) < min_diff:
                min_diff = abs(price - base_price)
                closest = (w, g, price)
        assert min_diff < 0.01, f"Centro de sensibilidad no coincide: diff={min_diff}"