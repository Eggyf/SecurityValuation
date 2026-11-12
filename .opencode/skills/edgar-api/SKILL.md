---
name: edgar-api
description: Cómo consumir las APIs públicas de SEC EDGAR (ticker a CIK, submissions, companyfacts, descarga de documentos) con la cabecera User-Agent obligatoria, límite de 10 peticiones por segundo, caché y manejo de errores. Úsala siempre que escribas o modifiques data_sources/edgar.py, descargues un 10-K o 10-Q automáticamente, uses companyfacts para histórico o TTM, o depures errores 403, 404 o 429 de sec.gov.
---

# SEC EDGAR: acceso programático

Esta skill solo aplica dentro de `data_sources/` y con el **modo online activado** (ver sección 13 de `AGENTS.md`). Fuera de ahí, no accedas a la red.

**Antes de implementar, verifica los detalles en la documentación oficial de la SEC** (página «EDGAR Application Programming Interfaces»), porque las rutas y los límites pueden cambiar. Esta skill resume lo que se conoce a la fecha de escribirla.

## Reglas de acceso

1. **User-Agent obligatorio** con nombre y email de contacto, por ejemplo `Nombre Apellido correo@dominio.com`. Léelo de la variable de entorno `SEC_USER_AGENT`. Si falta, **detente y pídelo**: sin ella la SEC bloquea la petición.
2. **Máximo 10 peticiones por segundo.** Implementa un limitador (por ejemplo, 8/s para dejar margen).
3. **Cachea en disco.** Los filings son inmutables, así que no caducan. Los listados (`submissions`) caducan en horas.
4. Reintentos con backoff exponencial ante `429` y `5xx`. Ante `403`, no reintentes: revisa el `User-Agent`.
5. Pide contenido comprimido (`Accept-Encoding: gzip`).
6. No hagas scraping de páginas HTML de búsqueda; usa solo los endpoints documentados.

## Endpoints

| Qué | URL |
|---|---|
| Ticker → CIK | `https://www.sec.gov/files/company_tickers.json` |
| Listado de filings de una empresa | `https://data.sec.gov/submissions/CIK##########.json` |
| Todos los hechos XBRL de una empresa | `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` |
| Un concepto de una empresa | `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/<Concepto>.json` |
| Un concepto en todas las empresas y un periodo | `https://data.sec.gov/api/xbrl/frames/us-gaap/<Concepto>/USD/CY2023Q4I.json` |
| Documento de un filing | `https://www.sec.gov/Archives/edgar/data/<cik_sin_ceros>/<accession_sin_guiones>/<primaryDocument>` |

- `CIK##########` es el CIK con **10 dígitos y ceros a la izquierda**.
- En la ruta de `Archives`, el CIK va **sin ceros** y el accession number **sin guiones**.

## Estructura de `submissions`

`filings.recent` contiene arrays paralelos (mismo índice = mismo filing):

`accessionNumber`, `filingDate`, `reportDate`, `form`, `primaryDocument`, `isXBRL`, `isInlineXBRL`.

También trae `sic`, `sicDescription`, `name`, `tickers` y `fiscalYearEnd`. Los filings más antiguos están en `filings.files` (archivos adicionales a descargar).

**Elegir el 10-K correcto:**

1. Filtra `form == "10-K"` (considera `10-K/A` como enmienda; no la uses salvo que el usuario lo pida o la original no tenga estados).
2. Si el usuario pide un ejercicio concreto, filtra por `reportDate`.
3. Si no, toma el más reciente por `filingDate`.
4. Confirma `isInlineXBRL == 1`; si no, el parseo iXBRL no será posible y hay que ir al fallback.

## Estructura de `companyfacts`

`facts["us-gaap"]["<Concepto>"]["units"]["USD"]` es una lista de hechos con:

`start` (solo duraciones), `end`, `val`, `accn`, `fy`, `fp`, `form`, `filed`, `frame` (opcional).

Trampas conocidas:

- **El mismo hecho aparece varias veces** (una por cada filing que lo incluye). Deduplica por `(end, start)` y elige el valor del filing más reciente (`filed`).
- `fy` y `fp` describen el filing donde se publicó el dato, **no necesariamente el periodo al que pertenece el hecho**. Identifica el periodo por `start`/`end`.
- Filtra `form in {"10-K", "10-Q"}` según lo que necesites.
- Para trimestres de flujo de caja, los 10-Q acumulan año a la fecha: el trimestre aislado se obtiene restando.
- **TTM** = último ejercicio anual + YTD actual − YTD del año anterior (mismo periodo).
- Usa `companyfacts` para validar el 10-K, no para sustituir el pipeline de extracción.

## Esqueleto del cliente

> No se ha ejecutado contra la red real. Pruébalo con `@pytest.mark.network` y un `User-Agent` válido.

Ver `scripts/edgar_client.py`.

## Tests

- **Nunca llamar a la red en tests por defecto.** Usa `httpx.MockTransport` o respuestas grabadas en `tests/fixtures/edgar/`.
- Un test para la normalización del CIK a 10 dígitos y para la construcción de la URL de `Archives`.
- Un test de elección de 10-K con un `submissions` de ejemplo que incluya un `10-K/A`.
- Un test de deduplicación de `companyfacts` con valores repetidos en varios filings.
- Un test que verifique que, sin `SEC_USER_AGENT`, el cliente lanza un error claro **antes** de hacer ninguna petición.
- Una prueba de integración marcada `network`, excluida por defecto.
