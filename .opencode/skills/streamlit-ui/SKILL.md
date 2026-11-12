---
name: streamlit-ui
description: Convenciones para la interfaz Streamlit de la app de valoración, incluyendo separación entre UI y lógica financiera, estado de sesión, pestañas, formato de cifras en español, avisos de validación que bloquean la valoración, disclaimer siempre visible, modo online apagado por defecto y trazabilidad de datos. Úsala siempre que crees o modifiques ui/app.py o cualquier página, widget o gráfico de la app, o cuando la interfaz muestre cifras mal formateadas, pierda el estado al interactuar o recalcule demasiado.
---

# Interfaz Streamlit

Archivos de referencia en `scripts/`:

- `formatting.py`: formateo en español con autotests ejecutados (`python formatting.py`).
- `app_skeleton.py`: esqueleto de la app. **Solo comprobado sintácticamente**; no se ejecutó con Streamlit. Revisa la API contra la versión instalada.

## Reglas de oro

1. **La UI no calcula finanzas.** Los widgets recogen entradas y llaman a funciones de `dcf_app/`; los resultados se muestran tal cual. Si escribes una fórmula del DCF dentro de `ui/`, está mal ubicada.
2. **El disclaimer financiero siempre visible** (barra lateral y pie). No es opcional ni se puede ocultar.
3. **Un `ERROR` de validación bloquea los resultados.** Muestra el error y detén con `st.stop()`; no enseñes un precio «con asterisco».
4. **Todo dato muestra su procedencia.** Cifras del 10-K: concepto o sección y confianza. Datos externos: proveedor y fecha. Supuestos por defecto: de dónde salen.
5. **Todo supuesto es editable.** El usuario manda; la UI avisa, no impone (salvo errores matemáticos como `WACC ≤ g`).
6. **Modo online apagado por defecto** (`dcf_online=False`). Nada sale a la red sin que el usuario lo active, y se indica claramente qué se descargaría.
7. **Nunca mostrar claves, rutas locales sensibles ni el `User-Agent` completo.**

## Estructura de pantalla

| Pestaña | Contenido |
|---|---|
| Datos | Subida del 10-K, tabla de datos extraídos con fuente, validaciones |
| Supuestos | Inputs editables agrupados (crecimiento, márgenes, WACC, terminal) |
| Resultados | Métricas principales, puente EV → equity, avisos |
| Sensibilidad | Tabla WACC × g y margen × crecimiento |
| Resumen (v2) | Football field, Monte Carlo, múltiplos, contrastes |

Una sola página con `st.tabs`. Orden lógico: datos → supuestos → resultados.

## Estado de sesión

- Cada ejecución reejecuta el script entero: **lo que debe persistir va en `st.session_state`**.
- Claves con prefijo `dcf_` y creadas en una única función `init_state()` con `setdefault`.
- Widgets con `key=` explícito para no perder valores al recolocar la interfaz.
- No guardes objetos enormes duplicados; guarda el modelo Pydantic y deriva tablas al mostrar.
- No uses `st.session_state` como sustituto de parámetros de función en `valuation/`.

## Rendimiento

- `@st.cache_data` solo en funciones **puras** con argumentos hashables (por ejemplo, la tabla de sensibilidad o Monte Carlo con semilla). No cachees lecturas de red sin TTL.
- `@st.cache_data(ttl=...)` para datos externos, con el mismo TTL definido en `data_sources/`.
- Los cálculos pesados (Monte Carlo) se lanzan con un botón y `st.spinner`, no en cada interacción.
- Usa `st.form` si un grupo de inputs debe aplicarse junto, para evitar recalcular tras cada tecla.

## Formato de cifras

- Usa `formatting.py`: coma decimal, punto de millar, porcentajes con espacio antes del `%`.
- **Porcentajes como fracciones en el modelo**, como porcentaje en el widget. Convierte en el borde con `pct_input_to_fraction`.
- Negativos con signo menos (`−`), no entre paréntesis, en la UI. Los paréntesis son para Excel.
- Datos ausentes: `n/d`, nunca `0`.
- Unidades en la etiqueta («MM USD»), no solo en el pie.

## Avisos de validación

| Nivel | Componente | Efecto |
|---|---|---|
| `OK` | `st.success` | Informa |
| `WARNING` | `st.warning` | No bloquea; indica cifra y causa |
| `ERROR` | `st.error` + `st.stop()` | Bloquea resultados |

Cada aviso lleva la **cifra concreta** («peso del TV 82 %, umbral 75 %»), nunca «parece alto».

## Gráficos

- `plotly` para football field, histograma de Monte Carlo y sensibilidades.
- Etiquetas de ejes con unidades; línea del precio actual si existe.
- Texto alternativo o tabla equivalente para la información importante, no solo color.
- Los parámetros de ancho (`use_container_width` o `width`) cambian entre versiones de Streamlit: **comprueba la versión instalada** antes de usarlos.

## Accesibilidad y claridad

- No transmitas el significado solo con color (verde/rojo): añade texto o icono.
- Etiquetas y ayudas (`help=`) en español claro, con la fórmula cuando aplique.
- Un resultado no se presenta como «recomendación» ni «comprar/vender».

## Qué probar

- Funciones de formato (ya hay autotests).
- Lógica de decisión de la UI extraída a funciones puras (`can_show_results(validation)`), no dentro del código de Streamlit.
- Opcional: `streamlit.testing.v1.AppTest` para comprobar que, con un `ERROR`, no aparece la métrica de precio. Verifica que existe en tu versión.
