#!/usr/bin/env python3
"""Topología interactiva: solo insumos del operador de red (sin resultados PF simulados)."""
from __future__ import annotations

import re
from pathlib import Path

HTML = Path(__file__).resolve().parent / "topologia_interactiva.html"

text = HTML.read_text(encoding="utf-8")

# Quitar script de escenarios PF
text = text.replace('<script src="escenarios_operacion.js"></script>\n', "")

# Barra de escenarios PF → aviso OR
text = re.sub(
    r"<section class=\"scenarios-wrap\">.*?</section>\n",
    '<p class="or-note">Datos del operador de red (ESSA): topología, líneas, cargas y perfil de demanda. '
    "Sin resultados de flujo de carga simulado.</p>\n",
    text,
    count=1,
    flags=re.S,
)
text = text.replace(
    '<section class="kpis scenario" id="kpisScenario" style="display:none"></section>\n', ""
)

# Pestañas y paneles PF
for chunk in [
    '      <div class="tab" data-tab="escenarios">Escenarios</div>\n',
    '      <div class="tab" data-tab="comparativa">Comparativa</div>\n',
    '    <div id="escenarios" class="panel"></div>\n',
    '    <div id="comparativa" class="panel"></div>\n',
]:
    text = text.replace(chunk, "")

# Leyenda tensión simulada
for chunk in [
    '      <span><i class="dot" style="background:#5dd39e"></i>U 0,95–1,05 p.u.</span>\n',
    '      <span><i class="dot" style="background:#ffa502"></i>U marginal</span>\n',
    '      <span><i class="dot" style="background:#ff4757"></i>Fuera de banda</span>\n',
    '      <span><i class="dot" style="background:#c084fc;border:2px solid #e056fd"></i>ΔU notable</span>\n',
]:
    text = text.replace(chunk, "")

text = text.replace("height: calc(100% - 340px)", "height: calc(100% - 168px)")

# Bloque JS PF
text = re.sub(
    r"const SCENARIOS = PF\.scenarios;.*?function nodeFontColor\(\) \{\n",
    "",
    text,
    count=1,
    flags=re.S,
)

# Restaurar nodeFontColor y funciones de nodo (solo OR)
insert = '''function nodeColor(n) {
  if (n.role === "poc") return "#ff6b4a";
  if (n.role === "path") return "#f4c95d";
  if (n.role === "load") return "#2ec4b6";
  return "#6ea8fe";
}
function nodeBorder(n) {
  if (n.role === "poc") return "#ff6b4a";
  if (n.role === "path") return "#f4c95d";
  return getComputedStyle(document.documentElement).getPropertyValue("--node-border-default").trim() || "#0b1220";
}
function nodeSize(n) {
  if (n.role === "poc") return 22;
  return 8 + Math.min(14, n.degree * 1.3 + (n.s_mva ? 4 : 0));
}
function nodeFontColor() {
'''

text = text.replace(
    "function nodeColor(n, sc = activeScenario) {",
    insert,
    1,
)
# Eliminar restos duplicados si el regex dejó basura
text = re.sub(r"function nodeColor\(n, sc = activeScenario\) \{.*?\n\}\n", "", text, count=1, flags=re.S)

# Funciones PF al final
for fn in [
    r"function fmt\(n, d=3\).*?function renderScenarioKpis\(sc\).*?function highlightDemandHour\(hora\).*?function selectScenario\(sc\).*?function renderScenarioButtons\(\).*?function fmtPctSigned\(v, d=1\).*?function renderMetricBlock\(.*?\n\}\n",
    r"function renderComparativaPanel\(activeId.*?\n\}\n",
    r"function highlightEscenarioTable\(activeId\).*?\n\}\n",
    r"function renderEscenariosPanel\(\).*?\n\}\n",
    r"renderScenarioButtons\(\);\nrenderEscenariosPanel\(\);\nrenderComparativaPanel\(SCENARIOS\[0\]\.id\);\n",
    r"selectScenario\(SCENARIOS\[0\]\);\n",
]:
    text = re.sub(fn, "", text, flags=re.S)

# Limpiar referencias activas
text = text.replace("function buildVisNode(n, sc = activeScenario)", "function buildVisNode(n)")
text = text.replace("function tipNode(n, sc = activeScenario)", "function tipNode(n)")
text = text.replace("nodeColor(vn._data, activeScenario)", "nodeColor(vn._data)")
text = text.replace("nodeBorder(vn._data, activeScenario)", "nodeBorder(vn._data)")
text = text.replace("nodeSize(vn._data, activeScenario)", "nodeSize(vn._data)")
text = text.replace("nodeColor(n, sc)", "nodeColor(n)")
text = text.replace("nodeBorder(n, sc)", "nodeBorder(n)")
text = text.replace("nodeSize(n, sc)", "nodeSize(n)")
text = text.replace("tipNode(n, sc)", "tipNode(n)")
text = text.replace("refreshNodeColors(activeScenario)", "")
text = text.replace("refreshNodeColors(sc)", "")
text = text.replace("function refreshNodeColors(sc) {\n  allNodes.forEach(vn => {\n    const n = vn._data;\n    vn.title = tipNode(n, sc);\n    vn.size = nodeSize(n, sc);\n    vn.color = {\n      background: nodeColor(n, sc),\n      border: nodeBorder(n, sc),\n      highlight: { background: nodeColor(n, sc), border: \"#fff\" }\n    };\n  });\n  const ds = network.body.data.nodes;\n  allNodes.forEach(vn => ds.update(vn));\n}\n", "")

text = re.sub(
    r"\$\{activeScenario && VMAP\[n\.id\].*?\}",
    "",
    text,
)
text = text.replace(
    'document.getElementById("netstat").textContent = `${keepN.size} nodos · ${keepE.size} líneas · ${activeScenario.label} · ${layoutLabel()}`;',
    'document.getElementById("netstat").textContent = `${keepN.size} nodos · ${keepE.size} líneas · ${layoutLabel()}`;',
)

# CSS nota OR
if ".or-note" not in text:
    text = text.replace(
        ".kpis { display:grid;",
        ".or-note { padding:8px 22px 10px; margin:0; font-size:12px; color:var(--muted); border-bottom:1px solid var(--line); background:var(--strip-bg); }\n.kpis { display:grid;",
    )

HTML.write_text(text, encoding="utf-8")
print(f"Actualizado: {HTML}")
