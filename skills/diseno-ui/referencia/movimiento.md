# Movimiento

El movimiento explica estado, relación y jerarquía, o crea un solo momento con intención que la pantalla se ganó. Decoración sin propósito es deuda.

- **Persuadir y Exhibir:** el movimiento puede cargar la voz. Mejor una secuencia focal ensayada que entradas repetidas en cada sección.
- **Operar y Leer:** el movimiento sirve a la retroalimentación, al estado y a la continuidad. Rápido, y sin coreografías de carga de página.

## 1. Encontrar el trabajo

Revisa el movimiento existente, los estados, los dispositivos y el presupuesto de rendimiento. Anima solo donde el movimiento:

- confirma una acción;
- hace legible un cambio de estado o una relación espacial;
- da continuidad en una navegación o un cambio de layout;
- dirige la atención en un momento importante.

No animes una zona estática solo porque existe.

## 2. Plan breve

Antes de implementar, escribe:

- **Momento focal:** la secuencia que merece intención, si hay alguna.
- **Continuidad:** qué cambios necesitan explicación.
- **Retroalimentación:** qué controles necesitan confirmación.
- **Presupuesto:** qué efectos son caros y cada cuánto corren.

## 3. Duración y curva

| Duración | Uso típico |
|---|---|
| 100–150 ms | Retroalimentación inmediata |
| 150–300 ms | Cambio de estado rutinario |
| 300–500 ms | Layout, overlay o transición de vista |
| 500–800 ms | Entrada focal deliberada (casi nunca en Operar) |

- La salida es más rápida que la entrada.
- Desaceleración natural: `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Sin rebote ni elástico por reflejo.**
- Una retroalimentación larga se siente como lentitud.

## 4. Implementar

- Transiciones y keyframes de CSS para estados y secuencias acotadas. View Transitions o Web Animations API cuando la continuidad es el punto.
- Con HTMX, las clases de swap y settle (`htmx-added`, `htmx-settling`) bastan para la mayoría de los casos; no agregues una librería por un efecto que el stack ya resuelve.
- El contenido es visible por defecto: si el script falla, la página no queda vacía.
- No animes `width`, `height`, `top`, `left` ni márgenes; usa `transform` y `opacity`, o FLIP.
- `will-change` solo durante la animación.
- Los bucles no esenciales (puntos que pulsan, marquesinas) se detienen fuera de pantalla, y en Operar casi siempre sobran.

## 5. Accesibilidad

Toda animación tiene ruta para `prefers-reduced-motion`: quita o reduce el desplazamiento y conserva los cambios de opacidad o color que comunican estado. Movimiento reducido significa menos y más suave, no cero retroalimentación.

## Verificar

- Cada animación explica algo: retroalimentación, estado o relación.
- Interrumpir o repetir la acción funciona bien.
- Teclado y móvil siguen usables.
- La ruta reducida conserva la retroalimentación.
- Quitar cualquier animación perdería significado, no solo adorno.

Después sigue con [pulir.md](pulir.md).
