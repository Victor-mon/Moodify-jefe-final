/* historial.js — Historial, favoritos y estadísticas */

const MINIMO_STATS_H = 10;

// ── Badges y helpers ──────────────────────────────────────────
const BADGE_CLASSES = {
  solicitud:'hist-badge-solicitud', reporte:'hist-badge-reporte',
  comunicado:'hist-badge-comunicado', queja:'hist-badge-queja',
  aviso:'hist-badge-aviso', pregunta:'hist-badge-pregunta',
};
const TONO_EMOJI = { frustracion:'🔴', urgencia:'⏰', positivo:'✅', neutro:'⚪' };

function badgeHtml(tipo) {
  const cls = BADGE_CLASSES[tipo] || 'hist-badge-general';
  return `<span class="hist-badge ${cls}">${tipo}</span>`;
}
function truncate(str, n) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '…' : str;
}

// ── Render historial / favoritos ──────────────────────────────
function renderItems(items, containerId, soloFavoritos = false) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!items || !items.length) {
    el.innerHTML = `<div class="empty-state">${soloFavoritos ? 'Aún no tienes favoritos guardados.' : 'Aún no has transformado ningún mensaje.'}</div>`;
    return;
  }
  el.innerHTML = items.map(it => {
    const esFav  = it.es_favorito || false;
    const id     = it.id || '';
    const fecha  = (it.created_at || '').slice(0, 16).replace('T', ' ');
    const orig   = truncate(it.mensaje_original   || '', 120);
    const dipl   = truncate(it.version_diplomatica || '', 80);
    const ejec   = truncate(it.version_ejecutiva   || '', 80);
    const casu   = truncate(it.version_casual      || '', 80);
    const tipo   = it.tipo_mensaje   || 'general';
    const tono   = it.tono_emocional || 'neutro';
    return `
      <div class="hist-item" id="hist-${id}">
        <div class="hist-meta">
          ${badgeHtml(tipo)}
          <span style="font-size:13px;">${TONO_EMOJI[tono] || '⚪'}</span>
          <span class="hist-time">${fecha}</span>
          <button
            class="hist-fav-btn${esFav ? ' is-fav' : ''}"
            title="${esFav ? 'Quitar de favoritos' : 'Agregar a favoritos'}"
            onclick="toggleFav('${id}', ${esFav})"
          >${esFav ? '★' : '☆'}</button>
        </div>
        <div class="hist-original">"${escHtml2(orig)}"</div>
        <div class="hist-versions">
          <div class="hist-ver"><div class="hist-ver-label">🤝 Diplomático</div>${escHtml2(dipl)}</div>
          <div class="hist-ver"><div class="hist-ver-label">💼 Ejecutivo</div>${escHtml2(ejec)}</div>
          <div class="hist-ver"><div class="hist-ver-label">😊 Casual</div>${escHtml2(casu)}</div>
        </div>
      </div>`;
  }).join('');
}

// ── Toggle favorito ───────────────────────────────────────────
async function toggleFav(recordId, estadoActual) {
  try {
    const data = await apiPost(`/api/favorito/${recordId}`, { estado: estadoActual });
    if (!data) return;
    // Actualiza el botón en el DOM
    const btn = document.querySelector(`#hist-${recordId} .hist-fav-btn`);
    if (btn) {
      const nuevoEstado = data.es_favorito;
      btn.classList.toggle('is-fav', nuevoEstado);
      btn.title      = nuevoEstado ? 'Quitar de favoritos' : 'Agregar a favoritos';
      btn.textContent = nuevoEstado ? '★' : '☆';
      btn.setAttribute('onclick', `toggleFav('${recordId}', ${nuevoEstado})`);
    }
  } catch (e) {
    console.error('Toggle fav error:', e);
  }
}

// ── Cargar historial ──────────────────────────────────────────
async function loadHistorial() {
  const el = document.getElementById('historial-content');
  if (el) el.innerHTML = '<div class="empty-state">Cargando...</div>';
  try {
    const data = await apiGet('/api/historial');
    renderItems(Array.isArray(data) ? data : [], 'historial-content', false);
  } catch (e) {
    if (el) el.innerHTML = '<div class="empty-state">Error al cargar el historial.</div>';
  }
}

// ── Cargar favoritos ──────────────────────────────────────────
async function loadFavoritos() {
  const el = document.getElementById('favoritos-content');
  if (el) el.innerHTML = '<div class="empty-state">Cargando...</div>';
  try {
    const data = await apiGet('/api/favoritos');
    renderItems(Array.isArray(data) ? data : [], 'favoritos-content', true);
  } catch (e) {
    if (el) el.innerHTML = '<div class="empty-state">Error al cargar favoritos.</div>';
  }
}

// ── Cargar estadísticas ───────────────────────────────────────
async function loadEstadisticas() {
  const el = document.getElementById('stats-content');
  if (el) el.innerHTML = '<div class="empty-state">Cargando...</div>';
  try {
    const stats = await apiGet('/api/estadisticas');
    if (el) el.innerHTML = renderStats(stats);
  } catch (e) {
    if (el) el.innerHTML = '<div class="empty-state">Error al cargar estadísticas.</div>';
  }
}

// ── Render estadísticas ───────────────────────────────────────
function renderStats(stats) {
  const total = stats.total || 0;
  if (total < MINIMO_STATS_H) {
    const pct = Math.round((total / MINIMO_STATS_H) * 100);
    return `<div class="stats-lock">
      <div class="stats-lock-icon">📊</div>
      <div class="stats-lock-title">Estadísticas en camino</div>
      <div class="stats-lock-sub">Necesitas al menos <strong>${MINIMO_STATS_H} mensajes</strong> transformados.<br><br>Te faltan <strong>${MINIMO_STATS_H - total}</strong> más.</div>
      <div>
        <div class="stats-progress-bar"><div class="stats-progress-fill" style="width:${pct}%"></div></div>
        <div class="stats-progress-label">${total} / ${MINIMO_STATS_H} mensajes</div>
      </div>
    </div>`;
  }

  const favoritos = stats.favoritos || 0;
  const emociones = stats.emociones || {};
  const tipos     = stats.tipos     || {};
  const dia_top   = stats.dia_top   || '—';
  const msgs_dia  = stats.msgs_dia_top || 0;

  const COLORES_EMO  = { frustracion:'#FF5555', urgencia:'#D4A000', positivo:'#B8F000', neutro:'#888' };
  const COLORES_TIPO = { solicitud:'#3D7ECC', reporte:'#87C200', comunicado:'#D4820A', queja:'#CC3333', aviso:'#8833CC', pregunta:'#0099BB', general:'#888' };
  const LABELS_EMO   = { frustracion:'😤 Frustración', urgencia:'⏰ Urgencia', positivo:'✅ Positivo', neutro:'⚪ Neutro' };
  const LABELS_TIPO  = { solicitud:'Solicitud', reporte:'Reporte', comunicado:'Comunicado', queja:'Queja', aviso:'Aviso', pregunta:'Pregunta', general:'General' };

  const maxEmo  = Math.max(...Object.values(emociones), 1);
  const maxTipo = Math.max(...Object.values(tipos), 1);

  const barrasEmo  = Object.entries(emociones).map(([k, v]) => `
    <div class="stat-bar-row">
      <span class="stat-bar-label">${LABELS_EMO[k] || k}</span>
      <div class="stat-bar-track"><div class="stat-bar-fill" style="width:${Math.round(v/maxEmo*100)}%;background:${COLORES_EMO[k]||'#888'};"></div></div>
      <span class="stat-bar-val">${v}</span>
    </div>`).join('');

  const barrasTipo = Object.entries(tipos).map(([k, v]) => `
    <div class="stat-bar-row">
      <span class="stat-bar-label">${LABELS_TIPO[k] || k}</span>
      <div class="stat-bar-track"><div class="stat-bar-fill" style="width:${Math.round(v/maxTipo*100)}%;background:${COLORES_TIPO[k]||'#888'};"></div></div>
      <span class="stat-bar-val">${v}</span>
    </div>`).join('');

  const emoDom  = Object.keys(emociones)[0] || 'neutro';
  const emoPct  = total ? Math.round((emociones[emoDom] || 0) / total * 100) : 0;
  const tipoDom = Object.keys(tipos)[0] || 'general';

  return `<div class="stats-grid">
    <div class="stat-card"><div class="stat-num">${total}</div><div class="stat-label">Mensajes transformados</div></div>
    <div class="stat-card"><div class="stat-num">${favoritos}</div><div class="stat-label">Guardados como favoritos</div></div>
    <div class="stat-card"><div class="stat-num" style="font-size:1.3rem">${LABELS_EMO[emoDom]||emoDom}</div><div class="stat-label">Emoción dominante · ${emoPct}%</div></div>
    <div class="stat-card"><div class="stat-num" style="font-size:1.3rem">${LABELS_TIPO[tipoDom]||tipoDom}</div><div class="stat-label">Tipo más frecuente</div></div>
    <div class="stat-card stat-card-wide"><div class="stat-section-title">Distribución emocional</div>${barrasEmo}</div>
    <div class="stat-card stat-card-wide"><div class="stat-section-title">Tipos de mensaje</div>${barrasTipo}</div>
    <div class="stat-card stat-card-wide"><div class="stat-num" style="font-size:1.1rem">${dia_top}</div><div class="stat-label">Día más activo · ${msgs_dia} mensajes</div></div>
  </div>`;
}

// ── Escape helper local ────────────────────────────────────────
function escHtml2(str) {
  if (!str) return '';
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}