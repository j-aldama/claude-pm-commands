# Primer uso y estados vacíos

El trabajo del primer uso no es enseñar el producto: es llevar a la persona lo más rápido posible al momento que demuestra que vale su tiempo.

## 1. Entender

- **El reto:** qué intenta lograr el usuario, dónde se atora y cuál es el momento de "ya entendí" que buscamos.
- **El usuario:** nivel de experiencia, motivación (¿curiosidad o se lo exige el trabajo?), cuánto tiempo tiene.
- **El éxito:** lo mínimo que debe aprender, la acción clave (primer pedido, primer caso) y cómo sabremos que funcionó.

Si falta el "momento de ya entendí", pregúntalo antes de diseñar.

## 2. Principios

- **Mostrar, no contar:** ejemplos que funcionan dentro del producto real, no un modo tutorial aparte.
- **Opcional cuando se pueda:** el experto se lo salta; nunca bloquees el producto.
- **Tiempo al valor:** el 20 % que da el 80 % primero; lo avanzado se descubre en contexto.
- **Contexto antes que ceremonia:** enseña la función cuando se necesita. Los estados vacíos son la mejor oportunidad.
- **Respeta la inteligencia:** nada de explicar lo obvio.

## 3. Estados vacíos

Cada estado vacío tiene:

1. **Qué va a aparecer aquí:** "Aquí verás los pedidos del día".
2. **Por qué importa,** si no es obvio.
3. **Cómo empezar:** un botón con la acción ("Registrar pedido") o una plantilla.
4. **Ayuda opcional:** un enlace corto, no un muro de texto.

Distingue los tipos; no es lo mismo:

| Tipo | Qué decir | Acción |
|---|---|---|
| Primera vez | Qué es y por qué sirve | Crear el primero o usar una plantilla |
| El usuario borró todo | Con poca ceremonia | Crear de nuevo |
| Sin resultados por búsqueda o filtro | Qué se buscó | Cambiar la búsqueda o limpiar filtros |
| Sin permiso | Por qué no lo ve | A quién pedir acceso |
| Error al cargar | Qué pasó | Reintentar |

En Operar, el vacío es sobrio y útil: una línea, una acción. Un estado vacío nunca aparece junto a datos que sí existen.

## 4. Otros patrones

- **Ayudas en contexto:** aparecen la primera vez que se ve la función, apuntan al elemento, se pueden cerrar y no vuelven a salir.
- **Recorridos guiados:** solo para interfaces complejas o cambios grandes; de 3 a 7 pasos como máximo, con "Saltar" visible, repetibles desde la ayuda.
- **Tutoriales interactivos:** solo para tareas de alto riesgo, con datos de ejemplo y un cierre claro.
- Guarda qué ya se vio (en el servidor o en `localStorage`) y respeta lo que el usuario cerró.

## Evitar

- Un recorrido largo obligatorio antes de usar el producto.
- La misma ayuda una y otra vez.
- Bloquear toda la interfaz durante un recorrido.
- Un "Saltar" escondido.
- Mostrar el primer uso a quien regresa.

## Verificar

- ¿Se llega rápido a la primera acción útil?
- ¿Cada estado vacío tiene su tipo correcto y su siguiente acción?
- ¿Se puede saltar y no reaparece?

Después sigue con [pulir.md](pulir.md).
