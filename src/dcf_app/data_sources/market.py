"""Proveedor de datos de mercado: precio, market cap (AGENTS.md §13.2).

Usa Financial Modeling Prep (FMP) como proveedor principal.
Requiere FMP_DATA_API_KEY (o MARKET_DATA_API_KEY) en .env.
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
    MarketDataProvider,
    NetworkError,
)
from dcf_app.data_sources.cache import CacheManager, CacheTTL

logger = logging.getLogger(__name__)

# Soporta tanto FMP_DATA_API_KEY como MARKET_DATA_API_KEY
MARKET_DATA_API_KEY = os.environ.get(
    "FMP_DATA_API_KEY", ""
) or os.environ.get("MARKET_DATA_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

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

MARKET_DATA_API_KEY = os.environ.get(
    "FMP_DATA_API_KEY", ""
) or os.environ.get("MARKET_DATA_API_KEY", "")


class FmpMarketProvider(MarketDataProvider):
    """Proveedor de datos de mercado desde Financial Modeling Prep (FMP)."""

    def __init__(self, api_key: str | None = None) -> None:
        """Inicializa el proveedor de datos de mercado FMP."""
        self.api_key = api_key or MARKET_DATA_API_KEY
        if not self.api_key:
            raise DataSourceConfigError(
                "FMP", "Falta FMP_DATA_API_KEY. Configúrala en .env."
            )
        self.cache = CacheManager()

    def get_price(self, ticker: str) -> DataSourceResult:
        """Obtiene el precio actual de una acción."""
        cache_key = f"FMP_price_{ticker}"
        cached = self.cache.get(cache_key, CacheTTL.PRICES)
        if cached is not None:
            return DataSourceResult.from_provider("FMP", cached)

        url = f"{FMP_BASE}/quote?symbol={ticker}&apikey={self.api_key}"
        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            raise NetworkError("FMP", f"Error obteniendo precio de {ticker}: {e}") from e

        if not isinstance(data, list) or not data:
            raise NetworkError("FMP", f"No se encontró precio para {ticker}: {data}")

        quote = data[0]
        price = quote.get("price")
        market_cap = quote.get("marketCap")

        result_data = {
            "ticker": ticker,
            "price": float(price) if price else None,
            "market_cap": float(market_cap) / 1e6 if market_cap else None,
            "provider": "FMP",
        }
        self.cache.set(cache_key, result_data, CacheTTL.PRICES, "FMP", url)
        return DataSourceResult.from_provider("FMP", result_data, url)

    def get_shares_outstanding(self, ticker: str) -> DataSourceResult:
        """Obtiene market cap (shares no disponible en FMP free, se estima)."""
        cache_key = f"FMP_profile_{ticker}"
        cached = self.cache.get(cache_key, CacheTTL.RATES)
        if cached is not None:
            return DataSourceResult.from_provider("FMP", cached)

        url = f"{FMP_BASE}/profile?symbol={ticker}&apikey={self.api_key}"
        try:
            response = httpx.get(url, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            logger.warning("No se pudo obtener perfil de %s: %s", ticker, e)
            return DataSourceResult.from_provider(
                "FMP",
                {
                    "ticker": ticker,
                    "shares_outstanding": None,
                    "market_cap": None,
                    "provider": "FMP",
                },
            )

        if not isinstance(data, list) or not data:
            return DataSourceResult.from_provider(
                "FMP",
                {
                    "ticker": ticker,
                    "shares_outstanding": None,
                    "market_cap": None,
                    "provider": "FMP",
                },
            )

        profile = data[0]
        market_cap = profile.get("marketCap")

        result_data = {
            "ticker": ticker,
            "shares_outstanding": None,  # No disponible en FMP free
            "market_cap": float(market_cap) / 1e6 if market_cap else None,
            "provider": "FMP",
        }
        self.cache.set(cache_key, result_data, CacheTTL.RATES, "FMP", url)
        return DataSourceResult.from_provider("FMP", result_data, url)


def get_market_data(ticker: str) -> dict[str, Any] | None:
    """Devuelve precio y market cap o None si no está disponible."""
    try:
        provider = FmpMarketProvider()
        result = provider.get_price(ticker)
        if isinstance(result.data, dict):
            return {
                "ticker": ticker,
                "price": result.data.get("price"),
                "market_cap": result.data.get("market_cap"),
                "shares_outstanding": None,
            }
    except (DataSourceConfigError, NetworkError):
        pass
    return None


__all__ = ["FmpMarketProvider", "get_market_data"]
