# SecurityValuation

Valoración por **Flujos de Caja Descontados (FCFF)** a partir del **Form 10-K** de una
empresa, con supuestos explícitos, trazabilidad de cada cifra y exportación auditable.

> **Aviso:** esta herramienta es un ejercicio de modelización. No constituye asesoramiento
> financiero, de inversión ni fiscal.

## Estado

En construcción (v1, MVP). El contrato de trabajo del proyecto vive en
[`AGENTS.md`](AGENTS.md).

- [x] Andamiaje del repositorio (entorno, lint, tipado, tests)
- [ ] Modelos Pydantic (`models/`)
- [ ] Motor DCF (proyección, WACC, valor terminal, puente, sensibilidades)
- [ ] Extracción iXBRL del 10-K + normalización + validaciones
- [ ] UI Streamlit
- [ ] Exportación a Excel con fórmulas

## Requisitos

- Python 3.12+ (el intérprete está fijado en `.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Uso

```bash
uv sync                            # crear el entorno e instalar dependencias
uv run pytest -q -m "not network"  # tests (sin red)
uv run ruff check .                # lint
uv run ruff format .               # formato
uv run mypy src                    # tipado estricto
uv run streamlit run src/dcf_app/ui/app.py   # UI (cuando exista)
```

## Estructura

```
src/dcf_app/
├── models/        # Pydantic: estados financieros, supuestos, resultados
├── extraction/    # Lectura del 10-K (iXBRL → fallback de texto)
├── normalization/ # Signos, escala, no recurrentes, leases, SBC
├── assumptions/   # Valores por defecto y históricos → proyección
├── valuation/     # Motor DCF puro y determinista
├── validation/    # Integridad contable
├── export/        # Excel e informe
└── ui/            # Streamlit
```

Las decisiones metodológicas se documentan en [`docs/methodology.md`](docs/methodology.md).
