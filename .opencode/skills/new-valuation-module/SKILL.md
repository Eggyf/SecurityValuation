---
name: new-valuation-module
description: Receta paso a paso para añadir un módulo nuevo de valoración o análisis a la app (modelos Pydantic, función pura, tests, pestaña de UI, documentación y aportación al resumen), con plantilla de código y lista de comprobación final. Úsala siempre que el usuario pida añadir un método de valoración, un score, un análisis o un nuevo cálculo financiero a valuation/ o analysis/, o cuando vayas a empezar cualquier tarea de la fase 2 del roadmap de AGENTS.md.
---

# Añadir un módulo nuevo

Plantilla de código en `references/module-template.md`. Esta skill fija el **orden de trabajo**; las fórmulas viven en `dcf-methodology`, `quality-scores` y `valuation-modules-v2`.

## Antes de escribir código

1. **Plan corto y confirmación del usuario** (modo plan): qué calcula, con qué entradas, qué devuelve y dónde se ve.
2. Confirma que **la v1 está estable** (tests en verde) y que el módulo no cambia el resultado del DCF base.
3. Si necesitas datos que no están en el 10-K, decide si son input manual o vienen de `data_sources/`. Nunca los inventes.
4. Si la metodología no está en una skill ni en `docs/methodology.md`, **escríbela primero** (fórmulas y decisiones) y pídele al usuario que la valide.

## Orden de implementación

1. **Modelos de entrada y salida** en `models/` (Pydantic v2). Campos con unidad y documentados. La salida incluye siempre `warnings: list[str]` y `assumptions_used`.
2. **Función pura** en `valuation/` o `analysis/`: sin I/O, sin estado global, sin aleatoriedad (o con semilla explícita como argumento).
3. **Tests primero o a la vez** (ver `finance-testing`): caso a mano, error de dominio, frontera, propiedad y, si procede, identidad con el DCF.
4. **Validación de entradas**: lanza `ValuationError` con un mensaje accionable, no devuelvas `NaN` en silencio.
5. **Pestaña en la UI** (ver `streamlit-ui`): supuestos editables, resultado y avisos. Sin fórmulas en la UI.
6. **Integración con el resumen**: aportación al football field o a la tabla de contrastes, y posibilidad de **desactivar** el módulo.
7. **Documentación**: entrada en `docs/methodology.md` con fórmula, decisiones y limitaciones.
8. **Exportación** (si procede): hoja en el Excel con fórmulas vivas (ver `excel-live-formulas`).
9. **Revisión final** con `valuation-sanity-check` y la lista de abajo.

## Reglas de diseño

- Un módulo, un archivo (o pocos), con una API pequeña: `run(inputs: ModuleInputs) -> ModuleResult`.
- Dependencias entre módulos **solo por modelos Pydantic**, nunca por importar internals ni por estado global.
- Reutiliza `bridge.py` para pasar de EV a precio; no dupliques el puente.
- Cada parámetro con valor por defecto cita su justificación en el docstring.
- Los avisos llevan cifra y umbral.
- Si el módulo no es aplicable (por ejemplo, empresa financiera, EBIT negativo), **devuelve «no aplicable» con motivo**, no un número.

## Lista de comprobación final

- [ ] `ruff check`, `ruff format` y `mypy --strict` limpios.
- [ ] Tests nuevos en verde y suite completa en verde (`-m "not network"`).
- [ ] Caso calculado a mano documentado en un docstring de test.
- [ ] Sin datos inventados: todo valor con fuente o marcado como supuesto.
- [ ] El resultado del DCF base **no cambió** (test de regresión con el caso base).
- [ ] Pestaña de UI con supuestos editables, avisos y disclaimer.
- [ ] El módulo se puede desactivar sin romper los demás.
- [ ] `docs/methodology.md` actualizado.
- [ ] Resumen al usuario: qué cambió, qué se comprobó, qué quedó pendiente o incierto.

## Qué NO hacer

- No refactorizar código no relacionado mientras añades el módulo.
- No añadir dependencias sin justificarlo y sin preguntar al usuario.
- No hacer commits salvo que el usuario lo pida.
- No tocar fixtures ni valores esperados para que un test pase.
- No presentar el resultado como recomendación de inversión.
