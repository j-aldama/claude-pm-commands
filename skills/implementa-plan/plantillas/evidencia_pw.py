"""Fixture de evidencia por paso para pytest, con o sin navegador (plantilla de /implementa-plan).

Con navegador (la prueba pide `page`, de pytest-playwright), cada paso deja captura de pantalla completa, consola y
errores de la página, peticiones fallidas o con estado >= 400 y URL. Sin navegador (un caso de API o de línea de
comandos), la captura del paso es de texto: lo que la prueba anota con `p.anota(...)` (la petición y la respuesta, el
comando y su salida) queda en paso-NN.txt. Los dos llevan duración y resultado. Escribe <EVIDENCIA_DIR>/<caso>/pasos.json después de CADA paso (de forma
atómica), con el commit (HEAD) que se probó y la ruta del archivo relativa a la raíz del repo. El estado final es
el peor de setup, call y teardown. El HTML lo arma `implementa_plan.py evidencia`.

Todo texto capturado pasa por `depura` (los mismos patrones que SECRETOS en implementa_plan.py y DEPURACION en
evidencia.ts: si cambias uno, cambia los tres). Las capturas tapan siempre los campos de contraseña, códigos de un
solo uso, tarjetas y lo marcado con data-sensible; además, cualquier texto con forma de secreto (TOKEN_VISIBLE) y los
input/textarea cuyo valor la tenga o cuyo nombre, id, placeholder, aria-label o autocomplete digan que guardan uno
(NOMBRE_SENSIBLE).

Registro, en el conftest.py de las pruebas e2e (ruta de import del módulo copiado):

    pytest_plugins = ["tests.e2e.evidencia_pw"]

Uso (el ID del caso manual va en el marcador o al inicio del nombre: test_m03_...):

    @pytest.mark.caso("M-03")
    def test_rechaza_correo_duplicado(page, paso):
        with paso("Abrir el registro", "Se ve el formulario vacío"):
            page.goto("/registro")
            expect(page.get_by_role("heading", name="Crear cuenta")).to_be_visible()
        with paso("Enviar un correo ya registrado", "Aparece «Ese correo ya existe»",
                  mascara=[page.get_by_label("Teléfono")]):
            ...

    @pytest.mark.caso("M-07")
    def test_api_rechaza_cantidad_cero(client, paso):          # sin `page`: no abre navegador
        with paso("POST /api/pedidos con cantidad 0", "Responde 400 con «cantidad inválida»") as p:
            r = client.post("/api/pedidos", {"cantidad": 0})
            p.anota(f"POST /api/pedidos {{'cantidad': 0}}\n{r.status_code} {r.content.decode()}")
            assert r.status_code == 400 and "cantidad inválida" in r.content.decode()

Un paso sin navegador que pasa tiene que anotar algo: sin captura ni texto, `implementa_plan.py evidencia` lo rechaza.
Si falla, su error queda en la captura de texto aunque no haya anotado nada.

Corrida de evidencia: EVIDENCIA_DIR=<dir> EVIDENCIA_CORRIDA=<id único> pytest <specs> --browser chromium (un solo
navegador, sin reruns). Con EVIDENCIA_CORRIDA, un rerun o el mismo caso en otro navegador truenan en vez de pisar la
evidencia. Sin EVIDENCIA_DIR escribe en test-results/evidencia (que debe estar ignorado por git).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
import time
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

PARAMETRO_SENSIBLE = re.compile(r"(token|secret|passw|pwd|api[_-]?key|apikey|session|sig|auth|credential|code)", re.I)
SELECTOR_SENSIBLE = ('input[type="password"], [autocomplete*="password"], [autocomplete="one-time-code"], '
                     '[autocomplete="cc-number"], [autocomplete="cc-csc"], [data-sensible]')
ID_CASO = re.compile(r"^M-\d{2,}$")
MAX_TEXTO = 2000
MAX_CAPTURA_TEXTO = 20000
# Corre en la página: marca los input/textarea (no ocultos) cuyo valor parece secreto o cuyo nombre dice que lo es.
MARCA_CAMPOS_SENSIBLES = """([token, nombre]) => {
  const conToken = new RegExp(token, 'i'); const sensible = new RegExp(nombre, 'i');
  document.querySelectorAll('input, textarea').forEach((el) => {
    if (el.type === 'hidden') return;
    const nombres = ['name', 'id', 'placeholder', 'aria-label', 'autocomplete'].map((a) => el.getAttribute(a) ?? '')
      .join(' ').replace(/([a-z0-9])([A-Z])/g, '$1_$2');
    if (conToken.test(el.value) || sensible.test(nombres)) el.setAttribute('data-evidencia-token', ''); }); }"""
QUITA_MARCAS = """() => document.querySelectorAll('[data-evidencia-token]')
  .forEach((el) => el.removeAttribute('data-evidencia-token'))"""
_CLAVE = (r"[A-Za-z0-9_.-]{0,40}(?:pass(?:word|wd)?|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key"
          r"|credential|authorization|session(?:[_-]?id)?|cookie|contrase[ñn]a|secreto)(?:[_.-]?(?:key|id|hash|digest))?s?")
_ENCABEZADO = r"(?:proxy-)?authorization|set-cookie|cookie|x-[a-z0-9-]{0,40}(?:auth|api-?key|token|secret)[a-z0-9-]{0,40}"
# Claves y cabeceras solo empiezan tras un delimitador (o al inicio): con \b, «x-auth-» × 30 000 tarda ~1 s en vez de 0.02 s.
# Sin «\"» ni «\'»: TOKEN_VISIBLE viaja tal cual a JavaScript (get_by_text), donde esos escapes no valen.
_INICIO = r"""(?<![^\s"'{,;(?&/])"""
_PROVEEDOR = (r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"
              r"|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|glpat-[A-Za-z0-9_-]{20,}"
              r"|[rsp]k_(?:live|test)_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}")
# Valor con forma de secreto en la pantalla: ≥ 8 caracteres con algún dígito, o ≥ 16 sin dígitos. «Basic information»
# y «Token generado» no entran; «Bearer abcdefghijklmnop» y «password: hunter2abc» sí.
_VALOR = r"(?:(?=[A-Za-z0-9._~+/=-]*\d)[A-Za-z0-9._~+/=-]{8,}|[A-Za-z0-9._~+/=-]{16,})"
# Secretos que se reconocen solos en el texto de la página: se tapan en la captura (mismo patrón en evidencia.ts).
TOKEN_VISIBLE = re.compile(
    r"-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    rf"|\b(?:{_PROVEEDOR})"
    rf"|\b(?:Basic|Digest|Bearer|Token|NTLM|Negotiate)\s+{_VALOR}"
    rf"""|{_INICIO}(?:{_CLAVE}|{_ENCABEZADO})["']?\s*[:=]\s*["']?{_VALOR}"""
    r"|\b[a-z][a-z0-9+.-]{0,30}://[^/\s:@]{1,200}:[^/\s@]{1,200}@", re.I)
# Nombre, id, placeholder, aria-label o autocomplete de un campo que guarda un secreto (mismo patrón en evidencia.ts).
# Por componente del nombre (camelCase ya separado): «secretary_name» o «tokenization» no cuentan; «sessionId» sí.
NOMBRE_SENSIBLE = re.compile(r"(?:^|[^a-z])(?:pass(?:word|wd)?|pwd|secret|token|api[_ -]?key|private[_ -]?key"
                             r"|access[_ -]?key|otp|one[_ -]?time|verification[_ -]?code|sms[_ -]?code|cvv|cvc"
                             r"|cc-number|cc-csc|card[_ -]?number|auth|authorization|session(?:[_ -]?id)?|cookie"
                             r"|contrase[ñn]a|secreto|clave[_ -]?(?:de[_ -]?)?acceso|nip|pin"
                             r"|c[oó]digo[_ -]?(?:de[_ -]?)?(?:verificaci[oó]n|seguridad|acceso))s?(?:$|[^a-z])", re.I)
DEPURACION = (
    (re.compile(r"\x1b\[[0-9;]*m"), ""),
    (re.compile(r"-----BEGIN ([A-Z ]{0,40})PRIVATE KEY-----.*?(?:-----END \1PRIVATE KEY-----|\Z)", re.S),
     "*** llave privada ***"),
    (re.compile(rf"{_INICIO}({_ENCABEZADO})[\"']?\s*[:=]\s*[\"']?(?!\*\*\*)[^\s\"'*][^\r\n\"']*", re.I), r"\1: ***"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), "***"),
    (re.compile(rf"\b(?:{_PROVEEDOR})"), "***"),
    (re.compile(r"\b(Basic|Digest|Bearer|Token|NTLM|Negotiate)\s+(?!\*\*\*)[A-Za-z0-9._~+/=-]{8,}", re.I), r"\1 ***"),
    (re.compile(rf"{_INICIO}({_CLAVE}[\"']?\s*[:=]\s*[\"']?)(?!\*\*\*)[^\s\"'&,;}}]{{4,}}", re.I), r"\1***"),
    (re.compile(r"(\b[a-z][a-z0-9+.-]{0,30}://)[^/\s@]{1,400}@", re.I), r"\1***@"),
)


def depura(texto, limite: int = MAX_TEXTO) -> str:
    texto = str(texto)
    for patron, reemplazo in DEPURACION:
        texto = patron.sub(reemplazo, texto)
    return texto[:limite]


def texto_del_paso(lineas: list[str], error: str | None, con_navegador: bool) -> str | None:
    """Captura de texto del paso: lo anotado y, si un paso sin navegador falló, su error (aunque no anotara nada)."""
    lineas = list(lineas) + ([f"ERROR: {error}"] if error and not con_navegador else [])
    return depura("\n".join(lineas), MAX_CAPTURA_TEXTO) if lineas else None


class Anotaciones:
    """Lo que la prueba deja escrito en un paso: la captura de texto de un caso de API o de línea de comandos."""

    def __init__(self) -> None:
        self.lineas: list[str] = []

    def anota(self, texto) -> None:
        self.lineas.append(str(texto))


def _limpia_consulta(consulta: str) -> str:
    pares = [(k, "***" if PARAMETRO_SENSIBLE.search(k) else v) for k, v in parse_qsl(consulta, keep_blank_values=True)]
    return urlencode(pares, safe="*")


def limpia_url(crudo: str) -> str:
    try:
        partes = urlsplit(crudo)
    except ValueError:
        return depura(crudo)
    netloc = partes.netloc.rsplit("@", 1)[-1]
    netloc = f"***@{netloc}" if "@" in partes.netloc else netloc
    fragmento = _limpia_consulta(partes.fragment) if "=" in partes.fragment else partes.fragment
    return depura(urlunsplit(partes._replace(netloc=netloc, query=_limpia_consulta(partes.query), fragment=fragmento)))


@lru_cache(maxsize=1)
def _datos_del_repo() -> tuple[str, str]:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    try:
        return git("rev-parse", "--show-toplevel"), git("rev-parse", "HEAD")
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd(), ""


def _caso_de(nodo) -> str:
    marca = nodo.get_closest_marker("caso")
    if marca and marca.args:
        caso = str(marca.args[0])
    else:
        m = re.match(r"test_m_?(\d{2,})_", nodo.name, re.I)
        caso = f"M-{m.group(1)}" if m else ""
    if not ID_CASO.match(caso):
        raise ValueError(f"{nodo.nodeid}: sin ID de caso M-01 válido (marcador caso o nombre test_m01_...)")
    return caso


def _escucha(page, consola: list[dict], red: list[dict]) -> None:
    page.on("console", lambda m: consola.append({"tipo": m.type, "texto": depura(m.text)}))
    page.on("pageerror", lambda e: consola.append({"tipo": "pageerror", "texto": depura(e)}))
    page.on("requestfailed", lambda r: red.append({"estado": r.failure or "fallida", "metodo": r.method,
                                                   "url": limpia_url(r.url)}))

    def respuesta(r) -> None:
        if r.status >= 400:
            red.append({"estado": str(r.status), "metodo": r.request.method, "url": limpia_url(r.url)})

    page.on("response", respuesta)


def _escribe_atomico(ruta: Path, datos: dict) -> None:
    temporal = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporal, ruta)


def _prepara_directorio(raiz: Path, caso: str, corrida: str | None, intento: int) -> Path:
    if (raiz / "cruce.json").exists():
        raise RuntimeError("esta vuelta ya se cruzó: corre la evidencia en una vuelta nueva")
    d = (raiz / caso).resolve()
    if d.parent != raiz.resolve():
        raise ValueError(f"el caso «{caso}» sale de EVIDENCIA_DIR")
    if corrida and intento > 1:
        raise RuntimeError("la corrida de evidencia no admite reruns: un reintento ocultaría la falla")
    previo = d / "pasos.json"
    if corrida and previo.is_file() and json.loads(previo.read_text(encoding="utf-8")).get("corrida") == corrida:
        raise RuntimeError(f"{caso} ya corrió en esta corrida (otro navegador): usa uno solo")
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    return d


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "caso(id): ID del caso manual (M-01) para la evidencia en pantalla")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    reporte = resultado.get_result()
    estados = item.__dict__.setdefault("_estados_evidencia", {})
    estados[reporte.when] = reporte.outcome
    ruta = getattr(item, "_ruta_evidencia", None)
    if reporte.when == "teardown" and ruta is not None and ruta.is_file():
        final = "failed" if "failed" in estados.values() else ("passed" if estados.get("call") == "passed" else None)
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        _escribe_atomico(ruta, {**datos, "estado": final})


def _captura_de_pantalla(page, d: Path, n: int, mascara) -> str | None:
    captura = f"paso-{n:02d}.png"
    try:
        # get_by_text no ve el valor de un input o textarea: los que traen un secreto (o cuyo nombre dice que lo
        # guardan) se marcan para taparlos.
        page.evaluate(MARCA_CAMPOS_SENSIBLES, [TOKEN_VISIBLE.pattern, NOMBRE_SENSIBLE.pattern])
        page.screenshot(path=str(d / captura), full_page=True,
                        mask=[page.locator(SELECTOR_SENSIBLE), page.get_by_text(TOKEN_VISIBLE),
                              page.locator("[data-evidencia-token]"), *(mascara or [])])
    except Exception:
        captura = None
    try:
        page.evaluate(QUITA_MARCAS)
    except Exception:
        pass
    return captura


@pytest.fixture
def paso(request):
    # Solo abre navegador si la prueba lo pide: un caso de API o de línea de comandos corre sin él.
    page = request.getfixturevalue("page") if "page" in request.fixturenames else None
    caso, corrida = _caso_de(request.node), os.environ.get("EVIDENCIA_CORRIDA")
    intento = getattr(request.node, "execution_count", 1)
    d = _prepara_directorio(Path(os.environ.get("EVIDENCIA_DIR") or Path("test-results") / "evidencia"), caso,
                            corrida, intento)
    raiz, head = _datos_del_repo()
    request.node._ruta_evidencia = d / "pasos.json"
    consola, red, pasos = [], [], []
    if page is not None:
        _escucha(page, consola, red)

    def guarda(estado: str | None) -> None:
        archivo = os.path.relpath(Path(str(request.node.path)).resolve(), raiz)
        _escribe_atomico(d / "pasos.json", {
            "caso": caso, "titulo": depura(request.node.name), "archivo": archivo, "head": head, "corrida": corrida,
            "reintento": intento - 1, "estado": estado, "pasos": pasos,
            "generado": dt.datetime.now().isoformat(timespec="seconds")})

    @contextmanager
    def _paso(accion: str, esperado: str, mascara=None):
        n, desde_consola, desde_red, inicio = len(pasos) + 1, len(consola), len(red), time.monotonic()
        resultado, error, notas = "falla", None, Anotaciones()
        try:
            yield notas
            resultado = "pasa"
        except Exception as e:
            error = depura(e)
            raise
        finally:
            captura = _captura_de_pantalla(page, d, n, mascara) if page is not None else None
            texto = None
            if (contenido := texto_del_paso(notas.lineas, error, page is not None)) is not None:
                texto = f"paso-{n:02d}.txt"
                (d / texto).write_text(contenido, encoding="utf-8")
            pasos.append({"n": n, "accion": depura(accion), "esperado": depura(esperado), "resultado": resultado,
                          "error": error, "url": limpia_url(page.url) if page is not None else None,
                          "captura": captura, "texto": texto, "consola": consola[desde_consola:],
                          "red": red[desde_red:], "duracion_ms": round((time.monotonic() - inicio) * 1000)})
            guarda(None)

    yield _paso
    # Provisional: el hook de teardown lo corrige con el peor de setup, call y teardown.
    guarda({"passed": "passed", "failed": "failed"}.get(request.node.__dict__.get("_estados_evidencia", {}).get("call")))
