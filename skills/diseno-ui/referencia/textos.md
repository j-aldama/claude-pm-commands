# Textos de interfaz

Reescribe el texto confuso para que el usuario entienda qué pasó, qué importa y qué hacer. Conserva el significado, los términos del negocio y la voz de la marca. Para México, español mexicano.

## 1. Revisar el lenguaje

Lee el recorrido completo, no frases sueltas. Busca:

- sustantivos, verbos y acciones ambiguos;
- jerga interna o conocimiento que se da por hecho;
- etiquetas, resultados y estados vagos;
- consecuencias, salida o tiempos que faltan;
- términos o mayúsculas inconsistentes;
- títulos, introducciones, ayudas y confirmaciones redundantes;
- texto que se rompe a anchos reales;
- tono que ignora el estrés, el riesgo o la urgencia del momento.

Pregunta antes de cambiar afirmaciones, sentido legal o un término que puede ser del negocio.

## 2. Jerarquía del mensaje

Para cada estado decide:

1. el único dato que el usuario necesita ahora;
2. la acción disponible;
3. el contexto que cambia la decisión;
4. el tono adecuado.

Cada idea se dice una vez. Si el título ya explica el estado, la introducción aporta algo nuevo o desaparece.

## 3. Reescribir por función

**Acciones y navegación**
- Verbo + objeto cuando el resultado no es obvio: "Asignar repartidor", no "Enviar"; "Ver pedido A-1042", no "Click aquí".
- La etiqueta dice qué va a pasar, no el gesto.
- Mismo verbo y mismo sustantivo para el mismo concepto en todo el producto.
- Acciones destructivas: nombra el objeto y la consecuencia. Prefiere deshacer a confirmar cuando la recuperación es segura. Si hay confirmación, el botón repite la acción ("Eliminar pedido"), nunca "Sí", "OK" o "Aceptar".

**Formularios**
- Etiquetas persistentes; el placeholder es un ejemplo, no la etiqueta.
- Requisitos de formato **antes** de enviar.
- Requerido y opcional marcados de forma consistente.
- La validación dice qué corregir y cómo, sin culpar: "Escribe el teléfono a 10 dígitos", no "Teléfono inválido".

**Errores y permisos**

Un error útil contesta:
1. qué falló;
2. por qué, si se sabe y sirve;
3. cómo salir o qué alternativa queda.

- Nunca códigos internos, trazas ni claves técnicas como mensaje principal.
- No prometas una causa o una solución que el sistema no conoce.
- En pagos, borrados, privacidad o pérdida de acceso: serio; nada de chistes.

**Carga, vacío y éxito**
- La carga nombra la operación real ("Buscando repartidores disponibles…"). Progreso determinado solo si existe; nunca inventado.
- El vacío distingue primera vez, sin resultados, filtros activos, sin permiso y falla, y da la siguiente acción. Ver [primer-uso.md](primer-uso.md).
- El éxito confirma el resultado en pocas palabras; menciona lo que sigue solo si cambia lo que el usuario debe hacer.

**Ayuda**
- La ayuda contesta una pregunta implícita, no repite el control.
- El detalle poco común va en revelación progresiva.
- Los enlaces se entienden fuera de contexto; los botones de solo ícono tienen nombre accesible.

## 4. Voz, accesibilidad y localización

- La voz es constante; el tono se adapta al momento.
- Mensajes completos, no fragmentos concatenados; las variables quedan en su lugar ("Se asignaron {n} pedidos").
- Plurales reales: "1 pedido" y "3 pedidos".
- `alt` transmite la información de la imagen; vacío si es decorativa.
- El nombre accesible coincide con la etiqueta visible.
- Ni la puntuación, ni el color, ni el ícono cargan el mensaje solos.
- Si la inconsistencia abarca todo el producto, propón un glosario corto de términos.

## 5. Verificar

- Se entiende sin conocimiento oculto del producto.
- Errores, vacíos y decisiones dicen qué hacer.
- Datos exactos y términos consistentes.
- Se escanea bien a los anchos reales y con zoom al 200 %.
- Aguanta nombres largos, plurales y valores dinámicos.
- El tono va con la consecuencia.

El texto final es tan corto como se pueda sin perder significado ni salida. Después sigue con [pulir.md](pulir.md).
