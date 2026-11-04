"""Prueba del ejecutor de verdad (D4 del plan «análisis de los pendientes 1 a 7 del bot»): Docker y la imagen
«ejecutor-valida» en la Mac, sin modelo y sin red para el contenedor. Va en «Manual»: necesita Docker en el anfitrión
y no corre dentro del propio ejecutor. Sin Docker o sin la imagen se salta y lo dice."""
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import valida_impl as v  # noqa: E402


def hay_ejecutor() -> bool:
    try:
        v.revisar_docker()
        return True
    except v.NoSePuedeValidar:
        return False


@unittest.skipUnless(hay_ejecutor(), "sin Docker o sin la imagen ejecutor-valida")
class EjecutorRealTest(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="ejecutor-real-"))
        (self.base / "copia").mkdir()
        (self.base / "copia" / "hola.txt").write_text("hola\n")
        self.montajes = [(self.base / "copia", v.ORIGEN)]
        self.entorno = v.entorno_del_ejecutor(False, {})

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def correr(self, comando, topes=None, plazo=120):
        nombre = f"valida-real-{secrets.token_hex(4)}"
        banderas = v.banderas_docker(nombre, self.montajes, self.entorno, topes or v.TOPES_COMANDO)
        r = v.correr_en_ejecutor(nombre, banderas, ["sh", "-c", v.INICIO, "valida", comando], plazo, "canario-real")
        quedan = subprocess.run(["docker", "ps", "-a", "--filter", f"name={nombre}", "-q"], capture_output=True, text=True).stdout.strip()
        self.assertEqual(quedan, "", "no queda el contenedor")
        return r

    def test_la_sonda_da_lo_esperado(self):
        problemas, medido = v.sonda_de_aislamiento(self.montajes, self.entorno, "canario-real")
        self.assertEqual(problemas, [], medido)

    def test_memoria_se_corta_con_oom(self):
        r = self.correr("node -e 'const a=[];for(;;)a.push(Buffer.alloc(32*1024*1024,1))'",
                        topes={**v.TOPES_COMANDO, "memoria": "256m"})
        self.assertEqual(r["motivo"], "sin memoria")

    def test_plazo_mata_el_contenedor(self):
        r = self.correr("sleep 60", plazo=3)
        self.assertEqual(r["motivo"], "plazo vencido")

    def test_la_copia_entra_de_solo_lectura_y_se_trabaja_en_tmp(self):
        r = self.correr('test ! -w "$VALIDA_ORIGEN" && cat hola.txt && echo otra > hola.txt && cat hola.txt')
        self.assertEqual(r["rc"], 0, r["salida"])
        self.assertIn("otra", r["salida"])
        self.assertEqual((self.base / "copia" / "hola.txt").read_text(), "hola\n")

    def test_chrome_sin_cabeza_carga_una_pagina_de_127(self):
        guion = (
            "node -e \"require('http').createServer((q,s)=>s.end('<title>pagina-local</title>')).listen(8765,'127.0.0.1')\" & "
            "sleep 1; \"$CHROME_PATH\" --headless=new --dump-dom --user-data-dir=/tmp/perfil http://127.0.0.1:8765/ 2>/dev/null"
        )
        r = self.correr(guion)
        self.assertIn("pagina-local", r["salida"])


if __name__ == "__main__":
    unittest.main()
