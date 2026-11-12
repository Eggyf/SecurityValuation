"""Caché en disco con TTL para fuentes externas (AGENTS.md §13.1).

Filings: sin caducidad (inmutables). Precios: 15 min-1 día. Tasas: 1 día.
Datasets de Damodaran: 30 días.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/edgar")


class CacheTTL:
    """TTL en segundos para cada categoría de dato."""

    FILINGS = None  # sin caducidad
    RATES = 86400  # 1 día
    PRICES = 900  # 15 minutos
    DAMODARAN = 2592000  # 30 días


class CacheManager:
    """Caché simple en disco basada en ficheros JSON/binarios."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        """Inicializa el gestor de caché."""
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Sanitizar la clave para usarla como nombre de fichero
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
        return self.cache_dir / f"{safe}.json"

    def get(self, key: str, ttl: int | None = None) -> Any | None:  # noqa: ANN401
        """Devuelve el dato cacheado si existe y no ha caducado."""
        path = self._path(key)
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        stored_at = envelope.get("_stored_at", 0)
        if ttl is not None and (time.time() - stored_at) > ttl:
            # Caducado
            with contextlib.suppress(OSError):
                path.unlink()
            return None

        return envelope.get("data")

    def set(
        self,
        key: str,
        data: Any,  # noqa: ANN401
        ttl: int | None = None,
        provider: str = "",
        url: str | None = None,
    ) -> None:
        """Guarda un dato en caché."""
        path = self._path(key)
        envelope = {
            "_stored_at": time.time(),
            "_provider": provider,
            "_url": url,
            "data": data,
        }
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(envelope, f)
        except (OSError, TypeError):
            # Si no se puede serializar (bytes), guardar como binario
            try:
                bin_path = path.with_suffix(".bin")
                if isinstance(data, (bytes, bytearray)):
                    bin_path.write_bytes(data)
            except OSError:
                logger.warning("No se pudo cachear %s", key)

    def get_bytes(self, key: str, ttl: int | None = None) -> bytes | None:
        """Devuelve bytes cacheados (para filings binarios)."""
        path = self._path(key).with_suffix(".bin")
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    def set_bytes(self, key: str, data: bytes, ttl: int | None = None) -> None:
        """Guarda bytes en caché."""
        path = self._path(key).with_suffix(".bin")
        try:
            path.write_bytes(data)
        except OSError:
            logger.warning("No se pudo cachear bytes %s", key)


__all__ = ["CACHE_DIR", "CacheManager", "CacheTTL"]
