---
name: generar-pdf
description: Genera un PDF profesional a partir de un archivo Markdown usando md-to-pdf-engine (Puppeteer + Marked)
argument-hint: "[ruta/archivo.md] [--template plantilla] [--cover] [--size A4|Letter]"
allowed-tools: Bash, Read
---

# Generador de PDF desde Markdown

Convierte un archivo `.md` a PDF profesional con [md-to-pdf-engine](https://github.com/j-aldama/md-to-pdf-engine).

## Requisito

El motor debe estar clonado y compilado, con su ruta en la variable de entorno `MD_PDF_ENGINE`:

```bash
git clone https://github.com/j-aldama/md-to-pdf-engine.git
cd md-to-pdf-engine && npm install && npm run build
export MD_PDF_ENGINE="$PWD"   # agrégalo a tu ~/.zshrc o ~/.bashrc
```

Si `MD_PDF_ENGINE` no está definida o `"$MD_PDF_ENGINE/dist/cli.js"` no existe, detente y dile al usuario cómo instalarlo; no busques el motor en otras rutas.

## Instrucciones

1. El usuario proporciona la ruta a un archivo `.md` en `$ARGUMENTS`.
2. Si no especifica plantilla, usa `tecnica-documentacion` para documentos técnicos o `corporativa-clasica` para reportes.
3. Ejecuta el CLI del motor desde su carpeta (necesita sus `node_modules`):

```bash
cd "$MD_PDF_ENGINE" && node dist/cli.js generate $ARGUMENTS
```

### Ejemplos de uso

```bash
# Básico: genera el PDF junto al .md
cd "$MD_PDF_ENGINE" && node dist/cli.js generate /ruta/al/archivo.md --template tecnica-documentacion

# Con portada y plantilla corporativa
cd "$MD_PDF_ENGINE" && node dist/cli.js generate /ruta/archivo.md --template corporativa-clasica --cover

# Con salida específica
cd "$MD_PDF_ENGINE" && node dist/cli.js generate /ruta/archivo.md --output /ruta/salida.pdf

# Horizontal en tamaño carta
cd "$MD_PDF_ENGINE" && node dist/cli.js generate /ruta/archivo.md --size Letter --orientation landscape
```

## Plantillas

La lista real la da `node "$MD_PDF_ENGINE/dist/cli.js" list-templates`. Las que trae el motor publicado:

| ID | Nombre | Ideal para |
|----|--------|-----------|
| `tecnica-documentacion` | Técnica/Documentación | Manuales técnicos, docs de código |
| `corporativa-clasica` | Corporativa Clásica | Reportes formales, propuestas |
| `moderna-minimalista` | Moderna Minimalista | Presentaciones limpias |
| `moderna-azul` | Moderna Azul | Documentos modernos en azul |
| `profesional-moderna` | Profesional Moderna | Estilo profesional contemporáneo |

## Opciones principales

- `--template <id>`: plantilla a usar.
- `--output <ruta>`: ruta del PDF de salida (por omisión, el mismo nombre con `.pdf`).
- `--size <A4|Letter|Legal>`: tamaño de página.
- `--orientation <portrait|landscape>`: orientación.
- `--cover`: incluye portada (el primer H1 se vuelve portada).
- `--no-page-numbers`: sin numeración de páginas.
- `--title`, `--author`: metadatos del PDF.

`node "$MD_PDF_ENGINE/dist/cli.js" generate --help` muestra todas.

## Comportamiento

- Siempre se ejecuta desde la carpeta del motor.
- Si el archivo `.md` no existe, avísale al usuario.
- Después de generar, informa la ruta del PDF y su tamaño.
