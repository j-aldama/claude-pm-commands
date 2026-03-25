# /audit-scope — Gap Analysis: Spec vs Codigo

Compara documentos de especificacion (cotizacion, PRD, diagramas) contra el codigo
actual para detectar funcionalidad faltante, parcial y scope creep.

## Argumentos
- `$ARGUMENTS` — Opcional: ruta a la carpeta con documentos de spec.
  Default: `cotizaciones/`
  Ejemplos: `cotizaciones`, `docs/specs`, `requirements/`

## Instrucciones

Eres un auditor de scope. Tu trabajo es cruzar lo que dice la especificacion contra
lo que realmente existe en el codigo. Se preciso: cita archivos y funciones para
cada hallazgo.

---

### Paso 1: Leer especificacion

1. Determina la carpeta de documentos:
   - Si `$ARGUMENTS` tiene valor, usa esa ruta
   - Si no, usa `cotizaciones/`
2. Lee TODOS los archivos de esa carpeta:
   - **PDFs**: cotizaciones, alcances, propuestas
   - **Imagenes**: diagramas de flujo, wireframes, mockups (.png, .jpg, .svg)
   - **Markdown/texto**: specs, notas, requisitos
3. Extrae una lista estructurada de:
   - **Funcionalidades** descritas (cada feature o capacidad del sistema)
   - **Flujos de usuario** (pasos que el usuario sigue)
   - **Integraciones** externas mencionadas (APIs, servicios, plataformas)
   - **Entregables** explicitamente listados
   - **Restricciones** o requisitos no funcionales (seguridad, performance, etc.)

4. Presenta al usuario un resumen de lo que encontraste en la spec.
   Pide confirmacion antes de continuar con el escaneo del codigo.

---

### Paso 2: Escanear codebase

Analiza el proyecto actual de forma sistematica:

1. **Estructura del proyecto**: Lee la estructura de directorios principal
2. **Modelos/Schema**: Busca definiciones de datos (models.py, schema.prisma, types, etc.)
3. **Endpoints/Rutas**: Busca URLs, routers, controllers, views
4. **Logica de negocio**: Busca services, utils, helpers con logica relevante
5. **Templates/Componentes**: Busca UI (templates, components, pages)
6. **Tests**: Busca cobertura de tests existente
7. **Integraciones**: Busca imports/configs de servicios externos (SDKs, API clients)
8. **Configuracion**: Busca env vars referenciadas, configs de deploy

NO leas archivos de dependencias (node_modules, venv, migrations autogeneradas).
Enfocate en codigo escrito por el equipo.

---

### Paso 3: Mapeo cruzado

Para CADA funcionalidad extraida de la spec:

1. Busca en el codigo evidencia de implementacion
2. Clasifica el estado:

| Estado | Criterio | Icono |
|--------|----------|-------|
| **Implementado** | Codigo completo que cubre la funcionalidad descrita | OK |
| **Parcial** | Existe codigo relacionado pero incompleto (stubs, TODOs, logica faltante) | PARCIAL |
| **No iniciado** | No hay codigo que implemente esta funcionalidad | FALTA |
| **Ambiguo** | Hay codigo que podria estar relacionado pero no es claro | REVISAR |

3. Para cada item, documenta la **evidencia**:
   - **Implementado**: archivos y funciones que lo implementan
   - **Parcial**: que existe y que falta especificamente
   - **No iniciado**: donde deberia vivir segun la estructura del proyecto
   - **Ambiguo**: que encontraste y por que no es claro

---

### Paso 4: Detectar scope creep

Busca funcionalidad en el codigo que NO aparece en la spec:

1. Revisa endpoints, modelos, y features que no mapean a ningun item de la spec
2. Ignora: infraestructura standard (auth basica, logging, error handling, CI/CD)
3. Reporta como **EXTRA** todo lo que sea logica de negocio o features no especificadas
4. Para cada item extra, indica:
   - Que hace
   - Donde vive (archivos)
   - Posible justificacion (fue un requisito implicito? es tech debt?)

---

### Paso 5: Generar reporte

Crea el archivo `[carpeta_spec]/audit-scope.md` con esta estructura:

```markdown
# Auditoria de Scope — [Nombre del Proyecto]
> Generado: [YYYY-MM-DD]
> Spec: [carpeta_spec]/
> Codebase: [directorio actual]

## Resumen ejecutivo

- **Cobertura general**: X/Y funcionalidades implementadas (Z%)
- **Parciales**: N items requieren trabajo adicional
- **No iniciados**: N items sin implementacion
- **Scope creep**: N items fuera de spec detectados

## Funcionalidades de la spec

### Implementadas (X)

| # | Funcionalidad | Evidencia (archivos) | Notas |
|---|--------------|---------------------|-------|
| 1 | [nombre] | `app/models.py:15`, `app/views.py:42` | Completo |

### Parcialmente implementadas (X)

| # | Funcionalidad | Lo que existe | Lo que falta |
|---|--------------|--------------|-------------|
| 1 | [nombre] | `app/models.py:15` — modelo existe | Falta: endpoint de API, validacion, tests |

### No iniciadas (X)

| # | Funcionalidad | Prioridad estimada | Donde deberia vivir |
|---|--------------|-------------------|-------------------|
| 1 | [nombre] | Alta — core del producto | `app/[modulo]/` |

### Ambiguas (X)

| # | Funcionalidad | Codigo encontrado | Duda |
|---|--------------|------------------|------|
| 1 | [nombre] | `app/utils.py:30` | No es claro si cubre el requisito X |

## Scope creep (funcionalidad fuera de spec)

| # | Que hace | Archivos | Justificacion probable |
|---|---------|---------|----------------------|
| 1 | [descripcion] | `app/extra.py` | Posible requisito implicito |

## Integraciones

| Integracion (spec) | Estado | Evidencia |
|-------------------|--------|-----------|
| [API/servicio] | Implementado / Parcial / No iniciado | [archivos] |

## Metricas

| Metrica | Valor |
|---------|-------|
| Total funcionalidades en spec | X |
| Implementadas | X (Y%) |
| Parciales | X (Y%) |
| No iniciadas | X (Y%) |
| Scope creep detectado | X items |
| Archivos de codigo analizados | X |

## Recomendaciones

### Proximos pasos (priorizado)
1. [Funcionalidad no iniciada mas critica] — Prioridad alta porque [razon]
2. [Parcial que necesita completarse] — Falta [detalle]
3. ...

### Scope creep a revisar con cliente
1. [Item extra] — Confirmar si es requisito o eliminarlo

### Riesgos
- [Riesgo identificado durante el analisis]
```

---

### Paso 6: Presentar resumen

Muestra al usuario en consola:
1. **Cobertura**: X/Y funcionalidades (Z%)
2. **Top 3 faltantes** mas criticos
3. **Scope creep** si hay
4. **Ruta del reporte**: `[carpeta_spec]/audit-scope.md`

---

## Reglas

- NUNCA modificar codigo ni la spec — este comando es de solo lectura y analisis
- Ser conservador al clasificar: si no es 100% claro que esta implementado, marcar como parcial
- No contar infraestructura standard como scope creep (auth, logging, CI/CD, error handling)
- Si la spec es ambigua en algun punto, clasificar como "Ambiguo" y explicar la duda
- Si no hay carpeta de spec o esta vacia, mostrar error claro y sugerir:
  > No se encontraron documentos en `[ruta]`.
  > Coloca la cotizacion, diagramas o specs en esa carpeta y vuelve a ejecutar.
- Priorizar profundidad sobre velocidad — es mejor un analisis completo que uno rapido
