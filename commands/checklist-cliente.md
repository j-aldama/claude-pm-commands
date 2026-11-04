# /checklist-cliente — Genera checklist de pruebas para el cliente

Genera un documento Markdown limpio y profesional con checklist de pruebas
de aceptacion, listo para imprimir como PDF y entregar al cliente para firma.

Si ya existe un protocolo tecnico (`docs/protocolo-pruebas-aceptacion.md` o
`docs/checklist.md`), lo transforma quitando secciones tecnicas.
Si no existe, lo genera desde cero analizando el codigo.

## Argumentos
- `$ARGUMENTS` — Opcional: **alcance** a cubrir (modulo, lista de modulos
  separados por coma) y/o flags. Si esta vacio, cubre todo lo que encuentre.
  Ejemplos:
  - `/checklist-cliente`
  - `/checklist-cliente "facturacion, pagos"`
  - `/checklist-cliente --separado`
  - `/checklist-cliente --out entregables/aceptacion.md`

**Compatibilidad con el uso anterior**: si `$ARGUMENTS` es una sola cosa que
**parece una ruta de archivo** (termina en `.md` o contiene `/`), se interpreta
como ruta de salida, igual que antes — no como alcance.

### Flags
- `--out <ruta>` — ruta o carpeta de salida (default: `docs/checklist-cliente.md`)
- `--separado` — un documento firmable **por modulo**
- `--mezclado` — **un solo documento** con todos los modulos y una sola firma

## Instructions

Eres un QA Lead que prepara documentos de entrega para clientes no tecnicos.
El documento debe ser claro, profesional y ejecutable por alguien que no
conoce el codigo ni la arquitectura del sistema.

---

### Paso 1: Buscar protocolo tecnico existente

Busca en este orden:
1. `docs/protocolo-pruebas-aceptacion.md`
2. `docs/protocolo-pruebas-aceptacion-*.md` (varios, uno por modulo)
3. `docs/checklist.md`
4. Cualquier `*.md` en `docs/` que contenga "pruebas de aceptacion" o "acceptance"

**Si encuentras uno**: leelo completo y ve al Paso 1.5.
**Si encuentras VARIOS con sufijo de modulo**: leelos todos y ve al Paso 1.5.
**Si NO encuentras ninguno**: ve al Paso 2 (generar desde cero).

---

### Paso 1.5: Modo de generacion

Este comando **hereda** la decision que ya se tomo en `/acceptance-checklist`
cuando puede, y solo pregunta cuando no hay una decision previa que respetar.

**Caso A — encontraste varios protocolos con sufijo de modulo**
(`protocolo-pruebas-aceptacion-facturacion.md`, `-pagos.md`, ...):
el modo separado **ya fue decidido**. No preguntes. Genera un documento de
cliente por cada protocolo encontrado, informalo en una linea y sigue al Paso 3.

```
Encontre 3 protocolos tecnicos por modulo → genero 3 documentos de cliente
(facturacion, pagos, auth), uno firmable por separado.
```

**Caso B — encontraste un solo protocolo que cubre varios modulos**
(tiene `PARTE 1 — X`, `PARTE 2 — Y`, ...) **o** vas a generar desde cero con un
alcance de 2+ modulos: aca si hay decision que tomar. Si se paso `--separado` o
`--mezclado`, usalo. Si no, DEBES preguntar y **esperar la respuesta**:

```
El protocolo cubre 3 modulos: facturacion, pagos, auth.

¿Como armo el documento para el cliente?

  [1] Separado — un documento firmable por modulo:
        docs/checklist-cliente-facturacion.md  (+ .pdf)
        docs/checklist-cliente-pagos.md        (+ .pdf)
        docs/checklist-cliente-auth.md         (+ .pdf)
      Cada modulo se acepta y se firma por separado. Sirve para entregas
      escalonadas: el cliente puede aprobar facturacion aunque pagos siga
      en revision.

  [2] Mezclado — un solo documento con una sola firma al final:
        docs/checklist-cliente.md              (+ .pdf)
      Una firma cubre los 3 modulos. Sirve para una entrega unica.

¿Separado o mezclado? (1/2)
```

**Default si el usuario no contesta claro: `separado`.** En un documento que se
firma, la firma unica es la opcion irreversible: si el cliente objeta un modulo,
un documento mezclado bloquea la aceptacion de los otros dos. Separado siempre
se puede presentar junto; mezclado no se puede partir despues de firmado.

**Si el alcance supera 8 modulos en modo separado**, avisar y proponer agrupar
por area de negocio — 15 documentos de firma no son una entrega, son un problema.

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

1. Determina la ruta base:
   - Si se paso `--out` (o `$ARGUMENTS` era una ruta), usa esa
   - Si no, usa `docs/checklist-cliente.md`
2. Escribe el archivo Markdown

**En modo separado**, la ruta base se sufija con el modulo (slug en minusculas,
sin acentos ni `ñ`, espacios y `/` a guiones):
`docs/checklist-cliente.md` → `docs/checklist-cliente-<modulo>.md`

Cada documento lleva **su propio encabezado y su propio bloque de firma** y
cubre solo su modulo. El encabezado nombra el modulo para que el cliente sepa
que esta firmando:

```markdown
# Protocolo de Pruebas de Aceptacion

## [Nombre del proyecto/cliente] — Facturacion

**Fecha**: ___/___/____
```

Reglas del modo separado:
- **Una firma por documento** — nunca una firma compartida entre modulos.
- Cada documento debe entenderse **suelto**: el cliente recibe uno solo y tiene
  que poder ejecutarlo sin los otros.
- **Nunca sobrescribir** un documento existente de otro alcance: sufijar con
  `-YYYYMMDD-HHMMSS` y avisarlo en el Paso 6.

---

### Paso 5: Generar PDF

Ejecuta, **por cada archivo Markdown generado**:
```bash
npx md-to-pdf [ruta-del-archivo]
```

Si falla, informa al usuario que instale: `npm install -g md-to-pdf`

En modo separado, si el PDF de un modulo falla, **sigue con los demas** y
reporta cual quedo sin PDF — no abortes la tanda completa.

---

### Paso 6: Presentar resumen

Muestra:
1. Ruta del archivo MD generado
2. Ruta del PDF generado
3. Total de escenarios
4. Si se genero desde protocolo tecnico o desde cero
5. **Modo usado** (`separado` / `mezclado` / modulo unico), y si fue heredado de
   los protocolos tecnicos encontrados o elegido en el momento

En modo separado, una fila por modulo:

```
Documentos de cliente generados (modo: separado, heredado de 3 protocolos tecnicos)

| Modulo      | Escenarios | Markdown                              | PDF   |
|-------------|-----------|---------------------------------------|-------|
| facturacion | 18        | docs/checklist-cliente-facturacion.md | ✓     |
| pagos       | 14        | docs/checklist-cliente-pagos.md       | ✓     |
| auth        | 16        | docs/checklist-cliente-auth.md        | ✓     |

Total: 48 escenarios en 3 documentos, cada uno con su firma independiente.
```

---

## Reglas

- NUNCA incluir jerga tecnica: sin endpoints, sin Docker, sin Redis, sin pytest
- NUNCA incluir secciones de tests automatizados ni resultados E2E
- NUNCA incluir criterios de aprobacion tecnicos ni tablas de resumen
- NUNCA usar tabla para la firma — solo lineas con guiones bajos
- **SIEMPRE respetar la separacion que ya traen los protocolos tecnicos**: si hay
  varios `protocolo-pruebas-aceptacion-<modulo>.md`, salen varios documentos de
  cliente. No consolidarlos en uno sin preguntar
- **SIEMPRE preguntar separado vs mezclado (Paso 1.5)** cuando el alcance abarca
  2 o mas modulos y no hay decision previa que heredar — NUNCA elegir en
  silencio. Si el usuario no define, el default es `separado`
- **UNA firma por documento** — nunca una firma que cubra modulos que el cliente
  podria querer aceptar por separado
- **NUNCA sobrescribir** un documento de cliente existente de otro alcance
- SIEMPRE dejar espacio en observaciones con `<br><br><br>`
- SIEMPRE simplificar el lenguaje para un cliente no tecnico
- La firma es SOLO para el cliente (sin desarrollador, sin QA)
- El documento debe ser util para alguien que NUNCA ha visto el codigo
- Si el protocolo tecnico tiene bugs reportados en observaciones, incluirlos
  como nota pero sin detalles tecnicos de la causa
