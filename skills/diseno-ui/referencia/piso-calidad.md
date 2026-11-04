# Piso de calidad

Léelo justo antes de editar una interfaz, aunque sea un ajuste chico. Aplícalo sin anunciar la lista. El brief o el sistema visual del proyecto pueden pasar por encima de cualquier punto de "Se rechaza por defecto"; tu costumbre no.

## Verificar sobre lo renderizado

Son comprobaciones del resultado, no intenciones. Hazlas juntas en cada vistazo al render, no una captura por ajuste.

- **Contraste:** texto normal y placeholders ≥ 4.5:1; texto grande ≥ 3:1; controles, íconos y anillo de foco ≥ 3:1. Sobre fondos de color, el texto secundario se tiñe del tono del fondo o del texto principal; **nunca gris sobre color**.
- **Profundidad:** las sombras tienen desplazamiento y desenfoque suave. Un halo de color sin desplazamiento es decoración.
- **Espaciado:** grupos apretados, separación generosa entre grupos, más espacio arriba de un título que abajo. Lee los valores calculados.
- **Tipografía:** cuerpo a 65–75 caracteres por línea; títulos de exhibición de 6rem como máximo; tracking no menor a -0.04em; títulos balanceados (`text-wrap: balance`); pasos de tamaño y peso evidentes. Prueba con el texto real en cada breakpoint y corrige lo que se desborde.
- **Movimiento:** un momento con intención, no efectos regados ni la misma entrada en cada sección. Desaceleración exponencial, partiendo de un estado ya visible. Ver [movimiento.md](movimiento.md).
- **Estados:** hover, deshabilitado, cargando, error y vacío. Además, contenido real, controles que funcionan, composición responsive y foco de teclado visible.
- **Superficies del navegador:** selección de texto, cursor de texto, scrollbars, anillos de foco, subrayado de enlaces y números en tablas salen con los valores por omisión del navegador. Dales el tono de la paleta. Es la señal más barata de que la página se construyó y no se ensambló, y la que más se olvida.
- **Textos:** el lenguaje del producto. Los controles nombran su acción; los errores nombran el problema y cómo salir. Ver [textos.md](textos.md).
- **Cobertura:** cada requisito del brief está presente y se encuentra en segundos.

## Nunca

Estas no dependen del gusto: rompen el uso.

- Quitar el foco visible (`outline: none` sin reemplazo con `:focus-visible`).
- Comunicar algo solo con color (verde y rojo sin texto ni forma).
- Texto gris sobre fondo de color.
- Contenido invisible en reposo que depende de un script o animación para aparecer.
- Datos, cifras o testimonios inventados presentados como reales. Los valores de ejemplo se etiquetan como tales.

## Se rechaza por defecto

Son los reflejos de la categoría. El brief puede pedir cualquiera; usarlos cuando nadie los pidió significa que no se decidió. Si reconoces uno, reescribe el elemento, no lo suavices.

**Andamios de página**
- Tarjetas iguales de ícono + título + texto como estructura de la página. **Tarjetas dentro de tarjetas: siempre mal.**
- La plantilla de "métrica héroe": número grande, etiqueta chica, estadísticas de apoyo, acento.
- Una etiqueta o "kicker" en mayúsculas arriba de cada título. El título se sostiene solo.
- Números de sección (01 / 02 / 03), salvo que la secuencia sea información que el lector necesita.
- Un modal para una tarea que no necesita interrumpir ni proteger el foco.

**Hábitos de superficie**
- Texto con degradado. El énfasis sale del peso o del tamaño.
- Vidrio y desenfoque como decoración.
- Borde lateral de color de más de 1 px en tarjetas, elementos de lista, avisos o alertas.
- Sombras duras desplazadas (`box-shadow: 4px 4px 0`) fuera de una estética neobrutalista elegida a propósito.
- Sparklines, anillos de progreso y rectángulos con sombra suave haciendo de contenido.
- Monoespaciada como disfraz de "técnico" en lugar de para código o datos.
- Emojis o glifos Unicode en lugar de un sistema de íconos. Los íconos salen de una librería real o de SVG propio, con un solo grosor y estilo.
- Claro u oscuro elegido por la categoría. Se elige por la escena de uso: quién, dónde y con qué luz.
- Paleta morado-azul o crema genérica cuando el proyecto tiene marca propia.
- Borde de 1 px más sombra amplia en la misma tarjeta: declara la elevación una sola vez, borde **o** sombra.
- Radios de tarjeta exagerados: 12–16 px. Las píldoras son para controles chicos.
- Fondos con rayas (`repeating-linear-gradient`) o cuadrícula sin un lienzo, mapa o plano real debajo.
- Ilustraciones armadas con formas geométricas o SVG "a mano alzada" imitando una ilustración real.

Este piso es el mínimo, no el techo: con todo en verde, el esfuerzo va a lo que hace única a la pantalla.
