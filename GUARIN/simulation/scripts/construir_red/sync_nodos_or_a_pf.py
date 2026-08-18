# -*- coding: utf-8 -*-
"""
Sincronizar nodos (ElmTerm) del modelo PowerFactory con los insumos OR.

Acciones:
  1. Renombrar buses equivalentes (p. ej. Terminal(1) -> 10 502_Term)
  2. Crear ElmTerm faltantes en la red Red @ 13,8 kV

Modos (variable MODO):
  "raiz"    — solo nodos raiz prioritarios + renombres (recomendado primero)
  "exacto"  — todos los nombres exactos Terminal i/j de lineas_base.txt

Ejecutar desde PowerFactory con el proyecto Mas X Menos Guarin abierto.
No importa _lib: PowerFactory no define __file__ y no encuentra imports locales.

Salida: resultados de scripts/construir_red/sync_nodos_or_pf.txt
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas fijas — PowerFactory ejecuta sin __file__ (copia a Temp)
# ---------------------------------------------------------------------------
_FALLBACK_GUARIN = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion\GUARIN"
)


def _guarin_dir():
    try:
        cand = Path(__file__).resolve().parents[3]
        if (cand / "simulation" / "scripts").is_dir():
            return cand
    except (NameError, IndexError, OSError):
        pass
    return _FALLBACK_GUARIN


GUARIN = _guarin_dir()
LINEAS_BASE = GUARIN / "data" / "lineas_base.txt"
OUT_DIR = GUARIN / "simulation" / "resultados de scripts" / "construir_red"
OUT_FILE = OUT_DIR / "sync_nodos_or_pf.txt"

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"
V_NOM_KV = 13.8

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
MODO = "raiz"  # "raiz" | "exacto"
DRY_RUN = True  # True = solo reporte; False = aplica cambios en PF
UKNOM_KV = V_NOM_KV
INCLUIR_VARIANTES_OR = True

RENOMBRES_PF_A_OR = {
    "Terminal(1)": "10 502_Term",
}

NODOS_RAIZ_PRIORITARIOS = (
    "4637844",
    "4637852",
    "4637861",
    "4916671",
    "10 502_Term",
)


# ---------------------------------------------------------------------------
# Utilidades (sin imports locales)
# ---------------------------------------------------------------------------
def root_id(node):
    n = (node or "").strip()
    if not n:
        return n
    m = re.fullmatch(r"(\d+)([A-Za-z]+)", n)
    if m:
        return m.group(1)
    return n


def _sort_key(x):
    return (0, int(x)) if x.isdigit() else (1, x)


def load_or_exact_terminals():
    if not LINEAS_BASE.is_file():
        raise FileNotFoundError("No se encontro %s" % LINEAS_BASE)
    nodes = set()
    text = LINEAS_BASE.read_text(encoding="utf-8-sig")
    for ln in text.splitlines()[2:]:
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        for col in (3, 4):
            t = parts[col].strip() if parts[col] else ""
            if t:
                nodes.add(t)
    return nodes


def connect_app():
    try:
        import powerfactory as pf  # type: ignore

        app = pf.GetApplication()
        if app is not None:
            try:
                app.ActivateProject(PROJECT_NAME)
            except Exception:
                pass
            return app
    except Exception:
        pass

    if PF_PATH not in sys.path:
        sys.path.insert(0, PF_PATH)
    import powerfactory as pf  # type: ignore

    app = pf.GetApplication()
    if app is None:
        raise RuntimeError(
            "No se pudo conectar a PowerFactory. "
            "Ejecuta este script desde PF (Execute Python Script)."
        )
    app.ActivateProject(PROJECT_NAME)
    return app


def pf_log(app, msg):
    print(msg)
    try:
        app.PrintPlain(msg)
    except Exception:
        pass


def get_network(app):
    nets = app.GetCalcRelevantObjects("*.ElmNet") or []
    for n in nets:
        if getattr(n, "loc_name", "") == "Red":
            return n
    if not nets:
        raise RuntimeError("No se encontro ElmNet en el proyecto.")
    return nets[0]


def find_pf_terminal(app, name):
    for o in app.GetCalcRelevantObjects("*.ElmTerm") or []:
        if getattr(o, "loc_name", None) == name:
            return o
    return None


def list_pf_terminal_names(app):
    return {
        getattr(o, "loc_name", "")
        for o in app.GetCalcRelevantObjects("*.ElmTerm") or []
        if getattr(o, "loc_name", None)
    }


def create_pf_terminal(net, name, uknom):
    term = net.CreateObject("ElmTerm", name)
    if term is None:
        raise RuntimeError("CreateObject ElmTerm '%s' devolvio None" % name)
    term.uknom = uknom
    try:
        term.iUsage = 0
    except Exception:
        pass
    try:
        term.phtech = 0
    except Exception:
        pass
    return term


def _targets_raiz(or_exact):
    targets = set(NODOS_RAIZ_PRIORITARIOS)
    if INCLUIR_VARIANTES_OR:
        for n in or_exact:
            if root_id(n) in NODOS_RAIZ_PRIORITARIOS:
                targets.add(n)
    return sorted(targets, key=_sort_key)


def _targets_exacto(or_exact, pf_names):
    return sorted(or_exact - pf_names, key=_sort_key)


def apply_renames(app, pf_names, report):
    ok = skip = 0
    report.append("")
    report.append("--- Renombres PF -> OR ---")
    for old, new in RENOMBRES_PF_A_OR.items():
        if old not in pf_names:
            report.append("SKIP %s -> %s: '%s' no existe en PF" % (old, new, old))
            skip += 1
            continue
        if new in pf_names:
            report.append("SKIP %s -> %s: destino '%s' ya existe" % (old, new, new))
            skip += 1
            continue
        term = find_pf_terminal(app, old)
        if term is None:
            report.append("ERROR %s -> %s: objeto no encontrado" % (old, new))
            skip += 1
            continue
        if DRY_RUN:
            report.append("DRY-RUN renombrar %s -> %s" % (old, new))
            ok += 1
        else:
            term.loc_name = new
            pf_names.discard(old)
            pf_names.add(new)
            report.append("OK renombrado %s -> %s" % (old, new))
            ok += 1
    return ok, skip


def apply_creates(app, net, names, pf_names, report):
    created = exists = skip = 0
    report.append("")
    report.append("--- Crear ElmTerm faltantes (modo=%s, uknom=%s kV) ---" % (MODO, UKNOM_KV))
    for name in names:
        if name in pf_names:
            report.append("EXISTS %s" % name)
            exists += 1
            continue
        r = root_id(name)
        same_root = [p for p in pf_names if root_id(p) == r]
        if MODO == "raiz" and same_root and name == r:
            report.append("SKIP %s: ya hay bus raiz %s" % (name, same_root[0]))
            skip += 1
            continue

        if DRY_RUN:
            report.append("DRY-RUN crear ElmTerm '%s'" % name)
            created += 1
            continue

        try:
            create_pf_terminal(net, name, UKNOM_KV)
            pf_names.add(name)
            report.append("OK creado ElmTerm '%s'" % name)
            created += 1
        except Exception as exc:
            report.append("ERROR crear '%s': %s" % (name, exc))
            skip += 1

    return created, exists, skip


def main():
    os.makedirs(str(OUT_DIR), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    or_exact = load_or_exact_terminals()
    app = connect_app()
    try:
        app.ClearOutputWindow()
    except Exception:
        pass

    net = get_network(app)
    pf_names = list_pf_terminal_names(app)

    report = [
        "SYNC NODOS OR -> POWERFACTORY — GUARIN 10-502",
        "Fecha: %s" % stamp,
        "Proyecto: %s" % PROJECT_NAME,
        "Modo: %s | DRY_RUN: %s" % (MODO, DRY_RUN),
        "Red destino: %s | Vnom: %s kV" % (net.loc_name, UKNOM_KV),
        "OR nodos exactos (lineas_base): %s" % len(or_exact),
        "PF ElmTerm antes: %s" % len(pf_names),
        "=" * 70,
    ]

    ren_ok, ren_skip = apply_renames(app, pf_names, report)

    if MODO == "exacto":
        to_create = _targets_exacto(or_exact, pf_names)
    else:
        to_create = _targets_raiz(or_exact)

    report.append("")
    report.append("Nodos a crear (lista %s): %s" % (len(to_create), ", ".join(to_create[:20])))
    if len(to_create) > 20:
        report.append("  ... +%s mas" % (len(to_create) - 20))

    cr_ok, cr_ex, cr_skip = apply_creates(app, net, to_create, pf_names, report)

    pf_after = list_pf_terminal_names(app)
    report.append("")
    report.append("=" * 70)
    report.append("=== RESUMEN ===")
    report.append("Renombres OK:     %s | omitidos: %s" % (ren_ok, ren_skip))
    report.append(
        "Crear OK:         %s | ya existian: %s | omitidos/error: %s" % (cr_ok, cr_ex, cr_skip)
    )
    report.append("PF ElmTerm despues: %s" % len(pf_after))
    if DRY_RUN:
        report.append("")
        report.append("DRY_RUN=True — no se modifico el proyecto.")
        report.append("Cambia DRY_RUN=False y vuelve a ejecutar para aplicar.")
    else:
        report.append("")
        report.append("Cambios aplicados. Ejecuta exportar_parametros_lineas.py y comparar_nodos_or_pf.py")

    text = "\n".join(report) + "\n"
    OUT_FILE.write_text(text, encoding="utf-8")
    for line in report:
        pf_log(app, line)
    pf_log(app, "Reporte: %s" % OUT_FILE)
    return 0


# PowerFactory: __name__ suele ser __main__; si no, igual hay que correr.
try:
    _run = __name__ == "__main__"
except NameError:
    _run = True

if _run:
    try:
        main()
    except Exception as exc:
        print("ERROR FATAL: %s" % exc)
        raise
