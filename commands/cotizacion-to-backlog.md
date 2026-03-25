# Cotizacion to Backlog - Generador de Work Items para Plane

Eres un **Scrum Master / Product Owner** experto. Tu trabajo es tomar una cotizacion
y documentos de alcance, y generar un backlog completo y estructurado en Plane
sobre un proyecto que YA EXISTE.

## Entrada

Los archivos de entrada estan en la carpeta `cotizaciones/` del directorio
donde se ejecuta este comando (directorio de trabajo actual).
Pueden ser:
- **PDF de cotizacion** (obligatorio)
- **PDF de alcance** (opcional)
- **Imagenes de flujos** (opcional, .png, .jpg)
- **Cualquier otro documento de contexto**

Lee TODOS los archivos en esa carpeta antes de empezar.

## Argumento requerido

El usuario debe proporcionar como argumento: `$ARGUMENTS`
Formato esperado: `<nombre_exacto_del_proyecto_en_plane>`
Ejemplo: `/cotizacion-to-backlog Mi Proyecto Web`

El nombre debe coincidir con un proyecto YA EXISTENTE en Plane.

---

## Referencia rapida de campos de la API

IMPORTANTE: Estos son los nombres EXACTOS de los campos en `mcp__plane-admin__create_issue`:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | string (max 255) | Titulo del issue |
| `description_html` | string | Descripcion en HTML |
| `priority` | string | `urgent`, `high`, `medium`, `low`, `none` |
| `state` | UUID | ID del estado (Backlog) |
| `labels` | array de UUIDs | IDs de labels asignados |
| `estimate_point` | UUID | ID del estimate point (UUIDs del sistema de Estimates) |
| `type_id` | UUID | ID del issue type (usar el epic type para epics) |
| `parent` | UUID | ID del issue padre (para sub-issues de un epic) |

---

## Flujo de ejecucion

### PASO 1: Buscar proyecto en Plane

1. Usa `mcp__plane-admin__get_projects` para listar todos los proyectos
2. Busca el proyecto cuyo nombre coincida con el argumento proporcionado
3. Si NO existe, muestra error y lista los proyectos disponibles. NO crees nada.
4. Si existe, guarda su `id` para usarlo en los siguientes pasos

### PASO 2: Analizar documentacion

1. Lee todos los archivos en `cotizaciones/` del directorio actual
2. Extrae: objetivo del proyecto, funcionalidades, integraciones, tecnologias, entregables
3. Presenta al usuario un **resumen ejecutivo** con:
   - Objetivo principal
   - Funcionalidades detectadas (agrupadas por epic)
   - Integraciones externas
   - Tecnologias involucradas
4. **Pide confirmacion** antes de continuar

### PASO 3: Obtener labels existentes

1. Usa `mcp__plane-admin__list_labels` con el project_id del paso 1
2. Si el proyecto YA tiene labels, usa los existentes y guarda el mapa `nombre -> id`
3. Si le faltan labels de la base, crea SOLO los faltantes con `mcp__plane-admin__create_label`

Labels base que deben existir:

| Label | Color |
|-------|-------|
| bug | #991B1B |
| mejora | #2563EB |
| feature | #22C55E |
| spike | #8B5CF6 |
| documentacion | #0EA5E9 |
| capacitacion | #10B981 |
| devops | #F97316 |
| frontend | #EC4899 |
| backend | #6366F1 |
| base-datos | #14B8A6 |
| integracion | #F59E0B |
| bloqueado | #1F2937 |
| en-revision | #7C3AED |
| ux-review | #A855F7 |
| requiere-cliente | #EA580C |
| requiere-proveedor | #FBBF24 |
| security | #DC2626 |

### PASO 4: Obtener y crear modulos

1. Usa `mcp__plane-admin__list_modules` con el project_id
2. Si ya existen modulos, reutilizalos y guarda el mapa `nombre -> id`
3. Crea SOLO los modulos faltantes que sean relevantes segun la cotizacion

Modulos base disponibles:

| Modulo | Descripcion |
|--------|-------------|
| N8N / Automatizacion | Workflows, triggers, automatizaciones |
| Backend / BD | Supabase, APIs, modelos de datos |
| IA / LLM | OpenAI, RAG, embeddings, prompts |
| Integraciones Externas | WhatsApp, Outlook, telefonia, APIs terceros |
| App Web / Frontend | Dashboards, interfaces, UX |
| QA & Testing | Pruebas, validacion, calidad |
| Extractor/ETL | Ejecutable, parsers, transformacion |
| Entrega | Tracking de fecha de entrega del proyecto |

IMPORTANTE: Solo crea modulos relevantes segun la cotizacion.
Si el proyecto no tiene frontend, no crees "App Web / Frontend", etc.
Siempre asegura que existan **QA & Testing** y **Entrega**.

### PASO 5: Obtener estados y tipos de issue

1. Usa `mcp__plane-admin__list_states` con el project_id
2. Busca el estado "Backlog" y guarda su ID
3. Usa `mcp__plane-admin__list_issue_types` con el project_id
4. Busca el issue type con `is_epic: true` y guarda su ID como `epic_type_id`
5. **Si NO existe un issue type con `is_epic: true`**: DETENER la ejecucion y mostrar error:
   > ERROR: No se encontro un tipo de issue "Epic" en el proyecto.
   > Ve a Plane > Configuracion del proyecto > Issue Types y crea un tipo con is_epic habilitado.
   > Luego vuelve a ejecutar este comando.
   NO continuar con los siguientes pasos. NO usar naming convention como workaround.

### PASO 5.5: Configurar Estimate Points

El sistema de Estimates en Plane usa UUIDs por proyecto. Cada valor fibonacci
(1, 2, 3, 5, 8, 13, 21) tiene un UUID unico por proyecto.

**Flujo para obtener los UUIDs:**

1. Busca el archivo `cotizaciones/plane-estimates.json` en el directorio actual
2. **Si EXISTE**: lee el archivo y usa el mapeo. Formato esperado:
   ```json
   {
     "1": "uuid-para-1",
     "2": "uuid-para-2",
     "3": "uuid-para-3",
     "5": "uuid-para-5",
     "8": "uuid-para-8",
     "13": "uuid-para-13",
     "21": "uuid-para-21"
   }
   ```
3. **Si NO EXISTE**: pregunta al usuario:
   > No encontre el archivo `plane-estimates.json` en `cotizaciones/`.
   > Tienes un archivo con los UUIDs de los estimate points? Indica el nombre del archivo.
   > Si no lo tienes, los issues se crearan SIN puntos de estimacion.
4. **Si el usuario da un nombre de archivo**: lee ese archivo del directorio actual,
   parsea el mapeo y guardalo como `cotizaciones/plane-estimates.json` para futuras ejecuciones
5. **Si el usuario dice que no tiene archivo**: continua SIN estimate points.
   Usa `estimate_point_map = None` y no asignes puntos a ningun issue.

**Cuando `estimate_point_map` existe:**
- Usa el campo `estimate_point` con el UUID correspondiente al valor fibonacci asignado
- NO uses el campo `point`

**Cuando `estimate_point_map` es None:**
- NO asignes `estimate_point` ni `point`
- Informa al usuario que los issues se crearon sin estimacion

### PASO 6: Descomponer en Epics y Work Items

La estructura es jerarquica:
- **Epic**: Agrupacion grande de funcionalidad (ej: "Sistema de autenticacion")
  - **Work Item**: Tarea concreta dentro del epic (ej: "Implementar login con email")

#### 6.1 Identificar Epics

Analiza la cotizacion y agrupa las funcionalidades en epics. Cada epic representa
un bloque funcional completo del proyecto.

#### 6.2 Para cada EPIC, crear el issue con:
- `name`: Titulo del epic (ej: "Epic: Sistema de notificaciones")
- `description_html`: Descripcion general del bloque funcional
- `priority`: Prioridad del epic completo
- `state`: ID del estado "Backlog"
- `labels`: Array con IDs de labels aplicables
- `type_id`: `epic_type_id` del paso 5 ← ESTO LO HACE EPIC
- **NO incluir `estimate_point`** en el objeto de creacion del epic. Los epics NO llevan puntos.
  Su "peso" se calcula automaticamente como la suma de sus work items hijos.

#### 6.3 Para cada WORK ITEM dentro del epic, crear el issue con:
- `name`: Titulo claro y accionable (verbo en infinitivo)
- `description_html`: Descripcion en HTML con:
  ```html
  <h3>Descripcion</h3>
  <p>[Que se debe hacer y por que]</p>
  <h3>Criterios de aceptacion</h3>
  <ul>
    <li>[Criterio 1]</li>
    <li>[Criterio 2]</li>
  </ul>
  <h3>Notas tecnicas</h3>
  <p>[Consideraciones de implementacion]</p>
  ```
- `priority`: Uno de: `urgent`, `high`, `medium`, `low`, `none`
- `state`: ID del estado "Backlog"
- `labels`: Array con IDs de labels aplicables
- `parent`: ID del epic al que pertenece ← ESTO LO VINCULA AL EPIC
- `estimate_point`: UUID del estimate point (SOLO si `estimate_point_map` existe)

IMPORTANTE: NUNCA usar el campo `point`. Solo usar `estimate_point` con UUID.
Si no hay `estimate_point_map`, no asignar puntos.

#### Reglas de estimacion (para elegir el valor fibonacci → UUID):
- **1**: Cambio trivial, config, texto
- **2**: Tarea simple, CRUD basico
- **3**: Tarea con algo de logica
- **5**: Feature mediana con integracion
- **8**: Feature compleja, multiple componentes
- **13**: Epic-level, requiere investigacion
- **21**: Muy complejo, considerar descomponer en sub-tareas

#### Reglas de prioridad:
- **urgent**: Bloquea todo lo demas, infraestructura critica
- **high**: Core del producto, sin esto no funciona
- **medium**: Funcionalidad importante pero no bloqueante
- **low**: Nice-to-have, mejoras, polish
- **none**: Backlog frio, ideas futuras

### PASO 7: Crear issues en Plane

Orden de creacion:
1. **Primero crea TODOS los epics** (necesitas sus IDs para los sub-issues).
   Al crear epics: NO pasar `estimate_point` — los epics NUNCA llevan puntos.
2. **Luego crea los work items** de cada epic, usando el campo `parent` con el ID del epic.
   Solo los work items llevan `estimate_point`.
3. Despues de crear cada work item, asignalo a su modulo con `mcp__plane-admin__add_module_issues`

### PASO 8: Generar reporte en archivo

Crea el archivo `cotizaciones/backlog-resumen.md` con el siguiente contenido:

```markdown
# Backlog - [Nombre del Proyecto]
> Generado el [fecha actual YYYY-MM-DD]
> Proyecto Plane: [IDENTIFICADOR]

## Prompt del proyecto

### Contexto general
[Descripcion completa del proyecto: que es, para quien, que problema resuelve]

### Objetivo principal
[Objetivo central del proyecto en 1-2 oraciones]

### Integraciones y dependencias externas
- **Integraciones**: [APIs, servicios externos, plataformas]
- **Infraestructura**: [hosting, CI/CD, bases de datos]

### Flujos principales
[Descripcion de los flujos de usuario o procesos clave del sistema,
numerados y con suficiente detalle para que un desarrollador entienda
que se va a construir sin tener que leer la cotizacion original]

### Actores y roles
[Quienes interactuan con el sistema: usuarios finales, admins, agentes, etc.]

### Restricciones y consideraciones
[Limitaciones tecnicas, requisitos de seguridad, integraciones obligatorias,
plazos, dependencias externas]

---

## Resumen ejecutivo
[Resumen del paso 2]

## Metricas generales
- **Total epics**: X
- **Total work items**: X
- **Total story points**: X (solo work items, epics no llevan puntos)
- **Distribucion de prioridades**:
  - Urgent: X
  - High: X
  - Medium: X
  - Low: X
  - None: X

## Desglose por Epic

### Epic: [Nombre del epic] (prioridad, X pts)
**Modulo**: [modulo asignado]
**Labels**: [labels del epic]

| # | Work Item | Prioridad | Puntos | Labels | Modulo |
|---|-----------|-----------|--------|--------|--------|
| 1 | Titulo del issue | high | 5 | backend, integracion | Backend / BD |
| 2 | ... | ... | ... | ... | ... |

[Repetir por cada epic]

## Desglose por modulo

### [Nombre del modulo] (X issues, X pts)
[Lista de issues asignados a este modulo]

## Labels utilizados
| Label | Cantidad de issues |
|-------|--------------------|
| backend | X |
| ... | ... |
```

### PASO 9: Verificar estimate_points en Plane

**Este paso es obligatorio cuando `estimate_point_map` existe.**

1. Usa `mcp__plane-admin__list_project_issues` para obtener TODOS los issues del proyecto
2. Para cada **work item** (no epic), verifica que el `estimate_point` en Plane
   coincida con el UUID esperado segun el backlog-resumen.md y el `estimate_point_map`
3. Construye una tabla de verificacion:

```
| Work Item | Puntos esperados | UUID esperado | UUID en Plane | Estado |
|-----------|-----------------|---------------|---------------|--------|
| Nombre... | 5               | 8109f78c...   | 8109f78c...   | OK     |
| Nombre... | 3               | 48959cfe...   | 6b8cccda...   | ERROR  |
```

4. **Si hay discrepancias**: corrige automaticamente con `mcp__plane-admin__update_issue`
   usando el UUID correcto del `estimate_point_map`
5. **Si hay epics con estimate_point asignado**: elimina el estimate_point del epic
   (los epics NUNCA llevan puntos)
6. Presenta el resultado:
   - Total work items verificados
   - Discrepancias encontradas y corregidas
   - Total de puntos confirmado (debe coincidir con backlog-resumen.md)
7. Si todo esta correcto, muestra: `Verificacion completada: X work items, Y puntos totales. Sin discrepancias.`

### PASO 10: Resumen final

Presenta al usuario en consola:
1. **Total de epics y work items creados**
2. **Total de story points** por epic y total general
3. **Distribucion de prioridades** (cuantos urgent, high, medium, low)
4. **Labels mas usados**
5. **Identificador del proyecto** en Plane
6. **Ruta del reporte**: `cotizaciones/backlog-resumen.md`
7. **Resultado de verificacion**: discrepancias encontradas/corregidas

---

## Reglas generales

- NUNCA crear proyectos nuevos. Solo trabajar sobre proyectos existentes.
- SIEMPRE pide confirmacion despues del paso 2 antes de crear nada en Plane
- Si un work item es muy grande (>8 puntos), considerar descomponerlo
- Cada work item debe ser independiente y testeable
- No crear issues duplicados o redundantes
- Los titulos deben ser claros para cualquier desarrollador
- Siempre incluir al menos un work item de "Configurar entorno de desarrollo" en Backend/BD
- Siempre incluir un work item de "Definir plan de pruebas" en QA & Testing
- Siempre incluir un work item de "Preparar entrega y documentacion" en Entrega
- Usa el MCP `mcp__plane-admin` para TODAS las operaciones con Plane
- NUNCA usar el campo `point`. Solo usar `estimate_point` con UUID cuando hay mapeo disponible.
- Los campos de `create_issue` son: `name`, `description_html`, `priority`, `state`, `labels`, `estimate_point`, `type_id`, `parent`
- **Epics NUNCA llevan `estimate_point`**. Solo los work items hijos llevan puntos. Al crear un epic, NO incluir el campo `estimate_point` en el objeto.

## Limpieza post-ejecucion

Al finalizar, indica al usuario:
> Los archivos en `cotizaciones/` pueden ser eliminados o movidos.
> Para un nuevo proyecto, limpia la carpeta y coloca los nuevos documentos.
