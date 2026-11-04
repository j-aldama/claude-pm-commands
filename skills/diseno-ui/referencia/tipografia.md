# Tipografía

La tipografía carga información, jerarquía y voz. Mejórala dentro del mundo visual existente; no reemplaces la identidad salvo que lo pidan (en ese caso, actualiza `DESIGN.md`).

- **Persuadir y Exhibir:** el tipo de exhibición puede cargar la voz, con contraste decidido y escala que responde al espacio.
- **Operar y Leer:** primero estabilidad, escaneo y medida. Una familia bien ajustada y una escala fija por rol suelen bastar.

## 1. Diagnosticar

Contesta cada punto con un archivo, un selector o un valor calculado:

- **Fuentes:** ¿qué familias, pesos y roles hay? ¿Se eligieron o son las de por omisión? ¿Cada familia hace falta?
- **Jerarquía:** ¿se distinguen de un vistazo título, cuerpo, etiqueta, metadato y dato? ¿Hay tamaños o pesos vecinos demasiado parecidos para trabajos distintos?
- **Escala:** ¿es una escala deliberada o una colección de valores sueltos? ¿El mismo rol se ve igual en todas las pantallas?
- **Lectura:** ¿el cuerpo está entre 45 y 75 caracteres por línea? ¿El interlineado, el contraste y el tracking están ajustados a la fuente y al ancho reales?
- **Estrés:** títulos largos, textos en español (más largos), zoom, contenedores angostos, fuente que no cargó.
- **Entrega:** ¿se cargan solo los pesos usados? ¿Hay respaldo con métricas parecidas para evitar texto invisible y saltos?

## 2. Definir el sistema

Antes de editar, escribe: los roles que necesita la interfaz, el contraste entre ellos, la medida y densidad, qué fuentes y pesos son los oficiales, y las restricciones de rendimiento o accesibilidad. Usa la menor cantidad de roles y familias que haga la jerarquía inconfundible. Combina tamaño, peso, espacio y tono; no le pidas todo al tamaño. Los tokens se nombran por propósito (`titulo-seccion`), no por valor (`text-22`).

## 3. Aplicar

- Cuerpo de 16 px (1rem) como piso en web, salvo un rol denso justificado.
- Prosa entre 45 y 75 caracteres; a líneas más anchas, más interlineado.
- Texto claro sobre fondo oscuro: un poco más de interlineado, de tracking y, si la fuente lo pide, un paso más de peso.
- Números tabulares en tablas y cifras que se comparan.
- Respeta el zoom del navegador y la configuración de fuente del usuario.
- Ritmo de párrafo con espacio **o** sangría, no ambos.
- No agregues una segunda familia sin un rol que solo ella pueda cumplir.

## Cortes de línea

- `text-wrap: balance` en títulos y bloques cortos centrados; `text-wrap: pretty` en cuerpo. Si el navegador no los soporta, queda el corte normal.
- En una columna demasiado angosta para que ayuden, edita el texto o ensancha la columna.
- Un corte a mano en un título va solo entre frases, y se revisa en cada ancho: un corte que cae a mitad de línea en el teléfono es peor que el corte normal.

## Verificar

- Los roles primario, secundario, cuerpo y metadato se reconocen sin leer el texto.
- El texto largo se lee cómodo en todos los anchos.
- No hay texto invisible ni saltos fuertes al cargar fuentes.
- El zoom, el foco y el contraste siguen funcionando.

Contesta cada punto con evidencia del render o del código, no con un "sí". Después sigue con [pulir.md](pulir.md).
