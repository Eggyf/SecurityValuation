"""Extracción de datos para scores de calidad desde FinancialStatements.

Convierte los estados financieros extraídos del 10-K en las estructuras
de datos que necesitan los scores (YearData, BeneishYear).
"""

from __future__ import annotations

from typing import Any

from dcf_app.analysis.quality_scores import BeneishYear, YearData
from dcf_app.models.fact import Scale as FactScale
from dcf_app.models.financials import FinancialStatements


def _fact_value(fact: Any) -> float | None:  # noqa: ANN401
    """Extrae el valor de un Fact en millones, o None si no existe."""
    if fact is None:
        return None
    val = getattr(fact, "value", None)
    if val is None:
        return None
    # Convertir a millones si tiene scale
    scale = getattr(fact, "scale", None)
    if scale is not None:
        try:
            converted = fact.to_scale(FactScale.MILLIONS)
            if converted is not None:
                return float(converted)
        except Exception:
            pass
    return float(val)


def extract_year_data(fs: FinancialStatements, index: int = -1) -> YearData:
    """Extrae YearData del ejercicio indicado (por defecto el último)."""
    if not fs.income_statements or not fs.balance_sheets:
        return YearData()

    inc = fs.income_statements[index]
    # Handle negative indices properly
    bal_idx = index if index >= 0 else len(fs.balance_sheets) + index
    bal = fs.balance_sheets[bal_idx] if 0 <= bal_idx < len(fs.balance_sheets) else None

    cf = None
    if fs.cash_flow_statements:
        cf_idx = index if index >= 0 else len(fs.cash_flow_statements) + index
        if 0 <= cf_idx < len(fs.cash_flow_statements):
            cf = fs.cash_flow_statements[cf_idx]
        else:
            cf = fs.cash_flow_statements[-1]

    if bal is None:
        return YearData(
            net_income=_fact_value(inc.net_income),
            cfo=_fact_value(cf.cfo) if cf else None,
            shares_outstanding=_fact_value(inc.diluted_weighted_shares),
            revenue=_fact_value(inc.revenue),
            gross_profit=_fact_value(inc.gross_profit),
            cogs=_fact_value(inc.cogs),
            ebit=_fact_value(inc.ebit),
            interest_expense=_fact_value(inc.interest_expense),
            depreciation=_fact_value(inc.depreciation_amortization),
            sga=_fact_value(inc.sga),
        )

    return YearData(
        net_income=_fact_value(inc.net_income),
        cfo=_fact_value(cf.cfo) if cf else None,
        total_assets=_fact_value(bal.total_assets),
        long_term_debt=_fact_value(bal.long_term_debt),
        current_assets=_fact_value(bal.accounts_receivable),  # proxy
        current_liabilities=_fact_value(bal.accounts_payable),  # proxy
        shares_outstanding=_fact_value(inc.diluted_weighted_shares),
        revenue=_fact_value(inc.revenue),
        gross_profit=_fact_value(inc.gross_profit),
        cogs=_fact_value(inc.cogs),
        ebit=_fact_value(inc.ebit),
        interest_expense=_fact_value(inc.interest_expense),
        accounts_receivable=_fact_value(bal.accounts_receivable),
        inventory=_fact_value(bal.inventory),
        accounts_payable=_fact_value(bal.accounts_payable),
        depreciation=_fact_value(inc.depreciation_amortization),
        sga=_fact_value(inc.sga),
        retained_earnings=None,  # No disponible directamente
        total_liabilities=_fact_value(bal.total_liabilities),
        current_liabilities_total=_fact_value(bal.accrued_liabilities),
    )


def extract_beneish_years(fs: FinancialStatements) -> tuple[BeneishYear, BeneishYear] | None:
    """Extrae dos BeneishYear consecutivos del 10-K.

    Returns None si no hay suficientes datos.
    """
    if len(fs.income_statements) < 2 or len(fs.balance_sheets) < 2:
        return None

    def _extract(idx: int) -> BeneishYear:
        inc = fs.income_statements[idx]
        bal = fs.balance_sheets[idx] if idx < len(fs.balance_sheets) else fs.balance_sheets[-1]
        cf = fs.cash_flow_statements[idx] if idx < len(fs.cash_flow_statements) else None

        return BeneishYear(
            receivables=_fact_value(bal.accounts_receivable),
            revenue=_fact_value(inc.revenue),
            cogs=_fact_value(inc.cogs),
            current_assets=_fact_value(bal.accounts_receivable),  # proxy
            ppe_net=None,  # No disponible directamente
            total_assets=_fact_value(bal.total_assets),
            depreciation=_fact_value(inc.depreciation_amortization),
            sga=_fact_value(inc.sga),
            current_liabilities=_fact_value(bal.accrued_liabilities),
            long_term_debt=_fact_value(bal.long_term_debt),
            net_income_cont_ops=_fact_value(inc.net_income),
            cfo=_fact_value(cf.cfo) if cf else None,
        )

    return _extract(-2), _extract(-1)


__all__ = ["extract_beneish_years", "extract_year_data"]
