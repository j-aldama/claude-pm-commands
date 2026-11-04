#!/bin/sh
# Chrome dentro del ejecutor: su sandbox interno no se puede anidar en el contenedor (que ya no tiene red ni
# privilegios) y /dev/shm es chico. Las pruebas lo encuentran por CHROME_PATH.
exec /usr/bin/chromium --no-sandbox --disable-dev-shm-usage "$@"
