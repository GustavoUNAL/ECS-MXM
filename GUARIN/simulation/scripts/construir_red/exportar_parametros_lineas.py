# -*- coding: utf-8 -*-
"""
Exporta parametros de lineas (ElmLne) desde PowerFactory.

Columnas:
  Name | In Folder | Grid | Terminal i | Terminal j | Length [km] |
  Type Name | Rtd.Current [kA] | R1 | X1 | B1 | R0 | X0 | B0

Salida:
  GUARIN/simulation/resultados de scripts/construir_red/lineas_parametros.csv
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"
STUDY_CASE = None  # ej. "Estudio de conexion"; None = caso activo

# PowerFactory a menudo ejecuta sin __file__ (copia a Temp)
_FALLBACK_SIM = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion\GUARIN\simulation"
)
try:
    _SIM = Path(__file__).resolve().parents[2]
    if not (_SIM / "scripts").is_dir():
        _SIM = _FALLBACK_SIM
except (NameError, IndexError, OSError):
    _SIM = _FALLBACK_SIM
OUTPUT_DIR = str(_SIM / "resultados de scripts" / "construir_red")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "lineas_parametros.csv")

HEADERS = [
    "Name",
    "In Folder",
    "Grid",
    "Terminal i",
    "Terminal j",
    "Length",
    "Type Name",
    "Rtd.Current",
    "R1",
    "X1",
    "B1",
    "R0",
    "X0",
    "B0",
]

UNITS = [
    "",
    "",
    "",
    "Busbar",
    "Busbar",
    "km",
    "",
    "kA",
    "Ohm",
    "Ohm",
    "uS",
    "Ohm",
    "Ohm",
    "uS",
]

# Anchos de columna para consola (In Folder se muestra corto)
COL_WIDTHS = [10, 18, 8, 12, 12, 8, 18, 12, 10, 10, 8, 10, 10, 8]


def connect_app():
    """Obtiene la aplicacion PowerFactory (interno o engine)."""
    try:
        import powerfactory as pf  # type: ignore

        app = pf.GetApplication()
        if app is not None:
            return app, pf
    except Exception:
        pass

    if PF_PATH not in sys.path:
        sys.path.insert(0, PF_PATH)
    import powerfactory as pf  # type: ignore

    app = pf.GetApplication()
    if app is None:
        raise RuntimeError(
            "No se pudo conectar a PowerFactory. "
            "Ejecuta el script desde PF o configura PF_PATH."
        )
    app.ActivateProject(PROJECT_NAME)
    if STUDY_CASE:
        case = app.GetProjectFolder("study").GetContents(f"{STUDY_CASE}.IntCase")
        if case:
            case[0].Activate()
    return app, pf


def safe_name(obj) -> str:
    if obj is None:
        return ""
    try:
        return str(obj.loc_name)
    except Exception:
        return str(obj)


def safe_attr(obj, attr, default=None):
    if obj is None:
        return default
    try:
        val = getattr(obj, attr)
        return default if val is None else val
    except Exception:
        try:
            return obj.GetAttribute(attr)
        except Exception:
            return default


def get_folder_path(line) -> str:
    """Ruta de carpetas del elemento (In Folder)."""
    try:
        full = line.GetFullName()
        parts = full.split("\\")
        if parts and parts[-1].startswith(line.loc_name):
            parts = parts[:-1]
        return "\\".join(parts)
    except Exception:
        parent = safe_attr(line, "fold_id")
        return safe_name(parent)


def short_folder(path: str) -> str:
    """Ultimas 2 carpetas para mostrar en consola."""
    if not path:
        return ""
    parts = [p for p in path.replace("/", "\\").split("\\") if p]
    if len(parts) <= 2:
        return "\\".join(parts)
    return "\\".join(parts[-2:])


def get_grid_name(line) -> str:
    grid = safe_attr(line, "cpGrid")
    if grid is not None:
        return safe_name(grid)
    try:
        parent = line.GetParent()
        while parent is not None:
            cname = parent.GetClassName() if hasattr(parent, "GetClassName") else ""
            if cname == "ElmNet":
                return safe_name(parent)
            parent = parent.GetParent()
    except Exception:
        pass
    return ""


def get_terminal_name(line, bus_attr: str) -> str:
    """Terminal i/j via cubicle -> cBusBar."""
    try:
        cub = getattr(line, bus_attr)
        if cub is None:
            return ""
        for attr in ("cBusBar", "cterm", "busbar"):
            term = safe_attr(cub, attr)
            if term is not None:
                return safe_name(term)
        return safe_name(cub)
    except Exception:
        return ""


def get_type_params(line):
    """Nombre de tipo, Inom y R/X/B totales."""
    typ = safe_attr(line, "typ_id")
    type_name = safe_name(typ)
    inom = safe_attr(typ, "sline", None)
    if inom is None:
        try:
            inom = line.GetInom(0)
        except Exception:
            inom = ""

    calc_keys = [
        ("R1", ("R1", "c:R1", "cR1")),
        ("X1", ("X1", "c:X1", "cX1")),
        ("B1", ("B1", "c:B1", "cB1")),
        ("R0", ("R0", "c:R0", "cR0")),
        ("X0", ("X0", "c:X0", "cX0")),
        ("B0", ("B0", "c:B0", "cB0")),
    ]
    totals = {}
    got_calc = False
    for out_key, candidates in calc_keys:
        val = None
        for cand in candidates:
            val = safe_attr(line, cand, None)
            if val is not None and val != "":
                break
        if val is not None and val != "":
            totals[out_key] = float(val)
            got_calc = True
        else:
            totals[out_key] = None

    if got_calc and all(v is not None for v in totals.values()):
        return type_name, inom, totals

    length = float(safe_attr(line, "dline", 0) or 0)
    n_parallel = float(safe_attr(line, "nlnum", 1) or 1)

    sections = []
    try:
        sections = line.GetContents("*.ElmLnesec") or []
    except Exception:
        sections = []

    if sections:
        r1 = x1 = b1 = r0 = x0 = b0 = 0.0
        for sec in sections:
            sec_typ = safe_attr(sec, "typ_id") or typ
            sec_len = float(safe_attr(sec, "dline", 0) or 0)
            r1 += float(safe_attr(sec_typ, "rline", 0) or 0) * sec_len
            x1 += float(safe_attr(sec_typ, "xline", 0) or 0) * sec_len
            b1 += float(safe_attr(sec_typ, "bline", 0) or 0) * sec_len
            r0 += float(safe_attr(sec_typ, "rline0", 0) or 0) * sec_len
            x0 += float(safe_attr(sec_typ, "xline0", 0) or 0) * sec_len
            b0 += float(safe_attr(sec_typ, "bline0", 0) or 0) * sec_len
            if not type_name:
                type_name = safe_name(sec_typ)
            if inom in (None, ""):
                inom = safe_attr(sec_typ, "sline", "")
    else:
        r1 = float(safe_attr(typ, "rline", 0) or 0) * length
        x1 = float(safe_attr(typ, "xline", 0) or 0) * length
        b1 = float(safe_attr(typ, "bline", 0) or 0) * length
        r0 = float(safe_attr(typ, "rline0", 0) or 0) * length
        x0 = float(safe_attr(typ, "xline0", 0) or 0) * length
        b0 = float(safe_attr(typ, "bline0", 0) or 0) * length

    if n_parallel > 1:
        r1 /= n_parallel
        x1 /= n_parallel
        r0 /= n_parallel
        x0 /= n_parallel
        b1 *= n_parallel
        b0 *= n_parallel

    defaults = {"R1": r1, "X1": x1, "B1": b1, "R0": r0, "X0": x0, "B0": b0}
    for k, v in defaults.items():
        if totals.get(k) is None:
            totals[k] = v

    return type_name, inom, totals


def fmt(val, decimals=6):
    if val is None or val == "":
        return ""
    try:
        return f"{float(val):.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(val)


def sort_key(row):
    name = row[0]
    try:
        return (0, int(name))
    except ValueError:
        return (1, name)


def pad_row(cells, widths):
    parts = []
    for i, cell in enumerate(cells):
        w = widths[i] if i < len(widths) else 12
        text = str(cell)
        if len(text) > w:
            text = text[: w - 1] + "…"
        parts.append(text.ljust(w))
    return "  ".join(parts)


def log(app, msg: str):
    print(msg)
    try:
        app.PrintPlain(msg)
    except Exception:
        pass


def save_csv(rows) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADERS)
        writer.writerow(UNITS)
        writer.writerows(rows)
    if not os.path.isfile(OUTPUT_FILE):
        raise IOError(f"No se creo el archivo: {OUTPUT_FILE}")
    return OUTPUT_FILE


def print_table(app, rows):
    """Tabla alineada en consola / Output Window de PF."""
    log(app, "")
    log(app, pad_row(HEADERS, COL_WIDTHS))
    log(app, pad_row(UNITS, COL_WIDTHS))
    log(app, "-" * (sum(COL_WIDTHS) + 2 * (len(COL_WIDTHS) - 1)))

    for row in rows:
        # En consola: carpeta corta; en CSV queda la ruta completa
        display = list(row)
        display[1] = short_folder(row[1])
        log(app, pad_row(display, COL_WIDTHS))


def export_lines(app) -> str:
    app.ClearOutputWindow()
    lines = app.GetCalcRelevantObjects("*.ElmLne") or []
    log(app, f"Lineas encontradas: {len(lines)}")
    log(app, f"Guardando en: {OUTPUT_FILE}")

    rows = []
    for line in lines:
        type_name, inom, totals = get_type_params(line)
        length = safe_attr(line, "dline", "")
        rows.append(
            [
                safe_name(line),
                get_folder_path(line),
                get_grid_name(line),
                get_terminal_name(line, "bus1"),
                get_terminal_name(line, "bus2"),
                fmt(length, 4),
                type_name,
                fmt(inom, 4),
                fmt(totals.get("R1")),
                fmt(totals.get("X1")),
                fmt(totals.get("B1")),
                fmt(totals.get("R0")),
                fmt(totals.get("X0")),
                fmt(totals.get("B0")),
            ]
        )

    rows.sort(key=sort_key)

    try:
        path = save_csv(rows)
        size = os.path.getsize(path)
        log(app, f"OK archivo guardado ({size} bytes): {path}")
    except Exception as exc:
        log(app, f"ERROR al guardar CSV: {exc}")
        raise

    print_table(app, rows)

    msg = (
        f"Exportadas {len(rows)} lineas -> {OUTPUT_FILE} "
        f"({datetime.now():%Y-%m-%d %H:%M:%S})"
    )
    log(app, msg)
    return OUTPUT_FILE


def main():
    app, _pf = connect_app()
    export_lines(app)


if __name__ == "__main__":
    main()
