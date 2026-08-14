# -*- coding: utf-8 -*-
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]  # GUARIN/simulation
_GUARIN = _ROOT.parent
base_path = _GUARIN / "data" / "lineas_base.txt"
pf_path = _ROOT / "results" / "lineas_parametros.csv"
out_path = _ROOT / "results" / "comparacion_lineas.txt"


def parse(path):
    text = path.read_text(encoding="utf-8-sig")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    rows = {}
    for ln in lines[2:]:
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        name = parts[0].strip()
        rows[name] = {
            "ti": parts[3].strip(),
            "tj": parts[4].strip(),
            "length": parts[5].strip() if len(parts) > 5 else "",
            "type": parts[6].strip() if len(parts) > 6 else "",
        }
    return rows


def key(n):
    return (0, int(n)) if n.isdigit() else (1, n)


base = parse(base_path)
pf = parse(pf_path)

exist = sorted(base.keys() & pf.keys(), key=key)
crear = sorted(base.keys() - pf.keys(), key=key)
extra = sorted(pf.keys() - base.keys(), key=key)

lines = []
lines.append("=== RESUMEN ===")
lines.append(
    f"Base: {len(base)} | PF: {len(pf)} | Ya existen: {len(exist)} | Por crear: {len(crear)} | Extra en PF: {len(extra)}"
)
lines.append("")
lines.append("=== YA EXISTEN EN PF ===")
lines.append(", ".join(exist))
lines.append("")
lines.append("=== POR CREAR (Name | Terminal i | Terminal j | Length km | Tipo) ===")
for n in crear:
    r = base[n]
    lines.append(f"{n}\t{r['ti']}\t{r['tj']}\t{r['length']}\t{r['type']}")
lines.append("")
lines.append("=== EXTRA EN PF (no estan en base) ===")
for n in extra:
    r = pf[n]
    lines.append(f"{n}\t{r['ti']}\t{r['tj']}\t{r['length']}\t{r['type']}")

text = "\n".join(lines)
out_path.write_text(text, encoding="utf-8")
print(text)
