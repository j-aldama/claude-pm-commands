#!/usr/bin/env python3
"""Docker falso para las pruebas de valida_impl.py (D4): acepta las órdenes que usa el ejecutor y anota cada llamada
en DOCKER_FALSO_LOG. `run` corre el comando en la Mac, con los montajes traducidos a sus rutas reales y SOLO el entorno
de los -e (nunca el del cliente), para que las pruebas vean qué entra al contenedor.

Modos (DOCKER_FALSO_MODO): ejecuta (por omisión) · cuelga (el comando no termina) · oom (sale 137 con OOMKilled) ·
toca-origen (escribe en el montaje del origen y después ejecuta) · sin-docker (info falla).
DOCKER_FALSO_MODO_COMANDOS cambia el modo solo para los comandos (no para la sonda).
DOCKER_FALSO_SONDA_MALA=campo hace que la sonda de aislamiento reporte ese campo roto.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SONDA_BUENA = {
    "canario": "ausente", "openai_api_key": "ausente", "escribir_raiz": "error EROFS", "escribir_origen": "error EROFS",
    "escribir_tmp": "ok", "leer_home_anfitrion": "error ENOENT", "marcador_anfitrion": "error ENOENT", "loopback": "ok",
    "internet": "error ENETUNREACH", "dns_lookup": "error EAI_AGAIN", "dns_resolve4": "error ECONNREFUSED",
    "cgroup": "ok pids.max=64 memory.max=536870912 cpu.max=100000 100000", "disco": "error ENOSPC",
    "procesos": "error EAGAIN tras 53 hijos",
}
MALOS = {"canario": "presente", "internet": "ok CONECTO", "marcador_anfitrion": "ok 32", "cgroup": "ok pids.max=max memory.max=max cpu.max=max 100000"}


def estado_dir() -> Path:
    d = Path(os.environ.get("DOCKER_FALSO_ESTADO") or Path(tempfile.gettempdir()) / "docker-falso-estado")
    d.mkdir(parents=True, exist_ok=True)
    return d


def anotar(args):
    log = os.environ.get("DOCKER_FALSO_LOG")
    if log:
        with open(log, "a") as f:
            f.write(json.dumps({"args": args, "canario_en_cliente": bool(os.environ.get("VALIDA_CANARIO"))}) + "\n")


def leer_run(args):
    """--name, montajes, entorno, tmpfs y el comando después de la imagen (la imagen va justo tras -w DIR)."""
    nombre, montajes, entorno, tmpfs, i = None, {}, {}, [], 0
    while i < len(args):
        a = args[i]
        if a == "--name":
            nombre = args[i + 1]; i += 2; continue
        if a == "-v":
            host, dentro, *_ = args[i + 1].split(":")
            montajes[dentro] = host; i += 2; continue
        if a == "-e":
            clave, _, valor = args[i + 1].partition("="); entorno[clave] = valor; i += 2; continue
        if a == "--tmpfs":
            tmpfs.append(args[i + 1].split(":")[0]); i += 2; continue
        if a == "-w":
            return nombre, montajes, entorno, tmpfs, args[i + 3:]
        i += 1 if not a.startswith("--") or a in ("--read-only",) else 2
    return nombre, montajes, entorno, tmpfs, []


def traducir(valor, rutas):
    for dentro, host in sorted(rutas.items(), key=lambda x: -len(x[0])):
        if valor == dentro or valor.startswith(dentro + "/"):
            return host + valor[len(dentro):]
    return valor


def run(args, modo):
    nombre, montajes, entorno, tmpfs, comando = leer_run(args)
    es_sonda = comando[:2] == ["node", "/sonda/sonda-aislamiento.mjs"]
    if not es_sonda:
        modo = os.environ.get("DOCKER_FALSO_MODO_COMANDOS", modo)
    estado = estado_dir() / f"{nombre}.json"
    estado.write_text(json.dumps({"oom": modo == "oom"}))
    if modo == "cuelga":
        time.sleep(600)
    if modo == "oom":
        return 137
    rutas = dict(montajes)
    for punto in tmpfs:
        rutas[punto] = tempfile.mkdtemp(prefix="docker-falso-tmpfs-")
    if es_sonda:
        medido = dict(SONDA_BUENA)
        malo = os.environ.get("DOCKER_FALSO_SONDA_MALA")
        if malo:
            medido[malo] = MALOS.get(malo, "inesperado")
        print(json.dumps(medido))
        return 0
    if modo == "toca-origen" and "/origen" in montajes:
        (Path(montajes["/origen"]) / "tocado.txt").write_text("el ejecutor escribió en el origen\n")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **{k: traducir(v, rutas) for k, v in entorno.items()}}
    return subprocess.run(comando, env=env, cwd=rutas.get("/tmp", tempfile.gettempdir())).returncode


def main():
    args = sys.argv[1:]
    anotar(args)
    modo = os.environ.get("DOCKER_FALSO_MODO", "ejecuta")
    orden = args[0] if args else ""
    if orden == "info":
        if modo == "sin-docker":
            print("Cannot connect to the Docker daemon", file=sys.stderr)
            return 1
        print("29.0.0")
        return 0
    if orden == "image":
        return 0
    if orden == "run":
        return run(args[1:], modo)
    if orden == "inspect":
        archivo = estado_dir() / f"{args[1]}.json"
        print("true" if archivo.exists() and json.loads(archivo.read_text()).get("oom") else "false")
        return 0
    if orden in ("kill", "rm"):
        return 0
    print(f"orden no soportada: {orden}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
