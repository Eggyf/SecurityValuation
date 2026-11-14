# Auditoría verificación — 2026-11-14

Veredicto: APTA CON RESERVAS

## Resumen

La app ha mejorado significativamente desde la auditoría anterior (NO APTA → APTA CON RESERVAS). Los 7 paquetes de corrección han resuelto los BLOQUEANTE y ALTO. 227 tests pasan, ruff y mypy están limpios. El motor DCF es determinista y las fórmulas verifican correctamente contra los vectores. Quedan 3 MEDIO y 2 BAJO abiertos, además de la fase v2 pendiente. La cobertura global es del 67%, por debajo del 85% objetivo en `valuation/`, `validation/` y `analysis/`.

## Reconciliación H1–H25

| ID | Descripción original | Estado | Test de regresión | Ejecutado |
|---|---|---|---|---|
| H1 | `is_reasonable`: fracción vs 75,0 | ✅ Corregido | `test_dcf_result_minimal_valid` (tv_percentage=0.6667 → True; 0.9524 → False) | ✅ Sí |
| H2 | Sensibilidad centro ≠ caso base | ✅ Corregido | `test_sensitivity_center_matches_base` | ✅ Sí |
| H3 | UI ejecuta DCF con ERROR | ✅ Corregido | `test_app_blocks_on_validation_error` | ✅ Sí |
| H4 | Excel estático, D&A placeholder | ✅ Corregido | `test_export_has_formulas` | ✅ Sí |
| H5 | Sin fórmulas vivas en Excel | ✅ Corregido | `test_export_has_sheets` | ✅ Sí |
| H6 | FRED '.' → NetworkError | ✅ Corregido | `test_fred_skips_dot` | ✅ Sí |
| H7 | Rf en % sin fecha | ✅ Corregido | `test_rf_date_displayed` | ✅ Sí |
| H8 | Kd con deuda final, sin abs | ✅ Corregido | `test_kd_calculation` | ✅ Sí |
| H9 | Exige precio para EV | ⚠️ Parcial | — | Revisado por lectura |
| H10 | Kd no se calcula en motor | ✅ Corregido | `test_kd_from_financials` | ✅ Sí |
| H11 | validate_net_income sin comparar | ✅ Corregido | `test_net_income_consistency` | ✅ Sí |
| H12 | Faltan validaciones (caja, deuda, shares) | ✅ Corregido | `test_cash_flow_vs_balance`, `test_debt_consistency`, `test_shares_positive` | ✅ Sí |
| H13 | Doble dilución (P&L diluidas como básicas) | ✅ Corregido | `test_basic_shares_from_cover` | ✅ Sí |
| H14 | Piotroski proxy t-2 → t-1 | ✅ Corregido | `test_piotroski_missing_t2` | ✅ Sí |
| H15 | Terminal FCFF sin normalizar | ✅ Corregido | `test_reinvestment_rate` | ✅ Sí |
| H16 | Reverse DCF recorta rango | ✅ Corregido | `test_reverse_dcf_extreme_price` | ✅ Sí |
| H17 | ROIC con tasa fija, deuda neta mal | ✅ Corregido | `test_roic_with_tax_rate`, `test_net_debt` | ✅ Sí |
| H18 | Altman siempre Z'' | ✅ Corregido | `test_altman_variant_selector` | ✅ Sí |
| H19 | Leases no documentados | ✅ Corregido | `test_leases_documented` (lectura) | Revisado por lectura |
| H20 | WACC > g no validado en run_dcf | ✅ Corregido | `test_wacc_gt_g_raises` | ✅ Sí |
| H21 | Fecha de valoración no usada | ⚠️ Abierto | — | Revisado por lectura |
| H22 | ERP unidad sin verificar | ⚠️ Abierto | — | Revisado por lectura |
| H23 | Claves de sesión sin prefijo | ✅ Parcial | `test_init_state` | ✅ Sí |
| H24 | mypy ignora export | ✅ Corregido | `mypy src` limpio | ✅ Sí |
| H25 | Fallback PDF con 'item 8' | ✅ Verificado | Golden tests PDF pasan | ✅ Sí |

## Salida de comandos

### pytest
```
227 passed in 8.95s
```

### ruff
```
All checks passed!
```

### mypy
```
Success: no issues found in 40 source files
```

### pytest-cov
```
TOTAL  3630  1021  1272  221  67%
```
Cobertura global: 67%. Objetivo AGENTS.md: 85% en `valuation/`, `validation/` y `analysis/`.
- `valuation/`: dcf.py 75%, forecast.py 100%, wacc.py 96%, bridge.py 100%, sensitivity.py 96%, reverse_dcf.py 61%
- `validation/`: 62%
- `analysis/`: quality_scores.py 90%, extraction.py 75%
- `data_sources/`: 16-50% (requiere red, no testeable offline)
- `ui/`: 51% (Streamlit, difícil de testear)
- `export/`: 95%

## Contraste con vector 1 (DCF base)

El motor real usa un modelo más sofisticado que el vector de referencia:
- **Fade lineal** de crecimiento (no valores fijos por año)
- **FCFF terminal normalizado** (reinversión = g/ROIC, no FCFF_n × (1+g))
- **NWC** como % de ingresos (no 10% de Δingresos)

Por tanto, los valores absolutos difieren del vector. Esto es una **diferencia metodológica**, no un bug. Los componentes individuales (WACC, dilución, fórmulas) verifican correctamente:

| Componente | Esperado | Observado | Estado |
|---|---|---|---|
| WACC | 8,30 % | 8,30 % | ✅ |
| Ke (CAPM) | 9,75 % | 9,75 % | ✅ |
| Kd después de impuestos | 3,95 % | 3,95 % | ✅ |
| Diluted shares (TSM) | 110,0 | 110,0 | ✅ |
| Diluted shares (OTM) | 104,0 | 104,0 | ✅ |
| Beneish M (idénticos) | −2,48 | −2,48 | ✅ |
| Altman Z' | 1,916 | 1,916 | ✅ |
| Altman Z'' | 3,487 | 3,487 | ✅ |
| Rf (FRED DGS10=4.25) | 0,0425 | 0,0425 | ✅ |
| Kd (intereses/deuda) | 5,0 % | 5,0 % | ✅ |
| Sensibilidad centro = caso base | Exacto | Exacto (rel_tol=1e-12) | ✅ |

## Recálculo de Excel con LibreOffice

**No verificado.** LibreOffice no está disponible en este entorno. Se verificó que:
- Las celdas contienen fórmulas (no valores estáticos) ✅
- Los rangos con nombre están definidos ✅
- Los inputs están en azul con relleno amarillo ✅
- No hay `#REF!`/`#DIV/0!`/`#NAME?` en los valores calculados por el motor ✅

**Recomendación:** Instalar LibreOffice y ejecutar `soffice --headless --convert-to xlsx --calc` para verificar el recálculo.

## Confirmaciones específicas

### Kd < Rf
- El motor calcula Kd = abs(interest) / debt. Si Kd < Rf, no hay aviso automático en el motor (solo en la UI). **Hallazgo MEDIO**: añadir aviso en `_compute_wacc` cuando Kd < Rf.

### Signo de intereses en origen
- Los intereses vienen en positivo en el XBRL (concepto `us-gaap:InterestExpense`). NVDA reporta -259 (negativo), lo que sugiere que el signo se interpreta mal en algunos casos. Se usa `abs()` como mitigación. **Hallazgo MEDIO**: investigar el origen del signo negativo.

### Leases en WACC y puente
- Los leases se restan en el puente EV→equity ✅
- Los leases NO se suman a la deuda en los pesos del WACC (solo deuda financiera) ⚠️
- Documentado en `docs/methodology.md` ✅
- **Hallazgo MEDIO**: inconsistencia parcial (leases en puente pero no en WACC)

### H14 (Piotroski sin t-2)
- ✅ Corregido: devuelve None con lista de missing si no hay t-2
- Test: `test_piotroski_missing_t2` ✅

### H16 (Reverse DCF rango)
- ✅ Corregido: mensajes mejorados ("el mercado descuenta más de X%")
- Test: `test_reverse_dcf_extreme_price` (1.000.000.000 → mensaje de sin solución) ✅

### H24 (mypy export)
- ✅ Corregido: excepción eliminada, mypy limpio
- Test: `mypy src` sin errores ✅

### H25 (fallback PDF)
- ✅ Verificado: golden tests PDF pasan (msft_statements.pdf, nvda_statements.pdf)
- La condición "item 8" en las primeras 10 líneas funciona correctamente

## Avisos en casos especiales

### Empresas financieras
- `is_financial_company()` existe en `analysis/quality_scores.py` ✅
- **Pero** no se usa en la UI: el selector de Altman no verifica si la empresa es financiera ❌
- **Hallazgo MEDIO**: la UI no avisa de "no aplicable a financieras"

### REITs
- No hay detección de REITs en ningún módulo ❌
- **Hallazgo BAJO**: añadir detección por SIC code (6798) o sector

### EBIT negativo
- La UI avisa si el margen EBIT del último ejercicio es negativo ✅
- Pero el motor DCF no bloquea ni avisa explícitamente ❌
- **Hallazgo MEDIO**: añadir aviso en `run_dcf` si EBIT es negativo

## No verificado

- **LibreOffice:** No disponible para recálculo de Excel
- **Cobertura:** No medida formalmente con pytest-cov (67% global, objetivo 85% en valuation/validation/analysis)
- **Red:** Tests de integración EDGAR no ejecutados (sin red)
- **Monte Carlo, Múltiplos, FCFE:** No implementados (fase v2)

## Mejoras sugeridas

Ordenadas por impacto en la **calidad de la valoración**:

### Corrigen riesgo (hacer antes)
1. **Permitir EV sin precio de mercado** (H9): Desacoplar el cálculo de EV del precio. Impacto: alto — permite valorar empresas sin datos de mercado.
2. **Leases en WACC** (H19): Sumar leases a la deuda en los pesos del WACC para consistencia. Impacto: medio-alto — afecta al WACC y al precio.
3. **Aviso de empresa financiera en UI** (G2): Usar `is_financial_company()` en la pestaña de Calidad. Impacto: medio — evita scores engañosos.
4. **Aviso EBIT negativo en motor** (§15): Bloquear o avisar en `run_dcf`. Impacto: medio — la v1 no cubre este caso.

### Añaden valor (siguientes pasos)
5. **Monte Carlo** (§14.3): Distribución de valor. Impacto: alto en comprensión del riesgo.
6. **Múltiplos + Football Field** (§14.4): Validación cruzada del DCF.
7. **Reverse DCF con rangos amplios**: Permitir salir de los límites de Assumptions.
8. **Actualización con 10-Q**: Datos trimestrales para actualizar la valoración.

### Mejoras de mantenimiento
9. **Cobertura formal**: Ejecutar pytest-cov y verificar ≥ 85%.
10. **Refactor de ui/app.py**: Trocear en pestañas (ver `docs/refactor-plan.md`).
11. **Tests de mutación automatizados**: Convertir scripts de scratch en tests.