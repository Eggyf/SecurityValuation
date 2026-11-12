---
name: valuation-sanity-check
description: Lista de revisión crítica para auditar un resultado de DCF antes de darlo por válido, comprobando peso del valor terminal, múltiplos implícitos, ROIC y reinversión terminal, crecimiento y márgenes frente al histórico, puente EV a equity y acciones diluidas. Úsala siempre al terminar cualquier cambio que afecte al motor DCF, a los supuestos por defecto o a la extracción de datos, y cuando el usuario pregunte si un valor "tiene sentido", "es razonable" o "por qué da tan alto o tan bajo".
---

# Revisión de coherencia de una valoración

Objetivo: detectar resultados que son **matemáticamente correctos pero económicamente absurdos**. Esta skill revisa; no corrige supuestos por su cuenta ni emite recomendaciones de inversión.

## Cómo usarla

1. Reúne los números del caso base: flujos, WACC, g, TV, EV, puente y precio.
2. Recorre los bloques A–F en orden y calcula cada métrica con la fórmula indicada.
3. Devuelve la tabla de avisos del final, con **la cifra concreta** que dispara cada uno.
4. Si hay un `ERROR`, dilo en la primera línea. No presentes un precio como fiable.

## A. Estructura del valor

| Comprobación | Fórmula | Alerta |
|---|---|---|
| Peso del TV | `PV(TV) / EV` | `> 75 %` aviso; `> 85 %` aviso fuerte |
| WACC frente a g | `WACC − g` | `< 1 pp` aviso; `≤ 0` ERROR |
| g frente a Rf | `g` vs `Rf` | `g > Rf` aviso |
| g absoluta | `g` | `> 3,5 %` aviso en economía desarrollada |

## B. Múltiplos implícitos

| Comprobación | Fórmula | Lectura |
|---|---|---|
| EV/EBITDA terminal implícito (Gordon) | `TV / EBITDA_n` | Comparar con múltiplos históricos y de peers; un valor muy superior al histórico indica TV inflado |
| g implícito en un múltiplo de salida | `g = (TV × WACC − FCFF_n) / (TV + FCFF_n)` | Debe ser coherente con la regla de g |
| EV/EBITDA actual implícito | `EV / EBITDA_0` | Contrastar con el múltiplo de mercado actual |
| P/E implícito | `Precio / EPS_0` | Contrastar con mercado si hay precio |

## C. Coherencia con el histórico

| Comprobación | Alerta |
|---|---|
| CAGR proyectado de ingresos frente al CAGR de 3 y 5 años | Proyectado `> 1,5 ×` el histórico, o `> 15 %` sostenido |
| Margen EBIT objetivo frente al máximo histórico | Objetivo por encima del máximo histórico sin justificación escrita |
| CapEx/ingresos y D&A/ingresos frente a la media | Desviación `> 30 %` relativa sin explicación |
| NWC/ingresos frente a la media | Cambios bruscos en el año 1 |
| Tasa impositiva proyectada | Fuera de [15 %, 30 %] sin justificación |
| Conversión de FCF (`FCFF / NOPAT`) | `> 100 %` sostenido (reinversión negativa) |

## D. Año terminal

| Comprobación | Fórmula | Alerta |
|---|---|---|
| Reinversión terminal | `(CapEx − D&A + ΔNWC) / NOPAT` | Debe ser ≈ `g / ROIC_terminal`; si es ≤ 0 con `g > 0`, aviso |
| ROIC terminal | `NOPAT_(n+1) / Capital invertido_n` | Muy por encima del WACC de forma indefinida: ventaja competitiva eterna (justificar). Muy por debajo: destrucción de valor |
| CapEx frente a D&A | `CapEx / D&A` | `< 1` en el año terminal con `g > 0`: aviso |
| Margen terminal | EBIT/ingresos | Por encima del mejor peer o del máximo histórico: aviso |

## E. Puente de EV a precio

- ¿Se restó toda la deuda financiera, incluidos los vencimientos corrientes?
- ¿Los leases se tratan igual en EBIT, WACC y puente?
- ¿Se restaron preferentes e intereses minoritarios?
- ¿La caja incluye inversiones a corto plazo y excluye la restringida?
- ¿Hay pensiones infrafinanciadas u otros pasivos tipo deuda que no estén en el puente? Si sí, aviso informativo.
- ¿Las acciones salen de la portada del 10-K más opciones/RSUs, no del promedio del P&L?
- ¿Las unidades coinciden (millones de USD y millones de acciones)?

## F. Contraste con el mercado y con otros métodos

- Si hay precio: `Upside = Valor / Precio − 1`. Un resultado a más de ±50 % del mercado **no es un error por sí mismo**, pero exige explicar qué supuesto lo provoca. Si está disponible Reverse DCF, úsalo para mostrar qué descuenta el mercado.
- Si hay otros métodos (FCFE, múltiplos, Monte Carlo), avisa si divergen más del 25 % del DCF.
- Comprueba que la sensibilidad WACC × g tiene al caso base en el centro.

## Cuándo es un ERROR (bloquea)

- `WACC ≤ g`.
- El balance de la extracción no cuadra (validaciones de `validation/` en `ERROR`).
- Acciones diluidas ≤ 0 o escala de unidades inconsistente.
- Equity negativo con precio por acción presentado sin advertencia.
- Falta cualquier input obligatorio del WACC.

## Formato de salida

```
Resultado: <OK | CON AVISOS | NO FIABLE>

| Nivel | Comprobación | Cifra | Umbral | Qué lo provoca |
|---|---|---|---|---|
| AVISO | Peso del TV | 82 % | 75 % | g 2,5 % y margen terminal 24 % |
| ERROR | WACC − g | 0,4 pp | 1,0 pp | WACC 7,4 % y g 7,0 % |

Supuestos que más mueven el valor: <lista corta, con la sensibilidad de cada uno>
Lo que NO se ha podido comprobar: <datos que faltaban>
```

## Reglas

- No cambies supuestos para "arreglar" un aviso. Reporta y propón opciones; decide el usuario.
- Cada aviso lleva su cifra. Nada de «parece alto».
- Nunca concluyas «comprar» o «vender».
- Si falta un dato para una comprobación, indícalo en «No se ha podido comprobar», no la omitas en silencio.
