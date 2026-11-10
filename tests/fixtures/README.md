# Fixtures

Aquí se guardan los artefactos de los *golden tests* (AGENTS.md §9): 10-K reales de
empresas públicas y el JSON de extracción esperado, para detectar regresiones del parser.

**Reglas:**

- Los 10-K son documentos públicos de la SEC; no deben incluir datos personales.
- El JSON esperado se revisa a mano contra el documento antes de aceptarlo como referencia.
- Nunca se modifican para «hacer pasar» un test: si una cifra esperada falla es porque el
  parser cambió de comportamiento.

Pendiente de añadir en el paso de extracción (roadmap §10.3, punto 4).
