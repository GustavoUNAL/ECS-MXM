# -*- coding: utf-8 -*-
"""
Corregir parametros de lineas ya existentes vs insumos OR.

  1. Longitud 825166 y 825167 (quedaron con el dline del duplicado PF)
  2. Crear TypLne 3F_15_CU_4_0_XLPE (el OR usa 4/0; PF no admite '/' en el nombre)
  3. Asignar ese tipo a 828934, 828942, 828945, 828948

  4. Sacar de servicio ElmTerm isla 4916671 (el tramo llega a 4916671A)

Ejecutar desde PowerFactory. DRY_RUN=True primero, luego False.

Salida: resultados de scripts/construir_red/corregir_parametros_lineas.txt
"""
import os
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
OUT_FILE = OUT_DIR / "corregir_parametros_lineas.txt"

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

DRY_RUN = True

# Longitudes OR (km)
LENGTHS = {
    "825166": 0.0165,
    "825167": 0.0299,
}

TYPE_TEMPLATE = "3F_15_CU_2_XLPE"
# Nombre PF (sin '/'). Equivale a 3F_15_CU_4/0_XLPE del OR.
TYPE_NAME = "3F_15_CU_4_0_XLPE"
TYPE_LINES = ("828934", "828942", "828945", "828948")

# Ohm/km y kA sacados de lineas_base (promedio de los 4 tramos OR)
TYPE_PARAMS = {
    "uline": 15.0,
    "sline": 0.295,
    "rline": 0.222,
    "xline": 0.142,
    "bline": 0.0,
    "rline0": 0.335,
    "xline0": 0.358,
    "bline0": 0.0,
}

# Bus raiz creado de mas: la linea 830657 llega a 4916671A, no a 4916671.
ISLAS_OUTSERV = ("4916671",)


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


def set_attr(obj, attr, value):
    try:
        setattr(obj, attr, value)
        return True
    except Exception:
        try:
            obj.SetAttribute(attr, value)
            return True
        except Exception:
            return False


def safe_attr(obj, attr, default=None):
    try:
        val = getattr(obj, attr)
        return default if val is None else val
    except Exception:
        return default


def type_folder(app, template):
    if template is not None:
        try:
            parent = template.GetParent()
            if parent is not None:
                return parent
        except Exception:
            pass
    for key in ("equip", "netmod", "library"):
        try:
            folder = app.GetProjectFolder(key)
        except Exception:
            folder = None
        if folder is not None:
            return folder
    return None


def ensure_cu40_type(app, report):
    existing = find_by_name(app, "TypLne", TYPE_NAME)
    if existing is not None:
        report.append("EXISTS TypLne '%s'" % TYPE_NAME)
        return existing

    tmpl = find_by_name(app, "TypLne", TYPE_TEMPLATE)
    folder = type_folder(app, tmpl)

    if DRY_RUN:
        where = getattr(folder, "loc_name", "?") if folder is not None else "?"
        src = TYPE_TEMPLATE if tmpl is not None else "CreateObject vacio"
        report.append("DRY-RUN crear TypLne '%s' (plantilla=%s, carpeta=%s)" % (TYPE_NAME, src, where))
        report.append("  params: sline=%.3f kA  rline=%.3f  xline=%.3f Ohm/km" % (
            TYPE_PARAMS["sline"], TYPE_PARAMS["rline"], TYPE_PARAMS["xline"]
        ))
        return None

    if folder is None:
        raise RuntimeError("No hay carpeta para crear TypLne.")

    new = None
    if tmpl is not None:
        for meth in ("CreateCopy",):
            try:
                fn = getattr(tmpl, meth, None)
                if fn:
                    new = fn()
                    break
            except Exception:
                new = None
        if new is None:
            try:
                new = folder.AddCopy(tmpl)
            except Exception:
                new = None

    if new is None:
        new = folder.CreateObject("TypLne", TYPE_NAME)
    if new is None:
        raise RuntimeError("No se pudo crear TypLne '%s'" % TYPE_NAME)

    set_attr(new, "loc_name", TYPE_NAME)
    for attr, val in TYPE_PARAMS.items():
        if not set_attr(new, attr, val):
            report.append("AVISO: no se escribio %s=%s en el tipo" % (attr, val))
    report.append("OK creado TypLne '%s'" % TYPE_NAME)
    return new


def apply_lengths(app, report):
    ok = skip = 0
    report.append("")
    report.append("--- Longitudes (dline) ---")
    for name, km in LENGTHS.items():
        line = find_by_name(app, "ElmLne", name)
        if line is None:
            report.append("SKIP %s: no existe ElmLne" % name)
            skip += 1
            continue
        cur = float(safe_attr(line, "dline", 0) or 0)
        if abs(cur - km) < 1e-6:
            report.append("OK %s ya tiene %.4f km" % (name, cur))
            ok += 1
            continue
        if DRY_RUN:
            report.append("DRY-RUN %s: dline %.4f -> %.4f km" % (name, cur, km))
            ok += 1
        else:
            if set_attr(line, "dline", float(km)):
                report.append("OK %s: dline %.4f -> %.4f km" % (name, cur, km))
                ok += 1
            else:
                report.append("ERROR %s: no se pudo escribir dline" % name)
                skip += 1
    return ok, skip


def apply_types(app, typ, report):
    ok = skip = 0
    report.append("")
    report.append("--- Asignar tipo %s ---" % TYPE_NAME)
    for name in TYPE_LINES:
        line = find_by_name(app, "ElmLne", name)
        if line is None:
            report.append("SKIP %s: no existe ElmLne" % name)
            skip += 1
            continue
        cur_typ = safe_attr(line, "typ_id")
        cur_name = getattr(cur_typ, "loc_name", "") if cur_typ is not None else ""
        if cur_name == TYPE_NAME:
            report.append("OK %s ya tiene %s" % (name, TYPE_NAME))
            ok += 1
            continue
        if DRY_RUN:
            report.append("DRY-RUN %s: tipo '%s' -> '%s'" % (name, cur_name or "?", TYPE_NAME))
            ok += 1
            continue
        if typ is None:
            report.append("ERROR %s: TypLne no disponible" % name)
            skip += 1
            continue
        if set_attr(line, "typ_id", typ):
            report.append("OK %s: tipo '%s' -> '%s'" % (name, cur_name or "?", TYPE_NAME))
            ok += 1
        else:
            report.append("ERROR %s: no se pudo asignar typ_id" % name)
            skip += 1
    return ok, skip


def _n_cubicles(term):
    try:
        cubs = term.GetContents("*.StaCubic") or []
        return len(cubs)
    except Exception:
        return -1


def apply_islas(app, report):
    """Saca de servicio ElmTerm huerfanos (sin cubicles) que dejan U=0 en el LF."""
    ok = skip = 0
    report.append("")
    report.append("--- Islas / barras huerfanas (outserv) ---")

    names = {getattr(o, "loc_name", "") for o in app.GetCalcRelevantObjects("*.ElmTerm") or []}

    for name in ISLAS_OUTSERV:
        term = find_by_name(app, "ElmTerm", name)
        if term is None:
            report.append("OK %s: ya no existe" % name)
            ok += 1
            continue
        ncub = _n_cubicles(term)
        cur = safe_attr(term, "outserv")
        alias = name + "A"
        tiene_alias = alias in names
        if cur in (1, True, "1"):
            report.append("OK %s ya esta fuera de servicio (cubicles=%s)" % (name, ncub))
            ok += 1
            continue
        if ncub > 0:
            report.append(
                "SKIP %s: tiene %s cubicle(s); no se toca (revisar a mano)" % (name, ncub)
            )
            skip += 1
            continue
        extra = " (existe %s conectado)" % alias if tiene_alias else ""
        if DRY_RUN:
            report.append("DRY-RUN outserv=1 en ElmTerm '%s'%s" % (name, extra))
            ok += 1
        else:
            if set_attr(term, "outserv", 1):
                report.append("OK outserv=1 en ElmTerm '%s'%s" % (name, extra))
                ok += 1
            else:
                report.append("ERROR no se pudo outserv '%s'" % name)
                skip += 1

    # Reportar otras barras sin cubicles (no se modifican)
    huerfanas = []
    for o in app.GetCalcRelevantObjects("*.ElmTerm") or []:
        n = getattr(o, "loc_name", "")
        if not n or n in ISLAS_OUTSERV:
            continue
        if safe_attr(o, "outserv") in (1, True, "1"):
            continue
        if _n_cubicles(o) == 0:
            huerfanas.append(n)
    if huerfanas:
        report.append(
            "AVISO otras barras sin cubicles (no modificadas): %s"
            % ", ".join(huerfanas[:15])
        )
        if len(huerfanas) > 15:
            report.append("  ... +%s" % (len(huerfanas) - 15))
    return ok, skip


def main():
    os.makedirs(str(OUT_DIR), exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    app = connect_app()
    try:
        app.ClearOutputWindow()
    except Exception:
        pass

    report = [
        "CORREGIR PARAMETROS LINEAS OR -> PF — GUARIN 10-502",
        "Fecha: %s" % stamp,
        "Proyecto: %s" % PROJECT_NAME,
        "DRY_RUN: %s" % DRY_RUN,
        "=" * 70,
        "No se crean puentes 0,0012 km ni la linea 9343 (duplicado de 9344).",
        "Idempotente: si longitudes/tipos ya estan OK, solo reporta EXISTS.",
    ]

    report.append("")
    report.append("--- TypLne CU 4/0 ---")
    typ = ensure_cu40_type(app, report)

    len_ok, len_skip = apply_lengths(app, report)
    typ_ok, typ_skip = apply_types(app, typ, report)
    isla_ok, isla_skip = apply_islas(app, report)

    report.append("")
    report.append("=" * 70)
    report.append("=== RESUMEN ===")
    report.append("Longitudes OK: %s | omitidos: %s" % (len_ok, len_skip))
    report.append("Tipos OK:      %s | omitidos: %s" % (typ_ok, typ_skip))
    report.append("Islas OK:      %s | omitidos: %s" % (isla_ok, isla_skip))
    if DRY_RUN:
        report.append("")
        report.append("DRY_RUN=True — no se modifico el proyecto.")
        report.append("Cambia DRY_RUN=False y vuelve a ejecutar para aplicar.")
    else:
        report.append("")
        report.append("Cambios aplicados. Ejecuta flujo_carga/exportar_flujo_carga.py")

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
