"""Cifra extraída del 10-K con trazabilidad completa (AGENTS.md §2.3 y §6).

Toda cifra que entra en la aplicación viaja envuelta en :class:`Fact`: el
valor tal como lo reporta la empresa, con su unidad, escala, periodo y
procedencia. La normalización (escala común, signos, ajustes) ocurre en
``normalization/``; este modelo nunca transforma el valor
(decisión registrada en ``docs/methodology.md``).
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Scale(StrEnum):
    """Escala en la que la empresa reporta la cifra (atributo ``scale`` de iXBRL)."""

    UNITS = "units"
    THOUSANDS = "thousands"
    MILLIONS = "millions"
    BILLIONS = "billions"

    @property
    def exponent(self) -> int:
        """Potencia de 10 que multiplica al valor reportado."""
        return _SCALE_EXPONENTS[self]

    @classmethod
    def from_exponent(cls, exponent: int) -> Scale:
        """Recupera la escala a partir del exponente iXBRL (0, 3, 6, 9)."""
        for scale, scale_exponent in _SCALE_EXPONENTS.items():
            if scale_exponent == exponent:
                return scale
        valid = sorted(_SCALE_EXPONENTS.values())
        raise ValueError(f"Exponente {exponent} no soportado; los válidos son {valid}.")


_SCALE_EXPONENTS: dict[Scale, int] = {
    Scale.UNITS: 0,
    Scale.THOUSANDS: 3,
    Scale.MILLIONS: 6,
    Scale.BILLIONS: 9,
}


class Confidence(StrEnum):
    """Fiabilidad de la procedencia de la cifra."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceKind(StrEnum):
    """Origen posible de una cifra (AGENTS.md §6)."""

    IXBRL = "ixbrl"  # tag estándar us-gaap
    IXBRL_EXTENSION = "ixbrl_extension"  # concepto personalizado de la empresa
    TEXT_FALLBACK = "text_fallback"  # tabla o texto del 10-K
    USER_INPUT = "user_input"  # introducido manualmente


_KIND_CONFIDENCE: dict[SourceKind, Confidence] = {
    SourceKind.IXBRL: Confidence.HIGH,
    SourceKind.IXBRL_EXTENSION: Confidence.MEDIUM,
    SourceKind.TEXT_FALLBACK: Confidence.LOW,
    SourceKind.USER_INPUT: Confidence.HIGH,
}


class SourceRef(BaseModel):
    """Procedencia auditable de una cifra (AGENTS.md §2.3).

    Un ``Fact`` sin fuente es un error: la UI debe poder mostrar de dónde
    sale cada número. Por eso iXBRL exige concepto y el texto exige
    sección/página.
    """

    model_config = ConfigDict(extra="forbid")

    kind: SourceKind
    concept: str | None = None  # p. ej. "us-gaap:Revenues" o "company:MetricaPropia"
    location: str | None = None  # p. ej. "Item 8, p. 57"

    @model_validator(mode="after")
    def _require_traceable_origin(self) -> Self:
        """Exige suficiente detalle según el tipo de fuente."""
        if self.kind in (SourceKind.IXBRL, SourceKind.IXBRL_EXTENSION) and not self.concept:
            raise ValueError(
                "Una fuente iXBRL debe indicar el concepto XBRL (p. ej. 'us-gaap:Revenues')."
            )
        if self.kind is SourceKind.TEXT_FALLBACK and not self.location:
            raise ValueError(
                "Una fuente de texto debe indicar sección y página (p. ej. 'Item 8, p. 57')."
            )
        return self

    @property
    def confidence(self) -> Confidence:
        """Confianza derivada del tipo de fuente (AGENTS.md §6)."""
        return _KIND_CONFIDENCE[self.kind]

    def describe(self) -> str:
        """Descripción legible para la UI."""
        if self.kind is SourceKind.IXBRL:
            text = f"iXBRL: {self.concept}"
        elif self.kind is SourceKind.IXBRL_EXTENSION:
            text = f"iXBRL (extensión de la empresa): {self.concept}"
        elif self.kind is SourceKind.TEXT_FALLBACK:
            text = f"Texto del 10-K: {self.location}"
        else:
            text = "Introducido por el usuario"
        if self.location and self.kind is not SourceKind.TEXT_FALLBACK:
            text += f" ({self.location})"
        return text


class Fact(BaseModel):
    """Una cifra del 10-K con unidad, escala, periodo y procedencia.

    - ``value`` es ``None`` cuando el dato no está en el documento: nunca se
      rellena con un valor típico (AGENTS.md §2.1).
    - El valor conserva el signo con el que lo reporta la empresa (p. ej., el
      CapEx suele aparecer como pago negativo en el flujo de caja).
    - La unidad y la escala son las originales del documento; la conversión a
      millones ocurre en ``normalization/``.
    """

    model_config = ConfigDict(extra="forbid")

    value: float | None = None
    unit: str = Field(min_length=1)  # 'USD', 'EUR', 'shares', 'USD_per_share', 'ratio', ...
    scale: Scale
    period_start: date | None = None  # None en datos instantáneos (balance)
    period_end: date
    source: SourceRef

    @model_validator(mode="after")
    def _period_order(self) -> Self:
        """Exige ``period_start < period_end`` cuando la cifra es de periodo."""
        if self.period_start is not None and self.period_start >= self.period_end:
            raise ValueError("period_start debe ser anterior a period_end.")
        return self

    @property
    def is_instant(self) -> bool:
        """True si la cifra es a fecha (balance) y no de periodo (P&L, flujo)."""
        return self.period_start is None

    @property
    def confidence(self) -> Confidence:
        """Confianza heredada de la fuente."""
        return self.source.confidence

    def to_scale(self, target: Scale) -> float | None:
        """Reescala el valor a otra escala: ``v' = v * 10**(e_origen - e_destino)``.

        Devuelve ``None`` si el valor falta.
        """
        if self.value is None:
            return None
        return self.value * 10.0 ** (self.scale.exponent - target.exponent)
