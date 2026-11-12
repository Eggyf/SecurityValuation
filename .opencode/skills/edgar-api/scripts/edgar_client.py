"""Esqueleto de cliente EDGAR. NO probado contra la red real.

Dependencias: httpx. Pensado para vivir en src/dcf_app/data_sources/edgar.py
detrás de la interfaz FilingsProvider.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

CACHE_DIR = Path(".cache/edgar")
MIN_INTERVAL = 1 / 8  # 8 peticiones/s, por debajo del límite de 10/s


class EdgarConfigError(RuntimeError):
    pass


def pad_cik(cik: int | str) -> str:
    """CIK a 10 dígitos con ceros a la izquierda (para data.sec.gov)."""
    return str(int(cik)).zfill(10)


def archive_url(cik: int | str, accession: str, primary_document: str) -> str:
    """URL de un documento en Archives: CIK sin ceros y accession sin guiones."""
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{primary_document}"
    )


class EdgarClient:
    def __init__(self, user_agent: str | None = None, client: httpx.Client | None = None):
        ua = user_agent or os.environ.get("SEC_USER_AGENT")
        if not ua:
            raise EdgarConfigError(
                "Falta SEC_USER_AGENT (nombre y email de contacto). "
                "La SEC bloquea peticiones sin User-Agent identificable."
            )
        self._client = client or httpx.Client(
            headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
            timeout=30.0,
        )
        self._last = 0.0

    def _throttle(self) -> None:
        wait = MIN_INTERVAL - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        return CACHE_DIR / (hashlib.sha256(url.encode()).hexdigest() + ".bin")

    def get_bytes(self, url: str, use_cache: bool = True, retries: int = 4) -> bytes:
        path = self._cache_path(url)
        if use_cache and path.exists():
            return path.read_bytes()
        delay = 1.0
        for attempt in range(retries):
            self._throttle()
            resp = self._client.get(url)
            if resp.status_code == 403:
                raise EdgarConfigError(
                    "403 de la SEC: revisa SEC_USER_AGENT; no se reintenta."
                )
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return resp.content
        raise RuntimeError(f"EDGAR no respondió tras {retries} intentos: {url}")

    def get_json(self, url: str, use_cache: bool = True) -> Any:
        return json.loads(self.get_bytes(url, use_cache))

    # --- Consultas ---
    def ticker_to_cik(self, ticker: str) -> int:
        data = self.get_json("https://www.sec.gov/files/company_tickers.json")
        for row in data.values():
            if row["ticker"].upper() == ticker.upper():
                return int(row["cik_str"])
        raise KeyError(f"Ticker no encontrado: {ticker}")

    def submissions(self, cik: int | str) -> dict:
        # El listado cambia con frecuencia: úsalo con caché corta o sin ella.
        return self.get_json(
            f"https://data.sec.gov/submissions/CIK{pad_cik(cik)}.json", use_cache=False
        )

    def company_facts(self, cik: int | str) -> dict:
        return self.get_json(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{pad_cik(cik)}.json",
            use_cache=False,
        )


def pick_10k(submissions: dict, report_year: int | None = None) -> dict:
    """Elige el 10-K (no enmiendas) más reciente, o el de un año de cierre dado."""
    recent = submissions["filings"]["recent"]
    rows = [dict(zip(recent.keys(), vals)) for vals in zip(*recent.values())]
    tenks = [r for r in rows if r["form"] == "10-K"]
    if report_year is not None:
        tenks = [r for r in tenks if r["reportDate"].startswith(str(report_year))]
    if not tenks:
        raise LookupError("No hay 10-K que cumpla el filtro (revisa filings.files)")
    return max(tenks, key=lambda r: r["filingDate"])
