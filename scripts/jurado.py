#!/usr/bin/env python3
"""jurado.py — la compuerta de las auditorías cruzadas de planes.

Quien escribe un plan no decide si está aprobado: lo decide esta máquina de
estados a partir de los veredictos registrados. La tabla de estados vive en
$CLAUDE_HOME/schemas/estados_jurado.json y es la única fuente de verdad.

Subcomandos
  valida      ARCHIVO [--salida F]        ¿el veredicto cumple el esquema? (0 sí, 1 no, 2 sin veredicto)
  consenso    --fase plan|impl --codex F [--segundo F] [--esperados F] [--raiz R]
  jueces      --sesion opus|fable [--con-advisor]
  pendientes  PLAN                        PENDIENTE: bloqueantes y diferidos
  matriz      PLAN                        la matriz de tipos de prueba
  precheck    PLAN [--repo R]             las citas archivo:línea, contra las raíces del plan
  esperados   PLAN                        los comandos del bloque «Automática» de la Verificación
  inicia      --plan P [--dir D] [--repo R] [--con-advisor] [--sesion S]
  registra    --dir D --ronda N --juez J (--archivo F | --estado E [--detalle X])
  siguiente   --dir D                     la acción que toca según la tabla de estados
  ronda       --dir D [--respuesta F]     revisión mecánica y Codex de la ronda que toca
  mejor       --dir D                     la mejor versión registrada del plan
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

RAIZ = Path(os.environ.get("CLAUDE_HOME") or Path.home() / ".claude")
ESQUEMA = RAIZ / "schemas" / "veredicto.json"
ESTADOS = RAIZ / "schemas" / "estados_jurado.json"
RUBRICA = RAIZ / "rubricas" / "plan.json"
AUDITORIAS = RAIZ / "auditorias"
MODELO_CODEX = "gpt-6.1-sol"
ESFUERZO_CODEX = "high"
TIMEOUT_CODEX = 20 * 60
JUEZ_VALIDO = re.compile(r"[a-z0-9][a-z0-9-]*")
RONDA_ARCHIVO = re.compile(r"ronda-(\d+)-")
PENDIENTE = re.compile(r"PENDIENTE:(.*?)(?=</code>|</td>|</p>|</li>|\n|$)", re.S)
CITA = re.compile(r"<code>([~\w./-]+):(\d+)(?:[–-](\d+))?</code>")
ASIGNACION = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=\S*")
TIPOS_PRUEBA = {
    "unitarias": "unitari", "integración": "integraci", "e2e": "e2e",
    "rutas de error": "rutas de error", "regresión": "regresi", "seguridad": "seguridad",
    "contrato": "contrato", "migración": "migraci", "rendimiento": "rendimiento",
}


# ───────────────────────────── utilidades ─────────────────────────────

def leer_json(ruta: Path):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def escribir_json(ruta: Path, datos) -> None:
    """Escritura atómica: un registro a medias no debe parecer un registro."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def texto_plano(fragmento: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragmento)).split())


def sin_acentos(texto: str) -> str:
    base = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in base if unicodedata.category(c) != "Mn")


def codex_bin() -> str:
    return os.environ.get("CODEX_BIN") or "codex"


def ahora() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


# ───────────────────────────── esquema ─────────────────────────────

_TIPOS_JSON = {"object": dict, "array": list, "string": str, "null": type(None), "boolean": bool}


def _tipo_ok(dato, tipo) -> bool:
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return any(isinstance(dato, _TIPOS_JSON[t]) for t in tipos if t in _TIPOS_JSON)


def validar_esquema(dato, esquema: dict, ruta: str = "$") -> list[str]:
    """Subconjunto de JSON Schema que usa veredicto.json: type, enum, required,
    properties, additionalProperties: false e items."""
    if "type" in esquema and not _tipo_ok(dato, esquema["type"]):
        return [f"{ruta}: se esperaba {esquema['type']}"]
    errores = []
    if "enum" in esquema and dato not in esquema["enum"]:
        errores.append(f"{ruta}: «{dato}» fuera de {esquema['enum']}")
    if isinstance(dato, dict):
        errores += _validar_objeto(dato, esquema, ruta)
    if isinstance(dato, list) and "items" in esquema:
        for i, item in enumerate(dato):
            errores += validar_esquema(item, esquema["items"], f"{ruta}[{i}]")
    return errores


def _validar_objeto(dato: dict, esquema: dict, ruta: str) -> list[str]:
    errores = [f"{ruta}: falta la clave «{k}»" for k in esquema.get("required", []) if k not in dato]
    props = esquema.get("properties", {})
    if esquema.get("additionalProperties") is False:
        errores += [f"{ruta}: clave no permitida «{k}»" for k in dato if k not in props]
    for clave, sub in props.items():
        if clave in dato:
            errores += validar_esquema(dato[clave], sub, f"{ruta}.{clave}")
    return errores


def extraer_json(texto: str) -> tuple[str, object]:
    """('ok', datos) | ('sin-veredicto', None) | ('invalido', None).

    Codex responde JSON puro; advisor responde prosa que termina en un bloque
    ```json. Dos bloques son ambiguos: inválido."""
    texto = texto.strip()
    try:
        return "ok", json.loads(texto)
    except json.JSONDecodeError:
        pass
    bloques = re.findall(r"```json\s*\n(.*?)\n\s*```", texto, re.S)
    if not bloques:
        return "sin-veredicto", None
    if len(bloques) > 1:
        return "invalido", None
    try:
        return "ok", json.loads(bloques[0])
    except json.JSONDecodeError:
        return "invalido", None


def cargar_veredicto(texto: str) -> tuple[str, dict | None, list[str]]:
    estado, datos = extraer_json(texto)
    if estado != "ok":
        return estado, None, []
    esquema = leer_json(ESQUEMA)
    if esquema is None:
        return "invalido", None, [f"no se pudo leer el esquema {ESQUEMA}"]
    errores = validar_esquema(datos, esquema)
    return ("invalido", None, errores) if errores else ("ok", datos, [])


# ───────────────────────────── consenso ─────────────────────────────

def normalizar_comando(comando: str, raiz: str | None) -> str:
    if raiz:
        for forma in {raiz.rstrip("/"), os.path.realpath(raiz)}:
            comando = comando.replace(forma, "$CLAUDE_HOME")
    comando = comando.replace("${CLAUDE_HOME}", "$CLAUDE_HOME").replace('"', "").replace("'", "")
    return " ".join(comando.split())


def evaluar_evidencia_impl(veredicto: dict, esperados: list[str], raiz: str | None) -> list[str]:
    """D1, como operación de conjuntos: cada esperado con al menos un verde;
    cualquier rojo o no-corrio bloquea; ningún comando extra; duplicados en verde sí."""
    esperados_n = {normalizar_comando(c, raiz) for c in esperados}
    verdes, otros = set(), set()
    for ev in veredicto.get("evidencia", []):
        destino = verdes if ev.get("resultado") == "verde" else otros
        destino.add(normalizar_comando(ev.get("comando", ""), raiz))
    motivos = [] if esperados_n else ["la lista de comandos esperados está vacía"]
    if esperados_n - verdes:
        motivos.append(f"faltan en verde: {sorted(esperados_n - verdes)}")
    if otros:
        motivos.append(f"en rojo o sin correr: {sorted(otros)}")
    if (verdes | otros) - esperados_n:
        motivos.append(f"comandos extra: {sorted((verdes | otros) - esperados_n)}")
    return motivos


def consenso(fase: str, codex: dict, segundo: dict | None = None,
             esperados: list[str] | None = None, raiz: str | None = None) -> tuple[bool, list[str]]:
    motivos = []
    if codex.get("veredicto") != "pasa":
        motivos.append(f"Codex: {codex.get('veredicto')}")
    if segundo is not None and segundo.get("veredicto") != "pasa":
        motivos.append(f"segundo juez: {segundo.get('veredicto')}")
    if fase == "impl":
        motivos += evaluar_evidencia_impl(codex, esperados or [], raiz)
    return not motivos, motivos


# ───────────────────────────── jueces ─────────────────────────────

def modelo_de_agente(agente: str) -> str | None:
    try:
        texto = (RAIZ / "agents" / f"{agente}.md").read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"^model:\s*(\S+)", texto, re.M)
    return m.group(1) if m else None


def jueces(sesion: str, con_advisor: bool) -> list[str]:
    """Codex siempre; el segundo juez solo con --con-advisor y nunca con el
    mismo modelo que la sesión. Sin Codex no hay jurado: falla ruidosa."""
    if not shutil.which(codex_bin()):
        raise RuntimeError(f"Codex no está disponible ({codex_bin()}); sin él no hay jurado")
    lista = ["codex"]
    if con_advisor:
        agente = "advisor-opus" if sesion == "fable" else "advisor"
        modelo = modelo_de_agente(agente)
        if modelo is None or modelo == sesion:
            raise RuntimeError(f"el segundo juez {agente} no existe o usa el mismo modelo que la sesión")
        lista.append(agente)
    return lista


# ───────────────────────────── revisiones mecánicas ─────────────────────────────

def analizar_pendientes(texto: str) -> tuple[list[str], list[str]]:
    """(bloqueantes, diferidos). Formato: PENDIENTE: qué — quién [— se cierra en E#].
    Una plantilla con <marcadores> o la etiqueta sola (la mención de la
    convención) no son pendientes."""
    bloqueantes, diferidos = [], []
    for m in PENDIENTE.finditer(texto):
        frase = texto_plano(m.group(1))
        if not frase or ("<" in frase and ">" in frase):
            continue
        partes = [p.strip() for p in frase.split("—")]
        con_duenio = len(partes) >= 2 and partes[0] and partes[1] and not partes[1].startswith("se cierra")
        diferido = re.search(r"se cierra en E\d+", frase)
        (diferidos if con_duenio and diferido else bloqueantes).append(frase)
    return bloqueantes, diferidos


def _tabla_matriz(texto: str) -> dict[str, list[str]] | None:
    m = re.search(r"<h3>[^<]*Matriz de tipos.*?</h3>.*?<table>(.*?)</table>", texto, re.S)
    if not m:
        return None
    filas = {}
    for fila in re.findall(r"<tr>(.*?)</tr>", m.group(1), re.S):
        celdas = [texto_plano(c) for c in re.findall(r"<td>(.*?)</td>", fila, re.S)]
        if len(celdas) >= 3:
            filas[sin_acentos(celdas[0])] = celdas
    return filas


def _revisar_tipo(tipo: str, celdas: list[str] | None) -> list[str]:
    if celdas is None:
        return [f"matriz: falta el tipo «{tipo}»"]
    aplica, donde = sin_acentos(celdas[1]), celdas[2].strip()
    if aplica.startswith("si"):
        return [] if donde not in ("", "—", "-") else [f"matriz: «{tipo}» aplica sin decir dónde"]
    if aplica.startswith("no aplica porque") and len(aplica) > len("no aplica porque") + 3:
        return []
    return [f"matriz: «{tipo}» no dice «Sí» ni «No aplica porque…» con su razón"]


def revisar_matriz(texto: str) -> list[str]:
    filas = _tabla_matriz(texto)
    if filas is None:
        return ["no hay matriz de tipos de prueba"]
    errores = []
    for tipo, clave in TIPOS_PRUEBA.items():
        celdas = next((c for k, c in filas.items() if clave in k), None)
        errores += _revisar_tipo(tipo, celdas)
    return errores


def raices_del_plan(texto: str, base: Path | None = None) -> list[Path] | None:
    """Las raíces de la línea de metadatos; una raíz relativa cuelga del plan."""
    m = re.search(r"Ra[ií]ces:(.*?)(?:·|</p>)", texto, re.S)
    if not m:
        return None
    raices = []
    for r in re.findall(r"<code>(.*?)</code>", m.group(1)):
        ruta = Path(os.path.expanduser(html.unescape(r)))
        raices.append(ruta if ruta.is_absolute() or base is None else base / ruta)
    return raices or None


def _dentro(ruta: Path, raiz: Path) -> bool:
    try:
        ruta.relative_to(raiz.resolve())
        return True
    except ValueError:
        return False


def _resolver_cita(nombre: str, raices: list[Path]) -> Path | None:
    base = Path(os.path.expanduser(nombre))
    candidatos = [base] if base.is_absolute() else [r / base for r in raices]
    for candidato in candidatos:
        real = candidato.resolve()
        if real.is_file() and any(_dentro(real, r) for r in raices):
            return real
    return None


def _revisar_cita(nombre: str, inicio: int, fin: int, raices: list[Path]) -> list[str]:
    ruta = _resolver_cita(nombre, raices)
    if ruta is None:
        return [f"cita inexistente o fuera de las raíces: {nombre}:{inicio}"]
    try:
        total = len(ruta.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return [f"cita ilegible: {nombre}"]
    if 1 <= inicio <= fin <= total:
        return []
    return [f"cita fuera de rango: {nombre}:{inicio}-{fin} (el archivo tiene {total} líneas)"]


def precheck(texto: str, repo: str | None = None, base: Path | None = None) -> list[str]:
    raices = raices_del_plan(texto, base)
    if raices is None:
        return ["el plan no declara «Raíces:» en su línea de metadatos"]
    if repo:
        raices = [Path(repo).expanduser()] + raices
    errores = [f"raíz inexistente o ilegible: {r}" for r in raices
               if not (r.is_dir() and os.access(r, os.R_OK | os.X_OK))]
    if errores:
        return errores
    for m in CITA.finditer(texto):
        inicio = int(m.group(2))
        errores += _revisar_cita(m.group(1), inicio, int(m.group(3) or inicio), raices)
    _, errores_esperados = extraer_esperados(texto)
    errores += [e for e in errores_esperados if e.startswith("ruta absoluta")]
    return sorted(set(errores))


def revision_mecanica(plan: Path, repo: str | None) -> dict:
    texto = plan.read_text(encoding="utf-8")
    bloqueantes, _ = analizar_pendientes(texto)
    motivos = precheck(texto, repo, plan.parent) + revisar_matriz(texto)
    motivos += [f"PENDIENTE bloqueante: {p}" for p in bloqueantes]
    return {"ok": not motivos, "motivos": motivos, "ts": ahora()}


# ───────────────────────────── esperados ─────────────────────────────

def _bloque_verificacion(texto: str) -> str | None:
    m = re.search(r"<h2>[^<]*Verificaci[oó]n[^<]*</h2>\s*<pre><code>(.*?)</code></pre>", texto, re.S)
    return html.unescape(m.group(1)) if m else None


def _lineas_automatica(bloque: str) -> list[str] | None:
    lineas, dentro = [], False
    for linea in bloque.splitlines():
        cabecera = sin_acentos(linea.strip())
        if cabecera.startswith("# automatica"):
            dentro = True
        elif dentro and cabecera.startswith("# manual"):
            break
        elif dentro:
            lineas.append(linea)
    return lineas if dentro else None


def _unir_comandos(lineas: list[str]) -> list[str]:
    comandos, actual = [], ""
    for linea in lineas:
        limpia = re.sub(r"\s+#\s.*$", "", linea).strip()
        if not limpia or limpia.startswith("#"):
            continue
        if limpia.endswith("\\"):
            actual += limpia[:-1].rstrip() + " "
            continue
        comando, actual = " ".join((actual + limpia).split()), ""
        if not ASIGNACION.fullmatch(comando):
            comandos.append(comando)
    if actual.strip():
        comandos.append(" ".join(actual.split()))
    return comandos


def extraer_esperados(texto: str) -> tuple[list[str], list[str]]:
    """(comandos, errores) del bloque «# Automática» de la Verificación."""
    bloque = _bloque_verificacion(texto)
    if bloque is None:
        return [], ["no hay bloque de Verificación"]
    lineas = _lineas_automatica(bloque)
    if lineas is None:
        return [], ["no hay bloque «# Automática» en la Verificación"]
    comandos = _unir_comandos(lineas)
    errores = [] if comandos else ["el bloque «# Automática» está vacío"]
    errores += [f"ruta absoluta al original en Automática: {c}" for c in comandos
                if "~/.claude" in c or "/Users/" in c]
    return comandos, errores


# ───────────────────────────── registro y estados ─────────────────────────────

def ultima_ronda(d: Path) -> int:
    numeros = [int(m.group(1)) for p in d.glob("ronda-*") if (m := RONDA_ARCHIVO.match(p.name))]
    return max(numeros, default=0)


def registrar_intento(d: Path, n: int, juez: str, estado: str, detalle: str) -> str:
    k = len(list(d.glob(f"ronda-{n}-{juez}-intento-*.json"))) + 1
    escribir_json(d / f"ronda-{n}-{juez}-intento-{k}.json",
                  {"estado": estado, "detalle": detalle, "ts": ahora()})
    return estado


def registrar_veredicto(d: Path, n: int, juez: str, texto: str) -> str:
    estado, datos, errores = cargar_veredicto(texto)
    if estado != "ok":
        return registrar_intento(d, n, juez, "json-invalido", "; ".join(errores) or estado)
    escribir_json(d / f"ronda-{n}-{juez}.json", datos)
    return "ok"


def _accion(accion: str, ronda: int, motivo: str) -> dict:
    return {"accion": accion, "ronda": ronda, "motivo": motivo}


def estado_juez(d: Path, n: int, juez: str, est: dict) -> tuple[str, str | None]:
    """('veredicto', valor) si ya votó; ('accion', accion) si no."""
    veredicto = leer_json(d / f"ronda-{n}-{juez}.json")
    if veredicto is not None:
        return "veredicto", veredicto.get("veredicto")
    intentos = [leer_json(p) or {} for p in sorted(d.glob(f"ronda-{n}-{juez}-intento-*.json"))]
    estados = [i.get("estado") for i in intentos]
    if "fallo-tecnico" in estados:
        return "accion", est["acciones"]["fallo_tecnico"]
    if estados.count("json-invalido") > est["reintentos_json_invalido"]:
        return "accion", est["acciones"]["json_invalido_agotado"]
    return "accion", "llamar-codex" if juez == "codex" else f"llamar-segundo:{juez}"


def _evaluar_jueces(d: Path, n: int, cfg: dict, est: dict) -> dict:
    tipo, valor = estado_juez(d, n, "codex", est)
    if tipo == "accion":
        return _accion(valor, n, "Codex")
    accion = est["codex"].get(valor, "escalar:veredicto-desconocido")
    segundo = cfg.get("segundo")
    if accion == "segundo-o-aprobado" and not segundo:
        return _accion("aprobado", n, "Codex: pasa")
    if accion == "segundo-o-aprobado":
        tipo, valor = estado_juez(d, n, segundo, est)
        if tipo == "accion":
            return _accion(valor, n, segundo)
        accion = est["segundo"].get(valor, "escalar:veredicto-desconocido")
    if accion != "corregir":
        return _accion(accion, n, "veredicto del jurado")
    if n >= est["max_rondas"]:
        return _accion(est["acciones"]["max_rondas"], n, f"{n} rondas sin aprobar")
    return _accion("corregir", n + 1, "nueva ronda")


def siguiente(d: Path) -> dict:
    est = leer_json(ESTADOS)
    if est is None:
        return _accion("escalar:registro", 0, f"no se pudo leer {ESTADOS}")
    faltante = est["acciones"]["registro_faltante"]
    cfg = leer_json(d / "config.json")
    if cfg is None:
        return _accion(faltante, 0, "falta config.json")
    n = ultima_ronda(d)
    if n == 0:
        return _accion("llamar-codex", 1, "primera ronda")
    if not (d / f"ronda-{n}-plan.html").exists():
        return _accion(faltante, n, "falta la copia del plan de la ronda")
    mecanico = leer_json(d / f"ronda-{n}-mecanico.json")
    if mecanico is None:
        return _accion(faltante, n, "falta el registro de la revisión mecánica")
    if not mecanico.get("ok"):
        return _accion(est["acciones"]["mecanico_falla"], n, "; ".join(mecanico.get("motivos", [])))
    return _evaluar_jueces(d, n, cfg, est)


def mejor(d: Path) -> Path | None:
    """Menos graves, luego menos medios; en empate, la ronda más reciente.
    Una ronda sin veredicto válido de Codex nunca es la mejor."""
    cfg = leer_json(d / "config.json") or {}
    candidatos = []
    for n in range(1, ultima_ronda(d) + 1):
        plan = d / f"ronda-{n}-plan.html"
        votos = [leer_json(d / f"ronda-{n}-codex.json")]
        if votos[0] is None or not plan.exists():
            continue
        if cfg.get("segundo"):
            votos.append(leer_json(d / f"ronda-{n}-{cfg['segundo']}.json") or {})
        hallazgos = [h for v in votos for h in v.get("hallazgos", [])]
        graves = sum(h.get("gravedad") == "grave" for h in hallazgos)
        medios = sum(h.get("gravedad") == "medio" for h in hallazgos)
        candidatos.append(((graves, medios, -n), plan))
    return min(candidatos)[1] if candidatos else None


# ───────────────────────────── la ronda con Codex ─────────────────────────────

PROMPT_PLAN = """Eres un juez independiente de un PLAN DE IMPLEMENTACIÓN (ronda {ronda}). No lo escribiste tú y no implementas nada: solo lectura. Responde en español mexicano.

Lee completo el plan: {plan}
Raíces donde viven los archivos que cita: {raices}
Una revisión mecánica ya comprobó que cada cita archivo:línea existe, que la matriz de tipos de prueba tiene forma completa y que los PENDIENTE: tienen dueño. Tú juzgas el fondo: si lo citado dice lo que el plan afirma y si el diseño es correcto.
No leas archivos .env ni nada con secret, token, password o api_key en el nombre.

Rúbrica (cita el ID en cada hallazgo):
{criterios}
{previo}
Veredicto: «pasa» = se puede implementar tal cual; «necesita-trabajo» = arreglos acotados; «reprueba» = el enfoque está mal.
Solo hallazgos accionables, cada uno con su corrección concreta. No inventes objeciones para justificar la revisión: si está bien, «pasa» con hallazgos vacíos o solo menores. En «evidencia» pon los comandos de solo lectura que corriste, tal cual.
"""


def _contexto_previo(d: Path, n: int, cfg: dict) -> str:
    if n <= 1:
        return ""
    hallazgos = []
    for juez in ["codex"] + ([cfg["segundo"]] if cfg.get("segundo") else []):
        voto = leer_json(d / f"ronda-{n - 1}-{juez}.json") or {}
        hallazgos += [{**h, "juez": juez} for h in voto.get("hallazgos", [])]
    respuesta = d / f"ronda-{n}-respuesta.md"
    texto = respuesta.read_text(encoding="utf-8") if respuesta.exists() else "(el autor no dejó respuesta)"
    return (f"\nHallazgos de la ronda {n - 1}, que el autor dice haber atendido; verifica que de verdad"
            f" quedaron resueltos:\n{json.dumps(hallazgos, ensure_ascii=False, indent=1)}\n"
            f"\nRespuesta del autor:\n{texto}\n")


def _prompt_juez_plan(d: Path, n: int, cfg: dict) -> str:
    rubrica = leer_json(RUBRICA) or {"criterios": []}
    criterios = "\n".join(f"- {c['id']}: {c['exige']}. Cómo se verifica: {c['como_se_verifica']}"
                          for c in rubrica["criterios"] if c.get("obligatorio"))
    texto = (d / f"ronda-{n}-plan.html").read_text(encoding="utf-8")
    base = Path(cfg["plan"]).parent
    raices = ", ".join(str(r) for r in (raices_del_plan(texto, base) or [])) or str(cfg.get("repo"))
    return PROMPT_PLAN.format(ronda=n, plan=d / f"ronda-{n}-plan.html", raices=raices,
                              criterios=criterios, previo=_contexto_previo(d, n, cfg))


def _dir_juez(cfg: dict, texto: str) -> str:
    if cfg.get("repo"):
        return cfg["repo"]
    raices = raices_del_plan(texto, Path(cfg["plan"]).parent) or [Path(cfg["plan"]).parent]
    return str(raices[0])


def correr_codex_plan(d: Path, n: int, cfg: dict) -> str:
    texto = (d / f"ronda-{n}-plan.html").read_text(encoding="utf-8")
    salida = d / f".codex-ronda-{n}.json"
    salida.unlink(missing_ok=True)
    cmd = [codex_bin(), "exec", "--model", MODELO_CODEX, "-c", f'model_reasoning_effort="{ESFUERZO_CODEX}"',
           "-s", "read-only", "--skip-git-repo-check", "-C", _dir_juez(cfg, texto),
           "--output-schema", str(ESQUEMA), "-o", str(salida), "-"]
    try:
        r = subprocess.run(cmd, input=_prompt_juez_plan(d, n, cfg), capture_output=True,
                           text=True, timeout=TIMEOUT_CODEX)
    except (subprocess.TimeoutExpired, OSError) as e:
        return registrar_intento(d, n, "codex", "fallo-tecnico", str(e)[:500])
    respuesta = salida.read_text(encoding="utf-8") if salida.exists() else ""
    salida.unlink(missing_ok=True)
    if r.returncode != 0 or not respuesta.strip():
        return registrar_intento(d, n, "codex", "fallo-tecnico", f"rc={r.returncode} {(r.stderr or '')[-400:]}")
    return registrar_veredicto(d, n, "codex", respuesta)


# ───────────────────────────── comandos ─────────────────────────────

def _imprimir(datos) -> None:
    print(json.dumps(datos, ensure_ascii=False, indent=1))


def cmd_valida(a) -> int:
    try:
        texto = Path(a.archivo).read_text(encoding="utf-8")
    except OSError as e:
        print(f"no se pudo leer {a.archivo}: {e}", file=sys.stderr)
        return 1
    estado, datos, errores = cargar_veredicto(texto)
    if estado == "sin-veredicto":
        print("sin veredicto: no hay JSON en la respuesta", file=sys.stderr)
        return 2
    if estado != "ok":
        print("veredicto inválido: " + ("; ".join(errores) or "JSON mal formado o ambiguo"), file=sys.stderr)
        return 1
    if a.salida:
        escribir_json(Path(a.salida), datos)
    print(f"válido: {datos['veredicto']}")
    return 0


def _veredicto_de_archivo(ruta: str | None) -> dict | None:
    if not ruta:
        return None
    estado, datos, _ = cargar_veredicto(Path(ruta).read_text(encoding="utf-8"))
    return datos if estado == "ok" else {"veredicto": "inválido", "evidencia": []}


def cmd_consenso(a) -> int:
    esperados = leer_json(Path(a.esperados)) if a.esperados else []
    if a.fase == "impl" and not isinstance(esperados, list):
        print("--esperados debe ser un archivo JSON con la lista de comandos", file=sys.stderr)
        return 1
    aprobado, motivos = consenso(a.fase, _veredicto_de_archivo(a.codex),
                                 _veredicto_de_archivo(a.segundo), esperados, a.raiz)
    _imprimir({"aprobado": aprobado, "motivos": motivos})
    return 0 if aprobado else 1


def cmd_jueces(a) -> int:
    try:
        _imprimir(jueces(a.sesion, a.con_advisor))
        return 0
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1


def _leer_plan(ruta: str) -> str | None:
    try:
        return Path(ruta).expanduser().read_text(encoding="utf-8")
    except OSError as e:
        print(f"no se pudo leer el plan {ruta}: {e}", file=sys.stderr)
        return None


def cmd_pendientes(a) -> int:
    texto = _leer_plan(a.plan)
    if texto is None:
        return 1
    bloqueantes, diferidos = analizar_pendientes(texto)
    _imprimir({"bloqueantes": bloqueantes, "diferidos": diferidos})
    return 1 if bloqueantes else 0


def cmd_lista_errores(errores: list[str] | None) -> int:
    if errores is None:
        return 1
    _imprimir({"ok": not errores, "errores": errores})
    return 1 if errores else 0


def cmd_matriz(a) -> int:
    texto = _leer_plan(a.plan)
    return cmd_lista_errores(None if texto is None else revisar_matriz(texto))


def cmd_precheck(a) -> int:
    texto = _leer_plan(a.plan)
    base = Path(a.plan).expanduser().resolve().parent
    return cmd_lista_errores(None if texto is None else precheck(texto, a.repo, base))


def cmd_esperados(a) -> int:
    texto = _leer_plan(a.plan)
    if texto is None:
        return 1
    comandos, errores = extraer_esperados(texto)
    if errores:
        _imprimir({"ok": False, "errores": errores})
        return 1
    _imprimir(comandos)
    return 0


def _dir_auditoria(plan: Path, repo: str | None) -> Path:
    proyecto = Path(repo).name if repo else plan.parent.name
    base = AUDITORIAS / (proyecto or "general") / f"{dt.date.today().isoformat()}-{plan.stem}"
    d, k = base, 1
    while d.exists():
        k += 1
        d = base.with_name(f"{base.name}-{k}")
    return d


def cmd_inicia(a) -> int:
    plan = Path(a.plan).expanduser().resolve()
    if not plan.is_file():
        print(f"no existe el plan {plan}", file=sys.stderr)
        return 1
    try:
        lista = jueces(a.sesion, a.con_advisor)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    d = Path(a.dir).expanduser() if a.dir else _dir_auditoria(plan, a.repo)
    if (d / "config.json").exists():
        print(f"ya hay una auditoría en {d}; usa otro --dir", file=sys.stderr)
        return 1
    cfg = {"plan": str(plan), "repo": a.repo, "sesion": a.sesion, "jueces": lista,
           "segundo": lista[1] if len(lista) > 1 else None, "creado": ahora()}
    try:
        escribir_json(d / "config.json", cfg)
    except OSError as e:
        print(f"no se pudo escribir el registro en {d}: {e}", file=sys.stderr)
        return 1
    print(d)
    return 0


def cmd_registra(a) -> int:
    d = Path(a.dir).expanduser()
    if not JUEZ_VALIDO.fullmatch(a.juez) or a.juez in ("plan", "mecanico"):
        print(f"nombre de juez no válido: {a.juez}", file=sys.stderr)
        return 1
    try:
        if a.estado:
            registrar_intento(d, a.ronda, a.juez, a.estado, a.detalle or "")
            return 0
        resultado = registrar_veredicto(d, a.ronda, a.juez, Path(a.archivo).read_text(encoding="utf-8"))
    except OSError as e:
        print(f"no se pudo escribir el registro en {d}: {e}", file=sys.stderr)
        return 1
    if resultado != "ok":
        print("la respuesta no cumple el esquema: quedó registrada como json-invalido", file=sys.stderr)
        return 3
    return 0


def cmd_siguiente(a) -> int:
    _imprimir(siguiente(Path(a.dir).expanduser()))
    return 0


def cmd_ronda(a) -> int:
    d = Path(a.dir).expanduser()
    sig = siguiente(d)
    if sig["accion"] not in ("llamar-codex", "corregir", "corregir-mecanico"):
        _imprimir(sig)
        return 1
    cfg = leer_json(d / "config.json")
    n = sig["ronda"]
    try:
        shutil.copyfile(cfg["plan"], d / f"ronda-{n}-plan.html")
        if a.respuesta:
            shutil.copyfile(a.respuesta, d / f"ronda-{n}-respuesta.md")
        mecanico = revision_mecanica(Path(cfg["plan"]), cfg.get("repo"))
        escribir_json(d / f"ronda-{n}-mecanico.json", mecanico)
    except OSError as e:
        print(f"no se pudo registrar la ronda {n} en {d}: {e}", file=sys.stderr)
        return 1
    if mecanico["ok"]:
        correr_codex_plan(d, n, cfg)
    _imprimir(siguiente(d))
    return 0


def cmd_mejor(a) -> int:
    ruta = mejor(Path(a.dir).expanduser())
    if ruta is None:
        print("ninguna ronda tiene un veredicto válido de Codex", file=sys.stderr)
        return 1
    print(ruta)
    return 0


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jurado.py", description="La compuerta de las auditorías cruzadas.")
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("valida")
    s.add_argument("archivo")
    s.add_argument("--salida")
    s = sub.add_parser("consenso")
    s.add_argument("--fase", choices=["plan", "impl"], required=True)
    s.add_argument("--codex", required=True)
    s.add_argument("--segundo")
    s.add_argument("--esperados")
    s.add_argument("--raiz")
    s = sub.add_parser("jueces")
    s.add_argument("--sesion", choices=["opus", "fable"], required=True)
    s.add_argument("--con-advisor", action="store_true")
    for nombre in ("pendientes", "matriz", "esperados"):
        sub.add_parser(nombre).add_argument("plan")
    s = sub.add_parser("precheck")
    s.add_argument("plan")
    s.add_argument("--repo")
    s = sub.add_parser("inicia")
    s.add_argument("--plan", required=True)
    s.add_argument("--dir")
    s.add_argument("--repo")
    s.add_argument("--sesion", choices=["opus", "fable"], default="opus")
    s.add_argument("--con-advisor", action="store_true")
    s = sub.add_parser("registra")
    s.add_argument("--dir", required=True)
    s.add_argument("--ronda", type=int, required=True)
    s.add_argument("--juez", required=True)
    grupo = s.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--archivo")
    grupo.add_argument("--estado", choices=["fallo-tecnico", "json-invalido"])
    s.add_argument("--detalle")
    for nombre in ("siguiente", "mejor"):
        sub.add_parser(nombre).add_argument("--dir", required=True)
    s = sub.add_parser("ronda")
    s.add_argument("--dir", required=True)
    s.add_argument("--respuesta")
    return p


COMANDOS = {
    "valida": cmd_valida, "consenso": cmd_consenso, "jueces": cmd_jueces,
    "pendientes": cmd_pendientes, "matriz": cmd_matriz, "precheck": cmd_precheck,
    "esperados": cmd_esperados, "inicia": cmd_inicia, "registra": cmd_registra,
    "siguiente": cmd_siguiente, "ronda": cmd_ronda, "mejor": cmd_mejor,
}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return COMANDOS[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
