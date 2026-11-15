---
name: beginner-visual-design
description: Guía de diseño visual y de experiencia para una app de valoración dirigida a personas que están empezando a invertir y no saben de finanzas, con flujo guiado, lenguaje llano, glosario, rangos en vez de cifras únicas, gráficos claros (rango de valor, cascada, mapa de sensibilidad), paleta accesible que no sugiere comprar o vender, avisos accionables y modo experto opcional. Úsala siempre que diseñes, cambies o revises cualquier pantalla, texto, gráfico, color, aviso o flujo de la interfaz, aunque el usuario solo pida "mejorar cómo se ve" o "añadir un gráfico".
---

# Diseño visual para principiantes

Complementa `streamlit-ui` (reglas técnicas) con **cómo debe verse y sentirse** la app. Archivos de apoyo:

- `scripts/theme.py`: paleta clara y oscura con **contraste comprobado** (`python theme.py`) y funciones de gráfico (plotly, sin ejecutar).
- `scripts/glossary.py`: 28 términos en español claro, con tooltip (≤ 140 caracteres) y autotest.
- `scripts/streamlit_config.toml`: tema para `.streamlit/config.toml`.
- `references/microcopy-es.md`: titulares, avisos, estados, escenarios, textos legales.
- `references/wireframes.md`: composición de las pantallas.

## Para quién y qué significa «bien»

Una persona que empieza a invertir, que ve la app quizá desde el móvil, que no conoce «WACC» ni «valor terminal» y que puede tomar decisiones con dinero real. La app tiene éxito si esa persona entiende:

1. **Qué dice la valoración** (un rango, no una verdad).
2. **Cuánto fiarse** (qué la hace incierta).
3. **Qué tendría que pasar** para justificar el precio.
4. **Que no es una recomendación.**

Pruebas rápidas: en **5 segundos** debe poder decir qué rango sale y en **30 segundos** por qué. Si no puede, la pantalla tiene demasiado.

## Principios

1. **Respuesta primero, detalle bajo demanda.** Titular en lenguaje llano arriba; lo técnico en expanders («Detalle para expertos»).
2. **Rangos, no números únicos.** Una cifra con decimales da una precisión falsa. Muestra rango y valor central; el exacto, en modo experto.
3. **Incertidumbre visible.** Rango, indicador de confianza con razones y «qué podría salir mal», siempre en el resultado.
4. **Explica donde aparece.** Cada término técnico lleva tooltip del glosario la primera vez.
5. **Nombre llano primero, técnico entre paréntesis:** «Rentabilidad exigida (WACC)».
6. **Valoración no es recomendación.** Sin verde/rojo, sin «comprar/vender», sin «infravalorada/sobrevalorada». Se compara con el precio con frases neutras («un 23 % por encima del precio de hoy») y colores azul/naranja.
7. **Guía, no abrumes.** Flujo de 4 pasos, valores por defecto sensatos y **escenarios con nombre** (Prudente / Equilibrado / Optimista) en lugar de pedir WACC y g. Los controles finos, en modo experto.
8. **Un mensaje por gráfico.** El título dice la conclusión; debajo, «Cómo leer este gráfico».
9. **Avisos que ayudan a actuar:** qué pasa, por qué importa, qué puedes hacer. Nunca códigos ni trazas.
10. **Móvil primero y accesible.** Una columna, texto base 16 px, el significado nunca depende solo del color.

## Flujo

1 Empresa → 2 Datos → 3 Escenario → 4 Resultado. Un paso por vez, con indicador de progreso y botón «Continuar» desactivado si hay un error. Detalle de cada pantalla en `references/wireframes.md`.

## Pantalla de resultado: orden fijo

1. **Titular** con el rango, el valor central, el precio de hoy y la frase de comparación.
2. **Gráfico de rango** con el precio actual como línea discontinua.
3. **Confianza** (Alta/Media/Baja) con 1 a 3 razones concretas.
4. **Qué tendría que pasar** (Reverse DCF en una frase y una comparación con el histórico).
5. **Por qué este número** (cascada del valor del negocio al valor por acción).
6. **Qué podría salir mal** (mapa de sensibilidad y avisos).
7. **Salud de la empresa** (Piotroski, Altman, con zonas y texto; nunca solo un número).
8. **Detalle para expertos** colapsado: flujos, WACC, valor terminal, exportar a Excel.

## Catálogo de gráficos

| Gráfico | Pregunta que responde | Reglas |
|---|---|---|
| Rango de valor | ¿Entre qué cifras cae el valor? | Barra horizontal, valor central marcado, precio de hoy en línea discontinua. El rango sale de la tabla de sensibilidad (o P25–P75 si hay Monte Carlo) |
| Cascada | ¿Cómo llego del negocio al valor por acción? | Valor de empresa → + caja → − deuda → valor para el accionista. Etiquetas en cada barra |
| Mapa de sensibilidad | ¿Qué tan incierto es el resultado? | Máximo 5 × 5, celdas inválidas con «n/d», centro destacado, escala azul/naranja centrada en el precio |
| Flujos futuros | ¿Cuánto dinero libre se espera por año? | Barras: pasado en gris, futuro en azul; empiezan en cero |
| ¿Qué descuenta el mercado? | ¿Es exigente el precio de hoy? | Dos barras: crecimiento exigido frente a histórico |
| Peso del largo plazo | ¿Cuánto depende de supuestos lejanos? | Una sola barra al 100 % con dos tramos (años proyectados y largo plazo) |
| Salud | ¿Cómo está la empresa? | Escala con zonas y palabra («zona segura»); no medidores tipo velocímetro |

Reglas de todos los gráficos:

- **Título = conclusión**, no descripción («El valor cae si exiges más rentabilidad»).
- Ejes con unidades; etiquetas directas en vez de leyendas lejanas.
- Sin 3D, sin ejes duales, sin tartas ni donuts con más de tres sectores.
- Las barras empiezan en cero.
- **El precio actual siempre es una línea discontinua** del mismo estilo.
- La información no puede depender del *hover*: en el móvil no existe. Pon los valores como texto.
- Altura mínima legible en móvil; alternativa en tabla colapsada para quien use lector de pantalla.
- Pie «Cómo leer este gráfico» (textos en `references/microcopy-es.md`).

## Color y tipografía

- Tokens en `scripts/theme.py`. Todos los pares de texto cumplen **AA (≥ 4,5:1)** en claro y oscuro (comprobado: mínimos 5,28:1 en oscuro y 6,37:1 en claro).
- Estados con **icono + palabra + color**: ✔ correcto, ⚠ revisar, ✖ error, ⓘ información.
- **Valor por encima del precio = azul; por debajo = naranja.** Nunca verde/rojo: parecería «bueno/malo» o «comprar/vender».
- Números en formato español (`formatting.py` de `streamlit-ui`), con unidades y `n/d` para ausentes (nunca 0).
- Una tipografía sans-serif del sistema; jerarquía por tamaño y peso, no por mayúsculas ni colores llamativos.

## Estados de pantalla

Cargando (qué está pasando, «paso 2 de 4»), vacío, error de lectura, bloqueado, dato no disponible y **no aplicable** (bancos, aseguradoras, pérdidas): pantalla propia que explica por qué y no muestra un valor. Textos en `references/microcopy-es.md`.

**Los avisos del motor deben llegar a la pantalla.** Un `logger.warning` no lo ve el usuario. El motor devuelve una lista de avisos estructurada (id, cifras) y la UI la traduce con el microcopy.

## Indicador de confianza

Cálculo propuesto, **a validar** por quien responda de las finanzas:

- **Baja** si hay datos que no cuadran, el valor depende de leer un PDF, el EBIT es negativo o el informe tiene más de unos 9 meses sin actualizar.
- **Media** si el valor a largo plazo pesa más del 75 %, hay avisos de datos dudosos o falta el precio.
- **Alta** en el resto.

Muestra siempre 1 a 3 razones concretas. No es una probabilidad de acierto y no debe presentarse como tal.

## Escenarios

Propuesta en `references/microcopy-es.md`. Al elegir uno, la app muestra los supuestos reales en frase llana («Supones que las ventas crecerán 6 % al año al principio…»). El usuario puede abrir «Ajustar los detalles» para tocar WACC, g, márgenes, etc.

## Implementación en Streamlit

- Tarjetas con `st.container(border=True)`; cifras con `st.metric`; ayudas con `help=`; progreso con `st.progress`; detalle con `st.expander`; pasos con una clave de estado `dcf_step`.
- Tema en `.streamlit/config.toml` (copiar `scripts/streamlit_config.toml`).
- Glosario: `help=GLOSSARY["wacc"]["tip"]` y expander «Qué significa» con `simple` y `example`.
- Plotly con `plotly_layout()` de `theme.py`.
- Las opciones de ancho de gráficos y componentes más nuevos (`st.popover`, `st.dialog`, `st.segmented_control`) **dependen de la versión de Streamlit**: comprueba la instalada.
- Lógica financiera nunca en la UI; solo presentación.

## Lo que no se hace

- Verde/rojo para «bien/mal», o cualquier recomendación de compra o venta.
- Una cifra exacta con decimales como titular.
- Siglas sin explicar (WACC, EV, FCFF) en la vista principal.
- Mostrar un valor cuando la validación tiene un error o la empresa no es aplicable.
- Avisos técnicos, trazas o nombres de variables.
- Tablas largas como primera vista.
- Ocultar el aviso legal o los límites del método.
- Animaciones o adornos que distraigan del mensaje.

## Lista de revisión visual

- [ ] ¿Se entiende el resultado en 5 segundos? ¿Y el porqué en 30?
- [ ] ¿Hay rango, confianza con razones y «qué podría salir mal»?
- [ ] ¿Cada término técnico visible tiene tooltip o nombre llano?
- [ ] ¿Cada aviso dice qué pasa, por qué importa y qué hacer?
- [ ] ¿Sin verde/rojo y sin lenguaje de recomendación?
- [ ] ¿El precio actual es una línea discontinua en todos los gráficos?
- [ ] ¿El título de cada gráfico es una conclusión y tiene su «Cómo leer»?
- [ ] ¿Funciona en una columna de móvil, sin depender del *hover*?
- [ ] ¿El significado se mantiene sin color?
- [ ] ¿Aviso legal corto siempre visible?
- [ ] ¿Casos «no aplicable», «bloqueado» y «sin precio» tienen su propia pantalla?
- [ ] ¿Los avisos del motor llegan a la pantalla (no solo a los registros)?

## Cómo probarlo

- `python scripts/theme.py` y `python scripts/glossary.py` (autotests de contraste y glosario).
- `streamlit.testing.v1.AppTest` (si tu versión lo trae) para comprobar que con un error de validación **no** aparece ningún valor y sí el mensaje llano.
- Prueba con 3 personas no expertas: ¿qué rango han entendido?, ¿por qué?, ¿qué harían con eso? Si alguna dice «tengo que comprar/vender», hay que cambiar el texto.
- Revisa capturas en móvil y en modo oscuro.
