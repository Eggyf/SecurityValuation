"""Proveedor EDGAR: descarga de 10-K/10-Q y datos de empresa (AGENTS.md §13.2).

Implementa `FilingsProvider` con:
- ticker → CIK (company_tickers.json)
- listado de filings por CIK (API `submissions`)
- descarga de filings (HTML/PDF) con User-Agent obligatorio y reintentos

Reintentos con backoff exponencial (max 10 peticiones/s, 5 intentos).
Caché: filings sin caducidad (inmutables), CIKs 24h.
Procedencia registrada (provider, URL, fetched_at).
Degradación a input manual si la fuente falla (AGENTS.md §13.1).
"""

from __future__ import annotations

import contextlib
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from dcf_app.data_sources.base import (
    DataSourceConfigError,
    DataSourceResult,
    FilingsProvider,
    InvalidTickerError,
    NetworkError,
    RateLimitError,
)
from dcf_app.data_sources.cache import CacheManager, CacheTTL

logger = logging.getLogger(__name__)

# Configuración de EDGAR (AGENTS.md §13.2)
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# User-Agent obligatorio para EDGAR (AGENTS.md §13.2)
# Cargar .env si existe
# Buscar .env en varios lugares
_env_candidates = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]
_env_path = None
for candidate in _env_candidates:
    if candidate.exists():
        _env_path = candidate
        break
if _env_path is not None:
    with _env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "")


def _pad_cik(cik: int | str) -> str:
    """CIK a 10 dígitos con ceros a la izquierda (para data.sec.gov)."""
    return str(int(cik)).zfill(10)


def _archive_url(cik: int | str, accession: str, primary_document: str) -> str:
    """URL de un documento en Archives: CIK sin ceros y accession sin guiones."""
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{primary_document}"
    )


class EdgarProvider(FilingsProvider):
    """Proveedor de datos EDGAR con caché y reintentos."""

    def __init__(
        self,
        user_agent: str | None = None,
        max_retries: int = 5,
        initial_delay: float = 1.0,
    ) -> None:
        """Inicializa el proveedor EDGAR."""
        self.user_agent = user_agent or SEC_USER_AGENT
        if not self.user_agent:
            raise DataSourceConfigError(
                "EDGAR",
                "Falta SEC_USER_AGENT. Configúrala en .env (ver .env.example).",
            )
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.cache = CacheManager()
        self._last_request = 0.0
        self._min_interval = 1.0 / 8  # 8 req/s, margen sobre el límite de 10/s

    def _throttle(self) -> None:
        """Limita a 8 peticiones/segundo (límite EDGAR: 10/s)."""
        wait = self._min_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _request_with_retry(self, url: str, description: str) -> DataSourceResult:
        """Realiza una petición HTTP con reintentos y backoff.

        Args:
            url: URL a pedir.
            description: descripción para logs.

        Returns:
            DataSourceResult con la respuesta.

        Raises:
            NetworkError: si falla después de reintentos.
            RateLimitError: si EDGAR responde con 429.
            DataSourceConfigError: si falta el User-Agent.
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
        }
        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                self._throttle()
                response = httpx.get(url, headers=headers, timeout=30.0)

                if response.status_code == 403:
                    raise DataSourceConfigError(
                        "EDGAR",
                        "403 de la SEC: revisa SEC_USER_AGENT; no se reintenta.",
                    )

                if response.status_code == 404:
                    raise NetworkError("EDGAR", f"No encontrado: {url}")

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("EDGAR rate limit: esperando %d segundos", retry_after)
                    time.sleep(retry_after)
                    raise RateLimitError("EDGAR", f"Rate limit (429), intento {attempt + 1}")

                response.raise_for_status()

                # Éxito
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("application/json"):
                    data = response.json()
                else:
                    data = response.content

                logger.info(
                    "Éxito: %s (%d bytes)",
                    description,
                    len(data) if isinstance(data, bytes) else len(str(data)),
                )
                return DataSourceResult.from_provider("EDGAR", data, url)

            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
                last_exception = e
                if isinstance(e, httpx.HTTPStatusError):
                    if e.response.status_code == 404:
                        raise NetworkError("EDGAR", f"No encontrado: {url}") from e
                    if e.response.status_code == 403:
                        raise DataSourceConfigError("EDGAR", "403 de la SEC") from e

            # Esperar con backoff exponencial
            delay = self.initial_delay * (2 ** attempt)
            logger.warning(
                "Intento %d/%d fallido (%s), esperando %.1f segundos",
                attempt + 1,
                self.max_retries,
                description,
                delay,
            )
            time.sleep(delay)

        # Si llegamos aquí, todos los intentos fallaron
        raise NetworkError(
            "EDGAR",
            f"Error después de {self.max_retries} intentos: {description}",
            last_exception,
        )

    def get_company_tickers(self) -> DataSourceResult:
        """Devuelve un dict ticker → CIK (ej: {"AAPL": "0000320193"})."""
        cached_data = self.cache.get("EDGAR_company_tickers", CacheTTL.RATES)
        if cached_data is not None:
            logger.debug("Usando caché de company_tickers")
            return DataSourceResult.from_provider("EDGAR", cached_data)

        url = EDGAR_TICKERS_URL
        result = self._request_with_retry(url, "company_tickers.json")

        if isinstance(result.data, dict):
            self.cache.set("EDGAR_company_tickers", result.data, CacheTTL.RATES, "EDGAR", url)

        return result

    def get_filings_list(self, cik: str) -> DataSourceResult:
        """Devuelve la lista de filings de una empresa (CIK).

        Args:
            cik: CIK (se normaliza a 10 dígitos).

        Returns:
            DataSourceResult con dict (API `submissions`).

        Raises:
            InvalidTickerError: si el CIK no existe.
            NetworkError: si la API falla.
        """
        cik_normalized = _pad_cik(cik)

        cache_key = f"EDGAR_filings_{cik_normalized}"
        cached_data = self.cache.get(cache_key, CacheTTL.RATES)
        if cached_data is not None:
            logger.debug("Usando caché de filings para CIK %s", cik_normalized)
            return DataSourceResult.from_provider("EDGAR", cached_data)

        url = EDGAR_SUBMISSIONS_URL.format(cik=cik_normalized)
        try:
            result = self._request_with_retry(url, f"filings para CIK {cik_normalized}")
        except NetworkError as e:
            if "No encontrado" in str(e):
                raise InvalidTickerError("EDGAR", f"CIK {cik_normalized} no encontrado") from e
            raise

        if isinstance(result.data, dict):
            self.cache.set(cache_key, result.data, CacheTTL.RATES, "EDGAR", url)

        return result

    def get_latest_filing_info(self, cik: str, form_type: str = "10-K") -> dict[str, Any] | None:
        """Devuelve info completa del último filing (accession + primaryDocument)."""
        filings = self.get_recent_filings(cik, form_type, n=1)
        return filings[0] if filings else None

    def get_recent_filings(
        self, cik: str, form_type: str = "10-K", n: int = 3
    ) -> list[dict[str, Any]]:
        """Devuelve los N filings más recientes de un tipo.

        Args:
            cik: CIK del emisor.
            form_type: tipo de formulario (ej: "10-K").
            n: número de filings a devolver.

        Returns:
            Lista de dicts con info de cada filing (accessionNumber, primaryDocument, etc.).
        """
        try:
            submissions = self.get_filings_list(cik)
            if not isinstance(submissions.data, dict):
                return []
            filings = submissions.data.get("filings", {}).get("recent", {})
            if not filings:
                return []

            # Construir lista de filings
            keys = list(filings.keys())
            rows = []
            for i in range(len(filings.get("accessionNumber", []))):
                row = {k: filings[k][i] for k in keys if i < len(filings[k])}
                rows.append(row)

            # Filtrar por form type
            candidates = [r for r in rows if r.get("form") == form_type]
            if not candidates:
                return []

            # Ordenar por filingDate descendente y tomar los N primeros
            candidates.sort(key=lambda r: r.get("filingDate", ""), reverse=True)
            return candidates[:n]

        except (NetworkError, InvalidTickerError):
            return []

    def download_filing(
        self,
        accession_number: str,
        cik: str | None = None,
        primary_document: str | None = None,
    ) -> DataSourceResult:
        """Descarga un filing concreto (HTML/PDF).

        Args:
            accession_number: número de acceso (ej: "0000320193-24-000010").
            cik: CIK del emisor (se resuelve si no se pasa).
            primary_document: nombre del documento primario (se busca si no se pasa).

        Returns:
            DataSourceResult con bytes (contenido del archivo).

        Raises:
            NetworkError: si la descarga falla.
            RateLimitError: si se supera el límite de EDGAR.
        """
        # Resolver CIK y primary_document si no se pasaron
        if cik is None or primary_document is None:
            # Parsear CIK del accession number
            parts = accession_number.split("-")
            if len(parts) < 2:
                raise ValueError(f"Accession number inválido: {accession_number}")
            cik = parts[0]

            if primary_document is None:
                info = self.get_latest_filing_info(cik, "10-K")
                if info and info.get("accessionNumber") == accession_number:
                    primary_document = info.get("primaryDocument")
                if primary_document is None:
                    # Intentar con el .txt por defecto
                    primary_document = f"{accession_number}.txt"

        # Construir URL
        url = _archive_url(cik, accession_number, primary_document)

        # Caché: sin caducidad (los filings son inmutables)
        cache_key = f"EDGAR_filing_{accession_number}"
        cached = self.cache.get_bytes(cache_key, CacheTTL.FILINGS)
        if cached is not None:
            logger.debug("Usando caché de filing %s", accession_number)
            return DataSourceResult.from_provider("EDGAR", cached, url)

        # Descargar
        logger.info("Descargando filing %s desde %s", accession_number, url)
        result = self._request_with_retry(url, f"filing {accession_number}")

        if not isinstance(result.data, bytes):
            raise NetworkError("EDGAR", f"Formato de archivo inválido para {accession_number}")

        # Guardar en caché
        self.cache.set_bytes(cache_key, result.data, CacheTTL.FILINGS)

        return result


# Instancia global (usada por la UI)
edgar_provider: EdgarProvider | None = None
with contextlib.suppress(DataSourceConfigError):
    edgar_provider = EdgarProvider()


def get_edgar_provider() -> EdgarProvider:
    """Devuelve la instancia global, creándola si es necesario."""
    global edgar_provider
    if edgar_provider is None:
        edgar_provider = EdgarProvider()
    return edgar_provider


def get_cik_from_ticker(ticker: str) -> str:
    """Resuelve un ticker a CIK usando el proveedor EDGAR."""
    provider = get_edgar_provider()
    result = provider.get_company_tickers()
    if not isinstance(result.data, dict):
        raise NetworkError("EDGAR", "company_tickers no es un dict")

    ticker_upper = ticker.upper()
    # company_tickers.json: {"0": {"cik_str": ..., "ticker": "AAPL", ...}, ...}
    for entry in result.data.values():
        if isinstance(entry, dict) and entry.get("ticker", "").upper() == ticker_upper:
            cik = entry.get("cik_str")
            if cik:
                return _pad_cik(cik)

    raise InvalidTickerError("EDGAR", f"Ticker {ticker} no encontrado en EDGAR")


def get_latest_filing(cik: str, form_type: str = "10-K") -> str | None:
    """Devuelve el accession_number del último filing de un tipo."""
    provider = get_edgar_provider()
    info = provider.get_latest_filing_info(cik, form_type)
    if info:
        return info.get("accessionNumber")
    return None


def get_latest_filing_info(cik: str, form_type: str = "10-K") -> dict[str, Any] | None:
    """Devuelve info completa del último filing."""
    provider = get_edgar_provider()
    return provider.get_latest_filing_info(cik, form_type)


__all__ = [
    "EdgarProvider",
    "edgar_provider",
    "get_cik_from_ticker",
    "get_edgar_provider",
    "get_latest_filing",
    "get_latest_filing_info",
]
