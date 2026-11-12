"""Exporta un DCF a Excel con FÓRMULAS VIVAS (no valores pegados).

Estructura: Supuestos (inputs en azul) -> Proyeccion (fórmulas) -> Valoracion.
Los inputs son rangos con nombre; las fórmulas los usan por nombre.
Uso: python build_dcf_workbook.py salida.xlsx
"""
from __future__ import annotations

import sys

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils import get_column_letter

BLUE = Font(name="Arial", size=10, color="0000FF")        # input editable
BLACK = Font(name="Arial", size=10, color="000000")       # fórmula
GREEN = Font(name="Arial", size=10, color="008000")       # enlace a otra hoja
BOLD = Font(name="Arial", size=10, bold=True)
HEADER = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
THIN = Side(style="thin", color="999999")

PCT, MM, PRICE, FACTOR = "0.0%", '#,##0.0;(#,##0.0);"-"', '#,##0.00', "0.0000"


def name(wb: Workbook, nm: str, ref: str) -> None:
    wb.defined_names[nm] = DefinedName(nm, attr_text=ref)


def build(path: str) -> None:
    wb = Workbook()

    # ---------------------------------------------------------------- Supuestos
    s = wb.active
    s.title = "Supuestos"
    s["A1"], s["A1"].font = "Supuestos (azul = editable)", BOLD
    scalars = [  # etiqueta, valor, nombre, formato, nota/fuente
        ("Ingresos año 0 (MM USD)", 1000, "rev0", MM, "10-K, cuenta de resultados"),
        ("Margen EBIT", 0.20, "ebit_margin", PCT, "Supuesto: media histórica"),
        ("Tasa impositiva normalizada", 0.21, "tax", PCT, "Supuesto"),
        ("D&A % ingresos", 0.04, "da_pct", PCT, "Media histórica"),
        ("CapEx % ingresos", 0.05, "capex_pct", PCT, "Media histórica"),
        ("ΔNWC % de Δingresos", 0.10, "nwc_pct", PCT, "Media histórica"),
        ("WACC", 0.09, "wacc", PCT, "CAPM, ver hoja de WACC"),
        ("g perpetuo", 0.025, "g_perp", PCT, "Debe ser < WACC y ≤ Rf"),
        ("Caja e inversiones CP (MM USD)", 150, "cash", MM, "10-K, balance"),
        ("Deuda financiera (MM USD)", 400, "debt", MM, "10-K, balance"),
        ("Acciones diluidas (MM)", 100, "shares", MM, "Portada 10-K + TSM"),
    ]
    for i, (lab, val, nm, fmt, note) in enumerate(scalars, start=3):
        s.cell(i, 1, lab).font = BLACK
        c = s.cell(i, 2, val)
        c.font, c.number_format, c.fill = BLUE, fmt, INPUT_FILL
        s.cell(i, 3, note).font = Font(name="Arial", size=9, italic=True, color="666666")
        name(wb, nm, f"Supuestos!$B${i}")

    r = 3 + len(scalars) + 1
    s.cell(r, 1, "Crecimiento de ingresos por año").font = BOLD
    for k, gr in enumerate([0.10, 0.08, 0.06, 0.05, 0.04], start=1):
        s.cell(r + 1, 1 + k, f"Año {k}").font = BOLD
        c = s.cell(r + 2, 1 + k, gr)
        c.font, c.number_format, c.fill = BLUE, PCT, INPUT_FILL
    s.cell(r + 2, 1, "Crecimiento").font = BLACK
    growth_row = r + 2
    s.column_dimensions["A"].width = 34
    s.column_dimensions["C"].width = 30

    # --------------------------------------------------------------- Proyeccion
    p = wb.create_sheet("Proyeccion")
    p["A1"], p["A1"].font = "Año", HEADER
    p["B1"] = 0
    for k in range(1, 6):
        p.cell(1, 2 + k, k)
    for col in range(1, 8):
        c = p.cell(1, col)
        c.font, c.fill, c.alignment = HEADER, HEADER_FILL, Alignment(horizontal="center")
    labels = ["Año", "Crecimiento", "Ingresos", "EBIT", "NOPAT", "D&A", "CapEx",
              "ΔNWC", "FCFF", "Factor de descuento", "VA del FCFF"]
    for i, lab in enumerate(labels, start=1):
        p.cell(i, 1, lab).font = BOLD if lab in ("FCFF", "Ingresos") else BLACK
    p["B3"] = "=rev0"; p["B3"].font = GREEN; p["B3"].number_format = MM
    for k in range(1, 6):
        col = get_column_letter(2 + k)
        prev = get_column_letter(1 + k)
        cells = {
            2: (f"=Supuestos!{get_column_letter(1 + k)}{growth_row}", PCT, GREEN),
            3: (f"={prev}3*(1+{col}2)", MM, BLACK),
            4: (f"={col}3*ebit_margin", MM, BLACK),
            5: (f"={col}4*(1-tax)", MM, BLACK),
            6: (f"={col}3*da_pct", MM, BLACK),
            7: (f"={col}3*capex_pct", MM, BLACK),
            8: (f"=({col}3-{prev}3)*nwc_pct", MM, BLACK),
            9: (f"={col}5+{col}6-{col}7-{col}8", MM, BOLD),
            10: (f"=1/(1+wacc)^{col}1", FACTOR, BLACK),
            11: (f"={col}9*{col}10", MM, BLACK),
        }
        for row, (f, fmt, font) in cells.items():
            c = p.cell(row, 2 + k, f)
            c.number_format, c.font = fmt, font
    p.column_dimensions["A"].width = 22

    # ---------------------------------------------------------------- Valoracion
    v = wb.create_sheet("Valoracion")
    rows = [
        ("VA de los FCFF (años 1–5)", "=SUM(Proyeccion!C11:G11)", MM),
        ("Valor terminal (Gordon)", "=Proyeccion!G9*(1+g_perp)/(wacc-g_perp)", MM),
        ("VA del valor terminal", "=B4/(1+wacc)^Proyeccion!G1", MM),
        ("Valor de empresa (EV)", "=B3+B5", MM),
        ("+ Caja e inversiones CP", "=cash", MM),
        ("− Deuda financiera", "=-debt", MM),
        ("Valor del equity", "=B6+B7+B8", MM),
        ("Acciones diluidas (MM)", "=shares", MM),
        ("Precio por acción (USD)", "=B9/B10", PRICE),
        ("Peso del TV sobre EV", "=B5/B6", PCT),
        ("Control WACC > g", '=IF(wacc>g_perp,"OK","ERROR")', None),
        ("Aviso peso del TV", '=IF(B12>0.75,"AVISO: TV > 75 % del EV","OK")', None),
    ]
    v["A1"], v["A1"].font = "Valoración", HEADER
    v["A1"].fill = HEADER_FILL
    v["B1"].fill = HEADER_FILL
    for i, (lab, f, fmt) in enumerate(rows, start=3):
        v.cell(i, 1, lab).font = BOLD if "Precio" in lab or "EV" in lab else BLACK
        c = v.cell(i, 2, f)
        c.font = BOLD if "Precio" in lab else BLACK
        if fmt:
            c.number_format = fmt
    v.column_dimensions["A"].width = 30
    v.column_dimensions["B"].width = 26
    wb.save(path)


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "dcf.xlsx")
    print("ok")
