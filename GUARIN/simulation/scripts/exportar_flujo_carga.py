# -*- coding: utf-8 -*-
"""
Exporta resultados de Flujo de Carga — MAS X MENOS GUARIN (10-502).

Escenarios operacionales (3 horas x 2 estados FV = 6 corridas):
  09:00 / 12:00 / 15:00
  Sin SSFV  -> ElmPvsys "SSFV 1 CPW" y "SSFV 2 CPW" fuera de servicio (outserv=1)
  Con SSFV  -> mismos ElmPvsys en servicio (outserv=0)

Exporta a GUARIN/simulation/results/flujo_carga/:
  resumen.csv
  tensiones.csv
  lineas.csv
  trafos.csv
  perdidas.csv
  reporte.txt

Ejecutar desde PowerFactory con el proyecto abierto.
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
STUDY_CASE = None

# Sistemas fotovoltaicos (ElmPvsys) — se ponen fuera de servicio / en servicio
PV_SYSTEMS = ["SSFV 1 CPW", "SSFV 2 CPW"]

# Demanda de referencia (cabecera) — OR 19/03/2024
# El modelo se asume calibrado en la hora BASE; las demas se escalan.
SCENARIOS = [
    {"hora": "09:00", "S_mva": 1.459139, "I_a": 61.05},
    {"hora": "12:00", "S_mva": 1.682856, "I_a": 70.41},
    {"hora": "15:00", "S_mva": 1.638498, "I_a": 68.55},
]
BASE_HORA = "12:00"  # hora a la que esta calibrado el modelo de cargas

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

# Salida: results/flujo_carga/ (fallback si PF ejecuta desde Temp)
_OUT_REL = Path(__file__).resolve().parents[1] / "results" / "flujo_carga"
_OUT_FALLBACK = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion"
    r"\GUARIN\simulation\results\flujo_carga"
)
OUT_DIR = _OUT_REL if (_OUT_REL.parent.parent / "scripts").is_dir() else _OUT_FALLBACK


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
    """Guarda plini/qlini (o scale0) de todas las cargas."""
    snap = []
    for lod in app.GetCalcRelevantObjects("*.ElmLod") or []:
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
        name = safe_name(term)
        u = safe_attr(term, "m:u")
        if u is None:
            continue
        try:
            u = float(u)
        except (TypeError, ValueError):
            continue
        un = safe_attr(term, "uknom") or safe_attr(term, "e:uknom")
        rows.append(
            {
                "terminal": name,
                "root": root_bus(name),
                "u_pu": u,
                "uknom_kV": un,
                "clave": 1 if root_bus(name) in NODOS_CLAVE or name in NODOS_CLAVE else 0,
            }
        )
    return rows


def read_lines(app):
    rows = []
    for ln in app.GetCalcRelevantObjects("*.ElmLne") or []:
        name = safe_name(ln)
        loading = safe_attr(ln, "c:loading")
        if loading is None:
            loading = safe_attr(ln, "m:loading")
        i = safe_attr(ln, "m:I:bus1") or safe_attr(ln, "s:I")
        p = safe_attr(ln, "m:P:bus1") or safe_attr(ln, "c:Ploss")
        try:
            loading_f = float(loading) if loading is not None else None
        except (TypeError, ValueError):
            loading_f = None
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
        name = safe_name(tr)
        loading = safe_attr(tr, "c:loading") or safe_attr(tr, "m:loading")
        p = safe_attr(tr, "m:P:bushv") or safe_attr(tr, "m:P:buslv")
        try:
            loading_f = float(loading) if loading is not None else None
        except (TypeError, ValueError):
            loading_f = None
        rows.append({"trafo": name, "loading_pct": loading_f, "P_MW": p})
    return rows


def read_losses_kw(app) -> float | None:
    """Suma perdidas de lineas + trafos (kW)."""
    total = 0.0
    found = False
    for ln in app.GetCalcRelevantObjects("*.ElmLne") or []:
        pl = safe_attr(ln, "c:Ploss") or safe_attr(ln, "m:Ploss")
        if pl is None:
            continue
        try:
            total += float(pl) * 1000.0  # MW -> kW si viene en MW
            # Heuristica: si valor > 5, probablemente ya esta en kW o W muy chico
            found = True
        except (TypeError, ValueError):
            continue
    # Si la suma es ridicula (> 1e4 kW para este circuito), asumir que Ploss ya era kW
    if found and total > 5000:
        total = total / 1000.0
    for tr in app.GetCalcRelevantObjects("*.ElmTr2") or []:
        pl = safe_attr(tr, "c:Ploss") or safe_attr(tr, "m:Ploss")
        if pl is None:
            continue
        try:
            val = float(pl)
            total += val * 1000.0 if abs(val) < 5 else val
            found = True
        except (TypeError, ValueError):
            continue
    # Intento via resultado global del estudio
    if not found:
        for attr in ("c:Losses", "m:Losses", "c:Ptot", "c:Ploss"):
            # buscar en ElmNet
            for net in app.GetCalcRelevantObjects("*.ElmNet") or []:
                v = safe_attr(net, attr)
                if v is not None:
                    try:
                        return float(v) * (1000.0 if abs(float(v)) < 50 else 1.0)
                    except (TypeError, ValueError):
                        pass
    return total if found else None


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

    base_S = next(s["S_mva"] for s in SCENARIOS if s["hora"] == BASE_HORA)
    snap = snapshot_loads(app)
    log(app, f"Cargas en snapshot: {len(snap)} | Base demanda {BASE_HORA} = {base_S} MVA")

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
        f"Escenarios: {[s['hora'] for s in SCENARIOS]}",
        "=" * 72,
    ]

    try:
        for sc in SCENARIOS:
            hora = sc["hora"]
            scale = sc["S_mva"] / base_S
            apply_load_scale(snap, scale)
            log(app, f"\n--- Hora {hora} | escala cargas = {scale:.4f} ({sc['S_mva']} MVA) ---")

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
                            "cumple": 1 if V_MIN_PU <= v["u_pu"] <= V_MAX_PU else 0,
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
                            "I_A": ln["I_A"],
                            "P_bus1_MW": ln["P_bus1_MW"],
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
                            "P_MW": tr["P_MW"],
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
                u_min = min((v["u_pu"] for v in volts), default=None)
                u_max = max((v["u_pu"] for v in volts), default=None)
                n_out = sum(1 for v in volts if not (V_MIN_PU <= v["u_pu"] <= V_MAX_PU))
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

                rows_resumen.append(
                    {
                        "hora": hora,
                        "estado": estado,
                        "S_cabecera_MVA": sc["S_mva"],
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
                    f"Upoc={u_poc} | Umin={u_min} | Umax={u_max} | "
                    f"fuera_banda={n_out} | Lmax_ln={ld_max_line} | "
                    f"Lmax_tr={ld_max_tr} | Ploss_kW={loss}"
                )

    finally:
        # Restaurar cargas y dejar FV cerrado (estado operativo)
        restore_loads(snap)
        set_pv_connected(app, connected=True)
        log(app, "Cargas restauradas; SSFV 1/2 CPW dejados EN SERVICIO (outserv=0).")

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
            "S_cabecera_MVA",
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
        ["hora", "estado", "terminal", "root", "u_pu", "uknom_kV", "clave", "cumple", "ldf_ok"],
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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR FATAL: {exc}")
        raise
