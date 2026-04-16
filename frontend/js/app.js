/* app.js — Lógica principal de Moodify */

const API     = 'http://localhost:8001';
const MINIMO_STATS = 10;

// ── Estado global ─────────────────────────────────────────────
let token      = localStorage.getItem('moodify_token')    || '';
let username   = localStorage.getItem('moodify_username') || 'usuario';
let textos_es  = {};
let idioma     = 'es';
let loadTimer  = null;
let loadRunning = false;
let loadProg   = 0;

// ── Guard: redirige si no hay sesión ──────────────────────────
if (!token) { window.location.href = '/'; }

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('nav-username').textContent = `@${username}`;
  checkStatsTab();
});

function checkStatsTab() {
  apiGet('/api/estadisticas').then(data => {
    const total   = data.total || 0;
    const tabBtn  = document.querySelector('[data-tab="estadisticas"]');
    if (total >= MINIMO_STATS && tabBtn) {
      tabBtn.classList.remove('locked');
      tabBtn.setAttribute('onclick', "switchPanel('estadisticas')");
    }
  }).catch(() => {});
}

// ── Fetch helpers ─────────────────────────────────────────────
async function apiPost(endpoint, body) {
  const res = await fetch(`${API}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  if (res.status === 401) { doLogout(); return; }
  return res.json();
}

async function apiGet(endpoint) {
  const res = await fetch(`${API}${endpoint}`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (res.status === 401) { doLogout(); return {}; }
  return res.json();
}

// ── Logout ────────────────────────────────────────────────────
function doLogout() {
  localStorage.removeItem('moodify_token');
  localStorage.removeItem('moodify_username');
  window.location.href = '/';
}

// ── Panel navigation ──────────────────────────────────────────
function switchPanel(tab) {
  document.querySelectorAll('.app-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab:not(.locked)').forEach(b => b.classList.remove('active'));

  const panel   = document.getElementById(`panel-${tab}`);
  const navTab  = document.querySelector(`[data-tab="${tab}"]`);
  if (panel)  panel.classList.add('active');
  if (navTab) navTab.classList.add('active');

  // Carga datos al entrar al panel
  if (tab === 'historial')    loadHistorial();
  if (tab === 'favoritos')    loadFavoritos();
  if (tab === 'estadisticas') loadEstadisticas();
}

// ── Overlay de carga ──────────────────────────────────────────
const PHASES = [
  [0,10,'ANALIZANDO'],[10,18,'DETECTANDO IDIOMA'],[18,22,'VISTA PREVIA'],
  [22,45,'TONO DIPLOMÁTICO'],[45,68,'TONO EJECUTIVO'],[68,88,'TONO CASUAL'],[88,98,'FINALIZANDO']
];
function getPhase(p) {
  for (const [a, b, l] of PHASES) if (p >= a && p < b) return l;
  return 'LISTO ✓';
}
function setProgress(p) {
  loadProg = p;
  const pd = document.getElementById('ov-prog');
  const dd = document.getElementById('ov-dot');
  const ph = document.getElementById('ov-phase');
  const pc = document.getElementById('ov-pct');
  if (pd) pd.style.width  = p + '%';
  if (dd) dd.style.left   = p + '%';
  if (ph) ph.textContent  = getPhase(p);
  if (pc) pc.textContent  = Math.round(p) + '%';
}
function startLoading() {
  if (loadRunning) return;
  loadRunning = true; loadProg = 0;
  document.getElementById('moodify-overlay').classList.add('active');
  setProgress(0); clearInterval(loadTimer);
  loadTimer = setInterval(() => {
    if (loadProg < 88) {
      const step = loadProg < 22 ? 2.5 : loadProg < 68 ? 1.0 : 0.4;
      setProgress(Math.min(88, loadProg + step));
    }
  }, 100);
}
function stopLoading() {
  if (!loadRunning) return;
  clearInterval(loadTimer); setProgress(100);
  setTimeout(() => {
    document.getElementById('moodify-overlay').classList.remove('active');
    loadRunning = false; setProgress(0);
  }, 700);
}

// ── Detector de idioma (en vivo) ──────────────────────────────
const ES_RE = /\b(que|de|en|es|una?|por|con|para|como|pero|todo|más|también|cuando|donde|esto|eso|aquí|ahí|hay|muy|bien|ahora|ya|si|no|los|las|del|al|le|les|se|me|te|nos|su|sus|mi|mis|tu|tus|tengo|necesito|solicito|pido|informo|comunico|hola|buenas|gracias|favor|día|días|semana|junta|reunión|equipo|trabajo|empresa|área|proyecto|reporte|porque|aunque|además|entonces|así|siguiente|próximo|wey|güey|bro|papu|cuate|mano|compa|carnal)\b/gi;
const EN_RE = /\b(the|and|for|are|but|not|you|all|can|her|was|one|our|out|day|get|has|him|his|how|its|may|new|now|old|see|two|who|will|with|from|they|this|that|have|been|said|each|she|which|their|there|were|your|what|when|would|about|could|please|thanks|hello|meeting|team|update|feedback|deadline|regarding|attached|kindly|schedule|review|report|project)\b/gi;
const ES_FUERTE = /[áéíóúüñÁÉÍÓÚÜÑ]|¿|¡|\b(estimad[ao]s?|saludos|atentamente)\b/gi;

function detectarIdioma(msg) {
  if (!msg || !msg.trim()) return { idioma:'desconocido', emoji:'🌐', confianza:0 };
  const tw  = Math.max(msg.split(/\s+/).length, 1);
  const es  = (msg.match(ES_RE) || []).length + (msg.match(ES_FUERTE) || []).length * 2;
  const en  = (msg.match(EN_RE) || []).length;
  const ses = es / tw, sen = en / tw;
  if (ses === 0 && sen === 0) return { idioma:'desconocido', emoji:'🌐', confianza:0 };
  if (ses >= sen * 1.5) return { idioma:'Español', emoji:'🇲🇽', confianza: Math.min(100, Math.round(ses/(ses+sen)*100)) };
  if (sen >= ses * 1.5) return { idioma:'Inglés',  emoji:'🇺🇸', confianza: Math.min(100, Math.round(sen/(ses+sen)*100)) };
  return { idioma:'Mixto (Spanglish)', emoji:'🌐', confianza:50 };
}

function onInputChange() {
  const msg  = document.getElementById('msg-input').value;
  const det  = detectarIdioma(msg);
  const box  = document.getElementById('detector-box');
  if (!box) return;
  if (det.idioma === 'desconocido') {
    box.innerHTML = '<div class="det-neutral">🌐 Idioma — Escribe para detectar</div>';
    return;
  }
  const color = det.idioma === 'Español' ? '#B8F000' : det.idioma === 'Inglés' ? '#3D7ECC' : '#E8800A';
  const prevLbl = det.idioma === 'Español' ? '🇺🇸 Vista previa en inglés' : '🇲🇽 Vista previa en español';
  box.innerHTML = `
    <div class="det-row">
      <span class="det-label">🌐 Idioma</span>
      <span class="det-idioma">${det.emoji} ${det.idioma}</span>
    </div>
    <div class="det-barra-bg"><div class="det-barra-fill" style="width:${det.confianza}%;background:${color};"></div></div>
    <div class="det-conf">Confianza: ${det.confianza}%</div>
    <div class="det-prev-label">${prevLbl}</div>
    <div class="det-placeholder det-conf">Aparecerá al transformar ✦</div>
  `;
}

// ── Transformar ───────────────────────────────────────────────
async function doTransform() {
  const msg = document.getElementById('msg-input').value.trim();
  if (!msg) return;
  startLoading();
  setOutputPlaceholders();
  try {
    const data = await apiPost('/api/transform', { mensaje: msg });
    if (!data) return;
    textos_es = data.textos_es || {};
    renderOutputs(data);
    renderDetector(data);
    renderTips(data.tips || []);
    // resetea selector de idioma
    selectLang('es');
    checkStatsTab();
  } catch (e) {
    console.error('Transform error:', e);
  } finally {
    stopLoading();
  }
}

function setOutputPlaceholders() {
  ['dipl','ejec','casu'].forEach(t => {
    const el = document.getElementById(`out-${t}`);
    if (el) el.innerHTML = '<span class="output-placeholder">Generando...</span>';
  });
}

function renderOutputs(data) {
  const map = { dipl: data.diplomatico, ejec: data.ejecutivo, casu: data.casual };
  for (const [key, text] of Object.entries(map)) {
    const el = document.getElementById(`out-${key}`);
    if (!el) continue;
    el.innerHTML = `<span>${escHtml(text)}</span><button class="copy-btn" onclick="copyText('out-${key}')">Copiar</button>`;
  }
}

function renderDetector(data) {
  const det = data.detector || {};
  const box = document.getElementById('detector-box');
  if (!box) return;
  if (!det.idioma || det.idioma === 'desconocido') {
    box.innerHTML = '<div class="det-neutral">🌐 Idioma — desconocido</div>';
    return;
  }
  const color = det.idioma === 'Español' ? '#B8F000' : det.idioma === 'Inglés' ? '#3D7ECC' : '#E8800A';
  const prevLbl = det.idioma === 'Español' ? '🇺🇸 Vista previa en inglés' : '🇲🇽 Vista previa en español';
  const prevHtml = data.preview
    ? `<div class="det-prev-box">${escHtml(data.preview)}</div>`
    : `<div class="det-placeholder det-conf">No disponible</div>`;
  box.innerHTML = `
    <div class="det-row">
      <span class="det-label">🌐 Idioma</span>
      <span class="det-idioma">${det.emoji} ${det.idioma}</span>
    </div>
    <div class="det-barra-bg"><div class="det-barra-fill" style="width:${det.confianza}%;background:${color};"></div></div>
    <div class="det-conf">Confianza: ${det.confianza}%</div>
    <div class="det-prev-label">${prevLbl}</div>
    ${prevHtml}
  `;
}

function renderTips(tips) {
  const wrap  = document.getElementById('clippy-wrap');
  const items = document.getElementById('clippy-items');
  if (!wrap || !items) return;
  if (!tips.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = 'block';
  items.innerHTML = tips.map(t => `
    <div class="clip-item">
      <span class="clip-icon">${t.icono}</span>
      <div>
        <div class="clip-title">${escHtml(t.titulo)}</div>
        <div class="clip-text">${escHtml(t.texto)}</div>
      </div>
    </div>
  `).join('');
}

// ── Seleccionar idioma de salida ──────────────────────────────
function selectLang(lang) {
  idioma = lang;
  const btnEs = document.getElementById('btn-es');
  const btnEn = document.getElementById('btn-en');
  if (btnEs) { btnEs.textContent = lang === 'es' ? '✓ ES 🇲🇽' : 'ES 🇲🇽'; btnEs.className = `lang-btn${lang==='es'?' on':''}`; }
  if (btnEn) { btnEn.textContent = lang === 'en' ? '✓ EN 🇺🇸' : 'EN 🇺🇸'; btnEn.className = `lang-btn${lang==='en'?' on':''}`; }
}

// ── Traducir ──────────────────────────────────────────────────
async function doTranslate() {
  if (!Object.keys(textos_es).length) return;
  startLoading();
  try {
    const data = await apiPost('/api/translate', { textos_es, idioma });
    if (!data) return;
    const map = { dipl: data.diplomatico, ejec: data.ejecutivo, casu: data.casual };
    for (const [key, text] of Object.entries(map)) {
      const el = document.getElementById(`out-${key}`);
      if (el) el.innerHTML = `<span>${escHtml(text)}</span><button class="copy-btn" onclick="copyText('out-${key}')">Copiar</button>`;
    }
  } catch (e) {
    console.error('Translate error:', e);
  } finally {
    stopLoading();
  }
}

// ── Copiar al portapapeles ────────────────────────────────────
function copyText(elId) {
  const el   = document.getElementById(elId);
  if (!el) return;
  const span = el.querySelector('span');
  const text = span ? span.textContent : '';
  navigator.clipboard.writeText(text).then(() => {
    const btn = el.querySelector('.copy-btn');
    if (btn) { const orig = btn.textContent; btn.textContent = '✓ Copiado'; setTimeout(() => btn.textContent = orig, 1500); }
  });
}

// ── Utilidades ────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}