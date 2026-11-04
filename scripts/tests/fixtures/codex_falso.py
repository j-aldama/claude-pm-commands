#!/usr/bin/env python3
"""Codex falso para las pruebas: recibe los mismos argumentos que el real y se
comporta según CODEX_FALSO_MODO. Cada llamada queda en CODEX_FALSO_LOG.

Modos: pasa · necesita-trabajo · reprueba · falla · vacio · invalido ·
ejecuta (corre de verdad los comandos entre <<<COMANDOS y COMANDOS>>>) ·
parcial (ejecuta pero omite el último) · modifica · crea · borra · chmod · pycache
(los últimos cinco tocan la copia y después ejecutan) ·
juzga (D4: no ejecuta nada; anota lo que recibe y aprueba sin evidencia propia) ·
miente (D4: aprueba con evidencia verde inventada para cada comando esperado) ·
herramienta (D4: además reporta en --json que usó una herramienta).
Con CODEX_FALSO_PROMPT=archivo guarda ahí lo que recibió por la entrada estándar.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def argumento(nombre, args):
    return args[args.index(nombre) + 1] if nombre in args else None


def comandos_del_prompt(prompt):
    if "<<<COMANDOS" in prompt:
        bloque = prompt.split("<<<COMANDOS", 1)[1].split("COMANDOS>>>", 1)[0]
    elif "## Comandos esperados" in prompt:
        bloque = prompt.split("## Comandos esperados", 1)[1].split("\n## ", 1)[0]
    else:
        return []
    return [linea.strip() for linea in bloque.splitlines() if linea.strip()]


def tocar_copia(modo, cwd):
    archivos = sorted(p for p in cwd.rglob("*") if p.is_file() and ".git" not in p.parts)
    if modo == "modifica":
        archivos[0].write_text(archivos[0].read_text() + "\n# tocado\n")
    elif modo == "crea":
        (cwd / "nuevo_modulo.py").write_text("X = 1\n")
    elif modo == "borra":
        archivos[-1].unlink()
    elif modo == "chmod":
        archivos[0].chmod(0o777)
    elif modo == "pycache":
        (cwd / "__pycache__").mkdir(exist_ok=True)
        (cwd / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"\0")


def ejecutar(comandos, cwd):
    evidencia = []
    for comando in comandos:
        r = subprocess.run(comando, shell=True, cwd=cwd, capture_output=True, text=True)
        evidencia.append({"comando": comando, "resultado": "verde" if r.returncode == 0 else "rojo",
                          "salida": (r.stdout + r.stderr)[-200:]})
    return evidencia


def main():
    args = sys.argv[1:]
    prompt = sys.stdin.read()
    modo = os.environ.get("CODEX_FALSO_MODO", "pasa")
    log = os.environ.get("CODEX_FALSO_LOG")
    if log:
        with open(log, "a") as f:
            f.write(json.dumps({"args": args, "CLAUDE_HOME": os.environ.get("CLAUDE_HOME"), "cwd": os.getcwd()}) + "\n")
    if os.environ.get("CODEX_FALSO_PROMPT"):
        Path(os.environ["CODEX_FALSO_PROMPT"]).write_text(prompt)
    if modo == "falla":
        print("error simulado: modelo no disponible", file=sys.stderr)
        return 1
    salida = Path(argumento("-o", args))
    if modo == "vacio":
        return 0
    if modo == "invalido":
        salida.write_text("esto no es un veredicto")
        return 0
    cwd = Path(argumento("--cd", args) or argumento("-C", args) or ".")
    evidencia = []
    if modo == "herramienta":
        print(json.dumps({"type": "item.completed", "item": {"id": "item_1", "type": "command_execution"}}))
    if modo == "miente":
        evidencia = [{"comando": c, "resultado": "verde", "salida": "todo bien"} for c in comandos_del_prompt(prompt)]
    elif modo not in ("pasa", "necesita-trabajo", "reprueba", "juzga", "herramienta"):
        tocar_copia(modo, cwd)
        comandos = comandos_del_prompt(prompt)
        evidencia = ejecutar(comandos[:-1] if modo == "parcial" else comandos, cwd)
    veredicto = modo if modo in ("necesita-trabajo", "reprueba") else "pasa"
    hallazgos = [] if veredicto == "pasa" else [{"gravedad": "medio", "criterio": "C2", "que": "falta una prueba",
                                                 "donde": "D1", "porque": "simulado", "correccion": "agregarla"}]
    salida.write_text(json.dumps({"veredicto": veredicto, "resumen": f"modo {modo}",
                                  "hallazgos": hallazgos, "evidencia": evidencia}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
