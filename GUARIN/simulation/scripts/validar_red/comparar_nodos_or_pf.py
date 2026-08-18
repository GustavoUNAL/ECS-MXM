# -*- coding: utf-8 -*-
"""
Comparar nodos OR (Excel) vs modelo PowerFactory — SIN modificar PF.

Salida: resultados de scripts/validar_red/comparacion_nodos.txt

Uso (fuera de PowerFactory):
  python comparar_nodos_or_pf.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from pf_or_insumos import (
    PF_EXPORT,
    ensure_results_validar,
    compare_or_pf,
    load_or_exact_terminals,
    load_pf_exact_from_export,
)


def main() -> int:
    or_exact = load_or_exact_terminals()
    pf_exact = load_pf_exact_from_export()

    if not pf_exact:
        print(f"AVISO: no hay nodos en {PF_EXPORT}")
        print("Exporta primero con exportar_parametros_lineas.py desde PowerFactory.")

    lines = compare_or_pf(or_exact, pf_exact)
    lines.append("")
    lines.append(f"Fuente OR: Excel insumos ({len(or_exact)} nodos exactos)")
    lines.append(f"Fuente PF: {PF_EXPORT.name}")

    out = ensure_results_validar() / "comparacion_nodos.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nGuardado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
