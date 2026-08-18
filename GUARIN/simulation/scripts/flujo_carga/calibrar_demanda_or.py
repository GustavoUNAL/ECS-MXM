# -*- coding: utf-8 -*-
"""
Calibrar demanda del alimentador al perfil OR (Excel 19/03/2024).

Ajusta las cargas de cada caso de estudio para que, CON SSFV FUERA DE
SERVICIO, la corriente en cabecera (linea 804306: 10 502_Term -> 1067001)
coincida con el Excel:

  09:00  61,05 A   1,459 MVA
  12:00  70,41 A   1,683 MVA
  15:00  68,55 A   1,638 MVA

Ejecutar desde PowerFactory. DRY_RUN=True primero, luego False.

Si CASOS_ESTUDIO esta vacio, intenta emparejar IntCase por el nombre
(09 / 12 / 15). Si no hay match, calibra solo el caso activo a 12:00.

Salida: resultados de scripts/flujo_carga/calibrar_demanda_or.txt
"""
import math
import os
import sys
from datetime import datetime
from pathlib import Path

OUT_DIR = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion"
    r"\GUARIN\simulation\resultados de scripts\flujo_carga"
)
OUT_FILE = OUT_DIR / "calibrar_demanda_or.txt"

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

DRY_RUN = False
TOL_PCT = 1.0  # error relativo maximo de I en cabecera
MAX_ITER = 8
LINEA_CABECERA = "804306"
V_KV = 13.8
PV_SYSTEMS = ["SSFV 1 CPW", "SSFV 2 CPW"]

# Nombres exactos de IntCase en PF (dejar "" para auto-detectar)
CASOS_ESTUDIO = {
    "09:00": "Hora 9",
    "12:00": "Hora 12",
    "15:00": "Hora 15",
}

PERFIL_OR = [
    {"hora": "09:00", "I_a": 61.05, "S_mva": 1.459139},
    {"hora": "12:00", "I_a": 70.41, "S_mva": 1.682856},
    {"hora": "15:00", "I_a": 68.55, "S_mva": 1.638498},
]


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
        raise RuntimeError("Ejecuta este script desde PowerFactory.")
    app.ActivateProject(PROJECT_NAME)
    return app


def pf_log(app, msg):
    print(msg)
    try:
        app.PrintPlain(msg)
    except Exception:
        pass


def safe_name(obj):
    try:
        return str(obj.loc_name)
    except Exception:
        return ""


def safe_attr(obj, attr, default=None):
    try:
        val = getattr(obj, attr)
        return default if val is None else val
    except Exception:
        try:
            return obj.GetAttribute(attr)
        except Exception:
            return default


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


def find_by_name(app, name, classes):
    for cls in classes:
        for o in app.GetCalcRelevantObjects("*.%s" % cls) or []:
            if safe_name(o) == name:
                return o
    return None


def _as_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_ampere(val):
    x = _as_float(val)
    if x is None:
        return None
    return x * 1000.0 if abs(x) < 2.0 else x


def _to_mw(val):
    x = _as_float(val)
    if x is None:
        return None
    return x / 1000.0 if abs(x) > 5.0 else x


def list_intcases(app):
    folder = app.GetProjectFolder("study")
    if folder is None:
        return []
    try:
        return list(folder.GetContents("*.IntCase", 1) or [])
    except Exception:
        return list(folder.GetContents("*.IntCase") or [])


def _hora_keys(hora):
    if hora.startswith("09"):
        return ("09:00", "9:00", "09h", "9h", "hora 9", "9am", "09 ")
    if hora.startswith("12"):
        return ("12:00", "12h", "12pm", "12 ", "mediod")
    if hora.startswith("15"):
        return ("15:00", "15h", "15 ", "3:00", "3pm")
    return (hora,)


def match_intcase(app, hora, configured):
    cases = list_intcases(app)
    if configured:
        for c in cases:
            if safe_name(c) == configured:
                return c
        return None
    keys = _hora_keys(hora)
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


def snapshot_loads(app):
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


def apply_load_scale(snap, scale):
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


def set_pv(app, connected):
    for name in PV_SYSTEMS:
        pv = find_by_name(app, name, ("ElmPvsys", "ElmGenstat"))
        if pv is None:
            continue
        set_attr(pv, "outserv", 0 if connected else 1)


def run_ldf(app):
    com = app.GetFromStudyCase("ComLdf")
    if com is None:
        raise RuntimeError("No hay ComLdf en el caso activo.")
    return int(com.Execute())


def persist_scenario(app, hora, report):
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
                report.append("  Creado Operation Scenario: %s" % name)
            except Exception as exc:
                report.append("  No se pudo crear IntScenario: %s" % exc)
    if scen is None:
        try:
            scen = app.GetActiveScenario()
        except Exception:
            scen = None
    if scen is None:
        report.append(
            "  AVISO: no hay Operation Scenario. El ajuste queda en la red "
            "(la ultima hora pisa las anteriores si no hay un scenario por caso)."
        )
        restore_loads(scaled)
        return
    try:
        scen.Activate()
    except Exception:
        pass
    restore_loads(scaled)
    try:
        scen.Save()
        report.append("  Guardado Operation Scenario: %s" % safe_name(scen))
    except Exception as exc:
        report.append("  AVISO: Save() del scenario fallo: %s" % exc)
        restore_loads(scaled)


def read_cabecera(app):
    ln = find_by_name(app, LINEA_CABECERA, ("ElmLne",))
    if ln is None:
        return None
    i = _to_ampere(safe_attr(ln, "m:I:bus1") or safe_attr(ln, "s:I"))
    p = _to_mw(safe_attr(ln, "m:P:bus1"))
    s = None
    if i is not None:
        s = math.sqrt(3.0) * V_KV * i / 1000.0
    return {"I_a": i, "P_mw": p, "S_mva": s, "linea": LINEA_CABECERA}


def calibrar_hora(app, sc, report, snap_base):
    i_tgt = sc["I_a"]
    s_tgt = sc["S_mva"]
    restore_loads(snap_base)
    set_pv(app, connected=False)

    ierr = run_ldf(app)
    cab0 = read_cabecera(app)
    if cab0 is None or cab0["I_a"] is None or cab0["I_a"] <= 0:
        report.append("ERROR: no se pudo leer I en linea %s" % LINEA_CABECERA)
        restore_loads(snap_base)
        return False

    err0 = 100.0 * (cab0["I_a"] - i_tgt) / i_tgt
    report.append(
        "  Base SIN_SSFV: I=%.2f A (OR %.2f, %+0.1f %%)  S=%.3f MVA (OR %.3f)  LDF=%s"
        % (cab0["I_a"], i_tgt, err0, cab0["S_mva"] or 0.0, s_tgt, ierr)
    )

    cum = 1.0
    i_fin = cab0["I_a"]
    s_fin = cab0["S_mva"]
    for niter in range(1, MAX_ITER + 1):
        err = 100.0 * (i_fin - i_tgt) / i_tgt
        if abs(err) <= TOL_PCT:
            break
        cum *= i_tgt / i_fin
        restore_loads(snap_base)
        apply_load_scale(snap_base, cum)
        ierr = run_ldf(app)
        cab = read_cabecera(app)
        if cab is None or cab["I_a"] is None:
            report.append("ERROR en iteracion %s" % niter)
            restore_loads(snap_base)
            return False
        i_fin = cab["I_a"]
        s_fin = cab["S_mva"]
        report.append(
            "  iter %s  escala=%.4f  I=%.2f A  err=%+0.2f %%  S=%.3f MVA"
            % (niter, cum, i_fin, 100.0 * (i_fin - i_tgt) / i_tgt, s_fin or 0.0)
        )

    err_f = 100.0 * (i_fin - i_tgt) / i_tgt
    ok = abs(err_f) <= TOL_PCT
    if DRY_RUN:
        restore_loads(snap_base)
        report.append(
            "  DRY-RUN: se restauraron cargas. Factor a aplicar = %.4f (%s)"
            % (cum, "cumple" if ok else "NO cumple TOL")
        )
    else:
        report.append(
            "  APLICADO escala=%.4f  I=%.2f A  err=%+0.2f %%  %s"
            % (cum, i_fin, err_f, "OK" if ok else "REVISAR")
        )
        persist_scenario(app, sc["hora"], report)
    return ok


def main():
    os.makedirs(str(OUT_DIR), exist_ok=True)
    app = connect_app()
    try:
        app.ClearOutputWindow()
    except Exception:
        pass

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cases = list_intcases(app)
    report = [
        "CALIBRAR DEMANDA CABECERA AL PERFIL OR — GUARIN 10-502",
        "Fecha: %s" % stamp,
        "DRY_RUN: %s" % DRY_RUN,
        "Linea cabecera: %s  |  TOL I = %.1f %%" % (LINEA_CABECERA, TOL_PCT),
        "IntCase en el proyecto: %s"
        % (", ".join(safe_name(c) for c in cases) or "(ninguno)"),
        "=" * 70,
    ]

    snap_base = snapshot_loads(app)
    report.append("Cargas base (en servicio): %s" % len(snap_base))

    ok_all = True
    matched = 0
    for sc in PERFIL_OR:
        hora = sc["hora"]
        configured = (CASOS_ESTUDIO.get(hora) or "").strip()
        icase = match_intcase(app, hora, configured)
        report.append("")
        report.append("--- %s  OR I=%.2f A  S=%.3f MVA ---" % (hora, sc["I_a"], sc["S_mva"]))
        if icase is not None:
            report.append("  IntCase: %s" % safe_name(icase))
            try:
                icase.Activate()
            except Exception as exc:
                report.append("  ERROR al activar: %s" % exc)
                ok_all = False
                continue
            matched += 1
        else:
            report.append("  AVISO: no hay IntCase para esta hora.")
            if hora != "12:00":
                report.append("  SKIP (solo se calibra el caso activo si es 12:00)")
                continue
            report.append("  Se calibra el caso ACTIVO como 12:00")

        if not calibrar_hora(app, sc, report, snap_base):
            ok_all = False

    set_pv(app, connected=True)
    report.append("")
    report.append("=" * 70)
    report.append("IntCase emparejados: %s / 3" % matched)
    report.append("Resultado: %s" % ("OK" if ok_all else "REVISAR"))
    if DRY_RUN:
        report.append("DRY_RUN=True — no se guardaron escalas. Pon False y repetir.")
    else:
        report.append("Cargas calibradas (SIN_SSFV = perfil Excel). SSFV dejado EN SERVICIO.")
        report.append("Ejecuta flujo_carga/exportar_flujo_carga.py")

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
