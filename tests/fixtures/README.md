# Fixtures

Artefactos de los *golden tests* de extracción (AGENTS.md §9). Si una cifra
esperada falla, es porque el parser cambió de comportamiento: entiende por qué
antes de tocar nada (AGENTS.md §10.5).

**Contenido actual:**

- `sample_ixbrl.html`: 10-K sintético con los casos difíciles del parser
  iXBRL: contexto dimensional (desglose por producto), duración trimestral,
  fact duplicado y conflicto de conceptos con valor distinto. Valores
  redondos diseñados a mano.
- `msft_statements.pdf`: recorte del 10-K FY2026 de Microsoft (documento
  público de la SEC) con la portada y las páginas de los tres estados
  financieros. Valores ancla verificados contra el documento original.
- `nvda_statements.pdf`: ídem del 10-K FY2026 de NVIDIA.

**Reglas:**

- Los 10-K (y sus recortes) son documentos públicos de la SEC; no deben
  incluir datos personales.
- Los valores esperados se revisan a mano contra el documento antes de
  aceptarlos como referencia.
- Nunca se modifican para «hacer pasar» un test.
