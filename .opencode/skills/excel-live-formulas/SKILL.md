---
name: excel-live-formulas
description: Cómo exportar la valoración a Excel con openpyxl usando fórmulas vivas, rangos con nombre, convención de colores financiera, hojas Supuestos/Proyección/Valoración y verificación del recálculo con LibreOffice. Úsala siempre que escribas o modifiques export/, generes un .xlsx con el DCF, el usuario pida "exportar a Excel", "que pueda cambiar los supuestos en Excel" o "una hoja con fórmulas", o cuando un Excel exportado muestre valores vacíos, errores #REF!/#NAME? o cifras que no coinciden con la app.
---

# Exportación a Excel con fórmulas vivas

**Regla central:** el Excel debe recalcularse al cambiar un supuesto. Exportar solo números pegados es un informe estático, no un modelo. Un analista tiene que poder auditar y modificar el DCF sin la app.

Scripts (ambos ejecutados y comprobados contra el caso base, **24,64 USD por acción**):

- `scripts/build_dcf_workbook.py`: genera un DCF completo con fórmulas vivas.
- `scripts/verify_recalc.py`: recalcula con LibreOffice y detecta errores.

## Estructura del libro

| Hoja | Contenido |
|---|---|
| `Supuestos` | Todos los inputs, en azul sobre fondo amarillo claro, con su fuente al lado. Cada input escalar tiene un **rango con nombre** (`wacc`, `g_perp`, `tax`...). |
| `Proyeccion` | Años en columnas, líneas en filas. **Solo fórmulas**. |
| `Valoracion` | Valor terminal, EV, puente a equity, precio por acción, controles. |
| (futuras) `WACC`, `Sensibilidad`, `Datos 10-K` | Misma convención. |

## Convención de color

| Color | Significa |
|---|---|
| Azul (`0000FF`) | Input editable por el usuario |
| Negro | Fórmula sobre la misma hoja |
| Verde (`008000`) | Enlace a otra hoja |
| Rojo | Aviso o error (por formato condicional o texto) |

Los inputs además llevan fondo `FFF2CC`. Incluye una leyenda en la hoja `Supuestos`.

## Reglas de construcción

1. **Fórmulas, no valores.** Escribe `=C3*ebit_margin`, no `220`.
2. **Rangos con nombre** para cada input: `wb.defined_names["wacc"] = DefinedName("wacc", attr_text="Supuestos!$B$9")` (openpyxl 3.1). Los nombres no pueden parecerse a una celda (`DA1` no vale; `da_pct` sí).
3. **Un supuesto, una celda.** Si el mismo valor aparece en dos sitios, uno es un enlace al otro.
4. **Ningún número «mágico» dentro de una fórmula**, salvo constantes de unidad (1, 0,5 para mitad de año). Un 0,75 de umbral va a una celda de supuesto o se documenta al lado.
5. **Controles visibles** en `Valoracion`: `WACC > g`, peso del TV, balance cuadra. Que devuelvan `OK` o un texto de aviso, no un error de Excel.
6. **Sin celdas combinadas** en zonas de cálculo, ni referencias circulares.
7. **Formatos de número:** porcentajes `0.0%`; importes `#,##0.0;(#,##0.0);"-"` (negativos entre paréntesis); precio `#,##0.00`; factor de descuento `0.0000`. Unidades en la etiqueta («MM USD»).
8. **Trazabilidad:** junto a cada input extraído del 10-K, una nota con su fuente (concepto XBRL o sección) y periodo.
9. Ancho de columnas razonable, filas de cabecera con relleno oscuro y texto blanco, panes congelados si la hoja crece.

## Trampas de openpyxl

- **No calcula.** Guarda la fórmula sin valor en caché. Si abres el archivo con `data_only=True` verás `None` hasta que Excel o LibreOffice lo recalculen. Por eso existe `verify_recalc.py`.
- Las fórmulas se escriben en sintaxis inglesa con separador de argumentos coma (`=IF(a>b,"x","y")`), aunque el Excel del usuario esté en español: Excel las traduce al abrir.
- Cuidado con comillas dentro de fórmulas de texto: `'=IF(wacc>g_perp,"OK","ERROR")'`.
- Referencias a otras hojas: `=Proyeccion!G9`. Si el nombre de la hoja tiene espacios, va entre comillas simples.
- No uses funciones nuevas de Excel (por ejemplo, matrices dinámicas) si el usuario puede abrirlo en LibreOffice o versiones antiguas. Prefiere `SUM`, `IF`, `INDEX`, `MATCH`.
- Una tabla de sensibilidad WACC × g con fórmulas vivas **no puede usar «tabla de datos»** (what-if) desde openpyxl. Escribe en cada celda la fórmula completa del precio con los parámetros de su fila y columna, o enlaza a un bloque de cálculo compacto. Documenta la opción elegida.

## Verificación obligatoria antes de dar la exportación por buena

1. Ejecuta `python verify_recalc.py archivo.xlsx`.
2. `errores` debe ser `ninguno` (sin `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A`, `#NUM!`).
3. El precio por acción del Excel recalculado coincide con el de la app (`math.isclose`, `abs_tol=0.01`).
4. Cambia un input en el libro (por ejemplo WACC) mediante código, recalcula y comprueba que el precio cambia en la dirección esperada.
5. Si `soffice` no está disponible, dilo: no afirmes que las fórmulas calculan bien sin haberlo comprobado.

## Tests

- Test que abre el `.xlsx` con `openpyxl` (sin `data_only`) y comprueba que las celdas de `Proyeccion` empiezan por `=`.
- Test que comprueba que todos los inputs tienen nombre definido.
- Test de paridad app/Excel con recálculo (marcado `slow` si requiere LibreOffice).
- Test de que ninguna fórmula contiene un número de 3 o más dígitos pegado (señal de valor «hardcodeado»).
