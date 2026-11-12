---
name: quality-scores
description: Fórmulas, entradas, variantes y umbrales de los scores de calidad y riesgo financiero Piotroski F-Score, Altman Z-Score (Z, Z' y Z''), Beneish M-Score y calidad de beneficios (CFO/beneficio neto, devengos), más ratios de DuPont y ROIC. Úsala siempre que implementes o modifiques analysis/, calcules alguno de estos scores o ratios, o el usuario pregunte por solidez financiera, riesgo de quiebra, manipulación contable o calidad de beneficios.
---

# Scores de calidad y riesgo

Implementación de referencia, con autotests, en `scripts/quality_scores.py`. Cópiala como base de `src/dcf_app/analysis/`; no la importes tal cual.

## Reglas generales

1. **No aplican a empresas financieras** (bancos, aseguradoras): sus balances no tienen capital circulante ni deuda operativa comparables. Si el SIC o los datos indican una financiera, devuelve «no aplicable».
2. Devuelve siempre **valor + desglose por componente + fórmula**. Un score sin desglose no es auditable.
3. Son **señales de alerta**, no veredictos de inversión. La UI muestra la cautela correspondiente.
4. Si falta una entrada, el score es `None` con la lista de entradas faltantes. Nunca calcules con ceros.
5. Todos los datos en la misma escala y moneda. Los promedios de balance usan inicio y fin de ejercicio.

## 1. Piotroski F-Score (0–9)

Un punto por cada criterio cumplido. Necesita dos ejercicios (y activos de t−2 para el ROA del año previo).

| # | Grupo | Criterio |
|---|---|---|
| 1 | Rentabilidad | ROA > 0 (`NI / activos iniciales`) |
| 2 | Rentabilidad | CFO > 0 |
| 3 | Rentabilidad | ΔROA > 0 |
| 4 | Rentabilidad | CFO > beneficio neto (calidad de beneficios) |
| 5 | Apalancamiento / liquidez | Disminuye la deuda a largo plazo sobre activos |
| 6 | Apalancamiento / liquidez | Aumenta el ratio corriente |
| 7 | Apalancamiento / liquidez | Sin emisión neta de acciones |
| 8 | Eficiencia | Aumenta el margen bruto |
| 9 | Eficiencia | Aumenta la rotación de activos (`Ingresos / activos iniciales`) |

Lectura habitual: 8–9 sólido, 0–2 débil, 3–7 intermedio. Originalmente propuesto para empresas con alto ratio valor contable/precio; úsalo como referencia, no como filtro universal.

## 2. Altman Z-Score

Variables:

```
X1 = Capital circulante / Activos totales
X2 = Beneficios retenidos / Activos totales
X3 = EBIT / Activos totales
X4 = Patrimonio / Pasivos totales     (mercado para Z; contable para Z' y Z'')
X5 = Ventas / Activos totales
```

| Variante | Cuándo | Fórmula | Zonas (distress / gris / segura) |
|---|---|---|---|
| **Z** | Cotizada, manufacturera | `1,2·X1 + 1,4·X2 + 3,3·X3 + 0,6·X4 + 1,0·X5` | `< 1,81` / `1,81–2,99` / `> 2,99` |
| **Z'** | Privada o sin precio de mercado | `0,717·X1 + 0,847·X2 + 3,107·X3 + 0,420·X4 + 0,998·X5` | `< 1,23` / `1,23–2,90` / `> 2,90` |
| **Z''** | No manufacturera / emergentes | `6,56·X1 + 3,26·X2 + 6,72·X3 + 1,05·X4` | `< 1,10` / `1,10–2,60` / `> 2,60` |

- Elige la variante según el tipo de empresa y **registra cuál usaste y por qué**.
- Z'' no usa X5, pensada para reducir el sesgo por tipo de industria. Para emergentes algunos autores suman una constante (+3,25); si la usas, documéntalo.
- Para empresas de software o servicios, prefiere Z''.

## 3. Beneish M-Score (8 variables)

Necesita dos ejercicios consecutivos.

```
M = −4,84 + 0,920·DSRI + 0,528·GMI + 0,404·AQI + 0,892·SGI
          + 0,115·DEPI − 0,172·SGAI + 4,679·TATA − 0,327·LVGI
```

| Índice | Fórmula |
|---|---|
| DSRI | `(CxC_t / Ventas_t) / (CxC_{t-1} / Ventas_{t-1})` |
| GMI | `MargenBruto_{t-1} / MargenBruto_t` |
| AQI | `[1 − (AC_t + PPE_t)/AT_t] / [1 − (AC_{t-1} + PPE_{t-1})/AT_{t-1}]` |
| SGI | `Ventas_t / Ventas_{t-1}` |
| DEPI | `[Dep_{t-1}/(Dep_{t-1}+PPE_{t-1})] / [Dep_t/(Dep_t+PPE_t)]` |
| SGAI | `(SGA_t/Ventas_t) / (SGA_{t-1}/Ventas_{t-1})` |
| LVGI | `[(PC_t + DLP_t)/AT_t] / [(PC_{t-1} + DLP_{t-1})/AT_{t-1}]` |
| TATA | `(Resultado de operaciones continuas − CFO) / AT_t` (versión simplificada con flujo de caja) |

- **Umbral:** valores de M por encima de **−1,78** suelen marcarse como posible manipuladora (más sensible). Algunos usan −2,22 (menos conservador). Muestra el umbral usado.
- Si dos ejercicios idénticos dan todos los índices en 1 y `TATA = 0`, el resultado es `−2,48`. Úsalo como test de regresión.
- Es un modelo estadístico con falsos positivos. Un M alto es una razón para **leer las notas contables**, no una acusación.

## 4. Calidad de beneficios

```
CFO / Beneficio neto      > 1 sostenido: beneficios respaldados por caja
Ratio de devengos         = (Beneficio neto − CFO) / Activos totales medios
                            alto y positivo de forma persistente: alerta
```

## 5. DuPont y ROIC

```
ROE (3 factores) = Margen neto × Rotación de activos × Apalancamiento
                 = (NI/Ventas) × (Ventas/AT) × (AT/Patrimonio)

ROIC = NOPAT / Capital invertido medio
Capital invertido = Deuda financiera + Leases (si son deuda) + Patrimonio − Caja excedente
```

Declara la definición de capital invertido que uses y mantenla en todo el proyecto, porque el ROIC terminal del DCF depende de ella.

## Tests mínimos

1. Piotroski: un caso que mejora en todo da 9; otro que empeora en todo da 0.
2. Altman: un caso construido a mano por variante, con tolerancia `1e-9`.
3. Beneish: dos años idénticos dan `−2,48` y `flag = False`.
4. Empresa financiera: devuelve «no aplicable», no un número.
5. Entrada faltante: devuelve `None` y enumera lo que falta.
6. El desglose suma al valor total (Altman, Beneish).
