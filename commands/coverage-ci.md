# /coverage-ci — Cablea cobertura con umbrales + CI que corre tests

Configura medición de cobertura con umbrales por trinquete (ratcheting) y genera
el workflow de GitHub Actions que corre los tests en cada PR. Ataca los dos
puntos débiles más comunes: suites que existen pero (1) no miden cobertura y
(2) no corren automáticamente en CI.

## Argumentos
- `$ARGUMENTS` — Opcional: flags.
  - `--python-only` — solo configura cobertura Python (pytest-cov)
  - `--js-only` — solo configura cobertura JS/TS (Vitest/Jest)
  - `--no-ci` — configura cobertura pero NO genera el workflow de CI
  - `--threshold N` — fuerza el umbral inicial en N% (default: medir el real)

## Instrucciones

Eres un test/CI engineer senior. Tu trabajo es cablear cobertura con umbrales
sanos y un CI mínimo que corra los tests, SIN romper la suite existente ni poner
umbrales irreales. Sigue las convenciones del proyecto.

**Principio rector**: el umbral inicial se pone **en o ligeramente por debajo de
la cobertura REAL actual**, y se sube por trinquete después. NUNCA poner 100%
(el equipo termina desactivándolo). Rango sano: 70–85%.

---

### Paso 0: Detectar stack y estado actual

1. Detectar lenguajes con tests:
   - Python: `pyproject.toml`/`pytest.ini`/`conftest.py` + `tests/`
   - JS/TS: `package.json` con `vitest`/`jest` + `*.test.*`/`*.spec.*`
2. Detectar gestor de paquetes JS por lockfile:
   - `pnpm-lock.yaml` → pnpm · `yarn.lock` → yarn · `package-lock.json` → npm · `bun.lockb` → bun
3. Detectar si ya hay cobertura configurada (`--cov` en addopts, `coverage` en
   vitest/jest config). Si ya existe, **solo ajustar umbrales**, no duplicar.
4. Detectar si el proyecto usa GitHub Actions (`.github/workflows/`).
5. **Reportar lo detectado y pedir confirmación** antes de tocar nada.

---

### Paso 1: Medir la cobertura real ANTES de poner umbral

A menos que se pase `--threshold`, **correr la suite con cobertura una vez** para
saber el número real, y usar ese número (redondeado hacia abajo) como umbral inicial.

**Python:**
```bash
pip install pytest-cov   # si falta
pytest --cov=<paquete> --cov-branch --cov-report=term-missing
```
Leer el `TOTAL` y usar ese % (o 5 puntos menos) como `fail_under`.

**JS/TS:**
```bash
<pm> run test -- --coverage    # o vitest run --coverage
```
Leer el % de lines/statements y usarlo como threshold inicial.

Si la suite falla al correr, **NO configurar umbrales** — reportar los fallos al
usuario primero (un umbral sobre una suite roja no tiene sentido).

---

### Paso 2: Configurar cobertura Python (pytest-cov)

En `pyproject.toml` (o `setup.cfg`/`pytest.ini` según use el proyecto):

```toml
[tool.coverage.run]
branch = true
source = ["<paquete>"]
omit = ["*/tests/*", "*/migrations/*", "*/__init__.py"]

[tool.pytest.ini_options]
addopts = "--cov=<paquete> --cov-branch --cov-report=term-missing --cov-report=xml"

[tool.coverage.report]
fail_under = <REAL>        # el número medido en el Paso 1, NO 100
show_missing = true
skip_covered = false
```

- Respetar el `addopts` existente (concatenar, no sobrescribir marcadores como
  `--strict-markers`).
- `--cov-report=xml` deja el archivo para que el CI suba cobertura si se quiere.

---

### Paso 3: Configurar cobertura JS/TS

**Vitest** (`vitest.config.ts`):
```ts
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      perFile: true,
      thresholds: {
        statements: <REAL>, branches: <REAL-5>,
        functions: <REAL>, lines: <REAL>,
        autoUpdate: true,   // sube los números solo al mejorar (trinquete)
      },
    },
  },
})
```

**Jest** (`jest.config.{js,ts}`) — no tiene `autoUpdate`, se trinquetea a mano:
```js
coverageThreshold: {
  global: { statements: <REAL>, branches: <REAL-5>, functions: <REAL>, lines: <REAL> },
},
coverageReporters: ['text', 'html', 'lcov'],
```

En monorepos (ej. pnpm + Turbo), configurar por paquete/app, no a nivel raíz.

---

### Paso 4: Generar el workflow de CI (salvo `--no-ci`)

Crear `.github/workflows/tests.yml`. **NO tocar** los workflows de deploy
existentes — este es un workflow nuevo e independiente que corre en PRs.

Adaptar la matriz al stack real detectado (Python, Node, o ambos):

```yaml
name: Tests

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  python:
    if: <hay-python>
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest --cov --cov-report=term-missing
        # el fail_under del pyproject actúa como gate

  node:
    if: <hay-node>
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: <pm>
      - run: <pm> install --frozen-lockfile
      - run: <pm> run test -- --coverage
```

Reglas del workflow:
- Excluir del CI los tests marcados `@pytest.mark.integration`/`e2e` que necesiten
  servicios externos reales (usar `-m "not integration and not e2e"`).
- NUNCA meter secretos ni credenciales reales en el YAML — usar `secrets.*` de
  GitHub si algún test los necesita (aunque idealmente los tests mockean, ver
  `/e2e-gen`).
- Si el proyecto ya tiene un workflow que corre tests, NO duplicar — avisar.

---

### Paso 5: Verificar (obligatorio)

Aplica la disciplina de `verification-before-completion`. Antes de declarar hecho:

1. Correr la suite con la config nueva y confirmar que **pasa con el umbral**:
   ```bash
   pytest            # exit 0, no cae por fail_under
   <pm> run test -- --coverage   # exit 0
   ```
2. Validar el YAML del workflow (sintaxis).
3. Si algo falla, reportar el output real — NO declarar éxito sin evidencia.

---

### Paso 6: Reportar

```
Cobertura + CI configurados:

Python:
  Cobertura actual:  78%
  Umbral (fail_under): 75%   ← trinquete: subir a medida que mejore
  Config:            pyproject.toml

JS/TS (pnpm + Vitest):
  Cobertura actual:  71%
  Thresholds:        lines 70 / branches 65 (autoUpdate on)

CI:
  .github/workflows/tests.yml — corre en cada PR y push a main/develop
  Tests de integración/e2e excluidos (requieren servicios reales)

Verificación: ✓ suite pasa con umbrales (pytest exit 0, vitest exit 0)

Siguiente paso sugerido: subir umbrales gradualmente (ratcheting) y añadir
Schemathesis a las APIs (ver /e2e-gen).
```

---

## Reglas

- **NUNCA poner 100%** de umbral — medir el real y arrancar en o bajo ese número
- **NUNCA sobrescribir** workflows de deploy existentes — crear uno nuevo e independiente
- **NUNCA configurar umbrales sobre una suite que falla** — reportar los fallos primero
- **SIEMPRE medir la cobertura real** antes de fijar el umbral (salvo `--threshold`)
- **SIEMPRE verificar** que la suite pasa con la config nueva antes de declarar hecho
- **NUNCA meter secretos** en el YAML de CI — usar `secrets.*` de GitHub
- **Excluir del CI** los tests que requieren servicios externos reales (integración/e2e)
- **Respetar** el gestor de paquetes real (pnpm/npm/yarn/bun por lockfile)
- En monorepos, configurar cobertura **por paquete/app**, no solo en la raíz
- Preferir **trinquete** (subir umbral al mejorar) sobre umbrales fijos altos
