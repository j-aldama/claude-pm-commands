# /e2e-gen — Genera tests automaticos backend + frontend (Playwright) + contrato OpenAPI

Genera tests automaticos para una feature completa —o para varios modulos a la
vez, preguntando antes si generarlos separados o mezclados (Paso 2.5)—,
cubriendo backend (API con
pytest + httpx), frontend (Playwright) y contrato de API (Schemathesis) **en
paralelo, no como alternativas**: si el backend es una API, los tests de
contrato OpenAPI se generan SIEMPRE que el schema exista o se pueda exponer,
ademas de (no en vez de) los tests de Playwright para los flujos de UI.
Auto-detecta el stack del proyecto, mockea servicios externos, cuida
fixtures/aislamiento de DB y aplica un filtro coverage-guided (cada test debe
pasar y añadir cobertura real). Sigue las convenciones existentes.

**Datos de prueba: factories primero, nunca datos hardcodeados por defecto.**
Los payloads y fixtures se generan con factories (`factory_boy`/`pytest-factoryboy`
en Python, `fishery`/`rosie` + `@faker-js/faker` en Node) o, para contrato de
API, directamente desde el schema OpenAPI via Schemathesis/Hypothesis. Datos
literales fijos (`"C-001"`, `"test@test.com"`) solo se usan como ultimo
recurso, con permiso explicito del usuario y marcados en el reporte final —
ver Paso 4.5.

## Argumentos

- `$ARGUMENTS` — Requerido: nombre de la feature/flow a testear, o una lista de
  modulos separados por coma, opcionalmente con flags.
  Ejemplos:
  - `/e2e-gen "login y registro"`
  - `/e2e-gen "dashboard alertas" --backend-only`
  - `/e2e-gen "checkout flow" --frontend-only`
  - `/e2e-gen "facturacion, pagos, auth" --separado`
  - `/e2e-gen "captura de pacientes"`

### Flags
- `--backend-only` — solo genera tests pytest para API
- `--frontend-only` — solo genera tests Playwright para UI
- `--no-run` — genera los tests pero no los ejecuta
- `--lang python|ts` — fuerza el lenguaje de los tests Playwright
  (default: auto-detectar segun el proyecto)
- `--separado` — alcance multi-modulo: genera un juego de archivos **por modulo**
  (salta la pregunta del Paso 2.5)
- `--mezclado` — alcance multi-modulo: genera **un solo juego** de archivos que
  cubre todos los modulos juntos (salta la pregunta del Paso 2.5)

## Instrucciones

Eres un test engineer senior. Tu trabajo es generar tests automaticos
exhaustivos para una feature, cubriendo backend y frontend. Sigue las
convenciones del proyecto y prioriza error paths sobre happy paths.

---

### Paso 0: Validar argumentos

**ANTES DE EMPEZAR**, verifica que `$ARGUMENTS` contenga el nombre de una
feature o una lista explicita de modulos. Si esta vacio o solo contiene flags
(`--backend-only`, `--frontend-only`, `--no-run`, `--lang`, `--separado`,
`--mezclado`), DEBES preguntar al usuario antes de hacer cualquier otra cosa.

**NO inferir** la feature del proyecto.
**NO generar tests para todo el proyecto** cuando el alcance es difuso ("todo",
"el sistema completo"). Una **lista explicita de modulos** (`"facturacion,
pagos, auth"`) SI es un alcance valido — se resuelve con el Paso 2.5.
**NO leer codigo todavia** — solo despues de que el usuario indique la feature.

#### Que hacer si `$ARGUMENTS` esta vacio:

1. Listar al usuario las features detectables del proyecto para ayudarlo a
   elegir. Hacer estos checks rapidos (solo lectura, no analisis profundo):

   - Si existe `prd.json` o `docs/prd.md` → leer y mostrar los user stories /
     features definidos:
     ```
     Features definidas en el PRD:
       1. Autenticacion (login, registro, recuperar password)
       2. Dashboard de alertas
       3. Captura de pacientes
       4. Reportes mensuales
     ```

   - Si NO hay PRD → scanear modulos del proyecto y agruparlos:
     ```
     Modulos detectados en el proyecto:

     Backend (app/api/v1/):
       - auth.py        (login, register, refresh)
       - alerts.py      (CRUD alertas)
       - patients.py    (gestion pacientes)
       - reports.py     (reportes)

     Frontend (src/pages/):
       - dashboard
       - alerts
       - patients
     ```

2. Preguntar al usuario:
   ```
   ¿Para cual feature generar los tests?

   Ejemplos:
     /e2e-gen "login y registro"
     /e2e-gen "dashboard alertas"
     /e2e-gen "alertas" --backend-only

   Tambien puedes describir la feature en tus propias palabras.
   ```

3. **ESPERAR** la respuesta del usuario antes de continuar al Paso 1.

4. Una vez que el usuario responde, validar que la respuesta tenga sentido.
   - Ambigua tipo "todo" o "el sistema completo" → preguntar de nuevo con mas
     especificidad (pedir que enumere los modulos que le importan).
   - Una lista concreta ("facturacion, pagos y auth") → **es valida**, se acepta
     y el modo de generacion se resuelve en el Paso 2.5.

#### Que hacer si `$ARGUMENTS` contiene el nombre de feature:

Continuar directamente al Paso 1.

---

### Paso 1: Detectar stack del proyecto

1. **Detectar backend**:
   - `pyproject.toml` con `fastapi`/`django`/`flask` en dependencias → Python
   - `package.json` con `express`/`hono`/`fastify` o rutas Next API → Node
   - Si no hay backend → marcar como `frontend-only`

2. **Detectar frontend**:
   - `playwright.config.{ts,js,mjs}` → Playwright ya configurado
   - `package.json` con `next`/`astro`/`vite`/`react`/`vue` → Frontend Node
   - `index.html` o templates HTML/Jinja → Frontend Python (FastAPI templates)
   - Si no hay frontend → marcar como `backend-only`

3. **Detectar tests existentes**:
   - `tests/`, `tests/e2e/`, `e2e/`, `__tests__/`
   - `conftest.py`, `playwright.config.*`
   - Lee 1-2 archivos de test existentes para aprender las convenciones

4. **Detectar generadores de datos disponibles** (determina si el Paso 4.5
   puede evitar datos hardcodeados sin pedir instalar nada nuevo):
   - Python: `factory_boy` / `pytest-factoryboy` en `pyproject.toml` o
     `requirements*.txt`; clases `*Factory(factory.Factory)` ya existentes en
     `tests/` o `*/factories.py`.
   - Node/TS: `fishery`, `rosie` o `@faker-js/faker` en `package.json`.
   - `Faker`/`faker` suelto (sin factory) tambien cuenta — sirve para generar
     valores no hardcodeados dentro de una fixture simple.

5. **Detectar si el backend expone (o puede exponer) OpenAPI**:
   - FastAPI: siempre expone `/openapi.json` de forma nativa.
   - Django REST Framework: `drf-spectacular` o `drf-yasg` en dependencias →
     `/api/schema/`. Si DRF esta pero **sin** ninguno de los dos, anotarlo para
     ofrecer instalarlo en el Paso 5 (no asumir que no se puede).
   - Node (`express`/`fastify`/`hono`): buscar `swagger-jsdoc`,
     `@fastify/swagger`, o un archivo `openapi.yaml`/`openapi.json` estatico.

6. **Reportar al usuario** lo detectado y pedir confirmacion antes de continuar:

   ```
   Stack detectado:
     Backend:  FastAPI (Python 3.12) — OpenAPI en /openapi.json
     Frontend: HTML + Tailwind (sin Playwright configurado)
     Tests:    pytest (35 archivos en tests/)
     Datos:    sin factory_boy instalado (voy a proponer instalarlo)

   Voy a generar:
     - tests/test_<feature>_api.py       (pytest + httpx, con factories)
     - tests/test_<feature>_contract.py  (Schemathesis, desde /openapi.json)
     - tests/e2e/test_<feature>_ui.py    (Playwright Python)
     - playwright.config.* (no existe)

   Continuar? (y/N)
   ```

---

### Paso 2: Identificar archivos relevantes a la feature

1. Toma el nombre de la feature de `$ARGUMENTS`
2. Extrae keywords relevantes (ej: "dashboard alertas" → `dashboard`, `alertas`, `alert`)
3. Usa Grep para buscar en `app/`, `src/`, `routes/`, `templates/`, `pages/`:
   - Endpoints relacionados (`@router.get`, `@app.post`, `path="/alerts"`)
   - Componentes/templates relacionados (`alerts.html`, `dashboard.tsx`)
   - Servicios relacionados (`alert_service.py`, `useAlerts.ts`)

4. Lista al usuario los archivos encontrados:

   ```
   Archivos relevantes para "dashboard alertas":

   Backend:
     - app/api/v1/alerts.py (5 endpoints)
       * GET    /api/v1/alerts
       * POST   /api/v1/alerts
       * GET    /api/v1/alerts/{id}
       * PATCH  /api/v1/alerts/{id}
       * DELETE /api/v1/alerts/{id}
     - app/services/alert_service.py
     - app/models/alert.py

   Frontend:
     - templates/alerts/dashboard.html
     - static/js/alerts.js

   Confirmar scope? (y/N/edit)
   ```

5. Si el usuario dice `edit`, preguntar que archivos incluir/excluir.

6. **Si los archivos caen en dos o mas areas funcionales distintas**, agruparlos
   por modulo en la lista (no solo por capa backend/frontend):

   ```
   Archivos relevantes para "facturacion, pagos, auth":

   Modulo: facturacion
     Backend:  app/api/v1/invoices.py (4 endpoints), app/services/invoice_service.py
     Frontend: templates/invoices/list.html

   Modulo: pagos
     Backend:  app/api/v1/payments.py (3 endpoints), app/services/stripe_client.py
     Frontend: templates/payments/checkout.html

   Modulo: auth
     Backend:  app/api/v1/auth.py (5 endpoints)
     Frontend: templates/auth/login.html
   ```

---

### Paso 2.5: Modo de generacion (solo si el alcance abarca mas de un modulo)

**Cuando se activa este paso.** Solo si el Paso 2 identifico archivos de **dos o
mas modulos / areas funcionales distintas**. Si todo el alcance cae en un solo
modulo, saltar directo al Paso 3 sin preguntar nada.

Un "modulo" aca es un area funcional con su propio router/servicio/pantallas
(`invoices`, `payments`, `auth`), no una capa (backend/frontend) ni un archivo
suelto. Un flujo que cruza modulos pero es **un solo recorrido de usuario**
(ej: "checkout" que toca `cart`, `payments` y `orders`) NO cuenta como
multi-modulo: es una feature sola y va mezclada por naturaleza.

**Si se paso `--separado` o `--mezclado`**, usar ese modo y solo informarlo en
una linea — no preguntar.

**Si no se paso ninguno de los dos**, DEBES preguntar y **esperar la respuesta**
antes de continuar al Paso 3:

```
El alcance abarca 3 modulos: facturacion, pagos, auth.

¿Como genero los tests?

  [1] Separado (recomendado) — un juego de archivos por modulo:
        tests/test_facturacion_api.py      + e2e/facturacion.spec.ts
        tests/test_pagos_api.py            + e2e/pagos.spec.ts
        tests/test_auth_api.py             + e2e/auth.spec.ts
      Cada modulo corre, falla y se mide por separado. Mas archivos,
      pero puedes correr solo el modulo que tocaste.

  [2] Mezclado — un solo juego de archivos para los 3:
        tests/test_facturacion_pagos_auth_api.py
        e2e/facturacion-pagos-auth.spec.ts
      Util cuando los 3 son en realidad un mismo flujo de punta a punta.
      Un fallo en un modulo tira el archivo completo.

¿Separado o mezclado? (1/2)
```

**Como cambia cada modo el resto del comando:**

| Paso | `--separado` | `--mezclado` |
|---|---|---|
| Paso 3 (cobertura) | Una tabla de scenarios **por modulo**, con subtotal por modulo y total general | Una sola tabla para todo el alcance |
| Paso 4.5 (fixtures) | Factories agrupadas por modulo en `tests/factories.py`; fixtures compartidas se crean **una sola vez** y se reusan entre modulos | Un solo bloque de factories |
| Paso 5 (generacion) | `tests/test_<modulo>_api.py`, `tests/test_<modulo>_contract.py`, `e2e/<modulo>.spec.ts` por cada modulo | `tests/test_<slug>_api.py`, `tests/test_<slug>_contract.py`, `e2e/<slug>.spec.ts` con `<slug>` derivado del alcance completo |
| Paso 6 (ejecucion) | Correr y medir cobertura **modulo por modulo** (`--cov=<paquete_del_modulo>`); un modulo rojo no bloquea reportar los verdes | Una sola corrida sobre todo el alcance |
| Paso 7 (reporte) | Tabla con una fila por modulo + estado individual | Un bloque unico |

**Default si el usuario no contesta claro o dice "da igual": `separado`.** Es el
modo reversible — juntar archivos despues es trivial, separar un archivo
monolitico ya escrito no lo es.

**Regla anti-explosion (aplica en ambos modos).** Si el alcance supera **6
modulos**, no generarlos todos de un tiro: avisar al usuario, proponer los que
tengan mayor riesgo (dinero, datos personales, permisos, borrados
irreversibles) y dejar el resto anotado como `cobertura_pendiente` en el
reporte del Paso 7, con modulo y motivo. **Nunca recortar en silencio.**

```
Son 9 modulos — es demasiado para una sola corrida.

Propongo arrancar con los 4 de mayor riesgo:
  pagos, auth, facturacion, usuarios

Los otros 5 (reportes, notificaciones, catalogo, ajustes, dashboard) quedan
anotados como cobertura pendiente y los corres con otra invocacion.

¿Le seguimos asi? (y/N/editar lista)
```

**Aislamiento entre modulos (solo `--separado`).** Los archivos de un modulo no
deben importar fixtures definidas dentro del archivo de otro modulo. Lo
compartido (`client`, `auth_headers`, `db_session`) vive en `conftest.py` /
`e2e/fixtures.ts`; lo especifico de un modulo vive con su modulo. Si dos modulos
necesitan la misma factory, va a `tests/factories.py`, no duplicada.

---

### Paso 3: Planear cobertura

Para cada endpoint del backend, planear:

| Tipo | Que cubrir |
|------|-----------|
| **Happy path** | 1-2 tests (request valido, response esperado) |
| **Validacion** | Inputs invalidos (campos requeridos, tipos, rangos) |
| **Auth/permisos** | Sin token, token invalido, rol incorrecto |
| **Errores** | 404 (recurso no existe), 409 (conflict), 500 |
| **Edge cases** | Valores boundary (0, MAX, empty list, null) |

Para cada flujo del frontend, planear:

| Tipo | Que cubrir |
|------|-----------|
| **Happy path** | Flujo principal end-to-end |
| **Validacion UI** | Forms con datos invalidos, mensajes de error visibles |
| **Estados de error** | Network error, 500, timeout, retry |
| **Responsive** | Desktop + mobile (Playwright `devices['iPhone 12']`) |
| **Accessibility** | Navegacion por teclado, roles ARIA, contraste |

Si el backend es una API (ver detección de OpenAPI en el Paso 1), sumar la capa de contrato:

| Tipo | Que cubrir |
|------|-----------|
| **Contrato OpenAPI** | Property-based por endpoint via Schemathesis (status + schema de respuesta); corre en paralelo a los tests manuales de arriba, no los reemplaza |

Lista los scenarios al usuario:

```
Cobertura planeada:

Backend (12 tests):
  Happy paths       (2)
  Validacion        (3)
  Auth/permisos     (3)
  Errores           (2)
  Edge cases        (2)

Contrato OpenAPI (Schemathesis):
  1 test parametrizado por operación del schema (~6 operaciones → ~6 casos base,
  cientos de ejemplos generados por Hypothesis por dentro)

Frontend (8 tests):
  Happy path        (1)
  Validacion UI     (2)
  Estados de error  (2)
  Responsive        (2)
  Accessibility     (1)

Total: 20 tests + contrato OpenAPI

Continuar? (y/N)
```

**Si el modo es `--separado`**, repetir el desglose por modulo y cerrar con el
total general, para que se vea que ningun modulo quedo sin planear:

```
Cobertura planeada (modo separado, 3 modulos):

  facturacion   backend 12 · contrato 6 ops · frontend 8   → 20 tests
  pagos         backend  9 · contrato 4 ops · frontend 5   → 14 tests
  auth          backend 11 · contrato 5 ops · frontend 6   → 17 tests

Total: 51 tests + contrato OpenAPI (15 operaciones)

Continuar? (y/N/quitar <modulo>)
```

---

### Paso 4: Setup de Playwright (si no existe)

Si el frontend lo requiere y no hay `playwright.config.*`:

1. **Avisar al usuario** y pedir confirmacion (descarga ~300MB de browsers):

   ```
   Playwright no esta configurado.

   Necesito ejecutar:
     npm install --save-dev @playwright/test
     npx playwright install chromium

   Esto descarga ~300MB. Continuar? (y/N)
   ```

2. Si confirma, ejecutar los comandos.

3. **Detectar el comando de arranque y el puerto reales** (NO hardcodear
   `just serve` ni `:8000`). Buscar en este orden y usar el primero que aplique:

   | Señal en el proyecto | `command` | `port` típico |
   |----------------------|-----------|---------------|
   | `justfile` con receta `serve`/`dev`/`run` | `just <receta>` | leer del justfile |
   | `package.json` script `dev`/`start` | `npm run dev` (o pnpm/yarn/bun según lockfile) | Next 3000, Vite 5173, Astro 4321 |
   | FastAPI (`uvicorn`/`fastapi` en deps) | `uvicorn <app>:app --port <p>` | 8000 |
   | Django (`manage.py`) | `python manage.py runserver <p>` | 8000 |
   | `docker-compose.yml` con servicio web | `docker compose up <svc>` | leer del `ports:` |

   Si no se puede determinar con confianza, **preguntar al usuario** el comando
   y el puerto exactos. NUNCA asumir `just serve`.

4. Crear `playwright.config.{ts,js}` con los valores detectados (abajo un
   ejemplo con placeholders `<START_CMD>` / `<PORT>` que debés sustituir):

   ```ts
   import { defineConfig, devices } from '@playwright/test';

   const PORT = process.env.PORT || '<PORT>';
   const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

   export default defineConfig({
     testDir: './e2e',
     fullyParallel: true,
     reporter: 'list',
     use: {
       baseURL: BASE_URL,
       trace: 'on-first-retry',
     },
     projects: [
       {
         name: 'chromium',
         use: { ...devices['Desktop Chrome'] },
       },
       {
         name: 'mobile',
         use: { ...devices['iPhone 12'] },
       },
     ],
     webServer: {
       command: '<START_CMD>',
       url: BASE_URL,
       reuseExistingServer: !process.env.CI,
       timeout: 60_000,
     },
   });
   ```

5. Para projects Python con Playwright Python:
   - Verificar `playwright` en `pyproject.toml`
   - Si no esta: avisar al usuario para agregarlo manualmente

---

### Paso 4.5: Fixtures de datos y mocking de servicios externos

Antes de generar los tests, resolver **de dónde salen los datos** y **cómo se
aislan los servicios externos**. Muchos tests fallan de forma intermitente por
no cuidar esto.

#### Fixtures / seeds de datos — factories primero, SIEMPRE

**Regla dura: nunca elegir datos hardcodeados como primera opción.** El orden
de preferencia es fijo y no se salta un escalón sin haberlo intentado:

1. **Reusar primero**: revisar `conftest.py` (Python), `*/factories.py` o
   `e2e/fixtures.ts` (Playwright TS) por fixtures/factories ya existentes
   (`client`, `auth_headers`, `db_session`, `test_user`, `AlertFactory`, etc.).
   Si existen, USARLAS — no crear nuevas.

2. **Si faltan factories y el Paso 1 detectó que el proyecto ya las tiene
   instaladas** (`factory_boy`/`pytest-factoryboy` en Python;
   `fishery`/`rosie`+`@faker-js/faker` en Node): generar las factories que
   falten siguiendo el patrón de las existentes (o el `Model`/schema si es la
   primera). Cada campo no-boundary se llena con `factory.Faker(...)` /
   `faker.<tipo>()` — nunca un literal fijo salvo que el campo sea un
   `choices`/enum, donde sí corresponde un valor concreto de esa lista.

3. **Si el proyecto NO tiene factories instaladas**: antes de caer a datos
   hardcodeados, **preguntar al usuario** si instalarlas ahora:
   ```
   El proyecto no tiene factory_boy/pytest-factoryboy instalado.

   Puedo instalarlo y generar factories para <Model1>, <Model2> en
   tests/factories.py, en vez de escribir los tests con datos fijos.

     pip install factory_boy pytest-factoryboy

   ¿Instalo e integro factories? (y/N — si no, sigo con datos concretos
   documentados como deuda técnica)
   ```
   (Node: `npm install -D fishery @faker-js/faker`.)
   - Si el usuario acepta: instalar, crear `tests/factories.py` (o
     `e2e/factories.ts`) con una factory por modelo relevante a la feature, y
     usarlas en todos los tests generados.
   - Si el usuario rechaza o no se puede instalar (repo sin acceso a escribir
     dependencias, CI restringido, etc.): recién ahí usar fixtures simples con
     datos concretos — pero **generados con `Faker`/`faker` cuando sea posible**
     (nombres, emails, IDs sintéticos) en vez de strings mágicos fijos, y
     **marcarlo explícitamente** en el reporte del Paso 7 como deuda técnica
     pendiente ("tests con datos hardcodeados — factory_boy no instalado").

4. **Aislamiento de DB**: preferir transacción por test con rollback, o una DB
   de test dedicada. NUNCA correr tests contra la DB de desarrollo/producción.

5. Si un test necesita estado previo (ej: "editar una alerta existente"), la
   fixture/factory debe **crear ese estado**, no asumir que ya está en la DB.

#### Mocking de servicios externos

Identificar en los archivos de la feature toda llamada a terceros: APIs HTTP
externas, envío de emails/SMS, webhooks salientes, colas, storage (S3), pagos,
LLMs. Para cada una:

| Capa | Cómo mockear |
|------|--------------|
| **Backend HTTP saliente** | `respx` (con httpx) o `responses`; interceptar la URL externa y devolver un fixture de respuesta |
| **Email/SMS/notificaciones** | mockear el cliente/servicio (`monkeypatch`, `unittest.mock.patch`) y **assert que se llamó** con los args correctos |
| **Frontend → API propia** | `page.route('**/api/...', route => route.fulfill({...}))` en Playwright para simular respuestas y estados de error |
| **Webhooks entrantes** | postear un payload de ejemplo al endpoint receptor; no depender del emisor real |

Regla: los tests **nunca** deben pegarle a un servicio externo real. Si un
escenario exige el servicio real (smoke de integración), marcarlo con
`@pytest.mark.integration` / `test.describe.skip` y avisar al usuario que ese
queda para prueba manual (encaja con `/acceptance-checklist`).

Reportar al usuario qué fixtures se van a crear y qué servicios se van a mockear
antes de generar.

---

### Paso 5: Generar los tests

Sigue las convenciones del proyecto detectadas en el Paso 1.

**Naming segun el modo del Paso 2.5.** En los ejemplos de abajo, `<feature>` es:
- modo **mezclado** (o alcance de un solo modulo) → el slug del alcance completo
  (`alerts`, `facturacion-pagos-auth`)
- modo **separado** → el nombre del modulo, y **se repite el bloque completo por
  cada modulo** (`test_facturacion_api.py`, `test_pagos_api.py`, ...)

En modo separado, generar los modulos **de uno en uno y en orden de riesgo**
(mayor riesgo primero), no todos a la vez: si algo se rompe a la mitad, lo ya
generado queda completo y utilizable.

#### Backend (Python + FastAPI + pytest)

Archivo: `tests/test_<feature>_api.py`

Payloads construidos desde una factory (`tests/factories.py`), nunca dicts
literales sueltos en el test — así cada test queda desacoplado de valores
mágicos y sirve como fixture reusable para el resto del suite:

```python
# tests/factories.py
import factory

from app.models.alert import Alert


class AlertFactory(factory.Factory):
    class Meta:
        model = Alert

    type = "milking_anomaly"          # enum/choices → valor concreto de la lista
    cow_id = factory.Sequence(lambda n: f"C-{n:03d}")
    severity = factory.Faker("random_element", elements=["low", "medium", "high"])
```

```python
"""Tests para los endpoints de <feature>."""

import pytest
from httpx import AsyncClient

from tests.factories import AlertFactory


@pytest.mark.asyncio
class TestAlertsAPI:
    """Tests para /api/v1/alerts."""

    # ─── Happy paths ────────────────────────────────────────────

    async def test_list_alerts_returns_paginated_results(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/alerts", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_create_alert_with_valid_data_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = factory.build(dict, FACTORY_CLASS=AlertFactory)
        response = await client.post(
            "/api/v1/alerts", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        assert response.json()["cow_id"] == payload["cow_id"]

    # ─── Validacion ─────────────────────────────────────────────

    async def test_create_alert_without_required_fields_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.post(
            "/api/v1/alerts", json={}, headers=auth_headers
        )
        assert response.status_code == 422

    # ─── Auth ───────────────────────────────────────────────────

    async def test_list_alerts_without_auth_returns_401(
        self, client: AsyncClient
    ):
        response = await client.get("/api/v1/alerts")
        assert response.status_code == 401

    # ─── Errores ────────────────────────────────────────────────

    async def test_get_alert_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        response = await client.get("/api/v1/alerts/999", headers=auth_headers)
        assert response.status_code == 404
```

#### Frontend (Playwright TypeScript)

Archivo: `e2e/<feature>.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Dashboard Alertas', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/alerts');
  });

  // ─── Happy path ───────────────────────────────────────────

  test('muestra la lista de alertas activas', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Alertas' })).toBeVisible();
    await expect(page.getByTestId('alert-list')).toBeVisible();
  });

  // ─── Validacion UI ────────────────────────────────────────

  test('marca alerta como leida actualiza el contador', async ({ page }) => {
    const initialCount = await page.getByTestId('unread-count').textContent();
    await page.getByRole('button', { name: 'Marcar leida' }).first().click();

    await expect(page.getByTestId('unread-count')).not.toHaveText(initialCount!);
  });

  test('formulario rechaza alerta sin tipo', async ({ page }) => {
    await page.getByRole('button', { name: 'Nueva alerta' }).click();
    await page.getByRole('button', { name: 'Crear' }).click();

    await expect(page.getByText('Tipo es requerido')).toBeVisible();
  });

  // ─── Errores ──────────────────────────────────────────────

  test('muestra mensaje de error si la API falla', async ({ page }) => {
    await page.route('**/api/v1/alerts', route => route.abort());
    await page.reload();

    await expect(page.getByText(/error al cargar/i)).toBeVisible();
  });

  // ─── Responsive ───────────────────────────────────────────

  test('navegacion mobile abre menu hamburguesa', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'Solo aplica a mobile');
    await page.getByLabel('Abrir menu').click();
    await expect(page.getByRole('navigation')).toBeVisible();
  });
});
```

#### Frontend (Playwright Python — alternativa)

Archivo: `tests/e2e/test_<feature>_ui.py`

```python
"""E2E tests para dashboard de alertas."""

import pytest
from playwright.async_api import Page, expect


@pytest.mark.asyncio
class TestAlertsDashboard:
    async def test_muestra_lista_alertas(self, page: Page):
        await page.goto("/dashboard/alerts")
        await expect(page.get_by_role("heading", name="Alertas")).to_be_visible()

    async def test_form_rechaza_alerta_sin_tipo(self, page: Page):
        await page.goto("/dashboard/alerts")
        await page.get_by_role("button", name="Nueva alerta").click()
        await page.get_by_role("button", name="Crear").click()
        await expect(page.get_by_text("Tipo es requerido")).to_be_visible()
```

#### Backend con OpenAPI — tests de contrato con Schemathesis (OBLIGATORIO si es API, en paralelo a Playwright)

Si la feature tiene backend tipo API (no solo templates server-rendered),
generar SIEMPRE este archivo además de los tests pytest+httpx y de los
Playwright — no es una alternativa a Playwright ni un "extra" descartable, son
capas distintas: Schemathesis valida el **contrato** de la API a partir del
schema (property-based, cientos de casos por endpoint), Playwright valida los
**flujos de UI** que consumen esa API. Un test de contrato roto y un E2E verde
al mismo tiempo es información real (la UI no está ejercitando el caso que
rompió el contrato).

1. **Si el backend ya expone OpenAPI** (FastAPI nativo, o DRF con
   `drf-spectacular`/`drf-yasg`, detectado en el Paso 1): generar el test de
   contrato directo, sin preguntar.

2. **Si es Django REST Framework pero SIN `drf-spectacular`/`drf-yasg`**: no
   saltar el bloque en silencio. Preguntar al usuario si instalar y cablear
   `drf-spectacular` para exponer el schema:
   ```
   El backend es DRF pero no expone OpenAPI todavia.

   Puedo instalar drf-spectacular y agregar la ruta /api/schema/ para poder
   generar tests de contrato con Schemathesis (además de los de Playwright).

     pip install drf-spectacular
     # + agregar a INSTALLED_APPS, DEFAULT_SCHEMA_CLASS y la URL /api/schema/

   ¿Lo instalo y expongo el schema? (y/N — si no, sigo solo con pytest+httpx
   y Playwright, y lo dejo anotado como cobertura pendiente)
   ```

3. **Si es otro framework sin soporte claro de OpenAPI** (Express/Hono/Flask
   puro sin swagger): no forzar la instalación de un generador de schema
   ajeno al proyecto — anotarlo en `cobertura_pendiente` del Paso 7 y seguir
   solo con pytest+httpx/Playwright.

Con una sola función se generan cientos de casos desde el schema (usa
Hypothesis por dentro) que cazan 500s ocultos, validaciones rotas y
desviaciones spec-vs-implementación — cero mantenimiento por endpoint nuevo.

Archivo: `tests/test_<feature>_contract.py`

```python
"""Tests de contrato generados desde el schema OpenAPI (Schemathesis)."""

import schemathesis
from app.main import app   # tu instancia FastAPI

# from_asgi: corre contra la app en memoria, NUNCA contra prod (regla de seguridad)
schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()   # 1 test parametrizado por operación del schema
def test_api_contract(case):
    case.call_and_validate()   # valida status + respuesta contra el contrato
```

Notas al generar:
- Requiere `pip install schemathesis` (avisar al usuario si falta; no instalar sin permiso).
- **SIEMPRE `from_asgi`/`from_wsgi` o TestClient** — nunca apuntar a una URL de
  producción con datos reales (regla de seguridad global).
- FastAPI/pydantic emite JSON Schema Draft 7; si aparecen falsos positivos por
  versión de schema, aplicar los *fixups* de Schemathesis en vez de silenciar el test.
- Empezar por validación de status/schema; el stateful testing y la auth
  persistente son un segundo nivel opcional.
- Si Schemathesis encuentra fallos, son **bugs reales de la API** → reportarlos
  por separado, NO ajustar el schema para esconderlos.

---

### Paso 6: Ejecutar y verificar

A menos que el flag `--no-run` este presente:

1. **Backend**:
   ```bash
   pytest tests/test_<feature>_api.py -v
   ```

2. **Frontend**:
   ```bash
   # Si el lenguaje es TS:
   npx playwright test e2e/<feature>.spec.ts

   # Si el lenguaje es Python:
   pytest tests/e2e/test_<feature>_ui.py -v
   ```

3. **Si fallan**:
   - Si el test esta mal escrito → ajustar el test
   - Si el test reveló un bug en el codigo → reportar SEPARADAMENTE, NO ajustar
     el test para esconderlo
   - Si el endpoint no existe aun (TDD) → reportar al usuario que necesita
     implementarlo

4. **Todos los tests deben pasar antes de reportar done**, excepto los que
   reflejen bugs reales en el codigo.

4.1 **En modo `--separado`: correr modulo por modulo, no todo junto.** Cada
   modulo se ejecuta y se mide con su propio comando:
   ```bash
   pytest tests/test_facturacion_api.py -v --cov=app.invoices --cov-report=term-missing
   pytest tests/test_pagos_api.py       -v --cov=app.payments --cov-report=term-missing
   ```
   - Un modulo en rojo **no bloquea** reportar los que quedaron verdes: se
     reporta el estado real de cada uno en la tabla del Paso 7.
   - Si un modulo falla por un bug del codigo (no del test), se reporta como
     bug y se sigue con el siguiente modulo — NO se detiene la corrida completa.
   - Nunca declarar el conjunto como "listo" si algun modulo quedo sin correr:
     ese modulo va como `pendiente` explicito en el reporte.

5. **Filtro coverage-guided** (mantiene la señal alta, evita ruido): correr los
   tests del backend **midiendo cobertura de los archivos de la feature**:
   ```bash
   pytest tests/test_<feature>_api.py --cov=<modulo_feature> --cov-report=term-missing
   ```
   - Un test que pasa pero **no añade cobertura ni asserts significativos** sobre
     la feature (ej: duplica exactamente lo que otro ya cubre) → descartarlo o
     fusionarlo. No proponer tests redundantes solo para inflar el conteo.
   - Priorizar cubrir las **líneas/ramas que `term-missing` reporta como no
     cubiertas** sobre agregar más variantes del happy path.
   - Objetivo: cada test propuesto pasa Y ejercita código o un assert que ningún
     otro test cubría. La métrica de éxito es cobertura real + error paths, NO
     cantidad de tests. (Inspirado en el patrón coverage-guided de Qodo Cover.)

---

### Paso 7: Reportar resultados

```
Generated tests for "dashboard alertas":

Datos de prueba:
  ✓ tests/factories.py — AlertFactory (factory_boy, instalado en este run)

Backend (pytest + httpx):
  ✓ tests/test_alerts_api.py — 12 tests (payloads via AlertFactory)
    - Happy paths:    2
    - Validacion:     3
    - Auth/permisos:  3
    - Errores:        2
    - Edge cases:     2

Contrato OpenAPI (Schemathesis):
  ✓ tests/test_alerts_contract.py — desde /openapi.json, 1 test parametrizado
    por operación (6 operaciones)

Frontend (Playwright TS):
  ✓ e2e/alerts-dashboard.spec.ts — 8 tests
    - Happy paths:        1
    - Validacion UI:      2
    - Estados de error:   2
    - Responsive:         2
    - Accessibility:      1

Total: 20 tests + contrato OpenAPI, all passing.

Tiempo: 14.3s

[Si el usuario rechazó instalar factories o no había OpenAPI disponible]:
⚠️ Deuda técnica pendiente:
  - Datos hardcodeados en tests/test_alerts_api.py (factory_boy no instalado,
    usuario declinó instalarlo) — considerar `pip install factory_boy pytest-factoryboy`
  - Sin tests de contrato OpenAPI: backend Express sin generador de schema —
    considerar exponer OpenAPI si el proyecto lo justifica

[Si encontro bugs]:
⚠️ Bugs encontrados (NO arreglados — solo reportados):
  - app/api/v1/alerts.py:45 — Endpoint no valida que cow_id exista en DB
  - templates/alerts/dashboard.html:12 — Falta atributo aria-label en boton
```

**En modo `--separado`, el reporte va con una fila por modulo** para que se lea
de un vistazo que quedo verde, que quedo rojo y que no se corrio:

```
Generated tests for "facturacion, pagos, auth" (modo: separado)

| Modulo      | Backend | Contrato | Frontend | Estado          | Cobertura |
|-------------|---------|----------|----------|-----------------|-----------|
| facturacion | 12      | 6 ops    | 8        | ✓ 20/20 pass    | 87%       |
| pagos       | 9       | 4 ops    | 5        | ⚠ 13/14 (1 bug) | 79%       |
| auth        | 11      | 5 ops    | 6        | ✓ 17/17 pass    | 91%       |

Total: 51 tests · 50 pass · 1 fallo por bug real
Tiempo: 48.2s

Archivos generados:
  tests/factories.py                    (compartido — 3 factories)
  tests/test_facturacion_api.py         tests/test_facturacion_contract.py
  tests/test_pagos_api.py               tests/test_pagos_contract.py
  tests/test_auth_api.py                tests/test_auth_contract.py
  e2e/facturacion.spec.ts   e2e/pagos.spec.ts   e2e/auth.spec.ts

⚠️ Bugs encontrados (NO arreglados — solo reportados):
  - app/api/v1/payments.py:88 — devuelve 500 en vez de 409 si el pago ya existe

⚠️ Cobertura pendiente (modulos fuera de esta corrida):
  - reportes      — excede el limite de 6 modulos por corrida (riesgo medio)
  - notificaciones — excede el limite de 6 modulos por corrida (riesgo bajo)
  Corrélos con: /e2e-gen "reportes, notificaciones" --separado
```

---

## Reglas

- **SIEMPRE pedir el nombre de la feature** si `$ARGUMENTS` esta vacio — NUNCA inferir
- **NUNCA generar tests para todo el proyecto a partir de un alcance difuso**
  ("todo", "el sistema completo") — pedir que enumere los modulos. Una lista
  explicita de modulos SI es alcance valido
- **SIEMPRE preguntar separado vs mezclado (Paso 2.5)** cuando el alcance abarca
  2 o mas modulos y no se paso `--separado` ni `--mezclado` — NUNCA elegir el
  modo en silencio. Si el usuario no define, el default es `separado`
- **MAXIMO 6 modulos por corrida** — si hay mas, proponer los de mayor riesgo y
  anotar el resto en `cobertura_pendiente` con modulo y motivo; nunca recortar
  en silencio
- **En modo separado, nunca declarar "listo" con modulos sin correr** — cada
  modulo reporta su estado real (verde / rojo / pendiente) en la tabla del Paso 7
- **En modo separado, no cruzar fixtures entre archivos de modulos distintos** —
  lo compartido va a `conftest.py` / `tests/factories.py` / `e2e/fixtures.ts`
- **NUNCA sobrescribir tests existentes** sin confirmar con el usuario
- **NUNCA ejecutar `npx playwright install` automaticamente** (descarga ~300MB)
- **NUNCA esconder bugs** ajustando los tests para que pasen — reportar bugs separadamente
- **SIEMPRE seguir las convenciones del proyecto** (naming, fixtures, AAA pattern)
- **PRIORIZAR error paths** sobre happy paths (heredado de `/test-gen`)
- **DETECTAR el lenguaje correcto**: Python project → Playwright Python; Node project → Playwright TS
- **NO crear `playwright.config`** sin confirmar que el usuario lo quiere
- **NO ejecutar tests** si el usuario paso `--no-run`
- Si la feature no se puede identificar claramente, **preguntar al usuario** cuales endpoints/pages incluir
- **Reusar fixtures existentes** del proyecto (`conftest.py`, `e2e/fixtures.ts`) en lugar de crear nuevas
- **NUNCA hardcodear** el comando de arranque (`just serve`) ni el puerto (`:8000`) en `playwright.config` — detectarlos del proyecto o preguntar
- **NUNCA pegarle a servicios externos reales** en los tests — mockear (respx/responses/monkeypatch/`page.route`); los que exijan el servicio real van marcados como integración y se derivan a prueba manual
- **Fixtures con teardown**: los datos que crea un test deben limpiarse; NUNCA correr tests contra la DB de desarrollo o producción
- **Schemathesis solo vía ASGI/WSGI/TestClient** — NUNCA apuntar el contract testing a una URL de producción con datos reales
- **Coverage-guided**: cada test propuesto debe pasar Y añadir cobertura/assert real; descartar tests redundantes. La métrica es cobertura + error paths, NO cantidad de tests
- **Datos hardcodeados NUNCA son la primera opción**: factories (`factory_boy`/`pytest-factoryboy`, `fishery`/`rosie`+`@faker-js/faker`) primero; si el proyecto no las tiene, PREGUNTAR si instalarlas antes de escribir literales fijos. Si el usuario rechaza, usar `Faker` dentro de fixtures simples y dejarlo anotado como deuda técnica en el reporte — nunca en silencio
- **Si el backend es una API, generar SIEMPRE el test de contrato OpenAPI/Schemathesis además de Playwright** (no en su lugar) cuando el schema exista o se pueda exponer con permiso del usuario (ej. instalar `drf-spectacular` en DRF); si el framework no soporta OpenAPI de forma razonable, anotarlo en `cobertura_pendiente`, nunca omitirlo en silencio
