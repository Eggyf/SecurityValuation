# Vectores de verificación (respuesta conocida)

Cada caso tiene entradas y una salida esperada **calculada fuera de la app**. Úsalos para contrastar el motor real. Si el motor da otro valor, hay un hallazgo: no ajustes el esperado.

Importes en millones, porcentajes como fracciones en el código.

## 1. DCF base (ver `dcf-methodology/scripts/dcf_reference.py`)

Entradas: ingresos 1.000; crecimiento 10 %, 8 %, 6 %, 5 %, 4 %; margen EBIT 20 %; impuestos 21 %; D&A 4 % de ingresos; CapEx 5 %; ΔNWC 10 % de Δingresos; WACC 9 %; g 2,5 %; caja 150; deuda 400; acciones diluidas 100; fin de año.

| Salida | Esperado | Tolerancia |
|---|---|---|
| FCFF año 1 | 152,8 | 1e-9 |
| FCFF años 1–5 | 152,8 / 167,0 / 179,2 / 189,4 / 198,2 | 0,1 |
| VA de los FCFF | 682,2 | 0,1 |
| Valor terminal | 3.125,9 | 0,1 |
| VA del TV | 2.031,7 | 0,1 |
| EV | 2.713,8 | 0,1 |
| Equity | 2.463,8 | 0,1 |
| Precio por acción | 24,64 | 0,01 |
| TV / EV | 74,9 % | 0,1 pp |

Variantes (mismas entradas, un cambio cada vez):

| Cambio | Precio esperado |
|---|---|
| g = 2,0 % | 23,10 |
| g = 3,0 % | 26,44 |
| WACC = 8 % | 29,65 |
| WACC = 10 % | 20,96 |
| Mitad de año (flujos a t − 0,5; TV de Gordon a n − 0,5) | 25,83 |

Controles: el centro de la tabla WACC × g es **exactamente** 24,64. Con `WACC = g` o `WACC < g` el motor debe fallar con error de dominio. Con deuda = 0 y caja = 0, `equity = EV`.

Upside con precio de mercado 20: `24,64 / 20 − 1 = +23,2 %`.

## 2. WACC

Rf 4,25 %; beta 1,1; ERP 5 %; E = 3.000; D = 1.000; Kd 5 %; t 21 %.

```
Ke          = 4,25 % + 1,1 × 5 % = 9,75 %
Kd después de impuestos = 5 % × (1 − 21 %) = 3,95 %
WACC        = 75 % × 9,75 % + 25 % × 3,95 % = 8,30 %
```

Esperado: **WACC = 8,30 %** (tolerancia 0,005 pp).

## 3. Beta desapalancada y reapalancada

β de mercado 1,2 con D/E 0,30 y t = 21 %.

```
β_u = 1,2 / (1 + 0,79 × 0,30) = 0,9701
β_L al reapalancar a D/E 0,50 = 0,9701 × (1 + 0,79 × 0,50) = 1,3533
```

Esperado: `β_u = 0,970`; `β_L = 1,353` (tolerancia 0,001). Si la app usa la beta de industria de Damodaran sin reapalancar, es un hallazgo.

## 4. Acciones diluidas (método de la acción de tesorería)

Acciones básicas (cover) 100; opciones 10 con precio de ejercicio 20; RSUs 4; precio actual 50.

```
Acciones netas por opciones = 10 × (1 − 20/50) = 6,0
Diluidas = 100 + 6,0 + 4 = 110,0
```

Esperado: **110,0**. Con precio 15 (opciones fuera de dinero): `100 + 0 + 4 = 104`. Si la app usa el promedio ponderado diluido del P&L, es un hallazgo ALTO.

## 5. Unidades y conversiones

| Entrada | Esperado |
|---|---|
| FRED `DGS10 = 4.25` | Rf = 0,0425 (fracción) |
| FRED `DGS10 = "."` (sin dato) | Usar la última observación válida y mostrar su fecha |
| iXBRL: texto «1,234», `scale=6`, `sign="-"` | −1.234,0 MM USD |
| iXBRL: texto «5,000», `scale=3` | 5,0 MM USD |
| Intereses 40; deuda media 800 | Kd = 5,0 % |
| Kd calculado < Rf | Aviso (Kd poco creíble) |
| Market cap 3.000 y `precio × acciones` = 3.300 | Aviso de incoherencia (> 5 %) |

## 6. Reverse DCF

Con el caso base y el fade lineal desde `g0` hasta g:

- Fabrica un precio con `g0 = 12 %` (da 24,54 USD) y resuelve: debe recuperar `12,0000 %` (error < 1e-6).
- Con precio 1.000.000.000: sin solución en el rango → mensaje, no número.
- Precio mayor → crecimiento implícito mayor (monotonía).

## 7. Scores de calidad (casos a mano)

- **Beneish:** dos ejercicios idénticos (todos los índices = 1, TATA = 0) → `M = −2,48`; `flag = False` con umbral −1,78.
- **Altman Z'** con X1 = 0,2; X2 = 0,3; X3 = 0,1; X4 = 0,5; X5 = 1,0 → `Z' = 1,916` (zona gris, entre 1,23 y 2,90).
- **Altman Z''** con X1 = 0,2; X2 = 0,3; X3 = 0,1; X4 = 0,5 → `6,56×0,2 + 3,26×0,3 + 6,72×0,1 + 1,05×0,5 = 3,487` (zona segura, > 2,60).
- **Piotroski:** año que mejora en los 9 criterios → 9; empeora en todos → 0.
- Empresa financiera: «no aplicable».

## 8. Mutaciones de validación

| Perturbación | Control que debe saltar |
|---|---|
| Activos totales + 2 % | Balance cuadra → `ERROR` |
| Ingresos × 1.000 en un solo año | Consistencia de escala |
| Gross profit ≠ ingresos − COGS en > 0,5 % | Margen bruto |
| NI del flujo ≠ NI del P&L | Coincidencia de NI |
| Faltan 2 ejercicios consecutivos | Ejercicios consecutivos |
| Eliminar un campo obligatorio | Campo `None` + aviso, no cero |

Para cada una, el resultado esperado es un aviso o error visible y, si es `ERROR`, ausencia de precio.

## 9. Determinismo y reproducibilidad

- Ejecutar el mismo caso dos veces → resultados idénticos bit a bit en el motor.
- Exportar entradas, volver a cargarlas y recalcular → mismo precio (`abs_tol=1e-9`).
- Monte Carlo (cuando exista): misma semilla → misma distribución.
