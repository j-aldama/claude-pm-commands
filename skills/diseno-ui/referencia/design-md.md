# DESIGN.md: documentar y extraer

`DESIGN.md` en la raíz del proyecto captura el sistema visual para que cualquier agente que genere pantallas nuevas se mantenga dentro de la marca. Sigue el formato abierto de DESIGN.md (https://github.com/google-labs-code/design.md): frontmatter YAML con los tokens, seguido de hasta ocho secciones en orden fijo. **Los tokens son normativos; la prosa explica cómo aplicarlos.**

## Cuándo

- El proyecto tiene un sistema visual coherente pero no tiene `DESIGN.md`.
- Se terminó la primera implementación de una dirección nueva.
- El `DESIGN.md` existente se quedó atrás del código.
- Antes de un rediseño grande, para guardar el estado actual.

Si ya existe un `DESIGN.md`, **no lo sobrescribas**: muéstralo y pregunta si se refresca, se reemplaza o se combina.

## 1. Encontrar los valores

En este orden:

1. Config de Tailwind (`theme.extend`: colors, fontFamily, spacing, borderRadius, boxShadow).
2. Variables CSS (`--color-*`, `--font-*`, `--radius-*`, `--shadow-*`) en la hoja global.
3. Archivos de tokens (`tokens.json`, Style Dictionary) o temas de CSS-in-JS.
4. Componentes base: botón, tarjeta, input, navegación, diálogo, tabla. Anota radio, color, hover, foco y padding.
5. El render: si hay navegador, lee estilos calculados de `body`, `h1`, `a`, `button` y `.card`. Atrapa valores que los tokens no tienen.

## 2. Armar el frontmatter

Solo lo que el proyecto **usa de verdad**: nada de tokens inventados ni escalas vacías.

```yaml
---
name: <nombre del proyecto>
description: <una línea>
colors:
  marca-rojo: "#f40009"
  tinta: "#222222"
  superficie: "#ffffff"
typography:
  titulo:
    fontFamily: "system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.25
  cuerpo:
    fontFamily: "system-ui, sans-serif"
    fontSize: "1rem"
    lineHeight: 1.5
rounded:
  sm: "4px"
  md: "8px"
spacing:
  sm: "8px"
  md: "16px"
components:
  boton-primario:
    backgroundColor: "{colors.marca-rojo}"
    textColor: "{colors.superficie}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
---
```

- Las referencias usan `{ruta.al.token}`. Los componentes pueden referir primitivos; los primitivos no se refieren entre sí.
- Los colores aceptan cualquier color CSS válido. Conserva el formato que el proyecto ya usa como fuente (hex u OKLCH) y no lo dupliques con otro valor en la prosa.
- Los subtokens de componente se limitan a: `backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height` y `width`. Sombras, foco y movimiento van en la prosa.
- Usa los nombres que el proyecto ya tiene; no los renombres a los de Material.
- Las variantes son una convención de nombres: `boton-primario`, `boton-primario-hover`.

## 3. Preguntar lo cualitativo

Lo que no se puede extraer se pregunta, en rondas de máximo 3 preguntas, con opciones concretas:

- una metáfora que resuma el sistema ("La bitácora del operador");
- el tono: 2–3 adjetivos y lo que el sistema rechaza;
- nombres descriptivos para los colores principales;
- la filosofía de elevación: plano, por capas o con sombras;
- la sensación de los componentes en una frase.

## 4. Escribir

Las secciones van en este orden, con sus encabezados canónicos en inglés para que otras herramientas las lean, y el contenido en el idioma del proyecto:

1. `## Overview`: la metáfora, la personalidad, la densidad y la lista de características clave.
2. `## Colors`: cada color con su nombre descriptivo, su valor y **dónde y por qué** se usa. Opcional: reglas con nombre ("Regla del rojo escaso: el rojo de marca ocupa menos del 10 % de una pantalla").
3. `## Typography`: familias, roles con peso, tamaño e interlineado, y la medida de lectura.
4. `## Layout`: rejilla, contenedores, breakpoints, escala de espaciado y densidad.
5. `## Elevation & Depth`: sombras con su valor exacto y cuándo se usan, o "sin sombras" y cómo se expresa la profundidad.
6. `## Shapes`: radios, bordes y recortes.
7. `## Components`: el comportamiento de cada componente, incluidos hover, foco y deshabilitado.
8. `## Do's and Don'ts`: lo que sí y lo que no, concreto.

Omite las secciones que no apliquen; no las llenes con reglas inventadas.

## Extraer patrones

Cuando el objetivo es mover patrones repetidos al sistema:

1. Encuentra dónde vive el sistema (componentes compartidos, includes de plantillas, tokens). Si no existe, pregunta dónde debe vivir antes de crearlo.
2. Extrae solo lo que se usa **3 o más veces con la misma intención**: componentes repetidos, valores escritos a mano que deberían ser tokens, variaciones inconsistentes del mismo concepto, combinaciones de tamaño, peso e interlineado que se repiten. Una abstracción prematura es peor que la duplicación.
3. Planea: qué componentes, qué tokens, qué variantes, qué nombres (siguiendo los del proyecto) y cómo migrar los usos actuales.
4. Migra todos los usos, verifica que se vean y funcionen igual, y borra las implementaciones viejas.
5. Actualiza `DESIGN.md`.

No extraigas cosas que se parecen pero sirven a propósitos distintos, ni crees un token para cada valor.
