# -*- coding: utf-8 -*-
"""
Coordinacion de protecciones — GUARIN 10-502 (sin PowerFactory).

Usa ajustes MICOM P142 (Excel/CNO), demanda OR y, si existe,
cortocircuito.csv de PF. Escribe CSV + JSON para el exportador LaTeX.

Ejecutar:
  python GUARIN/simulation/scripts/protecciones/exportar_coordinacion.py
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

GUARIN = Path(
    r"C:\Users\Usuario Principal\Documents\copower\Estudio de conexion\GUARIN"
)
OUT_DIR = GUARIN / "simulation" / "resultados de scripts" / "protecciones"
CC_CSV = GUARIN / "simulation" / "resultados de scripts" / "cortocircuito" / "resumen.csv"
COORD_JSON = GUARIN / "latex" / "analisis" / "coordinacion.json"

# Ajustes OR — MICOM P142 bahia CTO 10502
RTC = 60.0
I51_PRIM = 360.0  # A
TMS_51 = 0.1
I50_PRIM = 2160.0
I51N_PRIM = 120.0
TMS_51N = 0.15
I50N_PRIM = 1200.0

S_AC_KVA = 120.0
V_LV_KV = 0.22
V_HV_KV = 13.2
K_SC_INV = 1.5  # Ik simetrica inversores = 1.5 In

I_MAX_A = 70.41
I_MIN_A = 26.35
I_09 = 61.05
I_12 = 70.41
I_15 = 68.55


def t_iec_vi(i_a: float, i_s: float, tms: float) -> float | None:
    """Tiempo IEC Very Inverse: t = TMS * 13.5 / (I/Is - 1)."""
    if i_a is None or i_s <= 0 or i_a <= i_s:
        return None
    return tms * 13.5 / ((i_a / i_s) - 1.0)


def fmt(x, n=4):
    if x is None:
        return ""
    return f"{x:.{n}f}"


def load_ik_poc():
    ik3, ik1 = 5.12027, 3.14984
    if not CC_CSV.is_file():
        return ik3, ik1, "coordinacion.json / valor estudio"
    import csv as _csv

    with CC_CSV.open(encoding="utf-8-sig") as f:
        for row in _csv.DictReader(f):
            if row.get("nodo") == "3272966":
                try:
                    ik3 = float(row["Ikss_3ph_sin_kA"] or row.get("Ikss_3ph_con_kA") or ik3)
                except (TypeError, ValueError):
                    pass
                try:
                    ik1 = float(row["Ikss_1ph_sin_kA"] or row.get("Ikss_1ph_con_kA") or ik1)
                except (TypeError, ValueError):
                    pass
                return ik3, ik1, str(CC_CSV)
    return ik3, ik1, "CSV sin nodo 3272966; se usa valor previo"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ik3_kA, ik1_kA, fuente = load_ik_poc()
    ik3_a = ik3_kA * 1000.0
    ik1_a = ik1_kA * 1000.0

    i_nom_lv = S_AC_KVA / (math.sqrt(3.0) * V_LV_KV)
    i_sc_lv = K_SC_INV * i_nom_lv
    i_nom_mt = i_nom_lv * (V_LV_KV / V_HV_KV)
    i_sc_mt = i_sc_lv * (V_LV_KV / V_HV_KV)
    aporte_pct = 100.0 * i_sc_mt / (ik3_a) if ik3_a else None

    puntos = [
        ("I_load_max", I_MAX_A),
        ("1.5x_I_load", 1.5 * I_MAX_A),
        ("2x_I51", 2.0 * I51_PRIM),
        ("5x_I51", 5.0 * I51_PRIM),
        ("10x_I51", 10.0 * I51_PRIM),
        ("Ik3_POC_A", ik3_a),
        ("Ik1_POC_A", ik1_a),
    ]
    rows_t = []
    for name, i_a in puntos:
        t51 = t_iec_vi(i_a, I51_PRIM, TMS_51)
        t51n = t_iec_vi(i_a, I51N_PRIM, TMS_51N)
        rows_t.append(
            {
                "punto": name,
                "I_A": fmt(i_a, 2),
                "t_51_s": fmt(t51, 4) if t51 is not None else "",
                "opera_50": 1 if i_a >= I50_PRIM else 0,
                "t_51N_s": fmt(t51n, 4) if t51n is not None else "",
                "opera_50N": 1 if i_a >= I50N_PRIM else 0,
            }
        )

    t51_poc = t_iec_vi(ik3_a, I51_PRIM, TMS_51)
    t51n_poc = t_iec_vi(ik1_a, I51N_PRIM, TMS_51N)
    margen_51 = I51_PRIM / I_MAX_A
    margen_51n = I51N_PRIM / I_MAX_A

    resumen = {
        "fuente_Ik_POC": fuente,
        "Ik3_POC_kA": ik3_kA,
        "Ik1_POC_kA": ik1_kA,
        "I51_prim_A": I51_PRIM,
        "I50_prim_A": I50_PRIM,
        "I51N_prim_A": I51N_PRIM,
        "I50N_prim_A": I50N_PRIM,
        "I_max_A": I_MAX_A,
        "I_min_A": I_MIN_A,
        "I_gen_MT_A": round(i_nom_mt, 3),
        "I_sc_inv_MT_A": round(i_sc_mt, 3),
        "margen_51_vs_Iload": round(margen_51, 2),
        "margen_51N_vs_Iload": round(margen_51n, 2),
        "cumple_margen_pickup": margen_51 >= 1.5,
        "exportacion_no_dispara_51": i_nom_mt < I51_PRIM,
        "t51_en_Ik3_POC_s": t51_poc,
        "t51N_en_Ik1_POC_s": t51n_poc,
        "opera_50_en_POC": ik3_a >= I50_PRIM,
        "opera_50N_en_POC_1ph": ik1_a >= I50N_PRIM,
        "aporte_SSFV_pct_Ik3_POC": round(aporte_pct, 4) if aporte_pct else None,
        "criterio_aumento_cc": "< 1%",
        "ANSI_27_59_81_antiisla": "Cumple (inversores SOLIS)",
    }

    fields = ["punto", "I_A", "t_51_s", "opera_50", "t_51N_s", "opera_50N"]
    with (OUT_DIR / "tiempos_51.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_t)

    (OUT_DIR / "resumen.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Actualiza latex/analisis/coordinacion.json si existe
    if COORD_JSON.is_file():
        try:
            data = json.loads(COORD_JSON.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        data.setdefault("evaluacion", {})
        data["evaluacion"].update(
            {
                "margen_51_vs_Iload": resumen["margen_51_vs_Iload"],
                "cumple_margen_pickup": resumen["cumple_margen_pickup"],
                "exportacion_no_dispara_51": resumen["exportacion_no_dispara_51"],
                "t51_en_Ik3_POC_s": t51_poc,
                "t51N_en_Ik1_POC_s": t51n_poc,
                "opera_50_en_POC": resumen["opera_50_en_POC"],
                "opera_50N_en_POC_1ph": resumen["opera_50N_en_POC_1ph"],
                "aporte_SSFV_pct_Ik3_POC": resumen["aporte_SSFV_pct_Ik3_POC"],
            }
        )
        data.setdefault("cortocircuito", {})
        data["cortocircuito"]["Ik3_POC_kA"] = ik3_kA
        data["cortocircuito"]["Ik1_POC_kA"] = ik1_kA
        COORD_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "COORDINACION PROTECCIONES — GUARIN 10-502",
        "Fuente Ik POC: %s" % fuente,
        "Ik3 POC = %.5f kA | Ik1 POC = %.5f kA" % (ik3_kA, ik1_kA),
        "Margen 51 vs Imax = %.2f (criterio >= 1.5) %s"
        % (margen_51, "OK" if margen_51 >= 1.5 else "REVISAR"),
        "Igen MT = %.3f A << 360 A  |  aporte SSFV = %s %% de Ik3"
        % (i_nom_mt, resumen["aporte_SSFV_pct_Ik3_POC"]),
        "t51 @ Ik3 POC = %s s | opera 50: %s" % (fmt(t51_poc, 4), resumen["opera_50_en_POC"]),
        "Salida: %s" % OUT_DIR,
    ]
    (OUT_DIR / "reporte.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
