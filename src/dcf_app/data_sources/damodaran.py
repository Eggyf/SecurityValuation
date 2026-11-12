"""Proveedor de datos de Damodaran (NYU Stern) (AGENTS.md §13.2).

Descarga y parsea datasets gratuitos de Aswath Damodaran:
- ERP implícita (histimpl.xls)
- Betas por industria (betas.xls)
- Márgenes por industria (margin.xls)

Cachea 30 días. Requiere conexión a internet (modo online).
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

import httpx
import pandas as pd

from dcf_app.data_sources.base import (
    DataSourceConfigError,
    DataSourceResult,
    NetworkError,
)
from dcf_app.data_sources.cache import CacheManager, CacheTTL

logger = logging.getLogger(__name__)

# URLs de Damodaran (verificadas)
DAMODARAN_BASE = "https://pages.stern.nyu.edu/~adamodar/pc/datasets"
URLS = {
    "erp": f"{DAMODARAN_BASE}/histimpl.xls",
    "betas": f"{DAMODARAN_BASE}/betas.xls",
    "margins": f"{DAMODARAN_BASE}/margin.xls",
}

warnings.filterwarnings("ignore")


class DamodaranProvider:
    """Proveedor de datos de Damodaran (NYU Stern)."""

    def __init__(self) -> None:
        """Inicializa el proveedor de Damodaran."""
        self.cache = CacheManager()

    def get_implied_erp(self) -> DataSourceResult:
        """Obtiene la ERP implícita más reciente.

        Returns:
            DataSourceResult con dict: {"erp": float, "date": str, "source": "Damodaran"}
        """
        cache_key = "Damodaran_ERP"
        cached = self.cache.get(cache_key, CacheTTL.DAMODARAN)
        if cached is not None:
            return DataSourceResult.from_provider("Damodaran", cached)

        try:
            resp = httpx.get(URLS["erp"], timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise NetworkError("Damodaran", f"Error descargando ERP: {e}") from e

        try:
            import io

            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, header=None, engine="xlrd")
        except Exception as e:
            raise NetworkError("Damodaran", f"Error parseando ERP: {e}") from e

        # Buscar la fila del año más reciente (primera columna es el año)
        erp_value = None
        erp_date = None
        for i in range(len(df)):
            val = df.iloc[i, 0]
            if pd.notna(val) and isinstance(val, (int, float)) and 2000 <= val <= 2100:  # type: ignore
                # Columna 1 (índice 1) es el ERP
                erp_col = df.iloc[i, 1]
                if pd.notna(erp_col):  # type: ignore
                    erp_value = float(erp_col)  # type: ignore
                    erp_date = str(int(val))

        if erp_value is None:
            raise NetworkError("Damodaran", "No se encontró ERP en el archivo")

        result_data = {
            "erp": erp_value,
            "date": erp_date,
            "provider": "Damodaran (NYU Stern)",
            "url": URLS["erp"],
        }
        self.cache.set(cache_key, result_data, CacheTTL.DAMODARAN, "Damodaran", URLS["erp"])
        return DataSourceResult.from_provider("Damodaran", result_data, URLS["erp"])

    def get_betas_by_industry(self) -> DataSourceResult:
        """Obtiene betas por industria.

        Returns:
            DataSourceResult con dict: {industry_name: {"beta": float, ...}}
        """
        cache_key = "Damodaran_Betas"
        cached = self.cache.get(cache_key, CacheTTL.DAMODARAN)
        if cached is not None:
            return DataSourceResult.from_provider("Damodaran", cached)

        try:
            resp = httpx.get(URLS["betas"], timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise NetworkError("Damodaran", f"Error descargando betas: {e}") from e

        try:
            import io

            df = pd.read_excel(
                io.BytesIO(resp.content),
                sheet_name="Industry Averages",
                header=None,
                engine="xlrd",
            )
        except Exception as e:
            raise NetworkError("Damodaran", f"Error parseando betas: {e}") from e

        # Encontrar la fila de encabezado
        header_row = None
        for i in range(len(df)):
            row_str = " ".join(str(v) for v in df.iloc[i].values if pd.notna(v))
            if "industry name" in row_str.lower() and "beta" in row_str.lower():
                header_row = i
                break

        if header_row is None:
            raise NetworkError("Damodaran", "No se encontró encabezado en betas")

        # Parsear datos
        betas: dict[str, dict[str, Any]] = {}
        for i in range(header_row + 1, len(df)):
            industry = df.iloc[i, 0]
            if pd.isna(industry) or not isinstance(industry, str):  # type: ignore
                continue
            industry = industry.strip()
            if not industry or industry.lower().startswith("date") or industry.lower().startswith(
                "created"
            ):
                continue

            beta = df.iloc[i, 2] if pd.notna(df.iloc[i, 2]) else None  # type: ignore
            unlevered = df.iloc[i, 6] if len(df.columns) > 6 and pd.notna(df.iloc[i, 6]) else None  # type: ignore
            de_ratio = df.iloc[i, 3] if pd.notna(df.iloc[i, 3]) else None  # type: ignore
            tax_rate = df.iloc[i, 4] if pd.notna(df.iloc[i, 4]) else None  # type: ignore
            n_firms = df.iloc[i, 1] if pd.notna(df.iloc[i, 1]) else None  # type: ignore

            betas[industry] = {
                "beta": float(beta) if beta is not None else None,  # type: ignore
                "unlevered_beta": float(unlevered) if unlevered is not None else None,  # type: ignore
                "de_ratio": float(de_ratio) if de_ratio is not None else None,  # type: ignore
                "tax_rate": float(tax_rate) if tax_rate is not None else None,  # type: ignore
                "n_firms": int(n_firms) if n_firms is not None else None,  # type: ignore
            }

        result_data = {
            "betas": betas,
            "date": "2026-01-05",
            "provider": "Damodaran (NYU Stern)",
            "url": URLS["betas"],
        }
        self.cache.set(cache_key, result_data, CacheTTL.DAMODARAN, "Damodaran", URLS["betas"])
        return DataSourceResult.from_provider("Damodaran", result_data, URLS["betas"])

    def get_margins_by_industry(self) -> DataSourceResult:
        """Obtiene márgenes por industria.

        Returns:
            DataSourceResult con dict: {industry_name: {"gross_margin": float, ...}}
        """
        cache_key = "Damodaran_Margins"
        cached = self.cache.get(cache_key, CacheTTL.DAMODARAN)
        if cached is not None:
            return DataSourceResult.from_provider("Damodaran", cached)

        try:
            resp = httpx.get(URLS["margins"], timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise NetworkError("Damodaran", f"Error descargando márgenes: {e}") from e

        try:
            import io

            df = pd.read_excel(io.BytesIO(resp.content), sheet_name=0, header=None, engine="xlrd")
        except Exception as e:
            raise NetworkError("Damodaran", f"Error parseando márgenes: {e}") from e

        # Buscar encabezado
        header_row = None
        for i in range(len(df)):
            row_str = " ".join(str(v) for v in df.iloc[i].values if pd.notna(v))
            if "industry" in row_str.lower() and "margin" in row_str.lower():
                header_row = i
                break

        if header_row is None:
            raise NetworkError("Damodaran", "No se encontró encabezado en márgenes")

        margins: dict[str, dict[str, Any]] = {}
        for i in range(header_row + 1, len(df)):
            industry = df.iloc[i, 0]
            if pd.isna(industry) or not isinstance(industry, str):  # type: ignore
                continue
            industry = industry.strip()
            if not industry or industry.lower().startswith("date") or industry.lower().startswith(
                "created"
            ):
                continue

            # Intentar extraer márgenes (columnas varían)
            margin_data: dict[str, Any] = {"industry": industry}
            for j in range(1, min(len(df.columns), 8)):
                val = df.iloc[i, j]
                if pd.notna(val) and isinstance(val, (int, float)):  # type: ignore
                    margin_data[f"col_{j}"] = float(val)

            margins[industry] = margin_data

        result_data = {
            "margins": margins,
            "provider": "Damodaran (NYU Stern)",
            "url": URLS["margins"],
        }
        self.cache.set(cache_key, result_data, CacheTTL.DAMODARAN, "Damodaran", URLS["margins"])
        return DataSourceResult.from_provider("Damodaran", result_data, URLS["margins"])


def get_damodaran_erp() -> float | None:
    """Devuelve la ERP implícita de Damodaran o None si no está disponible."""
    try:
        provider = DamodaranProvider()
        result = provider.get_implied_erp()
        if isinstance(result.data, dict):
            return result.data.get("erp")
    except (NetworkError, DataSourceConfigError):
        pass
    return None


def get_damodaran_beta(industry: str) -> float | None:
    """Devuelve el beta de una industria o None si no está disponible."""
    try:
        provider = DamodaranProvider()
        result = provider.get_betas_by_industry()
        if isinstance(result.data, dict):
            betas = result.data.get("betas", {})
            for name, data in betas.items():
                if industry.lower() in name.lower():
                        val = data.get("beta")
                        return float(val) if val is not None else None
    except (NetworkError, DataSourceConfigError):
        pass
    return None


__all__ = [
    "DamodaranProvider",
    "get_damodaran_beta",
    "get_damodaran_erp",
]
