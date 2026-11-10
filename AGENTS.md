# AGENTS.md — DCF desde 10-K

Este archivo es la fuente de verdad para cualquier agente de IA (opencode u otro) que trabaje en este repositorio. Léelo completo antes de escribir código. Si algo aquí contradice una petición puntual del usuario, pregunta antes de actuar.

## 1. Objetivo del proyecto

Aplicación que recibe el **Form 10-K** de una empresa (archivo local) y produce una **valoración por Flujos de Caja Descontados (DCF)** transparente, auditable y reproducible.

Flujo de alto nivel:

```
10-K (HTML/iXBRL/PDF) → Extracción → Estados financieros normalizados → Supuestos → Motor DCF → Resultados + Sensibilidades → Informe (UI + Excel)
```

**Alcance v1 (MVP):** una empresa, un 10-K, un DCF FCFF a 5 años con valor terminal, sensibilidades y exportación a Excel.
**Alcance v2 (después del MVP):** descarga opcional desde SEC EDGAR y datos de mercado (§13), y módulos de valoración adicionales: Reverse DCF, ratios y scores de calidad, Monte Carlo, múltiplos con football field, y FCFE/EVA como contraste (§14).
**Fuera de alcance por ahora:** múltiples empresas en paralelo, bancos/aseguradoras/REITs (requieren otros modelos), consenso de analistas (datos de pago), backtesting.

## 2. Principios no negociables

1. **Nunca inventes datos financieros.** Si un valor no está en el 10-K ni lo ha dado el usuario, el campo queda como `None` y se pide explícitamente. Prohibido rellenar con "valores típicos" sin marcarlo como supuesto.
2. **Separación estricta:** la extracción (que puede usar LLM/heurísticas) está aislada del motor DCF (**100 % determinista, sin LLM, sin red**).
3. **Trazabilidad:** cada cifra extraída guarda su origen (concepto XBRL o sección/página del 10-K, periodo, unidad). La UI debe poder mostrar de dónde sale cada número.
4. **Supuestos explícitos y editables:** todo supuesto (crecimiento, márgenes, WACC, g, etc.) es un input visible, con valor por defecto justificado y modificable.
5. **Validar antes de valorar:** si las comprobaciones de integridad fallan (ver §6), la app avisa y no presenta un precio objetivo como si fuera fiable.
6. **Unidades siempre explícitas:** guarda moneda, escala (unidades/miles/millones) y periodo fiscal. Normaliza internamente a **millones de USD** salvo que se indique otra cosa.
7. **No es asesoramiento financiero.** La UI y el informe incluyen un aviso claro.
8. **Datos externos solo con opt-in y con procedencia.** La app funciona 100 % offline con un 10-K local. Toda descarga (EDGAR, mercado, tasas) es opcional, pasa por `data_sources/` (§13), queda cacheada, registra fuente y fecha, y el usuario puede sobrescribirla. Si una fuente falla, se degrada a input manual, nunca a un valor por defecto silencioso.

## 3. Stack técnico

| Capa | Elección | Notas |
|---|---|---|
| Lenguaje | Python 3.12+ | Tipado estático obligatorio |
| Gestor de entorno | `uv` | `uv sync`, `uv run ...` |
| Modelos de datos | `pydantic` v2 | Validación en todas las fronteras |
| Parseo 10-K | `beautifulsoup4` + `lxml` (HTML/iXBRL); `pymupdf` (PDF como fallback) | **Prioriza los tags iXBRL** (`ix:nonFraction`) sobre texto libre |
| Cálculo | `numpy`, `pandas` | El motor DCF usa funciones puras |
| UI | `streamlit` | Una sola página con pestañas |
| Exportación | `openpyxl` | Excel con **fórmulas vivas**, no solo valores |
| HTTP | `httpx` | Solo dentro de `data_sources/`; timeouts, reintentos con backoff y caché |
| Optimización | `scipy` | `brentq` para Reverse DCF |
| Gráficos | `plotly` | Football field, histogramas de Monte Carlo, sensibilidades |
| Tests | `pytest`, `hypothesis` | |
| Calidad | `ruff` (lint+format), `mypy --strict` | |

No añadas dependencias nuevas sin justificarlo en el PR/commit y sin preguntar al usuario.

## 4. Estructura del repositorio

```
.
├── AGENTS.md
├── pyproject.toml
├── README.md
├── src/dcf_app/
│   ├── models/          # Pydantic: FinancialStatements, Assumptions, DCFResult
│   ├── extraction/      # Lectura del 10-K
│   │   ├── ixbrl.py     # Extracción por tags XBRL (vía preferida)
│   │   ├── sections.py  # Localizar Item 7, Item 8, notas (fallback textual)
│   │   └── mapping.py   # Mapeo concepto XBRL → campo normalizado
│   ├── normalization/   # Ajustes: no recurrentes, leases, SBC, signos, escala
│   ├── assumptions/     # Valores por defecto + lógica de históricos → proyección
│   ├── valuation/       # Motor DCF (puro, determinista)
│   │   ├── forecast.py
│   │   ├── wacc.py
│   │   ├── terminal_value.py
│   │   ├── bridge.py    # EV → Equity → precio por acción
│   │   ├── sensitivity.py
│   │   ├── reverse_dcf.py      # v2
│   │   ├── monte_carlo.py      # v2
│   │   ├── multiples.py        # v2
│   │   ├── football_field.py   # v2
│   │   ├── fcfe.py             # v2
│   │   └── residual_income.py  # v2 (EVA / Residual Income)
│   ├── analysis/        # v2: ratios, DuPont, Piotroski, Altman, Beneish
│   ├── data_sources/    # v2: EDGAR, mercado, tasas, Damodaran (opt-in)
│   │   ├── base.py      # Protocols: FilingsProvider, MarketDataProvider, RatesProvider...
│   │   ├── edgar.py
│   │   ├── rates.py
│   │   ├── damodaran.py
│   │   ├── market.py
│   │   └── cache.py
│   ├── validation/      # Comprobaciones de integridad contable
│   ├── export/          # Excel / informe
│   └── ui/app.py        # Streamlit
├── tests/
│   ├── unit/
│   ├── property/
│   └── fixtures/        # 10-K de ejemplo y resultados esperados
└── docs/
    └── methodology.md   # Decisiones metodológicas (mantener actualizado)
```

## 5. Comandos

```bash
uv sync                          # instalar dependencias
uv run pytest -q -m "not network" # tests (por defecto, sin red)
uv run pytest -q -m network      # tests de integración con red (solo a mano)
uv run ruff check . && uv run ruff format .
uv run mypy src                  # tipado estricto
uv run streamlit run src/dcf_app/ui/app.py
```

**Antes de dar una tarea por terminada**, ejecuta tests, ruff y mypy y confirma que pasan. Si algo falla y no puedes arreglarlo, dilo; no lo ocultes.

## 6. Extracción y validación de datos del 10-K

### Datos que hay que extraer (últimos 3 ejercicios fiscales como mínimo)

**Cuenta de resultados:** Revenue, COGS, Gross Profit, SG&A, R&D, D&A, EBIT (Operating Income), Interest Expense, Pre-tax Income, Income Tax Expense, Net Income, Diluted EPS, Diluted Weighted Avg Shares, Stock-Based Compensation.

**Balance:** Cash & equivalents, Short-term investments, Accounts Receivable, Inventory, Other current assets, Accounts Payable, Accrued liabilities, Deferred revenue, Short-term debt (incl. current portion), Long-term debt, Operating lease liabilities (corriente y no corriente), Finance leases, Preferred stock, Non-controlling interest, Total Equity.

**Flujo de caja:** Cash from Operations, CapEx, D&A, SBC, cambios en capital circulante.

**Notas relevantes:** opciones y RSUs vivas (cantidad, precio de ejercicio medio) para acciones diluidas, tasa impositiva efectiva y estatutaria, vencimientos de deuda y tipo de interés, partidas no recurrentes (reestructuración, deterioros, litigios).

### Reglas de extracción

- Intenta **primero iXBRL**. Solo recurre a texto/tablas si el tag no existe, y márcalo con `source="text_fallback"` y menor confianza.
- Cada dato: `value`, `unit`, `scale`, `period_end`, `source`, `confidence`.
- Respeta los signos del XBRL (cuidado con CapEx, que suele aparecer como pago/negativo en el flujo de caja).
- Si hay conceptos personalizados de la empresa (`company:...`), mapéalos manualmente y regístralo en `mapping.py` con un comentario.
- Un LLM puede asistir **solo** para localizar o clasificar texto ambiguo; nunca para producir cifras que luego entren al modelo sin pasar por validación.

### Validaciones obligatorias (módulo `validation/`)

- Activos = Pasivos + Patrimonio (tolerancia < 0,5 %).
- Gross Profit = Revenue − COGS (cuando existan ambos).
- Net Income del P&L coincide con el del flujo de caja.
- Variación de caja del flujo ≈ variación de caja en balance (considerando efecto FX).
- Consistencia de escala entre estados (no mezclar miles con millones).
- Los 3 años cubren periodos consecutivos y son del mismo ejercicio fiscal.

Cada validación devuelve `OK | WARNING | ERROR` con mensaje legible. Un `ERROR` bloquea la valoración final.

## 7. Metodología DCF (v1)

Modelo: **FCFF (Free Cash Flow to the Firm)** descontado al WACC.

### 7.1 Flujo de caja libre

```
NOPAT = EBIT × (1 − t)
FCFF  = NOPAT + D&A − CapEx − ΔNWC
```

- `t`: tasa impositiva **normalizada** (por defecto, efectiva media de 3 años acotada entre 15 % y 30 %; el usuario puede sobrescribirla).
- **Stock-Based Compensation:** tratarlo como un **gasto real** (no sumarlo de vuelta). Es el valor por defecto. Ofrecer un toggle, con advertencia visible si se activa el add-back.
- Excluir partidas no recurrentes del EBIT base, documentando cada ajuste.
- ΔNWC: calcula con partidas operativas (sin caja ni deuda).

### 7.2 Proyección

- Horizonte: **5 años** (configurable 3–10).
- Ingresos: crecimiento año a año con **fade lineal** desde el crecimiento inicial hacia el crecimiento terminal. Defecto: crecimiento inicial = CAGR histórico 3 años acotado a [−5 %, 25 %]; el usuario lo ajusta.
- Márgenes: EBIT margin converge desde el actual hacia un margen objetivo (input).
- CapEx, D&A y NWC como % de ingresos (media histórica por defecto).
- Escenarios **Base / Bull / Bear** con parámetros distintos (el Base es el único obligatorio en v1).

### 7.3 WACC

```
Ke   = Rf + β × ERP                  (CAPM)
Kd   = coste de deuda antes de impuestos (intereses / deuda media, o input)
WACC = E/(D+E) × Ke + D/(D+E) × Kd × (1 − t)
```

- **Rf, β, ERP, precio de la acción y capitalización de mercado NO están en el 10-K**: son **inputs del usuario**. No los inventes. En modo offline se muestran vacíos con ayuda contextual. Con el **modo online** activado (§13) pueden precargarse desde las fuentes indicadas, siempre visibles, con su procedencia y fecha, y editables.
- Pesos con valor de mercado del equity y deuda a valor contable (o mercado si se aporta).
- Incluir leases operativos como deuda de forma consistente: si se suman a la deuda, el EBIT debe ser antes del coste de lease implícito (documentar la decisión elegida).

### 7.4 Valor terminal

- **Método principal:** Gordon Growth → `TV = FCFF_(n+1) / (WACC − g)`.
- **Método de contraste:** múltiplo de salida EV/EBITDA (input opcional).
- Reglas de cordura (bloquear o avisar):
  - `WACC > g` siempre; si no, error.
  - `g` por defecto 2,0–2,5 % y **nunca superior a Rf** ni al crecimiento nominal de largo plazo de la economía.
  - Avisar si el **TV representa > 75 % del EV**.
  - En el año terminal, CapEx ≥ D&A (reinversión coherente con el crecimiento `g`). Preferible usar la relación `Reinversión = g / ROIC`.

### 7.5 Descuento

- Convención de **mitad de año** (mid-year) activable; defecto: **fin de año**.
- Fecha de valoración = input (defecto: fecha de cierre del 10-K o fecha actual; debe ser explícito).

### 7.6 Puente de EV a precio por acción

```
Equity Value = EV + Caja e inversiones a corto plazo
                  − Deuda financiera − Leases (si se tratan como deuda)
                  − Acciones preferentes − Intereses minoritarios
                  (± otros ajustes documentados)
Precio por acción = Equity Value / Acciones diluidas
```

- Acciones diluidas: **método de la acción de tesorería** con opciones/RSUs del 10-K y el precio actual introducido por el usuario.
- Mostrar cada partida del puente con su fuente.

### 7.7 Sensibilidades

Como mínimo:
- Tabla **WACC × g** → precio por acción.
- Tabla **margen EBIT objetivo × crecimiento de ingresos**.
- Comparar precio implícito vs. precio de mercado (si se aporta) y mostrar el **upside/downside**.

## 8. Reglas de código

- **Funciones puras** en `valuation/`: mismas entradas → misma salida; sin I/O, sin estado global, sin aleatoriedad.
- Tipado completo; nada de `Any` salvo en el borde del parseo.
- Dinero y porcentajes: usa `float` internamente pero **nunca compares floats con `==`**; usa `math.isclose` o tolerancias en tests.
- Los porcentajes se guardan como fracciones (0.08 = 8 %). La UI los formatea.
- Errores de dominio con excepciones propias (`ValidationError`, `ExtractionError`, `ValuationError`), con mensajes accionables.
- Nada de `print`; usa `logging`.
- Nombres en inglés para código; textos de UI y docs de usuario en **español**.
- Funciones pequeñas y documentadas con docstring que cite la fórmula financiera cuando aplique.
- Cada decisión metodológica no obvia se anota en `docs/methodology.md`.

## 9. Testing

- **Unit tests** para cada fórmula del DCF con casos calculados a mano (incluye el cálculo en el docstring del test).
- **Property tests** (`hypothesis`):
  - Mayor WACC → menor valor (ceteris paribus).
  - Mayor g → mayor valor mientras `WACC > g`.
  - Sensibilidad simétrica coherente con el caso base.
- **Golden tests:** guardar 1–2 10-K reales en `tests/fixtures/` con el JSON de extracción esperado y comprobar que no hay regresiones.
- Un test de extracción debe fallar si el parser devuelve cifras sin fuente.
- Cobertura mínima objetivo: 85 % en `valuation/`, `validation/` y `analysis/`.
- **Los tests nunca llaman a la red.** Los providers se mockean o se usan respuestas grabadas en `tests/fixtures/`. Las pruebas de integración reales llevan `@pytest.mark.network` y se excluyen por defecto.
- Cada módulo v2 incluye sus propios tests (ver criterios en §14).

## 10. Cómo debe trabajar el agente

1. **Empieza en modo plan.** Para cualquier tarea no trivial, propone un plan corto y espera confirmación antes de editar.
2. **Cambios pequeños e incrementales:** una tarea = un cambio verificable. No refactorices código no relacionado.
3. **Orden recomendado de construcción (roadmap):**
   1. Modelos Pydantic (`models/`).
   2. Motor DCF con datos de entrada manuales + tests (sin 10-K todavía).
   3. WACC, valor terminal, puente EV→equity, sensibilidades.
   4. Extracción iXBRL del 10-K + normalización + validaciones.
   5. UI Streamlit (subida de archivo → revisión de datos → supuestos → resultados).
   6. Exportación a Excel con fórmulas.
   7. Fallback PDF/texto y mejoras de robustez.

   **Fase 2** (solo cuando la v1 esté estable y con tests; cada punto es una tarea independiente):

   8. `data_sources/` con EDGAR (ticker→CIK, descarga del 10-K, `companyfacts`) y caché (§13).
   9. Datos de mercado y tasas: Rf, precio, acciones, datasets de Damodaran (§13).
   10. Reverse DCF (§14.1).
   11. Ratios y scores de calidad: Piotroski, Altman, Beneish (§14.2).
   12. Monte Carlo (§14.3).
   13. Múltiplos de comparables + football field (§14.4).
   14. FCFE y Residual Income/EVA como contraste (§14.5).
4. **Pregunta antes de asumir** cuando falte información financiera. No tomes decisiones de valoración silenciosamente.
5. **No toques** `tests/fixtures/` ni los valores esperados para "hacer pasar" un test. Si un test falla, entiende por qué.
6. **No ejecutes** comandos destructivos (`rm -rf`, `git reset --hard`, `git push --force`). **No accedas a la red** salvo dentro de `data_sources/` y con el modo online activado; para instalar dependencias o probar endpoints reales, pide permiso.
7. **No hagas commits** salvo que el usuario lo pida.
8. Al terminar, resume: qué cambiaste, qué comprobaste (tests/lint/mypy) y qué quedó pendiente o incierto.

## 11. Seguridad y privacidad

- No subir 10-K, claves de API ni datos de usuario a servicios externos sin consentimiento explícito.
- Secretos solo en variables de entorno / `.env` (en `.gitignore`). Variables previstas: `SEC_USER_AGENT` (obligatoria para EDGAR), `FRED_API_KEY`, `MARKET_DATA_API_KEY` (según proveedor).
- Nunca registrar claves en logs ni en el informe exportado.
- Si en el futuro se integra un LLM, registrar qué datos se envían y permitir desactivarlo.

## 12. Definition of Done (por funcionalidad)

- [ ] Código tipado, `ruff` y `mypy --strict` limpios.
- [ ] Tests unitarios (y de propiedades si aplica) pasando.
- [ ] Supuestos y fórmulas documentados en `docs/methodology.md`.
- [ ] Sin datos inventados; todo valor con fuente o marcado como supuesto.
- [ ] La UI muestra avisos de validación y el disclaimer financiero.
- [ ] El resultado es reproducible: mismos inputs → mismo precio por acción.

## 13. Fuentes de datos externas (`data_sources/`)

El 10-K solo da información histórica de la empresa. Para valorar mejor hacen falta datos de mercado y de contexto. Este módulo los trae **solo si el usuario activa el modo online** (`DCF_ONLINE=1` o interruptor en la UI).

### 13.1 Reglas del módulo

- **Interfaces abstractas** (`typing.Protocol`) por tipo de dato: `FilingsProvider`, `MarketDataProvider`, `RatesProvider`, `PeersProvider`. El resto de la app depende de la interfaz, nunca de un proveedor concreto.
- **Caché en disco** (`.cache/`, en `.gitignore`) con TTL: filings sin caducidad (son inmutables); precios 15 min–1 día; tasas 1 día; datasets de Damodaran 30 días.
- **Procedencia:** cada dato externo guarda `provider`, `endpoint/URL`, `fetched_at` y se muestra en la UI. El usuario puede sobrescribirlo.
- **Degradación segura:** si una fuente falla o devuelve algo incoherente, la UI pide el dato manualmente. Prohibido sustituirlo por un valor típico sin avisar.
- **Cortesía y límites:** timeouts, reintentos con backoff exponencial, respetar los límites de cada API y no hacer scraping fuera de endpoints documentados.
- Antes de implementar cada proveedor, **verifica sus términos de uso y límites actuales** (cambian con frecuencia, sobre todo los planes gratuitos) y anótalos en `docs/methodology.md`.

### 13.2 Fuentes previstas

| Dato | Fuente | Acceso | Notas |
|---|---|---|---|
| 10-K, 10-Q y listado de filings | **SEC EDGAR** (`data.sec.gov`, `sec.gov/Archives`) | Gratis, sin clave | Cabecera `User-Agent` obligatoria con nombre y email (`SEC_USER_AGENT`). Límite de **10 peticiones/s**. Ticker→CIK con `company_tickers.json`; filings por CIK con la API `submissions`. |
| Histórico multi-año y TTM | **EDGAR XBRL `companyfacts`** | Gratis, sin clave | Permite 5–10 años de histórico (el 10-K da pocos) y trimestres de 10-Q para calcular TTM. Se usa también para **validación cruzada** con la extracción del 10-K. |
| Tasa libre de riesgo (Rf) | **US Treasury** (curva de rendimientos) o **FRED** (serie `DGS10`) | Treasury sin clave; FRED con clave gratuita | Usar el bono a 10 años por defecto, con la fecha visible. |
| ERP, betas sectoriales, márgenes y múltiplos por industria, riesgo país | **Datasets de Damodaran** (NYU Stern) | Descarga gratuita de Excel | Se actualizan sobre todo al inicio de cada año. Útiles para β desapalancada por industria, ERP implícita y márgenes objetivo de referencia. |
| Precio, acciones en circulación, β histórica | `yfinance` (no oficial, revisar términos; uso personal) o proveedores con clave (Financial Modeling Prep, Alpha Vantage, Polygon, Tiingo) | Según proveedor | Aislado tras `MarketDataProvider` para poder cambiar de proveedor sin tocar el resto. |
| Comparables (peers) | Lista por **código SIC** de EDGAR + múltiplos del proveedor de mercado | Mixto | La lista de peers es **siempre editable** por el usuario antes de calcular. |

No incluir consenso de analistas en v2 (datos de pago). Si se añade, solo como referencia visual, nunca como input directo del modelo.

### 13.3 Qué mejora cada fuente

- **companyfacts:** más histórico, TTM con 10-Q, y detección de errores de extracción al comparar ambas fuentes.
- **Rf y ERP (FRED/Treasury/Damodaran):** WACC reproducible y fechado, en vez de números escritos a mano.
- **Precio y acciones:** upside/downside, pesos de mercado en el WACC y acciones de tesorería exactas.
- **Betas y márgenes sectoriales:** punto de partida razonado para β y margen objetivo, siempre editable.
- **Peers:** valoración por múltiplos y football field (§14.4).

### 13.4 Notas específicas de EDGAR

- Normalizar el CIK a 10 dígitos con ceros a la izquierda en las URLs de `data.sec.gov`.
- Elegir el 10-K correcto del listado de `submissions` filtrando por `form == "10-K"` (considerar también `10-K/A`) y por fecha de cierre.
- Pedir siempre contenido comprimido y cachear la respuesta: los filings no cambian.
- Un 10-K descargado entra por **el mismo pipeline de extracción** que uno local. No existe un camino distinto para datos online.

## 14. Módulos de valoración adicionales (v2)

Todos reutilizan el modelo `Assumptions` y el motor determinista de `valuation/`. **Ninguno puede cambiar el resultado del DCF base** de la v1. Cada uno vive en su propio módulo, con su pestaña en la UI y su aportación al resumen final.

### 14.1 Reverse DCF (`valuation/reverse_dcf.py`)

- **Qué hace:** dado el precio de mercado, resuelve qué parámetro tendría que cumplirse para que el DCF dé ese precio: crecimiento inicial de ingresos, o margen EBIT objetivo, manteniendo el resto fijo.
- **Cómo:** `scipy.optimize.brentq` sobre `precio_modelo(x) − precio_mercado` en un rango razonable. Si no hay cambio de signo en el rango, informar «sin solución en el rango» en vez de devolver un número.
- **Salida:** el valor implícito comparado con el histórico de la empresa (CAGR a 3 y 5 años, margen máximo y medio) y una lectura en texto neutral («el mercado descuenta X % de crecimiento; la empresa creció Y %»).
- **Tests:** round-trip (generar un precio con parámetros conocidos y recuperarlos con error < tolerancia), caso sin solución, monotonía.

### 14.2 Ratios y scores de calidad (`analysis/`)

- **Ratios:** márgenes bruto, EBIT y FCF; ROIC (NOPAT / capital invertido medio); ROE; DuPont (margen × rotación × apalancamiento); DSO, DIO, DPO y ciclo de conversión de caja; cobertura de intereses; deuda neta/EBITDA; conversión de FCF.
- **Piotroski F-Score:** 9 criterios binarios (rentabilidad, apalancamiento/liquidez, eficiencia). Devolver el total y el desglose.
- **Altman Z-Score:** elegir la variante según el tipo de empresa (manufacturera, no manufacturera, mercados emergentes) y **documentar cuál se usa**. No aplicable a empresas financieras: la app debe avisarlo.
- **Beneish M-Score:** variante de 8 variables, requiere dos ejercicios consecutivos. Mostrar el valor y el umbral de referencia que se use, como señal de alerta, no como veredicto.
- **Calidad de beneficios:** CFO / beneficio neto y ratio de devengos (accruals).
- **Regla:** todo score se muestra con su **desglose por componente** y la fórmula, para que sea auditable. Ninguno se presenta como conclusión de inversión.
- **Tests:** casos calculados a mano y casos de la literatura; un test que falle si falta un componente y el score se calcula igualmente.

### 14.3 Monte Carlo (`valuation/monte_carlo.py`)

- **Qué hace:** simula miles de DCF variando los supuestos clave para obtener una distribución de valor en vez de un número único.
- **Variables y distribuciones por defecto:** crecimiento inicial y margen objetivo (triangular o normal truncada alrededor del caso base), WACC (normal truncada), g (triangular). Rangos configurables en la UI. Correlación opcional positiva y moderada entre crecimiento y margen.
- **Reproducibilidad:** `numpy.random.default_rng(seed)` con semilla visible y fija por defecto. Mismos inputs y semilla → mismos resultados.
- **Cordura:** forzar `g < WACC − 1 pp` en cada simulación; contar y mostrar cuántas se descartaron.
- **Rendimiento:** 10 000 simulaciones por defecto, vectorizadas con numpy.
- **Salida:** media, mediana, percentiles P5/P25/P75/P95, probabilidad de que el valor supere el precio de mercado e histograma.
- **Tests:** con varianza cero reproduce el DCF determinista; misma semilla, mismo resultado; la media converge al aumentar N; ningún caso con `WACC ≤ g`.

### 14.4 Múltiplos y football field (`valuation/multiples.py`, `valuation/football_field.py`)

- **Múltiplos:** EV/EBITDA, EV/EBIT, EV/Ventas y P/E de los peers. Usar **mediana y cuartiles**, no la media, por los outliers. Excluir múltiplos negativos o no significativos (NM) y mostrar cuántos peers entran.
- **Aplicación:** sobre la métrica de la empresa (último ejercicio o TTM si hay 10-Q), con el **mismo puente EV → equity → precio** que el DCF.
- **Football field:** un gráfico con un rango por método y una línea con el precio actual. Rangos: DCF base ± sensibilidad WACC×g, Monte Carlo P25–P75, múltiplos Q1–Q3 y, si hay datos, el rango de 52 semanas.
- **Tests:** mediana y cuartiles con casos manuales, exclusión de NM, el puente coincide con el del DCF.

### 14.5 FCFE y Residual Income / EVA (`valuation/fcfe.py`, `valuation/residual_income.py`)

- **FCFE:** `FCFE = FCFF − Intereses × (1 − t) + Δ deuda neta`, descontado al coste del equity (Ke). Requiere un supuesto de estructura de deuda (por defecto, ratio D/(D+E) constante).
- **Residual Income:** `V0 = B0 + Σ RI_t / (1+Ke)^t`, con `RI_t = NI_t − Ke × B_{t−1}`. Comprobar la relación de *clean surplus* en la proyección.
- **EVA:** `(ROIC − WACC) × capital invertido`, para ver si la empresa crea o destruye valor.
- **Uso:** son modelos de **contraste**. Mostrar la divergencia frente al DCF FCFF y avisar si supera un umbral configurable (por defecto 25 %).
- **Tests:** identidades algebraicas sobre casos simples (deuda cero → FCFE = FCFF a coste de capital propio) y comprobación del *clean surplus*.

### 14.6 Integración y criterios de aceptación

- Pestaña **«Resumen»** en la UI: football field, valor central, rango y avisos de todos los módulos activos.
- Cada módulo se puede desactivar sin romper los demás.
- Las dependencias entre módulos pasan por modelos Pydantic, nunca por estado global.
- Una tarea v2 está terminada cuando cumple la Definition of Done (§12) y sus tests específicos de §14.x.

## 15. Limitaciones conocidas (mantener a la vista)

- El DCF es muy sensible a WACC, g y márgenes terminales: presentar siempre rangos, no un único número.
- Un 10-K solo ofrece información histórica; las proyecciones dependen de supuestos del usuario.
- Empresas financieras, con pérdidas persistentes, cíclicas extremas o en fase pre-ingresos requieren ajustes que la v1 no cubre: la app debe avisar cuando detecte estos casos (EBIT negativo en la mayoría de años, sector financiero por SIC code, etc.).
- Los datos externos pueden tener retrasos, errores o cambiar de términos de uso. Se muestran siempre con fuente y fecha, y el usuario tiene la última palabra.
- Monte Carlo y los demás modelos de contraste dependen de las distribuciones y supuestos elegidos: más sofisticación no equivale a más precisión.
