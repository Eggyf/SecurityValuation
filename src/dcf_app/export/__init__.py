"""Exportación a Excel (con fórmulas vivas) y generación del informe."""

from dcf_app.export.excel import export_to_excel, export_to_excel_bytes

__all__ = ["export_to_excel", "export_to_excel_bytes"]
