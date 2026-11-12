"""Fuentes de datos externas: interfaces abstractas y excepciones (AGENTS.md §13.1).

Define los Protocols que el resto de la app consume (nunca un proveedor
concreto) y las excepciones de dominio propias del módulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------
class DataSourceError(Exception):
    """Base de todos los errores del módulo de fuentes externas."""

    def __init__(self, provider: str, message: str, cause: Exception | None = None) -> None:
        """Inicializa el error de fuente de datos."""
        self.provider = provider
        self.message = message
        super().__init__(f"{provider}: {message}")
        if cause is not None:
            self.__cause__ = cause


class NetworkError(DataSourceError):
    """Error de red o respuesta HTTP inesperada (incluye 404)."""


class RateLimitError(DataSourceError):
    """Se superó el límite de peticiones de la fuente (HTTP 429)."""


class InvalidTickerError(DataSourceError):
    """El ticker o CIK solicitado no existe en la fuente."""


class DataSourceConfigError(DataSourceError):
    """Falta configuración obligatoria (p. ej. SEC_USER_AGENT)."""


# ---------------------------------------------------------------------------
# Resultado de una fuente
# ---------------------------------------------------------------------------
@dataclass
class DataSourceResult:
    """Envuelve el dato devuelto por una fuente con su procedencia."""

    provider: str
    data: Any
    url: str | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_provider(cls, provider: str, data: Any, url: str | None = None) -> DataSourceResult:  # noqa: ANN401
        """Crea un DataSourceResult a partir de un proveedor."""
        return cls(provider=provider, data=data, url=url)


# ---------------------------------------------------------------------------
# Protocols (AGENTS.md §13.1)
# ---------------------------------------------------------------------------
class FilingsProvider(Protocol):
    """Proveedor de filings (10-K, 10-Q) y metadatos de empresa."""

    def get_company_tickers(self) -> DataSourceResult:
        """Devuelve el mapeo ticker → CIK."""
        ...

    def get_filings_list(self, cik: str) -> DataSourceResult:
        """Devuelve la lista de filings de un CIK."""
        ...

    def download_filing(self, accession_number: str) -> DataSourceResult:
        """Descarga un filing concreto."""
        ...


class MarketDataProvider(Protocol):
    """Proveedor de datos de mercado (precio, acciones, beta)."""

    def get_price(self, ticker: str) -> DataSourceResult:
        """Devuelve el precio de un ticker."""
        ...

    def get_shares_outstanding(self, ticker: str) -> DataSourceResult:
        """Devuelve las acciones en circulación."""
        ...


class RatesProvider(Protocol):
    """Proveedor de tasas (Rf, ERP)."""

    def get_risk_free_rate(self) -> DataSourceResult:
        """Devuelve la tasa libre de riesgo."""
        ...


__all__ = [
    "DataSourceConfigError",
    "DataSourceError",
    "DataSourceResult",
    "FilingsProvider",
    "InvalidTickerError",
    "MarketDataProvider",
    "NetworkError",
    "RateLimitError",
    "RatesProvider",
]
