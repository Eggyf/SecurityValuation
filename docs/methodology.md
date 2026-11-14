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
| Estructura de estados | Un modelo por estado y ejercicio (listas ordenadas, sin duplicados y con año base común, Reg S-X); las comprobaciones contables («3 años consecutivos», A = P + P) viven en `validation/`, no en el modelo | Firmada (2026-11-11) |
| Supuestos y resultados | `Assumptions` con todos los supuestos opcionales (WACC, g, márgenes, etc.) y `DCFResult` con proyección, TV, puente EV→equity y sensibilidades; `is_reasonable` valida cordura (TV < 75% EV, precios positivos) | Firmada (2026-11-10) |

## Extracción del 10-K (paso 7 del roadmap)

| Tema | Decisión | Estado |
|---|---|---|
| Vía preferida | iXBRL (`ix:nonFraction`) → builder de estados; PDF por etiquetas como fallback `text_fallback` | Firmada (2026-11-11) |
| Facts dimensionales | Se descartan los facts cuyo contexto XBRL tiene `segment`/`scenario` (desgloses por producto, región, etc.): no son cifras de la empresa consolidada | Firmada (2026-11-11) |
| Ventana anual | Solo duraciones de 300–380 días entran en P&L/flujos; los trimestres y acumulados de las notas quedan fuera; los instantes alimentan el balance | Firmada (2026-11-11) |
| Deduplicación | Dos facts con mismo (concepto, periodo, valor) colapsan en uno; distintos `contextRef` describen a veces el mismo periodo | Firmada (2026-11-11) |
| Conceptos en dos estados | D&A y SBC están en los mapas de P&L y flujos: el mismo tag se copia en ambos estados del ejercicio | Firmada (2026-11-11) |
| Conflictos de concepto | Varios conceptos mapean al mismo campo con valores distintos → gana el tag estándar us-gaap sobre la extensión de la empresa; a igualdad, el primero en orden de documento (determinista) | Firmada (2026-11-11) |
| Año base compartido | Reg S-X: el balance presenta 2 ejercicios y el P&L/flujos 3; el validador de `FinancialStatements` exige conjuntos ordenados sin duplicados y el ejercicio más reciente común a los tres estados (año base), no conjuntos idénticos | Firmada (2026-11-11) |
| Degradación segura | Si falta alguno de los tres estados, se devuelven listas vacías y `validate_extraction` lo comunica como advertencia; nunca se inventan cifras (AGENTS.md §2.8) | Firmada (2026-11-11) |
| Nombre de la empresa | iXBRL: `ix:nonNumeric` con `name="dei:EntityRegistrantName"` (forma real de EDGAR), con fallback a tag directo y `<title>`; PDF: regex sobre la portada con sufijos corporativos (Corporation/Inc./...), fallback al nombre de archivo | Firmada (2026-11-11) |
| PDF: patrón de parseo | Etiqueta en una línea + un valor por columna en el orden de la cabecera de años (patrón de los PDF renderizados de EDGAR, verificado contra MSFT FY2026 y NVDA FY2026); `$` suelto se salta; los guiones (—) consumen columna como valor ausente; las líneas que terminan en `:` son cabeceras de sección, no etiquetas | Firmada (2026-11-11) |
| PDF: secciones EPS/acciones | `Basic`/`Diluted` se desambiguan por la sección activa (EPS → `diluted_eps` en USD/acción; acciones → `diluted_weighted_shares`) | Firmada (2026-11-11) |
| PDF: SG&A partido | Cuando la empresa separa SG&A en componentes («Sales and marketing» + «General and administrative», MSFT), el parser los suma en un solo fact con la fuente «A + B»; la etiqueta directa de SG&A gana a los componentes | Firmada (2026-11-11) |
| PDF: escala de EPS | El «(In millions)» del estado aplica a las cifras monetarias y a los conteos de acciones, pero no a los importes por acción («except per share amounts»): `diluted_eps` lleva `Scale.UNITS` | Firmada (2026-11-11) |
| PDF: inicio de ejercicio | `period_start` = cierre anterior + 1 día; para la columna más antigua se aproxima (cierre − 1 año + 1 día) si el documento no aporta el cierre anterior | Firmada (2026-11-11) |
| PDF: limitación multi-página | Solo se parsea la primera página de cada estado; partidas que continúan en la página siguiente quedan en `None` (avisado por `validate_extraction` si falta algo crítico) | Firmada (2026-11-11) |
| Mapa de conceptos | Claves normalizadas (minúsculas, sin espacios/guiones/dos puntos); se corrigieron claves con espacios/mayúsculas que nunca podían matchear (`stockholders Equity`, `capitalExpenditures`, `netincreasein cash`) | Firmada (2026-11-11) |
| Golden tests | `tests/fixtures/sample_ixbrl.html` (sintético: dimensional, trimestral, duplicado, conflicto) y recortes PDF de MSFT/NVDA (portada + páginas de estados; documentos públicos de la SEC) con valores ancla verificados a mano | Firmada (2026-11-11) |

## Cierre de la v1: defaults, inputs de mercado y exportación

| Tema | Decisión | Estado |
|---|---|---|
| Defaults sugeridos | `assumptions/defaults.py` calcula los pre-rellenos solo desde el 10-K: CAGR de ingresos acotado a [−5 %, 25 %] (§7.2), margen EBIT del último ejercicio, efectiva media acotada a [15 %, 30 %] (§7.1), acciones diluidas medias (en M) y deuda contable ST+LT (§7.3); si el dato no está en el documento, `None` y la UI lo pide (AGENTS.md §2.1) | Firmada (2026-11-11) |
| ERP obligatoria | El motor ya no sustituye la prima de riesgo por un 5 % silencioso: sin ERP lanza `ValueError`; es un input del usuario (§7.3) y en v2 podrá precargarse de Damodaran (§13.2) | Firmada (2026-11-11) |
| Inputs de mercado en la UI | Rf, β, ERP, Kd, capitalización, precio y acciones se muestran vacíos con ayuda contextual; al pulsar «Ejecutar DCF» la UI lista los faltantes en vez de ejecutar con huecos | Firmada (2026-11-11) |
| Proxy contable del WACC | Si el usuario no aporta valores de mercado, los pesos usan el patrimonio contable (`metrics["equity_value"]`, antes inexistente y siempre 0.0) y la deuda contable; documentado como proxy, no como dato de mercado | Firmada (2026-11-11) |
| Origen visible de cada pre-relleno | Cada default pre-rellenado lleva un caption con su origen (CAGR FYxxxx-yyyy, margen EBIT actual, efectiva media del histórico, deuda del balance, medias diluidas como aproximación editable) | Firmada (2026-11-11) |
| Exportación desde la UI | Botón de descarga en la pestaña Resultados vía `export_to_excel_bytes` (mismo libro que `export_to_excel`, vía `io.BytesIO`); los supuestos usados se guardan en sesión (`dcf_assumptions`) para que el Excel coincida con el resultado mostrado | Firmada (2026-11-11) |
| Bounds del formulario | g limitado a [2,0 %, 2,5 %] (§7.4), tasa impositiva a [15 %, 30 %] (§7.1), margen EBIT a [0 %, 90 %]; el slider de horizonte alimenta la proyección (antes su valor se descartaba y era decorativo) | Firmada (2026-11-11) |
| EBIT negativo | Si el margen EBIT del último ejercicio es negativo, la UI avisa de que la v1 no cubre ese caso (§15) en vez de pre-rellenar el margen objetivo | Firmada (2026-11-11) |

## Leases operativos (H19)

**Decisión:** Los leases operativos se tratan como deuda financiera en el puente EV→equity y en los pesos del WACC. El EBIT se usa antes del coste de lease implícito (es decir, no se resta el coste de lease del EBIT). Esta es la opción más común en la práctica y la más conservadora.

**Implicaciones:**
- **EBIT:** Se usa el Operating Income tal como se reporta (antes de lease expense implícito).
- **WACC:** Los leases operativos se suman a la deuda financiera para los pesos (D/(D+E)).
- **Puente EV→equity:** Los leases operativos se restan como partida separada.

**Alternativa (no usada):** Restar el coste de lease del EBIT y no tratar los leases como deuda. Esto daría un EV menor y un precio por acción menor.

## Pendientes de decidir

Se resolverán al implementar cada módulo, no antes:

- **Modelo de dinero:** resuelto: `Fact` guarda el valor original + escala y la
  normalización a millones ocurre en `normalization/` (ver decisiones firmadas).
- **Leases operativos:** tratarlos como deuda y usar EBIT antes del coste de lease
  implícito (o la alternativa), documentando la elección.
- **CapEx terminal:** `Reinversión = g / ROIC` frente a la restricción simple `CapEx ≥ D&A`.
- **Acciones diluidas:** método de la acción de tesorería con opciones/RSUs del 10-K.
- **Escala en la extracción:** resuelto: iXBRL usa el atributo `scale` del tag y el PDF la
  detecta del «(In millions...)» del estado (excepción: EPS en unidades); la validación de
  consistencia entre estados se hace al consumir las cifras vía `Fact.to_scale()`.
- **WACC:** ¿Guardar el valor calculado en `Assumptions` (como propiedad) o calcularlo
  en el motor DCF y pasarlo como parámetro?
