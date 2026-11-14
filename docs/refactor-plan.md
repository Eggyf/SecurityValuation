# Plan de refactor de ui/app.py

## Problema actual
`ui/app.py` supera las 1000 líneas y contiene lógica financiera (cálculo de Kd, extracción de métricas, etc.), incumpliendo la regla de que la UI no calcula finanzas.

## Objetivo
Trocear la app en módulos por pestaña y extraer toda la lógica financiera a funciones puras.

## Estructura propuesta

```
src/dcf_app/ui/
├── app.py              # Punto de entrada: config, init_state, tabs, disclaimer
├── tabs/
│   ├── upload.py       # Pestaña 1: Subir 10-K (local + EDGAR)
│   ├── review.py       # Pestaña 2: Revisar datos extraídos
│   ├── assumptions.py  # Pestaña 3: Supuestos de valoración
│   ├── results.py      # Pestaña 4: Resultados + Excel
│   ├── reverse_dcf.py  # Pestaña 5: Reverse DCF
│   └── quality.py      # Pestaña 6: Scores de calidad
├── helpers.py          # Funciones auxiliares de UI (formateo, etc.)
└── __init__.py
```

## Extracción de lógica financiera

### Funciones a extraer (de ui/app.py a módulos puros)

1. **`_compute_historical_metrics`** (ya en dcf.py) — OK
2. **Kd calculation** → `valuation/wacc.py::estimate_cost_of_debt(financials) -> float | None`
3. **Extract year data** (ya en analysis/extraction.py) — OK
4. **`_missing_market_inputs`** → `assumptions/validation.py::missing_market_inputs(assumptions) -> list[str]`
5. **`_fact_display`** → `ui/helpers.py::format_fact(fact) -> str`
6. **`_fact_source`** → `ui/helpers.py::fact_source(fact) -> str`

### Lógica que debe salir de la UI

| Código actual en ui/app.py | Destino |
|---|---|
| Cálculo de Kd (intereses/deuda) | `valuation/wacc.py` |
| Extracción de YearData | `analysis/extraction.py` (ya hecho) |
| Cálculo de scores | `analysis/quality_scores.py` (ya hecho) |
| Reverse DCF | `valuation/reverse_dcf.py` (ya hecho) |
| Formateo de facts | `ui/helpers.py` |
| Validación de inputs | `validation/__init__.py` (ya hecho) |

### Plan de ejecución (futuro, no implementar ahora)

1. Crear `ui/helpers.py` con funciones de formateo
2. Crear `ui/tabs/` con un módulo por pestaña
3. Mover la lógica financiera a módulos puros (ya parcialmente hecho)
4. Actualizar `app.py` para importar y orquestar
5. Actualizar tests de UI

### Beneficios
- Cada pestaña es testeable independientemente
- La lógica financiera es testeable sin Streamlit
- Más fácil de mantener y extender
- Cumple la regla "la UI no calcula finanzas"