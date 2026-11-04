# /acceptance-checklist — Genera protocolo de pruebas de aceptacion

Analiza el codigo del proyecto actual y genera un documento Markdown completo
con checklist de pruebas de aceptacion manuales, listo para imprimir o compartir
con el cliente.

## Argumentos
- `$ARGUMENTS` — Opcional: **alcance** a cubrir (modulo, feature, lista de
  modulos separados por coma) y/o flags. Si esta vacio, cubre el proyecto
  completo.
  Ejemplos:
  - `/acceptance-checklist`
  - `/acceptance-checklist "facturacion, pagos, auth"`
  - `/acceptance-checklist "facturacion, pagos" --separado`
  - `/acceptance-checklist --out QA/acceptance.md`

**Compatibilidad con el uso anterior**: si `$ARGUMENTS` es una sola cosa que
**parece una ruta de archivo** (termina en `.md` o contiene `/`), se interpreta
como ruta de salida, igual que antes — no como alcance.

### Flags
- `--out <ruta>` — ruta o carpeta de salida
  (default: `docs/protocolo-pruebas-aceptacion.md`)
- `--separado` — alcance multi-modulo: genera un documento **por modulo**
  (salta la pregunta del Paso 2.5)
- `--mezclado` — alcance multi-modulo: genera **un solo documento** con todos los
  modulos como partes (salta la pregunta del Paso 2.5)

## Instrucciones

Eres un QA Lead senior. Tu trabajo es analizar el codigo del proyecto y generar
un protocolo de pruebas de aceptacion exhaustivo que un humano pueda ejecutar
paso a paso marcando checkboxes. Se preciso: cada escenario debe ser reproducible
sin conocimiento previo del sistema.

---

### Paso 1: Entender el proyecto

1. Lee `CLAUDE.md`, `README.md`, `AGENTS.md` y cualquier documentacion en `docs/`
2. Identifica:
   - **Nombre y descripcion** del proyecto
   - **Stack tecnologico** (framework, DB, servicios externos)
   - **Arquitectura**: estructura de carpetas, entry points, modulos principales
   - **Flujos de usuario** descritos en la documentacion
   - **Integraciones externas** (APIs, servicios, webhooks)
   - **Variables de entorno** necesarias para que el sistema funcione

3. Si existe un archivo PRD (`prd.json`, `docs/prd.md` o similar), leelo para
   extraer user stories y criterios de aceptacion.

---

### Paso 2: Escanear el codigo

Analiza el codebase sistematicamente:

1. **Endpoints/Rutas**: Lee todos los routers, views, controllers
   - Para cada endpoint extrae: metodo HTTP, path, parametros, respuesta esperada
   - Identifica cuales requieren autenticacion
2. **Servicios**: Lee la logica de negocio (services/, utils/, handlers/)
   - Identifica flujos complejos con multiples pasos
   - Identifica side effects (envio de emails, notificaciones, webhooks)
3. **Modelos/Schemas**: Identifica las entidades del sistema y sus relaciones
4. **Tests existentes**: Lee los archivos de test para entender que YA esta cubierto
   con tests automatizados y que NO (esto determina que necesita prueba manual)
5. **Configuracion**: Identifica servicios externos, env vars, Docker, etc.

**Si hay alcance acotado**, limita el escaneo a las carpetas/modulos que
correspondan mas sus dependencias directas. Si el alcance esta vacio, escanea
todo el proyecto.

---

### Paso 2.5: Modo de generacion (solo si el alcance abarca mas de un modulo)

**Cuando se activa.** Solo si el Paso 2 identifico **dos o mas modulos / areas
funcionales distintas**. Si todo cae en un solo modulo, salta al Paso 3 sin
preguntar.

Un "modulo" es un area funcional con su propio router/servicio/pantallas
(`invoices`, `payments`, `auth`), no una capa ni un archivo suelto. Un flujo que
cruza modulos pero es **un solo recorrido de usuario** (checkout tocando `cart`,
`payments` y `orders`) NO cuenta como multi-modulo.

**Si se paso `--separado` o `--mezclado`**, usar ese modo e informarlo en una
linea — no preguntar.

**Si no**, DEBES preguntar y **esperar la respuesta**:

```
El proyecto tiene 3 modulos con flujos probables: facturacion, pagos, auth.

¿Como genero el protocolo?

  [1] Separado — un documento por modulo:
        docs/protocolo-pruebas-aceptacion-facturacion.md
        docs/protocolo-pruebas-aceptacion-pagos.md
        docs/protocolo-pruebas-aceptacion-auth.md
      Sirve si entregas o apruebas modulo por modulo (entregas escalonadas).
      Cada uno se firma y se cierra por separado.

  [2] Mezclado (recomendado si es una sola entrega) — un documento con los
      3 modulos como PARTE 1 / PARTE 2 / PARTE 3:
        docs/protocolo-pruebas-aceptacion.md
      Una sola tabla de resumen y una sola aprobacion al final.

¿Separado o mezclado? (1/2)
```

**Como cambia cada modo:**

| Paso | `--separado` | `--mezclado` |
|---|---|---|
| Paso 3-4 | Escenarios y cobertura calculados **por modulo** | Todo junto |
| Paso 5 | Un archivo por modulo: `<base>-<modulo>.md`, cada uno con su propia tabla de resumen y su bloque de firma | Un archivo con `PARTE N` por modulo |
| Paso 6 | Tabla con una fila por modulo + ruta de cada archivo | Un bloque |

**Default si el usuario no contesta claro: `mezclado`.** Un protocolo de
aceptacion se lee y se aprueba mejor completo; separar solo tiene sentido si la
entrega es escalonada. (Es el criterio inverso a `/e2e-gen`, donde separar es lo
reversible — aca lo caro es fragmentar una aprobacion que deberia ser una sola.)

**Regla anti-explosion.** Si el alcance supera **8 modulos** en modo separado,
avisar y proponer agrupar por area de negocio o acotar el alcance. Nunca generar
15 documentos de firma sin avisar.

**Coherencia con `/checklist-cliente`.** El modo elegido aca **determina** lo que
ese comando puede producir despues: si generas separado, el de cliente sale
separado; si generas mezclado, sale un solo documento. Dilo en el resumen del
Paso 6 para que quede claro antes de armar la entrega al cliente.

---

### Paso 3: Clasificar escenarios de prueba

Agrupa los escenarios en categorias logicas. Para cada flujo del sistema, genera:

1. **Flujo feliz (happy path)**: El caso normal donde todo funciona correctamente
2. **Flujos alternativos**: Variaciones validas (ej: usuario nuevo vs existente)
3. **Pruebas negativas**: Casos de error esperados (permisos, validaciones, datos invalidos)
4. **Integraciones**: Pruebas que requieren servicios externos reales

Para cada escenario define:
- Nombre descriptivo
- Precondiciones
- Pasos exactos (con datos de ejemplo concretos, no genericos)
- Resultado esperado
- Checkbox `[ ]` para marcar pass/fail
- Campo de observaciones

---

### Paso 4: Determinar cobertura automatizada vs manual

Revisa los tests existentes del proyecto:

1. Cuenta tests por area/modulo
2. Identifica que cubren los tests automatizados (con mocks, no con servicios reales)
3. Identifica que NO esta cubierto y requiere prueba manual obligatoria:
   - Conexiones reales con APIs externas
   - Flujos end-to-end con multiples servicios
   - UI/UX si aplica
   - Timing real (crons, schedulers, timeouts)
   - Permisos y roles con datos reales

---

### Paso 5: Generar el protocolo

Determina la ruta del archivo:
- Si se paso `--out` (o `$ARGUMENTS` era una ruta), usa esa ruta como **base**
- Si no, usa `docs/protocolo-pruebas-aceptacion.md` como base
- Crea los directorios necesarios si no existen

**En modo `--separado`**, la ruta base se sufija con el modulo, derivando el
slug en minusculas, sin acentos ni `ñ`, espacios y `/` a guiones:
`docs/protocolo-pruebas-aceptacion.md` → `docs/protocolo-pruebas-aceptacion-<modulo>.md`

Cada archivo lleva la estructura completa de abajo (encabezado, instrucciones,
partes, resumen y firma) acotada **solo a su modulo** — tiene que servir suelto,
sin los otros. **Nunca sobrescribas** un archivo existente de otro alcance: si ya
existe, genera `<base>-<modulo>-YYYYMMDD-HHMMSS.md` y avisalo en el Paso 6.

Genera los modulos **de uno en uno, en orden de riesgo** (dinero, datos
personales, permisos, borrados irreversibles primero): si algo se corta a la
mitad, lo generado queda completo y utilizable.

Genera el archivo con esta estructura exacta:

```markdown
# Protocolo de Pruebas de Aceptacion

## [Nombre del Proyecto]

**Fecha**: ___/___/____
**Ejecutado por**: ____________________
**Ambiente**: Produccion / Staging (marcar)

---

## Estado de verificacion previa (tests automatizados)

> **IMPORTANTE**: Las siguientes verificaciones se realizaron con tests automatizados.
> NO son pruebas con datos reales ni con servicios externos reales.
> Confirman que la logica del codigo funciona correctamente en aislamiento,
> pero TODAS las pruebas de este protocolo deben ejecutarse manualmente
> con servicios y datos reales.

**Fecha de ultima ejecucion**: [fecha o "pendiente"]
**Resultado**: [N tests passed, N failures] o "pendiente"

| Area | Tests | Que verifican (con mocks, NO con servicios reales) |
|------|-------|---------------------------------------------------|
| [modulo] | [N] | [descripcion breve] |
| ... | ... | ... |

**Lo que NO esta cubierto por tests automatizados y requiere prueba manual obligatoria**:
- [lista de areas que necesitan prueba manual]

---

## Instrucciones Generales

- Ejecutar cada escenario en orden
- Marcar con [x] los que pasen, [ ] los que fallen
- Anotar observaciones en cada escenario
- Requisitos previos:
  - [ ] [Servicio 1 corriendo]
  - [ ] [Servicio 2 configurado]
  - [ ] [Env vars necesarias]
  - [ ] [Datos de prueba disponibles]

---

## PARTE N — [Nombre del Modulo/Flujo]

### [Codigo]: [Nombre del escenario] — Pendiente
- [ ] [Paso 1 con datos concretos]
- [ ] [Paso 2 — verificar resultado esperado]
- [ ] [Paso 3 — verificar side effect]
- **Observaciones**: ____

### [Codigo]: [Prueba negativa] — Pendiente
- [ ] [Intentar accion no permitida]
- [ ] [Verificar que retorna error apropiado]
- [ ] [Verificar que NO se modificaron datos]
- **Observaciones**: ____

---

## Resumen de Resultados

| Parte | Escenarios | Pass | Fail | Pendiente |
|-------|-----------|------|------|-----------|
| [Parte 1] | [N] | | | |
| [Parte 2] | [N] | | | |
| **Total** | **[N]** | | | |

**Aprobado por**: ____________________
**Fecha de aprobacion**: ___/___/____
**Observaciones generales**: ____
```

---

### Paso 6: Presentar resumen

Muestra al usuario:
1. **Total de escenarios** generados
2. **Escenarios por modulo** (tabla resumen)
3. **Areas que requieren prueba manual obligatoria** (no cubiertas por tests)
4. **Ruta del archivo** generado
5. **Modo usado** (`separado` / `mezclado` / modulo unico) y, si fue separado,
   la ruta de cada documento

En modo separado, el resumen va con una fila por modulo:

```
Protocolo generado (modo: separado, 3 modulos)

| Modulo      | Escenarios | Negativas | Manual obligatoria | Archivo                                        |
|-------------|-----------|-----------|--------------------|------------------------------------------------|
| facturacion | 18        | 7         | 3                  | docs/protocolo-pruebas-aceptacion-facturacion.md |
| pagos       | 14        | 6         | 5                  | docs/protocolo-pruebas-aceptacion-pagos.md       |
| auth        | 16        | 8         | 2                  | docs/protocolo-pruebas-aceptacion-auth.md        |

Total: 48 escenarios · 21 negativas · 10 requieren prueba manual obligatoria

Siguiente paso: /checklist-cliente --separado
(el modo separado se mantiene: van a salir 3 documentos de cliente, uno por modulo)
```

---

## Reglas

- NUNCA inventar funcionalidad — solo generar pruebas para lo que existe en el codigo
- **SIEMPRE preguntar separado vs mezclado (Paso 2.5)** cuando el alcance abarca
  2 o mas modulos y no se paso `--separado` ni `--mezclado` — NUNCA elegir el
  modo en silencio. Si el usuario no define, el default es `mezclado`
- **En modo separado, cada documento debe servir suelto**: encabezado, requisitos
  previos, escenarios, resumen y firma propios. Nunca un archivo que dependa de
  leer los otros para tener sentido
- **NUNCA sobrescribir** un protocolo existente de otro alcance — sufijar con
  timestamp y avisarlo
- **SIEMPRE informar el modo usado en el resumen**, porque condiciona lo que
  `/checklist-cliente` puede generar despues
- NUNCA generar pruebas genericas — cada paso debe tener datos concretos y resultados esperados
- Si el proyecto tiene tests automatizados, analizarlos y documentar que cubren
- Incluir SIEMPRE pruebas negativas (permisos, validaciones, errores)
- Incluir SIEMPRE verificacion de side effects (emails, notificaciones, logs, webhooks)
- Los codigos de escenario deben ser legibles: `A1`, `B2.3`, no UUIDs
- Agrupar por flujo/modulo, no por tipo de prueba
- Si no hay documentacion del proyecto (`CLAUDE.md` ni `README.md`), informar
  al usuario y generar el protocolo basado solo en el analisis del codigo
- Priorizar profundidad sobre velocidad — es mejor un protocolo completo que uno rapido
- El archivo generado debe ser util sin contexto adicional: cualquier persona
  debe poder ejecutar las pruebas leyendo solo el documento
