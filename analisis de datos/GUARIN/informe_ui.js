/** Panel de informe interactivo — requiere INFORME (informe_circuito.js). */
(function () {
  if (typeof INFORME === "undefined") return;

  const I = INFORME;
  const inv = I.inventario;
  const dem = I.demanda;
  const est = I.estados_operacionales;
  const pdf = I.pdf_validacion;

  function fmt(n, d = 3) {
    if (n == null || Number.isNaN(n)) return "—";
    return Number(n).toFixed(d);
  }

  function svgDemandCurve() {
    const pts = dem.puntos;
    const w = 640, h = 140, padL = 36, padR = 12, padT = 12, padB = 28;
    const ys = pts.map(p => p.S_MVA);
    const yMin = Math.min(...ys) * 0.92;
    const yMax = Math.max(...ys) * 1.04;
    const iw = w - padL - padR;
    const ih = h - padT - padB;
    const xAt = i => padL + (i / 23) * iw;
    const yAt = v => padT + ih - ((v - yMin) / (yMax - yMin)) * ih;
    const path = pts.map((p, i) => `${i ? "L" : "M"}${xAt(i).toFixed(1)},${yAt(p.S_MVA).toFixed(1)}`).join(" ");
    const studyHours = { 9: "09:00", 12: "12:00", 15: "15:00" };
    const marks = Object.entries(studyHours).map(([h, label]) => {
      const i = +h;
      const p = pts[i];
      return `<circle cx="${xAt(i)}" cy="${yAt(p.S_MVA)}" r="5" fill="#ff6b4a"/>
        <text x="${xAt(i)}" y="${yAt(p.S_MVA) - 8}" text-anchor="middle" fill="#ff6b4a" font-size="9">${label}</text>`;
    }).join("");
    const grid = [0, 0.5, 1].map(t => {
      const y = padT + ih * (1 - t);
      const val = yMin + (yMax - yMin) * t;
      return `<line x1="${padL}" y1="${y}" x2="${w - padR}" y2="${y}" stroke="var(--line)" opacity=".4"/>
        <text x="${padL - 4}" y="${y + 3}" text-anchor="end" fill="var(--muted)" font-size="9">${val.toFixed(2)}</text>`;
    }).join("");
    return `<svg viewBox="0 0 ${w} ${h}" style="width:100%;max-width:680px;height:auto">
      ${grid}<path d="${path}" fill="none" stroke="#3d8bfd" stroke-width="2.5"/>
      ${marks}
      <text x="${padL}" y="${h - 6}" fill="var(--muted)" font-size="9">00:00</text>
      <text x="${w - padR}" y="${h - 6}" text-anchor="end" fill="var(--muted)" font-size="9">23:00</text>
    </svg>`;
  }

  function renderResumen() {
    const el = document.getElementById("view-resumen");
    if (!el) return;
    el.innerHTML = `
      <div class="informe-intro detail">
        <b>Circuito ${I.fuentes.circuito}</b> · ${I.fuentes.subestacion} · ${I.fuentes.tension_kv} kV · ${I.fuentes.operador}<br>
        Proyecto AGPE: ${I.fuentes.proyecto} · POC nodo <b>${inv.poc_nodo}</b> (${inv.poc_carga})
      </div>
      <div class="informe-kpis">
        <div class="kpi big"><span>Nodos</span><b>${inv.n_nodos}</b><small>Excel · hoja Líneas</small></div>
        <div class="kpi big"><span>Líneas</span><b>${inv.n_lineas}</b><small>tramos del modelo</small></div>
        <div class="kpi big"><span>Cargas LV</span><b>${inv.n_cargas}</b><small>S = ${fmt(inv.s_cargas_mva)} MVA</small></div>
        <div class="kpi big"><span>Longitud</span><b>${fmt(inv.longitud_km, 3)}</b><small>km totales</small></div>
      </div>
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Fuentes de datos</h4>
          <table class="informe-table">
            <tr><th>Archivo</th><th>Contenido</th></tr>
            <tr><td><code>${I.fuentes.excel}</code></td><td>Modelo eléctrico: líneas, impedancias, cargas, demanda 24 h</td></tr>
            <tr><td><code>${I.fuentes.pdf}</code></td><td>Diagrama unifilar del circuito (referencia gráfica OR)</td></tr>
          </table>
        </div>
        <div class="informe-card">
          <h4>Validación Excel ↔ PDF</h4>
          <table class="informe-table">
            <tr><th>Elemento</th><th>Cantidad</th></tr>
            <tr><td>Etiquetas numéricas en PDF</td><td>${pdf.etiquetas_numericas}</td></tr>
            <tr><td>Coinciden con IDs de línea (Excel)</td><td>${pdf.coinciden_lineas} / ${inv.n_lineas}</td></tr>
            <tr><td>Coinciden con IDs de nodo (Excel)</td><td>${pdf.coinciden_nodos} / ${inv.n_nodos}</td></tr>
          </table>
          <p class="cmp-note">${pdf.nota}</p>
        </div>
      </div>
      <div class="informe-card">
        <h4>Conductores principales (Excel)</h4>
        <div class="bars">${I.conductores.slice(0, 8).map(c => {
          const max = I.conductores[0].km;
          return `<div class="barrow"><span>${c.name.replace("3F_15_", "")}</span>
            <div class="bar"><i style="width:${100 * c.km / max}%"></i></div>
            <span>${c.km} km · ${c.tramos} tr.</span></div>`;
        }).join("")}</div>
      </div>`;
  }

  function renderDemandaEstados() {
    const el = document.getElementById("demanda-intro");
    if (!el) return;
    const horasRows = Object.entries(dem.horas_estudio).map(([h, s]) =>
      `<tr><td>${h}</td><td>${fmt(s, 6)} MVA</td><td>${fmt(s / dem.s_max_mva * 100, 1)} % del pico</td></tr>`
    ).join("");
    el.innerHTML = `
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Perfil de demanda de cabecera · ${I.fuentes.fecha_demanda}</h4>
          ${svgDemandCurve()}
          <p class="cmp-note">Pico <b>${fmt(dem.s_max_mva, 3)} MVA</b> (${fmt(dem.i_max_a, 1)} A) a las 12:00 ·
          Mínimo ${fmt(dem.s_min_mva, 3)} MVA · Promedio ${fmt(dem.s_prom_mva, 3)} MVA.
          Puntos naranja = horas de estudio ESSA.</p>
        </div>
        <div class="informe-card">
          <h4>Horas representativas (insumo OR)</h4>
          <table class="informe-table"><thead><tr><th>Hora</th><th>S cabecera</th><th>Escala</th></tr></thead><tbody>${horasRows}</tbody></table>
          <p class="cmp-note">ESSA fija estas tres horas del perfil del <b>19/03/2024</b> para el estudio de conexión.</p>
        </div>
      </div>
      <div class="informe-grid-2">
        <div class="informe-card explain-card">
          <h4>Qué cambia al variar la hora (Sin AGPE)</h4>
          <ul>${est.que_cambia_hora.map(x => `<li>${x}</li>`).join("")}</ul>
        </div>
        <div class="informe-card explain-card">
          <h4>Qué cambia al pasar de Sin a Con AGPE (misma hora)</h4>
          <ul>${est.que_cambia_agpe.map(x => `<li>${x}</li>`).join("")}</ul>
        </div>
      </div>
      <div class="informe-card">
        <h4>${est.total} estados operacionales · ${est.descripcion}</h4>
        <p class="cmp-note">Usa la navegación siguiente para recorrer escenarios. El grafo (pestaña Grafo de red) se colorea según el escenario activo.</p>
      </div>`;
  }

  function renderDatos() {
    const el = document.getElementById("view-datos");
    if (!el) return;
    el.innerHTML = `<p class="cmp-note" style="margin-bottom:12px">Tablas del modelo Excel embebido en la visualización. Ordenables por columna.</p>`;
    const sis = document.getElementById("sistema");
    if (sis && sis.innerHTML.trim()) {
      const wrap = document.createElement("div");
      wrap.className = "informe-card";
      wrap.innerHTML = `<h4>Sistema / POC</h4><div class="detail">${sis.innerHTML}</div>`;
      el.appendChild(wrap);
    }
    ["nodos", "lineas", "cargas", "escenarios", "comparativa"].forEach(id => {
      const panel = document.getElementById(id);
      if (panel && el) {
        const wrap = document.createElement("div");
        wrap.className = "informe-card";
        wrap.innerHTML = `<h4>${id.charAt(0).toUpperCase() + id.slice(1)}</h4>`;
        wrap.appendChild(panel);
        panel.style.display = "block";
        panel.classList.add("active");
        el.appendChild(wrap);
      }
    });
  }

  function initMainNav() {
    const buttons = document.querySelectorAll(".main-nav button");
    const views = document.querySelectorAll(".view");
    let grafoReady = false;
    function show(name) {
      views.forEach(v => v.classList.toggle("active", v.id === "view-" + name));
      buttons.forEach(b => b.classList.toggle("active", b.dataset.view === name));
      if (name === "grafo" && window.network) {
        setTimeout(() => {
          window.network.redraw();
          window.network.fit({ animation: !grafoReady });
          grafoReady = true;
        }, 80);
      }
    }
    buttons.forEach(b => b.onclick = () => show(b.dataset.view));
    show("resumen");
  }

  renderResumen();
  renderDemandaEstados();
  renderDatos();
  initMainNav();
})();
