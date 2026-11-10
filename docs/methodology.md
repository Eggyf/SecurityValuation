# Metodología

Registro de las decisiones metodológicas no obvias del proyecto (AGENTS.md §8).
Cada entrada indica la decisión, su justificación y su estado.

## Convenciones generales

| Tema | Decisión | Estado |
|---|---|---|
| Unidad interna | Millones de la moneda de reporte (por defecto USD) | Firmada (AGENTS.md §2.6) |
| Porcentajes | Se almacenan como fracciones (`0.08` = 8 %); la UI los formatea | Firmada (AGENTS.md §8) |
| Convención de descuento | Fin de año por defecto; mitad de año activable | Firmada (AGENTS.md §7.5) |
| Comparación de flotantes | `math.isclose` / tolerancias; nunca `==` | Firmada (AGENTS.md §8) |
| Modelo de cifra | `Fact` (`models/fact.py`) guarda el valor original con unidad, escala, periodo y `SourceRef`; la normalización a millones ocurre en `normalization/` vía `Fact.to_scale()` | Firmada (2026-11-10) |
| Fuente obligatoria | iXBRL exige concepto XBRL; texto exige sección/página; la confianza (`HIGH/MEDIUM/LOW`) se deriva del tipo de fuente, no se pide aparte | Firmada (2026-11-10) |
| Estructura de estados | Un modelo por estado y ejercicio (listas ordenadas y alineadas); las comprobaciones contables («3 años consecutivos», A = P + P) viven en `validation/`, no en el modelo | Firmada (2026-11-10) |

## Pendientes de decidir

Se resolverán al implementar cada módulo, no antes:

- **Modelo de dinero:** resuelto: `Fact` guarda el valor original + escala y la
  normalización a millones ocurre en `normalization/` (ver decisiones firmadas).
- **Leases operativos:** tratarlos como deuda y usar EBIT antes del coste de lease
  implícito (o la alternativa), documentando la elección.
- **CapEx terminal:** `Reinversión = g / ROIC` frente a la restricción simple `CapEx ≥ D&A`.
- **Acciones diluidas:** método de la acción de tesorería con opciones/RSUs del 10-K.
- **Escala en la extracción:** detección de `scale` por estado financiero y validación de
  consistencia entre estados.
