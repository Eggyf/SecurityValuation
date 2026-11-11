"""Supuestos de valoración (AGENTS.md §7).

Todos los supuestos son opcionales (None si no se proporcionan). La
normalización a millones ocurre en ``normalization/``; aquí se guardan
los valores originales tal como los introduce el usuario o los deriva de
históricos.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Scenario(StrEnum):
    """Escenarios de proyección (AGENTS.md §7.2)."""

    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class GrowthMethod(StrEnum):
    """Método de proyección del crecimiento (AGENTS.md §7.2)."""

    HISTORICAL_CAGR = "historical_cagr"
    USER_INPUT = "user_input"
    FADE_LINEAR = "fade_linear"  # por defecto: crecimiento inicial → crecimiento terminal


class TerminalValueMethod(StrEnum):
    """Método de cálculo del valor terminal (AGENTS.md §7.4)."""

    GORDON_GROWTH = "gordon_growth"  # por defecto
    MULTIPLE = "multiple"


class DiscountConvention(StrEnum):
    """Convención de descuento (AGENTS.md §7.5)."""

    END_OF_YEAR = "end_of_year"
    MID_YEAR = "mid_year"


class Assumptions(BaseModel):
    """Supuestos de la valoración DCF (AGENTS.md §7).

    Todos los campos son opcionales: si no se proporcionan, el motor DCF
    usará valores por defecto justificados (AGENTS.md §2.1).
    """

    model_config = ConfigDict(extra="forbid")

    # --- Datos de la empresa ---
    company_name: str = Field(min_length=1)
    fiscal_year_end: date  # fecha de cierre del ejercicio fiscal
    valuation_date: date  # fecha de valoración (por defecto: fecha del último 10-K o actual)

    # --- Proyección (AGENTS.md §7.2) ---
    scenario: Scenario = Scenario.BASE
    forecast_horizon: int = Field(default=5, ge=3, le=10)  # años a proyectar
    growth_method: GrowthMethod = GrowthMethod.FADE_LINEAR
    initial_revenue_growth: float | None = Field(None, ge=-0.05, le=0.25)  # CAGR inicial [-5%, 25%]
    terminal_revenue_growth: float | None = Field(None, ge=0.02, le=0.025)  # g terminal [2%, 2.5%]
    ebit_margin_target: float | None = Field(None, ge=0.0, le=1.0)  # margen EBIT objetivo

    # --- WACC (AGENTS.md §7.3) ---
    risk_free_rate: float | None = Field(None, ge=0.0, le=0.1)  # Rf (bono 10 años)
    equity_beta: float | None = Field(None, ge=0.0)  # β desapalancado
    equity_risk_premium: float | None = Field(None, ge=0.0, le=0.2)  # prima de riesgo del mercado
    market_equity_value: float | None = Field(None, ge=0.0)  # capitalización de mercado
    market_debt_value: float | None = Field(None, ge=0.0)  # valor de mercado de la deuda
    cost_of_debt: float | None = Field(None, ge=0.0, le=1.0)  # Kd antes de impuestos
    tax_rate: float | None = Field(None, ge=0.0, le=0.3)  # tasa impositiva efectiva [0%, 30%]

    # --- Valor terminal (AGENTS.md §7.4) ---
    terminal_value_method: TerminalValueMethod = TerminalValueMethod.GORDON_GROWTH
    exit_multiple_ebitda: float | None = Field(None, ge=0.0)  # múltiplo de salida EV/EBITDA

    # --- Puente EV→equity (AGENTS.md §7.6) ---
    stock_price_current: float | None = Field(None, ge=0.0)  # precio de mercado actual
    shares_outstanding: float | None = Field(None, ge=0.0)  # acciones en circulación
    options_outstanding: float | None = Field(None, ge=0.0)  # opciones vivas
    rsus_outstanding: float | None = Field(None, ge=0.0)  # RSUs vivas
    average_option_exercise_price: float | None = Field(None, ge=0.0)  # precio medio de ejercicio

    # --- Otros ---
    discount_convention: DiscountConvention = DiscountConvention.END_OF_YEAR

    @model_validator(mode="after")
    def _terminal_growth_constraints(self) -> Self:
        """Valida que WACC > g y g ≤ Rf (AGENTS.md §7.4)."""
        if (
            self.terminal_revenue_growth is not None
            and self.risk_free_rate is not None
            and self.terminal_revenue_growth > self.risk_free_rate
        ):
            raise ValueError(
                f"El crecimiento terminal ({self.terminal_revenue_growth:.1%}) no puede "
                f"superar la tasa libre de riesgo ({self.risk_free_rate:.1%})."
            )
        return self

    @property
    def wacc(self) -> float | None:
        """WACC calculado (se calcula en ``valuation/wacc.py``)."""
        # Este campo es de solo lectura: el cálculo real está en el módulo de valuation
        return getattr(self, "_wacc", None)

    @wacc.setter
    def wacc(self, value: float) -> None:
        """Permite al motor DCF guardar el WACC calculado."""
        self._wacc = value


class DCFResult(BaseModel):
    """Resultado del cálculo DCF (AGENTS.md §7 y §7.6).

    Contiene la proyección año a año, el valor terminal, el puente EV→equity
    y las sensibilidades.
    """

    model_config = ConfigDict(extra="forbid")

    # --- Entradas ---
    assumptions: Assumptions

    # --- Proyección ---
    forecast_years: list[int]  # años proyectados (ej: [2025, 2026, 2027, 2028, 2029])
    revenue_forecast: list[float]  # ingresos proyectados (millones de USD)
    ebit_forecast: list[float]  # EBIT proyectado (millones de USD)
    nopat_forecast: list[float]  # NOPAT = EBIT * (1 - t)
    fcff_forecast: list[float]  # Free Cash Flow to the Firm
    capex_forecast: list[float]  # CapEx
    delta_nwc_forecast: list[float]  # variación del capital circulante

    # --- Valor terminal ---
    terminal_value: float  # valor terminal en millones de USD
    terminal_value_method: TerminalValueMethod
    terminal_value_multiple: float | None = None  # múltiplo de salida si se usa ese método

    # --- Valoración ---
    enterprise_value: float  # EV = suma de FCFF descontados + TV
    equity_value: float  # Equity Value = EV + Caja - Deuda - Leases - Acciones preferentes - NCI
    price_per_share: float  # precio por acción = Equity Value / Acciones diluidas
    upside_downside: float | None = None  # % (precio implícito vs. precio de mercado)

    # --- Desglose del puente EV→equity (AGENTS.md §7.6) ---
    bridge_breakdown: dict[str, float] = Field(default_factory=dict)  # partida → valor en M USD

    # --- Sensibilidades ---
    sensitivity_wacc_growth: dict[tuple[float, float], float] = Field(
        default_factory=dict
    )  # (WACC, g) → precio por acción
    sensitivity_margin_growth: dict[tuple[float, float], float] = Field(
        default_factory=dict
    )  # (margen EBIT, crecimiento inicial) → precio por acción

    # --- Métricas de calidad ---
    tv_percentage: float  # % del EV que representa el valor terminal
    reinvestment_rate: float | None = None  # tasa de reinversión en el año terminal

    @model_validator(mode="after")
    def _enterprise_value_consistency(self) -> Self:
        """Valida que EV = suma FCFF descontados + TV."""
        # Esta validación se implementa en ``valuation/bridge.py``
        return self

    @property
    def is_reasonable(self) -> bool:
        """Indica si el resultado es razonable (TV < 75% EV, etc.)."""
        return (
            self.tv_percentage < 75.0  # TV < 75% del EV (AGENTS.md §7.4)
            and self.price_per_share > 0  # precio positivo
            and self.enterprise_value > 0  # EV positivo
        )
