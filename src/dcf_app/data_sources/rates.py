"""Proveedor de tasas: tasa libre de riesgo (Rf) desde FRED (AGENTS.md §13.2).

Usa la serie DGS10 (bono del Tesoro a 10 años) por defecto.
Requiere FRED_API_KEY en .env (gratuita).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx

from dcf_app.data_sources.base import (
    DataSourceConfigError,
    DataSourceResult,
    NetworkError,
    RatesProvider,
)
from dcf_app.data_sources.cache import CacheManager, CacheTTL

logger = logging.getLogger(__name__)

# Cargar .env si existe
_env_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]
for _candidate in _env_candidates:
    if _candidate.exists():
        with _candidate.open(encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _, _value = _line.partition("=")
                    _key = _key.strip()
                    _value = _value.strip().strip('"').strip("'")
                    if _key and _key not in os.environ:
                        os.environ[_key] = _value
        break

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"


class FredRatesProvider(RatesProvider):
    """Proveedor de tasas desde FRED (Federal Reserve Economic Data)."""

    def __init__(self, api_key: str | None = None) -> None:
        """Inicializa el proveedor de tasas FRED."""
        self.api_key = api_key or FRED_API_KEY
        if not self.api_key:
            raise DataSourceConfigError(
                "FRED", "Falta FRED_API_KEY. Configúrala en .env (ver .env.example)."
            )
        self.cache = CacheManager()

    def get_risk_free_rate(self, series: str = "DGS10") -> DataSourceResult:
        """Obtiene la tasa libre de riesgo (último valor disponible).

        Args:
            series: serie de FRED (por defecto DGS10 = bono a 10 años).

        Returns:
            DataSourceResult con el valor de la tasa (en porcentaje, ej: 4.5).
        """
        cache_key = f"FRED_{series}"
        cached = self.cache.get(cache_key, CacheTTL.RATES)
        if cached is not None:
            return DataSourceResult.from_provider("FRED", cached)

        url = (
            f"{FRED_BASE_URL}?series_id={series}&api_key={self.api_key}"
            f"&file_type=json&sort_order=desc&limit=10"
        )
        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            raise NetworkError("FRED", f"Error obteniendo {series}: {e}") from e

        observations = data.get("observations", [])
        if not observations:
            raise NetworkError("FRED", f"No hay observaciones para {series}")

        # Buscar la primera observación válida (saltar '.')
        obs = None
        for o in observations:
            if o.get("value", ".") != ".":
                obs = o
                break

        if obs is None:
            raise NetworkError("FRED", f"No hay valores válidos para {series}")

        value_str = obs.get("value", ".")
        try:
            value = float(value_str)
        except ValueError as e:
            raise NetworkError("FRED", f"Valor inválido: {value_str}") from e

        result_data = {
            "series": series,
            "value": value,
            "date": obs.get("date", ""),
            "provider": "FRED",
        }
        self.cache.set(cache_key, result_data, CacheTTL.RATES, "FRED", url)
        return DataSourceResult.from_provider("FRED", result_data, url)

    def get_treasury_curve(self) -> DataSourceResult:
        """Obtiene la curva de rendimientos del Tesoro (DGS10, DGS2, DGS5, etc.)."""
        series_list = ["DGS2", "DGS5", "DGS10", "DGS30"]
        results = {}
        for s in series_list:
            try:
                r = self.get_risk_free_rate(s)
                if isinstance(r.data, dict):
                    results[s] = r.data
            except (NetworkError, DataSourceConfigError):
                pass
        return DataSourceResult.from_provider("FRED", results)


def get_risk_free_rate() -> float | None:
    """Devuelve la tasa libre de riesgo (DGS10) o None si no está disponible."""
    result = get_risk_free_rate_full()
    if result is not None:
        return result.get("value")
    return None


def get_risk_free_rate_full() -> dict[str, Any] | None:
    """Devuelve la tasa libre de riesgo con fecha y fuente."""
    try:
        provider = FredRatesProvider()
        result = provider.get_risk_free_rate()
        if isinstance(result.data, dict):
            return result.data
    except (DataSourceConfigError, NetworkError):
        pass
    return None


__all__ = ["FredRatesProvider", "get_risk_free_rate"]
