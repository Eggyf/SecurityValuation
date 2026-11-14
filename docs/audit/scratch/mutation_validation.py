"""Script de mutación para verificar que las validaciones saltan.

No modifica código de la app. Ejecutar con:
    uv run python docs/audit/scratch/mutation_validation.py
"""
from datetime import date

from dcf_app.models.fact import Fact, Scale, SourceKind, SourceRef
from dcf_app.models.financials import BalanceSheet, CashFlowStatement, FinancialStatements, IncomeStatement
from dcf_app.validation import has_errors, validate_all


def _src():
    return SourceRef(kind=SourceKind.IXBRL, concept="us-gaap:Revenues")


def _fact(value, scale=Scale.MILLIONS):
    return Fact(value=value, unit="USD", scale=scale, period_end=date(2024, 12, 31), source=_src())


def make():
    income = IncomeStatement(
        fiscal_year=2024, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31),
        revenue=_fact(1000.0), cogs=_fact(600.0), gross_profit=_fact(400.0),
    )
    balance = BalanceSheet(
        fiscal_year=2024, period_end=date(2024, 12, 31),
        total_assets=_fact(500.0), total_liabilities=_fact(300.0), total_equity=_fact(200.0),
    )
    cf = CashFlowStatement(
        fiscal_year=2024, period_start=date(2024, 1, 1), period_end=date(2024, 12, 31),
        cfo=_fact(100.0),
    )
    return FinancialStatements(company_name="Test", income_statements=[income],
                              balance_sheets=[balance], cash_flow_statements=[cf])


fs = make()
# Mutación 1: activos +2%
fs.balance_sheets[0].total_assets = _fact(510.0)
res = validate_all(fs)
print("Mut1 activos+2%:", [(r.name, r.status) for r in res])
assert has_errors(res), "ERROR no saltó con activos +2%"

# Mutación 2: ingresos x1000 en un año (escala)
fs2 = make()
fs2.income_statements[0].revenue = _fact(1000000.0, Scale.UNITS)
res2 = validate_all(fs2)
print("Mut2 escala:", [(r.name, r.status) for r in res2])

# Mutación 3: gross profit erróneo
fs3 = make()
fs3.income_statements[0].gross_profit = _fact(500.0)
res3 = validate_all(fs3)
print("Mut3 gross profit:", [(r.name, r.status) for r in res3])
assert any(r.name == "gross_profit" and r.status.value == "warning" for r in res3)
print("OK")
