"""Tests de :mod:`dcf_app.analysis.quality_scores`."""

from __future__ import annotations

import math

from dcf_app.analysis.quality_scores import (
    BeneishYear,
    YearData,
    altman_z_score,
    beneish_m_score,
    earnings_quality,
    financial_ratios,
    is_financial_company,
    piotroski_f_score,
)


class TestPiotroski:
    """Tests para Piotroski F-Score."""

    def test_all_improving(self) -> None:
        """Un año que mejora en todo da 9."""
        prev = YearData(
            net_income=50, cfo=60, total_assets=1000, long_term_debt=300,
            current_assets=400, current_liabilities=300, shares_outstanding=100,
            revenue=800, gross_profit=300,
        )
        cur = YearData(
            net_income=100, cfo=130, total_assets=1050, long_term_debt=250,
            current_assets=450, current_liabilities=300, shares_outstanding=100,
            revenue=950, gross_profit=400,
        )
        result = piotroski_f_score(cur, prev, prev_prev_total_assets=950)
        assert result.value == 9.0
        assert result.missing == []

    def test_all_declining(self) -> None:
        """Un año que empeora en todo da 0."""
        prev = YearData(
            net_income=100, cfo=130, total_assets=1000, long_term_debt=200,
            current_assets=500, current_liabilities=200, shares_outstanding=100,
            revenue=950, gross_profit=400,
        )
        cur = YearData(
            net_income=-10, cfo=-50, total_assets=900, long_term_debt=300,
            current_assets=400, current_liabilities=300, shares_outstanding=110,
            revenue=800, gross_profit=300,
        )
        result = piotroski_f_score(cur, prev, prev_prev_total_assets=1000)
        assert result.value == 0.0

    def test_missing_data(self) -> None:
        """Datos faltantes → None con lista de missing."""
        cur = YearData(net_income=100)
        prev = YearData(net_income=50)
        result = piotroski_f_score(cur, prev, prev_prev_total_assets=None)
        assert result.value is None
        assert len(result.missing) > 0

    def test_components_sum(self) -> None:
        """El desglose tiene 9 componentes."""
        prev = YearData(
            net_income=50, cfo=60, total_assets=1000, long_term_debt=300,
            current_assets=400, current_liabilities=300, shares_outstanding=100,
            revenue=800, gross_profit=300,
        )
        cur = YearData(
            net_income=100, cfo=130, total_assets=1050, long_term_debt=250,
            current_assets=450, current_liabilities=300, shares_outstanding=100,
            revenue=950, gross_profit=400,
        )
        result = piotroski_f_score(cur, prev, prev_prev_total_assets=950)
        assert len(result.components) == 9


class TestAltman:
    """Tests para Altman Z-Score."""

    def test_zprime_known_value(self) -> None:
        """Altman Z' con valores simples."""
        result = altman_z_score(
            "Zprime",
            working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        expected = 0.717 * 0.2 + 0.847 * 0.3 + 3.107 * 0.1 + 0.420 * 0.5 + 0.998 * 1.0
        assert math.isclose(result.value, expected, abs_tol=1e-9)

    def test_z_variant(self) -> None:
        """Altman Z (cotizada manufacturera)."""
        result = altman_z_score(
            "Z",
            working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        expected = 1.2 * 0.2 + 1.4 * 0.3 + 3.3 * 0.1 + 0.6 * 0.5 + 1.0 * 1.0
        assert math.isclose(result.value, expected, abs_tol=1e-9)

    def test_zdoubleprime_variant(self) -> None:
        """Altman Z'' (no manufacturera)."""
        result = altman_z_score(
            "Zdoubleprime",
            working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        expected = 6.56 * 0.2 + 3.26 * 0.3 + 6.72 * 0.1 + 1.05 * 0.5
        assert math.isclose(result.value, expected, abs_tol=1e-9)

    def test_missing_data(self) -> None:
        """Datos faltantes → None."""
        result = altman_z_score(
            "Z", working_capital=None, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        assert result.value is None
        assert "working_capital" in result.missing

    def test_unknown_variant(self) -> None:
        """Variante desconocida → None."""
        result = altman_z_score(
            "X", working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        assert result.value is None

    def test_zone_classification(self) -> None:
        """Clasificación de zona."""
        result = altman_z_score(
            "Z", working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        assert result.components["zone"] in ("distress", "grey", "safe")

    def test_components_sum(self) -> None:
        """Los componentes X1-X5 están presentes."""
        result = altman_z_score(
            "Z", working_capital=20, retained_earnings=30, ebit=10,
            equity=50, sales=100, total_assets=100, total_liabilities=100,
        )
        assert "X1" in result.components
        assert "X5" in result.components


class TestBeneish:
    """Tests para Beneish M-Score."""

    def test_identical_years(self) -> None:
        """Dos años idénticos dan -2.48."""
        y = BeneishYear(
            receivables=100, revenue=1000, cogs=600, current_assets=500,
            ppe_net=400, total_assets=1200, depreciation=50, sga=150,
            current_liabilities=300, long_term_debt=200,
            net_income_cont_ops=80, cfo=80,
        )
        result = beneish_m_score(y, y)
        expected = -4.84 + 0.920 + 0.528 + 0.404 + 0.892 + 0.115 - 0.172 + 4.679 * 0 - 0.327
        assert math.isclose(result.value, expected, abs_tol=1e-9)

    def test_no_flag_for_identical(self) -> None:
        """Dos años idénticos no activan la alerta."""
        y = BeneishYear(
            receivables=100, revenue=1000, cogs=600, current_assets=500,
            ppe_net=400, total_assets=1200, depreciation=50, sga=150,
            current_liabilities=300, long_term_debt=200,
            net_income_cont_ops=80, cfo=80,
        )
        result = beneish_m_score(y, y)
        assert result.value is not None
        assert result.value <= -1.78  # No flag

    def test_missing_data(self) -> None:
        """Datos faltantes → None."""
        y = BeneishYear(receivables=100, revenue=1000)
        result = beneish_m_score(y, y)
        assert result.value is None
        assert len(result.missing) > 0

    def test_components_present(self) -> None:
        """Los 8 componentes están presentes."""
        y = BeneishYear(
            receivables=100, revenue=1000, cogs=600, current_assets=500,
            ppe_net=400, total_assets=1200, depreciation=50, sga=150,
            current_liabilities=300, long_term_debt=200,
            net_income_cont_ops=80, cfo=80,
        )
        result = beneish_m_score(y, y)
        assert "DSRI" in result.components
        assert "TATA" in result.components
        assert len(result.components) == 8


class TestEarningsQuality:
    """Tests para calidad de beneficios."""

    def test_basic(self) -> None:
        """Calidad de beneficios básica."""
        result = earnings_quality(net_income=100, cfo=120, avg_total_assets=1000)
        assert result.value is not None
        assert math.isclose(result.value, 1.2, abs_tol=1e-9)
        assert "accruals_ratio" in result.components

    def test_missing_data(self) -> None:
        """Datos faltantes → None."""
        result = earnings_quality(net_income=None, cfo=120, avg_total_assets=1000)
        assert result.value is None
        assert "net_income" in result.missing


class TestFinancialRatios:
    """Tests para ratios financieros."""

    def test_basic_ratios(self) -> None:
        """Ratios básicos se calculan."""
        data = YearData(
            revenue=1000, cogs=600, gross_profit=400, ebit=250,
            net_income=200, total_assets=2000, total_equity=1200,
            accounts_receivable=100, inventory=150, accounts_payable=80,
            interest_expense=20, depreciation=50,
            long_term_debt=300, current_liabilities=200,
        )
        ratios = financial_ratios(data)
        assert ratios["gross_margin"] is not None
        assert math.isclose(ratios["gross_margin"], 0.4, abs_tol=1e-9)
        assert ratios["ebit_margin"] is not None
        assert math.isclose(ratios["ebit_margin"], 0.25, abs_tol=1e-9)
        assert ratios["roe"] is not None
        assert ratios["dso"] is not None
        assert ratios["dio"] is not None
        assert ratios["dpo"] is not None

    def test_dso_calculation(self) -> None:
        """DSO = AR / Revenue * 365."""
        data = YearData(revenue=1000, accounts_receivable=100)
        ratios = financial_ratios(data)
        assert math.isclose(ratios["dso"], 36.5, abs_tol=1e-9)

    def test_empty_data(self) -> None:
        """Sin datos, los ratios son None."""
        data = YearData()
        ratios = financial_ratios(data)
        assert ratios["gross_margin"] is None
        assert ratios["roe"] is None


class TestIsFinancial:
    """Tests para detección de empresas financieras."""

    def test_financial_sector(self) -> None:
        """Sector financiero → True."""
        assert is_financial_company(sector="Financial Services") is True

    def test_financial_sic(self) -> None:
        """SIC financiero → True."""
        assert is_financial_company(sic_code="6020") is True

    def test_non_financial(self) -> None:
        """Empresa no financiera → False."""
        assert is_financial_company(sic_code="3571", sector="Technology") is False
