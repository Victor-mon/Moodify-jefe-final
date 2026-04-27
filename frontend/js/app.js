/* app.js — Lógica principal de Moodify */

const API = "http://localhost:8000";
const MINIMO_STATS = 3;

/* ── SISTEMA DE INTERNACIONALIZACIÓN ─────────────────────────── */
const I18N = {
  es: {
    nav_transform:    'Transformar',
    nav_historial:    'Historial',
    nav_favoritos:    '★ Favoritos',
    nav_estadisticas: 'Estadísticas',
    nav_config:       'Configuración',
    btn_transform:    'Transformar',
    btn_translate:    'Traducir ✦',
    lang_output:      '🌐 Salida en',
    outputs_label:    '— VERSIONES ADAPTADAS',
    badge_dipl:       'Diplomático',
    badge_ejec:       'Ejecutivo',
    badge_casu:       'Casual',
    placeholder_dipl: 'La versión diplomática aparecerá aquí...',
    placeholder_ejec: 'La versión ejecutiva aparecerá aquí...',
    placeholder_casu: 'La versión casual aparecerá aquí...',
    textarea_ph:      'Escribe aquí tu mensaje — con groserías, slang, emojis o como salga...',
    sub_title:        'REESCRITURA INTELIGENTE CON IA',
    copy_btn:         'Copiar',
    copied_btn:       '✓ Copiado',
    generating:       'Generando...',
    detecting:        '🌐 Idioma — Escribe para detectar',
    clippy_header:    'MOODIFY DICE',
    sec_historial:    '— HISTORIAL DE MENSAJES',
    sec_favoritos:    '— FAVORITOS',
    sec_estadisticas: '— TUS ESTADÍSTICAS',
    loading:          'Cargando...',
    error_historial:  'Error al cargar el historial.',
    error_favoritos:  'Error al cargar favoritos.',
    empty_historial:  'Aún no has transformado ningún mensaje.',
    empty_favoritos:  'Aún no tienes favoritos guardados.',
    cfg_title:        'Configuración',
    cfg_appearance:   'Apariencia',
    cfg_theme_lbl:    'Tema',
    cfg_theme_dark:   'Modo oscuro',
    cfg_theme_light:  'Modo claro',
    cfg_lang_lbl:     'Idioma del agente',
    cfg_lang_sub:     'ES optimizado para México',
    cfg_account:      'Cuenta',
    cfg_username_lbl: 'Usuario',
    cfg_email_lbl:    'Correo',
    cfg_pass_lbl:     'Contraseña',
    cfg_pass_dots:    '••••••••',
    cfg_change:       'Cambiar',
    cfg_session:      'Sesión',
    cfg_logout:       '↩ Cerrar sesión',
    cfg_delete:       '✕ Eliminar cuenta',
    preview_en:       '🇺🇸 Vista previa en inglés',
    preview_es:       '🇲🇽 Vista previa en español',
    dipl_label:       'Diplomático',
    ejec_label:       'Ejecutivo',
    casu_label:       'Casual',
  },
  en: {
    nav_transform:    'Transform',
    nav_historial:    'History',
    nav_favoritos:    'Favorites',
    nav_estadisticas: 'Statistics',
    nav_config:       'Settings',
    btn_transform:    'Transform',
    btn_translate:    'Translate ✦',
    lang_output:      '🌐 Output in',
    outputs_label:    '— ADAPTED VERSIONS',
    badge_dipl:       'Diplomatic',
    badge_ejec:       'Executive',
    badge_casu:       'Casual',
    placeholder_dipl: 'The diplomatic version will appear here...',
    placeholder_ejec: 'The executive version will appear here...',
    placeholder_casu: 'The casual version will appear here...',
    textarea_ph:      'Write your message here — as it comes out...',
    sub_title:        'INTELLIGENT AI REWRITING',
    copy_btn:         'Copy',
    copied_btn:       '✓ Copied',
    generating:       'Generating...',
    detecting:        '🌐 Language — Start typing to detect',
    clippy_header:    'MOODIFY SAYS',
    sec_historial:    '— MESSAGE HISTORY',
    sec_favoritos:    '— FAVORITES',
    sec_estadisticas: '— YOUR STATISTICS',
    loading:          'Loading...',
    error_historial:  'Error loading history.',
    error_favoritos:  'Error loading favorites.',
    empty_historial:  'You have not transformed any messages yet.',
    empty_favoritos:  'You have no saved favorites yet.',
    cfg_title:        'Settings',
    cfg_appearance:   'Appearance',
    cfg_theme_lbl:    'Theme',
    cfg_theme_dark:   'Dark mode',
    cfg_theme_light:  'Light mode',
    cfg_lang_lbl:     'Agent language',
    cfg_lang_sub:     'ES optimized for Mexico',
    cfg_account:      'Account',
    cfg_username_lbl: 'Username',
    cfg_email_lbl:    'Email',
    cfg_pass_lbl:     'Password',
    cfg_pass_dots:    '••••••••',
    cfg_change:       'Change',
    cfg_session:      'Session',
    cfg_logout:       '↩ Sign out',
    cfg_delete:       '✕ Delete account',
    preview_en:       '🇺🇸 English preview',
    preview_es:       '🇲🇽 Spanish preview',
    dipl_label:       'Diplomatic',
    ejec_label:       'Executive',
    casu_label:       'Casual',
  }
};

let currentLang = sessionStorage.getItem('moodify_agent_lang') || 'es';

function t(key) {
  return (I18N[currentLang] || I18N['es'])[key] || key;
}

function applyI18n() {
  // ── Navegación ──────────────────────────────────────────────
  document.querySelectorAll('.nav-tab[data-tab]').forEach(btn => {
    const keyMap = {
      'transformar':  'nav_transform',
      'historial':    'nav_historial',
      'favoritos':    'nav_favoritos',
      'estadisticas': 'nav_estadisticas',
    };
    const key = keyMap[btn.dataset.tab];
    if (key) btn.textContent = t(key);
  });

  const cfgBtn = document.querySelector('.btn-nav-config');
  if (cfgBtn) cfgBtn.textContent = t('nav_config');

  // ── Panel transformar ───────────────────────────────────────
  const btnTr = document.querySelector('.btn-transform');
  if (btnTr) btnTr.textContent = t('btn_transform');

  const btnTl = document.querySelector('.btn-translate');
  if (btnTl) btnTl.textContent = t('btn_translate');

  const langLbl = document.querySelector('.lang-label');
  if (langLbl) langLbl.textContent = t('lang_output');

  const outLbl = document.querySelector('.outputs-label');
  if (outLbl) outLbl.textContent = t('outputs_label');

  document.querySelectorAll('.output-card').forEach(card => {
    const badge = card.querySelector('.tone-badge');
    if (!badge) return;
    if (card.classList.contains('card-dipl')) badge.textContent = t('badge_dipl');
    else if (card.classList.contains('card-ejec')) badge.textContent = t('badge_ejec');
    else if (card.classList.contains('card-casu')) badge.textContent = t('badge_casu');
  });

  ['dipl','ejec','casu'].forEach(k => {
    const el = document.getElementById('out-' + k);
    if (!el) return;
    const ph = el.querySelector('.output-placeholder');
    if (ph) ph.textContent = t('placeholder_' + k);
  });

  const ta = document.getElementById('msg-input');
  if (ta) ta.placeholder = t('textarea_ph');

  const sub = document.querySelector('.moodify-sub');
  if (sub) sub.innerHTML = `<span class="moodify-sub-accent">▸</span> ${t('sub_title')}`;

  const detBox = document.getElementById('detector-box');
  if (detBox) {
    const neutral = detBox.querySelector('.det-neutral');
    if (neutral) neutral.textContent = t('detecting');
  }

  const clippyH = document.querySelector('.clippy-header');
  if (clippyH) {
    clippyH.innerHTML = `<span class="clip-dot"></span> ${t('clippy_header')}`;
  }

  // ── Secciones historial/favoritos/stats ─────────────────────
  const secH = document.querySelector('#panel-historial .section-title');
  if (secH) secH.textContent = t('sec_historial');
  const secF = document.querySelector('#panel-favoritos .section-title');
  if (secF) secF.textContent = t('sec_favoritos');
  const secE = document.querySelector('#panel-estadisticas .section-title');
  if (secE) secE.textContent = t('sec_estadisticas');

  // ── Modal configuración (nuevo diseño compacto) ─────────────
  // Título del modal
  const cfgTitle = document.querySelector('.cfg-title');
  if (cfgTitle) cfgTitle.textContent = t('cfg_title');

  // Títulos de las dos columnas (.cfg-col → .cfg-section-title)
  const cfgColTitles = document.querySelectorAll('.cfg-col .cfg-section-title');
  if (cfgColTitles[0]) cfgColTitles[0].textContent = t('cfg_appearance');
  if (cfgColTitles[1]) cfgColTitles[1].textContent = t('cfg_account');

  // Labels de cada fila (.cfg-pill-label)
  const pillLabels = document.querySelectorAll('.cfg-pill-label');
  const pillKeys = ['cfg_theme_lbl', 'cfg_lang_lbl', 'cfg_username_lbl', 'cfg_email_lbl', 'cfg_pass_lbl'];
  pillLabels.forEach((el, i) => { if (pillKeys[i]) el.textContent = t(pillKeys[i]); });

  // Subtexto del tema (cambia según el estado actual)
  const cfgThemeSub = document.getElementById('cfg-theme-sub');
  if (cfgThemeSub) {
    const isLight = document.body.classList.contains('theme-light');
    cfgThemeSub.textContent = isLight ? t('cfg_theme_light') : t('cfg_theme_dark');
  }

  // Subtexto del idioma
  const cfgLangSub = document.getElementById('cfg-lang-sub');
  if (cfgLangSub) cfgLangSub.textContent = t('cfg_lang_sub');

  // Botones "Cambiar" de cuenta
  document.querySelectorAll('.cfg-btn-inline').forEach(el => {
    el.textContent = t('cfg_change');
  });

  // Botones del footer
  const cfgLogout = document.querySelector('.cfg-btn-logout');
  if (cfgLogout) cfgLogout.textContent = t('cfg_logout');
  const cfgDelete = document.querySelector('.cfg-btn-danger');
  if (cfgDelete) cfgDelete.textContent = t('cfg_delete');

  // Historial i18n si existe
  if (typeof renderHistorialI18n === 'function') renderHistorialI18n();
}

function setLang(lang) {
  currentLang = lang;
  sessionStorage.setItem('moodify_agent_lang', lang);
  applyI18n();

  const activePanel = document.querySelector('.app-panel.active');
  if (activePanel) {
    const tab = activePanel.id.replace('panel-', '');
    if (tab === 'historial') loadHistorial();
    if (tab === 'favoritos') loadFavoritos();
    if (tab === 'estadisticas') loadEstadisticas();
  }
}

/* ── Estado global ─────────────────────────────────────────── */
let token       = sessionStorage.getItem('moodify_token')    || '';
let username    = sessionStorage.getItem('moodify_username') || '';
let textos_es   = {};
let idioma      = 'es';
let loadRunning = false;

/* ── Guard: redirige si no hay sesión ──────────────────────── */
if (!token) { window.location.href = '/'; }

/* ── Init ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const savedLang = sessionStorage.getItem('moodify_agent_lang');
  if (savedLang && (savedLang === 'es' || savedLang === 'en')) {
    currentLang = savedLang;
  }
  // Nota: cfg-lang-select eliminado — el idioma se controla con cfg-btn-es / cfg-btn-en

  applyI18n();

  if (username) {
    const navU = document.getElementById('nav-username');
    if (navU) navU.textContent = `@${username}`;
  } else {
    apiGet('/api/perfil').then(data => {
      if (data && data.username) {
        username = data.username;
        sessionStorage.setItem('moodify_username', username);
        const navU = document.getElementById('nav-username');
        if (navU) navU.textContent = `@${username}`;
      }
    }).catch(() => {});
  }

  checkStatsTab();

  const initialTab = document.querySelector('.nav-tab.active');
  if (initialTab) updateNavIndicator(initialTab);
});

function checkStatsTab() {
  apiGet('/api/estadisticas').then(data => {
    const total  = data && data.total ? data.total : 0;
    const tabBtn = document.querySelector('[data-tab="estadisticas"]');
    if (tabBtn) {
      if (total >= MINIMO_STATS) {
        tabBtn.classList.remove('locked');
        tabBtn.onclick = () => switchPanel('estadisticas');
      } else {
        tabBtn.classList.add('locked');
        tabBtn.onclick = null;
      }
    }
  }).catch(() => {});
}

/* ── Fetch helpers ──────────────────────────────────────────── */
async function apiPost(endpoint, body) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(body),
    });
    if (res.status === 401) { doLogout(); return null; }
    return res.json();
  } catch (e) {
    console.error('apiPost error:', e);
    return null;
  }
}

async function apiGet(endpoint) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.status === 401) { doLogout(); return {}; }
    return res.json();
  } catch (e) {
    console.error('apiGet error:', e);
    return {};
  }
}

async function apiDelete(endpoint) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.status === 401) { doLogout(); return null; }
    return res.json();
  } catch (e) {
    console.error('apiDelete error:', e);
    return null;
  }
}

async function apiPut(endpoint, body) {
  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(body),
    });
    if (res.status === 401) { doLogout(); return null; }
    return { ok: res.ok, data: await res.json() };
  } catch (e) {
    console.error('apiPut error:', e);
    return null;
  }
}

/* ── Logout ─────────────────────────────────────────────────── */
function doLogout() {
  sessionStorage.removeItem('moodify_token');
  sessionStorage.removeItem('moodify_username');
  window.location.href = '/';
}

/* ── Panel navigation ───────────────────────────────────────── */
// REEMPLAZAR la función switchPanel en app.js:
function switchPanel(tab) {
  const current = document.querySelector('.app-panel.active');
  const next    = document.getElementById(`panel-${tab}`);
  const navTab  = document.querySelector(`[data-tab="${tab}"]`);

  if (current && current !== next) {
    current.style.transition = 'opacity 0.18s ease, transform 0.18s ease';
    current.style.opacity    = '0';
    current.style.transform  = 'translateY(6px)';
    setTimeout(() => {
      current.classList.remove('active');
      current.style.opacity   = '';
      current.style.transform = '';
      current.style.transition = '';
      if (next) {
        next.classList.add('active');
        next.style.opacity   = '0';
        next.style.transform = 'translateY(-6px)';
        void next.offsetWidth;
        next.style.transition = 'opacity 0.22s ease, transform 0.22s ease';
        next.style.opacity   = '1';
        next.style.transform = 'translateY(0)';
        setTimeout(() => {
          next.style.transition = '';
          next.style.opacity    = '';
          next.style.transform  = '';
        }, 240);
      }
    }, 160);
  } else if (next) {
    next.classList.add('active');
  }

  document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
  if (navTab && !navTab.classList.contains('locked')) navTab.classList.add('active');

  updateNavIndicator(navTab);

  if (tab === 'historial')    loadHistorial();
  if (tab === 'favoritos')    loadFavoritos();
  if (tab === 'estadisticas') loadEstadisticas();
}

function updateNavIndicator(activeEl) {
  let indicator = document.getElementById('nav-indicator');
  if (!indicator) {
    indicator = document.createElement('div');
    indicator.id = 'nav-indicator';
    document.getElementById('nav-tabs').appendChild(indicator);
  }
  if (!activeEl || activeEl.classList.contains('locked')) {
    indicator.style.opacity = '0';
    return;
  }
  const rect    = activeEl.getBoundingClientRect();
  const tabsRect = document.getElementById('nav-tabs').getBoundingClientRect();
  indicator.style.cssText = `
    position:absolute; bottom:6px; height:2px; border-radius:2px;
    background:#B8F000; pointer-events:none;
    transition: left 0.28s cubic-bezier(.4,0,.2,1), width 0.28s cubic-bezier(.4,0,.2,1), opacity 0.2s;
    left:${rect.left - tabsRect.left}px;
    width:${rect.width}px;
    opacity:1;
  `;
}

/* ══════════════════════════════════════════════════════════════
   OVERLAY DE CARGA — streaming real desde el backend
══════════════════════════════════════════════════════════════ */

const STAGE_LABELS_ES = {
  analizando: 'Analizando mensaje...',
  idioma:     'Detectando idioma...',
  preview:    'Generando vista previa...',
  dipl:       'Tono diplomático...',
  ejec:       'Tono ejecutivo...',
  casu:       'Tono casual...',
  guardando:  'Guardando historial...',
};
const STAGE_LABELS_EN = {
  analizando: 'Analyzing message...',
  idioma:     'Detecting language...',
  preview:    'Generating preview...',
  dipl:       'Diplomatic tone...',
  ejec:       'Executive tone...',
  casu:       'Casual tone...',
  guardando:  'Saving to history...',
};

function getStageLabel(stage, label) {
  const map = currentLang === 'en' ? STAGE_LABELS_EN : STAGE_LABELS_ES;
  return map[stage] || label || stage;
}

function setProgress(p, stage, label) {
  const pd = document.getElementById('ov-prog');
  const dd = document.getElementById('ov-dot');
  const ph = document.getElementById('ov-phase');
  const pc = document.getElementById('ov-pct');
  if (pd) pd.style.width = p + '%';
  if (dd) dd.style.left  = p + '%';
  if (ph) ph.textContent = label || stage || '';
  if (pc) pc.textContent = Math.round(p) + '%';
}

function startLoading() {
  if (loadRunning) return;
  loadRunning = true;
  const ov = document.getElementById('moodify-overlay');
  if (ov) ov.classList.add('active');
  setProgress(0, 'analizando', currentLang === 'en' ? 'Starting...' : 'Iniciando...');
}

function stopLoading() {
  setProgress(100, 'done', currentLang === 'en' ? 'Done ✓' : 'Listo ✓');
  setTimeout(() => {
    const ov = document.getElementById('moodify-overlay');
    if (ov) ov.classList.remove('active');
    loadRunning = false;
    setProgress(0, '', '');
  }, 600);
}

/* ── Detector de idioma (en vivo) ───────────────────────────── */
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
    box.innerHTML = `<div class="det-neutral">${t('detecting')}</div>`;
    return;
  }
  const color = det.idioma === 'Español' ? '#B8F000' : det.idioma === 'Inglés' ? '#3D7ECC' : '#E8800A';
  const prevLbl = det.idioma === 'Español' ? t('preview_en') : t('preview_es');
  box.innerHTML = `
    <div class="det-row">
      <span class="det-label">🌐 ${currentLang === 'en' ? 'Language' : 'Idioma'}</span>
      <span class="det-idioma">${det.emoji} ${det.idioma}</span>
    </div>
    <div class="det-barra-bg"><div class="det-barra-fill" style="width:${det.confianza}%;background:${color};"></div></div>
    <div class="det-conf">${currentLang === 'en' ? 'Confidence' : 'Confianza'}: ${det.confianza}%</div>
    <div class="det-prev-label">${prevLbl}</div>
    <div class="det-placeholder det-conf">${currentLang === 'en' ? 'Will appear after transforming ✦' : 'Aparecerá al transformar ✦'}</div>
  `;
}

/* ── Transformar — SSE streaming ────────────────────────────── */
async function doTransform() {
  const msg = document.getElementById('msg-input').value.trim();
  if (!msg) return;
  if (loadRunning) return;

  startLoading();
  setOutputPlaceholders();

  try {
    const res = await fetch(`${API}/api/transform`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ mensaje: msg }),
    });

    if (res.status === 401) { doLogout(); return; }
    if (!res.ok) { stopLoading(); return; }

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'progress') {
            const label = getStageLabel(data.stage, data.label);
            setProgress(data.pct, data.stage, label);
          }

          if (data.type === 'done') {
            textos_es = data.textos_es || {};
            renderOutputs(data);
            renderDetector(data);
            renderTips(data.tips || []);
            selectLang('es');
            checkStatsTab();
            stopLoading();
          }

        } catch (e) {
          console.warn('SSE parse error:', e);
        }
      }
    }
  } catch (e) {
    console.error('Transform stream error:', e);
    stopLoading();
  }
}

function setOutputPlaceholders() {
  ['dipl','ejec','casu'].forEach(k => {
    const el = document.getElementById(`out-${k}`);
    if (el) el.innerHTML = `<span class="output-placeholder">${t('generating')}</span>`;
  });
}

function renderOutputs(data) {
  const map = { dipl: data.diplomatico, ejec: data.ejecutivo, casu: data.casual };
  for (const [key, text] of Object.entries(map)) {
    const el = document.getElementById(`out-${key}`);
    if (!el) continue;
    el.innerHTML = `<span>${escHtml(text)}</span><button class="copy-btn" onclick="copyText('out-${key}')">${t('copy_btn')}</button>`;
  }
}

function renderDetector(data) {
  const det = data.detector || {};
  const box = document.getElementById('detector-box');
  if (!box) return;
  if (!det.idioma || det.idioma === 'desconocido') {
    box.innerHTML = `<div class="det-neutral">🌐 ${currentLang === 'en' ? 'Language — unknown' : 'Idioma — desconocido'}</div>`;
    return;
  }
  const color = det.idioma === 'Español' ? '#B8F000' : det.idioma === 'Inglés' ? '#3D7ECC' : '#E8800A';
  const prevLbl = det.idioma === 'Español' ? t('preview_en') : t('preview_es');
  const prevHtml = data.preview
    ? `<div class="det-prev-box">${escHtml(data.preview)}</div>`
    : `<div class="det-placeholder det-conf">${currentLang === 'en' ? 'Not available' : 'No disponible'}</div>`;
  box.innerHTML = `
    <div class="det-row">
      <span class="det-label">🌐 ${currentLang === 'en' ? 'Language' : 'Idioma'}</span>
      <span class="det-idioma">${det.emoji} ${det.idioma}</span>
    </div>
    <div class="det-barra-bg"><div class="det-barra-fill" style="width:${det.confianza}%;background:${color};"></div></div>
    <div class="det-conf">${currentLang === 'en' ? 'Confidence' : 'Confianza'}: ${det.confianza}%</div>
    <div class="det-prev-label">${prevLbl}</div>
    ${prevHtml}
  `;
}

/* ══════════════════════════════════════════════════════════════
   CLIPPY — mascota animada
══════════════════════════════════════════════════════════════ */

const CLIPPY_MOODS = {
  '🔴': { eyes: 'angry',   color: '#ff6b5b', glow: 'rgba(255,107,91,0.4)' },
  '🟡': { eyes: 'worried', color: '#ffb830', glow: 'rgba(255,184,48,0.4)' },
  '⏰': { eyes: 'alert',   color: '#6ab4ff', glow: 'rgba(106,180,255,0.4)' },
  '✅': { eyes: 'happy',   color: '#B8F000', glow: 'rgba(184,240,0,0.4)'  },
  '💬': { eyes: 'neutral', color: '#b08aff', glow: 'rgba(176,138,255,0.4)' },
  '💡': { eyes: 'happy',   color: '#40e0c0', glow: 'rgba(64,224,192,0.4)' },
};

function getClippyMoodFromTips(tips) {
  if (!tips || !tips.length) return CLIPPY_MOODS['✅'];
  const firstIcon = tips[0].icono;
  return CLIPPY_MOODS[firstIcon] || CLIPPY_MOODS['✅'];
}

function renderClippyCharacter(mood) {
  const { eyes, color, glow } = mood;

  const eyeShapes = {
    happy:   { l: 'M-5,-2 Q0,-7 5,-2',  r: 'M-5,-2 Q0,-7 5,-2',  pupils: false },
    angry:   { l: 'M-5,-4 Q0,-1 5,-4',  r: 'M-5,-4 Q0,-1 5,-4',  pupils: true  },
    worried: { l: 'M-5,-3 Q0,-6 5,-3',  r: 'M-5,-3 Q0,-6 5,-3',  pupils: true  },
    alert:   { l: null, r: null, pupils: true, big: true },
    neutral: { l: null, r: null, pupils: true },
  };

  const e = eyeShapes[eyes] || eyeShapes.neutral;

  let eyeSVG = '';
  if (e.big) {
    eyeSVG = `
      <ellipse cx="-14" cy="-8" rx="8" ry="9" fill="white" opacity="0.95"/>
      <ellipse cx="14"  cy="-8" rx="8" ry="9" fill="white" opacity="0.95"/>
      <circle  cx="-12" cy="-8" r="4" fill="#111" class="clippy-pupil-l"/>
      <circle  cx="16"  cy="-8" r="4" fill="#111" class="clippy-pupil-r"/>
      <circle  cx="-11" cy="-9" r="1.2" fill="white"/>
      <circle  cx="17"  cy="-9" r="1.2" fill="white"/>
    `;
  } else if (e.pupils) {
    eyeSVG = `
      <ellipse cx="-14" cy="-8" rx="6.5" ry="7" fill="white" opacity="0.9"/>
      <ellipse cx="14"  cy="-8" rx="6.5" ry="7" fill="white" opacity="0.9"/>
      <circle  cx="-13" cy="-8" r="3.5" fill="#111" class="clippy-pupil-l"/>
      <circle  cx="15"  cy="-8" r="3.5" fill="#111" class="clippy-pupil-r"/>
      <circle  cx="-12" cy="-9" r="1" fill="white"/>
      <circle  cx="16"  cy="-9" r="1" fill="white"/>
    `;
  } else {
    eyeSVG = `
      <path d="M-20,-8 Q-14,-15 -8,-8"  stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>
      <path d="M8,-8   Q14,-15  20,-8"  stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>
    `;
  }

  let browSVG = '';
  if (eyes === 'angry') {
    browSVG = `
      <line x1="-20" y1="-22" x2="-8"  y2="-17" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="8"   y1="-17" x2="20"  y2="-22" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
    `;
  } else if (eyes === 'worried') {
    browSVG = `
      <line x1="-20" y1="-17" x2="-8"  y2="-22" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="8"   y1="-22" x2="20"  y2="-17" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
    `;
  } else if (eyes === 'alert') {
    browSVG = `
      <line x1="-20" y1="-22" x2="-8" y2="-22" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
      <line x1="8"   y1="-22" x2="20" y2="-22" stroke="${color}" stroke-width="2.5" stroke-linecap="round"/>
    `;
  } else if (eyes === 'happy') {
    browSVG = `
      <path d="M-20,-21 Q-14,-25 -8,-21" stroke="${color}" stroke-width="2" fill="none" stroke-linecap="round"/>
      <path d="M8,-21   Q14,-25  20,-21" stroke="${color}" stroke-width="2" fill="none" stroke-linecap="round"/>
    `;
  }

  let mouthSVG = '';
  if (eyes === 'happy') {
    mouthSVG = `<path d="M-10,10 Q0,18 10,10" stroke="white" stroke-width="2.5" fill="none" stroke-linecap="round"/>`;
  } else if (eyes === 'angry') {
    mouthSVG = `<path d="M-10,14 Q0,8 10,14" stroke="white" stroke-width="2.5" fill="none" stroke-linecap="round"/>`;
  } else if (eyes === 'worried') {
    mouthSVG = `
      <path d="M-8,12 Q0,16 8,12" stroke="white" stroke-width="2" fill="none" stroke-linecap="round"/>
      <line x1="-4" y1="14" x2="-2" y2="16" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
      <line x1="2"  y1="16" x2="4" y2="14"  stroke="white" stroke-width="1.5" stroke-linecap="round"/>
    `;
  } else if (eyes === 'alert') {
    mouthSVG = `<ellipse cx="0" cy="13" rx="5" ry="4" fill="white" opacity="0.8"/>`;
  } else {
    mouthSVG = `<line x1="-8" y1="13" x2="8" y2="13" stroke="white" stroke-width="2.5" stroke-linecap="round"/>`;
  }

  return `
    <svg class="clippy-face" viewBox="-32 -36 64 70" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="0" cy="0" rx="28" ry="30"
        fill="${color}" opacity="0.15" filter="url(#clippy-blur)"/>
      <ellipse cx="0" cy="0" rx="26" ry="28"
        fill="#0a0d12" stroke="${color}" stroke-width="1.8"/>
      <ellipse cx="0" cy="-14" rx="14" ry="7"
        fill="white" opacity="0.04"/>
      ${browSVG}
      ${eyeSVG}
      ${mouthSVG}
      <line x1="-8"  y1="-28" x2="-12" y2="-36" stroke="${color}" stroke-width="1.8" stroke-linecap="round"/>
      <line x1="8"   y1="-28" x2="12"  y2="-36" stroke="${color}" stroke-width="1.8" stroke-linecap="round"/>
      <circle cx="-12" cy="-36" r="2.5" fill="${color}"/>
      <circle cx="12"  cy="-36" r="2.5" fill="${color}"/>
      <defs>
        <filter id="clippy-blur">
          <feGaussianBlur stdDeviation="4"/>
        </filter>
      </defs>
    </svg>
  `;
}

function renderTips(tips) {
  const wrap  = document.getElementById('clippy-wrap');
  const items = document.getElementById('clippy-items');
  const face  = document.getElementById('clippy-face-container');
  if (!wrap || !items) return;

  if (!tips.length) {
    wrap.classList.remove('clippy-visible');
    setTimeout(() => { wrap.style.display = 'none'; }, 400);
    return;
  }

  const mood = getClippyMoodFromTips(tips);

  if (face) {
    face.innerHTML = renderClippyCharacter(mood);
    face.style.setProperty('--clippy-glow', mood.glow);
    face.style.setProperty('--clippy-color', mood.color);
  }

  items.innerHTML = tips.map((tip, i) => `
    <div class="clip-item" style="animation-delay:${i * 0.08}s">
      <span class="clip-icon">${tip.icono}</span>
      <div>
        <div class="clip-title">${escHtml(tip.titulo)}</div>
        <div class="clip-text">${escHtml(tip.texto)}</div>
      </div>
    </div>
  `).join('');

  wrap.style.display = 'flex';
  requestAnimationFrame(() => {
    wrap.classList.add('clippy-visible');
  });

  startClippyBlink();
}

let clippyBlinkTimer = null;
function startClippyBlink() {
  if (clippyBlinkTimer) clearInterval(clippyBlinkTimer);
  clippyBlinkTimer = setInterval(() => {
    const face = document.querySelector('.clippy-face');
    if (!face) { clearInterval(clippyBlinkTimer); return; }
    face.classList.add('clippy-blink');
    setTimeout(() => face.classList.remove('clippy-blink'), 180);
  }, 2800 + Math.random() * 2000);
}

/* ── Seleccionar idioma de salida ───────────────────────────── */
function selectLang(lang) {
  idioma = lang;
  const btnEs = document.getElementById('btn-es');
  const btnEn = document.getElementById('btn-en');
  if (btnEs) { btnEs.textContent = lang === 'es' ? '✓ ES 🇲🇽' : 'ES 🇲🇽'; btnEs.className = `lang-btn${lang==='es'?' on':''}`; }
  if (btnEn) { btnEn.textContent = lang === 'en' ? '✓ EN 🇺🇸' : 'EN 🇺🇸'; btnEn.className = `lang-btn${lang==='en'?' on':''}`; }
}

/* ── Traducir ───────────────────────────────────────────────── */
async function doTranslate() {
  if (!Object.keys(textos_es).length) return;
  startLoading();
  try {
    const data = await apiPost('/api/translate', { textos_es, idioma });
    if (!data) return;
    const map = { dipl: data.diplomatico, ejec: data.ejecutivo, casu: data.casual };
    for (const [key, text] of Object.entries(map)) {
      const el = document.getElementById(`out-${key}`);
      if (el) el.innerHTML = `<span>${escHtml(text)}</span><button class="copy-btn" onclick="copyText('out-${key}')">${t('copy_btn')}</button>`;
    }
  } catch (e) {
    console.error('Translate error:', e);
  } finally {
    stopLoading();
  }
}

/* ── Copiar al portapapeles ─────────────────────────────────── */
function copyText(elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  const span = el.querySelector('span');
  const text = span ? span.textContent : '';
  navigator.clipboard.writeText(text).then(() => {
    const btn = el.querySelector('.copy-btn');
    if (btn) {
      const orig = t('copy_btn');
      btn.textContent = t('copied_btn');
      setTimeout(() => btn.textContent = orig, 1500);
    }
  });
}

/* ── Config modal ───────────────────────────────────────────── */
function openConfig() {
  const overlay = document.getElementById('cfg-overlay');
  if (overlay) overlay.classList.add('open');

  const uname = sessionStorage.getItem('moodify_username') || username || 'usuario';
  const unameDisplay = document.getElementById('cfg-username-display');
  if (unameDisplay) unameDisplay.textContent = '@' + uname;

  const emailDisplay = document.getElementById('cfg-email-display');
  if (emailDisplay && emailDisplay.textContent === '—') {
    apiGet('/api/perfil').then(data => {
      if (data && data.email) emailDisplay.textContent = data.email;
    }).catch(() => {});
  }

  // Marcar botón de idioma activo en el modal
  ['es','en'].forEach(l => {
    const btn = document.getElementById('cfg-btn-' + l);
    if (btn) btn.classList.toggle('active', l === currentLang);
  });

  applyI18n();
}

function closeConfig() {
  const overlay = document.getElementById('cfg-overlay');
  if (overlay) overlay.classList.remove('open');
}

function closeConfigOutside(e) {
  if (e.target === document.getElementById('cfg-overlay')) closeConfig();
}

function setAgentLang(val) {
  setLang(val);
  // Actualizar estado visual de los botones del modal
  ['es','en'].forEach(l => {
    const btn = document.getElementById('cfg-btn-' + l);
    if (btn) btn.classList.toggle('active', l === val);
  });
}

/* ── Cambio de username ─────────────────────────────────────── */
async function startChangeUsername() {
  const prompt1 = currentLang === 'en'
    ? 'New username (letters, numbers, underscore, min 3 chars):'
    : 'Nuevo nombre de usuario (letras, números, guion bajo, mín 3 caracteres):';
  const newU = prompt(prompt1);
  if (!newU || !newU.trim()) return;

  try {
    const result = await apiPut('/api/perfil/username', { username: newU.trim() });
    if (!result) {
      alert(currentLang === 'en' ? '❌ Connection error. Try again.' : '❌ Error de conexión. Intenta de nuevo.');
      return;
    }
    if (!result.ok) {
      alert(result.data?.detail || (currentLang === 'en' ? '❌ Error updating username.' : '❌ Error al actualizar el nombre de usuario.'));
      return;
    }
    username = newU.trim();
    sessionStorage.setItem('moodify_username', username);
    const navU = document.getElementById('nav-username');
    if (navU) navU.textContent = '@' + username;
    const cfgU = document.getElementById('cfg-username-display');
    if (cfgU) cfgU.textContent = '@' + username;
    alert(currentLang === 'en' ? '✅ Username updated successfully.' : '✅ Nombre de usuario actualizado correctamente.');
  } catch (e) {
    alert(currentLang === 'en' ? '❌ Connection error.' : '❌ Error de conexión.');
  }
}

/* ── Cambio de email ────────────────────────────────────────── */
async function startChangeEmail() {
  const prompt1 = currentLang === 'en' ? 'New email address:' : 'Nuevo correo electrónico:';
  const newEmail = prompt(prompt1);
  if (!newEmail || !newEmail.trim()) return;

  try {
    const result = await apiPut('/api/perfil/email', { email: newEmail.trim() });
    if (!result) {
      alert(currentLang === 'en' ? '❌ Connection error.' : '❌ Error de conexión.');
      return;
    }
    if (!result.ok) {
      alert(result.data?.detail || (currentLang === 'en' ? '❌ Error updating email.' : '❌ Error al actualizar el correo.'));
      return;
    }
    const emailDisplay = document.getElementById('cfg-email-display');
    if (emailDisplay) emailDisplay.textContent = newEmail.trim();
    alert(currentLang === 'en'
      ? '✅ A verification link was sent to your new email. Confirm it to complete the change.'
      : '✅ Se envió un enlace de verificación a tu nuevo correo. Confírmalo para completar el cambio.');
  } catch (e) {
    alert(currentLang === 'en' ? '❌ Connection error.' : '❌ Error de conexión.');
  }
}

/* ── Cambio de contraseña ───────────────────────────────────── */
async function startChangePassword() {
  const oldPass = prompt(currentLang === 'en'
    ? 'Current password:'
    : 'Contraseña actual:');
  if (!oldPass) return;

  const newPass = prompt(currentLang === 'en'
    ? 'New password (min 6 characters):'
    : 'Nueva contraseña (mínimo 6 caracteres):');
  if (!newPass || newPass.trim().length < 6) {
    alert(currentLang === 'en'
      ? '❌ Password must be at least 6 characters.'
      : '❌ La contraseña debe tener al menos 6 caracteres.');
    return;
  }

  try {
    const result = await apiPut('/api/perfil/password', {
      old_password: oldPass,
      new_password: newPass.trim(),
    });
    if (!result) {
      alert(currentLang === 'en' ? '❌ Connection error.' : '❌ Error de conexión.');
      return;
    }
    if (!result.ok) {
      alert(result.data?.detail || (currentLang === 'en'
        ? '❌ Error updating password.'
        : '❌ Error al actualizar la contraseña.'));
      return;
    }
    alert(currentLang === 'en'
      ? '✅ Password updated successfully.'
      : '✅ Contraseña actualizada correctamente.');
  } catch (e) {
    alert(currentLang === 'en' ? '❌ Connection error.' : '❌ Error de conexión.');
  }
}

/* ── Eliminar cuenta ────────────────────────────────────────── */
async function confirmDeleteAccount() {
  const msg1 = currentLang === 'en'
    ? '⚠️ Are you sure you want to delete your account?\n\nThis will permanently delete ALL your messages, history, and favorites. This action cannot be undone.'
    : '⚠️ ¿Estás seguro de que deseas eliminar tu cuenta?\n\nEsto eliminará permanentemente TODOS tus mensajes, historial y favoritos. Esta acción no se puede deshacer.';

  if (!confirm(msg1)) return;

  const confirmWord = currentLang === 'en' ? 'DELETE' : 'ELIMINAR';
  const msg2 = currentLang === 'en'
    ? `Type "${confirmWord}" to confirm permanent deletion:`
    : `Escribe "${confirmWord}" para confirmar la eliminación permanente:`;

  const input = prompt(msg2);
  if (input !== confirmWord) {
    alert(currentLang === 'en' ? 'Action cancelled.' : 'Acción cancelada.');
    return;
  }

  try {
    const result = await apiDelete('/api/cuenta');
    if (result && result.ok === false) {
      alert(result.detail || (currentLang === 'en' ? '❌ Error deleting account.' : '❌ Error al eliminar la cuenta.'));
      return;
    }
    alert(currentLang === 'en' ? '✅ Account deleted successfully.' : '✅ Cuenta eliminada correctamente.');
    doLogout();
  } catch (e) {
    alert(currentLang === 'en' ? '❌ Connection error. Try again.' : '❌ Error de conexión. Intenta de nuevo.');
  }
}

/* ── Utilidades ─────────────────────────────────────────────── */
function escHtml(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}