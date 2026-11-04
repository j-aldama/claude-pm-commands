# Crítica de UX

Revisión de solo lectura: resuelve el objetivo, junta evidencia, entrega un reporte con puntaje y prioridades, y termina preguntando qué atacar primero. No editas nada.

## 1. Resolver el objetivo

- Convierte lo que pidió el usuario en un archivo o una URL concreta. Prefiere la ruta del código cuando ambas identifican la misma pantalla.
- Clasifica la pantalla con [modos.md](modos.md).
- Lee el `CLAUDE.md` y el `DESIGN.md` del proyecto si existen.

## 2. Juntar evidencia

1. **Código:** plantilla, CSS, JS y el componente principal. Anota `archivo:línea`.
2. **Render:** si hay navegador disponible (playwright o chrome-devtools) y la pantalla se puede abrir, renderízala. Cuenta como "se puede abrir" el servidor local del proyecto o un HTML estático servido con `python3 -m http.server <puerto> --bind 127.0.0.1` desde su carpeta; detén ese servidor al terminar. Toma capturas a 375, 768 y 1280 px y recorre la acción principal con mouse y con teclado. "Solo código" es para cuando de verdad no se puede. Playwright guarda sus capturas dentro del directorio de trabajo (`.playwright-mcp/`): al terminar, borra solo las que dejaste tú.
3. **Medición, si está a la mano:** axe (`a11y-playwright`) para accesibilidad y Lighthouse para rendimiento. No los sustituyas con cálculos a ojo; si no corrieron, dilo.
4. **Segunda lectura opcional:** para un entregable importante, pasa las capturas a `gemini-vision` con la tabla de heurísticas de abajo **antes** de mostrarle tus hallazgos, para que no se ancle en ellos.

Forma tu juicio de diseño (sección 3) antes de leer resultados automáticos: los números anclan.

## 3. Evaluar

En este orden, porque lo funcional pesa más que lo estético:

1. **¿La tarea principal se puede completar?** Formularios que no envían, botones que no hacen nada, mensajes que contradicen el estado real, datos que se pierden.
2. **Estados:** cargando, vacío, error, éxito, deshabilitado, sin permiso.
3. **Heurísticas de Nielsen** (tabla de abajo), con puntaje de 0 a 4.
4. **Carga cognitiva** (lista de abajo).
5. **Piso de calidad:** recorre [piso-calidad.md](piso-calidad.md) **renglón por renglón contra el CSS y el HTML**, incluida la lista de "Se rechaza por defecto". Cada coincidencia es un hallazgo: P2 o P3, salvo que estorbe la tarea. Ahí están los patrones genéricos que una revisión libre suele pasar por alto (por ejemplo, un `border-left` de color en avisos).
6. **Especificidad:** ¿se ve hecha para este producto, o cualquier otro producto la usaría tal cual?
7. **Personas:** recorre la acción principal como 2 o 3 personas de la tabla de abajo.

### Heurísticas (0–4 cada una)

| # | Heurística | Qué revisar |
|---|---|---|
| 1 | Visibilidad del estado del sistema | Indicadores de carga, confirmación de acciones, progreso, ubicación actual, validación en línea |
| 2 | Lenguaje del usuario | Términos del negocio sin jerga técnica, orden lógico, íconos reconocibles |
| 3 | Control y libertad | Deshacer, cancelar, regresar, limpiar filtros, salir de flujos largos |
| 4 | Consistencia y estándares | Mismos términos, mismos componentes, convenciones de la plataforma |
| 5 | Prevención de errores | Confirmación en acciones destructivas, restricciones de entrada, valores por omisión, autoguardado |
| 6 | Reconocer antes que recordar | Opciones visibles, ayuda en contexto, autocompletado, íconos con texto |
| 7 | Flexibilidad y eficiencia | Atajos de teclado, acciones en lote, favoritos y recientes |
| 8 | Diseño minimalista | Solo lo necesario, jerarquía clara, color con propósito, sin ruido decorativo |
| 9 | Recuperarse de errores | Mensajes en lenguaje claro, problema específico, salida concreta, sin borrar lo capturado |
| 10 | Ayuda y documentación | Ayuda en contexto, enfocada en la tarea, sin salir de la pantalla |

**Escala:** 0 = inexistente o roto; 1 = graves huecos; 2 = parcial; 3 = bien con detalles menores; 4 = excelente de verdad. Sé honesto: la mayoría de las interfaces reales queda entre 20 y 32 de 40.

En Persuadir y Exhibir, la 7 y la 10 pueden ir como `n/a` con una línea de motivo. Entonces el máximo baja (por ejemplo, /32) y la banda se lee por porcentaje: 90 % o más, excelente; 70 %, buena; 50 %, aceptable; 30 %, pobre; menos, crítica. Nunca escribas /40 sobre un conjunto parcial.

### Carga cognitiva

Cuenta cuántos de estos fallan. 0–1, carga baja; 2–3, moderada; 4 o más, crítica.

- [ ] **Foco único:** la tarea principal se hace sin distracciones que compitan.
- [ ] **Bloques:** la información va en grupos de 4 elementos o menos.
- [ ] **Agrupación:** lo relacionado se ve junto (proximidad, fondo compartido).
- [ ] **Jerarquía:** queda claro al instante qué importa más.
- [ ] **Una cosa a la vez:** se decide una cosa antes de pasar a la siguiente.
- [ ] **Pocas opciones:** 4 o menos opciones visibles por punto de decisión.
- [ ] **Memoria:** no hay que recordar datos de otra pantalla para actuar en esta.
- [ ] **Revelación progresiva:** la complejidad aparece cuando se necesita.

### Personas

| Tipo de pantalla | Personas sugeridas |
|---|---|
| Panel, admin, datos | Experto con prisa, Accesibilidad |
| Formularios, asistentes | Primera vez, Accesibilidad, Móvil distraído |
| Landing, marketing | Primera vez, Probador de extremos, Móvil distraído |
| Checkout, e-commerce | Móvil distraído, Probador de extremos, Primera vez |
| Primer uso | Primera vez, Móvil distraído |

- **Experto con prisa:** se salta instrucciones, busca atajos y acciones en lote, odia confirmaciones para acciones de bajo riesgo y animaciones lentas.
- **Primera vez:** lee todo, duda antes de hacer clic, interpreta cada etiqueta literal, se pierde con íconos sin texto y jerga.
- **Accesibilidad:** navega solo con teclado o lector de pantalla, usa zoom al 200 %, no ve estados que solo cambian al pasar el mouse ni lo que se comunica solo con color.
- **Probador de extremos:** escribe nombres de 100 caracteres, emojis, pega desde Excel, recarga a la mitad, da doble clic al enviar, abre dos pestañas.
- **Móvil distraído:** una mano, conexión lenta, lo interrumpen a medio flujo; necesita objetivos táctiles de 44 px o más y que no se pierda lo capturado.

Si el `CLAUDE.md` del proyecto describe al usuario real (por ejemplo, "operadores todo el día"), agrega 1 persona derivada de ahí. No inventes datos de audiencia que no estén escritos.

### Severidad

| Nivel | Significa | Acción |
|---|---|---|
| **P0** | Bloquea: la tarea no se puede completar o se pierden datos | Arreglar ya |
| **P1** | Mayor: dificultad o confusión importante | Antes de entregar |
| **P2** | Menor: molesta, pero hay forma de seguir | En la siguiente pasada |
| **P3** | Pulido: sin impacto real | Si hay tiempo |

En duda entre dos niveles: ¿un usuario levantaría un ticket de soporte por esto? Si sí, es P1 o más.

## 4. Reporte

Si el usuario pidió un formato propio, el suyo manda; conserva al menos la línea de método, el tipo de pantalla y la severidad de cada hallazgo. Si no pidió formato, el reporte completo va en el chat, en este orden:

1. **Método** (primera línea): qué se revisó y cómo. Por ejemplo: "Código + capturas a 375/768/1280 + axe", o **"Revisado solo desde código: sin render, contrastes calculados, no medidos"**.
2. **Tipo de pantalla** y por qué.
3. **Puntaje:** tabla de las 10 heurísticas con puntaje y el hallazgo clave de cada una; total sobre el máximo aplicable y su banda.
4. **Veredicto de especificidad:** ¿hecha para este producto o intercambiable? Qué patrones genéricos aparecen.
5. **Impresión general:** qué funciona, qué no y la mayor oportunidad, en 2–3 líneas.
6. **Lo que funciona:** 2–3 cosas concretas y por qué funcionan.
7. **Problemas prioritarios:** 3–5, ordenados. Cada uno lleva:
   - **[P?] Qué:** el problema, con `archivo:línea` o selector.
   - **Por qué importa:** a quién afecta y cómo.
   - **Arreglo:** concreto, no "considera explorar…".
   - **Comando sugerido:** `endurecer`, `textos`, `composicion`, etc.
8. **Resto de hallazgos:** tabla compacta (severidad · dónde · qué · arreglo) con todo lo demás. Nada encontrado se queda fuera por no estar entre los 3–5.
9. **Banderas por persona:** para cada persona elegida, qué se le rompe exactamente en la acción principal.
10. **Preguntas:** van **al final** y no se escribe nada después.

### Preguntas

- Si hay 3 o más problemas prioritarios, haz de 2 a 4 preguntas. Cada una cita hallazgos concretos y ofrece 2–3 opciones:
  - **Dirección:** cuál categoría atacar primero (por ejemplo: flujo roto, estados o ruido visual).
  - **Intención:** si un tono o patrón fue deliberado (por ejemplo: "¿las métricas grandes son requisito del cliente?").
  - **Alcance:** "Solo los P0–P1", "Los 5 prioritarios" o "Todo".
  - **Restricciones (opcional):** qué no se toca.
- Con menos de 3 problemas prioritarios, en lugar de preguntas escribe la línea `Preguntas omitidas: <motivo>`.

Con la respuesta del usuario, propón la secuencia de comandos en orden y cierra con `pulir` como último paso.

## Reglas

- Directo y específico: "el botón Enviar", no "algunos elementos".
- Di qué está mal **y** por qué le importa al usuario.
- Prioriza sin piedad: si todo es importante, nada lo es.
- No suavices la crítica, pero no infles la severidad.
- Si el proyecto tiene reglas de interfaz propias (por ejemplo, no mostrar JSON ni claves internas), revísalas y cítalas.
