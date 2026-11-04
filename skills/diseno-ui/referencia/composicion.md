# Composición

La composición convierte la prioridad del producto en orden de lectura, agrupación, ritmo y espacio útil. Diagnostica el problema estructural antes de mover cajas.

- **Persuadir y Exhibir:** se vale una composición asimétrica o disruptiva cuando la dirección visual la justifica.
- **Operar y Leer:** estructura predecible, densidad estable y linealidad navegable son funcionalidad, no falta de creatividad.

Preserva el mundo visual: este comando cambia la estructura dentro de él.

## 1. Diagnosticar

Contesta con evidencia del render o del código, a varios anchos y estados:

- **Orden de lectura:** con la vista entrecerrada, ¿se identifican el elemento principal, el secundario y los grupos, en ese orden?
- **Agrupación:** ¿lo relacionado está cerca y lo distinto separado, o hay contenedores compensando una proximidad débil?
- **Ritmo:** ¿los intervalos apretados y los generosos crean una cadencia, o el mismo espaciado se repite hasta que todo pesa igual?
- **Estructura:** ¿la topología corresponde al contenido? ¿Las tarjetas o columnas repetidas son de verdad equivalentes, o es la plantilla del framework?
- **Densidad:** ¿la cantidad de información por zona corresponde a la frecuencia de uso y a la complejidad de la decisión?
- **Adaptación:** en angosto, intermedio, ancho, con zoom y con textos largos, ¿qué se reordena, colapsa o desborda? ¿El orden del DOM y del foco coincide con el visual?
- **Extremos:** contenido largo, vacíos, overlays, elementos fijos, objetivos táctiles chicos.
- **Relleno:** ¿hay contenedores con 4–8 px de padding donde el texto toca los bordes?

## 2. Definir la tesis espacial

Antes de editar, nombra: el camino principal de lectura o tarea, qué va junto y qué se separa, qué elemento manda y cuál apoya, la densidad y el ritmo, y cómo cambia la estructura por ancho y por método de entrada. Elige el modelo estructural más simple que exprese esas relaciones.

## 3. Aplicar

- Agrupa por significado: proximidad antes que contenedores o decoración.
- Ritmo por contraste deliberado entre intervalos apretados y generosos.
- Escala de espaciado documentada (base 4: 4, 8, 12, 16, 24, 32, 48…) en lugar de valores sueltos.
- Jerarquía según la prioridad del producto, no según el framework.
- Lo responsive es estructural: reordenar, colapsar o revelar según lo que sigue siendo importante.
- `gap` para el ritmo entre hermanos.
- Objetivos táctiles de 44 px aunque la marca visible sea más chica.
- Profundidad solo cuando aclara estado o jerarquía.
- Correcciones ópticas solo después de ver el render.

La variación no es meta: la repetición ayuda a reconocer. Rómpela solo cuando cambian el contenido o la prioridad.

## Verificar

- Con la vista entrecerrada se siguen viendo el principal, el secundario y los grupos.
- El camino de la tarea es claro en cada tamaño.
- El espaciado tiene ritmo, no monotonía.
- Textos largos, vacíos, zoom y contenido dinámico no rompen la estructura.
- El orden de teclado y lector de pantalla coincide con el visual.

Después sigue con [pulir.md](pulir.md).
