# -*- coding: utf-8 -*-
"""
Comparar lineas OR (lineas_base.txt) vs export PF — sin modificar PowerFactory.

Salida: resultados de scripts/validar_red/comparacion_lineas.txt

Uso:
  python comparar_lineas_or_pf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from pf_or_insumos import LINEAS_BASE, PF_EXPORT, ensure_results_validar


def parse(path):
    text = path.read_text(encoding="utf-8-sig")
    rows = {}
    for ln in text.splitlines()[2:]:
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


def main() -> int:
    if not PF_EXPORT.is_file():
        print(f"AVISO: exporta primero lineas desde PF -> {PF_EXPORT.name}")

    base = parse(LINEAS_BASE)
    pf = parse(PF_EXPORT) if PF_EXPORT.is_file() else {}

    exist = sorted(base.keys() & pf.keys(), key=key)
    crear = sorted(base.keys() - pf.keys(), key=key)
    extra = sorted(pf.keys() - base.keys(), key=key)

    lines = [
        "=== RESUMEN ===",
        f"Base: {len(base)} | PF: {len(pf)} | Ya existen: {len(exist)} | Por crear: {len(crear)} | Extra en PF: {len(extra)}",
        "",
        "=== YA EXISTEN EN PF ===",
        ", ".join(exist),
        "",
        "=== POR CREAR (Name | Terminal i | Terminal j | Length km | Tipo) ===",
    ]
    for n in crear:
        r = base[n]
        lines.append(f"{n}\t{r['ti']}\t{r['tj']}\t{r['length']}\t{r['type']}")
    lines.extend(["", "=== EXTRA EN PF (no estan en base) ==="])
    for n in extra:
        r = pf[n]
        lines.append(f"{n}\t{r['ti']}\t{r['tj']}\t{r['length']}\t{r['type']}")

    out = ensure_results_validar() / "comparacion_lineas.txt"
    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nGuardado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
