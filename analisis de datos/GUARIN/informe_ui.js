/** Panel de informe interactivo — requiere INFORME (informe_circuito.js). */
(function () {
  if (typeof INFORME === "undefined") return;

  const I = INFORME;
  const inv = I.inventario;
  const dem = I.demanda;
  const est = I.estados_operacionales;
  const pdf = I.pdf_validacion;
  const pve = I.pdf_vs_excel || {};
  const plan = I.plan_estudio_conexion || {};
  const xl = I.excel_analisis || {};
  const prot = (xl.protecciones || [])[0];
  const cargasSA = I.cargas_sin_agpe || null;

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

  function renderExcelAnalisis() {
    const hojas = (xl.hojas || ["Líneas", "Cargas_Demanda_corto", "Protecciones"]).map(h =>
      `<span class="tag">${h}</span>`).join("");
    const protRows = prot ? `
      <table class="informe-table" style="margin-top:8px">
        <tr><th>Campo</th><th>Valor</th></tr>
        <tr><td>Relé</td><td>${prot.rele} · bahía ${prot.bahia}</td></tr>
        <tr><td>RTC / RTP</td><td>${prot.rtc} / ${prot.rtp}</td></tr>
        <tr><td>Funciones</td><td>${prot.funciones}</td></tr>
        <tr><td>51 (sobrecorriente fase)</td><td>${prot["51_prim_A"]} A prim · TMS ${prot["51_tms"]}</td></tr>
        <tr><td>50 (instantáneo fase)</td><td>${prot["50_prim_A"]} A prim</td></tr>
        <tr><td>51N (sobrecorriente tierra)</td><td>${prot["51n_prim_A"]} A prim · TMS ${prot["51n_tms"]}</td></tr>
        <tr><td>50N (instantáneo tierra)</td><td>${prot["50n_prim_A"]} A prim</td></tr>
        <tr><td>Recierre 79</td><td>${prot.recierre_79}</td></tr>
      </table>` : "";
    return `
      <div class="informe-card">
        <h4>Análisis del Excel OR · ${I.fuentes.excel}</h4>
        <p class="cmp-note" style="margin:0 0 10px">Hojas: ${hojas}</p>
        <div class="informe-kpis-6">
          <div class="kpi big"><span>Líneas</span><b>${inv.n_lineas}</b><small>${xl.tramos_lazo || 0} lazos internos</small></div>
          <div class="kpi big"><span>Nodos</span><b>${inv.n_nodos}</b><small>${xl.n_conductores || 10} tipos conductor</small></div>
          <div class="kpi big"><span>Cargas</span><b>${inv.n_cargas}</b><small>${fmt(xl.carga_min_mva, 3)}–${fmt(xl.carga_max_mva, 2)} MVA</small></div>
          <div class="kpi big"><span>S cargas</span><b>${fmt(inv.s_cargas_mva)}</b><small>MVA instalados</small></div>
          <div class="kpi big"><span>P cargas</span><b>${fmt(xl.p_cargas_kw, 0)}</b><small>kW @ FP 0,9</small></div>
          <div class="kpi big"><span>Protección</span><b>${(xl.protecciones || []).length}</b><small>relé · ${prot ? "4 funciones" : "—"}</small></div>
        </div>
      </div>
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Cargas LV (hoja Cargas_Demanda_corto)</h4>
          <p class="cmp-note">${inv.n_cargas} cargas modeladas con potencia aparente nominal fija en el Excel.
          En el estudio, su <b>potencia activa se escala</b> según la hora del perfil de cabecera (factor = S<sub>cabecera</sub>(t) / S<sub>cabecera</sub>(pico)).</p>
          <table class="informe-table">
            <tr><td>S instalada total</td><td>${fmt(inv.s_cargas_mva)} MVA</td></tr>
            <tr><td>Demanda cabecera pico (12:00)</td><td>${fmt(dem.s_max_mva)} MVA · ${fmt(dem.i_max_a, 1)} A</td></tr>
            <tr><td>POC AGPE</td><td>${inv.poc_carga} · nodo ${inv.poc_nodo} · 0,15 MVA</td></tr>
          </table>
        </div>
        <div class="informe-card">
          <h4>Protección (hoja Protecciones)</h4>
          <p class="cmp-note">Un relé en la salida del circuito 10-502. Los ajustes <b>no cambian</b> entre estados operacionales.</p>
          ${protRows}
        </div>
      </div>`;
  }

  function renderCargasSinAgpe() {
    if (!cargasSA || !cargasSA.estados) return "";
    const horas = Object.keys(cargasSA.estados);
    const escalaRows = horas.map(h => {
      const e = cargasSA.estados[h];
      return `<tr><td>${h} · Sin AGPE</td><td>${fmt(e.s_cabecera_mva, 6)} MVA</td>
        <td>${e.i_cabecera_a != null ? fmt(e.i_cabecera_a, 1) + " A" : "—"}</td>
        <td><b>${fmt(e.escala, 4)}</b> (${fmt(e.escala_pct, 1)} %)</td>
        <td>${fmt(e.totales.p_kw, 0)} kW</td><td>${fmt(e.totales.s_mva, 3)} MVA</td></tr>`;
    }).join("");

    const tabs = horas.map((h, i) =>
      `<button type="button" class="cargas-tab${i === 1 ? " active" : ""}" data-hora="${h}">${h} Sin AGPE</button>`
    ).join("");

    function tableFor(hora) {
      const e = cargasSA.estados[hora];
      const rows = e.cargas.map(c => `<tr>
        <td>${c.name.replace("_LV_LOAD", "")}</td>
        <td>${c.node}</td>
        <td>${fmt(c.s_nominal_mva, 4)}</td>
        <td><b>${fmt(c.s_mva, 4)}</b></td>
        <td><b>${fmt(c.p_kw, 1)}</b></td>
        <td>${fmt(c.q_kvar, 1)}</td>
      </tr>`).join("");
      return `<table class="informe-table">
        <thead><tr><th>Carga</th><th>Nodo</th><th>S nom. 12h</th><th>S (MVA)</th><th>P (kW)</th><th>Q (kVAr)</th></tr></thead>
        <tbody>${rows}
        <tr style="font-weight:600;background:var(--panel2)">
          <td colspan="3">TOTAL ${hora}</td>
          <td>${fmt(e.totales.s_mva, 3)}</td>
          <td>${fmt(e.totales.p_kw, 0)}</td>
          <td>${fmt(e.totales.q_kvar, 0)}</td>
        </tr></tbody></table>`;
    }

    const panels = horas.map((h, i) =>
      `<div class="cargas-panel" data-hora="${h}" style="display:${i === 1 ? "block" : "none"}">${tableFor(h)}</div>`
    ).join("");

    return `
      <div class="informe-card" id="cargasSinAgpeCard">
        <h4>Insumo de cargas · Sin AGPE · 3 estados operacionales</h4>
        <p class="cmp-note">${cargasSA.metodo}<br>
        <code>${cargasSA.formula}</code><br>
        Los valores del Excel corresponden a la hora <b>base ${cargasSA.base_hora}</b> (${fmt(cargasSA.base_s_cabecera_mva, 3)} MVA cabecera).
        En 09:00 y 15:00 se multiplica <b>toda</b> carga por el mismo factor (Sin y Con AGPE comparten la misma potencia de carga a igual hora).</p>
        <table class="informe-table" style="margin-bottom:12px">
          <thead><tr><th>Estado</th><th>S cabecera</th><th>I cabecera</th><th>Escala vs 12:00</th><th>Σ P cargas</th><th>Σ S cargas</th></tr></thead>
          <tbody>${escalaRows}</tbody>
        </table>
        <div class="estado-tabs">${tabs}</div>
        <div class="cargas-estado-wrap">${panels}</div>
      </div>`;
  }

  function initCargasTabs() {
    const card = document.getElementById("cargasSinAgpeCard");
    if (!card) return;
    card.querySelectorAll(".cargas-tab").forEach(btn => {
      btn.onclick = () => {
        const h = btn.dataset.hora;
        card.querySelectorAll(".cargas-tab").forEach(b => b.classList.toggle("active", b === btn));
        card.querySelectorAll(".cargas-panel").forEach(p => {
          p.style.display = p.dataset.hora === h ? "block" : "none";
        });
      };
    });
  }

  function renderEstadosExplicacion() {
    const qh = est.que_cambia_hora || {};
    const listItems = (arr) => {
      if (!arr) return "";
      if (Array.isArray(arr)) return arr.map(x => `<li>${x}</li>`).join("");
      if (arr.insumo) return arr.insumo.map(x => `<li>${x}</li>`).join("");
      return "";
    };
    const insumoFijo = (est.insumo_fijo || est.que_no_cambia || []).map(x => `<li>${x}</li>`).join("");
    const escalaLi = cargasSA && cargasSA.estados
      ? Object.entries(cargasSA.estados).map(([h, e]) =>
          `<li>${h} → escala ${fmt(e.escala, 4)} (${fmt(e.escala_pct, 1)} %)</li>`).join("")
      : "";

    return `
      <div class="informe-card">
        <h4>Insumos por estado (Sin AGPE)</h4>
        <p class="cmp-note">El Excel fija la potencia <b>nominal</b> de cada carga a las <b>12:00</b> (pico).
        Las otras horas aplican el mismo factor a <b>las 51 cargas</b>. Sin y Con AGPE usan la misma potencia de carga a igual hora.</p>
        <div class="estado-flow">
          <div class="estado-box fijo"><b>Fijo (Excel)</b><ul>${insumoFijo}</ul></div>
          <div class="estado-box insumo"><b>Cambia con la hora</b><ul>${listItems(qh)}</ul></div>
          <div class="estado-box insumo"><b>Sin AGPE · 3 configuraciones</b><ul>${escalaLi}</ul></div>
        </div>
      </div>`;
  }

  function renderPdfVsExcel() {
    if (!pve.rol_pdf) return "";
    const listItems = arr => (arr || []).map(x => `<li>${x}</li>`).join("");
    const omitTipos = pve.omitidas_por_tipo || {};
    const omitRows = Object.entries(omitTipos).map(([k, n]) =>
      `<tr><td>${k.replace(/_/g, " ")}</td><td>${n}</td></tr>`
    ).join("");
    const orNoDiag = (pve.lineas_or_no_diagrama_ids || []).slice(0, 12).join(", ");
    const orRest = (pve.lineas_or_no_diagrama_ids || []).length > 12
      ? ` … +${pve.lineas_or_no_diagrama_ids.length - 12} más` : "";
    return `
      <div class="informe-card" style="margin-top:14px">
        <h4>PDF CTO 10 502 — qué aporta y qué cambia</h4>
        <p class="cmp-note ok" style="margin:0 0 12px">
          <b>Estados operacionales:</b> ${pve.que_cambia_con_estado}
        </p>
        <p class="cmp-note" style="margin:0 0 12px">${pve.rol_pdf}</p>
        <div class="informe-grid-2">
          <div>
            <h5 style="margin:0 0 6px;font-size:13px">Solo en el PDF (referencia gráfica)</h5>
            <ul class="informe-list">${listItems(pve.tiene_pdf)}</ul>
          </div>
          <div>
            <h5 style="margin:0 0 6px;font-size:13px">Solo en el Excel (modelo de cálculo)</h5>
            <ul class="informe-list">${listItems(pve.tiene_solo_excel)}</ul>
          </div>
        </div>
        <table class="informe-table" style="margin-top:12px">
          <tr><th>Equivalencia origen</th><td>PDF <code>${pve.origen_pdf}</code> = Excel <code>${pve.origen_excel}</code> — ${pve.equivalencia_origen}</td></tr>
          <tr><th>Líneas en diagrama manual</th><td>${pve.lineas_diagrama_manual ?? "—"} trazadas · ${pve.lineas_diagrama_en_or ?? "—"} en OR</td></tr>
          <tr><th>Líneas OR no graficadas</th><td>${pve.lineas_or_no_diagrama ?? "—"} (${orNoDiag}${orRest})</td></tr>
          <tr><th>Cargas en nodos del PDF</th><td>${pve.cargas_en_nodos_pdf ?? "—"} cargas LV (todas en Excel)</td></tr>
        </table>
        ${omitRows ? `<p class="cmp-note" style="margin:12px 0 6px"><b>${pdf.lineas_excel_sin_etiqueta_pdf ?? 125} tramos</b> del Excel sin etiqueta numérica en el unifilar — desglose:</p>
          <table class="informe-table"><thead><tr><th>Tipo</th><th>Cantidad</th></tr></thead><tbody>${omitRows}</tbody></table>` : ""}
      </div>`;
  }

  function renderPlanEstudio() {
    const el = document.getElementById("view-plan");
    if (!el || !plan.fases) return;

    const badgeLabel = { hecho: "Hecho", parcial: "En curso", pendiente: "Pendiente" };
    const rolRows = (plan.rol_archivos || []).map(r => `
      <tr>
        <td><code>${r.archivo}</code></td>
        <td>${r.rol}<br><span class="cmp-note">${r.no_es}</span></td>
      </tr>`).join("");
    const criteriosRows = (plan.criterios || []).map(c =>
      `<tr><td>${c.parametro}</td><td>${c.limite}</td></tr>`
    ).join("");
    const fasesHtml = plan.fases.map(f => `
      <article class="plan-fase estado-${f.estado}">
        <div class="plan-fase-head">
          <h4>Fase ${f.id} — ${f.nombre}</h4>
          <span class="plan-badge ${f.estado}">${badgeLabel[f.estado] || f.estado}</span>
        </div>
        <p class="plan-obj"><b>Objetivo:</b> ${f.objetivo}</p>
        <ol class="plan-steps">${f.pasos.map(p => `<li>${p}</li>`).join("")}</ol>
        <p class="plan-ent"><b>Entregable:</b> ${f.entregable}</p>
      </article>`).join("");
    const hechoLi = (plan.hecho || []).map(x => `<li>${x}</li>`).join("");
    const pendLi = (plan.pendiente || []).map(x => `<li>${x}</li>`).join("");
    const esc = plan.escenarios || {};

    el.innerHTML = `
      <div class="informe-intro detail">
        <b>${plan.titulo || "Plan de acción"}</b><br>
        ${plan.proyecto || ""} · Normativa: ${(plan.normativa || []).join(" · ")}
      </div>
      <div class="informe-card">
        <h4>Rol del Excel y del PDF</h4>
        <p class="cmp-note ok" style="margin:0 0 10px">${plan.regla}</p>
        <table class="informe-table">
          <tr><th>Archivo</th><th>Uso en el estudio</th></tr>
          ${rolRows}
        </table>
      </div>
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Escenarios de flujo de carga</h4>
          <table class="informe-table">
            <tr><td>Horas ESSA</td><td>${(esc.horas || []).join(" · ")}</td></tr>
            <tr><td>Modos</td><td>${(esc.modos || []).join(" · ")}</td></tr>
            <tr><td>Total</td><td>${esc.total ?? 6} escenarios</td></tr>
            <tr><td>Escala cargas</td><td>${esc.metodo_cargas || "—"}</td></tr>
          </table>
        </div>
        <div class="informe-card">
          <h4>Criterios de aceptación (CREG)</h4>
          <table class="plan-criterios">
            <thead><tr><th>Parámetro</th><th>Criterio</th></tr></thead>
            <tbody>${criteriosRows}</tbody>
          </table>
        </div>
      </div>
      <div class="informe-card">
        <h4>Fases del estudio</h4>
        <div class="plan-fases">${fasesHtml}</div>
        ${plan.decision ? `<div class="plan-decision"><b>Decisión clave:</b> ${plan.decision}</div>` : ""}
      </div>
      <div class="informe-card">
        <h4>Estado actual</h4>
        <div class="plan-checklist">
          <div>
            <h5 style="margin:0 0 6px;font-size:13px;color:var(--ok)">Completado</h5>
            <ul class="ok-list">${hechoLi}</ul>
          </div>
          <div>
            <h5 style="margin:0 0 6px;font-size:13px;color:var(--muted)">Por cerrar</h5>
            <ul class="todo-list">${pendLi}</ul>
          </div>
        </div>
      </div>`;
  }

  function renderResumen() {
    const el = document.getElementById("view-resumen");
    if (!el) return;
    el.innerHTML = `
      <div class="informe-intro detail">
        <b>Circuito ${I.fuentes.circuito}</b> · ${I.fuentes.subestacion} · ${I.fuentes.tension_kv} kV · ${I.fuentes.operador}<br>
        Proyecto AGPE: ${I.fuentes.proyecto} · POC nodo <b>${inv.poc_nodo}</b> (${inv.poc_carga})
      </div>
      ${renderExcelAnalisis()}
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Fuentes de datos</h4>
          <table class="informe-table">
            <tr><th>Archivo</th><th>Contenido</th></tr>
            <tr><td><code>${I.fuentes.excel}</code></td><td>Modelo eléctrico: líneas, impedancias, cargas, demanda 24 h, protección</td></tr>
            <tr><td><code>${I.fuentes.pdf}</code></td><td>Diagrama unifilar del circuito (referencia gráfica OR)</td></tr>
          </table>
        </div>
        <div class="informe-card">
          <h4>Validación Excel ↔ PDF</h4>
          <p class="cmp-note ${pdf.veredicto === "compatible" ? "ok" : "hl"}" style="margin:0 0 10px">
            <b>${pdf.veredicto === "compatible" ? "Fuentes compatibles" : "Revisar discrepancias"}</b> —
            ${pdf.veredicto_txt || pdf.nota}
          </p>
          <table class="informe-table">
            <tr><th>Comprobación</th><th>Resultado</th></tr>
            <tr><td>Etiquetas numéricas extraídas del PDF</td><td>${pdf.etiquetas_numericas_pdf ?? pdf.etiquetas_numericas ?? "—"}</td></tr>
            <tr><td>Todas existen en el Excel</td><td>${pdf.etiquetas_en_excel ?? "—"} (${fmt(pdf.pct_pdf_en_excel, 1)} %)</td></tr>
            <tr><td>IDs de línea visibles en PDF → Excel</td><td>${pdf.lineas_pdf_ok ?? "—"} / ${pdf.lineas_en_pdf ?? pdf.lineas_pdf_ok ?? "—"} coinciden</td></tr>
            <tr><td>IDs de nodo visibles en PDF → Excel</td><td>${pdf.nodos_pdf_ok ?? "—"} / ${pdf.nodos_en_pdf ?? pdf.nodos_pdf_ok ?? "—"} coinciden</td></tr>
            <tr><td>Tramos del modelo no etiquetados en unifilar</td><td>${pdf.lineas_excel_sin_etiqueta_pdf ?? "—"} de ${inv.n_lineas}</td></tr>
            <tr><td>Nodos sin número en PDF</td><td>${pdf.nodos_excel_sin_etiqueta_pdf ?? "—"} de ${inv.n_nodos}${pdf.nodos_sin_pdf?.length ? ` · ${pdf.nodos_sin_pdf.join(", ")} (en PDF: ${pve.origen_pdf || "CONUCO_13.8"})` : ""}</td></tr>
          </table>
        </div>
      </div>
      ${renderPdfVsExcel()}`;
  }

  function renderDemandaEstados() {
    const el = document.getElementById("demanda-intro");
    if (!el) return;
    const horasRows = Object.entries(dem.horas_estudio).map(([h, s]) =>
      `<tr><td>${h}</td><td>${fmt(s, 6)} MVA</td><td>${fmt(s / dem.s_max_mva * 100, 1)} % del pico</td></tr>`
    ).join("");
    el.innerHTML = `
      ${renderEstadosExplicacion()}
      ${renderCargasSinAgpe()}
      <div class="informe-grid-2">
        <div class="informe-card">
          <h4>Perfil de demanda de cabecera · ${I.fuentes.fecha_demanda}</h4>
          ${svgDemandCurve()}
          <p class="cmp-note">Pico <b>${fmt(dem.s_max_mva, 3)} MVA</b> (${fmt(dem.i_max_a, 1)} A) a las 12:00 ·
          Mínimo ${fmt(dem.s_min_mva, 3)} MVA · Promedio ${fmt(dem.s_prom_mva, 3)} MVA.
          Este perfil <b>escala las 51 cargas</b> en cada hora de estudio.</p>
        </div>
        <div class="informe-card">
          <h4>Horas representativas ESSA</h4>
          <table class="informe-table"><thead><tr><th>Hora</th><th>S cabecera</th><th>Escala cargas</th></tr></thead><tbody>${horasRows}</tbody></table>
        </div>
      </div>
      <div class="informe-card">
        <h4>${est.total} estados operacionales · ${est.descripcion}</h4>
        <p class="cmp-note">Usa la navegación siguiente. El grafo se colorea según tensiones del escenario activo.</p>
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
  renderPlanEstudio();
  renderDemandaEstados();
  renderDatos();
  initCargasTabs();
  initMainNav();
})();
