"""Notas relevantes del 10-K para la valoración (AGENTS.md §6).

Datos que no viven en los tres estados principales pero que necesita el
modelo: títulos dilutivos, tasas impositivas, partidas no recurrentes y
vencimientos de deuda.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dcf_app.models.fact import Fact


class DilutiveSecurities(BaseModel):
    """Opciones y RSUs vivas para el método de la acción de tesorería (AGENTS.md §7.6)."""

    model_config = ConfigDict(extra="forbid")

    options_outstanding: Fact | None = None  # unit: 'shares'
    options_weighted_avg_exercise_price: Fact | None = None  # unit: 'USD_per_share'
    rsus_outstanding: Fact | None = None  # unit: 'shares'


class EffectiveTaxRates(BaseModel):
    """Tasas impositivas efectiva y estatutaria del ejercicio más reciente."""

    model_config = ConfigDict(extra="forbid")

    effective: Fact | None = None  # unit: 'ratio'
    statutory: Fact | None = None  # unit: 'ratio'


class NonRecurringItem(BaseModel):
    """Partida no recurrente a excluir del EBIT base (AGENTS.md §7.1)."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    amount: Fact | None = None  # importe pre-impuestos tal como se reporta
    affects_ebit: bool = True


class DebtMaturity(BaseModel):
    """Vencimiento de deuda financiera por ejercicio fiscal."""

    model_config = ConfigDict(extra="forbid")

    fiscal_year: int
    amount: Fact | None = None


class SupplementaryNotes(BaseModel):
    """Notas del 10-K usadas por normalización, supuestos y el puente EV→equity."""

    model_config = ConfigDict(extra="forbid")

    dilutive_securities: DilutiveSecurities = Field(default_factory=DilutiveSecurities)
    effective_tax_rates: EffectiveTaxRates = Field(default_factory=EffectiveTaxRates)
    non_recurring_items: list[NonRecurringItem] = Field(default_factory=list)
    debt_maturities: list[DebtMaturity] = Field(default_factory=list)
    weighted_avg_interest_rate: Fact | None = None  # unit: 'ratio'; para Kd
    basic_shares_outstanding: Fact | None = None  # unit: 'shares'; de la portada
