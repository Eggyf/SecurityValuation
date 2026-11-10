"""Excepciones de dominio de la aplicación.

Todas las excepciones exponen mensajes accionables en español, pensados para
mostrarse directamente en la UI (AGENTS.md §8).
"""

from __future__ import annotations


class DCFError(Exception):
    """Base de todos los errores controlados de la aplicación."""


class ExtractionError(DCFError):
    """No se ha podido extraer un dato requerido del 10-K."""


class ValidationError(DCFError):
    """Una comprobación de integridad contable ha fallado (AGENTS.md §6)."""


class ValuationError(DCFError):
    """Entrada inválida o supuesto incoherente para el motor DCF."""


__all__ = ["DCFError", "ExtractionError", "ValidationError", "ValuationError"]
