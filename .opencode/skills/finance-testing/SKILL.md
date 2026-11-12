---
name: finance-testing
description: Patrones de tests para código financiero en Python con pytest e hypothesis, incluyendo casos calculados a mano, tolerancias con math.isclose, identidades contables, propiedades de monotonía, golden tests de extracción, tests sin red y configuración de marcadores. Úsala siempre que escribas, revises o arregles tests en tests/, añadas cualquier cálculo financiero nuevo, o cuando un test numérico falle de forma intermitente, dependa de la red o compare floats con ==.
---

# Tests para código financiero

Referencia ejecutable: `scripts/example_tests.py` (8 tests deterministas comprobados; las 2 propiedades de `hypothesis` se validaron con muestreo aleatorio equivalente porque `hypothesis` no estaba instalado al crear la skill).

## Principios

1. **Todo cálculo financiero tiene al menos un caso calculado a mano**, con el cálculo escrito en el docstring del test. Si no puedes explicar el número esperado, no es un test: es una foto del resultado.
2. **Nunca copies la salida del código como valor esperado.** Calcula el esperado por separado (a mano, con la referencia mínima o con una identidad).
3. **No toques valores esperados para que un test pase.** Entiende por qué falla. Si el esperado era erróneo, corrígelo con explicación en el commit.
4. **Los tests no usan la red.** Providers mockeados o respuestas grabadas.
5. **Un test, una idea.** Nombres que digan la regla: `test_wacc_not_greater_than_g_raises`.

## Comparar números

```python
import math
assert math.isclose(result, expected, rel_tol=1e-9)        # magnitud relativa
assert math.isclose(result, expected, abs_tol=0.01)        # precio con céntimos
assert math.isclose(x, 0.0, abs_tol=1e-12)                 # cerca de cero: abs_tol obligatorio
```

- **Nunca `==` con floats.** Con valores cercanos a cero, `rel_tol` solo no basta: añade `abs_tol`.
- La tolerancia refleja la precisión de la entrada. Un caso calculado a mano con 1 decimal admite `abs_tol=0.1`.
- Para arrays: `numpy.testing.assert_allclose(a, b, rtol=1e-9)`.

## Qué cubrir en cada módulo

| Tipo | Ejemplo |
|---|---|
| Caso a mano | FCFF del año 1, EV y precio del ejemplo resuelto |
| Error de dominio | `WACC ≤ g` lanza `ValuationError` |
| Identidad | Sin deuda, `Equity = EV + Caja` |
| Frontera | `WACC − g` justo en el límite, crecimiento 0, ingresos 0 |
| Monotonía | WACC mayor → valor menor; g mayor → valor mayor |
| Simetría de tabla | El centro de la sensibilidad coincide con el caso base |
| Round-trip | Reverse DCF recupera el parámetro que generó el precio |
| Reproducibilidad | Misma semilla, mismo resultado (Monte Carlo) |

## Propiedades con hypothesis

```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=200, deadline=None)
@given(valid_inputs, st.floats(0.001, 0.02))
def test_higher_wacc_lowers_value(i, delta): ...
```

**Las estrategias deben generar solo entradas donde la propiedad es una ley:**

- La monotonía en WACC solo vale con FCFF positivos. Acota margen, crecimiento y CapEx para garantizarlo, o filtra con `.filter(...)`.
- Impón `WACC − g ≥ 1 pp` en la estrategia, no con `assume` repetido (descarta demasiadas muestras).
- Si hypothesis encuentra un contraejemplo, **primero decide si es un fallo del código o un rango de entrada ilegítimo**. No relajes la propiedad por reflejo.
- `deadline=None` en cálculos con numpy; si no, fallos intermitentes por tiempo.

## Golden tests de extracción

- 1–2 10-K reales en `tests/fixtures/` y su JSON de extracción esperado.
- El test compara campo a campo con tolerancia, y **falla si falta cualquier campo o llega un dato sin `source`**.
- Cuando cambie legítimamente el parser, regenera el golden con una orden explícita (`--update-golden`) y revisa el diff a mano. Nunca regeneración automática en CI.
- Un fragmento iXBRL mínimo escrito a mano para probar `scale`, `sign="-"` y contextos con dimensiones.

## Tests sin red

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "-m 'not network and not slow'"
markers = [
  "network: llama a servicios externos (excluidos por defecto)",
  "slow: tests lentos, por ejemplo con LibreOffice",
]
```

- Para HTTP, `httpx.MockTransport` o respuestas JSON grabadas en `tests/fixtures/`.
- Un test explícito de que, sin `SEC_USER_AGENT`, el cliente falla **antes** de salir a la red.
- Los tests de integración reales llevan `@pytest.mark.network` y se ejecutan solo a mano.

## Fixtures útiles

```python
@pytest.fixture
def base_inputs() -> Inputs:        # el caso base del ejemplo resuelto
    return Inputs(...)
```

Mantén un único caso base compartido, para que el ejemplo resuelto, la sensibilidad y los tests de puente hablen del mismo número.

## Antipatrones

| Antipatrón | Alternativa |
|---|---|
| `assert price == 24.638351693` | `math.isclose(price, 24.64, abs_tol=0.01)` |
| Valor esperado pegado de la salida | Cálculo a mano en el docstring |
| `random` sin semilla | `numpy.random.default_rng(seed)` |
| Test que depende de la fecha de hoy | Inyectar la fecha |
| Test que depende de la red | Mock o fixture |
| Una sola aserción gigante | Varias aserciones con nombre claro |
| Subir una tolerancia hasta que pase | Entender la diferencia |

## Cobertura

Objetivo: ≥ 85 % en `valuation/`, `validation/` y `analysis/`. Cobertura alta no sustituye a los casos a mano: un módulo puede estar «cubierto» y dar un DCF equivocado.
