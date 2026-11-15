"""Glosario en español claro para el público principiante.

Cada término: `term` (nombre visible), `simple` (explicación de 1-2 frases, sin jerga),
`example` (analogía o cifra sencilla) y `tip` (texto corto para tooltip, <= 140 caracteres).
Úsalo desde la UI: tooltips con `tip` y paneles «Qué significa» con `simple` + `example`.
Autotest: `python glossary.py`.
"""
from __future__ import annotations

GLOSSARY: dict[str, dict[str, str]] = {
    "dcf": {
        "term": "Valoración por flujos de caja (DCF)",
        "simple": "Estima cuánto vale una empresa hoy sumando el dinero que se espera que genere en el futuro, restando lo que cuesta esperar.",
        "example": "Como valorar un alquiler: no pagas lo que cobrarás en 10 años, sino su valor de hoy.",
        "tip": "Calcula cuánto vale la empresa hoy a partir del dinero que se espera que genere en el futuro.",
    },
    "fcff": {
        "term": "Flujo de caja libre",
        "simple": "El dinero que le queda a la empresa después de pagar sus gastos e inversiones, antes de pagar a quienes le prestaron dinero.",
        "example": "Si una tienda vende 100, gasta 70 y reinvierte 10, le quedan 20 libres.",
        "tip": "Dinero que le queda a la empresa tras gastos e inversiones, antes de pagar a prestamistas.",
    },
    "wacc": {
        "term": "Rentabilidad exigida (WACC)",
        "simple": "La rentabilidad mínima que necesitan los inversores y prestamistas de la empresa para aceptar su riesgo. Se usa para descontar el futuro.",
        "example": "A mayor riesgo, mayor rentabilidad exigida y menor valor de hoy.",
        "tip": "Rentabilidad mínima que exigen quienes financian la empresa. Más riesgo, más exigencia, menor valor.",
    },
    "rf": {
        "term": "Tasa libre de riesgo",
        "simple": "Lo que rinde una inversión casi sin riesgo, normalmente el bono del Tesoro de EE. UU. a 10 años.",
        "example": "Si el bono rinde 4 %, cualquier otra inversión debe ofrecer más para compensar su riesgo.",
        "tip": "Rendimiento de una inversión casi sin riesgo (bono del Tesoro a 10 años). Es el punto de partida del cálculo.",
    },
    "beta": {
        "term": "Beta",
        "simple": "Mide cuánto se mueve una acción respecto al mercado. Mayor que 1: se mueve más que el mercado. Menor que 1: menos.",
        "example": "Con beta 1,5, si el mercado sube 10 %, la acción tiende a subir más, y a caer más cuando baja.",
        "tip": "Cuánto se mueve la acción respecto al mercado. Más de 1: más volátil. Menos de 1: más estable.",
    },
    "erp": {
        "term": "Prima de riesgo del mercado",
        "simple": "El extra de rentabilidad que se pide por invertir en bolsa en lugar de en un bono sin riesgo.",
        "example": "Si el bono rinde 4 % y la prima es 5 %, la bolsa en conjunto debería rendir sobre 9 %.",
        "tip": "Rentabilidad extra que se exige por invertir en bolsa en vez de en un bono sin riesgo.",
    },
    "kd": {
        "term": "Coste de la deuda",
        "simple": "El interés medio que paga la empresa por el dinero que debe.",
        "example": "Si debe 1.000 y paga 50 de intereses al año, su coste de deuda es 5 %.",
        "tip": "Interés medio que paga la empresa por su deuda. Se calcula como intereses entre deuda.",
    },
    "g": {
        "term": "Crecimiento a largo plazo",
        "simple": "Ritmo al que se supone que crecerá la empresa para siempre después de los años que proyectamos. Debe ser modesto, parecido al crecimiento de la economía.",
        "example": "Un 2-2,5 % es habitual. Un 6 % para siempre sería irreal.",
        "tip": "Crecimiento anual supuesto después del último año proyectado. Debe ser modesto, como el de la economía.",
    },
    "terminal_value": {
        "term": "Valor a largo plazo (valor terminal)",
        "simple": "La parte del valor que viene de lo que pase después del último año proyectado. Suele ser más de la mitad del total.",
        "example": "Si pesa el 80 %, tu resultado depende mucho de supuestos lejanos, y es menos fiable.",
        "tip": "Parte del valor que depende de lo que ocurra tras el último año proyectado. Si pesa mucho, hay más incertidumbre.",
    },
    "ev": {
        "term": "Valor de la empresa",
        "simple": "Lo que vale el negocio entero, sin contar cómo se financia: incluye la parte de los accionistas y la de los prestamistas.",
        "example": "Una casa vale 300, aunque tengas una hipoteca de 200 sobre ella.",
        "tip": "Valor del negocio completo, antes de restar la deuda. Después se pasa al valor para el accionista.",
    },
    "equity": {
        "term": "Valor para el accionista",
        "simple": "Lo que le corresponde a los dueños después de sumar la caja y restar la deuda.",
        "example": "Casa de 300 con hipoteca de 200: tu parte vale 100.",
        "tip": "Valor que queda para los accionistas tras sumar la caja y restar la deuda.",
    },
    "net_debt": {
        "term": "Deuda neta",
        "simple": "La deuda menos el dinero en caja. Muestra cuánto debe realmente la empresa.",
        "example": "Debe 500 y tiene 200 en caja: deuda neta 300.",
        "tip": "Deuda menos caja. Cuánto debe la empresa una vez descontado el dinero que tiene.",
    },
    "diluted_shares": {
        "term": "Acciones diluidas",
        "simple": "Las acciones actuales más las que podrían crearse con opciones y bonos para empleados. Se usa para repartir el valor entre todas.",
        "example": "100 acciones y 10 opciones en el dinero pueden dar 106 acciones diluidas.",
        "tip": "Acciones actuales más las que podrían crearse por opciones de empleados. Reparten el valor entre todas.",
    },
    "ebit_margin": {
        "term": "Margen operativo",
        "simple": "De cada 100 que vende la empresa, cuánto le queda del negocio principal antes de intereses e impuestos.",
        "example": "Margen del 20 %: de 100 vendidos, 20 son beneficio operativo.",
        "tip": "Parte de las ventas que se queda como beneficio del negocio, antes de intereses e impuestos.",
    },
    "cagr": {
        "term": "Crecimiento anual medio",
        "simple": "El ritmo medio de crecimiento por año durante un periodo, como si hubiera sido constante.",
        "example": "Ventas de 100 a 133 en 3 años: crecimiento anual medio de 10 %.",
        "tip": "Crecimiento medio por año durante varios años. Sirve para comparar con lo que se proyecta.",
    },
    "capex": {
        "term": "Inversión en activos (CapEx)",
        "simple": "Dinero que la empresa gasta en fábricas, equipos o tecnología para mantener y hacer crecer el negocio.",
        "example": "Una cadena que abre tiendas nuevas.",
        "tip": "Dinero que la empresa invierte en equipos, instalaciones o tecnología.",
    },
    "nwc": {
        "term": "Capital circulante",
        "simple": "El dinero atado en el día a día: lo que te deben los clientes y el inventario, menos lo que debes a proveedores.",
        "example": "Si vendes a crédito, tu dinero tarda en llegar y ese retraso necesita financiación.",
        "tip": "Dinero atado al funcionamiento diario: cobros pendientes e inventario, menos pagos pendientes.",
    },
    "roic": {
        "term": "Rentabilidad sobre el capital invertido (ROIC)",
        "simple": "Cuánto gana la empresa por cada dólar invertido en su negocio. Si supera la rentabilidad exigida, crea valor.",
        "example": "Invierte 100 y gana 15 al año: ROIC del 15 %.",
        "tip": "Beneficio que genera la empresa por cada dólar invertido en el negocio.",
    },
    "upside": {
        "term": "Diferencia con el precio",
        "simple": "Cuánto más o menos vale la acción según tu estimación frente a su precio actual en bolsa. No es una predicción.",
        "example": "Valor estimado 25 y precio 20: tu estimación está un 25 % por encima del precio.",
        "tip": "Diferencia entre tu valor estimado y el precio de hoy. Es una estimación, no una predicción.",
    },
    "reverse_dcf": {
        "term": "¿Qué descuenta el mercado?",
        "simple": "Hace el cálculo al revés: parte del precio de hoy y averigua qué crecimiento tendría que lograr la empresa para justificarlo.",
        "example": "Si el precio exige crecer 18 % al año y la empresa creció 8 %, el mercado espera mucho más.",
        "tip": "Parte del precio actual y calcula qué crecimiento tendría que lograr la empresa para justificarlo.",
    },
    "sensitivity": {
        "term": "Tabla de sensibilidad",
        "simple": "Muestra cómo cambia el valor si cambias un par de supuestos importantes. Enseña lo incierto que es el resultado.",
        "example": "Con rentabilidad exigida 8 % vale unos 30; con 10 %, unos 21.",
        "tip": "Muestra cómo cambia el valor al variar supuestos clave. Cuanto más cambia, más incierto es el resultado.",
    },
    "piotroski": {
        "term": "Puntuación Piotroski",
        "simple": "Nota de 0 a 9 sobre la salud financiera: beneficios, deuda y eficiencia. Más alta, mejor señal. No predice el precio.",
        "example": "8-9 señala solidez; 0-2, debilidad.",
        "tip": "Nota de 0 a 9 de salud financiera (beneficios, deuda, eficiencia). Es una señal, no una recomendación.",
    },
    "altman": {
        "term": "Puntuación Altman (riesgo de quiebra)",
        "simple": "Indicador que estima el riesgo de dificultades financieras graves. Tiene zonas: segura, gris y de riesgo. No sirve para bancos.",
        "example": "Zona de riesgo: conviene mirar la deuda y la caja con más cuidado.",
        "tip": "Estima el riesgo de problemas financieros graves. Zonas: segura, gris y de riesgo. No vale para bancos.",
    },
    "beneish": {
        "term": "Alerta contable (Beneish)",
        "simple": "Indicador estadístico que busca señales de que los beneficios podrían estar maquillados. Una alerta es motivo para mirar con más atención, no una acusación.",
        "example": "Si las ventas a crédito suben mucho más que las ventas, puede haber algo que revisar.",
        "tip": "Busca señales de beneficios maquillados. Una alerta es motivo para investigar, no una acusación.",
    },
    "earnings_quality": {
        "term": "Calidad de los beneficios",
        "simple": "Compara el beneficio contable con el dinero que realmente entra en caja. Si siempre hay mucho más beneficio que caja, hay que preguntarse por qué.",
        "example": "Beneficio de 100 y caja de 60: parte del beneficio todavía no es dinero.",
        "tip": "Compara el beneficio con el dinero real que entra. Si hay mucha diferencia, conviene investigar.",
    },
    "sbc": {
        "term": "Compensación en acciones",
        "simple": "Parte del sueldo de los empleados que se paga con acciones. Es un coste real para los accionistas, aunque no salga dinero de caja.",
        "example": "Paga 100 en acciones: los accionistas pasan a tener una porción menor.",
        "tip": "Sueldos pagados en acciones. Es un coste real para los accionistas, aunque no salga dinero de caja.",
    },
    "form_10k": {
        "term": "Informe 10-K",
        "simple": "El informe anual que las empresas que cotizan en EE. UU. presentan a la SEC. Contiene sus cuentas auditadas.",
        "example": "Es como el boletín de notas anual de la empresa.",
        "tip": "Informe anual que las empresas cotizadas en EE. UU. presentan a la SEC, con sus cuentas auditadas.",
    },
    "tsm": {
        "term": "Método de la acción de tesorería",
        "simple": "Forma de contar cuántas acciones nuevas añaden las opciones de empleados: supone que el dinero de su ejercicio recompra acciones.",
        "example": "10 opciones con precio de ejercicio 20 y acción a 50 añaden 6 acciones.",
        "tip": "Cuenta cuántas acciones nuevas añaden las opciones de empleados, descontando las que se recomprarían.",
    },
}


if __name__ == "__main__":
    long_tips = {k: len(v["tip"]) for k, v in GLOSSARY.items() if len(v["tip"]) > 140}
    missing = [k for k, v in GLOSSARY.items()
               if set(v) != {"term", "simple", "example", "tip"} or not all(v.values())]
    assert not long_tips, f"tooltips > 140: {long_tips}"
    assert not missing, f"entradas incompletas: {missing}"
    print(f"glosario OK: {len(GLOSSARY)} términos; tooltip máx {max(len(v['tip']) for v in GLOSSARY.values())} caracteres")
