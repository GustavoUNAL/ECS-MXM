# -*- coding: utf-8 -*-
"""
TEST: crea UNA linea de red (tramo real) en PowerFactory.

Linea de prueba (de "lineas por crear"):
  9344 | 1154575 <-> 1154583 | 0,0186 km | 3F_15_CU_2_XLPE

Ejecutar desde PowerFactory con el proyecto Mas X Menos Guarin abierto.
Si funciona, luego ampliamos el script para crear todas.
"""

from __future__ import annotations

import sys

# ---------------------------------------------------------------------------
# Configuracion del TEST (cambiar solo aqui)
# ---------------------------------------------------------------------------
PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

# Linea de prueba
LINE_NAME = "9344"
TERM_I = "1154575"
TERM_J = "1154583"
LENGTH_KM = 0.0186  # usar punto decimal
TYPE_NAME = "3F_15_CU_2_XLPE"

# Si True: solo busca objetos y reporta, NO crea nada
DRY_RUN = False

# Si la linea ya existe, no la recrea
SKIP_IF_EXISTS = True


def connect_app():
    try:
        import powerfactory as pf  # type: ignore

        app = pf.GetApplication()
        if app is not None:
            return app
    except Exception:
        pass

    if PF_PATH not in sys.path:
        sys.path.insert(0, PF_PATH)
    import powerfactory as pf  # type: ignore

    app = pf.GetApplication()
    if app is None:
        raise RuntimeError("No se pudo conectar a PowerFactory.")
    app.ActivateProject(PROJECT_NAME)
    return app


def log(app, msg: str, level: str = "info"):
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


def find_by_name(app, class_name: str, name: str):
    """Busca objeto por nombre exacto (loc_name)."""
    # 1) filtro directo
    objs = app.GetCalcRelevantObjects(f"{name}.{class_name}") or []
    for o in objs:
        if getattr(o, "loc_name", None) == name:
            return o
    # 2) barrido de todos los de la clase
    objs = app.GetCalcRelevantObjects(f"*.{class_name}") or []
    for o in objs:
        if getattr(o, "loc_name", None) == name:
            return o
    return None


def find_line_type(app, type_name: str):
    typ = find_by_name(app, "TypLne", type_name)
    if typ is not None:
        return typ

    # Buscar en carpetas tipicas de tipos / libreria
    folder_keys = ("equip", "netmod", "library", "script")
    for key in folder_keys:
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
            if getattr(o, "loc_name", None) == type_name:
                return o
    return None


def get_network(app):
    nets = app.GetCalcRelevantObjects("*.ElmNet") or []
    if not nets:
        raise RuntimeError("No se encontro ElmNet en el proyecto.")
    # Preferir "Red" si existe
    for n in nets:
        if getattr(n, "loc_name", "") == "Red":
            return n
    return nets[0]


def line_already_exists(app, name: str):
    return find_by_name(app, "ElmLne", name) is not None


def connect_line_to_terminals(line, term_i, term_j, app):
    """
    Conecta ElmLne a dos ElmTerm creando StaCubic en cada terminal
    y apuntando obj_id a la linea.
    """
    cub_i = term_i.CreateObject("StaCubic", f"cub_{line.loc_name}_i")
    cub_j = term_j.CreateObject("StaCubic", f"cub_{line.loc_name}_j")
    if cub_i is None or cub_j is None:
        raise RuntimeError("No se pudieron crear los cubicles StaCubic.")

    cub_i.obj_id = line
    cub_j.obj_id = line

    # Asignacion explicita de extremos (si la API lo permite)
    try:
        line.bus1 = cub_i
        line.bus2 = cub_j
    except Exception as exc:
        log(app, f"Aviso: no se pudo asignar bus1/bus2 directo ({exc})", "warn")

    return cub_i, cub_j


def verify_connection(line, app):
    """Lee Terminal i / j via cubicles."""
    ti = tj = "?"
    try:
        b1 = getattr(line, "bus1", None)
        b2 = getattr(line, "bus2", None)
        if b1 is not None:
            ti = getattr(getattr(b1, "cBusBar", None), "loc_name", None) or getattr(
                b1, "loc_name", "?"
            )
        if b2 is not None:
            tj = getattr(getattr(b2, "cBusBar", None), "loc_name", None) or getattr(
                b2, "loc_name", "?"
            )
    except Exception:
        pass
    log(app, f"Verificacion conexion: Terminal i={ti} | Terminal j={tj}")
    return ti, tj


def create_test_line(app):
    log(app, "=" * 60)
    log(app, "TEST crear linea de red / tramo real")
    log(app, f"  Name      : {LINE_NAME}")
    log(app, f"  Terminal i: {TERM_I}")
    log(app, f"  Terminal j: {TERM_J}")
    log(app, f"  Length    : {LENGTH_KM} km")
    log(app, f"  Type      : {TYPE_NAME}")
    log(app, f"  DRY_RUN   : {DRY_RUN}")
    log(app, "=" * 60)

    # --- Pre-chequeos ---
    if line_already_exists(app, LINE_NAME):
        msg = f"La linea '{LINE_NAME}' YA EXISTE en el proyecto."
        if SKIP_IF_EXISTS:
            log(app, msg + " (SKIP_IF_EXISTS=True -> no se recrea)", "warn")
            existing = find_by_name(app, "ElmLne", LINE_NAME)
            verify_connection(existing, app)
            return existing
        raise RuntimeError(msg + " Borrala o cambia LINE_NAME.")

    term_i = find_by_name(app, "ElmTerm", TERM_I)
    term_j = find_by_name(app, "ElmTerm", TERM_J)
    typ = find_line_type(app, TYPE_NAME)
    net = get_network(app)

    ok = True
    if term_i is None:
        log(app, f"ERROR: no existe terminal '{TERM_I}' (ElmTerm)", "error")
        ok = False
    else:
        log(app, f"OK terminal i: {term_i}")

    if term_j is None:
        log(app, f"ERROR: no existe terminal '{TERM_J}' (ElmTerm)", "error")
        ok = False
    else:
        log(app, f"OK terminal j: {term_j}")

    if typ is None:
        log(app, f"ERROR: no existe tipo de linea '{TYPE_NAME}' (TypLne)", "error")
        ok = False
    else:
        log(app, f"OK tipo: {typ}")

    log(app, f"OK red destino: {net.loc_name}")

    if not ok:
        raise RuntimeError("Faltan objetos. No se crea la linea.")

    if DRY_RUN:
        log(app, "DRY_RUN=True -> no se creo nada. Cambia a False para crear.")
        return None

    # --- Crear ---
    log(app, f"Creando ElmLne '{LINE_NAME}' en {net.loc_name} ...")
    line = net.CreateObject("ElmLne", LINE_NAME)
    if line is None:
        raise RuntimeError("CreateObject('ElmLne') devolvio None.")

    line.dline = float(LENGTH_KM)
    line.typ_id = typ

    cub_i, cub_j = connect_line_to_terminals(line, term_i, term_j, app)
    log(app, f"Cubicles creados: {cub_i.loc_name} / {cub_j.loc_name}")

    verify_connection(line, app)

    log(app, "-" * 60)
    log(app, f"EXITO: linea '{LINE_NAME}' creada.")
    log(app, f"  Length={line.dline} km | Type={getattr(line.typ_id, 'loc_name', '?')}")
    log(app, "Revisa en Data Manager / diagrama. Si esta OK, creamos el resto.")
    log(app, "-" * 60)
    return line


def main():
    app = connect_app()
    try:
        app.ClearOutputWindow()
    except Exception:
        pass
    create_test_line(app)


if __name__ == "__main__":
    main()
