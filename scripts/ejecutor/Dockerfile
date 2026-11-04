# Ejecutor desechable de valida_impl.py (D4 del plan «análisis de los pendientes 1 a 7 del bot», 15-oct-2026).
# Corre las pruebas de una copia sin red (--network none), con la raíz de solo lectura, sin credenciales y con topes.
# Se construye una vez, con red y con permiso de Juan: docker build -t ejecutor-valida ~/.claude/scripts/ejecutor
# La base va fijada por digest (la node:24-bookworm-slim que ya había en la Mac el 15-oct-2026).
FROM node:24-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df
RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium ffmpeg git python3 ca-certificates fonts-liberation \
 && rm -rf /var/lib/apt/lists/*
COPY chrome-envoltorio.sh /usr/local/bin/chrome-envoltorio
RUN chmod 0755 /usr/local/bin/chrome-envoltorio
USER 1000:1000
