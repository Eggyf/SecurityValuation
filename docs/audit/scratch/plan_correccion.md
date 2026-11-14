# Plan de corrección tras la auditoría de la app DCF

*Basado en el informe `2026-11-13-full.md` (veredicto: NO APTA). Incluye una lectura crítica del informe y paquetes de trabajo con prompts listos para opencode.*

## 1. Lectura del informe

El informe es útil: encuentra errores reales que afectan a la cifra final. Pero conviene leerlo con cuatro matices antes de actuar.

**Lo que está sólido**

- H1 a H3 son bugs claros y baratos de arreglar: el umbral del 75 % comparado como 75,0, el centro de la sensibilidad que no coincide con el caso base y la UI que valora aunque haya un ERROR.
- H13 es un doble conteo de dilución: usa las acciones diluidas medias del P&L como si fueran básicas y luego aplica la acción de tesorería encima. Infla las acciones y baja el precio.
- H17 es un error de fórmula (deuda neta calculada con activos circulantes en vez de caja).

**Matices importantes**

1. **El auditor no pudo ejecutar nada.** El propio informe dice que no tuvo shell: no corrió tests, ruff, mypy, los scripts de mutación ni los vectores. Por tanto la lista «Comprobaciones superadas» es en realidad **«revisadas por lectura»**. Hay incluso una contradicción: B2 figura como superada y, a la vez, «no se ejecutaron los scripts de mutación». El veredicto NO APTA es correcto, pero un futuro APTA solo valdrá si se ejecuta todo.
2. **Causa probable (error mío):** el `auditor.md` que te di empezaba con una regla que denegaba *todas* las acciones. En la V2 la acción `execute` forma parte de ese conjunto, y denegarla puede retirar la herramienta de shell. Te dejo versiones corregidas de `auditor.md` y `reviewer.md` sin esa regla global (deniegan solo edición, web, subagentes y shell no listado). Compruébalo al empezar la próxima auditoría: debe poder ejecutar `uv run pytest --co -q`.
3. **Hay hallazgos mal calibrados o con arreglos que empeorarían el producto** (ver sección 2).
4. **Falta un hallazgo transversal:** varios problemas (H7, H8, H13, H14, H18, H22) viven en `ui/app.py`, que supera las mil líneas y contiene lógica financiera. Eso incumple la regla de que la UI no calcula finanzas, y es la causa raíz de que los mismos errores aparezcan duplicados (H8 y H10 son el mismo cálculo de Kd en dos sitios).

## 2. Reclasificación y correcciones al informe

| ID | Informe | Mi lectura |
| --- | --- | --- |
| H1 | BLOQUEANTE | Bug real. Pero el ejemplo de reproducción es erróneo: con el umbral correcto (0,75), un TV del 74,9 % **sigue siendo «razonable»**. El fallo se ve con un TV del 80 %. Usa 80 % en el test. |
| H4 y H5 | BLOQUEANTE y ALTO | Son el mismo problema: el módulo de Excel exporta valores estáticos y con un D&A de relleno (`rev * 0,05`). Trátalos como un solo paquete. |
| H7 | ALTO | Más bien MEDIO: el informe mismo dice que la conversión a fracción ocurre en `_pct`. El problema real es mostrar la fecha y la procedencia. |
| H8 y H10 | ALTO y ALTO | Duplicados. Hay que calcular Kd **una sola vez, en el motor**, no en la UI. Además, `abs(interest)` puede **tapar un error de signo en la extracción**: los intereses suelen venir en positivo en el XBRL, así que un −259 sugiere que el signo se está interpretando mal en `_parse_value`. Investiga el origen antes de poner `abs()`. |
| H9 | ALTO | Es más una limitación de uso que un error. Y el arreglo propuesto está incompleto: el WACC necesita el valor de mercado del equity. Sin precio hace falta otra vía (D/E objetivo introducido por el usuario o de la industria). |
| H11 | ALTO | Peor de lo que parece: devuelve OK **sin comprobar nada**, así que la UI muestra un ✅ falso. Hasta implementarlo, debe devolver «no verificada», no OK. Y la descripción de la app que me pasaste afirma que esa validación existe. |
| H16 | MEDIO | El arreglo propuesto (recortar el rango de búsqueda a \[−5 %, 25 %\]) **empeora el producto**: justo en las acciones de alto crecimiento la respuesta útil es «el mercado descuenta más del 25 %». Mejor: permitir al solver salir de los límites de `Assumptions` e informar «supera el rango plausible del modelo». |
| H20 | MEDIO | BAJO: el propio informe reconoce que `terminal_value_gordon` ya lanza error. Solo es un mensaje tardío. |
| H21 | MEDIO | Mezcla dos cosas. La primera mitad dice que el descuento del TV es correcto. Lo pendiente es la fecha de valoración, que va unida a actualizar con el último 10-Q (paquete aparte, no urgente). |
| H22 | MEDIO | Probablemente BAJO: tu resumen dice que la ERP precargada sale como \~4 %, así que la unidad parece correcta. Lo sensato es una **guarda de rango** (por ejemplo ERP entre 2 % y 10 %), no una investigación larga. |

**Patrón común:** casi todos los errores de unidad (Rf, ERP, Kd) se previenen con una función que valide rangos plausibles al entrar un dato y avise si algo está fuera. Una sola guarda para todos.

**Un riesgo que el informe no menciona:** para empresas con varias clases de acciones (por ejemplo, las de Alphabet, Meta o Berkshire), las acciones de la portada del 10-K se reportan **con dimensiones**, y tu extracción descarta los hechos dimensionales. Al arreglar H13, esos datos hay que tratarlos como excepción y sumar las clases.

## 3. Orden de trabajo

El orden evita rehacer trabajo: primero las cifras erróneas, luego las entradas, después el motor y por último lo que lo refleja (Excel).

| Orden | Paquete | Hallazgos |
| --- | --- | --- |
| 0 | Reparar al auditor y fijar la línea base | (sección 1) |
| 1 | Cifras erróneas y falsa seguridad | H1, H2, H3, H11 |
| 2 | Acciones | H13 y validación de acciones > 0 |
| 3 | Entradas y WACC | H6, H7, H8, H10, H22, H9, H19 |
| 4 | Motor: valor terminal | H15, H20 |
| 5 | Excel | H4, H5, H24 |
| 6 | Calidad y Reverse DCF | H14, H16, H17, H18 |
| 7 | Orden y limpieza | H12, H23, H25, refactor de la UI |

El Excel va después del motor a propósito: replica sus fórmulas, y si el valor terminal cambia (paquete 4) habría que reescribirlo.

**Regla para todos los paquetes:** empieza en modo plan, un cambio verificable por vez, tests primero, y al terminar ejecuta `/check` y después `/audit <área>` del paquete.

## 4. Paquetes con sus prompts

### Paquete 0: línea base

Reemplaza `auditor.md` y `reviewer.md` por las versiones corregidas, reinicia opencode y comprueba que `/agents` muestra ambos. Asegúrate de que `.opencode/skills/dcf-methodology/scripts/dcf_reference.py` existe en el repositorio: el informe dice que no lo encontró.

```
/audit tests
```

Criterio de salida: el informe indica los resultados reales de `pytest`, `ruff` y `mypy`, y ejecuta los scripts de mutación y los vectores. Con eso sabrás qué pasa de verdad hoy.

### Paquete 1: cifras erróneas y falsa seguridad

```
Lee AGENTS.md y las skills finance-testing y streamlit-ui. Trabaja en modo plan primero.

Corrige estos cuatro problemas, cada uno con su test escrito antes:

1. DCFResult.is_reasonable compara una fracción con 75.0. El umbral debe ser 0.75. Tests: TV 80 % -> False; TV 74,9 % -> True.
2. sensitivity_wacc_growth usa growth_values[0] como crecimiento inicial. Recibe el crecimiento inicial base como parámetro. Test: la celda central de la tabla es EXACTAMENTE el precio del caso base (math.isclose, rel_tol=1e-12).
3. La UI ejecuta run_dcf aunque validate_all tenga ERROR. Crea una función pura can_run_valuation(validation_results) fuera de ui/, con test, y úsala para deshabilitar el botón y llamar a st.stop().
4. validate_net_income_consistency devuelve OK sin comparar. Mientras no esté implementada debe devolver NOT_CHECKED (aviso visible, no OK). Impleméntala: NI del P&L frente a NI del flujo de caja, tolerancia 0,5 %, y test de mutación.

No cambies valores esperados de tests existentes. Al terminar ejecuta /check y resume qué cambió.
```

### Paquete 2: acciones

```
Lee AGENTS.md y sec-10k-extraction. Modo plan primero.

Problema: la UI usa las acciones diluidas medias del P&L como acciones básicas y luego aplica el método de la acción de tesorería (doble dilución).

Haz esto:
1. Extrae las acciones de la portada del 10-K (dei:EntityCommonStockSharesOutstanding). Los hechos de la portada pueden tener dimensiones cuando hay varias clases de acciones: exceptúalos del filtro de dimensiones y suma las clases. Guarda fuente y fecha.
2. Aplica la acción de tesorería sobre esas acciones básicas.
3. Añade la validación acciones > 0.
4. Si no hay dato de portada, no sustituyas por el promedio diluido en silencio: pide el dato.

Tests: caso a mano con 100 básicas, 10 opciones a 20 y 4 RSUs con precio 50 = 110,0 acciones; con precio 15 = 104; empresa con dos clases de acciones. Ejecuta /check.
```

### Paquete 3: entradas y WACC

```
Lee AGENTS.md y dcf-methodology. Modo plan primero.

Objetivo: sacar de ui/app.py la lógica financiera de Rf, ERP y Kd y moverla a funciones puras (por ejemplo assumptions/ o valuation/wacc.py), con tests.

1. Rf desde FRED: salta las observaciones con valor '.', usa la última válida, convierte de porcentaje a fracción y devuelve también su fecha. La UI muestra la fecha.
2. Guarda de rangos plausibles para todo porcentaje de entrada: Rf 0-15 %, ERP 2-10 %, Kd 0-25 %, tasa impositiva 0-50 %. Fuera de rango, aviso con la cifra.
3. Kd = intereses / deuda media (si hay dos balances). Un solo cálculo, en el motor. Si Kd < Rf, aviso. El tope de 15 % ya no es silencioso: se avisa.
4. ANTES de usar abs() para los intereses, investiga por qué llega -259 en NVDA: los intereses suelen venir en positivo en el XBRL. Si el signo se interpreta mal en _parse_value, arréglalo en origen y añade un test con un fragmento iXBRL mínimo.
5. Permite calcular el EV sin precio de mercado ofreciendo un D/E objetivo editable para los pesos del WACC. El precio se exige solo para upside y para la dilución con opciones.
6. Documenta en docs/methodology.md la política de leases (H19) y aplícala igual en EBIT, WACC y puente.

Tests: vectores WACC = 8,30 % (Rf 4,25, beta 1,1, ERP 5, E 3000, D 1000, Kd 5, t 21) y Kd = 5,0 % con intereses 40 y deuda media 800. Ejecuta /check.
```

### Paquete 4: valor terminal

Antes de lanzarlo, **tienes que decidir un parámetro**: el ROIC terminal. Opciones habituales: igual al WACC (sin exceso de rentabilidad, la más conservadora), o una convergencia desde el ROIC actual hacia el WACC. Elige una y anótala.

```
Lee AGENTS.md y dcf-methodology (sección 4). Modo plan primero.

1. Calcula el FCFF terminal normalizado: NOPAT_(n+1) = NOPAT_n x (1+g); reinversión = g / ROIC_terminal; FCFF_(n+1) = NOPAT_(n+1) x (1 - reinversión). El ROIC terminal es un supuesto editable con el valor por defecto que defina el usuario.
2. Rellena reinvestment_rate en DCFResult. Comprueba CapEx >= D&A en el año terminal y avisa si no.
3. Muestra el EV/EBITDA implícito del valor terminal (Gordon) y el g implícito si se usa múltiplo de salida.
4. Valida WACC > g al empezar run_dcf, con un mensaje claro.

No cambies el comportamiento del caso base sin un test que lo documente: si el valor cambia, muestra el antes y el después. Ejecuta /check.
```

### Paquete 5: Excel

```
Lee AGENTS.md y excel-live-formulas. Modo plan primero.

Reescribe export/excel.py para generar fórmulas vivas, rangos con nombre e inputs en azul, siguiendo scripts/build_dcf_workbook.py de la skill. La hoja de proyección usa el resultado real del motor (hoy el D&A es un relleno rev * 0,05). Incluye el valor terminal normalizado del paquete 4.

Quita la excepción de mypy para dcf_app.export.* y corrige los tipos.

Tests: las celdas de Proyeccion empiezan por '='; todos los inputs tienen nombre definido; paridad app/Excel recalculando con LibreOffice (marcado slow), precio igual con abs_tol=0,01; sin errores de celda. Ejecuta /check.
```

### Paquete 6: calidad y Reverse DCF

```
Lee AGENTS.md, quality-scores y valuation-modules-v2. Modo plan primero.

1. Piotroski sin activos de t-2: devuelve None con la lista de lo que falta, no un proxy con t-1.
2. Ratios: deuda neta = deuda - caja; ROIC con la tasa impositiva normalizada del modelo y capital invertido medio. Documenta la definición.
3. Altman: selector de variante (Z, Z', Z'') con la elegida visible, y no aplicable a financieras.
4. Reverse DCF: el solver NO debe recortar su búsqueda a los límites de Assumptions. Si el crecimiento implícito supera el rango plausible, informa 'el mercado descuenta más de X %', no 'no produce valores válidos'. Mantén el mensaje claro de sin solución dentro del rango de búsqueda.

Tests: Piotroski con dos ejercicios -> None; round-trip del Reverse DCF; precio 1.000.000.000 -> mensaje de sin solución. Ejecuta /check.
```

### Paquete 7: orden y limpieza

```
Lee AGENTS.md y streamlit-ui. Modo plan primero.

1. Añade las validaciones que faltan: variación de caja del flujo frente al balance (con tolerancia por divisas) y deuda sin doble conteo (total frente a corriente más no corriente). Cada una con test de mutación.
2. Prefijo dcf_ en todas las claves de st.session_state, creadas en una función init_state().
3. Revisa el fallback PDF tras el cambio sin confirmar (segunda pasada con 'item 8' en las primeras 10 líneas): ejecuta los golden tests de PDF con msft_statements.pdf y nvda_statements.pdf. Si fallan, revierte esa condición.
4. Plan de refactor (solo el plan, no lo ejecutes): cómo trocear ui/app.py en una pestaña por módulo y sacar toda la lógica financiera a funciones puras. Muéstrame el plan.
```

## 5. Cuándo darlo por bueno

- `/audit` completo ejecutado de verdad: tests, ruff y mypy con resultados reales, y los vectores de verificación contrastados.
- Ningún BLOQUEANTE ni ALTO abierto.
- La descripción de la app coincide con lo que hace: cada validación anunciada se ejecuta de verdad.
- Después, y solo después, vuelve a mirar las mejoras que no son correcciones: actualizar con el último 10-Q, guardar y recargar una valoración, escenarios, gráfico tornado y los módulos v2 (Monte Carlo, múltiplos, FCFE).

## 6. Una nota final

El informe se basa en leer el código, no en ejecutarlo. Los números exactos y las líneas citadas pueden haber cambiado si el repositorio ya tiene cambios sin confirmar (el propio informe menciona dos). Antes de cada paquete, pide al agente que **reproduzca el fallo** con un test que falle; si no puede reproducirlo, el hallazgo se descarta o se reclasifica.
