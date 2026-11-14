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

## Motor DCF — Fórmulas exactas

### 1. Flujo de caja libre (FCFF)

```
NOPAT = EBIT × (1 − t)
FCFF  = NOPAT + D&A − CapEx − ΔNWC
```

- **EBIT base:** el reportado, ajustado por partidas no recurrentes.
- **Tasa `t`:** tasa normalizada, por defecto la efectiva media de 3 años acotada a [15 %, 30 %].
- **SBC:** gasto real, no se suma de vuelta por defecto.
- **ΔNWC:** solo partidas operativas. `ΔNWC_t = (Revenue_t − Revenue_{t-1}) × nwc_pct`. Para t=0 se usa `base_revenue` (último ejercicio histórico); si no se proporciona, se asume `Revenue_{-1} = 0`.

### 2. Proyección

- Horizonte: 5 años por defecto (configurable 3-10).
- **Fade lineal de crecimiento:**
  ```
  g_t = g_initial + (g_terminal - g_initial) × t / max(horizon - 1, 1)
  ```
  donde `t = 0 … horizon - 1`. Con `horizon = 1` se usa `g_initial`.
  ```
  Revenue_t = Revenue_{t-1} × (1 + g_t)
  ```
- **Convergencia lineal de margen EBIT:**
  ```
  m_t = m_current + (m_target - m_current) × t / max(horizon - 1, 1)
  ```
- EBIT = Revenue × margen EBIT
- NOPAT = EBIT × (1 − t)
- D&A = Revenue × da_pct
- CapEx = Revenue × capex_pct
- FCFF = NOPAT + D&A − CapEx − ΔNWC

### 3. WACC

```
Ke   = Rf + β × ERP
Kd   = intereses / deuda (o input)
WACC = E/(D+E) × Ke + D/(D+E) × Kd × (1 − t)
```

- **β:** beta apalancada (input del usuario). Si se usa beta de industria de Damodaran, desapalanca y reapalanca a la estructura de la empresa.
- **Pesos:** capitalización de mercado para equity; deuda a valor contable (o mercado si se aporta). Leases financieros se suman a la deuda.
- **Política de leases (US GAAP):** los leases operativos NO se restan ni entran en la deuda del WACC (su coste ya está en el EBIT). Los financieros SÍ, en ambos sitios (puente y WACC).

### 4. Valor terminal

**Gordon Growth (método principal):**
```
NOPAT_(n+1)    = NOPAT_n × (1 + g)
Reinversión    = g / ROIC_terminal  (ROIC_terminal por defecto = WACC)
FCFF_(n+1)     = NOPAT_(n+1) × (1 − Reinversión)
TV             = FCFF_(n+1) / (WACC − g)
```

**Múltiplo de salida (contraste):**
```
TV = EBITDA_n × múltiplo
```

**Reglas de cordura:**
- `WACC > g` siempre (error si no se cumple)
- `g` por defecto 2,0-2,5 %, nunca superior a Rf
- Aviso si TV / EV > 75 %
- En el año terminal, CapEx ≥ D&A

### 5. Descuento

- **Fin de año (defecto):** `DF_t = 1 / (1 + WACC)^t`
- **Mitad de año:** `DF_t = 1 / (1 + WACC)^(t − 0.5)`. Con Gordon, el TV se descuenta a `n − 0.5`.

### 6. Puente EV → Equity

```
Equity = EV + Caja + Inversiones CP
            − Deuda financiera − Leases financieros
            − Preferentes − Intereses minoritarios
            (± otros ajustes)
Precio = Equity / Acciones diluidas
```

**Acciones diluidas (método de la acción de tesorería):**
```
Diluidas = Básicas + Σ opciones in-the-money × (1 − Precio_ejercicio / Precio_actual) + RSUs
```
Solo cuentan opciones con `Precio_ejercicio < Precio_actual`.

### 7. Sensibilidades

- Tabla WACC × g con `WACC − g ≥ 1 pp`; celdas inválidas → `n/d`
- El centro de la tabla coincide exactamente con el caso base

### 8. Errores frecuentes

| Error | Cómo evitarlo |
|---|---|
| Sumar el SBC de vuelta sin diluir | Mantener SBC como gasto por defecto |
| Mezclar escala (miles/millones) | Normalizar a millones en la frontera de extracción |
| Doble conteo de leases | Política documentada (operativos fuera, financieros dentro) |
| Descontar el TV con el factor equivocado | Documentar y testear el caso mid-year |
| `g > Rf` o `g` cercano al WACC | Validar y avisar |
| Caja negativa en el puente por mal signo | Test con caso conocido |
| Acciones del P&L en vez de las actuales | Usar la portada del 10-K |
| Tasa efectiva de un año atípico | Usar media normalizada acotada |