# /guia-usuario — Genera una guía de usuario (HTML para corrección + PDF)

Genera un manual de usuario profesional de una aplicación web: explora cada
vista del portal, toma capturas reales con Playwright, documenta cada pantalla,
acción y elemento en lenguaje simple (no técnico), y produce una **versión HTML
para revisión** y luego un **PDF** con el formato de manual impreso y los
colores de la plataforma.

Sigue el estilo de las guías de usuario de Neurya: tipografía serif tipo libro,
secciones numeradas, pasos numerados, callouts con barra lateral, capturas
grandes embebidas, lenguaje orientado a usuario final ("No necesitas
conocimientos técnicos…").

## Argumentos
- `$ARGUMENTS` — Opcional:
  - Ruta base de salida (default: `docs/manual/`).
  - Nombre del producto/cliente para los títulos (si no, se infiere del repo).
  - Paleta de colores deseada (si no, se infieren de la UI / logo).

## Requisitos previos
- La app debe estar **corriendo localmente** y con datos (idealmente algunos de
  ejemplo). Si está vacía, los listados se ven sin contenido.
- Tener credenciales de un usuario para loguear (preferible un admin para ver
  todas las vistas). NO leer secretos de archivos `.env` prohibidos: tomar la
  contraseña por variable de entorno que el usuario provea, o pedirla.
- Motor de PDF/HTML [`md-to-pdf-engine`](https://github.com/j-aldama/md-to-pdf-engine) clonado en tu máquina,
  con su ruta en la variable de entorno `MD_PDF_ENGINE`
  (exporta `markdownToHTML` y `getTemplateById` desde `dist/index.js`; CLI en
  `dist/cli.js`). Si `dist/` falta o tocaste `src/`, recompilar:
  `cd "$MD_PDF_ENGINE" && npm install && npm run build`.

---

## Instrucciones

Eres un technical writer que produce manuales para usuarios no técnicos. El
documento debe poder leerlo alguien que no conoce el código ni la arquitectura.
**No inventes funcionalidad: documenta solo lo que existe en el código y en la UI.**

### Paso 1 — Confirmar alcance (AskUserQuestion)

Pregunta lo que cambie el resultado y no puedas inferir:
1. **Paleta de colores:** ¿qué colores usa el manual? (siempre preguntar)
   - **Neurya** — la marca de la agencia (azul Neurya `#0080ff` / oscuro
     `#0f2033` / acento `#00d4ff`). Para entregables con identidad Neurya.
   - **Cliente** — la identidad de marca del cliente final (su azul/rojo/etc.).
     Si se elige, pedir/confirmar los colores de marca del cliente.
   - **Plataforma** — los colores de la propia aplicación que se documenta
     (inferidos de la UI / logo: color de títulos, separadores, botones).
   Con la elección, usa o crea la plantilla del generador correspondiente
   (ver Paso 6).
2. **Capturas:** ¿autorizás automatizar el navegador con Playwright? (solo navega
   la app local, no envía nada a usuarios finales). Si no, el manual va sin
   screenshots (placeholders).
3. **Profundidad:** ¿exhaustivo (cada elemento/botón/etiqueta) o funcional
   (vista + acciones principales)?
4. **Flujos de agentes/IA** (si aplica): documentar paso a paso con ejemplos
   (sin disparar envíos), o ejecutar en modo simulación y capturar resultados.

Si el usuario ya dio estas respuestas en su prompt, no repreguntes. La paleta es
la única que se pregunta SIEMPRE, salvo que el usuario ya la haya indicado.

### Paso 2 — Mapear las vistas y los flujos (subagentes en paralelo)

Lanza agentes `Explore` en paralelo para no consumir contexto:
- Uno que mapee **cada vista** del dashboard/portal: propósito, columnas de
  tabla (textos exactos), botones (texto exacto), campos de formulario (label,
  tipo, requerido, opciones), badges de estado, filtros. Pídele textos de UI
  literales — van tal cual al manual.
- Uno (si hay agentes de IA/automatizaciones) que documente el **flujo de cada
  agente** de punta a punta, con `archivo:línea` y ejemplos "entra X → produce Y".
- Lee también el `sidebar`/menú para conocer el orden y los nombres de las
  secciones como las ve el usuario; eso estructura el manual.

### Paso 3 — Datos de ejemplo (DB demo aislada, NUNCA producción)

Antes de capturar, verifica **a qué base apunta la app local** (mirá `DATABASE_URL`
enmascarando credenciales: `host/puerto/db`, sin secretos). Si la "app local"
apunta a un contenedor o host de **producción**, NO siembres datos ahí ni captures
datos reales de clientes en un manual.

Camino recomendado (aislado): levanta un Postgres demo en un **puerto distinto**
(usa la imagen que el proyecto necesite — p. ej. `pgvector/pgvector:pg15` si el
esquema usa la extensión `vector`; `postgres:15` plano falla con
`extension "vector" is not available`), corre migraciones + seed de catálogos +
seed de registros demo, y arranca **una segunda instancia** del dashboard
(`DASHBOARD_PORT`/puerto propio, `DATABASE_URL` a la DB demo) solo para capturar.
Si el seed crea un admin de "producción" cuando hay `NODE_ENV=production` o
`ADMIN_*` en el entorno, resetea la password del admin de dev directamente en la
DB demo con la función `hashPassword` del propio repo (no leas secretos).

Los datos deben cubrir variedad (distintos estados, tipos, canales) para que las
capturas se vean representativas. No dispares notificaciones/envíos. Avisa que son
datos de muestra y deja anotado el puerto/where de la DB demo para poder bajarla
luego.

### Paso 4 — Capturar pantallas con Playwright

Escribe un script (`<app>/e2e/capture-manual.mjs` o similar) que:
- Loguee con las credenciales (email + password por variable de entorno).
- Capture cada vista a `docs/manual/img/NN-slug.png`. Usa un **viewport ancho
  (~1680×950)** y `deviceScaleFactor: 2`, `fullPage: true`: a 1440 los listados
  con muchas columnas (Requerimientos) se cortan.
- Capture los **modales de alta** clave (abrir el botón "Nuevo/Agregar" y
  screenshot del formulario). Conviene un segundo script `capture-modals.mjs`
  para no mezclar navegación de vistas con apertura de modales.
- Para vistas que tardan en cargar (detalle, dashboard), espera a que
  desaparezca "Cargando…" o usa `waitForTimeout` suficiente. Con Next.js en
  dev, **cada ruta compila en frío la primera vez** (lento): usa timeouts
  amplios (60–120 s) tras el login.
- Para tomar la contraseña sin leer `.env` prohibido: extrae solo la variable
  puntual con `grep`/`sed` y pásala como env var al `node`, sin imprimir el valor.
- **Forma de la API**: para abrir la ficha de detalle suele resolverse el id vía
  `fetch('/api/...')`. La respuesta puede ser un **array plano** o venir envuelta
  (`{data:[...]}`): contempla ambas (`Array.isArray(json) ? json : json.data`).

Si Playwright se acaba de (re)instalar, falta el binario del navegador:
`npx playwright install chromium`.

Verifica visualmente 2-3 capturas (con Read sobre los PNG) antes de seguir; si
alguna salió en "Cargando…" o vacía, re-captúrala con más espera.

### Paso 5 — Escribir el Markdown (tono GUÍA DE USUARIO)

Crea `docs/manual/guia-usuario-<producto>.md` con esta estructura y tono:
- **H1**: "Manual de Usuario — <Producto>". Párrafo de bienvenida + "No
  necesitas conocimientos técnicos…".
- Secciones numeradas (`## 1.`, `## 2.`, `### 9.1`…). Empieza por: qué puedes
  hacer, iniciar sesión, pantalla principal, controles comunes, y luego una
  sección por área del menú.
- Cada vista: una frase de propósito, la captura embebida con `![alt](ruta
  absoluta al png)`, y la explicación de columnas/acciones/campos en **bullets
  o pasos numerados**. Resalta términos de UI en **negrita**.
- Usa blockquotes `>` para las notas/advertencias ("Importante:", "Por qué
  importa:", consejos).
- Si hay agentes de IA: una sección por agente con el flujo en **pasos
  numerados** y una tabla "el usuario hace X → el agente hace Y".
- Lenguaje simple, en segunda persona ("haz clic", "verás"), sin jerga técnica.
- Cierre en cursiva: nota de que las capturas son de ejemplo y, si aplica, que
  en pruebas no se envía nada a usuarios reales.

Las rutas de imagen en el `.md` deben ser **absolutas** a los PNG.

### Paso 6 — Plantilla de colores del motor

El motor (`md-to-pdf-engine`) tiene plantillas en `src/templates/` (compiladas a
`dist/`). Según la paleta elegida en el Paso 1:
- **Neurya** → plantilla `neurya` si existe; si no, `ejecutiva-oscura` (tema
  oscuro de marca Neurya).
- **Plataforma** o **Cliente** → usa la plantilla genérica **`manual-usuario`**
  (trae todos los refinamientos de estilo de manual y toma los colores de su
  `TemplateConfig`). Para la marca del cliente, lo más simple es ajustar los
  colores de `src/templates/manual-usuario.ts` (o pasar una copia de esa config
  con `primary`/`secondary`/`accent` del cliente) y `npm run build`. No hace
  falta crear una plantilla por cliente: el estilo es el mismo, solo cambian los
  colores.

Mapeo de colores de la plantilla (`TemplateConfig.colors`):
- `primary` = color de títulos (azul/oscuro de marca).
- `secondary` = separadores/acentos (color del logo).
- `accent` = enlaces/detalles (color de botones).
Fuentes serif (`Georgia`/`Garamond`) para el look de manual impreso.

**Estilo del manual (refinamientos, no solo colores).** El CSS base es plano; un
buen manual necesita ajustes de legibilidad que conviene atar al `id` de la
plantilla en `src/pdf-styles.ts` (igual que `ejecutiva-oscura` y `manual-usuario`
ya hacen — mirá `generateManualStyles` como referencia), para no afectar otras
plantillas:
- **Ancho de línea**: `main { max-width: ~880px; margin: 0 auto }` — el cuerpo a
  borde completo (líneas >75 caracteres) se lee mal. En `@media print` quitarlo.
- **Callouts** (`blockquote`): fondo suave + barra de color de marca + el primer
  término en el color de acento, para que "Importante/Nota" salten a la vista.
- **Tablas**: header de marca con buen padding (≈10-12px), zebra visible, y la
  primera columna en negrita-marca cuando es una tabla de campos/columnas.
- **Capturas** (`main img`): borde sutil + `border-radius` + sombra suave para
  encuadrarlas como figura; quitar la sombra en `@media print`.
- Evitar cortes feos en impresión: `img`, `blockquote` y `h2/h3` con
  `break-inside/after: avoid`.

Plantillas ya disponibles (no recrear): **`manual-usuario`** (genérica para
manuales, refinada — usar esta por defecto), `ejecutiva-oscura` (reportes Neurya),
`corporativa-clasica`, `moderna-minimalista`, `tecnica-documentacion`,
`profesional-moderna`, `moderna-azul`.

### Paso 7 — Embeber imágenes y generar HTML (PARA CORRECCIÓN)

El motor NO resuelve rutas de imágenes locales: hay que **embeberlas en base64**
antes de generar. Lo más práctico es un script reutilizable
`docs/manual/build-html.mjs` que: (1) lee el `.md`, (2) reemplaza cada
`![alt](ruta.png)` por `![alt](data:image/png;base64,…)`, (3) llama a
`markdownToHTML(md, template)` y (4) inyecta `id`s de sección para el índice
clickeable. Importa el motor así:
```js
const { markdownToHTML, getTemplateById } =
  await import(`${process.env.MD_PDF_ENGINE}/dist/index.js`);
```

> **CRÍTICO — rutas de imagen absolutas correctas.** Las rutas `![](...)` del `.md`
> deben apuntar al usuario/host REAL de esta máquina. Si quedaron con otro home
> (p. ej. `/Users/otra-persona/...`), el embebido **falla en silencio** y el HTML
> sale de pocos KB en vez de varios MB. Verifica: el HTML final debe pesar varios
> MB y contener tantos `data:image/png;base64` como capturas. Si no, corrige el
> home en las rutas del `.md` y regenera.

Abre el HTML (`open …html`) y **detente acá**: el usuario revisa y pide
correcciones sobre el `.md`. Itera HTML hasta su visto bueno. Para revisar el
estilo sin leer 16 MB, podés renderizar 2-3 secciones a PNG con Playwright
(`page.goto('file://…html')` + `screenshot`) y mirarlas.

### Paso 8 — Generar el PDF final (tras aprobación)

Cuando el usuario apruebe el HTML, genera el PDF con el CLI del motor, desde el
`.md` con imágenes embebidas (el mismo que produjo el HTML):
```
node "$MD_PDF_ENGINE/dist/cli.js" generate \
  "<embed>.md" \
  --template <plantilla> \
  --output "docs/manual/guia-usuario-<producto>.pdf" \
  --title "Manual de Usuario — <Producto>" \
  --author "<autor o empresa>" \
  --overwrite
```
Verifica el PDF (Read sobre 2-3 páginas como imagen) para confirmar que las
imágenes se embebieron y los colores/estilo se aplicaron. Borra la copia `.md`
embebida temporal si la usaste (se regenera).

### Paso 9 — Entregables y limpieza

Reporta al usuario:
- `docs/manual/guia-usuario-<producto>.md` — fuente editable.
- `docs/manual/guia-usuario-<producto>.html` — versión de corrección.
- `docs/manual/guia-usuario-<producto>.pdf` — entregable final.
- `docs/manual/img/` — capturas.

Menciona si dejaste datos de ejemplo en la base local y el script de captura
(reutilizable). NO commitees salvo que el usuario lo pida.

---

## Notas
- Regla de oro: documentar lo real, no lo ideal. Textos de UI literales.
- Seguridad: nunca leas ni imprimas secretos de `.env`/credenciales; toma
  contraseñas por variable de entorno puntual.
- El HTML del Paso 7 es el punto de control humano: no generes el PDF hasta que
  el usuario apruebe.
