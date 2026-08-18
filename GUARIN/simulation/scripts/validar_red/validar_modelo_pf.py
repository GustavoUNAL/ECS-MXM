# -*- coding: utf-8 -*-
"""
Validacion del modelo PowerFactory — MAS X MENOS GUARIN (circuito 10-502).

Ejecutar desde PowerFactory (Python Script) con el proyecto abierto, o en modo
engine con PF_PATH / PROJECT_NAME configurados.

Comprueba:
  1. Inventario (lineas, terminales, cargas, trafos, generadores)
  2. Conectividad basica de lineas
  3. Flujo de carga (tensiones 0.90-1.10 p.u., cargabilidad <= 100%)
  4. Cortocircuito IEC 60909 en el POC (opcional)

Salida: resultados de scripts/validar_red/validacion_pf.txt
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuracion del estudio
# ---------------------------------------------------------------------------
PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"
STUDY_CASE = None  # None = caso activo

SITE = "GUARIN"
CIRCUITO = "10-502"
V_NOM_KV = 13.8
POC_NAME = "3272966"  # bus / terminal del punto de conexion

# Conteos esperados segun Excel OR (Datos Circuito 10 502 - 2026.xlsx)
EXPECTED_LINES = 215
EXPECTED_LOADS = 51
TOL_COUNT = 0.15  # tolerancia relativa (15%) si el modelo PF es subset del OR

V_MIN_PU = 0.90
V_MAX_PU = 1.10
LOADING_MAX_PCT = 100.0

RUN_LOAD_FLOW = True
RUN_SHORT_CIRCUIT = True
SC_FAULT_TYPE = 0  # 0=3ph (segun comando ComShc de la instalacion)

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
OUTPUT_DIR = _SIM / "resultados de scripts" / "validar_red"
OUTPUT_FILE = OUTPUT_DIR / "validacion_pf.txt"


# ---------------------------------------------------------------------------
# Conexion PF
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
        raise RuntimeError(
            "No se pudo conectar a PowerFactory. "
            "Ejecuta este script desde PF o configura PF_PATH."
        )
    app.ActivateProject(PROJECT_NAME)
    if STUDY_CASE:
        folder = app.GetProjectFolder("study")
        cases = folder.GetContents(f"{STUDY_CASE}.IntCase") if folder else []
        if cases:
            cases[0].Activate()
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


def find_terminal(app, name: str):
    for cls in ("ElmTerm", "ElmCoup"):
        objs = app.GetCalcRelevantObjects(f"*.{cls}") or []
        for o in objs:
            n = safe_name(o)
            if n == name or n.startswith(name):
                return o
    return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def inventory(app):
    lines = app.GetCalcRelevantObjects("*.ElmLne") or []
    terms = app.GetCalcRelevantObjects("*.ElmTerm") or []
    loads = app.GetCalcRelevantObjects("*.ElmLod") or []
    trafos = app.GetCalcRelevantObjects("*.ElmTr2") or []
    gens = (
        (app.GetCalcRelevantObjects("*.ElmGenstat") or [])
        + (app.GetCalcRelevantObjects("*.ElmPvsys") or [])
        + (app.GetCalcRelevantObjects("*.ElmSym") or [])
    )
    return {
        "lines": list(lines),
        "terms": list(terms),
        "loads": list(loads),
        "trafos": list(trafos),
        "gens": list(gens),
    }


def check_counts(inv, report: list[str]) -> list[str]:
    issues = []
    n_l, n_c = len(inv["lines"]), len(inv["loads"])
    report.append("--- Inventario ---")
    report.append(f"Lineas ElmLne:     {n_l}  (OR esperado ~{EXPECTED_LINES})")
    report.append(f"Terminales:        {len(inv['terms'])}")
    report.append(f"Cargas ElmLod:     {n_c}  (OR esperado ~{EXPECTED_LOADS})")
    report.append(f"Trafos ElmTr2:     {len(inv['trafos'])}")
    report.append(f"Generadores/PV:    {len(inv['gens'])}")

    if EXPECTED_LINES and abs(n_l - EXPECTED_LINES) / EXPECTED_LINES > TOL_COUNT:
        msg = f"Conteo de lineas difiere del OR ({n_l} vs {EXPECTED_LINES})"
        issues.append(msg)
        report.append(f"AVISO: {msg}")
    if EXPECTED_LOADS and abs(n_c - EXPECTED_LOADS) / EXPECTED_LOADS > TOL_COUNT:
        msg = f"Conteo de cargas difiere del OR ({n_c} vs {EXPECTED_LOADS})"
        issues.append(msg)
        report.append(f"AVISO: {msg}")
    return issues


def check_line_connectivity(inv, report: list[str]) -> list[str]:
    issues = []
    report.append("")
    report.append("--- Conectividad de lineas ---")
    bad = []
    for ln in inv["lines"]:
        bus1 = safe_attr(ln, "bus1")
        bus2 = safe_attr(ln, "bus2")
        # en PF a veces es cubicle -> cBusBar
        t1 = safe_attr(bus1, "cBusBar") if bus1 else None
        t2 = safe_attr(bus2, "cBusBar") if bus2 else None
        if t1 is None and bus1 is not None:
            t1 = bus1
        if t2 is None and bus2 is not None:
            t2 = bus2
        if t1 is None or t2 is None:
            bad.append(safe_name(ln))
    report.append(f"Lineas sin ambos extremos: {len(bad)}")
    if bad:
        issues.append(f"{len(bad)} lineas incompletas")
        report.append("Ejemplos: " + ", ".join(bad[:15]))
    else:
        report.append("OK: todas las lineas tienen terminales i/j")
    return issues


def run_load_flow(app, report: list[str]) -> list[str]:
    issues = []
    report.append("")
    report.append("--- Flujo de carga ---")
    com = app.GetFromStudyCase("ComLdf")
    if com is None:
        issues.append("No se encontro ComLdf en el caso de estudio")
        report.append("ERROR: ComLdf no disponible")
        return issues

    ierr = com.Execute()
    if ierr != 0:
        issues.append(f"Load Flow fallo (codigo {ierr})")
        report.append(f"ERROR: Load Flow codigo {ierr}")
        return issues
    report.append("Load Flow: OK")

    v_out = []
    for term in app.GetCalcRelevantObjects("*.ElmTerm") or []:
        v = safe_attr(term, "m:u")
        if v is None:
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        name = safe_name(term)
        if v < V_MIN_PU or v > V_MAX_PU:
            v_out.append((name, v))
    report.append(f"Barras fuera de [{V_MIN_PU}, {V_MAX_PU}] p.u.: {len(v_out)}")
    for name, v in v_out[:20]:
        report.append(f"  {name}: {v:.4f} p.u.")
        issues.append(f"Tension fuera de rango en {name}: {v:.4f} p.u.")

    over = []
    for ln in app.GetCalcRelevantObjects("*.ElmLne") or []:
        loading = safe_attr(ln, "c:loading")
        if loading is None:
            loading = safe_attr(ln, "m:loading")
        if loading is None:
            continue
        try:
            loading = float(loading)
        except (TypeError, ValueError):
            continue
        if loading > LOADING_MAX_PCT:
            over.append((safe_name(ln), loading))
    report.append(f"Lineas con cargabilidad > {LOADING_MAX_PCT}%: {len(over)}")
    for name, ld in over[:20]:
        report.append(f"  {name}: {ld:.2f}%")
        issues.append(f"Sobrecarga en linea {name}: {ld:.2f}%")

    for tr in app.GetCalcRelevantObjects("*.ElmTr2") or []:
        loading = safe_attr(tr, "c:loading") or safe_attr(tr, "m:loading")
        if loading is None:
            continue
        try:
            loading = float(loading)
        except (TypeError, ValueError):
            continue
        report.append(f"Trafo {safe_name(tr)}: cargabilidad {loading:.2f}%")
        if loading > LOADING_MAX_PCT:
            issues.append(f"Sobrecarga en trafo {safe_name(tr)}: {loading:.2f}%")

    return issues


def run_short_circuit(app, report: list[str]) -> list[str]:
    issues = []
    report.append("")
    report.append(f"--- Cortocircuito IEC 60909 (POC={POC_NAME}) ---")
    term = find_terminal(app, POC_NAME)
    if term is None:
        msg = f"No se encontro terminal POC '{POC_NAME}'"
        issues.append(msg)
        report.append(f"AVISO: {msg} — se omite CC")
        return issues

    com = app.GetFromStudyCase("ComShc")
    if com is None:
        issues.append("No se encontro ComShc")
        report.append("ERROR: ComShc no disponible")
        return issues

    try:
        com.iopt_mde = 1  # completo / IEC segun version
    except Exception:
        pass
    try:
        com.shcEvent = None
    except Exception:
        pass

    # Seleccionar barra de falla si el atributo existe
    for attr in ("shcobj", "p_bus", "bus"):
        try:
            setattr(com, attr, term)
            break
        except Exception:
            continue

    ierr = com.Execute()
    if ierr != 0:
        issues.append(f"Short Circuit fallo (codigo {ierr})")
        report.append(f"ERROR: Short Circuit codigo {ierr}")
        return issues

    ik = safe_attr(term, "m:Ik") or safe_attr(term, "m:Ikss")
    ip = safe_attr(term, "m:Ip")
    report.append(f"POC {safe_name(term)}: Ik={ik} kA, Ip={ip} kA")
    if ik is None:
        report.append("AVISO: no se leyeron variables m:Ik / m:Ikss (revisar resultados CC)")
    else:
        report.append("Cortocircuito: OK (valores leidos)")
    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = connect_app()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = [
        f"VALIDACION POWERFACTORY — {SITE} / circuito {CIRCUITO}",
        f"Fecha: {stamp}",
        f"Proyecto: {PROJECT_NAME}",
        f"Vnom: {V_NOM_KV} kV | POC: {POC_NAME}",
        "=" * 70,
    ]

    all_issues: list[str] = []
    inv = inventory(app)
    all_issues += check_counts(inv, report)
    all_issues += check_line_connectivity(inv, report)

    if RUN_LOAD_FLOW:
        all_issues += run_load_flow(app, report)
    if RUN_SHORT_CIRCUIT:
        all_issues += run_short_circuit(app, report)

    report.append("")
    report.append("=" * 70)
    report.append("=== VEREDICTO ===")
    if not all_issues:
        report.append("PASS — modelo coherente con criterios basicos del estudio")
        verdict = "PASS"
    else:
        report.append(f"REVIEW — {len(all_issues)} hallazgo(s):")
        for i, issue in enumerate(all_issues, 1):
            report.append(f"  {i}. {issue}")
        verdict = "REVIEW"

    text = "\n".join(report) + "\n"
    OUTPUT_FILE.write_text(text, encoding="utf-8")
    for line in report:
        log(app, line)
    log(app, f"Reporte escrito en: {OUTPUT_FILE}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR FATAL: {exc}")
        raise
