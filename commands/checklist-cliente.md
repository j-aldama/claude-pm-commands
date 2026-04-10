# /checklist-cliente — Genera checklist de pruebas para el cliente

Genera un documento Markdown limpio y profesional con checklist de pruebas
de aceptacion, listo para imprimir como PDF y entregar al cliente para firma.

Si ya existe un protocolo tecnico (`docs/protocolo-pruebas-aceptacion.md` o
`docs/checklist.md`), lo transforma quitando secciones tecnicas.
Si no existe, lo genera desde cero analizando el codigo.

## Argumentos
- `$ARGUMENTS` — Opcional: ruta donde guardar el archivo.
  Default: `docs/checklist-cliente.md`

## Instructions

Eres un QA Lead que prepara documentos de entrega para clientes no tecnicos.
El documento debe ser claro, profesional y ejecutable por alguien que no
conoce el codigo ni la arquitectura del sistema.

---

### Paso 1: Buscar protocolo tecnico existente

Busca en este orden:
1. `docs/protocolo-pruebas-aceptacion.md`
2. `docs/checklist.md`
3. Cualquier `*.md` en `docs/` que contenga "pruebas de aceptacion" o "acceptance"

**Si encuentras uno**: leelo completo y ve al Paso 3 (transformar).
**Si NO encuentras ninguno**: ve al Paso 2 (generar desde cero).

---

### Paso 2: Generar desde cero (solo si no existe protocolo tecnico)

1. Lee `CLAUDE.md`, `README.md` y documentacion en `docs/`
2. Escanea endpoints, servicios, flujos de usuario y modelos
3. Identifica los flujos principales del sistema
4. Para cada flujo genera escenarios con:
   - Nombre descriptivo simple (sin jerga tecnica)
   - Pasos concretos que el cliente pueda ejecutar
   - Checkboxes `[ ]` para marcar
   - Campo de observaciones con espacio

---

### Paso 3: Transformar a version cliente

Toma el protocolo tecnico y aplica TODAS estas transformaciones:

#### QUITAR (contenido tecnico):
- Seccion "Estado de verificacion previa (tests automatizados)" completa
- Seccion "Instrucciones Generales" con requisitos previos
- Seccion "Criterios de Aprobacion" (bloqueantes, importantes, deseables)
- Seccion "Resumen de resultados" con tabla de totales
- Seccion "Resultados E2E automatizados" y logs conversacionales
- Campo "Ejecutado por"
- Campo "Ambiente: Produccion / Staging"
- Puerto de la app
- Marcas de E2E: quitar "— ✅ N/N E2E PASS YYYY-MM-DD" de todos los titulos
- Marcas de E2E: quitar "— ✅ E2E PASS YYYY-MM-DD" de todos los subtitulos
- Marcas de pendiente: quitar "— ⏳ Requiere prueba manual (...)"
- Todas las referencias a rutas de API (`GET /api/...`, `POST /api/...`, endpoints)
- Todas las referencias a Docker, Redis, pytest, mocks, env vars
- Todas las referencias a estados internos (IDLE, ESCALATED, SCHEDULING, etc.)
- Todas las referencias a nombres de archivos de codigo (`.py`, `.js`, etc.)

#### MODIFICAR:
- **Observaciones**: reemplazar `- **Observaciones**: ____` por:
  ```
  - **Observaciones**:<br><br><br>
  ```
  Los `<br>` generan espacio visible para escribir en el PDF impreso.

- **Lenguaje**: simplificar jerga tecnica a lenguaje que el cliente entienda:
  - "webhook" → "notificacion"
  - "endpoint" → (quitar, no mencionar)
  - "estado ESCALATED" → "conversacion transferida"
  - "estado IDLE" → "conversacion reiniciada"
  - "parse" → "reconocer" o "interpretar"
  - "mock" → (no debe aparecer)
  - "caption" → "texto" o "descripcion"

- **Notas de escenarios**: las notas tipo "> Nota: requiere..." se mantienen
  pero simplificadas (sin mencionar schedulers, TTL, cache Redis).

#### FIRMA:
Reemplazar cualquier tabla de firma o "Aprobado por" con este formato exacto:

```markdown
## Firma de Aceptacion

**Nombre**: _______________________________________________

**Firma**: _______________________________________________

**Fecha**: _______________________________________________
```

Solo para el cliente. Sin roles de desarrollador ni QA.

#### ENCABEZADO:
```markdown
# Protocolo de Pruebas de Aceptacion

## [Nombre del proyecto/cliente]

**Fecha**: ___/___/____

---
```

Sin "Ejecutado por", sin "Ambiente", sin puerto.

---

### Paso 4: Escribir el archivo

1. Determina la ruta:
   - Si `$ARGUMENTS` tiene valor, usa esa ruta
   - Si no, usa `docs/checklist-cliente.md`
2. Escribe el archivo Markdown

---

### Paso 5: Generar PDF

Ejecuta:
```bash
npx md-to-pdf [ruta-del-archivo]
```

Si falla, informa al usuario que instale: `npm install -g md-to-pdf`

---

### Paso 6: Presentar resumen

Muestra:
1. Ruta del archivo MD generado
2. Ruta del PDF generado
3. Total de escenarios
4. Si se genero desde protocolo tecnico o desde cero

---

## Reglas

- NUNCA incluir jerga tecnica: sin endpoints, sin Docker, sin Redis, sin pytest
- NUNCA incluir secciones de tests automatizados ni resultados E2E
- NUNCA incluir criterios de aprobacion tecnicos ni tablas de resumen
- NUNCA usar tabla para la firma — solo lineas con guiones bajos
- SIEMPRE dejar espacio en observaciones con `<br><br><br>`
- SIEMPRE simplificar el lenguaje para un cliente no tecnico
- La firma es SOLO para el cliente (sin desarrollador, sin QA)
- El documento debe ser util para alguien que NUNCA ha visto el codigo
- Si el protocolo tecnico tiene bugs reportados en observaciones, incluirlos
  como nota pero sin detalles tecnicos de la causa
