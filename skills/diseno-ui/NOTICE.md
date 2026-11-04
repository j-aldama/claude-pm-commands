# Origen y licencia

Esta skill adapta material de **Impeccable** (https://github.com/pbakaus/impeccable), de Paul Bakaus, publicado bajo licencia Apache 2.0. La copia de la licencia está en `LICENSE`.

- Versión de origen: Impeccable 4.8.0, commit `2c95b19` del 4-nov-2026.
- Impeccable, a su vez, partió de la skill `frontend-design` de Anthropic.

## Qué se cambió

- Se tradujo al español mexicano y se condensó.
- Se tomaron solo estas guías: los modos de pantalla, `craft-floor`, `critique`, `harden`, `polish`, `clarify`, `onboard`, `bolder`, `quieter`, `distill`, `typeset`, `layout`, `colorize`, `animate`, `document` y `extract`.
- Se quitaron todas las dependencias de su motor: el binario `impeccable`, los hooks, el modo live, la telemetría, el catálogo remoto de direcciones, la persistencia de críticas en `.impeccable/` y `PRODUCT.md`.
- Las prohibiciones de gusto que eran absolutas ahora son "se rechazan por defecto": el brief puede pedirlas.
- La revisión formal de accesibilidad y la de rendimiento se delegan a las herramientas que ya usamos (axe-core y Lighthouse).
- Los casos de internacionalización se enfocaron en `es-MX`.
