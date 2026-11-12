# Skills de opencode para la app de DCF

Diez skills para el proyecto descrito en `AGENTS.md`: seis de finanzas y cuatro de ingeniería.

## Instalación

Copia la carpeta `.opencode/` a la raíz de tu repositorio (junto a `AGENTS.md`):

```
tu-repo/
├── AGENTS.md
└── .opencode/
    └── skills/
        ├── dcf-methodology/
        ├── sec-10k-extraction/
        ├── edgar-api/
        ├── valuation-sanity-check/
        ├── quality-scores/
        ├── valuation-modules-v2/
        ├── new-valuation-module/
        ├── finance-testing/
        ├── excel-live-formulas/
        └── streamlit-ui/
```

Reinicia opencode. Las skills aparecen en la herramienta `skill` y el agente las carga cuando la descripción coincide con la tarea. También puedes pedirlas por nombre: «usa la skill dcf-methodology».

Rutas alternativas que opencode también lee: `~/.config/opencode/skills/` (global) y `.claude/skills/`. Comprueba la documentación vigente por si cambian.

## Qué hay en cada una

| Skill | Contenido | Verificado |
|---|---|---|
| `dcf-methodology` | Fórmulas, puente a precio, errores típicos, ejemplo resuelto | Script de referencia ejecutado; ejemplo con sus números |
| `sec-10k-extraction` | Lectura de iXBRL, selección de hechos, mapeo us-gaap, diagnóstico | Solo documentación; comprobar nombres de conceptos contra el 10-K real |
| `edgar-api` | Endpoints, reglas de la SEC, esqueleto de cliente | Funciones puras probadas; **no probado contra la red real** |
| `valuation-sanity-check` | Revisión de coherencia con umbrales y formato de salida | Solo documentación |
| `quality-scores` | Piotroski, Altman, Beneish, calidad de beneficios, DuPont | Autotests del script ejecutados |
| `valuation-modules-v2` | Reverse DCF, Monte Carlo, múltiplos, FCFE, Residual Income | Reverse DCF y Monte Carlo probados; el resto es documentación |
| `new-valuation-module` | Receta de trabajo y plantilla de módulo | Plantilla **no ejecutada** (requiere pydantic) |
| `finance-testing` | Patrones de tests, hypothesis, golden tests, tests sin red | 8 tests ejecutados; las 2 propiedades de hypothesis se validaron con muestreo aleatorio, **no con hypothesis** |
| `excel-live-formulas` | Excel con fórmulas vivas, rangos con nombre, colores | Libro generado y **recalculado con LibreOffice**: 24,64 USD/acción, sin errores |
| `streamlit-ui` | Convenciones de UI, estado, formato en español, avisos | Formato con autotests; esqueleto de app **solo comprobado sintácticamente** |

## Cosas a revisar antes de fiarte

- Los **nombres de conceptos XBRL** cambian con las taxonomías y cada empresa usa los suyos.
- Los **umbrales** (75 % de peso del TV, 25 % de divergencia, rangos de g) son valores por defecto razonables, no verdades. Ajústalos a tu criterio.
- La SEC puede cambiar rutas y límites. Verifica en su documentación antes de implementar `edgar.py`.
- La API de Streamlit cambia entre versiones: contrasta el esqueleto con la que tengas instalada.
- Nada de esto es asesoramiento financiero.

`opencode.json.example` muestra cómo controlar permisos de skills; ajústalo a tu configuración.
