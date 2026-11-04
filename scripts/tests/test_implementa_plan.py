"""Pruebas de implementa_plan.py contra un repo git real con una suite que corre: registro, suites ordenadas, huecos,
rojos en el repo (mutación aplicada y deshecha), manuales congelados, evidencia con manifiesto, cruce con
identificador, rondas amarradas a HEAD, copia limpia, revisores encerrados, verificación, validación, cierre y
depuración (igual en el script y en las dos fixtures).
Incluye las reproducciones de los hallazgos de las rondas 1 a 8 de revisión (Codex, Sonnet y Fable).

Corren contra $CLAUDE_HOME (por omisión ~/.claude), igual que las de jurado.py.
"""
import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import types
import unittest
import zlib
from pathlib import Path
from unittest import mock

RAIZ = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")
sys.path.insert(0, str(RAIZ / "scripts"))
import implementa_plan as ip  # noqa: E402
import jurado  # noqa: E402

SCRIPT = RAIZ / "scripts" / "implementa_plan.py"
PLANTILLAS = RAIZ / "skills" / "implementa-plan" / "plantillas"
GIT_ENV = {"GIT_AUTHOR_NAME": "prueba", "GIT_AUTHOR_EMAIL": "p@x", "GIT_COMMITTER_NAME": "prueba",
           "GIT_COMMITTER_EMAIL": "p@x", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
CODEX = {"CODEX_BIN": sys.executable}
SUITE = "python3 -m unittest tests.test_app"
PLAN = """<p>Base: <code>abc1234</code></p><h2>6. Verificación</h2><pre><code># Automática
python3 -m unittest tests.test_app -v
# Manual
nada</code></pre>"""
APP = "def suma(a, b):\n    return a + b\n"
PRUEBA = ("import unittest\nfrom app import suma\n\n\nclass T(unittest.TestCase):\n"
          "    def test_suma(self):\n        self.assertEqual(suma(2, 3), 5)\n\n"
          "    def test_suma_borde(self):\n        self.assertEqual(suma(0, 0), 0)\n")


def parche(linea: str, original="    return a + b", archivo="app.py", inicio=1) -> str:
    return (f"--- a/{archivo}\n+++ b/{archivo}\n@@ -{inicio},2 +{inicio},2 @@\n def suma(a, b):\n-{original}\n+{linea}\n")


PARCHE_RESTA = parche("    return a - b")
PARCHE_MAS_UNO = parche("    return a + b + 1")
PARCHE_CERO = parche("    return a / 0")
# Rompe solo test_suma_borde (suma(0, 0)); test_suma sigue en verde.
PARCHE_SOLO_BORDE = parche("    return a + b if a or b else 1")
PARCHE_IMPORT = "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n-def suma(a, b):\n+def resta(a, b):\n     return a + b\n"
PARCHE_PRUEBA = ("--- a/tests/test_app.py\n+++ b/tests/test_app.py\n@@ -6,2 +6,2 @@\n     def test_suma(self):\n"
                 "-        self.assertEqual(suma(2, 3), 5)\n+        self.assertEqual(suma(2, 3), 6)\n")
ROJOS = (("T-01", "tests/test_app.py::T::test_suma", f"{SUITE}.T.test_suma", PARCHE_RESTA),
         ("T-02", "tests/test_app.py::T::test_suma_borde", f"{SUITE}.T.test_suma_borde", PARCHE_MAS_UNO))


def png(ancho=2, alto=2, pixeles=None, entrelazado=0) -> bytes:
    """PNG RGB válido; con «pixeles» = (ancho, alto) el IDAT trae otro tamaño que el que declara IHDR."""
    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos))
    real_ancho, real_alto = pixeles or (ancho, alto)
    crudo = b"".join(b"\x00" + b"\x00\x00\x00" * real_ancho for _ in range(real_alto))
    return (b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, entrelazado))
            + trozo(b"IDAT", zlib.compress(crudo)) + trozo(b"IEND", b""))


def cli(*args, env=None):
    salida = io.StringIO()
    with mock.patch.dict(os.environ, {**CODEX, **(env or {})}), contextlib.redirect_stdout(salida):
        rc = ip.main([str(a) for a in args])
    texto = salida.getvalue()
    return rc, json.loads(texto[texto.index("{"):]) if "{" in texto else {}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def commit(repo, ruta, contenido="x\n", mensaje=None):
    archivo = Path(repo) / ruta
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(contenido)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", mensaje or f"chore: cambia {ruta}")
    return git(repo, "rev-parse", "HEAD")


def caso_t(i, tipo="unitaria", camino="error"):
    return {"id": f"T-{i:02d}", "tipo": tipo, "camino": camino, "que_prueba": "q", "entrada": "e",
            "esperado": "x", "archivo": "tests/test_app.py", "protege": "app.py:2", "por_que_falta": "p"}


def huecos_completos():
    casos = [caso_t(i, tipo=t, camino="error" if i % 2 else "borde") for i, t in enumerate(ip.TIPOS, 1)]
    casos[0]["camino"] = "feliz"
    return {"resumen": "r", "casos": casos, "no_aplica": []}


def huecos_dos():
    return {"resumen": "r", "casos": [caso_t(1), caso_t(2, camino="borde")],
            "no_aplica": [{"tipo": t, "razon": "r"} for t in ip.TIPOS[1:]]}


def caso_m(i, camino="error", automatizable=True, razon="", pasos=1):
    return {"id": f"M-{i:02d}", "titulo": f"Caso {i}", "perfil": "admin", "camino": camino, "precondiciones": "p",
            "pasos": [{"accion": f"Paso {n}", "esperado": "Se ve"} for n in range(1, pasos + 1)],
            "datos": "sintéticos", "automatizable": automatizable, "razon_no_automatizable": razon}


def manuales(*casos):
    return {"resumen": "r", "casos": list(casos)}


def veredicto(valor="pasa", hallazgos=None, resumen="r"):
    return {"veredicto": valor, "resumen": resumen, "hallazgos": hallazgos or [], "evidencia": []}


def hallazgo(gravedad):
    return {"gravedad": gravedad, "criterio": "C1", "que": "q", "donde": "a.py:1", "porque": "p", "correccion": "c"}


def dictamen(caso, valor="correcto", reportado="pasa"):
    return {"caso": caso, "reportado": reportado, "dictamen": valor, "paso": "", "porque": "p", "correccion": ""}


def paso_ok(n=1, **extra):
    return {"n": n, "accion": f"Paso {n}", "esperado": "Se ve", "resultado": "pasa", "error": None,
            "url": "http://localhost/", "captura": f"paso-{n:02d}.png", "consola": [], "red": [], **extra}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        for ruta, texto in ((".gitignore", "__pycache__/\n"), ("tests/__init__.py", ""), ("tests/test_app.py", PRUEBA)):
            (self.repo / ruta).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / ruta).write_text(texto)
        commit(self.repo, "app.py", APP)

    def tearDown(self):
        self.tmp.cleanup()

    def json(self, nombre, datos):
        ruta = self.base / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        return ruta

    def plan(self, texto=PLAN, nombre="plan.html"):
        ruta = self.base / nombre
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def head(self):
        return git(self.repo, "rev-parse", "HEAD")

    def registro(self, *extra, plan=None, suite=SUITE):
        rc, datos = cli("inicia", "--plan", plan or self.plan(), "--repo", self.repo, "--suite", suite,
                        "--dir", self.base / "D", *extra)
        self.assertEqual(rc, 0, datos)
        return Path(datos["dir"])

    def congelar_manuales(self, d, *casos):
        casos = casos or (caso_m(1, "feliz"), caso_m(2, automatizable=False, razon="SMS"))
        rc, datos = cli("manuales", "--archivo", self.json("m.json", manuales(*casos)), "--dir", d)
        self.assertEqual(rc, 0, datos)

    def evidencia(self, d, *casos, ronda=1, estado="passed", pasos=None, **extra):
        for caso in casos:
            dir_caso = d / "evidencia" / f"ronda-{ronda}" / caso
            dir_caso.mkdir(parents=True, exist_ok=True)
            for p in pasos if pasos is not None else [paso_ok()]:
                if p.get("captura"):
                    (dir_caso / Path(p["captura"]).name).write_bytes(png())
            (dir_caso / "pasos.json").write_text(json.dumps({
                "caso": caso, "titulo": "t", "archivo": "e2e/a.spec.ts", "estado": estado, "head": self.head(),
                "corrida": "c1", "pasos": [paso_ok()] if pasos is None else pasos, "generado": "hoy", **extra}))
        return d / "evidencia" / f"ronda-{ronda}"

    def identificador(self, d, ronda, vuelta=False):
        ruta = d / "evidencia" / f"ronda-{ronda}" / "meta.json" if vuelta else d / f"ronda-{ronda}" / "estado.json"
        return json.loads(ruta.read_text())["identificador"]

    def revision(self, d, ronda, *dictamenes, nombre="r.json"):
        return self.json(nombre, {"identificador": self.identificador(d, ronda, vuelta=True), "resumen": "r",
                                  "casos": list(dictamenes)})


class IniciaTest(Base):
    def test_abre_registro_con_base_suite_y_copia_del_plan(self):
        plan = self.plan()
        d = self.registro(plan=plan)
        cfg = json.loads((d / "config.json").read_text())
        self.assertEqual((cfg["base"], cfg["rama_base"], cfg["suite"]), (self.head(), "main", SUITE))
        plan.write_text("cambiado después")
        self.assertEqual((d / "plan.html").read_text(), PLAN)
        self.assertEqual(cfg["plan_sha256"], hashlib.sha256(PLAN.encode()).hexdigest())

    def test_plan_de_la_sesion_y_arbol_sucio(self):
        d = self.registro("--desde-sesion", plan=self.plan("# Plan\n", "plan-sesion.md"))
        self.assertEqual(json.loads((d / "config.json").read_text())["plan_origen"], "sesion")
        (self.repo / "nuevo.txt").write_text("x")
        rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--dir", self.base / "D2")
        self.assertIn("cambios sin commit", datos["errores"][0])
        self.assertFalse((self.base / "D2").exists())

    def test_base_explicita_rama_inexistente_y_head_desatendido(self):
        git(self.repo, "branch", "develop")
        commit(self.repo, "otro.py")
        self.assertEqual(json.loads((self.registro("--base", "develop") / "config.json").read_text())["rama_base"],
                         "develop")
        rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--base", "nada",
                        "--dir", self.base / "D2")
        self.assertIn("«nada» no existe", datos["errores"][0])
        git(self.repo, "checkout", "-q", "--detach")
        rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--dir", self.base / "D3")
        self.assertIn("HEAD desatendido", datos["errores"][0])

    def test_suite_trivial_o_con_ruta_absoluta(self):
        for suite in ("true", "echo ok", ":", "  ", "/opt/homebrew/bin/python3 -m unittest", f"{SUITE} || true",
                      f"{SUITE}; true", f"{SUITE} | tee log.txt"):
            rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", suite,
                            "--dir", self.base / "D")
            self.assertEqual(rc, 1, suite)
            self.assertFalse((self.base / "D").exists())

    def test_suite_que_corta_en_la_primera_falla(self):
        for suite in ("pytest -x", "pytest --maxfail=1", "pytest --exitfirst", "python3 -m unittest -f tests.test_app",
                      "python manage.py test --failfast", "npx jest --bail", "npx jest -b", "npx vitest run --bail=3",
                      "npx playwright test --max-failures=2", f"{SUITE} && npx playwright test -x", "pytest -xvs",
                      "python -m pytest -vx", "pytest --maxfail 2", "npx jest --bail 1", "python3 -m unittest -fv tests.test_app",
                      "python -m unittest -vf"):
            rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", suite, "--dir", self.base / "D")
            self.assertEqual(rc, 1, suite)
            self.assertIn("corta en la primera falla", datos["errores"][0], suite)
            self.assertFalse((self.base / "D").exists())
        # -f y -b solo son fail-fast junto a unittest y jest; «=0» quita el tope.
        for k, suite in enumerate(("docker compose -f compose.yml run pruebas", "npx vitest run --bail=0",
                                   "npx playwright test --max-failures=0", "pytest --maxfail 0", "pytest -rxs",
                                   "npx playwright test --max-failures 0", "pytest -k xfoo", "python -m unittest -vk prueba_f")):
            rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", suite, "--dir", self.base / f"D{k}")
            self.assertEqual(rc, 0, (suite, datos))

    def test_url_local_remota_y_confirmacion_que_nombra_el_host(self):
        self.registro("--url", "http://127.0.0.1:8000")
        casos = (("https://staging.cliente.com", None), ("http://127.evil.com", None),
                 ("https://prod.cliente.com", "Juan: sí, usa staging.cliente.com"))
        for url, confirmacion in casos:
            extra = ["--confirmacion-url", confirmacion] if confirmacion else []
            rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--url", url,
                            *extra, "--dir", self.base / "D2")
            self.assertIn("no es local", datos["errores"][0], url)
        rc, _ = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--url",
                    "https://staging.cliente.com", "--confirmacion-url", "Juan: sí, usa staging.cliente.com",
                    "--dir", self.base / "D3")
        self.assertEqual(rc, 0)

    def test_advisor_sin_codex_y_entradas_invalidas(self):
        d = self.registro("--con-advisor", "--sesion", "fable")
        self.assertEqual(json.loads((d / "config.json").read_text())["jueces"], ["codex", "claude", "advisor-opus"])
        rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE,
                        env={"CODEX_BIN": "/no/existe/codex"})
        self.assertIn("Codex no está disponible", datos["errores"][0])
        rc, datos = cli("inicia", "--plan", self.base / "nada.html", "--repo", self.repo, "--suite", SUITE)
        self.assertIn("no existe el plan", datos["errores"][0])
        suelta = self.base / "suelta"
        suelta.mkdir()
        self.assertIn("no es un repo git", cli("inicia", "--plan", self.plan(), "--repo", suelta, "--suite",
                                               SUITE)[1]["errores"][0])

    def test_no_pisa_registro_y_resuelve_dir_relativo(self):
        self.registro()
        rc, datos = cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--dir", self.base / "D")
        self.assertIn("ya hay un registro", datos["errores"][0])
        r = subprocess.run([sys.executable, str(SCRIPT), "inicia", "--plan", str(self.plan()), "--repo",
                            str(self.repo), "--suite", SUITE, "--dir", "relativo"], cwd=self.base,
                           capture_output=True, text=True, env={**os.environ, **CODEX})
        self.assertEqual(json.loads(r.stdout)["dir"], str(self.base / "relativo"))
        r = subprocess.run([sys.executable, str(SCRIPT), "copia", "--dir", "relativo"], cwd=self.base, capture_output=True,
                           text=True, env={**os.environ, **CODEX})
        self.assertEqual(Path(json.loads(r.stdout)["copia"]).parent, self.base / "relativo" / "copias")


class SuiteTest(Base):
    def test_linea_base_inmutable_en_el_commit_base_y_en_orden(self):
        d = self.registro()
        self.assertIn("corre primero «suite --fase linea-base»", cli("suite", "--dir", d, "--fase", "fase-1")[1]["errores"][0])
        rc, datos = cli("suite", "--dir", d, "--fase", "linea-base")
        self.assertEqual((rc, json.loads((d / "suite-linea-base.json").read_text())["head"]), (0, self.head()))
        self.assertIn("inmutable", cli("suite", "--dir", d, "--fase", "linea-base")[1]["errores"][0])
        self.assertIn("corre primero «suite --fase fase-3»", cli("suite", "--dir", d, "--fase", "final")[1]["errores"][0])
        self.assertIn("inválida", cli("suite", "--dir", d, "--fase", "../fuera")[1]["errores"][0])

    def test_rojos_preexistentes_no_cuentan_como_nuevos(self):
        commit(self.repo, "app.py", "def suma(a, b):\n    return 0\n")
        d = self.registro()
        self.assertEqual(cli("suite", "--dir", d, "--fase", "linea-base")[1]["rc"], 1)
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-1")
        self.assertEqual((rc, datos["nuevos_vs_linea_base"]), (0, []))
        commit(self.repo, "tests/test_otro.py", "import unittest\nfrom app import suma\n\n\nclass U(unittest.TestCase):\n"
               "    def test_x(self):\n        self.assertEqual(suma(1, 1), 2)\n")
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual(rc, 0, datos)

    def test_rojo_preexistente_en_un_tramo_no_esconde_uno_nuevo_en_otro(self):
        """«A && B» con un rojo de la línea base en A: una regresión en B se ve (antes B ni corría)."""
        commit(self.repo, "tests/test_pre.py", "import unittest\n\n\nclass P(unittest.TestCase):\n"
               "    def test_pre(self):\n        self.fail('preexistente')\n")
        d = self.registro(suite=f"python3 -m unittest tests.test_pre && {SUITE}")
        self.assertEqual(cli("suite", "--dir", d, "--fase", "linea-base")[1]["rc"], 1)
        commit(self.repo, "app.py", "def suma(a, b):\n    return 0\n")
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-1")
        self.assertEqual((rc, datos["nuevos_vs_linea_base"]), (1, ["test_suma (tests.test_app.T.test_suma)"]))
        commit(self.repo, "app.py", APP)
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual((rc, datos["rc"], datos["nuevos_vs_linea_base"]), (0, 1, []))

    def test_linea_base_fuera_del_commit_base(self):
        d = self.registro()
        commit(self.repo, "otro.py")
        self.assertIn("en el commit base", cli("suite", "--dir", d, "--fase", "linea-base")[1]["errores"][0])

    def test_salida_depurada_y_fallas_leidas(self):
        suite = "python3 -c \"print('API_TOKEN=abcdefghijklmnop')\" && " + SUITE
        d = self.registro(suite=suite)
        cli("suite", "--dir", d, "--fase", "linea-base")
        commit(self.repo, "app.py", "def suma(a, b):\n    return 0\n")
        rc, datos = cli("suite", "--dir", d, "--fase", "ronda-1")
        texto = (d / "suite-ronda-1.txt").read_text()
        self.assertNotIn("abcdefghijklmnop", texto)
        self.assertEqual(datos["fallas"], ["test_suma (tests.test_app.T.test_suma)"])

    def test_roja_sin_fallas_legibles_o_abortada_lo_dice(self):
        d = self.registro()
        cli("suite", "--dir", d, "--fase", "linea-base")
        with mock.patch.object(ip, "_shell", return_value=(1, "algo salió mal pero sin formato de runner")):
            rc, datos = cli("suite", "--dir", d, "--fase", "fase-1")
        self.assertEqual((rc, datos["nuevos_vs_linea_base"]), (1, None))
        self.assertIn("sin ninguna falla legible", datos["errores"][0])
        with mock.patch.object(ip, "_shell", return_value=(2, "usage: pytest")):
            rc, datos = cli("suite", "--dir", d, "--fase", "fase-1")
        self.assertIn("la suite abortó (rc 2)", datos["errores"][0])


class CasosTest(Base):
    def test_suite_completa_pasa_y_se_congela(self):
        d = self.registro()
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_completos()))
        self.assertEqual(cli("casos", "--dir", d)[0], 0)
        self.assertTrue((d / "fase-2-huecos.json.sello.json").is_file())

    def test_cero_casos_exige_autorizacion_de_juan(self):
        d = self.registro()
        vacio = {"resumen": "r", "casos": [], "no_aplica": [{"tipo": t, "razon": "n/a"} for t in ip.TIPOS]}
        (d / "fase-2-huecos.json").write_text(json.dumps(vacio))
        self.assertIn("--sin-huecos", cli("casos", "--dir", d)[1]["errores"][0])
        self.assertEqual(cli("casos", "--dir", d, "--sin-huecos", "Juan: la suite ya cubre esto")[0], 0)
        self.assertEqual(ip._autorizacion_sellada(d, "fase-2-huecos.json"), "Juan: la suite ya cubre esto")

    def test_reglas_de_cobertura(self):
        datos = huecos_completos()
        datos["no_aplica"] = [{"tipo": "seguridad", "razon": "x"}, {"tipo": "seguridad", "razon": "y"}]
        errores = ip.revisar_casos(datos)
        self.assertIn("tipo «seguridad» tiene casos y a la vez «no aplica»", errores)
        self.assertIn("id repetido «seguridad»", errores)
        datos = huecos_completos()
        for c in datos["casos"][:5]:
            c["camino"] = "feliz"
        datos["casos"][6]["protege"] = " "
        errores = ip.revisar_casos(datos)
        self.assertTrue(any("camino feliz" in e for e in errores))
        self.assertIn("T-07: sin «protege»", errores)

    def test_esquema_invalido_y_json_en_prosa(self):
        datos = huecos_completos()
        datos["casos"][0]["tipo"] = "humo"
        self.assertEqual(cli("casos", "--archivo", self.json("c.json", datos))[0], 2)
        ruta = self.base / "c.md"
        ruta.write_text("Análisis...\n```json\n" + json.dumps(huecos_completos()) + "\n```\n", encoding="utf-8")
        self.assertEqual(cli("casos", "--archivo", ruta)[0], 0)


class RojoTest(Base):
    def setUp(self):
        super().setUp()
        self.d = self.registro()
        (self.d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", self.d)

    def rojo(self, caso, prueba, comando, contenido):
        ruta = self.base / f"{caso}.patch"
        ruta.write_text(contenido)
        return cli("rojo", "--dir", self.d, "--caso", caso, "--prueba", prueba, "--comando", comando, "--parche", ruta)

    def test_mutacion_de_produccion_pone_roja_la_asercion(self):
        rc, datos = self.rojo(*ROJOS[0])
        self.assertEqual(rc, 0, datos)
        self.assertEqual((datos["rc_sin"], datos["rc_con"] != 0), (0, True))
        self.assertIn("AssertionError", datos["salida"])
        self.assertEqual((self.repo / "app.py").read_text(), APP)
        self.assertEqual(git(self.repo, "worktree", "list").count("\n"), 0)

    def test_excepcion_que_no_es_asercion_no_cuenta(self):
        rc, datos = self.rojo("T-01", ROJOS[0][1], ROJOS[0][2], PARCHE_CERO)
        self.assertEqual(rc, 1)
        self.assertIn("falló por una excepción, no por su aserción", datos["errores"][0])

    def test_rojo_por_importacion_no_cuenta(self):
        rc, datos = self.rojo("T-01", ROJOS[0][1], ROJOS[0][2], PARCHE_IMPORT)
        self.assertIn("ImportError", datos["errores"][0])

    def test_comando_que_no_corre_la_prueba_o_que_esconde_el_rojo(self):
        casos = ((ROJOS[0][1], "git diff --quiet", "no corre"), ("tests/test_app.py", SUITE, "<archivo>::<nombre>"),
                 (ROJOS[0][1], f"{ROJOS[0][2]} || true", "sigue en verde"), (ROJOS[0][1], "echo test_suma", "sigue en verde"))
        for prueba, comando, motivo in casos:
            rc, datos = self.rojo("T-01", prueba, comando, PARCHE_RESTA)
            self.assertEqual(rc, 1, comando)
            self.assertIn(motivo, datos["errores"][0], comando)

    def test_seleccion_amplia_solo_cuenta_si_falla_la_prueba_declarada(self):
        rc, datos = self.rojo("T-01", ROJOS[0][1], SUITE, PARCHE_SOLO_BORDE)
        self.assertIn("fallaron otras pruebas, no esta", datos["errores"][0])
        self.assertEqual(self.rojo("T-02", ROJOS[1][1], SUITE, PARCHE_SOLO_BORDE)[0], 0)

    def test_cualquier_runner_que_apunte_a_la_prueba(self):
        validos = (("app/tests/test_x.py::Clase::test_y", "python manage.py test app.tests.test_x.Clase.test_y"),
                   ("app/tests/test_x.py::Clase::test_y", "python -m django test app.tests.test_x --settings=s"),
                   ("tests/test_x.py::test_y", "pytest -k 'test_y and not lento'"),
                   ("e2e/x.spec.ts::M-01 muestra el título", "npx playwright test e2e/x.spec.ts:12 --project=chromium"),
                   ("tests/e2e/test_m.py::test_m01", "pytest tests/e2e/test_m.py --browser chromium"),
                   ("src/x.test.ts::suma dos números", "npx vitest run src/x.test.ts -t 'suma dos números'"),
                   ("src/x.test.js::hace algo", "npm test -- -t 'hace algo'"),
                   ("tienda/tests/test_x.py::C::test_y", "python manage.py test tienda"))
        for prueba, comando in validos:
            ip._revisar_seleccion(prueba, comando)

    def test_reconoce_la_falla_de_cada_runner_sin_confundir_homonimos(self):
        salidas = {"tests/x.py::test_suma": "FAILED tests/x.py::test_suma - assert 1 == 2",
                   "app/t.py::C::test_y": "FAIL: test_y (app.t.C.test_y)\nAssertionError",
                   "e2e/a.spec.ts::M-01 algo": "  1) [chromium] › e2e/a.spec.ts:3:5 › M-01 algo",
                   # Playwright 1.61 real: describe en medio y la cabecera rematada con «────».
                   "e2e/x.spec.ts::M-01 muestra el título": "  ✘  1 [chromium] › e2e/x.spec.ts:3:7 › Registro › M-01 muestra "
                   "el título (713ms)\n\n  1) [chromium] › e2e/x.spec.ts:3:7 › Registro › M-01 muestra el título "
                   "────────────────────────────\n\n    Error: expect(locator).toHaveText(expected) failed\n",
                   "a.test.ts::hace algo": "  ● Suite › hace algo", "b.test.ts::suma dos": " FAIL  b.test.ts > s > suma dos",
                   "tests/x.py::test_p": "FAILED tests/x.py::test_p[caso-1] - assert"}
        for prueba, salida in salidas.items():
            self.assertTrue(ip.falla_la_prueba(prueba, salida), prueba)
        self.assertEqual(ip.fallas(salidas["e2e/x.spec.ts::M-01 muestra el título"]),
                         ["[chromium] › e2e/x.spec.ts:3:7 › Registro › M-01 muestra el título"])
        self.assertFalse(ip.falla_la_prueba("tests/x.py::test_suma", "FAILED tests/x.py::test_suma_borde - assert"))
        self.assertFalse(ip.falla_la_prueba("t.py::C::test_y", "FAIL: test_y_lento (t.C.test_y_lento)"))

    def test_falla_larga_se_juzga_completa_y_se_guarda_recortada(self):
        # unittest con maxDiff=None: «FAIL: test_grande» queda al principio y el resumen al final, con un diff enorme en medio.
        commit(self.repo, "tests/test_largo.py", "import unittest\nfrom app import suma\n\n\nclass L(unittest.TestCase):\n"
               "    maxDiff = None\n\n    def test_grande(self):\n        self.assertEqual('a' * suma(2000, 3000), 'a' * 5000)\n")
        rc, datos = self.rojo("T-01", "tests/test_largo.py::L::test_grande", "python3 -m unittest tests.test_largo.L.test_grande",
                              PARCHE_RESTA)
        self.assertEqual(rc, 0, datos)
        guardado = json.loads((self.d / "fase-3-rojos.json").read_text())["pruebas"][0]
        self.assertIn("[…]", guardado["salida"])
        self.assertLess(len(guardado["salida"]), ip.LIMITE_SALIDA + 20)
        self.assertEqual((guardado["errores"], cli("rojos", "--dir", self.d)[0]), ([], 1))  # falta T-02, no T-01
        self.assertNotIn("test_grande", " ".join(cli("rojos", "--dir", self.d)[1]["errores"]))
        # La aserción puede quedar en medio de una salida larga: el veredicto no sale del recorte.
        salidas = iter([(0, "ok"), (1, f"FAILED tests/test_app.py::T::test_suma_borde - x\n{'y' * 6000}AssertionError{'z' * 6000}")])
        with mock.patch.object(ip, "_shell", side_effect=lambda *a, **k: next(salidas)):
            rc, datos = self.rojo(*ROJOS[1])
        self.assertEqual((rc, cli("rojos", "--dir", self.d)[0]), (0, 0), datos)

    def test_repetir_sigue_aunque_un_parche_ya_no_aplique(self):
        for caso in ROJOS:
            self.rojo(*caso)
        commit(self.repo, "app.py", "def suma(a, b):\n    # otra base\n    return a + b\n")
        rc, datos = cli("rojos", "--dir", self.d, "--repetir")
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(datos["no_repetidos"]), ["T-01", "T-02"])
        self.assertIn("no aplica sobre HEAD", datos["no_repetidos"]["T-01"])
        self.assertTrue(all("venció" in e for e in datos["errores"]), datos["errores"])
        self.assertEqual(((self.repo / "app.py").read_text().count("otra base"), git(self.repo, "status", "--porcelain")), (1, ""))

    def test_pytest_raises_sin_excepcion_es_falla_de_asercion(self):
        p = {"prueba": "tests/x.py::test_raises", "rc_sin": 0, "rc_con": 1,
             "salida": "FAILED tests/x.py::test_raises - Failed: DID NOT RAISE\nE       Failed: DID NOT RAISE <class "
                       "'ValueError'>"}
        self.assertEqual(ip._errores_de_rojo(p), [])
        p["salida"] = "FAILED tests/x.py::test_raises - ZeroDivisionError\nE   ZeroDivisionError: division by zero"
        self.assertIn("excepción", ip._errores_de_rojo(p)[0])

    def test_vence_con_cambios_en_helpers_y_se_repite(self):
        commit(self.repo, "tests/helpers.py", "AYUDA = 1\n")
        for caso in ROJOS:
            self.rojo(*caso)
        self.assertTrue((self.d / "rojos" / "T-01.patch").is_file())
        commit(self.repo, "tests/test_nueva.py", "import unittest\n")
        self.assertEqual(cli("rojos", "--dir", self.d)[0], 0)
        commit(self.repo, "tests/helpers.py", "AYUDA = 2\n")
        self.assertTrue(any("venció" in e for e in cli("rojos", "--dir", self.d)[1]["errores"]))
        rc, datos = cli("rojos", "--dir", self.d, "--repetir")
        self.assertEqual((rc, sorted(datos["repetidos"])), (0, ["T-01", "T-02"]), datos)

    def test_sigterm_a_media_mutacion_deja_el_arbol_limpio(self):
        lento = "python3 -c \"import app, time; app.suma(2, 3) == 5 or time.sleep(60)\" tests.test_app.T.test_suma"
        (self.base / "m.patch").write_text(PARCHE_RESTA)
        proceso = subprocess.Popen([sys.executable, str(SCRIPT), "rojo", "--dir", str(self.d), "--caso", "T-01",
                                    "--prueba", ROJOS[0][1], "--comando", lento, "--parche", str(self.base / "m.patch")],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={**os.environ, **CODEX})
        limite = time.monotonic() + 30
        while (self.repo / "app.py").read_text() == APP and time.monotonic() < limite:
            time.sleep(0.1)
        time.sleep(0.5)
        proceso.terminate()
        proceso.wait(30)
        self.assertEqual(((self.repo / "app.py").read_text(), git(self.repo, "status", "--porcelain")), (APP, ""))

    def test_mutacion_del_mismo_tamano_se_ve_aunque_haya_bytecode_viejo(self):
        os.utime(self.repo / "app.py")
        for _ in range(3):
            subprocess.run([sys.executable, "-m", "unittest", "tests.test_app"], cwd=self.repo, capture_output=True,
                           env={k: v for k, v in os.environ.items() if k != "PYTHONDONTWRITEBYTECODE"})
            rc, datos = self.rojo(*ROJOS[0])
            self.assertEqual(rc, 0, datos)

    def test_deshace_la_mutacion_aunque_la_corrida_truene_y_guarda_salida_depurada(self):
        with mock.patch.object(ip, "_shell", side_effect=[(0, "ok"), KeyboardInterrupt()]):
            with self.assertRaises(KeyboardInterrupt):
                self.rojo(*ROJOS[0])
        self.assertEqual(((self.repo / "app.py").read_text(), git(self.repo, "status", "--porcelain")), (APP, ""))
        salidas = iter([(0, "ok API_TOKEN=abcdefghijklmnop"),
                        (1, "FAIL: test_suma_borde (tests.test_app.T.test_suma_borde)\nAssertionError: 1 != 0 "
                            "API_TOKEN=abcdefghijklmnop")])
        with mock.patch.object(ip, "_shell", side_effect=lambda *a, **k: next(salidas)):
            rc, datos = self.rojo(*ROJOS[1])
        self.assertEqual(rc, 0, datos)
        self.assertNotIn("abcdefghijklmnop", json.dumps(datos) + (self.d / "fase-3-rojos.json").read_text())

    def test_prueba_que_ya_falla_sin_la_mutacion(self):
        rc, datos = self.rojo("T-01", "tests/test_app.py::T::test_no_existe", f"{SUITE}.T.test_no_existe", PARCHE_RESTA)
        self.assertIn("no pasa sin la mutación", datos["errores"][0])

    def test_parche_que_toca_pruebas_y_caso_desconocido(self):
        self.assertIn("solo código de producción", self.rojo("T-01", *ROJOS[0][1:3], PARCHE_PRUEBA)[1]["errores"][0])
        nuevo = "--- /dev/null\n+++ b/otro.py\n@@ -0,0 +1 @@\n+x = 1\n"
        borra = "--- a/app.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-def suma(a, b):\n-    return a + b\n"
        for contenido in (nuevo, borra):
            self.assertIn("no crea, borra ni renombra", self.rojo("T-01", *ROJOS[0][1:3], contenido)[1]["errores"][0])
        self.assertEqual(((self.repo / "app.py").read_text(), git(self.repo, "status", "--porcelain")), (APP, ""))
        self.assertIn("T-09 no es un caso exigido", self.rojo("T-09", *ROJOS[0][1:])[1]["errores"][0])

    def test_rojos_exige_todos_los_casos_y_pruebas_distintas(self):
        self.rojo(*ROJOS[0])
        self.assertIn("caso T-02 sin prueba vista en rojo (corre «rojo»)", cli("rojos", "--dir", self.d)[1]["errores"])
        self.rojo("T-02", *ROJOS[0][1:])
        self.assertTrue(any("id repetido" in e for e in cli("rojos", "--dir", self.d)[1]["errores"]))
        self.rojo(*ROJOS[1])
        self.assertEqual(cli("rojos", "--dir", self.d)[0], 0)

    def test_rojo_vence_si_cambia_la_prueba_o_lo_mutado(self):
        for caso in ROJOS:
            self.rojo(*caso)
        commit(self.repo, "app.py", APP + "# cambio\n")
        self.assertTrue(any("el rojo venció" in e for e in cli("rojos", "--dir", self.d)[1]["errores"]))

    def test_descarte_necesita_cita_real(self):
        self.rojo(*ROJOS[0])
        (self.d / "fase-2-descartes.json").write_text(json.dumps({"descartes": [
            {"id": "T-02", "razon": "ya existe en tests/test_app.py:999"}, {"id": "T-77", "razon": "app.py:1"}]}))
        errores = cli("rojos", "--dir", self.d)[1]["errores"]
        self.assertIn("descarte de T-02 sin cita archivo:línea que exista en HEAD", errores)
        self.assertIn("descarte de «T-77», que no está en fase-2-huecos.json", errores)
        commit(self.repo, "tests/README.md", "Cómo correr las pruebas\n")
        for cita in ("ver app.py:1", "ver tests/README.md:1"):
            (self.d / "fase-2-descartes.json").write_text(json.dumps({"descartes": [{"id": "T-02", "razon": cita}]}))
            self.assertIn("la cita debe ser la prueba que ya lo cubre", " ".join(cli("rojos", "--dir", self.d)[1]["errores"]))
        (self.d / "fase-2-descartes.json").write_text(json.dumps({"descartes": [
            {"id": "T-02", "razon": "ya existe en tests/test_app.py:7"}]}))
        self.assertEqual(cli("rojos", "--dir", self.d)[0], 0)

    def test_archivos_tests_de_django_cuentan_como_pruebas(self):
        """Django descubre «tests_*.py»: vale como cita de un descarte, no se puede mutar y su cambio vence los rojos."""
        for ruta in ("candidates/tests_models.py", "tests_api.py", "tests/test_x.py", "x_test.py", "e2e/a.spec.ts"):
            self.assertTrue(ip.TEST_ARCHIVO.search(ruta) and ip.PRUEBA_UNITARIA.search(ruta), ruta)
        for ruta in ("contest_utils.py", "candidates/testing.py", "candidates/tests_.py", "attests_x.py"):
            self.assertFalse(ip.TEST_ARCHIVO.search(ruta) or ip.PRUEBA_UNITARIA.search(ruta), ruta)
        self.assertTrue(ip._es_segura("candidates/tests_models.py", set()))
        self.assertFalse(ip._es_segura("candidates/tests_models.py", {"candidates/tests_models.py"}))
        commit(self.repo, "candidates/tests_models.py", "import unittest\n\n\nclass M(unittest.TestCase):\n"
               "    def test_ya(self):\n        pass\n")
        self.rojo(*ROJOS[0])
        mutar_prueba = ("--- a/candidates/tests_models.py\n+++ b/candidates/tests_models.py\n@@ -5,2 +5,2 @@\n"
                        "     def test_ya(self):\n-        pass\n+        self.fail()\n")
        self.assertIn("solo código de producción", self.rojo("T-02", *ROJOS[1][1:3], mutar_prueba)[1]["errores"][0])
        (self.d / "fase-2-descartes.json").write_text(json.dumps({"descartes": [
            {"id": "T-02", "razon": "ya lo cubre candidates/tests_models.py:5"}]}))
        self.assertEqual(cli("rojos", "--dir", self.d)[0], 0)
        commit(self.repo, "candidates/tests_otros.py", "import unittest\n")
        self.assertEqual(cli("rojos", "--dir", self.d)[0], 0)
        commit(self.repo, "candidates/tests_models.py", "import unittest\n\n\nclass M(unittest.TestCase):\n"
               "    def test_ya(self):\n        pass\n# cambia\n")
        self.assertTrue(any("el rojo venció" in e for e in cli("rojos", "--dir", self.d)[1]["errores"]))
        commit(self.repo, "conftest.py", "")
        self.assertTrue(any("conftest.py" in e for e in cli("rojos", "--dir", self.d)[1]["errores"]))

    def test_huecos_alterados_despues_de_congelar(self):
        (self.d / "fase-2-huecos.json").write_text(json.dumps(huecos_completos()))
        self.assertIn("cambió después de validarse", self.rojo(*ROJOS[0])[1]["errores"][0])


class ManualesTest(Base):
    def test_validos_arman_html_y_se_congelan(self):
        d = self.registro()
        salida = self.base / "m.html"
        rc, res = cli("manuales", "--archivo", self.json("m.json", manuales(caso_m(1, "feliz"), caso_m(2),
                      caso_m(3, automatizable=False, razon="requiere SMS real"))), "--salida", salida, "--dir", d)
        self.assertEqual(rc, 0, res)
        self.assertIn("Te toca a ti", salida.read_text())
        self.assertEqual(sorted(ip._manuales(d)), ["M-01", "M-02"])

    def test_sin_automatizables_no_se_congela_y_no_hay_como_saltarlo(self):
        """Las pruebas manuales con captura y su revisión no se omiten: no hay autorización que las salte."""
        d = self.registro()
        for datos in (manuales(caso_m(1, automatizable=False, razon="SMS")), manuales()):
            rc, res = cli("manuales", "--archivo", self.json("m.json", datos), "--dir", d)
            self.assertEqual(rc, 1, res)
            self.assertIn("no se omiten", res["errores"][0])
            self.assertFalse((d / "manuales.json").exists())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli("manuales", "--archivo", self.json("m.json", manuales()), "--dir", d, "--sin-evidencia", "Juan: sí")

    def test_errores_de_contenido_no_congelan(self):
        d = self.registro()
        c = caso_m(1, "feliz", automatizable=False)
        c["id"], c["pasos"] = "caso1", []
        rc, datos = cli("manuales", "--archivo", self.json("m.json", manuales(c, caso_m(2, "feliz"))), "--dir", d)
        for esperado in ("id «caso1» no sigue el formato M-01", "caso1: sin pasos", "caso1: no automatizable sin razón",
                         "no hay casos de camino «error»"):
            self.assertIn(esperado, datos["errores"])
        self.assertFalse((d / "manuales.json").exists())

    def test_html_escapa_el_contenido(self):
        c = caso_m(1)
        c["titulo"] = "<script>alert(1)</script>"
        self.assertNotIn("<script>alert", ip.html_manuales(manuales(c)))


class EvidenciaTest(Base):
    def setUp(self):
        super().setUp()
        self.d = self.registro()
        self.congelar_manuales(self.d)

    def correr(self, ronda=1, *extra):
        return cli("evidencia", "--dir", self.d, "--ronda", ronda, *extra)

    def test_arma_html_amarra_a_head_y_da_identificador(self):
        self.evidencia(self.d, "M-01")
        rc, datos = self.correr()
        self.assertEqual(rc, 0, datos)
        raiz = self.d / "evidencia" / "ronda-1"
        meta = json.loads((raiz / "meta.json").read_text())
        self.assertEqual(meta["head"], self.head())
        self.assertTrue(datos["identificador"].startswith("vuelta 1 · ") and self.head()[:12] in datos["identificador"])
        self.assertIn("M-01/paso-01.png", meta["manifiesto"])

    def test_falta_caso_automatizable_o_sobra_uno(self):
        self.evidencia(self.d, "M-09")
        errores = self.correr()[1]["errores"]
        self.assertIn("sin evidencia del caso automatizable M-01", errores)
        self.assertIn("evidencia de M-09, que no es un caso automatizable de manuales", errores)

    def test_sin_pasos_sin_captura_png_falso_o_sin_estado(self):
        self.evidencia(self.d, "M-01", pasos=[])
        self.assertIn("M-01: sin pasos registrados", self.correr()[1]["errores"])
        raiz = self.evidencia(self.d, "M-01", pasos=[paso_ok(captura="/etc/passwd")], estado=None)
        errores = self.correr()[1]["errores"]
        self.assertIn("M-01 paso 1: sin captura válida", " ".join(errores))
        self.assertIn("M-01: sin estado final (None)", errores)
        self.assertNotIn("/etc/passwd'", (raiz / "index.html").read_text())
        self.evidencia(self.d, "M-01")
        for basura in (b"\x89PNG", png()[:-20] + png()[-12:], png().replace(b"IDAT", b"IDAX"),
                       b"\x89PNG\r\n\x1a\n" + b"\x00" * 41, png(2, 2, pixeles=(5, 5)), png(entrelazado=1)):
            (raiz / "M-01" / "paso-01.png").write_bytes(basura)
            self.assertIn("M-01 paso 1: sin captura válida", " ".join(self.correr()[1]["errores"]))

    def test_pasos_distintos_al_caso_manual(self):
        self.evidencia(self.d, "M-01", pasos=[paso_ok(1, accion="Otra cosa"), paso_ok(2)], head="0" * 40, corrida="")
        errores = self.correr()[1]["errores"]
        for esperado in ("M-01: 2 pasos en la evidencia y 1 en el caso manual", "M-01 paso 1: «accion» no es el del "
                         "caso manual", "M-01: la corrida es de otro commit (0000000000)", "M-01: sin EVIDENCIA_CORRIDA"):
            self.assertIn(esperado, errores)

    def test_paso_con_texto_que_se_depura_sigue_coincidiendo(self):
        manual = [{"accion": "Escribir password: incorrecto y enviar", "esperado": "Se ve el error"}]
        evidencia = [paso_ok(accion=ip.depurar("Escribir password: incorrecto y enviar"), esperado="Se ve el error")]
        self.assertEqual(ip._contra_manual("M-01", evidencia, manual, True), [])

    def test_paso_sin_navegador_con_captura_de_texto(self):
        raiz = self.evidencia(self.d, "M-01", pasos=[paso_ok(captura=None, texto="paso-01.txt")])
        (raiz / "M-01" / "paso-01.txt").write_text("POST /api/pedidos {cantidad: 0}\n400 cantidad inválida")
        rc, datos = self.correr()
        self.assertEqual(rc, 0, datos)
        self.assertIn("400 cantidad inválida", (raiz / "index.html").read_text())
        self.assertIn("M-01/paso-01.txt", json.loads((raiz / "meta.json").read_text())["manifiesto"])

    def test_captura_de_texto_vacia_ajena_o_con_secreto(self):
        raiz = self.evidencia(self.d, "M-01", pasos=[paso_ok(captura=None, texto="paso-01.txt")])
        (raiz / "M-01" / "paso-01.txt").write_text("   \n")
        self.assertIn("M-01 paso 1: sin captura válida", " ".join(self.correr()[1]["errores"]))
        (raiz / "M-01" / "paso-01.txt").write_text("200 OK token=ghp_abcdefghijklmnopqrstuvwxyz0123")
        self.assertIn("posible secreto en M-01 paso 1 (captura de texto)", " ".join(self.correr()[1]["errores"]))
        raiz = self.evidencia(self.d, "M-01", pasos=[paso_ok(captura=None, texto="../../config.json")])
        self.assertIn("M-01 paso 1: sin captura válida", " ".join(self.correr()[1]["errores"]))

    def test_pasos_corrupto(self):
        raiz = self.evidencia(self.d, "M-01")
        (raiz / "M-03").mkdir()
        (raiz / "M-03" / "pasos.json").write_text("{a medias")
        self.assertTrue(any("M-03" in e and "ilegible" in e for e in self.correr()[1]["errores"]))

    def test_secretos_en_consola_y_en_textos_del_spec(self):
        self.evidencia(self.d, "M-01", pasos=[paso_ok(consola=[{"tipo": "log", "texto": "{\"client_secret\":\"s3cr3tv\"}"}],
                                                      error="X-Auth-Token: abcdef123456")])
        errores = self.correr()[1]["errores"]
        self.assertIn("posible secreto en M-01 paso 1 (consola): clave=valor", errores)
        self.assertTrue(any("paso 1 (error)" in e for e in errores))

    def test_anexo_de_la_vuelta_se_depura_en_su_lugar(self):
        raiz = self.evidencia(self.d, "M-01")
        log = raiz / "servidor.log"
        log.write_text("GET /api Authorization: ApiKey abcdefghijklmnop ghp_abcdefghijklmnopqrstuvwxyz01\n")
        self.assertEqual(self.correr(1, "--anexo", log)[0], 0)
        self.assertEqual((ip.secretos_en(log.read_text()), "abcdefghijklmnop" in log.read_text()), ([], False))
        otro = self.d / "evidencia" / "servidor.log"
        otro.write_text("x")
        self.assertTrue(any("debe ser un archivo dentro de" in e for e in self.correr(1, "--anexo", otro)[1]["errores"]))

    def test_enmienda_manual_cambia_el_esperado_con_texto_de_juan(self):
        """Con evidencia ya armada, «manuales» no vuelve a congelar; la enmienda cambia el esperado, queda registrada y
        la evidencia se compara contra el texto nuevo."""
        self.evidencia(self.d, "M-01")
        self.assertEqual(self.correr()[0], 0)
        otra = self.json("m2.json", manuales(caso_m(1, "feliz"), caso_m(2, automatizable=False, razon="SMS")))
        self.assertIn("enmienda-manual", cli("manuales", "--archivo", otra, "--dir", self.d)[1]["errores"][0])
        base = ["enmienda-manual", "--dir", self.d, "--caso", "M-01", "--esperado", "Se ve en una línea",
                "--motivo", "ronda 1, app.py:2", "--autorizacion"]
        self.assertIn("no existe el paso 2", cli(*base, "Sí, enmiéndalo", "--paso", 2)[1]["errores"][0])
        self.assertIn("no pueden ir vacíos", cli(*base, " ", "--paso", 1)[1]["errores"][0])
        rc, datos = cli(*base, "Sí, enmiéndalo", "--paso", 1)
        self.assertEqual((rc, datos["antes"], datos["despues"]), (0, "Se ve", "Se ve en una línea"))
        self.assertEqual(ip._manuales(self.d)["M-01"]["pasos"][0]["esperado"], "Se ve en una línea")
        self.assertEqual(json.loads((self.d / "manuales-enmiendas.json").read_text())["enmiendas"][0]["autorizacion"],
                         "Sí, enmiéndalo")
        self.assertIn("M-01 paso 1: «esperado» no es el del caso manual", self.correr()[1]["errores"])
        self.evidencia(self.d, "M-01", pasos=[paso_ok(esperado="Se ve en una línea")])
        self.assertEqual(self.correr()[0], 0)

    def test_prepara_evidencia_vacia_la_vuelta_abierta(self):
        """Un intento anterior dejó M-99 y un log: después de prepararla, la corrida nueva pasa."""
        raiz = self.evidencia(self.d, "M-01", "M-99")
        (raiz / "servidor.log").write_text("viejo")
        self.assertIn("evidencia de M-99, que no es un caso automatizable de manuales", self.correr()[1]["errores"])
        for _ in range(2):
            rc, datos = cli("prepara-evidencia", "--dir", self.d, "--ronda", 1)
            self.assertEqual((rc, list(raiz.iterdir())), (0, []), datos)
        self.evidencia(self.d, "M-01")
        self.assertEqual(self.correr()[0], 0)

    def test_prepara_evidencia_no_toca_vuelta_cruzada_fuera_de_orden_ni_enlace(self):
        self.assertIn("la vuelta 1 no se cruzó", cli("prepara-evidencia", "--dir", self.d, "--ronda", 2)[1]["errores"][0])
        raiz = self.evidencia(self.d, "M-01")
        self.correr()
        (raiz / "cruce.json").write_text(json.dumps({"ok": True}))
        self.assertIn("ya se cruzó", cli("prepara-evidencia", "--dir", self.d, "--ronda", 1)[1]["errores"][0])
        self.assertTrue((raiz / "M-01" / "pasos.json").is_file())
        fuera = self.base / "fuera"
        fuera.mkdir()
        (fuera / "x").write_text("x")
        (self.d / "evidencia" / "ronda-2").symlink_to(fuera)
        self.assertIn("enlace simbólico", cli("prepara-evidencia", "--dir", self.d, "--ronda", 2)[1]["errores"][0])
        self.assertTrue((fuera / "x").is_file())

    def test_vueltas_en_orden_e_inmutables(self):
        self.evidencia(self.d, "M-01", ronda=2)
        self.assertIn("la vuelta 1 no se cruzó", self.correr(2)[1]["errores"][0])
        self.evidencia(self.d, "M-01")
        self.correr()
        (self.d / "evidencia" / "ronda-1" / "cruce.json").write_text(json.dumps({"ok": True}))
        self.assertIn("ya se cruzó", self.correr()[1]["errores"][0])

    def test_arbol_sucio_y_sin_manuales(self):
        self.evidencia(self.d, "M-01")
        (self.repo / "suelto.txt").write_text("x")
        self.assertIn("cambios sin commit", self.correr()[1]["errores"][0])
        d = self.base / "D2"
        (self.repo / "suelto.txt").unlink()
        cli("inicia", "--plan", self.plan(), "--repo", self.repo, "--suite", SUITE, "--dir", d)
        self.evidencia(d, "M-01")
        self.assertIn("manuales.json no está validado", cli("evidencia", "--dir", d, "--ronda", 1)[1]["errores"][0])

    def test_alertas_y_escape(self):
        paso = paso_ok(consola=[{"tipo": "pageerror", "texto": "<img src=x onerror=1>"}], red=[{"estado": "500"}])
        self.assertEqual(ip.alertas_de_paso(paso, self.base), ["sin captura", "pasa con errores de consola",
                                                                "pasa con respuestas 5xx"])
        self.evidencia(self.d, "M-01", pasos=[paso])
        self.correr()
        self.assertNotIn("<img src=x", (self.d / "evidencia" / "ronda-1" / "index.html").read_text())


class CruzaTest(Base):
    def setUp(self):
        super().setUp()
        self.d = self.registro()
        self.congelar_manuales(self.d, caso_m(1, "feliz"), caso_m(2), caso_m(3, automatizable=False, razon="SMS"))

    def armar(self, estado="passed", ronda=1, casos=("M-01", "M-02")):
        self.evidencia(self.d, *casos, ronda=ronda, estado=estado)
        return cli("evidencia", "--dir", self.d, "--ronda", ronda)

    def cruza(self, codex, claude, ronda=1, con_nonce=True):
        if con_nonce:
            a, b = self.revision(self.d, ronda, *codex, nombre="a.json"), self.revision(self.d, ronda, *claude,
                                                                                        nombre="b.json")
        else:
            a, b = (self.json(n, {"identificador": f"vuelta {ronda} · viejo", "resumen": "r", "casos": c})
                    for n, c in (("a.json", codex), ("b.json", claude)))
        return cli("cruza", "--dir", self.d, "--ronda", ronda, "--codex", a, "--claude", b)

    def test_ambos_correctos_y_la_prueba_pasa(self):
        self.armar()
        todos = [dictamen("M-01"), dictamen("M-02")]
        self.assertEqual(self.cruza(todos, todos)[0], 0)
        self.assertIn("ya se cruzó", self.cruza(todos, todos)[1]["errores"][0])

    def test_revision_sin_identificador_o_incompleta_no_gasta_la_vuelta(self):
        self.armar()
        todos = [dictamen("M-01"), dictamen("M-02")]
        self.assertIn("es de otra vuelta o de otra evidencia", self.cruza(todos, todos, con_nonce=False)[1]["errores"][0])
        rc, datos = self.cruza([dictamen("M-01")], todos)
        self.assertEqual(rc, 2)
        self.assertIn("revisión incompleta", datos["errores"][0])
        self.assertFalse((self.d / "evidencia" / "ronda-1" / "cruce.json").exists())
        self.assertEqual(self.cruza(todos, todos)[0], 0)

    def test_evidencia_alterada_despues_de_armarla(self):
        self.armar()
        (self.d / "evidencia" / "ronda-1" / "M-01" / "paso-01.png").write_bytes(png(3, 3))
        todos = [dictamen("M-01"), dictamen("M-02")]
        self.assertIn("la evidencia cambió después de armarla", self.cruza(todos, todos)[1]["errores"][0])

    def test_caso_que_falla_no_entra_aunque_digan_correcto(self):
        self.armar(estado="failed")
        todos = [dictamen("M-01", reportado="falla"), dictamen("M-02", reportado="falla")]
        rc, datos = self.cruza(todos, todos)
        self.assertEqual(rc, 1)
        self.assertTrue(all("no pasa (falla)" in " ".join(c["motivos"]) for c in datos["corregir"]))

    def test_reportado_erroneo_y_revisor_que_repite(self):
        self.armar()
        rc, datos = self.cruza([dictamen("M-01", reportado="falla"), dictamen("M-02")],
                               [dictamen("M-01"), dictamen("M-02")])
        self.assertIn("codex dice que reportó «falla»", datos["corregir"][0]["motivos"][0])
        self.armar(ronda=2)
        rc, datos = self.cruza([dictamen("M-01", "falso-positivo"), dictamen("M-01"), dictamen("M-02")],
                               [dictamen("M-01"), dictamen("M-02")], ronda=2)
        self.assertIn("repite casos", datos["errores"][0])

    def test_no_cruza_evidencia_con_errores_ni_de_otro_head(self):
        self.armar(casos=("M-01",))
        self.assertIn("tiene errores", self.cruza([dictamen("M-01")], [dictamen("M-01")])[1]["errores"][0])
        self.armar()
        commit(self.repo, "app.py", "cambio\n")
        self.assertIn("el HEAD cambió", self.cruza([dictamen("M-01"), dictamen("M-02")],
                                                   [dictamen("M-01"), dictamen("M-02")])[1]["errores"][0])

    def test_tres_fallas_seguidas_escalan(self):
        malo, bien = [dictamen("M-01", "falso-positivo"), dictamen("M-02")], [dictamen("M-01"), dictamen("M-02")]
        for k in (1, 2, 3):
            self.armar(ronda=k)
            rc, datos = self.cruza(malo, bien, ronda=k)
        self.assertEqual((datos["accion"], datos["discrepancias"]), ("escalar", ["M-01"]))
        self.evidencia(self.d, "M-01", "M-02", ronda=4)
        self.assertIn("3 vueltas seguidas sin aprobar", cli("evidencia", "--dir", self.d, "--ronda", 4)[1]["errores"][0])

    def test_una_asercion_debil_de_un_solo_revisor_no_bloquea(self):
        """Uno dice «asercion-debil» y el otro «correcto»: se confirma con nota. Los dos, o cualquier otro dictamen,
        bloquean."""
        for a, b, confirmado in (("asercion-debil", "correcto", True), ("correcto", "asercion-debil", True),
                                 ("asercion-debil", "asercion-debil", False), ("falso-positivo", "correcto", False),
                                 ("asercion-debil", "inconcluso", False), ("inconcluso", "correcto", False)):
            res = ip.cruzar({"casos": [dictamen("M-01", a)]}, {"casos": [dictamen("M-01", b)]}, {"M-01": "pasa"})
            self.assertEqual((res["ok"], res["confirmados"] == ["M-01"]), (confirmado, confirmado), (a, b))
            self.assertEqual([n["caso"] for n in res["notas"]], ["M-01"] if confirmado else [], (a, b))
        res = ip.cruzar({"casos": [dictamen("M-01", "asercion-debil")]}, {"casos": [dictamen("M-01")]}, {"M-01": "falla"})
        self.assertFalse(res["ok"])

    def test_lo_confirmado_no_se_vuelve_a_revisar_si_solo_cambio_otro_spec(self):
        """Vuelta 2 tras cambiar solo el spec de M-02: M-01 se hereda y los revisores solo ven M-02. Se vuelve a revisar
        si cambia producción, su propio spec o su caso manual (una enmienda)."""
        def armar(ronda, esperados=None):
            for caso in ("M-01", "M-02"):
                self.evidencia(self.d, caso, ronda=ronda, archivo=f"e2e/{caso.lower()}.spec.ts",
                               pasos=[paso_ok(esperado=(esperados or {}).get(caso, "Se ve"))])
            return cli("evidencia", "--dir", self.d, "--ronda", ronda)[1]
        for spec in ("e2e/m-01.spec.ts", "e2e/m-02.spec.ts"):
            commit(self.repo, spec, "// spec\n")
        self.assertEqual((armar(1)["heredados"], armar(1)["revisar"]), ([], ["M-01", "M-02"]))
        self.cruza([dictamen("M-01"), dictamen("M-02", "falso-positivo")], [dictamen("M-01"), dictamen("M-02")])
        commit(self.repo, "e2e/m-02.spec.ts", "// spec más fuerte\n")
        datos = armar(2)
        self.assertEqual((datos["heredados"], datos["revisar"]), (["M-01"], ["M-02"]))
        rc, res = self.cruza([dictamen("M-02")], [dictamen("M-02")], ronda=2)
        self.assertEqual((rc, res["confirmados"], res["heredados"]), (0, ["M-01", "M-02"], ["M-01"]), res)
        self.assertEqual(armar(3)["heredados"], ["M-01", "M-02"])
        commit(self.repo, "app.py", APP + "# corrige\n")
        self.assertEqual(armar(3)["heredados"], [])
        git(self.repo, "reset", "-q", "--hard", "HEAD~1")
        commit(self.repo, "e2e/m-01.spec.ts", "// otro spec\n")
        self.assertEqual(armar(3)["heredados"], ["M-02"])
        cli("enmienda-manual", "--dir", self.d, "--caso", "M-02", "--paso", 1, "--esperado", "Otro", "--motivo", "r1",
            "--autorizacion", "Sí")
        self.assertEqual(armar(3, {"M-02": "Otro"})["heredados"], [])

    def test_vuelta_extra_con_texto_de_juan_y_solo_una(self):
        """Tras 3 vueltas sin aprobar, la 4 se abre con el texto de Juan (sellado: «evidencia» y «cruza» ya no lo
        piden) y, si tampoco aprueba, no hay quinta."""
        malo, bien = [dictamen("M-01", "falso-positivo"), dictamen("M-02")], [dictamen("M-01"), dictamen("M-02")]
        texto = "Una vuelta más"
        self.assertIn("no pasa del límite", cli("prepara-evidencia", "--dir", self.d, "--ronda", 1,
                                                 "--vuelta-extra-autorizada", texto)[1]["errores"][0])
        for k in (1, 2, 3):
            self.armar(ronda=k)
            self.cruza(malo, bien, ronda=k)
        self.assertIn("--vuelta-extra-autorizada", cli("prepara-evidencia", "--dir", self.d, "--ronda", 4)[1]["errores"][0])
        self.assertEqual(cli("prepara-evidencia", "--dir", self.d, "--ronda", 4, "--vuelta-extra-autorizada", texto)[0], 0)
        self.assertEqual(json.loads((self.d / "evidencia" / "vuelta-extra.json").read_text())["autorizacion"], texto)
        self.assertEqual(self.armar(ronda=4)[0], 0)
        rc, datos = self.cruza(malo, bien, ronda=4)
        self.assertEqual((rc, datos["accion"]), (1, "escalar"))
        self.assertIn("ya se usó la vuelta extra", cli("prepara-evidencia", "--dir", self.d, "--ronda", 5,
                                                        "--vuelta-extra-autorizada", texto)[1]["errores"][0])

    def test_tras_la_vuelta_extra_otra_solo_si_cambio_produccion(self):
        """La vuelta extra (4) tampoco aprueba; se corrige producción: la vuelta 5 vuelve a evidenciar ese código sin
        otra autorización. Un cambio de documentación no la abre, y sin cambios nuevos no hay sexta."""
        malo, bien = [dictamen("M-01", "falso-positivo"), dictamen("M-02")], [dictamen("M-01"), dictamen("M-02")]
        for k in (1, 2, 3, 4):
            if k == 4:
                cli("prepara-evidencia", "--dir", self.d, "--ronda", 4, "--vuelta-extra-autorizada", "Vuelta 4")
            self.armar(ronda=k)
            self.cruza(malo, bien, ronda=k)
        commit(self.repo, "README.md", "Notas\n")
        self.assertIn("nada de producción, e2e ni manuales.json cambió", cli("prepara-evidencia", "--dir", self.d, "--ronda", 5)[1]["errores"][0])
        commit(self.repo, "app.py", APP + "# corrige la ronda 1\n")
        self.assertEqual(cli("prepara-evidencia", "--dir", self.d, "--ronda", 5)[0], 0)
        self.assertEqual(self.armar(ronda=5)[0], 0)
        self.assertEqual(self.cruza(malo, bien, ronda=5)[0], 1)
        self.assertIn("nada de producción, e2e ni manuales.json cambió desde la vuelta 5",
                      cli("prepara-evidencia", "--dir", self.d, "--ronda", 6)[1]["errores"][0])
        cli("enmienda-manual", "--dir", self.d, "--caso", "M-01", "--paso", 1, "--esperado", "Otro", "--motivo", "r1",
            "--autorizacion", "Sí")
        self.assertEqual(cli("prepara-evidencia", "--dir", self.d, "--ronda", 6)[0], 0)


class RondasTest(Base):
    def setUp(self):
        super().setUp()
        self.d = self.registro()

    def registra(self, ronda, juez, datos=None, con_nonce=True):
        datos = datos or veredicto()
        if con_nonce:
            datos = {**datos, "resumen": f"{self.identificador(self.d, ronda)} · revisado"}
        return cli("registra", "--dir", self.d, "--ronda", ronda, "--juez", juez,
                   "--archivo", self.json(f"{juez}-{ronda}-{len(list(self.base.glob('*.json')))}.json", datos))

    def ronda(self, codex=None, claude=None):
        rc, datos = cli("abre-ronda", "--dir", self.d)
        self.assertEqual(rc, 0, datos)
        self.registra(datos["ronda"], "codex", codex)
        self.registra(datos["ronda"], "claude", claude)
        return datos["ronda"]

    def test_ronda_congela_diff_y_da_identificador(self):
        self.assertEqual(ip.siguiente(self.d), {"accion": "abrir-ronda", "ronda": 1})
        commit(self.repo, "app.py", APP + "# nuevo\n")
        rc, datos = cli("abre-ronda", "--dir", self.d)
        self.assertIn("+# nuevo", Path(datos["diff"]).read_text())
        self.assertIn("chore: cambia app.py", (self.d / "ronda-1" / "commits.txt").read_text())
        self.assertEqual(datos["identificador"], f"ronda 1 · {datos['nonce']} · {datos['head'][:12]} · "
                                                 f"{datos['diff_sha256'][:12]}")

    def test_veredicto_de_otra_ronda_o_con_el_identificador_fuera_de_lugar(self):
        cli("abre-ronda", "--dir", self.d)
        rc, datos = self.registra(1, "codex", con_nonce=False)
        self.assertEqual(rc, 2)
        self.assertIn("no empieza con el identificador de la ronda", datos["errores"][0])
        prosa = self.base / "x.md"
        prosa.write_text(f"{self.identificador(self.d, 1)}\n```json\n{json.dumps(veredicto(resumen='viejo'))}\n```\n")
        rc, datos = cli("registra", "--dir", self.d, "--ronda", 1, "--juez", "codex", "--archivo", prosa)
        self.assertIn("no empieza con el identificador", datos["errores"][0])

    def test_cambio_que_toca_archivos_con_nombre_de_secreto(self):
        commit(self.repo, "config/api_token.py", "X = 1\n")
        rc, datos = cli("abre-ronda", "--dir", self.d)
        self.assertIn("pregunta a Juan", datos["errores"][0])
        rc, datos = cli("abre-ronda", "--dir", self.d, "--omitidos-autorizados", "Juan: revísenlo sin ese archivo")
        self.assertEqual((rc, datos["omitidos"]), (0, ["config/api_token.py"]))
        self.assertNotIn("api_token", Path(datos["diff"]).read_text())

    def test_registra_fuera_de_turno_sobrescribe_o_con_head_nuevo(self):
        self.assertIn("la ronda en curso es la 0", cli("registra", "--dir", self.d, "--ronda", 1, "--juez", "codex",
                                                       "--archivo", self.json("v.json", veredicto()))[1]["errores"][0])
        cli("abre-ronda", "--dir", self.d)
        self.registra(1, "codex", veredicto("necesita-trabajo", [hallazgo("grave")]))
        self.assertIn("no se sobrescribe", self.registra(1, "codex")[1]["errores"][0])
        commit(self.repo, "app.py", APP + "# a media ronda\n")
        self.assertIn("el HEAD cambió", self.registra(1, "claude")[1]["errores"][0])
        self.assertEqual(ip.siguiente(self.d)["accion"], "escalar")

    def test_veredicto_fabricado_a_mano_o_diff_alterado(self):
        cli("abre-ronda", "--dir", self.d)
        self.registra(1, "codex", veredicto("necesita-trabajo", [hallazgo("grave")]))
        (self.d / "ronda-1" / "revision-claude.json").write_text(json.dumps({**veredicto(), "_head": self.head()}))
        self.assertIn("claude: veredicto que no pasó por «registra»", ip.siguiente(self.d)["motivos"][0])
        (self.d / "ronda-1" / "cambios.diff").write_text("otro diff")
        self.assertIn("el diff de la ronda cambió", ip.siguiente(self.d)["motivos"])

    def test_aprobado_y_aprobado_sobre_otro_arbol(self):
        self.ronda(claude=veredicto(hallazgos=[hallazgo("menor")]))
        self.assertEqual(cli("siguiente", "--dir", self.d)[1]["accion"], "aprobado")
        commit(self.repo, "app.py", APP + "# después\n")
        self.assertIn("aprobado sobre otro árbol", ip.siguiente(self.d)["motivos"][0])

    def test_otra_ronda_exige_cambio_o_respuesta(self):
        self.ronda(codex=veredicto(hallazgos=[hallazgo("medio")]))
        self.assertIn("nada cambió desde la ronda 1", cli("abre-ronda", "--dir", self.d)[1]["errores"][0])
        (self.d / "ronda-1" / "respuesta.md").write_text("El hallazgo es falso: app.py:2 ya valida (salida de pytest).")
        self.assertEqual(cli("abre-ronda", "--dir", self.d)[1]["ronda"], 2)

    def test_no_abre_si_la_anterior_no_termino_o_se_aprobo(self):
        cli("abre-ronda", "--dir", self.d)
        self.assertIn("(revisar)", cli("abre-ronda", "--dir", self.d)[1]["errores"][0])
        self.registra(1, "codex")
        self.registra(1, "claude")
        self.assertIn("(aprobado)", cli("abre-ronda", "--dir", self.d)[1]["errores"][0])

    def test_tercera_ronda_escala_y_no_hay_cuarta(self):
        malo = veredicto("necesita-trabajo", [hallazgo("grave")])
        for n in (1, 2, 3):
            if n > 1:
                commit(self.repo, "app.py", APP + f"# intento {n}\n")
            self.ronda(codex=malo)
        self.assertEqual(ip.siguiente(self.d)["accion"], "escalar")
        commit(self.repo, "app.py", APP + "# cuarto\n")
        self.assertIn("ya se usaron las 3 rondas", cli("abre-ronda", "--dir", self.d)[1]["errores"][0])

    def test_ronda_extra_con_texto_de_juan_aprueba_sin_graves(self):
        """Tras la tercera ronda, Juan da una más: sin graves se aprueba y los medios quedan abiertos; con un grave
        escala, y no hay quinta."""
        texto = "corregir y una 4 ronda, si ya no salen hallazgos graves se da por terminado"
        self.assertIn("no pasa del máximo", cli("abre-ronda", "--dir", self.d, "--ronda-extra-autorizada", texto)[1]["errores"][0])
        medio = veredicto("necesita-trabajo", [{**hallazgo("medio"), "donde": "candidates/tasks.py:42"}])
        for n in (1, 2, 3):
            if n > 1:
                commit(self.repo, "app.py", APP + f"# intento {n}\n")
            self.ronda(codex=medio)
        commit(self.repo, "app.py", APP + "# cuarto\n")
        self.assertIn("--ronda-extra-autorizada", cli("abre-ronda", "--dir", self.d)[1]["errores"][0])
        rc, datos = cli("abre-ronda", "--dir", self.d, "--ronda-extra-autorizada", texto)
        self.assertEqual((rc, datos["ronda"], datos["ronda_extra_autorizada"]), (0, 4, texto))
        self.registra(4, "codex", medio)
        self.registra(4, "claude", veredicto("necesita-trabajo", [hallazgo("menor")]))
        res = ip.siguiente(self.d)
        self.assertEqual((res["accion"], [h["donde"] for h in res["abiertos"]]), ("aprobado", ["candidates/tasks.py:42"]))
        self.assertEqual(ip._ronda_extra(self.d), texto)
        (self.d / "pr.md").write_text("Cambio.\n")
        errores = cli("cierre", "--dir", self.d)[1]["errores"]
        self.assertIn("D/pr.md no lista el hallazgo medio abierto de codex en «candidates/tasks.py:42»", errores)
        self.assertTrue(any("no cita literal la autorización «ronda_extra»" in e for e in errores))
        (self.d / "pr.md").write_text(f"Juan: «{texto}». Queda abierto candidates/tasks.py:42.\n")
        errores = cli("cierre", "--dir", self.d)[1]["errores"]
        self.assertFalse(any("ronda_extra" in e or "hallazgo medio abierto" in e for e in errores), errores)
        (self.d / "ronda-4" / "revision-claude.json").unlink()
        self.registra(4, "claude", veredicto("necesita-trabajo", [hallazgo("grave")]))
        self.assertEqual(ip.siguiente(self.d)["accion"], "escalar")
        commit(self.repo, "app.py", APP + "# quinto\n")
        self.assertIn("ya se usaron las 3 rondas", cli("abre-ronda", "--dir", self.d, "--ronda-extra-autorizada",
                                                       texto)[1]["errores"][0])

    def test_veredicto_invalido_y_juez_desconocido(self):
        cli("abre-ronda", "--dir", self.d)
        self.assertEqual(self.registra(1, "codex", {"veredicto": "quizá", "resumen": "r"})[0], 2)
        self.assertTrue(list((self.d / "ronda-1").glob("invalido-codex-*.json")))
        self.assertIn("juez «gemini»", self.registra(1, "gemini")[1]["errores"][0])
        self.assertEqual(cli("siguiente", "--dir", self.base / "nada")[0], 2)


class SuiteCorreLosRojosTest(Base):
    def test_prueba_que_la_suite_no_corre(self):
        commit(self.repo, "tests/test_extra.py", "import unittest\nfrom app import suma\n\n\nclass U(unittest.TestCase):\n"
               "    def test_borde_extra(self):\n        self.assertEqual(suma(0, 0), 0)\n")
        d = self.registro()
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        cli("suite", "--dir", d, "--fase", "linea-base")
        cli("suite", "--dir", d, "--fase", "fase-1")
        rojos = (("T-01", *ROJOS[0][1:3], PARCHE_RESTA),
                 ("T-02", "tests/test_extra.py::U::test_borde_extra", "python3 -m unittest tests.test_extra.U.test_borde_extra",
                  PARCHE_SOLO_BORDE))
        for caso, prueba, comando, contenido in rojos:
            (self.base / f"{caso}.patch").write_text(contenido)
            rc, datos = cli("rojo", "--dir", d, "--caso", caso, "--prueba", prueba, "--comando", comando, "--parche",
                            self.base / f"{caso}.patch")
            self.assertEqual(rc, 0, datos)
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual(rc, 1)
        en_suite = json.loads((d / "suite-fase-3.json").read_text())["rojos_en_suite"]
        self.assertEqual((en_suite["verificados"], en_suite["fuera"], en_suite["corridas"]),
                         ([ROJOS[0][1]], ["tests/test_extra.py::U::test_borde_extra"], 2))
        self.assertIn("test_suma_borde", en_suite["motivos"]["tests/test_extra.py::U::test_borde_extra"])
        self.assertIn("la suite no corre tests/test_extra.py::U::test_borde_extra (", datos["errores"][0])
        self.assertEqual((self.repo / "app.py").read_text(), APP)

    def test_suite_encadenada_donde_la_mutacion_rompe_el_primer_tramo(self):
        """«A && B»: la mutación de T-02 rompe una prueba de A y su rojo vive en B; B tiene que correr de todos modos."""
        commit(self.repo, "tests/test_extra.py", "import unittest\nfrom app import suma\n\n\nclass U(unittest.TestCase):\n"
               "    def test_borde_extra(self):\n        self.assertEqual(suma(0, 0), 0)\n")
        d = self.registro(suite=f"{SUITE} && python3 -m unittest tests.test_extra")
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        cli("suite", "--dir", d, "--fase", "linea-base")
        cli("suite", "--dir", d, "--fase", "fase-1")
        rojos = (("T-01", *ROJOS[0][1:3], PARCHE_RESTA),
                 ("T-02", "tests/test_extra.py::U::test_borde_extra", "python3 -m unittest tests.test_extra.U.test_borde_extra",
                  PARCHE_SOLO_BORDE))
        for caso, prueba, comando, contenido in rojos:
            (self.base / f"{caso}.patch").write_text(contenido)
            self.assertEqual(cli("rojo", "--dir", d, "--caso", caso, "--prueba", prueba, "--comando", comando, "--parche",
                                 self.base / f"{caso}.patch")[0], 0)
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual(rc, 0, datos)
        en_suite = json.loads((d / "suite-fase-3.json").read_text())["rojos_en_suite"]
        self.assertEqual((sorted(en_suite["verificados"]), en_suite["fuera"], en_suite["corridas"]),
                         (sorted([ROJOS[0][1], "tests/test_extra.py::U::test_borde_extra"]), [], 2))
        self.assertEqual(((self.repo / "app.py").read_text(), git(self.repo, "status", "--porcelain")), (APP, ""))

    def test_mutaciones_de_archivos_distintos_van_en_una_sola_corrida(self):
        commit(self.repo, "resta.py", "def resta(a, b):\n    return a - b\n")
        commit(self.repo, "tests/test_resta.py", "import unittest\nfrom resta import resta\n\n\nclass R(unittest.TestCase):\n"
               "    def test_resta(self):\n        self.assertEqual(resta(5, 3), 2)\n")
        d = self.registro(suite="python3 -m unittest tests.test_app tests.test_resta")
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        cli("suite", "--dir", d, "--fase", "linea-base")
        cli("suite", "--dir", d, "--fase", "fase-1")
        rojos = (("T-01", *ROJOS[0][1:3], PARCHE_RESTA),
                 ("T-02", "tests/test_resta.py::R::test_resta", "python3 -m unittest tests.test_resta.R.test_resta",
                  "--- a/resta.py\n+++ b/resta.py\n@@ -1,2 +1,2 @@\n def resta(a, b):\n-    return a - b\n"
                  "+    return a + b\n"))
        for caso, prueba, comando, contenido in rojos:
            (self.base / f"{caso}.patch").write_text(contenido)
            self.assertEqual(cli("rojo", "--dir", d, "--caso", caso, "--prueba", prueba, "--comando", comando, "--parche",
                                 self.base / f"{caso}.patch")[0], 0)
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual(rc, 0, datos)
        en_suite = json.loads((d / "suite-fase-3.json").read_text())["rojos_en_suite"]
        self.assertEqual((sorted(en_suite["verificados"]), en_suite["fuera"], en_suite["corridas"], en_suite["grupos"]),
                         (sorted([ROJOS[0][1], "tests/test_resta.py::R::test_resta"]), [], 1, [["T-01", "T-02"]]))
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_grupos_sin_archivos_en_comun_y_el_que_falta_se_repite_solo(self):
        """T-01 y T-02 comparten parche (se aplica una vez); T-03 va en el mismo grupo. Si la mutación de T-01 tapa a
        test_c, el parche de T-03 se repite solo; si sola tampoco sale, queda fuera con su motivo."""
        grupos = ip.grupos_de_mutaciones([{"mutados": ["app.py"], "n": 1}, {"mutados": ["app.py"], "n": 2},
                                          {"mutados": ["otro.py"], "n": 3}])
        self.assertEqual([[x["n"] for x in g] for g in grupos], [[1, 3], [2]])
        d = self.registro()
        (d / "rojos").mkdir()
        for caso, texto in (("T-01", "parche 1"), ("T-02", "parche 1"), ("T-03", "parche 3")):
            (d / "rojos" / f"{caso}.patch").write_text(texto)
        (d / "fase-3-rojos.json").write_text(json.dumps({"pruebas": [
            {"caso": "T-01", "prueba": "tests/test_a.py::T::test_a", "mutados": ["app.py"]},
            {"caso": "T-02", "prueba": "tests/test_a.py::T::test_b", "mutados": ["app.py"]},
            {"caso": "T-03", "prueba": "tests/test_c.py::U::test_c", "mutados": ["otro.py"]}]}))
        cfg = json.loads((d / "config.json").read_text())
        grupo = "FAIL: test_a (tests.test_a.T.test_a)\nFAIL: test_b (tests.test_a.T.test_b)\nAssertionError"
        for sola, fuera in (("FAIL: test_c (tests.test_c.U.test_c)\nAssertionError", []),
                            ("FAIL: test_z (tests.test_z.Z.test_z)\nAssertionError", ["tests/test_c.py::U::test_c"])):
            llamadas = []

            def falsa(repo, parches, comando, plazo, sola=sola):
                llamadas.append(len(parches))
                return 1, grupo if len(parches) == 2 else sola
            with mock.patch.object(ip, "con_mutaciones", side_effect=falsa):
                res = ip.rojos_en_suite(d, cfg, 60)
            esperados = sorted({"tests/test_a.py::T::test_a", "tests/test_a.py::T::test_b",
                                "tests/test_c.py::U::test_c"} - set(fuera))
            self.assertEqual((sorted(res["verificados"]), res["fuera"], res["corridas"], llamadas, res["grupos"]),
                             (esperados, fuera, 2, [2, 1], [["T-01", "T-02", "T-03"]]))
            self.assertEqual(list(res["motivos"]), fuera)

    def test_parche_que_ya_no_aplica_no_tumba_la_fase_3(self):
        d = self.registro()
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        cli("suite", "--dir", d, "--fase", "linea-base")
        cli("suite", "--dir", d, "--fase", "fase-1")
        (self.base / "T-01.patch").write_text(PARCHE_RESTA)
        cli("rojo", "--dir", d, "--caso", "T-01", "--prueba", ROJOS[0][1], "--comando", ROJOS[0][2], "--parche", self.base / "T-01.patch")
        commit(self.repo, "app.py", "def suma(a, b):\n    # otra base\n    return a + b\n")
        rc, datos = cli("suite", "--dir", d, "--fase", "fase-3")
        self.assertEqual(rc, 1)
        self.assertIn("repite «rojo» con una mutación nueva", datos["errores"][0])
        self.assertTrue((d / "suite-fase-3.json").is_file())

    def test_tramos_de_nivel_superior_y_suite_sin_corte(self):
        self.assertEqual(ip.tramos_de_nivel_superior('pytest -k "a && b" && npx playwright test'),
                         ['pytest -k "a && b"', "npx playwright test"])
        self.assertEqual(ip.tramos_de_nivel_superior("(cd front && npm test) && pytest"), ["(cd front && npm test)", "pytest"])
        self.assertEqual(ip.suite_sin_corte("python manage.py test"), "python manage.py test")
        r = subprocess.run(["sh", "-c", ip.suite_sin_corte(f"cd {self.base} && false && pwd")], capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (1, str(self.base)))

    def test_suite_con_cd_a_otra_carpeta(self):
        """«A && cd sub && B»: el tramo B corre dentro de sub, igual que en la suite normal."""
        commit(self.repo, "sub/test_sub.py", "import sys\nimport unittest\nsys.path.insert(0, '..')\nfrom app import suma\n\n\n"
               "class U(unittest.TestCase):\n    def test_cero(self):\n        self.assertEqual(suma(0, 0), 0)\n")
        d = self.registro(suite=f"{SUITE} && cd sub && python3 -m unittest test_sub")
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        cli("suite", "--dir", d, "--fase", "linea-base")
        cli("suite", "--dir", d, "--fase", "fase-1")
        (self.base / "T-02.patch").write_text(PARCHE_SOLO_BORDE)
        rc, datos = cli("rojo", "--dir", d, "--caso", "T-02", "--prueba", "sub/test_sub.py::U::test_cero", "--comando",
                        "cd sub && python3 -m unittest test_sub.U.test_cero", "--parche", self.base / "T-02.patch")
        self.assertEqual(rc, 0, datos)
        cli("suite", "--dir", d, "--fase", "fase-3")
        en_suite = json.loads((d / "suite-fase-3.json").read_text())["rojos_en_suite"]
        self.assertEqual((en_suite["verificados"], en_suite["fuera"]), (["sub/test_sub.py::U::test_cero"], []))

    def test_suite_en_verde_no_verifica_aunque_mencione_la_prueba(self):
        d = self.registro()
        (d / "rojos").mkdir()
        (d / "rojos" / "T-01.patch").write_text(PARCHE_RESTA)
        (d / "fase-3-rojos.json").write_text(json.dumps({"pruebas": [{"caso": "T-01", "prueba": ROJOS[0][1]}]}))
        cfg = json.loads((d / "config.json").read_text())
        for rc, salida, verificado in ((0, "test_suma (tests.test_app.T.test_suma) ... ok", False),
                                       (0, "FAIL: test_suma (tests.test_app.T.test_suma)\nAssertionError", False),
                                       (1, "test_suma (tests.test_app.T.test_suma) ... ok\nFAILED (failures=1)", False),
                                       (1, "FAIL: test_suma (tests.test_app.T.test_suma)\nAssertionError", True)):
            with mock.patch.object(ip, "con_mutaciones", return_value=(rc, salida)):
                res = ip.rojos_en_suite(d, cfg, 60)
            self.assertEqual(res["verificados"] == [ROJOS[0][1]], verificado, salida)


class CopiaTest(Base):
    def test_copia_de_head_sin_secretos_ni_archivos_sin_rastrear(self):
        commit(self.repo, "config/api_token.py", "X = 1\n")
        commit(self.repo, ".env.example", "A=1\n")
        d = self.registro()
        (self.base / "fuera.txt").write_text("x")
        rc, datos = cli("copia", "--dir", d)
        copia = Path(datos["copia"])
        self.assertEqual(rc, 0)
        self.assertTrue((copia / "app.py").is_file())
        self.assertFalse((copia / "config" / "api_token.py").exists())
        self.assertFalse((copia / ".env.example").exists())
        self.assertEqual(cli("copia", "--dir", d)[1]["copia"], str(copia))

    def test_copia_con_symlinks_hostiles_y_diff_sin_secretos(self):
        d = self.registro()
        (self.repo / "absoluto").symlink_to("/etc/hosts")
        (self.repo / "afuera").symlink_to("../fuera")
        commit(self.repo, "config/secrets.py", "CLAVE = 1\n")
        rc, datos = cli("copia", "--dir", d)
        self.assertEqual(rc, 0, datos)
        self.assertEqual(sorted(datos["enlaces_omitidos"]), ["absoluto", "afuera"])
        self.assertEqual(datos["omitidos"], ["config/secrets.py"])
        self.assertNotIn("CLAVE", Path(datos["diff"]).read_text())
        self.assertFalse(list((d / "copias").glob(".*.tmp")))


FALSO_REVISOR = """#!{python}
import json, os, pathlib, sys
a = sys.argv[1:]
def lee(r):
    try:
        return pathlib.Path(r).read_text()[:12]
    except Exception as e:
        return type(e).__name__
datos = {{"vivo": lee(os.environ["REPO"] + "/app.py"), "cwd": os.getcwd(), "argv": a, "prompt": sys.stdin.read(),
         "casa": lee(pathlib.Path.home() / ".zshrc")}}
if "-o" in a:
    datos["copia"] = lee(a[a.index("-C") + 1] + "/app.py")
    pathlib.Path(a[a.index("-o") + 1]).write_text(json.dumps(datos))
else:
    print(json.dumps(datos))
"""


class RevisoresTest(Base):
    """Codex corre en sandbox-exec sobre la copia; el revisor Claude, en modo restringido encerrado en la copia y D."""

    def falso(self):
        ruta = self.base / "revisor-falso"
        ruta.write_text(FALSO_REVISOR.format(python=sys.executable))
        ruta.chmod(0o755)
        prompt = self.base / "p.md"
        prompt.write_text("revisa")
        return ruta, prompt

    def test_perfil_solo_deja_leer_lo_necesario(self):
        perfil = ip.perfil_codex(self.repo, self.base / "salida", [self.base / "D"])
        casa = Path.home().resolve()
        for patron in (f'(deny file-read* (subpath "{self.repo}")', f'(deny file-read-data (subpath "{casa}"))',
                       f'(subpath "{self.base / "D"}")', "\\.env", f"^{casa}/(.*/)?[^/]*[Tt][Oo][Kk][Ee][Nn]",
                       ".ssh", "(deny file-write*)"):
            self.assertIn(patron, perfil)

    def test_codex_en_sandbox_desde_el_repo_vivo(self):
        if not shutil.which("sandbox-exec"):
            self.skipTest("sin sandbox-exec")
        d = self.registro()
        falso, prompt = self.falso()
        with contextlib.chdir(self.repo):
            rc, datos = cli("codex", "--dir", d, "--prompt", prompt, "--esquema", "veredicto", "--salida",
                            self.base / "s.json", env={"CODEX_BIN": str(falso), "REPO": str(self.repo)})
        self.assertEqual(rc, 0, datos)
        r = json.loads((self.base / "s.json").read_text())
        self.assertEqual((r["vivo"], r["copia"], r["cwd"]), ("PermissionError", APP[:12], datos["copia"]))
        self.assertTrue(r["prompt"].startswith("revisa"))
        self.assertEqual(r["argv"][r["argv"].index("--model") + 1], "gpt-6.1-sol")
        for bandera in ("--ephemeral", "--ignore-user-config", "project_doc_max_bytes=0"):
            self.assertIn(bandera, r["argv"])
        if (Path.home() / ".zshrc").is_file():
            self.assertEqual(r["casa"], "PermissionError")

    def test_codex_que_falla_se_puede_reintentar_en_el_mismo_segundo(self):
        if not shutil.which("sandbox-exec"):
            self.skipTest("sin sandbox-exec")
        d = self.registro()
        _, prompt = self.falso()
        for _ in range(2):
            rc, datos = cli("codex", "--dir", d, "--prompt", prompt, "--esquema", "veredicto", "--salida",
                            self.base / "s.json", env={"CODEX_BIN": "/usr/bin/false"})
            self.assertIn("Codex falló", datos["errores"][0])
        self.assertFalse((self.base / "s.json").exists())

    def test_claude_restringido_a_la_copia_y_al_registro(self):
        d = self.registro()
        falso, prompt = self.falso()
        with contextlib.chdir(self.repo):
            rc, datos = cli("claude", "--dir", d, "--prompt", prompt, "--esquema", "casos_manuales", "--salida",
                            self.base / "c.md", env={"CLAUDE_BIN": str(falso), "REPO": str(self.repo)})
        self.assertEqual(rc, 0, datos)
        r = json.loads((self.base / "c.md").read_text())
        self.assertEqual(r["cwd"], datos["copia"])
        self.assertTrue(r["prompt"].startswith("revisa"))
        for bandera in ("--restricted", "--safe-mode", "--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(bandera, r["argv"])
        self.assertEqual((r["argv"][r["argv"].index("--tools") + 1], r["argv"][r["argv"].index("--add-dir") + 1],
                          r["argv"][r["argv"].index("--model") + 1]), ("Read,Grep,Glob", str(d), "opus"))
        rc, datos = cli("claude", "--dir", d, "--prompt", prompt, "--esquema", "casos_manuales", "--salida",
                        self.base / "c2.md", env={"CLAUDE_BIN": "/usr/bin/false"})
        self.assertIn("el revisor Claude falló", datos["errores"][0])

    def test_los_revisores_reciben_el_esquema_dentro_del_prompt(self):
        """Encerrados en la copia y en D no pueden leer ~/.claude/schemas: el esquema viaja en el prompt y queda guardado."""
        d = self.registro()
        falso, prompt = self.falso()
        rc, datos = cli("claude", "--dir", d, "--prompt", prompt, "--esquema", "veredicto", "--salida", self.base / "r" / "c.md",
                        env={"CLAUDE_BIN": str(falso), "REPO": str(self.repo)})
        self.assertEqual(rc, 0, datos)
        recibido = json.loads((self.base / "r" / "c.md").read_text())["prompt"]
        self.assertIn("UN solo bloque ```json", recibido)
        for campo in ('"necesita-trabajo"', '"criterio"', '"no-corrio"'):
            self.assertIn(campo, recibido)
        self.assertEqual((self.base / "r" / "c.prompt.md").read_text(), recibido)
        if not shutil.which("sandbox-exec"):
            return
        rc, datos = cli("codex", "--dir", d, "--prompt", prompt, "--esquema", "casos_prueba", "--salida", self.base / "r" / "h.json",
                        env={"CODEX_BIN": str(falso), "REPO": str(self.repo)})
        self.assertEqual(rc, 0, datos)
        recibido = json.loads((self.base / "r" / "h.json").read_text())["prompt"]
        self.assertIn("Responde solo con el JSON", recibido)
        self.assertIn('"por_que_falta"', recibido)
        self.assertEqual((self.base / "r" / "h.prompt.md").read_text(), recibido)


class VerificacionTest(Base):
    def test_une_plan_suite_y_nuevos_y_amarra_a_head(self):
        d = self.registro()
        rc, datos = cli("verificacion", "--dir", d, "--comando", "npx playwright test", "--comando", SUITE)
        self.assertEqual(rc, 0, datos)
        self.assertEqual(datos["comandos"], ["python3 -m unittest tests.test_app -v", SUITE, "npx playwright test"])
        texto = (d / "verificacion.html").read_text()
        m = re.search(r"Base:(.{0,200}?)\b([0-9a-f]{7,40})\b", re.sub(r"<[^>]+>", " ", texto))
        self.assertEqual(m.group(2), self.head())

    def test_plan_markdown_hereda_su_automatica(self):
        md = ("# Plan\n## Verificación\n```bash\n# Automática\npytest -k \"a and b\" && echo ok\n"
              "# Manual\nver pantalla\n```\n## Riesgos\nnada\n")
        d = self.registro(plan=self.plan(md, "plan-sesion.md"))
        self.assertEqual(cli("verificacion", "--dir", d)[1]["comandos"], ["pytest -k \"a and b\" && echo ok", SUITE])

    def test_verificacion_declarada_pero_ilegible(self):
        for nombre, texto in (("v.md", "## Verificación\nCorrer pytest a mano.\n"),
                              ("v.html", "<h2 class='x'>Verificación</h2><p>pytest</p>")):
            d = self.base / f"D-{nombre}"
            cli("inicia", "--plan", self.plan(texto, nombre), "--repo", self.repo, "--suite", SUITE, "--dir", d)
            self.assertEqual(cli("verificacion", "--dir", d)[0], 1, nombre)
            rc, datos = cli("verificacion", "--dir", d, "--comando", "pytest -q", "--plan-ilegible",
                            "la Verificación del plan es prosa; sus comandos van en --comando")
            self.assertEqual(rc, 0, datos)

    def test_plan_ilegible_descarta_lo_heredado_y_exige_sustitutos(self):
        md = "## Verificación\n```\n# Automática\npython3 /Users/usuario/proj/manage.py test\n```\n"
        d = self.registro(plan=self.plan(md, "abs.md"))
        self.assertIn("ruta absoluta", cli("verificacion", "--dir", d)[1]["errores"][0])
        self.assertIn("pasa con --comando", cli("verificacion", "--dir", d, "--plan-ilegible", "Juan: sí")[1]["errores"][0])
        rc, datos = cli("verificacion", "--dir", d, "--plan-ilegible", "Juan: usa manage.py relativo",
                        "--comando", "python3 manage.py test")
        self.assertEqual((rc, datos["comandos"]), (0, [SUITE, "python3 manage.py test"]))

    def test_rechaza_rutas_absolutas_triviales_e_ilegibles(self):
        self.assertEqual(ip.revisar_comando("pytest -q 2>/dev/null && cat ./x"), [])
        for comando in ("python3 /tmp/x.py", "pytest --rootdir=/opt/app", "cat </etc/passwd", "ls ~/x", "true",
                        "echo 'sin cerrar"):
            self.assertTrue(ip.revisar_comando(comando), comando)


class CierreTest(Base):
    def valida_falsa(self, rc, resultado=None):
        falso = self.base / f"valida_{rc}.py"
        falso.write_text("import json, sys, pathlib\nd = pathlib.Path(sys.argv[sys.argv.index('--registro') + 1])\n"
                         f"(d / 'impl-validacion.json').write_text(json.dumps({resultado or {'aprobado': rc == 0}!r}))\n"
                         f"print(json.dumps({{'aprobado': {rc == 0}}}))\nsys.exit({rc})\n")
        return mock.patch.object(ip, "VALIDA_IMPL", falso)

    def completo(self, evidencia_ok=True, pasos=None):
        d = self.registro()
        cli("suite", "--dir", d, "--fase", "linea-base")
        git(self.repo, "switch", "-q", "-c", "feature/prueba")
        cli("suite", "--dir", d, "--fase", "fase-1")
        (d / "fase-2-huecos.json").write_text(json.dumps(huecos_dos()))
        cli("casos", "--dir", d)
        for caso, prueba, comando, contenido in ROJOS:
            ruta = self.base / f"{caso}.patch"
            ruta.write_text(contenido)
            cli("rojo", "--dir", d, "--caso", caso, "--prueba", prueba, "--comando", comando, "--parche", ruta)
        cli("suite", "--dir", d, "--fase", "fase-3")
        self.congelar_manuales(d)
        self.evidencia(d, "M-01", pasos=pasos)
        cli("evidencia", "--dir", d, "--ronda", 1)
        codex = dictamen("M-01") if evidencia_ok else dictamen("M-01", "falso-positivo")
        rc, datos = cli("cruza", "--dir", d, "--ronda", 1, "--codex", self.revision(d, 1, codex, nombre="a.json"),
                        "--claude", self.revision(d, 1, dictamen("M-01"), nombre="b.json"))
        self.assertEqual(rc, 0 if evidencia_ok else 1, datos)
        return d

    def aprobar(self, d, rc_valida=0, resultado=None, pr="Cambio con pruebas.\n"):
        cli("abre-ronda", "--dir", d)
        ident = self.identificador(d, 1)
        for juez in ("codex", "claude"):
            cli("registra", "--dir", d, "--ronda", 1, "--juez", juez,
                "--archivo", self.json("v.json", veredicto(resumen=f"{ident} · ok")))
        cli("verificacion", "--dir", d)
        with self.valida_falsa(rc_valida, resultado), contextlib.redirect_stderr(io.StringIO()):
            cli("valida", "--dir", d)
        cli("suite", "--dir", d, "--fase", "final")
        (d / "pr.md").write_text(pr)

    def test_todo_en_orden(self):
        d = self.completo()
        self.aprobar(d)
        rc, datos = cli("cierre", "--dir", d)
        self.assertEqual(rc, 0, datos)
        self.assertTrue((d / "cierre.json").is_file())

    def test_cierre_arma_un_solo_html_con_pestanas_y_las_capturas_adentro(self):
        d = self.completo()
        validacion = {"aprobado": True, "motivos": [], "veredicto": {"veredicto": "pasa", "resumen": "ok",
                                                                      "hallazgos": []},
                      "evidencia": [{"comando": SUITE, "resultado": "verde", "salida": "OK api_key=abcd1234efgh5678"}]}
        self.aprobar(d, resultado=validacion)
        rc, datos = cli("cierre", "--dir", d)
        self.assertEqual(rc, 0, datos)
        html = Path(datos["reporte"]).read_text(encoding="utf-8")
        self.assertEqual(Path(datos["reporte"]), d / "reporte-pruebas.html")
        self.assertEqual(re.findall(r"<label for='pt-\d+'>([^<]+)</label>", html),
                         ["Suite", "Unitarias", "Manuales", "Validación aislada"])
        self.assertIn("data:image/png;base64," + base64.b64encode(png()).decode(), html)
        self.assertNotIn("paso-01.png'", html)
        self.assertIn("confirmado por los dos revisores", html)
        self.assertIn("<span class='alerta'>Te toca a ti</span>: SMS", html)
        self.assertEqual(html.count("<span class='pasa'>válido</span>"), 2)
        self.assertIn("La salida no lista cada prueba", html)
        self.assertNotIn("abcd1234efgh5678", html)
        self.assertIn("cierre: aprobado", html)
        commit(self.repo, "README.md", "Notas\n", mensaje="docs: notas")
        html = Path(cli("reporte", "--dir", d)[1]["html"]).read_text(encoding="utf-8")
        self.assertIn("cierre: de otro commit", html)

    def test_cierre_con_errores_tambien_deja_el_reporte(self):
        d = self.registro()
        rc, datos = cli("cierre", "--dir", d)
        self.assertEqual(rc, 1)
        html = Path(datos["reporte"]).read_text(encoding="utf-8")
        self.assertIn("cierre: con ", html)
        self.assertIn("Sin señal: no hay casos manuales congelados", html)
        self.assertFalse((d / "cierre.json").exists())

    def test_reporte_lista_cada_prueba_y_una_pestana_por_tipo(self):
        d = self.registro(suite=f"{SUITE} -v")
        cli("suite", "--dir", d, "--fase", "linea-base")
        (d / "fase-2-huecos.json").write_text(json.dumps({"resumen": "r", "no_aplica": [], "casos": [
            caso_t(1, tipo="seguridad"), caso_t(2, tipo="unitaria")]}))
        rc, datos = cli("reporte", "--dir", d)
        self.assertEqual(rc, 0, datos)
        html = Path(datos["html"]).read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"<label for='pt-\d+'>([^<]+)</label>", html),
                         ["Suite", "Unitarias", "Seguridad", "Manuales", "Validación aislada"])
        self.assertIn("<summary>Pasan (2)</summary>", html)
        self.assertIn("<tr><td>test_suma (tests.test_app.T.test_suma)</td><td class='pasa'>pasa</td></tr>", html)
        self.assertEqual(html.count("sin prueba vista en rojo"), 2)
        self.assertIn("cierre: sin correr", html)

    def test_evidencia_sin_aprobar_no_cierra_y_no_hay_como_cortarla(self):
        d = self.completo(evidencia_ok=False)
        self.aprobar(d, pr="Cambio con pruebas.\n")
        rc, datos = cli("cierre", "--dir", d)
        self.assertEqual(rc, 1, datos)
        self.assertTrue(any("no se corta ni se omite" in e for e in datos["errores"]), datos["errores"])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli("cierre", "--dir", d, "--evidencia-sin-aprobar-autorizada", "Juan: corta")

    def test_enmienda_despues_de_la_evidencia_exige_otra_vuelta_y_va_en_el_pr(self):
        d = self.completo()
        self.aprobar(d)
        cli("enmienda-manual", "--dir", d, "--caso", "M-01", "--paso", 1, "--esperado", "Se ve en una línea",
            "--motivo", "ronda 1, app.py:2", "--autorizacion", "Sí, enmiéndalo")
        errores = cli("cierre", "--dir", d)[1]["errores"]
        self.assertTrue(any("manuales.json cambió (una enmienda) después de la evidencia de ronda-1" in e for e in errores))
        self.assertIn("D/pr.md no lista la enmienda del caso M-01 paso 1 ni su esperado nuevo", errores)
        self.assertTrue(any("no cita literal la autorización «enmienda_M-01_paso_1_1»" in e for e in errores))

    def test_faltan_fases(self):
        texto = " ".join(cli("cierre", "--dir", self.registro())[1]["errores"])
        for esperado in ("revisión final no está aprobada", "suite «linea-base»", "fase-2-huecos.json",
                         "manuales.json", "validacion.json", "falta D/pr.md"):
            self.assertIn(esperado, texto)

    def test_firma_de_claude_en_commits_o_en_el_pr(self):
        d = self.completo()
        commit(self.repo, "tests/test_extra.py", "import unittest\n",
               mensaje="test: extra\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
        self.aprobar(d, pr="Cambio.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n")
        errores = " ".join(cli("cierre", "--dir", d)[1]["errores"])
        self.assertIn("hay commits con firma de Claude", errores)
        self.assertIn("D/pr.md trae firma de Claude", errores)
        (d / "pr.md").write_text("Cambio.\n\nCo-Authored-By: Bob <bob@x.com>\n")
        self.assertIn("D/pr.md trae firma de Claude", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_pr_con_secreto_o_sin_la_autorizacion_literal(self):
        d = self.completo()
        self.aprobar(d, rc_valida=2, resultado={"aprobado": False, "motivos": ["sin docker"]},
                     pr="Cambio. Token ghp_abcdefghijklmnopqrstuvwxyz0123\n")
        rc, datos = cli("cierre", "--dir", d, "--borrador-autorizado", "Juan: ábrelo en draft, no hay Docker")
        errores = " ".join(datos["errores"])
        self.assertIn("D/pr.md trae un posible secreto", errores)
        self.assertIn("no cita literal la autorización «borrador»", errores)
        (d / "pr.md").write_text("Draft. Autorización: Juan: ábrelo en draft, no hay Docker\n")
        rc, datos = cli("cierre", "--dir", d, "--borrador-autorizado", "Juan: ábrelo en draft, no hay Docker")
        self.assertEqual((rc, datos["no_validado"]), (0, True))

    def test_prosa_legitima_en_el_pr_y_descartes_listados(self):
        d = self.completo()
        self.aprobar(d, pr="Valida que el password: requiere 8 caracteres. Datos generated with factory_boy. Manda "
                           "Authorization: Bearer <token> y cookie: la sesión dura 2 horas.\n")
        self.assertEqual(cli("cierre", "--dir", d)[0], 0)
        for fuga in ("API_TOKEN=abcdefghijklmnop", "X-Auth=abcdefghijklmnop", "X-Auth-Token: abcdef123456",
                     "password: hunter2abc"):
            (d / "pr.md").write_text(f"Cambio. {fuga}\n")
            self.assertIn("D/pr.md trae un posible secreto", " ".join(cli("cierre", "--dir", d)[1]["errores"]), fuga)
        (d / "pr.md").write_text("Valida el password.\n")
        (d / "fase-2-descartes.json").write_text(json.dumps({"descartes": [{"id": "T-02", "razon": "tests/test_app.py:7"}]}))
        self.assertIn("D/pr.md no lista el caso descartado T-02", cli("cierre", "--dir", d)[1]["errores"])

    def test_sin_casos_automatizables_no_cierra(self):
        """Un registro viejo con manuales.json sin casos automatizables (antes se podía saltar) no llega al PR."""
        d = self.completo()
        self.aprobar(d)
        jurado.escribir_json(d / "manuales.json", manuales(caso_m(1, automatizable=False, razon="SMS")))
        ip._sellar(d, "manuales.json")
        errores = cli("cierre", "--dir", d)[1]["errores"]
        self.assertIn("manuales.json no tiene casos automatizables: la evidencia con captura no se omite", errores)

    def test_evidencia_vieja_por_produccion_o_helper_e2e(self):
        for ruta in ("app.py", "e2e/helpers.ts", "frontend/e2e/otro.spec.ts", "app/prompts/saludo.md",
                     "tests/fixtures/usuarios.json", "tests/helpers/navegador.py", "conftest.py", "e2e/a.spec.ts"):
            with self.subTest(ruta=ruta):
                self.tearDown()
                self.setUp()
                d = self.completo()
                commit(self.repo, ruta, "cambio\n")
                self.aprobar(d)
                self.assertIn("repite las fases 5 y 6", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_documentacion_o_pruebas_unitarias_no_invalidan_la_evidencia(self):
        d = self.completo()
        commit(self.repo, "tests/test_extra.py", "import unittest\n")
        commit(self.repo, "docs/uso.md", "# Uso\n")
        commit(self.repo, "README.md", "# Proyecto\n")
        rc, datos = cli("rojos", "--dir", d, "--repetir")
        self.assertEqual((rc, len(datos["repetidos"])), (0, 0), datos)
        self.aprobar(d)
        self.assertEqual(cli("cierre", "--dir", d)[0], 0)

    def test_que_cambio_invalida_la_evidencia(self):
        specs = {"tests/ui/test_login.py"}
        for ruta, segura in (("tests/test_x.py", True), ("src/a.test.ts", True), ("docs/x.md", True),
                             ("README.md", True), ("tests/ui/test_login.py", False), ("tests/helpers/nav.py", False),
                             ("conftest.py", False), ("e2e/a.spec.ts", False), ("app/prompts/x.md", False)):
            self.assertEqual(ip._es_segura(ruta, specs), segura, ruta)

    def test_evidencia_alterada_despues_de_cruzar(self):
        d = self.completo()
        self.aprobar(d)
        (d / "evidencia" / "ronda-1" / "M-01" / "paso-01.png").write_bytes(png(4, 4))
        self.assertIn("cambió después de cruzarse", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_validacion_de_otro_head(self):
        d = self.completo()
        self.aprobar(d)
        commit(self.repo, "tests/test_extra.py", "import unittest\n")
        errores = " ".join(cli("cierre", "--dir", d)[1]["errores"])
        self.assertIn("la validación aislada es de otro HEAD", errores)
        self.assertIn("la suite final es de otro HEAD", errores)

    def test_validacion_que_no_pudo_correr_exige_autorizacion(self):
        d = self.completo()
        self.aprobar(d, rc_valida=2, resultado={"aprobado": False, "motivos": ["sin docker"]})
        self.assertIn("sin la autorización literal de Juan", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_suite_intermedia_con_rojos_nuevos(self):
        d = self.completo()
        self.aprobar(d)
        fase3 = json.loads((d / "suite-fase-3.json").read_text())
        (d / "suite-fase-3.json").write_text(json.dumps({**fase3, "rc": 1, "fallas": ["test_x (m.T.test_x)"]}))
        self.assertIn("la suite «fase-3» tiene rojos nuevos", " ".join(cli("cierre", "--dir", d)[1]["errores"]))
        (d / "suite-fase-3.json").write_text(json.dumps({**fase3, "head": "0" * 40}))
        self.assertIn("no está después de la fase anterior", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_rojo_sin_comprobar_en_la_suite(self):
        d = self.completo()
        self.aprobar(d)
        fase3 = json.loads((d / "suite-fase-3.json").read_text())
        (d / "suite-fase-3.json").write_text(json.dumps({**fase3, "rojos_en_suite": {"verificados": [], "fuera": []}}))
        self.assertIn(f"no está comprobado que la suite corra {ROJOS[0][1]}",
                      " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_rama_y_commits(self):
        self.assertEqual([bool(ip.RAMA.match(x)) for x in ("feature/PROJ-123-algo", "fix/area/Login", "hotfix/x", "feature/")],
                         [True, True, False, False])
        d = self.completo()
        git(self.repo, "switch", "-q", "-c", "lateral", "main" if "main" in git(self.repo, "branch") else "master")
        commit(self.repo, "docs/notas.md", "n\n", mensaje="docs: notas")
        git(self.repo, "switch", "-q", "feature/prueba")
        git(self.repo, "merge", "-q", "--no-ff", "--no-edit", "lateral")
        commit(self.repo, "tests/test_otro.py", "import unittest\n", mensaje="test(e2e): agrega specs")
        git(self.repo, "revert", "--no-edit", "HEAD")
        self.aprobar(d)
        self.assertEqual(cli("cierre", "--dir", d)[0], 0)
        commit(self.repo, "tests/test_extra.py", "import unittest\n", mensaje="arreglo varias cosas")
        self.aprobar(d)
        self.assertIn("commits que no siguen Conventional Commits", " ".join(cli("cierre", "--dir", d)[1]["errores"]))
        self.tearDown()
        self.setUp()
        d = self.completo()
        git(self.repo, "switch", "-q", "-c", "mi-rama")
        self.aprobar(d)
        self.assertIn("no es feature/<slug>", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_suite_final_roja(self):
        d = self.completo()
        self.aprobar(d)
        (d / "suite-final.json").write_text(json.dumps({"head": self.head(), "rc": 1, "fallas": ["x"]}))
        self.assertIn("rojos que no estaban en la línea base: x", " ".join(cli("cierre", "--dir", d)[1]["errores"]))

    def test_copia_del_plan_alterada(self):
        d = self.completo()
        self.aprobar(d)
        (d / "plan.html").write_text("otro plan")
        self.assertIn("la copia congelada del plan cambió", cli("cierre", "--dir", d)[1]["errores"])


class SalidaDelRunnerTest(unittest.TestCase):
    def test_lee_cada_prueba_de_unittest_pytest_playwright_y_jest(self):
        salidas = {
            "unittest": ("test_a (m.C.test_a) ... ok\ntest_b (m.C.test_b)\nHace b ... FAIL\n"
                         "test_c (m.C.test_c) ... 2026 INFO algo\nok\ntest_d (m.C.test_d) ... skipped 'x'\n"
                         "test_e (m.C.test_e) ... expected failure\n"),
            "pytest": ("tests/t.py::test_a PASSED   [ 50%]\ntests/t.py::test_b FAILED   [100%]\n"
                       "FAILED tests/t.py::test_b - assert 1 == 2\nPASSED tests/t.py::test_a\n"),
            "playwright": ("  ✓  1 [chromium] › e2e/a.spec.ts:3:5 › M-01 muestra (1.2s)\n"
                           "  ✘  2 [chromium] › e2e/a.spec.ts:9:5 › M-02 falla (3.0s)\n"
                           "  -  3 [chromium] › e2e/a.spec.ts:12:5 › M-03 omitida\n"),
            "jest": "PASS src/a.test.js\n  ✓ suma dos números (3 ms)\n  ✕ resta (1 ms)\n  ○ skipped pendiente\n",
        }
        esperado = {
            "unittest": {"test_a (m.C.test_a)": "pasa", "test_b (m.C.test_b)": "falla", "test_d (m.C.test_d)": "omitida",
                         "test_e (m.C.test_e)": "esperada"},
            "pytest": {"tests/t.py::test_a": "pasa", "tests/t.py::test_b": "falla"},
            "playwright": {"[chromium] › e2e/a.spec.ts:3:5 › M-01 muestra": "pasa",
                           "[chromium] › e2e/a.spec.ts:9:5 › M-02 falla": "falla",
                           "[chromium] › e2e/a.spec.ts:12:5 › M-03 omitida": "omitida"},
            "jest": {"suma dos números": "pasa", "resta": "falla", "skipped pendiente": "omitida"},
        }
        for runner, salida in salidas.items():
            with self.subTest(runner=runner):
                self.assertEqual(ip.pruebas_de_la_salida(salida), esperado[runner])

    def test_una_prueba_sin_resultado_no_se_queda_con_el_de_la_siguiente(self):
        self.assertEqual(ip.pruebas_de_la_salida("test_x (m.C.test_x)\ntest_y (m.C.test_y) ... FAIL\n"),
                         {"test_y (m.C.test_y)": "falla"})

    def test_resumen_del_runner(self):
        django = "Found 4389 test(s).\n....\n" + "-" * 70 + "\nRan 4389 tests in 281.923s\n\nOK (skipped=5)\n"
        self.assertEqual(ip.resumen_del_runner(django), ["Ran 4389 tests in 281.923s", "OK (skipped=5)"])
        self.assertEqual(ip.resumen_del_runner("x\n===== 1 failed, 1 passed in 0.12s =====\n"),
                         ["===== 1 failed, 1 passed in 0.12s ====="])

    def test_desglose_escapa_los_nombres(self):
        self.assertNotIn("<img src=x>", ip._desglose({"<img src=x>": "pasa"}))


class RojoFinalTest(unittest.TestCase):
    BASE = {"rc": 1, "fallas": ["test_a (m.T.test_a)"]}

    def test_mismos_rojos_que_la_linea_base_con_autorizacion(self):
        final = {"rc": 1, "fallas": ["test_a (m.T.test_a)"]}
        self.assertIn("autorización literal", ip._rojo_final(final, self.BASE, None)[0])
        self.assertEqual(ip._rojo_final(final, self.BASE, "Juan: esos rojos ya estaban"), [])

    def test_rojo_nuevo_o_ilegible_no_se_autoriza(self):
        nuevo = {"rc": 1, "fallas": ["test_a (m.T.test_a)", "test_b (m.T.test_b)"]}
        self.assertIn("rojos que no estaban", ip._rojo_final(nuevo, self.BASE, "Juan: sí")[0])
        self.assertIn("no se puede comparar", ip._rojo_final({"rc": 1, "fallas": []}, self.BASE, "Juan: sí")[0])
        self.assertIn("rojos que no estaban", ip._rojo_final(nuevo, {"rc": 0, "fallas": []}, "Juan: sí")[0])

    def test_corrida_abortada_no_se_compara(self):
        abortada = {"rc": 2, "fallas": ["test_a (m.T.test_a)"]}
        self.assertIsNone(ip.rojos_nuevos(abortada, self.BASE))
        self.assertIn("no se puede comparar", ip._rojo_final(abortada, self.BASE, "Juan: sí")[0])

    def test_lee_fallas_de_cada_runner(self):
        salida = ("FAILED tests/test_x.py::test_y - assert 1 == 2\nFAIL: test_suma (tests.test_app.T.test_suma)\n"
                  "  1) [chromium] › e2e/a.spec.ts:3:5 › M-01 algo\n  ● Suite › hace algo\n"
                  " FAIL  src/b.test.ts > suma > suma dos\nFAILED (failures=1)\n")
        self.assertEqual(len(ip.fallas(salida)), 5)


class DepuracionTest(unittest.TestCase):
    MUESTRAS = ('{"password":"hunter2abc","access_token":"abcdefghij12"}', "refresh_token=abcdef123456",
                "client_secret: s3cr3tvalue", "Authorization: Basic dXNlcjpwYXNz", "Authorization: ApiKey abcdef123456",
                "X-Auth-Token: abcdef123456", "X-Auth=abcdefghijklmnop", "Authorization=ApiKey abcdefghijklmnop", "Cookie: sessionid=abc123def; other=1", '{"Authorization": "ApiKey xyz1234"}',
                "GET /repos/ghp_abcdefghijklmnopqrstuvwxyz0123", "sk-ant-api03-abcdefghijklmnopqrstuvwx",
                "Bearer abcdefghijklmnop", "https://bob:s3cret@x.com/", "AKIAABCDEFGHIJKLMNOP",
                "eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2Q",
                "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nIBAAKC\n-----END RSA PRIVATE KEY-----",
                "SECRET_KEY=abcdef123456", '{"clientSecret": "abcdef123456"}', "password_hash: abcdef123456")
    # Claves normales que solo contienen una palabra sensible: se quedan como están (el revisor necesita su valor).
    NO_SECRETOS = ("secretary_name: Alexandra Montes", "tokenization_method: deterministic", "credential_type: temporary",
                   '{"token_expires_in": 3600, "passengers": 3}')

    def test_claves_normales_no_se_depuran(self):
        modulo = self._fixture_pytest()
        for texto in self.NO_SECRETOS:
            with self.subTest(texto=texto):
                self.assertEqual((ip.depurar(texto), ip.secretos_en(texto), modulo.depura(texto),
                                  bool(modulo.TOKEN_VISIBLE.search(texto))), (texto, [], texto, False))
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        js = (self._bloque_ts() + "\nconst depura = (t) => DEPURACION.reduce((x, [p, r]) => x.replace(p, r), String(t));\n"
              f"console.log(JSON.stringify({json.dumps(self.NO_SECRETOS)}.map((x) => [depura(x), TOKEN_VISIBLE.test(x)])));")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), [[x, False] for x in self.NO_SECRETOS])

    def test_paso_sin_navegador_que_falla_deja_su_error(self):
        m = self._fixture_pytest()
        casos = [([], "ConnectionError: rechazada", False), ([], "Timeout", True), (["GET /x", "200 ok"], None, False),
                 ([], None, False), (["token=ghp_abcdefghijklmnopqrstuvwxyz0123"], "falla", False)]
        esperado = ["ERROR: ConnectionError: rechazada", None, "GET /x\n200 ok", None, "token=***\nERROR: falla"]
        self.assertEqual([m.texto_del_paso(*c) for c in casos], esperado)
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        texto = (PLANTILLAS / "evidencia.ts").read_text()
        funcion = texto[texto.index("export function textoDelPaso"):]
        funcion = funcion[:funcion.index("\n}\n") + 3].replace("export ", "")
        for tipo in (": string[]", ": string | null", ": boolean"):
            funcion = funcion.replace(tipo, "")
        js = (self._bloque_ts() + "\nconst MAX_CAPTURA_TEXTO = 20000;\nconst depura = (t, l = 2000) => "
              "DEPURACION.reduce((x, [p, r]) => x.replace(p, r), String(t)).slice(0, l);\n" + funcion
              + f"\nconsole.log(JSON.stringify({json.dumps(casos)}.map((c) => textoDelPaso(...c))));")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), esperado)

    def test_cada_muestra_se_detecta_y_se_depura_completa(self):
        for muestra in self.MUESTRAS:
            with self.subTest(muestra=muestra):
                depurado = ip.depurar(muestra)
                self.assertTrue(ip.secretos_en(muestra))
                self.assertEqual(ip.secretos_en(depurado), [])
                for resto in ("dXNlcjpwYXNz", "abcdef123456", "MIIEow", "abc123def", "xyz1234", "abcdefghijklmnop"):
                    self.assertNotIn(resto, depurado)

    def test_sin_costo_cuadratico(self):
        for texto in ("token" * 40000, "password_" * 20000, "x-auth-" * 30000):
            inicio = time.monotonic()
            ip.depurar(texto)
            ip.secretos_en(texto)
            self.assertLess(time.monotonic() - inicio, 0.5, texto[:10])

    def test_la_fixture_de_pytest_depura_igual(self):
        modulo = self._fixture_pytest()
        self.assertEqual([modulo.depura(m) for m in self.MUESTRAS], [ip.depurar(m) for m in self.MUESTRAS])

    # Lo que se tapa en la captura (texto de la página, valor de un campo) y lo que no (encabezados y avisos normales).
    VISIBLES = ("Bearer abcdefghijklmnop", "Bearer abcdefgh1", "password: hunter2abc", "api_key=ABCDEFGH12",
                "X-Auth-Token: abcdef123456", "Authorization: Basic dXNlcjpwYXNzd29yZDE=", "Cookie: sessionid=abc123def",
                "ghp_abcdefghijklmnopqrstuvwxyz0123", "eyJhbGciOiJIUzI1.eyJzdWIiOiIxMjM0.SflKxwRJSMeKKF2Q",
                "https://bob:s3cret@x.com/", "-----BEGIN RSA PRIVATE KEY-----", "AKIAABCDEFGHIJKLMNOP")
    NO_VISIBLES = ("Basic information", "Basic Authentication", "Token generado correctamente", "Password: required",
                   "Password: ***", "Bearer ***", "token: 1234", "El token expira en 24 horas", "Crear cuenta",
                   "https://localhost:8000/login")
    # Nombre, id, placeholder, aria-label o autocomplete de un campo.
    NOMBRES = ("password", "api_key", "token", "csrf_token", "Contraseña actual (password)", "one-time-code", "cc-number",
               "otp", "verification_code", "sessionid", "session_id", "authorization", "auth_token", "cookie",
               "contraseña", "secreto_compartido", "user-password", "API key", "apiKey", "privateKey", "verificationCode",
               "smsCode", "cardNumber", "Código de verificación", "clave de acceso", "NIP", "pin")
    NO_NOMBRES = ("passengers", "email", "q", "username", "postal_code", "author", "phone", "secretary_name",
                  "tokenization_method", "credential_type", "authority", "bypass_mode", "compass", "codigo_postal",
                  "Código postal", "clave_producto", "spinner", "opinion", "snippet")

    @staticmethod
    def _fixture_pytest():
        falso = types.ModuleType("pytest")
        falso.hookimpl = lambda **k: (lambda f: f)
        falso.fixture = lambda f=None, **k: f if f else (lambda g: g)
        with mock.patch.dict(sys.modules, {"pytest": falso}), mock.patch.object(sys, "dont_write_bytecode", True):
            spec = importlib.util.spec_from_file_location("evidencia_pw_prueba", PLANTILLAS / "evidencia_pw.py")
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        return modulo

    @staticmethod
    def _bloque_ts() -> str:
        texto = (PLANTILLAS / "evidencia.ts").read_text()
        bloque = texto[texto.index("const CLAVE"):texto.index("export function depura")]
        return bloque.replace("const DEPURACION: [RegExp, string][] =", "const DEPURACION =")

    def test_la_fixture_de_playwright_depura_igual(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        js = (self._bloque_ts() + "\nconst depura = (t) => DEPURACION.reduce((x, [p, r]) => x.replace(p, r), String(t));\n"
              f"console.log(JSON.stringify({json.dumps(self.MUESTRAS)}.map(depura)));")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), [ip.depurar(m) for m in self.MUESTRAS])

    def test_las_dos_fixtures_tapan_lo_mismo_en_la_captura(self):
        m = self._fixture_pytest()
        esperado = {"visibles": [True] * len(self.VISIBLES), "no_visibles": [False] * len(self.NO_VISIBLES),
                    "nombres": [True] * len(self.NOMBRES), "no_nombres": [False] * len(self.NO_NOMBRES)}
        en_python = {"visibles": [bool(m.TOKEN_VISIBLE.search(x)) for x in self.VISIBLES],
                     "no_visibles": [bool(m.TOKEN_VISIBLE.search(x)) for x in self.NO_VISIBLES],
                     "nombres": [bool(m.NOMBRE_SENSIBLE.search(x)) for x in self.NOMBRES],
                     "no_nombres": [bool(m.NOMBRE_SENSIBLE.search(x)) for x in self.NO_NOMBRES]}
        self.assertEqual(en_python, esperado)
        # Lo que viaja a get_by_text / page.evaluate no puede traer escapes que JavaScript no entienda.
        for patron in (m.TOKEN_VISIBLE.pattern, m.NOMBRE_SENSIBLE.pattern):
            self.assertNotIn('\\"', patron)
            self.assertNotIn("\\'", patron)
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        js = (self._bloque_ts() + f"\nconst V={json.dumps(self.VISIBLES)}, NV={json.dumps(self.NO_VISIBLES)}, "
              f"N={json.dumps(self.NOMBRES)}, NN={json.dumps(self.NO_NOMBRES)};\n"
              "console.log(JSON.stringify({visibles: V.map(x => TOKEN_VISIBLE.test(x)), no_visibles: NV.map(x => TOKEN_VISIBLE.test(x)),"
              " nombres: N.map(x => NOMBRE_SENSIBLE.test(x)), no_nombres: NN.map(x => NOMBRE_SENSIBLE.test(x))}));")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), esperado)
        # Y el mismo patrón de Python, compilado en JavaScript, da lo mismo: es lo que Playwright manda al navegador.
        js = (f"const T = new RegExp({json.dumps(m.TOKEN_VISIBLE.pattern)}, 'i'); const N = new RegExp({json.dumps(m.NOMBRE_SENSIBLE.pattern)}, 'i');\n"
              f"console.log(JSON.stringify([{json.dumps(self.VISIBLES + self.NO_VISIBLES)}.map(x => T.test(x)), "
              f"{json.dumps(self.NOMBRES + self.NO_NOMBRES)}.map(x => N.test(x))]));")
        r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), [esperado["visibles"] + esperado["no_visibles"], esperado["nombres"] + esperado["no_nombres"]])

    def test_las_dos_fixtures_marcan_los_mismos_campos(self):
        """La función que corre en la página marca los input/textarea por valor o por nombre, nunca los ocultos."""
        node = shutil.which("node")
        if not node:
            self.skipTest("sin node")
        m = self._fixture_pytest()
        texto = (PLANTILLAS / "evidencia.ts").read_text()
        en_ts = texto[texto.index("const MARCA_CAMPOS_SENSIBLES"):texto.index("const ID_CASO")]
        en_ts = en_ts.replace(": [string, string]", "").replace(" as HTMLInputElement", "")
        campos = [{"type": "text", "name": "api_key", "value": "clave-generica"}, {"type": "text", "name": "email", "value": "a@b"},
                  {"type": "hidden", "name": "csrfmiddlewaretoken", "value": "t0ken1234"},
                  {"type": "textarea", "name": "notas", "value": "ghp_abcdefghijklmnopqrstuvwxyz0123"},
                  {"type": "text", "name": "passengers", "value": "2"}, {"type": "text", "id": "pw", "placeholder": "Contraseña (password)", "value": ""},
                  {"type": "text", "name": "authToken", "value": "abc"}, {"type": "text", "name": "secretaryName", "value": "Ana"},
                  {"type": "text", "name": "apiKey", "value": "x"}, {"type": "text", "name": "oneTimeCode", "value": "1"},
                  {"type": "text", "name": "smsCode", "value": "1"}, {"type": "text", "name": "tokenizationMethod", "value": "a"},
                  {"type": "text", "name": "credentialType", "value": "b"}]
        for nombre, fuente in (("ts", en_ts + "\nconst fn = MARCA_CAMPOS_SENSIBLES;"), ("py", f"const fn = {m.MARCA_CAMPOS_SENSIBLES};")):
            js = (f"const campos = {json.dumps(campos)}; const marcados = [];\n"
                  "globalThis.document = { querySelectorAll: () => campos.map((c) => ({ ...c, getAttribute: (a) => c[a] ?? null,"
                  " setAttribute: () => marcados.push(c.name ?? c.id) })) };\n" + fuente
                  + f"\nfn([{json.dumps(m.TOKEN_VISIBLE.pattern)}, {json.dumps(m.NOMBRE_SENSIBLE.pattern)}]);\n"
                  "console.log(JSON.stringify(marcados.sort()));")
            r = subprocess.run([node, "-e", js], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(r.stdout), ["apiKey", "api_key", "authToken", "notas", "oneTimeCode", "pw", "smsCode"],
                             nombre)


if __name__ == "__main__":
    unittest.main()
