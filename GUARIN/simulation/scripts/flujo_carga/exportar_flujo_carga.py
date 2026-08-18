# -*- coding: utf-8 -*-
"""
Exporta resultados de Flujo de Carga — MAS X MENOS GUARIN (10-502).

Escenarios (3 horas x 2 estados FV = 6 corridas):
  09:00 / 12:00 / 15:00 segun perfil OR Excel 19/03/2024
  Sin SSFV  -> ElmPvsys "SSFV 1 CPW" y "SSFV 2 CPW" fuera de servicio
  Con SSFV  -> mismos ElmPvsys en servicio

Si AJUSTAR_A_OR=True, escala las cargas para que I en la linea 804306
(SIN_SSFV) coincida con el Excel: 61.05 / 70.41 / 68.55 A.

Exporta a GUARIN/simulation/resultados de scripts/flujo_carga/.
Ejecutar desde PowerFactory con el proyecto abierto (este archivo en disco,
no el objeto ComPython viejo del proyecto).
"""

from __future__ import annotations

import csv
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"
STUDY_CASE = None

# Sistemas fotovoltaicos (ElmPvsys) — se ponen fuera de servicio / en servicio
PV_SYSTEMS = ["SSFV 1 CPW", "SSFV 2 CPW"]

# Demanda de referencia (cabecera) — OR 19/03/2024
SCENARIOS = [
    {"hora": "09:00", "S_mva": 1.459139, "I_a": 61.05},
    {"hora": "12:00", "S_mva": 1.682856, "I_a": 70.41},
    {"hora": "15:00", "S_mva": 1.638498, "I_a": 68.55},
]

# Nombres exactos IntCase ("" = auto por 09/12/15 en el nombre)
CASOS_ESTUDIO = {
    "09:00": "Hora 9",
    "12:00": "Hora 12",
    "15:00": "Hora 15",
}

# Ajustar cargas para que I en cabecera SIN_SSFV = Excel (y dejar el ajuste)
AJUSTAR_A_OR = True
TOL_I_PCT = 1.0
LINEA_CABECERA = "804306"
V_KV = 13.8

# Nodos prioritarios (POC y ruta)
NODOS_CLAVE = [
    "3272966",
    "3272869",
    "3272761",
    "3272664",
    "3272567",
    "1065971",
    "2479567",
]

# Lineas prioritarias (ruta al POC); el CSV incluye TODAS las lineas
LINEAS_CLAVE = ["807671", "807672", "807673", "807674", "807675"]

V_MIN_PU = 0.90
V_MAX_PU = 1.10
LOADING_MAX = 100.0

# Salida fija (PowerFactory a menudo ejecuta una copia en Temp / sin __file__)
OUT_DIR = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion"
    r"\GUARIN\simulation\resultados de scripts\flujo_carga"
)


# ---------------------------------------------------------------------------
# Utilidades PF
# ---------------------------------------------------------------------------
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
    if STUDY_CASE:
        folder = app.GetProjectFolder("study")
        cases = folder.GetContents(f"{STUDY_CASE}.IntCase") if folder else []
        if cases:
            cases[0].Activate()
    return app


def log(app, msg: str):
    print(msg)
    try:
        app.PrintPlain(msg)
    except Exception:
        pass


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


def set_attr(obj, attr, value) -> bool:
    try:
        setattr(obj, attr, value)
        return True
    except Exception:
        try:
            obj.SetAttribute(attr, value)
            return True
        except Exception:
            return False


def find_by_name(app, name: str, classes=None):
    classes = classes or (
        "ElmCoup",
        "ElmSwitch",
        "RelDevice",
        "ElmTerm",
        "ElmLne",
        "ElmTr2",
        "ElmLod",
        "ElmGenstat",
        "ElmPvsys",
    )
    for cls in classes:
        objs = app.GetCalcRelevantObjects(f"*.{cls}") or []
        for o in objs:
            if safe_name(o) == name:
                return o
        # busqueda parcial (sufijos A/B)
        for o in objs:
            n = safe_name(o)
            if n == name or n.startswith(name):
                return o
    # barrido amplio
    for cls in ("ElmCoup", "ElmSwitch", "ElmTerm", "StaCubic"):
        objs = app.GetCalcRelevantObjects(f"*.{cls}") or []
        for o in objs:
            if name.lower() in safe_name(o).lower():
                return o
    return None


def root_bus(name: str) -> str:
    """Quita sufijo de fase A/B/C/G al final."""
    n = (name or "").strip()
    if len(n) > 1 and n[-1] in "ABCGabcdefgh":
        base = n[:-1]
        if base.isdigit() or base.replace("_", "").isalnum():
            return base
    return n


# ---------------------------------------------------------------------------
# Control FV (ElmPvsys: SSFV 1 CPW / SSFV 2 CPW)
# ---------------------------------------------------------------------------
def set_pvsys_outserv(pv, out_of_service: bool) -> str:
    """outserv=1 fuera de servicio; outserv=0 en servicio."""
    val = 1 if out_of_service else 0
    if set_attr(pv, "outserv", val):
        cur = safe_attr(pv, "outserv")
        return f"OK (outserv={cur})"
    return "FALLO al escribir outserv"


def set_pv_connected(app, connected: bool) -> list[str]:
    """
    connected=True  -> FV en servicio (outserv=0)  = CON_SSFV
    connected=False -> FV fuera de servicio (outserv=1) = SIN_SSFV
    """
    msgs = []
    for name in PV_SYSTEMS:
        pv = find_by_name(app, name, classes=("ElmPvsys", "ElmGenstat"))
        if pv is None:
            msgs.append(f"{name}: NO ENCONTRADO (ElmPvsys)")
            continue
        status = set_pvsys_outserv(pv, out_of_service=not connected)
        estado = "EN SERVICIO" if connected else "FUERA DE SERVICIO"
        msgs.append(f"{name} [{pv.GetClassName()}]: {estado} — {status}")
    return msgs


# ---------------------------------------------------------------------------
# Escalado de demanda
# ---------------------------------------------------------------------------
def snapshot_loads(app):
    """Guarda plini/qlini (o scale0) de cargas en servicio."""
    snap = []
    for lod in app.GetCalcRelevantObjects("*.ElmLod") or []:
        if safe_attr(lod, "outserv") in (1, True, "1"):
            continue
        snap.append(
            {
                "obj": lod,
                "plini": safe_attr(lod, "plini"),
                "qlini": safe_attr(lod, "qlini"),
                "slini": safe_attr(lod, "slini"),
                "scale0": safe_attr(lod, "scale0"),
            }
        )
    return snap


def apply_load_scale(snap, scale: float):
    """Escala potencias respecto al snapshot base."""
    for item in snap:
        lod = item["obj"]
        if item["plini"] is not None:
            set_attr(lod, "plini", float(item["plini"]) * scale)
        if item["qlini"] is not None:
            set_attr(lod, "qlini", float(item["qlini"]) * scale)
        if item["slini"] is not None and item["plini"] is None:
            set_attr(lod, "slini", float(item["slini"]) * scale)
        if item["scale0"] is not None and item["plini"] is None and item["slini"] is None:
            set_attr(lod, "scale0", float(item["scale0"]) * scale)


def restore_loads(snap):
    for item in snap:
        lod = item["obj"]
        if item["plini"] is not None:
            set_attr(lod, "plini", item["plini"])
        if item["qlini"] is not None:
            set_attr(lod, "qlini", item["qlini"])
        if item["slini"] is not None:
            set_attr(lod, "slini", item["slini"])
        if item["scale0"] is not None:
            set_attr(lod, "scale0", item["scale0"])


def list_intcases(app):
    folder = app.GetProjectFolder("study")
    if folder is None:
        return []
    try:
        return list(folder.GetContents("*.IntCase", 1) or [])
    except Exception:
        return list(folder.GetContents("*.IntCase") or [])


def match_intcase(app, hora: str):
    configured = (CASOS_ESTUDIO.get(hora) or "").strip()
    cases = list_intcases(app)
    if configured:
        for c in cases:
            if safe_name(c) == configured:
                return c
        return None
    keys = {
        "09:00": ("09:00", "9:00", "09h", "9h", "hora 9", "9am"),
        "12:00": ("12:00", "12h", "12pm", "mediod"),
        "15:00": ("15:00", "15h", "3:00", "3pm"),
    }.get(hora, (hora,))
    scored = []
    for c in cases:
        n = safe_name(c).lower().replace(".", ":")
        for k in keys:
            if k.lower() in n:
                scored.append((len(k), c))
                break
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def read_cabecera(app):
    ln = find_by_name(app, LINEA_CABECERA, classes=("ElmLne",))
    if ln is None:
        return {"I_a": None, "P_mw": None, "S_mva": None}
    i = _to_ampere(safe_attr(ln, "m:I:bus1") or safe_attr(ln, "s:I"))
    p = _to_mw(safe_attr(ln, "m:P:bus1"))
    s = (math.sqrt(3.0) * V_KV * i / 1000.0) if i else None
    return {"I_a": i, "P_mw": p, "S_mva": s}


def persist_scenario(app, hora, log_fn):
    """Guarda las cargas actuales en un Operation Scenario por hora."""
    scaled = snapshot_loads(app)
    folder = None
    for key in ("scen", "scheme", "ops"):
        try:
            folder = app.GetProjectFolder(key)
        except Exception:
            folder = None
        if folder is not None:
            break
    name = "Demanda OR %s" % hora.replace(":", "h")
    scen = None
    if folder is not None:
        try:
            contents = list(folder.GetContents("*.IntScenario", 1) or [])
        except Exception:
            contents = list(folder.GetContents("*.IntScenario") or [])
        for s in contents:
            if safe_name(s) == name:
                scen = s
                break
        if scen is None:
            try:
                scen = folder.CreateObject("IntScenario", name)
                log_fn("  Creado Operation Scenario: %s" % name)
            except Exception as exc:
                log_fn("  No se pudo crear IntScenario: %s" % exc)
    if scen is None:
        try:
            scen = app.GetActiveScenario()
        except Exception:
            scen = None
    if scen is None:
        log_fn("  AVISO: ajuste no ligado a Operation Scenario (puede ser global).")
        restore_loads(scaled)
        return
    try:
        scen.Activate()
    except Exception:
        pass
    restore_loads(scaled)
    try:
        scen.Save()
        log_fn("  Guardado Operation Scenario: %s" % safe_name(scen))
    except Exception as exc:
        log_fn("  AVISO: Save() del scenario fallo: %s" % exc)
        restore_loads(scaled)


def ajustar_cabecera(app, i_tgt: float, log_fn, snap_base) -> float:
    """Escala cargas desde snap_base (PV off) hasta I_cabecera ~ Excel."""
    restore_loads(snap_base)
    set_pv_connected(app, connected=False)
    run_ldf(app)
    cab = read_cabecera(app)
    i0 = cab["I_a"]
    if not i0:
        log_fn("  AVISO: no se leyo I en %s" % LINEA_CABECERA)
        return 1.0
    cum = 1.0
    i_now = i0
    for it in range(8):
        err = 100.0 * (i_now - i_tgt) / i_tgt
        log_fn(
            "  ajuste cabecera iter %s  escala=%.4f  I=%.2f A  OR=%.2f  err=%+.2f %%"
            % (it, cum, i_now, i_tgt, err)
        )
        if abs(err) <= TOL_I_PCT:
            break
        cum *= i_tgt / i_now
        restore_loads(snap_base)
        apply_load_scale(snap_base, cum)
        run_ldf(app)
        cab = read_cabecera(app)
        i_now = cab["I_a"] or i_now
    return cum


# ---------------------------------------------------------------------------
# Load Flow + lectura de resultados
# ---------------------------------------------------------------------------
def run_ldf(app) -> int:
    com = app.GetFromStudyCase("ComLdf")
    if com is None:
        raise RuntimeError("No se encontro ComLdf en el caso de estudio")
    return int(com.Execute())


def read_voltages(app):
    rows = []
    for term in app.GetCalcRelevantObjects("*.ElmTerm") or []:
        if safe_attr(term, "outserv") in (1, True, "1"):
            continue
        name = safe_name(term)
        u = _as_float(safe_attr(term, "m:u"))
        if u is None:
            continue
        un = safe_attr(term, "uknom") or safe_attr(term, "e:uknom")
        energ = 1 if u >= 0.05 else 0
        rows.append(
            {
                "terminal": name,
                "root": root_bus(name),
                "u_pu": u,
                "uknom_kV": un,
                "clave": 1 if root_bus(name) in NODOS_CLAVE or name in NODOS_CLAVE else 0,
                "energizado": energ,
            }
        )
    return rows


def read_lines(app):
    rows = []
    for ln in app.GetCalcRelevantObjects("*.ElmLne") or []:
        if safe_attr(ln, "outserv") in (1, True, "1"):
            continue
        name = safe_name(ln)
        loading = safe_attr(ln, "c:loading")
        if loading is None:
            loading = safe_attr(ln, "m:loading")
        i = _to_ampere(safe_attr(ln, "m:I:bus1") or safe_attr(ln, "s:I"))
        p = _to_mw(safe_attr(ln, "m:P:bus1") or safe_attr(ln, "c:Ploss"))
        loading_f = _as_float(loading)
        rows.append(
            {
                "linea": name,
                "loading_pct": loading_f,
                "I_A": i,
                "P_bus1_MW": p,
                "clave": 1 if name in LINEAS_CLAVE else 0,
            }
        )
    return rows


def read_trafos(app):
    rows = []
    for tr in app.GetCalcRelevantObjects("*.ElmTr2") or []:
        if safe_attr(tr, "outserv") in (1, True, "1"):
            continue
        name = safe_name(tr)
        loading = safe_attr(tr, "c:loading") or safe_attr(tr, "m:loading")
        p = _to_mw(safe_attr(tr, "m:P:bushv") or safe_attr(tr, "m:P:buslv"))
        rows.append({"trafo": name, "loading_pct": _as_float(loading), "P_MW": p})
    return rows


def _as_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_ampere(val):
    """PF suele entregar m:I en kA. Si |I|<2 se interpreta kA."""
    x = _as_float(val)
    if x is None:
        return None
    return x * 1000.0 if abs(x) < 2.0 else x


def _to_mw(val):
    """PF m:P a veces viene en kW. Si |P|>5 se interpreta kW -> MW."""
    x = _as_float(val)
    if x is None:
        return None
    return x / 1000.0 if abs(x) > 5.0 else x


def _to_kw(val) -> float:
    """Normaliza perdidas a kW. Este circuito ronda 5 kW."""
    x = float(val)
    ax = abs(x)
    if ax < 0.5:
        return x * 1000.0  # MW
    if ax < 200:
        return x  # kW
    return x / 1000.0  # W


def read_losses_kw(app) -> float | None:
    """Perdidas del alimentador en kW."""
    for net in app.GetCalcRelevantObjects("*.ElmNet") or []:
        for attr in ("c:Losses", "c:Ploss", "m:Ploss"):
            v = safe_attr(net, attr)
            if v is None:
                continue
            try:
                kw = _to_kw(v)
                if 0.05 <= abs(kw) <= 100:
                    return kw
            except (TypeError, ValueError):
                continue

    # Suma |P1+P2| de lineas (perdida) + trafos, ya normalizado a MW
    mw = 0.0
    n = 0
    for ln in app.GetCalcRelevantObjects("*.ElmLne") or []:
        if safe_attr(ln, "outserv") in (1, True, "1"):
            continue
        p1 = _to_mw(safe_attr(ln, "m:P:bus1"))
        p2 = _to_mw(safe_attr(ln, "m:P:bus2"))
        pl = _as_float(safe_attr(ln, "c:Ploss") or safe_attr(ln, "m:Ploss"))
        if p1 is not None and p2 is not None:
            mw += abs(p1 + p2)
            n += 1
        elif pl is not None:
            mw += abs(_to_kw(pl) / 1000.0)
            n += 1
    for tr in app.GetCalcRelevantObjects("*.ElmTr2") or []:
        if safe_attr(tr, "outserv") in (1, True, "1"):
            continue
        pl = _as_float(safe_attr(tr, "c:Ploss") or safe_attr(tr, "m:Ploss"))
        if pl is None:
            continue
        mw += abs(_to_kw(pl) / 1000.0)
        n += 1
    if n == 0:
        return None
    return mw * 1000.0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = connect_app()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log(app, f"=== Export Flujo de Carga GUARIN — {stamp} ===")

    # Verificar sistemas FV (ElmPvsys)
    for name in PV_SYSTEMS:
        pv = find_by_name(app, name, classes=("ElmPvsys", "ElmGenstat"))
        if pv is None:
            log(app, f"AVISO: no se encontro {name} (ElmPvsys). Revisa el nombre en el modelo.")
        else:
            log(app, f"OK PV: {name} [{pv.GetClassName()}] outserv={safe_attr(pv, 'outserv')}")

    rows_resumen = []
    rows_v = []
    rows_ln = []
    rows_tr = []
    rows_loss = []
    report = [
        f"FLUJO DE CARGA — GUARIN / circuito 10-502",
        f"Fecha: {stamp}",
        f"Sistemas FV (ElmPvsys): {', '.join(PV_SYSTEMS)} "
        f"(outserv=1 sin FV, outserv=0 con FV)",
        f"Cabecera: linea {LINEA_CABECERA} vs Excel OR (I/S)",
        f"AJUSTAR_A_OR: {AJUSTAR_A_OR}",
        f"IntCase: {[safe_name(c) for c in list_intcases(app)]}",
        f"Escenarios: {[s['hora'] for s in SCENARIOS]}",
        "=" * 72,
    ]

    snap_base = snapshot_loads(app)
    log(app, f"Cargas base (en servicio): {len(snap_base)}")

    try:
        for sc in SCENARIOS:
            hora = sc["hora"]
            icase = match_intcase(app, hora)
            if icase is not None:
                icase.Activate()
                log(app, f"\n--- Hora {hora} | IntCase={safe_name(icase)} | OR I={sc['I_a']} A ---")
            else:
                log(app, f"\n--- Hora {hora} | (caso activo) | OR I={sc['I_a']} A ---")

            scale = 1.0
            if AJUSTAR_A_OR:
                scale = ajustar_cabecera(app, sc["I_a"], lambda m: log(app, m), snap_base)
                persist_scenario(app, hora, lambda m: log(app, m))
                log(app, f"  escala final cargas = {scale:.4f}")

            for con_fv in (False, True):
                estado = "CON_SSFV" if con_fv else "SIN_SSFV"
                msgs = set_pv_connected(app, connected=con_fv)
                for m in msgs:
                    log(app, f"  {m}")

                ierr = run_ldf(app)
                ok = ierr == 0
                log(app, f"  Load Flow {estado}: {'OK' if ok else f'ERROR codigo {ierr}'}")

                # Tensiones
                volts = read_voltages(app)
                for v in volts:
                    rows_v.append(
                        {
                            "hora": hora,
                            "estado": estado,
                            "terminal": v["terminal"],
                            "root": v["root"],
                            "u_pu": f"{v['u_pu']:.6f}",
                            "uknom_kV": v["uknom_kV"],
                            "clave": v["clave"],
                            "energizado": v["energizado"],
                            "cumple": (
                                1
                                if v["energizado"] and V_MIN_PU <= v["u_pu"] <= V_MAX_PU
                                else ("" if not v["energizado"] else 0)
                            ),
                            "ldf_ok": 1 if ok else 0,
                        }
                    )

                # Lineas
                lines = read_lines(app)
                for ln in lines:
                    ld = ln["loading_pct"]
                    rows_ln.append(
                        {
                            "hora": hora,
                            "estado": estado,
                            "linea": ln["linea"],
                            "loading_pct": f"{ld:.4f}" if ld is not None else "",
                            "I_A": f"{ln['I_A']:.4f}" if ln["I_A"] is not None else "",
                            "P_bus1_MW": f"{ln['P_bus1_MW']:.6f}" if ln["P_bus1_MW"] is not None else "",
                            "clave": ln["clave"],
                            "cumple": 1 if (ld is None or ld <= LOADING_MAX) else 0,
                            "ldf_ok": 1 if ok else 0,
                        }
                    )

                # Trafos
                trafos = read_trafos(app)
                for tr in trafos:
                    ld = tr["loading_pct"]
                    rows_tr.append(
                        {
                            "hora": hora,
                            "estado": estado,
                            "trafo": tr["trafo"],
                            "loading_pct": f"{ld:.4f}" if ld is not None else "",
                            "P_MW": f"{tr['P_MW']:.6f}" if tr["P_MW"] is not None else "",
                            "cumple": 1 if (ld is None or ld <= LOADING_MAX) else 0,
                            "ldf_ok": 1 if ok else 0,
                        }
                    )

                # Perdidas
                loss = read_losses_kw(app)
                rows_loss.append(
                    {
                        "hora": hora,
                        "estado": estado,
                        "perdidas_kW": f"{loss:.4f}" if loss is not None else "",
                        "ldf_ok": 1 if ok else 0,
                    }
                )

                # Resumen nodos clave
                v_clave = [v for v in volts if v["clave"] == 1]
                energ = [v for v in volts if v.get("energizado", 1)]
                u_min = min((v["u_pu"] for v in energ), default=None)
                u_max = max((v["u_pu"] for v in energ), default=None)
                n_out = sum(1 for v in energ if not (V_MIN_PU <= v["u_pu"] <= V_MAX_PU))
                ld_max_line = max(
                    (ln["loading_pct"] for ln in lines if ln["loading_pct"] is not None),
                    default=None,
                )
                ld_max_tr = max(
                    (tr["loading_pct"] for tr in trafos if tr["loading_pct"] is not None),
                    default=None,
                )
                u_poc = next(
                    (v["u_pu"] for v in volts if root_bus(v["terminal"]) == "3272966" or v["terminal"].startswith("3272966")),
                    None,
                )
                cab = read_cabecera(app)
                i_err = None
                if cab["I_a"] and estado == "SIN_SSFV":
                    i_err = 100.0 * (cab["I_a"] - sc["I_a"]) / sc["I_a"]

                rows_resumen.append(
                    {
                        "hora": hora,
                        "estado": estado,
                        "S_or_mva": sc["S_mva"],
                        "I_or_a": sc["I_a"],
                        "I_cab_a": f"{cab['I_a']:.4f}" if cab["I_a"] is not None else "",
                        "S_cab_mva": f"{cab['S_mva']:.4f}" if cab["S_mva"] is not None else "",
                        "P_cab_mw": f"{cab['P_mw']:.4f}" if cab["P_mw"] is not None else "",
                        "err_I_pct": f"{i_err:.2f}" if i_err is not None else "",
                        "escala_cargas": f"{scale:.4f}",
                        "ldf_ok": 1 if ok else 0,
                        "u_poc_pu": f"{u_poc:.6f}" if u_poc is not None else "",
                        "u_min_pu": f"{u_min:.6f}" if u_min is not None else "",
                        "u_max_pu": f"{u_max:.6f}" if u_max is not None else "",
                        "n_barras_fuera_banda": n_out,
                        "loading_max_linea_pct": f"{ld_max_line:.4f}" if ld_max_line is not None else "",
                        "loading_max_trafo_pct": f"{ld_max_tr:.4f}" if ld_max_tr is not None else "",
                        "perdidas_kW": f"{loss:.4f}" if loss is not None else "",
                        "n_nodos_clave": len(v_clave),
                    }
                )

                report.append(
                    f"{hora} {estado}: LDF={'OK' if ok else ierr} | "
                    f"Icab={cab['I_a']} A (OR {sc['I_a']}) | "
                    f"Scab={cab['S_mva']} MVA (OR {sc['S_mva']}) | "
                    f"Upoc={u_poc} | Umin={u_min} | fuera_banda={n_out} | "
                    f"Lmax_ln={ld_max_line} | Lmax_tr={ld_max_tr} | Ploss_kW={loss}"
                )

    finally:
        set_pv_connected(app, connected=True)
        log(
            app,
            "SSFV 1/2 CPW dejados EN SERVICIO (outserv=0). "
            "Cargas: ultima hora del perfil OR (activa el IntCase 12:00 para el pico).",
        )

    # Comparativos sin vs con (delta) en resumen extra
    deltas = []
    for hora in [s["hora"] for s in SCENARIOS]:
        sin = next((r for r in rows_resumen if r["hora"] == hora and r["estado"] == "SIN_SSFV"), None)
        con = next((r for r in rows_resumen if r["hora"] == hora and r["estado"] == "CON_SSFV"), None)
        if not sin or not con:
            continue

        def f(x):
            try:
                return float(x) if x != "" else None
            except Exception:
                return None

        du = None
        if f(sin["u_poc_pu"]) is not None and f(con["u_poc_pu"]) is not None:
            du = f(con["u_poc_pu"]) - f(sin["u_poc_pu"])
        dloss = None
        if f(sin["perdidas_kW"]) is not None and f(con["perdidas_kW"]) is not None:
            dloss = f(con["perdidas_kW"]) - f(sin["perdidas_kW"])
        dld = None
        if f(sin["loading_max_linea_pct"]) is not None and f(con["loading_max_linea_pct"]) is not None:
            dld = f(con["loading_max_linea_pct"]) - f(sin["loading_max_linea_pct"])
        dtr = None
        if f(sin["loading_max_trafo_pct"]) is not None and f(con["loading_max_trafo_pct"]) is not None:
            dtr = f(con["loading_max_trafo_pct"]) - f(sin["loading_max_trafo_pct"])
        deltas.append(
            {
                "hora": hora,
                "dU_poc_pu": f"{du:.6f}" if du is not None else "",
                "dP_loss_kW": f"{dloss:.4f}" if dloss is not None else "",
                "dLoading_max_linea_pct": f"{dld:.4f}" if dld is not None else "",
                "dLoading_max_trafo_pct": f"{dtr:.4f}" if dtr is not None else "",
            }
        )
        report.append(
            f"DELTA {hora}: dUpoc={du} p.u. | dPloss={dloss} kW | "
            f"dLmax_ln={dld} | dLmax_tr={dtr}"
        )

    write_csv(
        OUT_DIR / "resumen.csv",
        [
            "hora",
            "estado",
            "S_or_mva",
            "I_or_a",
            "I_cab_a",
            "S_cab_mva",
            "P_cab_mw",
            "err_I_pct",
            "escala_cargas",
            "ldf_ok",
            "u_poc_pu",
            "u_min_pu",
            "u_max_pu",
            "n_barras_fuera_banda",
            "loading_max_linea_pct",
            "loading_max_trafo_pct",
            "perdidas_kW",
            "n_nodos_clave",
        ],
        rows_resumen,
    )
    write_csv(
        OUT_DIR / "deltas.csv",
        [
            "hora",
            "dU_poc_pu",
            "dP_loss_kW",
            "dLoading_max_linea_pct",
            "dLoading_max_trafo_pct",
        ],
        deltas,
    )
    write_csv(
        OUT_DIR / "tensiones.csv",
        ["hora", "estado", "terminal", "root", "u_pu", "uknom_kV", "clave", "energizado", "cumple", "ldf_ok"],
        rows_v,
    )
    write_csv(
        OUT_DIR / "lineas.csv",
        ["hora", "estado", "linea", "loading_pct", "I_A", "P_bus1_MW", "clave", "cumple", "ldf_ok"],
        rows_ln,
    )
    write_csv(
        OUT_DIR / "trafos.csv",
        ["hora", "estado", "trafo", "loading_pct", "P_MW", "cumple", "ldf_ok"],
        rows_tr,
    )
    write_csv(
        OUT_DIR / "perdidas.csv",
        ["hora", "estado", "perdidas_kW", "ldf_ok"],
        rows_loss,
    )

    report.append("")
    report.append(f"Archivos en: {OUT_DIR}")
    (OUT_DIR / "reporte.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    log(app, f"Export listo → {OUT_DIR}")
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
