---
description: Genera o audita un plan con el jurado (Codex; advisor solo con --con-advisor), hasta 3 rondas; implementa solo con --implementar y aprobación del jurado
argument-hint: "<problemas>" | --plan <ruta> [--repo <ruta>] [--implementar] [--con-advisor]
---

# /plan-auditado — plan aprobado por el jurado, no por quien lo escribe

## Argumentos
- `$ARGUMENTS`
- `--plan <ruta>`: audita ese plan existente. **Nunca implementa**, aunque venga `--implementar`.
- Sin `--plan`: el texto son los problemas a resolver y primero generas el plan (paso 1).
- `--repo <ruta>`: repo del código que el plan toca. Por omisión, el directorio actual si es repo git.
- `--implementar`: si el jurado aprueba, cuenta como frase de arranque (CLAUDE.md, «Planeacion vs implementacion»). Sin aprobación no se implementa.
- `--con-advisor`: tu petición textual de un segundo juez. **Sin esta bandera nunca se llama a advisor.**

La aprobación no la decides tú: la decide `~/.claude/scripts/jurado.py siguiente` a partir de los veredictos registrados, con la tabla `~/.claude/schemas/estados_jurado.json`. Tú ejecutas lo que diga.

## 1. Generar el plan (solo sin `--plan`)

Formato canónico: la plantilla `~/.claude/plantillas/plan.html` (secciones en tablas con columna «En simple», decisiones D1..Dn, pruebas con la columna «Protege» y el mismo `<style>`). Además, para que el jurado lo pueda revisar:

- En la línea de metadatos, `Raíces: <code>ruta</code>, <code>ruta</code>` con todo lo que el plan cita. Una raíz relativa cuelga de la carpeta del plan.
- Cada cita como `<code>archivo:línea</code>` o `<code>archivo:inicio–fin</code>`, relativa a una raíz.
- Un h3 «Matriz de tipos …» con los nueve tipos (unitarias, integración, e2e, rutas de error, regresión del bug, seguridad, contrato, migración/datos, rendimiento): cada uno «Sí» y dónde, o «No aplica porque …».
- Lo que no sepas: `PENDIENTE: qué — quién — se cierra en E#`. Sin «se cierra en», bloquea.
- Verificación con un bloque `# Automática` (comandos relativos a la raíz del repo o a `$CLAUDE_HOME`, sin rutas absolutas al original; de ahí salen los comandos que Codex debe correr) y otro `# Manual`.
- **Si el plan toca interfaz** (plantillas, CSS, componentes o pantallas), carga la skill `diseno-ui` antes de escribirlo y agrega:
  - una decisión de interfaz por pantalla (su propio D#): su tipo (`referencia/modos.md`) y qué se muestra en cada estado que el cambio agrega o modifica (cargando, vacío, error, éxito, deshabilitado, sin permiso, texto largo y doble envío; ver `referencia/endurecer.md`). Es la decisión que van a citar los casos manuales de esos estados;
  - en Pruebas, al menos un caso por cada uno de esos estados;
  - en el bloque `# Manual`, `/diseno-ui critica <pantalla>` sin P0 ni P1 que el cambio introduzca o agrave. Los scripts no ejecutan el bloque `# Manual`: la crítica la corre quien implementa (paso 4 de este comando, o la Fase 1 de `/implementa-plan`).

  Si no toca interfaz, no aplica y no se menciona.

Guárdalo en `docs/` del repo si pertenece al proyecto; si no, en `~/Desktop`.

## 2. Abrir la auditoría

```bash
python3 ~/.claude/scripts/jurado.py inicia --plan <plan> [--repo <repo>] --sesion <opus|fable> [--con-advisor]
```

`--sesion` es el modelo de esta sesión. Imprime el directorio de la auditoría (`D`). Si falla porque Codex no está disponible, detente y dilo: sin Codex no hay jurado.

## 3. El ciclo

Corre `python3 ~/.claude/scripts/jurado.py ronda --dir D [--respuesta <archivo>]` y lee el JSON que imprime (`accion`, `ronda`, `motivo`). Haz exactamente lo que diga la acción:

| Acción | Qué haces |
|---|---|
| `corregir-mecanico` | Corrige en el plan lo que dice `motivo` (citas, matriz o pendientes) y vuelve a correr `ronda`. No consume ronda. |
| `llamar-codex` | Vuelve a correr `ronda`: es el reintento por un JSON inválido. |
| `corregir` | Lee los hallazgos de la ronda anterior (`D/ronda-<N-1>-codex.json` y, si hubo, del segundo juez). Corrige el plan para cada uno. Si no estás de acuerdo con un hallazgo, no lo ignores: escribe por qué en un archivo de respuesta, con evidencia (archivo:línea, comando y salida), y córrelo con `ronda --respuesta <archivo>`. |
| `llamar-segundo:<agente>` | Solo existe con `--con-advisor`. Llama al subagente `<agente>` (`advisor` o `advisor-opus`) con la ruta `D/ronda-<N>-plan.html`, la rúbrica `~/.claude/rubricas/plan.json` y la instrucción de terminar con un bloque ```json del esquema `~/.claude/schemas/veredicto.json`. Guarda su respuesta completa en un archivo y regístrala con `jurado.py registra --dir D --ronda N --juez <agente> --archivo <archivo>`. Si el subagente falla: `registra ... --estado fallo-tecnico --detalle "<error>"`. Después, `jurado.py siguiente --dir D`. |
| `aprobado` | Paso 4. |
| `escalar:*` | Detente. Reporta la razón, los hallazgos abiertos y la mejor versión (`jurado.py mejor --dir D`). Decide Juan. |

## 4. Al aprobar

- Sin `--implementar`, o con `--plan`: entrega el plan y la ruta `D`, y **detente**: espera la frase de arranque.
- Con `--implementar`: implementa el plan. Si toca interfaz, antes de validar corre `/diseno-ui critica <pantalla>` por cada pantalla que cambia, sin su sección de preguntas, y corrige los P0 y P1 que el cambio introdujo o agravó; los que ya estaban se reportan y no se arreglan sin que Juan lo pida. Al terminar, valida con Codex:

  ```bash
  python3 ~/.claude/scripts/valida_impl.py --plan <plan> --origen <repo> --registro D [--incluir <ruta> ...]
  ```

  `--incluir` solo cuando el origen no es repo git (rutas relativas a copiar). rc 0 = aprobado; rc 1 = no aprobado: corrige y vuelve a validar; rc 2 = no se pudo validar: repórtalo y no lo des por bueno. Sin rc 0 la implementación no está terminada. Advisor no revisa el cierre salvo que Juan lo pida.

## Reglas

- Nunca apruebas tú y nunca descartas un hallazgo sin una respuesta con evidencia.
- Nunca llamas a advisor sin `--con-advisor`.
- Si Codex no está disponible o rechaza el modelo, detente: no se cae a otro juez.
- Todo queda en `D` (`~/.claude/auditorias/...`), fuera del repo del cliente.
