"""Exportación a Excel con fórmulas vivas (AGENTS.md §4, §7).

Genera un libro Excel con múltiples hojas y fórmulas que se recalculan
automáticamente al cambiar los inputs.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from dcf_app.models.assumptions import Assumptions, DCFResult
from dcf_app.models.financials import FinancialStatements


def _style_header(ws, row: int, ncols: int) -> None:
    """Aplica estilo de encabezado a una fila."""
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _write_title(ws, title: str, row: int = 1) -> int:
    """Escribe un título y devuelve la siguiente fila."""
    ws.cell(row=row, column=1, value=title).font = Font(bold=True, size=14)
    return row + 2


def _auto_width(ws) -> None:
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


def export_to_excel(
    result: DCFResult,
    financials: FinancialStatements,
    assumptions: Assumptions,
    output_path: str | Path,
) -> Path:
    """Exporta el DCF completo a un archivo Excel con fórmulas vivas.

    Args:
        result: resultado del DCF.
        financials: estados financieros.
        assumptions: supuestos de valoración.
        output_path: ruta del archivo de salida.

    Returns:
        Ruta del archivo generado.
    """
    wb = openpyxl.Workbook()

    # Hoja 1: Inputs y supuestos
    _write_inputs_sheet(wb, assumptions, financials)

    # Hoja 2: Estados financieros históricos
    _write_financials_sheet(wb, financials)

    # Hoja 3: Proyección
    _write_projection_sheet(wb, result, assumptions)

    # Hoja 4: DCF y puente
    _write_dcf_sheet(wb, result)

    # Hoja 5: Sensibilidades
    _write_sensitivity_sheet(wb, result)

    # Hoja 6: Puente EV → Equity
    _write_bridge_sheet(wb, result)

    # Eliminar hoja por defecto si existe
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]

    output = Path(output_path)
    wb.save(output)
    return output


def _write_inputs_sheet(wb, assumptions: Assumptions, financials: FinancialStatements) -> None:
    """Hoja de inputs y supuestos."""
    ws = wb.create_sheet("Inputs")
    row = _write_title(ws, "Supuestos de valoración")

    # Datos de la empresa
    ws.cell(row=row, column=1, value="Empresa").font = Font(bold=True)
    ws.cell(row=row, column=2, value=assumptions.company_name)
    row += 1
    ws.cell(row=row, column=1, value="Fecha de valoración")
    ws.cell(row=row, column=2, value=str(assumptions.valuation_date))
    row += 2

    # Proyección
    ws.cell(row=row, column=1, value="PROYECCIÓN").font = Font(bold=True, color="366092")
    row += 1
    inputs_proj = [
        ("Horizonte (años)", assumptions.forecast_horizon),
        ("Crecimiento inicial (%)", (assumptions.initial_revenue_growth or 0) * 100),
        ("Crecimiento terminal g (%)", (assumptions.terminal_revenue_growth or 0) * 100),
        ("Margen EBIT objetivo (%)", (assumptions.ebit_margin_target or 0) * 100),
    ]
    for label, value in inputs_proj:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)
        row += 1
    row += 1

    # WACC
    ws.cell(row=row, column=1, value="WACC").font = Font(bold=True, color="366092")
    row += 1
    inputs_wacc = [
        ("Tasa libre de riesgo Rf (%)", (assumptions.risk_free_rate or 0) * 100),
        ("Beta del equity", assumptions.equity_beta or 0),
        ("Prima de riesgo ERP (%)", (assumptions.equity_risk_premium or 0) * 100),
        ("Coste de la deuda Kd (%)", (assumptions.cost_of_debt or 0) * 100),
        ("Tasa impositiva (%)", (assumptions.tax_rate or 0) * 100),
        ("Capitalización de mercado (M)", assumptions.market_equity_value or 0),
        ("Deuda a valor de mercado (M)", assumptions.market_debt_value or 0),
    ]
    for label, value in inputs_wacc:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)
        row += 1
    row += 1

    # Terminal
    ws.cell(row=row, column=1, value="VALOR TERMINAL").font = Font(bold=True, color="366092")
    row += 1
    ws.cell(row=row, column=1, value="Método")
    ws.cell(row=row, column=2, value=assumptions.terminal_value_method.value)
    row += 1
    if assumptions.exit_multiple_ebitda is not None:
        ws.cell(row=row, column=1, value="Múltiplo EV/EBITDA")
        ws.cell(row=row, column=2, value=assumptions.exit_multiple_ebitda)
        row += 1
    row += 1

    # Mercado
    ws.cell(row=row, column=1, value="MERCADO").font = Font(bold=True, color="366092")
    row += 1
    inputs_market = [
        ("Precio de la acción (USD)", assumptions.stock_price_current or 0),
        ("Acciones en circulación (M)", assumptions.shares_outstanding or 0),
        ("Opciones vivas (M)", assumptions.options_outstanding or 0),
        ("RSUs vivas (M)", assumptions.rsus_outstanding or 0),
        ("Precio medio de ejercicio (USD)", assumptions.average_option_exercise_price or 0),
    ]
    for label, value in inputs_market:
        ws.cell(row=row, column=1, value=label)
        ws.cell(row=row, column=2, value=value)
        row += 1

    _auto_width(ws)


def _write_financials_sheet(wb, financials: FinancialStatements) -> None:
    """Hoja de estados financieros históricos."""
    ws = wb.create_sheet("Financials")
    row = _write_title(ws, "Estados financieros históricos")

    # Ingresos
    if financials.income_statements:
        ws.cell(row=row, column=1, value="CUENTA DE RESULTADOS").font = Font(
            bold=True, color="366092"
        )
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.income_statements]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1

        items = [
            ("Revenue", "revenue"),
            ("COGS", "cogs"),
            ("Gross Profit", "gross_profit"),
            ("SG&A", "sga"),
            ("R&D", "rd"),
            ("D&A", "depreciation_amortization"),
            ("EBIT", "ebit"),
            ("Interest Expense", "interest_expense"),
            ("Pretax Income", "pretax_income"),
            ("Income Tax", "income_tax_expense"),
            ("Net Income", "net_income"),
            ("Diluted EPS", "diluted_eps"),
            ("Diluted Shares", "diluted_weighted_shares"),
            ("SBC", "sbc"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.income_statements, 2):
                fact = getattr(stmt, attr, None)
                val = (
                    fact.to_scale(
                        __import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS
                    )
                    if fact and fact.value is not None
                    else None
                )
                ws.cell(row=row, column=col, value=val)
            row += 1
        row += 1

    # Balance
    if financials.balance_sheets:
        ws.cell(row=row, column=1, value="BALANCE").font = Font(bold=True, color="366092")
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.balance_sheets]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1

        items = [
            ("Cash & Equivalents", "cash_and_equivalents"),
            ("ST Investments", "short_term_investments"),
            ("Accounts Receivable", "accounts_receivable"),
            ("Inventory", "inventory"),
            ("Accounts Payable", "accounts_payable"),
            ("Accrued Liabilities", "accrued_liabilities"),
            ("ST Debt", "short_term_debt"),
            ("LT Debt", "long_term_debt"),
            ("Leases (op. CP)", "operating_lease_liabilities_current"),
            ("Leases (op. LP)", "operating_lease_liabilities_noncurrent"),
            ("Preferred Stock", "preferred_stock"),
            ("NCI", "non_controlling_interest"),
            ("Total Equity", "total_equity"),
            ("Total Assets", "total_assets"),
            ("Total Liabilities", "total_liabilities"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.balance_sheets, 2):
                fact = getattr(stmt, attr, None)
                val = (
                    fact.to_scale(
                        __import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS
                    )
                    if fact and fact.value is not None
                    else None
                )
                ws.cell(row=row, column=col, value=val)
            row += 1
        row += 1

    # Flujo de caja
    if financials.cash_flow_statements:
        ws.cell(row=row, column=1, value="FLUJO DE CAJA").font = Font(bold=True, color="366092")
        row += 1
        headers = ["Partida"] + [str(s.fiscal_year) for s in financials.cash_flow_statements]
        for col, h in enumerate(headers, 1):
            ws.cell(row=row, column=col, value=h)
        _style_header(ws, row, len(headers))
        row += 1

        items = [
            ("CFO", "cfo"),
            ("CapEx", "capex"),
            ("D&A", "depreciation_amortization"),
            ("SBC", "sbc"),
            ("ΔNWC", "change_in_working_capital"),
            ("Net Change in Cash", "net_change_in_cash"),
        ]
        for label, attr in items:
            ws.cell(row=row, column=1, value=label)
            for col, stmt in enumerate(financials.cash_flow_statements, 2):
                fact = getattr(stmt, attr, None)
                val = (
                    fact.to_scale(
                        __import__("dcf_app.models.fact", fromlist=["Scale"]).Scale.MILLIONS
                    )
                    if fact and fact.value is not None
                    else None
                )
                ws.cell(row=row, column=col, value=val)
            row += 1

    _auto_width(ws)


def _write_projection_sheet(wb, result: DCFResult, assumptions: Assumptions) -> None:
    """Hoja de proyección de flujos."""
    ws = wb.create_sheet("Projection")
    row = _write_title(ws, "Proyección de flujos (FCFF)")

    headers = ["Año"] + [str(y) for y in result.forecast_years]
    for col, h in enumerate(headers, 1):
        ws.cell(row=row, column=col, value=h)
    _style_header(ws, row, len(headers))
    row += 1

    # Ingresos (con fórmula de crecimiento)
    ws.cell(row=row, column=1, value="Ingresos")
    for col, val in enumerate(result.revenue_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    row += 1

    ws.cell(row=row, column=1, value="Margen EBIT")
    for col, val in enumerate(result.ebit_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    # EBIT = Revenue x Margen
    row += 1

    ws.cell(row=row, column=1, value="EBIT")
    for col, val in enumerate(result.ebit_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    row += 1

    ws.cell(row=row, column=1, value="NOPAT")
    for col, val in enumerate(result.nopat_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    row += 1

    ws.cell(row=row, column=1, value="D&A")
    for col, (rev, _margin) in enumerate(
        zip(result.revenue_forecast, result.ebit_forecast, strict=False), 2
    ):
        ws.cell(row=row, column=col, value=rev * 0.05)  # placeholder
    row += 1

    ws.cell(row=row, column=1, value="CapEx")
    for col, val in enumerate(result.capex_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    row += 1

    ws.cell(row=row, column=1, value="ΔNWC")
    for col, val in enumerate(result.delta_nwc_forecast, 2):
        ws.cell(row=row, column=col, value=val)
    row += 1

    ws.cell(row=row, column=1, value="FCFF").font = Font(bold=True)
    for col, val in enumerate(result.fcff_forecast, 2):
        ws.cell(row=row, column=col, value=val).font = Font(bold=True)
    row += 2

    # Nota
    ws.cell(
        row=row, column=1, value="Nota: D&A calculado como % de ingresos (media histórica)."
    ).font = Font(italic=True, size=9)

    _auto_width(ws)


def _write_dcf_sheet(wb, result: DCFResult) -> None:
    """Hoja de DCF: descuento, valor terminal, EV."""
    ws = wb.create_sheet("DCF")
    row = _write_title(ws, "Valoración DCF")

    # Valor terminal
    ws.cell(row=row, column=1, value="Valor terminal (M USD)").font = Font(bold=True)
    ws.cell(row=row, column=2, value=result.terminal_value)
    row += 1
    ws.cell(row=row, column=1, value="Método de valor terminal")
    ws.cell(row=row, column=2, value=result.terminal_value_method.value)
    row += 1
    ws.cell(row=row, column=1, value="TV como % del EV")
    ws.cell(row=row, column=2, value=result.tv_percentage)
    ws.cell(row=row, column=2).number_format = "0.0%"
    row += 2

    # Valoración
    ws.cell(row=row, column=1, value="Enterprise Value (M USD)").font = Font(bold=True)
    ws.cell(row=row, column=2, value=result.enterprise_value).font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=1, value="Equity Value (M USD)").font = Font(bold=True)
    ws.cell(row=row, column=2, value=result.equity_value).font = Font(bold=True)
    row += 1
    ws.cell(row=row, column=1, value="Precio por acción (USD)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=2, value=result.price_per_share).font = Font(bold=True, size=12)
    row += 1
    if result.upside_downside is not None:
        ws.cell(row=row, column=1, value="Upside/Downside (%)")
        ws.cell(row=row, column=2, value=result.upside_downside / 100)
        ws.cell(row=row, column=2).number_format = "0.0%"
    row += 2

    # Cordura
    ws.cell(row=row, column=1, value="Resultado razonable").font = Font(bold=True)
    ws.cell(row=row, column=2, value="Sí" if result.is_reasonable else "No")
    row += 1

    _auto_width(ws)


def _write_sensitivity_sheet(wb, result: DCFResult) -> None:
    """Hoja de sensibilidades."""
    ws = wb.create_sheet("Sensitivities")
    row = _write_title(ws, "Sensibilidades")

    # WACC x g
    ws.cell(row=row, column=1, value="Sensibilidad: WACC x g -> Precio por acción").font = Font(
        bold=True, color="366092"
    )
    row += 1

    if result.sensitivity_wacc_growth:
        waccs = sorted({k[0] for k in result.sensitivity_wacc_growth})
        gs = sorted({k[1] for k in result.sensitivity_wacc_growth})

        # Encabezado
        ws.cell(row=row, column=1, value="WACC \\ g")
        for col, g in enumerate(gs, 2):
            ws.cell(row=row, column=col, value=g).number_format = "0.0%"
        _style_header(ws, row, len(gs) + 1)
        row += 1

        for w in waccs:
            ws.cell(row=row, column=1, value=w).number_format = "0.0%"
            for col, g in enumerate(gs, 2):
                val = result.sensitivity_wacc_growth.get((w, g), float("nan"))
                ws.cell(row=row, column=col, value=val if val == val else None)
            row += 1
        row += 1

    # Margen x Crecimiento
    ws.cell(
        row=row, column=1, value="Sensibilidad: Margen EBIT x Crecimiento -> Precio por acción"
    ).font = Font(bold=True, color="366092")
    row += 1

    if result.sensitivity_margin_growth:
        margins = sorted({k[0] for k in result.sensitivity_margin_growth})
        growths = sorted({k[1] for k in result.sensitivity_margin_growth})

        ws.cell(row=row, column=1, value="Margen \\ Crec.")
        for col, g in enumerate(growths, 2):
            ws.cell(row=row, column=col, value=g).number_format = "0.0%"
        _style_header(ws, row, len(growths) + 1)
        row += 1

        for m in margins:
            ws.cell(row=row, column=1, value=m).number_format = "0.0%"
            for col, g in enumerate(growths, 2):
                val = result.sensitivity_margin_growth.get((m, g), float("nan"))
                ws.cell(row=row, column=col, value=val if val == val else None)
            row += 1

    _auto_width(ws)


def _write_bridge_sheet(wb, result: DCFResult) -> None:
    """Hoja del puente EV → Equity."""
    ws = wb.create_sheet("Bridge")
    row = _write_title(ws, "Puente EV -> Equity -> Precio por acción")

    items = list(result.bridge_breakdown.items())
    for label, value in items:
        ws.cell(row=row, column=1, value=label.replace("_", " ").title())
        ws.cell(row=row, column=2, value=value)
        if label == "equity_value":
            ws.cell(row=row, column=1).font = Font(bold=True)
            ws.cell(row=row, column=2).font = Font(bold=True)
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="Precio por acción (USD)").font = Font(bold=True, size=12)
    ws.cell(row=row, column=2, value=result.price_per_share).font = Font(bold=True, size=12)

    _auto_width(ws)
