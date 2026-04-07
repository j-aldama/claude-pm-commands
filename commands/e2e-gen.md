# /e2e-gen — Genera tests automaticos backend + frontend (Playwright)

Genera tests automaticos para una feature completa, cubriendo backend (API con
pytest + httpx) y frontend (Playwright). Auto-detecta el stack del proyecto
y sigue las convenciones existentes.

## Argumentos

- `$ARGUMENTS` — Requerido: nombre de la feature/flow a testear, opcionalmente
  con flags.
  Ejemplos:
  - `/e2e-gen "login y registro"`
  - `/e2e-gen "dashboard alertas" --backend-only`
  - `/e2e-gen "checkout flow" --frontend-only`
  - `/e2e-gen "captura de pacientes"`

### Flags
- `--backend-only` — solo genera tests pytest para API
- `--frontend-only` — solo genera tests Playwright para UI
- `--no-run` — genera los tests pero no los ejecuta
- `--lang python|ts` — fuerza el lenguaje de los tests Playwright
  (default: auto-detectar segun el proyecto)

## Instrucciones

Eres un test engineer senior. Tu trabajo es generar tests automaticos
exhaustivos para una feature, cubriendo backend y frontend. Sigue las
convenciones del proyecto y prioriza error paths sobre happy paths.

---

### Paso 0: Validar argumentos

**ANTES DE EMPEZAR**, verifica que `$ARGUMENTS` contenga el nombre de una
feature. Si esta vacio o solo contiene flags (`--backend-only`,
`--frontend-only`, `--no-run`, `--lang`), DEBES preguntar al usuario antes
de hacer cualquier otra cosa.

**NO inferir** la feature del proyecto.
**NO generar tests para todo el proyecto**.
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

   Tambien podes describir la feature en tus propias palabras.
   ```

3. **ESPERAR** la respuesta del usuario antes de continuar al Paso 1.

4. Una vez que el usuario responde, validar que la respuesta tenga sentido
   (no sea ambigua tipo "todo" o "el sistema completo"). Si es ambigua,
   preguntar de nuevo con mas especificidad.

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

4. **Reportar al usuario** lo detectado y pedir confirmacion antes de continuar:

   ```
   Stack detectado:
     Backend:  FastAPI (Python 3.12)
     Frontend: HTML + Tailwind (sin Playwright configurado)
     Tests:    pytest (35 archivos en tests/)

   Voy a generar:
     - tests/test_<feature>_api.py    (pytest + httpx)
     - tests/e2e/test_<feature>_ui.py (Playwright Python)
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

Lista los scenarios al usuario:

```
Cobertura planeada:

Backend (12 tests):
  Happy paths       (2)
  Validacion        (3)
  Auth/permisos     (3)
  Errores           (2)
  Edge cases        (2)

Frontend (8 tests):
  Happy path        (1)
  Validacion UI     (2)
  Estados de error  (2)
  Responsive        (2)
  Accessibility     (1)

Total: 20 tests

Continuar? (y/N)
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

3. Crear `playwright.config.{ts,js}` minimo:

   ```ts
   import { defineConfig, devices } from '@playwright/test';

   export default defineConfig({
     testDir: './e2e',
     fullyParallel: true,
     reporter: 'list',
     use: {
       baseURL: process.env.BASE_URL || 'http://localhost:8000',
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
       command: 'just serve',
       url: 'http://localhost:8000',
       reuseExistingServer: !process.env.CI,
       timeout: 60_000,
     },
   });
   ```

4. Para projects Python con Playwright Python:
   - Verificar `playwright` en `pyproject.toml`
   - Si no esta: avisar al usuario para agregarlo manualmente

---

### Paso 5: Generar los tests

Sigue las convenciones del proyecto detectadas en el Paso 1.

#### Backend (Python + FastAPI + pytest)

Archivo: `tests/test_<feature>_api.py`

```python
"""Tests para los endpoints de <feature>."""

import pytest
from httpx import AsyncClient


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
        payload = {
            "type": "milking_anomaly",
            "cow_id": "C-001",
            "severity": "high",
        }
        response = await client.post(
            "/api/v1/alerts", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        assert response.json()["cow_id"] == "C-001"

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

---

### Paso 7: Reportar resultados

```
Generated tests for "dashboard alertas":

Backend (pytest + httpx):
  ✓ tests/test_alerts_api.py — 12 tests
    - Happy paths:    2
    - Validacion:     3
    - Auth/permisos:  3
    - Errores:        2
    - Edge cases:     2

Frontend (Playwright TS):
  ✓ e2e/alerts-dashboard.spec.ts — 8 tests
    - Happy paths:        1
    - Validacion UI:      2
    - Estados de error:   2
    - Responsive:         2
    - Accessibility:      1

Total: 20 tests, all passing.

Tiempo: 14.3s

[Si encontro bugs]:
⚠️ Bugs encontrados (NO arreglados — solo reportados):
  - app/api/v1/alerts.py:45 — Endpoint no valida que cow_id exista en DB
  - templates/alerts/dashboard.html:12 — Falta atributo aria-label en boton
```

---

## Reglas

- **SIEMPRE pedir el nombre de la feature** si `$ARGUMENTS` esta vacio — NUNCA inferir
- **NUNCA generar tests para todo el proyecto** — el comando es por feature, no global
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
