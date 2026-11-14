---
name: app-audit
description: Lista de auditoría completa de la app de valoración DCF desde 10-K, con comprobaciones por área (extracción iXBRL, validaciones, supuestos y datos externos, motor DCF, resultados, Reverse DCF, scores de calidad, exportación a Excel, UI, seguridad, tests y reproducibilidad), método de verificación independiente, niveles de severidad y formato de informe. Úsala siempre que el usuario pida auditar, revisar, validar o comprobar que la app calcula bien, o antes de dar por buena una versión, y cuando haya dudas de que una cifra, un score o un aviso sea correcto.
---

# Auditoría de la app

Complementa `valuation-sanity-check` (que revisa **una valoración concreta**) con la revisión de **la app entera**: que cada módulo haga lo que dice y que los números sean correctos. Casos con respuesta conocida en `references/verification-vectors.md`.

## Principios de auditoría

1. **Verificación independiente.** No des por bueno un número porque el código lo produzca. Recalcúlalo por otra vía (a mano, con `dcf-methodology/scripts/dcf_reference.py`, con un script propio) y compara.
2. **Evidencia, no impresión.** Cada hallazgo lleva archivo y línea, la cifra observada y la esperada, y cómo reproducirlo.
3. **Prueba que los controles saltan.** Una validación que nunca ha fallado no está probada. Perturba un dato (activos +2 %, cambiar escala, quitar un campo) y comprueba que aparece el `WARNING` o `ERROR` esperado.
4. **No corrijas.** Reporta y propone el arreglo en texto. Decide el usuario.
5. **Di lo que no pudiste comprobar.** Sin red no se verifican datos externos; sin un 10-K de prueba no se verifica extracción. Anótalo.
6. **Sin recomendaciones de inversión.** Se audita el software, no la empresa.

## Niveles de severidad

| Nivel | Significa | Ejemplos |
|---|---|---|
| BLOQUEANTE | Da una cifra errónea o engañosa sin avisar | Escala mal aplicada, `WACC ≤ g` sin bloqueo, signo del CapEx invertido |
| ALTO | Puede sesgar el valor de forma material o incumple una regla del `AGENTS.md` | Acciones del P&L en vez de cover + TSM, dato externo sin fuente, fórmula dentro de la UI |
| MEDIO | Riesgo o incoherencia con impacto acotado | Umbral sin justificar, aviso sin cifra, tolerancia demasiado holgada |
| BAJO | Mejora de claridad o mantenimiento | Texto de ayuda confuso, nombre ambiguo |

## Áreas y comprobaciones

### A. Extracción del 10-K

- **A1** Escala: `scale` aplicado (3 = miles, 6 = millones) y todo normalizado a MM USD.
- **A2** Signo: `sign="-"` respetado una sola vez. CapEx con el signo documentado.
- **A3** Solo hechos **sin dimensiones** para totales consolidados.
- **A4** Periodo identificado por `endDate`; ejercicios consecutivos; duración de ~1 año.
- **A5** Reexpresiones: prevalece la cifra del 10-K más reciente que la contiene.
- **A6** Cada cifra tiene `source`, `period_end`, unidad y confianza. Un campo ausente es `None`, no `0`.
- **A7** Fallback PDF marcado con menor confianza y avisado en la UI.
- **A8** Conceptos propios de la empresa (`prefijo:Concepto`) mapeados con registro.
- **A9** Con modo online: descarga el 10-K correcto (`10-K`, no `10-K/A`), el más reciente o el pedido.
- **A10** Unidades correctas: no mezclar `USD`, `shares` y `USD/shares`.

### B. Validaciones

- **B1** Balance cuadra (tolerancia < 0,5 %), margen bruto, NI del P&L = NI del flujo, escala consistente, ejercicios consecutivos.
- **B2** Cada validación salta con un dato perturbado (prueba de mutación).
- **B3** Un `ERROR` bloquea la valoración y la UI no muestra precio.
- **B4** Faltan validaciones recomendadas: variación de caja del flujo ≈ variación en balance (± FX); deuda sin doble conteo (total frente a corriente + no corriente); acciones > 0.

### C. Supuestos y datos externos

- **C1** Rf desde FRED `DGS10`: la serie viene **en porcentaje** (4,25 = 4,25 %): ¿se convierte a fracción? ¿Se usa la última observación válida (los días sin dato aparecen como `.`)? ¿Se muestra la fecha?
- **C2** ERP de Damodaran: se muestra con su **fecha** y es editable.
- **C3** Beta: si se usa beta por industria, ¿se **desapalanca y reapalanca** a la estructura de la empresa? ¿Cómo se asigna la industria (SIC → Damodaran)?
- **C4** Kd = intereses / deuda: ¿deuda media o final? ¿Incluye intereses de leases con deuda que los excluye? Cotas razonables (por ejemplo `Kd ≥ Rf`) y aviso si sale absurdo.
- **C5** Tasa impositiva: acotada [15 %, 30 %]; se distingue la del NOPAT de la del escudo fiscal.
- **C6** Acciones: ¿cover del 10-K + método de la acción de tesorería (opciones y RSUs), o promedio ponderado del P&L? Lo primero es lo correcto.
- **C7** Market cap frente a `precio × acciones`: ¿coherentes? ¿Cuál se usa en los pesos del WACC?
- **C8** Antigüedad de los datos visible (edad del 10-K, fecha del precio). Aviso si el 10-K tiene más de ~9 meses y no se actualizó con el último 10-Q.
- **C9** Inputs obligatorios: la app bloquea con lista clara. Comprobar que no se exige el precio para calcular EV si solo hace falta para upside.
- **C10** Sin red por defecto; descargas solo con modo online; caché con TTL; claves solo por entorno.
- **C11** Todo supuesto editable y con su procedencia.

### D. Motor DCF

- **D1** FCFF = NOPAT + D&A − CapEx − ΔNWC; ΔNWC con partidas operativas (sin caja ni deuda).
- **D2** SBC tratado como gasto por defecto; si hay toggle de add-back, advertencia.
- **D3** Tasa del NOPAT normalizada, no la efectiva de un año.
- **D4** Valor terminal: `FCFF_(n+1)/(WACC − g)`; ¿FCFF terminal normalizado (reinversión = g/ROIC)? `CapEx ≥ D&A` en el año terminal.
- **D5** Múltiplo de salida: ¿se muestra el `g` implícito? Gordon: ¿se muestra el múltiplo implícito?
- **D6** Descuento: fin de año por defecto; con mitad de año el TV de Gordon se descuenta a `n − 0,5`.
- **D7** Puente: caja + inversiones CP − deuda − leases (si son deuda, y coherente con el WACC) − preferentes − NCI.
- **D8** Sensibilidades: centro = caso base **exacto**; celdas con `WACC − g < 1 pp` como `n/d`.
- **D9** `WACC > g` impuesto; `g ≤ Rf` avisado.
- **D10** Determinismo: mismas entradas, mismo resultado (ejecutar dos veces).
- **D11** Contraste numérico con `dcf_reference.py` y los vectores.
- **D12** Función pura: sin I/O ni estado global dentro de `valuation/`.

### E. Resultados y avisos

- **E1** Aviso TV > 75 % del EV, con la cifra.
- **E2** «Resultado no razonable»: ¿qué regla concreta lo dispara? Debe ser explícita y con umbral (ver `valuation-sanity-check`).
- **E3** Upside = `valor / precio − 1`, signo y unidades correctos.
- **E4** Tabla de proyección coherente con el motor (no recalculada en la UI).
- **E5** Disclaimer siempre visible.

### F. Reverse DCF

- **F1** Round-trip: recupera el parámetro que generó un precio.
- **F2** Sin solución en el rango → mensaje claro, no un número.
- **F3** Rango de búsqueda razonable y comparación con el histórico (CAGR 3/5 años, márgenes).
- **F4** Mantiene fijos el resto de supuestos y los muestra.

### G. Calidad

- **G1** Piotroski: 9 criterios con definiciones correctas (ROA sobre activos iniciales).
- **G2** Altman: variante documentada (Z'' para no manufactureras); **no aplicable a financieras**.
- **G3** Beneish: 8 variables y umbral visible; requiere dos ejercicios.
- **G4** Entrada faltante → `None` con lista, nunca cero.
- **G5** Desglose por componente visible.
- **G6** Ratios: ROIC, DuPont, DSO/DIO/DPO, cobertura, conversión de FCF con fórmula documentada y promedios de balance donde corresponda.

### H. Exportación a Excel

- **H1** Fórmulas vivas, no valores; rangos con nombre; inputs en azul.
- **H2** Recalcular con LibreOffice: sin `#REF!`/`#DIV/0!`/`#NAME?`; precio igual al de la app (`abs_tol=0,01`).
- **H3** Cambiar un input en el libro cambia el resultado en la dirección esperada.

### I. UI

- **I1** Sin fórmulas financieras en `ui/`.
- **I2** `ERROR` → `st.stop()`; sin precio.
- **I3** Estado de sesión con prefijo y sin pérdidas al cambiar de pestaña.
- **I4** Formato en español y `n/d` para ausentes, nunca `0`.
- **I5** El significado no depende solo del color.

### J. Seguridad y privacidad

- **J1** Claves en entorno; nunca en logs, UI ni Excel exportado.
- **J2** `.env` no versionado; `.cache/` en `.gitignore`.
- **J3** `User-Agent` de EDGAR por entorno; límite de peticiones respetado.
- **J4** Nada sale a la red sin modo online.
- **J5** Sin subida de datos del usuario a terceros.

### K. Tests

- **K1** Casos a mano en cada fórmula; propiedades de monotonía.
- **K2** Tests sin red; marcadores `network` y `slow`.
- **K3** Golden tests con **varios sectores** (por ejemplo tecnología, comercio, industria) y ejercicios fiscales distintos del año natural.
- **K4** Valores esperados no «pegados» de la salida del código.
- **K5** Cobertura ≥ 85 % en `valuation/`, `validation/` y `analysis/`; **cobertura no equivale a corrección**.

### L. Reproducibilidad

- **L1** Se puede guardar o exportar el conjunto de entradas (datos, supuestos, fuentes, fechas, versión de la app) y reproducir el resultado exacto.
- **L2** Semillas fijas en cualquier simulación.

## Procedimiento

1. **Alcance:** todo o un área (A–L). Lee `AGENTS.md` y la estructura del repo.
2. **Reconocimiento:** localiza el código de cada comprobación; anota archivo y función.
3. **Ejecuta** tests, `ruff`, `mypy` y registra el resultado.
4. **Verifica con vectores** (`references/verification-vectors.md`): ejecuta el motor real con entradas conocidas y compara con los valores esperados.
5. **Mutaciones:** para cada validación, crea un script de prueba en `docs/audit/scratch/` que perturbe un dato y confirme que salta el control. No modifiques el código de la app.
6. **Contraste independiente** del motor DCF con `dcf_reference.py` y con tu propio cálculo.
7. **Informe** en `docs/audit/AAAA-MM-DD-<alcance>.md` y resumen en el chat.

## Formato del informe

```
# Auditoría <alcance> — <fecha>
Veredicto: <APTA | APTA CON RESERVAS | NO APTA>

## Resumen
<3–5 líneas: qué funciona, qué no, riesgo principal>

## Hallazgos
| ID | Severidad | Área | Archivo:línea | Observado | Esperado | Cómo reproducir | Arreglo propuesto |

## Comprobaciones superadas
<lista de IDs verificados con evidencia breve>

## No verificado
<qué faltó y por qué>

## Mejoras sugeridas
<ordenadas por impacto en la calidad de la valoración>
```

`APTA` solo si no hay BLOQUEANTE ni ALTO abiertos.
