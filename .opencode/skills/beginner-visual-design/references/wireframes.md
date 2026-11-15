# Wireframes (guía de composición)

Mobile primero: una columna. En escritorio, máximo dos columnas y ancho de lectura contenido (~900 px). Los bloques son tarjetas (`st.container(border=True)`).

## 1. Inicio y pasos

```
┌──────────────────────────────────────────┐
│  ① Empresa ─ ② Datos ─ ③ Escenario ─ ④ Resultado   │  ← progreso (st.progress o texto)
├──────────────────────────────────────────┤
│  Elige la empresa                        │
│  Escribe el símbolo en bolsa o sube su   │
│  informe anual (10-K).                   │
│                                          │
│  [ AAPL                         ]        │
│  [ o sube un archivo (HTML/PDF)  ]       │
│                                          │
│  ▸ ¿Qué es un informe 10-K?              │  ← expander con glosario
│                                          │
│  [ Continuar ]                           │
├──────────────────────────────────────────┤
│  Herramienta educativa. No es            │  ← aviso corto, siempre visible
│  asesoramiento financiero.               │
└──────────────────────────────────────────┘
```

## 2. Revisar datos (semáforo con palabras)

```
┌──────────────────────────────────────────┐
│  Hemos leído tu informe                  │
│  ✔ Las cuentas cuadran                   │
│  ⚠ El beneficio neto difiere un 1,2 %    │
│     entre dos estados. Podemos seguir,   │
│     con menos confianza.   [Ver detalle] │
│  ✖ (si hay error) Falta el balance       │
│     No podemos dar un valor todavía.     │
│                                          │
│  Confianza en los datos:  ●●○  Media     │
│  ▸ Ver cifras leídas (con su origen)     │  ← tabla en expander, modo experto
│  [ Continuar ]  (desactivado si hay ✖)   │
└──────────────────────────────────────────┘
```

Un ✖ desactiva «Continuar» y explica qué dato corregir. El icono y la palabra acompañan siempre al color.

## 3. Escenario

```
┌──────────────────────────────────────────┐
│  ¿Cómo imaginas el futuro de {empresa}?  │
│                                          │
│  ( ) Prudente      Las cosas salen peor  │
│  (•) Equilibrado   Lo razonable según    │
│                    el pasado             │
│  ( ) Optimista     Salen bien, sin       │
│                    fantasías             │
│                                          │
│  Con este escenario supones que:         │
│   • Las ventas crecerán 6 % al año al    │
│     principio, y 2,5 % a largo plazo     │
│   • De cada 100 vendidos, 20 serán       │
│     beneficio operativo                  │
│   • Rentabilidad exigida: 8,3 %          │
│                                          │
│  ▸ Ajustar los detalles (modo experto)   │
│  [ Ver resultado ]                       │
└──────────────────────────────────────────┘
```

## 4. Resultado (orden fijo de arriba abajo)

Todas las cifras de estos esquemas son ilustrativas.

```
┌──────────────────────────────────────────┐
│  Según tus supuestos, cada acción de     │  ← 1. Titular (texto grande)
│  Empresa Ejemplo valdría entre 21 y 28.  │
│  Valor central: 24,6 USD · Hoy: 20,0 USD │
│  Tu estimación está un 23 % por encima   │
│  del precio de hoy.                      │
│  Es una estimación, no una recomendación │
├──────────────────────────────────────────┤
│  [barra de rango con línea de precio]    │  ← 2. Gráfico de rango
│  Cómo leer este gráfico ▸                │
├──────────────────────────────────────────┤
│  Confianza: Media                        │  ← 3. Confianza con razones
│  • El 75 % del valor depende del largo   │
│    plazo.   • Datos con 8 meses.         │
├──────────────────────────────────────────┤
│  Qué tendría que pasar                   │  ← 4. ¿Qué descuenta el mercado?
│  El precio de hoy exige ventas +14 %     │
│  al año. Históricamente: +8 %.           │
├──────────────────────────────────────────┤
│  Por qué este número                     │  ← 5. Cascada: de negocio a acción
│  [gráfico en cascada]                    │
├──────────────────────────────────────────┤
│  Qué podría salir mal                    │  ← 6. Sensibilidad (mapa 5×5) y avisos
│  [mapa de calor] + avisos con acción     │
├──────────────────────────────────────────┤
│  Salud de la empresa                     │  ← 7. Indicadores con zonas y texto
│  Piotroski 7/9 · Altman: zona segura     │
├──────────────────────────────────────────┤
│  ▸ Detalle para expertos                 │  ← 8. Todo lo técnico, colapsado
│    (flujos, WACC, valor terminal, Excel) │
└──────────────────────────────────────────┘
```

## 5. No aplicable (banco, aseguradora)

```
┌──────────────────────────────────────────┐
│  ⓘ Este método no sirve para bancos      │
│    ni aseguradoras                       │
│  Su dinero y su deuda funcionan distinto │
│  y los números saldrían engañosos.       │
│  [ Probar con otra empresa ]             │
└──────────────────────────────────────────┘
```

Sin cifras de valor en pantalla. Misma estructura para «no aplicable por pérdidas», con la opción de verlo como ejercicio y el aviso permanente.
