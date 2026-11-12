---
name: valuation-modules-v2
description: Guía de implementación de los módulos de valoración adicionales Reverse DCF, simulación Monte Carlo, valoración por múltiplos con football field, FCFE y Residual Income/EVA como contraste del DCF, con fórmulas, reglas de cordura, estructura de módulos y casos de test. Úsala siempre que implementes o modifiques valuation/reverse_dcf.py, monte_carlo.py, multiples.py, football_field.py, fcfe.py o residual_income.py, o cuando el usuario pida "qué descuenta el mercado", rangos de valor, probabilidades, comparables o contrastar el DCF con otro método.
---

# Módulos de valoración v2

Amplía la sección 14 de `AGENTS.md`. Requisito previo: el motor DCF de la v1 estable y con tests. **Ningún módulo puede alterar el resultado del DCF base.**

Scripts de referencia con autotests (ejecútalos con `python3` desde `scripts/`):

- `reverse_dcf_example.py`: round-trip comprobado.
- `monte_carlo_example.py`: reproducibilidad y caso de varianza cero comprobados.
- `dcf_reference.py`: motor mínimo del que dependen los dos anteriores (copia del de `dcf-methodology`).

Son código de referencia; adáptalos a los modelos Pydantic del proyecto en lugar de copiarlos sin más.

## 1. Reverse DCF

**Idea:** fijar el precio de mercado y resolver qué parámetro hace que el DCF coincida.

- Parámetros que se pueden resolver: crecimiento inicial de ingresos (con fade hacia `g`), margen EBIT objetivo, o WACC implícito (la «rentabilidad exigida» que justifica el precio).
- Método: `scipy.optimize.brentq` sobre `f(x) = precio_modelo(x) − precio_mercado`.
- **Si `f(lo)` y `f(hi)` tienen el mismo signo, no hay solución en el rango:** devuelve `None` y explícalo. No fuerces un valor.
- Resuelve **un parámetro cada vez** con el resto fijo, y muestra los fijos.
- Compara el resultado con el histórico (CAGR 3 y 5 años, margen medio y máximo) y escribe una lectura neutral: «El precio implica X; la empresa creció Y».

**Tests:**

1. Round-trip: generar un precio con parámetros conocidos y recuperarlos (`|error| < 1e-6`).
2. Precio imposible → `None`.
3. Monotonía: precio mayor → parámetro implícito mayor.

## 2. Monte Carlo

**Idea:** convertir el DCF en una distribución en lugar de un número.

Distribuciones por defecto (todas configurables en la UI):

| Variable | Distribución | Notas |
|---|---|---|
| Desplazamiento del crecimiento | Normal(0, σ) | Se suma a la trayectoria base |
| Margen EBIT objetivo | Normal truncada | Acotada a [1 %, 60 %] |
| WACC | Normal truncada | Acotada a [3 %, 20 %] |
| g perpetuo | Triangular(mín, moda, máx) | Máx ≤ Rf |

Reglas:

- **Reproducible:** `numpy.random.default_rng(seed)`, semilla visible y fija por defecto.
- **Cordura:** descarta la simulación si `g ≥ WACC − 1 pp`, **cuéntalas y muestra el recuento**. Un descarte alto indica rangos mal elegidos.
- **Correlación opcional:** crecimiento y margen con correlación positiva moderada. Si la añades, usa una normal bivariante y documenta ρ.
- **Rendimiento:** 10 000 simulaciones por defecto. Si el motor es un bucle Python, aceptable para un MVP; si se vuelve lento, vectoriza `forecast` y `bridge` con numpy.
- **Salida:** media, mediana, P5/P25/P75/P95, `P(valor > precio mercado)` e histograma.
- Presenta el resultado como «distribución bajo estos supuestos», **no como probabilidad real de acierto**.

**Tests:**

1. Misma semilla → mismo resultado.
2. Varianza cero (y `g` degenerado) → reproduce el DCF determinista.
3. Ninguna simulación válida con `WACC − g < 1 pp`.
4. La media converge al aumentar N (comparar N=1 000 y N=20 000).
5. `P5 < mediana < P95`.

## 3. Múltiplos de comparables

```
EV/EBITDA, EV/EBIT, EV/Ventas        → valor de empresa implícito
P/E                                  → equity implícito
```

Procedimiento:

1. Lista de peers (por SIC, **siempre editable** por el usuario). Mínimo recomendado: 5; avisa si hay menos.
2. Calcula el múltiplo de cada peer con sus propios EV y métrica LTM. EV de cada peer = capitalización + deuda + leases (misma política que el DCF) + preferentes + minoritarios − caja.
3. **Excluye múltiplos negativos o no significativos** y muestra cuántos peers entran en cada múltiplo.
4. Usa **mediana y cuartiles**, no la media, por los valores atípicos.
5. Aplica Q1, mediana y Q3 a la métrica de la empresa: `EV_implícito = múltiplo × métrica`.
6. Pasa de EV a precio con **el mismo puente que el DCF** (`bridge.py`). No dupliques la lógica.

Cautelas a mostrar en la UI: diferencias de crecimiento, margen y riesgo entre empresa y peers; los múltiplos reflejan el sentimiento de mercado actual, el DCF no.

**Tests:** mediana y cuartiles con datos a mano; exclusión de múltiplos negativos; el puente coincide con el del DCF; con un solo peer, aviso.

## 4. Football field

Un rango (mín–máx) por método, más una línea con el precio actual:

| Método | Rango |
|---|---|
| DCF base | Mínimo y máximo de la tabla de sensibilidad WACC × g (celdas válidas) |
| Monte Carlo | P25–P75 (y opcionalmente P5–P95 más claro) |
| Múltiplos | Q1–Q3 de cada múltiplo |
| Mercado | Rango de 52 semanas, si hay datos |

Implementación con `plotly` (barras horizontales de rango). Cada barra debe poder mostrar su fuente y supuestos al pasar el ratón. Si un método no está disponible, no pongas una barra vacía: omítela y dilo.

## 5. FCFE (flujo al accionista)

```
FCFE = FCFF − Intereses × (1 − t) + Δ Deuda neta
Valor del equity = Σ FCFE_t / (1 + Ke)^t + TV_equity / (1 + Ke)^n
TV_equity = FCFE_(n+1) / (Ke − g)
```

- Requiere supuesto de estructura de deuda: por defecto, ratio D/(D+E) constante, de modo que `Δ Deuda neta = ratio × Δ(capital)`; documenta la opción.
- Descuento a **Ke**, no al WACC.
- Si FCFE da muy distinto del DCF con deuda estable, revisa primero los supuestos de deuda.
- No es adecuado con deuda que cambia mucho o FCFE negativo persistente.

**Test de identidad:** con deuda cero e intereses cero, `FCFE = FCFF` y, con `Ke = WACC`, el valor del equity coincide con el EV más la caja.

## 6. Residual Income y EVA

```
RI_t = NI_t − Ke × B_{t-1}
V0   = B0 + Σ RI_t / (1 + Ke)^t + TV_RI / (1 + Ke)^n
TV_RI = RI_(n+1) / (Ke − g_RI)         (g_RI ≤ g)

EVA_t = (ROIC_t − WACC) × Capital invertido_{t-1} = NOPAT_t − WACC × CI_{t-1}
```

- Verifica la relación de **clean surplus**: `B_t = B_{t-1} + NI_t − Dividendos_t − Recompras_t + Emisiones_t`. Si no se cumple, el modelo no es consistente.
- Útil cuando el flujo de caja es muy volátil o negativo; el valor contable ancla gran parte del valor.
- Es un modelo de contraste: no sustituye al DCF.

**Test:** con `ROE = Ke` constante, `RI = 0` y `V0 = B0`.

## 7. Contraste entre métodos

Calcula la divergencia `|V_método − V_DCF| / V_DCF` y avisa si supera el umbral configurable (por defecto 25 %). Una divergencia grande no dice cuál es correcto: dice **qué supuesto** investigar (normalmente WACC, g o el margen terminal).

## 8. Estructura de cada módulo

1. Función pura en `valuation/` con tipos Pydantic de entrada y salida.
2. Tests unitarios y, si procede, de propiedades.
3. Pestaña en la UI con sus supuestos editables.
4. Aportación al resumen y al football field.
5. Entrada en `docs/methodology.md` con fórmulas y decisiones.
6. Se puede desactivar sin romper el resto.
