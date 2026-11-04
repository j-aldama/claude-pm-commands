# Tipos de pantalla

El tipo dice cómo se ve el éxito del visitante en **esta** pantalla. Se elige por la pantalla, no por el producto: la landing de una herramienta es Persuadir; la documentación de una marca de moda es Leer.

| Tipo | El visitante… | Ejemplos | La ambición se nota en… |
|---|---|---|---|
| **Operar** | completa una tarea | paneles, admin, CRUD, configuración, herramientas internas | precisión, consistencia, densidad útil |
| **Leer** | entiende algo | documentación, guías, artículos, ayuda, changelog | medida de lectura, estructura, navegación |
| **Persuadir** | decide y actúa | landing, campañas, precios, marketing | un punto de vista claro, una acción visible |
| **Exhibir** | está dentro de la obra | portafolio, galería, showcase | la obra manda desde el primer vistazo |

En Persuadir y Exhibir se va con todo: trabajo con carácter, distinto a la plantilla de la categoría. En Operar y Leer, la ambición es precisión y contención, y los patrones que el visitante ya conoce se quedan.

## Operar a fondo

**La prueba:** alguien que usa herramientas de esta categoría debe poder confiar en la interfaz al instante, sin detenerse en cada componente "raro". La falla típica no es lo plano, es lo extraño sin motivo: botones decorados, controles inventados, movimiento gratuito, fuentes de exhibición en etiquetas.

**Tipografía**
- Una sola familia suele bastar: títulos, botones, etiquetas, cuerpo y datos.
- Escala fija en `rem`, no fluida. Razón entre pasos de 1.125 a 1.2.
- Prosa a 65–75 caracteres por línea; tablas y datos pueden ser más densos.
- Números tabulares (`font-variant-numeric: tabular-nums`) en columnas de cifras.

**Color**
- Contenido por defecto. El acento es para acción primaria, selección actual y estados, no para decorar.
- Vocabulario de estados estandarizado: hover, foco, activo, deshabilitado, seleccionado, cargando, error, advertencia, éxito, información.
- Una segunda capa neutra para barras laterales, barras de herramientas y paneles.
- Sin colores saturados en elementos inactivos.

**Composición**
- Lo responsive es estructural: colapsar la barra lateral, tabla adaptable, columnas por breakpoint. No tipografía fluida.
- Patrones estándar permitidos: barra superior más navegación lateral, migas, pestañas, paleta de comandos.
- Se vale la densidad: tablas con muchas filas, paneles con muchas etiquetas.

**Componentes**
- Cada control interactivo tiene estado normal, hover, foco, activo, deshabilitado, cargando y error.
- Esqueletos para carga en lugar de spinners en medio del contenido.
- Estados vacíos que enseñan qué hacer, no "No hay datos".
- Mismo botón para la misma acción en todas las pantallas. Si "Guardar" se ve distinto en dos lugares, uno está mal.
- Los menús desplegables escapan de su contenedor: `<dialog>`, el popover API o `position: fixed`, nunca recortados por `overflow: hidden`.

**Movimiento**
- 150–250 ms en casi todas las transiciones.
- El movimiento comunica estado: cambio, retroalimentación, carga, aparición. Nada más.
- Sin coreografías de carga de página: el usuario entra a trabajar.

**Se rechaza en Operar**
- Movimiento decorativo.
- Componentes inconsistentes entre pantallas.
- Fuentes de exhibición en etiquetas, botones o datos.
- Reinventar controles estándar (scrollbars, modales o formularios "creativos").
- Modal como primera idea: agota antes las opciones en línea.
- La plantilla de "métrica héroe" (número gigante, etiqueta chiquita, gráfica decorativa) como estructura de un panel de trabajo.

## Leer a fondo

- La pregunta del lector manda; la orientación nunca se pierde: dónde estoy, a dónde sigo.
- Columna de lectura tranquila: cuerpo alrededor de 16 px, 60–75 caracteres por línea, buen contraste.
- El carácter de la marca va en el marco (encabezado, navegación, aperturas de sección, cómo se ven código y tablas), no dentro de la columna.
- Monoespaciada solo para código, parámetros y etiquetas cortas.

## Persuadir a fondo

- La primera vista hace la oferta entendible y deseable, muestra una acción clara y demuestra algo que solo este producto puede probar.
- La acción es la que el visitante vino a hacer, en su forma real: buscar vuelos, agendar cita, agregar al carrito. Un enlace decorativo hacia otra página no cuenta.
- La plantilla de la categoría (titular sobre subtítulo y botón, fila de tarjetas iguales debajo) es el punto de partida a evitar, no la meta.
- Imágenes reales cuando el brief las pide; nada de ilustraciones armadas con formas genéricas.

## Exhibir a fondo

- La obra manda desde la primera vista; la interfaz se hace a un lado.
- Una decisión por pantalla (qué pieza abrir), no filtros, orden y etiquetas a la vez.
