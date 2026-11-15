"""Glosario en español claro para el público principiante."""

GLOSSARY: dict[str, dict[str, str]] = {
    "dcf": {
        "term": "Valoración por flujos de caja (DCF)",
        "simple": "Estima cuánto vale una empresa hoy sumando el dinero que se espera que genere en el futuro, restando lo que cuesta esperar.",  # noqa: E501
        "tip": "Calcula cuánto vale la empresa hoy a partir del dinero que se espera que genere en el futuro.",  # noqa: E501
    },
    "fcff": {
        "term": "Flujo de caja libre",
        "simple": "El dinero que le queda a la empresa después de pagar sus gastos e inversiones, antes de pagar a quienes le prestaron dinero.",  # noqa: E501
        "tip": "Dinero que le queda a la empresa tras gastos e inversiones, antes de pagar a prestamistas.",  # noqa: E501
    },
    "wacc": {
        "term": "Rentabilidad exigida (WACC)",
        "simple": "La rentabilidad mínima que necesitan los inversores y prestamistas de la empresa para aceptar su riesgo. Se usa para descontar el futuro.",  # noqa: E501
        "tip": "Rentabilidad mínima que exigen quienes financian la empresa. Más riesgo, más exigencia, menor valor.",  # noqa: E501
    },
    "rf": {
        "term": "Tasa libre de riesgo",
        "simple": "Lo que rinde una inversión casi sin riesgo, normalmente el bono del Tesoro de EE. UU. a 10 años.",  # noqa: E501
        "tip": "Rendimiento de una inversión casi sin riesgo (bono del Tesoro a 10 años). Es el punto de partida del cálculo.",  # noqa: E501
    },
    "beta": {
        "term": "Beta",
        "simple": "Mide cuánto se mueve una acción respecto al mercado. Mayor que 1: se mueve más que el mercado. Menor que 1: menos.",  # noqa: E501
        "tip": "Cuánto se mueve la acción respecto al mercado. Más de 1: más volátil. Menos de 1: más estable.",  # noqa: E501
    },
    "erp": {
        "term": "Prima de riesgo del mercado",
        "simple": "El extra de rentabilidad que se pide por invertir en bolsa en lugar de en un bono sin riesgo.",  # noqa: E501
        "tip": "Rentabilidad extra que se exige por invertir en bolsa en vez de en un bono sin riesgo.",  # noqa: E501
    },
    "kd": {
        "term": "Coste de la deuda",
        "simple": "El interés medio que paga la empresa por el dinero que debe.",
        "tip": "El interés medio que paga la empresa por el dinero que debe.",
    },
    "ev": {
        "term": "Valor de empresa (EV)",
        "simple": "Lo que vale toda la empresa, incluyendo lo que debe, antes de restar la deuda.",
        "tip": "Lo que vale toda la empresa, incluyendo deuda, antes de restar lo que debe.",
    },
    "tv": {
        "term": "Valor terminal",
        "simple": "El valor de la empresa más allá del horizonte de proyección, asumiendo que crece a un ritmo constante para siempre.",  # noqa: E501
        "tip": "El valor de la empresa más allá de los años proyectados, asumiendo crecimiento constante.",  # noqa: E501
    },
    "piotroski": {
        "term": "Piotroski F-Score",
        "simple": "Puntuación de 0 a 9 que mide la salud financiera de la empresa. 8-9: sólida. 0-2: débil.",  # noqa: E501
        "tip": "Puntuación de salud financiera (0-9). 8-9: sólida. 0-2: débil.",
    },
    "altman": {
        "term": "Altman Z-Score",
        "simple": "Estima el riesgo de quiebra. Por encima de 2,99: zona segura. Por debajo de 1,81: zona de peligro.",  # noqa: E501
        "tip": "Estima el riesgo de quiebra. >2,99: segura. <1,81: peligro.",
    },
    "beneish": {
        "term": "Beneish M-Score",
        "simple": "Detecta posibles manipulaciones contables. Un valor alto es una señal de alerta, no una acusación.",  # noqa: E501
        "tip": "Detecta posibles manipulaciones contables. Un valor alto es una alerta, no una acusación.",  # noqa: E501
    },
    "roic": {
        "term": "Rentabilidad del capital invertido (ROIC)",
        "simple": "Cuánto beneficio genera la empresa por cada euro invertido en el negocio.",
        "tip": "Beneficio por cada euro invertido en el negocio.",
    },
    "roe": {
        "term": "Rentabilidad sobre fondos propios (ROE)",
        "simple": "Cuánto beneficio genera la empresa respecto al dinero de los accionistas.",
        "tip": "Beneficio respecto al dinero de los accionistas.",
    },
    "dso": {
        "term": "Días de cobro (DSO)",
        "simple": "Cuántos días tarda la empresa en cobrar a sus clientes.",
        "tip": "Días que tarda la empresa en cobrar a sus clientes.",
    },
    "ccc": {
        "term": "Ciclo de conversión de caja",
        "simple": "Días que tarda la empresa en convertir sus inversiones en caja.",
        "tip": "Días que tarda la empresa en convertir inversiones en caja.",
    },
    "upside": {
        "term": "Potencial de revalorización",
        "simple": "Diferencia entre tu estimación de valor y el precio de hoy, en porcentaje.",
        "tip": "Diferencia entre tu estimación y el precio de hoy, en porcentaje.",
    },
    "g": {
        "term": "Crecimiento a largo plazo",
        "simple": "El ritmo al que se espera que crezca la empresa para siempre, después de los años proyectados.",  # noqa: E501
        "tip": "Ritmo de crecimiento esperado para siempre, después de los años proyectados.",
    },
    "nopat": {
        "term": "Beneficio operativo después de impuestos (NOPAT)",
        "simple": "Lo que ganaría la empresa si no tuviera deuda, después de impuestos.",
        "tip": "Beneficio operativo después de impuestos, como si no hubiera deuda.",
    },
    "capex": {
        "term": "Inversiones (CapEx)",
        "simple": "Dinero que la empresa gasta en comprar o mejorar activos (fábricas, equipos, etc.).",  # noqa: E501
        "tip": "Dinero gastado en comprar o mejorar activos (fábricas, equipos).",
    },
    "nwc": {
        "term": "Capital circulante (NWC)",
        "simple": "Dinero que la empresa tiene comprometido en su operación diaria (stock, facturas por cobrar, menos facturas por pagar).",  # noqa: E501
        "tip": "Dinero comprometido en la operación diaria (stock + facturas por cobrar - por pagar).",  # noqa: E501
    },
}


def get_tip(key: str) -> str:
    """Devuelve el tooltip de un término."""
    return GLOSSARY.get(key, {}).get("tip", "")


def get_simple(key: str) -> str:
    """Devuelve la explicación simple de un término."""
    return GLOSSARY.get(key, {}).get("simple", "")


def get_term(key: str) -> str:
    """Devuelve el nombre visible de un término."""
    return GLOSSARY.get(key, {}).get("term", key)


# Autotest
if __name__ == "__main__":
    for key, entry in GLOSSARY.items():
        assert "term" in entry
        assert "simple" in entry
        assert "tip" in entry
        assert len(entry["tip"]) <= 140, f"Tip too long for {key}: {len(entry['tip'])}"
    print(f"Autotest OK: {len(GLOSSARY)} términos, todos con tip <= 140 chars")
