---
name: sec-10k-extraction
description: Cómo extraer estados financieros de un Form 10-K (HTML/iXBRL) y normalizarlos con trazabilidad, mapeando conceptos us-gaap a los campos del proyecto, manejando signos, escala, contextos, dimensiones, reexpresiones y años fiscales. Úsala siempre que toques extraction/, normalization/, mapping.py, el parseo de iXBRL o PDF del 10-K, o cuando una cifra extraída parezca incorrecta, falte o tenga el signo o la escala equivocados.
---

# Extracción de datos de un 10-K

Complementa la sección 6 de `AGENTS.md`. La tabla completa de conceptos está en `references/xbrl-mapping.md`: léela antes de añadir o cambiar un mapeo.

## Principios

1. **iXBRL primero.** Un 10-K moderno es HTML con etiquetas `ix:nonFraction`. Cada cifra trae concepto, contexto, unidad, escala y signo. Eso es más fiable que leer tablas.
2. **Texto/PDF solo como fallback**, con `source="text_fallback"` y confianza menor.
3. **Nada sin fuente.** Cada dato guarda `value`, `unit`, `scale`, `period_end`, `source` (concepto XBRL o sección/página) y `confidence`.
4. **Un LLM puede ayudar a localizar o clasificar texto ambiguo, nunca a producir una cifra** que entre al modelo sin pasar por validación.

## Cómo leer un hecho iXBRL

Cada `ix:nonFraction` tiene, entre otros:

- `name`: concepto (por ejemplo `us-gaap:Revenues`).
- `contextRef`: apunta a un contexto con el periodo (`instant` o `startDate`/`endDate`) y, si existen, **dimensiones** (segmentos, productos, regiones).
- `unitRef`: `USD`, `shares`, `USD/shares`, `pure`.
- `scale`: potencia de 10 aplicada al texto mostrado (3 = miles, 6 = millones).
- `sign="-"`: indica que el valor real es negativo aunque se muestre sin signo.
- `format`: cómo se escribe el número en pantalla (por ejemplo `ixt:num-dot-decimal`, `ixt:zerodash` para un guion que significa cero).

```
valor_real = (número_mostrado) × 10^scale × (−1 si sign="-" else 1)
```

## Reglas de selección de hechos

- **Totales consolidados:** usa solo hechos **sin dimensiones** en su contexto. Los hechos con dimensiones son desgloses (segmentos, productos); no los uses como total.
- **Duración vs instante:** P&L y flujo de caja son duraciones; balance es instante. Comprueba que la duración sea de un ejercicio completo (≈ 350–380 días; 52/53 semanas).
- **Ejercicio actual vs comparativos:** un 10-K incluye varios años. Identifica el periodo por `endDate`, no por posición.
- **Duplicados:** el mismo hecho puede aparecer varias veces (resumen, estados, notas). Si los valores coinciden, quédate con uno; si difieren, marca `WARNING` y conserva ambos en el registro.
- **Reexpresiones:** si un ejercicio previo se reexpresó, usa la cifra del **10-K más reciente** que la contiene, y anota que fue reexpresada.
- **Año fiscal ≠ año natural:** etiqueta por fecha de cierre real (`period_end`), no por `fy` de la API, que puede ser engañoso.
- **Unidades:** separa `USD`, `shares` y `USD/shares`. No mezcles acciones con dólares.

## Qué hacer con cada categoría

**Conceptos estándar.** Usa la lista de `references/xbrl-mapping.md`. Para cada campo hay varios conceptos posibles; recórrelos en orden de preferencia y registra cuál usaste.

**Conceptos propios de la empresa** (`prefijo:Concepto`, por ejemplo `aapl:...`). Si el campo requerido solo existe como concepto propio, mapéalo a mano en `mapping.py` con un comentario que explique el criterio y el 10-K de origen.

**Cifras calculadas.** Si un total (por ejemplo `GrossProfit`) no está reportado, calcúlalo desde sus componentes y márcalo `source="derived"`. No lo trates como dato reportado.

**Notas del 10-K que hacen falta para el DCF:**

| Dato | Dónde buscarlo |
|---|---|
| Opciones y RSUs vivas | Nota de compensación basada en acciones |
| Tasa impositiva efectiva y estatutaria | Nota de impuestos a las ganancias |
| Vencimientos y tipos de la deuda | Nota de deuda |
| Pasivos por arrendamientos | Nota de arrendamientos |
| Partidas no recurrentes | MD&A (Item 7) y notas de reestructuración/deterioro |
| Segmentos | Nota de información por segmentos |
| Acciones en circulación recientes | Portada del 10-K |

## Estructura del 10-K (para localizar texto)

- Item 1: negocio. Item 1A: factores de riesgo.
- Item 7: MD&A (explicaciones de márgenes, partidas no recurrentes, liquidez).
- Item 7A: riesgo de mercado (tipos de interés, divisas).
- Item 8: estados financieros y notas.
- Item 9A: controles internos.

## Normalización

1. Pasar todo a **millones de USD** en la frontera (`scale` aplicado, unidades convertidas).
2. Un campo ausente es `None`, nunca `0`.
3. Las deudas, el capex y los pagos mantienen la convención que defina `models/`; documenta el signo de cada campo en su docstring.
4. Después de normalizar, ejecuta las validaciones de `validation/` (balance cuadra, gross profit, NI coincide, etc.). Un `ERROR` bloquea la valoración.

## Diagnóstico rápido cuando algo no cuadra

| Síntoma | Causa probable |
|---|---|
| Cifra 1.000 veces mayor o menor | `scale` mal aplicado o mezcla de miles y millones |
| Signo invertido | Se ignoró `sign="-"` o se aplicó dos veces |
| Total no coincide con el reportado | Se tomó un hecho con dimensión |
| Año equivocado | Se identificó el periodo por posición en lugar de `endDate` |
| `None` en un campo habitual | La empresa usa un concepto alternativo o propio |
| Dos valores distintos para lo mismo | Reexpresión o hecho de una nota con otro perímetro |
| Acciones absurdas | Se usó `shares` en vez de `USD/shares`, o la escala |

## Tests

- Un 10-K real en `tests/fixtures/` con el JSON de extracción esperado (golden test).
- Un test que falla si algún dato llega sin `source`.
- Un test de escala y signo con un fragmento iXBRL mínimo escrito a mano.
- Un test de contexto con dimensiones: el total consolidado no debe tomar el valor del segmento.
