---
name: implementa-plan
description: Implementa de punta a punta el plan acordado en la sesión (o el archivo que se le pase) - implementación, huecos de la suite detectados por Codex, pruebas de todos los tipos (no solo camino feliz) que se ven fallar contra una mutación de producción, casos de prueba manuales escritos por otro agente y corridos con una herramienta (navegador con Playwright, API o línea de comandos) con captura y logs por paso en un HTML, doble revisión de esa evidencia buscando falsos positivos y negativos, revisión final con Codex + Claude en máximo 3 rondas, validación aislada y PR. Invocarlo es la frase de arranque para ese plan.
argument-hint: "[<ruta-plan>] [--repo <ruta>] [--url <base-local>] [--base <rama>] [--con-advisor]"
disable-model-invocation: true
---

# /implementa-plan — del plan al PR, con pruebas que se ven fallar y evidencia en pantalla

## Argumentos
- `$ARGUMENTS`
- `<ruta-plan>` (opcional): plan en HTML o Markdown. **Sin ruta, se implementa el plan del que se habló en esta sesión** (ver «De dónde sale el plan»). El plan no se modifica: `inicia` congela una copia en `D`.
- `--repo <ruta>`: repo que toca el plan (por omisión, el directorio actual).
- `--url <base>`: URL de la app para Playwright. Solo loopback (`localhost`, `127.x`, `::1`); otra (staging) con `--confirmacion-url "<texto literal de Juan que nombre el host>"`. Producción nunca.
- `--base <rama>`: rama de la que sale el trabajo y a la que va el PR (por omisión, la actual).
- `--con-advisor`: petición textual de Juan de un tercer revisor en la Fase 7. Sin esta bandera no se llama a advisor.

Invocar `/implementa-plan` **es** la frase de arranque para ese plan (CLAUDE.md, «Planeación vs implementación»). No autoriza implementar otra cosa.

`S` = `python3 ~/.claude/scripts/implementa_plan.py` · `K` = `~/.claude/skills/implementa-plan` · `D` = el registro que imprime `S inicia`.

## Cómo está armada
Tú implementas y orquestas; `S` comprueba cada paso, lo amarra al commit y deja registro en `D`. Si `S` dice que no, no se avanza. Protege contra errores honestos (tuyos o de otro agente), no contra trampas: nunca escribes a mano en `D` lo que produce un subcomando. Todo lo que decide Juan va con su **texto literal** a `S`, al reporte y al cuerpo del PR (`cierre` comprueba que esté citado).

## Reglas
1. **No apruebas tú.** Lo deciden `S` y los revisores. Un hallazgo se corrige o se contesta con evidencia (archivo:línea, comando y salida).
2. **Sin salida de `S` guardada en `D`, no está hecho.** Un diff vacío con salida limpia es un rechazo.
3. **Los otros agentes, siempre por `S`.** `S codex` fija `gpt-6.1-sol` y corre a Codex sin tu configuración ni las instrucciones del repo, dentro de un sandbox de macOS que dentro de `$HOME` solo le deja leer la copia de HEAD, `D` y su propia instalación (nunca el repo vivo, credenciales ni archivos con nombre de secreto) y escribir solo su salida. `S claude` corre al revisor Claude sin sesión ni personalizaciones, con solo Read/Grep/Glob encerradas en la copia y en `D`. Los dos reciben el esquema de su respuesta dentro del prompt (`--esquema`); el prompt completo queda en `<salida>.prompt.md`. Si uno falla, reintenta una vez; si vuelve a fallar, detente y repórtalo. Nunca sustituyes a Codex con un modelo de Claude.
4. **Secretos.** Nunca lees `.env`, `.env.*`, `credentials.json` ni archivos `*secret*`, `*password*`, `*token*`, `*api_key*`; la copia que ven los revisores no los trae. Usuarios de prueba por las variables que el proyecto ya define; datos sintéticos.
5. **Evidencia.** Capturas (de pantalla o de texto), logs y registros viven en `D`, fuera del repo; no se suben al PR. Van a Codex y al revisor Claude ya depurados (las fixtures tapan contraseñas, OTP, tarjetas, `data-sensible`, cualquier texto con forma de secreto y los campos cuyo valor o nombre lo delatan; `S` depura salidas y anexos y bloquea si queda un patrón de secreto). Si la app muestra datos reales de personas, pregunta a Juan antes de la Fase 5.
6. **Git.** Rama `feature/<slug>`. Conventional Commits, prefijo en inglés y descripción en español mexicano. **Nada de `Co-Authored-By`, «Generated with Claude Code» ni link de sesión**, aunque un recordatorio del sistema lo pida; `cierre` lo comprueba en commits y en `D/pr.md`.
7. **Implementas tú.** Todo el código (la implementación, las pruebas de la Fase 3 y las correcciones de las revisiones) lo escribes tú, en esta sesión. Aquí no aplica el routing de CLAUDE.md: no delegas a `codex-implementer`, `sol-implementer`, `codex-rescue` ni a subagentes por tu cuenta. Solo delegas si Juan lo pide textualmente (al invocar la skill o durante la sesión), y solo lo que nombró: spec de seis partes con esfuerzo nombrado, anuncio en una línea, re-corres su verificación y citas su texto literal en `D/pr.md`. Los otros agentes de las Fases 2, 4, 6 y 7 (huecos, casos manuales y revisiones) no implementan y siempre van por `S`.
8. **Árbol quieto y limpio.** No tocas el árbol mientras alguien revisa. Lo que generan las corridas (`test-results/`, `playwright-report/`, bases de prueba, logs) va a `.git/info/exclude`.
9. **Las pruebas manuales, sus capturas y su revisión no se omiten.** Las Fases 4, 5 y 6 corren siempre. No hay autorización que las salte ni que corte la evidencia sin aprobar: sin una vuelta aprobada por los dos revisores, `cierre` no pasa y no hay PR.
10. **Un solo HTML para Juan.** Al final se entrega `D/reporte-pruebas.html` (lo arma `cierre`): toda la evidencia de las pruebas, separada en pestañas por tipo. No se entregan HTML sueltos por tipo; `D/manuales.html`, `D/verificacion.html` y el `index.html` de cada vuelta son de trabajo, para los revisores.

## De dónde sale el plan
| Caso | Qué haces |
|---|---|
| Viene `<ruta-plan>` | Ese archivo. |
| En la sesión se escribió o citó un archivo de plan | El más reciente; dilo en una línea («Implemento `<ruta>`»). |
| El plan solo existe en la conversación | Transcríbelo a `<scratchpad>/plan-sesion.md` (Objetivo; Decisiones D1..Dn con lo que se acordó y archivo:línea; Archivos; Pruebas; Verificación con un bloque ``` que tenga `# Automática` y `# Manual`; Fuera de alcance; `PENDIENTE: qué — quién`). Nada que no se haya dicho. Muestra las decisiones en una tabla corta y pregunta una vez (AskUserQuestion): «¿Implemento este plan?». Pasa `--desde-sesion` a `inicia`. |
| Más de un candidato, o ninguno | Pregunta cuál. |

## Fase 0 — Arranque
1. Lee el plan. Lo que tenga `PENDIENTE` o una decisión abierta se pregunta antes de implementar esa parte. Si el plan toca interfaz y no trae su decisión de interfaz (tipo de pantalla y qué se muestra en cada estado), pregúntalo antes de `inicia`. Si Juan la quiere, se agrega al plan antes de congelarlo (al transcribirlo, si viene de la sesión). Si no, se sigue sin casos de estados de pantalla y su respuesta literal va en `D/pr.md`.
2. Detecta sin escribir nada: el comando que corre **todas** las pruebas del proyecto, relativo a la raíz, sin rutas absolutas y sin cortar en la primera falla (`-x`, `-xvs`, `--failfast`, `--bail`, `--maxfail N`). `inicia` los rechaza en el comando, pero no ve la configuración del runner: revisa tú `addopts` en `pytest.ini`, `pyproject.toml`, `setup.cfg` y `tox.ini`; el script que corre `npm test` en `package.json`; `bail` en la config de Jest o Vitest; `maxFailures` en la de Playwright; y `--failfast` o `failfast` en el `TEST_RUNNER` de Django. Si alguno corta, anúlalo en el comando (`pytest -o addopts=""`, `npx jest --bail=0`, `npx vitest run --bail=0`, `npx playwright test --max-failures=0`). Esto lo decides tú; no se le pregunta a Juan. Que la suite imprima cada prueba con su resultado, para el reporte final: Django o unittest `-v 2`, pytest `-rA`, `npx jest --verbose`, `npx vitest run --reporter=verbose`, `npx playwright test --reporter=list`. Si las e2e van aparte o en otra carpeta: `pytest && cd frontend && npx playwright test`. Corre con `sh`: para un entorno virtual, `. .venv/bin/activate && pytest` (`source` no existe en el `sh` de Linux). Y cómo levantar la app y su URL local.
3. **Validación aislada.** Si el proyecto necesita dependencias fuera de git (`.venv`, `node_modules`) o servicios (Postgres, Redis), el contenedor de `valida_impl` no podrá correrlo. Díselo a Juan ahora: seguir sabiendo que el PR saldrá como draft no validado, o preparar antes una imagen para `valida --imagen` (trabajo aparte, con su permiso).
4. Árbol sucio: pregunta qué hacer; no hagas stash por tu cuenta.
5. `S inicia --plan <plan> --repo <repo> --suite "<todas las pruebas>" [--url … [--confirmacion-url "…"]] [--base <rama>] --sesion <opus|fable> [--con-advisor] [--desde-sesion]`.
6. Si `rama_base` no es la rama actual, `git switch <rama_base>`. Luego `S suite --dir D --fase linea-base` (una sola vez; lo que ya estaba rojo queda como preexistente) y `git switch -c feature/<slug>` (o `fix/`, `refactor/`, `docs/`; `cierre` lo exige).

## Fase 1 — Implementar
Si el plan toca interfaz (plantillas, CSS, componentes o pantallas):
- Carga la skill `diseno-ui` y lee su `referencia/piso-calidad.md` antes de editar esos archivos.
- Al terminar las entregas de interfaz, con la app levantada, corre `/diseno-ui critica <pantalla>` por cada pantalla que toca el cambio, sin su sección de preguntas.
- Guarda cada reporte en `D/critica-<pantalla>.md`.
- Antes de la compuerta, corrige los P0 y P1 que el cambio introdujo o agravó. Los que ya estaban no se arreglan sin que Juan lo pida: van listados en `D/pr.md`.

Es trabajo tuyo, no delegación: la regla 7 sigue igual. `S` no comprueba esta crítica; su resultado va en `D/pr.md`.

Un commit por entrega del plan (`feat:` / `fix:` / `refactor:`). Compuerta: `S suite --dir D --fase fase-1` (rc 0 si no hay rojos nuevos frente a la línea base; un rc distinto de 1 es que la suite abortó).

## Fase 2 — Huecos de la suite (Codex)
1. `S copia --dir D` → `copia` y `diff`. Llena `K/prompts/huecos.md` → `D/fase-2-prompt.md`.
2. `S codex --dir D --prompt D/fase-2-prompt.md --esquema casos_prueba --salida D/fase-2-huecos.json` y luego `S casos --dir D`. rc 1: repite Codex una vez con los `errores` al final del prompt. Si Codex no encuentra huecos, pregunta a Juan; solo con su sí, `S casos --dir D --sin-huecos "<texto literal>"`.
3. Un caso se descarta solo en `D/fase-2-descartes.json` (`{"descartes": [{"id": "T-03", "razon": "ya lo cubre tests/test_x.py:42"}]}`) citando la línea de **la prueba que ya lo cubre**. Cada descarte va en `D/pr.md`.

## Fase 3 — Pruebas que se ven fallar
1. Una prueba por caso, con las convenciones de la suite (factories, servicios externos mockeados). Escribe todas y haz un commit `test: …` antes de los rojos: un cambio posterior en pruebas, helpers o su configuración vence los rojos ya vistos.
2. Para cada caso, escribe la mutación mínima de producción que el caso dice proteger (cambiar una condición, un valor, quitar una validación; un parche de `git diff` que solo modifica archivos existentes, guardado **fuera del repo**, p. ej. `<scratchpad>/T-01.patch`) y corre `S rojo --dir D --caso T-01 --prueba "<archivo>::<nombre>" --comando "<corre esa prueba>" --parche <mutacion.patch>`. `S` corre la prueba en el repo sin la mutación (debe pasar), aplica el parche, la corre de nuevo (debe fallar **esa** prueba **por su aserción**, no por carga, recolección ni otra excepción) y deshace el parche. Cualquier runner sirve:

   | Runner | `--prueba` | `--comando` |
   |---|---|---|
   | pytest | `tests/test_x.py::Clase::test_y` | `pytest tests/test_x.py::Clase::test_y` |
   | Django | `app/tests/test_x.py::Clase::test_y` | `python manage.py test app.tests.test_x.Clase.test_y` |
   | unittest | `tests/test_x.py::Clase::test_y` | `python -m unittest tests.test_x.Clase.test_y` |
   | Playwright TS | `e2e/x.spec.ts::M-01 título` | `npx playwright test e2e/x.spec.ts -g "M-01 título"` |
   | pytest-playwright | `tests/e2e/test_x.py::test_m01` | `pytest tests/e2e/test_x.py::test_m01` |
   | Jest / Vitest | `src/x.test.ts::nombre del caso` | `npx jest src/x.test.ts -t "nombre del caso"` / `npx vitest run src/x.test.ts -t "…"` |

   En Jest, Vitest y Playwright el nombre es el del `test()`, sin el `describe` que lo envuelve. El comando debe nombrar el archivo, el módulo o el nombre de la prueba. Para un caso e2e, la app tiene que recargar el código mutado (servidor de desarrollo o `webServer` de Playwright); contra un build fijo el rojo no se ve. Si `rojo` se interrumpe a la mitad, `git checkout HEAD -- <archivos mutados>`.
3. `S rojos --dir D`: un rojo válido por cada caso no descartado. Un rojo vence si después cambian su prueba, lo que muta, otras pruebas o helpers, o la configuración de pruebas; `S rojos --dir D --repetir` vuelve a correr los vencidos con su comando y su parche guardados.
4. Si una prueba destapa un bug real, se corrige producción (`fix: …`), no la prueba.
5. `S suite --dir D --fase fase-3`. Además de la suite normal, la corre completa con las mutaciones de los rojos aplicadas y exige que salga en rojo con cada prueba declarada entre las fallas: si no, la suite no la corre (archivo mal nombrado, spec fuera del glob) o la mutación la corta antes, y lo dice en `motivos`. Para no correr la suite una vez por rojo, un parche repetido se aplica una vez y los que no tocan los mismos archivos van juntos en una corrida (`grupos`); si en un grupo falta una prueba, su parche se repite solo. Cuenta con una corrida por grupo, más una por cada parche que haya que repetir. Toda corrida de la suite (también la normal de cada fase) sigue con los demás tramos de `A && B` aunque uno falle, en el mismo shell: un `cd` o un `source` siguen valiendo. Si después cambia un rojo (uno nuevo o `rojos --repetir`), vuelve a correr la fase-3: `cierre` lo exige.

## Fase 4 — Casos de prueba manuales (otro agente, de solo lectura)
1. `S copia --dir D`. Llena `K/prompts/manuales.md` → `D/fase-4-prompt.md` y corre `S claude --dir D --prompt D/fase-4-prompt.md --esquema casos_manuales --salida D/fase-4-manuales.md`.
2. `S manuales --archivo D/fase-4-manuales.md --salida D/manuales.html --dir D`. rc 1 o 2: repite `S claude` una vez con los `errores` al final del prompt.
3. Cada caso es automatizable si alguna herramienta lo puede correr: el navegador (Playwright) para lo que se ve en pantalla, un cliente HTTP para una API, la línea de comandos para un comando o una tarea. Solo los que ninguna puede (SMS o correo real, dispositivo físico, juicio visual subjetivo) le tocan a Juan. Siempre hay al menos un caso automatizable (`manuales` lo exige y nada lo salta): lo que no se ve en pantalla se comprueba por API o por línea de comandos, y en un refactor, lo que no debía cambiar. Si el agente no trae ninguno, repite `S claude` con el error al final del prompt.
4. `D/manuales.html` es de trabajo. Los casos que le tocan a Juan van en la pestaña «Manuales» del reporte final.

## Fase 5 — Correr los casos manuales con una herramienta, con captura de cada paso (vuelta K, empieza en 1)
1. Copia la fixture al directorio de pruebas del proyecto: `K/plantillas/evidencia.ts` (@playwright/test) o `K/plantillas/evidencia_pw.py` (pytest, con o sin pytest-playwright; regístrala con `pytest_plugins`).
2. Una prueba por caso automatizable, con el ID en el título (`M-03 …`) o `@pytest.mark.caso("M-03")`, y un paso por cada paso del caso manual, en orden y con su texto literal; su aserción comprueba el `esperado`, no solo que algo respondió. Según la herramienta del caso:
   - **Pantalla:** `paso(acción, esperado, …)` con `page`: cada paso deja captura de pantalla, consola y red. Campos sensibles que no sean contraseñas: `mascara` o `data-sensible`.
   - **API o línea de comandos:** en pytest, `with paso(acción, esperado) as p:` en una prueba que no pide `page` (no abre navegador) y `p.anota(...)` con la petición y la respuesta o el comando y su salida; en Playwright TS, `pasoApi(acción, esperado, async (anota) => …)` con el fixture `request`. Lo anotado es la captura de texto del paso (`paso-NN.txt`); un paso sin captura ni texto no pasa `evidencia`.
3. Commit de las pruebas y la fixture (`test(e2e): …`). Quedan en la suite: corren con `--suite` como cualquier otra.
4. `S prepara-evidencia --dir D --ronda K`: vacía la vuelta antes de cada intento, para que no quede nada de uno anterior (un caso que ya no existe, pasos o log viejos). Si algún caso usa la app viva (navegador o HTTP contra la URL local), levántala con su log en `D/evidencia/ronda-K/servidor.log`; si todos corren en proceso (cliente de pruebas de Django, línea de comandos), no hay servidor ni log. Corre sin reintentos y, si hay navegador, uno solo: `EVIDENCIA_DIR=D/evidencia/ronda-K EVIDENCIA_CORRIDA=<fecha-hora> npx playwright test <specs> --retries=0` y `--project=<uno>` si la config define proyectos (pytest: `--browser chromium` si hay casos de pantalla).
5. Detén la app (si la levantaste) y corre `S evidencia --dir D --ronda K [--anexo D/evidencia/ronda-K/servidor.log]` (el anexo solo si hubo servidor) → `index.html` e `identificador`. rc 1 (falta o sobra un caso, pasos distintos al manual, un paso sin captura de pantalla ni de texto, otro commit, posible secreto, corridas mezcladas): corrige y repite en la misma vuelta desde el paso 4, con `prepara-evidencia`.

## Fase 6 — Verificar la evidencia: dos revisores, paso por paso
1. Llena `K/prompts/revision_evidencia.md` (`{{IDENTIFICADOR}}` = el que imprimió `evidencia`; `{{CASOS_A_REVISAR}}` = su `revisar`). Desde la vuelta 2, `evidencia` hereda los casos que los dos confirmaron en la vuelta anterior si solo cambiaron documentación o specs de evidencia, y no el suyo ni su caso manual; esos no se vuelven a revisar. En un mismo mensaje, en paralelo:
   - `S codex --dir D --prompt <prompt> --esquema revision_evidencia --salida D/evidencia/ronda-K/revision-codex.json`
   - `S claude --dir D --prompt <prompt> --esquema revision_evidencia --salida D/evidencia/ronda-K/revision-claude.md`
2. `S cruza --dir D --ronda K --codex …/revision-codex.json --claude …/revision-claude.md`. Cada revisor compara cada captura (de pantalla o de texto) con el `esperado` del paso. Un caso se confirma solo si la prueba pasó y los dos dicen «correcto», o uno «correcto» y el otro «asercion-debil» (queda en `notas`, que van al PR). rc 2 (revisión de otra vuelta, incompleta o con casos ajenos): no gasta la vuelta; pídesela de nuevo a quien falló.
3. rc 1: `falso-positivo` → bug de producción o aserción que no mira lo correcto; `falso-negativo` → la prueba (selector, espera, dato); `asercion-debil` de los dos → reforzar; `inconcluso` → más evidencia; «no pasa» → arreglar la prueba o producción. Commit y Fase 5 con K+1.
4. Tres vueltas seguidas sin aprobar: detente y escala a Juan. Si pide una vuelta más, su texto literal va a `S prepara-evidencia --dir D --ronda 4 --vuelta-extra-autorizada "<texto>"` (queda sellado; es una sola vuelta extra). La evidencia no se corta ni se omite: si la vuelta extra tampoco aprueba, corrige lo que la tumba (producción, el spec o, con el sí de Juan, `enmienda-manual`) y la vuelta siguiente se abre sola, porque algo cambió desde el último cruce; sin cambios no hay otra vuelta y no hay PR.

## Fase 7 — Revisión final (Codex + Claude, máx. 3 rondas)
1. `S abre-ronda --dir D` → N, `D/ronda-N/cambios.diff`, `D/ronda-N/commits.txt` e `identificador`. Si el cambio toca archivos con nombre de secreto, pregunta a Juan y repite con `--omitidos-autorizados "<texto literal>"`. Desde la ronda 2 exige un commit nuevo o `D/ronda-(N-1)/respuesta.md`. Después: `S suite --dir D --fase ronda-N` y `S copia --dir D`.
2. Llena `K/prompts/revision_final.md` (`{{IDENTIFICADOR}}`, `{{DIFF}}` = `D/ronda-N/cambios.diff`, `{{COMMITS}}` = `D/ronda-N/commits.txt`, `{{SALIDA_SUITE}}` = `D/suite-ronda-N.txt`). En un mismo mensaje, en paralelo:
   - `S codex --dir D --prompt <prompt> --esquema veredicto --salida D/ronda-N/codex.json`
   - `S claude --dir D --prompt <prompt> --esquema veredicto --salida D/ronda-N/claude.md`
   - Solo con `--con-advisor`: el agente de `jueces` en `D/config.json` (`advisor` o `advisor-opus`), con el prompt completo que guardó `S claude` (`D/ronda-N/claude.prompt.md`) → `D/ronda-N/advisor.md`.
3. Sin tocar el árbol: `S registra --dir D --ronda N --juez <codex|claude|advisor…> --archivo <archivo>`. rc 2 (JSON inválido o `resumen` que no empieza con el identificador): pide al mismo revisor que lo rehaga una vez.
4. `S siguiente --dir D`:

| `accion` | Qué haces |
|---|---|
| `revisar` | Falta el veredicto de `faltan`. |
| `corregir` | Corrige cada hallazgo grave y medio (y los menores baratos) o contéstalo con evidencia en `D/ronda-N/respuesta.md`. Commit `fix: atiende revisión ronda N`. Si tocaste producción, specs, helpers o fixtures de prueba, repite las Fases 5–6 en una vuelta nueva (`cierre` lo exige; documentación y archivos de prueba unitaria no). Si una corrección cambia lo que un caso manual dice en su `esperado`, pregunta a Juan; con su sí, `S enmienda-manual --dir D --caso M-xx --paso N --esperado "<texto nuevo>" --motivo "<hallazgo, ronda N, archivo:línea>" --autorizacion "<texto literal>"` y repite las Fases 5–6. Con evidencia ya armada, `manuales --dir` no vuelve a congelar. Si `S rojos --dir D` dice que venció algún rojo, `S rojos --dir D --repetir`. Vuelve al paso 1 con `{{PREVIOS}}`. |
| `aprobado` | Fase 8. |
| `escalar` | Detente; reporta motivos, hallazgos abiertos y discrepancias. Sin PR. Decide Juan. Si después de la ronda 3 pide una más, su texto literal va a `S abre-ronda --dir D --ronda-extra-autorizada "<texto>"` (una sola). Esa ronda se aprueba si ningún revisor trae graves; los medios que queden salen en `abiertos` y van en `D/pr.md` con su `donde`. Con un grave, escala. |

## Fase 8 — Validación aislada, cierre y PR
0. `S rojos --dir D`; si venció alguno (un archivo de prueba nuevo no los vence; sí cambiar pruebas existentes, helpers o la configuración de pruebas), `S rojos --dir D --repetir` y luego `S suite --dir D --fase fase-3`. Un caso en `no_repetidos` (su parche ya no aplica) pide un `rojo` nuevo.
1. `S verificacion --dir D [--comando "<e2e autocontenido>"]` → `D/verificacion.html`. Hereda el bloque «# Automática» del plan y siempre incluye la suite. Rechaza comandos triviales, rutas absolutas y `||`, `;` o `|` (esconden fallas). Si la Verificación del plan no se puede usar, pregunta a Juan; con su sí, `--plan-ilegible "<texto literal>"` y los sustitutos en `--comando`.
2. `S valida --dir D [--imagen <imagen>]` corre `valida_impl.py` en un contenedor sin red. rc 0: sigue. rc 1 por el cambio: corrige y vuelve a la Fase 7. rc 1 por el entorno o rc 2: pregunta a Juan si sale como **draft sin validar**; con su sí, su texto va a `cierre --borrador-autorizado`.
3. `S suite --dir D --fase final`. Si sale roja y **todos** sus rojos ya estaban en la línea base, pregunta a Juan y pasa su texto a `cierre --rojos-preexistentes-autorizados`. Un rojo nuevo se corrige.
4. Escribe `D/pr.md`: qué cambia y qué plan implementa (si vino de la sesión: «plan acordado en la sesión del <fecha>» con D1..Dn); pruebas por tipo y camino; casos descartados con su razón; evidencia (resumen y ruta local, sin capturas); cada enmienda de un caso manual (ID, paso y esperado nuevo, de `D/manuales-enmiendas.json`); las `notas` de la última vuelta (asercion-debil de un solo revisor); pruebas que le tocan a Juan; rondas y veredictos; discrepancias Codex/Claude; si hubo crítica de interfaz, sus rutas en `D`, los P0 y P1 corregidos y los preexistentes que quedan; resultado de la validación; cada autorización de Juan citada literal. Sin firma.
5. `S cierre --dir D [--borrador-autorizado "…"] [--rojos-preexistentes-autorizados "…"]`. También exige la última vuelta de evidencia aprobada, la rama `feature/…` (o `fix/`, `refactor/`, `docs/`) y que cada commit desde la base sea Conventional Commits. **Sin rc 0 no hay PR.** En cada corrida arma `D/reporte-pruebas.html` (también con errores; su ruta sale en `reporte`), con una pestaña por tipo: la suite completa (cada corrida, con el desglose por prueba de la final), las pruebas nuevas de la Fase 3 por tipo (unitaria, integración, seguridad…) con su mutación y su rojo, los casos manuales con sus capturas y el dictamen de los revisores, y la validación aislada. `S reporte --dir D` lo vuelve a armar sin cerrar.
6. `git push -u origin <rama>` y `gh pr create --base <rama_base> --title "<tipo>: …" --body-file D/pr.md` (`--draft` si `cierre` dice `no_validado`).
7. Opcional, si tienes `vault-capture`: `vault-capture auto --event milestone --title "<plan>: PR abierto" --source claude --body "<PR, D, resultado>"`.

## Placeholders de los prompts
`{{PLAN}}` = `plan` de `D/config.json` · `{{REPO}}` = `copia` de `S copia` · `{{DIFF}}` = `diff` de `S copia` (Fases 2 y 4) o `D/ronda-N/cambios.diff` (Fase 7) · `{{BASE}}`/`{{RAMA}}` = `base` de `config.json` / la rama `feature/…` · `{{SALIDA_SUITE}}` = el `D/suite-<fase>.txt` más reciente · `{{ARCHIVOS_DE_PRUEBA}}` = archivos de prueba de la copia · `{{RUTAS}}`/`{{URL}}` = pantallas que toca el diff / `url` de `config.json` · `{{CASOS_A_REVISAR}}` = `revisar` de `S evidencia` · `{{MANUALES}}` = `D/manuales.json` · `{{DIR_EVIDENCIA}}`/`{{HTML}}`/`{{LOG_SERVIDOR}}` = `D/evidencia/ronda-K/`, su `index.html` y su `servidor.log` («no aplica» si no hubo servidor) · `{{SPECS}}` = pruebas que generaron la evidencia, en la copia · `{{COMMITS}}` = `D/ronda-N/commits.txt` · `{{EVIDENCIA}}` = `index.html` de la última vuelta aprobada · `{{RONDA}}`/`{{IDENTIFICADOR}}` = N / el `identificador` impreso, tal cual · `{{PREVIOS}}` = hallazgos de la ronda anterior y su `respuesta.md` («ninguno» en la ronda 1). El formato de salida y el esquema no se escriben: los agrega `S codex`/`S claude` con `--esquema`.

## Reporte final
Corto y con fuente: link del PR, rama, `D`, suite (`<n> pruebas según D/suite-final.txt, al <fecha>`), **un solo HTML**: `D/reporte-pruebas.html` (la evidencia de todas las pruebas por pestañas, con los casos que le toca correr a Juan; ningún otro HTML por tipo), rondas y veredictos, discrepancias, autorizaciones literales de Juan y lo que no se pudo validar. Con `no_validado`, la implementación **no está terminada**: dilo así.
