"""Recalcula un .xlsx con LibreOffice y lee los valores calculados.

openpyxl guarda fórmulas SIN valores en caché: para comprobar que calculan bien
hay que recalcular. Uso: python verify_recalc.py archivo.xlsx
Requiere `soffice` en el PATH.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile

from openpyxl import load_workbook


def recalc(path: str) -> dict:
    if not shutil.which("soffice"):
        raise RuntimeError("soffice no está disponible; no se puede recalcular")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "xlsx", "--outdir", tmp, path],
            check=True, capture_output=True, timeout=120,
        )
        wb = load_workbook(pathlib.Path(tmp) / pathlib.Path(path).name, data_only=True)
        return {ws.title: {c.coordinate: c.value for row in ws.iter_rows() for c in row
                           if c.value is not None} for ws in wb}


def find_errors(values: dict) -> list[str]:
    bad = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!")
    return [f"{sh}!{cell}={v}" for sh, cells in values.items()
            for cell, v in cells.items() if isinstance(v, str) and v in bad]


if __name__ == "__main__":
    vals = recalc(sys.argv[1])
    errs = find_errors(vals)
    print("errores:", errs or "ninguno")
    v = vals.get("Valoracion", {})
    for k in ("B3", "B5", "B6", "B9", "B11", "B12", "B13", "B14"):
        print(k, v.get(k))
