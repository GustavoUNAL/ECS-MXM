# -*- coding: utf-8 -*-
"""Compara nodos/busbars: base OR (lineas base) vs modelo PF (lineas_parametros)."""
from pathlib import Path
import re

_ROOT = Path(__file__).resolve().parents[1]  # GUARIN/simulation
_GUARIN = _ROOT.parent
BASE = _GUARIN / "data" / "lineas_base.txt"
PF = _ROOT / "results" / "lineas_parametros.csv"
OUT = _ROOT / "results" / "comparacion_nodos.txt"


def parse_nodes(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    nodes = set()
    edges = []  # (name, ti, tj)
    for ln in lines[2:]:
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        name = parts[0].strip()
        ti = parts[3].strip()
        tj = parts[4].strip()
        if ti:
            nodes.add(ti)
        if tj:
            nodes.add(tj)
        edges.append((name, ti, tj))
    return nodes, edges


def base_id(node: str) -> str:
    """Quita sufijo de cubículo A/B/C... y espacios; deja el id de bus principal."""
    n = node.strip()
    # casos especiales tipo "10 502_Term" o "Terminal(1)"
    if not n:
        return n
    # quitar letra final de cubículo: 1103458A -> 1103458, 1067052B -> 1067052
    m = re.fullmatch(r"(\d+)([A-Za-z]+)", n)
    if m:
        return m.group(1)
    return n


base_nodes, base_edges = parse_nodes(BASE)
pf_nodes, pf_edges = parse_nodes(PF)

# Comparacion exacta (nombre tal cual)
solo_base = sorted(base_nodes - pf_nodes, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
solo_pf = sorted(pf_nodes - base_nodes, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
ambos = sorted(base_nodes & pf_nodes, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))

# Comparacion por bus "raiz" (sin sufijo A/B/C)
base_roots = {base_id(n): n for n in base_nodes}
pf_roots = {base_id(n): n for n in pf_nodes}
base_root_set = set(base_roots)
pf_root_set = set(pf_roots)

roots_solo_base = sorted(
    base_root_set - pf_root_set,
    key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
)
roots_solo_pf = sorted(
    pf_root_set - base_root_set,
    key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
)
roots_ambos = sorted(
    base_root_set & pf_root_set,
    key=lambda x: (0, int(x)) if x.isdigit() else (1, x),
)

# Nodos de la base que solo difieren por sufijo (cubículo) vs modelo
cubre_por_raiz = []
for n in solo_base:
    r = base_id(n)
    if r in pf_root_set:
        cubre_por_raiz.append((n, pf_roots[r]))

lines = []
lines.append("=== RESUMEN NODOS / BUSBAR ===")
lines.append(f"OR (lineas base.txt):     {len(base_nodes)} nodos distintos (Terminal i/j tal cual)")
lines.append(f"Modelo PF (lineas_parametros.csv): {len(pf_nodes)} nodos distintos")
lines.append(f"Coinciden exactos:        {len(ambos)}")
lines.append(f"Solo en OR (exacto):      {len(solo_base)}")
lines.append(f"Solo en Modelo (exacto):  {len(solo_pf)}")
lines.append("")
lines.append("--- Por bus raiz (sin sufijo A/B/C de cubículo) ---")
lines.append(f"OR buses raiz:            {len(base_root_set)}")
lines.append(f"Modelo buses raiz:        {len(pf_root_set)}")
lines.append(f"Coinciden raiz:           {len(roots_ambos)}")
lines.append(f"Solo en OR (raiz):        {len(roots_solo_base)}")
lines.append(f"Solo en Modelo (raiz):    {len(roots_solo_pf)}")
lines.append(
    f"Nombres OR cubiertos por un bus del modelo (mismo id, distinto sufijo): {len(cubre_por_raiz)}"
)
lines.append("")
lines.append("=== SOLO EN OR — buses raiz que NO existen en el modelo ===")
for r in roots_solo_base:
    # listar variantes en OR
    vars_ = sorted(n for n in base_nodes if base_id(n) == r)
    lines.append(f"{r}\tvariantes OR: {', '.join(vars_)}")
lines.append("")
lines.append("=== SOLO EN MODELO — buses raiz que NO estan en la base OR ===")
for r in roots_solo_pf:
    vars_ = sorted(n for n in pf_nodes if base_id(n) == r)
    lines.append(f"{r}\tvariantes PF: {', '.join(vars_)}")
lines.append("")
lines.append("=== SOLO EN OR (nombre exacto) — muchos son cubículos A/B/C ===")
for n in solo_base:
    r = base_id(n)
    if r in pf_root_set:
        lines.append(f"{n}\t-> en modelo como bus '{pf_roots[r]}' (mismo raiz {r})")
    else:
        lines.append(f"{n}\t-> NO hay bus raiz {r} en el modelo")
lines.append("")
lines.append("=== SOLO EN MODELO (nombre exacto) ===")
for n in solo_pf:
    r = base_id(n)
    if r in base_root_set:
        lines.append(f"{n}\t-> en OR como '{base_roots[r]}' (mismo raiz {r})")
    else:
        lines.append(f"{n}\t-> NO esta en OR")

text = "\n".join(lines)
OUT.write_text(text, encoding="utf-8")
print(text)
