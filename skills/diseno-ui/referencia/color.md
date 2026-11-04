# Color

El color aporta jerarquía, significado y atmósfera. Conserva los colores confirmados de la marca y las convenciones semánticas; no reemplaces el mundo visual con el pretexto de "darle color".

- **Persuadir y Exhibir:** el color puede cargar la voz y adueñarse de zonas grandes.
- **Operar y Leer:** el color codifica acción, selección, estado, orientación y jerarquía de lectura. Su escasez le da fuerza al acento.

## 1. Revisar antes de elegir

Lee `DESIGN.md`, los tokens (config de Tailwind, variables CSS) y los estados representativos. Identifica:

- qué colores son compromisos de marca;
- los roles actuales de superficie, texto, acción y semántica;
- dónde el gris esconde jerarquía o estado;
- fallas de contraste y cosas comunicadas solo con color;
- si se necesitan tema oscuro o visualización de datos;
- si la petición es más color o una identidad nueva. La identidad nueva es otra conversación: pregunta.

## 2. Estrategia por roles

Nombra la temperatura emocional, la relación dominante, el rango de contraste y la dosis de color. Construye **roles**, no una bolsa de muestras:

- lienzo y superficies elevadas;
- texto primario y secundario;
- acción, foco y selección;
- bordes y separadores;
- éxito, advertencia, error e información;
- categorías o escalas de datos, si las hay.

Usa el espacio de color que ya usa el proyecto. Para una paleta web nueva, OKLCH permite ajustar luminosidad y croma de forma predecible. El tono sale del significado del producto, no de la costumbre de la categoría.

## 3. Aplicar a escala de sistema

- El color más fuerte se adueña de una zona o un rol, no se riega en acentos chiquitos.
- El color de la acción primaria no se gasta en decoración.
- Sobre superficies de color, el texto secundario sale del tono de la superficie o del texto, no de un gris lavado.
- Significados semánticos constantes, respetando las convenciones del dominio.
- En datos, además del color: luminosidad, forma, etiqueta o patrón.
- El tema oscuro se diseña (elevación y contraste explícitos), no se invierte en automático.
- Con sistema de tokens: primitivos más semánticos; el cambio de tema remapea los semánticos.

## Contraste

| Contenido | Mínimo WCAG AA |
|---|---|
| Texto normal | 4.5:1 |
| Texto grande | 3:1 |
| Controles, íconos, anillo de foco | 3:1 |

No te fíes del ojo: mide en hover, foco, deshabilitado, overlays, texto sobre imagen y en ambos temas (axe con `a11y-playwright` o chrome-devtools). Revisa también con simulación de daltonismo. Prefiere colores explícitos a cadenas de transparencias que vuelven el contraste dependiente del fondo.

## Verificar

- Cada color tiene un rol estable o un propósito de atmósfera concreto.
- La atención cae en la acción, el contenido o el estado que se quería.
- La paleta funciona en estados densos, interactivos, de error y vacíos.
- Contraste y señales no cromáticas pasan en todos los estados.
- Se reconoce como este producto, no como un tratamiento "colorido" genérico.

Después sigue con [pulir.md](pulir.md).
