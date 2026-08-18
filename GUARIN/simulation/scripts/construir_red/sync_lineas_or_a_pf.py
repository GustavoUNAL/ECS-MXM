# -*- coding: utf-8 -*-
"""
Sincronizar lineas (ElmLne) del diagrama/OR que faltan en PowerFactory.

Acciones:
  1. Renombrar duplicados PF -> ID OR (p. ej. 10396 -> 825166)
  2. Crear las 11 lineas del diagrama que no existen

Ejecutar desde PowerFactory con el proyecto Mas X Menos Guarin abierto.
Primero DRY_RUN=True; si el reporte esta bien, DRY_RUN=False.

Salida: resultados de scripts/construir_red/sync_lineas_or_pf.txt
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path

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
OUT_DIR = GUARIN / "simulation" / "resultados de scripts" / "construir_red"
OUT_FILE = OUT_DIR / "sync_lineas_or_pf.txt"

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

DRY_RUN = True  # True = solo reporte; False = aplica cambios
SKIP_IF_EXISTS = True

# Duplicados actuales en PF -> nombre del diagrama/OR
RENOMBRES_PF_A_OR = {
    "9343": "9344",
    "10396": "825166",
    "10397": "825167",
    "26921": "828934",
    "26920": "828942",
    "5303": "828945",
    "5305": "828948",
}

# Si el nombre OR del tipo no existe en PF, probar estos alias
TYPE_ALIASES = {
    "3F_15_CU_4/0_XLPE": (
        "3F_15_CU_4/0_XLPE",
        "3F_15_CU_4_0_XLPE",
        "3F_15_CU_4/0",
        "CU_4/0",
    ),
}

# 11 lineas del diagrama (extremos OR; el script resuelve sufijos A/B/C)
LINEAS = [
    {"name": "9344", "ti": "1154575", "tj": "1154583", "km": 0.0186, "typ": "3F_15_CU_2_XLPE"},
    {"name": "825166", "ti": "1101277B", "tj": "1103431", "km": 0.0165, "typ": "3F_15_CU_2_XLPE"},
    {"name": "825167", "ti": "1103431", "tj": "1103458A", "km": 0.0299, "typ": "3F_15_CU_2_XLPE"},
    {"name": "828934", "ti": "1101447A", "tj": "1101455A", "km": 0.0493, "typ": "3F_15_CU_4/0_XLPE"},
    {"name": "828942", "ti": "1101455E", "tj": "1101471A", "km": 0.0652, "typ": "3F_15_CU_4/0_XLPE"},
    {"name": "828945", "ti": "1101471A", "tj": "1101480A", "km": 0.0708, "typ": "3F_15_CU_4/0_XLPE"},
    {"name": "828948", "ti": "1101480A", "tj": "2479567B", "km": 0.0493, "typ": "3F_15_CU_4/0_XLPE"},
    {"name": "830653", "ti": "1101382E", "tj": "4637844", "km": 0.0165, "typ": "3F_15_CU_2_XLPE"},
    {"name": "830654", "ti": "4637844", "tj": "4637852", "km": 0.0092, "typ": "3F_15_CU_2_XLPE"},
    {"name": "830655", "ti": "4637852", "tj": "4637861", "km": 0.0205, "typ": "3F_15_CU_2_XLPE"},
    {"name": "830657", "ti": "4637861", "tj": "4916671A", "km": 0.0114, "typ": "3F_15_CU_2_XLPE"},
]


def root_id(node):
    n = (node or "").strip()
    m = re.fullmatch(r"(\d+)([A-Za-z]+)", n)
    return m.group(1) if m else n


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


def pf_log(app, msg, level="info"):
    print(msg)
    try:
        if level == "error":
            app.PrintError(msg)
        elif level == "warn":
            app.PrintWarn(msg)
        else:
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


def find_by_name(app, class_name, name):
    name = (name or "").strip()
    if not name:
        return None
    for o in app.GetCalcRelevantObjects("%s.%s" % (name, class_name)) or []:
        if getattr(o, "loc_name", None) == name:
            return o
    for o in app.GetCalcRelevantObjects("*.%s" % class_name) or []:
        if getattr(o, "loc_name", None) == name:
            return o
    return None


def iter_line_types(app):
    seen = set()
    for o in app.GetCalcRelevantObjects("*.TypLne") or []:
        n = getattr(o, "loc_name", None)
        if n and n not in seen:
            seen.add(n)
            yield o
    for key in ("equip", "netmod", "library", "script"):
        try:
            folder = app.GetProjectFolder(key)
        except Exception:
            folder = None
        if folder is None:
            continue
        try:
            contents = folder.GetContents("*.TypLne", 1) or []
        except Exception:
            contents = []
        for o in contents:
            n = getattr(o, "loc_name", None)
            if n and n not in seen:
                seen.add(n)
                yield o


def find_line_type(app, type_name):
    candidates = list(TYPE_ALIASES.get(type_name, (type_name,)))
    if type_name not in candidates:
        candidates.insert(0, type_name)
    for cand in candidates:
        typ = find_by_name(app, "TypLne", cand)
        if typ is not None:
            return typ
    needle = type_name.replace("/", "_").lower()
    for o in iter_line_types(app):
        n = (o.loc_name or "").lower().replace("/", "_")
        if needle in n or n in needle:
            return o
        if "cu_4" in n and "4/0" in type_name.replace("_", "/"):
            return o
    return None


def find_line_effective(app, name):
    """Objeto ElmLne por nombre OR, o por el nombre PF que se va a renombrar."""
    obj = find_by_name(app, "ElmLne", name)
    if obj is not None:
        return obj
    for old, new in RENOMBRES_PF_A_OR.items():
        if new == name:
            return find_by_name(app, "ElmLne", old)
    return None


def resolve_terminal(app, wanted):
    """Prueba nombre exacto OR y luego bus raiz (sin A/B/C)."""
    wanted = (wanted or "").strip()
    tried = []
    for cand in (wanted, root_id(wanted)):
        if not cand or cand in tried:
            continue
        tried.append(cand)
        obj = find_by_name(app, "ElmTerm", cand)
        if obj is not None:
            return obj, cand, tried
    return None, None, tried


def term_name_of_line(line, bus_attr):
    try:
        cub = getattr(line, bus_attr, None)
        if cub is None:
            return ""
        for attr in ("cBusBar", "cterm", "busbar"):
            term = getattr(cub, attr, None)
            if term is not None:
                return getattr(term, "loc_name", "") or ""
        return getattr(cub, "loc_name", "") or ""
    except Exception:
        return ""


def list_line_names(app):
    return {
        getattr(o, "loc_name", "")
        for o in app.GetCalcRelevantObjects("*.ElmLne") or []
        if getattr(o, "loc_name", None)
    }


def line_endpoints_key(line):
    a = root_id(term_name_of_line(line, "bus1"))
    b = root_id(term_name_of_line(line, "bus2"))
    return tuple(sorted((a, b)))


def find_parallel(app, ti_name, tj_name, skip_name=None):
    key = tuple(sorted((root_id(ti_name), root_id(tj_name))))
    if not key[0] or not key[1]:
        return None
    for o in app.GetCalcRelevantObjects("*.ElmLne") or []:
        n = getattr(o, "loc_name", "")
        if skip_name and n == skip_name:
            continue
        if line_endpoints_key(o) == key:
            return o
    return None


def connect_line_to_terminals(line, term_i, term_j):
    cub_i = term_i.CreateObject("StaCubic", "cub_%s_i" % line.loc_name)
    cub_j = term_j.CreateObject("StaCubic", "cub_%s_j" % line.loc_name)
    if cub_i is None or cub_j is None:
        raise RuntimeError("No se pudieron crear StaCubic para %s" % line.loc_name)
    cub_i.obj_id = line
    cub_j.obj_id = line
    try:
        line.bus1 = cub_i
        line.bus2 = cub_j
    except Exception:
        pass
    return cub_i, cub_j


def apply_renames(app, names, report):
    ok = skip = 0
    report.append("")
    report.append("--- Renombres PF -> OR ---")
    for old, new in RENOMBRES_PF_A_OR.items():
        if old not in names:
            report.append("SKIP %s -> %s: '%s' no existe en PF" % (old, new, old))
            skip += 1
            continue
        if new in names:
            report.append("SKIP %s -> %s: destino '%s' ya existe" % (old, new, new))
            skip += 1
            continue
        obj = find_by_name(app, "ElmLne", old)
        if obj is None:
            report.append("ERROR %s -> %s: objeto no encontrado" % (old, new))
            skip += 1
            continue
        if DRY_RUN:
            report.append("DRY-RUN renombrar %s -> %s" % (old, new))
        else:
            obj.loc_name = new
            report.append("OK renombrado %s -> %s" % (old, new))
        names.discard(old)
        names.add(new)
        ok += 1
    return ok, skip


def apply_types(app, report):
    """Tras renombrar: homologar TypLne si el tipo OR existe en PF."""
    ok = skip = 0
    report.append("")
    report.append("--- Tipo de linea (si el TypLne existe en PF) ---")
    for spec in LINEAS:
        name = spec["name"]
        line = find_line_effective(app, name)
        if line is None:
            continue
        current = ""
        try:
            typ_now = getattr(line, "typ_id", None)
            current = getattr(typ_now, "loc_name", "") if typ_now is not None else ""
        except Exception:
            current = ""
        if current == spec["typ"]:
            report.append("OK %s ya tiene tipo %s" % (name, current))
            ok += 1
            continue
        typ = find_line_type(app, spec["typ"])
        if typ is None:
            report.append(
                "AVISO %s: tipo OR '%s' no esta en PF (actual: '%s'). Se deja el tipo actual."
                % (name, spec["typ"], current or "?")
            )
            skip += 1
            continue
        used = getattr(typ, "loc_name", spec["typ"])
        if DRY_RUN:
            report.append("DRY-RUN %s: tipo '%s' -> '%s'" % (name, current or "?", used))
            ok += 1
        else:
            line.typ_id = typ
            report.append("OK %s: tipo '%s' -> '%s'" % (name, current or "?", used))
            ok += 1
    return ok, skip


def apply_creates(app, net, names, report):
    created = exists = skip = 0
    report.append("")
    report.append("--- Crear ElmLne faltantes ---")
    for spec in LINEAS:
        name = spec["name"]
        if name in names:
            report.append("EXISTS %s (ya en PF o cubierta por renombre)" % name)
            exists += 1
            continue

        term_i, used_i, tried_i = resolve_terminal(app, spec["ti"])
        term_j, used_j, tried_j = resolve_terminal(app, spec["tj"])
        typ = find_line_type(app, spec["typ"])

        problems = []
        if term_i is None:
            problems.append("no hay ElmTerm %s (probado: %s)" % (spec["ti"], ", ".join(tried_i)))
        if term_j is None:
            problems.append("no hay ElmTerm %s (probado: %s)" % (spec["tj"], ", ".join(tried_j)))
        if typ is None:
            problems.append("no hay TypLne '%s'" % spec["typ"])
        if problems:
            report.append("SKIP %s: %s" % (name, "; ".join(problems)))
            skip += 1
            continue

        parallel = find_parallel(app, used_i, used_j, skip_name=name)
        if parallel is not None:
            report.append(
                "SKIP %s: ya hay linea '%s' entre %s y %s (posible duplicado)"
                % (name, parallel.loc_name, used_i, used_j)
            )
            skip += 1
            continue

        msg = "ElmLne '%s' | %s <-> %s | %.4f km | %s" % (
            name,
            used_i,
            used_j,
            spec["km"],
            spec["typ"],
        )
        if DRY_RUN:
            report.append("DRY-RUN crear %s" % msg)
            created += 1
            continue

        try:
            line = net.CreateObject("ElmLne", name)
            if line is None:
                raise RuntimeError("CreateObject devolvio None")
            line.dline = float(spec["km"])
            line.typ_id = typ
            connect_line_to_terminals(line, term_i, term_j)
            names.add(name)
            report.append("OK creado %s" % msg)
            created += 1
        except Exception as exc:
            report.append("ERROR crear '%s': %s" % (name, exc))
            skip += 1

    return created, exists, skip


def main():
    os.makedirs(str(OUT_DIR), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app = connect_app()
    try:
        app.ClearOutputWindow()
    except Exception:
        pass

    net = get_network(app)
    names = list_line_names(app)

    report = [
        "SYNC LINEAS OR -> POWERFACTORY — GUARIN 10-502",
        "Fecha: %s" % stamp,
        "Proyecto: %s" % PROJECT_NAME,
        "DRY_RUN: %s" % DRY_RUN,
        "Red destino: %s" % net.loc_name,
        "PF ElmLne antes: %s" % len(names),
        "Lineas objetivo: %s" % len(LINEAS),
        "=" * 70,
    ]

    ren_ok, ren_skip = apply_renames(app, names, report)
    typ_ok, typ_skip = apply_types(app, report)
    cr_ok, cr_ex, cr_skip = apply_creates(app, net, names, report)

    after = list_line_names(app)
    report.append("")
    report.append("=" * 70)
    report.append("=== RESUMEN ===")
    report.append("Renombres OK:     %s | omitidos: %s" % (ren_ok, ren_skip))
    report.append("Tipos OK/aviso:   %s | sin TypLne OR: %s" % (typ_ok, typ_skip))
    report.append(
        "Crear OK:         %s | ya existian: %s | omitidos/error: %s" % (cr_ok, cr_ex, cr_skip)
    )
    report.append("PF ElmLne despues: %s" % len(after))
    if DRY_RUN:
        report.append("")
        report.append("DRY_RUN=True — no se modifico el proyecto.")
        report.append("Cambia DRY_RUN=False y vuelve a ejecutar para aplicar.")
    else:
        report.append("")
        report.append("Cambios aplicados. Ejecuta exportar_parametros_lineas.py")

    text = "\n".join(report) + "\n"
    OUT_FILE.write_text(text, encoding="utf-8")
    for line in report:
        pf_log(app, line)
    pf_log(app, "Reporte: %s" % OUT_FILE)
    return 0


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
