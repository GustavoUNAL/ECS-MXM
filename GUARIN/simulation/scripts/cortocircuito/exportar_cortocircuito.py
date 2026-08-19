# -*- coding: utf-8 -*-
"""
Cortocircuito IEC 60909 — MAS X MENOS GUARIN (10-502).

Calcula falla trifasica y monofasica en nodos de la ruta al POC,
con SSFV fuera de servicio y en servicio.

Ejecutar desde PowerFactory (proyecto abierto). Pegar el wrapper
simulation/scripts/exportar_cortocircuito.py en un ComPython.

Salida: resultados de scripts/cortocircuito/
  cortocircuito.csv
  resumen.csv
  reporte.txt
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

PV_SYSTEMS = ["SSFV 1 CPW", "SSFV 2 CPW"]
CASO_CC = "Hora 12"  # IEC 60909 no depende de la carga; se usa el caso pico

# Aporte inversores (metodologia del estudio): Ikss = 1.5 In
K_SC_INV = 1.5
S_AC_KVA = 120.0
V_LV_KV = 0.22
V_HV_KV = 13.2

NODOS = [
    "3272966",
    "3272869",
    "3272761",
    "3272664",
    "3272567",
    "1065971",
    "2479567",
    "10 502_Term",
    "1067001",
]

# Tipo de falla: strings IEC primero (PF a veces ignora el entero 0
# si el comando ya quedo en 'spgf').
FALLAS = [
    {"id": "3ph", "label": "Trifasica", "codes": ("3psc", 0)},
    {"id": "1ph", "label": "Monofasica", "codes": ("spgf", 3, 2)},
]

OUT_DIR = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion"
    r"\GUARIN\simulation\resultados de scripts\cortocircuito"
)


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


def log(app, msg):
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
            n = safe_name(o)
            if n == name or n.startswith(name):
                return o
    return None


def activate_case(app, name):
    folder = app.GetProjectFolder("study")
    if folder is None:
        return None
    try:
        cases = list(folder.GetContents("*.IntCase", 1) or [])
    except Exception:
        cases = list(folder.GetContents("*.IntCase") or [])
    for c in cases:
        if safe_name(c) == name:
            c.Activate()
            return c
    return None


def set_pv(app, connected):
    msgs = []
    for name in PV_SYSTEMS:
        pv = find_by_name(app, name, ("ElmPvsys", "ElmGenstat"))
        if pv is None:
            msgs.append("%s: NO ENCONTRADO" % name)
            continue
        set_attr(pv, "outserv", 0 if connected else 1)
        msgs.append("%s outserv=%s" % (name, safe_attr(pv, "outserv")))
    return msgs


def configure_pvsys_sc(app):
    """Ikss = 1.5 In en cada ElmPvsys (criterio del estudio / inversor)."""
    msgs = []
    for name in PV_SYSTEMS:
        pv = find_by_name(app, name, ("ElmPvsys", "ElmGenstat"))
        if pv is None:
            msgs.append("%s: no encontrado para Ikss" % name)
            continue
        applied = []
        for attr, val in (
            ("ikss", K_SC_INV),
            ("c_k", K_SC_INV),
            ("K", K_SC_INV),
            ("rtox", 0.1),
            ("i_p2p", 1),
        ):
            if set_attr(pv, attr, val):
                applied.append("%s=%s" % (attr, safe_attr(pv, attr)))
        msgs.append("%s [%s] SC: %s" % (name, pv.GetClassName(), ", ".join(applied) or "sin atributos SC"))
    return msgs


def expected_contrib_ka():
    i_n = S_AC_KVA / (3.0 ** 0.5 * V_LV_KV)
    i_sc_lv = K_SC_INV * i_n
    i_sc_hv = i_sc_lv * (V_LV_KV / V_HV_KV)
    return i_sc_hv / 1000.0


def _as_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_ka(val):
    x = _as_float(val)
    if x is None:
        return None
    # PF a veces entrega A. Si |x| > 80 se interpreta A -> kA
    return x / 1000.0 if abs(x) > 80 else x


def _to_mva(val):
    x = _as_float(val)
    if x is None:
        return None
    return x / 1000.0 if abs(x) > 5000 else x


def configure_iec(com):
    for attr, val in (
        ("iopt_mde", 1),  # IEC 60909 en PF 2022+
        ("iopt_allbus", 1),
        ("iopt_cnf", 0),
        ("iopt_cur", 0),
        ("cmax", 1.1),
        ("Rf", 0.0),
        ("Xf", 0.0),
        # Incluir aporte de convertidores / generacion estatica (IEC 60909-0:2016)
        ("iopt_fsc", 1),
        ("iopt_conv", 1),
        ("iopt_feed", 1),
        ("i_shcgen", 1),
        ("iopt_pe", 1),
        ("iopt_gen", 1),
        ("iopt_infeed", 1),
    ):
        set_attr(com, attr, val)
    mde = safe_attr(com, "iopt_mde")
    if mde not in (0, 1):
        set_attr(com, "iopt_mde", 0)


def set_fault_type(com, codes):
    """Fuerza el tipo de falla y verifica que PF lo haya aceptado."""
    last = None
    for attr in ("iopt_shc", "iopt_asc"):
        for code in codes:
            if not set_attr(com, attr, code):
                continue
            cur = safe_attr(com, attr)
            last = (attr, code, cur)
            if _fault_matches(cur, code):
                return True, "%s=%s" % (attr, cur)
    if last:
        return True, "%s set %s -> %s (sin verificar)" % last
    return False, "sin atributo"


def _fault_matches(cur, code):
    if cur is None:
        return False
    if cur == code:
        return True
    a, b = str(cur).lower(), str(code).lower()
    if a == b:
        return True
    aliases = {
        "3psc": ("0", "3ph", "3p", "3psc"),
        "spgf": ("2", "3", "1ph", "spgf", "1psc"),
        0: ("0", "3psc", "3ph"),
        3: ("3", "spgf", "1ph"),
        2: ("2", "spgf", "1ph"),
    }
    want = aliases.get(code, (str(code),))
    return a in want or b in {str(x).lower() for x in want}


def get_com_shc(app):
    com = app.GetFromStudyCase("ComShc")
    if com is None:
        raise RuntimeError("No hay ComShc en el caso de estudio")
    configure_iec(com)
    return com


def read_term_sc(term):
    ik = None
    ip = None
    sk = None
    for a in ("m:Ikss", "m:Ik", "m:Iks"):
        ik = _to_ka(safe_attr(term, a))
        if ik is not None:
            break
    for a in ("m:ip", "m:Ip"):
        ip = _to_ka(safe_attr(term, a))
        if ip is not None:
            break
    for a in ("m:Skss", "m:Sk", "m:Sks"):
        sk = _to_mva(safe_attr(term, a))
        if sk is not None:
            break
    return ik, ip, sk


def pick_terminal(app, name):
    exact = None
    partial = None
    for term in app.GetCalcRelevantObjects("*.ElmTerm") or []:
        n = safe_name(term)
        if n == name:
            exact = term
            break
        if partial is None and (n.startswith(name) or name in n):
            partial = term
    return exact or partial


def run_shc(app, falla):
    com = get_com_shc(app)
    ok, det = set_fault_type(com, falla["codes"])
    if not ok:
        return False, "no se pudo fijar tipo de falla %s" % falla["id"]
    ierr = int(com.Execute())
    if ierr != 0:
        return False, "ComShc codigo %s (%s)" % (ierr, det)
    return True, "OK (%s)" % det


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    os.makedirs(str(OUT_DIR), exist_ok=True)
    app = connect_app()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log(app, "=== Cortocircuito IEC 60909 GUARIN — %s ===" % stamp)

    icase = activate_case(app, CASO_CC)
    log(app, "IntCase: %s" % (safe_name(icase) if icase else "(activo)"))

    get_com_shc(app)
    for m in configure_pvsys_sc(app):
        log(app, m)
    d_est = expected_contrib_ka()
    log(
        app,
        "Aporte esperado inversores: 1.5 In -> %.4f kA en %.1f kV (%.2f %% de 5.12 kA)"
        % (d_est, V_HV_KV, 100.0 * d_est / 5.12),
    )

    com0 = app.GetFromStudyCase("ComShc")
    flags = []
    for a in ("iopt_fsc", "iopt_conv", "iopt_feed", "i_shcgen", "iopt_pe", "iopt_gen", "iopt_infeed"):
        v = safe_attr(com0, a)
        if v is not None:
            flags.append("%s=%s" % (a, v))
    if flags:
        log(app, "ComShc convertidores: %s" % ", ".join(flags))
    else:
        log(app, "AVISO: ComShc no expone flags de convertidor; el aporte puede seguir en 0.")

    terms = []
    for name in NODOS:
        t = pick_terminal(app, name)
        if t is None:
            log(app, "AVISO: no se encontro nodo %s" % name)
        else:
            terms.append((name, t))
            log(app, "OK nodo %s -> %s" % (name, safe_name(t)))

    rows = []
    report = [
        "CORTOCIRCUITO IEC 60909 — GUARIN 10-502",
        "Fecha: %s" % stamp,
        "IntCase: %s" % (safe_name(icase) if icase else ""),
        "cmax=1.1  |  nodos: %s" % ", ".join(n for n, _ in terms),
        "Aporte FV esperado: Ikss=1.5 In -> %.5f kA @ %.1f kV" % (expected_contrib_ka(), V_HV_KV),
        "=" * 72,
    ]

    try:
        for con_fv in (False, True):
            estado = "CON_SSFV" if con_fv else "SIN_SSFV"
            for m in set_pv(app, connected=con_fv):
                log(app, "  %s" % m)
            for falla in FALLAS:
                ok, msg = run_shc(app, falla)
                log(app, "  %s %s: %s" % (estado, falla["id"], msg))
                report.append("%s %s: %s" % (estado, falla["label"], msg))
                if not ok:
                    continue
                for name, term in terms:
                    ik, ip, sk = read_term_sc(term)
                    rows.append(
                        {
                            "estado": estado,
                            "falla": falla["id"],
                            "nodo": name,
                            "terminal_pf": safe_name(term),
                            "Ikss_kA": "" if ik is None else "%.6f" % ik,
                            "Ip_kA": "" if ip is None else "%.6f" % ip,
                            "Skss_MVA": "" if sk is None else "%.4f" % sk,
                        }
                    )
                    report.append(
                        "  %s %s: Ikss=%s kA  Ip=%s kA  Skss=%s MVA"
                        % (name, falla["id"], ik, ip, sk)
                    )
    finally:
        set_pv(app, connected=True)

    resumen = []
    nodos_res = [n for n, _ in terms]
    for nodo in nodos_res:
        rec = {"nodo": nodo}
        for falla in ("3ph", "1ph"):
            sin = next(
                (r for r in rows if r["nodo"] == nodo and r["falla"] == falla and r["estado"] == "SIN_SSFV"),
                None,
            )
            con = next(
                (r for r in rows if r["nodo"] == nodo and r["falla"] == falla and r["estado"] == "CON_SSFV"),
                None,
            )

            def f(x):
                try:
                    return float(x) if x not in (None, "") else None
                except Exception:
                    return None

            ik_s = f(sin["Ikss_kA"]) if sin else None
            ik_c = f(con["Ikss_kA"]) if con else None
            d = None
            pct = None
            if ik_s is not None and ik_c is not None:
                d = ik_c - ik_s
                pct = 100.0 * d / ik_s if ik_s else None
            rec["Ikss_%s_sin_kA" % falla] = "" if ik_s is None else "%.6f" % ik_s
            rec["Ikss_%s_con_kA" % falla] = "" if ik_c is None else "%.6f" % ik_c
            rec["dIkss_%s_kA" % falla] = "" if d is None else "%.8f" % d
            rec["dIkss_%s_pct" % falla] = "" if pct is None else "%.4f" % pct
        resumen.append(rec)
        report.append(
            "DELTA %s  3ph=%s kA (%s %%)  1ph=%s kA (%s %%)"
            % (
                nodo,
                rec.get("dIkss_3ph_kA"),
                rec.get("dIkss_3ph_pct"),
                rec.get("dIkss_1ph_kA"),
                rec.get("dIkss_1ph_pct"),
            )
        )

    write_csv(
        OUT_DIR / "cortocircuito.csv",
        ["estado", "falla", "nodo", "terminal_pf", "Ikss_kA", "Ip_kA", "Skss_MVA"],
        rows,
    )
    write_csv(
        OUT_DIR / "resumen.csv",
        [
            "nodo",
            "Ikss_3ph_sin_kA",
            "Ikss_3ph_con_kA",
            "dIkss_3ph_kA",
            "dIkss_3ph_pct",
            "Ikss_1ph_sin_kA",
            "Ikss_1ph_con_kA",
            "dIkss_1ph_kA",
            "dIkss_1ph_pct",
        ],
        resumen,
    )
    report.append("")
    report.append("Archivos en: %s" % OUT_DIR)
    (OUT_DIR / "reporte.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    log(app, "Export CC listo -> %s" % OUT_DIR)
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
