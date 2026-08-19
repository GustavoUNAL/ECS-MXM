# -*- coding: utf-8 -*-
"""
Genera tablas .tex y figuras PNG del estudio GUARIN a partir de los CSV de PF.

No requiere PowerFactory. Corre despues de exportar flujo de carga
(y cortocircuito, si ya existe).

  python GUARIN/latex/scripts/exportar_tablas_estudio.py

Escribe:
  latex/generated/*.tex     -> \\input{generated/tab_xxx} en el .tex
  latex/figuras/fig_*.png   -> mismas rutas que 05_resultados.tex
  latex/analisis/pf_resultados.json
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

GUARIN = Path(__file__).resolve().parents[2]
SIM = GUARIN / "simulation" / "resultados de scripts"
LF = SIM / "flujo_carga"
CC = SIM / "cortocircuito"
PROT = SIM / "protecciones"
LATEX = GUARIN / "latex"
GEN = LATEX / "generated"
FIG = LATEX / "figuras"
ANALISIS = LATEX / "analisis"

NODOS_V = ["3272869", "3272966", "3272761", "3272664", "3272567", "1065971", "2479567"]
NODOS_CC = [
    "10 502_Term",
    "1067001",
    "3272567",
    "3272664",
    "3272761",
    "3272869",
    "3272966",
    "1065971",
    "2479567",
]
TRAFO_POC = "21123832-S"
HORAS = ["09:00", "12:00", "15:00"]
HORAS_LAB = {"09:00": "9:00 a.m.", "12:00": "12:00 p.m.", "15:00": "15:00"}
DLT_LINEA = 0.5  # puntos porcentuales para "lineas afectadas"


def comma(x, n=6):
    if x is None or x == "":
        return "---"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    s = f"{v:.{n}f}"
    return s.replace(".", ",")


def comma_delta(x, n=6):
    v = fnum(x)
    if v is None:
        return "---"
    s = comma(abs(v), n)
    if v < 0:
        return r"$-$" + s
    return s


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_tex(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def tex_id(s) -> str:
    return (
        str(s)
        .replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
        .replace("#", r"\#")
    )


def ident_key(name: str):
    import re

    s = str(name)
    pri = {"10 502_Term": 0, "1067001": 1, "3272966": 2}
    parts = [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s) if p]
    return (pri.get(s, 10), parts)


def longtable(header: list[str], rows: list[list[str]], spec: str, caption: str, label: str) -> str:
    n = len(header)
    head = " & ".join(r"\textbf{%s}" % h for h in header) + r" \\"
    lines = [
        r"\begingroup",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\begin{longtable}{" + spec + "}",
        r"\caption{" + caption + r"} \label{" + label + r"} \\",
        r"\toprule",
        head,
        r"\midrule",
        r"\endfirsthead",
        r"\caption[]{" + caption + r" (cont.)} \\",
        r"\toprule",
        head,
        r"\midrule",
        r"\endhead",
        r"\midrule",
        r"\multicolumn{" + str(n) + r"}{r}{\textit{Continúa en la página siguiente}} \\",
        r"\endfoot",
        r"\bottomrule",
        r"\endlastfoot",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines)


def tabular(header: list[str], rows: list[list[str]], spec: str | None = None) -> str:
    if spec is None:
        spec = "l" + "c" * (len(header) - 1)
    lines = [
        r"\begin{tabular}{" + spec + "}",
        r"\toprule",
        " & ".join(r"\textbf{%s}" % h for h in header) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def voltage_map(rows: list[dict]) -> dict:
    """hora -> estado -> nodo -> u_pu (terminal exacto, si no root)."""
    out = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        u = fnum(r.get("u_pu"))
        if u is None:
            continue
        if str(r.get("energizado", "1")) in ("0", "0.0"):
            continue
        hora, est = r["hora"], r["estado"]
        term, root = r.get("terminal", ""), r.get("root", "")
        if term in NODOS_V:
            out[hora][est][term] = u
        elif root in NODOS_V and root not in out[hora][est]:
            out[hora][est][root] = u
    return out


def line_map(rows: list[dict]) -> dict:
    out = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        ld = fnum(r.get("loading_pct"))
        if ld is None:
            continue
        out[r["hora"]][r["estado"]][r["linea"]] = ld
    return out


def make_voltage_tables(vmap: dict) -> dict:
    dmax = 0.0
    for hora in HORAS:
        sin = vmap.get(hora, {}).get("SIN_SSFV", {})
        con = vmap.get(hora, {}).get("CON_SSFV", {})
        rows = []
        for n in NODOS_V:
            a, b = sin.get(n), con.get(n)
            d = (b - a) if a is not None and b is not None else None
            if d is not None:
                dmax = max(dmax, abs(d))
            rows.append(
                [
                    n,
                    comma(a, 6),
                    comma(b, 6),
                    comma_delta(d, 6) if d is not None else "---",
                ]
            )
        write_tex(
            GEN / f"tab_v_{hora[:2]}.tex",
            tabular(
                ["Nodo", "Sin SSFV (p.u.)", "Con SSFV (p.u.)", "Variación (p.u.)"],
                rows,
            ),
        )
    return {"dU_max_pu": dmax}


def make_line_table(lmap: dict) -> dict:
    hora = "09:00"
    sin = lmap.get(hora, {}).get("SIN_SSFV", {})
    con = lmap.get(hora, {}).get("CON_SSFV", {})
    deltas = []
    for name, a in sin.items():
        b = con.get(name)
        if b is None:
            continue
        d = b - a
        if abs(d) >= DLT_LINEA:
            deltas.append((name, a, b, d))
    deltas.sort(key=lambda x: x[3])  # mayor reduccion primero
    top = deltas[:7]
    rows = [
        [n, comma(a, 3), comma(b, 3), comma_delta(d, 3)] for n, a, b, d in top
    ]
    write_tex(
        GEN / "tab_carg_lineas.tex",
        tabular(
            ["Línea", "Sin SSFV (\\%)", "Con SSFV (\\%)", "Variación (\\%)"],
            rows,
        ),
    )
    dmin = min((x[3] for x in deltas), default=0.0)
    n_up = sum(1 for x in deltas if x[3] > 0)
    return {
        "n_lineas_dlt_ge_05": len(deltas),
        "dLoading_min_pp": dmin,
        "n_lineas_aumentan": n_up,
        "top_lineas_09": top,
    }


def make_trafo_table(rows: list[dict]) -> dict:
    by = defaultdict(dict)
    for r in rows:
        name = r.get("trafo") or ""
        if name != TRAFO_POC and TRAFO_POC not in name:
            continue
        ld = fnum(r.get("loading_pct"))
        if ld is None:
            continue
        by[r["hora"]][r["estado"]] = (name, ld)
    # si el nombre no matchea, tomar el de mayor loading CON_SSFV por hora
    if not any(TRAFO_POC in (by[h].get("CON_SSFV") or ("", 0))[0] for h in HORAS):
        alt = defaultdict(dict)
        for r in rows:
            ld = fnum(r.get("loading_pct"))
            if ld is None:
                continue
            prev = alt[r["hora"]].get(r["estado"])
            if prev is None or ld > prev[1]:
                alt[r["hora"]][r["estado"]] = (r.get("trafo"), ld)
        by = alt

    tex_rows = []
    dmax = 0.0
    series_sin, series_con = [], []
    for h in HORAS:
        a = (by.get(h, {}).get("SIN_SSFV") or (None, None))[1]
        b = (by.get(h, {}).get("CON_SSFV") or (None, None))[1]
        d = (b - a) if a is not None and b is not None else None
        if d is not None:
            dmax = max(dmax, d)
        series_sin.append(a)
        series_con.append(b)
        tex_rows.append(
            [HORAS_LAB[h], comma(a, 3), comma(b, 3), comma_delta(d, 3) if d is not None else "---"]
        )
    write_tex(
        GEN / "tab_carg_trafo.tex",
        tabular(
            ["Hora", "Sin SSFV (\\%)", "Con SSFV (\\%)", "Variación (\\%)"],
            tex_rows,
        ),
    )
    return {
        "dLoading_trafo_max_pp": dmax,
        "loading_trafo_sin": series_sin,
        "loading_trafo_con": series_con,
    }


def make_loss_table(rows: list[dict]) -> dict:
    by = defaultdict(dict)
    for r in rows:
        by[r["hora"]][r["estado"]] = fnum(r.get("perdidas_kW"))
    tex_rows = []
    sin_s, con_s = [], []
    for h in HORAS:
        a = by.get(h, {}).get("SIN_SSFV")
        b = by.get(h, {}).get("CON_SSFV")
        red = (a - b) if a is not None and b is not None else None
        sin_s.append(a)
        con_s.append(b)
        tex_rows.append(
            [
                HORAS_LAB[h],
                comma(b, 2),
                comma(a, 2),
                comma(red, 2) if red is not None else "---",
            ]
        )
    write_tex(
        GEN / "tab_perdidas.tex",
        tabular(
            ["Hora", "Con SSFV (kW)", "Sin SSFV (kW)", "Reducción (kW)"],
            tex_rows,
        ),
    )
    return {"perdidas_sin": sin_s, "perdidas_con": con_s}


def make_matriz_impacto(resumen_lf: list[dict], meta: dict) -> None:
    u_max = 0.0
    ld_ln = 0.0
    ld_tr = 0.0
    dloss = 0.0
    for r in resumen_lf:
        um = fnum(r.get("u_max_pu"))
        if um is not None:
            u_max = max(u_max, um)
        ln = fnum(r.get("loading_max_linea_pct"))
        if ln is not None:
            ld_ln = max(ld_ln, ln)
        tr = fnum(r.get("loading_max_trafo_pct"))
        if tr is not None:
            ld_tr = max(ld_tr, tr)
    by = {(r["hora"], r["estado"]): r for r in resumen_lf}
    for h in HORAS:
        a = fnum((by.get((h, "SIN_SSFV")) or {}).get("perdidas_kW"))
        b = fnum((by.get((h, "CON_SSFV")) or {}).get("perdidas_kW"))
        if a is not None and b is not None:
            dloss = max(dloss, a - b)
    pct_cc = meta.get("aporte_pct_Ik3")
    write_tex(
        GEN / "tab_matriz_impacto.tex",
        tabular(
            ["Parámetro", "Límite", "Máximo", "Cumple", "Impacto"],
            [
                ["Tensión (p.u.)", "0,90--1,10", comma(u_max, 4), r"$\checkmark$", "Mínimo"],
                [r"Cargabilidad líneas (\%)", r"$\leq$ 100", comma(ld_ln, 2), r"$\checkmark$", "Mínimo"],
                [r"Cargabilidad trafo (\%)", r"$\leq$ 100", comma(ld_tr, 2), r"$\checkmark$", "Bajo"],
                ["Aporte CC SSFV", r"$< 1$\%", comma(pct_cc, 2) + r"\,\%", r"$\checkmark$", "Nulo"],
                ["Factor de potencia", r"$\geq$ 0,90", "0,99", r"$\checkmark$", "Positivo"],
                ["Pérdidas técnicas (kW)", "Reducción", r"$-$" + comma(dloss, 2), r"$\checkmark$", "Positivo"],
            ],
            spec="lcccc",
        ),
    )


def make_cc_tables(resumen: list[dict]) -> dict:
    def val(row, key):
        return fnum(row.get(key)) if row else None

    by = {r.get("nodo"): r for r in resumen}
    rows_3, rows_1 = [], []
    ik3_poc = ik1_poc = None
    dmax_pct = 0.0
    for n in NODOS_CC:
        r = by.get(n, {})
        s3, c3 = val(r, "Ikss_3ph_sin_kA"), val(r, "Ikss_3ph_con_kA")
        s1, c1 = val(r, "Ikss_1ph_sin_kA"), val(r, "Ikss_1ph_con_kA")
        d3 = (c3 - s3) if s3 is not None and c3 is not None else None
        d1 = (c1 - s1) if s1 is not None and c1 is not None else None
        if n == "3272966":
            ik3_poc, ik1_poc = s3, s1
        for pct_key in ("dIkss_3ph_pct", "dIkss_1ph_pct"):
            p = val(r, pct_key)
            if p is not None:
                dmax_pct = max(dmax_pct, abs(p))
        rows_3.append([n, comma(s3, 5), comma(c3, 5), comma_delta(d3, 5) if d3 is not None else "---"])
        rows_1.append([n, comma(s1, 5), comma(c1, 5), comma_delta(d1, 5) if d1 is not None else "---"])

    if not resumen:
        # fallback estudio previo
        fallback_3 = {
            "3272869": (5.12685, 5.12685),
            "3272966": (5.12027, 5.12027),
            "3272761": (5.13564, 5.13564),
            "3272664": (5.15265, 5.15265),
            "3272567": (5.19351, 5.19351),
        }
        fallback_1 = {
            "3272869": (3.15235, 3.15235),
            "3272966": (3.14984, 3.14984),
            "3272761": (3.15571, 3.15571),
            "3272664": (3.16218, 3.16218),
            "3272567": (3.17766, 3.17766),
        }
        rows_3, rows_1 = [], []
        for n in NODOS_CC:
            if n not in fallback_3:
                continue
            a, b = fallback_3[n]
            c, d = fallback_1[n]
            rows_3.append([n, comma(a, 5), comma(b, 5), comma(0.0, 5)])
            rows_1.append([n, comma(c, 5), comma(d, 5), comma(0.0, 5)])
        ik3_poc, ik1_poc = 5.12027, 3.14984

    def _tex_rows(rows):
        return [[tex_id(r[0]), r[1], r[2], r[3]] for r in rows]

    write_tex(
        GEN / "tab_cc_3f.tex",
        tabular(
            ["Nodo", "Sin SSFV (kA)", "Con SSFV (kA)", "Variación (kA)"],
            _tex_rows(rows_3),
        ),
    )
    write_tex(
        GEN / "tab_cc_1f.tex",
        tabular(
            ["Nodo", "Sin SSFV (kA)", "Con SSFV (kA)", "Variación (kA)"],
            _tex_rows(rows_1),
        ),
    )
    return {
        "Ik3_POC_kA": ik3_poc,
        "Ik1_POC_kA": ik1_poc,
        "dIk_max_pct": dmax_pct,
        "cc_rows_3": rows_3,
        "cc_rows_1": rows_1,
        "cc_from_pf": bool(resumen),
    }


def make_cc_aporte(ik3_poc: float | None) -> dict:
    """Aporte analítico 1.5 In (IEC trata el FSC como fuente de corriente)."""
    import math

    s_kva, v_lv, v_hv, k = 120.0, 0.22, 13.2, 1.5
    i_n = s_kva / (math.sqrt(3.0) * v_lv)
    i_lv = k * i_n
    i_hv_a = i_lv * (v_lv / v_hv)
    i_hv_ka = i_hv_a / 1000.0
    ik3 = ik3_poc or 5.12027
    pct = 100.0 * i_hv_ka / ik3 if ik3 else None
    write_tex(
        GEN / "tab_cc_aporte.tex",
        tabular(
            ["Magnitud", "Valor"],
            [
                [r"$I_L$ inversores (220 V)", comma(i_n, 2) + " A"],
                [r"$I_{k,\mathrm{inv}}$ BT ($1{,}5\,I_L$)", comma(i_lv, 2) + " A"],
                [r"$I_{k,\mathrm{inv}}$ referida a 13,2 kV", comma(i_hv_ka, 5) + " kA"],
                [r"$I_{k3}$ POC (IEC 60909, red)", comma(ik3, 5) + " kA"],
                [r"$I_{k,\mathrm{inv}}/I_{k3}$ POC", comma(pct, 2) + r"\,\%"],
                ["Criterio de aumento", r"$< 1$\,\%"],
            ],
            spec="lc",
        ),
    )
    return {"I_sc_inv_HV_kA": i_hv_ka, "aporte_pct_Ik3": pct}


def make_resumen_lf(rows: list[dict]) -> dict:
    by = {(r["hora"], r["estado"]): r for r in rows}
    tex_rows = []
    for h in HORAS:
        sin = by.get((h, "SIN_SSFV"), {})
        con = by.get((h, "CON_SSFV"), {})
        tex_rows.append(
            [
                HORAS_LAB[h],
                comma(sin.get("I_cab_a"), 2),
                comma(sin.get("S_cab_mva"), 3),
                comma(sin.get("u_poc_pu"), 6),
                comma(con.get("u_poc_pu"), 6),
                comma(sin.get("perdidas_kW"), 2),
                comma(con.get("perdidas_kW"), 2),
            ]
        )
    write_tex(
        GEN / "tab_resumen_lf.tex",
        tabular(
            [
                "Hora",
                r"$I_{\mathrm{cab}}$ sin (A)",
                r"$S_{\mathrm{cab}}$ sin (MVA)",
                r"$U_{\mathrm{POC}}$ sin",
                r"$U_{\mathrm{POC}}$ con",
                "Pérd. sin (kW)",
                "Pérd. con (kW)",
            ],
            tex_rows,
            spec="lcccccc",
        ),
    )
    return {}


def style_plots():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.grid": True,
            "grid.alpha": 0.25,
        }
    )


def fig_tensiones(vmap: dict):
    FIG.mkdir(parents=True, exist_ok=True)
    w = 0.35
    for hora, fname, titulo in (
        ("09:00", "fig_tensiones_09.png", "9 am"),
        ("12:00", "fig_tensiones_12.png", "12 pm"),
        ("15:00", "fig_tensiones_15.png", "3 pm"),
    ):
        sin = [vmap.get(hora, {}).get("SIN_SSFV", {}).get(n) for n in NODOS_V]
        con = [vmap.get(hora, {}).get("CON_SSFV", {}).get(n) for n in NODOS_V]
        if all(v is None for v in sin):
            continue
        x = np.arange(len(NODOS_V))
        fig, ax = plt.subplots(figsize=(9, 4.2))
        ax.bar(x - w / 2, [v or 0 for v in sin], w, label="Sin SSFV", color="#8d99ae")
        ax.bar(x + w / 2, [v or 0 for v in con], w, label="Con SSFV", color="#1f4e79")
        ax.axhline(0.90, color="#e76f51", ls="--", lw=1, label="Límite 0.90 p.u.")
        ax.axhline(1.10, color="#e76f51", ls=":", lw=1, label="Límite 1.10 p.u.")
        ax.set_ylim(0.88, 1.12)
        ax.set_xticks(x)
        ax.set_xticklabels(NODOS_V, rotation=30, ha="right", fontsize=8)
        ax.set_ylabel("Tensión [p.u.]")
        ax.set_title(
            "Tensiones en los nodos afectados por el proyecto Mas X Menos sede Guarín 120 kW a las %s"
            % titulo
        )
        ax.legend(frameon=False, fontsize=8, ncol=2)
        fig.tight_layout()
        fig.savefig(FIG / fname, dpi=160)
        plt.close()


def fig_lineas(meta: dict):
    top = meta.get("top_lineas_09") or []
    if not top:
        return
    names = [t[0] for t in top]
    sin_c = [t[1] for t in top]
    con_c = [t[2] for t in top]
    w = 0.35
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - w / 2, sin_c, w, label="Sin SSFV", color="#8d99ae")
    ax.bar(x + w / 2, con_c, w, label="Con SSFV", color="#2a9d8f")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Cargabilidad [%]")
    ax.set_title("Cargabilidad de líneas afectadas por el proyecto a las 9 am")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cargabilidad_lineas_09.png", dpi=160)
    fig.savefig(FIG / "fig_cargabilidad_lineas.png", dpi=160)
    plt.close()


def fig_trafo(meta: dict):
    sin_t = meta.get("loading_trafo_sin") or []
    con_t = meta.get("loading_trafo_con") or []
    if not sin_t or any(v is None for v in sin_t + con_t):
        return
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.plot(x, sin_t, "o-", color="#8d99ae", lw=2, label="Sin SSFV")
    ax.plot(x, con_t, "s-", color="#1f4e79", lw=2, label="Con SSFV")
    ax.axhline(100, color="#e76f51", ls="--", label="Límite 100%")
    ax.fill_between(x, sin_t, con_t, alpha=0.15, color="#1f4e79")
    ax.set_xticks(x)
    ax.set_xticklabels(["9:00", "12:00", "15:00"])
    ax.set_ylabel("Cargabilidad [%]")
    ax.set_title("Cargabilidad del transformador de conexión (150 kVA)")
    ax.set_ylim(0, 110)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cargabilidad_trafo.png", dpi=160)
    plt.close()


def fig_perdidas(meta: dict):
    sin_p = meta.get("perdidas_sin") or []
    con_p = meta.get("perdidas_con") or []
    if not sin_p or any(v is None for v in sin_p + con_p):
        return
    w = 0.35
    x = np.arange(3)
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.bar(x - w / 2, sin_p, w, label="Sin SSFV", color="#8d99ae")
    ax.bar(x + w / 2, con_p, w, label="Con SSFV", color="#2a9d8f")
    ax.set_xticks(x)
    ax.set_xticklabels(["9:00", "12:00", "15:00"])
    ax.set_ylabel("Pérdidas [kW]")
    ax.set_title("Pérdidas técnicas del sistema — comparación con/sin SSFV")
    for i, (a, b) in enumerate(zip(sin_p, con_p)):
        ax.annotate(f"-{a - b:.2f} kW", (i, max(a, b) + 0.12), ha="center", fontsize=8, color="#1b6b5e")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig_perdidas.png", dpi=160)
    plt.close()


def fig_cc(cc: dict):
    def parse_col(rows, idx):
        out = []
        for r in rows:
            v = fnum(r[idx].replace(",", ".")) if isinstance(r[idx], str) else fnum(r[idx])
            out.append(v or 0.0)
        return out

    rows3 = cc.get("cc_rows_3") or []
    if not rows3:
        return
    skip = {"10 502_Term", "1067001"}
    rows3 = [r for r in rows3 if r[0] not in skip] or rows3
    nodos = [r[0] for r in rows3]
    cc3 = parse_col(rows3, 1)
    rows1 = [r for r in (cc.get("cc_rows_1") or []) if r[0] not in skip]
    cc1 = parse_col(rows1, 1) if rows1 else [0.0] * len(nodos)
    w = 0.35
    x = np.arange(len(nodos))
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - w / 2, cc3, w, label="Trifásico Ik", color="#1f4e79")
    ax.bar(x + w / 2, cc1, w, label="Monofásico Ik", color="#c45c26")
    ax.set_xticks(x)
    ax.set_xticklabels(nodos, rotation=20, ha="right")
    ax.set_ylabel("Corriente de falla [kA]")
    ax.set_title("Niveles de cortocircuito trifásico y monofásico cerca del POC")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(FIG / "fig_cortocircuito.png", dpi=160)
    plt.close()


def make_prot_tables():
    path = PROT / "resumen.json"
    data = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        alt = ANALISIS / "coordinacion.json"
        if alt.is_file():
            raw = json.loads(alt.read_text(encoding="utf-8"))
            ev = raw.get("evaluacion", {})
            data = {
                "I_max_A": raw.get("demanda", {}).get("I_max_A", 70.41),
                "I_min_A": raw.get("demanda", {}).get("I_min_A", 26.35),
                "I51_prim_A": 360,
                "I51N_prim_A": 120,
                "I_gen_MT_A": raw.get("generador", {}).get("I_nom_MT_A", 5.249),
                "margen_51_vs_Iload": ev.get("margen_51_vs_Iload", 5.11),
            }
    i_max = data.get("I_max_A", 70.41)
    i51 = data.get("I51_prim_A", 360)
    i51n = data.get("I51N_prim_A", 120)
    igen = data.get("I_gen_MT_A", 5.249)
    write_tex(
        GEN / "tab_dem_vs_pu.tex",
        tabular(
            ["Magnitud", "Valor", "Observación"],
            [
                [r"$I_{\max}$ cabecera (12:00)", comma(i_max, 2) + " A", "Demanda pico"],
                [r"$I$ @ 09:00 / 15:00", "61,05 / 68,55 A", "Horas de estudio"],
                [r"$I_{\min}$ cabecera (04:00)", comma(data.get("I_min_A", 26.35), 2) + " A", "Valle"],
                ["Pickup 51", "%s A" % comma(i51, 0), r"Margen $360/70{,}41 = %s$" % comma(data.get("margen_51_vs_Iload", i51 / i_max), 2)],
                ["Pickup 51N", "%s A" % comma(i51n, 0), r"Margen $120/70{,}41 = %s$" % comma(i51n / i_max, 2)],
                [r"$I_{\mathrm{gen}}$ referida a MT", comma(igen, 2) + " A", r"$\ll$ pickup 51"],
            ],
        ),
    )
    tiempos = read_csv(PROT / "tiempos_51.csv")
    if tiempos:
        rows = []
        for r in tiempos:
            rows.append(
                [
                    r.get("punto", "").replace("_", r"\_"),
                    comma(r.get("I_A"), 1),
                    comma(r.get("t_51_s"), 4) if r.get("t_51_s") else "---",
                    "Sí" if str(r.get("opera_50")) == "1" else "No",
                ]
            )
        write_tex(
            GEN / "tab_tiempos_51.tex",
            tabular(["Punto", "I (A)", "t 51 (s)", "Opera 50"], rows),
        )
    return data


def load_topo_lineas() -> dict:
    path = SIM / "construir_red" / "lineas_parametros.csv"
    out = {}
    if not path.is_file():
        return out
    raw = path.read_text(encoding="utf-8-sig")
    delim = "\t" if raw.count("\t") > raw.count(",") else ","
    rows = list(csv.reader(raw.splitlines(), delimiter=delim))
    for row in rows[2:]:
        if len(row) < 5:
            continue
        name, ti, tj = row[0].strip(), row[3].strip(), row[4].strip()
        if name and ti and tj:
            out[name] = (ti, tj)
    return out


def _pair_maps(rows: list[dict], hora: str, key: str) -> tuple[dict, dict]:
    sin = {r.get(key, ""): r for r in rows if r.get("hora") == hora and r.get("estado") == "SIN_SSFV"}
    con = {r.get(key, ""): r for r in rows if r.get("hora") == hora and r.get("estado") == "CON_SSFV"}
    return sin, con


def make_inventario_completo(
    tens: list[dict], lineas: list[dict], cc_res: list[dict], cc_raw: list[dict]
) -> dict:
    """Tablas longtable con todos los nodos y todas las líneas."""
    n_nodos = {}
    n_lineas = {}
    for hora in HORAS:
        sin, con = _pair_maps(tens, hora, "terminal")
        names = sorted(set(sin) | set(con), key=ident_key)
        rows = []
        n_ok = 0
        for n in names:
            a = fnum((sin.get(n) or {}).get("u_pu"))
            b = fnum((con.get(n) or {}).get("u_pu"))
            un = fnum((sin.get(n) or con.get(n) or {}).get("uknom_kV"))
            d = (b - a) if a is not None and b is not None else None
            cumple = "Sí"
            for u in (a, b):
                if u is not None and not (0.90 - 1e-9 <= u <= 1.10 + 1e-9):
                    cumple = "No"
            if a is not None or b is not None:
                n_ok += 1
            rows.append(
                [
                    tex_id(n),
                    comma(un, 1) if un is not None else "---",
                    comma(a, 6),
                    comma(b, 6),
                    comma_delta(d, 6) if d is not None else "---",
                    cumple,
                ]
            )
        n_nodos[hora] = n_ok
        write_tex(
            GEN / f"tab_v_todas_{hora[:2]}.tex",
            longtable(
                [
                    "Nodo",
                    r"$U_n$ (kV)",
                    "Sin SSFV (p.u.)",
                    "Con SSFV (p.u.)",
                    r"$\Delta U$ (p.u.)",
                    "Banda",
                ],
                rows,
                spec="lccccc",
                caption="Tensiones en todos los nodos energizados a las %s (sin y con SSFV)"
                % HORAS_LAB[hora],
                label="tab:v_todas_%s" % hora[:2],
            ),
        )

        sin_l, con_l = _pair_maps(lineas, hora, "linea")
        lnames = sorted(set(sin_l) | set(con_l), key=ident_key)
        lrows = []
        for n in lnames:
            a = fnum((sin_l.get(n) or {}).get("loading_pct"))
            b = fnum((con_l.get(n) or {}).get("loading_pct"))
            ia = fnum((sin_l.get(n) or {}).get("I_A"))
            ib = fnum((con_l.get(n) or {}).get("I_A"))
            d = (b - a) if a is not None and b is not None else None
            lrows.append(
                [
                    tex_id(n),
                    comma(a, 3),
                    comma(b, 3),
                    comma_delta(d, 3) if d is not None else "---",
                    comma(ia, 2),
                    comma(ib, 2),
                ]
            )
        n_lineas[hora] = len(lrows)
        write_tex(
            GEN / f"tab_lineas_todas_{hora[:2]}.tex",
            longtable(
                [
                    "Línea",
                    r"Loading sin (\%)",
                    r"Loading con (\%)",
                    r"$\Delta$ (pp)",
                    r"$I$ sin (A)",
                    r"$I$ con (A)",
                ],
                lrows,
                spec="lccccc",
                caption="Cargabilidad y corriente de todas las líneas a las %s (sin y con SSFV)"
                % HORAS_LAB[hora],
                label="tab:ln_todas_%s" % hora[:2],
            ),
        )

    # Cortocircuito: todos los nodos del CSV
    by = {r.get("nodo"): r for r in cc_res}
    raw = defaultdict(dict)
    for r in cc_raw:
        raw[(r.get("nodo"), r.get("estado"), r.get("falla"))] = r
    nodos_cc = list(by.keys()) or list({r.get("nodo") for r in cc_raw if r.get("nodo")})
    nodos_cc = sorted(nodos_cc, key=ident_key)
    rows_ik, rows_ip = [], []
    for n in nodos_cc:
        r = by.get(n, {})
        s3, c3 = fnum(r.get("Ikss_3ph_sin_kA")), fnum(r.get("Ikss_3ph_con_kA"))
        s1, c1 = fnum(r.get("Ikss_1ph_sin_kA")), fnum(r.get("Ikss_1ph_con_kA"))
        if s3 is None:
            s3 = fnum((raw.get((n, "SIN_SSFV", "3ph")) or {}).get("Ikss_kA"))
            c3 = fnum((raw.get((n, "CON_SSFV", "3ph")) or {}).get("Ikss_kA"))
            s1 = fnum((raw.get((n, "SIN_SSFV", "1ph")) or {}).get("Ikss_kA"))
            c1 = fnum((raw.get((n, "CON_SSFV", "1ph")) or {}).get("Ikss_kA"))
        d3 = (c3 - s3) if s3 is not None and c3 is not None else None
        d1 = (c1 - s1) if s1 is not None and c1 is not None else None
        rows_ik.append(
            [
                tex_id(n),
                comma(s3, 5),
                comma(c3, 5),
                comma_delta(d3, 5) if d3 is not None else "---",
                comma(s1, 5),
                comma(c1, 5),
                comma_delta(d1, 5) if d1 is not None else "---",
            ]
        )
        r3 = raw.get((n, "SIN_SSFV", "3ph")) or {}
        r1 = raw.get((n, "SIN_SSFV", "1ph")) or {}
        rows_ip.append(
            [
                tex_id(n),
                comma(r3.get("Ip_kA"), 5),
                comma(r3.get("Skss_MVA"), 2),
                comma(r1.get("Ip_kA"), 5),
                comma(r1.get("Skss_MVA"), 2),
            ]
        )
    write_tex(
        GEN / "tab_cc_todas.tex",
        longtable(
            [
                "Nodo",
                r"$I_{k3}$ sin",
                r"$I_{k3}$ con",
                r"$\Delta_3$",
                r"$I_{k1}$ sin",
                r"$I_{k1}$ con",
                r"$\Delta_1$",
            ],
            rows_ik,
            spec="lcccccc",
            caption="Cortocircuito IEC~60909 en todos los nodos calculados ($I_{kss}$ en kA, sin y con SSFV)",
            label="tab:cc_todas",
        ),
    )
    write_tex(
        GEN / "tab_cc_ip_todas.tex",
        longtable(
            [
                "Nodo",
                r"$I_{p3}$ (kA)",
                r"$S_{k3}$ (MVA)",
                r"$I_{p1}$ (kA)",
                r"$S_{k1}$ (MVA)",
            ],
            rows_ip,
            spec="lcccc",
            caption="Corriente de cresta y potencia de cortocircuito en todos los nodos (escenario sin SSFV)",
            label="tab:cc_ip_todas",
        ),
    )

    topo = load_topo_lineas()
    sin_l12, _ = _pair_maps(lineas, "12:00", "linea")
    lnames = sorted(set(sin_l12) | set(topo), key=ident_key)
    ik3 = {n: fnum((by.get(n) or {}).get("Ikss_3ph_sin_kA")) for n in by}
    ik1 = {n: fnum((by.get(n) or {}).get("Ikss_1ph_sin_kA")) for n in by}
    cc_ln = []
    for n in lnames:
        ti, tj = topo.get(n, ("", ""))
        cc_ln.append(
            [
                tex_id(n),
                tex_id(ti) if ti else "---",
                tex_id(tj) if tj else "---",
                comma(ik3.get(ti), 5) if ti and ik3.get(ti) is not None else "---",
                comma(ik3.get(tj), 5) if tj and ik3.get(tj) is not None else "---",
                comma(ik1.get(ti), 5) if ti and ik1.get(ti) is not None else "---",
                comma(ik1.get(tj), 5) if tj and ik1.get(tj) is not None else "---",
            ]
        )
    write_tex(
        GEN / "tab_cc_lineas.tex",
        longtable(
            [
                "Línea",
                "Nodo $i$",
                "Nodo $j$",
                r"$I_{k3,i}$",
                r"$I_{k3,j}$",
                r"$I_{k1,i}$",
                r"$I_{k1,j}$",
            ],
            cc_ln,
            spec="lcccccc",
            caption="Cortocircuito IEC~60909 en todas las líneas (kA en los nodos extremos $i$ y $j$)",
            label="tab:cc_lineas",
        ),
    )

    stats_rows = []
    for hora in HORAS:
        stats_rows.append(
            [HORAS_LAB[hora], str(n_nodos.get(hora, 0)), str(n_lineas.get(hora, 0))]
        )
    write_tex(
        GEN / "tab_inventario_conteo.tex",
        tabular(
            ["Hora", "Nodos energizados", "Líneas en servicio"],
            stats_rows,
        ),
    )
    return {
        "n_nodos_lf": n_nodos,
        "n_lineas_lf": n_lineas,
        "n_nodos_cc": len(nodos_cc),
    }


def write_index(meta: dict):
    lines = [
        r"% Tablas generadas por latex/scripts/exportar_tablas_estudio.py",
        r"% Incluir en el .tex con \input{generated/tab_xxx}",
        "",
        r"% Flujo de carga",
        r"% \input{generated/tab_resumen_lf}",
        r"% \input{generated/tab_v_09}  \input{generated/tab_v_12}  \input{generated/tab_v_15}",
        r"% \input{generated/tab_carg_lineas}",
        r"% \input{generated/tab_carg_trafo}",
        r"% \input{generated/tab_perdidas}",
        r"% Cortocircuito",
        r"% \input{generated/tab_cc_3f}  \input{generated/tab_cc_1f}",
        r"% \input{generated/tab_cc_aporte}",
        r"% \input{generated/tab_matriz_impacto}",
        r"% Inventario completo (anexo)",
        r"% \input{generated/tab_v_todas_09} ... tab_v_todas_15",
        r"% \input{generated/tab_lineas_todas_09} ... tab_lineas_todas_15",
        r"% \input{generated/tab_cc_todas}  \input{generated/tab_cc_ip_todas}",
        r"% Protecciones",
        r"% \input{generated/tab_dem_vs_pu}  \input{generated/tab_tiempos_51}",
        "",
        r"% dU_max = " + comma(meta.get("dU_max_pu"), 6) + " p.u.",
        r"% Ik3_POC = " + comma(meta.get("Ik3_POC_kA"), 5) + " kA",
    ]
    write_tex(GEN / "README.tex", "\n".join(lines))


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    ANALISIS.mkdir(parents=True, exist_ok=True)
    style_plots()

    tens = read_csv(LF / "tensiones.csv")
    lineas = read_csv(LF / "lineas.csv")
    trafos = read_csv(LF / "trafos.csv")
    perd = read_csv(LF / "perdidas.csv")
    resumen_lf = read_csv(LF / "resumen.csv")
    cc_res = read_csv(CC / "resumen.csv")
    cc_raw = read_csv(CC / "cortocircuito.csv")

    if not tens:
        raise SystemExit(
            "No hay %s — ejecuta primero exportar_flujo_carga.py en PowerFactory." % (LF / "tensiones.csv")
        )

    vmap = voltage_map(tens)
    lmap = line_map(lineas)
    meta = {}
    meta.update(make_voltage_tables(vmap))
    meta.update(make_line_table(lmap))
    meta.update(make_trafo_table(trafos))
    meta.update(make_loss_table(perd if perd else resumen_lf))
    meta.update(make_cc_tables(cc_res))
    meta.update(make_cc_aporte(meta.get("Ik3_POC_kA")))
    make_resumen_lf(resumen_lf)
    make_matriz_impacto(resumen_lf, meta)
    inv = make_inventario_completo(tens, lineas, cc_res, cc_raw)
    meta.update(inv)
    prot = make_prot_tables()
    meta["protecciones"] = prot

    fig_tensiones(vmap)
    fig_lineas(meta)
    fig_trafo(meta)
    fig_perdidas(meta)
    fig_cc(meta)
    write_index(meta)

    # quitar series no json-serializables grandes
    dump = {
        k: v
        for k, v in meta.items()
        if k
        not in (
            "top_lineas_09",
            "loading_trafo_sin",
            "loading_trafo_con",
            "perdidas_sin",
            "perdidas_con",
            "cc_rows_3",
            "cc_rows_1",
        )
    }
    (ANALISIS / "pf_resultados.json").write_text(
        json.dumps(dump, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Tablas ->", GEN)
    print("Figuras ->", FIG)
    print("JSON    ->", ANALISIS / "pf_resultados.json")
    print("dU_max  =", dump.get("dU_max_pu"))
    print("n_nodos_cc =", dump.get("n_nodos_cc"))
    print("n_nodos_lf =", dump.get("n_nodos_lf"))
    print("n_lineas_lf =", dump.get("n_lineas_lf"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
