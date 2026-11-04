#!/usr/bin/env python3
"""implementa_plan.py — la compuerta de /implementa-plan.

Quien implementa no decide si ya terminó. Lo que este script puede comprobar por sí mismo lo comprueba él (corre la
suite, la mutación que pone una prueba en rojo y la validación aislada) y amarra cada resultado al commit que juzgó:
cualquier cambio posterior lo invalida. Lo que solo Juan puede decidir (un PR sin validar, rojos preexistentes, una
URL que no es local, una Verificación ilegible) exige su texto literal, que queda registrado y sale en el reporte y en el PR.

Modelo de amenaza: protege contra errores honestos del agente que implementa (y de los otros agentes), no contra
trampas deliberadas: un agente que edite D/ o este script puede saltárselo, y por eso todo lo autorizado queda a la
vista.

  inicia        --plan P --repo R --suite CMD [--url U [--confirmacion-url TEXTO]] [--base RAMA] [--dir D]
                [--sesion opus|fable] [--con-advisor] [--desde-sesion]
  suite         --dir D --fase NOMBRE [--plazo S]           corre la suite de inicia y guarda rc + HEAD
                (fase-3: además, con las mutaciones de los rojos aplicadas, para comprobar que la suite los corre;
                las que no comparten archivos van juntas en una corrida)
  casos         --archivo F | --dir D [--sin-huecos TEXTO]   valida los huecos (con --dir los congela)
  rojo          --dir D --caso T-01 --prueba ID --comando C --parche P [--plazo S]
                corre la prueba en el repo sin y con la mutación (y la deshace); registra el resultado
  rojos         --dir D [--repetir]                          ¿cada caso exigido se vio en rojo? (--repetir: los vencidos)
  manuales      --archivo F [--salida H] [--dir D]          valida y congela los casos manuales (al menos uno
                automatizable: la evidencia con captura y su revisión no se omiten)
  enmienda-manual --dir D --caso M-01 --paso N --esperado T --motivo M --autorizacion TEXTO
                cambia el esperado de un paso ya congelado (con el texto literal de Juan; va en el PR)
  prepara-evidencia --dir D --ronda K [--vuelta-extra-autorizada TEXTO]   vacía la vuelta abierta antes de correrla
  evidencia     --dir D --ronda K [--anexo R ...] [--vuelta-extra-autorizada TEXTO]   arma D/evidencia/ronda-K/index.html
                (tras 3 vueltas seguidas sin aprobar, una sola vuelta más con el texto literal de Juan)
  cruza         --dir D --ronda K --codex A --claude B        cruza las dos revisiones de la evidencia
  abre-ronda    --dir D [--omitidos-autorizados TEXTO] [--ronda-extra-autorizada TEXTO]
                abre la siguiente ronda de la revisión final (pasado el máximo, una sola más con el texto de Juan:
                se aprueba si ningún revisor trae graves y los medios abiertos van en el PR)
  registra      --dir D --ronda N --juez J --archivo F       guarda un veredicto (veredicto.json); nunca sobrescribe
  siguiente     --dir D                                      abrir-ronda | revisar | corregir | aprobado | escalar
  verificacion  --dir D [--comando C ...] [--plan-ilegible TEXTO]  arma el plan que consume valida_impl.py
  valida        --dir D [--imagen I]                         corre valida_impl.py y amarra su rc al HEAD
  copia         --dir D                                      HEAD y diff sin archivos con nombre de secreto
  codex         --dir D --prompt P --esquema E --salida F [--esfuerzo high]   Codex sobre la copia, en sandbox
  claude        --dir D --prompt P --esquema E --salida F [--modelo M]   el revisor Claude, encerrado en la copia y en D
                (los dos reciben el esquema dentro del prompt: no necesitan leer ~/.claude/schemas)
  reporte       --dir D                                      arma D/reporte-pruebas.html: un solo HTML con toda la
                evidencia de las pruebas, una pestaña por tipo (suite, cada tipo de prueba nueva, manuales con sus
                capturas, validación aislada); «cierre» lo vuelve a armar
  cierre        --dir D [--borrador-autorizado TEXTO] [--rojos-preexistentes-autorizados TEXTO]
                exige la última vuelta de evidencia aprobada (no se corta sin aprobar),  D/pr.md sin firma ni secretos y con cada autorización de Juan citada literal; arma el reporte

Salida: JSON. rc 0 = ok o aprobado, 1 = no pasa (o error de uso), 2 = entrada inválida.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import html
import io
import ipaddress
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tarfile
import tempfile
import time
import zlib
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jurado  # noqa: E402

ESQUEMAS = jurado.RAIZ / "schemas"
VALIDA_IMPL = Path(__file__).resolve().parent / "valida_impl.py"
TIPOS = ("unitaria", "integracion", "e2e", "contrato", "seguridad", "regresion", "datos", "rendimiento",
         "concurrencia", "accesibilidad")
SUITES_EXIGIDAS = ("linea-base", "fase-1", "fase-3", "final")
MAX_RONDAS = 3
MAX_FALLAS_EVIDENCIA = 3
PLAZO = 1800
LIMITE_SALIDA = 4000
ID_MANUAL = re.compile(r"^M-\d{2,}$")
CAPTURA = re.compile(r"^paso-\d{2,}\.png$")
# Captura de texto de un paso sin navegador (API, línea de comandos): lo que la prueba anotó.
CAPTURA_TEXTO = re.compile(r"^paso-\d{2,}\.txt$")
MAX_CAPTURA_TEXTO = 200_000
FASE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")
CITA = re.compile(r"([\w./-]+\.[A-Za-z0-9]+):(\d+)")
REPORTADO = {"passed": "pasa", "failed": "falla", "timedOut": "falla", "interrupted": "falla"}
TRIVIAL = re.compile(r"^\s*(true|:|/bin/true|exit\s+0|echo(\s.*)?|printf(\s.*)?)\s*$")
# Rama y commits que pide CLAUDE.md: feature/, fix/, refactor/ o docs/ y Conventional Commits.
RAMA = re.compile(r"^(feature|fix|refactor|docs)/[A-Za-z0-9][A-Za-z0-9._/-]*$")
CONVENCIONAL = re.compile(r"^(?:(feat|fix|refactor|docs|test|chore|perf|build|ci|style|revert)(\([^)]+\))?!?: \S"
                          r'|Revert ")')
RUTAS_PERMITIDAS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/bin/sh", "/bin/bash", "/usr/bin/env"}
# Un rojo por esto no prueba la aserción: prueba que el código ya no carga.
ROJO_FALSO = re.compile(r"ImportError|ModuleNotFoundError|SyntaxError|IndentationError|NameError|ReferenceError"
                        r"|AttributeError: module|errors? (during|while) collect|ERROR collecting|no tests ran"
                        r"|No tests found|Cannot find module|TS\d{4}:|is not defined", re.I)
# Un rojo válido es la aserción de la prueba (Python, Jest, Vitest, Playwright, Chai), no cualquier excepción.
ASERCION = re.compile(r"AssertionError|\bassert\b|Expected|expect\(|\.to(Be|Equal|Have|Contain|Match)|Received", re.I)
# pytest.raises sin excepción y pytest.fail: «E   Failed: DID NOT RAISE …» (con mayúscula y la E de pytest).
ASERCION_PYTEST = re.compile(r"^E\s+Failed: ", re.M)
# Infraestructura de pruebas: si cambia, un rojo ya visto puede dejar de valer.
CONFIG_PRUEBAS = re.compile(r"(^|/)(conftest\.py|pytest\.ini|tox\.ini|setup\.cfg|pyproject\.toml|package\.json"
                            r"|tsconfig[^/]*\.json|(jest|vitest|playwright|babel)\.config\.[cm]?[jt]s)$")
SIN_BYTECODE = {"PYTHONDONTWRITEBYTECODE": "1"}
# Django también descubre «tests_*.py» (candidates/tests_models.py), no solo «test_*.py».
PRUEBA_UNITARIA = re.compile(r"(^|/)(tests?|__tests__|specs?)(/|$)|(^|/)tests?_[^/]+\.py$|_test\.(py|go)$"
                             r"|\.(spec|test)\.[cm]?[jt]sx?$")
# Un archivo de prueba por su nombre (no por su carpeta: tests/README.md o tests/helpers.py no son pruebas).
TEST_ARCHIVO = re.compile(r"(^|/)(test_[^/]*|tests_[^/]+|[^/]*_test|tests)\.py$|\.(spec|test)\.[cm]?[jt]sx?$")
# Cambios que no pueden alterar lo que se vio en pantalla (además de archivos de prueba unitaria).
DOCUMENTACION = re.compile(r"^docs?/|(^|/)(README|CHANGELOG|LICENSE|AUTHORS|CONTRIBUTING)(\.\w+)?$", re.I)
# CLAUDE.md prohíbe cualquier Co-Authored-By, no solo el de Claude; «generated with factory_boy» sí es prosa.
FIRMA = re.compile(r"^\s*co-authored-by:|generated with \[?claude code|claude\.ai/code", re.I | re.M)
NOMBRES_SECRETOS = (".env", ".env.*", "*secret*", "*token*", "*password*", "*api_key*", "credentials.json")
# Fallas que imprime cada runner (pytest -r, unittest, Playwright, Jest/Vitest), para comparar rojos.
FALLAS = (re.compile(r"^(?:FAILED|ERROR)\s+([^\s(]\S*)", re.M), re.compile(r"^(?:FAIL|ERROR):\s+(\S+ \([^)]*\))", re.M),
          re.compile(r"^\s*\d+\)\s+(\[[^\]]+\]\s+›.+?)\s*$", re.M), re.compile(r"^\s*●\s+(.+?)\s*$", re.M),
          re.compile(r"^\s*FAIL\s+(\S+\s+>\s+.+?)\s*$", re.M))
E2E = re.compile(r"(^|/)(e2e|tests?-e2e|e2e-tests?|playwright|cypress)(/|$)|playwright\.config\.|(^|/)evidencia(_pw)?\.",
                 re.I)
# Mismos patrones que depuran las fixtures (plantillas/evidencia.ts y evidencia_pw.py): si algo de esto sobrevive en
# la evidencia, es una fuga.
# La clave termina en la palabra sensible (más _key, _id, _hash o una s): «client_secret» y «SECRET_KEY» sí,
# «secretary_name» y «credential_type» no. Prefijo y esquema de URL acotados: con * el motor retrocede de forma cuadrática (el esquema de URL sin tope tardaba 59 s con «x-auth-» × 30 000).
_CLAVE = (r"[A-Za-z0-9_.-]{0,40}(?:pass(?:word|wd)?|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key"
          r"|credential|authorization|session(?:[_-]?id)?|cookie|contrase[ñn]a|secreto)(?:[_.-]?(?:key|id|hash|digest))?s?")
_ENCABEZADO = r"(?:proxy-)?authorization|set-cookie|cookie|x-[a-z0-9-]{0,40}(?:auth|api-?key|token|secret)[a-z0-9-]{0,40}"
# Claves y cabeceras solo empiezan tras un delimitador (o al inicio): con \b, «x-auth-» × 30 000 tarda ~1 s en vez de 0.02 s.
_INICIO = r"(?<![^\s\"'{,;(?&/])"
SECRETOS = {
    "llave-privada": re.compile(r"-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----"),
    "encabezado": re.compile(rf"{_INICIO}(?P<h>{_ENCABEZADO})[\"']?\s*[:=]\s*[\"']?(?!\*\*\*)[^\s\"'*][^\r\n\"']*", re.I),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    "proveedor": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:ant-|proj-)?"
                            r"[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}"
                            r"|glpat-[A-Za-z0-9_-]{20,}|[rsp]k_(?:live|test)_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16})"),
    "esquema-auth": re.compile(r"\b(?P<esq>Basic|Digest|Bearer|Token|NTLM|Negotiate)\s+(?!\*\*\*)"
                               r"[A-Za-z0-9._~+/=-]{8,}", re.I),
    "clave=valor": re.compile(rf"{_INICIO}(?P<clave>{_CLAVE}[\"']?\s*[:=]\s*[\"']?)(?!\*\*\*)(?P<valor>[^\s\"'&,;}}]{{4,}})",
                              re.I),
    "url-con-usuario": re.compile(r"\b[a-z][a-z0-9+.-]{0,30}://[^/\s:@]{1,200}:(?!\*\*\*@)[^/\s@]{1,200}@", re.I),
}

# En el cuerpo del PR «el password: requiere 8 caracteres» es prosa; un valor con forma de token o una asignación no.
_VALOR_TOKEN = r"(?=[A-Za-z0-9._~+/=-]*\d)(?=[A-Za-z0-9._~+/=-]*[A-Za-z])[A-Za-z0-9._~+/=-]{10,}"
SECRETOS_PR = {
    **{n: SECRETOS[n] for n in ("llave-privada", "jwt", "proveedor", "esquema-auth", "url-con-usuario")},
    "asignacion": re.compile(rf"{_INICIO}(?:{_CLAVE}|{_ENCABEZADO})[\"']?\s*=\s*[\"']?(?!\*\*\*)[^\s\"'&,;}}]{{6,}}", re.I),
    "clave-con-token": re.compile(rf"{_INICIO}(?:{_CLAVE}|{_ENCABEZADO})[\"']?\s*:\s*[\"']?{_VALOR_TOKEN}", re.I),
}

CSS = """:root{--bg:#fff;--fg:#1d2329;--muted:#5b6670;--line:#d9dee3;--head:#eef1f4;--ok:#1a7f37;--bad:#c62828;
--warn:#9a6700;--zebra:#f7f9fa}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#14181c;--fg:#e6e9ec;--muted:#9aa5ae;
--line:#2e353c;--head:#1f252b;--ok:#4ac26b;--bad:#ff6b6b;--warn:#d4a72c;--zebra:#181d22}}
body{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;margin:0 auto;max-width:1280px;
padding:16px}
h1{font-size:22px}h2{font-size:17px;margin-top:32px}.meta{color:var(--muted)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:var(--head)}tr:nth-child(even) td{background:var(--zebra)}td:first-child{font-weight:600;
white-space:nowrap}.pasa{color:var(--ok);font-weight:600}.falla{color:var(--bad);font-weight:600}
.sin-estado,.alerta{color:var(--warn);font-weight:600}img{max-width:320px;border:1px solid var(--line)}
pre{white-space:pre-wrap;margin:0;font-size:12px}ol{margin:0;padding-left:18px}"""


class Falla(Exception):
    """Error de uso o de estado: se reporta como JSON con rc 1 (o el rc que traiga)."""

    def __init__(self, motivo: str, rc: int = 1):
        super().__init__(motivo)
        self.rc = rc


# ───────────────────────────── utilidades ─────────────────────────────

def _imprimir(datos) -> None:
    print(json.dumps(datos, ensure_ascii=False, indent=1))


def _falla(motivo: str, rc: int = 1) -> int:
    _imprimir({"ok": False, "errores": [motivo]})
    return rc


def _esquema(nombre: str) -> dict:
    datos = jurado.leer_json(ESQUEMAS / f"{nombre}.json")
    if not isinstance(datos, dict):
        raise Falla(f"no se pudo leer el esquema {ESQUEMAS / nombre}.json", rc=2)
    return datos


def _cargar(ruta, esquema: str) -> tuple[dict | None, list[str]]:
    """Lee un JSON (puro o al final de prosa en un bloque ```json) y lo valida contra el esquema."""
    try:
        texto = Path(ruta).expanduser().read_text(encoding="utf-8")
    except OSError as e:
        return None, [f"no se pudo leer {ruta}: {e}"]
    estado, datos = jurado.extraer_json(texto)
    if estado != "ok":
        return None, [f"{ruta}: {estado}"]
    errores = jurado.validar_esquema(datos, _esquema(esquema))
    return (None, errores) if errores else (datos, [])


def _git(repo, *args: str, entrada: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False, input=entrada,
                          text=entrada is None)


def _head(repo) -> str:
    return _git(repo, "rev-parse", "HEAD").stdout.strip()


def _sucio(repo) -> list[str]:
    return _git(repo, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()


def _exige_limpio(repo) -> None:
    sucio = _sucio(repo)
    if sucio:
        raise Falla(f"el árbol de {repo} tiene cambios sin commit ({len(sucio)}): {'; '.join(sucio[:5])}")


def _cambiados(repo, desde: str) -> list[str]:
    return [r for r in _git(repo, "diff", "--name-only", "-z", desde, "HEAD").stdout.split("\0") if r]


def _agregados(repo, desde: str) -> list[str]:
    return [r for r in _git(repo, "diff", "--name-only", "--diff-filter=A", "-z", desde, "HEAD").stdout.split("\0") if r]


def _sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def _shell(comando: str, cwd, plazo: int, entorno: dict | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(["sh", "-c", comando], cwd=str(cwd), capture_output=True, text=True, timeout=plazo,
                           check=False, env={**os.environ, **(entorno or {})})
    except subprocess.TimeoutExpired:
        return 124, f"tiempo agotado tras {plazo} s"
    return r.returncode, (r.stdout + r.stderr)


def _e(valor) -> str:
    return html.escape("" if valor is None else str(valor))


def _pagina(titulo: str, cuerpo: str, css: str = "") -> str:
    return (f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>{_e(titulo)}</title>"
            f"<style>{CSS}{css}</style></head><body><h1>{_e(titulo)}</h1>{cuerpo}</body></html>\n")


def _escribir(ruta: Path, texto: str) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def _duplicados(ids: list[str]) -> list[str]:
    return [f"id repetido «{i}»" for i, n in Counter(ids).items() if n > 1]


def _config(d: Path) -> dict:
    cfg = jurado.leer_json(d / "config.json")
    if not isinstance(cfg, dict):
        raise Falla(f"no hay config.json legible en {d}; corre «inicia» primero", rc=2)
    return cfg


def _congelado(d: Path, nombre: str) -> Path:
    """Ruta de un artefacto congelado; falla si cambió después de validarse."""
    ruta, sello = d / nombre, jurado.leer_json(d / f"{nombre}.sello.json")
    if not ruta.is_file() or not isinstance(sello, dict):
        raise Falla(f"{nombre} no está validado ni congelado en {d}")
    if _sha256(ruta) != sello.get("sha256"):
        raise Falla(f"{nombre} cambió después de validarse")
    return ruta


def _sellar(d: Path, nombre: str, autorizacion: str | None = None) -> None:
    jurado.escribir_json(d / f"{nombre}.sello.json", {"sha256": _sha256(d / nombre), "autorizacion": autorizacion,
                                                      "ts": jurado.ahora()})


def _autorizacion_sellada(d: Path, nombre: str) -> str | None:
    return (jurado.leer_json(d / f"{nombre}.sello.json") or {}).get("autorizacion")


def _leer(ruta) -> str:
    try:
        return Path(ruta).expanduser().read_text(encoding="utf-8")
    except OSError as e:
        raise Falla(f"no se pudo leer {ruta}: {e}")


def secretos_en(texto: str) -> list[str]:
    return [nombre for nombre, patron in SECRETOS.items() if patron.search(texto or "")]


def depurar(texto: str) -> str:
    texto = re.sub(r"-----BEGIN ([A-Z ]{0,40})PRIVATE KEY-----.*?(?:-----END \1PRIVATE KEY-----|\Z)",
                   "*** llave privada ***", texto, flags=re.S)
    texto = SECRETOS["encabezado"].sub(lambda m: f"{m.group('h')}: ***", texto)
    texto = SECRETOS["jwt"].sub("***", texto)
    texto = SECRETOS["proveedor"].sub("***", texto)
    texto = SECRETOS["esquema-auth"].sub(lambda m: f"{m.group('esq')} ***", texto)
    texto = SECRETOS["clave=valor"].sub(lambda m: f"{m.group('clave')}***", texto)
    return re.sub(r"(\b[a-z][a-z0-9+.-]{0,30}://)[^/\s@]{1,400}@", r"\1***@", texto, flags=re.I)


# ───────────────────────────── inicia ─────────────────────────────

def _dir_registro(plan: Path, repo: Path) -> Path:
    base = jurado.AUDITORIAS / repo.name / f"{dt.date.today().isoformat()}-impl-{plan.stem}"
    d, k = base, 1
    while d.exists():
        k += 1
        d = base.with_name(f"{base.name}-{k}")
    return d


def revisar_url(url: str | None, confirmacion: str | None) -> list[str]:
    if url is None:
        return []
    partes = urlsplit(url)
    if partes.scheme not in ("http", "https") or not partes.hostname:
        return [f"URL inválida: {url}"]
    host = partes.hostname
    try:
        local = ipaddress.ip_address(host).is_loopback or host == "0.0.0.0"
    except ValueError:
        local = host == "localhost" or host.endswith(".localhost")
    if local:
        return []
    if not confirmacion or host.lower() not in confirmacion.lower():
        return [f"{host} no es local: hace falta --confirmacion-url con el texto literal de Juan que nombre ese host"]
    return []


def _base(repo: Path, rama: str | None) -> dict:
    if _git(repo, "rev-parse", "--is-inside-work-tree").returncode != 0:
        raise Falla(f"{repo} no es un repo git")
    if _git(repo, "rev-parse", "HEAD").returncode != 0:
        raise Falla(f"{repo} no tiene commits: no hay base contra la cual medir")
    rama = rama or _git(repo, "branch", "--show-current").stdout.strip()
    if not rama:
        raise Falla("HEAD desatendido: pasa --base <rama> para saber contra qué va el PR")
    sha = _git(repo, "rev-parse", "--verify", f"{rama}^{{commit}}")
    if sha.returncode != 0:
        raise Falla(f"la rama base «{rama}» no existe en {repo}")
    return {"base": sha.stdout.strip(), "rama_base": rama}


def _congelar_plan(plan: Path, d: Path) -> Path:
    """Copia el plan al registro: revisores y validación juzgan contra esta versión, no contra una que siga cambiando."""
    copia = d / f"plan{plan.suffix or '.md'}"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(plan, copia)
    return copia


def _revisar_inicio(a, plan: Path) -> None:
    if not plan.is_file():
        raise Falla(f"no existe el plan {plan}")
    if not shutil.which(jurado.codex_bin()):
        raise Falla(f"Codex no está disponible ({jurado.codex_bin()}); sin él no hay segundo modelo")
    if not a.suite.strip() or TRIVIAL.match(a.suite):
        raise Falla(f"--suite «{a.suite}» no corre ninguna prueba")
    if (bandera := fail_fast(a.suite)):
        raise Falla(f"--suite corta en la primera falla («{bandera}»): quítala; la línea base, los rojos nuevos y la "
                    "comprobación de fase-3 necesitan la lista completa de fallas")
    errores = revisar_comando(a.suite) + revisar_url(a.url, a.confirmacion_url)
    if errores:
        raise Falla(errores[0])


def cmd_inicia(a) -> int:
    plan, repo = Path(a.plan).expanduser().resolve(), Path(a.repo).expanduser().resolve()
    _revisar_inicio(a, plan)
    base = _base(repo, a.base)
    _exige_limpio(repo)
    d = Path(a.dir).expanduser().resolve() if a.dir else _dir_registro(plan, repo)
    if (d / "config.json").exists():
        raise Falla(f"ya hay un registro en {d}; usa otro --dir")
    jueces = ["codex", "claude"] + (["advisor-opus" if a.sesion == "fable" else "advisor"] if a.con_advisor else [])
    copia = _congelar_plan(plan, d)
    cfg = {"plan": str(copia), "plan_origen": "sesion" if a.desde_sesion else str(plan),
           "plan_sha256": _sha256(copia), "repo": str(repo), **base, "suite": " ".join(a.suite.split()),
           "url": a.url, "confirmacion_url": a.confirmacion_url, "jueces": jueces, "max_rondas": MAX_RONDAS,
           "sesion": a.sesion,
           "creado": jurado.ahora()}
    jurado.escribir_json(d / "config.json", cfg)
    _imprimir({"dir": str(d), "plan": str(copia), "plan_origen": cfg["plan_origen"], **base, "jueces": jueces})
    return 0


# ───────────────────────────── suite ─────────────────────────────

def fallas(salida: str) -> list[str]:
    """Pruebas que fallaron según la salida del runner. Playwright remata su cabecera con «────»: se quita."""
    return sorted({re.sub(r"\s*─+$", "", " ".join(m.group(1).split())) for patron in FALLAS
                   for m in patron.finditer(salida)})


def fail_fast(comando: str) -> str | None:
    """La bandera que corta la suite en la primera falla, si la hay. «--maxfail 0», «--bail=0» o «--bail=false» no
    cortan. En pytest también cuenta la x dentro de un grupo de banderas cortas (-xvs), salvo después de una que toma
    valor (-rxs es «-r xs»); en unittest, la f (-fv)."""
    try:
        tokens = shlex.split(comando)
    except ValueError:
        return None
    es_pytest = any(Path(x).name in ("pytest", "py.test") for x in tokens)
    for i, x in enumerate(tokens):
        nombre, igual, valor = x.partition("=")
        if nombre in ("--maxfail", "--max-failures"):
            valor = valor if igual else (tokens[i + 1] if i + 1 < len(tokens) else "")
            if not re.fullmatch(r"0+", valor):
                return x
        elif nombre in ("-x", "--exitfirst", "--failfast", "--bail"):
            if not (igual and re.fullmatch(r"0+|false", valor)):
                return x
        elif (x == "-f" and "unittest" in tokens) or (x == "-b" and "jest" in tokens):
            return x
        elif re.fullmatch(r"-[A-Za-z]{2,}", x) and (es_pytest or "unittest" in tokens):
            corta, con_valor = ("x", "kmpcoWr") if es_pytest else ("f", "k")
            for letra in x[1:]:
                if letra in con_valor:
                    break
                if letra == corta:
                    return x
    return None


def _revisar_orden_suite(d: Path, cfg: dict, fase: str) -> None:
    if fase == "linea-base":
        if (d / "suite-linea-base.json").exists():
            raise Falla("la línea base ya se corrió: es inmutable")
        if _head(cfg["repo"]) != cfg["base"]:
            raise Falla("la línea base se corre en el commit base, antes de tocar nada")
        return
    previa = dict(zip(SUITES_EXIGIDAS[1:], SUITES_EXIGIDAS)).get(fase, "linea-base")
    if not (d / f"suite-{previa}.json").is_file():
        raise Falla(f"corre primero «suite --fase {previa}»")


def cmd_suite(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    if not FASE.match(a.fase):
        raise Falla(f"fase «{a.fase}» inválida (minúsculas, dígitos y guiones)")
    _revisar_orden_suite(d, cfg, a.fase)
    _exige_limpio(cfg["repo"])
    head = _head(cfg["repo"])
    # Sin cortar en el primer tramo rojo de «A && B»: un rojo preexistente en A no puede esconder uno nuevo en B.
    rc, salida = _shell(suite_sin_corte(cfg["suite"]), cfg["repo"], a.plazo)
    salida = depurar(salida)
    _escribir(d / f"suite-{a.fase}.txt", salida)
    corrida = {"head": head, "rc": rc, "comando": cfg["suite"], "fallas": fallas(salida), "ts": jurado.ahora()}
    if a.fase == "fase-3":
        corrida["rojos_en_suite"] = rojos_en_suite(d, cfg, a.plazo)
    jurado.escribir_json(d / f"suite-{a.fase}.json", corrida)
    nuevos = rojos_nuevos(corrida, jurado.leer_json(d / "suite-linea-base.json") or {}) if a.fase != "linea-base" else []
    errores = _errores_de_suite(corrida, a.fase)
    _imprimir({"fase": a.fase, "rc": rc, "head": head, "fallas": corrida["fallas"], "nuevos_vs_linea_base": nuevos,
               "errores": errores, "salida": salida[-LIMITE_SALIDA:]})
    if a.fase == "linea-base":
        return 0 if rc in (0, 1) else 1
    return 0 if nuevos == [] and not errores else 1


def _errores_de_suite(corrida: dict, fase: str) -> list[str]:
    """Por qué una corrida no sirve, en palabras: abortó, salió roja sin fallas legibles, o no corre un rojo."""
    rc, en_suite = corrida["rc"], corrida.get("rojos_en_suite", {})
    errores = [f"la suite no corre {x} ({en_suite.get('motivos', {}).get(x, '')}): revisa el nombre del archivo o el "
               "comando de --suite; si la mutación la corta antes (carga, recolección o fail-fast en la configuración "
               "del runner), afina la mutación" for x in en_suite.get("fuera", [])]
    if fase == "linea-base":
        return errores
    if rc not in (0, 1):
        errores.append(f"la suite abortó (rc {rc}): no se puede comparar con la línea base")
    elif rc == 1 and not corrida["fallas"]:
        errores.append("la suite salió roja (rc 1) sin ninguna falla legible en su salida: el runner debe listar las "
                       "pruebas que fallan (pytest, unittest, Django, Jest, Vitest, Playwright)")
    return errores


def rojos_nuevos(corrida: dict, base: dict) -> list[str] | None:
    """Fallas que no estaban en la línea base. None si no se puede comparar: la corrida abortó (rc distinto de 1, el
    código de «fallaron pruebas» de pytest, unittest, Django, Jest, Vitest y Playwright) o no se leyeron sus fallas."""
    if corrida.get("rc") == 0:
        return []
    actuales = set(corrida.get("fallas") or [])
    if corrida.get("rc") != 1 or not actuales:
        return None
    return sorted(actuales - (set(base.get("fallas") or []) if base.get("rc") == 1 else set()))


def _rojo_final(final: dict, base: dict, autorizado: str | None) -> list[str]:
    """Una suite final roja solo pasa si sus rojos son un subconjunto de los de la línea base y Juan lo aceptó."""
    nuevos = rojos_nuevos(final, base)
    if nuevos is None:
        return [f"la suite final salió con rc {final.get('rc')} y no se puede comparar con la línea base (abortó o no "
                "se leyeron sus fallas)"]
    if nuevos:
        return [f"rojos que no estaban en la línea base: {', '.join(nuevos[:5])}"]
    return [] if autorizado else ["la suite final tiene los mismos rojos que la línea base: hace falta la "
                                  "autorización literal de Juan (--rojos-preexistentes-autorizados)"]


def _revisar_suites(d: Path, cfg: dict, rojos_autorizados: str | None) -> list[str]:
    errores = [f"falta la corrida de suite «{f}»: corre «suite --fase {f}»" for f in SUITES_EXIGIDAS
               if not (d / f"suite-{f}.json").is_file()]
    final, base = jurado.leer_json(d / "suite-final.json"), jurado.leer_json(d / "suite-linea-base.json") or {}
    if base and base.get("head") != cfg["base"]:
        errores.append("la línea base no se corrió en el commit base")
    errores += _revisar_intermedias(d, cfg, base)
    if not isinstance(final, dict):
        return errores
    if final.get("head") != _head(cfg["repo"]):
        return errores + ["la suite final es de otro HEAD: vuelve a correr «suite --fase final»"]
    return errores + ([] if final.get("rc") == 0 else _rojo_final(final, base, rojos_autorizados))


def _es_ancestro(repo, a: str, b: str) -> bool:
    return _git(repo, "merge-base", "--is-ancestor", a, b).returncode == 0


def _revisar_intermedias(d: Path, cfg: dict, base: dict) -> list[str]:
    """fase-1 y fase-3 sin rojos nuevos, y en orden: base ≤ fase-1 ≤ fase-3 ≤ HEAD."""
    errores, anterior = [], cfg["base"]
    for fase in ("fase-1", "fase-3"):
        corrida = jurado.leer_json(d / f"suite-{fase}.json")
        if not isinstance(corrida, dict):
            continue
        nuevos = rojos_nuevos(corrida, base)
        if nuevos is None or nuevos:
            errores.append(f"la suite «{fase}» tiene rojos nuevos o ilegibles frente a la línea base: {nuevos}")
        if not _es_ancestro(cfg["repo"], anterior, corrida["head"]):
            errores.append(f"la suite «{fase}» no está después de la fase anterior en la historia")
        anterior = corrida["head"]
    en_suite = (jurado.leer_json(d / "suite-fase-3.json") or {}).get("rojos_en_suite", {})
    pruebas = (jurado.leer_json(d / "fase-3-rojos.json") or {}).get("pruebas", [])
    if pruebas and en_suite.get("huella") != huella_rojos(pruebas):
        errores.append("los rojos cambiaron después de «suite --fase fase-3» (un rojo nuevo o «rojos --repetir»): "
                       "vuelve a correrla")
    errores += [f"no está comprobado que la suite corra {p.get('prueba')}: corre «suite --fase fase-3»"
                for p in pruebas if p.get("prueba") not in set(en_suite.get("verificados", []))]
    if not _es_ancestro(cfg["repo"], anterior, "HEAD"):
        errores.append("HEAD no desciende de la última suite intermedia")
    return errores


# ───────────────────────────── casos de la suite y rojos ─────────────────────────────

def revisar_casos(datos: dict, sin_huecos: str | None = None) -> list[str]:
    casos, no_aplica = datos["casos"], datos["no_aplica"]
    if not casos and not sin_huecos:
        return ["no hay casos: seguir sin pruebas nuevas exige la autorización literal de Juan (--sin-huecos)"]
    exentos = [n["tipo"] for n in no_aplica if n["razon"].strip()]
    errores = _duplicados([c["id"] for c in casos]) + _duplicados([n["tipo"] for n in no_aplica])
    errores += [f"«no aplica» de «{n['tipo']}» sin razón" for n in no_aplica if not n["razon"].strip()]
    cubiertos = {c["tipo"] for c in casos}
    errores += [f"tipo «{t}» tiene casos y a la vez «no aplica»" for t in sorted(cubiertos & set(exentos))]
    errores += [f"tipo «{t}» sin casos ni razón de «no aplica»" for t in TIPOS if t not in cubiertos | set(exentos)]
    errores += [f"{c['id']}: sin «protege»" for c in casos if not c["protege"].strip()]
    if not casos:
        return errores
    return errores + _revisar_caminos([c["camino"] for c in casos], tope_feliz=1 / 3, exige=("error", "borde"))


def _revisar_caminos(caminos: list[str], tope_feliz: float, exige: tuple[str, ...]) -> list[str]:
    cuenta = Counter(caminos)
    errores = [f"no hay casos de camino «{c}»" for c in exige if not cuenta[c]]
    if cuenta["feliz"] > tope_feliz * len(caminos):
        errores.append(f"{cuenta['feliz']} de {len(caminos)} casos son camino feliz; el tope es "
                       f"{round(tope_feliz * 100)} %")
    return errores


def cmd_casos(a) -> int:
    if not a.archivo and not a.dir:
        raise Falla("pasa --archivo o --dir")
    d = Path(a.dir).expanduser() if a.dir else None
    datos, errores = _cargar(d / "fase-2-huecos.json" if d else a.archivo, "casos_prueba")
    if datos is None:
        return _falla("; ".join(errores), rc=2)
    errores = revisar_casos(datos, a.sin_huecos)
    if d and not errores:
        _sellar(d, "fase-2-huecos.json", a.sin_huecos if not datos["casos"] else None)
    _imprimir({"ok": not errores, "errores": errores, "casos": len(datos["casos"]),
               "por_tipo": dict(Counter(c["tipo"] for c in datos["casos"])),
               "por_camino": dict(Counter(c["camino"] for c in datos["casos"]))})
    return 0 if not errores else 1


def _linea_existe(repo, ruta: str, linea: int) -> bool:
    r = _git(repo, "show", f"HEAD:{ruta}")
    return r.returncode == 0 and 1 <= linea <= len(r.stdout.splitlines())


def _descartes(d: Path, repo, ids: set[str]) -> tuple[set[str], list[str]]:
    datos = jurado.leer_json(d / "fase-2-descartes.json") or {"descartes": []}
    fuera, errores = set(), []
    for x in datos.get("descartes", []):
        caso, m = x.get("id"), CITA.search(str(x.get("razon", "")))
        if caso not in ids:
            errores.append(f"descarte de «{caso}», que no está en fase-2-huecos.json")
        elif not m or not _linea_existe(repo, m.group(1), int(m.group(2))):
            errores.append(f"descarte de {caso} sin cita archivo:línea que exista en HEAD")
        elif not TEST_ARCHIVO.search(m.group(1)):
            errores.append(f"descarte de {caso}: la cita debe ser la prueba que ya lo cubre, no {m.group(1)}")
        else:
            fuera.add(caso)
    return fuera, errores


def _casos_exigidos(d: Path, repo) -> tuple[list[str], list[str]]:
    ruta = _congelado(d, "fase-2-huecos.json")
    huecos, errores = _cargar(ruta, "casos_prueba")
    if huecos is None:
        return [], errores
    ids = [c["id"] for c in huecos["casos"]]
    fuera, errores = _descartes(d, repo, set(ids))
    return [i for i in ids if i not in fuera], errores


def _archivos_del_parche(repo, parche: bytes) -> list[str]:
    r = _git(repo, "apply", "--numstat", "--summary", "-", entrada=parche)
    if r.returncode != 0:
        raise Falla(f"el parche no es válido: {r.stderr.decode(errors='replace')[:300]}")
    texto = r.stdout.decode()
    tocados = [linea.split("\t", 2)[2] for linea in texto.splitlines() if linea.count("\t") >= 2]
    if re.search(r"^\s*(create|delete) mode|^\s*rename ", texto, re.M) or b"/dev/null" in parche or any(
            _git(repo, "cat-file", "-e", f"HEAD:{t}").returncode != 0 for t in tocados):
        raise Falla("la mutación solo modifica archivos que ya existen: no crea, borra ni renombra")
    return tocados


def con_mutaciones(repo: Path, parches: list[bytes], comando: str, plazo: int) -> tuple[int, str]:
    """Aplica los parches en el repo, corre el comando y lo deja como estaba pase lo que pase (también con SIGTERM).

    En el repo y no en un worktree aparte: así cualquier runner encuentra sus dependencias, su configuración y la app
    que levanta (Django, pytest, Playwright con webServer, Jest, Vitest). Sin bytecode y con la fecha de los archivos
    mutados movida, para que ningún caché sirva la versión sin mutar."""
    tocados = sorted({x for parche in parches for x in _archivos_del_parche(repo, parche)})
    antes = {x: (Path(repo) / x).stat().st_mtime_ns for x in tocados}
    try:
        for parche in parches:
            aplicado = _git(repo, "apply", "-", entrada=parche)
            if aplicado.returncode != 0:
                raise Falla(f"el parche no aplica sobre HEAD: {aplicado.stderr.decode(errors='replace')[:300]}")
        for x, ns in antes.items():
            ruta = Path(repo) / x
            os.utime(ruta, ns=(time.time_ns(), max(ruta.stat().st_mtime_ns, ns + 2_000_000_000)))
        return _shell(comando, repo, plazo, SIN_BYTECODE)
    finally:
        _git(repo, "checkout", "HEAD", "--", *tocados)
        if _git(repo, "diff", "--quiet", "HEAD", "--", *tocados).returncode != 0:
            raise Falla(f"no se pudo deshacer la mutación en {tocados}: «git checkout HEAD -- <archivos>» a mano")


def _correr_mutacion(repo: Path, comando: str, parche: bytes, plazo: int) -> dict:
    """Salida completa ya depurada: el veredicto se calcula sobre ella y solo se persiste un recorte."""
    rc_sin, salida_sin = _shell(comando, repo, plazo, SIN_BYTECODE)
    rc_con, salida_con = con_mutaciones(repo, [parche], comando, plazo)
    return {"rc_sin": rc_sin, "salida_sin": depurar(salida_sin)[-1000:], "rc_con": rc_con, "salida": depurar(salida_con)}


def _recorte(texto: str, limite: int = LIMITE_SALIDA) -> str:
    """Cabeza y cola: unittest y Django ponen «FAIL: nombre» al principio y el resumen al final."""
    if len(texto) <= limite:
        return texto
    cabeza = limite // 3
    return texto[:cabeza] + "\n[…]\n" + texto[-(limite - cabeza):]


def nombre_de_prueba(prueba: str) -> str:
    """Lo que el runner imprime de la prueba: el último segmento del selector (archivo::Clase::nombre)."""
    return prueba.split("::")[-1].strip()


def _revisar_seleccion(prueba: str, comando: str) -> None:
    """Cualquier runner vale; el comando solo tiene que apuntar a la prueba (por archivo, módulo o nombre)."""
    archivo, nombre = prueba.split("::")[0].strip(), nombre_de_prueba(prueba)
    if "::" not in prueba or not archivo or not nombre:
        raise Falla(f"--prueba «{prueba}» debe ser <archivo>::<nombre>, como la reporta el runner")
    modulo = re.sub(r"\.py$", "", archivo).replace("/", ".")
    partes = modulo.split(".")
    prefijos = {".".join(partes[:k]) for k in range(1, len(partes))} | {"/".join(partes[:k]) for k in range(1, len(partes))}
    try:
        tokens = {x.rstrip("/") for x in shlex.split(comando)}
    except ValueError as e:
        raise Falla(f"comando ilegible: {e}")
    if not (any(x in comando for x in (archivo, modulo, nombre)) or tokens & prefijos):
        raise Falla(f"el comando no corre «{prueba}»: debe nombrar su archivo, su módulo o su nombre")


def falla_la_prueba(prueba: str, salida: str) -> bool:
    """¿La prueba declarada está entre las que fallaron? (no otra con nombre parecido, como test_x_borde)."""
    nombre = re.escape(nombre_de_prueba(prueba))
    vistas = fallas(salida)
    if vistas:
        return any(re.search(rf"(?:^|[\s.:›>]){nombre}(?:\s*[\[(]|\s*$)", f) for f in vistas)
    return bool(re.search(rf"(?<![\w-]){nombre}(?![\w-])", salida))


def registrar_rojo(d: Path, cfg: dict, caso: str, prueba: str, comando: str, parche: bytes, plazo: int) -> dict:
    repo = Path(cfg["repo"])
    _exige_limpio(repo)
    _revisar_seleccion(prueba, comando)
    exigidos, errores = _casos_exigidos(d, repo)
    if caso not in exigidos:
        raise Falla(f"{caso} no es un caso exigido de fase-2-huecos.json; {'; '.join(errores)}".rstrip("; "))
    tocados = _archivos_del_parche(repo, parche)
    if not tocados or any(PRUEBA_UNITARIA.search(x) or E2E.search(x) for x in tocados):
        raise Falla(f"el parche debe mutar solo código de producción: {tocados}")
    _escribir(d / "rojos" / f"{caso}.patch", parche.decode("utf-8", errors="replace"))
    entrada = {"caso": caso, "prueba": prueba, "comando": comando, "head": _head(repo), "mutados": tocados,
               "parche_sha256": hashlib.sha256(parche).hexdigest(), **_correr_mutacion(repo, comando, parche, plazo),
               "ts": jurado.ahora()}
    entrada["errores"] = _errores_de_rojo(entrada)
    entrada["salida"] = _recorte(entrada["salida"])
    rojos = jurado.leer_json(d / "fase-3-rojos.json") or {"pruebas": []}
    rojos["pruebas"] = [x for x in rojos["pruebas"] if x.get("caso") != caso] + [entrada]
    jurado.escribir_json(d / "fase-3-rojos.json", rojos)
    return entrada


def cmd_rojo(a) -> int:
    d = Path(a.dir)
    try:
        parche = Path(a.parche).expanduser().read_bytes()
    except OSError as e:
        raise Falla(f"no se pudo leer el parche: {e}")
    r = registrar_rojo(d, _config(d), a.caso, a.prueba, a.comando, parche, a.plazo)
    _imprimir({"ok": not r["errores"], **{k: r[k] for k in ("errores", "rc_sin", "rc_con", "salida")}})
    return 0 if not r["errores"] else 1


def _errores_de_rojo(p: dict) -> list[str]:
    prueba, salida = p.get("prueba", ""), depurar(p.get("salida", ""))
    if p.get("rc_sin") != 0:
        return [f"{prueba}: no pasa sin la mutación (rc {p.get('rc_sin')}): {p.get('salida_sin', '')[-300:]}"]
    if p.get("rc_con") in (0, None):
        return [f"{prueba}: sigue en verde con la mutación: no protege lo que dice"]
    if (m := ROJO_FALSO.search(salida)):
        return [f"{prueba}: el rojo es de carga o recolección, no de la aserción ({m.group(0)})"]
    if not falla_la_prueba(prueba, salida):
        return [f"{prueba}: con la mutación fallaron otras pruebas, no esta ({', '.join(fallas(salida)[:3])})"]
    if not (ASERCION.search(salida) or ASERCION_PYTEST.search(salida)):
        return [f"{prueba}: falló por una excepción, no por su aserción"]
    return []


def _rojo_vigente(p: dict, repo) -> list[str]:
    archivo = str(p.get("prueba", "")).split("::")[0]
    if _git(repo, "cat-file", "-e", f"HEAD:{archivo}").returncode != 0:
        return [f"{p.get('prueba')}: el archivo de prueba «{archivo}» no está en HEAD"]
    propios, desde = {archivo, *p.get("mutados", [])}, p.get("head", "HEAD")
    # Un archivo de prueba nuevo no cambia si otra prueba ya vista falla (un conftest o una config nuevos, sí).
    nuevos = {r for r in _agregados(repo, desde) if not CONFIG_PRUEBAS.search(r)}
    tocados = sorted(r for r in _cambiados(repo, desde) if r in propios or (
        r not in nuevos and not DOCUMENTACION.search(r)
        and (PRUEBA_UNITARIA.search(r) or E2E.search(r) or CONFIG_PRUEBAS.search(r))))
    return [f"{p.get('prueba')}: el rojo venció: cambiaron {', '.join(tocados[:5])}; corre «rojos --repetir»"] if tocados else []


def revisar_rojos(d: Path, repo) -> list[str]:
    try:
        exigidos, errores = _casos_exigidos(d, repo)
    except Falla as e:
        return [str(e)]
    pruebas = (jurado.leer_json(d / "fase-3-rojos.json") or {}).get("pruebas", [])
    errores += _duplicados([p.get("prueba") for p in pruebas])
    for p in pruebas:
        # El veredicto se calculó en «rojo» sobre la salida completa; aquí solo queda un recorte.
        errores += (p["errores"] if "errores" in p else [f"{p.get('prueba')}: registro sin veredicto; repite «rojo»"])
        errores += _rojo_vigente(p, repo)
    vistos = {p.get("caso") for p in pruebas}
    return errores + [f"caso {c} sin prueba vista en rojo (corre «rojo»)" for c in exigidos if c not in vistos]


def cmd_rojos(a) -> int:
    d = Path(a.dir)
    cfg = _config(d)
    repetidos, no_repetidos = [], {}
    for p in (jurado.leer_json(d / "fase-3-rojos.json") or {}).get("pruebas", []) if a.repetir else []:
        guardado = d / "rojos" / f"{p.get('caso')}.patch"
        if not (_rojo_vigente(p, cfg["repo"]) and guardado.is_file()):
            continue
        try:
            registrar_rojo(d, cfg, p["caso"], p["prueba"], p["comando"], guardado.read_bytes(), a.plazo)
            repetidos.append(p["caso"])
        except Falla as e:
            # Un parche que ya no aplica no detiene a los demás: ese caso pide un «rojo» nuevo.
            no_repetidos[p["caso"]] = str(e)
    errores = revisar_rojos(d, cfg["repo"])
    _imprimir({"ok": not errores, "errores": errores, "repetidos": repetidos, "no_repetidos": no_repetidos})
    return 0 if not errores else 1


def tramos_de_nivel_superior(comando: str) -> list[str]:
    """Partes de «A && B» separadas solo por los «&&» de nivel superior: fuera de comillas, paréntesis y llaves."""
    tramos, actual, comilla, nivel, i = [], "", None, 0, 0
    while i < len(comando):
        c = comando[i]
        if c == "\\" and comilla != "'" and i + 1 < len(comando):
            actual, i = actual + comando[i:i + 2], i + 2
            continue
        if comilla:
            comilla = None if c == comilla else comilla
        elif c in "'\"":
            comilla = c
        elif c in "({":
            nivel += 1
        elif c in ")}":
            nivel -= 1
        elif nivel == 0 and comando.startswith("&&", i):
            tramos, actual, i = tramos + [actual.strip()], "", i + 2
            continue
        actual, i = actual + c, i + 1
    return [x for x in tramos + [actual.strip()] if x]


def suite_sin_corte(comando: str) -> str:
    """La suite con todos sus tramos corriendo aunque uno falle, en el mismo shell (un «cd» o un «source» siguen
    valiendo para los siguientes), y en rojo si cualquiera falló: «A && B» → «{ A; } || f=1; { B; } || f=1; exit»."""
    tramos = tramos_de_nivel_superior(comando)
    if len(tramos) < 2:
        return comando
    return "; ".join(f"{{ {x}\n}} || __fallo=1" for x in tramos) + '; exit "${__fallo:-0}"'


def huella_rojos(pruebas: list[dict]) -> str:
    """Qué rojos (caso, prueba, parche y commit) comprobó la fase-3: si cambia uno, la comprobación ya no vale."""
    datos = sorted((p.get("caso"), p.get("prueba"), p.get("parche_sha256"), p.get("head")) for p in pruebas)
    return hashlib.sha256(json.dumps(datos).encode()).hexdigest()


def _motivo_fuera(rc: int, salida: str) -> str:
    carga = ROJO_FALSO.search(salida)
    visto = f"carga/recolección: {carga.group(0)}" if carga else (", ".join(fallas(salida)[:3]) or "sin fallas legibles")
    return f"rc {rc}, {visto}"


def grupos_de_mutaciones(unicos: list[dict]) -> list[list[dict]]:
    """Reparte los parches (ya sin repetidos) en grupos que no comparten archivos mutados, cada uno en el primer grupo
    donde quepa: dos mutaciones del mismo archivo no se pueden aplicar juntas."""
    grupos: list[list[dict]] = []
    for u in unicos:
        destino = next((g for g in grupos if not any(set(u["mutados"]) & set(x["mutados"]) for x in g)), None)
        if destino is None:
            grupos.append([u])
        else:
            destino.append(u)
    return grupos


def _verifica_con(repo: Path, suite: str, parches: list[bytes], pruebas: list[str], plazo: int, res: dict) -> dict:
    """Corre la suite con los parches aplicados; anota las pruebas que salen entre las fallas y devuelve
    {prueba: motivo} de las que no."""
    try:
        rc, salida = con_mutaciones(repo, parches, suite, plazo)
    except (OSError, Falla) as e:
        return {x: f"{e}; repite «rojo» con una mutación nueva" for x in pruebas}
    res["corridas"] += 1
    salida = depurar(salida)
    faltan = {}
    for x in pruebas:
        if rc != 0 and fallas(salida) and falla_la_prueba(x, salida):
            res["verificados"].append(x)
        else:
            faltan[x] = _motivo_fuera(rc, salida)
    return faltan


def _parches_unicos(d: Path, repo: Path, pruebas: list[dict], res: dict) -> list[dict]:
    """Un parche por contenido, con sus archivos mutados y las pruebas que lo usan (dos casos pueden compartirlo)."""
    unicos: dict[str, dict] = {}
    for p in pruebas:
        try:
            parche = (d / "rojos" / f"{p['caso']}.patch").read_bytes()
            mutados = p.get("mutados") or _archivos_del_parche(repo, parche)
        except (OSError, Falla) as e:
            res["fuera"].append(p["prueba"])
            res["motivos"][p["prueba"]] = f"{e}; repite «rojo» con una mutación nueva"
            continue
        u = unicos.setdefault(hashlib.sha256(parche).hexdigest(), {"parche": parche, "mutados": mutados, "casos": [],
                                                                    "pruebas": []})
        u["casos"].append(p["caso"])
        u["pruebas"].append(p["prueba"])
    return list(unicos.values())


def rojos_en_suite(d: Path, cfg: dict, plazo: int) -> dict:
    """Corre la suite completa con las mutaciones de los rojos aplicadas, sin cortar en el primer tramo que falle: tiene
    que salir en rojo y cada prueba declarada, entre las fallas que lista el runner. Si no, la suite no la corre (archivo
    mal nombrado, spec fuera del glob) o la mutación la corta antes (carga, recolección, fail-fast en la configuración).

    Para no correr la suite una vez por rojo, un parche repetido se aplica una vez y los que no comparten archivos van
    juntos en la misma corrida. «rojo» ya probó que cada prueba falla por su propia mutación; aquí solo se comprueba
    que la suite la corre. Si en un grupo falta alguna, su parche se repite solo: la mutación de otro pudo taparla."""
    repo, suite = Path(cfg["repo"]), suite_sin_corte(cfg["suite"])
    pruebas = (jurado.leer_json(d / "fase-3-rojos.json") or {}).get("pruebas", [])
    res = {"verificados": [], "fuera": [], "motivos": {}, "corridas": 0, "grupos": [], "huella": huella_rojos(pruebas)}
    for grupo in grupos_de_mutaciones(_parches_unicos(d, repo, pruebas, res)):
        res["grupos"].append(sorted(c for u in grupo for c in u["casos"]))
        faltan = _verifica_con(repo, suite, [u["parche"] for u in grupo], [x for u in grupo for x in u["pruebas"]],
                               plazo, res)
        for u in (grupo if len(grupo) > 1 else []):
            solas = [x for x in u["pruebas"] if faltan.pop(x, None) is not None]
            if solas:
                faltan.update(_verifica_con(repo, suite, [u["parche"]], solas, plazo, res))
        res["fuera"] += list(faltan)
        res["motivos"].update(faltan)
    return res


# ───────────────────────────── casos manuales ─────────────────────────────

def revisar_manuales(datos: dict) -> list[str]:
    """Las pruebas manuales, sus capturas y su revisión no se omiten: siempre hay al menos un caso automatizable."""
    casos = datos["casos"]
    if not any(c["automatizable"] for c in casos):
        return ["no hay casos automatizables: las pruebas manuales con captura y su revisión no se omiten; lo que no "
                "se ve en pantalla se comprueba por API o por línea de comandos (también lo que no debía cambiar)"]
    errores = _duplicados([c["id"] for c in casos])
    errores += [f"id «{c['id']}» no sigue el formato M-01" for c in casos if not ID_MANUAL.match(c["id"])]
    errores += [f"{c['id']}: sin pasos" for c in casos if not c["pasos"]]
    errores += [f"{c['id']}: no automatizable sin razón" for c in casos
                if not c["automatizable"] and not c["razon_no_automatizable"].strip()]
    return errores + _revisar_caminos([c["camino"] for c in casos], tope_feliz=1 / 2, exige=("error",))


def html_manuales(datos: dict) -> str:
    filas = "".join(
        f"<tr><td>{_e(c['id'])}</td><td>{_e(c['titulo'])}</td><td>{_e(c['perfil'])}</td><td>{_e(c['camino'])}</td>"
        f"<td>{_e(c['precondiciones'])}</td><td><ol>"
        + "".join(f"<li>{_e(p['accion'])} → <em>{_e(p['esperado'])}</em></li>" for p in c["pasos"])
        + f"</ol></td><td>{_e(c['datos'])}</td><td>"
        + ("Una herramienta (navegador, API o comando)" if c["automatizable"] else f"<span class='alerta'>Te toca a ti</span>: "
           f"{_e(c['razon_no_automatizable'])}")
        + "</td></tr>" for c in datos["casos"])
    pendientes = sum(1 for c in datos["casos"] if not c["automatizable"])
    cuerpo = (f"<p class='meta'>{len(datos['casos'])} casos · {pendientes} quedan para correr a mano · "
              f"generado {_e(jurado.ahora())}</p><p>{_e(datos['resumen'])}</p><div class='tw'><table><tr><th>ID</th>"
              "<th>Caso</th><th>Perfil</th><th>Camino</th><th>Precondiciones</th><th>Pasos → esperado</th>"
              "<th>Datos</th><th>Quién lo corre</th></tr>" + filas + "</table></div>")
    return _pagina("Pruebas manuales", cuerpo)


def cmd_manuales(a) -> int:
    datos, errores = _cargar(a.archivo, "casos_manuales")
    if datos is None:
        return _falla("; ".join(errores), rc=2)
    errores = revisar_manuales(datos)
    if a.salida:
        _escribir(Path(a.salida).expanduser(), html_manuales(datos))
    if a.dir and not errores:
        d = Path(a.dir).expanduser()
        if list(d.glob("evidencia/ronda-*")):
            raise Falla("ya hay evidencia contra manuales.json: no se vuelve a congelar; para cambiar el esperado de "
                        "un paso, «enmienda-manual» con la autorización literal de Juan")
        jurado.escribir_json(d / "manuales.json", datos)
        _sellar(d, "manuales.json")
    _imprimir({"ok": not errores, "errores": errores, "casos": len(datos["casos"]),
               "automatizables": [c["id"] for c in datos["casos"] if c["automatizable"]],
               "a_mano": [c["id"] for c in datos["casos"] if not c["automatizable"]], "html": a.salida})
    return 0 if not errores else 1


def _enmiendas(d: Path) -> list[dict]:
    return (jurado.leer_json(d / "manuales-enmiendas.json") or {}).get("enmiendas", [])


def cmd_enmienda_manual(a) -> int:
    """Cambia el esperado de un paso de un caso manual ya congelado cuando un hallazgo (de la revisión final, por
    ejemplo) cambia el comportamiento que el caso describe. Lo decide Juan: su texto literal, el motivo y el texto de
    antes y después quedan en D/manuales-enmiendas.json, y «cierre» exige citarlos en el PR."""
    d = Path(a.dir).expanduser()
    _config(d)
    datos = jurado.leer_json(_congelado(d, "manuales.json"))
    caso = next((c for c in datos["casos"] if c["id"] == a.caso), None)
    if caso is None or not 1 <= a.paso <= len(caso["pasos"]):
        raise Falla(f"no existe el paso {a.paso} del caso {a.caso} en manuales.json")
    if not all(x.strip() for x in (a.esperado, a.motivo, a.autorizacion)):
        raise Falla("--esperado, --motivo y --autorizacion no pueden ir vacíos")
    antes = caso["pasos"][a.paso - 1]["esperado"]
    caso["pasos"][a.paso - 1]["esperado"] = a.esperado
    jurado.escribir_json(d / "manuales.json", datos)
    _sellar(d, "manuales.json")
    _escribir(d / "manuales.html", html_manuales(datos))
    enmienda = {"caso": a.caso, "paso": a.paso, "antes": antes, "despues": a.esperado, "motivo": a.motivo,
                "autorizacion": a.autorizacion, "ts": jurado.ahora()}
    jurado.escribir_json(d / "manuales-enmiendas.json", {"enmiendas": _enmiendas(d) + [enmienda]})
    _imprimir({"ok": True, **enmienda})
    return 0


def _manuales(d: Path) -> dict[str, dict]:
    """Casos automatizables del manuales.json congelado, por ID."""
    datos = jurado.leer_json(_congelado(d, "manuales.json"))
    return {c["id"]: c for c in datos["casos"] if c["automatizable"]}


# ───────────────────────────── evidencia ─────────────────────────────

def cargar_evidencia(raiz: Path) -> tuple[list[dict], list[str]]:
    casos, errores = [], []
    for archivo in sorted(raiz.glob("*/pasos.json")):
        datos = jurado.leer_json(archivo)
        if not isinstance(datos, dict) or not isinstance(datos.get("pasos"), list) or not datos.get("caso"):
            errores.append(f"{archivo}: pasos.json ilegible o sin «caso»/«pasos»")
        elif datos["caso"] != archivo.parent.name:
            errores.append(f"{archivo}: dice ser «{datos['caso']}» pero está en «{archivo.parent.name}»")
        else:
            casos.append({**datos, "_dir": archivo.parent})
    if not casos and not errores:
        errores.append(f"no hay evidencia en {raiz} (se esperaba <caso>/pasos.json)")
    return casos, errores


def _trozos_png(datos: bytes):
    """(tipo, contenido) de cada trozo, con longitud y CRC verificados; ValueError si algo no cuadra."""
    i = 8
    while i < len(datos):
        if i + 12 > len(datos):
            raise ValueError("trozo truncado")
        largo, tipo = struct.unpack(">I", datos[i:i + 4])[0], datos[i + 4:i + 8]
        contenido, crc = datos[i + 8:i + 8 + largo], datos[i + 8 + largo:i + 12 + largo]
        if len(contenido) != largo or len(crc) != 4 or struct.unpack(">I", crc)[0] != zlib.crc32(tipo + contenido):
            raise ValueError(f"trozo {tipo!r} corrupto")
        yield tipo, contenido
        i += 12 + largo


def png_valido(ruta: Path) -> bool:
    """Un PNG que se puede decodificar: trozos con CRC, IHDR primero, IDAT que descomprime al tamaño esperado, IEND."""
    try:
        datos = ruta.read_bytes()
        if datos[:8] != b"\x89PNG\r\n\x1a\n":
            return False
        trozos = list(_trozos_png(datos))
        ancho, alto, bits, color, _, _, entrelazado = struct.unpack(">IIBBBBB", trozos[0][1])
        canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        crudo = zlib.decompress(b"".join(c for tipo, c in trozos if tipo == b"IDAT"))
    except (OSError, ValueError, KeyError, IndexError, struct.error, zlib.error):
        return False
    if trozos[0][0] != b"IHDR" or trozos[-1][0] != b"IEND" or not 0 < ancho <= 20_000 or not 0 < alto <= 200_000:
        return False
    esperado = alto * (1 + (ancho * canales * bits + 7) // 8)
    return entrelazado == 0 and len(crudo) == esperado


def captura_valida(dir_caso: Path, nombre) -> bool:
    if not isinstance(nombre, str) or not CAPTURA.match(nombre):
        return False
    ruta = dir_caso / nombre
    return ruta.is_file() and not ruta.is_symlink() and png_valido(ruta)


def texto_de_captura(dir_caso: Path, nombre) -> str | None:
    """Contenido de la captura de texto de un paso, o None si no hay una válida (no vacía, dentro del caso)."""
    if not isinstance(nombre, str) or not CAPTURA_TEXTO.match(nombre):
        return None
    ruta = dir_caso / nombre
    if not ruta.is_file() or ruta.is_symlink() or ruta.stat().st_size > MAX_CAPTURA_TEXTO:
        return None
    try:
        texto = ruta.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return texto if texto.strip() else None


def con_captura(paso: dict, dir_caso: Path) -> bool:
    """Cada paso deja evidencia: captura de pantalla (navegador) o de texto (API, línea de comandos), o las dos."""
    return captura_valida(dir_caso, paso.get("captura")) or texto_de_captura(dir_caso, paso.get("texto")) is not None


def reportado(caso: dict) -> str:
    return REPORTADO.get(caso.get("estado"), "sin-estado")


def _errores_de_caso(caso: dict, manual: dict | None, head: str) -> list[str]:
    pasos, c = caso.get("pasos") or [], caso["caso"]
    errores = [f"{c}: sin pasos registrados"] if not pasos else []
    if reportado(caso) == "sin-estado":
        errores.append(f"{c}: sin estado final ({caso.get('estado')})")
    errores += [f"{c} paso {p.get('n')}: sin captura válida (ni de pantalla ni de texto)" for p in pasos
                if not con_captura(p, caso["_dir"])]
    if manual:
        errores += _contra_manual(c, pasos, manual["pasos"], reportado(caso) == "pasa")
    if caso.get("head") != head:
        errores.append(f"{c}: la corrida es de otro commit ({str(caso.get('head'))[:10]})")
    if not caso.get("corrida"):
        errores.append(f"{c}: sin EVIDENCIA_CORRIDA")
    return errores


def _normal(texto) -> str:
    return " ".join(str(texto or "").casefold().split()).rstrip(" .")


def _contra_manual(caso: str, pasos: list[dict], esperados: list[dict], completo: bool) -> list[str]:
    errores = []
    if (completo and len(pasos) != len(esperados)) or len(pasos) > len(esperados):
        errores.append(f"{caso}: {len(pasos)} pasos en la evidencia y {len(esperados)} en el caso manual")
    for i, (paso, esperado) in enumerate(zip(pasos, esperados), 1):
        for campo in ("accion", "esperado"):
            if _normal(paso.get(campo)) != _normal(depurar(str(esperado[campo]))):
                errores.append(f"{caso} paso {i}: «{campo}» no es el del caso manual")
    return errores


def errores_de_evidencia(casos: list[dict], manuales: dict[str, dict], head: str) -> list[str]:
    ids = [c["caso"] for c in casos]
    errores = ([f"sin evidencia del caso automatizable {i}" for i in manuales if i not in ids]
               + [f"evidencia de {i}, que no es un caso automatizable de manuales" for i in ids if i not in manuales])
    for caso in casos:
        errores += _errores_de_caso(caso, manuales.get(caso["caso"]), head)
    if len({c.get("corrida") for c in casos}) > 1:
        errores.append("la evidencia mezcla corridas distintas: corre «prepara-evidencia» y repite la corrida completa")
    return errores + fugas(casos)


def _textos_de_caso(caso: dict):
    yield "título", str(caso.get("titulo", ""))
    for p in caso.get("pasos") or []:
        for campo in ("accion", "esperado", "error", "url"):
            yield f"paso {p.get('n')} ({campo})", str(p.get(campo) or "")
        for c in p.get("consola") or []:
            yield f"paso {p.get('n')} (consola)", str(c.get("texto", ""))
        for r in p.get("red") or []:
            yield f"paso {p.get('n')} (red)", str(r.get("url", ""))
        if "_dir" in caso and (texto := texto_de_captura(caso["_dir"], p.get("texto"))):
            yield f"paso {p.get('n')} (captura de texto)", texto


def fugas(casos: list[dict]) -> list[str]:
    return [f"posible secreto en {c['caso']} {donde}: {', '.join(tipos)}"
            for c in casos for donde, texto in _textos_de_caso(c) if (tipos := secretos_en(texto))]


def alertas_de_paso(paso: dict, dir_caso: Path) -> list[str]:
    alertas = [] if con_captura(paso, dir_caso) else ["sin captura"]
    if paso.get("resultado") == "pasa":
        if any(c.get("tipo") in ("error", "pageerror") for c in paso.get("consola") or []):
            alertas.append("pasa con errores de consola")
        if any(str(r.get("estado", "")).startswith("5") for r in paso.get("red") or []):
            alertas.append("pasa con respuestas 5xx")
    return alertas


def alertas_de_caso(caso: dict) -> list[str]:
    pasos, estado = caso.get("pasos") or [], reportado(caso)
    alertas = []
    if estado == "pasa" and any(p.get("resultado") != "pasa" for p in pasos):
        alertas.append("el caso pasa con un paso que no pasa")
    if estado == "falla" and pasos and all(p.get("resultado") == "pasa" for p in pasos):
        alertas.append("falla fuera de los pasos registrados")
    return alertas


def todas_las_alertas(caso: dict) -> list[str]:
    de_pasos = {x for p in caso.get("pasos") or [] for x in alertas_de_paso(p, caso["_dir"])}
    return alertas_de_caso(caso) + sorted(de_pasos)


def _celda_registros(registros: list[dict], campos: tuple[str, ...]) -> str:
    if not registros:
        return ""
    return "<pre>" + _e("\n".join(" ".join(str(r.get(c, "")) for c in campos) for r in registros)) + "</pre>"


def _html_paso(paso: dict, dir_caso: Path, base: Path) -> str:
    captura = ""
    if captura_valida(dir_caso, paso.get("captura")):
        rel = _e(os.path.relpath(dir_caso / paso["captura"], base))
        captura = f"<a href='{rel}'><img src='{rel}' loading='lazy' alt='Paso {_e(paso.get('n'))}'></a>"
    if (texto := texto_de_captura(dir_caso, paso.get("texto"))) is not None:
        captura += f"<pre>{_e(texto[:LIMITE_SALIDA])}</pre>"
    res = _e(paso.get("resultado"))
    return (f"<tr><td>{_e(paso.get('n'))}</td><td>{_e(paso.get('accion'))}</td><td>{_e(paso.get('esperado'))}</td>"
            f"<td><span class='{res}'>{res}</span>"
            + (f"<pre>{_e(paso.get('error'))}</pre>" if paso.get("error") else "")
            + "".join(f"<div class='alerta'>⚠ {_e(x)}</div>" for x in alertas_de_paso(paso, dir_caso))
            + f"</td><td>{_e(paso.get('url'))}</td><td>{_celda_registros(paso.get('consola') or [], ('tipo', 'texto'))}"
            f"</td><td>{_celda_registros(paso.get('red') or [], ('estado', 'metodo', 'url'))}</td><td>{captura}</td></tr>")


def _html_caso(caso: dict, base: Path) -> str:
    estado = reportado(caso)
    filas = "".join(_html_paso(p, caso["_dir"], base) for p in caso.get("pasos") or [])
    return (f"<h2 id='{_e(caso['caso'])}'>{_e(caso['caso'])} — {_e(caso.get('titulo'))} "
            f"<span class='{estado}'>({estado})</span></h2><p class='meta'>Prueba: <code>{_e(caso.get('archivo'))}"
            f"</code> · {_e(caso.get('generado'))}</p>"
            + "".join(f"<p class='alerta'>⚠ {_e(x)}</p>" for x in alertas_de_caso(caso))
            + "<div class='tw'><table><tr><th>#</th><th>Acción</th><th>Esperado</th><th>Resultado</th><th>URL</th>"
            "<th>Consola</th><th>Red (≥400 o fallida)</th><th>Captura</th></tr>" + filas + "</table></div>")


def html_evidencia(casos: list[dict], raiz: Path, anexos: list[Path], errores: list[str]) -> str:
    cuenta = Counter(reportado(c) for c in casos)
    indice = "".join(
        f"<tr><td><a href='#{_e(c['caso'])}'>{_e(c['caso'])}</a></td><td>{_e(c.get('titulo'))}</td>"
        f"<td class='{reportado(c)}'>{reportado(c)}</td><td>{len(c.get('pasos') or [])}</td>"
        f"<td>{_e('; '.join(todas_las_alertas(c)))}</td></tr>" for c in casos)
    ligas = "".join(f"<li><a href='{_e(os.path.relpath(r, raiz))}'>{_e(r.name)}</a> (depurado)</li>" for r in anexos)
    cuerpo = (f"<p class='meta'>{len(casos)} casos según <code>{_e(raiz)}</code>, al {_e(jurado.ahora())}: "
              f"{cuenta['pasa']} pasan · {cuenta['falla']} fallan · {cuenta['sin-estado']} sin estado</p>"
              + "".join(f"<p class='falla'>✗ {_e(x)}</p>" for x in errores)
              + (f"<p>Anexos:</p><ul>{ligas}</ul>" if ligas else "")
              + "<div class='tw'><table><tr><th>Caso</th><th>Título</th><th>Resultado</th><th>Pasos</th>"
              "<th>Alertas</th></tr>" + indice + "</table></div>"
              + "".join(_html_caso(c, raiz) for c in casos))
    return _pagina("Evidencia de pruebas en pantalla", cuerpo)


def _depurar_anexos(anexos: list[str], raiz: Path) -> tuple[list[Path], list[str]]:
    """Depura cada anexo en su lugar (dentro de la vuelta): en D no queda una copia sin depurar."""
    copias, errores, permitido = [], [], raiz.resolve()
    for ruta in anexos:
        origen = Path(ruta).expanduser().resolve()
        if permitido not in origen.parents or origen.is_symlink():
            errores.append(f"el anexo {ruta} debe ser un archivo dentro de {permitido}")
            continue
        try:
            texto = origen.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errores.append(f"no se pudo leer el anexo {ruta}: {e}")
            continue
        _escribir(origen, depurar(texto))
        copias.append(origen)
    return copias, errores


def manifiesto(raiz: Path) -> dict[str, str]:
    """sha256 de todo lo que ven los revisores de la vuelta (sin meta, cruce ni las revisiones mismas)."""
    return {str(p.relative_to(raiz)): _sha256(p) for p in sorted(raiz.rglob("*"))
            if p.is_file() and p.name not in ("meta.json", "cruce.json") and not p.name.startswith("revision-")}


def _cruce(d: Path, k: int) -> dict | None:
    return jurado.leer_json(d / "evidencia" / f"ronda-{k}" / "cruce.json")


def _fallas_seguidas(d: Path, hasta: int) -> int:
    n = 0
    for k in range(hasta, 0, -1):
        cruce = _cruce(d, k)
        if not isinstance(cruce, dict) or cruce.get("ok"):
            break
        n += 1
    return n


def _vuelta_abierta(d: Path, k: int, extra: str | None = None) -> Path:
    if k < 1:
        raise Falla("las vueltas empiezan en 1")
    if k > 1 and _cruce(d, k - 1) is None:
        raise Falla(f"la vuelta {k - 1} no se cruzó: las vueltas van en orden")
    if _cruce(d, k) is not None:
        raise Falla(f"la vuelta {k} ya se cruzó; corre una vuelta nueva")
    seguidas = _fallas_seguidas(d, k - 1)
    if seguidas >= MAX_FALLAS_EVIDENCIA:
        _autoriza_vuelta_extra(d, k, seguidas, extra)
    elif extra:
        raise Falla(f"la vuelta {k} no pasa del límite de {MAX_FALLAS_EVIDENCIA}: no lleva --vuelta-extra-autorizada")
    return d / "evidencia" / f"ronda-{k}"


def _vuelta_extra(d: Path) -> dict:
    return jurado.leer_json(d / "evidencia" / "vuelta-extra.json") or {}


def _autoriza_vuelta_extra(d: Path, k: int, seguidas: int, extra: str | None) -> None:
    """Tras MAX_FALLAS_EVIDENCIA vueltas seguidas sin aprobar se escala a Juan. Con su texto literal hay una sola
    vuelta más, sellada en D (la usan después «evidencia» y «cruza») y citada en el PR. Ya usada, solo se abre otra
    para volver a evidenciar lo que cambió después (producción, e2e, specs o una enmienda del caso)."""
    sellada = _vuelta_extra(d)
    if sellada and sellada.get("ronda") != k:
        if _cambios_desde_cruce(d, _config(d)["repo"], k - 1) or _manuales_cambiaron(d, k - 1):
            return
        raise Falla(f"ya se usó la vuelta extra y nada de producción, e2e ni manuales.json cambió desde la vuelta "
                    f"{k - 1}: no hay otra vuelta; escala a Juan (la evidencia no se omite: sin una vuelta aprobada no hay PR)")
    if seguidas > MAX_FALLAS_EVIDENCIA:
        raise Falla(f"{seguidas} vueltas seguidas sin aprobar: escala a Juan")
    if not sellada and not extra:
        raise Falla(f"{MAX_FALLAS_EVIDENCIA} vueltas seguidas sin aprobar: escala a Juan (una vuelta más exige su texto "
                    "literal en --vuelta-extra-autorizada)")
    if not sellada:
        (d / "evidencia").mkdir(exist_ok=True)
        jurado.escribir_json(d / "evidencia" / "vuelta-extra.json",
                             {"ronda": k, "autorizacion": extra, "ts": jurado.ahora()})


def cmd_prepara_evidencia(a) -> int:
    """Deja vacía la vuelta abierta antes de correr la evidencia: lo de un intento anterior (un caso que ya no existe,
    pasos viejos, el log del servidor) no se mezcla con la corrida nueva. Una vuelta ya cruzada no se toca."""
    d = Path(a.dir).expanduser()
    _config(d)
    raiz = _vuelta_abierta(d, a.ronda, a.vuelta_extra_autorizada)
    if any(x.is_symlink() for x in (d / "evidencia", raiz)):
        raise Falla(f"{raiz} o su carpeta es un enlace simbólico: no se borra")
    if raiz.exists():
        shutil.rmtree(raiz)
    raiz.mkdir(parents=True)
    _imprimir({"ok": True, "ronda": a.ronda, "dir": str(raiz)})
    return 0


def cmd_evidencia(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    raiz = _vuelta_abierta(d, a.ronda, a.vuelta_extra_autorizada)
    _exige_limpio(cfg["repo"])
    manuales, head = _manuales(d), _head(cfg["repo"])
    casos, errores = cargar_evidencia(raiz)
    if not casos:
        return _falla("; ".join(errores), rc=2)
    anexos, e_anexos = _depurar_anexos(a.anexo, raiz)
    errores += errores_de_evidencia(casos, manuales, head) + e_anexos
    _escribir(raiz / "index.html", html_evidencia(casos, raiz, anexos, errores))
    nonce, lista = secrets.token_hex(6), manifiesto(raiz)
    huella = hashlib.sha256(json.dumps(lista, sort_keys=True).encode()).hexdigest()
    identificador = f"vuelta {a.ronda} · {nonce} · {head[:12]} · {huella[:12]}"
    heredados = _heredables(d, cfg["repo"], a.ronda, casos, manuales)
    jurado.escribir_json(raiz / "meta.json", {"head": head, "corrida": casos[0].get("corrida"), "errores": errores,
                                              "esperados": sorted(manuales), "identificador": identificador,
                                              "manuales_sha256": _sha256(d / "manuales.json"),
                                              "casos_sha256": {i: _sha_caso(c) for i, c in manuales.items()},
                                              "heredados": heredados, "manifiesto": lista, "ts": jurado.ahora()})
    _imprimir({"ok": not errores, "errores": errores, "html": str(raiz / "index.html"), "identificador": identificador,
               "casos": {c["caso"]: reportado(c) for c in casos}, "heredados": heredados,
               "revisar": sorted(c["caso"] for c in casos if c["caso"] not in heredados),
               "alertas": {c["caso"]: todas_las_alertas(c) for c in casos if todas_las_alertas(c)}})
    return 0 if not errores else 1


def _sha_caso(caso: dict | None) -> str:
    return hashlib.sha256(json.dumps(caso, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _heredables(d: Path, repo, k: int, casos: list[dict], manuales: dict) -> list[str]:
    """Casos que no hace falta volver a revisar en la vuelta k: los dos revisores los confirmaron en la vuelta k-1, su
    prueba pasa y no cambió su caso manual. Desde entonces solo pudieron cambiar la documentación y los archivos de las
    pruebas de evidencia, y no el de este caso; si cambió producción, un helper o la configuración, se revisa todo."""
    previa = _cruce(d, k - 1) if k > 1 else None
    meta = jurado.leer_json(d / "evidencia" / f"ronda-{k - 1}" / "meta.json") or {}
    if not isinstance(previa, dict) or not meta.get("casos_sha256"):
        return []
    specs = {str(c.get("archivo")) for c in casos if c.get("archivo")}
    cambiados = set(_cambiados(repo, previa["head"]))
    if any(not DOCUMENTACION.search(r) and r not in specs for r in cambiados):
        return []
    return sorted(c["caso"] for c in casos if c["caso"] in previa.get("confirmados", []) and reportado(c) == "pasa"
                  and str(c.get("archivo")) not in cambiados
                  and meta["casos_sha256"].get(c["caso"]) == _sha_caso(manuales.get(c["caso"])))


# ───────────────────────────── cruce de revisiones de evidencia ─────────────────────────────

def _por_caso(revision: dict, juez: str) -> dict:
    repetidos = _duplicados([c["caso"] for c in revision["casos"]])
    if repetidos:
        raise Falla(f"la revisión de {juez} repite casos: {'; '.join(repetidos)}", rc=2)
    return {c["caso"]: c for c in revision["casos"]}


def _solo_una_debil(dictamenes: dict) -> bool:
    """Un revisor dice «asercion-debil» y el otro «correcto»: no bloquea, queda como nota para el PR. Bloquean la
    misma marca de los dos y cualquier otro dictamen (falso positivo o negativo, inconcluso)."""
    valores = sorted(d["dictamen"] for d in dictamenes.values())
    return valores == ["asercion-debil", "correcto"]


def _juicio(estado: str, dictamenes: dict) -> list[str]:
    """Motivos para no confirmar un caso; vacío si se confirma."""
    motivos = [f"{j} dice que reportó «{d['reportado']}», pero la evidencia dice «{estado}»"
               for j, d in dictamenes.items() if d["reportado"] != estado]
    if not _solo_una_debil(dictamenes):
        motivos += [f"{j}: {d['dictamen']}" for j, d in dictamenes.items() if d["dictamen"] != "correcto"]
    if estado != "pasa":
        motivos.append(f"la prueba no pasa ({estado}): un spec en rojo no entra a la suite")
    return motivos


def _heredado(caso: str, estado: str) -> dict:
    return {"caso": caso, "reportado": estado, "dictamen": "correcto", "paso": "", "correccion": "",
            "porque": "confirmado en la vuelta anterior; no cambió su prueba, su caso ni el código"}


def cruzar(codex: dict, claude: dict, estados: dict[str, str], heredados: set[str] = frozenset()) -> dict:
    """Un caso se confirma si su prueba pasa y los dos revisores dicen «correcto» (o uno «correcto» y el otro
    «asercion-debil», que va a `notas`). Un caso heredado que un revisor no dictaminó cuenta como «correcto» de ese
    revisor."""
    por = {"codex": _por_caso(codex, "codex"), "claude": _por_caso(claude, "claude")}
    res = {"confirmados": [], "corregir": [], "discrepancias": [], "sin_revisar": [], "ajenos": [], "notas": [],
           "heredados": []}
    for caso in sorted(set(estados) | set(por["codex"]) | set(por["claude"])):
        dictamenes = {j: por[j][caso] for j in por if caso in por[j]}
        if caso not in estados:
            res["ajenos"].append(caso)
            continue
        if caso in heredados and len(dictamenes) < 2:
            dictamenes = {j: dictamenes.get(j) or _heredado(caso, estados[caso]) for j in por}
            res["heredados"].append(caso)
        if len(dictamenes) < 2:
            res["sin_revisar"].append({"caso": caso, "falta": [j for j in por if j not in dictamenes]})
            continue
        motivos = _juicio(estados[caso], dictamenes)
        if motivos:
            res["corregir"].append({"caso": caso, "motivos": motivos, **dictamenes})
        else:
            res["confirmados"].append(caso)
            if _solo_una_debil(dictamenes):
                res["notas"].append({"caso": caso, **{j: d for j, d in dictamenes.items() if d["dictamen"] != "correcto"}})
        if len({d["dictamen"] for d in dictamenes.values()}) > 1:
            res["discrepancias"].append(caso)
    res["ok"] = not (res["corregir"] or res["sin_revisar"] or res["ajenos"])
    return res


def _meta_vigente(d: Path, raiz: Path, repo) -> dict:
    meta = jurado.leer_json(raiz / "meta.json")
    if not isinstance(meta, dict):
        raise Falla("corre «evidencia» antes de «cruza»")
    if meta.get("errores"):
        raise Falla("la evidencia de esta vuelta tiene errores: corrígelos y vuelve a correr «evidencia»")
    _exige_limpio(repo)
    if meta.get("head") != _head(repo):
        raise Falla("el HEAD cambió desde que se armó la evidencia: corre una vuelta nueva")
    if meta.get("manuales_sha256") != _sha256(_congelado(d, "manuales.json")):
        raise Falla("manuales.json cambió desde que se armó la evidencia")
    if manifiesto(raiz) != meta.get("manifiesto"):
        raise Falla("la evidencia cambió después de armarla (capturas, pasos o anexos): vuelve a correr «evidencia»")
    return meta


def _revision_de_la_vuelta(ruta, identificador: str, juez: str) -> tuple[dict | None, list[str]]:
    datos, errores = _cargar(ruta, "revision_evidencia")
    if datos is not None and datos["identificador"] != identificador:
        return None, [f"la revisión de {juez} es de otra vuelta o de otra evidencia ({datos['identificador']} ≠ "
                      f"{identificador})"]
    return datos, errores


def cmd_cruza(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    raiz = _vuelta_abierta(d, a.ronda)
    meta = _meta_vigente(d, raiz, cfg["repo"])
    codex, e1 = _revision_de_la_vuelta(a.codex, meta["identificador"], "codex")
    claude, e2 = _revision_de_la_vuelta(a.claude, meta["identificador"], "claude")
    casos, e3 = cargar_evidencia(raiz)
    if codex is None or claude is None or e3 or not casos:
        return _falla("; ".join(e1 + e2 + e3) or "sin evidencia", rc=2)
    res = cruzar(codex, claude, {c["caso"]: reportado(c) for c in casos}, set(meta.get("heredados", [])))
    if res["sin_revisar"] or res["ajenos"]:
        # Falla de formato del revisor, no de la app: no gasta la vuelta; se le pide de nuevo.
        return _falla(f"revisión incompleta: sin revisar {res['sin_revisar']}, ajenos {res['ajenos']}; pídela de "
                      "nuevo al revisor que falló", rc=2)
    res["sin_evidencia"] = [i for i in meta["esperados"] if i not in {c["caso"] for c in casos}]
    res["ok"] = res["ok"] and not res["sin_evidencia"]
    res.update({"head": meta["head"], "ronda": a.ronda, "ts": jurado.ahora()})
    jurado.escribir_json(raiz / "cruce.json", res)
    if not res["ok"] and _fallas_seguidas(d, a.ronda) >= MAX_FALLAS_EVIDENCIA:
        res["accion"] = "escalar"
    _imprimir(res)
    return 0 if res["ok"] else 1


# ───────────────────────────── rondas de la revisión final ─────────────────────────────

def _rondas_abiertas(d: Path) -> int:
    return max((int(p.parent.name.split("-")[1]) for p in d.glob("ronda-*/estado.json")), default=0)


def _estado_ronda(d: Path, n: int) -> dict:
    estado = jurado.leer_json(d / f"ronda-{n}" / "estado.json")
    if not isinstance(estado, dict):
        raise Falla(f"la ronda {n} no está abierta; corre «abre-ronda»")
    return estado


def _vigente(cfg: dict, estado: dict) -> list[str]:
    """La ronda solo vale para el árbol que se congeló al abrirla."""
    motivos = [f"cambios sin commit: {'; '.join(_sucio(cfg['repo'])[:5])}"] if _sucio(cfg["repo"]) else []
    if _head(cfg["repo"]) != estado["head"]:
        motivos.append(f"el HEAD cambió desde que se abrió la ronda ({estado['head'][:10]} → {_head(cfg['repo'])[:10]})")
    return motivos


def _revisar_apertura(d: Path, cfg: dict, n: int, extra: str | None = None) -> None:
    """La siguiente ronda se abre si la anterior pidió corregir. Pasado el máximo hay una sola ronda más, con el texto
    literal de Juan (--ronda-extra-autorizada), que se aprueba si ningún revisor trae hallazgos graves."""
    if n > cfg["max_rondas"] + 1 or (n > cfg["max_rondas"] and not extra):
        raise Falla(f"ya se usaron las {cfg['max_rondas']} rondas: escala a Juan"
                    + ("" if n > cfg["max_rondas"] + 1 else " (una ronda más exige su texto literal en "
                                                              "--ronda-extra-autorizada)"))
    if extra and n <= cfg["max_rondas"]:
        raise Falla(f"la ronda {n} no pasa del máximo de {cfg['max_rondas']}: no lleva --ronda-extra-autorizada")
    if n == 1:
        return
    previa = siguiente(d)
    if previa["accion"] != ("escalar" if extra else "corregir"):
        raise Falla(f"la ronda {n - 1} no terminó en «corregir» ({previa['accion']}): no se abre otra")
    respuesta = d / f"ronda-{n - 1}" / "respuesta.md"
    sin_respuesta = not respuesta.is_file() or not respuesta.read_text(encoding="utf-8").strip()
    if _head(cfg["repo"]) == _estado_ronda(d, n - 1)["head"] and sin_respuesta:
        raise Falla(f"nada cambió desde la ronda {n - 1}: corrige con un commit o contesta con evidencia en "
                    f"ronda-{n - 1}/respuesta.md")


def cmd_abre_ronda(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    n = _rondas_abiertas(d) + 1
    _revisar_apertura(d, cfg, n, a.ronda_extra_autorizada)
    _exige_limpio(cfg["repo"])
    diff, omitidos = diff_para_revisores(cfg["repo"], cfg["base"])
    if omitidos and not a.omitidos_autorizados:
        raise Falla(f"el cambio toca archivos con nombre de secreto que los revisores no verán ({', '.join(omitidos)}): "
                    "pregunta a Juan y pasa su respuesta literal con --omitidos-autorizados")
    dir_ronda = d / f"ronda-{n}"
    _escribir(dir_ronda / "cambios.diff", diff)
    _escribir(dir_ronda / "commits.txt", depurar(_git(cfg["repo"], "log", "--format=%h %s%n%b", f"{cfg['base']}..HEAD").stdout))
    head, sha, nonce = _head(cfg["repo"]), _sha256(dir_ronda / "cambios.diff"), secrets.token_hex(6)
    estado = {"ronda": n, "head": head, "diff_sha256": sha, "nonce": nonce,
              "identificador": f"ronda {n} · {nonce} · {head[:12]} · {sha[:12]}", "omitidos": omitidos,
              "omitidos_autorizados": a.omitidos_autorizados if omitidos else None,
              "ronda_extra_autorizada": a.ronda_extra_autorizada, "abierta": jurado.ahora()}
    jurado.escribir_json(dir_ronda / "estado.json", estado)
    _imprimir({**estado, "diff": str(dir_ronda / "cambios.diff")})
    return 0


def cmd_registra(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    if a.juez not in cfg["jueces"]:
        raise Falla(f"juez «{a.juez}» fuera de {cfg['jueces']}")
    if a.ronda != _rondas_abiertas(d):
        raise Falla(f"la ronda en curso es la {_rondas_abiertas(d)}, no la {a.ronda}")
    dir_ronda = d / f"ronda-{a.ronda}"
    motivos = _vigente(cfg, _estado_ronda(d, a.ronda))
    if motivos:
        raise Falla("el veredicto ya no aplica: " + "; ".join(motivos))
    destino = dir_ronda / f"revision-{a.juez}.json"
    if destino.exists():
        raise Falla(f"ya hay veredicto de {a.juez} en la ronda {a.ronda}; no se sobrescribe")
    texto, identificador = _leer(a.archivo), _estado_ronda(d, a.ronda)["identificador"]
    estado, datos, errores = jurado.cargar_veredicto(texto)
    if estado == "ok" and not str(datos.get("resumen", "")).startswith(identificador):
        raise Falla(f"el «resumen» del veredicto no empieza con el identificador de la ronda ({identificador}): "
                    "¿es de otra ronda o de otro diff? Pide al revisor que lo rehaga", rc=2)
    if estado != "ok":
        k = len(list(dir_ronda.glob(f"invalido-{a.juez}-*.json"))) + 1
        jurado.escribir_json(dir_ronda / f"invalido-{a.juez}-{k}.json",
                             {"estado": estado, "errores": errores, "texto": texto[:4000], "ts": jurado.ahora()})
        return _falla(f"veredicto de {a.juez} {estado}: {'; '.join(errores)}", rc=2)
    jurado.escribir_json(destino, {**datos, "_head": _head(cfg["repo"]), "_registrado": jurado.ahora()})
    sellos = jurado.leer_json(dir_ronda / "sellos.json") or {}
    jurado.escribir_json(dir_ronda / "sellos.json", {**sellos, a.juez: _sha256(destino)})
    _imprimir({"ok": True, "archivo": str(destino)})
    return 0


def _integridad(dir_ronda: Path, jueces: list[str], estado: dict) -> list[str]:
    """Veredictos que no pasaron por «registra», de otro HEAD, o un diff que cambió después de abrir."""
    sellos = jurado.leer_json(dir_ronda / "sellos.json") or {}
    motivos = [] if _sha256(dir_ronda / "cambios.diff") == estado.get("diff_sha256") else ["el diff de la ronda cambió"]
    for juez in jueces:
        ruta = dir_ronda / f"revision-{juez}.json"
        v = jurado.leer_json(ruta) or {}
        if sellos.get(juez) != _sha256(ruta):
            motivos.append(f"{juez}: veredicto que no pasó por «registra» o que cambió después")
        elif v.get("_head") != estado["head"]:
            motivos.append(f"{juez}: veredicto de otro HEAD")
        elif jurado.validar_esquema({k: x for k, x in v.items() if not k.startswith("_")}, _esquema("veredicto")):
            motivos.append(f"{juez}: veredicto fuera de esquema")
    return motivos


def _hallazgos(dir_ronda: Path, jueces: list[str], gravedad: str) -> list[dict]:
    return [{"juez": juez, **h} for juez in jueces
            for h in (jurado.leer_json(dir_ronda / f"revision-{juez}.json") or {}).get("hallazgos", [])
            if h.get("gravedad") == gravedad]


def _motivos(dir_ronda: Path, jueces: list[str]) -> list[str]:
    motivos = []
    for juez in jueces:
        v = jurado.leer_json(dir_ronda / f"revision-{juez}.json") or {}
        if v.get("veredicto") != "pasa":
            motivos.append(f"{juez}: {v.get('veredicto')}")
        abiertos = [h for h in v.get("hallazgos", []) if h.get("gravedad") in ("grave", "medio")]
        if abiertos:
            motivos.append(f"{juez}: {len(abiertos)} hallazgos grave/medio abiertos")
    return motivos


def siguiente(d: Path) -> dict:
    cfg = _config(d)
    n = _rondas_abiertas(d)
    if n == 0:
        return {"accion": "abrir-ronda", "ronda": 1}
    estado, dir_ronda = _estado_ronda(d, n), d / f"ronda-{n}"
    vigencia = _vigente(cfg, estado)
    faltan = [j for j in cfg["jueces"] if not (dir_ronda / f"revision-{j}.json").is_file()]
    if faltan:
        if vigencia:
            return {"accion": "escalar", "ronda": n, "motivos": ["el árbol cambió a media ronda: " + "; ".join(vigencia)]}
        return {"accion": "revisar", "ronda": n, "faltan": faltan}
    integridad = _integridad(dir_ronda, cfg["jueces"], estado)
    if integridad:
        return {"accion": "escalar", "ronda": n, "motivos": integridad}
    motivos = _motivos(dir_ronda, cfg["jueces"])
    if not motivos and not vigencia:
        return {"accion": "aprobado", "ronda": n, "head": estado["head"]}
    if n > cfg["max_rondas"] and not vigencia and not _hallazgos(dir_ronda, cfg["jueces"], "grave"):
        # La ronda extra que autorizó Juan termina sin graves: se da por terminada y los medios quedan en el PR.
        return {"accion": "aprobado", "ronda": n, "head": estado["head"],
                "abiertos": _hallazgos(dir_ronda, cfg["jueces"], "medio")}
    if not motivos:
        motivos = ["aprobado sobre otro árbol: " + "; ".join(vigencia)]
    if n >= cfg["max_rondas"]:
        return {"accion": "escalar", "ronda": n, "motivos": motivos}
    return {"accion": "corregir", "ronda": n, "siguiente_ronda": n + 1, "motivos": motivos}


def cmd_siguiente(a) -> int:
    res = siguiente(Path(a.dir).expanduser())
    _imprimir(res)
    return 0 if res["accion"] == "aprobado" else 1


# ───────────────────────────── copia limpia para los revisores ─────────────────────────────

def es_nombre_secreto(ruta: str) -> bool:
    return any(fnmatch(parte.lower(), patron) for parte in Path(ruta).parts for patron in NOMBRES_SECRETOS)


def diff_para_revisores(repo, base: str) -> tuple[str, list[str]]:
    """Diff base..HEAD sin archivos con nombre de secreto (regla de Juan), y la lista de los que se omitieron."""
    nombres = [r for r in _git(repo, "diff", "--name-only", "-z", base, "HEAD").stdout.split("\0") if r]
    omitidos = sorted(r for r in nombres if es_nombre_secreto(r))
    exclusiones = [f":(exclude,glob,icase){forma}" for patron in NOMBRES_SECRETOS
                   for forma in (f"**/{patron}", f"**/{patron}/**")]
    texto = _git(repo, "diff", "--binary", base, "HEAD", "--", ".", *exclusiones).stdout
    filtrados = [o for o in omitidos if f" b/{o}\n" in texto or f" a/{o} " in texto]
    if filtrados:
        raise Falla(f"el filtro del diff dejó pasar archivos con nombre de secreto: {filtrados}")
    return texto, omitidos


def _filtro_seguro(omitidos: list[str]):
    def filtro(miembro, destino):
        try:
            return tarfile.data_filter(miembro, destino)
        except tarfile.FilterError:
            omitidos.append(miembro.name)
            return None
    return filtro


def armar_copia(d: Path, cfg: dict) -> dict:
    """HEAD sin archivos sin rastrear ni con nombre de secreto: lo único que ven Codex y el revisor Claude."""
    _exige_limpio(cfg["repo"])
    head = _head(cfg["repo"])
    destino, enlaces = d / "copias" / head[:12], []
    if not destino.is_dir():
        archivo = subprocess.run(["git", "-C", cfg["repo"], "archive", "--format=tar", "HEAD"], capture_output=True,
                                 check=False)
        if archivo.returncode != 0:
            raise Falla(f"git archive falló: {archivo.stderr.decode(errors='replace')[:300]}")
        temporal = destino.with_name(f".{destino.name}.tmp")
        shutil.rmtree(temporal, ignore_errors=True)
        temporal.mkdir(parents=True)
        try:
            with tarfile.open(fileobj=io.BytesIO(archivo.stdout)) as tar:
                miembros = [m for m in tar.getmembers() if not es_nombre_secreto(m.name)]
                tar.extractall(temporal, members=miembros, filter=_filtro_seguro(enlaces))
            temporal.rename(destino)
        except (OSError, tarfile.TarError) as e:
            raise Falla(f"no se pudo armar la copia: {e}")
        finally:
            shutil.rmtree(temporal, ignore_errors=True)
    diff, omitidos = diff_para_revisores(cfg["repo"], cfg["base"])
    _escribir(destino.with_suffix(".diff"), diff)
    return {"ok": True, "copia": str(destino), "diff": str(destino.with_suffix(".diff")), "head": head,
            "omitidos": omitidos, "enlaces_omitidos": enlaces}


def cmd_copia(a) -> int:
    d = Path(a.dir).expanduser()
    _imprimir(armar_copia(d, _config(d)))
    return 0


CREDENCIALES = (".ssh", ".aws", ".config/gh", ".config/gcloud", ".docker", ".gnupg", ".kube", ".netrc", ".pgpass",
                ".npmrc", ".git-credentials")
# Codex sin configuración del usuario, sin instrucciones del repo (AGENTS.md), sin sesión guardada, sin plugins, apps,
# hooks, navegador ni búsqueda web: solo lee la copia y responde el esquema.
CODEX_AISLADO = ("--ephemeral", "--ignore-user-config", "--ignore-rules", "-c", "project_doc_max_bytes=0",
                 "-c", 'web_search="disabled"', *[x for f in ("plugins", "apps", "hooks", "browser_use", "computer_use",
                                                              "image_generation", "multi_agent", "skill_search")
                                                   for x in ("--disable", f)])


def _sbpl(ruta) -> str:
    return json.dumps(str(Path(ruta).resolve()))


def _raiz_en_casa(ejecutable: str | None) -> Path | None:
    """~/.nvm para ~/.nvm/versions/node/vX/bin/node: lo que hay que dejar leer para que el ejecutable arranque."""
    ruta = shutil.which(ejecutable) if ejecutable else None
    casa = Path.home().resolve()
    try:
        return casa / Path(os.path.realpath(ruta)).relative_to(casa).parts[0] if ruta else None
    except (ValueError, IndexError):
        return None


def perfil_codex(repo, salida: Path, legibles: list[Path]) -> str:
    """Sandbox de macOS para una corrida de Codex. Dentro de $HOME solo lee lo que está en «legibles» (D, los esquemas,
    ~/.codex y la instalación de Codex y Node); nunca el repo vivo, credenciales ni archivos con nombre de secreto bajo
    $HOME (la biblioteca estándar de Python, con token.py y secrets.py, vive fuera). Solo escribe en su salida y en
    temporales. Codex corre sin su propio sandbox porque el de macOS no se anida cuando el exterior niega algo."""
    casa = Path.home().resolve()
    letras = lambda palabra: "".join(f"[{c.upper()}{c.lower()}]" if c.isalpha() else c for c in palabra)
    nombres = " ".join(f'(regex #"^{casa}/(.*/)?[^/]*{letras(n)}[^/]*$")' for n in ("secret", "password", "token", "api_key"))
    return ("(version 1)\n(allow default)\n(deny file-write*)\n"
            f"(allow file-write* (subpath \"/private/var/folders\") (subpath \"/private/tmp\") (subpath \"/dev\") "
            f"(subpath {_sbpl(casa / '.codex')}) (subpath {_sbpl(salida)}))\n"
            f"(deny file-read-data (subpath {_sbpl(casa)}))\n"
            f"(allow file-read-data {' '.join(f'(subpath {_sbpl(x)})' for x in [casa / '.codex', *legibles])})\n"
            f"(deny file-read* (subpath {_sbpl(repo)}) {' '.join(f'(subpath {_sbpl(casa / c)})' for c in CREDENCIALES)})\n"
            f'(deny file-read* (regex #"/\\.env(\\.[^/]*)?$") (regex #"/credentials\\.json$") {nombres})\n')


def _correr_revisor(comando: list[str], prompt: str, cwd: str, plazo: int) -> tuple[int, str, str]:
    try:
        r = subprocess.run(comando, input=prompt, capture_output=True, text=True, timeout=plazo, check=False, cwd=cwd)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"tiempo agotado tras {plazo} s"


FORMATOS = {"codex": "Responde solo con el JSON que cumpla este esquema, sin campos de más ni de menos:",
            "claude": "Termina tu respuesta con UN solo bloque ```json que cumpla este esquema, sin campos de más ni "
                      "de menos. Nada después del bloque:"}


def prompt_con_esquema(prompt: str, esquema: str, revisor: str) -> str:
    """El esquema va dentro del prompt: los revisores corren encerrados y no pueden leer ~/.claude/schemas."""
    texto = json.dumps(_esquema(esquema), ensure_ascii=False, indent=1)
    return f"{prompt.rstrip()}\n\n## Formato de salida\n{FORMATOS[revisor]}\n```\n{texto}\n```\n"


def _guardar_prompt(a, revisor: str) -> tuple[Path, str]:
    """Deja el prompt completo (con el esquema) junto a la salida: <salida>.prompt.md."""
    destino = Path(a.salida).expanduser()
    prompt = prompt_con_esquema(_leer(a.prompt), a.esquema, revisor)
    _escribir(destino.with_name(f"{destino.stem}.prompt.md"), prompt)
    return destino, prompt


def cmd_codex(a) -> int:
    """Codex (gpt-6.1-sol, fijo) sobre la copia, dentro del sandbox; su respuesta queda en --salida."""
    d = Path(a.dir)
    cfg = _config(d)
    if not shutil.which("sandbox-exec"):
        raise Falla("no hay sandbox-exec: sin aislamiento no se lanza a Codex; escala a Juan")
    copia = armar_copia(d, cfg)
    destino, prompt = _guardar_prompt(a, "codex")
    (d / "codex").mkdir(exist_ok=True)
    trabajo = Path(tempfile.mkdtemp(prefix=f"{dt.datetime.now():%Y%m%d-%H%M%S}-{a.esquema}-", dir=d / "codex"))
    legibles = [d, ESQUEMAS, *filter(None, (_raiz_en_casa(jurado.codex_bin()), _raiz_en_casa("node")))]
    _escribir(trabajo / "perfil.sb", perfil_codex(cfg["repo"], trabajo, legibles))
    comando = ["sandbox-exec", "-f", str(trabajo / "perfil.sb"), jurado.codex_bin(), "exec", *CODEX_AISLADO,
               "--model", "gpt-6.1-sol", "-c", f'model_reasoning_effort="{a.esfuerzo}"', "-s", "danger-full-access",
               "--skip-git-repo-check", "-C", copia["copia"], "--output-schema", str(ESQUEMAS / f"{a.esquema}.json"),
               "-o", str(trabajo / "salida.json"), "-"]
    rc, salida, error = _correr_revisor(comando, prompt, copia["copia"], a.plazo)
    _escribir(trabajo / "codex.log", depurar(salida + error))
    if rc != 0 or not (trabajo / "salida.json").is_file():
        raise Falla(f"Codex falló (rc {rc}); log en {trabajo / 'codex.log'}. Reintenta una vez; si vuelve a fallar, "
                    "detente")
    shutil.copyfile(trabajo / "salida.json", destino)
    _imprimir({"ok": True, "salida": str(destino), "copia": copia["copia"], "log": str(trabajo / "codex.log")})
    return 0


def cmd_claude(a) -> int:
    """El revisor Claude sin sesión guardada ni personalizaciones (CLAUDE.md, skills, hooks, MCP), con solo
    Read/Grep/Glob y encerradas en la copia y en D; su respuesta completa queda en --salida."""
    d = Path(a.dir)
    cfg = _config(d)
    copia = armar_copia(d, cfg)
    destino, prompt = _guardar_prompt(a, "claude")
    comando = [os.environ.get("CLAUDE_BIN", "claude"), "-p", "--model", a.modelo or cfg.get("sesion", "opus"),
               "--restricted", "--safe-mode", "--strict-mcp-config", "--no-session-persistence",
               "--tools", "Read,Grep,Glob", "--add-dir", str(d)]
    rc, salida, error = _correr_revisor(comando, prompt, copia["copia"], a.plazo)
    if rc != 0 or not salida.strip():
        raise Falla(f"el revisor Claude falló (rc {rc}): {depurar(error)[-500:]}. Reintenta una vez; si vuelve a "
                    "fallar, detente")
    _escribir(destino, salida)
    _imprimir({"ok": True, "salida": str(destino), "copia": copia["copia"]})
    return 0


# ───────────────────────────── plan de verificación y validación aislada ─────────────────────────────

def _seccion_md(texto: str) -> str | None:
    """Cuerpo de la sección «Verificación» de un plan Markdown (los # dentro de bloques ``` no cortan)."""
    lineas, dentro, en_bloque = [], False, False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_bloque = not en_bloque
        elif not en_bloque and re.match(r"#{1,6}\s", linea):
            if dentro:
                break
            dentro = "verificacion" in jurado.sin_acentos(linea)
            continue
        if dentro:
            lineas.append(linea)
    return "\n".join(lineas) if dentro else None


def _esperados_md(texto: str) -> tuple[list[str], list[str]]:
    seccion = _seccion_md(texto)
    if seccion is None:
        return [], []
    for bloque in re.findall(r"^\s*```[^\n]*\n(.*?)^\s*```", seccion, re.S | re.M):
        lineas = jurado._lineas_automatica(bloque)
        if lineas is not None:
            comandos = jurado._unir_comandos(lineas)
            return comandos, [] if comandos else ["el bloque «# Automática» del plan está vacío"]
    return [], ["el plan tiene sección Verificación pero ningún bloque ``` con «# Automática»"]


def esperados_del_plan(texto: str, es_html: bool) -> tuple[list[str], list[str]]:
    """(comandos, errores) del bloque «# Automática»; si el plan declara Verificación, tiene que poder leerse."""
    if not es_html:
        return _esperados_md(texto)
    if not re.search(r"<h[1-6][^>]*>[^<]*Verificaci[oó]n", texto, re.I):
        return [], []
    return jurado.extraer_esperados(texto)


def _ruta_absoluta(token: str) -> str | None:
    token = re.sub(r"^\d*[<>]+&?", "", token)
    ruta = token.split("=", 1)[1] if "=" in token else token
    return ruta if ruta.startswith(("/", "~")) and ruta not in RUTAS_PERMITIDAS else None


def _operadores(comando: str) -> list[str]:
    lexico = shlex.shlex(comando, posix=True, punctuation_chars=True)
    lexico.whitespace_split = True
    return [t for t in lexico if t in ("||", ";", "|", "&", "|&")]


def revisar_comando(comando: str) -> list[str]:
    try:
        tokens, operadores = shlex.split(comando), _operadores(comando)
    except ValueError as e:
        return [f"comando ilegible «{comando}»: {e}"]
    errores = [f"comando trivial: «{comando}»"] if TRIVIAL.match(comando) else []
    errores += [f"«{op}» en «{comando}» puede esconder que falló: une comandos solo con «&&»" for op in operadores]
    return errores + [f"ruta absoluta «{r}» en «{comando}»" for t in tokens if (r := _ruta_absoluta(t))]


def armar_verificacion(plan_texto: str, es_html: bool, cfg: dict, nuevos: list[str],
                       ilegible: str | None) -> tuple[str, list[str]]:
    previos, errores = esperados_del_plan(plan_texto, es_html)
    if ilegible:
        previos, errores = [], [] if any(c.strip() for c in nuevos) else [
            "con --plan-ilegible pasa con --comando los comandos del plan que sí se pueden correr"]
    comandos = list(dict.fromkeys(previos + [cfg["suite"]] + [" ".join(c.split()) for c in nuevos if c.strip()]))
    for comando in comandos:
        errores += revisar_comando(comando)
    nombre = Path(cfg["plan"]).stem
    cuerpo = (f"<p>Base: <code>{_e(cfg['base'])}</code> (rama <code>{_e(cfg['rama_base'])}</code>) · Raíces: "
              f"<code>.</code> · Plan: <code>{_e(cfg['plan'])}</code></p><h2>Verificación</h2><pre><code># Automática\n"
              + "\n".join(_e(c) for c in comandos)
              + "\n# Manual\nRevisar la evidencia en pantalla y las pruebas que quedaron a mano.</code></pre>")
    return _pagina(f"Verificación — {nombre}", cuerpo), errores


def cmd_verificacion(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    plan = Path(cfg["plan"])
    try:
        plan_texto = plan.read_text(encoding="utf-8")
    except OSError as e:
        raise Falla(f"no se pudo leer el plan {plan}: {e}")
    texto, errores = armar_verificacion(plan_texto, plan.suffix.lower() in (".html", ".htm"), cfg, a.comando,
                                        a.plan_ilegible)
    if errores:
        return _falla("; ".join(errores))
    _exige_limpio(cfg["repo"])
    salida = d / "verificacion.html"
    _escribir(salida, texto)
    comandos = jurado.extraer_esperados(texto)[0]
    jurado.escribir_json(d / "verificacion.json", {"head": _head(cfg["repo"]), "sha256": _sha256(salida),
                                                   "comandos": comandos, "plan_ilegible": a.plan_ilegible})
    _imprimir({"ok": True, "plan": str(salida), "comandos": comandos, "plan_ilegible": a.plan_ilegible})
    return 0


def cmd_valida(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    ver, plan = jurado.leer_json(d / "verificacion.json"), d / "verificacion.html"
    _exige_limpio(cfg["repo"])
    if not isinstance(ver, dict) or not plan.is_file():
        raise Falla("corre «verificacion» primero")
    if ver["head"] != _head(cfg["repo"]) or ver["sha256"] != _sha256(plan):
        raise Falla("verificacion.html es de otro HEAD o cambió: vuelve a correr «verificacion»")
    entorno = {**os.environ, **({"VALIDA_IMAGEN": a.imagen} if a.imagen else {})}
    r = subprocess.run([sys.executable, str(VALIDA_IMPL), "--plan", str(plan), "--origen", cfg["repo"],
                        "--registro", str(d)], capture_output=True, text=True, check=False, env=entorno)
    imagen = (jurado.leer_json(d / "impl-validacion.json") or {}).get("imagen") or a.imagen or "ejecutor-valida"
    inspeccion = subprocess.run([os.environ.get("DOCKER_BIN", "docker"), "image", "inspect", "--format", "{{.Id}}",
                                 imagen], capture_output=True, text=True, check=False) if shutil.which(
        os.environ.get("DOCKER_BIN", "docker")) else None
    jurado.escribir_json(d / "validacion.json", {"head": ver["head"], "plan_sha256": ver["sha256"], "rc": r.returncode,
                                                 "imagen": imagen, "imagen_id": inspeccion.stdout.strip()
                                                 if inspeccion and inspeccion.returncode == 0 else None,
                                                 "ts": jurado.ahora()})
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


# ───────────────────────────── reporte de pruebas ─────────────────────────────

# Cada prueba con su resultado en la salida detallada del runner: Django y unittest con -v 2 (el docstring va en la
# línea siguiente, que no puede ser otra prueba), pytest -v o -rA, Playwright --reporter=list, Jest --verbose y Vitest.
POR_PRUEBA = (
    re.compile(r"^(?P<n>\w+ \([\w.]+\))(?:\n(?!\w+ \([\w.]+\))[^\n]*?)? \.\.\. (?P<r>ok|FAIL|ERROR|skipped"
               r"|expected failure|unexpected success)\b", re.M),
    re.compile(r"^(?P<n>\S+::\S+) (?P<r>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b", re.M),
    re.compile(r"^(?P<r>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS) (?P<n>\S+::\S+)", re.M),
    re.compile(r"^[ \t]*(?P<r>✓|✘|-)[ \t]+\d+ (?P<n>\[[^\]\n]+\] › [^\n]+?)(?: \(\d+(?:\.\d+)?m?s\))?[ \t]*$", re.M),
    re.compile(r"^[ \t]*(?P<r>✓|√|✕|×|○|↓)[ \t]+(?![ \t]*\d+ \[)(?P<n>[^\n]+?)(?: \(?\d+(?:\.\d+)? ?m?s\)?)?[ \t]*$", re.M),
)
RESULTADO = {"ok": "pasa", "PASSED": "pasa", "✓": "pasa", "√": "pasa", "FAIL": "falla", "ERROR": "falla",
             "FAILED": "falla", "unexpected success": "falla", "XPASS": "falla", "✘": "falla", "✕": "falla",
             "×": "falla", "skipped": "omitida", "SKIPPED": "omitida", "-": "omitida", "○": "omitida", "↓": "omitida",
             "expected failure": "esperada", "XFAIL": "esperada"}
ETIQUETAS = {"falla": "Fallan", "omitida": "Omitidas", "esperada": "Fallas esperadas", "pasa": "Pasan"}
# Resumen final de unittest/Django («Ran N tests», «OK (skipped=5)»), pytest, Jest, Vitest y Playwright.
RESUMEN_RUNNER = re.compile(r"^[ \t]*(Ran \d+ tests? in \S+|(?:OK|FAILED)(?: \([^)\n]*\))?"
                            r"|=+ [^=\n]*\d+ (?:passed|failed|errors?|skipped)[^=\n]* =+"
                            r"|Tests?:?[ \t]+[^\n]*\d+ (?:passed|failed|total)[^\n]*"
                            r"|\d+ (?:passed|failed|flaky|skipped|did not run)(?: \([^)\n]*\))?)[ \t]*$", re.M)
NOMBRE_TIPO = {"unitaria": "Unitarias", "integracion": "Integración", "e2e": "E2E", "contrato": "Contrato",
               "seguridad": "Seguridad", "regresion": "Regresión", "datos": "Datos", "rendimiento": "Rendimiento",
               "concurrencia": "Concurrencia", "accesibilidad": "Accesibilidad"}
LIMITE_REPORTE = 30_000
CSS_REPORTE = """.pestanas>input{position:absolute;opacity:0;pointer-events:none}
.pestanas>nav{display:flex;flex-wrap:wrap;gap:4px;border-bottom:1px solid var(--line);margin:16px 0 0}
.pestanas>nav label{padding:8px 14px;cursor:pointer;border:1px solid var(--line);border-bottom:0;
border-radius:6px 6px 0 0;background:var(--head)}.panel{display:none;padding-top:4px}
details{margin:8px 0}summary{cursor:pointer;font-weight:600}img.captura{cursor:zoom-in}
img.captura.grande{max-width:100%;cursor:zoom-out}h3{font-size:15px;margin-top:24px}
@media print{.pestanas>nav{display:none}.panel{display:block!important}}"""
ZOOM = ("<script>document.addEventListener('click',function(e){var t=e.target;"
        "if(t.classList&&t.classList.contains('captura'))t.classList.toggle('grande')})</script>")


def pruebas_de_la_salida(salida: str) -> dict[str, str]:
    """Cada prueba que el runner lista una por una, con su resultado (pasa, falla, omitida o esperada). Vacío si la
    suite corrió sin salida detallada."""
    vistas: dict[str, str] = {}
    for patron in POR_PRUEBA:
        for m in patron.finditer(salida):
            vistas.setdefault(" ".join(m["n"].split()), RESULTADO[m["r"]])
    return vistas


def resumen_del_runner(salida: str) -> list[str]:
    return [m.group(1).strip() for m in RESUMEN_RUNNER.finditer(salida)][-6:]


def _json(ruta: Path) -> dict:
    datos = jurado.leer_json(ruta)
    return datos if isinstance(datos, dict) else {}


def _dicts(datos: dict, clave: str) -> list[dict]:
    valor = datos.get(clave)
    return [x for x in valor if isinstance(x, dict)] if isinstance(valor, list) else []


def _texto(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _pre(texto, limite: int = LIMITE_REPORTE) -> str:
    """Todo texto del reporte va depurado: el reporte se comparte."""
    return f"<pre>{_e(_recorte(depurar(str(texto or '')), limite))}</pre>"


def _png_en_linea(dir_caso: Path, nombre) -> str | None:
    """La captura dentro del HTML, para que el reporte se pueda mandar solo."""
    if not captura_valida(dir_caso, nombre):
        return None
    return "data:image/png;base64," + base64.b64encode((dir_caso / nombre).read_bytes()).decode()


def _pestanas(paneles: list[tuple[str, str]]) -> tuple[str, str]:
    """(css, html) de las pestañas, sin JavaScript: un radio por pestaña."""
    css = "".join(f"#pt-{i}:checked~nav label[for=pt-{i}]{{background:var(--bg);font-weight:600}}"
                  f"#pt-{i}:focus-visible~nav label[for=pt-{i}]{{outline:2px solid var(--fg)}}"
                  f"#pt-{i}:checked~#pp-{i}{{display:block}}" for i in range(len(paneles)))
    entradas = "".join(f"<input type='radio' name='pestana' id='pt-{i}'{' checked' if not i else ''}>"
                       for i in range(len(paneles)))
    etiquetas = "".join(f"<label for='pt-{i}'>{_e(t)}</label>" for i, (t, _) in enumerate(paneles))
    secciones = "".join(f"<section class='panel' id='pp-{i}'><h2>{_e(t)}</h2>{c}</section>"
                        for i, (t, c) in enumerate(paneles))
    return css, f"<div class='pestanas'>{entradas}<nav>{etiquetas}</nav>{secciones}</div>"


# Suite

def _corridas(d: Path) -> list[tuple[str, dict]]:
    """Cada corrida de la suite guardada en D, en el orden en que se corrió."""
    corridas = [(p.stem.removeprefix("suite-"), _json(p)) for p in d.glob("suite-*.json")]
    return sorted(((f, c) for f, c in corridas if c), key=lambda x: str(x[1].get("ts", "")))


def _conteo(pruebas: dict[str, str]) -> str:
    cuenta = Counter(pruebas.values())
    return " · ".join(f"{cuenta[r]} {r}" for r in ETIQUETAS if cuenta[r])


def _desglose(pruebas: dict[str, str]) -> str:
    if not pruebas:
        return ("<p class='alerta'>La salida no lista cada prueba: la suite corrió sin salida detallada (Django o "
                "unittest -v 2, pytest -rA, Jest --verbose, Vitest --reporter=verbose, Playwright --reporter=list)."
                "</p>")
    grupos: dict[str, list[str]] = {}
    for nombre, resultado in sorted(pruebas.items()):
        grupos.setdefault(resultado, []).append(nombre)
    return "".join(
        f"<details{' open' if r == 'falla' else ''}><summary>{ETIQUETAS[r]} ({len(grupos[r])})</summary>"
        "<div class='tw'><table><tr><th>Prueba</th><th>Resultado</th></tr>"
        + "".join(f"<tr><td>{_e(n)}</td><td class='{r}'>{r}</td></tr>" for n in grupos[r])
        + "</table></div></details>" for r in ETIQUETAS if r in grupos)


def _rojos_de_fase_3(corrida: dict) -> str:
    en = corrida.get("rojos_en_suite")
    if not isinstance(en, dict):
        return ""
    grupos = "; ".join(", ".join(map(str, g)) for g in en.get("grupos", []) if isinstance(g, list))
    fuera = "".join(f"<li>{_e(x)}: {_e(en.get('motivos', {}).get(x, ''))}</li>" for x in en.get("fuera", []))
    return (f"<p>Con las mutaciones de los rojos aplicadas: {len(en.get('verificados', []))} pruebas vistas en rojo "
            f"dentro de la suite completa, en {_e(en.get('corridas', 0))} corridas (grupos: {_e(grupos or '—')}).</p>"
            + (f"<p class='falla'>La suite no corre:</p><ul>{fuera}</ul>" if fuera else ""))


def _html_corrida(d: Path, fase: str, corrida: dict, base: dict, detalle: bool) -> str:
    log = d / f"suite-{fase}.txt"
    salida = depurar(_texto(log))
    pruebas = pruebas_de_la_salida(salida)
    nuevos = [] if fase == "linea-base" else rojos_nuevos(corrida, base)
    lista = "".join(f"<li>{_e(f)}</li>" for f in corrida.get("fallas") or [])
    return (f"<details{' open' if detalle else ''}><summary>{_e(fase)} — rc {_e(corrida.get('rc'))}"
            f"{' · ' + _conteo(pruebas) if pruebas else ''}</summary><p class='meta'>Commit <code>"
            f"{_e(str(corrida.get('head'))[:10])}</code> · {_e(corrida.get('ts'))} · <code>"
            f"{_e(depurar(str(corrida.get('comando', ''))))}</code> · log completo: <code>{_e(log)}</code></p>"
            + _pre("\n".join(resumen_del_runner(salida)) or "(sin línea de resumen del runner)")
            + (f"<p>Fallas:</p><ul>{lista}</ul>" if lista else "")
            + (f"<p class='falla'>Nuevas respecto de la línea base: {_e(', '.join(nuevos))}</p>" if nuevos else "")
            + _rojos_de_fase_3(corrida) + (_desglose(pruebas) if detalle else "")
            + f"<details><summary>Salida del runner</summary>{_pre(salida)}</details></details>")


def _panel_suite(d: Path) -> str:
    corridas = _corridas(d)
    if not corridas:
        return "<p class='meta'>Sin señal: no hay ninguna corrida de la suite (D/suite-*.json).</p>"
    por_fase = dict(corridas)
    detalle = "final" if "final" in por_fase else corridas[-1][0]
    filas = "".join(f"<tr><td>{_e(f)}</td><td><code>{_e(str(c.get('head'))[:10])}</code></td><td>{_e(c.get('ts'))}"
                    f"</td><td class='{'pasa' if c.get('rc') == 0 else 'falla'}'>{_e(c.get('rc'))}</td>"
                    f"<td>{len(c.get('fallas') or [])}</td></tr>" for f, c in corridas)
    return (f"<p class='meta'>{len(corridas)} corridas de la suite completa según D/suite-*.json. El desglose por "
            f"prueba va en la corrida «{_e(detalle)}»; en las demás, el resumen del runner y las fallas.</p>"
            "<div class='tw'><table><tr><th>Corrida</th><th>Commit</th><th>Fecha</th><th>rc</th><th>Fallas</th></tr>"
            + filas + "</table></div>"
            + "".join(_html_corrida(d, f, c, por_fase.get("linea-base", {}), f == detalle) for f, c in corridas))


# Pruebas nuevas (Fase 3), una pestaña por tipo

def _estado_rojo(p: dict | None, descarte: dict | None, repo) -> str:
    if descarte:
        return f"<span class='alerta'>descartado</span>: {_e(descarte.get('razon'))}"
    if p is None:
        return "<span class='falla'>sin prueba vista en rojo</span>"
    errores = list(p.get("errores", ["registro sin veredicto"])) + _rojo_vigente(p, repo)
    if not errores:
        return "<span class='pasa'>válido</span>"
    return "".join(f"<div class='falla'>{_e(x)}</div>" for x in errores)


def _html_hueco(d: Path, c: dict, p: dict | None, descarte: dict | None, repo) -> str:
    rojo = p or {}
    parche = _texto(d / "rojos" / f"{Path(str(c.get('id'))).name}.patch") if p else ""
    mutacion = (f"{_e(', '.join(map(str, rojo.get('mutados', []))))}<details><summary>Mutación</summary>"
                f"{_pre(parche)}</details>") if p else "—"
    con = (f"rc {_e(rojo.get('rc_con'))}<details><summary>Salida</summary><p><code>"
           f"{_e(depurar(str(rojo.get('comando', ''))))}</code></p>{_pre(rojo.get('salida'))}</details>") if p else "—"
    return (f"<tr><td>{_e(c.get('id'))}</td><td>{_e(c.get('que_prueba'))}<div class='meta'>{_e(c.get('camino'))} · "
            f"protege {_e(c.get('protege'))}</div></td><td>{_e(c.get('entrada'))} → <em>{_e(c.get('esperado'))}</em>"
            f"</td><td><code>{_e(rojo.get('prueba') or c.get('archivo'))}</code></td><td>{mutacion}</td>"
            f"<td>{'rc ' + _e(rojo.get('rc_sin')) if p else '—'}</td><td>{con}</td>"
            f"<td>{_estado_rojo(p, descarte, repo)}</td></tr>")


def _paneles_por_tipo(d: Path, repo) -> list[tuple[str, str]]:
    huecos = _json(d / "fase-2-huecos.json")
    rojos = {p.get("caso"): p for p in _dicts(_json(d / "fase-3-rojos.json"), "pruebas")}
    descartes = {x.get("id"): x for x in _dicts(_json(d / "fase-2-descartes.json"), "descartes")}
    por_tipo: dict[str, list[dict]] = {}
    for c in _dicts(huecos, "casos"):
        por_tipo.setdefault(str(c.get("tipo")), []).append(c)
    paneles = []
    for tipo in sorted(por_tipo, key=lambda t: TIPOS.index(t) if t in TIPOS else len(TIPOS)):
        casos = por_tipo[tipo]
        filas = "".join(_html_hueco(d, c, rojos.get(c.get("id")), descartes.get(c.get("id")), repo) for c in casos)
        paneles.append((NOMBRE_TIPO.get(tipo, tipo), (
            f"<p class='meta'>{len(casos)} casos de tipo «{_e(tipo)}» según D/fase-2-huecos.json. Cada prueba pasa "
            "sin la mutación de producción y falla con ella, por su aserción.</p><div class='tw'><table><tr><th>Caso"
            "</th><th>Qué prueba</th><th>Entrada → esperado</th><th>Prueba</th><th>Mutación</th><th>Sin la mutación"
            "</th><th>Con la mutación</th><th>Estado</th></tr>" + filas + "</table></div>")))
    return paneles


# Casos manuales, con sus capturas

def _ultima_vuelta(d: Path) -> tuple[Path | None, dict]:
    vueltas = sorted((int(p.parent.name[6:]), p.parent) for p in d.glob("evidencia/ronda-*/meta.json")
                     if re.fullmatch(r"ronda-\d+", p.parent.name))
    return (vueltas[-1][1], _json(vueltas[-1][1] / "cruce.json")) if vueltas else (None, {})


def _revision_del_caso(caso: str, cruce: dict) -> str:
    if not cruce:
        return "<span class='alerta'>sin cruzar</span>"
    corregir = next((c for c in _dicts(cruce, "corregir") if c.get("caso") == caso), None)
    if corregir:
        return "<span class='falla'>a corregir</span>" + "".join(f"<div>{_e(m)}</div>" for m in corregir.get("motivos", []))
    if caso not in cruce.get("confirmados", []):
        return "<span class='alerta'>sin confirmar</span>"
    nota = next((n for n in _dicts(cruce, "notas") if n.get("caso") == caso), {})
    heredado = " (de la vuelta anterior)" if caso in cruce.get("heredados", []) else ""
    return (f"<span class='pasa'>confirmado por los dos revisores{heredado}</span>"
            + "".join(f"<div class='alerta'>Nota de {_e(j)}: {_e(v.get('porque'))}</div>"
                      for j, v in nota.items() if isinstance(v, dict)))


def _html_paso_reporte(paso: dict, dir_caso: Path) -> str:
    imagen = _png_en_linea(dir_caso, paso.get("captura"))
    captura = f"<img class='captura' src='{imagen}' alt='Paso {_e(paso.get('n'))}'>" if imagen else ""
    if (texto := texto_de_captura(dir_caso, paso.get("texto"))) is not None:
        captura += _pre(texto, MAX_CAPTURA_TEXTO)
    res = str(paso.get("resultado"))
    return (f"<tr><td>{_e(paso.get('n'))}</td><td>{_e(paso.get('accion'))}</td><td>{_e(paso.get('esperado'))}</td>"
            f"<td><span class='{_e(res)}'>{_e(res)}</span>" + (_pre(paso.get("error")) if paso.get("error") else "")
            + "".join(f"<div class='alerta'>⚠ {_e(x)}</div>" for x in alertas_de_paso(paso, dir_caso))
            + f"</td><td>{captura or '—'}</td><td>{_celda_registros(paso.get('consola') or [], ('tipo', 'texto'))}"
            f"{_celda_registros(paso.get('red') or [], ('estado', 'metodo', 'url'))}</td></tr>")


def _html_manual(c: dict, evidencia: dict | None, cruce: dict, enmiendas: list[dict]) -> str:
    cid = str(c.get("id"))
    if evidencia:
        filas = "".join(_html_paso_reporte(p, evidencia["_dir"]) for p in evidencia.get("pasos") or [])
        quien = (f"Lo corrió una herramienta: <code>{_e(evidencia.get('archivo'))}</code> · "
                 f"{_revision_del_caso(cid, cruce)}")
    else:
        pendiente = "sin evidencia en la última vuelta" if c.get("automatizable") else "a mano"
        filas = "".join(f"<tr><td>{i}</td><td>{_e(p.get('accion'))}</td><td>{_e(p.get('esperado'))}</td>"
                        f"<td class='alerta'>{pendiente}</td><td>—</td><td></td></tr>"
                        for i, p in enumerate(_dicts(c, "pasos"), 1))
        quien = ("<span class='falla'>Sin evidencia en la última vuelta</span>" if c.get("automatizable") else
                 f"<span class='alerta'>Te toca a ti</span>: {_e(c.get('razon_no_automatizable'))}")
    cambios = "".join(f"<p class='alerta'>Enmienda del paso {_e(e.get('paso'))}: «{_e(e.get('antes'))}» → "
                      f"«{_e(e.get('despues'))}». {_e(e.get('motivo'))}. Juan: «{_e(e.get('autorizacion'))}»</p>"
                      for e in enmiendas if e.get("caso") == cid)
    return (f"<h3 id='{_e(cid)}'>{_e(cid)} — {_e(c.get('titulo'))}</h3><p class='meta'>Perfil: {_e(c.get('perfil'))}"
            f" · Camino: {_e(c.get('camino'))} · Precondiciones: {_e(c.get('precondiciones'))} · Datos: "
            f"{_e(c.get('datos'))}</p><p>{quien}</p>{cambios}<div class='tw'><table><tr><th>#</th><th>Acción</th>"
            "<th>Esperado</th><th>Resultado</th><th>Captura</th><th>Consola y red</th></tr>" + filas
            + "</table></div>")


def _panel_manuales(d: Path) -> str:
    casos = _dicts(_json(d / "manuales.json"), "casos")
    if not casos:
        return "<p class='meta'>Sin señal: no hay casos manuales congelados (D/manuales.json).</p>"
    raiz, cruce = _ultima_vuelta(d)
    evidencia = {e["caso"]: e for e in cargar_evidencia(raiz)[0]} if raiz else {}
    vuelta = ("sin vuelta de evidencia" if raiz is None else f"evidencia de la vuelta {_e(raiz.name[6:])}, "
              + ("aprobada" if cruce.get("ok") else "sin aprobar" if cruce else "sin cruzar"))
    a_mano = sum(1 for c in casos if not c.get("automatizable"))
    filas = "".join(f"<tr><td><a href='#{_e(c.get('id'))}'>{_e(c.get('id'))}</a></td><td>{_e(c.get('titulo'))}</td>"
                    f"<td>{_e(c.get('camino'))}</td><td>{'herramienta' if c.get('automatizable') else 'a mano'}</td>"
                    f"<td>{_e(reportado(evidencia[c.get('id')]) if c.get('id') in evidencia else '—')}</td></tr>"
                    for c in casos)
    return (f"<p class='meta'>{len(casos)} casos según D/manuales.json · {len(casos) - a_mano} los corre una "
            f"herramienta y {a_mano} te tocan a ti · {vuelta}.</p><div class='tw'><table><tr><th>ID</th><th>Caso</th>"
            "<th>Camino</th><th>Quién lo corre</th><th>Resultado</th></tr>" + filas + "</table></div>"
            + "".join(_html_manual(c, evidencia.get(c.get("id")), cruce, _enmiendas(d)) for c in casos))


# Validación aislada

def _panel_validacion(d: Path) -> str:
    v, impl = _json(d / "validacion.json"), _json(d / "impl-validacion.json")
    if not v and not impl:
        return "<p class='meta'>Sin señal: no se corrió «valida» (no hay D/validacion.json).</p>"
    filas = "".join(f"<tr><td><code>{_e(depurar(str(x.get('comando'))))}</code></td><td class='"
                    f"{'pasa' if x.get('resultado') == 'verde' else 'falla'}'>{_e(x.get('resultado'))}</td>"
                    f"<td><details><summary>Salida</summary>{_pre(x.get('salida'))}</details></td></tr>"
                    for x in _dicts(impl, "evidencia"))
    veredicto = impl.get("veredicto") if isinstance(impl.get("veredicto"), dict) else {}
    hallazgos = "".join(f"<li>{_e(h.get('gravedad'))} · {_e(h.get('donde'))}: {_e(h.get('que'))}</li>"
                        for h in _dicts(veredicto, "hallazgos"))
    return (f"<p class='meta'>valida_impl.py salió con rc {_e(v.get('rc'))} en el commit <code>"
            f"{_e(str(v.get('head'))[:10])}</code> · imagen <code>{_e(v.get('imagen'))}</code> · {_e(v.get('ts'))}. "
            "Copia aislada sin red; corre cada comando del bloque «Automática» de D/verificacion.html.</p>"
            + "".join(f"<p class='falla'>{_e(m)}</p>" for m in impl.get("motivos", []) if m)
            + "<div class='tw'><table><tr><th>Comando</th><th>Resultado</th><th>Salida</th></tr>" + filas
            + "</table></div>"
            + (f"<p>Veredicto de Codex: <strong>{_e(veredicto.get('veredicto'))}</strong>. "
               f"{_e(depurar(str(veredicto.get('resumen', ''))))}</p>" if veredicto else "")
            + (f"<ul>{hallazgos}</ul>" if hallazgos else ""))


def html_reporte(d: Path, cfg: dict, cierre: dict | None) -> str:
    """Un solo HTML con toda la evidencia de las pruebas, una pestaña por tipo: la suite completa (cada corrida), las
    pruebas nuevas de la Fase 3 por tipo (unitaria, integración, seguridad…), los casos manuales con sus capturas y
    la validación aislada."""
    repo = cfg["repo"]
    origen = cfg.get("plan_origen")
    nombre = d.name if origen in (None, "sesion") else Path(origen).stem
    rama = _git(repo, "branch", "--show-current").stdout.strip()
    head = _head(repo)
    estado = ("sin correr" if not isinstance(cierre, dict) else "de otro commit" if cierre.get("head") != head
              else "aprobado" if cierre.get("ok") else f"con {len(cierre.get('errores', []))} errores")
    meta = (f"<p class='meta'>Repo <code>{_e(repo)}</code> · rama <code>{_e(rama)}</code> · base <code>"
            f"{_e(str(cfg.get('base'))[:10])}</code> → HEAD <code>{_e(head[:10])}</code> · registro <code>"
            f"{_e(d)}</code> · generado {_e(jurado.ahora())} · cierre: {_e(estado)}</p>")
    paneles = ([("Suite", _panel_suite(d))] + _paneles_por_tipo(d, repo)
               + [("Manuales", _panel_manuales(d)), ("Validación aislada", _panel_validacion(d))])
    css, cuerpo = _pestanas(paneles)
    return _pagina(f"Pruebas — {nombre}", meta + cuerpo + ZOOM, CSS_REPORTE + css)


def escribir_reporte(d: Path, cfg: dict, cierre: dict | None) -> Path:
    ruta = d / "reporte-pruebas.html"
    _escribir(ruta, html_reporte(d, cfg, cierre))
    return ruta


def cmd_reporte(a) -> int:
    d = Path(a.dir).expanduser()
    ruta = escribir_reporte(d, _config(d), jurado.leer_json(d / "cierre.json"))
    _imprimir({"ok": True, "html": str(ruta)})
    return 0


# ───────────────────────────── cierre ─────────────────────────────

def _revisar_fases(d: Path, repo) -> list[str]:
    errores = []
    try:
        huecos, e = _cargar(_congelado(d, "fase-2-huecos.json"), "casos_prueba")
        errores += e or revisar_casos(huecos, _autorizacion_sellada(d, "fase-2-huecos.json"))
    except Falla as x:
        errores.append(str(x))
    try:
        _manuales(d)
    except Falla as x:
        errores.append(str(x))
    return errores + revisar_rojos(d, repo)


def _es_segura(ruta: str, specs: set[str]) -> bool:
    """Un cambio que no puede alterar lo que se vio en pantalla: documentación, o un archivo de prueba (por su nombre)
    que no es e2e ni uno de los specs de la evidencia. Helpers, conftest y fixtures sí cuentan: la app o los specs
    pueden usarlos."""
    if ruta in specs or E2E.search(ruta):
        return False
    return bool(DOCUMENTACION.search(ruta) or TEST_ARCHIVO.search(ruta))


def _revisar_evidencia_final(d: Path, repo) -> list[str]:
    """Las pruebas manuales, sus capturas y su revisión no se omiten ni se cortan: la última vuelta tiene que estar
    aprobada por los dos revisores y seguir valiendo para el HEAD."""
    try:
        manuales = _manuales(d)
    except Falla as e:
        return [str(e)]
    if not manuales:
        return ["manuales.json no tiene casos automatizables: la evidencia con captura no se omite"]
    vueltas = sorted((int(p.parent.name.split("-")[1]), p) for p in d.glob("evidencia/ronda-*/cruce.json"))
    cruce = jurado.leer_json(vueltas[-1][1]) if vueltas else None
    if not isinstance(cruce, dict) or not cruce.get("ok"):
        return ["la última revisión de la evidencia no está aprobada: la evidencia no se corta ni se omite; corrige y "
                "corre otra vuelta (Fases 5 y 6)"]
    raiz = vueltas[-1][1].parent
    if manifiesto(raiz) != (jurado.leer_json(raiz / "meta.json") or {}).get("manifiesto"):
        return [f"la evidencia de {raiz.name} cambió después de cruzarse"]
    if _manuales_cambiaron(d, vueltas[-1][0]):
        return [f"manuales.json cambió (una enmienda) después de la evidencia de {raiz.name}: repite las fases 5 y 6"]
    tocan = _cambios_desde_cruce(d, repo, vueltas[-1][0])
    return [f"la evidencia es de {cruce['head'][:10]} y desde entonces cambiaron producción o e2e "
            f"({', '.join(tocan[:5])}): repite las fases 5 y 6"] if tocan else []


def _manuales_cambiaron(d: Path, k: int) -> bool:
    """¿manuales.json cambió (una enmienda) después de armar la evidencia de la vuelta k?"""
    meta = jurado.leer_json(d / "evidencia" / f"ronda-{k}" / "meta.json") or {}
    return (d / "manuales.json").is_file() and meta.get("manuales_sha256") != _sha256(d / "manuales.json")


def _cambios_desde_cruce(d: Path, repo, k: int) -> list[str]:
    """Lo que cambió desde el HEAD que juzgó el cruce de la vuelta k y puede alterar lo que se vio: producción, e2e o
    los specs de esa evidencia (documentación y pruebas unitarias no cuentan)."""
    raiz, cruce = d / "evidencia" / f"ronda-{k}", _cruce(d, k)
    if not isinstance(cruce, dict) or not cruce.get("head"):
        return []
    specs = {str(c.get("archivo")) for c in cargar_evidencia(raiz)[0] if c.get("archivo")}
    return [r for r in _cambiados(repo, cruce["head"]) if not _es_segura(r, specs)]


def _revisar_validacion(d: Path, repo, autorizado: str | None) -> tuple[list[str], bool]:
    v, plan = jurado.leer_json(d / "validacion.json"), d / "verificacion.html"
    if not isinstance(v, dict):
        return ["falta validacion.json: corre «valida»"], False
    if v.get("head") != _head(repo):
        return ["la validación aislada es de otro HEAD: vuelve a correr «verificacion» y «valida»"], False
    if not plan.is_file() or _sha256(plan) != v.get("plan_sha256"):
        return ["verificacion.html cambió después de validar"], False
    if v.get("rc") == 0:
        return [], False
    if autorizado:
        return [], True
    return [f"valida_impl.py salió con rc {v.get('rc')}: sin la autorización literal de Juan "
            "(--borrador-autorizado) no hay PR"], False


def _revisar_entrega(d: Path, cfg: dict, autorizaciones: dict, abiertos: list[dict] = ()) -> list[str]:
    """Sin firma de Claude en los commits ni en el PR, sin secretos en el PR, cada autorización citada literal y los
    casos descartados o enmendados y los hallazgos que quedaron abiertos, listados."""
    errores = []
    if FIRMA.search(_git(cfg["repo"], "log", f"{cfg['base']}..HEAD", "--format=%B").stdout):
        errores.append("hay commits con firma de Claude (Co-Authored-By, Generated with, claude.ai/code)")
    pr = d / "pr.md"
    if not pr.is_file():
        return errores + ["falta D/pr.md, el cuerpo del PR: escríbelo antes de «cierre»"]
    texto = pr.read_text(encoding="utf-8")
    errores += ["D/pr.md trae firma de Claude"] if FIRMA.search(texto) else []
    fugas_pr = [n for n, patron in SECRETOS_PR.items() if patron.search(texto)]
    errores += [f"D/pr.md trae un posible secreto: {', '.join(fugas_pr)}"] if fugas_pr else []
    errores += [f"D/pr.md no cita literal la autorización «{nombre}»: {valor}"
                for nombre, valor in autorizaciones.items() if isinstance(valor, str) and valor not in texto]
    errores += [f"D/pr.md no lista el hallazgo {h['gravedad']} abierto de {h['juez']} en «{h.get('donde')}»"
                for h in abiertos if str(h.get("donde")) not in texto]
    errores += [f"D/pr.md no lista la enmienda del caso {e['caso']} paso {e['paso']} ni su esperado nuevo"
                for e in _enmiendas(d) if e["caso"] not in texto or e["despues"] not in texto]
    return errores + [f"D/pr.md no lista el caso descartado {c}" for c in _ids_descartados(d) if c not in texto]


def _revisar_git(cfg: dict) -> list[str]:
    """La rama no es la base y sigue feature/<slug> (o fix/, refactor/, docs/); cada commit desde la base es
    Conventional Commits. Los merges y los «Revert "…"» que arma git no cuentan."""
    repo, errores = cfg["repo"], []
    rama = _git(repo, "branch", "--show-current").stdout.strip()
    if not RAMA.match(rama) or rama == cfg["rama_base"]:
        errores.append(f"la rama «{rama or 'HEAD desatendido'}» no es feature/<slug> (o fix/, refactor/, docs/) "
                       f"distinta de {cfg['rama_base']}")
    asuntos = _git(repo, "log", "--no-merges", f"{cfg['base']}..HEAD", "--format=%s").stdout.splitlines()
    malos = [x for x in asuntos if not CONVENCIONAL.match(x)]
    if malos:
        errores.append(f"commits que no siguen Conventional Commits («feat: …», «fix: …»): {'; '.join(malos[:3])}")
    return errores


def _ids_descartados(d: Path) -> list[str]:
    return [x.get("id") for x in (jurado.leer_json(d / "fase-2-descartes.json") or {}).get("descartes", [])]


def _autorizaciones_de_rondas(d: Path) -> list[str]:
    return [e["omitidos_autorizados"] for e in (jurado.leer_json(p) or {} for p in sorted(d.glob("ronda-*/estado.json")))
            if e.get("omitidos_autorizados")]


def _ronda_extra(d: Path) -> str | None:
    return next((e["ronda_extra_autorizada"] for e in (jurado.leer_json(p) or {} for p in d.glob("ronda-*/estado.json"))
                 if e.get("ronda_extra_autorizada")), None)


def cmd_cierre(a) -> int:
    d = Path(a.dir).expanduser()
    cfg = _config(d)
    repo = cfg["repo"]
    errores = [] if _sha256(Path(cfg["plan"])) == cfg["plan_sha256"] else ["la copia congelada del plan cambió"]
    veredicto = siguiente(d)
    if veredicto["accion"] != "aprobado":
        errores.append(f"la revisión final no está aprobada ({veredicto['accion']})")
    errores += _revisar_suites(d, cfg, a.rojos_preexistentes_autorizados)
    errores += _revisar_fases(d, repo) + _revisar_evidencia_final(d, repo)
    e_valida, sin_validar = _revisar_validacion(d, repo, a.borrador_autorizado)
    autorizaciones = {"borrador": a.borrador_autorizado if sin_validar else None,
                      "rojos_preexistentes": a.rojos_preexistentes_autorizados, "url": cfg.get("confirmacion_url"),
                      "sin_huecos": _autorizacion_sellada(d, "fase-2-huecos.json"),
                      "vuelta_extra": _vuelta_extra(d).get("autorizacion"),
                      **{f"enmienda_{e['caso']}_paso_{e['paso']}_{i}": e["autorizacion"]
                         for i, e in enumerate(_enmiendas(d), 1)},
                      "plan_ilegible": (jurado.leer_json(d / "verificacion.json") or {}).get("plan_ilegible"),
                      "ronda_extra": _ronda_extra(d),
                      **{f"omitidos_ronda_{i}": v for i, v in enumerate(_autorizaciones_de_rondas(d), 1)}}
    abiertos = veredicto.get("abiertos", [])
    errores += e_valida + _revisar_entrega(d, cfg, autorizaciones, abiertos) + _revisar_git(cfg)
    res = {"ok": not errores, "errores": errores, "borrador": sin_validar, "no_validado": sin_validar,
           "head": _head(repo), "autorizaciones": autorizaciones, "descartes": _ids_descartados(d),
           "hallazgos_abiertos": abiertos}
    # El reporte para Juan se arma en cada cierre (también con errores, para ver dónde quedó); sin él no hay cierre.
    try:
        res["reporte"] = str(escribir_reporte(d, cfg, res))
    except (OSError, ValueError, KeyError, TypeError) as e:
        errores.append(f"no se pudo armar D/reporte-pruebas.html: {e}")
        res["ok"] = False
    if not errores:
        jurado.escribir_json(d / "cierre.json", {**res, "ts": jurado.ahora()})
    _imprimir(res)
    return 0 if not errores else 1


# ───────────────────────────── CLI ─────────────────────────────

def _con_dir(sub, nombre: str):
    s = sub.add_parser(nombre)
    s.add_argument("--dir", required=True)
    return s


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="implementa_plan.py", description="Compuerta de /implementa-plan.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inicia")
    for nombre in ("--plan", "--repo", "--suite"):
        s.add_argument(nombre, required=True)
    for nombre in ("--url", "--confirmacion-url", "--base", "--dir"):
        s.add_argument(nombre)
    s.add_argument("--sesion", choices=["opus", "fable"], default="opus")
    s.add_argument("--con-advisor", action="store_true")
    s.add_argument("--desde-sesion", action="store_true")
    s = _con_dir(sub, "suite")
    s.add_argument("--fase", required=True)
    s.add_argument("--plazo", type=int, default=PLAZO)
    s = sub.add_parser("casos")
    s.add_argument("--archivo")
    s.add_argument("--dir")
    s.add_argument("--sin-huecos", help="texto literal de Juan que acepta seguir sin casos nuevos")
    s = _con_dir(sub, "rojo")
    for nombre in ("--caso", "--prueba", "--comando", "--parche"):
        s.add_argument(nombre, required=True)
    s.add_argument("--plazo", type=int, default=PLAZO)
    s = _con_dir(sub, "rojos")
    s.add_argument("--repetir", action="store_true", help="vuelve a correr los rojos que vencieron")
    s.add_argument("--plazo", type=int, default=PLAZO)
    s = sub.add_parser("manuales")
    s.add_argument("--archivo", required=True)
    s.add_argument("--salida")
    s.add_argument("--dir")
    s = _con_dir(sub, "enmienda-manual")
    s.add_argument("--caso", required=True)
    s.add_argument("--paso", type=int, required=True, help="número del paso, desde 1")
    s.add_argument("--esperado", required=True, help="el esperado nuevo del paso")
    s.add_argument("--motivo", required=True, help="el hallazgo que cambia el comportamiento (ronda N, archivo:línea)")
    s.add_argument("--autorizacion", required=True, help="texto literal de Juan que acepta la enmienda")
    for nombre in ("prepara-evidencia", "evidencia"):
        s = _con_dir(sub, nombre)
        s.add_argument("--ronda", type=int, required=True)
        s.add_argument("--vuelta-extra-autorizada", help="texto literal de Juan: una vuelta más después de "
                       f"{MAX_FALLAS_EVIDENCIA} seguidas sin aprobar")
    s.add_argument("--anexo", action="append", default=[])
    s = _con_dir(sub, "cruza")
    s.add_argument("--ronda", type=int, required=True)
    s.add_argument("--codex", required=True)
    s.add_argument("--claude", required=True)
    s = _con_dir(sub, "abre-ronda")
    s.add_argument("--omitidos-autorizados", help="texto literal de Juan: los revisores no verán los archivos con "
                   "nombre de secreto que toca el cambio")
    s.add_argument("--ronda-extra-autorizada", help="texto literal de Juan: una ronda más después del máximo, que se "
                   "aprueba si ningún revisor trae hallazgos graves")
    s = _con_dir(sub, "registra")
    s.add_argument("--ronda", type=int, required=True)
    s.add_argument("--juez", required=True)
    s.add_argument("--archivo", required=True)
    _con_dir(sub, "siguiente")
    s = _con_dir(sub, "verificacion")
    s.add_argument("--comando", action="append", default=[])
    s.add_argument("--plan-ilegible", help="texto literal de Juan que acepta reemplazar la Verificación del plan por "
                   "los --comando")
    s = _con_dir(sub, "valida")
    s.add_argument("--imagen", help="imagen del ejecutor con las dependencias del proyecto (VALIDA_IMAGEN)")
    _con_dir(sub, "copia")
    s = _con_dir(sub, "codex")
    s.add_argument("--prompt", required=True)
    s.add_argument("--esquema", required=True, choices=["casos_prueba", "revision_evidencia", "veredicto"])
    s.add_argument("--salida", required=True)
    s.add_argument("--esfuerzo", default="high", choices=["low", "medium", "high", "xhigh"])
    s.add_argument("--plazo", type=int, default=PLAZO)
    s = _con_dir(sub, "claude")
    s.add_argument("--prompt", required=True)
    s.add_argument("--esquema", required=True, choices=["casos_manuales", "revision_evidencia", "veredicto"])
    s.add_argument("--salida", required=True)
    s.add_argument("--modelo", help="modelo del revisor Claude (por omisión, el de la sesión: opus o fable)")
    s.add_argument("--plazo", type=int, default=PLAZO)
    _con_dir(sub, "reporte")
    s = _con_dir(sub, "cierre")
    s.add_argument("--borrador-autorizado", help="texto literal de Juan que autoriza un PR draft sin validación")
    s.add_argument("--rojos-preexistentes-autorizados", help="texto literal de Juan que acepta rojos de la línea base")
    return p


COMANDOS = {"inicia": cmd_inicia, "suite": cmd_suite, "casos": cmd_casos, "rojo": cmd_rojo, "rojos": cmd_rojos,
            "manuales": cmd_manuales, "enmienda-manual": cmd_enmienda_manual, "prepara-evidencia": cmd_prepara_evidencia, "evidencia": cmd_evidencia,
            "cruza": cmd_cruza, "abre-ronda": cmd_abre_ronda,
            "registra": cmd_registra, "siguiente": cmd_siguiente, "verificacion": cmd_verificacion,
            "valida": cmd_valida, "copia": cmd_copia, "codex": cmd_codex, "claude": cmd_claude, "reporte": cmd_reporte,
            "cierre": cmd_cierre}


def _salir_por_senal(numero, _marco):
    raise SystemExit(128 + numero)


def main(argv: list[str] | None = None) -> int:
    a = _parser().parse_args(argv)
    if getattr(a, "dir", None):
        a.dir = str(Path(a.dir).expanduser().resolve())
    # Un SIGTERM (p. ej. el tiempo agotado de una herramienta) corre los «finally»: «rojo» deshace su mutación.
    for senal in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(senal, _salir_por_senal)
    try:
        return COMANDOS[a.cmd](a)
    except Falla as e:
        return _falla(str(e), rc=e.rc)


if __name__ == "__main__":
    sys.exit(main())
