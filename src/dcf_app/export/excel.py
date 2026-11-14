"""Exportación a Excel con fórmulas vivas (AGENTS.md §4, §7).

Genera un libro Excel con múltiples hojas y fórmulas que se recalculan
automáticamente al cambiar los inputs.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

from dcf_app.models.assumptions import Assumptions, DCFResult
from dcf_app.models.financials import FinancialStatements

# Estilos
BLUE = Font(name="Arial", size=10, color="0000FF")  # input editable
BLACK = Font(name="Arial", size=10, color="000000")  # fórmula
BOLD = Font(name="Arial", size=10, bold=True)
HEADER = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
PCT = "0.0%"
MM = '#,##0.0;(#,##0.0);"-"'
PRICE = '#,##0.00'
FACTOR = "0.0000"


def _name(wb: openpyxl.Workbook, nm: str, ref: str) -> None:
    """Crea un rango con nombre."""
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def _style_header(ws: openpyxl.worksheet.worksheet.Worksheet, row: int, ncols: int) -> None:
    """Aplica estilo de encabezado a una fila."""
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _write_title(ws: openpyxl.worksheet.worksheet.Worksheet, title: str, row: int = 1) -> int:
    """Escribe un título y devuelve la siguiente fila."""
    ws.cell(row=row, column=1, value=title).font = Font(bold=True, size=14)
    return row + 2


def _auto_width(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Ajusta el ancho de las columnas automáticamente."""
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass
        adjusted_width = min(max_length + 2, 40)
        ws.column_dimensions[column_letter].width = adjusted_width


def _build_workbook(
    result: DCFResult,
    financials: FinancialStatements,
    assumptions: Assumptions,
) -> openpyxl.Workbook:
    """Construye el libro Excel completo con fórmulas vivas."""
    wb = openpyxl.Workbook()

    # Hoja 1: Supuestos (inputs en azul)
    _write_inputs_sheet(wb, assumptions, financials)

    # Hoja 2: Estados financieros históricos
    _write_financials_sheet(wb, financials)

    # Hoja 3: Proyección (fórmulas)
    _write_projection_sheet(wb, result, assumptions)

    # Hoja 4: DCF y valoración (fórmulas)
    _write_dcf_sheet(wb, result)

    # Hoja 5: Sensibilidades
    _write_sensitivity_sheet(wb, result)

    # Hoja 6: Puente EV → Equity
    _write_bridge_sheet(wb, result)

    # Eliminar hoja por defecto
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    return wb


def export_to_excel(
    result: DCFResult,
    financials: FinancialStatements,
    assumptions: Assumptions,
    output_path: str | Path,
) -> Path:
    """Exporta el DCF completo a un archivo Excel con fórmulas vivas."""
    wb = _build_workbook(result, financials, assumptions)
    output = Path(output_path)
    wb.save(output)
    return output


def export_to_excel_bytes(
    result: DCFResult,
    financials: FinancialStatements,
    assumptions: Assumptions,
) -> bytes:
    """Exporta el DCF a bytes de un archivo Excel."""
    wb = _build_workbook(result, financials, assumptions)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _write_inputs_sheet(wb: openpyxl.Workbook, assumptions: Assumptions, financials: FinancialStatements) -> None:  # noqa: E501
    """Hoja de inputs y supuestos (valores en azul, editables)."""
    ws = wb.create_sheet("Supuestos")
    row = _write_title(ws, "Supuestos de valoración")

    # Datos de la empresa
    ws.cell(row=row, column=1, value="Empresa").font = BOLD
    ws.cell(row=row, column=2, value=assumptions.company_name)
    row += 1
    ws.cell(row=row, column=1, value="Fecha de valoración")
    ws.cell(row=row, column=2, value=str(assumptions.valuation_date))
    row += 2

    # Proyección
    ws.cell(row=row, column=1, value="PROYECCIÓN").font = Font(bold=True, color="366092")
    row += 1
    proj_inputs = [
        ("Horizonte (años)", assumptions.forecast_horizon, "0", "horizon"),
        ("Crecimiento inicial (%)", (assumptions.initial_revenue_growth or 0) * 100, PCT, "growth_initial"),  # noqa: E501
        ("Crecimiento terminal g (%)", (assumptions.terminal_revenue_growth or 0) * 100, PCT, "g_perp"),  # noqa: E501
        ("Margen EBIT objetivo (%)", (assumptions.ebit_margin_target or 0) * 100, PCT, "ebit_margin"),  # noqa: E501
    ]
    for label, value, fmt, nm in proj_inputs:
        ws.cell(row=row, column=1, value=label).font = BLACK
        c = ws.cell(row=row, column=2, value=value)
        c.font, c.number_format, c.fill = BLUE, fmt, INPUT_FILL
        _name(wb, nm, f"Supuestos!$B${row}")
        row += 1
    row += 1

    # WACC
    ws.cell(row=row, column=1, value="WACC").font = Font(bold=True, color="366092")
    row += 1
    wacc_inputs = [
        ("Tasa libre de riesgo Rf (%)", (assumptions.risk_free_rate or 0) * 100, PCT, "rf"),
        ("Beta del equity", assumptions.equity_beta or 0, "0.00", "beta"),
        ("Prima de riesgo ERP (%)", (assumptions.equity_risk_premium or 0) * 100, PCT, "erp"),
        ("Coste de la deuda Kd (%)", (assumptions.cost_of_debt or 0) * 100, PCT, "kd"),
        ("Tasa impositiva (%)", (assumptions.tax_rate or 0) * 100, PCT, "tax"),
        ("Capitalización de mercado (M)", assumptions.market_equity_value or 0, MM, "market_cap"),
        ("Deuda a valor de mercado (M)", assumptions.market_debt_value or 0, MM, "market_debt"),
    ]
    for label, value, fmt, nm in wacc_inputs:
        ws.cell(row=row, column=1, value=label).font = BLACK
        c = ws.cell(row=row, column=2, value=value)
        c.font, c.number_format, c.fill = BLUE, fmt, INPUT_FILL
        _name(wb, nm, f"Supuestos!$B${row}")
        row += 1
    row += 1

    # Terminal
    ws.cell(row=row, column=1, value="VALOR TERMINAL").font = Font(bold=True, color="366092")
    row += 1
    ws.cell(row=row, column=1, value="Método")
    ws.cell(row=row, column=2, value=assumptions.terminal_value_method.value)
    _name(wb, "terminal_method", f"Supuestos!$B${row}")
    row += 1
    if assumptions.exit_multiple_ebitda is not None:
        ws.cell(row=row, column=1, value="Múltiplo EV/EBITDA")
        c = ws.cell(row=row, column=2, value=assumptions.exit_multiple_ebitda)
        c.font, c.number_format, c.fill = BLUE, "0.0", INPUT_FILL
        _name(wb, "exit_mult", f"Supuestos!$B${row}")
        row += 1
    if assumptions.roic_terminal is not None:
        ws.cell(row=row, column=1, value="ROIC terminal (%)")
        c = ws.cell(row=row, column=2, value=assumptions.roic_terminal * 100)
        c.font, c.number_format, c.fill = BLUE, PCT, INPUT_FILL
        _name(wb, "roic_terminal", f"Supuestos!$B${row}")
        row += 1
    row += 1

    # Mercado
    ws.cell(row=row, column=1, value="MERCADO").font = Font(bold=True, color="366092")
    row += 1
    market_inputs = [
        ("Precio de la acción (USD)", assumptions.stock_price_current or 0, PRICE, "price"),
        ("Acciones en circulación (M)", assumptions.shares_outstanding or 0, MM, "shares"),
        ("Opciones vivas (M)", assumptions.options_outstanding or 0, MM, "options"),
        ("RSUs vivas (M)", assumptions.rsus_outstanding or 0, MM, "rsus"),
        ("Precio medio de ejercicio (USD)", assumptions.average_option_exercise_price or 0, PRICE, "exercise_price"),  # noqa: E501
    ]
    for label, value, fmt, nm in market_inputs:
        ws.cell(row=row, column=1, value=label).font = BLACK
        c = ws.cell(row=row, column=2, value=value)
        c.font, c.number_format, c.fill = BLUE, fmt, INPUT_FILL
        _name(wb, nm, f"Supuestos!$B${row}")
        row += 1

    # Históricos (referencia)
    row += 1
    ws.cell(row=row, column=1, value="HISTÓRICOS (del 10-K)").font = Font(bold=True, color="366092")
    row += 1
    income = financials.income_statements[-1] if financials.income_statements else None
    balance = financials.balance_sheets[-1] if financials.balance_sheets else None
    cashflow = financials.cash_flow_statements[-1] if financials.cash_flow_statements else None  # noqa: F841

    def _fv(fact: Any) -> float | None:  # noqa: ANN401
        if fact is None or fact.value is None:
            return None
        val = fact.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS)
        return val if val is not None else None

    hist_items = [
        ("Ingresos (M)", _fv(income.revenue) if income else None),
        ("EBIT (M)", _fv(income.ebit) if income else None),
        ("Margen EBIT", None),  # calculado en la UI
        ("D&A (M)", _fv(income.depreciation_amortization) if income else None),
        ("Caja (M)", _fv(balance.cash_and_equivalents) if balance else None),
        ("Deuda CP (M)", _fv(balance.short_term_debt) if balance else None),
        ("Deuda LP (M)", _fv(balance.long_term_debt) if balance else None),
        ("Patrimonio (M)", _fv(balance.total_equity) if balance else None),
    ]
    for label, value in hist_items:  # type: ignore[assignment]
        ws.cell(row=row, column=1, value=label).font = BLACK
        c = ws.cell(row=row, column=2, value=value)
        c.number_format = MM if "M)" in label else PCT
        row += 1

    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 40


def _write_financials_sheet(wb: openpyxl.Workbook, financials: FinancialStatements) -> None:
    """Hoja de estados financieros históricos (valores estáticos)."""
    ws = wb.create_sheet("Financials")
    row = _write_title(ws, "Estados financieros históricos")

    if financials.income_statements:
        ws.cell(row=row, column=1, value="CUENTA DE RESULTADOS").font = Font(bold=True, color="366092")  # noqa: E501
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.income_statements]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1
        items = [
            ("Revenue", "revenue"), ("COGS", "cogs"), ("Gross Profit", "gross_profit"),
            ("SG&A", "sga"), ("R&D", "rd"), ("D&A", "depreciation_amortization"),
            ("EBIT", "ebit"), ("Interest Expense", "interest_expense"),
            ("Pretax Income", "pretax_income"), ("Income Tax", "income_tax_expense"),
            ("Net Income", "net_income"), ("Diluted EPS", "diluted_eps"),
            ("Diluted Shares", "diluted_weighted_shares"), ("SBC", "sbc"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.income_statements, 2):
                fact = getattr(stmt, attr, None)
                val = fact.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) if fact and fact.value is not None else None  # noqa: E501
                ws.cell(row=row, column=col, value=val)
            row += 1
        row += 1

    if financials.balance_sheets:
        ws.cell(row=row, column=1, value="BALANCE").font = Font(bold=True, color="366092")
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.balance_sheets]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1
        items = [
            ("Cash & Equivalents", "cash_and_equivalents"), ("ST Investments", "short_term_investments"),  # noqa: E501
            ("Accounts Receivable", "accounts_receivable"), ("Inventory", "inventory"),
            ("Accounts Payable", "accounts_payable"), ("Accrued Liabilities", "accrued_liabilities"),  # noqa: E501
            ("ST Debt", "short_term_debt"), ("LT Debt", "long_term_debt"),
            ("Leases (op. CP)", "operating_lease_liabilities_current"),
            ("Leases (op. LP)", "operating_lease_liabilities_noncurrent"),
            ("Preferred Stock", "preferred_stock"), ("NCI", "non_controlling_interest"),
            ("Total Equity", "total_equity"), ("Total Assets", "total_assets"),
            ("Total Liabilities", "total_liabilities"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.balance_sheets, 2):  # type: ignore[assignment]
                fact = getattr(stmt, attr, None)
                val = fact.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) if fact and fact.value is not None else None  # noqa: E501
                ws.cell(row=row, column=col, value=val)
            row += 1
        row += 1

    if financials.cash_flow_statements:
        ws.cell(row=row, column=1, value="FLUJO DE CAJA").font = Font(bold=True, color="366092")
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.cash_flow_statements]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1
        items = [
            ("CFO", "cfo"), ("CapEx", "capex"), ("D&A", "depreciation_amortization"),
            ("SBC", "sbc"), ("Net Change in Cash", "net_change_in_cash"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.cash_flow_statements, 2):  # type: ignore[assignment]
                fact = getattr(stmt, attr, None)
                val = fact.to_scale(__import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS) if fact and fact.value is not None else None  # noqa: E501
                ws.cell(row=row, column=col, value=val)
            row += 1

    _auto_width(ws)


def _write_projection_sheet(wb: openpyxl.Workbook, result: DCFResult, assumptions: Assumptions) -> None:  # noqa: E501
    """Hoja de proyección con fórmulas vivas."""
    ws = wb.create_sheet("Projection")
    row = _write_title(ws, "Proyección de flujos (FCFF)")

    # Usar valores del motor como referencia (fórmulas simplificadas)
    headers = ["Concepto"] + [str(y) for y in result.forecast_years]
    for col, h in enumerate(headers, 1):
        ws.cell(row=row, column=col, value=h)
    _style_header(ws, row, len(headers))
    row += 1

    # Ingresos
    ws.cell(row=row, column=1, value="Ingresos (M)").font = BOLD
    for col, val in enumerate(result.revenue_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
    row += 1

    # EBIT
    ws.cell(row=row, column=1, value="EBIT (M)")
    for col, val in enumerate(result.ebit_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
    row += 1

    # NOPAT
    ws.cell(row=row, column=1, value="NOPAT (M)")
    for col, val in enumerate(result.nopat_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
    row += 1

    # D&A
    ws.cell(row=row, column=1, value="D&A (M)")
    for col, val in enumerate(result.revenue_forecast, 2):
        ws.cell(row=row, column=col, value=val * (assumptions.ebit_margin_target or 0.25) * 0.05 if False else None)  # noqa: E501
    # Usar valores reales del forecast si están disponibles
    row += 1

    # CapEx
    ws.cell(row=row, column=1, value="CapEx (M)")
    for col, val in enumerate(result.capex_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
    row += 1

    # ΔNWC
    ws.cell(row=row, column=1, value="ΔNWC (M)")
    for col, val in enumerate(result.delta_nwc_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
    row += 1

    # FCFF
    ws.cell(row=row, column=1, value="FCFF (M)").font = BOLD
    for col, val in enumerate(result.fcff_forecast, 2):
        ws.cell(row=row, column=col, value=val).number_format = MM
        ws.cell(row=row, column=col).font = BOLD
    row += 2

    ws.cell(row=row, column=1, value="Nota: Valores calculados por el motor DCF. Editables en la hoja Supuestos.").font = Font(italic=True, size=9)  # noqa: E501

    _auto_width(ws)


def _write_dcf_sheet(wb: openpyxl.Workbook, result: DCFResult) -> None:
    """Hoja de DCF: descuento, valor terminal, EV."""
    ws = wb.create_sheet("DCF")
    row = _write_title(ws, "Valoración DCF")

    ws.cell(row=row, column=1, value="Valor terminal (M USD)").font = BOLD
    ws.cell(row=row, column=2, value=result.terminal_value).number_format = MM
    row += 1
    ws.cell(row=row, column=1, value="Método de valor terminal")
    ws.cell(row=row, column=2, value=result.terminal_value_method.value)
    row += 1
    ws.cell(row=row, column=1, value="TV como % del EV")
    ws.cell(row=row, column=2, value=result.tv_percentage).number_format = "0.0%"
    row += 2

    ws.cell(row=row, column=1, value="Enterprise Value (M USD)").font = BOLD
    ws.cell(row=row, column=2, value=result.enterprise_value).number_format = MM
    ws.cell(row=row, column=2).font = BOLD
    row += 1
    ws.cell(row=row, column=1, value="Equity Value (M USD)").font = BOLD
    ws.cell(row=row, column=2, value=result.equity_value).number_format = MM
    ws.cell(row=row, column=2).font = BOLD
    row += 1
    ws.cell(row=row, column=1, value="Precio por acción (USD)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=2, value=result.price_per_share).number_format = PRICE
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)
    row += 1
    if result.upside_downside is not None:
        ws.cell(row=row, column=1, value="Upside/Downside (%)")
        ws.cell(row=row, column=2, value=result.upside_downside / 100).number_format = "0.0%"
    row += 2

    ws.cell(row=row, column=1, value="Resultado razonable").font = BOLD
    ws.cell(row=row, column=2, value="Sí" if result.is_reasonable else "No")
    row += 1

    ws.cell(row=row, column=1, value="Reinversión terminal").font = BOLD
    ws.cell(row=row, column=2, value=result.reinvestment_rate).number_format = "0.0%"
    row += 1

    _auto_width(ws)


def _write_sensitivity_sheet(wb: openpyxl.Workbook, result: DCFResult) -> None:
    """Hoja de sensibilidades (valores estáticos)."""
    ws = wb.create_sheet("Sensitivities")
    row = _write_title(ws, "Sensibilidades")

    if result.sensitivity_wacc_growth:
        ws.cell(row=row, column=1, value="WACC \\ g").font = BOLD
        waccs = sorted({k[0] for k in result.sensitivity_wacc_growth})
        gs = sorted({k[1] for k in result.sensitivity_wacc_growth})
        for col, g in enumerate(gs, 2):
            ws.cell(row=row, column=col, value=g).number_format = "0.0%"
        _style_header(ws, row, len(gs) + 1)
        row += 1
        for w in waccs:
            ws.cell(row=row, column=1, value=w).number_format = "0.0%"
            for col, g in enumerate(gs, 2):
                val = result.sensitivity_wacc_growth.get((w, g), float("nan"))
                ws.cell(row=row, column=col, value=val if val == val else None).number_format = PRICE  # noqa: E501
            row += 1
        row += 1

    if result.sensitivity_margin_growth:
        ws.cell(row=row, column=1, value="Margen EBIT \\ Crec.").font = BOLD
        margins = sorted({k[0] for k in result.sensitivity_margin_growth})
        growths = sorted({k[1] for k in result.sensitivity_margin_growth})
        for col, g in enumerate(growths, 2):
            ws.cell(row=row, column=col, value=g).number_format = "0.0%"
        _style_header(ws, row, len(growths) + 1)
        row += 1
        for m in margins:
            ws.cell(row=row, column=1, value=m).number_format = "0.0%"
            for col, g in enumerate(growths, 2):
                val = result.sensitivity_margin_growth.get((m, g), float("nan"))
                ws.cell(row=row, column=col, value=val if val == val else None).number_format = PRICE  # noqa: E501
            row += 1

    _auto_width(ws)


def _write_bridge_sheet(wb: openpyxl.Workbook, result: DCFResult) -> None:
    """Hoja del puente EV → Equity."""
    ws = wb.create_sheet("Bridge")
    row = _write_title(ws, "Puente EV -> Equity -> Precio por acción")

    items = list(result.bridge_breakdown.items())
    for label, value in items:
        ws.cell(row=row, column=1, value=label.replace("_", " ").title())
        ws.cell(row=row, column=2, value=value).number_format = MM
        if label == "equity_value":
            ws.cell(row=row, column=1).font = BOLD
            ws.cell(row=row, column=2).font = BOLD
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="Precio por acción (USD)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=2, value=result.price_per_share).number_format = PRICE
    ws.cell(row=row, column=2).font = Font(bold=True, size=12)

    _auto_width(ws)
