# Textos de la interfaz (español claro)

Tono: cercano, tranquilo y directo. Tuteo. Frases cortas. Sin culpar al usuario ni asustarlo. Cada texto responde a: **qué pasa, por qué importa, qué puedes hacer.**

Reglas de redacción:

- Nombre llano primero, término técnico después y entre paréntesis: «Rentabilidad exigida (WACC)».
- Nunca «comprar», «vender», «infravalorada», «sobrevalorada», «oportunidad» ni «garantizado».
- Di «estimación», «según tus supuestos», «podría». Nunca «la empresa vale X» a secas.
- Cifras redondeadas en lo que se muestra de entrada (precio con 2 decimales, porcentajes con 1). El detalle exacto, en el modo experto.
- Evita siglas sin explicar (EV, FCFF, NOPAT, TSM). Si aparecen, con tooltip del glosario.
- Nada de mensajes técnicos (`ValueError`, trazas, nombres de variables). Esos van a los registros.

## Pasos del flujo

| Paso | Título | Texto de ayuda |
|---|---|---|
| 1 | Elige la empresa | Escribe el símbolo en bolsa (por ejemplo AAPL) o sube su informe anual (10-K). |
| 2 | Revisa los datos | Comprobamos que las cuentas cuadran. Si algo falla, te lo explicamos. |
| 3 | Elige un escenario | Tres puntos de partida. Puedes ajustar los detalles si quieres. |
| 4 | Mira el resultado | Un rango de valor, no una cifra exacta. |

## Titular del resultado

```
Según tus supuestos, cada acción de {empresa} valdría entre {bajo} y {alto} USD.
Valor central: {medio} USD. Hoy cotiza a {precio} USD.
```

Frase de comparación (usa la distancia entre valor central y precio):

| Distancia | Frase |
|---|---|
| entre −5 % y +5 % | Tu estimación está cerca del precio de hoy. |
| más de +5 % | Tu estimación central está un {pct} % por encima del precio de hoy. |
| menos de −5 % | Tu estimación central está un {pct} % por debajo del precio de hoy. |

Siempre debajo, en texto atenuado: «Es una estimación basada en supuestos. No es una predicción ni una recomendación de inversión.»

Sin precio: «Valor estimado entre {bajo} y {alto} USD por acción. Añade el precio actual para compararlo.»

## Escenarios predefinidos

Son puntos de partida con nombres llanos. Los números concretos los decide quien responda de las finanzas del producto; la tabla es una **propuesta a validar**.

| Escenario | Qué significa para el usuario | Propuesta técnica (a validar) |
|---|---|---|
| Prudente | «Las cosas salen peor de lo habitual.» | Crecimiento inicial = mitad del crecimiento histórico; margen objetivo = margen medio histórico; rentabilidad exigida +1 punto |
| Equilibrado | «Lo más razonable según el pasado.» | Valores por defecto de la app |
| Optimista | «Las cosas salen bien, pero sin fantasías.» | Crecimiento inicial = histórico (con tope); margen objetivo = actual + hasta 2 puntos (sin superar el máximo histórico); rentabilidad exigida −0,5 puntos |

Al elegir uno, mostrar debajo los supuestos reales en lenguaje llano: «Supones que las ventas crecerán 6 % al año al principio, hasta 2,5 % a largo plazo.»

## Avisos

Formato: icono + título corto en negrita + una frase de qué pasa + una frase de por qué importa + «Qué puedes hacer».

| Id | Título | Qué pasa y por qué importa | Qué puedes hacer |
|---|---|---|---|
| tv_alto | Gran parte del valor depende del largo plazo | El {pct} % del valor viene de lo que pase después del año {n}. Cuanto más lejano es el supuesto, más incierto es el resultado. | Prueba con un crecimiento a largo plazo más bajo y mira cuánto cambia el valor. |
| ebit_negativo | Esta empresa pierde dinero en su negocio principal | Este método supone beneficios futuros razonables. Con pérdidas, el resultado puede no tener sentido. | Úsalo solo como ejercicio, o espera a que la empresa sea rentable. |
| financiera | Este método no sirve para bancos ni aseguradoras | Su dinero y su deuda funcionan distinto, y los números salen engañosos. | No te mostramos un valor. Prueba con una empresa no financiera. |
| reit | Las inmobiliarias cotizadas se valoran de otra forma | Este método no recoge bien cómo reparten beneficios. | Interpreta el resultado con mucha cautela. |
| coste_deuda_bajo | El coste de la deuda sale más bajo que el bono del Tesoro | Es poco habitual y puede venir de un dato mal leído. | Revisa el dato o escribe uno tú. |
| datos_antiguos | Los datos tienen {meses} meses | Desde entonces la empresa pudo cambiar su deuda, su caja o sus acciones. | Sube un informe más reciente. |
| datos_no_cuadran | Hay cifras que no cuadran | {detalle_llano}. Con datos así no podemos dar un valor fiable. | Revisa el archivo o prueba con otro. |
| datos_dudosos | Hay cifras que conviene revisar | {detalle_llano}. Podemos seguir, pero con menos confianza. | Mira las cifras marcadas en amarillo. |
| lectura_pdf | Leímos tu PDF como texto | Puede haber errores de lectura, sobre todo en tablas. | Revisa las cifras marcadas. Un archivo HTML suele leerse mejor. |
| sin_precio | Falta el precio de la acción | Podemos calcular el valor, pero no compararlo con el mercado. | Añade el precio actual si quieres la comparación. |
| supuestos_limite | Tus supuestos están muy cerca de un límite | Un cambio pequeño en la rentabilidad exigida o en el crecimiento a largo plazo cambia mucho el resultado. | Baja el crecimiento a largo plazo o sube la rentabilidad exigida. |
| supuesto_invalido | Esa combinación no es posible | La rentabilidad exigida ({wacc}) debe ser mayor que el crecimiento a largo plazo ({g}). | Cambia uno de los dos. |

## Estados de pantalla

| Estado | Texto |
|---|---|
| Cargando (extracción) | Leyendo tu informe… paso {i} de {n}: {tarea} |
| Cargando (cálculo) | Calculando el valor con tus supuestos… |
| Vacío | Todavía no has elegido una empresa. Empieza por el paso 1. |
| Error de lectura | No pudimos leer este archivo. Comprueba que es el informe anual (10-K) de la empresa, en HTML o PDF. |
| Sin conexión | No hay conexión. Puedes seguir con un archivo que ya tengas. |
| Dato no disponible | n/d (no está en el informe) |
| Bloqueado | No podemos darte un valor todavía: {motivo_llano}. |

## Indicador de confianza

| Nivel | Texto |
|---|---|
| Alta | Los datos cuadran y el resultado no depende demasiado de supuestos lejanos. |
| Media | Hay algún aspecto que conviene revisar: {razón_1}. |
| Baja | {razón_1}; {razón_2}. Toma el resultado solo como ejercicio. |

Mostrar siempre 1 a 3 razones concretas. No es una probabilidad de acertar.

## Pies de gráfico («Cómo leer este gráfico»)

| Gráfico | Texto |
|---|---|
| Rango de valor | La barra muestra el rango en el que cae el valor al variar los supuestos más importantes. La línea discontinua es el precio de hoy. |
| Cascada | Parte del valor del negocio entero. Se suma la caja y se resta la deuda hasta llegar a lo que queda para los accionistas. |
| Mapa de sensibilidad | Cada casilla es el valor por acción con otra combinación. El cuadro central es tu escenario. Cuanto más cambian los colores, más incierto es el resultado. |
| Flujos futuros | Barras con el dinero libre que se espera cada año. Las grises son datos pasados. |
| ¿Qué descuenta el mercado? | Compara el crecimiento que exige el precio de hoy con el que la empresa ha logrado. |

## Avisos legales

Corto, siempre visible: «Herramienta educativa. No es asesoramiento financiero ni una recomendación de inversión.»

Largo (enlace «Más información»): «Esta herramienta calcula estimaciones a partir de las cuentas publicadas de la empresa y de los supuestos que eliges. Los resultados dependen mucho de esos supuestos y pueden ser muy distintos de la realidad. Invertir implica riesgo de pérdida. Antes de tomar decisiones, consulta con un profesional que conozca tu situación.»

## Bienvenida (una sola vez)

«Esta herramienta te ayuda a estimar cuánto podría valer una empresa y qué tendría que pasar para justificar su precio. No te dice qué comprar. En 4 pasos tendrás un rango de valor y verás qué lo sostiene.»
