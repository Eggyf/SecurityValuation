---
name: dcf-methodology
description: Metodología detallada para construir o modificar un DCF por FCFF (flujo de caja libre a la empresa), incluyendo NOPAT, ΔNWC, WACC por CAPM, valor terminal, convención de mitad de año y puente de EV a precio por acción. Úsala siempre que vayas a escribir, cambiar o revisar código de valuation/, supuestos por defecto, WACC, valor terminal, acciones diluidas o tests numéricos del DCF, aunque el usuario solo pida "arreglar el cálculo" o "añadir un parámetro".
---

# Metodología DCF (FCFF)

Esta skill amplía la sección 7 de `AGENTS.md`. Si algo entra en conflicto, **manda AGENTS.md** y se avisa al usuario.

## Cuándo usarla

- Al implementar o modificar `forecast.py`, `wacc.py`, `terminal_value.py`, `bridge.py` o `sensitivity.py`.
- Al escribir tests con cifras del DCF.
- Al elegir valores por defecto de supuestos.

Para un caso resuelto con números, lee `references/worked-example.md`. Para contrastar tu motor, ejecuta `scripts/dcf_reference.py` (referencia mínima, no sustituye al motor real).

## 1. Flujo de caja libre a la empresa

```
NOPAT = EBIT × (1 − t)
FCFF  = NOPAT + D&A − CapEx − ΔNWC
```

Reglas:

- **EBIT base:** el reportado, ajustado por partidas no recurrentes (reestructuración, deterioros, litigios). Documenta cada ajuste con su fuente.
- **Tasa `t`:** tasa normalizada, no la efectiva de un solo año. Por defecto, la efectiva media de 3 años acotada a [15 %, 30 %]. El usuario puede sobrescribirla.
- **SBC (stock-based compensation):** es un coste real. **No lo sumes de vuelta** por defecto. Si el usuario activa el add-back, muestra una advertencia y, además, diluye con las acciones futuras esperadas, o el valor queda inflado.
- **ΔNWC:** solo partidas operativas. Excluye caja, inversiones financieras, deuda y la parte corriente de la deuda.
  `NWC = (Cuentas a cobrar + Inventario + Otros activos corrientes operativos) − (Cuentas a pagar + Pasivos acumulados + Ingresos diferidos)`
- **CapEx:** positivo en el modelo (salida de caja). El XBRL de `PaymentsToAcquirePropertyPlantAndEquipment` ya viene positivo como pago; no le cambies el signo dos veces.
- **D&A:** si incluye amortización de intangibles de adquisiciones, decide explícitamente si se reinvierte. Documéntalo.

## 2. Proyección

- Horizonte 5 años por defecto (configurable 3–10).
- Crecimiento de ingresos con **fade lineal** hacia `g`: `g_t = g_0 + (g − g_0) × (t / n)` o la forma que defina `docs/methodology.md`. Elige una y úsala siempre.
- Márgenes: convergen linealmente hacia el margen objetivo.
- CapEx, D&A y NWC como % de ingresos (o de Δingresos para NWC).
- Si el crecimiento inicial supera el 15 %, el motor lo permite pero la UI muestra aviso de sostenibilidad.

## 3. WACC

```
Ke   = Rf + β × ERP
Kd   = intereses / deuda media    (o input)
WACC = E/(D+E) × Ke + D/(D+E) × Kd × (1 − t)
```

- **β:** si usas una β de mercado, desapalanca y reapalanca a la estructura objetivo: `β_u = β_L / (1 + (1 − t) × D/E)`; `β_L = β_u × (1 + (1 − t) × D/E)`.
- **Pesos:** capitalización de mercado para E; deuda a valor contable salvo que el usuario aporte valor de mercado.
- **Leases operativos:** si los sumas a la deuda en el puente, **inclúyelos también en D del WACC** y asegúrate de que el EBIT no esté ya cargado con el coste total del lease. Sé consistente y documenta la opción elegida.
- Tasa `t` del escudo fiscal: la marginal si se conoce; si no, la normalizada del punto 1.
- Si faltan Rf, β, ERP o precio, **no inventes**: pídelos o pon el campo en blanco.

## 4. Valor terminal

Gordon:

```
TV = FCFF_(n+1) / (WACC − g),  con FCFF_(n+1) = FCFF_n × (1 + g)  (simplificación)
```

Mejor práctica: normalizar el FCFF terminal.

```
NOPAT_(n+1)    = NOPAT_n × (1 + g)
Reinversión    = g / ROIC_terminal
FCFF_(n+1)     = NOPAT_(n+1) × (1 − Reinversión)
```

Reglas de cordura:

- `WACC > g` siempre. Si no, error (`ValuationError`).
- `g` por defecto entre 2,0 % y 2,5 %, nunca por encima de Rf ni del crecimiento nominal de largo plazo.
- En el año terminal, `CapEx ≥ D&A`.
- Aviso si TV / EV > 75 %.
- Con múltiplo de salida: `TV = EBITDA_n × múltiplo`. Calcula siempre el `g` implícito:
  `g = (TV × WACC − FCFF_n) / (TV + FCFF_n)`.

## 5. Descuento

- **Fin de año (defecto):** `DF_t = 1 / (1 + WACC)^t`.
- **Mitad de año:** `DF_t = 1 / (1 + WACC)^(t − 0.5)`. Con Gordon, el TV se descuenta a `n − 0.5`; con múltiplo de salida, a `n`.
- Si la fecha de valoración no coincide con el cierre del último ejercicio, calcula `t` fraccionarios desde la fecha de valoración, y ajusta caja y deuda al momento más cercano disponible.

## 6. Puente de EV a precio por acción

```
Equity = EV + Caja + Inversiones a corto plazo
            − Deuda financiera − Leases (si son deuda)
            − Preferentes − Intereses minoritarios
            (± otros ajustes documentados: pensiones infrafinanciadas,
               inversiones en asociadas, activos no operativos)
Precio = Equity / Acciones diluidas
```

**Acciones diluidas (método de la acción de tesorería):**

```
Acciones diluidas = Básicas
                  + Σ opciones in-the-money × (1 − Precio_ejercicio / Precio_actual)
                  + RSUs/PSUs pendientes
                  + conversión de convertibles si están in-the-money
```

- Solo cuentan las opciones con `Precio_ejercicio < Precio_actual`.
- Usa el precio actual aportado por el usuario. Si el valor depende del propio resultado, itera hasta converger (máx. 20 iteraciones, tolerancia 1e-6).
- Usa las acciones básicas más recientes de la portada del 10-K, no el promedio ponderado del P&L.

## 7. Sensibilidades

- Tabla WACC × g con `WACC − g ≥ 1 pp`; las celdas inválidas se muestran como `n/d`, no como error.
- Rangos por defecto: WACC ± 1 pp en pasos de 0,5; g ± 0,5 pp en pasos de 0,25.
- El centro de la tabla debe coincidir **exactamente** con el caso base. Añade un test.

## 8. Errores frecuentes

| Error | Cómo evitarlo |
|---|---|
| Sumar el SBC de vuelta sin diluir | Mantener SBC como gasto por defecto |
| Mezclar escala (miles/millones) | Normalizar a millones en la frontera de extracción |
| Doble conteo de leases | Elegir una política y aplicarla a EBIT, WACC y puente |
| Descontar el TV con el factor equivocado | Documentar y testear el caso mid-year |
| `g > Rf` o `g` cercano al WACC | Validar y avisar |
| Caja negativa en el puente por mal signo | Test con caso conocido |
| Acciones del P&L en vez de las actuales | Usar la portada del 10-K |
| Tasa efectiva de un año atípico | Usar media normalizada acotada |

## 9. Tests mínimos de esta skill

1. Caso calculado a mano (ver `references/worked-example.md`) con tolerancia `1e-6`.
2. `WACC ≤ g` lanza `ValuationError`.
3. Monotonía: WACC mayor → valor menor; g mayor → valor mayor.
4. El centro de la sensibilidad coincide con el caso base.
5. Con deuda y leases cero, el puente solo suma caja.
6. Mid-year ≥ fin de año con los mismos flujos positivos.
