#!/usr/bin/env python3
"""Extrae resumen del circuito 10-502 desde Excel OR y valida contra PDF unifilar."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import openpyxl

BASE = Path(__file__).resolve().parent
DATA = BASE.parents[1] / "GUARIN" / "data" / "Datos Circuito 10 502 - 2026.xlsx"
PDF = BASE.parents[1] / "GUARIN" / "data" / "CTO 10 502.pdf"
OUT_JSON = BASE / "informe_circuito.json"
OUT_JS = BASE / "informe_circuito.js"


def norm_terminal(t) -> str | None:
    if not t:
        return None
    s = str(t).strip()
    m = re.match(r"^(\d+)", s)
    return m.group(1) if m else (s.split()[0] if s else None)


def main() -> None:
    wb = openpyxl.load_workbook(DATA, data_only=True)
    ws = wb["Líneas "]
    lines = []
    nodes: set[str] = set()
    cond_stats: dict[str, dict] = defaultdict(lambda: {"tramos": 0, "km": 0.0})

    for row in ws.iter_rows(min_row=3, values_only=True):
        if row[0] is None:
            continue
        lid = str(row[0]).strip()
        ti, tj = str(row[3] or ""), str(row[4] or "")
        L = float(row[5] or 0)
        cond = str(row[6] or "").strip()
        lines.append({"id": lid, "from": norm_terminal(ti), "to": norm_terminal(tj), "L_km": L, "conductor": cond})
        for t in (ti, tj):
            n = norm_terminal(t)
            if n:
                nodes.add(n)
        cond_stats[cond]["tramos"] += 1
        cond_stats[cond]["km"] += L

    ws2 = wb["Cargas_Demanda_corto"]
    loads = []
    demand = []
    poc_carga = None
    for row in ws2.iter_rows(min_row=3, values_only=True):
        if row[0] is None or row[4] is None:
            continue
        node = norm_terminal(row[2])
        loads.append({"name": str(row[0]).strip(), "node": node, "S_MVA": float(row[4]), "fp": float(row[5] or 0.9)})
        if node == "3272966":
            poc_carga = str(row[0]).strip()

    for row in ws2.iter_rows(min_row=2, max_row=25, values_only=True):
        if row[10] is None or row[12] is None:
            continue
        h = row[10].hour if hasattr(row[10], "hour") else int(str(row[10])[11:13])
        demand.append({"hora": h, "I_A": round(float(row[11]), 3), "S_MVA": round(float(row[12]), 6)})

    import fitz  # pymupdf

    doc = fitz.open(PDF)
    pdf_nums: set[str] = set()
    for page in doc:
        for ln in page.get_text("text").splitlines():
            ln = ln.strip()
            if re.match(r"^\d{5,7}$", ln):
                pdf_nums.add(ln)
    doc.close()

    line_ids = {l["id"] for l in lines}
    informe = {
        "fuentes": {
            "excel": DATA.name,
            "pdf": PDF.name,
            "fecha_demanda": "2024-03-19",
            "subestacion": "SE Conucos",
            "circuito": "10-502",
            "tension_kv": 13.8,
            "operador": "ESSA",
            "proyecto": "MAS X MENOS Guarín — 141,6 kWp / 120 kW AC",
        },
        "inventario": {
            "n_lineas": len(lines),
            "n_nodos": len(nodes),
            "n_cargas": len(loads),
            "longitud_km": round(sum(l["L_km"] for l in lines), 3),
            "s_cargas_mva": round(sum(l["S_MVA"] for l in loads), 3),
            "poc_nodo": "3272966",
            "poc_carga": poc_carga,
        },
        "pdf_validacion": {
            "etiquetas_numericas": len(pdf_nums),
            "coinciden_lineas": len(pdf_nums & line_ids),
            "coinciden_nodos": len(pdf_nums & nodes),
            "nota": "El PDF es diagrama gráfico; no todas las etiquetas son texto extraíble.",
        },
        "demanda": {
            "puntos": demand,
            "s_max_mva": max(d["S_MVA"] for d in demand),
            "s_min_mva": min(d["S_MVA"] for d in demand),
            "s_prom_mva": round(sum(d["S_MVA"] for d in demand) / len(demand), 6),
            "i_max_a": max(d["I_A"] for d in demand),
            "horas_estudio": {"09:00": 1.459139, "12:00": 1.682856, "15:00": 1.638498},
        },
        "conductores": [
            {"name": k, "tramos": v["tramos"], "km": round(v["km"], 3)}
            for k, v in sorted(cond_stats.items(), key=lambda x: -x[1]["km"])[:12]
        ],
        "estados_operacionales": {
            "descripcion": "3 horas representativas ESSA × Sin/Con AGPE 120 kW AC (metodología CREG)",
            "horas": ["09:00", "12:00", "15:00"],
            "total": 6,
            "que_cambia_hora": [
                "Demanda de cabecera (MVA) — escala todas las cargas",
                "Corriente e intensidad en líneas",
                "Pérdidas del circuito",
                "Tensiones en nodos",
            ],
            "que_cambia_agpe": [
                "Inyección de 120 kW AC en POC 3272966",
                "Tensión mínima del circuito (sube)",
                "Carga del trafo en POC (sube en %)",
                "Pérdidas (disminuyen)",
                "Potencia trafo POC: importación → exportación neta",
            ],
        },
    }

    OUT_JSON.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JS.write_text(
        "const INFORME = " + json.dumps(informe, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"OK -> {OUT_JSON.name}, {OUT_JS.name}")


if __name__ == "__main__":
    main()
