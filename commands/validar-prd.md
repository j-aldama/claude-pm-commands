# Validar PRD contra Plane

Valida que todos los items de un archivo `prd.json` tengan su contraparte
como issues en un proyecto de Plane. Detecta discrepancias y permite crear
los items faltantes.

## Argumentos

El usuario debe proporcionar: `$ARGUMENTS`
Formato: `<nombre_exacto_del_proyecto_en_plane>`
Ejemplo: `/validar-prd Mi Proyecto Web`

## Entrada

El archivo `prd.json` debe estar en el directorio de trabajo actual o
en la subcarpeta del proyecto. Buscar en este orden:
1. `./prd.json`
2. `./docs/prd.json`
3. Preguntar al usuario la ruta

## Estructura esperada del PRD

```json
{
  "project": "string",
  "identifier": "string",
  "description": "string",
  "userStories": [
    {
      "id": "IDENT-001",
      "title": "string",
      "description": "string",
      "acceptanceCriteria": ["string"],
      "storyPoints": number,
      "priority": number,
      "domain": "string",
      "passes": boolean,
      "dependencies": ["IDENT-001"]
    }
  ]
}
```

## Referencia de campos de la API

Campos EXACTOS de `mcp__plane-admin__create_issue`:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `name` | string (max 255) | Titulo del issue |
| `description_html` | string | Descripcion en HTML |
| `priority` | string | `urgent`, `high`, `medium`, `low`, `none` |
| `state` | UUID | ID del estado (Backlog) |
| `labels` | array de UUIDs | IDs de labels asignados |
| `estimate_point` | UUID | ID del estimate point |
| `type_id` | UUID | ID del issue type (epic) |
| `parent` | UUID | ID del issue padre |

IMPORTANTE: NUNCA usar el campo `point`. Solo usar `estimate_point` con UUID.

---

## Flujo de ejecucion

### PASO 1: Buscar proyecto en Plane

1. Usa `mcp__plane-admin__get_projects` para listar todos los proyectos
2. Busca el proyecto cuyo nombre coincida con el argumento proporcionado
3. Si NO existe, muestra error y lista los proyectos disponibles. NO hagas nada mas.
4. Si existe, guarda su `id` y su `identifier`

### PASO 2: Leer el PRD

1. Busca `prd.json` en el orden indicado arriba
2. Parsea el JSON y extrae `userStories`
3. Muestra resumen: total stories, por dominio, total puntos

### PASO 3: Obtener issues existentes de Plane

1. Usa `mcp__plane-admin__list_project_issues` con el project_id
2. Para cada issue que necesite mas detalle, usa `mcp__plane-admin__get_issue_using_readable_identifier`
3. Construye una lista de issues con: id, name, state, priority, estimate_point, labels, parent

### PASO 4: Obtener configuracion del proyecto

1. Usa `mcp__plane-admin__list_labels` → mapa `nombre -> id`
2. Usa `mcp__plane-admin__list_modules` → mapa `nombre -> id`
3. Usa `mcp__plane-admin__list_states` → obtener ID de "Backlog"
4. Usa `mcp__plane-admin__list_issue_types` → obtener `epic_type_id`

### PASO 5: Configurar Estimate Points

1. Busca `plane-estimates.json` en el directorio actual o en `cotizaciones/`
2. Si existe, lee el mapeo UUID fibonacci
3. Si no existe, pregunta al usuario por el archivo
4. Si no tiene archivo, continua sin estimaciones

### PASO 6: Comparar PRD vs Plane

Para cada `userStory` en el PRD, buscar un issue en Plane que coincida.
Criterios de match (en orden de prioridad):
1. **Match exacto por titulo** (name == title)
2. **Match parcial por titulo** (el titulo del PRD esta contenido en el name del issue o viceversa)
3. **Match por ID** (el id del PRD como "DASH-001" coincide con el sequence_id del issue)

Clasificar cada story en una de estas categorias:

| Estado | Significado |
|--------|-------------|
| `MATCH` | Story del PRD tiene issue correspondiente en Plane |
| `FALTANTE_EN_PLANE` | Story existe en PRD pero no en Plane |
| `SOLO_EN_PLANE` | Issue existe en Plane pero no en PRD |

### PASO 7: Presentar reporte de comparacion

Muestra al usuario una tabla clara:

```
## Resultado de validacion

### Stories con match (X de Y)
| PRD ID | PRD Title | Plane Issue | Estado Plane |
|--------|-----------|-------------|--------------|
| PROJ-001 | Crear modelo de usuarios... | MYAPP-15 | Backlog |

### Stories faltantes en Plane (X)
| PRD ID | Title | Puntos | Dominio |
|--------|-------|--------|---------|
| PROJ-003 | Servicio de notificaciones... | 3 | backend |

### Issues solo en Plane (sin contraparte en PRD) (X)
| Issue | Title | Estado |
|-------|-------|--------|
| MYAPP-50 | Configurar CI/CD... | In Progress |
```

### PASO 8: Resolver faltantes

Para CADA story marcada como `FALTANTE_EN_PLANE`, preguntar al usuario:

> **PROJ-003**: "Servicio de notificaciones push"
> Dominio: backend | Puntos: 3 | Prioridad: 2
>
> Esta story no tiene issue en Plane. Que deseas hacer?
> 1. Crear issue en Plane
> 2. Ignorar (no es necesario)
> 3. Ya existe pero con otro nombre (vincular manualmente)

**Si elige "Crear":**

Crear el issue con `mcp__plane-admin__create_issue`:
- `name`: title del PRD
- `description_html`: Convertir description + acceptanceCriteria a HTML:
  ```html
  <h3>Descripcion</h3>
  <p>[description del PRD]</p>
  <h3>Criterios de aceptacion</h3>
  <ul>
    <li>[criterio 1]</li>
    <li>[criterio 2]</li>
  </ul>
  <h3>Dependencias</h3>
  <p>[lista de dependencias del PRD]</p>
  ```
- `priority`: Mapear priority numerico del PRD:
  - 1 → `urgent`
  - 2 → `high`
  - 3 → `medium`
  - 4 → `low`
  - 5 → `none`
- `state`: ID del estado "Backlog"
- `labels`: Mapear domain del PRD a labels:
  - `backend` → label "backend"
  - `frontend` → label "frontend"
  - `qa` → label existente o crear si no existe
  - `devops` → label "devops"
  - Agregar label "feature" a todos
- `estimate_point`: Si hay mapeo, usar UUID correspondiente a storyPoints del PRD
- Asignar al modulo correspondiente segun domain:
  - `backend` → "Backend / BD"
  - `frontend` → "App Web / Frontend"
  - `qa` → "QA & Testing"

**Si elige "Ya existe con otro nombre":**

Pedir al usuario el identificador del issue en Plane (ej: "MYAPP-50") y
registrar la vinculacion en el reporte.

### PASO 9: Resolver issues solo en Plane

Para cada issue que existe en Plane pero NO en el PRD, informar al usuario:

> **MYAPP-50**: "Tarea de configuracion extra"
> Este issue existe en Plane pero no tiene contraparte en el PRD.
> Puede ser una tarea operativa, de soporte, o algo que falta en el PRD.

No crear ni eliminar nada. Solo informar.

### PASO 10: Resumen final en consola

Presenta al usuario:
1. Total de matches encontrados
2. Total de issues creados
3. Total de items ignorados
4. Total de issues solo en Plane

NO generar ningun archivo de reporte. Todo se muestra en consola.

---

## Reglas generales

- NUNCA eliminar issues de Plane
- NUNCA modificar issues existentes de Plane
- Solo CREAR issues nuevos cuando el usuario lo apruebe explicitamente
- Preguntar uno por uno los items faltantes, no crear en lote
- Usa el MCP `mcp__plane-admin` para TODAS las operaciones con Plane
- NUNCA usar el campo `point`. Solo usar `estimate_point` con UUID cuando hay mapeo disponible.
