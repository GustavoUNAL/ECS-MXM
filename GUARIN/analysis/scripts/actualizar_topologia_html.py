#!/usr/bin/env python3
"""Inyecta escenarios PF y layout vertical en topologia_interactiva.html."""
from __future__ import annotations

import json
import re
from pathlib import Path

from paths import OUTPUT, WEB

HTML = WEB / "topologia_interactiva.html"
ESC = OUTPUT / "escenarios_operacion.json"

CSS_EXTRA = """
.scenarios-wrap { padding:10px 22px 0; border-bottom:1px solid var(--line); background:#0e1628; }
.scenarios-wrap h3 { margin:0 0 8px; font-size:12px; color:var(--muted); font-weight:600; letter-spacing:.3px; text-transform:uppercase; }
.scenarios { display:flex; flex-wrap:wrap; gap:6px; padding-bottom:10px; }
.sc-btn {
  background:var(--panel2); color:var(--text); border:1px solid var(--line);
  border-radius:999px; padding:6px 12px; font-size:12px; cursor:pointer;
}
.sc-btn:hover { border-color:var(--accent); }
.sc-btn.active { background:#1e3a8a; border-color:#3d8bfd; }
.sc-btn.gen { border-color:#2ec4b6; }
.sc-btn.gen.active { background:#0f4c45; border-color:#2ec4b6; }
.sc-info { font-size:12px; color:var(--muted); margin:0 0 10px; min-height:18px; }
.kpis.scenario { grid-template-columns:repeat(7,minmax(90px,1fr)); }
"""

HTML_SCENARIOS_BAR = """
<section class="scenarios-wrap">
  <h3>Escenarios operacionales (flujo de carga ESSA · 6 corridas PF)</h3>
  <div class="scenarios" id="scenarios"></div>
  <p class="sc-info" id="scInfo">Selecciona un escenario para colorear nodos por tensión y ver KPIs del caso.</p>
</section>
"""

JS_REPLACEMENTS: list[tuple[str, str]] = [
    (
        ".layout { display:grid; grid-template-columns: 1.4fr .9fr; gap:12px; padding:0 22px 16px; height: calc(100% - 168px); }",
        ".layout { display:grid; grid-template-columns: 1.4fr .9fr; gap:12px; padding:0 22px 16px; height: calc(100% - 248px); }",
    ),
    (
        '<section class="kpis" id="kpis"></section>',
        HTML_SCENARIOS_BAR + '\n<section class="kpis" id="kpis"></section>\n<section class="kpis scenario" id="kpisScenario" style="display:none"></section>',
    ),
    (
        '<div class="tab" data-tab="cargas">Cargas</div>',
        '<div class="tab" data-tab="cargas">Cargas</div>\n      <div class="tab" data-tab="escenarios">Escenarios</div>',
    ),
    (
        '<div id="cargas" class="panel"></div>',
        '<div id="cargas" class="panel"></div>\n    <div id="escenarios" class="panel"></div>',
    ),
    (
        '/** Layout arbóreo desde la subestación: ramas paralelas sin cruces (estilo unifilar). */',
        '/** Layout arbóreo vertical: SE arriba, ramas hacia abajo (estilo unifilar). */',
    ),
    (
        """  const yPos = new Map();
  let leafIdx = 0;
  function assignY(u) {
    const ch = (children.get(u) || []).slice().sort((a, b) => {
      const da = D.nodes.find(n => n.id === a)?.degree || 0;
      const db = D.nodes.find(n => n.id === b)?.degree || 0;
      return db - da || String(a).localeCompare(String(b), "es");
    });
    if (!ch.length) {
      yPos.set(u, leafIdx++);
      return yPos.get(u);
    }
    const ys = ch.map(assignY);
    yPos.set(u, ys.reduce((s, y) => s + y, 0) / ys.length);
    return yPos.get(u);
  }
  assignY(rootId);

  const xGap = 155;
  const yGap = 42;
  const pos = new Map();
  for (const [id, d] of depth) {
    pos.set(id, { x: d * xGap, y: (yPos.get(id) || 0) * yGap });
  }
  D.nodes.forEach(n => {
    if (pos.has(n.id)) return;
    pos.set(n.id, { x: (Math.max(...depth.values()) + 2) * xGap, y: leafIdx++ * yGap });
  });""",
        """  const xPos = new Map();
  let leafIdx = 0;
  function assignX(u) {
    const ch = (children.get(u) || []).slice().sort((a, b) => {
      const da = D.nodes.find(n => n.id === a)?.degree || 0;
      const db = D.nodes.find(n => n.id === b)?.degree || 0;
      return db - da || String(a).localeCompare(String(b), "es");
    });
    if (!ch.length) {
      xPos.set(u, leafIdx++);
      return xPos.get(u);
    }
    const xs = ch.map(assignX);
    xPos.set(u, xs.reduce((s, x) => s + x, 0) / xs.length);
    return xPos.get(u);
  }
  assignX(rootId);

  const xGap = 42;
  const yGap = 72;
  const pos = new Map();
  for (const [id, d] of depth) {
    pos.set(id, { x: (xPos.get(id) || 0) * xGap, y: d * yGap });
  }
  D.nodes.forEach(n => {
    if (pos.has(n.id)) return;
    pos.set(n.id, { x: leafIdx++ * xGap, y: (Math.max(...depth.values()) + 2) * yGap });
  });""",
    ),
    (
        'forceDirection: "horizontal"',
        'forceDirection: "vertical"',
    ),
    (
        'const D = JSON.parse(document.getElementById("data").textContent);',
        """const D = JSON.parse(document.getElementById("data").textContent);
const PF = JSON.parse(document.getElementById("escenarios").textContent);
const SCENARIOS = PF.scenarios;
const VMAP = PF.vmap;
let activeScenario = SCENARIOS[0];""",
    ),
    (
        """function nodeColor(n) {
  if (n.role === "poc") return "#ff6b4a";
  if (n.role === "path") return "#f4c95d";
  if (n.role === "load") return "#2ec4b6";
  return "#6ea8fe";
}""",
        """function voltageColor(pu) {
  if (pu == null || Number.isNaN(pu)) return null;
  if (pu < 0.90 || pu > 1.10) return "#ff4757";
  if (pu < 0.95 || pu > 1.05) return "#ffa502";
  return "#5dd39e";
}
function nodeColor(n, sc = activeScenario) {
  const v = sc && VMAP[n.id] ? VMAP[n.id][sc.vkey] : null;
  const vc = voltageColor(v);
  if (vc) return vc;
  if (n.role === "poc") return "#ff6b4a";
  if (n.role === "path") return "#f4c95d";
  if (n.role === "load") return "#2ec4b6";
  return "#6ea8fe";
}
function nodeBorder(n) {
  if (n.role === "poc") return "#ff6b4a";
  if (n.role === "path") return "#f4c95d";
  return "#0b1220";
}""",
    ),
    (
        """function tipNode(n) {
  return `Nodo ${n.id}\\nRol: ${n.role}\\nGrado: ${n.degree}` +
    (n.load ? `\\nCarga: ${n.load}\\n${n.s_mva} MVA / ${n.p_kw} kW` : "");
}""",
        """function tipNode(n, sc = activeScenario) {
  const v = sc && VMAP[n.id] ? VMAP[n.id][sc.vkey] : null;
  return `Nodo ${n.id}\\nRol: ${n.role}\\nGrado: ${n.degree}` +
    (v != null ? `\\nTensión (${sc.label}): ${v.toFixed(4)} p.u.` : "") +
    (n.load ? `\\nCarga: ${n.load}\\n${n.s_mva} MVA / ${n.p_kw} kW` : "");
}""",
    ),
    (
        """const allNodes = D.nodes.map(n => ({
  id: n.id, label: n.id, title: tipNode(n),
  color: { background: nodeColor(n), border: "#0b1220" },
  size: nodeSize(n), font: { color: "#dbe7ff", size: 11 },
  x: layoutPos.get(n.id).x,
  y: layoutPos.get(n.id).y,
  fixed: { x: true, y: true },
  _role: n.role, _data: n
}));""",
        """function buildVisNode(n, sc = activeScenario) {
  return {
    id: n.id,
    label: n.id === ROOT ? "SE Conucos" : n.id,
    title: tipNode(n, sc),
    color: { background: nodeColor(n, sc), border: nodeBorder(n), highlight: { background: nodeColor(n, sc), border: "#fff" } },
    size: nodeSize(n),
    font: { color: "#dbe7ff", size: n.id === ROOT ? 12 : 11 },
    x: layoutPos.get(n.id).x,
    y: layoutPos.get(n.id).y,
    fixed: { x: true, y: true },
    _role: n.role, _data: n
  };
}
const allNodes = D.nodes.map(n => buildVisNode(n));""",
    ),
    (
        """  document.getElementById("netstat").textContent = `${keepN.size} nodos · ${keepE.size} líneas · layout unifilar`;""",
        """  document.getElementById("netstat").textContent = `${keepN.size} nodos · ${keepE.size} líneas · ${activeScenario.label} · vertical`;""",
    ),
    (
        '<span><i class="dot" style="background:transparent;border:1px dashed #5a6a85;border-radius:2px"></i>Lazo / paralelo</span>',
        """<span><i class="dot" style="background:transparent;border:1px dashed #5a6a85;border-radius:2px"></i>Lazo / paralelo</span>
      <span><i class="dot" style="background:#5dd39e"></i>U 0,95–1,05 p.u.</span>
      <span><i class="dot" style="background:#ffa502"></i>U marginal</span>
      <span><i class="dot" style="background:#ff4757"></i>Fuera de banda</span>""",
    ),
]

JS_INSERT_BEFORE_APPLY = """
function fmt(n, d=3) { return Number(n).toLocaleString("es-CO", { minimumFractionDigits: d, maximumFractionDigits: d }); }

function renderScenarioKpis(sc) {
  const box = document.getElementById("kpisScenario");
  box.style.display = "grid";
  const gen = sc.trafo_p_mw < 0 ? `Exportación ${Math.abs(sc.trafo_p_mw).toFixed(1)} kW` : `Inyección trafo ${sc.trafo_p_mw.toFixed(1)} kW`;
  box.innerHTML = [
    ["Escenario", sc.label],
    ["S cabecera", fmt(sc.s_cabecera_mva) + " MVA"],
    ["U POC", fmt(sc.u_poc_pu, 4) + " p.u."],
    ["U min / max", fmt(sc.u_min_pu, 4) + " / " + fmt(sc.u_max_pu, 4)],
    ["Línea máx", fmt(sc.loading_linea_pct, 1) + " %"],
    ["Trafo POC", fmt(sc.loading_trafo_pct, 1) + " %"],
    ["Pérdidas", fmt(sc.perdidas_kw, 0) + " kW"],
  ].map(([k,v]) => `<div class="kpi"><span>${k}</span><b>${v}</b></div>`).join("");
  document.getElementById("scInfo").innerHTML =
    `<b>${sc.label}</b> · ${sc.nota} · ${gen} · ` +
    (sc.cumple ? `<span class="ok">Cumple banda y cargabilidad</span>` : `<span class="hl">Revisar cumplimiento</span>`);
}

function refreshNodeColors(sc) {
  allNodes.forEach(vn => {
    const n = vn._data;
    vn.title = tipNode(n, sc);
    vn.color = { background: nodeColor(n, sc), border: nodeBorder(n), highlight: { background: nodeColor(n, sc), border: "#fff" } };
  });
  const ds = network.body.data.nodes;
  allNodes.forEach(vn => ds.update(vn));
}

function highlightDemandHour(hora) {
  const h = parseInt(String(hora), 10);
  document.querySelectorAll("#chart .col").forEach((el, i) => {
    el.classList.toggle("peak", i === h);
    el.style.outline = i === h ? "2px solid #3d8bfd" : "";
  });
}

function selectScenario(sc) {
  activeScenario = sc;
  document.querySelectorAll(".sc-btn").forEach(b => b.classList.toggle("active", b.dataset.id === sc.id));
  renderScenarioKpis(sc);
  refreshNodeColors(sc);
  highlightDemandHour(sc.hora);
  applyFilter();
}

function renderScenarioButtons() {
  document.getElementById("scenarios").innerHTML = SCENARIOS.map(sc =>
    `<button type="button" class="sc-btn${sc.gen ? " gen" : ""}" data-id="${sc.id}">${sc.label}</button>`
  ).join("");
  document.querySelectorAll(".sc-btn").forEach(b => b.onclick = () => selectScenario(SCENARIOS.find(s => s.id === b.dataset.id)));
}

function renderEscenariosPanel() {
  document.getElementById("escenarios").innerHTML = `
    <div class="detail" style="margin-bottom:12px">
      <b>Estados de operación ESSA</b><br>
      Tres horas representativas (09:00, 12:00, 15:00) del perfil de demanda del 19/03/2024.<br>
      Cada hora se simula <b>sin</b> y <b>con</b> la AGPE de 120 kW AC en el POC 3272966 (6 corridas PF).
    </div>` +
    table(
      ["Escenario", "S cabecera", "U POC", "U min", "U max", "Línea %", "Trafo POC %", "Pérd. kW", "Trafo kW"],
      SCENARIOS.map(sc => [
        sc.label,
        fmt(sc.s_cabecera_mva),
        fmt(sc.u_poc_pu, 4),
        fmt(sc.u_min_pu, 4),
        fmt(sc.u_max_pu, 4),
        fmt(sc.loading_linea_pct, 1),
        fmt(sc.loading_trafo_pct, 1),
        fmt(sc.perdidas_kw, 0),
        fmt(sc.trafo_p_mw, 1)
      ])
    );
  sortable(document.getElementById("escenarios"));
}

renderScenarioButtons();
renderEscenariosPanel();
selectScenario(SCENARIOS[0]);

"""


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    esc_json = ESC.read_text(encoding="utf-8")

    if "</style>" not in html:
        raise SystemExit("No se encontró </style>")
    html = html.replace("</style>", CSS_EXTRA + "\n</style>", 1)

    for old, new in JS_REPLACEMENTS:
        if old not in html:
            raise SystemExit(f"Patrón no encontrado: {old[:80]}...")
        html = html.replace(old, new, 1)

    esc_tag = f'<script id="escenarios" type="application/json">{esc_json}</script>\n'
    if 'id="escenarios"' not in html:
        html = html.replace('<script>\nconst D = JSON.parse', esc_tag + '<script>\nconst D = JSON.parse', 1)

    if "renderScenarioButtons();" not in html:
        html = html.replace("applyFilter();\nshowNode", JS_INSERT_BEFORE_APPLY + "applyFilter();\nshowNode", 1)

    # showNode: add voltage if available
    html = html.replace(
        "    ${load ? `Carga <b>${load.name}</b>: ${load.s_mva} MVA · ${load.p_kw} kW · FP ${load.fp}` : \"Sin carga LV modelada\"}",
        "    ${activeScenario && VMAP[n.id] ? `<br>Tensión <b>${activeScenario.label}</b>: ${VMAP[n.id][activeScenario.vkey].toFixed(4)} p.u.` : \"\"}\n    ${load ? `Carga <b>${load.name}</b>: ${load.s_mva} MVA · ${load.p_kw} kW · FP ${load.fp}` : \"Sin carga LV modelada\"}",
        1,
    )

    HTML.write_text(html, encoding="utf-8")
    print("Actualizado:", HTML)


if __name__ == "__main__":
    main()
