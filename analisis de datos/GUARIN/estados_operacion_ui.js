/** UI de estados operacionales — requiere PF (escenarios_operacion.js) y globals del HTML principal. */
(function () {
  if (typeof PF === "undefined" || typeof D === "undefined") return;

  const SCENARIOS = PF.scenarios;
  const VMAP = PF.vmap;
  const HOURLY = PF.hourly || {};
  const PF_CONST = PF.constantes || {};
  const HORAS = ["09:00", "12:00", "15:00"];
  const COL_SIN = "#6ea8fe";
  const COL_CON = "#2ec4b6";
  const COL_ACT = "#ff6b4a";
  const COL_REF = "#93a4c3";

  let activeScenario = SCENARIOS[0];
  let prevScenario = null;
  let scenarioIdx = 0;

  window._esc = { SCENARIOS, VMAP, HOURLY, activeScenario, getActive: () => activeScenario };

  function fmt(n, d = 3) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toFixed(d);
  }
  function fmtPctSigned(v, d = 1) {
    if (v == null || Number.isNaN(v)) return "—";
    return (v >= 0 ? "+" : "") + Number(v).toFixed(d);
  }
  function idxOf(sc) {
    return SCENARIOS.findIndex(s => s.id === sc.id);
  }
  function scenarioAt(i) {
    return SCENARIOS[((i % SCENARIOS.length) + SCENARIOS.length) % SCENARIOS.length];
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

  function flashKpis() {
    const el = document.getElementById("kpisScenario");
    if (!el) return;
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
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

  function updateNavState(sc) {
    const i = idxOf(sc);
    const ctr = document.getElementById("scCounter");
    if (ctr) ctr.textContent = `${i + 1} / ${SCENARIOS.length}`;
    document.querySelectorAll("#hourPills .pill").forEach(p =>
      p.classList.toggle("active", p.dataset.hora === sc.hora));
    document.querySelectorAll("#genToggle .pill").forEach(p =>
      p.classList.toggle("active", p.dataset.gen === (sc.gen ? "1" : "0")));
    document.querySelectorAll(".sc-btn").forEach(b =>
      b.classList.toggle("active", b.dataset.id === sc.id));
  }

  function renderNavBar() {
    const nav = document.getElementById("scNav");
    if (!nav) return;
    nav.innerHTML = `
      <div class="sc-nav-group">
        <button type="button" class="sc-nav-btn" id="scPrev" title="Escenario anterior (←)">◀</button>
        <span class="sc-counter" id="scCounter">1 / 6</span>
        <button type="button" class="sc-nav-btn" id="scNext" title="Siguiente escenario (→)">▶</button>
      </div>
      <div class="sc-nav-group">
        <span class="sc-nav-label">Hora ESSA</span>
        <div class="pill-group" id="hourPills">
          ${HORAS.map(h => `<button type="button" class="pill" data-hora="${h}">${h}</button>`).join("")}
        </div>
      </div>
      <div class="sc-nav-group">
        <span class="sc-nav-label">AGPE</span>
        <div class="pill-group" id="genToggle">
          <button type="button" class="pill" data-gen="0">Sin SSFV</button>
          <button type="button" class="pill gen" data-gen="1">Con 120 kW</button>
        </div>
      </div>
      <span class="sc-hint">← → navegar · 1-6 directo · ↑↓ Sin/Con</span>`;

    document.getElementById("scPrev").onclick = () => selectScenario(scenarioAt(scenarioIdx - 1));
    document.getElementById("scNext").onclick = () => selectScenario(scenarioAt(scenarioIdx + 1));
    document.querySelectorAll("#hourPills .pill").forEach(p => {
      p.onclick = () => {
        const sin = sinScenarioFor(p.dataset.hora);
        const con = conScenarioFor(p.dataset.hora);
        selectScenario(activeScenario.gen ? con : sin);
      };
    });
    document.querySelectorAll("#genToggle .pill").forEach(p => {
      p.onclick = () => {
        const sc = p.dataset.gen === "1" ? conScenarioFor(activeScenario.hora) : sinScenarioFor(activeScenario.hora);
        if (sc) selectScenario(sc);
      };
    });
  }

  function renderScenarioButtons() {
    const box = document.getElementById("scenarioBtns");
    if (!box) return;
    box.innerHTML = SCENARIOS.map((sc, i) =>
      `<button type="button" class="sc-btn${sc.gen ? " gen" : ""}" data-id="${sc.id}" data-idx="${i}" title="${sc.nota}">${i + 1}. ${sc.label}</button>`
    ).join("");
    box.querySelectorAll(".sc-btn").forEach(b =>
      b.onclick = () => selectScenario(SCENARIOS[+b.dataset.idx]));
  }

  /* ── SVG charts ── */
  function svgLineChart({ title, series, xLabels, yUnit, yDec = 2, h = 130, trend = false }) {
    const w = 300;
    const padL = 36, padR = 8, padT = 8, padB = 26;
    const allY = series.flatMap(s => s.ys.filter(v => v != null));
    if (!allY.length) return `<div class="curve-card"><h4>${title}</h4><p style="font-size:11px;color:var(--muted)">Sin datos</p></div>`;
    let yMin = Math.min(...allY);
    let yMax = Math.max(...allY);
    const padY = (yMax - yMin || 0.01) * 0.12;
    yMin -= padY;
    yMax += padY;
    const n = xLabels.length;
    const iw = w - padL - padR;
    const ih = h - padT - padB;
    const xAt = i => padL + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw);
    const yAt = v => padT + ih - ((v - yMin) / (yMax - yMin)) * ih;

    const grid = [0, 0.5, 1].map(t => {
      const y = padT + ih * (1 - t);
      const val = yMin + (yMax - yMin) * t;
      return `<line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="var(--line)" stroke-width="1" opacity=".5"/>
        <text x="${padL - 4}" y="${y + 3}" text-anchor="end" fill="var(--muted)" font-size="9">${val.toFixed(yDec)}</text>`;
    }).join("");

    const paths = series.map(s => {
      const pts = s.ys.map((y, i) => y == null ? null : [xAt(i), yAt(y)]);
      const valid = pts.filter(Boolean);
      if (!valid.length) return "";
      const d = valid.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
      const dots = valid.map(p =>
        `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3.5" fill="${s.color}" stroke="var(--panel)" stroke-width="1.5"/>`
      ).join("");
      return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" ${s.dash ? 'stroke-dasharray="5 4"' : ""}/>${dots}`;
    }).join("");

    const xLabs = xLabels.map((lb, i) =>
      `<text x="${xAt(i)}" y="${h - 6}" text-anchor="middle" fill="var(--muted)" font-size="9">${lb}</text>`
    ).join("");

    const legend = series.map(s =>
      `<span><i style="background:${s.color}${s.dash ? ";opacity:.7" : ""}"></i>${s.name}</span>`
    ).join("");

    return `<div class="curve-card${trend ? " trend" : ""}">
      <h4>${title}</h4>
      <svg viewBox="0 0 ${w} ${h}" aria-hidden="true">${grid}${paths}${xLabs}</svg>
      <div class="curve-legend">${legend}<span style="margin-left:auto">${yUnit || ""}</span></div>
    </div>`;
  }

  function svgTransitionChart(prev, curr) {
    if (!prev || prev.id === curr.id) {
      return `<div class="curve-card"><h4>Cambio vs escenario anterior</h4>
        <p style="font-size:12px;color:var(--muted);margin:20px 0">Usa ◀ ▶ para ver cómo evolucionan las magnitudes entre estados.</p></div>`;
    }
    const metrics = [
      { k: "u_poc_pu", lb: "U POC", u: " p.u.", d: 4, scale: 1 },
      { k: "u_min_pu", lb: "U mín", u: " p.u.", d: 4, scale: 1 },
      { k: "loading_linea_pct", lb: "Línea", u: " %", d: 1, scale: 1 },
      { k: "loading_trafo_pct", lb: "Trafo", u: " %", d: 1, scale: 1 },
      { k: "perdidas_kw", lb: "Pérdidas", u: " kW", d: 0, scale: 0.001 },
      { k: "trafo_p_mw", lb: "Trafo POC", u: " kW", d: 1, scale: 1 },
    ];
    const w = 300, h = 130, padL = 72, padR = 12, rowH = 18;
    const rows = metrics.map(m => {
      const a = prev[m.k] * (m.scale || 1);
      const b = curr[m.k] * (m.scale || 1);
      return { ...m, a, b, delta: b - a };
    });
    const maxAbs = Math.max(...rows.map(r => Math.max(Math.abs(r.a), Math.abs(r.b))), 0.001) * 1.15;
    const yAt = i => 16 + i * rowH;
    const xScale = v => padL + ((v + maxAbs) / (2 * maxAbs)) * (w - padL - padR);

    const body = rows.map((r, i) => {
      const y = yAt(i);
      const x0 = xScale(r.a);
      const x1 = xScale(r.b);
      const col = r.delta >= 0 ? "#5dd39e" : "#ff6b4a";
      return `<text x="4" y="${y + 4}" fill="var(--muted)" font-size="9">${r.lb}</text>
        <line x1="${Math.min(x0, x1)}" y1="${y}" x2="${Math.max(x0, x1)}" y2="${y}" stroke="${col}" stroke-width="3" stroke-linecap="round" opacity=".85"/>
        <circle cx="${x0}" cy="${y}" r="4" fill="${COL_REF}"/>
        <circle cx="${x1}" cy="${y}" r="4.5" fill="${COL_ACT}"/>
        <text x="${w - 4}" y="${y + 4}" text-anchor="end" fill="${col}" font-size="9">${fmtPctSigned(r.delta, r.d)}</text>`;
    }).join("");

    return `<div class="curve-card">
      <h4>Cambio: ${prev.label} → ${curr.label}</h4>
      <svg viewBox="0 0 ${w} ${h}" aria-hidden="true">
        <line x1="${xScale(0)}" y1="8" x2="${xScale(0)}" y2="${h - 8}" stroke="var(--line)" stroke-dasharray="3 3"/>
        ${body}
      </svg>
      <div class="curve-legend">
        <span><i style="background:${COL_REF}"></i>Anterior</span>
        <span><i style="background:${COL_ACT}"></i>Actual</span>
      </div>
    </div>`;
  }

  function pocProfileNodes() {
    const poc = D.meta.poc;
    const chain = [];
    const seen = new Set();
    if (D.poc_path?.length) {
      chain.push(D.poc_path[0].from);
      seen.add(chain[0]);
      D.poc_path.forEach(p => {
        if (!seen.has(p.to)) { chain.push(p.to); seen.add(p.to); }
      });
    }
    if (!seen.has(poc)) chain.push(poc);
    return chain.filter(id => VMAP[id]);
  }

  function svgVoltageProfile(sc) {
    const nodes = pocProfileNodes();
    const sin = sinScenarioFor(sc.hora);
    const labels = nodes.map((id, i) => i === nodes.length - 1 ? "POC" : id.slice(-4));
    const ysAct = nodes.map(id => VMAP[id]?.[sc.vkey] ?? null);
    const ysSin = sin ? nodes.map(id => VMAP[id]?.[sin.vkey] ?? null) : ysAct.map(() => null);
    const series = [
      { name: sc.label, color: COL_ACT, ys: ysAct },
      { name: sin ? `Sin ${sc.hora}` : "Referencia", color: COL_REF, ys: ysSin, dash: true },
    ];
    return svgLineChart({
      title: `Perfil de tensión · ruta al POC (${sc.hora})`,
      series,
      xLabels: labels,
      yUnit: "p.u.",
      yDec: 3,
      h: 140,
    });
  }

  function buildTrendCharts(sc) {
    const sinSeries = HORAS.map(h => sinScenarioFor(h));
    const conSeries = HORAS.map(h => conScenarioFor(h));
    const xShort = HORAS.map(h => h.slice(0, 5));

    const uPoc = svgLineChart({
      title: "Tensión POC · curvas Sin / Con",
      trend: true,
      series: [
        { name: "Sin SSFV", color: COL_SIN, ys: sinSeries.map(s => s?.u_poc_pu) },
        { name: "Con SSFV", color: COL_CON, ys: conSeries.map(s => s?.u_poc_pu) },
      ],
      xLabels: xShort,
      yUnit: "p.u.",
      yDec: 3,
    });

    const perd = svgLineChart({
      title: "Pérdidas del circuito · curvas Sin / Con",
      trend: true,
      series: [
        { name: "Sin SSFV", color: COL_SIN, ys: sinSeries.map(s => s?.perdidas_kw) },
        { name: "Con SSFV", color: COL_CON, ys: conSeries.map(s => s?.perdidas_kw) },
      ],
      xLabels: xShort,
      yUnit: "kW",
      yDec: 0,
    });

    const trafo = svgLineChart({
      title: "Carga trafo POC · curvas Sin / Con",
      trend: true,
      series: [
        { name: "Sin SSFV", color: COL_SIN, ys: sinSeries.map(s => s?.loading_trafo_pct) },
        { name: "Con SSFV", color: COL_CON, ys: conSeries.map(s => s?.loading_trafo_pct) },
      ],
      xLabels: xShort,
      yUnit: "%",
      yDec: 1,
    });

    return { uPoc, perd, trafo };
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

  function renderEscCharts(sc, prev) {
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

    const trends = buildTrendCharts(sc);
    const hi = HORAS.indexOf(sc.hora);

    box.innerHTML = `
      <div class="curve-grid">
        ${trends.uPoc}
        ${svgTransitionChart(prev, sc)}
        ${svgVoltageProfile(sc)}
      </div>
      <div class="curve-grid">
        ${trends.perd}
        ${trends.trafo}
        <div class="esc-chart-mini">
          <h4>Δ Sin → Con AGPE (${sc.hora}) · efecto de la planta</h4>
          ${hourly ? `
            <div style="font-size:11px;line-height:1.6;margin-bottom:8px">
              ΔU POC <b>${fmtPctSigned(hourly.dU_poc, 4)}</b> p.u. ·
              ΔU mín <b>${fmtPctSigned(hourly.dU_min, 4)}</b> p.u.<br>
              Δ línea <b>${fmtPctSigned(hourly.d_linea_pct, 2)}</b> % ·
              Δ trafo <b>${fmtPctSigned(hourly.d_trafo_pct, 1)}</b> % ·
              Δ pérd. <b>${fmtPctSigned(hourly.d_perd_kw, 1)}</b> kW
            </div>` : ""}
          <div class="esc-nodes-mini">${top}</div>
        </div>
      </div>
      <div class="esc-delta-grid">
        <div class="esc-chart-mini">
          <h4>Cambios respecto a ${refLabel}</h4>
          ${bars}
        </div>
        <div class="esc-chart-mini">
          <h4>Posición en el día ESSA</h4>
          <svg viewBox="0 0 300 90" style="width:100%;height:auto">
            ${HORAS.map((h, i) => {
              const x = 40 + i * 110;
              const s = sinScenarioFor(h);
              const c = conScenarioFor(h);
              const yS = 55 - (s?.u_poc_pu - 0.994) * 800;
              const yC = 55 - (c?.u_poc_pu - 0.994) * 800;
              const active = h === sc.hora;
              return `<g opacity="${active ? 1 : 0.45}">
                <text x="${x}" y="12" text-anchor="middle" fill="var(--muted)" font-size="10" font-weight="${active ? 700 : 400}">${h}</text>
                <line x1="${x - 20}" y1="${yS}" x2="${x + 20}" y2="${yS}" stroke="${COL_SIN}" stroke-width="2"/>
                <line x1="${x - 20}" y1="${yC}" x2="${x + 20}" y2="${yC}" stroke="${COL_CON}" stroke-width="2"/>
                <circle cx="${x - 20}" cy="${yS}" r="4" fill="${COL_SIN}"/>
                <circle cx="${x + 20}" cy="${yC}" r="4" fill="${COL_CON}"/>
                ${active ? `<rect x="${x - 28}" y="18" width="56" height="58" fill="none" stroke="var(--accent)" stroke-width="1.5" rx="6"/>` : ""}
              </g>`;
            }).join("")}
            <text x="4" y="58" fill="var(--muted)" font-size="8">U POC</text>
          </svg>
          <div class="curve-legend"><span><i style="background:${COL_SIN}"></i>Sin</span><span><i style="background:${COL_CON}"></i>Con</span></div>
        </div>
      </div>`;

    box.querySelectorAll(".curve-card.trend svg").forEach(svg => {
      const circles = svg.querySelectorAll("circle");
      [0, 1].forEach(sIdx => {
        const dot = circles[sIdx * HORAS.length + hi];
        if (dot) dot.setAttribute("r", "6");
      });
    });
  }

  function renderMetricBlock(title, metric, transform, unit, activeId) {
    const vals = SCENARIOS.map(s => transform(s[metric]));
    const max = Math.max(...vals, 0.001) * 1.08;
    return SCENARIOS.map(s => {
      const v = transform(s[metric]);
      const w = Math.max(4, 100 * v / max);
      const cls = s.gen ? "bar-con" : "bar-sin";
      const active = s.id === activeId ? " active-sc" : "";
      return `<div class="cmp-row${active}"><span>${s.label}</span><div class="cmp-bar"><i class="${cls}" style="width:${w}%"></i></div><span>${fmt(v, metric.includes("pu") ? 4 : 1)}${unit}</span></div>`;
    }).join("");
  }

  function renderComparativaPanel(activeId) {
    const panel = document.getElementById("comparativa");
    if (!panel) return;
    const sc = SCENARIOS.find(s => s.id === activeId) || SCENARIOS[0];
    const blocks = [
      ["Tensión POC", "u_poc_pu", v => v, " p.u."],
      ["Tensión mínima", "u_min_pu", v => v, " p.u."],
      ["Carga línea máx", "loading_linea_pct", v => v, " %"],
      ["Carga trafo POC", "loading_trafo_pct", v => v, " %"],
      ["Pérdidas circuito", "perdidas_kw", v => v, " kW"],
      ["Pot. trafo POC", "trafo_p_mw", v => Math.abs(v), " kW"],
    ];
    panel.innerHTML = `
      <div class="detail" style="margin-bottom:12px">
        <b>Curvas Sin / Con por hora ESSA</b> — arriba en la franja de escenarios.
        Usa ◀ ▶ o las pastillas Hora / AGPE para recorrer los 6 estados y ver el gráfico de transición.
      </div>
      <div class="cmp-legend">
        <span><i style="background:#6ea8fe"></i>Sin SSFV</span>
        <span><i style="background:#2ec4b6"></i>Con SSFV</span>
      </div>
      <div class="cmp-grid">
        ${blocks.map(([t, m, fn, u]) => `<div class="cmp-chart"><h4>${t}</h4>${renderMetricBlock(t, m, fn, u, activeId)}</div>`).join("")}
      </div>
      <p class="cmp-note">${Object.entries(PF_CONST).map(([k, v]) => `<b>${k}:</b> ${v}`).join(" · ")}</p>`;
  }

  function highlightEscenarioTable(activeId) {
    document.querySelectorAll("#escenarios tbody tr").forEach(tr =>
      tr.classList.toggle("active-sc", tr.dataset.sc === activeId));
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
        Clic en fila o usa el navegador superior. Teclas <b>← →</b> y <b>1-6</b>.
      </div>
      <div style="overflow:auto"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    sortable(document.getElementById("escenarios"));
    document.querySelectorAll("#escenarios tbody tr").forEach(tr => {
      tr.style.cursor = "pointer";
      tr.onclick = () => selectScenario(SCENARIOS.find(s => s.id === tr.dataset.sc));
    });
  }

  window.selectScenario = function (sc, opts = {}) {
    if (!sc) return;
    if (!opts.silent) prevScenario = activeScenario;
    activeScenario = sc;
    scenarioIdx = idxOf(sc);
    window._esc.activeScenario = sc;
    updateNavState(sc);
    renderScenarioKpis(sc);
    flashKpis();
    renderEscCharts(sc, prevScenario);
    refreshNodeColors(sc);
    highlightDemandHour(sc.hora);
    renderComparativaPanel(sc.id);
    highlightEscenarioTable(sc.id);
    if (typeof applyFilter === "function") applyFilter();
  };

  function bindKeyboard() {
    document.addEventListener("keydown", e => {
      if (e.target.matches("input, select, textarea")) return;
      if (e.key === "ArrowLeft") { e.preventDefault(); selectScenario(scenarioAt(scenarioIdx - 1)); }
      else if (e.key === "ArrowRight") { e.preventDefault(); selectScenario(scenarioAt(scenarioIdx + 1)); }
      else if (e.key === "ArrowUp") {
        e.preventDefault();
        const c = conScenarioFor(activeScenario.hora);
        if (c) selectScenario(c);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        const s = sinScenarioFor(activeScenario.hora);
        if (s) selectScenario(s);
      } else if (e.key >= "1" && e.key <= "6") {
        selectScenario(SCENARIOS[+e.key - 1]);
      }
    });
  }

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

  renderNavBar();
  renderScenarioButtons();
  renderEscenariosPanel();
  bindKeyboard();
  renderComparativaPanel(SCENARIOS[0].id);
  selectScenario(SCENARIOS[0], { silent: true });
})();
