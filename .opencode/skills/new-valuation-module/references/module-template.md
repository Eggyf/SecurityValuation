# Plantilla de módulo

Ejemplo mínimo con un módulo ficticio «implied_multiple» (EV/EBITDA implícito). Adapta nombres y campos; mantén la forma.

## `src/dcf_app/models/implied_multiple.py`

```python
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ImpliedMultipleInputs(BaseModel):
    """Entradas del módulo. Importes en millones de USD."""

    enterprise_value: float = Field(..., description="EV del DCF base (MM USD)")
    ebitda: float = Field(..., description="EBITDA del último ejercicio (MM USD)")

    @field_validator("ebitda")
    @classmethod
    def _ebitda_not_zero(cls, v: float) -> float:
        if v == 0:
            raise ValueError("EBITDA no puede ser 0")
        return v


class ImpliedMultipleResult(BaseModel):
    applicable: bool
    multiple: float | None = None
    warnings: list[str] = Field(default_factory=list)
    assumptions_used: dict[str, float | str] = Field(default_factory=dict)
```

## `src/dcf_app/valuation/implied_multiple.py`

```python
from __future__ import annotations

from dcf_app.models.implied_multiple import ImpliedMultipleInputs, ImpliedMultipleResult


def run(inputs: ImpliedMultipleInputs) -> ImpliedMultipleResult:
    """EV/EBITDA implícito = EV / EBITDA.

    Función pura: sin I/O ni estado global.
    No aplicable si el EBITDA es negativo (el múltiplo no es significativo).
    """
    if inputs.ebitda < 0:
        return ImpliedMultipleResult(
            applicable=False,
            warnings=[f"EBITDA negativo ({inputs.ebitda:.1f} MM USD): múltiplo no significativo"],
        )
    multiple = inputs.enterprise_value / inputs.ebitda
    warnings: list[str] = []
    if multiple > 25:
        warnings.append(f"EV/EBITDA implícito {multiple:.1f}x, por encima de 25x")
    return ImpliedMultipleResult(
        applicable=True,
        multiple=multiple,
        warnings=warnings,
        assumptions_used={"ebitda": inputs.ebitda, "enterprise_value": inputs.enterprise_value},
    )
```

## `tests/unit/test_implied_multiple.py`

```python
import math

from dcf_app.models.implied_multiple import ImpliedMultipleInputs
from dcf_app.valuation.implied_multiple import run


def test_multiple_by_hand():
    """EV 2.713,8 y EBITDA 300 → 2.713,8 / 300 = 9,046."""
    res = run(ImpliedMultipleInputs(enterprise_value=2713.8, ebitda=300))
    assert res.applicable
    assert math.isclose(res.multiple, 9.046, abs_tol=1e-3)


def test_negative_ebitda_is_not_applicable():
    res = run(ImpliedMultipleInputs(enterprise_value=1000, ebitda=-10))
    assert not res.applicable
    assert res.multiple is None
    assert res.warnings


def test_high_multiple_warns_with_number():
    res = run(ImpliedMultipleInputs(enterprise_value=3000, ebitda=100))
    assert any("30.0x" in w for w in res.warnings)
```

## Pestaña de UI (ver `streamlit-ui`)

```python
def tab_implied_multiple() -> None:
    st.header("EV/EBITDA implícito")
    res = implied_multiple.run(build_inputs_from_state())   # sin fórmulas aquí
    if not res.applicable:
        st.info("No aplicable: " + "; ".join(res.warnings))
        return
    st.metric("EV/EBITDA implícito", f"{res.multiple:.1f}x")
    for w in res.warnings:
        st.warning(w)
```

## Entrada en `docs/methodology.md`

```markdown
### EV/EBITDA implícito
- Fórmula: EV / EBITDA del último ejercicio.
- Decisiones: EBITDA = EBIT + D&A reportados; no se ajusta por no recurrentes.
- Limitaciones: no significativo con EBITDA ≤ 0.
- Umbral de aviso: 25x (configurable).
```
