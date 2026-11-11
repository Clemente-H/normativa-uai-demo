
function init(root, DATA, send, primera) {
  const $id = (id) => root.querySelector('#' + id);
  const APP = root.querySelector('.app');



const CARGO_VAR = {"Decano/a de Pregrado":"--c-decano","Director/a de Pregrado":"--c-director","Comisión de Gracia":"--c-gracia","Secretaría Académica de Pregrado":"--c-secre","Profesor/a del curso":"--c-profe","Decano/a de Facultad o Escuela":"--c-facultad","Tribunal o Comité de Honor":"--c-honor","Otro":"--c-otro"};
const CARGO_CORTO = {"Secretaría Académica de Pregrado":"Secretaría Académica","Decano/a de Facultad o Escuela":"Decano/a de Facultad","Tribunal o Comité de Honor":"Comité de Honor"};
const CORTO = {cambio_licenciatura:"Cambio de licenciatura",cambio_sede:"Cambio de sede",suspension:"Suspensión",suspension_adicional:"Suspensión adicional",anulacion:"Anulación",reincorporacion:"Reincorporación",eliminacion_reconsideracion:"Reconsiderar eliminación",justificacion:"Justificar inasistencia",recorreccion:"Recorrección",convalidacion:"Convalidación",homologacion:"Homologación",sancion_honor:"Infracción al Código de Honor"};
const YEARS = Object.keys(DATA.por_año).map(Number).sort();
const TR = DATA.tramites.map(t => t.id);
const css = v => getComputedStyle(APP).getPropertyValue(v).trim();
const color = c => c ? css(CARGO_VAR[c] || "--c-otro") : css("--ink3");
const item = (y, id) => (DATA.por_año[y] || []).find(i => i.id === id) || null;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const pdf = (y, p) => DATA.urls[y] + (p ? "#page=" + p : "");
const ICON_EXT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 3h7v7M10 14 21 3M21 14v7H3V3h7"/></svg>';

let year = YEARS[YEARS.length - 1], selT = "suspension", selC = null, playing = null;

function changed(y, id) {
  const a = item(y, id), b = item(y - 1, id);
  if (!a || !b) return false;
  return (a.decide || null) !== (b.decide || null) || (a.decide_alt || null) !== (b.decide_alt || null);
}

/* ---------- tema ---------- */
function setTheme(t) {
  APP.dataset.theme = t;
  root.querySelectorAll(".toggle button").forEach(b => b.classList.toggle("on", b.dataset.t === t));
  try { localStorage.setItem("tema", t); } catch (e) {}
  renderAll();
}
root.querySelectorAll(".toggle button").forEach(b => b.onclick = () => setTheme(b.dataset.t));

/* ---------- cohorte ---------- */
const track = $id("track");
YEARS.forEach(y => { const b = document.createElement("button"); b.dataset.y = y; b.innerHTML = '<span class="dot"></span>' + y; b.onclick = () => { stopPlay(); setYear(y); }; track.appendChild(b); });
function setYear(y) { year = y; renderAll(); }
$id("play").onclick = () => playing ? stopPlay() : startPlay();
function startPlay() {
  const btn = $id("play"); btn.classList.add("on"); btn.querySelector("span").textContent = "Detener";
  let i = 0; setYear(YEARS[0]);
  playing = setInterval(() => { i++; if (i >= YEARS.length) return stopPlay(); setYear(YEARS[i]); }, 1500);
}
function stopPlay() { clearInterval(playing); playing = null; const btn = $id("play"); btn.classList.remove("on"); btn.querySelector("span").textContent = "Ver la evolución"; }

/* ---------- grafo ---------- */
const CARGOS_USADOS = DATA.cargos.filter(c => YEARS.some(y => DATA.por_año[y].some(i => i.decide === c || i.decide_alt === c)));
function renderGraph() {
  const svg = $id("graph");
  const H = 520, top = 26, rowT = (H - top * 2) / (TR.length - 1), rowC = (H - top * 2) / Math.max(1, CARGOS_USADOS.length - 1);
  const xc = 205, xt = 470;
  const yT = i => top + i * rowT, yC = i => top + i * rowC;
  const counts = {}; CARGOS_USADOS.forEach(c => counts[c] = 0);
  TR.forEach(id => { const it = item(year, id); if (it && it.decide in counts) counts[it.decide]++; if (it && it.decide_alt in counts) counts[it.decide_alt]++; });
  if (!svg.dataset.built) {
    let h = '<g id="links"></g>';
    CARGOS_USADOS.forEach((c, i) => {
      h += `<g class="cargo" data-c="${esc(c)}" transform="translate(0,${yC(i)})"><rect x="8" y="-15" width="${xc - 8}" height="30" rx="15"></rect><circle cx="${xc - 16}" cy="0" r="11"></circle><text class="n" x="${xc - 16}" y="4" text-anchor="middle">0</text><text x="22" y="4.5"></text></g>`;
    });
    TR.forEach((id, i) => {
      h += `<g class="tram" data-t="${id}" transform="translate(${xt},${yT(i)})"><rect x="0" y="-15" width="240" height="30" rx="9"></rect><text x="12" y="4.5">${esc(CORTO[id] || id)}</text><text class="chg" x="232" y="4" text-anchor="end"></text></g>`;
    });
    svg.innerHTML = h;
    const lg = svg.querySelector("#links");
    TR.forEach(id => { ["main", "alt"].forEach(k => { const p = document.createElementNS("http://www.w3.org/2000/svg", "path"); p.setAttribute("class", "link" + (k === "alt" ? " alt" : "")); p.dataset.t = id; p.dataset.k = k; lg.appendChild(p); }); });
    svg.querySelectorAll(".cargo").forEach(g => g.onclick = () => { selC = selC === g.dataset.c ? null : g.dataset.c; renderGraph(); renderDetail(); });
    svg.querySelectorAll(".tram").forEach(g => g.onclick = () => { selT = g.dataset.t; selC = null; renderAll(); });
    svg.dataset.built = 1;
  }
  svg.querySelectorAll(".cargo").forEach(g => {
    const c = g.dataset.c, col = color(c);
    g.classList.toggle("zero", counts[c] === 0);
    const r = g.querySelector("rect");
    r.setAttribute("fill", selC === c ? col : "transparent"); r.setAttribute("stroke", col); r.setAttribute("stroke-width", 2);
    g.querySelector("circle").setAttribute("fill", col);
    g.querySelector(".n").textContent = counts[c];
    const t = g.querySelectorAll("text")[1]; t.textContent = CARGO_CORTO[c] || c; t.style.fill = selC === c ? "#fff" : "";
  });
  let nChg = 0;
  svg.querySelectorAll(".tram").forEach(g => {
    const id = g.dataset.t, it = item(year, id), ch = changed(year, id);
    if (ch) nChg++;
    g.classList.toggle("sel", id === selT);
    g.classList.toggle("none", !it || !it.decide);
    g.classList.toggle("changed", ch);
    g.querySelector(".chg").textContent = ch ? "CAMBIÓ" : (!it || !it.decide ? "NO INDICA" : "");
  });
  svg.querySelectorAll(".link").forEach(p => {
    const id = p.dataset.t, it = item(year, id), i = TR.indexOf(id);
    const c = it ? (p.dataset.k === "main" ? it.decide : it.decide_alt) : null;
    const ci = CARGOS_USADOS.indexOf(c);
    if (ci < 0) { p.style.opacity = 0; p.setAttribute("d", `M${xt} ${yT(i)} C ${xt} ${yT(i)}, ${xt} ${yT(i)}, ${xt} ${yT(i)}`); return; }
    p.style.opacity = "";
    const y1 = yC(ci), y2 = yT(i), m = (xc + xt) / 2;
    p.setAttribute("d", `M${xc + 4} ${y1} C ${m} ${y1}, ${m} ${y2}, ${xt} ${y2}`);
    p.setAttribute("stroke", color(c)); p.style.color = color(c);
    p.classList.toggle("dim", (selC && c !== selC) || (!selC && selT && id !== selT && false));
    p.classList.toggle("hi", (selC && c === selC) || (!selC && id === selT));
  });
  $id("kChg").textContent = nChg;
  $id("kTram").textContent = TR.filter(id => (item(year, id) || {}).decide).length;
  $id("kVer").textContent = TR.filter(id => (item(year, id) || {}).verificada).length;
}

function whoHTML(c, lit) { if (!c) return '<span style="color:var(--ink3)">No indicado en el reglamento</span>'; return `<span class="who" style="color:${color(c)}"><i style="background:${color(c)}"></i><span style="color:var(--ink)">${esc(c === "Otro" && lit ? lit : c)}</span></span>`; }
function renderDetail() {
  const d = $id("detail");
  if (selC) {
    const lst = TR.map(id => ({ id, it: item(year, id) })).filter(o => o.it && (o.it.decide === selC || o.it.decide_alt === selC));
    d.innerHTML = `<span class="tag">Cargo | promoción ${year}</span><h3>${whoHTML(selC)}</h3><p class="meta" style="margin:0;color:var(--ink2);font-size:13.5px">Decide ${lst.length} de ${TR.length} trámites mapeados.</p>` +
      lst.map(o => `<div class="row"><span>${esc(CORTO[o.id])}</span><span>${esc(o.it.articulo || "")}${o.it.pagina_real ? ", p. " + o.it.pagina_real : ""}${o.it.decide_alt === selC ? " (alternativa)" : ""}</span></div>`).join("") +
      `<button class="btn" onclick="selC=null;renderGraph();renderDetail()">Volver al trámite</button>`;
    return;
  }
  const it = item(year, selT), prev = item(year - 1, selT);
  let h = `<span class="tag">Trámite | promoción ${year}</span><h3>${esc(CORTO[selT])}</h3>`;
  if (!it) { d.innerHTML = h + "<p>Sin datos.</p>"; return; }
  h += `<div class="row"><span>Decide</span><span>${whoHTML(it.decide, it.cargo_literal)}</span></div>`;
  if (it.decide_alt) h += `<div class="row"><span>O bien</span><span>${whoHTML(it.decide_alt)}</span></div>`;
  if (it.recibe) h += `<div class="row"><span>Se pide ante</span><span>${whoHTML(it.recibe)}</span></div>`;
  if (it.plazo) h += `<div class="row"><span>Plazo</span><span>${esc(it.plazo)}</span></div>`;
  if (it.condicion) h += `<div class="row"><span>Requisito</span><span>${esc(it.condicion)}</span></div>`;
  if (changed(year, selT)) h += `<div class="diff"><b>Cambió respecto de ${year - 1}:</b> antes decidía ${esc(prev.decide || "no indicado")}${prev.decide_alt ? " o " + esc(prev.decide_alt) : ""}.</div>`;
  if (it.cita) h += `<blockquote>"${esc(it.cita)}"</blockquote>`;
  h += `<div class="src">${it.verificada ? '<span class="tag ok">Cita verificada en el PDF</span>' : '<span class="tag bad">Cita no encontrada</span>'}<span>${esc(it.reglamento || "")} | ${esc(it.articulo || "")} | p. ${it.pagina_real || it.pagina || "?"}</span></div>`;
  h += `<div><a class="btn" target="_blank" rel="noopener" href="${pdf(year, it.pagina_real || it.pagina)}">${ICON_EXT}Abrir PDF oficial en esa página</a></div>`;
  if (it.nota) h += `<p style="margin:0;font-size:12.5px;color:var(--ink2)">${esc(it.nota)}</p>`;
  d.innerHTML = h;
}

/* ---------- matriz ---------- */
function renderMatrix() {
  const m = $id("matrix");
  let h = "<tr><th class='rowh'></th>" + YEARS.map(y => `<th data-y="${y}" class="${y === year ? "on" : ""}">${y}</th>`).join("") + "</tr>";
  let total = 0;
  TR.forEach(id => {
    h += `<tr data-t="${id}" class="${id === selT ? "sel" : ""}"><th class="rowh">${esc(CORTO[id])}</th>`;
    YEARS.forEach(y => {
      const it = item(y, id), ch = changed(y, id); if (ch) total++;
      const c = it && it.decide;
      const art = it && it.articulo ? it.articulo.replace(/Art[íi]culo\s*/i, "art. ").split(/[,;(]/)[0] : "";
      const cls = [c ? "" : "none", y === year ? "colon" : "", (y === year && id === selT) ? "cellsel" : "", it && c && !it.verificada ? "unver" : ""].join(" ");
      const bg = c ? (it.decide_alt ? `linear-gradient(135deg, ${color(c)} 55%, ${color(it.decide_alt)} 55%)` : color(c)) : "";
      h += `<td class="${cls}" data-y="${y}" data-t="${id}" style="background:${bg}" title="${esc((c || "No indicado") + (it && it.decide_alt ? " o " + it.decide_alt : "") + " | " + (it ? it.articulo || "" : ""))}">${c ? esc(art) : "s/i"}${ch ? '<span class="chgdot"></span>' : ""}</td>`;
    });
    h += "</tr>";
  });
  m.innerHTML = h;
  m.querySelectorAll("td").forEach(td => td.onclick = () => { stopPlay(); selT = td.dataset.t; selC = null; setYear(+td.dataset.y); });
  m.querySelectorAll("th[data-y]").forEach(th => th.onclick = () => { stopPlay(); setYear(+th.dataset.y); });
  $id("timeTag").textContent = total + " cambios de responsable";
  $id("legend").innerHTML = CARGOS_USADOS.map(c => `<span><i style="background:${color(c)}"></i>${esc(c)}</span>`).join("") + '<span><i style="background:repeating-linear-gradient(45deg,var(--surface2),var(--surface2) 3px,var(--line) 3px,var(--line) 5px)"></i>No indicado (s/i)</span><span>? cita sin verificar</span>';
}

/* ---------- hallazgos ---------- */
let filtro = "Todos";
function renderFinds() {
  const tipos = ["Todos", ...new Set(DATA.hallazgos.map(h => h.tipo))];
  $id("filters").innerHTML = tipos.map(t => `<button class="${t === filtro ? "on" : ""}" data-f="${esc(t)}">${esc(t)}</button>`).join("");
  root.querySelectorAll("#filters button").forEach(b => b.onclick = () => { filtro = b.dataset.f; renderFinds(); });
  const cls = { "Contradicción": "acc", "Vacío": "warn", "Referencia rota": "bad", "Vigencia": "pri" };
  $id("finds").innerHTML = DATA.hallazgos.filter(h => filtro === "Todos" || h.tipo === filtro).map(h =>
    `<div class="find" id="f-${h.id}"><div><span class="tag ${cls[h.tipo] || ""}">${esc(h.tipo)}</span></div><h4>${esc(h.titulo)}</h4><p>${esc(h.detalle)}</p><div class="ev">${esc(h.evidencia)}</div>${h.url ? `<div><a class="btn" target="_blank" rel="noopener" href="${h.url}">${ICON_EXT}Ver evidencia</a></div>` : ""}</div>`).join("");
}

function renderTrack() {
  $id("yearBig").textContent = year;
  $id("yGraph").textContent = year;
  const i = YEARS.indexOf(year);
  track.querySelectorAll("button").forEach((b, k) => { b.classList.toggle("on", +b.dataset.y === year); b.classList.toggle("past", k < i); });
  const btns = track.querySelectorAll("button"), a = btns[0].getBoundingClientRect(), b = btns[i].getBoundingClientRect(), t = track.getBoundingClientRect();
  $id("trackFill").style.width = Math.max(0, b.left + b.width / 2 - (a.left + a.width / 2)) + "px";
}
function renderAll() { renderTrack(); renderGraph(); renderDetail(); renderMatrix(); }


/* ---------- biblioteca ---------- */
let libTipo = "Todos", libEst = null;
const EST_CLS = { "Vigente":"ok", "Revisar":"warn", "Superado":"bad", "Duplicado":"", "No normativo":"", "Falta":"acc" };
function renderLib() {
  const q = ($id("libQ").value || "").toLowerCase();
  const docs = DATA.documentos;
  const tipos = ["Todos", ...new Set(docs.map(d => d.tipo))];
  $id("libF").innerHTML = tipos.map(t => `<button class="${t === libTipo ? "on" : ""}" data-f="${esc(t)}">${esc(t)}</button>`).join("");
  root.querySelectorAll("#libF button").forEach(b => b.onclick = () => { libTipo = b.dataset.f; renderLib(); });
  const cuenta = {}; docs.forEach(d => cuenta[d.estado] = (cuenta[d.estado] || 0) + 1);
  $id("libSum").innerHTML = Object.entries(cuenta).map(([e, n]) => `<button class="tag ${EST_CLS[e] || ""}" style="border:0;${libEst === e ? "outline:2px solid currentColor" : ""}" data-e="${esc(e)}">${n} ${esc(e.toLowerCase())}</button>`).join("");
  root.querySelectorAll("#libSum button").forEach(b => b.onclick = () => { libEst = libEst === b.dataset.e ? null : b.dataset.e; renderLib(); });
  $id("libTag").textContent = docs.filter(d => d.estado !== "Falta").length + " archivos";
  const lst = docs.filter(d => (libTipo === "Todos" || d.tipo === libTipo) && (!libEst || d.estado === libEst) && (!q || (d.documento + " " + d.cohortes + " " + d.responsable + " " + d.vigencia).toLowerCase().includes(q)));
  $id("lib").innerHTML = lst.map(d => `<div class="doc ${d.estado === "Falta" ? "falta" : ""}"><div class="ti">${esc(d.sigla)}</div><div style="min-width:0"><h5 title="${esc(d.documento)}">${esc(d.documento)}</h5><small title="${esc(d.vigencia + " | " + d.responsable)}">${esc(d.cohortes)} | ${esc(d.vigencia)}</small></div><span class="tag ${EST_CLS[d.estado] || ""}">${esc(d.estado)}</span>${d.enlace ? `<a class="btn" target="_blank" rel="noopener" href="${esc(d.enlace)}">${ICON_EXT}Abrir</a>` : "<span></span>"}</div>`).join("") || '<p style="color:var(--ink2)">Sin resultados.</p>';
}
$id("libQ").oninput = renderLib;

/* ---------- chat (maqueta) ---------- */
const msgs = $id("msgs");
function addUser(t) { const d = document.createElement("div"); d.className = "msg u"; d.textContent = t; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight; }
function flash(el) { if (!el) return; el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); el.scrollIntoView({ behavior: "smooth", block: "center" }); }
const ESTADO = { respondida: ["ok", "Respondida"], falta_año: ["pri", "Depende del año de ingreso"], contradiccion: ["acc", "Te corrijo"], no_esta: ["bad", "No está en los documentos"] };
function answer(r) {
  const d = document.createElement("div"); d.className = "msg a"; d.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>'; msgs.appendChild(d); msgs.scrollTop = msgs.scrollHeight;
  setTimeout(() => {
    const [k, l] = ESTADO[r.estado] || ["", r.estado];
    d.innerHTML = `<div><span class="tag ${k}">${l}</span></div><div class="txt"></div>`;
    const txt = d.querySelector(".txt"); const full = r.texto; let n = 0;
    const tick = setInterval(() => {
      n += 4; txt.innerHTML = full.slice(0, n).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*\*[^*]*$/, ""); msgs.scrollTop = msgs.scrollHeight;
      if (n >= full.length) {
        clearInterval(tick);
        txt.innerHTML = full.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
        (r.citas || []).forEach(c => { const it = c.cita ? c : item(c.año, c.id); if (!it || !it.cita) return; d.insertAdjacentHTML("beforeend", `<div class="cite"><div>${it.verificada ? '<span class="tag ok">Cita verificada en el PDF</span>' : '<span class="tag bad">Cita no encontrada</span>'}</div><div>"${esc(it.cita)}"</div><div class="meta">${esc(it.reglamento || "")}${String(it.reglamento || "").includes(String(c.año)) ? "" : " " + c.año} | ${esc(it.articulo || "")} | p. ${it.pagina_real || it.pagina} <a target="_blank" rel="noopener" href="${pdf(c.año, it.pagina_real || it.pagina)}">abrir PDF</a></div></div>`); });
        if (r.derivar) d.insertAdjacentHTML("beforeend", `<div class="meta"><b>Derivar a:</b> ${esc(r.derivar)}</div>`);
        if (r.foco) d.insertAdjacentHTML("beforeend", `<div><button class="btn">Mostrar en el tablero</button></div>`), d.querySelector("button.btn").onclick = () => mover(r.foco);
        msgs.scrollTop = msgs.scrollHeight;
        if (r.estado === "no_esta") { const k = $id("kFail"); k.textContent = +k.textContent + 1; const kp = $id("kpiFail"); kp.classList.remove("bump"); void kp.offsetWidth; kp.classList.add("bump"); }
        if (r.foco) setTimeout(() => mover(r.foco), 400);
      }
    }, 14);
  }, r.live ? 150 : 900);
}
function mover(f) {
  stopPlay();
  if (f.tramite) { selT = f.tramite; selC = null; }
  if (f.cargo) selC = f.cargo;
  if (f.año) setYear(f.año); else renderAll();
  if (f.vista === "tiempo") { flash($id("cardTime")); const tr = root.querySelector(`#matrix tr[data-t="${f.tramite}"]`); if (tr) { tr.classList.add("pulse"); } if (f.play) setTimeout(startPlay, 900); }
  else if (f.hallazgo) { flash($id("cardGraph")); setTimeout(() => { filtro = "Todos"; renderFinds(); const el = $id("f-" + f.hallazgo); el.classList.add("hi"); flash(el); setTimeout(() => el.classList.remove("hi"), 4000); }, 1800); }
  else flash($id("cardGraph"));
}
let pendiente = null, ultimoId = null;
function ask(q) {
  addUser(q);
  pendiente = document.createElement("div"); pendiente.className = "msg a";
  pendiente.innerHTML = '<span class="typing"><i></i><i></i><i></i></span><span class="meta">Leyendo el reglamento de la promoción ' + year + '…</span>';
  msgs.appendChild(pendiente); msgs.scrollTop = msgs.scrollHeight;
  send("pregunta", { id: Date.now() + "-" + Math.random().toString(36).slice(2, 7), q, año: year });
}
function recibir(d) {
  if (d.stats) { const k = $id("kFail"); if (+k.textContent !== d.stats.sin_respuesta) k.textContent = d.stats.sin_respuesta; }
  const r = d.respuesta; if (!r || r.id === ultimoId) return; ultimoId = r.id;
  if (pendiente) { pendiente.remove(); pendiente = null; }
  answer(r);
}
$id("chips").innerHTML = DATA.chat.map(c => `<button>${esc(c.pregunta)}</button>`).join("");
root.querySelectorAll("#chips button").forEach(b => b.onclick = () => ask(b.textContent));
$id("composer").onsubmit = e => { e.preventDefault(); const i = $id("inp"); if (i.value.trim()) { ask(i.value.trim()); i.value = ""; } };
msgs.innerHTML = `<div class="msg a"><div class="txt">Hola. Respondo con los reglamentos oficiales de pregrado y te muestro en el tablero de dónde sale cada respuesta. ¿Qué necesitas saber?</div></div>`;

/* ---------- inicio ---------- */
let t0 = "light"; try { t0 = localStorage.getItem("tema") || "light"; } catch (e) {}
APP.dataset.theme = t0;
root.querySelectorAll(".toggle button").forEach(b => b.classList.toggle("on", b.dataset.t === t0));
renderFinds(); renderLib(); renderAll();
window.addEventListener("resize", renderTrack);

  ultimoId = primera && primera.respuesta ? primera.respuesta.id : null;
  recibir({ stats: primera && primera.stats });
  return { recibir };
}

export default function (component) {
  const { data, setTriggerValue, parentElement } = component;
  parentElement.__send = setTriggerValue;
  if (!document.getElementById('fuente-inter')) {
    const l = document.createElement('link'); l.id = 'fuente-inter'; l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap';
    document.head.appendChild(l);
  }
  if (!parentElement.__api) {
    parentElement.__api = init(parentElement, data.base, (k, v) => parentElement.__send(k, v), data);
  } else {
    parentElement.__api.recibir(data);
  }
}
