# /acceptance-checklist — Genera protocolo de pruebas de aceptacion

Analiza el codigo del proyecto actual y genera un documento Markdown completo
con checklist de pruebas de aceptacion manuales, listo para imprimir o compartir
con el cliente.

## Argumentos
- `$ARGUMENTS` — Opcional: ruta donde guardar el archivo generado.
  Default: `docs/protocolo-pruebas-aceptacion.md`
  Ejemplos: `docs/pruebas.md`, `QA/acceptance.md`

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
- Si `$ARGUMENTS` tiene valor, usa esa ruta
- Si no, usa `docs/protocolo-pruebas-aceptacion.md`
- Crea los directorios necesarios si no existen

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

---

## Reglas

- NUNCA inventar funcionalidad — solo generar pruebas para lo que existe en el codigo
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
