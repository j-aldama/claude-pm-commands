"""Pruebas de jurado.py: esquema, consenso, máquina de estados, jueces y revisiones mecánicas.

Corren contra $CLAUDE_HOME (por omisión ~/.claude), así que valida_impl.py las
puede correr dentro de su copia.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")
sys.path.insert(0, str(RAIZ / "scripts"))
import jurado  # noqa: E402

FIXTURES = RAIZ / "scripts" / "tests" / "fixtures"
JURADO = RAIZ / "scripts" / "jurado.py"
CODEX_FALSO = FIXTURES / "codex_falso.py"


def veredicto(valor="pasa", evidencia=None, hallazgos=None):
    return {"veredicto": valor, "resumen": "r", "hallazgos": hallazgos or [], "evidencia": evidencia or []}


def ev(comando, resultado="verde"):
    return {"comando": comando, "resultado": resultado, "salida": None}


def hallazgo(gravedad):
    return {"gravedad": gravedad, "criterio": "C2", "que": "q", "donde": "D1", "porque": "p", "correccion": "c"}


def correr(*args, env=None):
    entorno = {**os.environ, "CLAUDE_HOME": str(RAIZ), **(env or {})}
    return subprocess.run([sys.executable, str(JURADO), *args], capture_output=True, text=True, env=entorno)


class ValidaTest(unittest.TestCase):
    def test_json_completo_es_valido(self):
        estado, datos, _ = jurado.cargar_veredicto((FIXTURES / "veredicto_ok.json").read_text())
        self.assertEqual((estado, datos["veredicto"]), ("ok", "pasa"))

    def test_sin_clave_evidencia_es_invalido(self):
        estado, _, errores = jurado.cargar_veredicto((FIXTURES / "veredicto_sin_evidencia.json").read_text())
        self.assertEqual(estado, "invalido")
        self.assertTrue(any("evidencia" in e for e in errores))

    def test_veredicto_fuera_del_enum_es_invalido(self):
        estado, _, _ = jurado.cargar_veredicto(json.dumps(veredicto("ship")))
        self.assertEqual(estado, "invalido")

    def test_clave_extra_es_invalida(self):
        estado, _, _ = jurado.cargar_veredicto(json.dumps({**veredicto(), "extra": 1}))
        self.assertEqual(estado, "invalido")

    def test_texto_sin_json_es_sin_veredicto(self):
        self.assertEqual(jurado.cargar_veredicto("todo bien, ship it")[0], "sin-veredicto")

    def test_prosa_de_advisor_con_bloque_json(self):
        estado, datos, _ = jurado.cargar_veredicto((FIXTURES / "advisor_con_prosa.md").read_text())
        self.assertEqual((estado, datos["veredicto"]), ("ok", "pasa"))

    def test_dos_bloques_json_es_invalido(self):
        bloque = "```json\n" + json.dumps(veredicto()) + "\n```"
        self.assertEqual(jurado.cargar_veredicto(f"a\n{bloque}\nb\n{bloque}")[0], "invalido")

    def test_codigos_de_salida_del_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            prosa = Path(tmp) / "x.md"
            prosa.write_text("sin json")
            self.assertEqual(correr("valida", str(FIXTURES / "veredicto_ok.json")).returncode, 0)
            self.assertEqual(correr("valida", str(FIXTURES / "veredicto_sin_evidencia.json")).returncode, 1)
            self.assertEqual(correr("valida", str(prosa)).returncode, 2)


class ConsensoImplTest(unittest.TestCase):
    ESPERADOS = ["python3 -m unittest -v", "python3 a.py", "python3 b.py"]

    def aprobado(self, evidencia, raiz=None, segundo=None):
        return jurado.consenso("impl", veredicto("pasa", evidencia), segundo, self.ESPERADOS, raiz)[0]

    def test_evidencia_vacia_no_aprueba(self):
        self.assertFalse(self.aprobado([]))

    def test_dos_de_tres_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS[:2]]))

    def test_rojo_esperado_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS[:2]] + [ev(self.ESPERADOS[2], "rojo")]))

    def test_rojo_extra_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS] + [ev("ls", "rojo")]))

    def test_no_corrio_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS] + [ev(self.ESPERADOS[0], "no-corrio")]))

    def test_mismo_comando_verde_y_rojo_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS] + [ev(self.ESPERADOS[1], "rojo")]))

    def test_completo_con_duplicados_verdes_aprueba(self):
        self.assertTrue(self.aprobado([ev(c) for c in self.ESPERADOS] + [ev(self.ESPERADOS[0])]))

    def test_comando_extra_verde_no_aprueba(self):
        self.assertFalse(self.aprobado([ev(c) for c in self.ESPERADOS] + [ev("python3 c.py")]))

    def test_espacios_distintos_cuentan(self):
        self.assertTrue(self.aprobado([ev("python3  -m   unittest -v"), ev("python3 a.py"), ev("python3 b.py")]))

    def test_ruta_de_la_copia_expandida_cuenta(self):
        esperados = ['python3 "$CLAUDE_HOME/scripts/x.py"']
        reportado = veredicto("pasa", [ev("python3 /tmp/copia-123/scripts/x.py")])
        self.assertTrue(jurado.consenso("impl", reportado, None, esperados, "/tmp/copia-123")[0])

    def test_advisor_sin_evidencia_y_pasa_cuenta(self):
        self.assertTrue(self.aprobado([ev(c) for c in self.ESPERADOS], segundo=veredicto("pasa", [])))

    def test_codex_necesita_trabajo_no_aprueba_aunque_todo_corra(self):
        completo = veredicto("necesita-trabajo", [ev(c) for c in self.ESPERADOS])
        self.assertFalse(jurado.consenso("impl", completo, None, self.ESPERADOS, None)[0])


class ConsensoPlanTest(unittest.TestCase):
    def test_plan_con_evidencia_vacia_y_pasa_aprueba(self):
        self.assertTrue(jurado.consenso("plan", veredicto("pasa"), veredicto("pasa"))[0])

    def test_plan_con_segundo_que_pide_trabajo_no_aprueba(self):
        self.assertFalse(jurado.consenso("plan", veredicto("pasa"), veredicto("necesita-trabajo"))[0])


def armar_ronda(d: Path, caso: dict) -> None:
    """Construye el directorio de una auditoría a partir del caso de una fila de la tabla."""
    segundo = "advisor" if caso.get("con_advisor") else None
    jurado.escribir_json(d / "config.json", {"plan": str(d / "plan.html"), "segundo": segundo})
    n = caso.get("ronda", 1)
    if not caso.get("falta_plan"):
        (d / f"ronda-{n}-plan.html").write_text("<p>plan</p>")
        jurado.escribir_json(d / f"ronda-{n}-mecanico.json", {"ok": caso.get("mecanico_ok", True), "motivos": []})
    if "codex" in caso:
        jurado.escribir_json(d / f"ronda-{n}-codex.json", veredicto(caso["codex"]))
    for estado in caso.get("codex_intentos", []):
        jurado.registrar_intento(d, n, "codex", estado, "simulado")
    if "segundo" in caso:
        jurado.escribir_json(d / f"ronda-{n}-advisor.json", veredicto(caso["segundo"]))
    for estado in caso.get("segundo_intentos", []):
        jurado.registrar_intento(d, n, "advisor", estado, "simulado")


class SiguienteTest(unittest.TestCase):
    def test_cada_fila_de_la_tabla_de_estados(self):
        filas = json.loads(jurado.ESTADOS.read_text())["filas"]
        self.assertGreaterEqual(len(filas), 10)
        for fila in filas:
            with self.subTest(fila["situacion"]), tempfile.TemporaryDirectory() as tmp:
                armar_ronda(Path(tmp), fila["caso"])
                self.assertEqual(jurado.siguiente(Path(tmp))["accion"], fila["esperado"])

    def test_corregir_abre_la_ronda_siguiente(self):
        with tempfile.TemporaryDirectory() as tmp:
            armar_ronda(Path(tmp), {"codex": "necesita-trabajo"})
            self.assertEqual(jurado.siguiente(Path(tmp)), {"accion": "corregir", "ronda": 2, "motivo": "nueva ronda"})

    def test_sin_config_escala(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(jurado.siguiente(Path(tmp))["accion"], "escalar:registro")

    def test_sin_rondas_llama_a_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            jurado.escribir_json(Path(tmp) / "config.json", {"plan": "x", "segundo": None})
            self.assertEqual(jurado.siguiente(Path(tmp)), {"accion": "llamar-codex", "ronda": 1, "motivo": "primera ronda"})

    def test_falta_el_registro_mecanico_escala(self):
        with tempfile.TemporaryDirectory() as tmp:
            jurado.escribir_json(Path(tmp) / "config.json", {"plan": "x", "segundo": None})
            (Path(tmp) / "ronda-1-plan.html").write_text("x")
            self.assertEqual(jurado.siguiente(Path(tmp))["accion"], "escalar:registro")


class JuecesTest(unittest.TestCase):
    def jueces(self, sesion, con_advisor=True):
        with mock.patch.dict(os.environ, {"CODEX_BIN": str(CODEX_FALSO)}):
            return jurado.jueces(sesion, con_advisor)

    def test_sesion_opus(self):
        self.assertEqual(self.jueces("opus"), ["codex", "advisor"])

    def test_sesion_fable(self):
        self.assertEqual(self.jueces("fable"), ["codex", "advisor-opus"])

    def test_sin_bandera_solo_codex(self):
        self.assertEqual(self.jueces("opus", False), ["codex"])

    def test_el_segundo_nunca_es_el_modelo_de_la_sesion(self):
        for sesion in ("opus", "fable"):
            segundo = self.jueces(sesion)[1]
            self.assertNotEqual(jurado.modelo_de_agente(segundo), sesion)

    def test_nunca_gemini_y_siempre_codex_primero(self):
        for sesion in ("opus", "fable"):
            lista = self.jueces(sesion)
            self.assertEqual(lista[0], "codex")
            self.assertFalse(any("gemini" in j for j in lista))

    def test_codex_no_disponible_es_error(self):
        r = correr("jueces", "--sesion", "opus", env={"CODEX_BIN": "/no/existe/codex"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("no está disponible", r.stderr)

    def test_advisor_opus_no_se_presenta_como_fable(self):
        cuerpo = (RAIZ / "agents" / "advisor-opus.md").read_text()
        for frase in ("You are the advisor: Fable", "pinned to Fable", "model: fable"):
            self.assertNotIn(frase, cuerpo)


class PendientesTest(unittest.TestCase):
    def analizar(self, texto):
        return jurado.analizar_pendientes(texto)

    def test_sin_duenio_bloquea(self):
        self.assertEqual(len(self.analizar("<code>PENDIENTE: el formato del evento</code>")[0]), 1)

    def test_con_duenio_y_cierre_es_diferido(self):
        bloq, dif = self.analizar("<code>PENDIENTE: el formato — arquitecto — se cierra en E2</code>")
        self.assertEqual((len(bloq), len(dif)), (0, 1))

    def test_con_duenio_sin_cierre_bloquea(self):
        self.assertEqual(len(self.analizar("<td>PENDIENTE: el formato — arquitecto</td>")[0]), 1)

    def test_cierre_sin_duenio_bloquea(self):
        self.assertEqual(len(self.analizar("<td>PENDIENTE: el formato — se cierra en E2</td>")[0]), 1)

    def test_la_palabra_en_prosa_no_cuenta(self):
        self.assertEqual(self.analizar("<p>queda un pendiente y un PENDIENTE bloqueante</p>"), ([], []))

    def test_plantilla_y_etiqueta_sola_no_cuentan(self):
        texto = "<code>PENDIENTE: &lt;qué falta&gt; — &lt;quién&gt;</code> y <code>PENDIENTE:</code> con dueño"
        self.assertEqual(self.analizar(texto), ([], []))


class MejorTest(unittest.TestCase):
    def armar(self, d, rondas):
        jurado.escribir_json(d / "config.json", {"plan": "x", "segundo": None})
        for n, gravedades in rondas.items():
            (d / f"ronda-{n}-plan.html").write_text(f"version {n}")
            if gravedades is not None:
                jurado.escribir_json(d / f"ronda-{n}-codex.json",
                                     veredicto("necesita-trabajo", hallazgos=[hallazgo(g) for g in gravedades]))

    def test_menos_graves_gana_a_la_ultima(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.armar(d, {1: ["grave", "grave"], 2: ["medio"], 3: ["grave"]})
            ruta = jurado.mejor(d)
            self.assertEqual(ruta.name, "ronda-2-plan.html")
            self.assertTrue(ruta.exists())
            self.assertNotEqual(ruta.read_text(), (d / "ronda-3-plan.html").read_text())

    def test_empate_en_graves_gana_menos_medios(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.armar(Path(tmp), {1: ["medio"], 2: ["medio", "medio"]})
            self.assertEqual(jurado.mejor(Path(tmp)).name, "ronda-1-plan.html")

    def test_ronda_sin_veredicto_valido_nunca_gana(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.armar(Path(tmp), {1: ["grave"], 2: None})
            self.assertEqual(jurado.mejor(Path(tmp)).name, "ronda-1-plan.html")

    def test_sin_veredictos_no_hay_mejor(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.armar(Path(tmp), {1: None})
            self.assertIsNone(jurado.mejor(Path(tmp)))


class RegistraTest(unittest.TestCase):
    def test_registra_un_veredicto_valido(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = correr("registra", "--dir", tmp, "--ronda", "1", "--juez", "codex",
                       "--archivo", str(FIXTURES / "veredicto_ok.json"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads((Path(tmp) / "ronda-1-codex.json").read_text())["veredicto"], "pasa")

    def test_respuesta_invalida_queda_como_intento(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = correr("registra", "--dir", tmp, "--ronda", "1", "--juez", "advisor",
                       "--archivo", str(FIXTURES / "veredicto_sin_evidencia.json"))
            self.assertEqual(r.returncode, 3)
            intento = json.loads((Path(tmp) / "ronda-1-advisor-intento-1.json").read_text())
            self.assertEqual(intento["estado"], "json-invalido")

    def test_directorio_sin_permiso_falla_con_mensaje(self):
        with tempfile.TemporaryDirectory() as tmp:
            cerrado = Path(tmp) / "cerrado"
            cerrado.mkdir()
            cerrado.chmod(0o500)
            try:
                r = correr("registra", "--dir", str(cerrado), "--ronda", "1", "--juez", "codex",
                           "--estado", "fallo-tecnico")
            finally:
                cerrado.chmod(0o700)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no se pudo escribir", r.stderr)

    def test_nombre_de_juez_con_diagonal_se_rechaza(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = correr("registra", "--dir", tmp, "--ronda", "1", "--juez", "../codex", "--estado", "fallo-tecnico")
            self.assertEqual(r.returncode, 1)
            self.assertEqual(list(Path(tmp).iterdir()), [])


PLAN_MINIMO = """<p>Base: x · Raíces: {raices} · Evidencia: y</p>
<p>{citas}</p>
<h2>6. Verificación</h2><pre><code># Automática
{automatica}
# Manual
codex exec algo</code></pre>"""


class PrecheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        for raiz in ("r1", "r2"):
            (self.base / raiz).mkdir()
            (self.base / raiz / f"{raiz}.py").write_text("a\nb\nc\n")
        (self.base / "fuera.py").write_text("x\n")

    def tearDown(self):
        self.tmp.cleanup()

    def errores(self, citas, raices="<code>r1</code>, <code>r2</code>", automatica="python3 -m unittest"):
        texto = PLAN_MINIMO.format(raices=raices, citas=citas, automatica=automatica)
        return jurado.precheck(texto, None, self.base)

    def test_citas_validas_en_dos_raices(self):
        self.assertEqual(self.errores("<code>r1.py:2</code> y <code>r2.py:1–3</code>"), [])

    def test_cita_fuera_de_rango(self):
        self.assertIn("fuera de rango", self.errores("<code>r1.py:9</code>")[0])

    def test_cita_inexistente(self):
        self.assertIn("inexistente", self.errores("<code>nada.py:1</code>")[0])

    def test_cita_que_sale_de_la_raiz_con_puntos(self):
        self.assertIn("fuera de las raíces", self.errores("<code>../fuera.py:1</code>")[0])

    def test_cita_absoluta_fuera_de_las_raices(self):
        self.assertIn("fuera de las raíces", self.errores(f"<code>{self.base / 'fuera.py'}:1</code>")[0])

    def test_raiz_inexistente(self):
        self.assertIn("raíz inexistente", self.errores("", raices="<code>no_hay</code>")[0])

    def test_raiz_ilegible(self):
        (self.base / "r1").chmod(0o000)
        try:
            self.assertIn("raíz inexistente o ilegible", self.errores("")[0])
        finally:
            (self.base / "r1").chmod(0o755)

    def test_plan_sin_raices(self):
        self.assertIn("Raíces", jurado.precheck("<p>Base: x</p>", None, self.base)[0])

    def test_ruta_absoluta_en_automatica(self):
        errores = self.errores("", automatica="python3 ~/.claude/scripts/jurado.py valida x")
        self.assertTrue(any("ruta absoluta" in e for e in errores))


MATRIZ = "<h3>Matriz de tipos de este plan</h3><div class='tw'><table><tr><th>Tipo</th></tr>{filas}</table></div>"
TIPOS_OK = [("Unitarias", "Sí", "t.py"), ("Integración", "No aplica porque no hay piezas", "—"),
            ("E2E", "No aplica porque no hay pantalla", "—"), ("Rutas de error", "Sí", "t.py"),
            ("Regresión del bug", "Sí", "t.py"), ("Seguridad", "No aplica porque no hay entrada", "—"),
            ("Contrato", "Sí", "t.py"), ("Migración/datos", "No aplica porque no hay datos", "—"),
            ("Rendimiento", "No aplica porque es trivial", "—")]


class MatrizTest(unittest.TestCase):
    def errores(self, tipos):
        filas = "".join(f"<tr><td>{t}</td><td>{a}</td><td>{d}</td><td>s</td></tr>" for t, a, d in tipos)
        return jurado.revisar_matriz(MATRIZ.format(filas=filas))

    def test_matriz_completa(self):
        self.assertEqual(self.errores(TIPOS_OK), [])

    def test_falta_un_tipo(self):
        self.assertIn("rendimiento", self.errores(TIPOS_OK[:-1])[0])

    def test_no_aplica_sin_razon(self):
        tipos = TIPOS_OK[:-1] + [("Rendimiento", "No aplica", "—")]
        self.assertEqual(len(self.errores(tipos)), 1)

    def test_aplica_sin_donde(self):
        tipos = [("Unitarias", "Sí", "—")] + TIPOS_OK[1:]
        self.assertIn("sin decir dónde", self.errores(tipos)[0])

    def test_plan_sin_matriz(self):
        self.assertEqual(jurado.revisar_matriz("<p>nada</p>"), ["no hay matriz de tipos de prueba"])


class EsperadosTest(unittest.TestCase):
    def extraer(self, automatica):
        return jurado.extraer_esperados(PLAN_MINIMO.format(raices="", citas="", automatica=automatica))

    def test_une_continuaciones_y_omite_comentarios_y_asignaciones(self):
        comandos, errores = self.extraer('T=x\n# un comentario\npython3 a.py \\\n  --uno   # nota\npython3 b.py')
        self.assertEqual((comandos, errores), (["python3 a.py --uno", "python3 b.py"], []))

    def test_bloque_vacio_es_error(self):
        self.assertIn("vacío", self.extraer("# solo comentario")[1][0])

    def test_ruta_absoluta_es_error(self):
        self.assertTrue(any("ruta absoluta" in e for e in self.extraer("cat /Users/usuario/x")[1]))

    def test_sin_bloque_automatica_es_error(self):
        texto = "<h2>6. Verificación</h2><pre><code>python3 a.py</code></pre>"
        self.assertIn("Automática", jurado.extraer_esperados(texto)[1][0])


class RondaTest(unittest.TestCase):
    """La ronda completa con un Codex falso: revisión mecánica, registro y siguiente."""

    def ronda(self, plan, modo, veces=1):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "codex.log"
            entorno = {"CODEX_BIN": str(CODEX_FALSO), "CODEX_FALSO_MODO": modo, "CODEX_FALSO_LOG": str(log)}
            d = Path(tmp) / "auditoria"
            r = correr("inicia", "--plan", str(FIXTURES / plan), "--dir", str(d), env=entorno)
            self.assertEqual(r.returncode, 0, r.stderr)
            for _ in range(veces):
                r = correr("ronda", "--dir", str(d), env=entorno)
            llamadas = len(log.read_text().splitlines()) if log.exists() else 0
            return json.loads(r.stdout), llamadas, d

    def test_plan_bueno_con_codex_que_pasa_se_aprueba(self):
        sig, llamadas, _ = self.ronda("plan_bueno.html", "pasa")
        self.assertEqual((sig["accion"], llamadas), ("aprobado", 1))

    def test_citas_rotas_no_llama_a_codex(self):
        sig, llamadas, _ = self.ronda("plan_citas_rotas.html", "pasa")
        self.assertEqual((sig["accion"], llamadas), ("corregir-mecanico", 0))

    def test_codex_que_falla_escala(self):
        sig, _, _ = self.ronda("plan_bueno.html", "falla")
        self.assertEqual(sig["accion"], "escalar:fallo-tecnico")

    def test_codex_mudo_escala_como_fallo_tecnico(self):
        sig, _, _ = self.ronda("plan_bueno.html", "vacio")
        self.assertEqual(sig["accion"], "escalar:fallo-tecnico")

    def test_json_invalido_se_reintenta_una_vez_y_luego_escala(self):
        sig, _, _ = self.ronda("plan_bueno.html", "invalido")
        self.assertEqual(sig["accion"], "llamar-codex")
        sig, llamadas, _ = self.ronda("plan_bueno.html", "invalido", veces=2)
        self.assertEqual((sig["accion"], llamadas), ("escalar:json-invalido", 2))

    def test_codex_usa_el_modelo_fijo_y_solo_lectura(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "codex.log"
            entorno = {"CODEX_BIN": str(CODEX_FALSO), "CODEX_FALSO_LOG": str(log)}
            d = Path(tmp) / "a"
            correr("inicia", "--plan", str(FIXTURES / "plan_bueno.html"), "--dir", str(d), env=entorno)
            correr("ronda", "--dir", str(d), env=entorno)
            args = json.loads(log.read_text().splitlines()[0])["args"]
            for esperado in ("--model", "gpt-6.1-sol", "read-only", "--skip-git-repo-check", "--output-schema"):
                self.assertIn(esperado, args)

    def test_ronda_aprobada_no_se_vuelve_a_correr(self):
        _, _, _ = self.ronda("plan_bueno.html", "pasa")
        sig, llamadas, _ = self.ronda("plan_bueno.html", "pasa", veces=2)
        self.assertEqual((sig["accion"], llamadas), ("aprobado", 1))


if __name__ == "__main__":
    unittest.main()
