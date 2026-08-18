# -*- coding: utf-8 -*-
"""Utilidades compartidas: insumos OR (Excel) vs modelo PowerFactory."""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas del sitio GUARIN
# ---------------------------------------------------------------------------
SCRIPTS = Path(__file__).resolve().parent.parent
SIMULATION = SCRIPTS.parent
GUARIN = SIMULATION.parent
DATA = GUARIN / "data"
EXCEL_OR = DATA / "Datos Circuito 10 502 - 2026.xlsx"
LINEAS_BASE = DATA / "lineas_base.txt"
RESULTS = SIMULATION / "resultados de scripts"
RESULTS_CONSTRUIR = RESULTS / "construir_red"
RESULTS_VALIDAR = RESULTS / "validar_red"
RESULTS_FLUJO = RESULTS / "flujo_carga"
PF_EXPORT = RESULTS_CONSTRUIR / "lineas_parametros.csv"

PF_PATH = r"C:\Program Files\DIgSILENT\PowerFactory 2024"
PROJECT_NAME = r"\Usuario Principal.IntUser\Mas X Menos Guarin.IntPrj"

V_NOM_KV = 13.8

# Renombrar buses PF → nombre OR (origen subestación)
RENOMBRES_PF_A_OR: dict[str, str] = {
    "Terminal(1)": "10 502_Term",
}

# Nodos raíz que faltan en PF según comparación OR (docs/lineas_por_crear.md)
NODOS_RAIZ_PRIORITARIOS: tuple[str, ...] = (
    "4637844",
    "4637852",
    "4637861",
    "4916671",
    "10 502_Term",
)


def root_id(node: str) -> str:
    """Quita sufijo de cubículo (1103458A → 1103458). No trunca '10 502_Term'."""
    n = (node or "").strip()
    if not n:
        return n
    m = re.fullmatch(r"(\d+)([A-Za-z]+)", n)
    if m:
        return m.group(1)
    return n


def _strip_cell(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def load_or_exact_from_excel(path: Path = EXCEL_OR) -> set[str]:
    """Todos los nombres exactos de Terminal i/j del Excel OR."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Líneas "]
    nodes: set[str] = set()
    for row in ws.iter_rows(min_row=3, values_only=True):
        if row[0] is None:
            continue
        for col in (3, 4):
            t = _strip_cell(row[col])
            if t:
                nodes.add(t)
    return nodes


def load_or_exact_from_lineas_base(path: Path = LINEAS_BASE) -> set[str]:
    """Fallback: parsea lineas_base.txt (export OR)."""
    text = path.read_text(encoding="utf-8-sig")
    nodes: set[str] = set()
    for ln in text.splitlines()[2:]:
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        for col in (3, 4):
            t = _strip_cell(parts[col])
            if t:
                nodes.add(t)
    return nodes


def ensure_results_dir() -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    return RESULTS


def ensure_results_construir() -> Path:
    RESULTS_CONSTRUIR.mkdir(parents=True, exist_ok=True)
    return RESULTS_CONSTRUIR


def ensure_results_validar() -> Path:
    RESULTS_VALIDAR.mkdir(parents=True, exist_ok=True)
    return RESULTS_VALIDAR


def ensure_results_flujo() -> Path:
    RESULTS_FLUJO.mkdir(parents=True, exist_ok=True)
    return RESULTS_FLUJO


def load_or_exact_terminals() -> set[str]:
    if EXCEL_OR.is_file():
        return load_or_exact_from_excel()
    if LINEAS_BASE.is_file():
        return load_or_exact_from_lineas_base()
    raise FileNotFoundError(f"No se encontro Excel ni {LINEAS_BASE}")


def load_pf_exact_from_export(path: Path = PF_EXPORT) -> set[str]:
    """Nodos en el CSV exportado de PF (lineas_parametros.csv)."""
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8-sig")
    nodes: set[str] = set()
    for ln in text.splitlines()[2:]:
        parts = ln.split("\t")
        if len(parts) < 5:
            continue
        for col in (3, 4):
            t = _strip_cell(parts[col])
            if t:
                nodes.add(t)
    return nodes


def group_by_root(names: set[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for n in names:
        out.setdefault(root_id(n), set()).add(n)
    return out


def compare_or_pf(or_exact: set[str], pf_exact: set[str]) -> list[str]:
    """Genera texto de reporte comparación."""
    or_roots = group_by_root(or_exact)
    pf_roots = group_by_root(pf_exact)

    solo_or = sorted(or_exact - pf_exact, key=_sort_key)
    solo_pf = sorted(pf_exact - or_exact, key=_sort_key)
    ambos = sorted(or_exact & pf_exact, key=_sort_key)

    roots_solo_or = sorted(set(or_roots) - set(pf_roots), key=_sort_key)
    roots_solo_pf = sorted(set(pf_roots) - set(or_roots), key=_sort_key)
    roots_ambos = sorted(set(or_roots) & set(pf_roots), key=_sort_key)

    cubre_por_raiz = [
        n for n in solo_or if root_id(n) in pf_roots
    ]

    lines = [
        "=== RESUMEN NODOS / BUSBAR ===",
        f"OR (Excel / insumos):     {len(or_exact)} nombres exactos",
        f"Modelo PF:                {len(pf_exact)} nombres exactos",
        f"Coinciden exactos:        {len(ambos)}",
        f"Solo en OR (exacto):      {len(solo_or)}",
        f"Solo en Modelo (exacto):  {len(solo_pf)}",
        "",
        "--- Por bus raiz (sin sufijo A/B/C de cubículo) ---",
        f"OR buses raiz:            {len(or_roots)}",
        f"Modelo buses raiz:        {len(pf_roots)}",
        f"Coinciden raiz:           {len(roots_ambos)}",
        f"Solo en OR (raiz):        {len(roots_solo_or)}",
        f"Solo en Modelo (raiz):    {len(roots_solo_pf)}",
        f"OR cubiertos por raiz en PF (distinto sufijo): {len(cubre_por_raiz)}",
        "",
        "=== SOLO EN OR — buses raiz que NO existen en el modelo ===",
    ]
    for r in roots_solo_or:
        vars_ = sorted(or_roots[r])
        lines.append(f"{r}\tvariantes OR: {', '.join(vars_)}")

    lines.append("")
    lines.append("=== SOLO EN MODELO — buses raiz que NO estan en la base OR ===")
    for r in roots_solo_pf:
        vars_ = sorted(pf_roots[r])
        lines.append(f"{r}\tvariantes PF: {', '.join(vars_)}")

    lines.append("")
    lines.append("=== RENOMBRES SUGERIDOS (PF -> OR) ===")
    for old, new in RENOMBRES_PF_A_OR.items():
        in_pf = old in pf_exact
        tgt_free = new not in pf_exact
        lines.append(f"{old} -> {new}\t(PF tiene origen={in_pf}, destino libre={tgt_free})")

    lines.append("")
    lines.append("=== NODOS PRIORITARIOS A CREAR (raiz) ===")
    for r in NODOS_RAIZ_PRIORITARIOS:
        st = "OK en PF" if r in pf_roots else "FALTA"
        lines.append(f"{r}\t{st}")

    return lines


def _sort_key(x: str):
    return (0, int(x)) if x.isdigit() else (1, x)


# ---------------------------------------------------------------------------
# PowerFactory (solo cuando se importa desde scripts PF)
# ---------------------------------------------------------------------------
def connect_app(project: str = PROJECT_NAME):
    try:
        import powerfactory as pf  # type: ignore

        app = pf.GetApplication()
        if app is not None:
            app.ActivateProject(project)
            return app
    except Exception:
        pass

    if PF_PATH not in sys.path:
        sys.path.insert(0, PF_PATH)
    import powerfactory as pf  # type: ignore

    app = pf.GetApplication()
    if app is None:
        raise RuntimeError("No se pudo conectar a PowerFactory.")
    app.ActivateProject(project)
    return app


def pf_log(app, msg: str, level: str = "info"):
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


def get_network(app):
    nets = app.GetCalcRelevantObjects("*.ElmNet") or []
    for n in nets:
        if getattr(n, "loc_name", "") == "Red":
            return n
    if not nets:
        raise RuntimeError("No se encontro ElmNet en el proyecto.")
    return nets[0]


def find_pf_terminal(app, name: str):
    for cls in ("ElmTerm",):
        for o in app.GetCalcRelevantObjects(f"*.{cls}") or []:
            if getattr(o, "loc_name", None) == name:
                return o
    return None


def list_pf_terminal_names(app) -> set[str]:
    return {
        getattr(o, "loc_name", "")
        for o in app.GetCalcRelevantObjects("*.ElmTerm") or []
        if getattr(o, "loc_name", None)
    }


def set_terminal_name(term, new_name: str) -> None:
    term.loc_name = new_name


def create_pf_terminal(net, app, name: str, uknom: float = V_NOM_KV):
    term = net.CreateObject("ElmTerm", name)
    if term is None:
        raise RuntimeError(f"CreateObject ElmTerm '{name}' devolvio None")
    term.uknom = uknom
    try:
        term.iUsage = 0
    except Exception:
        pass
    try:
        term.phtech = 0
    except Exception:
        pass
    return term
