# Pulir

Pulir es refinar, nunca rediseñar a escondidas. Conserva el mundo visual, el contenido, el comportamiento y todo lo que está fuera del alcance. Si el concepto está mal, dilo y recomienda rediseño o `audaz`; no metas un reemplazo disfrazado.

## 1. Entender el sistema

Lee el `DESIGN.md`, los tokens (config de Tailwind, variables CSS), los componentes compartidos y las pantallas vecinas. Si no hay sistema formal, sigue las convenciones coherentes del proyecto.

Clasifica cada desviación antes de corregirla:

- **Falta un token:** el sistema necesita un valor reutilizable.
- **Implementación suelta:** ya existe un componente o patrón compartido que debe reemplazarla.
- **Desajuste de concepto:** el flujo o la jerarquía difieren de las áreas comparables del producto.
- **Defecto local:** simplemente está incompleto o inconsistente.

Corrige la causa en el nivel más estrecho correcto. Pregunta cuando un principio del sistema no se pueda inferir.

## 2. Juntar evidencia

Usa la pantalla tú mismo a los tamaños reales (375, 768 y 1280 px). Determina:

- si el flujo está completo;
- el nivel de calidad esperado y el tiempo disponible;
- qué está incompleto a propósito;
- qué estados, longitudes de contenido, roles y métodos de entrada va a encontrar el usuario.

Si hubo una `critica` en esta conversación, toma sus P0 y P1 como entrada, y aun así haz tu propia pasada.

## 3. Triage

Arregla en este orden:

1. Tareas rotas o bloqueadas, pérdida de datos, estado engañoso, rutas inaccesibles.
2. Estados faltantes: cargando, vacío, error, éxito, deshabilitado, sin permiso.
3. Flujo, jerarquía, responsive y desviaciones del sistema.
4. Inconsistencias visuales y de movimiento.
5. Limpieza de código y recursos.

No perfecciones una esquina dejando el resto abajo del mismo nivel.

## 4. Pulir el recorrido completo

**Flujo y jerarquía**
- Los mismos términos, patrones de guardado y modelos mentales que las pantallas vecinas.
- La tarea principal y el estado actual son obvios, sin aplanar todo al mismo peso.
- Llegada, transición, vacío y recuperación se conectan; no son pantallas aisladas.

**Composición y tipografía**
- Alineado a la rejilla y a la escala de espaciado del proyecto; corrige la alineación óptica, no solo la matemática.
- Lo relacionado, junto; lo distinto, separado con generosidad.
- El mismo rol de texto se ve igual en todas partes; prueba medida, cortes de línea, zoom y carga de fuentes.

**Color, imágenes e íconos**
- Tokens semánticos y significados de color estables.
- Contraste de texto, controles y foco en **cada** estado.
- Una sola familia de íconos, con el mismo grosor y tamaño.
- Las imágenes no mueven el layout al cargar: proporción declarada y `alt` útil.

**Interacción y estado**
- Cada control tiene estado normal, hover, foco, activo, deshabilitado, cargando, error y éxito.
- Foco visible, orden lógico de tabulación, etiquetas, objetivos táctiles adecuados.
- Movimiento coherente e interrumpible; no agregues animación para que "se note" el pulido.

**Contenido y código**
- Términos, mayúsculas y puntuación consistentes. Pregunta antes de cambiar afirmaciones.
- Quita salidas de depuración, código muerto, imports sin uso y estilos obsoletos.
- Reemplaza implementaciones sueltas con componentes compartidos cuando el sistema ya tiene el patrón.
- Promueve a token solo lo que de verdad se reutiliza.

## 5. Verificar y cerrar

Recorre el flujo completo otra vez con mouse, teclado y touch. Revisa:

- layouts angosto, intermedio y ancho;
- estados de carga, vacío, error, éxito, deshabilitado, contenido largo y contenido faltante;
- zoom, contraste, foco y nombres accesibles (axe con `a11y-playwright` si el proyecto lo tiene);
- errores de consola, saltos de layout e imágenes;
- acuerdo con `DESIGN.md`, las pantallas vecinas y el alcance pedido.

Cierra revisando el diff: quita cambios accidentales, código huérfano, valores redundantes y archivos temporales. Se entrega solo cuando el flujo está completo y parejo en todo el recorrido.
