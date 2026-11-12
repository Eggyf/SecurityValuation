# Ejemplo resuelto (verificable con `scripts/dcf_reference.py`)

Importes en millones. Todos los números salen del script; si cambias algo, vuelve a ejecutarlo.

## Entradas

| Concepto | Valor |
|---|---|
| Ingresos año 0 | 1.000 |
| Crecimiento años 1–5 | 10 %, 8 %, 6 %, 5 %, 4 % |
| Margen EBIT | 20 % (constante) |
| Tasa impositiva | 21 % |
| D&A | 4 % de ingresos |
| CapEx | 5 % de ingresos |
| ΔNWC | 10 % de Δingresos |
| WACC | 9 % |
| g | 2,5 % |
| Caja / Deuda | 150 / 400 |
| Acciones diluidas | 100 |
| Convención | Fin de año |

## Año 1 a mano

```
Ingresos = 1.000 × 1,10                 = 1.100,0
EBIT     = 1.100 × 20 %                 =   220,0
NOPAT    = 220 × (1 − 21 %)             =   173,8
D&A      = 1.100 × 4 %                  =    44,0
CapEx    = 1.100 × 5 %                  =    55,0
ΔNWC     = (1.100 − 1.000) × 10 %       =    10,0
FCFF     = 173,8 + 44,0 − 55,0 − 10,0   =   152,8
```

## Resultados

| Año | Ingresos | FCFF | Factor de descuento |
|---|---|---|---|
| 1 | 1.100,0 | 152,8 | 0,9174 |
| 2 | 1.188,0 | 167,0 | 0,8417 |
| 3 | 1.259,3 | 179,2 | 0,7722 |
| 4 | 1.322,2 | 189,4 | 0,7084 |
| 5 | 1.375,1 | 198,2 | 0,6499 |

```
PV(FCFF 1–5)   =   682,2
TV (Gordon)    = 198,2 × 1,025 / (0,09 − 0,025) = 3.125,9
PV(TV)         = 3.125,9 / 1,09^5               = 2.031,7
EV             = 682,2 + 2.031,7                = 2.713,8
Equity         = 2.713,8 + 150 − 400            = 2.463,8
Precio/acción  = 2.463,8 / 100                  =    24,64
TV / EV        =                                   74,9 %
```

El TV pesa casi el 75 %: está en el límite del aviso. Es normal en un DCF a 5 años.

## Sensibilidad (precio por acción)

| | WACC 8 % | WACC 9 % | WACC 10 % |
|---|---|---|---|
| g 2,0 % | n/d en este ejemplo | 23,10 | n/d en este ejemplo |
| g 2,5 % | 29,65 | **24,64** | 20,96 |
| g 3,0 % | n/d en este ejemplo | 26,44 | n/d en este ejemplo |

(Los valores `n/d` solo indican que el script no los calculó, no que sean inválidos.)

## Mid-year

Con convención de mitad de año (flujos a `t − 0,5` y TV a `n − 0,5`): **25,83** por acción.

## Test sugerido

```python
def test_worked_example_matches_reference():
    result = run_dcf(base_inputs)
    assert math.isclose(result.enterprise_value, 2713.8, abs_tol=0.1)
    assert math.isclose(result.price_per_share, 24.64, abs_tol=0.01)
```
