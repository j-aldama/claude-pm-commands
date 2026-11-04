---
name: diseno-ui
description: "Usar cuando se pide diseñar, revisar, criticar, pulir, endurecer o ajustar una interfaz web: pantallas, paneles de operación, formularios, landing pages o componentes. Aplica a revisiones de UX antes de entregar, jerarquía, composición, tipografía, color, movimiento, textos de interfaz, estados vacíos, de error o de carga, casos extremos, y a documentar el sistema visual en DESIGN.md. Palabras clave: critique, polish, harden, UI review, UX, se ve genérica, se ve recargada, hazla más sobria, más audaz, qué le arreglo a esta pantalla."
argument-hint: "[critica | pulir | endurecer | textos | primer-uso | audaz | sobrio | destilar | tipografia | composicion | color | movimiento | documentar] [pantalla o componente]"
license: "Adaptado de pbakaus/impeccable (Apache 2.0). Ver NOTICE.md"
---

# Diseño de interfaces

Decide por el **tipo de pantalla**, verifica sobre **lo renderizado** y respeta **lo que ya existe** (marca, `DESIGN.md`, reglas del proyecto).

## Antes de empezar

1. Lee las reglas del proyecto: su `CLAUDE.md`, su `DESIGN.md` si existe y cualquier regla de interfaz que tenga. Mandan sobre esta skill.
2. Clasifica la pantalla (Operar, Leer, Persuadir o Exhibir) con [referencia/modos.md](referencia/modos.md). Se clasifica la pantalla, no el producto.
3. Carga solo la referencia del comando que toca (tabla de abajo).
4. Antes de editar cualquier interfaz, lee [referencia/piso-calidad.md](referencia/piso-calidad.md).
5. Si estamos en planeación, los comandos que editan entregan el plan de cambios y se detienen hasta la frase de arranque.

## Comandos

| Comando | Alias | Para qué | Referencia | ¿Edita? |
|---|---|---|---|---|
| `critica` | critique | Revisión de UX con puntaje, prioridades P0–P3 y preguntas | [critica.md](referencia/critica.md) | No |
| `pulir` | polish | Pasada final antes de entregar | [pulir.md](referencia/pulir.md) | Sí |
| `endurecer` | harden | Errores, textos largos, vacíos, permisos, doble envío | [endurecer.md](referencia/endurecer.md) | Sí |
| `textos` | clarify | Reescribir etiquetas, errores y ayudas | [textos.md](referencia/textos.md) | Sí |
| `primer-uso` | onboard | Primera vez y estados vacíos | [primer-uso.md](referencia/primer-uso.md) | Sí |
| `audaz`, `sobrio`, `destilar` | bolder, quieter, distill | Subir o bajar intensidad, o quitar lo que sobra | [intensidad.md](referencia/intensidad.md) | Sí |
| `tipografia` | typeset | Jerarquía y escala de texto | [tipografia.md](referencia/tipografia.md) | Sí |
| `composicion` | layout | Orden de lectura, agrupación, ritmo, densidad | [composicion.md](referencia/composicion.md) | Sí |
| `color` | colorize | Color con función: acción, estado, jerarquía | [color.md](referencia/color.md) | Sí |
| `movimiento` | animate | Transiciones que explican un cambio de estado | [movimiento.md](referencia/movimiento.md) | Sí |
| `documentar` | document, extract | Escribir o actualizar `DESIGN.md`; extraer tokens y componentes | [design-md.md](referencia/design-md.md) | Sí |

**Sin comando explícito:**
- "Revísala", "qué le arreglo", "dame tu opinión": `critica`.
- "Déjala lista para entregar": `pulir`.
- "¿Qué pasa si falla o viene vacío?": `endurecer`.
- Cualquier otro trabajo de diseño: modos + piso de calidad.
- Solo `/diseno-ui`, sin nada más: muestra la tabla y pregunta. Nunca corras un comando por tu cuenta.

Si dos comandos aplican, pregunta una vez.

## Lo que no hace esta skill

| Necesidad | Usa |
|---|---|
| Accesibilidad formal (WCAG con axe-core) | `a11y-playwright` |
| Rendimiento medido | Lighthouse de chrome-devtools o `performance-engineer` |
| Abrir la página, interactuar, tomar capturas | `playwright-explorer` o chrome-devtools |
| Estilos, paletas y pares tipográficos para algo nuevo | `ui-ux-pro-max` |
| Dirección estética de una página nueva | `frontend-design` |
| Segunda lectura visual independiente | `gemini-vision` con las capturas |

## Evidencia

- Mira la pantalla renderizada a 375, 768 y 1280 px cuando haya navegador y se pueda abrir (servidor local del proyecto o un HTML estático servido en `127.0.0.1`). Si de verdad no se puede, el reporte dice **"revisado solo desde código"** en la primera línea.
- Cada hallazgo cita `archivo:línea` o un selector.
- axe, Lighthouse o un detector en CI son evidencia de defectos, no prueba de calidad: un escaneo limpio no sustituye mirar.

## Criterio

- **El brief y la marca mandan.** Si piden una estética, fuente o paleta concreta, se respeta aunque choque con una regla de esta skill.
- **Refinar conserva; rediseñar reemplaza.** Refinar mantiene identidad, comportamiento y todo lo que está fuera del alcance. Si el concepto está mal, dilo y propón rediseño; no lo cueles como "pulido".
- **No inventes datos ni afirmaciones.** Pregunta antes de cambiar textos con cifras, promesas o términos del negocio.
- **Textos en el idioma del producto.** Para México: español mexicano y formatos `es-MX` (fecha dd/mm/aaaa, `$1,234.56 MXN`).

## Errores comunes

| Error | Corrección |
|---|---|
| Tratar un panel como landing: métricas gigantes, degradados, animación de entrada | Operar pide precisión y calma: [modos.md](referencia/modos.md) |
| Revisar solo lo visual y pasar por alto que el formulario no funciona | En `critica`, lo que rompe la tarea va primero |
| Entregar 20 hallazgos sin orden | 3–5 prioritarios con P0–P3; el resto en una tabla corta |
| Revisar solo con datos perfectos | `endurecer`: textos largos, vacío, error, doble clic |
| "Pulir" cambiando la identidad | Es rediseño: dilo y pregunta |
| Reportar sin haber visto la pantalla y sin decirlo | Declara "revisado solo desde código" |

Origen y licencia: [NOTICE.md](NOTICE.md).
