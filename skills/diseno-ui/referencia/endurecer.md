# Endurecer

Una interfaz que solo funciona con datos perfectos no está lista. Endurece contra las entradas, errores, idiomas y redes que el usuario real va a traer.

## 1. Diagnosticar

Recorre la pantalla con cada grupo y anota qué se rompe, con `archivo:línea`.

**Entradas extremas**
- Texto muy largo: razones sociales tipo "Abarrotes y Misceláneas La Esperanza del Norte S.A. de C.V.", correos largos, descripciones de 500 caracteres.
- Texto muy corto o vacío: un carácter, campo opcional sin llenar.
- Caracteres especiales: acentos, ñ, emojis, comillas, texto pegado desde Excel con tabuladores.
- Números grandes: millones, montos con centavos, negativos.
- Muchos elementos: listas de 1,000+ filas, selects de 50+ opciones.
- Ningún dato: estado vacío.

**Errores**
- Red: sin conexión, lenta, tiempo agotado.
- Respuestas del servidor: 400, 401, 403, 404, 409, 429 y 500.
- Validación, permisos y operaciones simultáneas (dos pestañas o dos usuarios editando).

**Idioma y formato (`es-MX` por defecto)**
- Español ocupa 20–30 % más que inglés: nada de anchos fijos en botones y etiquetas.
- Fechas dd/mm/aaaa o "4 nov 2026"; hora de 12 h o 24 h según la convención del producto, pero consistente.
- Moneda `$1,234.56` con coma de miles y punto decimal; aclara MXN o USD cuando conviva más de una.
- Plurales correctos: "1 pedido" y "2 pedidos", nunca "pedido(s)".
- Si el producto soporta otros idiomas o escritura de derecha a izquierda, usa propiedades lógicas (`margin-inline-start`) y las APIs `Intl`.

## 2. Arreglar por dimensión

### Desborde de texto
- Una línea con elipsis: `overflow: hidden; text-overflow: ellipsis; white-space: nowrap;` (en Tailwind, `truncate`) más un `title` con el texto completo.
- Varias líneas: `line-clamp-2` o `line-clamp-3`.
- Permitir que corte: `overflow-wrap: anywhere` (en Tailwind, `break-words`).
- Hijos de flex o grid que no se encogen: `min-width: 0` (en Tailwind, `min-w-0`).
- Cuerpo de 16 px como piso; 14 px solo para texto realmente secundario. iOS hace zoom en inputs de menos de 16 px.
- Prueba con zoom al 200 %: los contenedores crecen con el texto.

### Errores
- Cada error dice qué falló, por qué (si se sabe y sirve) y cómo salir. Ver [textos.md](textos.md).
- Nunca códigos crudos ("Error 500") como mensaje principal, ni trazas, ni JSON.
- Botón de reintentar en fallas de red; el error no borra lo capturado.
- Por estatus:

| Estatus | Respuesta en pantalla |
|---|---|
| 400 o 422 | Errores junto a cada campo |
| 401 | Llevar a iniciar sesión y regresar a donde estaba |
| 403 | Explicar que no tiene permiso y a quién pedirlo |
| 404 | Estado de "no encontrado" con salida |
| 409 | Avisar del conflicto y ofrecer recargar sin perder lo escrito |
| 429 | Pedir que espere, con el tiempo si se conoce |
| 500 | Mensaje genérico humano, reintentar y a quién avisar |

- Un componente que falla no tumba toda la pantalla.

### Estados límite
- **Vacío:** primera vez, sin resultados por filtro, sin permiso o error de carga. Cada uno es distinto y lleva su siguiente acción. Ver [primer-uso.md](primer-uso.md).
- **Cargando:** di qué se está cargando; usa esqueletos en listas y tablas.
- **Muchos datos:** paginación o scroll virtual, búsqueda y filtros; nunca cargar 10,000 filas.
- **Doble envío:** deshabilita el botón mientras se procesa y muestra que se está procesando. En HTMX, `hx-disabled-elt="this"` con `hx-indicator`; en JS, desactívalo hasta que haya respuesta. Del lado del servidor, que la operación aguante repetirse (llave de idempotencia o validación de duplicado).
- **Condiciones de carrera:** ignora respuestas viejas (aborta la petición anterior al teclear en una búsqueda).
- **Permisos:** sin permiso de ver, sin permiso de editar o solo lectura, siempre con la explicación de por qué.
- **Gestos interrumpidos** (deslizadores y arrastres propios): con `pointercancel`, `lostpointercapture` o `blur` se limpia el estado de arrastre, y el siguiente gesto funciona sin recargar.

### Validación
- En el cliente: requeridos, formato, longitud, con el formato explicado **antes** de enviar (`aria-describedby`).
- En el servidor, **siempre**: nunca confiar solo en el cliente.
- Etiquetas persistentes; el placeholder es un ejemplo, no la etiqueta.

### Accesibilidad
- Todo funciona con teclado, en orden lógico, con foco visible.
- Los cambios dinámicos se anuncian: `role="status"` para éxito y `role="alert"` para errores.
- Nada se comunica solo con color.
- La revisión formal con axe va con `a11y-playwright`.

### Red lenta
- Esqueletos, actualizaciones optimistas con reversa si falla, y búsqueda con debounce de unos 300 ms.
- Limpia listeners, timers y peticiones pendientes al salir de la vista.

## 3. Verificar

Prueba cada uno y di con qué se probó (navegador, viewport emulado o dispositivo real) y qué quedó sin probar:

- Nombre de 100+ caracteres en cada campo de texto visible.
- Emojis y acentos en cada campo.
- Red apagada y red lenta (perfil 3G en devtools).
- Lista con 1,000+ elementos.
- Clic 10 veces seguidas en enviar.
- Cada estatus de error forzado.
- Todos los datos borrados: estado vacío.
- Zoom al 200 % y navegación solo con teclado.

Cuando los extremos estén cubiertos, sigue con [pulir.md](pulir.md).
