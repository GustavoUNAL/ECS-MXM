/** UI de estados operacionales — requiere PF (escenarios_operacion.js) y globals del HTML principal. */
(function () {
  if (typeof PF === "undefined" || typeof D === "undefined") return;

  const SCENARIOS = PF.scenarios;
  const VMAP = PF.vmap;
  const HOURLY = PF.hourly || {};
  const PF_CONST = PF.constantes || {};
  let activeScenario = SCENARIOS[0];

  window._esc = { SCENARIOS, VMAP, HOURLY, activeScenario, getActive: () => activeScenario };

  function fmt(n, d = 3) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toFixed(d);
  }
  function fmtPctSigned(v, d = 1) {
    if (v == null || Number.isNaN(v)) return "—";
    const s = v >= 0 ? "+" : "";
    return s + Number(v).toFixed(d);
  }

  function voltageColor(pu) {
    if (pu == null || Number.isNaN(pu)) return null;
    if (pu < 0.90 || pu > 1.10) return "#ff4757";
    if (pu < 0.95 || pu > 1.05) return "#ffa502";
    return "#5dd39e";
  }

  function sinScenarioFor(hora) {
    return SCENARIOS.find(s => s.hora === hora && !s.gen);
  }
  function conScenarioFor(hora) {
    return SCENARIOS.find(s => s.hora === hora && s.gen);
  }
  function nodeDeltaU(nodeId, sc = activeScenario) {
    const h = HOURLY[sc?.hora];
    if (!h || !VMAP[nodeId]) return 0;
    const row = h.top_nodes.find(t => t.n === nodeId);
    if (row) return Math.abs(row.dU);
    const sin = sinScenarioFor(sc.hora);
    const con = conScenarioFor(sc.hora);
    if (!sin || !con) return 0;
    const vs = VMAP[nodeId][sin.vkey];
    const vc = VMAP[nodeId][con.vkey];
    if (vs == null || vc == null) return 0;
    return sc.gen ? Math.abs(vc - vs) : 0;
  }

  window.nodeColor = function (n, sc = activeScenario) {
    const v = sc && VMAP[n.id] ? VMAP[n.id][sc.vkey] : null;
    const vc = voltageColor(v);
    if (vc) return vc;
    if (n.role === "poc") return "#ff6b4a";
    if (n.role === "path") return "#f4c95d";
    if (n.role === "load") return "#2ec4b6";
    return "#6ea8fe";
  };
  window.nodeBorder = function (n, sc = activeScenario) {
    if (nodeDeltaU(n.id, sc) >= 0.0004) return "#e056fd";
    if (n.role === "poc") return "#ff6b4a";
    if (n.role === "path") return "#f4c95d";
    return getComputedStyle(document.documentElement).getPropertyValue("--node-border-default").trim() || "#0b1220";
  };
  window.nodeSize = function (n, sc = activeScenario) {
    if (n.role === "poc") return 22;
    const dU = nodeDeltaU(n.id, sc);
    if (dU >= 0.001) return 14 + Math.min(10, n.degree);
    if (dU >= 0.0004) return 12 + Math.min(8, n.degree * 0.8);
    return 8 + Math.min(14, n.degree * 1.3 + (n.s_mva ? 4 : 0));
  };

  function refreshNodeColors(sc = activeScenario) {
    const nodes = window.allNodes;
    const net = window.network;
    if (!nodes || !net) return;
    nodes.forEach(vn => {
      const n = vn._data;
      vn.title = window.tipNode(n, sc);
      vn.size = window.nodeSize(n, sc);
      vn.color = {
        background: window.nodeColor(n, sc),
        border: window.nodeBorder(n, sc),
        highlight: { background: window.nodeColor(n, sc), border: "#fff" }
      };
    });
    net.body.data.nodes.update(nodes);
  }
  window.refreshNodeColors = refreshNodeColors;

  const _tipNode = window.tipNode;
  window.tipNode = function (n, sc = activeScenario) {
    const base = _tipNode(n);
    const v = sc && VMAP[n.id] ? VMAP[n.id][sc.vkey] : null;
    return base + (v != null ? `\nTensión (${sc.label}): ${v.toFixed(4)} p.u.` : "");
  };

  function highlightDemandHour(hora) {
    const h = parseInt(String(hora).split(":")[0], 10);
    document.querySelectorAll("#chart .col").forEach((el, i) => {
      el.classList.toggle("peak", i === h);
      el.style.opacity = i === h ? "1" : "0.45";
    });
  }

  function renderScenarioKpis(sc) {
    const el = document.getElementById("kpisScenario");
    if (!el) return;
    el.style.display = "grid";
    const refPeak = SCENARIOS.find(s => s.id === "12_sin");
    const escala = refPeak ? sc.s_cabecera_mva / refPeak.s_cabecera_mva : null;
    const rows = [
      ["Escenario", sc.label],
      ["Demanda cabecera", fmt(sc.s_cabecera_mva) + " MVA"],
      ["Escala vs pico", escala != null ? fmt(escala, 4) : "—"],
      ["U POC", fmt(sc.u_poc_pu, 4) + " p.u."],
      ["U mín / máx", fmt(sc.u_min_pu, 4) + " / " + fmt(sc.u_max_pu, 4)],
      ["Línea máx", fmt(sc.loading_linea_pct, 1) + " %"],
      ["Trafo POC", fmt(sc.loading_trafo_pct, 1) + " %"],
    ];
    el.innerHTML = rows.map(([k, v]) => `<div class="kpi"><span>${k}</span><b>${v}</b></div>`).join("");
    document.getElementById("scInfo").textContent =
      `${sc.nota} · ${sc.gen ? "Con AGPE 120 kW" : "Sin AGPE"} · Pérdidas ${fmt(sc.perdidas_kw, 0)} kW · Trafo POC ${fmt(sc.trafo_p_mw, 1)} kW`;
  }

  function scenarioCompare(sc) {
    const sin = sinScenarioFor(sc.hora);
    const ref = sc.gen ? sin : (SCENARIOS.find(s => s.id === "12_sin") || sin);
    if (!ref || ref.id === sc.id) {
      const peak = SCENARIOS.find(s => s.id === "12_sin");
      return { ref: peak, refLabel: peak ? "vs 12:00 Sin (pico ESSA)" : "referencia", hourly: HOURLY[sc.hora] };
    }
    return { ref, refLabel: sc.gen ? `vs ${sin.label}` : `vs ${ref.label}`, hourly: HOURLY[sc.hora] };
  }

  function escBar(label, delta, max, cls) {
    const w = Math.max(3, 100 * Math.abs(delta) / max);
    return `<div class="esc-row"><span>${label}</span><div class="esc-bar ${cls}"><i style="width:${w}%"></i></div><span>${fmtPctSigned(delta, Math.abs(delta) < 0.01 ? 4 : 1)}</span></div>`;
  }

  function renderEscCharts(sc) {
    const box = document.getElementById("escCharts");
    if (!box) return;
    const { ref, refLabel, hourly } = scenarioCompare(sc);
    const deltas = [
      ["ΔU POC", sc.u_poc_pu - ref.u_poc_pu],
      ["ΔU mín", sc.u_min_pu - ref.u_min_pu],
      ["Δ línea %", sc.loading_linea_pct - ref.loading_linea_pct],
      ["Δ trafo %", sc.loading_trafo_pct - ref.loading_trafo_pct],
      ["Δ pérd. kW", sc.perdidas_kw - ref.perdidas_kw],
      ["Δ trafo kW", sc.trafo_p_mw - ref.trafo_p_mw],
    ];
    const max = Math.max(...deltas.map(d => Math.abs(d[1])), 0.001) * 1.1;
    const bars = deltas.map(([k, v]) => escBar(k, v, max, v >= 0 ? "pos" : "neg")).join("");
    const top = (hourly?.top_nodes || []).slice(0, 8).map(n =>
      `<div><code>${n.n}</code> ${fmtPctSigned(n.dU, 4)} p.u.</div>`
    ).join("") || "—";
    box.innerHTML = `
      <div class="esc-chart-mini">
        <h4>Cambios respecto a ${refLabel}</h4>
        ${bars}
      </div>
      <div class="esc-chart-mini">
        <h4>Nodos con mayor ΔU (${sc.hora}${sc.gen ? " · Con AGPE" : " · Sin AGPE"})</h4>
        <div class="esc-nodes-mini">${top}</div>
        <div style="margin-top:6px;font-size:10px;color:var(--muted)">Borde violeta en grafo: |ΔU Sin→Con| ≥ 0,0004 p.u.</div>
      </div>`;
  }

  function renderMetricBlock(title, metric, transform, unit, activeId) {
    const vals = SCENARIOS.map(s => transform(s[metric]));
    const max = Math.max(...vals, 0.001) * 1.08;
    const rows = SCENARIOS.map(s => {
      const v = transform(s[metric]);
      const w = Math.max(4, 100 * v / max);
      const cls = s.gen ? "bar-con" : "bar-sin";
      const active = s.id === activeId ? " active-sc" : "";
      return `<div class="cmp-row${active}"><span>${s.label}</span><div class="cmp-bar"><i class="${cls}" style="width:${w}%"></i></div><span>${fmt(v, metric.includes("pu") ? 4 : 1)}${unit}</span></div>`;
    }).join("");
    return `<div class="cmp-chart"><h4>${title}</h4>${rows}</div>`;
  }

  function renderComparativaPanel(activeId) {
    const panel = document.getElementById("comparativa");
    if (!panel) return;
    const sc = SCENARIOS.find(s => s.id === activeId) || SCENARIOS[0];
    const h = HOURLY[sc.hora];
    const sinRows = h ? `
      <div class="cmp-delta"><b>Sin → Con AGPE (${sc.hora})</b><br>
      ΔU POC: ${fmtPctSigned(h.dU_poc, 4)} p.u. · ΔU mín: ${fmtPctSigned(h.dU_min, 4)} p.u.<br>
      Δ línea: ${fmtPctSigned(h.d_linea_pct, 2)} % · Δ trafo POC: ${fmtPctSigned(h.d_trafo_pct, 1)} %<br>
      Δ pérdidas: ${fmtPctSigned(h.d_perd_kw, 1)} kW · Trafo Sin ${fmt(h.trafo_sin_kw, 1)} kW → Con ${fmt(h.trafo_con_kw, 1)} kW
      </div>` : "";
    panel.innerHTML = `
      <div class="detail" style="margin-bottom:12px">
        <b>Qué define cada estado</b><br>
        · <b>Hora (ESSA):</b> demanda de cabecera del 19/03/2024 — escala todas las cargas del circuito.<br>
        · <b>Sin / Con AGPE:</b> operación del circuito sin o con la planta de 120 kW AC en el POC 3272966 (metodología CREG).<br>
        · <b>Resultados de flujo:</b> del estudio de conexión (tensiones, cargas de línea/trafo, pérdidas).
      </div>
      ${sinRows}
      <div class="cmp-legend">
        <span><i style="background:#6ea8fe"></i>Sin SSFV</span>
        <span><i style="background:#2ec4b6"></i>Con SSFV</span>
      </div>
      <div class="cmp-grid">
        ${renderMetricBlock("Tensión POC", "u_poc_pu", v => v, " p.u.", activeId)}
        ${renderMetricBlock("Tensión mínima", "u_min_pu", v => v, " p.u.", activeId)}
        ${renderMetricBlock("Carga línea máx", "loading_linea_pct", v => v, " %", activeId)}
        ${renderMetricBlock("Carga trafo POC", "loading_trafo_pct", v => v, " %", activeId)}
        ${renderMetricBlock("Pérdidas circuito", "perdidas_kw", v => v, " kW", activeId)}
        ${renderMetricBlock("Pot. trafo POC", "trafo_p_mw", v => Math.abs(v), " kW", activeId)}
      </div>
      <p class="cmp-note">${Object.entries(PF_CONST).map(([k,v]) => `<b>${k}:</b> ${v}`).join(" · ")}</p>`;
  }

  function highlightEscenarioTable(activeId) {
    document.querySelectorAll("#escenarios tbody tr").forEach(tr => {
      tr.classList.toggle("active-sc", tr.dataset.sc === activeId);
    });
  }

  function renderScenarioButtons() {
    const box = document.getElementById("scenarioBtns");
    if (!box) return;
    box.innerHTML = SCENARIOS.map(sc =>
      `<button type="button" class="sc-btn${sc.gen ? " gen" : ""}" data-id="${sc.id}" title="${sc.nota}">${sc.label}</button>`
    ).join("");
    box.querySelectorAll(".sc-btn").forEach(b => b.onclick = () => selectScenario(SCENARIOS.find(s => s.id === b.dataset.id)));
  }

  function renderEscenariosPanel() {
    const rows = SCENARIOS.map(sc => [
      sc.label, fmt(sc.s_cabecera_mva), fmt(sc.u_poc_pu, 4), fmt(sc.u_min_pu, 4), fmt(sc.u_max_pu, 4),
      fmt(sc.loading_linea_pct, 1), fmt(sc.loading_trafo_pct, 1), fmt(sc.perdidas_kw, 0), fmt(sc.trafo_p_mw, 1)
    ]);
    const head = ["Escenario", "S cabecera", "U POC", "U min", "U max", "Línea %", "Trafo POC %", "Pérd. kW", "Trafo kW"]
      .map((h, i) => `<th data-i="${i}">${h}</th>`).join("");
    const body = SCENARIOS.map((sc, idx) =>
      `<tr data-sc="${sc.id}">${rows[idx].map(c => `<td>${c}</td>`).join("")}</tr>`
    ).join("");
    document.getElementById("escenarios").innerHTML = `
      <div class="detail" style="margin-bottom:12px">
        <b>6 estados de operación</b> — tres horas representativas con perfil ESSA (09:00, 12:00, 15:00 del 19/03/2024),
        cada una <b>sin</b> y <b>con</b> la AGPE de 120 kW AC. Clic en una fila para activar el escenario en el grafo.
      </div>
      <div style="overflow:auto"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    sortable(document.getElementById("escenarios"));
    document.querySelectorAll("#escenarios tbody tr").forEach(tr => {
      tr.style.cursor = "pointer";
      tr.onclick = () => selectScenario(SCENARIOS.find(s => s.id === tr.dataset.sc));
    });
  }

  window.selectScenario = function (sc) {
    activeScenario = sc;
    window._esc.activeScenario = sc;
    document.querySelectorAll(".sc-btn").forEach(b => b.classList.toggle("active", b.dataset.id === sc.id));
    renderScenarioKpis(sc);
    renderEscCharts(sc);
    refreshNodeColors(sc);
    highlightDemandHour(sc.hora);
    renderComparativaPanel(sc.id);
    highlightEscenarioTable(sc.id);
    if (typeof applyFilter === "function") applyFilter();
  };

  const _applyFilter = window.applyFilter;
  if (_applyFilter) {
    window.applyFilter = function () {
      _applyFilter();
      const ns = document.getElementById("netstat");
      if (ns && activeScenario) {
        const base = ns.textContent.replace(/ · \d{2}:\d{2} · .*$/, "");
        ns.textContent = base + ` · ${activeScenario.label}`;
      }
    };
  }

  const _showNode = window.showNode;
  if (_showNode) {
    window.showNode = function (n) {
      _showNode(n);
      if (activeScenario && VMAP[n.id]) {
        const v = VMAP[n.id][activeScenario.vkey];
        if (v != null) {
          document.getElementById("detailBox").innerHTML +=
            `<br>Tensión <b>${activeScenario.label}</b>: ${v.toFixed(4)} p.u.`;
        }
      }
    };
  }

  renderScenarioButtons();
  renderEscenariosPanel();
  renderComparativaPanel(SCENARIOS[0].id);
  selectScenario(SCENARIOS[0]);
})();
