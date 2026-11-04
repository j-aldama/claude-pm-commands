# /test-cases — Genera casos de prueba manuales en HTML interactivo multi-perfil

Analiza la aplicacion (completa o la parte indicada) y genera **un unico archivo
HTML autocontenido** con casos de prueba manuales organizados en pestañas por
perfil de usuario (rol x personalidad), para repartir a compañeros y que
prueben la plataforma sin conocer el codigo.

El HTML permite marcar OK/Falla/Bloqueado/N-A, escribir notas, guarda el
progreso en el navegador y exporta los resultados a JSON/Markdown y reportes
de bug listos para pegar en un ticket.

## Argumentos

- `$ARGUMENTS` — **Opcional**. Alcance a cubrir: nombre de modulo, feature,
  ruta de carpeta o descripcion libre. **Si esta vacio, cubre la aplicacion
  completa sin preguntar** (con los presupuestos del Paso 5.4).
  Ejemplos:
  - `/test-cases`
  - `/test-cases "modulo de facturacion"`
  - `/test-cases apps/portal/ --url http://localhost:8000`
  - `/test-cases "login y registro" --no-browser`

### Flags

- `--no-browser` — omite la verificacion en runtime, solo analisis estatico
- `--url <base>` — URL base de la app corriendo (evita autodeteccion)
- `--allow-remote-url` — permite una URL que no sea local (requiere confirmacion
  explicita del usuario en el momento; ver Paso 4.1)
- `--perfiles "a,b"` — limita a perfiles ya derivados del codigo
- `--merge <archivo.json>` — regenera conservando los resultados de una
  ejecucion previa **exportada desde el HTML**
- `--overwrite` — permite sobrescribir artefactos existentes
- `--out <ruta>` — ruta de salida dentro del repo (default: `docs/qa/`)
- `--name <slug>` — fuerza el identificador del archivo (por defecto se deriva
  del alcance; ver Paso 0.4)
- `--separado` — alcance multi-modulo: genera **un HTML por modulo** (salta la
  pregunta del Paso 2.5)
- `--mezclado` — alcance multi-modulo: genera **un solo HTML** con todos los
  modulos, filtrables desde la interfaz (salta la pregunta del Paso 2.5)

---

## Instrucciones

Eres un **QA Lead senior**. Tu trabajo es producir un plan de pruebas manuales
exhaustivo y **ejecutable por alguien que no conoce el sistema**, aplicando
tecnicas formales de QA sobre el comportamiento real del codigo.

### Reglas inviolables

- **No inventes funcionalidad.** Cada caso deriva de codigo leido o de UI
  observada. Si dudas de un comportamiento, el caso queda con
  `nivel_verificacion: "estatico"`, nunca con un resultado esperado afirmado
  como si estuviera confirmado.
- **Nunca abras `.env`, `.env.*`, `credentials.json`, `*secret*`, `*password*`,
  `*token*`, `*api_key*`.** Ver Paso 4.3.
- **Nunca escribas credenciales, cookies, tokens, headers de auth, emails
  personales, IDs de registros reales ni URLs prefirmadas** en el HTML, el JSON
  ni la salida del chat. Usa placeholders (`<usuario admin de prueba>`) y datos
  sinteticos.
- **Runtime solo contra entornos locales o QA aislados.** Nunca produccion.
  Ver Paso 4.1.
- **No modifiques codigo de la aplicacion.** Este comando solo lee y escribe en
  la ruta de salida.
- **Nunca elijas el modo de entregable en silencio.** Si el alcance abarca 2 o
  mas modulos y no se paso `--separado` ni `--mezclado`, pregunta (Paso 2.5).
  Si el usuario no define, el default es `mezclado`.
- **No ejecutes vos mismo acciones destructivas ni con efectos externos**
  durante la navegacion automatizada del Paso 4: borrar, cobrar, enviar
  emails/SMS/WhatsApp, disparar webhooks, migrar o resetear datos. **Esta regla
  es sobre lo que VOS automatizas con Playwright ahora, no sobre el contenido
  del catalogo.** Los flujos que en produccion terminan en un efecto externo
  real (mensajeria, cobros, notificaciones a terceros) igual se convierten en
  casos de prueba manuales — ver Paso 5.1.11 — para que un humano los ejecute
  despues en un entorno aislado. Nunca los omitas del catalogo ni los mandes a
  `cobertura_pendiente` solo porque tienen un efecto externo: eso deja sin
  cubrir justo lo que valida el go/no-go a produccion.

### Que NO hace este comando

- No escribe tests automaticos → `/e2e-gen`.
- No genera el protocolo lineal de aceptacion en Markdown → `/acceptance-checklist`.
- No genera el documento simplificado y firmable para cliente → `/checklist-cliente`.
  **Este HTML es un artefacto interno**: contiene referencias tecnicas, bugs y
  metricas, y no debe entregarse como documento de aceptacion.
- No genera manual de usuario ni inventario visual de pantallas → `/guia-usuario`.
  Aca las capturas son evidencia diagnostica, no documentacion.

---

### Paso 0 — Parsear argumentos y preparar

1. Extrae flags de `$ARGUMENTS`; lo que quede es el **alcance**.
2. Si el alcance esta vacio → alcance = **aplicacion completa**. No preguntes.
3. **Resolver `OUT_DIR`** (default `docs/qa/`): resuelve la ruta canonica y
   verifica que quede **dentro del repositorio actual**. Rechaza rutas que
   escapen con `../`, symlinks que apunten fuera, y rutas del sistema. Crea el
   directorio si no existe.
4. **Derivar el `SLUG` del entregable.** Los archivos NUNCA se llaman solo
   `test-cases`: llevan un identificador para poder convivir varios en la misma
   carpeta (uno por modulo, por sprint o por entrega).

   - Si se paso `--name <slug>`, usalo tal cual (normalizado).
   - Si no, derivalo del **alcance**: minusculas, sin acentos ni `ñ`, espacios y
     `/` a guiones, solo `[a-z0-9-]`, sin guiones repetidos ni al inicio/final,
     maximo 40 caracteres. Quita palabras de relleno (`modulo`, `de`, `del`,
     `la`, `el`, `los`, `app`, `apps`, `src`) cuando el resto siga siendo
     identificable.
   - Si el alcance esta vacio (app completa) → `SLUG = "app-completa"`.

   | Invocacion | Archivos generados |
   |---|---|
   | `/test-cases` | `test-cases-app-completa.html` / `.json` |
   | `/test-cases "modulo de facturacion"` | `test-cases-facturacion.html` |
   | `/test-cases apps/portal/` | `test-cases-portal.html` |
   | `/test-cases "login y registro"` | `test-cases-login-y-registro.html` |
   | `/test-cases "pagos" --name pagos-sprint12` | `test-cases-pagos-sprint12.html` |

   El `SLUG` se usa tambien en el `<title>` y el encabezado del HTML, y en la
   clave de `localStorage` (Paso 6.2), para que dos entregables abiertos en el
   mismo navegador **no se pisen el progreso**.

   **En modo `--separado` (Paso 2.5) hay un `SLUG` por modulo**, derivado del
   nombre del modulo con las mismas reglas (`test-cases-facturacion.html`,
   `test-cases-pagos.html`, ...). Si se paso `--name`, se usa como prefijo:
   `--name sprint12` → `test-cases-sprint12-facturacion.html`. La deteccion de
   colisiones del punto 5 aplica a **cada** entregable por separado.

5. **Colision de artefactos**: si ya existen `test-cases-<SLUG>.html` / `.json`
   y no se paso `--overwrite` ni `--merge`, **no sobrescribas**: genera
   `test-cases-<SLUG>-YYYYMMDD-HHMMSS.html/.json` y avisalo en el resumen final.
   Si el slug derivado choca con otro entregable de alcance distinto, preferi
   pedirle al usuario un `--name` a inventar un sufijo poco claro.
6. Si se paso `--merge <archivo.json>`, cargalo ahora y valida que tenga
   `results_schema_version`. Si no es un export de resultados valido, avisa y
   continua sin merge.
7. Escribe siempre a un temporal y renombra al final (escritura atomica).

---

### Paso 1 — Contexto del proyecto

Lee, si existen: `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/`, PRD
(`prd.json`, `docs/prd.md`), `package.json` / `pyproject.toml` /
`requirements.txt`, `docker-compose.yml`, `Makefile`.

Extrae: nombre del producto, stack, entry points, estructura de modulos,
integraciones externas y flujos de usuario ya documentados.

Si hay alcance acotado, identifica que carpetas/modulos corresponden y **limita
el escaneo del Paso 2 a esos** mas sus dependencias directas.

---

### Paso 2 — Mapa funcional (analisis estatico)

Escanea y construye un mapa interno. **De aca salen los valores frontera: no
inventes limites, leelos del codigo.**

1. **Rutas / endpoints**: metodo HTTP, path, parametros, decoradores de
   auth/permisos, respuesta esperada, redirecciones.
2. **Vistas y templates**: pantallas, componentes, navegacion, estados vacios y
   de carga.
3. **Formularios**: cada campo con tipo, `required`, validadores, longitudes,
   rangos, regex, `choices`, dependencias entre campos.
4. **Modelos / esquemas**: `max_length`, `unique`, `null`/`blank`, FK y
   `on_delete`, `choices`, defaults, constraints e indices unicos.
5. **Permisos y roles**: grupos, `is_staff`/`is_superuser`, clases de permiso,
   mixins, multi-tenant, ownership a nivel de objeto.
6. **Maquinas de estado**: campos `status`/`estado`, transiciones permitidas y
   **las prohibidas**.
7. **Asincronia**: tareas en background, webhooks, cron, emails, notificaciones.
8. **Feature flags** y configuracion que cambie comportamiento visible.

**Procedencia del dato.** Cada limite o regla se clasifica como `codigo`,
`runtime` o `desconocido`. El codigo no siempre manda: validaciones de APIs
externas, constraints de DB remota, configuracion de despliegue o flags
dinamicos pueden diferir. **Si codigo y runtime discrepan, prevalece runtime** y
la discrepancia se reporta en el resumen final.

Anota el `archivo:linea` de cada hallazgo — se usa en la trazabilidad del Paso 5.

---

### Paso 2.5 — Modo de entregable (solo si el mapa abarca mas de un modulo)

**Cuando se activa.** Solo si el Paso 2 mapeo **dos o mas modulos / areas
funcionales distintas**. Con un solo modulo, salta al Paso 3 sin preguntar.

**Si se paso `--separado` o `--mezclado`**, usalo e informalo en una linea.

**Si no**, pregunta y **espera la respuesta** antes de seguir:

```
El alcance abarca 4 modulos: facturacion, pagos, auth, usuarios.

¿Como armo el entregable?

  [1] Mezclado (recomendado) — un solo HTML con los 4 modulos:
        docs/qa/test-cases-app-completa.html
      El HTML ya filtra por modulo, asi que cada tester puede enfocarse en lo
      suyo sin abrir otro archivo. Una sola barra de progreso global.

  [2] Separado — un HTML por modulo:
        docs/qa/test-cases-facturacion.html
        docs/qa/test-cases-pagos.html
        docs/qa/test-cases-auth.html
        docs/qa/test-cases-usuarios.html
      Sirve para repartir: le mandas a cada compañero solo su archivo, y
      cada uno exporta su JSON por separado. Progreso independiente.

¿Mezclado o separado? (1/2)
```

**Default si el usuario no contesta claro: `mezclado`.** A diferencia de los
comandos de aceptacion, aca mezclar **no pierde nada**: el HTML ya trae filtros
por modulo (Paso 6.2) y su clave de `localStorage` por entregable. Separar solo
gana cuando vas a repartir archivos distintos a personas distintas.

**Como cambia cada modo:**

| Paso | `--separado` | `--mezclado` |
|---|---|---|
| Paso 0.4 (slug) | Un `SLUG` **por modulo** (`test-cases-<modulo>.html/.json`) | Un solo `SLUG` del alcance completo |
| Paso 3 (perfiles) | Perfiles derivados por modulo; un modulo sin rol propio reusa los globales | Un juego de perfiles para todo |
| Paso 5.4 (presupuestos) | Se reparten entre modulos — ver abajo | Presupuestos globales tal cual |
| Paso 6 (entregable) | Un HTML+JSON por modulo, cada uno autocontenido | Un HTML+JSON |
| Paso 7 (merge) | El `--merge` valida el `slug` contra el modulo, no contra el alcance | Igual que hoy |

**Presupuestos en modo separado (importante).** Los limites del Paso 5.4 estan
calibrados para *un* entregable de app completa. En separado **NO los
multipliques por modulo**: reparti el presupuesto global entre los modulos segun
la matriz de riesgo, con un **piso de 15 casos funcionales por modulo** para que
ningun entregable salga vacio. Si el reparto no alcanza ese piso para todos, es
señal de que son demasiados modulos → aplica la regla de abajo.

**Regla anti-explosion.** Maximo **6 entregables** por corrida en modo separado.
Si hay mas modulos, cubri los de mayor riesgo (dinero, datos personales,
permisos, borrados irreversibles) y manda el resto a `cobertura_pendiente` con
modulo, motivo y prioridad, incluyendo el comando exacto para generarlos despues.
**Nunca recortar en silencio.**

**Generacion incremental.** En separado, genera y cierra **un modulo completo a
la vez** (Pasos 3 a 6 para ese modulo, incluido su smoke test del Paso 7.2) antes
de arrancar el siguiente, en orden de riesgo. Si la corrida se corta, lo ya
entregado es utilizable en vez de quedar todo a medias.

---

### Paso 3 — Derivar perfiles (rol x personalidad)

**3.1 Roles reales.** Extraelos del codigo del Paso 2. Incluye siempre **usuario
anonimo / no autenticado** si hay cualquier ruta publica o login. No inventes
roles que el codigo no tenga.

**3.2 Arquetipos de personalidad:**

| Arquetipo | Como prueba |
|---|---|
| **Novato** | Sigue el camino feliz, no entiende jerga, se pierde, necesita mensajes claros, deja campos vacios sin querer |
| **Experto / apurado** | Va rapido, atajos, URLs directas, multiples pestañas, doble clic, no lee confirmaciones |
| **Caotico** | Rompe el flujo: back del navegador, refresh a mitad de proceso, sesion expirada, valores extremos, pega texto raro |
| **Malicioso** | Intenta escalar privilegios, cambia IDs en la URL, accede a datos ajenos, manipula formularios |

**3.3 Combinacion.** Cruza roles x arquetipos, pero **no generes el producto
cartesiano**:
- Cada rol lleva al menos **Novato** (happy path) y **Caotico**.
- **Malicioso** solo para el rol de menor privilegio y el anonimo — nunca para
  el superadmin (no tiene sentido escalar desde arriba).
- **Experto/apurado** para los roles que usan el sistema a diario.
- Fusiona combinaciones cuyos casos serian practicamente identicos.
- Objetivo: **3 a 8 perfiles**. Si salen mas, prioriza por riesgo y registra los
  descartados con su motivo.

**3.4 `--perfiles` solo selecciona, no crea.** Si un nombre no corresponde a un
perfil derivado, rechazalo e informa los disponibles. Nunca crea roles, eleva
privilegios ni anula las reglas de seguridad de este comando.

**3.5 Ficha de cada perfil** (cabecera de su pestaña): nombre legible
(ej. *"Recepcionista apurada"*), rol tecnico del que deriva, que sabe y que no,
que intenta lograr, y precondiciones generales (usuario, datos previos, permisos).

---

### Paso 4 — Verificacion en runtime (salvo `--no-browser`)

**4.1 Barrera de entorno — se evalua ANTES de cualquier conexion.**

Solo se acepta runtime contra:
- `localhost`, `127.0.0.1`, `[::1]`, o `*.localhost`
- Una URL de QA/staging que el usuario apruebe **explicitamente en el momento**,
  pasando `--allow-remote-url` y confirmando cuando se lo preguntes.

**Rechaza siempre** dominios que parezcan produccion (`www.`, dominio del
cliente, `prod`, `api.` publico) y hosts remotos sin aprobacion. Si el entorno
no pasa la barrera: **no te conectes**, avisa en una linea y degrada a analisis
estatico. No pidas permiso dos veces ni insistas.

**4.2 Detectar si ya esta corriendo.** Prueba `--url` si se paso; si no, prueba
`http://localhost` en `8000, 3000, 5173, 5000, 8080` con
`curl -s -o /dev/null -w "%{http_code}" --max-time 3`.

**4.3 Intentar levantarla — con preflight obligatorio.**

Busca en este orden: `docker compose up -d` → `make dev`/`make run` → script
`dev`/`start` de `package.json` → `python manage.py runserver` → `uvicorn`.

**Antes de ejecutar nada, LEE el comando y verifica** que se cumpla todo esto:
- Apunta a servicios locales, no a hosts remotos.
- No incluye migraciones destructivas, seeds masivos, `reset`, `flush`, `drop`.
- No usa un perfil/entorno de produccion.
- Los puertos que necesita estan libres (si ya hay algo corriendo ahi, no lo
  toques: usalo o degrada).

**Si no podes demostrar que se cumple, no lo ejecutes.** Degrada a estatico.

Si lo levantas: espera hasta 60s con reintentos; registra los PIDs o los IDs de
contenedor **exactos que creaste vos** y apaga solo esos al final. **Nunca
ejecutes `docker compose down` global** ni mates procesos que ya estaban.

Si falla el arranque: no insistas. Continua con analisis estatico puro y avisa.

**4.4 Credenciales — orden estricto:**

1. **Variables ya exportadas en el shell**: `QA_BASE_URL`, `QA_<ROL>_USER`,
   `QA_<ROL>_PASS` (ej. `QA_ADMIN_USER`), y nombres comunes del stack.
   Comproba **solo si existen** (`[ -n "${VAR:-}" ] && echo presente`).
   **Nunca imprimas su valor**: pasalas directamente al proceso del navegador.
2. **Seeds / fixtures / factories del repo** con usuarios de prueba no secretos.
3. **Preguntar al usuario** la URL base y las credenciales por rol.

**Nunca leas ni ejecutes el archivo `.env`.** Si no hay variables en el entorno,
podes mencionarle al usuario que las cargue el mismo en su shell antes de
reintentar — pero el comando no lo hace por el. Solo degradas a estatico si el
usuario no responde, se niega a darlas, o paso `--no-browser`.

**4.5 Navegar con Playwright** (MCP `playwright` o `claude-in-chrome`). Por cada
rol con credenciales, loguearse y recorrer las pantallas del alcance.

**La navegacion es de solo lectura.** Podes leer, filtrar, abrir y navegar. Para
crear, editar o borrar hace falta que se cumpla TODO: entorno local aislado,
datos sinteticos con prefijo `QA_`, la accion no dispara integraciones externas,
y esta declarada como permitida. Si no, se documenta sin ejecutar.

**Esto limita lo que EJECUTAS ahora, no lo que generas.** No es motivo para
excluir del catalogo los casos que en la vida real si disparan un efecto
externo (enviar un WhatsApp, cobrar, notificar a un webhook). Esos casos se
generan igual — ver Paso 5.1.11 — marcados para que los ejecute un humano
despues, nunca vos en este paso.

Objetivo del recorrido:
- Confirmar que las rutas del Paso 2 existen y son alcanzables.
- Descubrir pantallas, botones o validaciones que el codigo no revelaba.
- Capturar los **textos reales** de labels y mensajes de error — los casos deben
  citar lo que el tester va a ver, no el nombre interno del campo.
- Detectar discrepancias entre codigo y runtime.
- Capturar pantalla de las vistas clave.

**4.6 Capturas — presupuesto duro.** Maximo **12 capturas**, ancho maximo 800px,
comprimidas (WebP o JPEG), presupuesto total embebido de **5 MB**. Si se excede,
**omite las de menor prioridad** y deja un placeholder con su descripcion. **El
HTML siempre queda como un unico archivo**: nunca crees dependencias externas de
imagenes.

---

### Paso 5 — Generar los casos de prueba

**5.1 Tecnicas.** Aplica cada una **cuando exista el objeto correspondiente** en
el modulo. Si una tecnica no aplica (no hay filtros, ni estados, ni uploads),
registrala como `no_aplica` con motivo y `archivo:linea` — **no rellenes con
casos inventados**.

1. **Happy path** — flujo completo de punta a punta por cada flujo principal.
2. **Particiones de equivalencia** — una clase valida y las invalidas relevantes.
3. **Valores frontera** — por cada limite leido del codigo: `min-1`, `min`,
   `min+1`, `max-1`, `max`, `max+1`. Ademas: vacio, solo espacios, `0`,
   negativos, decimales donde se espera entero, fechas pasadas/futuras/hoy,
   fecha fin < fecha inicio, unicode y emoji, texto muy largo, HTML/`<script>`
   en campos de texto (verificar escapado), numeros con separadores de miles.
4. **Tablas de decision** — cuando el resultado depende de varias condiciones
   combinadas.
5. **Transicion de estados** — cada transicion permitida y, explicitamente, las
   **prohibidas** (verificar que el sistema las rechaza).
6. **Pairwise** — para filtros, buscadores y formularios con muchas opciones.
7. **Unicidad e integridad** — duplicados en campos unicos, borrado de registros
   referenciados, huerfanos, concurrencia (dos pestañas editando lo mismo).
8. **Error guessing / destructivos** — doble clic en submit, back del navegador
   tras guardar, refresh a mitad de flujo, sesion expirada, cancelar a mitad,
   red lenta, archivo de tipo/tamaño incorrecto en uploads.
9. **Permisos y seguridad (OWASP A01)** — URL directa a vista sin permiso,
   **IDOR** cambiando el ID en la barra, accion de admin desde cuenta comun,
   acceso cross-tenant, acceso sin sesion, endpoint de API directo, manipular
   campos ocultos del formulario.
10. **UX / movil / accesibilidad** — responsive en movil, navegacion completa por
    teclado, foco visible, estados vacios y de carga, claridad de los mensajes de
    error, textos cortados, contraste, zoom 200%. Para un barrido formal WCAG 2.2 AA
    con axe-core, usa la skill `a11y-playwright` sobre el mismo modulo.
11. **Efectos externos reales / integraciones** — cuando el flujo principal de
    negocio del modulo termina en un efecto que sale del sistema (enviar
    WhatsApp/email/SMS, cobrar, notificar un webhook, sincronizar con un
    tercero), genera **siempre** al menos un caso de punta a punta que lo
    cubra: disparar el flujo desde la UI con datos sinteticos y verificar en
    el sistema externo (o su sandbox/numero de prueba) que el efecto ocurrio y
    que el contenido/destino fue el correcto — no solo que la UI mostro un
    mensaje de exito. **No excluyas esta tecnica por tratarse de una "accion
    con efecto externo"**: esa restriccion (Paso 4.5) es sobre lo que el
    agente ejecuta solo durante la verificacion, no sobre el catalogo de
    casos. Marca estos casos `modo_ejecucion: requiere_entorno_aislado`, con
    precondicion explicita de usar solo datos/numeros/cuentas de prueba
    (prefijo `QA_`) y advertencia de nunca usar destinatarios reales.
    Prioridad `critica` cuando ese efecto es justo lo que valida el go/no-go a
    produccion (ej. confirmar que a un candidato le llega el WhatsApp
    correcto antes de salir a produccion).

**5.1.1 Que tecnica usar segun el objeto (referencia ISTQB):**

| Situacion en el codigo | Tecnica |
|---|---|
| Campo de formulario, parametro con rango valido | Particiones de equivalencia + valores frontera |
| Resultado depende de varias condiciones combinadas (permisos + estado + rol) | Tabla de decision |
| Entidad con estados y transiciones (pedido, ticket, sesion) | Transicion de estados — incluye las prohibidas |
| Filtro/buscador con muchas opciones combinables | Pairwise |
| Flujo de punta a punta con variantes (guest checkout, cupon, pago rechazado) | Escenario/caso de uso: 1 caso por flujo principal + 1 por variante alterna + 1 por variante de excepcion |
| Area de alto riesgo o comportamiento desconocido | Error guessing / exploratorio dirigido |
| Flujo termina en un efecto que sale del sistema (envio, cobro, webhook, sync) | Efectos externos reales (5.1.11) — punta a punta con verificacion en el sistema externo/sandbox |

No apliques una tecnica solo porque existe en la tabla — aplica la que corresponda al
objeto real que encontraste en el codigo (ver regla del Paso 5.1: `no_aplica` con
motivo si no corresponde).

**5.2 Estructura de cada caso:**

| Campo | Contenido |
|---|---|
| `case_id` | Determinista, derivado de `rol\|arquetipo\|modulo\|flujo\|tecnica\|variante`. **No dependa del orden de generacion.** Formato legible: `TC-FACT-ADMIN-BORDE-003` |
| `fingerprint` | Hash corto del contenido semantico (pasos + datos + esperado). Sirve al merge del Paso 7 |
| `perfil` | Perfil al que pertenece (dos perfiles = dos casos distintos) |
| `modulo` | Modulo / area funcional |
| `titulo` | Que se prueba, en una linea, sin jerga |
| `tecnica` | Tecnica de QA aplicada |
| `precondiciones` | Estado previo necesario, en pasos concretos |
| `datos` | Valores literales a usar (no "un valor invalido") |
| `pasos` | Numerados, imperativos, reproducibles sin conocer el sistema |
| `esperado` | Resultado observable en pantalla, con el texto real si se conoce |
| `prioridad` | `critica` \| `alta` \| `media` \| `baja` |
| `modo_ejecucion` | `seguro` \| `requiere_entorno_aislado` \| `solo_documentar` |
| `nivel_verificacion` | `estatico` \| `runtime_observado` \| `runtime_ejecutado` |
| `evidencia_verificacion` | Que se comprobo y como (vacio si `estatico`) |
| `automatizable` | `si` \| `no` + `motivo_manual` — lo consume `/e2e-gen` |
| `referencia` | `archivo:linea` o endpoint — va en bloque colapsable |

**Sobre `nivel_verificacion`:** haber visto la pantalla es `runtime_observado`.
Solo marca `runtime_ejecutado` si ejecutaste realmente ese caso y observaste el
resultado. **Ver una pantalla no verifica un caso de frontera, un IDOR ni una
transicion prohibida.**

**Sobre `modo_ejecucion: requiere_entorno_aislado`:** es el valor correcto
para pasos que crean/editan datos o disparan un efecto externo real (envios,
cobros, notificaciones, webhooks) — **no es un motivo para quitar el caso del
catalogo ni mandarlo a `cobertura_pendiente`.** El caso se genera igual, con
esta marca, para que lo ejecute un humano contra un entorno aislado. Ver Paso
5.1.11.

**5.3 Calidad.** Los pasos deben ser ejecutables por alguien que abre la app por
primera vez. Nada de "validar el flujo": deci que boton tocar, que escribir y que
tiene que aparecer. **Prioriza error paths sobre happy paths.**

**5.4 Presupuestos (obligatorios cuando el alcance es la app completa):**

| Limite | Valor |
|---|---|
| Inventario inicial | 200 archivos o 100k lineas |
| Lectura profunda | 80 archivos / 12 flujos de mayor riesgo |
| Modulos cubiertos | 20 |
| Casos funcionales | 120 |
| Casos de seguridad | 40 (compartidos entre perfiles) |
| Perfiles | 3–8 |
| Capturas | 12 |
| Peso del HTML | 5 MB |

**Anti-explosion de fronteras:** la matriz de valores frontera de un campo se
genera **una vez por modulo** y se asigna al perfil mas relevante — no se
duplica por cada perfil. Con varios campos, aplica pairwise sobre los valores
frontera en lugar del producto completo.

Prioriza por riesgo: dinero, datos personales, permisos, borrados irreversibles.
**Todo lo que exceda los presupuestos va a `cobertura_pendiente` con modulo,
motivo y prioridad. Nunca recortes en silencio.**

**Matriz de riesgo (impacto x probabilidad)** para decidir que modulo entra dentro
del presupuesto cuando hay que elegir: score = impacto (1-3) x probabilidad (1-3).

| Score | Prioridad | Ejemplo |
|---|---|---|
| 9 | Critica | pagos, borrado irreversible, datos personales, auth |
| 6 | Alta | flujo principal del modulo, permisos entre roles |
| 3-4 | Media | validaciones de formulario, filtros, exportaciones |
| 1-2 | Baja | textos, estados visuales sin efecto en datos |

Los modulos con score 9 nunca van a `cobertura_pendiente` aunque el presupuesto este
lleno — se recorta primero en los de score 1-2.

---

### Paso 6 — Generar el entregable

**6.1 `OUT_DIR/test-cases-<SLUG>.json`** — catalogo en crudo, versionable:

```json
{
  "schema_version": "1.0",
  "proyecto": "...",
  "slug": "facturacion",
  "alcance": "...",
  "generado": "YYYY-MM-DD",
  "runtime": { "verificado": true, "base_url": "http://localhost:8000",
               "entorno": "local" },
  "perfiles": [
    { "id": "admin-novato", "nombre": "Administrador novato", "rol": "admin",
      "arquetipo": "novato", "ficha": "...", "precondiciones": "..." }
  ],
  "perfiles_descartados": [{ "nombre": "...", "motivo": "..." }],
  "casos": [{ "case_id": "TC-FACT-ADMIN-BORDE-003", "fingerprint": "a1b2c3d4",
              "...": "..." }],
  "tecnicas_no_aplicables": [{ "modulo": "...", "tecnica": "...",
                               "motivo": "...", "referencia": "..." }],
  "discrepancias_codigo_runtime": ["..."],
  "cobertura_pendiente": [{ "modulo": "...", "motivo": "...",
                            "prioridad": "..." }]
}
```

**6.2 `OUT_DIR/test-cases-<SLUG>.html`** — un unico archivo autocontenido.

El `<title>` y el encabezado visible deben incluir proyecto y alcance
(ej. *"Casos de prueba — Portal Neurya · Facturacion"*), para que el compañero
sepa que archivo abrio cuando recibe varios.

#### Requisitos tecnicos (obligatorios)

- **Cero peticiones de red**: CSS y JS inline, sin CDN, sin fuentes externas,
  sin `fetch`. Debe funcionar offline, con doble clic desde el escritorio, y
  mandado por mail o WhatsApp.

- **Serializacion segura del dataset (CRITICO).** Los casos contienen payloads
  XSS como dato de prueba. Un `</script>` dentro del JSON cierra el bloque y
  ejecuta HTML. Al escribir el `<script type="application/json" id="test-data">`,
  escapa el JSON serializado **antes de insertarlo**, exactamente asi:

  ```js
  const payload = JSON.stringify(data)
    .replace(/&/g, '\\u0026')
    .replace(/</g, '\\u003C')
    .replace(/>/g, '\\u003E')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
  // `payload` se inserta como contenido del <script type="application/json">
  ```

  Ojo con el doble backslash: cada reemplazo debe producir la **secuencia de
  escape JSON de 6 caracteres** (backslash + `u003C`), NO el caracter en si.
  Asi el `<` nunca llega literal al documento y un `</script>` incrustado en un
  dato de prueba no puede cerrar el bloque. Los dos ultimos son separadores de
  linea unicode que rompen el parser de JS si van crudos.
  Leelo despues **solo** con
  `JSON.parse(document.getElementById('test-data').textContent)`.

- **Prohibido `innerHTML`.** Todo el contenido de casos, notas y evidencia se
  inserta creando nodos DOM y asignando `textContent`. Nada de plantillas
  interpoladas, atributos construidos por concatenacion, handlers inline ni
  interpolacion en CSS.

- **Enlaces de evidencia**: si el campo de evidencia se renderiza como enlace,
  acepta solo esquemas `http:`, `https:` y `file:`. Cualquier otro
  (`javascript:`, `data:`) se muestra como texto plano.

- Responsive: los compañeros lo van a abrir en el celular.

#### Interfaz

- Cabecera: proyecto, alcance, fecha, y **aviso destacado** si el runtime no se
  verifico ("casos derivados solo del codigo, no verificados contra la app").
- **Pestañas por perfil**, cada una con su ficha arriba.
- Barra de progreso por perfil: `probados / total`, con desglose OK/Falla/Bloqueado.
- Filtros: buscador por texto (con debounce) y filtros por modulo, prioridad,
  tecnica, nivel de verificacion y estado.
- Por caso, tarjeta colapsable con: id, titulo, badges (prioridad, tecnica,
  `no verificado`, `solo documentar`), precondiciones, datos, pasos numerados,
  resultado esperado, `<details>` "Referencia tecnica" (cerrado por defecto),
  botones **OK / Falla / Bloqueado / N-A**, notas y evidencia.
- Los casos `Falla` se resaltan. Los `solo_documentar` se marcan claramente como
  "no ejecutar en este entorno".
- **Renderizado perezoso**: monta solo la pestaña activa y pagina de a 25
  tarjetas. El dataset completo va embebido, pero no se monta entero al cargar.

#### Persistencia

- Estado en `localStorage`, clave `testcases::<proyecto>::<SLUG>` — asi dos
  entregables distintos abiertos en el mismo navegador no se pisan el progreso.
- **`localStorage` puede fallar bajo `file://`** (deshabilitado, `SecurityError`,
  o distinto segun navegador). Envolvelo en `try/catch` y detecta disponibilidad
  con una escritura/lectura de prueba al arrancar. Si no esta disponible, muestra
  un aviso "persistencia no disponible en este navegador — exporta tus resultados
  antes de cerrar" y deja el resto funcionando.
- Guardado automatico al cambiar cualquier campo (debounce en los de texto).
- Campo "Probado por" que se incluye en las exportaciones.
- Boton "Reiniciar" con confirmacion **inline**. Nunca `confirm()` ni `alert()`:
  bloquean la pagina.

#### Exportacion e importacion (todo client-side)

- **Exportar JSON** — resultados completos con `results_schema_version`, `slug`,
  `case_id` y `fingerprint` de cada caso. **Este es el archivo que alimenta
  `--merge`.** El archivo descargado se llama
  `resultados-<SLUG>-<probado-por>.json`, para que al juntar los de varios
  compañeros no se sobrescriban entre si.
- **Exportar Markdown** — resumen con tabla de resultados y detalle de fallas,
  para pegar en un ticket o PR.
- **Importar resultados** — carga un JSON exportado y restaura el estado (asi un
  compañero retoma en otra maquina, o se consolidan varias ejecuciones).
- **Copiar reporte de bug** por caso: titulo, perfil, precondiciones, pasos,
  esperado, obtenido (de las notas), severidad y referencia tecnica.
- **Degradacion**: las descargas se disparan solo desde un gesto del usuario,
  revocan el Object URL y capturan errores. Si `Blob`/`download` o
  `navigator.clipboard` fallan (Safari, iOS, `file://`), muestra el contenido en
  un `<textarea>` seleccionable como fallback.

---

### Paso 7 — Merge, validacion y cierre

**7.1 Merge (si `--merge <archivo.json>`).** El HTML no puede escribir en disco:
la fuente de resultados es el JSON exportado desde el navegador.

Verifica primero que el `slug` del export coincida con el `SLUG` de esta
ejecucion. Si no coincide, **para y avisa** — estarias mezclando resultados de
un entregable con los casos de otro. Luego cruza por `case_id`:

- Existe y **mismo `fingerprint`** → conserva estado, notas y evidencia.
- Existe y **`fingerprint` distinto** (el caso cambio) → conserva el estado pero
  marcalo `requiere_revalidacion` y resaltalo en el HTML.
- Caso nuevo → sin estado.
- Caso que ya no existe → va a la seccion "Obsoletos" del JSON y se reporta.
  **No lo borres en silencio.**

**7.2 Smoke test obligatorio antes de entregar.** Verifica y **arregla** lo que
falle (no lo reportes como pendiente):

1. Un caso cuyo dato contenga `</script><script>alert(1)</script>` se renderiza
   como texto y no rompe la pagina.
2. El HTML abre sin errores de consola y sin ninguna peticion externa.
3. Marcar estado y notas, recargar, y que el estado persista.
4. Modo sin `localStorage` y sin `clipboard`: la pagina sigue usable y avisa.
5. Exportar JSON y Markdown; reimportar el JSON y que restaure.
6. Merge con un caso nuevo, uno modificado y uno obsoleto.
7. Filtros, cambio de pestaña, paginacion y reset.
8. IDs unicos; todos los casos con pasos, esperado, prioridad y perfil.
9. Si ya existe otro entregable en `OUT_DIR`, abrir ambos y comprobar que el
   progreso de uno no afecta al del otro (claves de storage distintas).
10. Sin credenciales, tokens ni datos personales reales en HTML ni JSON.

**7.3 Resumen final al usuario** (breve, en el chat):

- Rutas generadas y peso del HTML.
- Nº de casos **por perfil** y **por prioridad**, cada uno con su **porcentaje
  del total**.
- **% de casos por nivel de verificacion** (estatico / observado / ejecutado).
- Perfiles descartados y por que.
- Discrepancias detectadas entre codigo y runtime.
- **Si el modulo tiene algun flujo con efecto externo real** (envios,
  cobros, notificaciones, webhooks, sync con terceros): decir explicitamente
  si quedo cubierto con casos `requiere_entorno_aislado` (Paso 5.1.11) o, si
  no aplica al alcance, por que no. Nunca dejarlo implicito.
- Cobertura pendiente: que quedo fuera, por que, con que prioridad.
- Si se genero con timestamp por no sobrescribir, decilo.
- Si ya habia otros `test-cases-*.html` en `OUT_DIR`, listalos en una linea para
  que se vea que entregables conviven.
- **Modo usado** (`separado` / `mezclado` / modulo unico).
- Como usarlo: *"Abrí `docs/qa/test-cases-<SLUG>.html` y mandale el archivo a
  cada compañero; cada uno marca su pestaña y al terminar exporta el JSON. Para
  consolidar: `/test-cases "<alcance>" --merge <json exportado>`."*

**En modo separado**, el resumen lleva una fila por entregable, para que se vea
de un vistazo que se genero y a quien mandarle cada archivo:

```
Casos de prueba generados (modo: separado, 4 modulos)

| Modulo      | Casos | Perfiles | Verificado runtime | Peso   | Archivo                        |
|-------------|-------|----------|--------------------|--------|--------------------------------|
| pagos       | 38    | 4        | si                 | 412 KB | test-cases-pagos.html          |
| auth        | 31    | 5        | si                 | 355 KB | test-cases-auth.html           |
| facturacion | 27    | 3        | si                 | 298 KB | test-cases-facturacion.html    |
| usuarios    | 19    | 3        | no (solo estatico) | 210 KB | test-cases-usuarios.html       |

Total: 115 casos en 4 entregables independientes.
Cada archivo tiene su propia clave de localStorage — el progreso no se pisa
aunque un compañero abra dos.

Consolidar cada uno por separado:
  /test-cases "pagos" --merge resultados-pagos-<quien>.json
```

**Nunca declares la tanda como terminada si algun modulo quedo sin generar**:
va explicito en `cobertura_pendiente` con su motivo y el comando para generarlo.

**7.4 Autocaptura (opcional).** Solo si tienes `vault-capture` instalado, registra el hito en tu vault:

```bash
vault-capture auto --event milestone \
  --title "Casos de prueba QA generados: <alcance>" --source claude \
  --body "<N> casos, <M> perfiles, salida en docs/qa/test-cases-<SLUG>.html"
```
